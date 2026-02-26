#!/usr/bin/env python3
"""
Recompute calibration accuracy, convergence, and stability metrics.

Inputs (from data_dir):
  - ability_labels.csv: participant_id, ability_label, source
  - asked_questions.csv: session_id, round, question_id, difficulty
  - evaluations.csv: session_id, round, overall_score

Output: output/tab_calibration.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path


def _compute_calibration_accuracy(difficulty_df, ability_df):
    """MAE between normalized difficulty and ability label."""
    # Merge by session/participant; normalize both to [0,1]
    # Return per-interview accuracy, then aggregate
    raise NotImplementedError("Requires ability_labels.csv and asked_questions.csv")


def _compute_convergence(asked_df):
    """First round where |d_t - d_{t-1}| < 0.5 for 2 consecutive rounds."""
    raise NotImplementedError("Requires asked_questions.csv")


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    ability_path = data_dir / "ability_labels.csv"
    asked_path = data_dir / "asked_questions.csv"
    eval_path = data_dir / "evaluations.csv"

    if not all(p.exists() for p in [ability_path, asked_path, eval_path]):
        # Placeholder
        placeholder = pd.DataFrame({
            "Ability Level": ["Low (0.0-0.4)", "Medium (0.4-0.7)", "High (0.7-1.0)", "Overall"],
            "Calibration Accuracy (%)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
            "Avg. Convergence (questions)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
            "Stability Rate (%)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
        })
        placeholder.to_csv(output_dir / "tab_calibration.csv", index=False)
        return False

    # TODO: Implement full computation when data schema is confirmed
    return False
