#!/usr/bin/env python3
"""
Recompute gap targeting, coverage, and personalization metrics.

Inputs:
  - missing_concepts.csv: session_id, round, concept_id, chapter, queried_within_k
  - asked_questions.csv: session_id, round, chapter, priority_used
  - question_bank.csv: track, required_chapters
  - expert_relevance_ratings.csv (optional)

Output: output/tab_selection.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    missing_path = data_dir / "missing_concepts.csv"
    asked_path = data_dir / "asked_questions.csv"

    if not missing_path.exists() or not asked_path.exists():
        placeholder = pd.DataFrame({
            "Strategy": ["Multi-Priority (Ours)", "Random", "Fixed Template", "Difficulty-Only"],
            "Gap Targeting (%)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
            "Coverage (%)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
            "Personalization (%)": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
            "Avg. Relevance Score": ["ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE", "ILLUSTRATIVE"],
        })
        placeholder.to_csv(output_dir / "tab_selection.csv", index=False)
        return False

    missing_df = pd.read_csv(missing_path)
    asked_df = pd.read_csv(asked_path)
    relevance_path = data_dir / "expert_relevance_ratings.csv"
    qbank_path = data_dir / "question_bank.csv"

    # Gap targeting: % of missing concepts queried within k
    hit = missing_df["queried_within_k"].sum()
    total = len(missing_df)
    gap_pct = 100 * hit / total if total > 0 else 0

    # Coverage: % of required chapters covered per session (simplified: chapters asked / all chapters)
    chapters_in_bank = set()
    if qbank_path.exists():
        qb = pd.read_csv(qbank_path)
        chapters_in_bank = set(qb["chapter"].dropna().unique())
    asked_chapters = asked_df.groupby("session_id")["chapter"].apply(lambda x: set(x.dropna().unique())).to_dict()
    if chapters_in_bank:
        cov_pcts = [100 * len(ac & chapters_in_bank) / len(chapters_in_bank) for ac in asked_chapters.values()]
        cov = np.mean(cov_pcts) if cov_pcts else 0
    else:
        cov = 0

    # Personalization / relevance from expert_relevance_ratings
    rel_pct = 0
    if relevance_path.exists():
        rel_df = pd.read_csv(relevance_path)
        rel_pct = 100 * rel_df["relevance"].mean() if "relevance" in rel_df.columns else 0

    out = pd.DataFrame({
        "Strategy": ["Multi-Priority (Ours)", "Random", "Fixed Template", "Difficulty-Only"],
        "Gap Targeting (%)": [f"{gap_pct:.1f}", "—", "—", "—"],
        "Coverage (%)": [f"{cov:.1f}", "—", "—", "—"],
        "Personalization (%)": [f"{rel_pct:.1f}", "—", "—", "—"],
        "Avg. Relevance Score": [f"{rel_pct/100:.2f}", "—", "—", "—"],
    })
    out.to_csv(output_dir / "tab_selection.csv", index=False)

    # Priority distribution
    if "priority_used" in asked_df.columns:
        pri = asked_df["priority_used"].value_counts(normalize=True) * 100
        per_sess = asked_df.groupby(["session_id", "priority_used"]).size().unstack(fill_value=0)
        avg_q = per_sess.mean()
        pri_rows = []
        labels = {"P1": "Missing Chapters", "P2": "Resume Match", "P3": "Weighted Random"}
        for p in ["P1", "P2", "P3"]:
            rate = pri.get(p, 0)
            aq = avg_q.get(p, 0)
            pri_rows.append({"Priority Level": f"Priority {p[-1]} ({labels.get(p, p)})", "Application Rate (%)": f"{rate:.1f}", "Avg. Questions per Interview": f"{aq:.1f}"})
        if pri_rows:
            pd.DataFrame(pri_rows).to_csv(output_dir / "tab_priority_distribution.csv", index=False)

    return True
