"""Shared data loaders for WideSeek-style offline training/evaluation."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

import pandas as pd


def safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def safe_int(v, default: int = 0) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _stable_bucket(key: str, mod: int) -> int:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % max(mod, 1)


def add_split_column(df: pd.DataFrame, session_col: str = "session_id") -> pd.DataFrame:
    """Add deterministic train/val/test split by session id hash."""
    out = df.copy()
    labels = []
    for sid in out.get(session_col, pd.Series([0] * len(out))):
        b = _stable_bucket(str(sid), 100)
        if b < 70:
            labels.append("train")
        elif b < 85:
            labels.append("val")
        else:
            labels.append("test")
    out["split"] = labels
    return out


def derive_width_from_row(row: pd.Series) -> int:
    prov = str(row.get("provenance", "rule")).strip().lower()
    score = safe_float(row.get("overall_score", 0.0))
    if prov == "rule":
        return 1
    if prov == "llm":
        return 2 if score < 0.45 else 4
    if prov == "hybrid":
        return 4 if score < 0.5 else 8
    return 1


def derive_action_from_width(width: int) -> str:
    w = int(max(1, width))
    if w <= 1:
        return "rule_only"
    if w == 2:
        return "llm_single"
    return "llm_multi"


def estimate_cost_from_width(width: int) -> float:
    w = float(max(1, int(width)))
    return round(0.03 + 0.07 * max(0.0, (w - 1.0) / 3.0), 4)


def estimate_latency_from_width(width: int) -> float:
    return float(850 + 320 * int(max(1, width)))


def estimate_instability_from_width(width: int) -> float:
    return round(min(0.6, 0.03 * int(max(1, width))), 4)


def parse_missing_count(v) -> int:
    if v is None:
        return 0
    s = str(v).strip()
    if not s or s == "[]":
        return 0
    # Raw CSV stores as JSON-like string; this robustly approximates count.
    return max(1, s.count("要点"))


def load_eval_policy_df(data_dir: Path) -> pd.DataFrame:
    """Load eval trajectory; bootstrap from evaluations when missing."""
    path = data_dir / "eval_policy_trajectory.csv"
    if path.exists():
        df = pd.read_csv(path)
        if not df.empty:
            return df

    eval_path = data_dir / "evaluations.csv"
    if not eval_path.exists():
        return pd.DataFrame()
    eval_df = pd.read_csv(eval_path)
    if eval_df.empty:
        return pd.DataFrame()

    proxy = pd.DataFrame()
    proxy["session_id"] = eval_df.get("session_id", 0)
    proxy["round"] = eval_df.get("round", 1)
    proxy["overall_score"] = eval_df.get("overall_score", 0.0).apply(safe_float)
    proxy["provenance"] = eval_df.get("provenance", "rule")
    proxy["missing_points_count"] = eval_df.get("missing_points", "").apply(parse_missing_count)
    proxy["width_completed"] = eval_df.apply(derive_width_from_row, axis=1)
    proxy["width_requested"] = proxy["width_completed"]
    proxy["action"] = proxy["width_completed"].apply(derive_action_from_width)
    proxy["latency_ms"] = proxy["width_completed"].apply(estimate_latency_from_width)
    proxy["estimated_cost"] = proxy["width_completed"].apply(estimate_cost_from_width)
    proxy["instability"] = proxy["width_completed"].apply(estimate_instability_from_width)
    proxy["answer_length"] = eval_df.get("overall_score", 0.0).apply(lambda s: int(80 + 400 * safe_float(s)))
    proxy["fallback_count"] = 0
    proxy["llm_calls_used"] = proxy["action"].apply(lambda a: 0 if a == "rule_only" else 1)
    proxy["multi_judge_used"] = proxy["action"].apply(lambda a: 1 if a == "llm_multi" else 0)
    proxy = proxy.sort_values(["session_id", "round"]).reset_index(drop=True)
    proxy["recent_avg_score"] = (
        proxy.groupby("session_id")["overall_score"].transform(lambda s: s.rolling(3, min_periods=1).mean())
    )
    proxy["reward"] = (
        proxy["overall_score"]
        - 0.15 * proxy["estimated_cost"]
        - 0.10 * (proxy["latency_ms"] / max(proxy["latency_ms"].quantile(0.95), 1.0)).clip(0.0, 1.0)
        - 0.08 * proxy["instability"].clip(0.0, 1.0)
    )
    return proxy


def snapshot_manifest(df: pd.DataFrame) -> dict:
    splits = add_split_column(df)
    counts = splits.groupby("split", as_index=False).size()
    by_split = {str(r["split"]): int(r["size"]) for _, r in counts.iterrows()}
    session_counts = (
        splits.groupby(["split", "session_id"], as_index=False).size().groupby("split", as_index=False)["size"].count()
    )
    sessions_by_split = {str(r["split"]): int(r["size"]) for _, r in session_counts.iterrows()}
    return {
        "rows": int(len(df)),
        "sessions": int(splits["session_id"].nunique()) if "session_id" in splits.columns else 0,
        "rows_by_split": by_split,
        "sessions_by_split": sessions_by_split,
    }

