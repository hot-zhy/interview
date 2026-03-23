"""Structured data models for the agentic interview framework.

These models define the observation, memory, state, action, and trace
structures used by the agent controller.  They are purely additive and
do not affect existing schemas or database tables.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Action space
# ---------------------------------------------------------------------------

class ActionType(str, enum.Enum):
    ASK_NEXT = "ask_next"
    FOLLOW_UP = "follow_up"
    TERMINATE = "terminate"


class ActionDecision(BaseModel):
    action: ActionType
    reason: str = ""
    new_difficulty: Optional[int] = None
    selected_question_id: Optional[str] = None
    followup_text: Optional[str] = None


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """Raw observation produced at the end of a turn."""
    turn_number: int
    question_id: Optional[str] = None
    question_text: str = ""
    question_chapter: str = ""
    question_difficulty: int = 1
    candidate_answer: str = ""
    answer_type: str = "text"  # "text" | "audio"
    audio_analysis: Optional[Dict[str, Any]] = None
    expression_analysis: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Evaluation result (tool output)
# ---------------------------------------------------------------------------

class EvaluationResult(BaseModel):
    scores: Dict[str, float] = Field(default_factory=dict)
    overall_score: float = 0.0
    feedback: str = ""
    missing_points: List[str] = Field(default_factory=list)
    next_direction: Optional[str] = None
    reasoning: Optional[str] = None
    provenance: str = "unknown"  # "rule" | "llm" | "hybrid" | "fallback"


# ---------------------------------------------------------------------------
# Follow-up plan
# ---------------------------------------------------------------------------

class FollowUpPlan(BaseModel):
    should_followup: bool = False
    reason: str = ""
    followup_text: str = ""
    source: str = "none"  # "llm" | "template" | "none"


# ---------------------------------------------------------------------------
# Interview memory
# ---------------------------------------------------------------------------

class InterviewMemory(BaseModel):
    """Persistent interview memory accumulated across turns."""
    session_id: int
    # Histories (append-only)
    score_history: List[float] = Field(default_factory=list)
    difficulty_trajectory: List[int] = Field(default_factory=list)
    chapter_trace: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    followup_counts: Dict[str, int] = Field(default_factory=dict)  # asked_question_id -> count
    next_direction_hints: List[str] = Field(default_factory=list)
    # Resume prior (set once at session start)
    resume_skills: Optional[List[str]] = None
    # Evaluation provenance log
    provenance_log: List[str] = Field(default_factory=list)
    # Turn-level records (lightweight)
    turn_evaluations: List[Dict[str, Any]] = Field(default_factory=list)

    def append_turn(
        self,
        score: float,
        difficulty: int,
        chapter: str,
        new_missing: List[str],
        next_direction: Optional[str],
        provenance: str,
        asked_question_id: Optional[str] = None,
    ) -> None:
        self.score_history.append(score)
        self.difficulty_trajectory.append(difficulty)
        self.chapter_trace.append(chapter)
        for concept in new_missing:
            if concept and concept not in self.missing_concepts:
                self.missing_concepts.append(concept)
        if next_direction:
            self.next_direction_hints.append(next_direction)
        self.provenance_log.append(provenance)

    def record_followup(self, asked_question_id: str) -> None:
        key = str(asked_question_id)
        self.followup_counts[key] = self.followup_counts.get(key, 0) + 1

    @property
    def turn_count(self) -> int:
        return len(self.score_history)

    @property
    def chapters_visited(self) -> set:
        return set(self.chapter_trace)

    @property
    def latest_score(self) -> Optional[float]:
        return self.score_history[-1] if self.score_history else None

    @property
    def latest_hint(self) -> Optional[str]:
        return self.next_direction_hints[-1] if self.next_direction_hints else None


# ---------------------------------------------------------------------------
# Interview state (compressed from memory)
# ---------------------------------------------------------------------------

class InterviewState(BaseModel):
    """Compressed state derived from memory + session constraints."""
    current_difficulty: int = 3
    coverage_state: Dict[str, int] = Field(default_factory=dict)  # chapter -> visit count
    missing_concept_state: List[str] = Field(default_factory=list)
    remaining_budget: int = 10
    followup_budget_for_current: int = 2  # remaining follow-ups for current question
    resume_prior: Optional[List[str]] = None
    latest_evaluation: Optional[EvaluationResult] = None
    latest_hint: Optional[str] = None
    # Aggregated metrics
    avg_score: float = 0.0
    recent_avg_score: float = 0.0
    score_std: float = 0.0
    difficulty_range: int = 0
    chapter_coverage_count: int = 0
    # Feature availability
    llm_available: bool = False
    multi_judge_enabled: bool = False
    cot_enabled: bool = False


# ---------------------------------------------------------------------------
# Tool invocation record
# ---------------------------------------------------------------------------

class ToolInvocationRecord(BaseModel):
    tool_name: str
    input_summary: str = ""
    output_summary: str = ""
    success: bool = True
    fallback_used: bool = False
    duration_ms: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Agent trace (per-turn)
# ---------------------------------------------------------------------------

class AgentTrace(BaseModel):
    """Structured trace for a single agent turn."""
    turn_number: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    observation: Optional[Observation] = None
    memory_snapshot: Optional[Dict[str, Any]] = None
    state_snapshot: Optional[Dict[str, Any]] = None
    action: Optional[ActionDecision] = None
    evaluation: Optional[EvaluationResult] = None
    followup_plan: Optional[FollowUpPlan] = None
    tool_invocations: List[ToolInvocationRecord] = Field(default_factory=list)
    notes: str = ""
