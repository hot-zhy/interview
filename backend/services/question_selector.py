"""Question selector service with adaptive strategy."""
import random
import math
from dataclasses import dataclass
from typing import List, Optional, Dict, Protocol
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.db.models import QuestionBank, InterviewSession, AskedQuestion, Evaluation
from backend.core.config import settings
from backend.services.personalized_algorithms import (
    SkillMasteryProfile,
    estimate_ability,
    ucb_chapter_score,
    compute_personalization_weights,
)
from backend.services.selection_rl import (
    build_bandit_feature_snapshot,
    choose_chapter_with_contextual_bandit,
)

try:
    from rapidfuzz import fuzz as _rf_fuzz  # type: ignore
except Exception:  # pragma: no cover
    _rf_fuzz = None


@dataclass
class SelectionContext:
    """State passed to chapter-selection policies."""

    db: Session
    session: InterviewSession
    current_difficulty: int
    track_chapters: Dict[str, float]
    asked_chapters: List[str]
    resume_skills: Optional[List[str]]
    missing_chapters: Optional[List[str]]
    llm_context: Optional[Dict]


class ChapterSelectionPolicy(Protocol):
    """Strategy interface for chapter selection."""

    def select_chapter(self, ctx: SelectionContext) -> str:
        ...


def _partial_ratio(a: str, b: str) -> int:
    """Return an int in [0,100] similar to rapidfuzz.fuzz.partial_ratio."""
    a = (a or "").lower()
    b = (b or "").lower()
    if not a or not b:
        return 0
    if _rf_fuzz is not None:
        return int(_rf_fuzz.partial_ratio(a, b))
    # Fallback: SequenceMatcher ratio (not true partial ratio, but keeps system working)
    return int(SequenceMatcher(None, a, b).ratio() * 100)


class RulePriorityChapterPolicy:
    """Baseline policy: priority cascade + weighted random fallback."""

    def select_chapter(self, ctx: SelectionContext) -> str:
        return _select_chapter(
            track_chapters=ctx.track_chapters,
            resume_skills=ctx.resume_skills,
            missing_chapters=ctx.missing_chapters,
            asked_chapters=ctx.asked_chapters,
            llm_context=ctx.llm_context,
        )


class ThompsonChapterPolicy:
    """Maintain legacy Thompson behavior behind the strategy interface."""

    def select_chapter(self, ctx: SelectionContext) -> str:
        rule_choice = _select_chapter(
            track_chapters=ctx.track_chapters,
            resume_skills=ctx.resume_skills,
            missing_chapters=ctx.missing_chapters,
            asked_chapters=ctx.asked_chapters,
            llm_context=ctx.llm_context,
        )
        ts_chapter = _select_chapter_thompson(
            db=ctx.db,
            session=ctx.session,
            track_chapters=ctx.track_chapters,
            asked_chapters=ctx.asked_chapters,
            current_difficulty=ctx.current_difficulty,
        )
        if ts_chapter and not ctx.missing_chapters and not ctx.resume_skills:
            return ts_chapter
        return rule_choice


class ContextualBanditChapterPolicy:
    """Contextual-bandit chapter selector with safe fallback."""

    def select_chapter(self, ctx: SelectionContext) -> str:
        fallback = RulePriorityChapterPolicy().select_chapter(ctx)
        if not ctx.track_chapters:
            return fallback

        feature_snapshot = build_bandit_feature_snapshot(
            db=ctx.db,
            session=ctx.session,
            current_difficulty=ctx.current_difficulty,
            track_chapters=ctx.track_chapters,
            asked_chapters=ctx.asked_chapters,
            resume_skills=ctx.resume_skills or [],
            missing_chapters=ctx.missing_chapters or [],
            llm_context=ctx.llm_context or {},
        )
        choice = choose_chapter_with_contextual_bandit(
            snapshot=feature_snapshot,
            candidate_chapters=list(ctx.track_chapters.keys()),
            fallback_chapter=fallback,
            policy_path=getattr(settings, "rl_policy_artifact_path", ""),
            alpha=float(getattr(settings, "rl_bandit_alpha", 0.35)),
        )
        return choice or fallback


def _resolve_chapter_policy(strategy: str) -> ChapterSelectionPolicy:
    if strategy == "thompson_sampling":
        return ThompsonChapterPolicy()
    if strategy == "contextual_bandit":
        return ContextualBanditChapterPolicy()
    return RulePriorityChapterPolicy()


