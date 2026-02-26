"""
自适应面试算法模块
包含智能题目选择、难度调整、结束判断等核心算法
"""
import math
from typing import List, Optional, Dict, Tuple
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.models import (
    InterviewSession, AskedQuestion, Evaluation, QuestionBank
)
from backend.core.config import settings

try:
    from rapidfuzz import fuzz as _rf_fuzz  # type: ignore
except Exception:  # pragma: no cover
    _rf_fuzz = None


def _partial_ratio(a: str, b: str) -> int:
    a = (a or "").lower()
    b = (b or "").lower()
    if not a or not b:
        return 0
    if _rf_fuzz is not None:
        return int(_rf_fuzz.partial_ratio(a, b))
    return int(SequenceMatcher(None, a, b).ratio() * 100)


class AdaptiveInterviewEngine:
    """自适应面试引擎"""
    
    def __init__(self, db: Session, session: InterviewSession):
        self.db = db
        self.session = session
        self.followup_limit = 2  # 每个问题最多追问2次
        # 轮次：以用户设置的 total_rounds 为基准
        user_rounds = session.total_rounds or 10
        min_ratio = float(getattr(settings, "min_rounds_ratio", 0.5))
        max_ratio = float(getattr(settings, "max_rounds_ratio", 1.2))
        max_cap = int(getattr(settings, "max_rounds_cap", 20))
        self.min_rounds = max(3, int(user_rounds * min_ratio))
        self.max_rounds = min(max_cap, int(user_rounds * max_ratio))
        self.user_total_rounds = user_rounds  # 用户期望轮数（硬上限）
        self.window_size = 3  # 滑动窗口大小（用于计算最近N次表现）
    
    def should_ask_followup(
        self,
        asked_question_id: int,
        evaluation_score: float,
        missing_points: List[str]
    ) -> Tuple[bool, str]:
        """
        判断是否应该追问
        
        Returns:
            (should_followup, reason)
        """
        # 检查该问题已经追问的次数
        followup_count = self._count_followups_for_question(asked_question_id)
        
        if followup_count >= self.followup_limit:
            return False, f"已达到追问上限（{self.followup_limit}次）"
        
        # 如果分数太低且有缺失点，可以追问
        if evaluation_score < 0.6 and len(missing_points) > 0:
            # 检查是否已经问过相同的问题
            if self._has_similar_followup(asked_question_id, missing_points[0]):
                return False, "已问过类似问题"
            return True, "分数较低且有缺失点，适合追问"
        
        # 如果分数在0.6-0.7之间，有缺失点，且追问次数<1，可以追问一次
        if 0.6 <= evaluation_score < 0.7 and len(missing_points) > 0 and followup_count < 1:
            return True, "分数中等，首次追问以深入了解"
        
        return False, "分数达标或无需追问"
    
    def should_end_interview(self) -> Tuple[bool, str]:
        """
        判断是否应该结束面试。
        
        结束条件（满足任一即结束）：
        1. 达到用户设置的 total_rounds（硬上限）
        2. 达到 max_rounds（自适应上限，略高于用户设置）
        3. 提前结束：表现优秀且稳定 / 表现很差且无改善 / 覆盖充分且稳定
        4. 未达 min_rounds 前不提前结束
        
        Returns:
            (should_end, reason)
        """
        asked_questions = self.db.query(AskedQuestion).filter(
            AskedQuestion.session_id == self.session.id
        ).all()
        
        if not asked_questions:
            return False, "尚未开始"
        
        evaluations = [aq.evaluation for aq in asked_questions if aq.evaluation]
        
        if not evaluations:
            return False, "尚无评估结果"
        
        current = self.session.current_round
        
        # 1. 硬上限：用户设置的轮数
        if current >= self.user_total_rounds:
            return True, f"已达到设定轮数（{self.user_total_rounds}轮）"
        
        # 2. 自适应上限
        if current >= self.max_rounds:
            return True, f"已达到最大轮次（{self.max_rounds}轮）"
        
        # 3. 未达最少轮次，不提前结束
        if current < self.min_rounds:
            return False, f"未达最少轮次（{self.min_rounds}轮）"
        
        # 4. 计算表现指标
        scores = [float(e.overall_score) for e in evaluations]
        avg_score = sum(scores) / len(scores)
        recent_scores = scores[-self.window_size:] if len(scores) >= self.window_size else scores
        recent_avg = sum(recent_scores) / len(recent_scores)
        
        std_dev = 0.0
        if len(scores) >= 3:
            variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
            std_dev = math.sqrt(variance)
        
        difficulties = [aq.difficulty for aq in asked_questions]
        difficulty_range = max(difficulties) - min(difficulties) if difficulties else 0
        chapters = set(aq.topic for aq in asked_questions if aq.topic)
        chapter_coverage = len(chapters)
        
        # 5. 提前结束条件
        # 5a. 表现优秀且稳定
        if avg_score >= 0.85 and recent_avg >= 0.85 and std_dev < 0.15:
            return True, f"表现优秀且稳定（平均分{avg_score:.2f}），提前结束"
        
        # 5b. 表现很差且无改善
        if avg_score < 0.4 and recent_avg < 0.4:
            return True, f"表现较差且无改善（平均分{avg_score:.2f}），结束面试"
        
        # 5c. 覆盖充分且表现稳定（难度跨度≥2，章节≥3，最近平均≥0.7）
        if std_dev < 0.2 and difficulty_range >= 2 and chapter_coverage >= 3 and recent_avg >= 0.7:
            return True, f"表现稳定、覆盖充分（平均分{recent_avg:.2f}），结束面试"
        
        return False, f"继续面试（当前{current}轮，平均分{avg_score:.2f}）"
    
    def calculate_adaptive_difficulty(self) -> int:
        """
        计算自适应难度（基于滑动窗口和趋势分析）
        
        Returns:
            建议的难度等级 (1-5)
        """
        # Strategy switch (backward compatible default: "heuristic")
        if getattr(settings, "difficulty_strategy", "heuristic") == "target_score_control":
            return self._calculate_difficulty_target_score_control()

        # 获取最近的评估
        recent_asked = self.db.query(AskedQuestion).filter(
            AskedQuestion.session_id == self.session.id
        ).order_by(AskedQuestion.created_at.desc()).limit(self.window_size).all()
        
        if not recent_asked:
            return self.session.level
        
        # 获取评估分数
        scores = []
        difficulties = []
        for aq in reversed(recent_asked):  # 从旧到新
            if aq.evaluation:
                scores.append(aq.evaluation.overall_score)
                difficulties.append(aq.difficulty)
        
        if not scores:
            return self.session.level
        
        # 计算加权平均分（越近的权重越大）
        weights = [i + 1 for i in range(len(scores))]
        weighted_avg = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        
        # 计算趋势（最近两次的差异）
        trend = 0
        if len(scores) >= 2:
            trend = scores[-1] - scores[-2]
        
        # 获取当前难度
        current_difficulty = difficulties[-1] if difficulties else self.session.level
        
        # 自适应调整
        # 如果加权平均分高且趋势向上，提高难度
        if weighted_avg >= 0.8 and trend > 0.1:
            new_difficulty = min(current_difficulty + 1, 5)
        # 如果加权平均分高但趋势稳定，保持或微调
        elif weighted_avg >= 0.75:
            new_difficulty = current_difficulty
        # 如果加权平均分中等，根据趋势调整
        elif weighted_avg >= 0.6:
            if trend > 0.05:
                new_difficulty = min(current_difficulty + 1, 5)
            elif trend < -0.05:
                new_difficulty = max(current_difficulty - 1, 1)
            else:
                new_difficulty = current_difficulty
        # 如果加权平均分低，降低难度
        else:
            new_difficulty = max(current_difficulty - 1, 1)
        
        return new_difficulty

    def _calculate_difficulty_target_score_control(self) -> int:
        """
        A slightly more advanced difficulty controller:
        - Targets a desired score level (settings.target_score)
        - Uses proportional error + trend (derivative-like) to adjust difficulty
        - Smooths using a small window (self.window_size)
        """
        recent_asked = self.db.query(AskedQuestion).filter(
            AskedQuestion.session_id == self.session.id
        ).order_by(AskedQuestion.created_at.desc()).limit(self.window_size).all()

        if not recent_asked:
            return self.session.level

        scores: List[float] = []
        difficulties: List[int] = []
        for aq in reversed(recent_asked):
            if aq.evaluation:
                scores.append(float(aq.evaluation.overall_score))
                difficulties.append(int(aq.difficulty))

        if not scores:
            return self.session.level

        current_difficulty = difficulties[-1] if difficulties else self.session.level
        target = float(getattr(settings, "target_score", 0.70))
        kp = float(getattr(settings, "difficulty_kp", 1.2))
        kd = float(getattr(settings, "difficulty_kd", 0.6))
        step = float(getattr(settings, "difficulty_step", 1.0))

        # Window average and trend
        avg = sum(scores) / len(scores)
        trend = scores[-1] - scores[-2] if len(scores) >= 2 else 0.0

        # Control signal (positive => increase difficulty if avg > target)
        error = avg - target
        delta = kp * error + kd * trend

        # Convert to discrete step with clipping
        # We cap per-update magnitude to avoid oscillation
        delta = max(-step, min(step, delta))
        if abs(delta) < 0.15:
            return current_difficulty

        new_difficulty = current_difficulty + (1 if delta > 0 else -1)
        return max(1, min(5, new_difficulty))
    
    def _count_followups_for_question(self, asked_question_id: int) -> int:
        """统计某个问题被追问的次数"""
        # 获取该问题的所有回答轮次
        asked_q = self.db.query(AskedQuestion).filter(
            AskedQuestion.id == asked_question_id
        ).first()
        
        if not asked_q:
            return 0
        
        # 统计该问题之后，在创建下一个新问题之前的回答次数
        # 这需要检查 InterviewTurn 中 candidate 角色的连续回答
        # 简化实现：检查该问题之后是否有其他问题
        next_questions = self.db.query(AskedQuestion).filter(
            AskedQuestion.session_id == self.session.id,
            AskedQuestion.created_at > asked_q.created_at
        ).count()
        
        # 如果下一个问题还没创建，说明还在追问阶段
        # 通过检查该问题之后是否有新的 AskedQuestion 来判断
        # 更准确的方法：检查该问题的 evaluation 是否被更新过多次
        # 或者检查该问题之后是否有新的 AskedQuestion
        
        # 简化：检查该问题之后是否有新的问题
        # 如果没有新问题，说明还在追问，追问次数 = 该问题之后的回答次数
        turns_after = self.db.query(func.count()).select_from(
            self.db.query(AskedQuestion).filter(
                AskedQuestion.session_id == self.session.id,
                AskedQuestion.created_at > asked_q.created_at
            ).subquery()
        ).scalar() or 0
        
        # 如果之后没有新问题，说明还在追问
        # 追问次数 = 该问题之后的 candidate 回答次数
        if turns_after == 0:
            # 统计该问题之后的 candidate 回答
            from backend.db.models import InterviewTurn
            candidate_turns = self.db.query(InterviewTurn).filter(
                InterviewTurn.session_id == self.session.id,
                InterviewTurn.role == "candidate",
                InterviewTurn.created_at > asked_q.created_at
            ).count()
            return candidate_turns
        
        return 0
    
    def _has_similar_followup(self, asked_question_id: int, missing_point: str) -> bool:
        """检查是否已经问过类似的问题"""
        asked_q = self.db.query(AskedQuestion).filter(
            AskedQuestion.id == asked_question_id
        ).first()
        
        if not asked_q:
            return False
        
        # 检查该问题之后的 interviewer 消息是否包含类似的 missing_point
        from backend.db.models import InterviewTurn
        
        interviewer_turns = self.db.query(InterviewTurn).filter(
            InterviewTurn.session_id == self.session.id,
            InterviewTurn.role == "interviewer",
            InterviewTurn.created_at > asked_q.created_at
        ).all()
        
        for turn in interviewer_turns:
            # 检查相似度
            similarity = _partial_ratio(missing_point, turn.content)
            if similarity > 70:  # 70% 相似度阈值
                return True
        
        return False

