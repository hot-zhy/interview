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

    return False
