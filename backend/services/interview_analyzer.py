"""
Interview data analysis service.
Provides comprehensive statistical analysis of interview performance data.
"""
import math
from typing import Dict, List, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.models import InterviewSession, Evaluation, AskedQuestion
from collections import Counter, defaultdict


def analyze_interview_data(
    db: Session,
    session_id: int
) -> Dict:
    """
    Comprehensive analysis of interview data.
    
    Returns:
        Dictionary containing all analysis metrics and insights
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise ValueError("Session not found")
    
    # Get all evaluations
    evaluations = db.query(Evaluation).join(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).order_by(Evaluation.created_at).all()
    
    if not evaluations:
        return _empty_analysis()
    
    # Get all asked questions
    asked_questions = db.query(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).order_by(AskedQuestion.created_at).all()
    
    # Basic statistics
    basic_stats = _calculate_basic_statistics(evaluations, asked_questions)
    
    # Performance trends
    performance_trends = _analyze_performance_trends(evaluations)
    
    # Chapter-wise analysis
    chapter_analysis = _analyze_by_chapter(evaluations, asked_questions)
    
    # Difficulty progression
    difficulty_analysis = _analyze_difficulty_progression(asked_questions, evaluations)
    
    # Dimension analysis
    dimension_analysis = _analyze_dimensions(evaluations)
    
    # Stability metrics
    stability_metrics = _calculate_stability_metrics(evaluations)
    
    # Coverage metrics
    coverage_metrics = _calculate_coverage_metrics(asked_questions)
    
    # Improvement indicators
    improvement_indicators = _analyze_improvement(evaluations)
    
    return {
        "basic_statistics": basic_stats,
        "performance_trends": performance_trends,
        "chapter_analysis": chapter_analysis,
        "difficulty_analysis": difficulty_analysis,
        "dimension_analysis": dimension_analysis,
        "stability_metrics": stability_metrics,
        "coverage_metrics": coverage_metrics,
        "improvement_indicators": improvement_indicators
    }


def _calculate_basic_statistics(
    evaluations: List[Evaluation],
    asked_questions: List[AskedQuestion]
) -> Dict:
    """Calculate basic statistical metrics."""
    scores = [e.overall_score for e in evaluations]
    
    if not scores:
        return {}
    
    n = len(scores)
    mean_score = sum(scores) / n
    
    # Variance and standard deviation
    variance = sum((s - mean_score) ** 2 for s in scores) / n
    std_dev = math.sqrt(variance)
    
    # Median
    sorted_scores = sorted(scores)
    if n % 2 == 0:
        median = (sorted_scores[n//2 - 1] + sorted_scores[n//2]) / 2
    else:
        median = sorted_scores[n//2]
    
    # Min and max
    min_score = min(scores)
    max_score = max(scores)
    
    # Range
    score_range = max_score - min_score
    
    # Coefficient of variation (relative variability)
    cv = std_dev / mean_score if mean_score > 0 else 0
    
    return {
        "total_questions": n,
        "mean_score": round(mean_score, 3),
        "median_score": round(median, 3),
        "std_deviation": round(std_dev, 3),
        "min_score": round(min_score, 3),
        "max_score": round(max_score, 3),
        "score_range": round(score_range, 3),
        "coefficient_of_variation": round(cv, 3),
        "total_duration_minutes": _estimate_duration(asked_questions)
    }


def _analyze_performance_trends(evaluations: List[Evaluation]) -> Dict:
    """Analyze performance trends over time."""
    if len(evaluations) < 2:
        return {"trend": "insufficient_data"}
    
    scores = [e.overall_score for e in evaluations]
    
    # Linear regression for trend
    n = len(scores)
    x = list(range(1, n + 1))
    x_mean = sum(x) / n
    y_mean = sum(scores) / n
    
    numerator = sum((x[i] - x_mean) * (scores[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    
    slope = numerator / denominator if denominator > 0 else 0
    intercept = y_mean - slope * x_mean
    
    # Trend classification
    if slope > 0.01:
        trend = "improving"
    elif slope < -0.01:
        trend = "declining"
    else:
        trend = "stable"
    
    # Early vs late performance
    if n >= 4:
        early_avg = sum(scores[:n//2]) / (n//2)
        late_avg = sum(scores[n//2:]) / (n - n//2)
        early_late_diff = late_avg - early_avg
    else:
        early_avg = None
        late_avg = None
        early_late_diff = None
    
    # Recent performance (last 3)
    recent_avg = sum(scores[-3:]) / min(3, len(scores))
    
    return {
        "trend": trend,
        "slope": round(slope, 4),
        "intercept": round(intercept, 3),
        "early_average": round(early_avg, 3) if early_avg else None,
        "late_average": round(late_avg, 3) if late_avg else None,
        "early_late_difference": round(early_late_diff, 3) if early_late_diff is not None else None,
        "recent_average": round(recent_avg, 3)
    }


def _analyze_by_chapter(
    evaluations: List[Evaluation],
    asked_questions: List[AskedQuestion]
) -> Dict:
    """Analyze performance by knowledge chapter."""
    # Map evaluations to chapters
    chapter_scores = defaultdict(list)
    chapter_counts = Counter()
    
    for aq, eval_obj in zip(asked_questions, evaluations):
        if aq.topic:
            chapter_scores[aq.topic].append(eval_obj.overall_score)
            chapter_counts[aq.topic] += 1
    
    # Calculate statistics per chapter
    chapter_stats = {}
    for chapter, scores in chapter_scores.items():
        if scores:
            chapter_stats[chapter] = {
                "count": len(scores),
                "mean_score": round(sum(scores) / len(scores), 3),
                "min_score": round(min(scores), 3),
                "max_score": round(max(scores), 3),
                "std_dev": round(math.sqrt(sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)), 3)
            }
    
    # Identify strongest and weakest chapters
    if chapter_stats:
        strongest = max(chapter_stats.items(), key=lambda x: x[1]["mean_score"])
        weakest = min(chapter_stats.items(), key=lambda x: x[1]["mean_score"])
    else:
        strongest = None
        weakest = None
    
    return {
        "chapter_statistics": chapter_stats,
        "strongest_chapter": strongest[0] if strongest else None,
        "strongest_chapter_score": round(strongest[1]["mean_score"], 3) if strongest else None,
        "weakest_chapter": weakest[0] if weakest else None,
        "weakest_chapter_score": round(weakest[1]["mean_score"], 3) if weakest else None,
        "total_chapters_covered": len(chapter_stats)
    }


def _analyze_difficulty_progression(
    asked_questions: List[AskedQuestion],
    evaluations: List[Evaluation]
) -> Dict:
    """Analyze how difficulty and performance interact."""
    if not asked_questions or not evaluations:
        return {}
    
    # Pair questions with evaluations
    difficulty_scores = []
    for aq, eval_obj in zip(asked_questions, evaluations):
        if aq.difficulty and eval_obj.overall_score is not None:
            difficulty_scores.append((aq.difficulty, eval_obj.overall_score))
    
    if not difficulty_scores:
        return {}
    
    # Group by difficulty
    difficulty_groups = defaultdict(list)
    for diff, score in difficulty_scores:
        difficulty_groups[diff].append(score)
    
    # Calculate average score per difficulty level
    difficulty_avg_scores = {}
    for diff, scores in difficulty_groups.items():
        difficulty_avg_scores[diff] = round(sum(scores) / len(scores), 3)
    
    # Difficulty progression
    difficulties = [aq.difficulty for aq in asked_questions if aq.difficulty]
    if len(difficulties) >= 2:
        difficulty_trend = "increasing" if difficulties[-1] > difficulties[0] else "decreasing" if difficulties[-1] < difficulties[0] else "stable"
        difficulty_range = max(difficulties) - min(difficulties)
    else:
        difficulty_trend = "stable"
        difficulty_range = 0
    
    # Correlation between difficulty and score
    if len(difficulty_scores) >= 3:
        diff_values = [d for d, _ in difficulty_scores]
        score_values = [s for _, s in difficulty_scores]
        correlation = _calculate_correlation(diff_values, score_values)
    else:
        correlation = None
    
    return {
        "difficulty_levels_used": sorted(difficulty_groups.keys()),
        "average_scores_by_difficulty": difficulty_avg_scores,
        "difficulty_trend": difficulty_trend,
        "difficulty_range": difficulty_range,
        "difficulty_score_correlation": round(correlation, 3) if correlation is not None else None
    }


def _analyze_dimensions(evaluations: List[Evaluation]) -> Dict:
    """Analyze performance across five evaluation dimensions."""
    dimension_scores = {
        "correctness": [],
        "depth": [],
        "clarity": [],
        "practicality": [],
        "tradeoffs": []
    }
    
    for eval_obj in evaluations:
        scores = eval_obj.scores_json
        for dim in dimension_scores.keys():
            if dim in scores:
                dimension_scores[dim].append(scores[dim])
    
    dimension_stats = {}
    for dim, scores in dimension_scores.items():
        if scores:
            dimension_stats[dim] = {
                "mean": round(sum(scores) / len(scores), 3),
                "std_dev": round(math.sqrt(sum((s - sum(scores)/len(scores))**2 for s in scores) / len(scores)), 3),
                "min": round(min(scores), 3),
                "max": round(max(scores), 3)
            }
    
    # Identify strongest and weakest dimensions
    if dimension_stats:
        strongest_dim = max(dimension_stats.items(), key=lambda x: x[1]["mean"])
        weakest_dim = min(dimension_stats.items(), key=lambda x: x[1]["mean"])
    else:
        strongest_dim = None
        weakest_dim = None
    
    return {
        "dimension_statistics": dimension_stats,
        "strongest_dimension": strongest_dim[0] if strongest_dim else None,
        "weakest_dimension": weakest_dim[0] if weakest_dim else None
    }


def _calculate_stability_metrics(evaluations: List[Evaluation]) -> Dict:
    """Calculate stability and consistency metrics."""
    scores = [e.overall_score for e in evaluations]
    
    if len(scores) < 2:
        return {"stability": "insufficient_data"}
    
    mean_score = sum(scores) / len(scores)
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    std_dev = math.sqrt(variance)
    
    # Coefficient of variation
    cv = std_dev / mean_score if mean_score > 0 else 0
    
    # Stability classification
    if cv < 0.15:
        stability = "highly_stable"
    elif cv < 0.25:
        stability = "stable"
    elif cv < 0.35:
        stability = "moderate"
    else:
        stability = "unstable"
    
    # Score consistency (percentage within one std dev)
    within_one_std = sum(1 for s in scores if abs(s - mean_score) <= std_dev)
    consistency_ratio = within_one_std / len(scores)
    
    return {
        "stability": stability,
        "coefficient_of_variation": round(cv, 3),
        "standard_deviation": round(std_dev, 3),
        "consistency_ratio": round(consistency_ratio, 3),
        "scores_within_one_std": within_one_std,
        "total_scores": len(scores)
    }


def _calculate_coverage_metrics(asked_questions: List[AskedQuestion]) -> Dict:
    """Calculate coverage metrics for chapters and difficulties."""
    chapters = set(aq.topic for aq in asked_questions if aq.topic)
    difficulties = set(aq.difficulty for aq in asked_questions if aq.difficulty)
    
    # Chapter diversity (Shannon entropy)
    chapter_counts = Counter(aq.topic for aq in asked_questions if aq.topic)
    if chapter_counts:
        total = sum(chapter_counts.values())
        entropy = -sum((count/total) * math.log2(count/total) for count in chapter_counts.values() if count > 0)
        max_entropy = math.log2(len(chapter_counts))
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
    else:
        entropy = 0
        normalized_entropy = 0
    
    return {
        "chapters_covered": len(chapters),
        "difficulty_levels_covered": len(difficulties),
        "chapter_diversity_entropy": round(entropy, 3),
        "normalized_diversity": round(normalized_entropy, 3),
        "chapter_distribution": dict(chapter_counts)
    }


def _analyze_improvement(evaluations: List[Evaluation]) -> Dict:
    """Analyze improvement indicators."""
    if len(evaluations) < 3:
        return {"improvement": "insufficient_data"}
    
    scores = [e.overall_score for e in evaluations]
    
    # First half vs second half
    n = len(scores)
    first_half = scores[:n//2]
    second_half = scores[n//2:]
    
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    improvement_ratio = (second_avg - first_avg) / first_avg if first_avg > 0 else 0
    
    # Consecutive improvements
    consecutive_improvements = 0
    max_consecutive = 0
    current_streak = 0
    
    for i in range(1, len(scores)):
        if scores[i] > scores[i-1]:
            current_streak += 1
            consecutive_improvements += 1
            max_consecutive = max(max_consecutive, current_streak)
        else:
            current_streak = 0
    
    # Improvement classification
    if improvement_ratio > 0.1:
        improvement_status = "significant_improvement"
    elif improvement_ratio > 0.05:
        improvement_status = "moderate_improvement"
    elif improvement_ratio > -0.05:
        improvement_status = "stable"
    elif improvement_ratio > -0.1:
        improvement_status = "moderate_decline"
    else:
        improvement_status = "significant_decline"
    
    return {
        "improvement_status": improvement_status,
        "improvement_ratio": round(improvement_ratio, 3),
        "first_half_average": round(first_avg, 3),
        "second_half_average": round(second_avg, 3),
        "consecutive_improvements": consecutive_improvements,
        "max_consecutive_improvements": max_consecutive
    }


def _calculate_correlation(x: List[float], y: List[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0
    
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    x_variance = sum((x[i] - x_mean) ** 2 for i in range(n))
    y_variance = sum((y[i] - y_mean) ** 2 for i in range(n))
    
    denominator = math.sqrt(x_variance * y_variance)
    
    if denominator == 0:
        return 0.0
    
    return numerator / denominator


def _estimate_duration(asked_questions: List[AskedQuestion]) -> Optional[float]:
    """Estimate interview duration in minutes."""
    if not asked_questions:
        return None
    
    # Estimate based on timestamps
    first_question = min(aq.created_at for aq in asked_questions)
    last_question = max(aq.created_at for aq in asked_questions)
    
    duration_seconds = (last_question - first_question).total_seconds()
    duration_minutes = duration_seconds / 60
    
    return round(duration_minutes, 1)


def _empty_analysis() -> Dict:
    """Return empty analysis structure."""
    return {
        "basic_statistics": {},
        "performance_trends": {"trend": "no_data"},
        "chapter_analysis": {},
        "difficulty_analysis": {},
        "dimension_analysis": {},
        "stability_metrics": {"stability": "no_data"},
        "coverage_metrics": {},
        "improvement_indicators": {"improvement": "no_data"}
    }

