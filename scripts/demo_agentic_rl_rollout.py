#!/usr/bin/env python3
"""Lightweight demo helper for Agentic-RL rollout artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def _safe_read(path: Path):
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Summarize Agentic-RL rollout artifacts.")
    parser.add_argument("--output-dir", default="reproduce_results/output", help="Directory containing tab_*.csv outputs")
    args = parser.parse_args()

    out = Path(args.output_dir)
    eval_tab = _safe_read(out / "tab_eval_policy.csv")
    sel_tab = _safe_read(out / "tab_bandit_policy.csv")
    joint_tab = _safe_read(out / "tab_joint_ablation.csv")

    print("=== Agentic-RL Demo Summary ===")
    if eval_tab is not None and not eval_tab.empty:
        row = eval_tab.iloc[0].to_dict()
        print(f"[Eval-RL] samples={row.get('Train Samples')} avg_reward={row.get('Avg Reward')} top1={row.get('Top1 Action Match (%)')}")
    else:
        print("[Eval-RL] tab_eval_policy.csv missing")

    if sel_tab is not None and not sel_tab.empty:
        row = sel_tab.iloc[0].to_dict()
        print(f"[Question-RL] samples={row.get('Train Samples')} avg_reward={row.get('Avg Reward')} regret={row.get('Avg Regret')}")
    else:
        print("[Question-RL] tab_bandit_policy.csv missing")

    if joint_tab is not None and not joint_tab.empty:
        print("[Joint Ablation]")
        print(joint_tab.to_string(index=False))
    else:
        print("[Joint Ablation] tab_joint_ablation.csv missing")


if __name__ == "__main__":
    main()
