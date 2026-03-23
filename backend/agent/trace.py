"""Structured tracing for the agent controller.

Traces are stored in-memory during a session and can optionally be
serialised for post-hoc analysis.  Tracing is purely additive and
does not interfere with the production interview flow.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.agent.models import (
    ActionDecision,
    AgentTrace,
    EvaluationResult,
    FollowUpPlan,
    InterviewMemory,
    InterviewState,
    Observation,
    ToolInvocationRecord,
)


class TraceCollector:
    """Collects per-turn agent traces for a session."""

    def __init__(self, session_id: int) -> None:
        self.session_id = session_id
        self.traces: List[AgentTrace] = []

    def begin_turn(self, turn_number: int) -> AgentTrace:
        trace = AgentTrace(turn_number=turn_number)
        self.traces.append(trace)
        return trace

    @property
    def current(self) -> Optional[AgentTrace]:
        return self.traces[-1] if self.traces else None

    def record_observation(self, obs: Observation) -> None:
        if self.current:
            self.current.observation = obs

    def record_memory_snapshot(self, mem: InterviewMemory) -> None:
        if self.current:
            self.current.memory_snapshot = {
                "turn_count": mem.turn_count,
                "chapters_visited": list(mem.chapters_visited),
                "missing_concepts_count": len(mem.missing_concepts),
                "latest_score": mem.latest_score,
            }

    def record_state_snapshot(self, state: InterviewState) -> None:
        if self.current:
            self.current.state_snapshot = {
                "difficulty": state.current_difficulty,
                "remaining_budget": state.remaining_budget,
                "avg_score": round(state.avg_score, 3),
                "recent_avg": round(state.recent_avg_score, 3),
                "coverage_count": state.chapter_coverage_count,
                "llm_available": state.llm_available,
            }

    def record_action(self, action: ActionDecision) -> None:
        if self.current:
            self.current.action = action

    def record_evaluation(self, ev: EvaluationResult) -> None:
        if self.current:
            self.current.evaluation = ev

    def record_followup(self, plan: FollowUpPlan) -> None:
        if self.current:
            self.current.followup_plan = plan

    def record_tool(self, rec: ToolInvocationRecord) -> None:
        if self.current:
            self.current.tool_invocations.append(rec)

    def record_tools(self, recs: List[ToolInvocationRecord]) -> None:
        for r in recs:
            self.record_tool(r)

    def to_json(self) -> str:
        return json.dumps(
            [t.model_dump(mode="json") for t in self.traces],
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "total_turns": len(self.traces),
            "actions": [
                t.action.action.value if t.action else None
                for t in self.traces
            ],
            "provenances": [
                t.evaluation.provenance if t.evaluation else None
                for t in self.traces
            ],
            "fallback_count": sum(
                1
                for t in self.traces
                for ti in t.tool_invocations
                if ti.fallback_used
            ),
        }
