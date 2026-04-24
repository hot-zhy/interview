"""JudgeRouter: route between rule-based and LLM judges with validation and fallback.

Preserves the existing evaluation output schema so that downstream report
generation and UI are not broken.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from backend.agent.eval_policy import (
    EvalPolicyState,
    EvalRewardSignal,
    EvalRoutingAction,
    choose_eval_action,
    compute_eval_reward,
)
from backend.agent.models import EvaluationResult, ToolInvocationRecord
from backend.agent.tools import LLMJudgeTool, RuleJudgeTool, ValidatorTool
from backend.core.config import settings


class JudgeRouter:
    """Orchestrates hybrid evaluation with routing, validation, fallback,
    and optional multi-judge aggregation."""

    def __init__(self) -> None:
        self.rule_judge = RuleJudgeTool()
        self.llm_judge = LLMJudgeTool()
        self.validator = ValidatorTool()

    def evaluate(
        self,
        question: str,
        correct_answer: str,
        user_answer: str,
        routing_state: Optional[Dict] = None,
    ) -> tuple[EvaluationResult, List[ToolInvocationRecord]]:
        """Run the full routing pipeline and return (result, tool_records)."""
        records: List[ToolInvocationRecord] = []
        state = self._build_policy_state(user_answer=user_answer, routing_state=routing_state)
        policy_action = self._resolve_policy_action(state)

        # Step 1: always compute rule-based baseline
        rule_result, rule_rec = self.rule_judge.invoke(question, correct_answer, user_answer)
        records.append(rule_rec)

        # Step 2: optional early return for rule-only route
        if policy_action == EvalRoutingAction.RULE_ONLY or not settings.zhipuai_api_key:
            rule_result.provenance = "rule_policy"
            self._attach_policy_meta(
                result=rule_result,
                state=state,
                action=EvalRoutingAction.RULE_ONLY,
                fallback_reason="llm_disabled" if not settings.zhipuai_api_key else "",
            )
            return rule_result, records

        judge_count = self._pick_judge_count(policy_action)
        llm_result, llm_rec = self._invoke_llm_with_judge_count(
            question=question,
            correct_answer=correct_answer,
            user_answer=user_answer,
            judge_count=judge_count,
        )
        records.append(llm_rec)

        if llm_result is not None:
            # Step 3: validate LLM output
            is_valid, reason = self.validator.validate(llm_result)

            if is_valid:
                llm_result.provenance = "hybrid_policy"
                self._attach_policy_meta(
                    result=llm_result,
                    state=state,
                    action=policy_action,
                    fallback_reason="",
                )
                return llm_result, records

            records.append(ToolInvocationRecord(
                tool_name="validator",
                input_summary="llm_output",
                output_summary=f"invalid: {reason}",
                success=True,
                fallback_used=True,
            ))
            rule_result.provenance = "rule_fallback_validation"
            self._attach_policy_meta(
                result=rule_result,
                state=state,
                action=policy_action,
                fallback_reason=f"validator:{reason}",
            )
            return rule_result, records

        # LLM returned None (unavailable)
        rule_result.provenance = "rule_fallback_unavailable"
        self._attach_policy_meta(
            result=rule_result,
            state=state,
            action=policy_action,
            fallback_reason="llm_none",
        )
        return rule_result, records

    def evaluate_dict(
        self,
        question: str,
        correct_answer: str,
        user_answer: str,
    ) -> dict:
        """Convenience method returning a plain dict matching the legacy
        format used by interview_engine._evaluate_answer_with_fallback."""
        ev, _ = self.evaluate(question, correct_answer, user_answer)
        return {
            "scores": ev.scores,
            "overall_score": ev.overall_score,
            "feedback": ev.feedback,
            "missing_points": ev.missing_points,
            "next_direction": ev.next_direction,
            "reasoning": ev.reasoning,
            "policy_meta": ev.policy_meta,
        }

    def _build_policy_state(
        self,
        user_answer: str,
        routing_state: Optional[Dict],
    ) -> EvalPolicyState:
        routing_state = routing_state or {}
        return EvalPolicyState(
            round_idx=int(routing_state.get("round_idx", 1)),
            total_rounds=max(1, int(routing_state.get("total_rounds", 10))),
            answer_length=len((user_answer or "").strip()),
            recent_avg_score=float(routing_state.get("recent_avg_score", 0.6)),
            missing_points_count=int(routing_state.get("missing_points_count", 0)),
            fallback_count=int(routing_state.get("fallback_count", 0)),
            llm_calls_used=int(routing_state.get("llm_calls_used", 0)),
            multi_judge_used=int(routing_state.get("multi_judge_used", 0)),
            llm_available=bool(settings.zhipuai_api_key),
            multi_judge_enabled=int(getattr(settings, "llm_multi_judge_count", 1)) > 1,
        )

    def _resolve_policy_action(self, state: EvalPolicyState) -> EvalRoutingAction:
        if not bool(getattr(settings, "enable_eval_policy_agent", False)):
            return EvalRoutingAction.LLM_SINGLE if state.llm_available else EvalRoutingAction.RULE_ONLY
        return choose_eval_action(state)

    def _pick_judge_count(self, action: EvalRoutingAction) -> int:
        if action == EvalRoutingAction.LLM_MULTI:
            return max(2, int(getattr(settings, "llm_multi_judge_count", 1)))
        return 1

    def _invoke_llm_with_judge_count(
        self,
        question: str,
        correct_answer: str,
        user_answer: str,
        judge_count: int,
    ):
        old_count = int(getattr(settings, "llm_multi_judge_count", 1))
        try:
            settings.llm_multi_judge_count = int(max(1, judge_count))
            return self.llm_judge.invoke(question, correct_answer, user_answer)
        finally:
            settings.llm_multi_judge_count = old_count

    def _attach_policy_meta(
        self,
        result: EvaluationResult,
        state: EvalPolicyState,
        action: EvalRoutingAction,
        fallback_reason: str,
    ) -> None:
        reward = compute_eval_reward(
            EvalRewardSignal(
                agreement=result.overall_score,
                quality=result.overall_score,
                feedback_hit=1.0 if result.missing_points else 0.0,
                llm_used=action in {EvalRoutingAction.LLM_SINGLE, EvalRoutingAction.LLM_MULTI},
                multi_judge_used=action == EvalRoutingAction.LLM_MULTI,
                followup_used=action == EvalRoutingAction.ASK_FOLLOWUP_THEN_EVAL,
            )
        )
        result.reasoning = result.reasoning or ""
        result.policy_meta = {
            "reward": round(float(reward), 5),
            "action": action.value,
            "state": {
                "round_idx": state.round_idx,
                "answer_length": state.answer_length,
                "recent_avg_score": round(state.recent_avg_score, 4),
                "missing_points_count": state.missing_points_count,
                "fallback_count": state.fallback_count,
                "llm_calls_used": state.llm_calls_used,
                "multi_judge_used": state.multi_judge_used,
            },
        }
        if fallback_reason:
            result.policy_meta["fallback_reason"] = fallback_reason