def select_question(
    db: Session,
    session: InterviewSession,
    current_difficulty: int,
    resume_skills: Optional[List[str]] = None,
    missing_chapters: Optional[List[str]] = None,
    next_direction_hints: Optional[List[str]] = None
) -> Optional[QuestionBank]:
    """
    Select next question based on adaptive strategy.
    
    Args:
        db: Database session
        session: Interview session
        current_difficulty: Current difficulty level
        resume_skills: Skills from resume (optional)
        missing_chapters: Chapters with missing knowledge (optional)
        next_direction_hints: LLM 评估的下一题方向建议（可选）
    
    Returns:
        Selected question or None
    """
    # Get track chapter weights
    track_chapters = settings.track_chapters.get(session.track, {})
    
    asked_chapters = _get_asked_chapters(db, session.id)

    # 将 next_direction 匹配到的章节加入 missing_chapters 作为选题提示
    if next_direction_hints:
        hint_chapters = []
        for hint in next_direction_hints:
            if not hint or not hint.strip():
                continue
            for ch in track_chapters.keys():
                if _partial_ratio(hint.strip(), ch) > 60:
                    hint_chapters.append(ch)
                    break
        if hint_chapters:
            missing_chapters = list(missing_chapters or []) + hint_chapters

    # Build LLM context for topic planning (pass to _select_chapter)
    llm_ctx = None
    if settings.zhipuai_api_key:
        ch_scores = {}
        asked_qs = db.query(AskedQuestion).filter(AskedQuestion.session_id == session.id).all()
        for aq in asked_qs:
            if aq.evaluation and aq.topic:
                ch_scores.setdefault(aq.topic, []).append(float(aq.evaluation.overall_score))
        ch_avg = {ch: sum(sc) / len(sc) for ch, sc in ch_scores.items()}
        all_scores = [float(aq.evaluation.overall_score) for aq in asked_qs if aq.evaluation]
        llm_ctx = {
            "track": session.track,
            "chapter_scores": ch_avg,
            "missing_concepts": list(missing_chapters or []),
            "current_difficulty": current_difficulty,
            "avg_score": sum(all_scores) / len(all_scores) if all_scores else 0.5,
        }

    # Determine target chapter through pluggable chapter policy.
    selector = getattr(settings, "selector_strategy", "weighted_random")
    policy = _resolve_chapter_policy(selector)
    selection_ctx = SelectionContext(
        db=db,
        session=session,
        current_difficulty=current_difficulty,
        track_chapters=track_chapters,
        asked_chapters=asked_chapters,
        resume_skills=resume_skills,
        missing_chapters=missing_chapters,
        llm_context=llm_ctx,
    )
    target_chapter = policy.select_chapter(selection_ctx)
    
    # Query questions matching criteria
    query = db.query(QuestionBank).filter(
        and_(
            QuestionBank.difficulty == current_difficulty,
            QuestionBank.chapter.ilike(f"%{target_chapter}%")
        )
    )
    
    # Exclude already asked questions
    asked_qids = {aq.qbank_id for aq in db.query(AskedQuestion.qbank_id)
                  .filter(AskedQuestion.session_id == session.id)
                  .filter(AskedQuestion.qbank_id.isnot(None))
                  .all()}
    
    if asked_qids:
        query = query.filter(~QuestionBank.id.in_(asked_qids))
    
    available_questions = query.all()
    
    # If no exact match, try fuzzy chapter matching
    if not available_questions:
        query = db.query(QuestionBank).filter(
            QuestionBank.difficulty == current_difficulty
        )
        if asked_qids:
            query = query.filter(~QuestionBank.id.in_(asked_qids))
        
        all_questions = query.all()
        
        # Fuzzy match chapters
        matched = []
        for q in all_questions:
            for chapter_key in track_chapters.keys():
                if _partial_ratio(q.chapter, chapter_key) > 70:
                    matched.append(q)
                    break
        
        available_questions = matched if matched else all_questions
    
    # If still no questions, try any difficulty
    if not available_questions:
        query = db.query(QuestionBank)
        if asked_qids:
            query = query.filter(~QuestionBank.id.in_(asked_qids))
        available_questions = query.all()
    
    if not available_questions:
        return None
    
    # 个性化选题策略
    if selector == "personalized" or selector == "max_info":
        return _select_personalized(
            db, session, available_questions, current_difficulty,
            resume_skills, missing_chapters, track_chapters
        )
    
    return random.choice(available_questions)


