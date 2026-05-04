#!/usr/bin/env python3
"""Generate final best-configuration decision report."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def _read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = (data_dir, seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    gate = _read(output_dir / "tab_go_nogo.csv")
    canary = _read(output_dir / "tab_canary_abtest.csv")
    reward = _read(output_dir / "tab_eval_policy_reward_sweep.csv")
    width = _read(output_dir / "tab_width_policy.csv")
    subtask = _read(output_dir / "tab_subtask_policy.csv")
    snapshot = _read(output_dir / "tab_training_snapshot.csv")

    if gate.empty or canary.empty:
        pd.DataFrame({"Decision": ["ILLUSTRATIVE"]}).to_csv(output_dir / "tab_best_config.csv", index=False)
        (output_dir / "best_decision_report.md").write_text(
            "# Best Decision Report\n\nInsufficient data to build final report.\n",
            encoding="utf-8",
        )
        return False

    gate_row = gate.iloc[0]
    recommended_stage = str(gate_row.get("Recommended Stage", "N/A"))
    decision = str(gate_row.get("Decision", "NO_GO"))
    reason = str(gate_row.get("Reason", "unknown"))

    stage_row = canary[canary["Stage"] == recommended_stage]
    stage_row = stage_row.iloc[0] if not stage_row.empty else canary.iloc[0]

    reward_row = reward.sort_values("Avg Reward", ascending=False).iloc[0] if not reward.empty else None
    width_row = width.iloc[0] if not width.empty else None
    subtask_row = subtask.iloc[0] if not subtask.empty else None
    snap_row = snapshot.iloc[0] if not snapshot.empty else None

    config_df = pd.DataFrame(
        {
            "Decision": [decision],
            "Recommended Stage": [recommended_stage],
            "Failure Reason": [reason],
            "Best Alpha": [reward_row["alpha"] if reward_row is not None else ""],
            "Best Beta": [reward_row["beta"] if reward_row is not None else ""],
            "Best Gamma": [reward_row["gamma"] if reward_row is not None else ""],
            "Top1 Width Match (%)": [width_row["Top1 Width Match (%)"] if width_row is not None else ""],
            "Avg Width": [width_row["Avg Width"] if width_row is not None else ""],
            "Subtask Diversity": [subtask_row["Action Diversity"] if subtask_row is not None else ""],
            "Quality Delta (%)": [stage_row.get("Quality Delta (%)", "")],
            "Cost Delta (%)": [stage_row.get("Cost Delta (%)", "")],
            "P95 Latency Delta (%)": [stage_row.get("P95 Latency Delta (%)", "")],
            "Fallback Delta (%)": [stage_row.get("Fallback Delta (%)", "")],
            "Snapshot Rows": [snap_row["Rows"] if snap_row is not None else ""],
        }
    )
    config_df.to_csv(output_dir / "tab_best_config.csv", index=False)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    report = f"""# Best Decision Report

- Generated at: `{ts}`
- Decision: `{decision}`
- Recommended rollout stage: `{recommended_stage}`
- Gate reason: `{reason}`

## Best Configuration

- Reward weights: `alpha={config_df.iloc[0]['Best Alpha']}`, `beta={config_df.iloc[0]['Best Beta']}`, `gamma={config_df.iloc[0]['Best Gamma']}`
- Width policy: `avg_width={config_df.iloc[0]['Avg Width']}`, `top1_width_match={config_df.iloc[0]['Top1 Width Match (%)']}%`
- Subtask policy: `action_diversity={config_df.iloc[0]['Subtask Diversity']}`

## Canary Delta at Recommended Stage

- Quality delta: `{config_df.iloc[0]['Quality Delta (%)']}%`
- Cost delta: `{config_df.iloc[0]['Cost Delta (%)']}%`
- P95 latency delta: `{config_df.iloc[0]['P95 Latency Delta (%)']}%`
- Fallback delta: `{config_df.iloc[0]['Fallback Delta (%)']}%`

## Reproducibility

- Snapshot rows: `{config_df.iloc[0]['Snapshot Rows']}`
- Key artifacts:
  - `tab_training_snapshot.csv`
  - `tab_eval_policy_ablation.csv`
  - `tab_eval_policy_reward_sweep.csv`
  - `tab_width_policy.csv`
  - `tab_subtask_policy.csv`
  - `tab_canary_abtest.csv`
  - `tab_go_nogo.csv`
  - `tab_best_config.csv`
"""
    (output_dir / "best_decision_report.md").write_text(report, encoding="utf-8")
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

