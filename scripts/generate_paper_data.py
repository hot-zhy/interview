"""Generate richer synthetic interview data for paper analysis."""
import argparse
import csv
import hashlib
import math
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.db.base import SessionLocal  # noqa: E402
from backend.db.models import (  # noqa: E402
    AskedQuestion,
    Evaluation,
    InterviewSession,
    InterviewTurn,
    QuestionBank,
    Report,
    Resume,
    User,
)


TRACKS = [
    "Java Backend",
    "Java Concurrency",
    "JVM & Performance",
    "Spring & Microservices",
]

CHAPTERS_BY_TRACK = {
    "Java Backend": ["Java Basics", "Collections", "Concurrency", "JVM", "Spring", "Database", "System Design"],
    "Java Concurrency": ["Concurrency", "Threading", "Locks", "Thread Pool", "Memory Model"],
    "JVM & Performance": ["JVM", "GC", "Memory", "Performance", "Profiling"],
    "Spring & Microservices": ["Spring", "Microservices", "Database", "Caching", "System Design"],
}

QUESTION_SCENARIOS = [
    "high-traffic promotion event",
    "cross-region deployment with strict latency SLA",
    "legacy monolith migration phase",
    "sudden dependency failure and rollback",
    "cost optimization under rapid business growth",
]

PERSONAS = [
    {
        "name": "junior_practical",
        "weight": 0.28,
        "exp_range": (1, 3),
        "communication": 0.58,
        "stability": 0.52,
        "dropout_rate": 0.16,
        "preferred_tracks": ["Java Backend", "Spring & Microservices"],
    },
    {
        "name": "mid_balanced",
        "weight": 0.34,
        "exp_range": (3, 6),
        "communication": 0.70,
        "stability": 0.67,
        "dropout_rate": 0.09,
        "preferred_tracks": ["Java Backend", "Java Concurrency", "Spring & Microservices"],
    },
    {
        "name": "senior_architect",
        "weight": 0.24,
        "exp_range": (6, 10),
        "communication": 0.80,
        "stability": 0.78,
        "dropout_rate": 0.05,
        "preferred_tracks": ["JVM & Performance", "Spring & Microservices", "Java Backend"],
    },
    {
        "name": "theory_strong_comm_weak",
        "weight": 0.14,
        "exp_range": (2, 8),
        "communication": 0.48,
        "stability": 0.60,
        "dropout_rate": 0.12,
        "preferred_tracks": ["Java Concurrency", "JVM & Performance"],
    },
]

ARM_CONFIGS = {
    "control": {
        "base_bias": 0.00,
        "round_gain": 0.010,
        "difficulty_adapt": 0.20,
        "fatigue_penalty": 0.014,
    },
    "treatment": {
        "base_bias": 0.04,
        "round_gain": 0.024,
        "difficulty_adapt": 0.32,
        "fatigue_penalty": 0.009,
    },
}

MISSING_POINT_POOL = [
    "edge case handling",
    "failure mode analysis",
    "capacity estimation",
    "monitoring and alerting",
    "transaction consistency detail",
    "rollback and canary strategy",
]


def _clamp(value, low, high):
    return max(low, min(high, value))


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _weighted_pick(items, weight_key, rng):
    total = sum(item[weight_key] for item in items)
    pivot = rng.uniform(0, total)
    cur = 0.0
    for item in items:
        cur += item[weight_key]
        if cur >= pivot:
            return item
    return items[-1]


def _ensure_question_bank(db, per_track: int, rng: random.Random) -> int:
    """Create synthetic question bank records if missing."""
    created = 0
    existing_ids = {row.id for row in db.query(QuestionBank.id).all()}
    idx = len(existing_ids) + 1

    for track in TRACKS:
        chapters = CHAPTERS_BY_TRACK[track]
        for _ in range(per_track):
            chapter = rng.choice(chapters)
            difficulty = rng.randint(1, 5)
            qid = f"PAPER_Q_{idx:04d}"
            idx += 1
            if qid in existing_ids:
                continue
            scenario = rng.choice(QUESTION_SCENARIOS)
            question = (
                f"[{track}] In a {scenario}, design a {chapter} solution at difficulty {difficulty}. "
                "Discuss architecture choice, trade-offs, observability, and incident response."
            )
            answer = (
                "Strong answer should include assumptions, architecture decomposition, consistency/performance "
                "trade-offs, risk mitigation, and measurable verification plan."
            )
            db.add(
                QuestionBank(
                    id=qid,
                    question=question,
                    correct_answer=answer,
                    difficulty=difficulty,
                    chapter=chapter,
                )
            )
            created += 1
    return created