def _select_chapter(
    track_chapters: Dict[str, float],
    resume_skills: Optional[List[str]],
    missing_chapters: Optional[List[str]],
    asked_chapters: List[str],
    llm_context: Optional[Dict] = None,
) -> str:
    """Select target chapter based on strategy.

    Args:
        llm_context: Optional dict with keys for LLM topic planning:
            track, chapter_scores, missing_concepts, current_difficulty, avg_score
    """
    avoid_k = int(getattr(settings, "recent_chapter_avoid_k", 2))
    recent_avoid = asked_chapters[-avoid_k:] if avoid_k > 0 else []

    # Priority 0 (LLM-as-planner): ask LLM to reason about next topic
    if llm_context and settings.zhipuai_api_key:
        try:
            from backend.services.llm_provider import suggest_next_topic_llm
            suggestion = suggest_next_topic_llm(
                track=llm_context.get("track", ""),
                chapters_covered=asked_chapters,
                chapter_scores=llm_context.get("chapter_scores", {}),
                missing_concepts=llm_context.get("missing_concepts", []),
                resume_skills=resume_skills,
                available_chapters=list(track_chapters.keys()),
                current_difficulty=llm_context.get("current_difficulty", 3),
                avg_score=llm_context.get("avg_score", 0.5),
            )
            if suggestion:
                ch = suggestion["chapter"]
                for key in track_chapters.keys():
                    if _partial_ratio(ch, key) > 70 and key not in recent_avoid:
                        return key
        except Exception:
            pass

    # Priority 1: Missing chapters (weak areas)
    if missing_chapters:
        for missing in missing_chapters:
            for chapter_key in track_chapters.keys():
                if _partial_ratio(missing, chapter_key) > 70:
                    return chapter_key
    
    # Priority 2: Resume skills matching
    if resume_skills:
        for skill in resume_skills:
            for chapter_key in track_chapters.keys():
                if _partial_ratio(skill, chapter_key) > 70:
                    # Avoid recently asked chapters
                    if chapter_key not in recent_avoid:
                        return chapter_key
    
    # Priority 3: Track-based sampling (default: weighted random; optional: Thompson sampling)
    if track_chapters:
        strategy = getattr(settings, "selector_strategy", "weighted_random")
        chapters = list(track_chapters.keys())
        weights = list(track_chapters.values())

        # Avoid recently asked if possible
        available = [c for c in chapters if c not in recent_avoid] or chapters

        if strategy == "thompson_sampling":
            # Thompson sampling over chapters using Beta posterior from historical performance.
            # We interpret "success" as overall_score >= settings.success_threshold.
            alpha0 = float(getattr(settings, "thompson_alpha0", 1.0))
            beta0 = float(getattr(settings, "thompson_beta0", 1.0))
            # NOTE: We don't have db here; Thompson sampling is approximated via weights only.
            # Full posterior is computed in select_question() where db is available.
            # Here we fallback to weighted random if called without db context.
            # (Kept for backward compatibility; real TS is handled in select_question.)
            return random.choices(available, weights=[track_chapters.get(c, 1.0) for c in available], k=1)[0]

        # weighted random fallback
        return random.choices(available, weights=[track_chapters.get(c, 1.0) for c in available], k=1)[0]
    
    # Fallback: random from all
    return "Java基础"


def _build_mastery_profile(db: Session, session_id: int) -> SkillMasteryProfile:
    """从会话评估构建技能掌握度画像"""
    profile = SkillMasteryProfile()
    asked = db.query(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).all()
    for aq in asked:
        if aq.evaluation and aq.topic:
            profile.update(aq.topic, float(aq.evaluation.overall_score))
    return profile


def _get_ability_history(db: Session, session_id: int) -> List[tuple]:
    """获取 (difficulty, score) 历史用于能力估计"""
    history = []
    asked = db.query(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).order_by(AskedQuestion.created_at).all()
    for aq in asked:
        if aq.evaluation:
            history.append((aq.difficulty, float(aq.evaluation.overall_score)))
    return history


def _select_personalized(
    db: Session,
    session: InterviewSession,
    available_questions: List[QuestionBank],
    current_difficulty: int,
    resume_skills: Optional[List[str]],
    missing_chapters: Optional[List[str]],
    track_chapters: Dict[str, float],
) -> Optional[QuestionBank]:
    """
    个性化选题：能力估计 + 最大信息 + 掌握度/UCB。
    参考：IRT Fisher Information, EDGE, UCB
    """
    history = _get_ability_history(db, session.id)
    ability = estimate_ability(history, default=float(session.level))
    
    mastery = _build_mastery_profile(db, session.id)
    
    chapter_successes = {}
    chapter_failures = {}
    asked = db.query(AskedQuestion).filter(AskedQuestion.session_id == session.id).all()
    thr = float(getattr(settings, "success_threshold", 0.70))
    for aq in asked:
        if not aq.topic:
            continue
        matched = None
        for ch in (track_chapters or {}).keys():
            if _partial_ratio(aq.topic, ch) > 70:
                matched = ch
                break
        if not matched:
            matched = aq.topic
        if aq.evaluation:
            if float(aq.evaluation.overall_score) >= thr:
                chapter_successes[matched] = chapter_successes.get(matched, 0) + 1
            else:
                chapter_failures[matched] = chapter_failures.get(matched, 0) + 1
    
    total_trials = sum(chapter_successes.values()) + sum(chapter_failures.values())
    
    # 为每道题计算综合得分：信息量 * 章节个性化
    scored = []
    for q in available_questions:
        info = _fisher_info_simple(ability, q.difficulty)
        ch = q.chapter or "unknown"
        ucb = ucb_chapter_score(ch, chapter_successes, chapter_failures, total_trials)
        pers = compute_personalization_weights(
            ch, resume_skills, missing_chapters, mastery, track_chapters
        )
        score = info * (0.5 + 0.5 * min(ucb, 2.0)) * pers
        scored.append((q, score))
    
    exploration = float(getattr(settings, "personalized_exploration_rate", 0.15))
    if random.random() < exploration:
        return random.choice(available_questions)
    
    scored.sort(key=lambda x: x[1], reverse=True)
    top = [s[0] for s in scored[:5]]
    return random.choice(top) if top else available_questions[0]


