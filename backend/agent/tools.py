"""Tool wrappers around existing services.

Each wrapper provides a uniform interface for the agent controller while
delegating to the original, stable implementation.  Internal behaviour of
existing services is NOT modified.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from backend.agent.models import EvaluationResult, ToolInvocationRecord
from backend.core.config import settings


# ---------------------------------------------------------------------------
# Base tool
# ---------------------------------------------------------------------------

class _BaseTool:
    name: str = "base"

    def _record(
        self,
        input_summary: str,
        output_summary: str,
        success: bool,
        fallback_used: bool,
        start: float,
    ) -> ToolInvocationRecord:
        return ToolInvocationRecord(
            tool_name=self.name,
            input_summary=input_summary[:200],
            output_summary=output_summary[:200],
            success=success,
            fallback_used=fallback_used,
            duration_ms=round((time.time() - start) * 1000, 1),
        )


# ---------------------------------------------------------------------------
# Rule-based judge
# ---------------------------------------------------------------------------

class RuleJudgeTool(_BaseTool):
    name = "rule_judge"

    def invoke(
        self, question: str, correct_answer: str, user_answer: str
    ) -> tuple[EvaluationResult, ToolInvocationRecord]:
        from backend.services.evaluator_rules import evaluate_answer

        start = time.time()
        try:
            result = evaluate_answer(question, correct_answer, user_answer)
            ev = EvaluationResult(
                scores=result["scores"],
                overall_score=result["overall_score"],
                feedback=result["feedback"],
                missing_points=result.get("missing_points", []),
                next_direction=result.get("next_direction"),
                provenance="rule",
            )
            rec = self._record("rule_judge", f"score={ev.overall_score:.2f}", True, False, start)
            return ev, rec
        except Exception as exc:
            rec = self._record("rule_judge", str(exc)[:100], False, False, start)
            raise


# ---------------------------------------------------------------------------
# LLM judge
# ---------------------------------------------------------------------------

class LLMJudgeTool(_BaseTool):
    name = "llm_judge"

    def invoke(
        self, question: str, correct_answer: str, user_answer: str, judge_count: Optional[int] = None
    ) -> tuple[Optional[EvaluationResult], ToolInvocationRecord]:
        from backend.services.llm_provider import evaluate_with_llm

        start = time.time()
        try:
            result = evaluate_with_llm(
                question,
                correct_answer,
                user_answer,
                judge_count_override=judge_count,
            )
            if result is None:
                rec = self._record("llm_judge", "llm_unavailable", True, False, start)
                return None, rec
            ev = EvaluationResult(
                scores=result["scores"],
                overall_score=result["overall_score"],
                feedback=result["feedback"],
                missing_points=result.get("missing_points", []),
                next_direction=result.get("next_direction"),
                reasoning=result.get("reasoning"),
                provenance="llm",
            )
            if isinstance(result.get("_multi_judge_meta"), dict):
                ev.policy_meta["multi_judge"] = result["_multi_judge_meta"]
            rec = self._record("llm_judge", f"score={ev.overall_score:.2f}", True, False, start)
            return ev, rec
        except Exception as exc:
            rec = self._record("llm_judge", f"error: {exc}"[:100], False, False, start)
            return None, rec


# ---------------------------------------------------------------------------
# Validator / critic
# ---------------------------------------------------------------------------

class ValidatorTool(_BaseTool):
    name = "validator"

    def validate(self, ev: EvaluationResult) -> tuple[bool, str]:
        """Check schema compliance and score ranges.

        Returns (is_valid, reason).
        """
        required_dims = {"correctness", "depth", "clarity", "practicality", "tradeoffs"}
        if not required_dims.issubset(ev.scores.keys()):
            return False, f"missing dimensions: {required_dims - set(ev.scores.keys())}"

        for dim, val in ev.scores.items():
            if not (0.0 <= val <= 1.0):
                return False, f"{dim} out of range: {val}"

        if not (0.0 <= ev.overall_score <= 1.0):
            return False, f"overall_score out of range: {ev.overall_score}"

        return True, "ok"


# ---------------------------------------------------------------------------
# Follow-up generator
# ---------------------------------------------------------------------------

class FollowUpGeneratorTool(_BaseTool):
    name = "followup_generator"

    def invoke(
        self,
        original_question: str,
        user_answer: str,
        feedback: str,
        missing_points: List[str],
        followup_count: int = 0,
        correct_answer: str = "",
    ) -> tuple[Optional[str], str, ToolInvocationRecord]:
        """Returns (followup_text, source, record).

        source is "llm" | "template".
        """
        start = time.time()

        # Try LLM first
        from backend.services.llm_provider import generate_followup_with_llm

        llm_result = generate_followup_with_llm(
            original_question=original_question,
            user_answer=user_answer,
            feedback=feedback,
            missing_points=missing_points,
            followup_count=followup_count,
            correct_answer=correct_answer,
        )
        if llm_result:
            rec = self._record("followup_gen", "llm", True, False, start)
            return llm_result, "llm", rec

        # Fallback to template
        from backend.services.interview_phrases import get_followup_phrase

        template_result = get_followup_phrase(missing_points, feedback)
        rec = self._record("followup_gen", "template_fallback", True, True, start)
        return template_result, "template", rec


# ---------------------------------------------------------------------------
# Resume parser
# ---------------------------------------------------------------------------

class ResumeParserTool(_BaseTool):
    name = "resume_parser"

    def invoke(self, db: DBSession, resume_id: int) -> tuple[Optional[List[str]], ToolInvocationRecord]:
        """Returns (skills_list, record)."""
        from backend.db.models import Resume

        start = time.time()
        try:
            resume = db.query(Resume).filter(Resume.id == resume_id).first()
            if resume and resume.parsed_json:
                skills = resume.parsed_json.get("skills", [])
                rec = self._record("resume_parser", f"{len(skills)} skills", True, False, start)
                return skills, rec
            rec = self._record("resume_parser", "no_data", True, False, start)
            return None, rec
        except Exception as exc:
            rec = self._record("resume_parser", str(exc)[:100], False, False, start)
            return None, rec


# ---------------------------------------------------------------------------
# Speech analysis
# ---------------------------------------------------------------------------

class SpeechAnalysisTool(_BaseTool):
    name = "speech_analysis"

    def invoke(self, audio_data: Dict[str, Any]) -> tuple[Optional[Dict], ToolInvocationRecord]:
        from backend.services.audio_processor import process_audio_answer

        start = time.time()
        try:
            result = process_audio_answer(audio_data)
            rec = self._record("speech_analysis", "ok", True, False, start)
            return result, rec
        except Exception as exc:
            rec = self._record("speech_analysis", str(exc)[:100], False, False, start)
            return None, rec


# ---------------------------------------------------------------------------
# Expression analysis
# ---------------------------------------------------------------------------

class ExpressionAnalysisTool(_BaseTool):
    name = "expression_analysis"

    def invoke(self, image_data: str) -> tuple[Optional[Dict], ToolInvocationRecord]:
        from backend.services.expression_analyzer import analyze_expression

        start = time.time()
        try:
            result = analyze_expression(image_data, enforce_detection=False)
            rec = self._record("expression_analysis", "ok", True, False, start)
            return result, rec
        except Exception as exc:
            rec = self._record("expression_analysis", str(exc)[:100], False, False, start)
            return None, rec


# ---------------------------------------------------------------------------
# Report synthesizer
# ---------------------------------------------------------------------------

class ReportSynthesisTool(_BaseTool):
    name = "report_synthesis"

    def invoke(self, db: DBSession, session_id: int) -> tuple[Optional[Dict], ToolInvocationRecord]:
        from backend.services.report_generator import generate_report

        start = time.time()
        try:
            report = generate_report(db, session_id)
            rec = self._record("report_synthesis", "ok", True, False, start)
            return report, rec
        except Exception as exc:
            rec = self._record("report_synthesis", str(exc)[:100], False, False, start)
            return None, rec
