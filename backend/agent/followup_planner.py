"""FollowUpPlanner: wraps existing follow-up logic into a planner interface.

Does NOT change follow-up limits, question flow, or template logic.
"""
from __future__ import annotations

from typing import List

from backend.agent.models import FollowUpPlan, InterviewMemory, InterviewState
from backend.agent.tools import FollowUpGeneratorTool


class FollowUpPlanner:
    """Decides whether to follow up and generates the follow-up text."""

    def __init__(self) -> None:
        self.generator = FollowUpGeneratorTool()
        self.followup_limit = 2

    def plan(
        self,
        state: InterviewState,
        memory: InterviewMemory,
        asked_question_id: str,
        evaluation_score: float,
        missing_points: List[str],
        original_question: str,
        user_answer: str,
        correct_answer: str,
        feedback: str,
    ) -> FollowUpPlan:
        """Decide whether to follow up and produce the text if so.

        Replicates the decision logic from AdaptiveInterviewEngine.should_ask_followup
        but operates on the agent's state/memory rather than querying the DB.
        """
        followup_count = memory.followup_counts.get(str(asked_question_id), 0)

        if followup_count >= self.followup_limit:
            return FollowUpPlan(
                should_followup=False,
                reason=f"follow-up limit reached ({self.followup_limit})",
            )

        should = False
        reason = ""

        if evaluation_score < 0.6 and len(missing_points) > 0:
            should = True
            reason = "low score with missing concepts"
        elif 0.6 <= evaluation_score < 0.7 and len(missing_points) > 0 and followup_count < 1:
            should = True
            reason = "moderate score, first follow-up for deeper probing"

        if not should:
            return FollowUpPlan(should_followup=False, reason="score adequate or no gaps")

        if state.remaining_budget <= 0:
            return FollowUpPlan(should_followup=False, reason="no remaining budget")

        text, source, _ = self.generator.invoke(
            original_question=original_question,
            user_answer=user_answer,
            feedback=feedback,
            missing_points=missing_points,
            followup_count=followup_count,
            correct_answer=correct_answer,
        )

        return FollowUpPlan(
            should_followup=True,
            reason=reason,
            followup_text=text or "",
            source=source,
        )
