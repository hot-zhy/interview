"""Guardrails for staged rollout and safe fallback."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Dict

from backend.core.config import settings


@dataclass
class GuardrailDecision:
    allow_llm: bool
    forced_action: str = ""
    reason: str = ""
    rollout_variant: str = "control"


def in_rollout_bucket(session_id: int) -> bool:
    """Deterministic hash bucketing for session-level rollout."""
    pct = max(0, min(int(getattr(settings, "rollout_percent", 10)), 100))
    if pct >= 100:
        return True
    if pct <= 0:
        return False
    token = f"{getattr(settings, 'rollout_hash_salt', 'rollout')}:{int(session_id)}"
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < pct


def evaluate_guardrails(session_id: int, routing_state: Dict) -> GuardrailDecision:
    """Decide if LLM routes are allowed for current turn."""
    variant = str(getattr(settings, "rollout_variant", "control"))
    if variant == "control":
        return GuardrailDecision(allow_llm=False, forced_action="rule_only", reason="control_variant", rollout_variant=variant)
    if not in_rollout_bucket(session_id):
        return GuardrailDecision(allow_llm=False, forced_action="rule_only", reason="outside_rollout_bucket", rollout_variant=variant)

    llm_calls = int(routing_state.get("llm_calls_used", 0))
    multi_calls = int(routing_state.get("multi_judge_used", 0))
    fallback_count = int(routing_state.get("fallback_count", 0))
    turn_idx = max(1, int(routing_state.get("round_idx", 1)))
    fallback_rate = float(fallback_count) / float(turn_idx)

    if llm_calls >= int(getattr(settings, "guardrail_max_llm_calls_per_session", 10)):
        return GuardrailDecision(False, "rule_only", "llm_budget_exceeded", variant)
    if multi_calls >= int(getattr(settings, "guardrail_max_multi_judge_per_session", 4)):
        return GuardrailDecision(False, "llm_single", "multi_judge_budget_exceeded", variant)
    if fallback_rate > float(getattr(settings, "guardrail_max_fallback_rate", 0.5)):
        return GuardrailDecision(False, "rule_only", "fallback_rate_spike", variant)
    return GuardrailDecision(True, "", "", variant)

