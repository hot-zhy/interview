"""Termination policy for deciding whether to stop an interview round."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np

from backend.core.config import settings


class TerminationAction(str, Enum):
    CONTINUE = "continue"
    TERMINATE = "terminate"


@dataclass
class TerminationPolicyState:
    round_idx: int
    total_rounds: int
    avg_score: float
    recent_avg_score: float
    std_dev: float
    difficulty_range: int
    chapter_coverage: int
    fallback_count: int
    recent_improvement: float


def _bounded(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def build_termination_feature_vector(state: TerminationPolicyState) -> list[float]:
    total = max(int(state.total_rounds), 1)
    return [
        1.0,
        _bounded(float(state.round_idx) / float(total), 0.0, 1.0),
        _bounded(float(state.avg_score), 0.0, 1.0),
        _bounded(float(state.recent_avg_score), 0.0, 1.0),
        _bounded(float(state.std_dev) / 0.5, 0.0, 1.0),
        _bounded(float(state.difficulty_range) / 4.0, 0.0, 1.0),
        _bounded(float(state.chapter_coverage) / 6.0, 0.0, 1.0),
        _bounded(float(state.fallback_count) / 6.0, 0.0, 1.0),
        _bounded((float(state.recent_improvement) + 1.0) / 2.0, 0.0, 1.0),
    ]


def _heuristic_action(state: TerminationPolicyState) -> tuple[TerminationAction, str]:
    if state.avg_score >= 0.85 and state.recent_avg_score >= 0.85 and state.std_dev < 0.15:
        return TerminationAction.TERMINATE, "excellent_and_stable"
    if state.avg_score < 0.4 and state.recent_avg_score < 0.4 and state.recent_improvement <= 0.02:
        return TerminationAction.TERMINATE, "poor_and_no_improvement"
    if (
        state.std_dev < 0.2
        and state.difficulty_range >= 2
        and state.chapter_coverage >= 3
        and state.recent_avg_score >= 0.7
    ):
        return TerminationAction.TERMINATE, "coverage_and_stability"
    return TerminationAction.CONTINUE, "need_more_evidence"


def choose_termination_action(state: TerminationPolicyState) -> tuple[TerminationAction, str]:
    strategy = str(getattr(settings, "termination_policy_strategy", "heuristic"))
    heuristic_action, heuristic_reason = _heuristic_action(state)
    if strategy != "contextual_bandit":
        return heuristic_action, f"heuristic:{heuristic_reason}"

    artifact = Path(str(getattr(settings, "termination_policy_artifact_path", "") or ""))
    if not artifact.exists():
        return heuristic_action, "artifact_missing_fallback"

    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except Exception:
        return heuristic_action, "artifact_load_failed_fallback"

    models = payload.get("models", {})
    if not isinstance(models, dict):
        return heuristic_action, "artifact_models_invalid_fallback"

    x = np.array(build_termination_feature_vector(state), dtype=float)
    best_action = heuristic_action
    best_score = -float("inf")
    alpha = float(getattr(settings, "termination_policy_alpha", 0.20))
    valid_actions = {TerminationAction.CONTINUE.value, TerminationAction.TERMINATE.value}

    for action_name, model in models.items():
        if action_name not in valid_actions:
            continue
        try:
            a_inv = np.array(model["A_inv"], dtype=float)
            b = np.array(model["b"], dtype=float)
        except Exception:
            continue
        if a_inv.shape[0] != x.shape[0]:
            continue
        theta = a_inv @ b
        exploit = float(theta @ x)
        explore = float(alpha) * math.sqrt(max(float(x @ a_inv @ x), 0.0))
        score = exploit + explore
        if score > best_score:
            best_score = score
            best_action = TerminationAction(action_name)

    if best_score == -float("inf"):
        return heuristic_action, "bandit_unavailable_fallback"
    return best_action, f"bandit:{best_action.value}:{best_score:.4f}"

