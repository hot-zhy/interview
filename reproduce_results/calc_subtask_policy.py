#!/usr/bin/env python3
"""Learn an offline policy for subtask-plan enablement."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from eval_policy_utils import EvalSampleRow, evaluate_eval_policy, persist_eval_policy, train_linucb_eval
from wideseek_data_utils import add_split_column, load_eval_policy_df, safe_float


def _ideal_subtasks(score: float, missing_count: int) -> int:
    if score < 0.35 or missing_count >= 2:
        return 3
    if score < 0.50:
        return 2
    if score < 0.65:
        return 1
    return 0


def _quality_gain(ideal: int, chosen: int) -> float:
    return max(0.0, 0.05 * (3 - abs(int(ideal) - int(chosen))))


def _build_samples(df: pd.DataFrame) -> list[EvalSampleRow]:
    samples: list[EvalSampleRow] = []
    max_round = max(float(df["round"].max()), 1.0)
    for _, row in df.iterrows():
        score = safe_float(row.get("overall_score", 0.0))
        miss = int(safe_float(row.get("missing_points_count", 0), 0))
        ideal = _ideal_subtasks(score, miss)
        chosen = int(max(0, min(3, round(safe_float(row.get("width_completed", 1)) / 3.0))))
        action = f"subtasks_{chosen}"
        reward = (
            score
            + _quality_gain(ideal, chosen)
            - 0.02 * chosen
            - 0.04 * min(max(safe_float(row.get("latency_ms", 0.0)) / 3500.0, 0.0), 1.0)
            - 0.03 * min(max(safe_float(row.get("instability", 0.0)), 0.0), 1.0)
        )
        features = [
            1.0,
            min(max(float(row.get("round", 1)) / max_round, 0.0), 1.0),
            min(max(float(row.get("answer_length", 0)) / 1200.0, 0.0), 1.0),
            min(max(float(row.get("recent_avg_score", 0.5)), 0.0), 1.0),
            min(max(float(miss) / 6.0, 0.0), 1.0),
            min(max(float(row.get("fallback_count", 0)) / 6.0, 0.0), 1.0),
            min(max(float(row.get("llm_calls_used", 0)) / 8.0, 0.0), 1.0),
            min(max(float(row.get("multi_judge_used", 0)) / 3.0, 0.0), 1.0),
            1.0,
            1.0,
        ]
        samples.append(
            EvalSampleRow(
                session_id=int(row.get("session_id", 0)),
                round_number=int(row.get("round", 1)),
                action=action,
                reward=float(reward),
                features=features,
            )
        )
    return samples


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = seed
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_eval_policy_df(data_dir)
    if df.empty:
        pd.DataFrame({"Strategy": ["Subtask Planner Policy"], "Train Samples": ["ILLUSTRATIVE"]}).to_csv(
            output_dir / "tab_subtask_policy.csv",
            index=False,
        )
        return False

    for col in ["overall_score", "missing_points_count", "latency_ms", "instability", "width_completed"]:
        df[col] = df.get(col, 0.0).apply(safe_float)

    split_df = add_split_column(df)
    train_df = split_df[split_df["split"] == "train"].reset_index(drop=True)
    eval_df = split_df[split_df["split"].isin(["val", "test"])].reset_index(drop=True)
    if train_df.empty or eval_df.empty:
        train_df = split_df
        eval_df = split_df
    train_samples = _build_samples(train_df)
    eval_samples = _build_samples(eval_df)
    payload = train_linucb_eval(train_samples, l2=1.0)
    metrics = evaluate_eval_policy(payload, eval_samples, alpha=0.20)

    subtask_payload = {
        "feature_dim": payload.get("feature_dim", 0),
        "models": payload.get("models", {}),
        "training_rows": payload.get("training_rows", 0),
        "type": "subtask_policy",
    }
    artifact = persist_eval_policy(output_dir, subtask_payload)
    artifact_renamed = output_dir / "contextual_subtask_policy.json"
    if artifact_renamed.exists():
        artifact_renamed.unlink()
    artifact.rename(artifact_renamed)

    sampled_actions = pd.Series([s.action for s in train_samples])
    pd.DataFrame(
        {
            "Strategy": ["Subtask Planner Policy (LinUCB)"],
            "Train Samples": [int(subtask_payload.get("training_rows", 0))],
            "Eval Samples": [len(eval_samples)],
            "Avg Reward": [f"{metrics['avg_reward']:.4f}"],
            "Avg Regret": [f"{metrics['avg_regret']:.4f}"],
            "Top1 Action Match (%)": [f"{metrics['top1_action_match']:.1f}"],
            "Action Diversity": [int(sampled_actions.nunique())],
            "Policy Artifact": [artifact_renamed.name],
        }
    ).to_csv(output_dir / "tab_subtask_policy.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

