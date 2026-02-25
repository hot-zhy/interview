"""Question selector service with adaptive strategy."""
import random
import math
from typing import List, Optional, Dict
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.db.models import QuestionBank, InterviewSession, AskedQuestion, Evaluation
from backend.core.config import settings

try:
    from rapidfuzz import fuzz as _rf_fuzz  # type: ignore
except Exception:  # pragma: no cover
    _rf_fuzz = None


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


def select_question(
    db: Session,
    session: InterviewSession,
    current_difficulty: int,
    resume_skills: Optional[List[str]] = None,
    missing_chapters: Optional[List[str]] = None
) -> Optional[QuestionBank]:
    """
    Select next question based on adaptive strategy.
    
    Args:
        db: Database session
        session: Interview session
        current_difficulty: Current difficulty level
        resume_skills: Skills from resume (optional)
        missing_chapters: Chapters with missing knowledge (optional)
    
    Returns:
        Selected question or None
    """
    # Get track chapter weights
    track_chapters = settings.track_chapters.get(session.track, {})
    
    asked_chapters = _get_asked_chapters(db, session.id)

    # Determine target chapter
    # If selector_strategy == thompson_sampling, use Thompson sampling for the "track-based" fallback,
    # while still honoring priority-1/2 rules (missing chapters, resume skills).
    if getattr(settings, "selector_strategy", "weighted_random") == "thompson_sampling":
        target_chapter = _select_chapter(
            track_chapters=track_chapters,
            resume_skills=resume_skills,
            missing_chapters=missing_chapters,
            asked_chapters=asked_chapters
        )
        # If priority-1/2 did not trigger (i.e., returns fallback default), override with TS.
        # Heuristic: if returned chapter is not in track_chapters, force TS. If it is, still allow TS
        # when we have enough history to sample.
        ts_chapter = _select_chapter_thompson(
            db=db,
            session=session,
            track_chapters=track_chapters,
            asked_chapters=asked_chapters,
            current_difficulty=current_difficulty
        )
        if ts_chapter:
            # Only override when we are in fallback mode (no missing/resume match).
            if not missing_chapters and not resume_skills:
                target_chapter = ts_chapter
    else:
        target_chapter = _select_chapter(
            track_chapters=track_chapters,
            resume_skills=resume_skills,
            missing_chapters=missing_chapters,
            asked_chapters=asked_chapters
        )
    
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
    
    # Random selection (could be weighted by chapter weights in future)
    return random.choice(available_questions)


def _select_chapter(
    track_chapters: Dict[str, float],
    resume_skills: Optional[List[str]],
    missing_chapters: Optional[List[str]],
    asked_chapters: List[str]
) -> str:
    """Select target chapter based on strategy."""
    avoid_k = int(getattr(settings, "recent_chapter_avoid_k", 2))
    recent_avoid = asked_chapters[-avoid_k:] if avoid_k > 0 else []

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

