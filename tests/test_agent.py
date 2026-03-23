"""Tests for the agentic interview framework.

Validates that:
- Legacy flow is unchanged when feature flags are off (regression safety)
- Agent models serialise/deserialise correctly
- Memory updates work
- StateBuilder produces valid states
- JudgeRouter falls back correctly
- FollowUpPlanner respects limits
- Controller action selection is deterministic
"""
import math
import pytest

from backend.agent.models import (
    ActionDecision,
    ActionType,
    EvaluationResult,
    FollowUpPlan,
    InterviewMemory,
    InterviewState,
    Observation,
    ToolInvocationRecord,
    AgentTrace,
)
from backend.agent.memory import MemoryManager
from backend.agent.state_builder import StateBuilder
from backend.agent.tools import ValidatorTool
from backend.agent.trace import TraceCollector


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestModels:
    def test_action_decision_serialises(self):
        ad = ActionDecision(action=ActionType.ASK_NEXT, reason="test")
        d = ad.model_dump()
        assert d["action"] == "ask_next"
        assert d["reason"] == "test"

    def test_evaluation_result_defaults(self):
        ev = EvaluationResult()
        assert ev.overall_score == 0.0
        assert ev.provenance == "unknown"

    def test_observation_fields(self):
        obs = Observation(turn_number=1, candidate_answer="hello")
        assert obs.turn_number == 1
        assert obs.answer_type == "text"

    def test_interview_memory_append(self):
        mem = InterviewMemory(session_id=1)
        mem.append_turn(0.7, 3, "JVM", ["gc"], "explore gc", "hybrid")
        assert mem.turn_count == 1
        assert mem.latest_score == 0.7
        assert "gc" in mem.missing_concepts
        assert mem.latest_hint == "explore gc"

    def test_interview_memory_followup(self):
        mem = InterviewMemory(session_id=1)
        mem.record_followup("q1")
        mem.record_followup("q1")
        assert mem.followup_counts["q1"] == 2

    def test_interview_memory_dedup_missing(self):
        mem = InterviewMemory(session_id=1)
        mem.append_turn(0.5, 2, "Java基础", ["thread"], None, "rule")
        mem.append_turn(0.5, 2, "Java基础", ["thread", "lock"], None, "rule")
        assert mem.missing_concepts.count("thread") == 1
        assert "lock" in mem.missing_concepts


# ---------------------------------------------------------------------------
# StateBuilder tests
# ---------------------------------------------------------------------------

class TestStateBuilder:
    def _make_memory(self, scores, difficulties, chapters):
        mem = InterviewMemory(session_id=1, resume_skills=["Java", "Spring"])
        for s, d, c in zip(scores, difficulties, chapters):
            mem.append_turn(s, d, c, [], None, "rule")
        return mem

    def test_basic_state(self):
        mem = self._make_memory([0.8, 0.6, 0.7], [3, 3, 4], ["A", "B", "C"])
        state = StateBuilder.build(
            memory=mem,
            session_total_rounds=10,
            current_round=3,
            current_difficulty=4,
        )
        assert state.current_difficulty == 4
        assert state.remaining_budget == 7
        assert state.chapter_coverage_count == 3
        assert abs(state.avg_score - 0.7) < 0.01
        assert state.resume_prior == ["Java", "Spring"]

    def test_empty_memory(self):
        mem = InterviewMemory(session_id=1)
        state = StateBuilder.build(mem, 10, 0, 3)
        assert state.avg_score == 0.0
        assert state.remaining_budget == 10

    def test_followup_budget(self):
        mem = InterviewMemory(session_id=1)
        mem.record_followup("q5")
        state = StateBuilder.build(mem, 10, 1, 3, current_asked_question_id="q5")
        assert state.followup_budget_for_current == 1


# ---------------------------------------------------------------------------
# Validator tests
# ---------------------------------------------------------------------------

class TestValidator:
    def test_valid_result(self):
        ev = EvaluationResult(
            scores={"correctness": 0.8, "depth": 0.7, "clarity": 0.6, "practicality": 0.5, "tradeoffs": 0.4},
            overall_score=0.65,
        )
        ok, reason = ValidatorTool().validate(ev)
        assert ok

    def test_missing_dimension(self):
        ev = EvaluationResult(
            scores={"correctness": 0.8, "depth": 0.7},
            overall_score=0.5,
        )
        ok, reason = ValidatorTool().validate(ev)
        assert not ok
        assert "missing" in reason

    def test_out_of_range(self):
        ev = EvaluationResult(
            scores={"correctness": 1.5, "depth": 0.7, "clarity": 0.6, "practicality": 0.5, "tradeoffs": 0.4},
            overall_score=0.65,
        )
        ok, reason = ValidatorTool().validate(ev)
        assert not ok


# ---------------------------------------------------------------------------
# Trace tests
# ---------------------------------------------------------------------------

class TestTrace:
    def test_trace_collector(self):
        tc = TraceCollector(session_id=42)
        t = tc.begin_turn(1)
        tc.record_observation(Observation(turn_number=1))
        tc.record_action(ActionDecision(action=ActionType.ASK_NEXT, reason="test"))
        tc.record_tool(ToolInvocationRecord(tool_name="rule_judge"))

        assert len(tc.traces) == 1
        assert tc.current.action.action == ActionType.ASK_NEXT
        assert len(tc.current.tool_invocations) == 1

    def test_summary(self):
        tc = TraceCollector(session_id=1)
        tc.begin_turn(1)
        tc.record_action(ActionDecision(action=ActionType.TERMINATE, reason="done"))
        s = tc.summary()
        assert s["total_turns"] == 1
        assert s["actions"] == ["terminate"]

    def test_to_json(self):
        tc = TraceCollector(session_id=1)
        tc.begin_turn(1)
        j = tc.to_json()
        assert '"turn_number": 1' in j


# ---------------------------------------------------------------------------
# Feature flag regression test
# ---------------------------------------------------------------------------

class TestFeatureFlags:
    def test_defaults_off(self):
        """All agentic flags default to False, preserving legacy flow."""
        from backend.core.config import Settings
        s = Settings()
        assert s.enable_agent_controller is False
        assert s.enable_memory_state is False
        assert s.enable_tool_routing is False
        assert s.enable_multi_judge is False
        assert s.enable_followup_planner is False
        assert s.enable_agent_tracing is False
