"""Shared utilities for agentic-RL question selection.

This module keeps feature extraction and reward proxy logic in one place so
online inference and offline training use the same representation.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.db.models import AskedQuestion, InterviewSession
from backend.services.personalized_algorithms import estimate_ability


@dataclass
class BanditFeatureSnapshot:
    """Feature snapshot for one chapter-selection decision."""

    base_features: Dict[str, float]
    chapter_features: Dict[str, Dict[str, float]]


@dataclass
class TrainingSample:
    """Single history-derived sample for offline policy learning."""

    session_id: int
    round_number: int
    chapter: str
    reward: float
    feature_vector: List[float]


def _safe_mean(values: List[float], default: float = 0.0) -> float:
    if not values:
        return default
    return float(sum(values) / len(values))


def _bounded(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _chapter_match(chapter: str, candidates: List[str]) -> Optional[str]:
    if chapter in candidates:
        return chapter
    lower = (chapter or "").lower()
    for c in candidates:
        if c.lower() == lower:
            return c
    for c in candidates:
        if c.lower() in lower or lower in c.lower():
            return c
    return None


def _build_history(db: Session, session_id: int) -> List[tuple]:
    asked = (
        db.query(AskedQuestion)
        .filter(AskedQuestion.session_id == session_id)
        .order_by(AskedQuestion.created_at.asc())
        .all()
    )
    history: List[tuple] = []
    for aq in asked:
        if aq.evaluation:
            history.append((int(aq.difficulty), float(aq.evaluation.overall_score)))
    return history


def build_bandit_feature_snapshot(
    db: Session,
    session: InterviewSession,
    current_difficulty: int,
    track_chapters: Dict[str, float],
    asked_chapters: List[str],
    resume_skills: List[str],
    missing_chapters: List[str],
    llm_context: Dict,
) -> BanditFeatureSnapshot:
    """Create shared features for chapter bandit decisions."""
    chapters = list(track_chapters.keys())
    asked = (
        db.query(AskedQuestion)
        .filter(AskedQuestion.session_id == session.id)
        .order_by(AskedQuestion.created_at.asc())
        .all()
    )
    history = _build_history(db, session.id)
    ability = estimate_ability(history, default=float(session.level))
    scores = [float(aq.evaluation.overall_score) for aq in asked if aq.evaluation]
    recent_window = int(getattr(settings, "rl_feature_window", 3))
    recent_scores = scores[-recent_window:] if recent_window > 0 else scores

    chapter_counts: Dict[str, int] = {c: 0 for c in chapters}
    chapter_scores: Dict[str, List[float]] = {c: [] for c in chapters}
    for aq in asked:
        mapped = _chapter_match(aq.topic or "", chapters)
        if not mapped:
            continue
        chapter_counts[mapped] += 1
        if aq.evaluation:
            chapter_scores[mapped].append(float(aq.evaluation.overall_score))

    total_asked = max(1, len(asked))
    coverage_ratio = len([c for c, n in chapter_counts.items() if n > 0]) / max(1, len(chapters))
    base = {
        "bias": 1.0,
        "ability": _bounded((ability - 1.0) / 4.0, 0.0, 1.0),
        "difficulty": _bounded((float(current_difficulty) - 1.0) / 4.0, 0.0, 1.0),
        "avg_score": _bounded(_safe_mean(scores, 0.5), 0.0, 1.0),
        "recent_score": _bounded(_safe_mean(recent_scores, 0.5), 0.0, 1.0),
        "coverage_ratio": _bounded(coverage_ratio, 0.0, 1.0),
        "remaining_ratio": _bounded(
            1.0 - (float(session.current_round or 0) / max(float(session.total_rounds or 1), 1.0)),
            0.0,
            1.0,
        ),
        "hint_available": 1.0 if llm_context.get("missing_concepts") else 0.0,
    }

    chapter_feature_map: Dict[str, Dict[str, float]] = {}
    missing = set(missing_chapters or [])
    resume = set(resume_skills or [])
    for ch in chapters:
        n = chapter_counts.get(ch, 0)
        chapter_feature_map[ch] = {
            "track_weight": float(track_chapters.get(ch, 0.0)),
            "chapter_seen_ratio": _bounded(n / total_asked, 0.0, 1.0),
            "chapter_score": _bounded(_safe_mean(chapter_scores.get(ch, []), 0.5), 0.0, 1.0),
            "chapter_gap": 1.0 if ch in missing else 0.0,
            "chapter_resume_match": 1.0 if ch in resume else 0.0,
            "chapter_recent_asked": 1.0 if ch in asked_chapters[-2:] else 0.0,
        }

    return BanditFeatureSnapshot(base_features=base, chapter_features=chapter_feature_map)


def feature_vector_for_chapter(snapshot: BanditFeatureSnapshot, chapter: str) -> List[float]:
    """Encode shared + chapter features into a fixed-order vector."""
    base = snapshot.base_features
    per = snapshot.chapter_features.get(chapter, {})
    return [
        float(base.get("bias", 1.0)),
        float(base.get("ability", 0.5)),
        float(base.get("difficulty", 0.5)),
        float(base.get("avg_score", 0.5)),
        float(base.get("recent_score", 0.5)),
        float(base.get("coverage_ratio", 0.0)),
        float(base.get("remaining_ratio", 1.0)),
        float(base.get("hint_available", 0.0)),
        float(per.get("track_weight", 0.0)),
        float(per.get("chapter_seen_ratio", 0.0)),
        float(per.get("chapter_score", 0.5)),
        float(per.get("chapter_gap", 0.0)),
        float(per.get("chapter_resume_match", 0.0)),
        float(per.get("chapter_recent_asked", 0.0)),
    ]


def compute_reward_proxy(
    previous_score: Optional[float],
    current_score: float,
    prev_coverage_ratio: float,
    new_coverage_ratio: float,
    llm_used: bool = False,
    followup_used: bool = False,
    is_terminal_round: bool = False,
    session_quality: Optional[float] = None,
) -> float:
    """Reward proxy for offline selection policy learning."""
    gain = max(0.0, float(current_score) - float(previous_score or 0.0))
    quality = _bounded(float(current_score), 0.0, 1.0)
    coverage_gain = max(0.0, float(new_coverage_ratio) - float(prev_coverage_ratio))
    cost = 0.0
    if llm_used:
        cost += float(getattr(settings, "rl_cost_llm_penalty", 0.05))
    if followup_used:
        cost += float(getattr(settings, "rl_cost_followup_penalty", 0.03))
    reward = (
        float(getattr(settings, "rl_reward_gain_weight", 0.40)) * gain
        + float(getattr(settings, "rl_reward_quality_weight", 0.25)) * quality
        + float(getattr(settings, "rl_reward_coverage_weight", 0.20)) * coverage_gain
        - float(getattr(settings, "rl_reward_cost_weight", 0.15)) * cost
    )
    if is_terminal_round and session_quality is not None:
        reward += 0.10 * _bounded(float(session_quality), 0.0, 1.0)
    return float(reward)


def choose_chapter_with_contextual_bandit(
    snapshot: BanditFeatureSnapshot,
    candidate_chapters: List[str],
    fallback_chapter: str,
    policy_path: str,
    alpha: float = 0.35,
) -> Optional[str]:
    """Choose chapter by LinUCB parameters from an offline-trained artifact."""
    if not candidate_chapters:
        return fallback_chapter
    path = Path(policy_path)
    if not path.exists():
        return fallback_chapter
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback_chapter

    models = payload.get("models", {})
    if not isinstance(models, dict):
        return fallback_chapter

    best_score = -float("inf")
    best_chapter = fallback_chapter
    for chapter in candidate_chapters:
        model = models.get(chapter)
        if not model:
            continue
        try:
            a_inv = np.array(model["A_inv"], dtype=float)
            b = np.array(model["b"], dtype=float)
        except Exception:
            continue
        x = np.array(feature_vector_for_chapter(snapshot, chapter), dtype=float)
        if a_inv.shape[0] != x.shape[0]:
            continue
        theta = a_inv @ b
        exploit = float(theta @ x)
        explore = float(alpha) * math.sqrt(max(float(x @ a_inv @ x), 0.0))
        score = exploit + explore
        if score > best_score:
            best_score = score
            best_chapter = chapter

    return best_chapter


def build_training_samples_from_session_history(
    db: Session,
    session: InterviewSession,
    track_chapters: Dict[str, float],
) -> List[TrainingSample]:
    """Build contextual-bandit samples directly from interview history."""
    chapters = list(track_chapters.keys())
    asked = (
        db.query(AskedQuestion)
        .filter(AskedQuestion.session_id == session.id)
        .order_by(AskedQuestion.created_at.asc())
        .all()
    )
    if not asked or not chapters:
        return []

    samples: List[TrainingSample] = []
    seen_chapters: set = set()
    prev_score: Optional[float] = None

    for round_idx, aq in enumerate(asked, start=1):
        chapter = _chapter_match(aq.topic or "", chapters)
        if not chapter or not aq.evaluation:
            continue

        prev_cov = len(seen_chapters) / max(1, len(chapters))
        seen_chapters.add(chapter)
        new_cov = len(seen_chapters) / max(1, len(chapters))
        score = float(aq.evaluation.overall_score)

        snapshot = build_bandit_feature_snapshot(
            db=db,
            session=session,
            current_difficulty=int(aq.difficulty),
            track_chapters=track_chapters,
            asked_chapters=[x.topic or "" for x in asked[:round_idx]],
            resume_skills=[],
            missing_chapters=[],
            llm_context={},
        )
        reward = compute_reward_proxy(
            previous_score=prev_score,
            current_score=score,
            prev_coverage_ratio=prev_cov,
            new_coverage_ratio=new_cov,
            llm_used=False,
            followup_used=False,
            is_terminal_round=(round_idx == len(asked)),
            session_quality=_safe_mean([float(x.evaluation.overall_score) for x in asked if x.evaluation], default=0.5),
        )
        samples.append(
            TrainingSample(
                session_id=int(session.id),
                round_number=round_idx,
                chapter=chapter,
                reward=reward,
                feature_vector=feature_vector_for_chapter(snapshot, chapter),
            )
        )
        prev_score = score

    return samples
