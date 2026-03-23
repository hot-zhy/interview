"""Rule-based evaluator (no LLM required)."""
import re
from typing import Dict, List
from difflib import SequenceMatcher

try:
    from rapidfuzz import fuzz as _rf_fuzz  # type: ignore
except Exception:  # pragma: no cover
    _rf_fuzz = None


def _ratio(a: str, b: str) -> int:
    a = (a or "").lower()
    b = (b or "").lower()
    if not a or not b:
        return 0
    if _rf_fuzz is not None:
        return int(_rf_fuzz.token_set_ratio(a, b))
    return int(SequenceMatcher(None, a, b).ratio() * 100)
from backend.schemas.evaluation import Scores


def evaluate_answer(
    question: str,
    correct_answer: str,
    user_answer: str
) -> Dict:
    """
    Evaluate answer using rule-based approach.
    
    Returns:
        {
            "scores": Scores,
            "overall_score": float,
            "feedback": str,
            "missing_points": List[str],
            "next_direction": str
        }
    """
    # Quality gate: very short or empty answers get zero across the board
    stripped = (user_answer or "").strip()
    if len(stripped) < 10:
        return {
            "scores": {"correctness": 0, "depth": 0, "clarity": 0, "practicality": 0, "tradeoffs": 0},
            "overall_score": 0.0,
            "feedback": "回答内容过短，无法进行有效评估。请尝试详细回答。",
            "missing_points": _extract_key_points(correct_answer)[:5],
            "next_direction": _suggest_next_direction(_extract_key_points(correct_answer)[:3], question),
        }

    # Extract key points from correct answer
    key_points = _extract_key_points(correct_answer)
    
    # Calculate coverage
    coverage_scores = _calculate_coverage(user_answer, key_points)
    
    # Calculate similarity
    similarity = _ratio(user_answer, correct_answer) / 100.0

    # If answer has zero coverage of key points, structure scores are meaningless
    has_substance = coverage_scores['coverage'] > 0.05 or similarity > 0.15

    # Calculate structure scores (only if answer has substance)
    structure_scores = _evaluate_structure(user_answer) if has_substance else {"clarity": 0, "practicality": 0, "tradeoffs": 0}
    
    # Combine scores
    correctness = (coverage_scores['coverage'] * 0.6 + similarity * 0.4)
    depth = coverage_scores['depth']
    clarity = structure_scores['clarity']
    practicality = structure_scores['practicality']
    tradeoffs = structure_scores['tradeoffs']
    
    # Clamp to [0, 1]
    correctness = max(0.0, min(1.0, correctness))
    depth = max(0.0, min(1.0, depth))
    clarity = max(0.0, min(1.0, clarity))
    practicality = max(0.0, min(1.0, practicality))
    tradeoffs = max(0.0, min(1.0, tradeoffs))
    
    # Overall score (weighted average)
    overall_score = (
        correctness * 0.30 +
        depth * 0.25 +
        clarity * 0.20 +
        practicality * 0.15 +
        tradeoffs * 0.10
    )
    
    # Identify missing points
    missing_points = _identify_missing_points(user_answer, key_points)
    
    # Generate feedback
    feedback = _generate_feedback(
        correctness, depth, clarity, practicality, tradeoffs,
        missing_points, key_points
    )
    
    # Next direction
    next_direction = _suggest_next_direction(missing_points, question)
    
    return {
        "scores": {
            "correctness": correctness,
            "depth": depth,
            "clarity": clarity,
            "practicality": practicality,
            "tradeoffs": tradeoffs
        },
        "overall_score": overall_score,
        "feedback": feedback,
        "missing_points": missing_points,
        "next_direction": next_direction
    }


def _extract_key_points(text: str) -> List[str]:
    """Extract key points from correct answer."""
    points = []
    
    # Split by common separators
    patterns = [
        r'\d+[\.、]\s*([^\n]+)',  # Numbered list
        r'[-•*]\s*([^\n]+)',      # Bullet points
        r'([^。；\n]+[。；])',     # Sentences
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text)
        for match in matches:
            point = match.group(1).strip()
            if len(point) > 5:  # Filter out very short points
                points.append(point)
    
    # If no structured points found, split by sentences
    if not points:
        sentences = re.split(r'[。；\n]', text)
        points = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    # If still empty, use whole text as one point
    if not points:
        points = [text]
    
    return points