def _cleanup_previous_synthetic_data(db):
    users_to_delete = db.query(User).filter(User.email.like("paper_%@example.com")).all()
    for user in users_to_delete:
        db.delete(user)

    qbank_to_delete = db.query(QuestionBank).filter(QuestionBank.id.like("PAPER_Q_%")).all()
    for q in qbank_to_delete:
        db.delete(q)


def _pick_questions_for_track(db, track):
    chapters = CHAPTERS_BY_TRACK[track]
    return db.query(QuestionBank).filter(QuestionBank.chapter.in_(chapters)).all()


def _select_persona(rng):
    return _weighted_pick(PERSONAS, "weight", rng)


def _select_track(rng, persona):
    if rng.random() < 0.78:
        return rng.choice(persona["preferred_tracks"])
    return rng.choice(TRACKS)


def _build_candidate_answer(persona_name, chapter, overall, round_idx, rng):
    style = {
        "junior_practical": "I would start from implementation details and then refine for production risks.",
        "mid_balanced": "I would split this by architecture, data consistency, and operational safeguards.",
        "senior_architect": "I would first define SLO and failure boundaries, then decide architecture by constraints.",
        "theory_strong_comm_weak": "I know the core concept and formulas, but I may explain in a fragmented way.",
    }[persona_name]
    filler = rng.choice(["", " To be honest,", " In my previous project,"])
    confidence = round(overall, 2)
    return (
        f"{filler} For {chapter}, {style} "
        f"My confidence this round is around {confidence}, and I would validate with load test and monitoring data."
    ).strip()


def _missing_points_from_score(score, rng):
    if score >= 0.82:
        return [rng.choice(["extreme load testing detail", "cost forecast granularity"])]
    if score >= 0.68:
        return rng.sample(MISSING_POINT_POOL, 2)
    return rng.sample(MISSING_POINT_POOL, 3)


def _derive_feedback(score, missing_points):
    if score >= 0.82:
        level = "Strong answer quality with clear structure and practical grounding."
    elif score >= 0.68:
        level = "Good baseline answer with room for deeper system-level reasoning."
    else:
        level = "Partial answer; key design and validation elements are still missing."
    return f"{level} Focus next on: {', '.join(missing_points)}."


def _session_status(planned_rounds, actual_rounds, avg_score):
    if actual_rounds < planned_rounds:
        if actual_rounds <= max(2, int(planned_rounds * 0.6)):
            return "cancelled"
        return "completed" if avg_score >= 0.62 else "cancelled"
    return "completed"


def _sample_score_components(overall, communication, years_exp, rng):
    exp_bonus = _clamp((years_exp - 4) * 0.015, -0.04, 0.09)
    correctness = _clamp(overall + rng.uniform(-0.05, 0.04), 0.22, 0.99)
    depth = _clamp(overall - 0.03 + exp_bonus + rng.uniform(-0.06, 0.05), 0.2, 0.99)
    clarity = _clamp(overall - 0.05 + (communication - 0.6) * 0.35 + rng.uniform(-0.05, 0.05), 0.18, 0.99)
    practicality = _clamp(overall - 0.02 + exp_bonus + rng.uniform(-0.05, 0.05), 0.18, 0.99)
    tradeoffs = _clamp((depth + practicality) / 2 + rng.uniform(-0.05, 0.05), 0.18, 0.99)
    return {
        "correctness": round(correctness, 3),
        "depth": round(depth, 3),
        "clarity": round(clarity, 3),
        "practicality": round(practicality, 3),
        "tradeoffs": round(tradeoffs, 3),
    }


def _sample_overall_score(rng, arm, base_skill, question_difficulty, round_idx, stability, fatigue_anchor):
    cfg = ARM_CONFIGS[arm]
    difficulty_gap = (question_difficulty - 3) * 0.085
    learning_curve = cfg["round_gain"] * (1 - math.exp(-0.42 * round_idx)) * 5.0
    fatigue = cfg["fatigue_penalty"] * max(0, round_idx - fatigue_anchor)
    noise = rng.uniform(-0.08, 0.08) * (1.18 - stability)
    return _clamp(base_skill - difficulty_gap + learning_curve - fatigue + noise, 0.18, 0.98)


