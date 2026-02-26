#!/usr/bin/env python3
"""
Recompute system performance: duration, uptime, satisfaction, response time.

Inputs:
  - sessions.csv: duration_min, n_questions
  - evaluation_provenance_log.csv: provenance, fallback_triggered
  - evaluation_timing_log.csv: mode, latency_sec
  - survey_responses.csv: satisfaction

Output: output/tab_system_performance.csv
"""

import pandas as pd
from pathlib import Path


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    sessions_path = data_dir / "sessions.csv"

    if not sessions_path.exists():
        placeholder = pd.DataFrame({
            "Metric": [
                "Avg. Interview Duration",
                "Avg. Questions per Interview",
                "Calibration Accuracy",
                "Question Selection Relevance",
                "Evaluation Agreement",
                "System Uptime",
                "Avg. Response Time",
                "User Satisfaction",
            ],
            "Value": ["ILLUSTRATIVE"] * 8,
            "95% CI": ["ILLUSTRATIVE"] * 8,
        })
        placeholder.to_csv(output_dir / "tab_system_performance.csv", index=False)
        return False

    return False
