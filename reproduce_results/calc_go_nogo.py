#!/usr/bin/env python3
"""Apply Go/No-Go gates from canary AB metrics."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = (data_dir, seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    canary_path = output_dir / "tab_canary_abtest.csv"
    if not canary_path.exists():
        pd.DataFrame(
            {
                "Gate": ["go_nogo"],
                "Decision": ["ILLUSTRATIVE"],
                "Reason": ["ILLUSTRATIVE"],
            }
        ).to_csv(output_dir / "tab_go_nogo.csv", index=False)
        return False

    df = pd.read_csv(canary_path)
    if df.empty:
        return False
    rows = []
    for _, row in df.iterrows():
        quality_ok = float(row["Quality Delta (%)"]) >= 3.0
        cost_ok = float(row["Cost Delta (%)"]) <= 10.0
        latency_ok = float(row["P95 Latency Delta (%)"]) <= 15.0
        stability_ok = float(row["Fallback Delta (%)"]) <= 0.0
        rows.append(
            {
                "stage": str(row["Stage"]),
                "quality_ok": quality_ok,
                "cost_ok": cost_ok,
                "latency_ok": latency_ok,
                "stability_ok": stability_ok,
                "quality_delta": float(row["Quality Delta (%)"]),
            }
        )

    passing = [r for r in rows if all([r["quality_ok"], r["cost_ok"], r["latency_ok"], r["stability_ok"]])]
    if passing:
        best = sorted(passing, key=lambda r: r["quality_delta"], reverse=True)[0]
        decision = "GO"
        failed = []
    else:
        best = sorted(rows, key=lambda r: r["quality_delta"], reverse=True)[0]
        decision = "NO_GO"
        failed = []
        if not best["quality_ok"]:
            failed.append("quality")
        if not best["cost_ok"]:
            failed.append("cost")
        if not best["latency_ok"]:
            failed.append("latency")
        if not best["stability_ok"]:
            failed.append("stability")

    pd.DataFrame(
        {
            "Gate": ["go_nogo"],
            "Decision": [decision],
            "Recommended Stage": [best["stage"]],
            "Quality Gate (>=3%)": [best["quality_ok"]],
            "Cost Gate (<=10%)": [best["cost_ok"]],
            "Latency Gate (<=15%)": [best["latency_ok"]],
            "Stability Gate (fallback<=0%)": [best["stability_ok"]],
            "Reason": [",".join(failed) if failed else "all_passed"],
        }
    ).to_csv(output_dir / "tab_go_nogo.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

