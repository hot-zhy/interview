#!/usr/bin/env python3
"""
Recompute interview outcome distribution by termination type.

Inputs:
  - termination_log.csv: session_id, reason, rounds
  - sessions.csv: session_id

Output: output/tab_interview_outcomes.csv
"""

import pandas as pd
from pathlib import Path


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    term_path = data_dir / "termination_log.csv"
    sessions_path = data_dir / "sessions.csv"

    if not term_path.exists() or not sessions_path.exists():
        placeholder = pd.DataFrame({
            "Termination Type": ["Early (Excellent)", "Early (Poor)", "Normal", "Forced (Max Rounds)", "Total"],
            "Count": ["ILLUSTRATIVE"] * 5,
            "Percentage": ["ILLUSTRATIVE"] * 5,
            "Avg. Rounds": ["ILLUSTRATIVE"] * 5,
        })
        placeholder.to_csv(output_dir / "tab_interview_outcomes.csv", index=False)
        return False

    return False
