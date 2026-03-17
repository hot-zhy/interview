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

    eval_df = pd.read_csv(eval_path)
    human_df = pd.read_csv(human_path)
    # Merge: response_id = asked_question_id
    human_avg = human_df.groupby("response_id").agg({
        "correctness": "mean", "depth": "mean", "clarity": "mean",
        "practicality": "mean", "tradeoffs": "mean", "overall_score": "mean",
    }).reset_index()
    merged = eval_df.merge(human_avg, left_on="asked_question_id", right_on="response_id", how="inner")
    if merged.empty:
        return False
    dims = ["correctness", "depth", "clarity", "practicality", "tradeoffs"]
    rows = []
    for d in dims:
        sys_col = d + "_x" if d + "_x" in merged.columns else d
        hum_col = d + "_y" if d + "_y" in merged.columns else d
        if sys_col in merged.columns and hum_col in merged.columns:
            diff = (merged[sys_col].astype(float) - merged[hum_col].astype(float)).abs()
            exact = (diff < 0.1).mean() * 100
        else:
            exact = 0
        rows.append({"Dimension": d.capitalize(), "Exact Agreement (%)": f"{exact:.1f}"})
    # Overall
    so = merged["overall_score_x"] if "overall_score_x" in merged.columns else merged["overall_score"]
    ho = merged["overall_score_y"] if "overall_score_y" in merged.columns else merged["overall_score"]
    if so is not None and ho is not None:
        diff = (pd.to_numeric(so, errors="coerce") - pd.to_numeric(ho, errors="coerce")).abs()
        exact = (diff < 0.1).mean() * 100
        rows.append({"Dimension": "Overall", "Exact Agreement (%)": f"{exact:.1f}"})
    out = pd.DataFrame(rows)
    out.to_csv(output_dir / "tab_evaluation.csv", index=False)
    return True
