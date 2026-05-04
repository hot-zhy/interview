#!/usr/bin/env python3
"""Sweep alpha/beta/gamma weights for joint reward diagnostics."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from wideseek_data_utils import load_eval_policy_df, safe_float


def _calc_reward(df: pd.DataFrame, alpha: float, beta: float, gamma: float) -> pd.Series:
    return (
        df["overall_score"]
        - alpha * df["estimated_cost"]
        - beta * df["latency_norm"]
        - gamma * df["instability"]
    )


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = seed
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = load_eval_policy_df(data_dir)
    if df.empty:
        pd.DataFrame(
            [
                {
                    "alpha": "ILLUSTRATIVE",
                    "beta": "ILLUSTRATIVE",
                    "gamma": "ILLUSTRATIVE",
                    "Avg Joint Reward": "ILLUSTRATIVE",
                    "Top Width": "ILLUSTRATIVE",
                }
            ]
        ).to_csv(output_dir / "tab_joint_reward_sweep.csv", index=False)
        return False

    df["overall_score"] = df.get("overall_score", 0.0).apply(safe_float)
    df["estimated_cost"] = df.get("estimated_cost", 0.0).apply(safe_float)
    df["latency_ms"] = df.get("latency_ms", 0.0).apply(safe_float)
    df["latency_norm"] = (df["latency_ms"] / max(df["latency_ms"].quantile(0.95), 1.0)).clip(lower=0.0, upper=1.0)
    df["instability"] = df.get("instability", 0.0).apply(safe_float).clip(lower=0.0, upper=1.0)
    df["width_completed"] = df.get("width_completed", 1).fillna(1).astype(int)

    sweeps = [
        (0.05, 0.05, 0.05),
        (0.10, 0.08, 0.06),
        (0.15, 0.10, 0.08),
        (0.20, 0.12, 0.10),
    ]
    rows = []
    for alpha, beta, gamma in sweeps:
        reward = _calc_reward(df, alpha=alpha, beta=beta, gamma=gamma)
        width_perf = (
            pd.DataFrame({"width": df["width_completed"], "reward": reward})
            .groupby("width", as_index=False)["reward"]
            .mean()
        )
        top_width = int(width_perf.sort_values("reward", ascending=False).iloc[0]["width"]) if not width_perf.empty else 1
        rows.append(
            {
                "alpha": alpha,
                "beta": beta,
                "gamma": gamma,
                "Avg Joint Reward": round(float(reward.mean()), 5),
                "Top Width": top_width,
            }
        )

    pd.DataFrame(rows).to_csv(output_dir / "tab_joint_reward_sweep.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

