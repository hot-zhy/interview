#!/usr/bin/env python3
"""
Recompute evaluation agreement, κ, ICC, fallback rate.

Inputs:
  - evaluations.csv: session_id, round, provenance (rule/llm/hybrid)
  - human_evaluations.csv: response_id, evaluator_id, dim_scores
  - evaluation_provenance_log.csv: eval_id, provenance, fallback_triggered

Output: output/tab_evaluation.csv, tab_evaluation_reliability.csv
"""

import pandas as pd
from pathlib import Path


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    eval_path = data_dir / "evaluations.csv"
    human_path = data_dir / "human_evaluations.csv"

    if not eval_path.exists() or not human_path.exists():
        placeholder = pd.DataFrame({
            "Dimension": ["Correctness", "Depth", "Clarity", "Practicality", "Tradeoffs", "Overall"],
            "Rule-Based (%)": ["ILLUSTRATIVE"] * 6,
            "LLM-Enhanced (%)": ["ILLUSTRATIVE"] * 6,
            "Hybrid (%)": ["ILLUSTRATIVE"] * 6,
        })
        placeholder.to_csv(output_dir / "tab_evaluation.csv", index=False)
        return False

    return False
