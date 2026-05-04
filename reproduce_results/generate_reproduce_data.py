#!/usr/bin/env python3
"""Generate a larger deterministic CSV dataset for the reproduction pipeline."""
from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean


TRACKS = {
    "Java Backend": [
        "String",
        "基本语法",
        "基本数据类型",
        "变量",
        "方法",
        "面向对象基础",
        "Object",
        "异常",
        "集合",
        "数据库",
        "系统设计",
    ],
    "Java Concurrency": ["并发", "线程池", "锁", "JMM", "集合", "JVM", "系统设计"],
    "JVM & Performance": ["JVM", "GC", "I/O", "性能调优", "序列化和反序列化", "数据库", "系统设计"],
    "Spring & Microservices": ["Spring", "微服务", "数据库", "缓存", "注解", "SPI", "系统设计"],
}

ALL_CHAPTERS = sorted({chapter for chapters in TRACKS.values() for chapter in chapters})
PRIORITIES = ["P1", "P2", "P3"]
PROVENANCE = ["rule", "llm", "hybrid"]
MISSING_POINT_POOL = [
    "核心概念边界",
    "异常场景处理",
    "性能瓶颈分析",
    "生产环境验证",
    "一致性权衡",
    "监控与回滚方案",
]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_question_bank(rng: random.Random, questions_per_chapter: int) -> list[dict]:
    rows: list[dict] = []
    qid = 1
    for track, chapters in TRACKS.items():
        for chapter in chapters:
            base_difficulty = 2 if chapter in {"String", "变量", "方法", "基本语法"} else 3
            for idx in range(questions_per_chapter):
                difficulty = int(clamp(base_difficulty + rng.choice([-1, 0, 0, 1, 2]), 1, 5))
                rows.append(
                    {
                        "question_id": qid,
                        "difficulty": difficulty,
                        "chapter": chapter,
                        "track": track,
                    }
                )
                qid += 1
    return rows


def pick_question(
    rng: random.Random,
    question_bank: list[dict],
    track: str,
    target_difficulty: float,
    recent_ids: list[int],
) -> dict:
    chapters = set(TRACKS[track])
    candidates = [
        q
        for q in question_bank
        if q["chapter"] in chapters
        and q["question_id"] not in recent_ids
        and abs(int(q["difficulty"]) - target_difficulty) <= 1.25
    ]
    if not candidates:
        candidates = [q for q in question_bank if q["chapter"] in chapters and q["question_id"] not in recent_ids]
    if not candidates:
        candidates = [q for q in question_bank if q["chapter"] in chapters]
    return rng.choice(candidates)


def score_components(
    rng: random.Random,
    ability: float,
    difficulty: int,
    round_idx: int,
    communication: float,
) -> dict:
    difficulty_penalty = (difficulty - 3) * 0.075
    learning = 0.018 * min(round_idx, 6)
    fatigue = 0.018 * max(0, round_idx - 6)
    base = clamp(ability - difficulty_penalty + learning - fatigue + rng.gauss(0, 0.055), 0.12, 0.96)
    correctness = clamp(base + rng.gauss(0, 0.055), 0.05, 0.98)
    depth = clamp(base - 0.025 + rng.gauss(0, 0.06), 0.04, 0.98)
    clarity = clamp(base + (communication - 0.62) * 0.28 + rng.gauss(0, 0.05), 0.04, 0.98)
    practicality = clamp(base + rng.gauss(0, 0.055), 0.04, 0.98)
    tradeoffs = clamp((depth + practicality) / 2 + rng.gauss(0, 0.05), 0.04, 0.98)
    overall = clamp(
        correctness * 0.30 + depth * 0.23 + clarity * 0.17 + practicality * 0.17 + tradeoffs * 0.13,
        0.05,
        0.98,
    )
    return {
        "correctness": round(correctness, 3),
        "depth": round(depth, 3),
        "clarity": round(clarity, 3),
        "practicality": round(practicality, 3),
        "tradeoffs": round(tradeoffs, 3),
        "overall_score": round(overall, 4),
    }


def missing_points_for_score(rng: random.Random, score: float) -> list[str]:
    if score >= 0.78:
        count = rng.choice([0, 1])
    elif score >= 0.58:
        count = rng.choice([1, 2])
    else:
        count = rng.choice([2, 3])
    return rng.sample(MISSING_POINT_POOL, count) if count else []


