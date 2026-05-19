"""Resume-focused interview agent.

The agent owns the resume-only interview mode. It plans questions from resume
evidence, keeps follow-ups tied to that same evidence, and stops when the
planned resume probes are exhausted.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from backend.db.models import AskedQuestion, Evaluation, InterviewSession, Resume


RESUME_TOPIC_PREFIX = "ResumeQA"


@dataclass(frozen=True)
class ResumeProbe:
    index: int
    topic: str
    evidence_type: str
    evidence: str
    skills: List[str]


@dataclass(frozen=True)
class ResumeQuestion:
    question: str
    reference_answer: str
    topic: str
    evidence: str


class ResumeQAAgent:
    """Plan and execute resume-only questioning.

    This intentionally does not depend on LangChain at runtime. The project
    already has a stable ZhipuAI provider, so this agent uses that existing API
    surface and keeps an optional-framework style orchestration boundary.
    """

    def __init__(self, db: DBSession, session: InterviewSession) -> None:
        self.db = db
        self.session = session
        self.resume = self._load_resume()
        self.resume_data = self.resume.parsed_json if self.resume and self.resume.parsed_json else {}
        self.probes = build_resume_probes(self.resume_data, max_items=max(1, session.total_rounds or 3))

    def has_resume_context(self) -> bool:
        return bool(self.resume_data)

    def first_question(self, track: str, difficulty: int) -> Optional[ResumeQuestion]:
        probe = self.probes[0] if self.probes else None
        if not probe:
            return None
        return self._generate_question(probe, track=track, difficulty=difficulty)

    def next_question_after_current(self, track: str, difficulty: int) -> Optional[ResumeQuestion]:
        completed = self._completed_resume_questions_count()
        if completed >= min(len(self.probes), self.session.total_rounds or len(self.probes)):
            return None
        probe = self.probes[completed]
        return self._generate_question(probe, track=track, difficulty=difficulty)

    def should_follow_up(
        self,
        asked_question: AskedQuestion,
        evaluation: Dict,
        answer_text: str,
        followup_count: int,
    ) -> tuple[bool, str]:
        if followup_count >= 1:
            return False, "resume probe follow-up limit reached"
        if not asked_question or asked_question.qbank_id is not None:
            return False, "not a resume probe"

        score = float(evaluation.get("overall_score", 0.0) or 0.0)
        missing_points = evaluation.get("missing_points") or []
        answer_len = len((answer_text or "").strip())

        if answer_len < 80:
            return True, "resume answer is too brief; verify concrete ownership and details"
        if score < 0.72:
            return True, "resume evidence still has gaps; ask one targeted follow-up"
        if len(missing_points) >= 2:
            return True, "resume answer left multiple evidence gaps"
        return False, "resume evidence is sufficiently covered"

    def make_follow_up(
        self,
        asked_question: AskedQuestion,
        answer_text: str,
        evaluation: Dict,
        followup_count: int,
    ) -> str:
        probe = self._probe_for_question(asked_question)
        evidence = probe.evidence if probe else asked_question.question_text
        skills = probe.skills if probe else []

        try:
            from backend.services.llm_provider import generate_resume_probe_followup_llm

            llm_result = generate_resume_probe_followup_llm(
                resume_evidence=evidence,
                skills=skills,
                original_question=asked_question.question_text,
                user_answer=answer_text,
                feedback=str(evaluation.get("feedback", "")),
                missing_points=list(evaluation.get("missing_points") or []),
                followup_count=followup_count,
            )
            if llm_result:
                return llm_result
        except Exception:
            pass

        return _fallback_resume_followup(
            evidence=evidence,
            missing_points=list(evaluation.get("missing_points") or []),
            answer_text=answer_text,
        )

    def _load_resume(self) -> Optional[Resume]:
        if not self.session.resume_id:
            return None
        return self.db.query(Resume).filter(Resume.id == self.session.resume_id).first()

    def _completed_resume_questions_count(self) -> int:
        return (
            self.db.query(AskedQuestion)
            .join(Evaluation, Evaluation.asked_question_id == AskedQuestion.id)
            .filter(
                AskedQuestion.session_id == self.session.id,
                AskedQuestion.qbank_id.is_(None),
            )
            .count()
        )

    def _probe_for_question(self, asked_question: AskedQuestion) -> Optional[ResumeProbe]:
        if not asked_question:
            return None
        topic = asked_question.topic or ""
        if topic.startswith(f"{RESUME_TOPIC_PREFIX}:"):
            try:
                idx = int(topic.split(":", 1)[1])
                for probe in self.probes:
                    if probe.index == idx:
                        return probe
            except ValueError:
                return None
        return None

    def _generate_question(self, probe: ResumeProbe, track: str, difficulty: int) -> ResumeQuestion:
        try:
            from backend.services.llm_provider import generate_resume_probe_question_llm

            llm_result = generate_resume_probe_question_llm(
                resume_parsed=self.resume_data,
                probe={
                    "evidence_type": probe.evidence_type,
                    "evidence": probe.evidence,
                    "skills": probe.skills,
                },
                track=track,
                difficulty=difficulty,
            )
            if llm_result:
                return ResumeQuestion(
                    question=llm_result["question"],
                    reference_answer=llm_result["reference_answer"],
                    topic=f"{RESUME_TOPIC_PREFIX}:{probe.index}",
                    evidence=probe.evidence,
                )
        except Exception:
            pass

        fallback = _fallback_resume_question(probe, track, difficulty)
        return ResumeQuestion(
            question=fallback["question"],
            reference_answer=fallback["reference_answer"],
            topic=f"{RESUME_TOPIC_PREFIX}:{probe.index}",
            evidence=probe.evidence,
        )


def build_resume_probes(resume_data: Dict, max_items: int = 3) -> List[ResumeProbe]:
    skills = _clean_items(resume_data.get("skills") or [], limit=8)
    probes: List[ResumeProbe] = []

    for evidence_type, key in (("project", "projects"), ("experience", "experience")):
        for item in _clean_items(resume_data.get(key) or [], limit=max_items):
            probes.append(
                ResumeProbe(
                    index=len(probes),
                    topic=f"{RESUME_TOPIC_PREFIX}:{len(probes)}",
                    evidence_type=evidence_type,
                    evidence=item,
                    skills=_match_skills(item, skills),
                )
            )
            if len(probes) >= max_items:
                return probes

    for skill in skills[:max_items]:
        probes.append(
            ResumeProbe(
                index=len(probes),
                topic=f"{RESUME_TOPIC_PREFIX}:{len(probes)}",
                evidence_type="skill",
                evidence=skill,
                skills=[skill],
            )
        )
        if len(probes) >= max_items:
            return probes

    return probes


def _clean_items(values: List, limit: int) -> List[str]:
    cleaned: List[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or "未识别" in text:
            continue
        if text not in cleaned:
            cleaned.append(text[:220])
        if len(cleaned) >= limit:
            break
    return cleaned


def _match_skills(evidence: str, skills: List[str]) -> List[str]:
    evidence_l = evidence.lower()
    matched = [skill for skill in skills if skill.lower() in evidence_l]
    return matched[:4] if matched else skills[:3]


def _fallback_resume_question(probe: ResumeProbe, track: str, difficulty: int) -> Dict[str, str]:
    skill_hint = "、".join(probe.skills[:3]) if probe.skills else f"{track} 相关技术"
    if probe.evidence_type == "skill":
        question = (
            f"你简历里写到 {probe.evidence}。请结合一个真实项目，说明你如何使用它解决问题，"
            "以及你做过哪些权衡。"
        )
    else:
        angle = "架构设计、关键实现和效果验证" if difficulty >= 3 else "你的职责、实现步骤和遇到的问题"
        question = (
            f"简历中提到「{probe.evidence}」。请围绕 {skill_hint}，讲讲这个经历里"
            f"你具体负责的{angle}。"
        )
    reference = (
        "回答应包含简历证据对应的业务背景、个人职责、关键技术选择、实现细节、"
        "遇到的问题、解决方案、结果指标，以及能证明本人真实参与的细节。"
    )
    return {"question": question, "reference_answer": reference}


def _fallback_resume_followup(evidence: str, missing_points: List[str], answer_text: str) -> str:
    if len((answer_text or "").strip()) < 80:
        return f"刚才这段还比较概括。围绕「{evidence[:60]}」，你能补充一个你亲手处理的关键细节或线上问题吗？"
    if missing_points:
        return f"你刚才的回答里「{missing_points[0]}」还不够具体。结合「{evidence[:60]}」，当时你是怎么判断和落地的？"
    return f"结合「{evidence[:60]}」，如果重新做一次，你会保留什么设计，又会改掉什么？"
