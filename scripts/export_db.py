#!/usr/bin/env python3
"""
Export database tables to CSV for reproduction pipeline.

Usage:
  python scripts/export_db.py [--output data/]

Output files (in --output directory):
  - participants.csv   (from users + resumes)
  - sessions.csv       (from interview_sessions)
  - asked_questions.csv
  - evaluations.csv
  - turns.csv          (from interview_turns, for human eval sampling)
  - question_bank.csv
  - resumes.csv        (raw resume metadata)
  - eval_policy_trajectory.csv

Manual annotation files (see MISSING_DATA.md):
  - ability_labels.csv
  - missing_concepts.csv
  - human_evaluations.csv
  - expert_relevance_ratings.csv
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings
from backend.db.models import (
    User, Resume, QuestionBank, InterviewSession,
    InterviewTurn, AskedQuestion, Evaluation, Report
)


def _safe_str(v):
    if v is None:
        return ""
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def export_participants(session, out_dir: Path):
    """Export users as participants; derive resume_available from resumes."""
    users = session.query(User).all()
    if not users:
        return False
    rows = []
    for u in users:
        has_resume = session.query(Resume).filter(Resume.user_id == u.id).first() is not None
        rows.append({
            "participant_id": u.id,
            "resume_available": 1 if has_resume else 0,
            "experience_level": "",
            "education_level": "",
            "primary_language": "",
        })
    path = out_dir / "participants.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return True


def export_sessions(session, out_dir: Path):
    """Export interview_sessions as sessions.csv."""
    sessions = session.query(InterviewSession).all()
    if not sessions:
        return False
    rows = []
    for s in sessions:
        n_questions = session.query(AskedQuestion).filter(AskedQuestion.session_id == s.id).count()
        duration_min = None
        if s.started_at and s.ended_at:
            delta = s.ended_at - s.started_at
            duration_min = round(delta.total_seconds() / 60, 1)
        rows.append({
            "session_id": s.id,
            "participant_id": s.user_id,
            "track": s.track or "",
            "duration_min": duration_min or "",
            "n_questions": n_questions,
            "initial_difficulty": s.level,
            "termination_reason": s.status or "completed",
            "termination_rounds": s.current_round or s.total_rounds or 0,
        })
    path = out_dir / "sessions.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return True


def export_asked_questions(session, out_dir: Path):
    """Export asked_questions."""
    aqs = session.query(AskedQuestion).order_by(AskedQuestion.session_id, AskedQuestion.created_at).all()
    if not aqs:
        return False
    rows = []
    for i, aq in enumerate(aqs):
        # Derive round from order within session
        prev = session.query(AskedQuestion).filter(
            AskedQuestion.session_id == aq.session_id,
            AskedQuestion.created_at < aq.created_at
        ).count()
        round_num = prev + 1
        rows.append({
            "session_id": aq.session_id,
            "round": round_num,
            "question_id": aq.qbank_id or f"custom_{aq.id}",
            "difficulty": aq.difficulty,
            "chapter": aq.topic or "",
            "priority_used": "",  # Not stored in DB; fill from logs if available
        })
    path = out_dir / "asked_questions.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return True


def export_evaluations(session, out_dir: Path):
    """Export evaluations with scores_json flattened."""
    evals = session.query(Evaluation).all()
    if not evals:
        return False
    rows = []
    for e in evals:
        aq = session.query(AskedQuestion).filter(AskedQuestion.id == e.asked_question_id).first()
        if not aq:
            continue
        round_num = session.query(AskedQuestion).filter(
            AskedQuestion.session_id == aq.session_id,
            AskedQuestion.created_at <= aq.created_at
        ).count()
        scores = e.scores_json or {}
        missing = e.missing_points_json
        missing_str = json.dumps(missing, ensure_ascii=False) if isinstance(missing, (list, dict)) else _safe_str(missing)
        scores_payload = e.scores_json or {}
        policy_meta = scores_payload.get("_agentic_meta", {}) if isinstance(scores_payload, dict) else {}
        rows.append({
            "session_id": aq.session_id,
            "round": round_num,
            "question_id": aq.qbank_id or f"custom_{aq.id}",
            "asked_question_id": e.asked_question_id,
            "correctness": scores.get("correctness", ""),
            "depth": scores.get("depth", ""),
            "clarity": scores.get("clarity", ""),
            "practicality": scores.get("practicality", ""),
            "tradeoffs": scores.get("tradeoffs", ""),
            "overall_score": e.overall_score,
            "provenance": policy_meta.get("action", ""),
            "missing_points": missing_str,
        })
    path = out_dir / "evaluations.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return True


def export_eval_policy_trajectory(session, out_dir: Path):
    """Export state-action-reward trajectories for eval-policy offline training."""
    evals = session.query(Evaluation).all()
    if not evals:
        return False
    rows = []
    for e in evals:
        aq = session.query(AskedQuestion).filter(AskedQuestion.id == e.asked_question_id).first()
        if not aq:
            continue
        scores_payload = e.scores_json if isinstance(e.scores_json, dict) else {}
        policy_meta = scores_payload.get("_agentic_meta", {}) if isinstance(scores_payload, dict) else {}
        state = policy_meta.get("state", {}) if isinstance(policy_meta, dict) else {}
        round_num = session.query(AskedQuestion).filter(
            AskedQuestion.session_id == aq.session_id,
            AskedQuestion.created_at <= aq.created_at
        ).count()
        rows.append({
            "session_id": aq.session_id,
            "round": round_num,
            "asked_question_id": aq.id,
            "action": policy_meta.get("action", ""),
            "reward": policy_meta.get("reward", ""),
            "fallback_reason": policy_meta.get("fallback_reason", ""),
            "answer_length": state.get("answer_length", ""),
            "recent_avg_score": state.get("recent_avg_score", ""),
            "missing_points_count": state.get("missing_points_count", ""),
            "fallback_count": state.get("fallback_count", ""),
            "llm_calls_used": state.get("llm_calls_used", ""),
            "multi_judge_used": state.get("multi_judge_used", ""),
            "overall_score": e.overall_score,
        })
    path = out_dir / "eval_policy_trajectory.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return True


def export_turns(session, out_dir: Path):
    """Export interview_turns for human evaluation sampling."""
    turns = session.query(InterviewTurn).order_by(InterviewTurn.session_id, InterviewTurn.created_at).all()
    if not turns:
        return False
    rows = []
    for t in turns:
        rows.append({
            "id": t.id,
            "session_id": t.session_id,
            "role": t.role,
            "content": t.content[:5000] if t.content else "",  # Truncate very long
        })
    path = out_dir / "turns.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return True


def export_question_bank(session, out_dir: Path):
    """Export question_bank."""
    qb = session.query(QuestionBank).all()
    if not qb:
        return False
    rows = []
    for q in qb:
        rows.append({
            "question_id": q.id,
            "difficulty": q.difficulty,
            "chapter": q.chapter or "",
            "track": "",  # Not in model; may be derived from usage
        })
    path = out_dir / "question_bank.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return True


def export_resumes(session, out_dir: Path):
    """Export resume metadata (user_id, filename); raw_text can be large."""
    resumes = session.query(Resume).all()
    if not resumes:
        return False
    rows = []
    for r in resumes:
        rows.append({
            "resume_id": r.id,
            "user_id": r.user_id,
            "filename": r.filename or "",
            "has_parsed_json": 1 if r.parsed_json else 0,
        })
    path = out_dir / "resumes.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return True


def main():
    parser = argparse.ArgumentParser(description="Export DB tables to CSV for reproduction")
    parser.add_argument("--output", "-o", default="data", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    from backend.db.base import SessionLocal
    session = SessionLocal()
    try:
        exporters = [
            ("participants.csv", export_participants),
            ("sessions.csv", export_sessions),
            ("asked_questions.csv", export_asked_questions),
            ("evaluations.csv", export_evaluations),
            ("eval_policy_trajectory.csv", export_eval_policy_trajectory),
            ("turns.csv", export_turns),
            ("question_bank.csv", export_question_bank),
            ("resumes.csv", export_resumes),
        ]
        for name, fn in exporters:
            ok = fn(session, out_dir)
            print(f"  {name}: {'OK' if ok else 'empty (skipped)'}")
        print(f"\nExported to {out_dir.absolute()}")
        print("Manual annotation files (see MISSING_DATA.md): ability_labels.csv, missing_concepts.csv, human_evaluations.csv, expert_relevance_ratings.csv")
    finally:
        session.close()


if __name__ == "__main__":
    main()
