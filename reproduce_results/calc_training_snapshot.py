#!/usr/bin/env python3
"""Freeze training snapshot and generate baseline tables."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from calc_eval_policy import run as run_eval_policy
from calc_joint_reward_sweep import run as run_joint_reward
from calc_wideseek_baseline import run as run_width_baseline
from wideseek_data_utils import add_split_column, load_eval_policy_df, snapshot_manifest


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_eval_policy_df(data_dir)
    if df.empty:
        pd.DataFrame(
            {
                "Snapshot": ["baseline_snapshot"],
                "Rows": ["ILLUSTRATIVE"],
                "Train Rows": ["ILLUSTRATIVE"],
                "Val Rows": ["ILLUSTRATIVE"],
                "Test Rows": ["ILLUSTRATIVE"],
            }
        ).to_csv(output_dir / "tab_training_snapshot.csv", index=False)
        return False

    snap = add_split_column(df)
    snap_path = output_dir / "snapshot_eval_policy_trajectory.csv"
    snap.to_csv(snap_path, index=False)

    manifest = snapshot_manifest(snap)
    manifest["seed"] = int(seed)
    manifest["snapshot_file"] = snap_path.name
    (output_dir / "snapshot_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    run_eval_policy(data_dir, output_dir, seed)
    run_width_baseline(data_dir, output_dir, seed)
    run_joint_reward(data_dir, output_dir, seed)

    pd.DataFrame(
        {
            "Snapshot": ["baseline_snapshot"],
            "Rows": [manifest["rows"]],
            "Train Rows": [manifest["rows_by_split"].get("train", 0)],
            "Val Rows": [manifest["rows_by_split"].get("val", 0)],
            "Test Rows": [manifest["rows_by_split"].get("test", 0)],
            "Eval Baseline": ["tab_eval_policy.csv"],
            "Width Baseline": ["tab_wideseek_baseline.csv"],
            "Joint Sweep": ["tab_joint_reward_sweep.csv"],
        }
    ).to_csv(output_dir / "tab_training_snapshot.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

