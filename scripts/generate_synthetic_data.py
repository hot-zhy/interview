#!/usr/bin/env python3
"""
Generate synthetic annotation and log data for reproduction pipeline.

Uses existing exported data (participants, sessions, asked_questions, evaluations)
to produce plausible synthetic:
  - ability_labels.csv
  - missing_concepts.csv
  - human_evaluations.csv
  - expert_relevance_ratings.csv
  - evaluation_provenance_log.csv
  - termination_log.csv
  - survey_responses.csv

Usage:
  python scripts/generate_synthetic_data.py [--output data/] [--seed 42]
"""

import argparse
import csv
import random
from pathlib import Path


def load_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def generate_ability_labels(sessions: list[dict], evaluations: list[dict], seed: int) -> list[dict]:
    """Derive ability_label from session avg score + noise (simulates external expert)."""
    random.seed(seed)
    # session_id -> list of overall_scores
    sess_scores = {}
    for e in evaluations:
        sid = e.get("session_id")
        if not sid:
            continue
        try:
            s = float(e.get("overall_score", 0))
        except (ValueError, TypeError):
            continue
        sess_scores.setdefault(sid, []).append(s)

    rows = []
    for s in sessions:
        sid = s.get("session_id")
        scores = sess_scores.get(sid, [])
        avg = sum(scores) / len(scores) if scores else 0.3
        # Map [0,1] to ability 1-5, add noise
        raw = avg * 4 + 1  # 1-5
        noise = random.gauss(0, 0.4)
        ability = max(1, min(5, round(raw + noise)))
        rows.append({
            "session_id": sid,
            "participant_id": s.get("participant_id"),
            "ability_label": ability,
            "source": "synthetic_expert",
        })
    return rows


def generate_missing_concepts(
    asked: list[dict], question_bank: list[dict], seed: int, k: int = 3
) -> list[dict]:
    """Synthetic: for multi-round sessions, mark some chapters as 'missing' and whether queried within k."""
    random.seed(seed)
    chapters = list({q.get("chapter") for q in question_bank if q.get("chapter")})
    if not chapters:
        chapters = ["String", "基本语法", "异常", "I/O", "SPI", "序列化和反序列化"]

    # session_id -> [(round, chapter), ...] sorted by round
    sess_rounds = {}
    for a in asked:
        sid = a.get("session_id")
        r = int(a.get("round", 0))
        ch = a.get("chapter") or ""
        if sid and ch:
            sess_rounds.setdefault(sid, []).append((r, ch))
    for sid in sess_rounds:
        sess_rounds[sid] = sorted(sess_rounds[sid], key=lambda x: x[0])

    rows = []
    for sid, rounds_ch in sess_rounds.items():
        if len(rounds_ch) < 2:
            continue
        max_round = max(r[0] for r in rounds_ch)
        n_entries = random.randint(3, min(8, len(rounds_ch) * 2))
        for _ in range(n_entries):
            round_idx = random.randint(1, max_round)
            chapter = random.choice(chapters)
            later = [(r, ch) for r, ch in rounds_ch if r > round_idx and r <= round_idx + k]
            queried = 1 if any(ch == chapter for _, ch in later) else 0
            rows.append({
                "session_id": sid,
                "round": round_idx,
                "concept_id": f"{chapter}_{round_idx}",
                "chapter": chapter,
                "queried_within_k": queried,
            })
    return rows


def generate_human_evaluations(evaluations: list[dict], seed: int, sample_ratio: float = 0.3) -> list[dict]:
    """Sample evaluations, add evaluator scores with small noise (simulates human variance)."""
    random.seed(seed)
    sample = random.sample(evaluations, max(1, int(len(evaluations) * sample_ratio)))
    rows = []
    for e in sample:
        try:
            c = float(e.get("correctness", 0))
            d = float(e.get("depth", 0))
            cl = float(e.get("clarity", 0.5))
            p = float(e.get("practicality", 0.4))
            t = float(e.get("tradeoffs", 0.3))
            o = float(e.get("overall_score", 0.2))
        except (ValueError, TypeError):
            continue
        for ev_id in [1, 2]:  # 2 evaluators
            noise = 0.08
            rows.append({
                "response_id": e.get("asked_question_id"),
                "evaluator_id": ev_id,
                "correctness": round(max(0, min(1, c + random.gauss(0, noise))), 2),
                "depth": round(max(0, min(1, d + random.gauss(0, noise))), 2),
                "clarity": round(max(0, min(1, cl + random.gauss(0, noise))), 2),
                "practicality": round(max(0, min(1, p + random.gauss(0, noise))), 2),
                "tradeoffs": round(max(0, min(1, t + random.gauss(0, noise))), 2),
                "overall_score": round(max(0, min(1, o + random.gauss(0, noise))), 4),
            })
    return rows


