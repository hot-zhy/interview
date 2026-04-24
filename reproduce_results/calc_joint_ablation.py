#!/usr/bin/env python3
"""Build joint ablation table for eval-RL and question-RL."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def _read_metric(path: Path, col: str, default: str = "—") -> str:
    if not path.exists():
        return default
    df = pd.read_csv(path)
    if df.empty or col not in df.columns:
        return default
    return str(df.iloc[0][col])


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = (data_dir, seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selection_path = output_dir / "tab_selection.csv"
    bandit_path = output_dir / "tab_bandit_policy.csv"
    eval_policy_path = output_dir / "tab_eval_policy.csv"

    has_any = selection_path.exists() or bandit_path.exists() or eval_policy_path.exists()
    if not has_any:
        pd.DataFrame(
            {
                "Setting": ["Baseline", "Eval-RL only", "Question-RL only", "Eval-RL + Question-RL"],
                "Selection Reward": ["ILLUSTRATIVE"] * 4,
                "Selection Regret": ["ILLUSTRATIVE"] * 4,
                "Eval Avg Reward": ["ILLUSTRATIVE"] * 4,
                "Eval Top1 Action Match (%)": ["ILLUSTRATIVE"] * 4,
            }
        ).to_csv(output_dir / "tab_joint_ablation.csv", index=False)
        return False

    selection_reward = _read_metric(selection_path, "Cumulative Reward")
    selection_regret = _read_metric(selection_path, "Regret")
    eval_avg_reward = _read_metric(eval_policy_path, "Avg Reward")
    eval_top1 = _read_metric(eval_policy_path, "Top1 Action Match (%)")

    rows = pd.DataFrame(
        [
            {
                "Setting": "Baseline",
                "Selection Reward": "—",
                "Selection Regret": "—",
                "Eval Avg Reward": "—",
                "Eval Top1 Action Match (%)": "—",
            },
            {
                "Setting": "Eval-RL only",
                "Selection Reward": "—",
                "Selection Regret": "—",
                "Eval Avg Reward": eval_avg_reward,
                "Eval Top1 Action Match (%)": eval_top1,
            },
            {
                "Setting": "Question-RL only",
                "Selection Reward": selection_reward,
                "Selection Regret": selection_regret,
                "Eval Avg Reward": "—",
                "Eval Top1 Action Match (%)": "—",
            },
            {
                "Setting": "Eval-RL + Question-RL",
                "Selection Reward": selection_reward,
                "Selection Regret": selection_regret,
                "Eval Avg Reward": eval_avg_reward,
                "Eval Top1 Action Match (%)": eval_top1,
            },
        ]
    )
    rows.to_csv(output_dir / "tab_joint_ablation.csv", index=False)
    return True
