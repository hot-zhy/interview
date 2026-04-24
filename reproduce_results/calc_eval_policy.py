#!/usr/bin/env python3
"""Train and evaluate contextual-bandit policy for evaluation routing."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from eval_policy_utils import (
    build_eval_samples,
    evaluate_eval_policy,
    persist_eval_policy,
    train_linucb_eval,
)


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = seed
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    samples = build_eval_samples(data_dir)
    if not samples:
        placeholder = pd.DataFrame(
            {
                "Strategy": ["Eval Routing Contextual Bandit"],
                "Train Samples": ["ILLUSTRATIVE"],
                "Avg Reward": ["ILLUSTRATIVE"],
                "Avg Regret": ["ILLUSTRATIVE"],
                "Top1 Action Match (%)": ["ILLUSTRATIVE"],
            }
        )
        placeholder.to_csv(output_dir / "tab_eval_policy.csv", index=False)
        return False

    payload = train_linucb_eval(samples, l2=1.0)
    metrics = evaluate_eval_policy(payload, samples, alpha=0.25)
    artifact = persist_eval_policy(output_dir, payload)

    pd.DataFrame(
        {
            "Strategy": ["Eval Routing Contextual Bandit"],
            "Train Samples": [int(payload.get("training_rows", 0))],
            "Avg Reward": [f"{metrics['avg_reward']:.4f}"],
            "Avg Regret": [f"{metrics['avg_regret']:.4f}"],
            "Top1 Action Match (%)": [f"{metrics['top1_action_match']:.1f}"],
            "Policy Artifact": [artifact.name],
        }
    ).to_csv(output_dir / "tab_eval_policy.csv", index=False)

    pd.DataFrame(
        [
            {
                "session_id": s.session_id,
                "round": s.round_number,
                "action": s.action,
                "reward": round(float(s.reward), 5),
                "feature_dim": len(s.features),
            }
            for s in samples
        ]
    ).to_csv(output_dir / "eval_policy_training_samples.csv", index=False)
    return True