def _fisher_info_simple(ability: float, difficulty: int) -> float:
    """简化 Fisher 信息：难度越接近能力，信息越大"""
    diff = abs(ability - difficulty)
    return 1.0 / (1.0 + diff * 0.5)


def _get_asked_chapters(db: Session, session_id: int) -> List[str]:
    """Get list of chapters already asked in this session."""
    asked = db.query(AskedQuestion.topic).filter(
        AskedQuestion.session_id == session_id
    ).all()
    return [a[0] for a in asked]


def _select_chapter_thompson(
    db: Session,
    session: InterviewSession,
    track_chapters: Dict[str, float],
    asked_chapters: List[str],
    current_difficulty: Optional[int] = None
) -> Optional[str]:
    """Thompson sampling for chapter choice using session history (Beta-Bernoulli).

    Context option (settings.thompson_context):
    - "chapter": aggregate all past outcomes per chapter
    - "chapter_difficulty": aggregate only outcomes at the same difficulty as current_difficulty
      (a simple contextual bandit approximation)
    """
    if not track_chapters:
        return None
    avoid_k = int(getattr(settings, "recent_chapter_avoid_k", 2))
    recent_avoid = asked_chapters[-avoid_k:] if avoid_k > 0 else []
    candidates = [c for c in track_chapters.keys() if c not in recent_avoid] or list(track_chapters.keys())

    alpha0 = float(getattr(settings, "thompson_alpha0", 1.0))
    beta0 = float(getattr(settings, "thompson_beta0", 1.0))
    thr = float(getattr(settings, "success_threshold", 0.70))
    ctx = getattr(settings, "thompson_context", "chapter_difficulty")

    # Collect per-chapter successes/failures from existing evaluations in this session
    # success := overall_score >= thr
    asked = db.query(AskedQuestion).filter(AskedQuestion.session_id == session.id).all()
    per = {c: {"s": 0, "f": 0} for c in track_chapters.keys()}
    for aq in asked:
        if ctx == "chapter_difficulty" and current_difficulty is not None:
            if aq.difficulty != int(current_difficulty):
                continue
        chap = aq.topic or ""
        # match to known chapters using fuzzy mapping
        matched = None
        for key in track_chapters.keys():
            if _partial_ratio(chap, key) > 70:
                matched = key
                break
        if not matched or not aq.evaluation:
            continue
        if float(aq.evaluation.overall_score) >= thr:
            per[matched]["s"] += 1
        else:
            per[matched]["f"] += 1

    # Sample theta_c ~ Beta(alpha0+s, beta0+f) and pick max; bias by track weight as prior scaling
    best_c = None
    best_val = -1.0
    for c in candidates:
        s = per.get(c, {}).get("s", 0)
        f = per.get(c, {}).get("f", 0)
        a = alpha0 + s
        b = beta0 + f
        # Python's random.betavariate
        theta = random.betavariate(a, b)
        val = theta * float(track_chapters.get(c, 1.0))
        if val > best_val:
            best_val = val
            best_c = c
    return best_c


def adjust_difficulty(
    db: Session,
    session_id: int,
    current_difficulty: int,
    min_difficulty: int = 1,
    max_difficulty: int = 5
) -> int:
    """
    Adjust difficulty based on recent evaluation scores.
    This is a legacy function - new code should use AdaptiveInterviewEngine.calculate_adaptive_difficulty()
    
    Returns:
        New difficulty level
    """
    # Get last evaluation
    last_asked = db.query(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).order_by(AskedQuestion.created_at.desc()).first()
    
    if not last_asked or not last_asked.evaluation:
        return current_difficulty
    
    overall_score = last_asked.evaluation.overall_score
    
    if overall_score >= 0.8:
        # Increase difficulty
        new_difficulty = min(current_difficulty + 1, max_difficulty)
    elif overall_score <= 0.5:
        # Decrease difficulty
        new_difficulty = max(current_difficulty - 1, min_difficulty)
    else:
        # Maintain
        new_difficulty = current_difficulty
    
    return new_difficulty

