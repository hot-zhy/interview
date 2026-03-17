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


def _compute_calibration_accuracy(asked_df, ability_df, sessions_df=None):
    """MAE between normalized final difficulty and ability label (1-5 -> 0-1)."""
    final_d = asked_df.sort_values(["session_id", "round"]).groupby("session_id").last().reset_index()
    final_d = final_d[["session_id", "difficulty"]].rename(columns={"difficulty": "final_difficulty"})
    final_d["d_norm"] = (final_d["final_difficulty"] - 1) / 4.0
    ab = ability_df.copy()
    ab["a"] = pd.to_numeric(ab["ability_label"], errors="coerce")
    ab["a_norm"] = (ab["a"] - 1) / 4.0
    if "session_id" in ab.columns:
        ab = ab[["session_id", "a_norm"]].drop_duplicates("session_id")
    elif "participant_id" in ab.columns and sessions_df is not None:
        ab = ab.merge(sessions_df[["session_id", "participant_id"]], on="participant_id")[["session_id", "a_norm"]]
    else:
        return None, None
    merged = final_d.merge(ab, on="session_id", how="inner")
    if merged.empty:
        return None, None
    mae = np.abs(merged["d_norm"] - merged["a_norm"]).mean()
    acc_pct = max(0, 100 * (1 - mae))
    return mae, acc_pct


def _compute_convergence(asked_df):
    """First round where |d_t - d_{t-1}| < 0.5 for 2 consecutive rounds."""
    conv_rounds = []
    for sid, grp in asked_df.sort_values(["session_id", "round"]).groupby("session_id"):
        d = grp["difficulty"].values
        r = grp["round"].values
        if len(d) < 3:
            conv_rounds.append(len(d))
            continue
        for i in range(2, len(d)):
            if abs(d[i] - d[i - 1]) < 0.5 and abs(d[i - 1] - d[i - 2]) < 0.5:
                conv_rounds.append(int(r[i]))
                break
        else:
            conv_rounds.append(len(d))
    return np.mean(conv_rounds) if conv_rounds else None


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    ability_path = data_dir / "ability_labels.csv"
    asked_path = data_dir / "asked_questions.csv"
    eval_path = data_dir / "evaluations.csv"

    if not all(p.exists() for p in [ability_path, asked_path, eval_path]):
        placeholder = pd.DataFrame({
            "Ability Level": ["Low (0.0-0.4)", "Medium (0.4-0.7)", "High (0.7-1.0)", "Overall"],
            "Calibration Accuracy (%)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
            "Avg. Convergence (questions)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
            "Stability Rate (%)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
        })
        placeholder.to_csv(output_dir / "tab_calibration.csv", index=False)
        return False

    ability_df = pd.read_csv(ability_path)
    asked_df = pd.read_csv(asked_path)
    eval_df = pd.read_csv(eval_path)
    sessions_df = pd.read_csv(data_dir / "sessions.csv") if (data_dir / "sessions.csv").exists() else None

    mae, acc_pct = _compute_calibration_accuracy(asked_df, ability_df, sessions_df)
    conv = _compute_convergence(asked_df)

    # Bucket by ability level
    ab = ability_df.copy()
    sid_col = "session_id" if "session_id" in ab.columns else "participant_id"
    ab["a"] = pd.to_numeric(ab["ability_label"], errors="coerce")
    low = ab[ab["a"] <= 2.5]
    mid = ab[(ab["a"] > 2.5) & (ab["a"] <= 3.5)]
    high = ab[ab["a"] > 3.5]
    rows = []
    for label, sub in [("Low (0.0-0.4)", low), ("Medium (0.4-0.7)", mid), ("High (0.7-1.0)", high)]:
        if sub.empty:
            rows.append({"Ability Level": label, "Calibration Accuracy (%)": "—", "Avg. Convergence (questions)": "—", "Stability Rate (%)": "—"})
        else:
            asked_sub = asked_df[asked_df["session_id"].isin(sub[sid_col])] if sid_col == "session_id" else asked_df
            if sid_col == "participant_id":
                sess_df = pd.read_csv(data_dir / "sessions.csv") if (data_dir / "sessions.csv").exists() else pd.DataFrame()
                if not sess_df.empty:
                    sess_ids = sess_df.merge(sub, on="participant_id")["session_id"]
                    asked_sub = asked_df[asked_df["session_id"].isin(sess_ids)]
            _, ap = _compute_calibration_accuracy(asked_sub, sub, sessions_df)
            rows.append({"Ability Level": label, "Calibration Accuracy (%)": f"{ap:.1f}" if ap else "—", "Avg. Convergence (questions)": f"{conv:.1f}" if conv else "—", "Stability Rate (%)": "—"})
    rows.append({"Ability Level": "Overall", "Calibration Accuracy (%)": f"{acc_pct:.1f}" if acc_pct else "—", "Avg. Convergence (questions)": f"{conv:.1f}" if conv else "—", "Stability Rate (%)": "—"})
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "tab_calibration.csv", index=False)
    return True
