"""JudgeRouter: route between rule-based and LLM judges with validation and fallback.

Preserves the existing evaluation output schema so that downstream report
generation and UI are not broken.
"""
from __future__ import annotations

from typing import List, Optional

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
    ) -> tuple[EvaluationResult, List[ToolInvocationRecord]]:
        """Run the full routing pipeline and return (result, tool_records)."""
        records: List[ToolInvocationRecord] = []

        # Step 1: always compute rule-based baseline
        rule_result, rule_rec = self.rule_judge.invoke(question, correct_answer, user_answer)
        records.append(rule_rec)

        # Step 2: try LLM if API key is configured
        if settings.zhipuai_api_key:
            llm_result, llm_rec = self.llm_judge.invoke(question, correct_answer, user_answer)
            records.append(llm_rec)

            if llm_result is not None:
                # Step 3: validate LLM output
                is_valid, reason = self.validator.validate(llm_result)

                if is_valid:
                    llm_result.provenance = "hybrid"
                    return llm_result, records
                else:
                    # Validation failed — fall back to rule
                    records.append(ToolInvocationRecord(
                        tool_name="validator",
                        input_summary="llm_output",
                        output_summary=f"invalid: {reason}",
                        success=True,
                        fallback_used=True,
                    ))
                    rule_result.provenance = "rule_fallback_validation"
                    return rule_result, records

            # LLM returned None (unavailable)
            rule_result.provenance = "rule_fallback_unavailable"
            return rule_result, records

        # No LLM configured
        rule_result.provenance = "rule"
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
        }