def generate_dataset(
    output: Path,
    seed: int,
    participants_count: int,
    sessions_per_participant: int,
    min_rounds: int,
    max_rounds: int,
    questions_per_chapter: int,
) -> dict[str, int]:
    rng = random.Random(seed)
    question_bank = build_question_bank(rng, questions_per_chapter)

    participants: list[dict] = []
    resumes: list[dict] = []
    sessions: list[dict] = []
    asked_questions: list[dict] = []
    evaluations: list[dict] = []
    turns: list[dict] = []

    asked_by_session: dict[int, list[dict]] = defaultdict(list)
    evals_by_session: dict[int, list[dict]] = defaultdict(list)
    ability_by_session: dict[int, int] = {}
    participant_ability: dict[int, float] = {}

    session_id = 1
    asked_id = 1
    turn_id = 1

    for participant_id in range(1, participants_count + 1):
        persona = rng.choices(["junior", "mid", "senior"], weights=[0.45, 0.38, 0.17], k=1)[0]
        if persona == "junior":
            ability = clamp(rng.gauss(0.45, 0.10), 0.18, 0.68)
            education = rng.choice(["bachelor", "bachelor", "master", ""])
        elif persona == "mid":
            ability = clamp(rng.gauss(0.62, 0.11), 0.35, 0.82)
            education = rng.choice(["bachelor", "master", "master", ""])
        else:
            ability = clamp(rng.gauss(0.76, 0.10), 0.50, 0.94)
            education = rng.choice(["bachelor", "master", "master"])
        communication = clamp(rng.gauss(0.63 + (ability - 0.55) * 0.25, 0.11), 0.32, 0.92)
        resume_available = 1 if rng.random() < (0.52 + ability * 0.35) else 0
        language = rng.choices(["zh", "en", ""], weights=[0.58, 0.28, 0.14], k=1)[0]
        participant_ability[participant_id] = ability

        participants.append(
            {
                "participant_id": participant_id,
                "resume_available": resume_available,
                "experience_level": persona,
                "education_level": education,
                "primary_language": language,
            }
        )
        if resume_available:
            resumes.append(
                {
                    "resume_id": participant_id,
                    "user_id": participant_id,
                    "filename": f"resume_{participant_id}.pdf",
                    "has_parsed_json": 1,
                }
            )

        preferred_tracks = {
            "junior": ["Java Backend", "Spring & Microservices"],
            "mid": ["Java Backend", "Java Concurrency", "Spring & Microservices"],
            "senior": ["JVM & Performance", "Spring & Microservices", "Java Concurrency"],
        }[persona]

        for _ in range(sessions_per_participant):
            track = rng.choice(preferred_tracks if rng.random() < 0.78 else list(TRACKS))
            planned_rounds = rng.randint(min_rounds, max_rounds)
            dropout_rate = {"junior": 0.13, "mid": 0.08, "senior": 0.05}[persona]
            early_stop = rng.random() < dropout_rate
            n_questions = rng.randint(3, planned_rounds - 1) if early_stop else planned_rounds
            target_difficulty = clamp(round(1 + ability * 4), 1, 5)
            initial_difficulty = int(target_difficulty)
            recent_ids: list[int] = []

            for round_idx in range(1, n_questions + 1):
                question = pick_question(rng, question_bank, track, target_difficulty, recent_ids)
                recent_ids = (recent_ids + [int(question["question_id"])])[-4:]
                metrics = score_components(rng, ability, int(question["difficulty"]), round_idx, communication)
                score = metrics["overall_score"]
                priority = rng.choices(PRIORITIES, weights=[0.48, 0.28, 0.24], k=1)[0]
                provenance = rng.choices(PROVENANCE, weights=[0.72, 0.18, 0.10], k=1)[0]
                missing_points = missing_points_for_score(rng, score)

                asked_row = {
                    "session_id": session_id,
                    "round": round_idx,
                    "question_id": question["question_id"],
                    "difficulty": question["difficulty"],
                    "chapter": question["chapter"],
                    "priority_used": priority,
                }
                asked_questions.append(asked_row)
                asked_by_session[session_id].append(asked_row)

                eval_row = {
                    "session_id": session_id,
                    "round": round_idx,
                    "question_id": question["question_id"],
                    "asked_question_id": asked_id,
                    "correctness": metrics["correctness"],
                    "depth": metrics["depth"],
                    "clarity": metrics["clarity"],
                    "practicality": metrics["practicality"],
                    "tradeoffs": metrics["tradeoffs"],
                    "overall_score": score,
                    "provenance": provenance,
                    "missing_points": json.dumps(missing_points, ensure_ascii=False),
                }
                evaluations.append(eval_row)
                evals_by_session[session_id].append(eval_row)

                turns.append(
                    {
                        "id": turn_id,
                        "session_id": session_id,
                        "role": "interviewer",
                        "content": f"第{round_idx}题（{question['chapter']}）：请结合项目经验说明关键知识点和取舍。",
                    }
                )
                turn_id += 1
                turns.append(
                    {
                        "id": turn_id,
                        "session_id": session_id,
                        "role": "candidate",
                        "content": "（已提交语音回答）",
                    }
                )
                turn_id += 1

                if score > 0.78:
                    target_difficulty = clamp(target_difficulty + 0.35, 1, 5)
                elif score < 0.48:
                    target_difficulty = clamp(target_difficulty - 0.35, 1, 5)
                else:
                    target_difficulty = clamp(target_difficulty + rng.uniform(-0.18, 0.18), 1, 5)
                asked_id += 1

            scores = [float(row["overall_score"]) for row in evals_by_session[session_id]]
            avg_score = mean(scores) if scores else ability
            if early_stop:
                termination_reason = "active" if rng.random() < 0.45 else "early_stop"
                duration_min = "" if termination_reason == "active" else round(8.0 + n_questions * rng.uniform(2.5, 4.2), 1)
            else:
                termination_reason = "completed"
                duration_min = round(10.0 + n_questions * rng.uniform(3.0, 5.2) + avg_score * 5, 1)

            sessions.append(
                {
                    "session_id": session_id,
                    "participant_id": participant_id,
                    "track": track,
                    "duration_min": duration_min,
                    "n_questions": n_questions,
                    "initial_difficulty": initial_difficulty,
                    "termination_reason": termination_reason,
                    "termination_rounds": n_questions,
                }
            )
            ability_label = int(clamp(round(1 + avg_score * 4 + rng.gauss(0, 0.35)), 1, 5))
            ability_by_session[session_id] = ability_label
            session_id += 1

    ability_labels = [
        {
            "session_id": row["session_id"],
            "participant_id": row["participant_id"],
            "ability_label": ability_by_session[int(row["session_id"])],
            "source": "synthetic_expert",
        }
        for row in sessions
    ]

    missing_concepts = []
    for row in asked_questions:
        if rng.random() > 0.58:
            continue
        session_rounds = asked_by_session[int(row["session_id"])]
        future = [
            future_row["chapter"]
            for future_row in session_rounds
            if int(row["round"]) < int(future_row["round"]) <= int(row["round"]) + 3
        ]
        chapter = rng.choice(ALL_CHAPTERS)
        if rng.random() < 0.42:
            chapter = row["chapter"]
        missing_concepts.append(
            {
                "session_id": row["session_id"],
                "round": row["round"],
                "concept_id": f"{chapter}_{row['session_id']}_{row['round']}",
                "chapter": chapter,
                "queried_within_k": 1 if chapter in future else 0,
            }
        )

    human_evaluations = []
    sampled_evals = rng.sample(evaluations, max(1, int(len(evaluations) * 0.42)))
    for row in sampled_evals:
        for evaluator_id in (1, 2):
            human_evaluations.append(
                {
                    "response_id": row["asked_question_id"],
                    "evaluator_id": evaluator_id,
                    "correctness": round(clamp(float(row["correctness"]) + rng.gauss(0, 0.065), 0, 1), 2),
                    "depth": round(clamp(float(row["depth"]) + rng.gauss(0, 0.065), 0, 1), 2),
                    "clarity": round(clamp(float(row["clarity"]) + rng.gauss(0, 0.065), 0, 1), 2),
                    "practicality": round(clamp(float(row["practicality"]) + rng.gauss(0, 0.065), 0, 1), 2),
                    "tradeoffs": round(clamp(float(row["tradeoffs"]) + rng.gauss(0, 0.065), 0, 1), 2),
                    "overall_score": round(clamp(float(row["overall_score"]) + rng.gauss(0, 0.055), 0, 1), 4),
                }
            )

    expert_relevance = []
    for row in sessions:
        ability = participant_ability[int(row["participant_id"])]
        base = 0.54 + 0.22 * ability + 0.03 * min(int(row["n_questions"]), 8)
        expert_relevance.append(
            {
                "session_id": row["session_id"],
                "evaluator_id": 1,
                "relevance": 1 if rng.random() < clamp(base, 0.2, 0.95) else 0,
            }
        )

    provenance_log = [
        {
            "eval_id": row["asked_question_id"],
            "provenance": row["provenance"],
            "llm_available": 1,
            "fallback_triggered": 1 if row["provenance"] == "rule" and rng.random() < 0.08 else 0,
        }
        for row in evaluations
    ]
    termination_log = [
        {
            "session_id": row["session_id"],
            "reason": row["termination_reason"],
            "rounds": row["termination_rounds"],
        }
        for row in sessions
    ]
    survey_responses = [
        {
            "session_id": row["session_id"],
            "satisfaction": rng.choices([2, 3, 4, 5], weights=[0.04, 0.20, 0.42, 0.34], k=1)[0],
        }
        for row in sessions
    ]

    write_csv(output / "participants.csv", participants, ["participant_id", "resume_available", "experience_level", "education_level", "primary_language"])
    write_csv(output / "resumes.csv", resumes, ["resume_id", "user_id", "filename", "has_parsed_json"])
    write_csv(output / "sessions.csv", sessions, ["session_id", "participant_id", "track", "duration_min", "n_questions", "initial_difficulty", "termination_reason", "termination_rounds"])
    write_csv(output / "question_bank.csv", question_bank, ["question_id", "difficulty", "chapter", "track"])
    write_csv(output / "asked_questions.csv", asked_questions, ["session_id", "round", "question_id", "difficulty", "chapter", "priority_used"])
    write_csv(output / "evaluations.csv", evaluations, ["session_id", "round", "question_id", "asked_question_id", "correctness", "depth", "clarity", "practicality", "tradeoffs", "overall_score", "provenance", "missing_points"])
    write_csv(output / "turns.csv", turns, ["id", "session_id", "role", "content"])
    write_csv(output / "ability_labels.csv", ability_labels, ["session_id", "participant_id", "ability_label", "source"])
    write_csv(output / "missing_concepts.csv", missing_concepts, ["session_id", "round", "concept_id", "chapter", "queried_within_k"])
    write_csv(output / "human_evaluations.csv", human_evaluations, ["response_id", "evaluator_id", "correctness", "depth", "clarity", "practicality", "tradeoffs", "overall_score"])
    write_csv(output / "expert_relevance_ratings.csv", expert_relevance, ["session_id", "evaluator_id", "relevance"])
    write_csv(output / "evaluation_provenance_log.csv", provenance_log, ["eval_id", "provenance", "llm_available", "fallback_triggered"])
    write_csv(output / "termination_log.csv", termination_log, ["session_id", "reason", "rounds"])
    write_csv(output / "survey_responses.csv", survey_responses, ["session_id", "satisfaction"])

    return {
        "participants": len(participants),
        "resumes": len(resumes),
        "sessions": len(sessions),
        "question_bank": len(question_bank),
        "asked_questions": len(asked_questions),
        "evaluations": len(evaluations),
        "turns": len(turns),
        "ability_labels": len(ability_labels),
        "missing_concepts": len(missing_concepts),
        "human_evaluations": len(human_evaluations),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate larger reproduction CSV data.")
    parser.add_argument("--output", "-o", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--seed", type=int, default=20260504)
    parser.add_argument("--participants", type=int, default=100)
    parser.add_argument("--sessions-per-participant", type=int, default=3)
    parser.add_argument("--min-rounds", type=int, default=5)
    parser.add_argument("--max-rounds", type=int, default=8)
    parser.add_argument("--questions-per-chapter", type=int, default=6)
    args = parser.parse_args()

    counts = generate_dataset(
        output=args.output,
        seed=args.seed,
        participants_count=args.participants,
        sessions_per_participant=args.sessions_per_participant,
        min_rounds=args.min_rounds,
        max_rounds=args.max_rounds,
        questions_per_chapter=args.questions_per_chapter,
    )
    print("Generated reproduction dataset:")
    for name, count in counts.items():
        print(f"  {name}: {count}")
    print(f"Output: {args.output.resolve()}")


if __name__ == "__main__":
    main()