def _calculate_coverage(user_answer: str, key_points: List[str]) -> Dict:
    """Calculate how well user answer covers key points."""
    user_lower = user_answer.lower()
    covered_count = 0
    total_coverage = 0.0
    max_depth = 0.0
    
    for point in key_points:
        point_lower = point.lower()
        # Check if point is covered
        # Use token-set ratio as a robust approximation when RapidFuzz is unavailable
        ratio = _ratio(user_lower, point_lower) / 100.0
        
        if ratio > 0.5:  # Threshold for coverage
            covered_count += 1
            total_coverage += ratio
            max_depth = max(max_depth, ratio)
    
    coverage = covered_count / len(key_points) if key_points else 0.0
    depth = total_coverage / len(key_points) if key_points else 0.0
    
    return {
        "coverage": coverage,
        "depth": depth
    }


def _evaluate_structure(user_answer: str) -> Dict:
    """Evaluate answer structure and quality indicators.

    Scores start at 0 — points are only awarded when specific
    patterns are detected, so garbage/irrelevant answers get 0.
    """
    # Clarity: structure indicators + explanation markers
    has_structure = bool(re.search(r'[1-9][\.、]|[-•*]|首先|其次|最后|第一|第二', user_answer))
    has_explanation = bool(re.search(r'因为|由于|所以|因此|原理|机制', user_answer))
    clarity = (0.5 if has_structure else 0) + (0.5 if has_explanation else 0)

    # Practicality: examples + code/implementation references
    has_example = bool(re.search(r'例如|比如|举例|实际|场景|案例', user_answer))
    has_code = bool(re.search(r'代码|实现|方法|函数|类|接口', user_answer))
    practicality = (0.5 if has_example else 0) + (0.5 if has_code else 0)

    # Tradeoffs: comparison/limitation discussion
    has_tradeoff = bool(re.search(
        r'优缺点|利弊|权衡|取舍|对比|比较|限制|不足|缺点',
        user_answer
    ))
    tradeoffs = 1.0 if has_tradeoff else 0.0

    return {
        "clarity": min(1.0, clarity),
        "practicality": min(1.0, practicality),
        "tradeoffs": min(1.0, tradeoffs)
    }


def _identify_missing_points(user_answer: str, key_points: List[str]) -> List[str]:
    """Identify key points not covered in user answer."""
    missing = []
    user_lower = user_answer.lower()
    
    for point in key_points:
        point_lower = point.lower()
        ratio = _ratio(user_lower, point_lower) / 100.0
        
        if ratio < 0.5:  # Not well covered
            missing.append(point)
    
    return missing[:5]  # Limit to top 5 missing points


def _generate_feedback(
    correctness: float,
    depth: float,
    clarity: float,
    practicality: float,
    tradeoffs: float,
    missing_points: List[str],
    key_points: List[str]
) -> str:
    """Generate feedback text."""
    feedback_parts = []
    
    # Overall assessment
    if correctness >= 0.8:
        feedback_parts.append("回答基本正确，覆盖了主要知识点。")
    elif correctness >= 0.6:
        feedback_parts.append("回答部分正确，但存在一些遗漏。")
    else:
        feedback_parts.append("回答不够准确，需要补充更多内容。")
    
    # Depth
    if depth < 0.6:
        feedback_parts.append("建议深入阐述原理和机制，增加技术深度。")
    
    # Clarity
    if clarity < 0.6:
        feedback_parts.append("建议使用更清晰的结构（如分点说明），便于理解。")
    
    # Practicality
    if practicality < 0.6:
        feedback_parts.append("建议补充实际应用场景或代码示例。")
    
    # Tradeoffs
    if tradeoffs < 0.5:
        feedback_parts.append("建议讨论优缺点、适用场景和权衡取舍。")
    
    # Missing points
    if missing_points:
        feedback_parts.append(f"\n缺失的关键点：\n" + "\n".join([f"- {mp}" for mp in missing_points[:3]]))
    
    return "\n".join(feedback_parts) if feedback_parts else "回答较为完整，继续保持！"


def _suggest_next_direction(missing_points: List[str], question: str) -> str:
    """Suggest next question direction."""
    if not missing_points:
        return "可以深入探讨相关的高级话题或实际应用场景。"
    
    # Extract keywords from missing points
    keywords = []
    for point in missing_points[:2]:
        # Extract important terms
        terms = re.findall(r'[\u4e00-\u9fa5]{2,}|[A-Z][a-z]+', point)
        keywords.extend(terms[:2])
    
    if keywords:
        return f"建议进一步了解：{', '.join(keywords[:3])}。"
    
    return "建议补充相关基础知识后再继续。"

