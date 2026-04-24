#!/usr/bin/env python3
"""Train and evaluate contextual-bandit selection policy from history data."""

from pathlib import Path

import pandas as pd

from bandit_utils import (
    build_bandit_samples,
    evaluate_policy,
    persist_policy,
    train_linucb,
)


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = build_bandit_samples(data_dir)
    if not samples:
        placeholder = pd.DataFrame(
            {
                "Strategy": ["Contextual Bandit (LinUCB)"],
                "Train Samples": ["ILLUSTRATIVE"],
                "Avg Reward": ["ILLUSTRATIVE"],
                "Avg Regret": ["ILLUSTRATIVE"],
                "Coverage@3 (%)": ["ILLUSTRATIVE"],
                "Ability Error": ["ILLUSTRATIVE"],
                "Cost Violation Rate (%)": ["ILLUSTRATIVE"],
            }
        )
        placeholder.to_csv(output_dir / "tab_bandit_policy.csv", index=False)
        return False

    payload = train_linucb(samples, l2=1.0)
    metrics = evaluate_policy(payload, samples, alpha=0.35)
    artifact = persist_policy(output_dir, payload)

    rows = pd.DataFrame(
        {
            "Strategy": ["Contextual Bandit (LinUCB)"],
            "Train Samples": [int(payload.get("training_rows", 0))],
            "Avg Reward": [f"{metrics['avg_reward']:.4f}"],
            "Avg Regret": [f"{metrics['avg_regret']:.4f}"],
            "Coverage@3 (%)": [f"{metrics['coverage_at_3']:.1f}"],
            "Ability Error": [f"{metrics['ability_error']:.3f}"],
            "Cost Violation Rate (%)": [f"{metrics['cost_violation_rate']:.1f}"],
            "Policy Artifact": [str(artifact.name)],
        }
    )
    rows.to_csv(output_dir / "tab_bandit_policy.csv", index=False)

    sample_rows = pd.DataFrame(
        [
            {
                "session_id": s.session_id,
                "round": s.round_number,
                "chapter": s.chapter,
                "reward": round(float(s.reward), 5),
                "feature_dim": len(s.features),
            }
            for s in samples
        ]
    )
    sample_rows.to_csv(output_dir / "bandit_training_samples.csv", index=False)
    return True
