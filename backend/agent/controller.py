"""AgentController: top-level orchestration layer for the agentic interview.

Implements the closed-loop:
    observation -> memory update -> state build -> action selection
    -> tool invocation -> feedback -> memory update

This controller wraps existing stable modules and does NOT replace them.
It is activated only when ``enable_agent_controller`` is True in settings.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from backend.agent.followup_planner import FollowUpPlanner
from backend.agent.judge_router import JudgeRouter
from backend.agent.memory import MemoryManager
from backend.agent.models import (
    ActionDecision,
    ActionType,
    EvaluationResult,
    InterviewMemory,
    InterviewState,
    Observation,
)
from backend.agent.state_builder import StateBuilder
from backend.agent.tools import ResumeParserTool
from backend.agent.trace import TraceCollector
from backend.core.config import settings
from backend.db.models import (
    AskedQuestion,
    InterviewSession,
    QuestionBank,
    Resume,
)
from backend.services.adaptive_interview import AdaptiveInterviewEngine
from backend.services.question_selector import select_question


class AgentController:
    """Memory-aware, tool-augmented interview agent controller.

    Usage::

        ctrl = AgentController(db, session)
        result = ctrl.process_answer(answer_text, ...)
    """

    def __init__(self, db: DBSession, session: InterviewSession) -> None:
        self.db = db
        self.session = session

        # Sub-components
        self.judge_router = JudgeRouter()
        self.followup_planner = FollowUpPlanner()
        self.tracer = TraceCollector(session.id)

        # Load or build memory
        self.memory = MemoryManager.build_from_db(db, session)

        # Existing adaptive engine (reused for difficulty / termination)
        self.adaptive_engine = AdaptiveInterviewEngine(db, session)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process_answer(
        self,
        answer_text: str,
        asked_question: AskedQuestion,
        audio_analysis: Optional[Dict] = None,
        expression_analysis: Optional[Dict] = None,
    ) -> Dict:
        """Process a candidate answer through the full agentic loop.

        Returns a dict compatible with the legacy ``submit_answer`` output so
        the caller (interview_engine / Streamlit page) can use it unchanged.
        """
        turn_number = self.memory.turn_count + 1
        trace = self.tracer.begin_turn(turn_number)

        # 1. Observation
        obs = Observation(
            turn_number=turn_number,
            question_id=str(asked_question.id),
            question_text=asked_question.question_text,
            question_chapter=asked_question.topic or "",
            question_difficulty=asked_question.difficulty,
            candidate_answer=answer_text,
            audio_analysis=audio_analysis,
            expression_analysis=expression_analysis,
        )
        self.tracer.record_observation(obs)

        # 2. Evaluate (via judge router)
        eval_result, tool_records = self.judge_router.evaluate(
            question=asked_question.question_text,
            correct_answer=asked_question.correct_answer_text,
            user_answer=answer_text,
        )
        self.tracer.record_evaluation(eval_result)
        self.tracer.record_tools(tool_records)

        # 3. Update memory
        MemoryManager.update_after_evaluation(
            self.memory,
            asked_question_id=str(asked_question.id),
            score=eval_result.overall_score,
            difficulty=asked_question.difficulty,
            chapter=asked_question.topic or "",
            missing_points=eval_result.missing_points,
            next_direction=eval_result.next_direction,
            provenance=eval_result.provenance,
        )
        self.tracer.record_memory_snapshot(self.memory)

        # 4. Build state
        llm_available = bool(settings.zhipuai_api_key)
        state = StateBuilder.build(
            memory=self.memory,
            session_total_rounds=self.session.total_rounds or 10,
            current_round=self.session.current_round,
            current_difficulty=asked_question.difficulty,
            current_asked_question_id=str(asked_question.id),
            latest_evaluation=eval_result,
            llm_available=llm_available,
        )
        self.tracer.record_state_snapshot(state)

        # 5. Choose action (pass answer_text for memory-aware follow-up)
        action = self._choose_action(state, asked_question, eval_result, answer_text)
        self.tracer.record_action(action)

        # 6. Execute action
        return self._execute_action(action, state, eval_result, asked_question, answer_text)

    # ------------------------------------------------------------------
    # Action selection (deterministic policy)
    # ------------------------------------------------------------------

    def _choose_action(
        self,
        state: InterviewState,
        asked_question: AskedQuestion,
        eval_result: EvaluationResult,
        answer_text: str = "",
    ) -> ActionDecision:
        # Check termination (reuse existing logic)
        should_end, end_reason = self.adaptive_engine.should_end_interview()
        if should_end:
            return ActionDecision(
                action=ActionType.TERMINATE,
                reason=end_reason,
            )

        # Check follow-up (pass actual answer for misconception-aware probing)
        followup_plan = self.followup_planner.plan(
            state=state,
            memory=self.memory,
            asked_question_id=str(asked_question.id),
            evaluation_score=eval_result.overall_score,
            missing_points=eval_result.missing_points,
            original_question=asked_question.question_text,
            user_answer=answer_text,
            correct_answer=asked_question.correct_answer_text or "",
            feedback=eval_result.feedback,
        )
        self.tracer.record_followup(followup_plan)

        if followup_plan.should_followup and state.remaining_budget > 0:
            MemoryManager.record_followup(self.memory, str(asked_question.id))
            return ActionDecision(
                action=ActionType.FOLLOW_UP,
                reason=followup_plan.reason,
                followup_text=followup_plan.followup_text,
            )

        # Default: ask next
        new_difficulty = self.adaptive_engine.calculate_adaptive_difficulty()

        # Double-check termination after difficulty update
        should_end, end_reason = self.adaptive_engine.should_end_interview()
        if should_end:
            return ActionDecision(
                action=ActionType.TERMINATE,
                reason=end_reason,
            )

        return ActionDecision(
            action=ActionType.ASK_NEXT,
            reason="proceeding to next question",
            new_difficulty=new_difficulty,
        )

    # ------------------------------------------------------------------
    # Action execution
    # ------------------------------------------------------------------

    def _execute_action(
        self,
        action: ActionDecision,
        state: InterviewState,
        eval_result: EvaluationResult,
        asked_question: AskedQuestion,
        answer_text: str,
    ) -> Dict:
        """Execute the chosen action, returning a legacy-compatible dict."""

        eval_dict = {
            "scores": eval_result.scores,
            "overall_score": eval_result.overall_score,
            "feedback": eval_result.feedback,
            "missing_points": eval_result.missing_points,
            "next_direction": eval_result.next_direction,
            "reasoning": eval_result.reasoning,
        }

        if action.action == ActionType.TERMINATE:
            return {
                "_agent_action": "terminate",
                "_agent_reason": action.reason,
                "evaluation": eval_dict,
            }

        if action.action == ActionType.FOLLOW_UP:
            return {
                "_agent_action": "follow_up",
                "_agent_reason": action.reason,
                "evaluation": eval_dict,
                "followup": True,
                "followup_text": action.followup_text or "",
            }

        # ASK_NEXT
        new_difficulty = action.new_difficulty or state.current_difficulty
        resume_skills = self.memory.resume_skills

        # Collect missing chapters from memory
        missing_chapters = list(self.memory.missing_concepts)

        # Next-direction hints from memory
        next_direction_hints = []
        if self.memory.latest_hint:
            next_direction_hints = [self.memory.latest_hint]

        next_question = select_question(
            db=self.db,
            session=self.session,
            current_difficulty=new_difficulty,
            resume_skills=resume_skills,
            missing_chapters=missing_chapters,
            next_direction_hints=next_direction_hints,
        )

        if not next_question:
            return {
                "_agent_action": "terminate",
                "_agent_reason": "no_questions_available",
                "evaluation": eval_dict,
            }

        return {
            "_agent_action": "ask_next",
            "_agent_reason": action.reason,
            "evaluation": eval_dict,
            "followup": False,
            "next_question_obj": next_question,
            "new_difficulty": new_difficulty,
        }

    # ------------------------------------------------------------------
    # Trace access
    # ------------------------------------------------------------------

    def get_trace_summary(self) -> Dict:
        return self.tracer.summary()

    def get_trace_json(self) -> str:
        return self.tracer.to_json()
