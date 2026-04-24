"""InterviewMemory manager: load, update, and persist interview memory.

Memory is stored in Streamlit session_state when the agent controller is
active, and optionally serialised to a JSON column for post-hoc analysis.
The manager never modifies existing database tables; it only reads from them
to reconstruct memory when needed.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from backend.db.models import (
    AskedQuestion, Evaluation, InterviewSession, Resume,
)
from backend.agent.models import InterviewMemory


class MemoryManager:
    """Builds and maintains an InterviewMemory instance for a session."""

    @staticmethod
    def build_from_db(db: DBSession, session: InterviewSession) -> InterviewMemory:
        """Reconstruct full memory from the database for a given session.

        This is used on first load or after a page refresh.  It reads existing
        asked-question and evaluation rows without writing anything.
        """
        mem = InterviewMemory(session_id=session.id)

        # Resume prior
        if session.resume_id:
            resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
            if resume and resume.parsed_json:
                mem.resume_skills = resume.parsed_json.get("skills", [])

        asked_qs: List[AskedQuestion] = (
            db.query(AskedQuestion)
            .filter(AskedQuestion.session_id == session.id)
            .order_by(AskedQuestion.created_at)
            .all()
        )

        for aq in asked_qs:
            ev: Optional[Evaluation] = aq.evaluation
            if ev is None:
                continue

            missing = ev.missing_points_json or []
            mem.append_turn(
                score=float(ev.overall_score),
                difficulty=aq.difficulty,
                chapter=aq.topic or "",
                new_missing=missing,
                next_direction=ev.next_direction,
                provenance="reconstructed",
                asked_question_id=str(aq.id),
            )
            scores = ev.scores_json or {}
            mem.turn_evaluations.append({
                "asked_question_id": str(aq.id),
                "overall_score": float(ev.overall_score),
                "policy_meta": scores.get("_agentic_meta", {}),
            })

        return mem

    @staticmethod
    def update_after_evaluation(
        mem: InterviewMemory,
        asked_question_id: str,
        score: float,
        difficulty: int,
        chapter: str,
        missing_points: List[str],
        next_direction: Optional[str],
        provenance: str,
        policy_meta: Optional[Dict] = None,
    ) -> InterviewMemory:
        """Append a new turn's data to memory (in-place mutation + return)."""
        mem.append_turn(
            score=score,
            difficulty=difficulty,
            chapter=chapter,
            new_missing=missing_points,
            next_direction=next_direction,
            provenance=provenance,
            asked_question_id=asked_question_id,
        )
        mem.turn_evaluations.append({
            "asked_question_id": asked_question_id,
            "overall_score": float(score),
            "policy_meta": policy_meta or {},
        })
        return mem

    @staticmethod
    def record_followup(mem: InterviewMemory, asked_question_id: str) -> InterviewMemory:
        mem.record_followup(asked_question_id)
        return mem
