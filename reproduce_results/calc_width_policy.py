#!/usr/bin/env python3
"""Train/evaluate width decision policy (w=1/2/4/8)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from eval_policy_utils import EvalSampleRow, evaluate_eval_policy, persist_eval_policy, train_linucb_eval
from wideseek_data_utils import add_split_column, load_eval_policy_df, safe_float


def _width_action(width: int) -> str:
    return f"width_{int(max(1, width))}"


def _build_samples(df: pd.DataFrame) -> list[EvalSampleRow]:
    rows: list[EvalSampleRow] = []
    max_round = max(float(df["round"].max()), 1.0)
    for _, row in df.iterrows():
        width = int(max(1, safe_float(row.get("width_completed", 1), 1.0)))
        features = [
            1.0,
            min(max(float(row.get("round", 1)) / max_round, 0.0), 1.0),
            min(max(float(row.get("answer_length", 0)) / 1200.0, 0.0), 1.0),
            min(max(float(row.get("recent_avg_score", 0.5)), 0.0), 1.0),
            min(max(float(row.get("missing_points_count", 0)) / 6.0, 0.0), 1.0),
            min(max(float(row.get("fallback_count", 0)) / 6.0, 0.0), 1.0),
            min(max(float(row.get("llm_calls_used", 0)) / 8.0, 0.0), 1.0),
            min(max(float(row.get("multi_judge_used", 0)) / 3.0, 0.0), 1.0),
            1.0,
            1.0,
        ]
        rows.append(
            EvalSampleRow(
                session_id=int(row.get("session_id", 0)),
                round_number=int(row.get("round", 1)),
                action=_width_action(width),
                reward=float(row.get("reward", 0.0) or 0.0),
                features=features,
            )
        )
    return rows


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = seed
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_eval_policy_df(data_dir)
    if df.empty:
        pd.DataFrame({"Strategy": ["Width Policy"], "Train Samples": ["ILLUSTRATIVE"]}).to_csv(
            output_dir / "tab_width_policy.csv",
            index=False,
        )
        return False

    for col in ["reward", "overall_score", "latency_ms", "estimated_cost", "width_completed"]:
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
    metrics = evaluate_eval_policy(payload, eval_samples, alpha=0.30)

    width_payload = {
        "feature_dim": payload.get("feature_dim", 0),
        "models": payload.get("models", {}),
        "training_rows": payload.get("training_rows", 0),
        "type": "width_policy",
    }
    artifact = persist_eval_policy(output_dir, width_payload)
    artifact_renamed = output_dir / "contextual_width_policy.json"
    if artifact_renamed.exists():
        artifact_renamed.unlink()
    artifact.rename(artifact_renamed)

    pd.DataFrame(
        {
            "Strategy": ["Width Policy (LinUCB)"],
            "Train Samples": [int(width_payload.get("training_rows", 0))],
            "Eval Samples": [len(eval_samples)],
            "Avg Reward": [f"{metrics['avg_reward']:.4f}"],
            "Avg Regret": [f"{metrics['avg_regret']:.4f}"],
            "Top1 Width Match (%)": [f"{metrics['top1_action_match']:.1f}"],
            "Avg Width": [f"{df['width_completed'].mean():.2f}"],
            "P95 Latency(ms)": [f"{df['latency_ms'].quantile(0.95):.1f}"],
            "Avg Cost": [f"{df['estimated_cost'].mean():.4f}"],
            "Policy Artifact": [artifact_renamed.name],
        }
    ).to_csv(output_dir / "tab_width_policy.csv", index=False)

    pd.DataFrame(
        {
            "session_id": split_df.get("session_id", 0),
            "round": split_df.get("round", 1),
            "split": split_df.get("split", "train"),
            "width": split_df["width_completed"].astype(int),
            "reward": split_df["reward"].round(5),
        }
    ).to_csv(output_dir / "width_policy_training_samples.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

