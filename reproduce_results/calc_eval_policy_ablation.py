#!/usr/bin/env python3
"""Feature ablation and reward-weight sweeps for eval routing policy."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Iterable, List

import pandas as pd

from eval_policy_utils import EvalSampleRow, evaluate_eval_policy, train_linucb_eval
from wideseek_data_utils import add_split_column, load_eval_policy_df, safe_float

FEATURE_NAMES = [
    "bias",
    "round_progress",
    "answer_length",
    "recent_avg_score",
    "missing_points_count",
    "fallback_count",
    "llm_calls_used",
    "multi_judge_used",
    "llm_available",
    "multi_judge_enabled",
]


def _build_samples(df: pd.DataFrame, disabled_features: Iterable[str] = ()) -> List[EvalSampleRow]:
    disabled = set(disabled_features)
    samples: List[EvalSampleRow] = []
    max_round = max(float(df["round"].max()), 1.0)
    for _, row in df.iterrows():
        action = str(row.get("action", "") or "")
        if not action:
            continue
        vec = [
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
        for idx, name in enumerate(FEATURE_NAMES):
            if name in disabled:
                vec[idx] = 0.0
        samples.append(
            EvalSampleRow(
                session_id=int(row.get("session_id", 0)),
                round_number=int(row.get("round", 1)),
                action=action,
                reward=float(row.get("reward", 0.0) or 0.0),
                features=vec,
            )
        )
    return samples


def _apply_reward_weights(df: pd.DataFrame, alpha: float, beta: float, gamma: float) -> pd.Series:
    latency = (df["latency_ms"] / max(df["latency_ms"].quantile(0.95), 1.0)).clip(0.0, 1.0)
    instability = df["instability"].clip(0.0, 1.0)
    return df["overall_score"] - alpha * df["estimated_cost"] - beta * latency - gamma * instability


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = seed
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_eval_policy_df(data_dir)
    if df.empty:
        pd.DataFrame({"Ablation": ["ILLUSTRATIVE"], "Avg Reward": ["ILLUSTRATIVE"]}).to_csv(
            output_dir / "tab_eval_policy_ablation.csv",
            index=False,
        )
        pd.DataFrame({"alpha": ["ILLUSTRATIVE"], "beta": ["ILLUSTRATIVE"], "gamma": ["ILLUSTRATIVE"]}).to_csv(
            output_dir / "tab_eval_policy_reward_sweep.csv",
            index=False,
        )
        return False

    # Ensure numeric columns
    for col in ["overall_score", "estimated_cost", "latency_ms", "instability", "reward"]:
        df[col] = df.get(col, 0.0).apply(safe_float)
    split_df = add_split_column(df)
    train_df = split_df[split_df["split"] == "train"].reset_index(drop=True)
    eval_df = split_df[split_df["split"].isin(["val", "test"])].reset_index(drop=True)
    if train_df.empty or eval_df.empty:
        train_df = split_df
        eval_df = split_df

    ablations = {
        "all_features": [],
        "drop_latency_proxies": ["llm_calls_used", "multi_judge_used"],
        "drop_answer_shape": ["answer_length", "missing_points_count"],
        "drop_history": ["recent_avg_score", "fallback_count"],
    }
    ablation_rows = []
    for name, dropped in ablations.items():
        train_samples = _build_samples(train_df, disabled_features=dropped)
        eval_samples = _build_samples(eval_df, disabled_features=dropped)
        payload = train_linucb_eval(train_samples, l2=1.0)
        metrics = evaluate_eval_policy(payload, eval_samples, alpha=0.25)
        ablation_rows.append(
            {
                "Ablation": name,
                "Dropped": ",".join(dropped) if dropped else "none",
                "Train Samples": int(payload.get("training_rows", 0)),
                "Eval Samples": len(eval_samples),
                "Avg Reward": round(float(metrics["avg_reward"]), 5),
                "Avg Regret": round(float(metrics["avg_regret"]), 5),
                "Top1 Action Match (%)": round(float(metrics["top1_action_match"]), 2),
            }
        )
    pd.DataFrame(ablation_rows).to_csv(output_dir / "tab_eval_policy_ablation.csv", index=False)

    sweeps = [(0.05, 0.05, 0.05), (0.10, 0.08, 0.06), (0.15, 0.10, 0.08), (0.20, 0.12, 0.10)]
    sweep_rows = []
    train_samples_base = _build_samples(train_df, disabled_features=[])
    eval_samples_base = _build_samples(eval_df, disabled_features=[])
    action_col = train_df["action"] if "action" in train_df.columns else pd.Series([""] * len(train_df))
    train_valid_rows = train_df[action_col.astype(str).str.strip() != ""].reset_index(drop=True)
    eval_action_col = eval_df["action"] if "action" in eval_df.columns else pd.Series([""] * len(eval_df))
    eval_valid_rows = eval_df[eval_action_col.astype(str).str.strip() != ""].reset_index(drop=True)
    for alpha, beta, gamma in sweeps:
        train_weighted = _apply_reward_weights(train_valid_rows, alpha=alpha, beta=beta, gamma=gamma)
        eval_weighted = _apply_reward_weights(eval_valid_rows, alpha=alpha, beta=beta, gamma=gamma)
        train_samples = [
            replace(sample, reward=float(train_weighted.iloc[idx]))
            for idx, sample in enumerate(train_samples_base)
        ]
        eval_samples = [
            replace(sample, reward=float(eval_weighted.iloc[idx]))
            for idx, sample in enumerate(eval_samples_base)
        ]
        payload = train_linucb_eval(train_samples, l2=1.0)
        metrics = evaluate_eval_policy(payload, eval_samples, alpha=0.25)
        sweep_rows.append(
            {
                "alpha": alpha,
                "beta": beta,
                "gamma": gamma,
                "Train Samples": len(train_samples),
                "Eval Samples": len(eval_samples),
                "Avg Reward": round(float(metrics["avg_reward"]), 5),
                "Avg Regret": round(float(metrics["avg_regret"]), 5),
                "Top1 Action Match (%)": round(float(metrics["top1_action_match"]), 2),
            }
        )
    pd.DataFrame(sweep_rows).to_csv(output_dir / "tab_eval_policy_reward_sweep.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