def _pick_question_for_round(track_questions, target_difficulty, recent_ids, rng):
    candidates = [q for q in track_questions if abs(q.difficulty - target_difficulty) <= 1 and q.id not in recent_ids]
    if not candidates:
        candidates = [q for q in track_questions if q.id not in recent_ids] or track_questions
    return rng.choice(candidates)


def generate_data(
    seed: int,
    users: int,
    sessions_per_user: int,
    rounds: int,
    qbank_per_track: int,
    preset: str,
    clean_paper_data: bool,
    arm_csv_path: str,
):
    rng = random.Random(seed)
    db = SessionLocal()
    try:
        if clean_paper_data:
            _cleanup_previous_synthetic_data(db)
            db.flush()

        qbank_created = _ensure_question_bank(db, qbank_per_track, rng)
        db.flush()

        users_created = 0
        resumes_created = 0
        sessions_created = 0
        asked_created = 0
        evals_created = 0
        turns_created = 0
        reports_created = 0
        arm_rows = []

        base_now = datetime.now(timezone.utc)
        pwd_hash = _hash_password("paper_demo_password")

        for i in range(users):
            arm = "control"
            if preset == "ab_study":
                arm = "control" if i < users // 2 else "treatment"

            persona = _select_persona(rng)
            years_exp = rng.randint(persona["exp_range"][0], persona["exp_range"][1])
            communication = _clamp(persona["communication"] + rng.uniform(-0.06, 0.06), 0.32, 0.94)
            stability = _clamp(persona["stability"] + rng.uniform(-0.08, 0.08), 0.28, 0.95)

            email = f"paper_{arm}_{seed}_{i+1:03d}@example.com"
            user = db.query(User).filter(User.email == email).first()
            if user is None:
                user = User(email=email, password_hash=pwd_hash)
                db.add(user)
                db.flush()
                users_created += 1

            resume = Resume(
                user_id=user.id,
                filename=f"resume_{user.id}.pdf",
                raw_text=(
                    f"Candidate profile: {persona['name']}, {years_exp} years backend experience. "
                    "Worked on Java, SQL, cache tuning, and service reliability improvements."
                ),
                parsed_json={
                    "years_experience": years_exp,
                    "education": rng.choice(["Bachelor", "Master"]),
                    "skills": ["Java", "Spring", "SQL", "System Design", "Observability"],
                    "communication": round(communication, 3),
                    "stability": round(stability, 3),
                    "persona": persona["name"],
                    "experiment_arm": arm,
                },
            )
            db.add(resume)
            db.flush()
            resumes_created += 1

            arm_cfg = ARM_CONFIGS[arm]
            base_skill = _clamp(
                0.45 + years_exp * 0.035 + (communication - 0.6) * 0.12 + arm_cfg["base_bias"] + rng.uniform(-0.08, 0.08),
                0.28,
                0.92,
            )

            for _ in range(sessions_per_user):
                track = _select_track(rng, persona)
                planned_rounds = max(5, rounds + rng.randint(-2, 2))
                dropout = rng.random() < persona["dropout_rate"] * (1.1 if arm == "control" else 0.8)
                actual_rounds = planned_rounds if not dropout else rng.randint(2, planned_rounds - 1)
                fatigue_anchor = rng.randint(5, 7)

                started_at = base_now - timedelta(days=rng.randint(3, 75), minutes=rng.randint(0, 240))
                session_duration = rng.randint(22, 48) + actual_rounds * rng.randint(2, 4)
                ended_at = started_at + timedelta(minutes=session_duration)

                initial_level = _clamp(int(round(base_skill * 4.5)), 1, 5)
                session = InterviewSession(
                    user_id=user.id,
                    resume_id=resume.id,
                    track=track,
                    level=initial_level,
                    status="active",
                    total_rounds=planned_rounds,
                    current_round=0,
                    started_at=started_at,
                    ended_at=ended_at,
                    expression_history_json=[],
                )
                db.add(session)
                db.flush()
                sessions_created += 1

                track_questions = _pick_questions_for_track(db, track) or db.query(QuestionBank).all()
                recent_qids = []
                target_difficulty = _clamp(initial_level, 1, 5)
                overall_scores = []
                expression_series = []

                for round_idx in range(1, actual_rounds + 1):
                    question = _pick_question_for_round(track_questions, target_difficulty, recent_qids, rng)
                    recent_qids = (recent_qids + [question.id])[-3:]

                    overall = _sample_overall_score(
                        rng=rng,
                        arm=arm,
                        base_skill=base_skill,
                        question_difficulty=question.difficulty,
                        round_idx=round_idx,
                        stability=stability,
                        fatigue_anchor=fatigue_anchor,
                    )
                    metrics = _sample_score_components(overall, communication, years_exp, rng)
                    weighted_overall = (
                        metrics["correctness"] * 0.30
                        + metrics["depth"] * 0.23
                        + metrics["clarity"] * 0.17
                        + metrics["practicality"] * 0.17
                        + metrics["tradeoffs"] * 0.13
                    )
                    weighted_overall = _clamp(weighted_overall + rng.uniform(-0.03, 0.02), 0.18, 0.98)
                    overall_scores.append(weighted_overall)

                    # Adaptive next difficulty resembles realistic interview control.
                    if weighted_overall > 0.78:
                        target_difficulty = _clamp(target_difficulty + arm_cfg["difficulty_adapt"], 1, 5)
                    elif weighted_overall < 0.56:
                        target_difficulty = _clamp(target_difficulty - arm_cfg["difficulty_adapt"], 1, 5)
                    else:
                        target_difficulty = _clamp(target_difficulty + rng.uniform(-0.2, 0.2), 1, 5)

                    interviewer_prompt = (
                        f"Round {round_idx}/{planned_rounds}. "
                        f"Please explain your design for topic {question.chapter} with concrete trade-offs."
                    )
                    candidate_answer = _build_candidate_answer(
                        persona_name=persona["name"],
                        chapter=question.chapter,
                        overall=weighted_overall,
                        round_idx=round_idx,
                        rng=rng,
                    )

                    db.add(InterviewTurn(session_id=session.id, role="interviewer", content=interviewer_prompt))
                    db.add(InterviewTurn(session_id=session.id, role="candidate", content=candidate_answer))
                    turns_created += 2

                    asked = AskedQuestion(
                        session_id=session.id,
                        qbank_id=question.id,
                        topic=question.chapter,
                        difficulty=question.difficulty,
                        question_text=question.question,
                        correct_answer_text=question.correct_answer,
                    )
                    db.add(asked)
                    db.flush()
                    asked_created += 1

                    missing_points = _missing_points_from_score(weighted_overall, rng)
                    stress = _clamp(0.72 - weighted_overall + rng.uniform(-0.08, 0.08), 0.06, 0.96)
                    engagement = _clamp(
                        0.56 + communication * 0.3 - 0.05 * max(0, round_idx - fatigue_anchor) + rng.uniform(-0.08, 0.08),
                        0.2,
                        0.95,
                    )
                    confidence = _clamp(weighted_overall + rng.uniform(-0.07, 0.06), 0.15, 0.98)

                    speech = {
                        "pace_wpm": int(_clamp(105 + weighted_overall * 75 + rng.randint(-18, 20), 90, 195)),
                        "pause_ratio": round(_clamp(0.09 + stress * 0.18 + rng.uniform(-0.03, 0.03), 0.03, 0.44), 3),
                        "filler_ratio": round(_clamp(0.04 + (1 - communication) * 0.16 + rng.uniform(-0.02, 0.02), 0.01, 0.35), 3),
                        "interruption_count": int(_clamp(rng.gauss(1.2 + stress * 3.5, 1.0), 0, 8)),
                    }
                    expression = {
                        "engagement": round(engagement, 3),
                        "confidence": round(confidence, 3),
                        "stress": round(stress, 3),
                    }
                    expression_series.append({"round": round_idx, **expression})

                    db.add(
                        Evaluation(
                            asked_question_id=asked.id,
                            answer_text=candidate_answer,
                            scores_json=metrics,
                            overall_score=round(weighted_overall, 3),
                            feedback_text=_derive_feedback(weighted_overall, missing_points),
                            missing_points_json=missing_points,
                            next_direction=f"Drill deeper into {question.chapter} with production constraints.",
                            speech_analysis_json=speech,
                            expression_analysis_json=expression,
                        )
                    )
                    evals_created += 1

                avg_score = round(mean(overall_scores), 3) if overall_scores else 0.0
                early_window = overall_scores[: max(1, len(overall_scores) // 2)] or [avg_score]
                late_window = overall_scores[max(1, len(overall_scores) // 2):] or [avg_score]
                improvement = round(mean(late_window) - mean(early_window), 3)
                status = _session_status(planned_rounds, actual_rounds, avg_score)

                session.current_round = actual_rounds
                session.status = status
                session.expression_history_json = expression_series

                strengths = []
                weaknesses = []
                if communication > 0.72:
                    strengths.append("structured communication")
                if years_exp >= 6:
                    strengths.append("practical system trade-off awareness")
                if avg_score > 0.78:
                    strengths.append("stable high-quality technical reasoning")
                if not strengths:
                    strengths.append("solid baseline concept understanding")

                if communication < 0.58:
                    weaknesses.append("answer coherence under pressure")
                if improvement < 0.02:
                    weaknesses.append("limited within-session adaptation speed")
                if avg_score < 0.62:
                    weaknesses.append("insufficient depth on reliability details")
                if not weaknesses:
                    weaknesses.append("can improve quantitative validation detail")

                report_md = (
                    f"# Session Report {session.id}\n\n"
                    f"- Arm: {arm}\n"
                    f"- Persona: {persona['name']}\n"
                    f"- Track: {track}\n"
                    f"- Planned rounds: {planned_rounds}\n"
                    f"- Actual rounds: {actual_rounds}\n"
                    f"- Avg score: {avg_score}\n"
                    f"- Improvement: {improvement}\n"
                    f"- Status: {status}\n\n"
                    "## Strengths\n"
                    + "".join(f"- {item}\n" for item in strengths)
                    + "\n## Improvement Plan\n"
                    + "".join(f"- {item}\n" for item in weaknesses)
                )

                db.add(
                    Report(
                        session_id=session.id,
                        summary_json={
                            "experiment_arm": arm,
                            "persona": persona["name"],
                            "avg_score": avg_score,
                            "improvement": improvement,
                            "planned_rounds": planned_rounds,
                            "actual_rounds": actual_rounds,
                            "status": status,
                            "strengths": strengths,
                            "weaknesses": weaknesses,
                        },
                        markdown=report_md,
                    )
                )
                reports_created += 1

                arm_rows.append(
                    {
                        "user_id": user.id,
                        "session_id": session.id,
                        "arm": arm,
                        "persona": persona["name"],
                        "track": track,
                        "status": status,
                        "planned_rounds": planned_rounds,
                        "actual_rounds": actual_rounds,
                        "avg_score": avg_score,
                        "improvement": improvement,
                    }
                )

        db.commit()

        if arm_csv_path:
            out_path = Path(arm_csv_path)
            if not out_path.is_absolute():
                out_path = Path(__file__).resolve().parent.parent / out_path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "user_id",
                        "session_id",
                        "arm",
                        "persona",
                        "track",
                        "status",
                        "planned_rounds",
                        "actual_rounds",
                        "avg_score",
                        "improvement",
                    ],
                )
                writer.writeheader()
                writer.writerows(arm_rows)

        print("Richer synthetic paper dataset written successfully.")
        print(
            {
                "question_bank_created": qbank_created,
                "users_created": users_created,
                "resumes_created": resumes_created,
                "sessions_created": sessions_created,
                "asked_questions_created": asked_created,
                "evaluations_created": evals_created,
                "turns_created": turns_created,
                "reports_created": reports_created,
                "preset": preset,
                "arm_rows": len(arm_rows),
            }
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Generate richer synthetic data for paper analysis")
    parser.add_argument("--seed", type=int, default=20260325)
    parser.add_argument("--users", type=int, default=36)
    parser.add_argument("--sessions-per-user", type=int, default=3)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--qbank-per-track", type=int, default=30)
    parser.add_argument("--preset", choices=["default", "ab_study"], default="ab_study")
    parser.add_argument("--clean-paper-data", action="store_true")
    parser.add_argument("--arm-csv-path", default="data/paper_arm_metrics.csv")
    args = parser.parse_args()

    generate_data(
        seed=args.seed,
        users=args.users,
        sessions_per_user=args.sessions_per_user,
        rounds=args.rounds,
        qbank_per_track=args.qbank_per_track,
        preset=args.preset,
        clean_paper_data=args.clean_paper_data,
        arm_csv_path=args.arm_csv_path,
    )


if __name__ == "__main__":
    main()
