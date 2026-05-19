#!/usr/bin/env python3
"""
Extended evaluation experiments for the AI interview system.

This module complements the core reproduction tables with metrics commonly
reported in recent AI interview and automated assessment papers:

- system-vs-human scoring validity
- human inter-rater reliability
- signed scoring bias
- ability/session subgroup diagnostics
- user-experience stratification
- chapter and difficulty diagnostics
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


DIMS = ["correctness", "depth", "clarity", "practicality", "tradeoffs", "overall_score"]


def _safe_float(value, default=np.nan):
    try:
        return float(value)
    except Exception:
        return default


def _pearson(x: pd.Series, y: pd.Series) -> float:
    x = pd.to_numeric(x, errors="coerce")
    y = pd.to_numeric(y, errors="coerce")
    mask = x.notna() & y.notna()
    if mask.sum() < 3 or x[mask].nunique() < 2 or y[mask].nunique() < 2:
        return np.nan
    return float(np.corrcoef(x[mask], y[mask])[0, 1])


def _spearman(x: pd.Series, y: pd.Series) -> float:
    return _pearson(x.rank(method="average"), y.rank(method="average"))


def _icc_1k(long_df: pd.DataFrame, target_col: str, rater_col: str, score_col: str) -> float:
    """One-way average-measures ICC, robust enough for balanced 2-rater data."""
    pivot = long_df.pivot_table(index=target_col, columns=rater_col, values=score_col, aggfunc="mean")
    pivot = pivot.dropna(axis=0, how="any")
    n, k = pivot.shape
    if n < 2 or k < 2:
        return np.nan
    values = pivot.to_numpy(dtype=float)
    grand = values.mean()
    row_means = values.mean(axis=1)
    ms_between = k * np.square(row_means - grand).sum() / (n - 1)
    ms_within = np.square(values - row_means[:, None]).sum() / (n * (k - 1))
    denom = ms_between
    if denom == 0:
        return np.nan
    return float((ms_between - ms_within) / ms_between)


def _bucket_ability(value) -> str:
    value = _safe_float(value)
    if np.isnan(value):
        return "Unknown"
    if value <= 2:
        return "Low"
    if value <= 3:
        return "Medium"
    return "High"


def _bucket_duration(value) -> str:
    value = _safe_float(value)
    if np.isnan(value):
        return "Unknown"
    if value < 45:
        return "<45 min"
    if value <= 60:
        return "45-60 min"
    return ">60 min"


def _bucket_questions(value) -> str:
    value = _safe_float(value)
    if np.isnan(value):
        return "Unknown"
    if value <= 6:
        return "<=6"
    if value <= 9:
        return "7-9"
    return ">=10"


def _format_pct(value: float) -> str:
    return "NA" if pd.isna(value) else f"{100 * value:.1f}"


def _format_num(value: float, digits: int = 3) -> str:
    return "NA" if pd.isna(value) else f"{value:.{digits}f}"


def _load_overlap(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    eval_df = pd.read_csv(data_dir / "evaluations.csv")
    human_df = pd.read_csv(data_dir / "human_evaluations.csv")
    human_avg = human_df.groupby("response_id")[DIMS].mean().reset_index()
    merged = eval_df.merge(
        human_avg,
        left_on="asked_question_id",
        right_on="response_id",
        how="inner",
        suffixes=("_sys", "_human"),
    )
    return eval_df, human_df, merged


def _score_validity(data_dir: Path, output_dir: Path) -> bool:
    eval_df, human_df, merged = _load_overlap(data_dir)
    rows = []
    for dim in DIMS:
        sys_col = f"{dim}_sys"
        human_col = f"{dim}_human"
        diff = pd.to_numeric(merged[sys_col], errors="coerce") - pd.to_numeric(merged[human_col], errors="coerce")
        abs_diff = diff.abs()
        rows.append({
            "Dimension": dim,
            "Overlap N": int(diff.notna().sum()),
            "MAE": _format_num(abs_diff.mean()),
            "RMSE": _format_num(np.sqrt(np.square(diff).mean())),
            "Mean Signed Error": _format_num(diff.mean()),
            "Pearson r": _format_num(_pearson(merged[sys_col], merged[human_col])),
            "Spearman rho": _format_num(_spearman(merged[sys_col], merged[human_col])),
            "Exact@0.10 (%)": _format_pct((abs_diff <= 0.10).mean()),
            "Within@0.20 (%)": _format_pct((abs_diff <= 0.20).mean()),
        })
    pd.DataFrame(rows).to_csv(output_dir / "tab_score_validity.csv", index=False)

    rel_rows = []
    for dim in DIMS:
        rel_rows.append({
            "Dimension": dim,
            "Human Ratings": int(human_df[dim].notna().sum()),
            "Responses": int(human_df["response_id"].nunique()),
            "Raters": int(human_df["evaluator_id"].nunique()),
            "ICC(1,k)": _format_num(_icc_1k(human_df, "response_id", "evaluator_id", dim)),
            "Human SD": _format_num(pd.to_numeric(human_df[dim], errors="coerce").std()),
        })
    pd.DataFrame(rel_rows).to_csv(output_dir / "tab_human_reliability.csv", index=False)

    bias_rows = []
    for dim in DIMS:
        sys_col = f"{dim}_sys"
        human_col = f"{dim}_human"
        diff = pd.to_numeric(merged[sys_col], errors="coerce") - pd.to_numeric(merged[human_col], errors="coerce")
        bias_rows.append({
            "Dimension": dim,
            "System Mean": _format_num(pd.to_numeric(merged[sys_col], errors="coerce").mean()),
            "Human Mean": _format_num(pd.to_numeric(merged[human_col], errors="coerce").mean()),
            "Mean Signed Error": _format_num(diff.mean()),
            "Over-Score Rate (%)": _format_pct((diff > 0.10).mean()),
            "Under-Score Rate (%)": _format_pct((diff < -0.10).mean()),
        })
    pd.DataFrame(bias_rows).to_csv(output_dir / "tab_scoring_bias.csv", index=False)
    return True


def _fairness_and_ux(data_dir: Path, output_dir: Path) -> bool:
    sessions = pd.read_csv(data_dir / "sessions.csv")
    eval_df = pd.read_csv(data_dir / "evaluations.csv")
    participants = pd.read_csv(data_dir / "participants.csv") if (data_dir / "participants.csv").exists() else pd.DataFrame()
    ability = pd.read_csv(data_dir / "ability_labels.csv") if (data_dir / "ability_labels.csv").exists() else pd.DataFrame()
    survey = pd.read_csv(data_dir / "survey_responses.csv") if (data_dir / "survey_responses.csv").exists() else pd.DataFrame()

    session_scores = eval_df.groupby("session_id")["overall_score"].mean().rename("avg_system_score").reset_index()
    base = sessions.merge(session_scores, on="session_id", how="left")
    if not participants.empty:
        base = base.merge(participants, on="participant_id", how="left")
    if not ability.empty:
        base = base.merge(ability[["session_id", "ability_label"]], on="session_id", how="left")
    if not survey.empty:
        base = base.merge(survey, on="session_id", how="left")
    base["ability_bucket"] = base["ability_label"].apply(_bucket_ability) if "ability_label" in base else "Unknown"
    base["duration_bucket"] = base["duration_min"].apply(_bucket_duration)
    base["question_bucket"] = base["n_questions"].apply(_bucket_questions)

    rows = []
    for group_col in ["ability_bucket", "track", "resume_available"]:
        if group_col not in base.columns:
            continue
        for group, sub in base.groupby(group_col, dropna=False):
            rows.append({
                "Group Type": group_col,
                "Group": str(group),
                "Sessions": len(sub),
                "Avg System Score": _format_num(pd.to_numeric(sub["avg_system_score"], errors="coerce").mean()),
                "Avg Satisfaction": _format_num(pd.to_numeric(sub.get("satisfaction"), errors="coerce").mean() if "satisfaction" in sub else np.nan),
                "Avg Duration Min": _format_num(pd.to_numeric(sub["duration_min"], errors="coerce").mean(), 1),
                "Completion Rate (%)": _format_pct((sub["termination_reason"].astype(str) == "completed").mean() if "termination_reason" in sub else np.nan),
            })
    pd.DataFrame(rows).to_csv(output_dir / "tab_subgroup_diagnostics.csv", index=False)

    ux_rows = []
    for group_col in ["duration_bucket", "question_bucket", "ability_bucket"]:
        for group, sub in base.groupby(group_col, dropna=False):
            ux_rows.append({
                "Segment": group_col,
                "Group": str(group),
                "Sessions": len(sub),
                "Avg Satisfaction": _format_num(pd.to_numeric(sub.get("satisfaction"), errors="coerce").mean() if "satisfaction" in sub else np.nan),
                "Avg System Score": _format_num(pd.to_numeric(sub["avg_system_score"], errors="coerce").mean()),
                "Avg Questions": _format_num(pd.to_numeric(sub["n_questions"], errors="coerce").mean(), 1),
                "Avg Duration Min": _format_num(pd.to_numeric(sub["duration_min"], errors="coerce").mean(), 1),
            })
    corr_rows = []
    if "satisfaction" in base:
        for col in ["duration_min", "n_questions", "avg_system_score"]:
            corr_rows.append({
                "Segment": "correlation",
                "Group": f"satisfaction_vs_{col}",
                "Sessions": int(base[["satisfaction", col]].dropna().shape[0]),
                "Avg Satisfaction": "NA",
                "Avg System Score": "NA",
                "Avg Questions": "NA",
                "Avg Duration Min": _format_num(_pearson(base["satisfaction"], base[col])),
            })
    pd.DataFrame(ux_rows + corr_rows).to_csv(output_dir / "tab_user_experience_segments.csv", index=False)
    return True


def _question_diagnostics(data_dir: Path, output_dir: Path) -> bool:
    asked = pd.read_csv(data_dir / "asked_questions.csv")
    eval_df = pd.read_csv(data_dir / "evaluations.csv")
    missing = pd.read_csv(data_dir / "missing_concepts.csv") if (data_dir / "missing_concepts.csv").exists() else pd.DataFrame()
    eval_by_question = (
        eval_df[["session_id", "question_id", "overall_score", "correctness", "depth", "clarity"]]
        .groupby(["session_id", "question_id"], as_index=False)
        .mean(numeric_only=True)
    )
    merged = asked.merge(
        eval_by_question,
        on=["session_id", "question_id"],
        how="left",
    )

    rows = []
    for chapter, sub in merged.groupby("chapter", dropna=False):
        rows.append({
            "Chapter": str(chapter),
            "Asked Count": len(sub),
            "Sessions Covered": int(sub["session_id"].nunique()),
            "Avg Difficulty": _format_num(pd.to_numeric(sub["difficulty"], errors="coerce").mean(), 2),
            "Avg Overall": _format_num(pd.to_numeric(sub["overall_score"], errors="coerce").mean()),
            "Avg Correctness": _format_num(pd.to_numeric(sub["correctness"], errors="coerce").mean()),
            "Avg Depth": _format_num(pd.to_numeric(sub["depth"], errors="coerce").mean()),
            "Avg Clarity": _format_num(pd.to_numeric(sub["clarity"], errors="coerce").mean()),
        })
    pd.DataFrame(rows).sort_values(["Asked Count", "Chapter"], ascending=[False, True]).to_csv(
        output_dir / "tab_chapter_diagnostics.csv",
        index=False,
    )

    diff_rows = []
    for difficulty, sub in merged.groupby("difficulty", dropna=False):
        diff_rows.append({
            "Difficulty": difficulty,
            "Asked Count": len(sub),
            "Avg Overall": _format_num(pd.to_numeric(sub["overall_score"], errors="coerce").mean()),
            "Avg Correctness": _format_num(pd.to_numeric(sub["correctness"], errors="coerce").mean()),
            "Avg Depth": _format_num(pd.to_numeric(sub["depth"], errors="coerce").mean()),
        })
    pd.DataFrame(diff_rows).sort_values("Difficulty").to_csv(output_dir / "tab_difficulty_curve.csv", index=False)

    if not missing.empty and "chapter" in missing.columns:
        miss_rows = []
        for chapter, sub in missing.groupby("chapter", dropna=False):
            miss_rows.append({
                "Chapter": str(chapter),
                "Missing Concepts": len(sub),
                "Queried Within K (%)": _format_pct(pd.to_numeric(sub["queried_within_k"], errors="coerce").mean()),
            })
        pd.DataFrame(miss_rows).sort_values(["Missing Concepts", "Chapter"], ascending=[False, True]).to_csv(
            output_dir / "tab_gap_targeting_by_chapter.csv",
            index=False,
        )
    return True


def run(data_dir: Path, output_dir: Path, seed: int) -> bool:
    data_dir = Path(data_dir)
    output_dir = Path(output_dir)
    required = [
        data_dir / "evaluations.csv",
        data_dir / "human_evaluations.csv",
        data_dir / "sessions.csv",
        data_dir / "asked_questions.csv",
    ]
    if not all(path.exists() for path in required):
        return False

    _score_validity(data_dir, output_dir)
    _fairness_and_ux(data_dir, output_dir)
    _question_diagnostics(data_dir, output_dir)
    return True
