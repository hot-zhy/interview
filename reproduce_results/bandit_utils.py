"""Utilities for offline contextual-bandit training and evaluation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class SampleRow:
    session_id: int
    round_number: int
    chapter: str
    reward: float
    features: List[float]


def _estimate_ability(history: List[Tuple[int, float]], default: float = 3.0) -> float:
    if not history:
        return default
    total_w = 0.0
    weighted_sum = 0.0
    for i, (difficulty, score) in enumerate(history):
        w = float(i + 1)
        est = float(difficulty) + (float(score) - 0.5) * 2.0
        est = max(1.0, min(5.0, est))
        total_w += w
        weighted_sum += est * w
    return weighted_sum / total_w if total_w > 0 else default


def _vector(
    ability: float,
    difficulty: float,
    avg_score: float,
    recent_score: float,
    coverage_ratio: float,
    remaining_ratio: float,
    chapter_track_weight: float,
    chapter_seen_ratio: float,
    chapter_score: float,
    chapter_gap: float,
    chapter_resume_match: float,
    chapter_recent_asked: float,
) -> List[float]:
    return [
        1.0,
        max(0.0, min(1.0, (ability - 1.0) / 4.0)),
        max(0.0, min(1.0, (difficulty - 1.0) / 4.0)),
        max(0.0, min(1.0, avg_score)),
        max(0.0, min(1.0, recent_score)),
        max(0.0, min(1.0, coverage_ratio)),
        max(0.0, min(1.0, remaining_ratio)),
        0.0,  # hint_available (not consistently available in exported CSV)
        chapter_track_weight,
        chapter_seen_ratio,
        chapter_score,
        chapter_gap,
        chapter_resume_match,
        chapter_recent_asked,
    ]


def _reward_proxy(
    previous_score: float,
    current_score: float,
    prev_coverage_ratio: float,
    new_coverage_ratio: float,
    llm_used: bool,
    followup_used: bool,
    is_terminal_round: bool = False,
    session_quality: float = 0.0,
) -> float:
    gain = max(0.0, float(current_score) - float(previous_score))
    quality = max(0.0, min(1.0, float(current_score)))
    coverage_gain = max(0.0, float(new_coverage_ratio) - float(prev_coverage_ratio))
    cost = (0.05 if llm_used else 0.0) + (0.03 if followup_used else 0.0)
    reward = 0.40 * gain + 0.25 * quality + 0.20 * coverage_gain - 0.15 * cost
    if is_terminal_round:
        reward += 0.10 * max(0.0, min(1.0, float(session_quality)))
    return reward


def build_bandit_samples(data_dir: Path) -> List[SampleRow]:
    asked_path = data_dir / "asked_questions.csv"
    eval_path = data_dir / "evaluations.csv"
    if not asked_path.exists() or not eval_path.exists():
        return []

    asked = pd.read_csv(asked_path)
    evaluations = pd.read_csv(eval_path)
    merged = asked.merge(
        evaluations[["session_id", "round", "overall_score", "provenance"]],
        on=["session_id", "round"],
        how="left",
    )
    merged = merged.sort_values(["session_id", "round"]).reset_index(drop=True)
    all_chapters = sorted([c for c in merged["chapter"].dropna().unique().tolist() if str(c).strip()])
    n_chapters = max(1, len(all_chapters))

    samples: List[SampleRow] = []
    for sid, group in merged.groupby("session_id"):
        group = group.sort_values("round")
        session_quality = float(group["overall_score"].fillna(0.5).mean()) if not group.empty else 0.5
        score_history: List[Tuple[int, float]] = []
        chapter_counts: Dict[str, int] = {c: 0 for c in all_chapters}
        chapter_scores: Dict[str, List[float]] = {c: [] for c in all_chapters}
        seen: set = set()
        total_rounds = max(int(group["round"].max()), 1)
        prev_score = 0.0

        for _, row in group.iterrows():
            chapter = str(row.get("chapter", "") or "")
            if not chapter:
                continue
            difficulty = float(row.get("difficulty", 3) or 3)
            score = float(row.get("overall_score", prev_score) or prev_score)
            ability = _estimate_ability(score_history, default=difficulty)
            avg_score = float(np.mean([h[1] for h in score_history])) if score_history else 0.5
            recent_vals = [h[1] for h in score_history[-3:]] if score_history else []
            recent_score = float(np.mean(recent_vals)) if recent_vals else avg_score
            prev_cov = len(seen) / n_chapters
            seen.add(chapter)
            new_cov = len(seen) / n_chapters

            chapter_seen_ratio = chapter_counts.get(chapter, 0) / max(1, len(score_history))
            chapter_score = (
                float(np.mean(chapter_scores.get(chapter, [])))
                if chapter_scores.get(chapter)
                else 0.5
            )
            chapter_recent_asked = 1.0 if score_history and group[group["round"] < row["round"]]["chapter"].tail(2).isin([chapter]).any() else 0.0
            llm_used = str(row.get("provenance", "")).lower() in {"llm", "hybrid"}
            followup_used = bool(str(row.get("priority_used", "")).upper().startswith("P1"))

            reward = _reward_proxy(
                previous_score=prev_score,
                current_score=score,
                prev_coverage_ratio=prev_cov,
                new_coverage_ratio=new_cov,
                llm_used=llm_used,
                followup_used=followup_used,
                is_terminal_round=int(row["round"]) == int(total_rounds),
                session_quality=session_quality,
            )

            features = _vector(
                ability=ability,
                difficulty=difficulty,
                avg_score=avg_score,
                recent_score=recent_score,
                coverage_ratio=prev_cov,
                remaining_ratio=max(0.0, 1.0 - (float(row["round"]) / float(total_rounds))),
                chapter_track_weight=1.0 / n_chapters,
                chapter_seen_ratio=chapter_seen_ratio,
                chapter_score=chapter_score,
                chapter_gap=1.0 if chapter_recent_asked == 0.0 and score < 0.65 else 0.0,
                chapter_resume_match=1.0 if str(row.get("priority_used", "")).upper() == "P2" else 0.0,
                chapter_recent_asked=chapter_recent_asked,
            )
            samples.append(
                SampleRow(
                    session_id=int(sid),
                    round_number=int(row["round"]),
                    chapter=chapter,
                    reward=float(reward),
                    features=features,
                )
            )

            chapter_counts[chapter] = chapter_counts.get(chapter, 0) + 1
            chapter_scores.setdefault(chapter, []).append(score)
            score_history.append((int(difficulty), float(score)))
            prev_score = score

    return samples


def train_linucb(samples: List[SampleRow], l2: float = 1.0) -> Dict:
    if not samples:
        return {"feature_dim": 0, "models": {}, "training_rows": 0}

    d = len(samples[0].features)
    by_chapter: Dict[str, List[SampleRow]] = {}
    for row in samples:
        by_chapter.setdefault(row.chapter, []).append(row)

    models: Dict[str, Dict] = {}
    for chapter, rows in by_chapter.items():
        a = np.eye(d) * float(l2)
        b = np.zeros(d, dtype=float)
        for r in rows:
            x = np.array(r.features, dtype=float)
            a += np.outer(x, x)
            b += r.reward * x
        a_inv = np.linalg.inv(a)
        models[chapter] = {
            "A_inv": a_inv.tolist(),
            "b": b.tolist(),
            "n": len(rows),
        }
    return {"feature_dim": d, "models": models, "training_rows": len(samples)}


def evaluate_policy(models_payload: Dict, samples: List[SampleRow], alpha: float = 0.35) -> Dict[str, float]:
    models = models_payload.get("models", {})
    if not models or not samples:
        return {
            "avg_reward": 0.0,
            "avg_regret": 0.0,
            "coverage_at_3": 0.0,
            "ability_error": 0.0,
            "cost_violation_rate": 0.0,
        }

    chapters = list(models.keys())
    rewards = []
    regrets = []
    topk_hits = 0
    ability_errors = []
    violations = 0

    for row in samples:
        x = np.array(row.features, dtype=float)
        chosen_pred = None
        preds: List[Tuple[str, float]] = []
        for ch in chapters:
            model = models.get(ch, {})
            try:
                a_inv = np.array(model["A_inv"], dtype=float)
                b = np.array(model["b"], dtype=float)
            except Exception:
                continue
            theta = a_inv @ b
            val = float(theta @ x + alpha * np.sqrt(max(float(x @ a_inv @ x), 0.0)))
            preds.append((ch, val))
            if ch == row.chapter:
                chosen_pred = val

        if not preds:
            continue
        preds.sort(key=lambda p: p[1], reverse=True)
        best_val = preds[0][1]
        chosen_val = chosen_pred if chosen_pred is not None else preds[-1][1]
        regrets.append(max(0.0, best_val - chosen_val))
        rewards.append(float(row.reward))
        top3 = [p[0] for p in preds[:3]]
        if row.chapter in top3:
            topk_hits += 1

        inferred_ability = 1.0 + 4.0 * float(row.features[1])
        inferred_difficulty = 1.0 + 4.0 * float(row.features[2])
        ability_errors.append(abs(inferred_ability - inferred_difficulty))
        if float(row.features[13]) > 0.5 and float(row.features[6]) < 0.2:
            violations += 1

    n = max(1, len(rewards))
    return {
        "avg_reward": float(np.mean(rewards)) if rewards else 0.0,
        "avg_regret": float(np.mean(regrets)) if regrets else 0.0,
        "coverage_at_3": 100.0 * topk_hits / n,
        "ability_error": float(np.mean(ability_errors)) if ability_errors else 0.0,
        "cost_violation_rate": 100.0 * violations / n,
    }


def persist_policy(output_dir: Path, payload: Dict) -> Path:
    out = output_dir / "contextual_bandit_policy.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
