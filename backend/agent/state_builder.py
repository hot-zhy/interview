"""StateBuilder: convert observation + memory + constraints into InterviewState."""
from __future__ import annotations

import math
from collections import Counter
from typing import Optional

from backend.agent.models import (
    EvaluationResult,
    InterviewMemory,
    InterviewState,
)
from backend.core.config import settings


class StateBuilder:
    """Constructs a compressed InterviewState from InterviewMemory."""

    @staticmethod
    def build(
        memory: InterviewMemory,
        session_total_rounds: int,
        current_round: int,
        current_difficulty: int,
        current_asked_question_id: Optional[str] = None,
        latest_evaluation: Optional[EvaluationResult] = None,
        llm_available: bool = False,
    ) -> InterviewState:
        scores = memory.score_history
        window = int(getattr(settings, "window_size", 3) if hasattr(settings, "window_size") else 3)

        # Aggregated metrics
        avg_score = sum(scores) / len(scores) if scores else 0.0
        recent = scores[-window:] if len(scores) >= window else scores
        recent_avg = sum(recent) / len(recent) if recent else 0.0

        std_dev = 0.0
        if len(scores) >= 3:
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            std_dev = math.sqrt(variance)

        diffs = memory.difficulty_trajectory
        diff_range = (max(diffs) - min(diffs)) if diffs else 0

        coverage = dict(Counter(memory.chapter_trace))

        # Follow-up budget for current question
        fup_budget = 2
        if current_asked_question_id:
            used = memory.followup_counts.get(str(current_asked_question_id), 0)
            fup_budget = max(0, 2 - used)

        remaining = max(0, session_total_rounds - current_round)

        multi_judge = int(getattr(settings, "llm_multi_judge_count", 1)) > 1
        cot = bool(getattr(settings, "llm_use_cot", False))

        return InterviewState(
            current_difficulty=current_difficulty,
            coverage_state=coverage,
            missing_concept_state=list(memory.missing_concepts),
            remaining_budget=remaining,
            followup_budget_for_current=fup_budget,
            resume_prior=memory.resume_skills,
            latest_evaluation=latest_evaluation,
            latest_hint=memory.latest_hint,
            avg_score=avg_score,
            recent_avg_score=recent_avg,
            score_std=std_dev,
            difficulty_range=diff_range,
            chapter_coverage_count=len(coverage),
            llm_available=llm_available,
            multi_judge_enabled=multi_judge,
            cot_enabled=cot,
        )
