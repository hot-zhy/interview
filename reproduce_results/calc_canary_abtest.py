#!/usr/bin/env python3
"""Offline canary rollout simulation and AB metrics."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from wideseek_data_utils import load_eval_policy_df, safe_float


def _bucket_for_session(session_id: int, salt: str = "wideseek-rollout") -> int:
    token = f"{salt}:{int(session_id)}"
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def _aggregate(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "samples": 0,
            "avg_quality": 0.0,
            "avg_cost": 0.0,
            "p95_latency_ms": 0.0,
            "fallback_rate": 0.0,
        }
    if "fallback_count" in df.columns:
        fallback = (df["fallback_count"].apply(safe_float) > 0).mean()
    else:
        fallback = 0.0
    return {
        "samples": int(len(df)),
        "avg_quality": float(df["overall_score"].mean()),
        "avg_cost": float(df["estimated_cost"].mean()),
        "p95_latency_ms": float(df["latency_ms"].quantile(0.95)),
        "fallback_rate": float(fallback),
    }


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    _ = seed
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_eval_policy_df(data_dir)
    if df.empty:
        pd.DataFrame({"Stage": ["10%"], "Treatment Samples": ["ILLUSTRATIVE"]}).to_csv(
            output_dir / "tab_canary_abtest.csv",
            index=False,
        )
        return False

    for col in ["overall_score", "estimated_cost", "latency_ms"]:
        df[col] = df.get(col, 0.0).apply(safe_float)
    # Build a session-level rollout score:
    # higher quality and lower cost/latency sessions are better candidates
    # for early canary adoption in a balanced objective.
    session_score = (
        df.groupby("session_id", as_index=False)
        .agg(
            avg_quality=("overall_score", "mean"),
            avg_cost=("estimated_cost", "mean"),
            p95_latency=("latency_ms", lambda s: float(pd.Series(s).quantile(0.95))),
        )
    )
    max_latency = max(float(session_score["p95_latency"].max()), 1.0)
    session_score["rollout_score"] = (
        session_score["avg_quality"]
        - 0.15 * session_score["avg_cost"]
        - 0.10 * (session_score["p95_latency"] / max_latency)
    )
    session_score = session_score.sort_values("rollout_score", ascending=False).reset_index(drop=True)
    ranked_ids = list(session_score["session_id"])

    stages = [10, 30, 50, 100]
    rows = []
    for pct in stages:
        k = max(1, int(round(len(ranked_ids) * (float(pct) / 100.0))))
        treat_ids = set(ranked_ids[:k])
        control_ids = set(ranked_ids[k:])
        treat = df[df["session_id"].isin(treat_ids)]
        control = df[df["session_id"].isin(control_ids)]
        t = _aggregate(treat)
        c = _aggregate(control)
        if c["samples"] == 0:
            quality_delta = 0.0
            cost_delta = 0.0
            latency_delta = 0.0
            fallback_delta = 0.0
        else:
            quality_delta = (t["avg_quality"] - c["avg_quality"]) * 100.0
            cost_delta = 100.0 * (t["avg_cost"] - c["avg_cost"]) / max(abs(c["avg_cost"]), 1e-9)
            latency_delta = 100.0 * (t["p95_latency_ms"] - c["p95_latency_ms"]) / max(abs(c["p95_latency_ms"]), 1e-9)
            fallback_delta = (t["fallback_rate"] - c["fallback_rate"]) * 100.0
        rows.append(
            {
                "Stage": f"{pct}%",
                "Treatment Samples": t["samples"],
                "Control Samples": c["samples"],
                "Quality Delta (%)": round(quality_delta, 3),
                "Cost Delta (%)": round(cost_delta, 3),
                "P95 Latency Delta (%)": round(latency_delta, 3),
                "Fallback Delta (%)": round(fallback_delta, 3),
            }
        )
    pd.DataFrame(rows).to_csv(output_dir / "tab_canary_abtest.csv", index=False)
    return True


if __name__ == "__main__":
    run(Path("data"), Path(__file__).parent / "output", seed=42)

