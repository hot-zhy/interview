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

    sessions_df = pd.read_csv(sessions_path)
    rows = []
    # Duration (exclude invalid negative)
    dur = pd.to_numeric(sessions_df["duration_min"], errors="coerce")
    dur = dur[dur > 0]
    avg_dur = dur.mean() if len(dur) > 0 else 0
    rows.append({"Metric": "Avg. Interview Duration", "Value": f"{avg_dur:.1f} min", "95% CI": "—"})
    # Questions
    nq = pd.to_numeric(sessions_df["n_questions"], errors="coerce")
    avg_nq = nq.mean() if len(nq) > 0 else 0
    rows.append({"Metric": "Avg. Questions per Interview", "Value": f"{avg_nq:.1f}", "95% CI": "—"})
    # Placeholders for others (filled by other calc scripts)
    rows.append({"Metric": "Calibration Accuracy", "Value": "—", "95% CI": "—"})
    rows.append({"Metric": "Question Selection Relevance", "Value": "—", "95% CI": "—"})
    rows.append({"Metric": "Evaluation Agreement", "Value": "—", "95% CI": "—"})
    # Uptime from provenance log
    prov_path = data_dir / "evaluation_provenance_log.csv"
    if prov_path.exists():
        prov = pd.read_csv(prov_path)
        total = len(prov)
        fallback = prov["fallback_triggered"].sum() if "fallback_triggered" in prov.columns else 0
        uptime = 100 * (1 - fallback / total) if total > 0 else 100
        rows.append({"Metric": "System Uptime", "Value": f"{uptime:.1f}%", "95% CI": "—"})
    else:
        rows.append({"Metric": "System Uptime", "Value": "—", "95% CI": "—"})
    rows.append({"Metric": "Avg. Response Time", "Value": "—", "95% CI": "—"})
    # Satisfaction
    survey_path = data_dir / "survey_responses.csv"
    if survey_path.exists():
        survey = pd.read_csv(survey_path)
        sat = pd.to_numeric(survey["satisfaction"], errors="coerce")
        avg_sat = sat.mean() if len(sat) > 0 else 0
        rows.append({"Metric": "User Satisfaction", "Value": f"{avg_sat:.1f}/5.0", "95% CI": "—"})
    else:
        rows.append({"Metric": "User Satisfaction", "Value": "—", "95% CI": "—"})
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "tab_system_performance.csv", index=False)
    return True