def generate_expert_relevance_ratings(sessions: list[dict], seed: int) -> list[dict]:
    """Synthetic relevance: higher for sessions with more questions (personalized)."""
    random.seed(seed)
    rows = []
    for s in sessions:
        nq = int(s.get("n_questions", 1))
        # More questions -> more likely relevant (personalized)
        base = 0.5 + 0.1 * min(nq, 5)
        rel = 1 if random.random() < base else 0
        rows.append({
            "session_id": s.get("session_id"),
            "evaluator_id": 1,
            "relevance": rel,
        })
    return rows


def generate_evaluation_provenance_log(evaluations: list[dict], seed: int) -> list[dict]:
    """Assign provenance: ~80% rule, ~15% llm, ~5% hybrid."""
    random.seed(seed)
    rows = []
    for e in evaluations:
        r = random.random()
        if r < 0.80:
            prov = "rule"
        elif r < 0.95:
            prov = "llm"
        else:
            prov = "hybrid"
        rows.append({
            "eval_id": e.get("asked_question_id"),
            "provenance": prov,
            "llm_available": 1,
            "fallback_triggered": 1 if prov == "rule" and random.random() < 0.1 else 0,
        })
    return rows


def generate_termination_log(sessions: list[dict]) -> list[dict]:
    """From sessions: termination_reason, termination_rounds."""
    rows = []
    for s in sessions:
        rows.append({
            "session_id": s.get("session_id"),
            "reason": s.get("termination_reason", "completed"),
            "rounds": s.get("termination_rounds", 0),
        })
    return rows


def generate_survey_responses(sessions: list[dict], seed: int) -> list[dict]:
    """Synthetic satisfaction 1-5, slightly positive bias."""
    random.seed(seed)
    rows = []
    for s in sessions:
        sat = random.choices([3, 4, 5], weights=[0.2, 0.4, 0.4])[0]
        rows.append({
            "session_id": s.get("session_id"),
            "satisfaction": sat,
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", "-o", default="data", help="Output directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    out_dir = Path(args.output)
    data_dir = out_dir

    sessions = load_csv(data_dir / "sessions.csv")
    evaluations = load_csv(data_dir / "evaluations.csv")
    asked = load_csv(data_dir / "asked_questions.csv")
    question_bank = load_csv(data_dir / "question_bank.csv")

    if not sessions:
        print("No sessions.csv found. Run export_db.py first.")
        return

    # Generate
    ability = generate_ability_labels(sessions, evaluations, args.seed)
    missing = generate_missing_concepts(asked, question_bank, args.seed)
    human = generate_human_evaluations(evaluations, args.seed)
    relevance = generate_expert_relevance_ratings(sessions, args.seed)
    provenance = generate_evaluation_provenance_log(evaluations, args.seed)
    termination = generate_termination_log(sessions)
    survey = generate_survey_responses(sessions, args.seed)

    # Save
    save_csv(out_dir / "ability_labels.csv", ability, ["session_id", "participant_id", "ability_label", "source"])
    save_csv(out_dir / "missing_concepts.csv", missing, ["session_id", "round", "concept_id", "chapter", "queried_within_k"])
    save_csv(out_dir / "human_evaluations.csv", human, ["response_id", "evaluator_id", "correctness", "depth", "clarity", "practicality", "tradeoffs", "overall_score"])
    save_csv(out_dir / "expert_relevance_ratings.csv", relevance, ["session_id", "evaluator_id", "relevance"])
    save_csv(out_dir / "evaluation_provenance_log.csv", provenance, ["eval_id", "provenance", "llm_available", "fallback_triggered"])
    save_csv(out_dir / "termination_log.csv", termination, ["session_id", "reason", "rounds"])
    save_csv(out_dir / "survey_responses.csv", survey, ["session_id", "satisfaction"])

    print("Generated synthetic data:")
    print(f"  ability_labels.csv: {len(ability)} rows")
    print(f"  missing_concepts.csv: {len(missing)} rows")
    print(f"  human_evaluations.csv: {len(human)} rows")
    print(f"  expert_relevance_ratings.csv: {len(relevance)} rows")
    print(f"  evaluation_provenance_log.csv: {len(provenance)} rows")
    print(f"  termination_log.csv: {len(termination)} rows")
    print(f"  survey_responses.csv: {len(survey)} rows")
    print(f"\nOutput: {out_dir.absolute()}")


if __name__ == "__main__":
    main()
