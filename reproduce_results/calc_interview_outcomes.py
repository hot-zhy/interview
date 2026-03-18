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

    term_df = pd.read_csv(term_path)
    sessions_df = pd.read_csv(sessions_path)
    # Map reason to category
    def cat(r):
        r = str(r).lower()
        if "completed" in r or "normal" in r:
            return "Normal"
        if "active" in r or "cancelled" in r:
            return "Forced (Max Rounds)"
        return "Normal"
    term_df["cat"] = term_df["reason"].apply(cat)
    term_df["rounds_num"] = pd.to_numeric(term_df["rounds"], errors="coerce")
    summary = term_df.groupby("cat").agg(count=("session_id", "count"), avg_rounds=("rounds_num", "mean")).reset_index()
    summary = summary.rename(columns={"cat": "Termination Type"})
    total = summary["count"].sum()
    summary["Percentage"] = (100 * summary["count"] / total).round(1).astype(str) + "%"
    summary["Avg. Rounds"] = summary["avg_rounds"].round(1)
    total_row = pd.DataFrame([{"Termination Type": "Total", "count": total, "Percentage": "100%", "Avg. Rounds": term_df["rounds_num"].mean()}])
    out = pd.concat([summary[["Termination Type", "count", "Percentage", "Avg. Rounds"]], total_row], ignore_index=True)
    out = out.rename(columns={"count": "Count"})
    out.to_csv(output_dir / "tab_interview_outcomes.csv", index=False)
    return True
