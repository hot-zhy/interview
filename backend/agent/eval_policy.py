"""Evaluation routing policy for agentic-RL.

This module defines a state/action/reward abstraction for deciding how the
system evaluates each answer. The policy is safe-by-default and always allows
fallback to the legacy judge pipeline.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from backend.core.config import settings


class EvalRoutingAction(str, Enum):
    RULE_ONLY = "rule_only"
    LLM_SINGLE = "llm_single"
    LLM_MULTI = "llm_multi"
    ASK_FOLLOWUP_THEN_EVAL = "ask_followup_then_eval"


@dataclass
class EvalPolicyState:
    """Compact state used for evaluation-routing decisions."""

    round_idx: int
    total_rounds: int
    answer_length: int
    recent_avg_score: float
    missing_points_count: int
    fallback_count: int
    llm_calls_used: int
    multi_judge_used: int
    llm_available: bool
    multi_judge_enabled: bool


@dataclass
class EvalRewardSignal:
    """Reward components for training / analysis."""

    agreement: float
    quality: float
    feedback_hit: float
    llm_used: bool
    multi_judge_used: bool
    followup_used: bool
    latency_ms: float = 0.0
    instability: float = 0.0


def _bounded(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def build_eval_feature_vector(state: EvalPolicyState) -> list[float]:
    total = max(int(state.total_rounds), 1)
    return [
        1.0,
        _bounded(float(state.round_idx) / float(total), 0.0, 1.0),
        _bounded(float(state.answer_length) / 1200.0, 0.0, 1.0),
        _bounded(state.recent_avg_score, 0.0, 1.0),
        _bounded(float(state.missing_points_count) / 6.0, 0.0, 1.0),
        _bounded(float(state.fallback_count) / 6.0, 0.0, 1.0),
        _bounded(float(state.llm_calls_used) / max(float(settings.eval_policy_max_llm_calls_per_session), 1.0), 0.0, 1.0),
        _bounded(float(state.multi_judge_used) / max(float(settings.eval_policy_max_multi_judge_per_session), 1.0), 0.0, 1.0),
        1.0 if state.llm_available else 0.0,
        1.0 if state.multi_judge_enabled else 0.0,
    ]


def _heuristic_action(state: EvalPolicyState) -> EvalRoutingAction:
    if not state.llm_available:
        return EvalRoutingAction.RULE_ONLY

    if state.llm_calls_used >= int(settings.eval_policy_max_llm_calls_per_session):
        return EvalRoutingAction.RULE_ONLY

    if state.answer_length < 20:
        return EvalRoutingAction.RULE_ONLY

    if state.missing_points_count >= 2 and state.answer_length < 120:
        return EvalRoutingAction.ASK_FOLLOWUP_THEN_EVAL

    if (
        state.multi_judge_enabled
        and state.multi_judge_used < int(settings.eval_policy_max_multi_judge_per_session)
        and state.recent_avg_score < 0.65
    ):
        return EvalRoutingAction.LLM_MULTI

    return EvalRoutingAction.LLM_SINGLE


def choose_eval_action(state: EvalPolicyState) -> EvalRoutingAction:
    """Choose evaluation action using heuristic or contextual policy."""
    strategy = getattr(settings, "eval_policy_strategy", "heuristic")
    if strategy != "contextual_bandit":
        return _heuristic_action(state)

    artifact = Path(getattr(settings, "eval_policy_artifact_path", ""))
    if not artifact.exists():
        return _heuristic_action(state)

    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except Exception:
        return _heuristic_action(state)

    models = payload.get("models", {})
    if not isinstance(models, dict):
        return _heuristic_action(state)

    x = np.array(build_eval_feature_vector(state), dtype=float)
    best_action = _heuristic_action(state)
    best_score = -float("inf")
    alpha = float(getattr(settings, "eval_policy_alpha", 0.25))

    for action_name, model in models.items():
        if action_name not in {a.value for a in EvalRoutingAction}:
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
            best_action = EvalRoutingAction(action_name)
    return best_action


def compute_eval_reward(signal: EvalRewardSignal) -> float:
    """Reward used by offline training and diagnostics."""
    cost = 0.0
    if signal.llm_used:
        cost += float(getattr(settings, "eval_cost_llm_penalty", 0.03))
    if signal.multi_judge_used:
        cost += float(getattr(settings, "eval_cost_multi_judge_penalty", 0.07))
    if signal.followup_used:
        cost += float(getattr(settings, "eval_cost_followup_penalty", 0.02))
    latency_budget = max(float(getattr(settings, "eval_latency_budget_ms", 3500.0)), 1.0)
    latency_term = _bounded(float(signal.latency_ms) / latency_budget, 0.0, 1.0)
    instability_ref = max(float(getattr(settings, "eval_instability_reference", 0.25)), 1e-6)
    instability_term = _bounded(float(signal.instability) / instability_ref, 0.0, 1.0)
    return float(
        float(getattr(settings, "eval_reward_agreement_weight", 0.45)) * _bounded(signal.agreement, 0.0, 1.0)
        + float(getattr(settings, "eval_reward_quality_weight", 0.25)) * _bounded(signal.quality, 0.0, 1.0)
        + float(getattr(settings, "eval_reward_feedback_weight", 0.20)) * _bounded(signal.feedback_hit, 0.0, 1.0)
        - float(getattr(settings, "eval_reward_cost_weight", 0.10)) * cost
        - float(getattr(settings, "eval_reward_latency_weight", 0.10)) * latency_term
        - float(getattr(settings, "eval_reward_instability_weight", 0.10)) * instability_term
    )
