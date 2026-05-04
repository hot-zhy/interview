#!/usr/bin/env python3
"""Build baseline quality/cost/latency table by width cohort."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

import pandas as pd
from wideseek_data_utils import load_eval_policy_df, safe_float


def _summarize(df: pd.DataFrame, label: str) -> Dict:
    if df.empty:
        return {
            "Cohort": label,
            "Samples": 0,
            "Avg Quality": "ILLUSTRATIVE",
            "Avg Cost Est.": "ILLUSTRATIVE",
            "P95 Latency(ms)": "ILLUSTRATIVE",
            "Avg Instability": "ILLUSTRATIVE",
        }
    return {
        "Cohort": label,
        "Samples": int(len(df)),
        "Avg Quality": f"{df['overall_score'].mean():.4f}",
        "Avg Cost Est.": f"{df['estimated_cost'].mean():.4f}",
        "P95 Latency(ms)": f"{df['latency_ms'].quantile(0.95):.1f}",
        "Avg Instability": f"{df['instability'].mean():.4f}",
    }


def _cohorts() -> Iterable[tuple[str, int]]:
    return [("width_1", 1), ("width_2", 2), ("width_4", 4), ("width_8", 8)]


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = seed
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    df = load_eval_policy_df(data_dir)
    if df.empty:
        pd.DataFrame(
            [
                {
                    "Cohort": "width_1",
                    "Samples": "ILLUSTRATIVE",
                    "Avg Quality": "ILLUSTRATIVE",
                    "Avg Cost Est.": "ILLUSTRATIVE",
                    "P95 Latency(ms)": "ILLUSTRATIVE",
                    "Avg Instability": "ILLUSTRATIVE",
                }
            ]
        ).to_csv(output_dir / "tab_wideseek_baseline.csv", index=False)
        return False
    df["width_completed"] = df.get("width_completed", 1).fillna(1).astype(int)
    df["overall_score"] = df.get("overall_score", 0.0).apply(safe_float)
    df["latency_ms"] = df.get("latency_ms", 0.0).apply(safe_float)
    df["estimated_cost"] = df.get("estimated_cost", 0.0).apply(safe_float)
    df["instability"] = df.get("instability", 0.0).apply(safe_float)

    rows = []
    for label, width in _cohorts():
        part = df[df["width_completed"] == width]
        rows.append(_summarize(part, label))
    rows.append(_summarize(df, "overall"))

    pd.DataFrame(rows).to_csv(output_dir / "tab_wideseek_baseline.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

