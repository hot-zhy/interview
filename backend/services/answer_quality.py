"""Lightweight answer quality gate for interview flow."""
import re
from typing import Dict


_MEANINGLESS_WORDS = {
    "1",
    "11",
    "111",
    "123",
    "test",
    "asdf",
    "qwer",
    "abc",
    "aaa",
    "???",
    "...",
    "无",
    "随便",
    "乱写",
    "哈哈",
    "呵呵",
}

_LOW_EFFORT_WORDS = {
    "不知道",
    "不会",
    "不清楚",
    "忘了",
    "没学过",
    "不懂",
    "不知道怎么说",
}


def classify_answer_quality(answer: str) -> Dict:
    """Classify whether an answer is useful enough for normal evaluation.

    The goal is not to judge correctness. It only catches empty, spammy, or
    obviously non-serious answers before they go through the full LLM path.
    """
    text = (answer or "").strip()
    normalized = re.sub(r"\s+", "", text).lower()

    if not normalized:
        return {
            "category": "empty",
            "meaningful": False,
            "severity": "invalid",
            "reason": "回答为空",
        }

    if normalized in _MEANINGLESS_WORDS:
        return {
            "category": "meaningless",
            "meaningful": False,
            "severity": "invalid",
            "reason": "回答明显不是有效面试回答",
        }

    if len(normalized) <= 2 and not re.search(r"[\u4e00-\u9fa5]{2,}|[a-zA-Z]{3,}", normalized):
        return {
            "category": "meaningless",
            "meaningful": False,
            "severity": "invalid",
            "reason": "回答过短且缺少可评估信息",
        }

    unique_chars = set(normalized)
    if len(normalized) >= 4 and len(unique_chars) <= 2:
        return {
            "category": "meaningless",
            "meaningful": False,
            "severity": "invalid",
            "reason": "回答疑似重复字符或无意义输入",
        }

    if normalized in _LOW_EFFORT_WORDS:
        return {
            "category": "low_effort",
            "meaningful": True,
            "severity": "weak",
            "reason": "候选人表示不了解，需要引导式追问",
        }

    if len(normalized) < 10:
        return {
            "category": "too_short",
            "meaningful": True,
            "severity": "weak",
            "reason": "回答较短，需要进一步展开",
        }

    return {
        "category": "normal",
        "meaningful": True,
        "severity": "normal",
        "reason": "",
    }

