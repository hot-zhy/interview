#!/usr/bin/env python3
"""Train/evaluate interview termination policy (continue/terminate)."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

from eval_policy_utils import EvalSampleRow, evaluate_eval_policy, persist_eval_policy, train_linucb_eval
from wideseek_data_utils import add_split_column, parse_missing_count, safe_float, safe_int


def _feature_vector(
    round_idx: int,
    total_rounds: int,
    avg_score: float,
    recent_avg: float,
    std_dev: float,
    difficulty_range: int,
    chapter_coverage: int,
    fallback_count: int,
    recent_improvement: float,
) -> List[float]:
    total = max(int(total_rounds), 1)
    return [
        1.0,
        min(max(float(round_idx) / float(total), 0.0), 1.0),
        min(max(float(avg_score), 0.0), 1.0),
        min(max(float(recent_avg), 0.0), 1.0),
        min(max(float(std_dev) / 0.5, 0.0), 1.0),
        min(max(float(difficulty_range) / 4.0, 0.0), 1.0),
        min(max(float(chapter_coverage) / 6.0, 0.0), 1.0),
        min(max(float(fallback_count) / 6.0, 0.0), 1.0),
        min(max((float(recent_improvement) + 1.0) / 2.0, 0.0), 1.0),
    ]


def _build_samples(data_dir: Path) -> List[EvalSampleRow]:
    sessions_path = data_dir / "sessions.csv"
    eval_path = data_dir / "evaluations.csv"
    asked_path = data_dir / "asked_questions.csv"
    if not (sessions_path.exists() and eval_path.exists() and asked_path.exists()):
        return []

    sessions = pd.read_csv(sessions_path)
    evaluations = pd.read_csv(eval_path)
    asked = pd.read_csv(asked_path)
    if sessions.empty or evaluations.empty or asked.empty:
        return []

    sessions = sessions.copy()
    sessions["termination_rounds"] = sessions.get("termination_rounds", 0).apply(lambda v: max(1, safe_int(v, 1)))
    sessions["n_questions"] = sessions.get("n_questions", 0).apply(lambda v: max(1, safe_int(v, 1)))

    eval_df = evaluations.copy()
    eval_df["session_id"] = eval_df.get("session_id", 0).apply(safe_int)
    eval_df["round"] = eval_df.get("round", 1).apply(lambda v: max(1, safe_int(v, 1)))
    eval_df["overall_score"] = eval_df.get("overall_score", 0.0).apply(safe_float)
    eval_df["missing_points_count"] = eval_df.get("missing_points", "").apply(parse_missing_count)

    asked_df = asked.copy()
    asked_df["session_id"] = asked_df.get("session_id", 0).apply(safe_int)
    asked_df["round"] = asked_df.get("round", 1).apply(lambda v: max(1, safe_int(v, 1)))

    merged = (
        eval_df.merge(
            asked_df[["session_id", "round", "difficulty", "chapter"]],
            on=["session_id", "round"],
            how="left",
        )
        .sort_values(["session_id", "round"])
        .reset_index(drop=True)
    )

    session_meta: Dict[int, Dict] = {
        int(r["session_id"]): {
            "termination_rounds": max(1, safe_int(r.get("termination_rounds", 1), 1)),
            "n_questions": max(1, safe_int(r.get("n_questions", 1), 1)),
            "termination_reason": str(r.get("termination_reason", "completed")),
        }
        for _, r in sessions.iterrows()
    }

    rows: List[EvalSampleRow] = []
    for sid, grp in merged.groupby("session_id"):
        sid_int = int(safe_int(sid, 0))
        g = grp.sort_values("round").reset_index(drop=True)
        if g.empty:
            continue

        meta = session_meta.get(sid_int, {})
        observed_last_round = int(g["round"].max())
        term_round = int(meta.get("termination_rounds", observed_last_round))
        total_rounds = max(int(meta.get("n_questions", term_round)), term_round, observed_last_round)

        scores: List[float] = []
        chapters_seen: set[str] = set()
        difficulties_seen: List[int] = []
        fallback_count = 0

        for _, row in g.iterrows():
            round_idx = max(1, int(safe_int(row.get("round", 1), 1)))
            score = float(safe_float(row.get("overall_score", 0.0), 0.0))
            scores.append(score)
            if str(row.get("provenance", "")).startswith("rule_fallback"):
                fallback_count += 1
            chapter = str(row.get("chapter", "") or "").strip()
            if chapter:
                chapters_seen.add(chapter)
            diff = safe_int(row.get("difficulty", 0), 0)
            if diff > 0:
                difficulties_seen.append(diff)

            avg_score = float(sum(scores) / len(scores))
            recent_scores = scores[-3:] if len(scores) >= 3 else scores
            recent_avg = float(sum(recent_scores) / len(recent_scores))
            std_dev = 0.0
            if len(scores) >= 3:
                variance = sum((s - avg_score) ** 2 for s in scores) / float(len(scores))
                std_dev = variance ** 0.5
            recent_improvement = scores[-1] - scores[-2] if len(scores) >= 2 else 0.0
            difficulty_range = (max(difficulties_seen) - min(difficulties_seen)) if difficulties_seen else 0
            chapter_coverage = len(chapters_seen)

            action = "terminate" if round_idx == term_round else "continue"
            round_pressure = min(max(float(round_idx) / float(total_rounds), 0.0), 1.0)
            if action == "terminate":
                reward = 0.75 + 0.30 * recent_avg - 0.20 * max(0.0, round_pressure - 0.8)
                if str(meta.get("termination_reason", "completed")) == "early_stop":
                    reward += 0.05
            else:
                need_more_rounds = max(0.0, 0.75 - recent_avg)
                reward = 0.65 + 0.25 * need_more_rounds + 0.12 * (1.0 - round_pressure)

            rows.append(
                EvalSampleRow(
                    session_id=sid_int,
                    round_number=round_idx,
                    action=action,
                    reward=float(reward),
                    features=_feature_vector(
                        round_idx=round_idx,
                        total_rounds=total_rounds,
                        avg_score=avg_score,
                        recent_avg=recent_avg,
                        std_dev=std_dev,
                        difficulty_range=difficulty_range,
                        chapter_coverage=chapter_coverage,
                        fallback_count=fallback_count,
                        recent_improvement=recent_improvement,
                    ),
                )
            )
    return rows


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = seed
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = _build_samples(data_dir)
    if not samples:
        pd.DataFrame({"Strategy": ["Termination Policy"], "Train Samples": ["ILLUSTRATIVE"]}).to_csv(
            output_dir / "tab_termination_policy.csv",
            index=False,
        )
        return False

    df = pd.DataFrame(
        {
            "session_id": [s.session_id for s in samples],
            "round": [s.round_number for s in samples],
            "action": [s.action for s in samples],
            "reward": [s.reward for s in samples],
        }
    )
    split_df = add_split_column(df)
    train_keys = set(
        split_df[split_df["split"] == "train"][["session_id", "round"]].apply(
            lambda r: (int(r["session_id"]), int(r["round"])), axis=1
        )
    )
    eval_keys = set(
        split_df[split_df["split"].isin(["val", "test"])][["session_id", "round"]].apply(
            lambda r: (int(r["session_id"]), int(r["round"])), axis=1
        )
    )
    if not train_keys or not eval_keys:
        train_keys = {(s.session_id, s.round_number) for s in samples}
        eval_keys = train_keys

    train_samples = [s for s in samples if (s.session_id, s.round_number) in train_keys]
    eval_samples = [s for s in samples if (s.session_id, s.round_number) in eval_keys]

    payload = train_linucb_eval(train_samples, l2=1.0)
    metrics = evaluate_eval_policy(payload, eval_samples, alpha=0.20)

    term_payload = {
        "feature_dim": payload.get("feature_dim", 0),
        "models": payload.get("models", {}),
        "training_rows": payload.get("training_rows", 0),
        "type": "termination_policy",
    }
    artifact = persist_eval_policy(output_dir, term_payload)
    artifact_renamed = output_dir / "contextual_termination_policy.json"
    if artifact_renamed.exists():
        artifact_renamed.unlink()
    artifact.rename(artifact_renamed)

    terminate_rate = 100.0 * float((df["action"] == "terminate").mean())
    avg_stop_round = float(df[df["action"] == "terminate"]["round"].mean()) if (df["action"] == "terminate").any() else 0.0
    pd.DataFrame(
        {
            "Strategy": ["Termination Policy (LinUCB)"],
            "Train Samples": [int(term_payload.get("training_rows", 0))],
            "Eval Samples": [len(eval_samples)],
            "Terminate Rate (%)": [f"{terminate_rate:.1f}"],
            "Avg Stop Round": [f"{avg_stop_round:.2f}"],
            "Avg Reward": [f"{metrics['avg_reward']:.4f}"],
            "Avg Regret": [f"{metrics['avg_regret']:.4f}"],
            "Top1 Match (%)": [f"{metrics['top1_action_match']:.1f}"],
            "Policy Artifact": [artifact_renamed.name],
        }
    ).to_csv(output_dir / "tab_termination_policy.csv", index=False)

    split_df.to_csv(output_dir / "termination_policy_training_samples.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

