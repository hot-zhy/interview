"""Question selector service with adaptive strategy."""
import random
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.db.models import QuestionBank, InterviewSession, AskedQuestion, Evaluation
from backend.core.config import settings
from rapidfuzz import fuzz


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
    
    # Determine target chapter
    target_chapter = _select_chapter(
        track_chapters=track_chapters,
        resume_skills=resume_skills,
        missing_chapters=missing_chapters,
        asked_chapters=_get_asked_chapters(db, session.id)
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
                if fuzz.partial_ratio(q.chapter.lower(), chapter_key.lower()) > 70:
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
    # Priority 1: Missing chapters (weak areas)
    if missing_chapters:
        for missing in missing_chapters:
            for chapter_key in track_chapters.keys():
                if fuzz.partial_ratio(missing.lower(), chapter_key.lower()) > 70:
                    return chapter_key
    
    # Priority 2: Resume skills matching
    if resume_skills:
        for skill in resume_skills:
            for chapter_key in track_chapters.keys():
                if fuzz.partial_ratio(skill.lower(), chapter_key.lower()) > 70:
                    # Avoid recently asked chapters
                    if chapter_key not in asked_chapters[-2:]:
                        return chapter_key
    
    # Priority 3: Weighted random from track chapters
    if track_chapters:
        chapters = list(track_chapters.keys())
        weights = list(track_chapters.values())
        # Avoid recently asked
        available = [c for c in chapters if c not in asked_chapters[-2:]]
        if available:
            return random.choices(available, k=1)[0]
        return random.choices(chapters, weights=weights, k=1)[0]
    
    # Fallback: random from all
    return "Java基础"


def _get_asked_chapters(db: Session, session_id: int) -> List[str]:
    """Get list of chapters already asked in this session."""
    asked = db.query(AskedQuestion.topic).filter(
        AskedQuestion.session_id == session_id
    ).all()
    return [a[0] for a in asked]


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

