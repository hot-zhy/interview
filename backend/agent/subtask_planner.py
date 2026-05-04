"""WideSeek-style evaluation subtask planning."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from backend.agent.models import EvaluationResult
from backend.core.config import settings


@dataclass
class EvalSubtask:
    task_id: str
    focus: str
    prompt_hint: str


def build_eval_subtasks(question: str, user_answer: str) -> List[EvalSubtask]:
    """Build a small set of parallel evaluation perspectives."""
    if not bool(getattr(settings, "enable_wide_subtask_planner", False)):
        return []
    hints = [
        ("correctness", "重点核查事实正确性、概念定义和关键遗漏"),
        ("depth", "重点核查回答是否有原理层解释与边界条件讨论"),
        ("practicality_tradeoffs", "重点核查工程实践可落地性与权衡分析"),
    ]
    tasks: List[EvalSubtask] = []
    for idx, (focus, hint) in enumerate(hints[: max(1, int(getattr(settings, "wide_subtask_max_workers", 3)))], start=1):
        tasks.append(
            EvalSubtask(
                task_id=f"eval_subtask_{idx}",
                focus=focus,
                prompt_hint=f"问题: {question[:160]} | 回答摘要: {user_answer[:200]} | {hint}",
            )
        )
    return tasks


def summarize_subtask_plan(tasks: List[EvalSubtask]) -> Dict:
    return {
        "enabled": bool(tasks),
        "count": len(tasks),
        "focuses": [t.focus for t in tasks],
        "hints": [t.prompt_hint for t in tasks],
    }


def annotate_result_with_subtasks(result: EvaluationResult, plan_summary: Dict) -> None:
    """Attach a concise explanation for traceability."""
    if not plan_summary.get("enabled"):
        return
    result.policy_meta = result.policy_meta or {}
    result.policy_meta["subtask_plan"] = {
        "count": int(plan_summary.get("count", 0)),
        "focuses": list(plan_summary.get("focuses", [])),
    }

