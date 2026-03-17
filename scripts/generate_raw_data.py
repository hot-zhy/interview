#!/usr/bin/env python3
"""
Generate synthetic raw data (participants, sessions, asked_questions, evaluations, turns, question_bank).

Creates a self-contained dataset for reproduction pipeline without database.

Usage:
  python scripts/generate_raw_data.py [--output data/] [--seed 42] [--n-sessions 60] [--n-participants 15]
"""

import argparse
import csv
import json
import random
from pathlib import Path

TRACKS = ["Java Backend", "Java Concurrency", "JVM & Performance", "Spring & Microservices"]
CHAPTERS = [
    "String", "基本语法", "基本数据类型", "变量", "方法", "面向对象基础",
    "Object", "异常", "泛型", "反射", "注解", "SPI", "I/O", "序列化和反序列化",
    "集合", "并发", "JVM", "Spring", "数据库", "系统设计", "基础概念与常识",
]
PRIORITIES = ["P1", "P2", "P3"]
PROVENANCE = ["rule", "llm", "hybrid"]
TERMINATION = ["completed", "active", "completed", "completed"]  # bias to completed


def _sample(lst, k=1):
    return random.sample(lst, min(k, len(lst)))


def generate_question_bank(seed: int, n_questions: int = 80) -> list[dict]:
    """Generate question bank with id, difficulty, chapter."""
    random.seed(seed)
    rows = []
    qid = 1
    for ch in CHAPTERS:
        n = max(1, n_questions // len(CHAPTERS))
        for _ in range(n):
            diff = random.choices([1, 2, 3, 4, 5], weights=[0.1, 0.2, 0.4, 0.2, 0.1])[0]
            rows.append({"question_id": qid, "difficulty": diff, "chapter": ch, "track": ""})
            qid += 1
            if qid > n_questions:
                break
        if qid > n_questions:
            break
    return rows


def generate_participants(seed: int, n: int = 15) -> list[dict]:
    random.seed(seed)
    rows = []
    for i in range(1, n + 1):
        rows.append({
            "participant_id": i,
            "resume_available": random.choice([0, 1]),
            "experience_level": random.choice(["junior", "mid", "senior", ""]),
            "education_level": random.choice(["bachelor", "master", ""]),
            "primary_language": random.choice(["zh", "en", ""]),
        })
    return rows


def generate_sessions(seed: int, n_participants: int, n_sessions: int = 60) -> list[dict]:
    random.seed(seed)
    rows = []
    for i in range(1, n_sessions + 1):
        pid = random.randint(1, n_participants)
        track = random.choice(TRACKS)
        nq = random.choices([3, 4, 5, 6, 7, 8], weights=[0.1, 0.2, 0.3, 0.2, 0.15, 0.05])[0]
        init_diff = random.randint(2, 4)
        term = random.choice(TERMINATION)
        dur = random.gauss(25, 8) if term == "completed" else None
        dur = max(5, min(45, round(dur, 1))) if dur else ""
        rows.append({
            "session_id": i,
            "participant_id": pid,
            "track": track,
            "duration_min": dur,
            "n_questions": nq,
            "initial_difficulty": init_diff,
            "termination_reason": term,
            "termination_rounds": nq,
        })
    return rows


def generate_asked_questions(
    seed: int, sessions: list[dict], question_bank: list[dict]
) -> tuple[list[dict], dict]:
    """Generate asked_questions. Returns (rows, session_id -> list of (round, qid, difficulty, chapter))."""
    random.seed(seed)
    qb_by_chapter = {}
    for q in question_bank:
        ch = q["chapter"]
        qb_by_chapter.setdefault(ch, []).append(q)
    qb_all = question_bank

    rows = []
    session_asked = {}  # session_id -> [(round, qid, diff, ch), ...]
    aq_id = 1
    for s in sessions:
        sid = s["session_id"]
        nq = s["n_questions"]
        diff = s["initial_difficulty"]
        asked = []
        for r in range(1, nq + 1):
            # Adaptive: adjust difficulty based on round
            if r > 1 and random.random() < 0.4:
                diff = max(1, min(5, diff + random.choice([-1, 0, 1])))
            ch = random.choice(CHAPTERS)
            pool = qb_by_chapter.get(ch, qb_all)
            q = random.choice(pool)
            priority = random.choice(PRIORITIES)
            rows.append({
                "session_id": sid,
                "round": r,
                "question_id": q["question_id"],
                "difficulty": diff,
                "chapter": q["chapter"],
                "priority_used": priority,
            })
            asked.append((r, q["question_id"], diff, q["chapter"]))
            aq_id += 1
        session_asked[sid] = asked
    return rows, session_asked


def generate_evaluations(
    seed: int, asked_rows: list[dict], session_asked: dict
) -> list[dict]:
    random.seed(seed)
    rows = []
    aq_id = 1
    for row in asked_rows:
        sid = row["session_id"]
        rnd = row["round"]
        qid = row["question_id"]
        diff = row["difficulty"]
        # Score inversely related to difficulty, plus noise
        base = 0.8 - 0.15 * diff + random.gauss(0, 0.1)
        base = max(0.05, min(0.95, base))
        c = round(base * random.uniform(0.8, 1.0), 3)
        d = round(base * 0.5 * random.uniform(0.5, 1.0), 3)
        cl = round(0.4 + random.uniform(0, 0.4), 2)
        p = round(0.3 + random.uniform(0, 0.4), 2)
        t = round(0.2 + random.uniform(0, 0.3), 2)
        overall = round(0.2 * c + 0.2 * d + 0.2 * cl + 0.2 * p + 0.2 * t + random.gauss(0, 0.05), 4)
        overall = max(0.1, min(0.95, overall))
        missing = [f"要点{i+1}" for i in range(random.randint(0, 3))]
        rows.append({
            "session_id": sid,
            "round": rnd,
            "question_id": qid,
            "asked_question_id": aq_id,
            "correctness": c,
            "depth": d,
            "clarity": cl,
            "practicality": p,
            "tradeoffs": t,
            "overall_score": overall,
            "provenance": random.choices(PROVENANCE, weights=[0.75, 0.15, 0.1])[0],
            "missing_points": json.dumps(missing, ensure_ascii=False),
        })
        aq_id += 1
    return rows


def generate_turns(seed: int, sessions: list[dict], asked_rows: list[dict]) -> list[dict]:
    random.seed(seed)
    rows = []
    tid = 1
    by_session = {}
    for a in asked_rows:
        by_session.setdefault(a["session_id"], []).append(a)
    for s in sessions:
        sid = s["session_id"]
        asked = by_session.get(sid, [])
        for a in asked:
            rnd, qid, _, ch = a["round"], a["question_id"], a["difficulty"], a["chapter"]
            rows.append({
                "id": tid,
                "session_id": sid,
                "role": "interviewer",
                "content": f"第{rnd}题（{ch}）：请简述相关知识点。",
            })
            tid += 1
            rows.append({
                "id": tid,
                "session_id": sid,
                "role": "candidate",
                "content": "（已提交语音回答）",
            })
            tid += 1
    return rows


def generate_resumes(seed: int, participants: list[dict]) -> list[dict]:
    random.seed(seed)
    rows = []
    for p in participants:
        if p.get("resume_available", 0) == 1:
            rows.append({
                "resume_id": p["participant_id"],
                "user_id": p["participant_id"],
                "filename": f"resume_{p['participant_id']}.pdf",
                "has_parsed_json": 1,
            })
    return rows


def save_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="data", help="Output directory")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-sessions", type=int, default=60)
    parser.add_argument("--n-participants", type=int, default=15)
    parser.add_argument("--n-questions", type=int, default=80)
    args = parser.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate
    qbank = generate_question_bank(args.seed, args.n_questions)
    participants = generate_participants(args.seed, args.n_participants)
    sessions = generate_sessions(args.seed, args.n_participants, args.n_sessions)
    asked_rows, session_asked = generate_asked_questions(args.seed, sessions, qbank)
    evaluations = generate_evaluations(args.seed, asked_rows, session_asked)
    turns = generate_turns(args.seed, sessions, asked_rows)
    resumes = generate_resumes(args.seed, participants)

    # Save
    save_csv(out_dir / "question_bank.csv", qbank, ["question_id", "difficulty", "chapter", "track"])
    save_csv(out_dir / "participants.csv", participants, ["participant_id", "resume_available", "experience_level", "education_level", "primary_language"])
    save_csv(out_dir / "sessions.csv", sessions, ["session_id", "participant_id", "track", "duration_min", "n_questions", "initial_difficulty", "termination_reason", "termination_rounds"])
    save_csv(out_dir / "asked_questions.csv", asked_rows, ["session_id", "round", "question_id", "difficulty", "chapter", "priority_used"])
    save_csv(out_dir / "evaluations.csv", evaluations, ["session_id", "round", "question_id", "asked_question_id", "correctness", "depth", "clarity", "practicality", "tradeoffs", "overall_score", "provenance", "missing_points"])
    save_csv(out_dir / "turns.csv", turns, ["id", "session_id", "role", "content"])
    if resumes:
        save_csv(out_dir / "resumes.csv", resumes, ["resume_id", "user_id", "filename", "has_parsed_json"])

    print("Generated raw data:")
    print(f"  participants.csv: {len(participants)} rows")
    print(f"  sessions.csv: {len(sessions)} rows")
    print(f"  question_bank.csv: {len(qbank)} rows")
    print(f"  asked_questions.csv: {len(asked_rows)} rows")
    print(f"  evaluations.csv: {len(evaluations)} rows")
    print(f"  turns.csv: {len(turns)} rows")
    print(f"  resumes.csv: {len(resumes)} rows")
    print(f"\nOutput: {out_dir.absolute()}")
    print("\nNext: python scripts/generate_synthetic_data.py --output", args.output, "--seed", args.seed)


if __name__ == "__main__":
    main()
