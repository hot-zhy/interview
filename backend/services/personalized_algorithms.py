"""
个性化面试算法模块
基于论文中的算法实现，让用户感受到个性化面试体验

参考论文与框架：
- IRT/CAT (Embretson & Reise): Fisher Information 最大信息选题，能力估计
- EDGE (Verma 2025): Misconception-aware 能力估计、知识缺口诊断
- BanditCAT / Thompson Sampling: 探索-利用平衡，章节选择
- UCB (Auer et al.): 多臂老虎机选题，控制探索
- Knowledge Tracing (Corbett & Anderson): 技能掌握度追踪
- Gap-Focused Question Generation: 针对回答缺口的追问生成
"""
import math
import random
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

try:
    from rapidfuzz import fuzz as _rf_fuzz
except Exception:
    _rf_fuzz = None


def _partial_ratio(a: str, b: str) -> int:
    a = (a or "").lower()
    b = (b or "").lower()
    if not a or not b:
        return 0
    if _rf_fuzz is not None:
        return int(_rf_fuzz.partial_ratio(a, b))
    from difflib import SequenceMatcher
    return int(SequenceMatcher(None, a, b).ratio() * 100)


@dataclass
class SkillMasteryProfile:
    """技能掌握度画像（Knowledge Tracing 简化版）"""
    chapter_scores: Dict[str, List[float]] = field(default_factory=dict)
    chapter_counts: Dict[str, int] = field(default_factory=dict)
    
    def update(self, chapter: str, score: float):
        if chapter not in self.chapter_scores:
            self.chapter_scores[chapter] = []
            self.chapter_counts[chapter] = 0
        self.chapter_scores[chapter].append(score)
        self.chapter_counts[chapter] += 1
        # 只保留最近 5 次
        if len(self.chapter_scores[chapter]) > 5:
            self.chapter_scores[chapter] = self.chapter_scores[chapter][-5:]
    
    def get_mastery(self, chapter: str) -> float:
        """返回 0-1 的掌握度"""
        if chapter not in self.chapter_scores or not self.chapter_scores[chapter]:
            return 0.5  # 未知时中性
        return sum(self.chapter_scores[chapter]) / len(self.chapter_scores[chapter])
    
    def get_weakest_chapters(self, track_chapters: Dict[str, float], top_k: int = 3) -> List[str]:
        """返回掌握度最低的章节（需在 track 内）"""
        candidates = []
        for ch in track_chapters.keys():
            mastery = self.get_mastery(ch)
            if self.chapter_counts.get(ch, 0) > 0:  # 至少问过
                candidates.append((ch, mastery))
        if not candidates:
            return []
        candidates.sort(key=lambda x: x[1])
        return [c[0] for c in candidates[:top_k]]


def estimate_ability(
    history: List[Tuple[int, float]],
    default: float = 3.0
) -> float:
    """
    基于历史 (difficulty, score) 估计能力（IRT 简化版）。
    
    2PL 中 P(correct) = σ(a(θ - b))，当 θ ≈ b 时 P≈0.5。
    若 score 高，说明 θ > b；若 score 低，θ < b。
    简化：ability ≈ last_difficulty + (last_score - 0.5) * 2
    使用加权平均（越近权重越大）。
    """
    if not history:
        return default
    
    total_w = 0
    weighted_sum = 0
    for i, (diff, score) in enumerate(history):
        w = i + 1  # 越近权重越大
        # 能力估计：diff + (score - 0.5) * 2，范围约 [1, 5]
        est = diff + (score - 0.5) * 2
        est = max(1.0, min(5.0, est))
        weighted_sum += est * w
        total_w += w
    
    return weighted_sum / total_w if total_w > 0 else default


def fisher_info_approx(ability: float, difficulty: float, discrimination: float = 1.0) -> float:
    """
    2PL 的 Fisher 信息近似：I(θ) = a² * p * (1-p)，其中 p = σ(a(θ-b))。
    当 θ ≈ b 时信息最大。返回 0-1 的归一化值。
    """
    def sigmoid(x):
        return 1 / (1 + math.exp(-x))
    
    p = sigmoid(discrimination * (ability - difficulty))
    info = discrimination ** 2 * p * (1 - p)
    return info


def select_by_maximum_information(
    candidates: List[Tuple[any, int]],  # (question, difficulty)
    estimated_ability: float,
    exploration_rate: float = 0.15
) -> any:
    """
    最大信息选题（Fisher Information）。
    选择 difficulty 最接近 ability 的题目，使信息量最大。
    加入 exploration_rate 的随机探索，避免过于贪婪。
    """
    if not candidates:
        return None
    
    if random.random() < exploration_rate:
        return random.choice(candidates)[0]
    
    best_q = None
    best_info = -1.0
    for q, diff in candidates:
        info = fisher_info_approx(estimated_ability, float(diff))
        if info > best_info:
            best_info = info
            best_q = q
    
    return best_q if best_q is not None else candidates[0][0]


def ucb_chapter_score(
    chapter: str,
    chapter_successes: Dict[str, int],
    chapter_failures: Dict[str, int],
    total_trials: int,
    c: float = 1.5
) -> float:
    """
    UCB (Upper Confidence Bound) 章节选择分数。
    score = mean + c * sqrt(log(N) / n)
    平衡探索（少问的章节）与利用（表现好的章节）。
    """
    s = chapter_successes.get(chapter, 0)
    f = chapter_failures.get(chapter, 0)
    n = s + f
    if n == 0:
        return float('inf')  # 未探索的优先
    mean = s / n
    if total_trials <= 0:
        return mean
    ucb_bonus = c * math.sqrt(math.log(total_trials + 1) / n)
    return mean + ucb_bonus


def compute_personalization_weights(
    chapter: str,
    resume_skills: Optional[List[str]] = None,
    missing_chapters: Optional[List[str]] = None,
    mastery_profile: Optional[SkillMasteryProfile] = None,
    track_chapters: Optional[Dict[str, float]] = None,
) -> float:
    """
    计算章节的个性化权重（用于选题时的加权采样）。
    综合考虑：简历匹配、薄弱点、掌握度、track 权重。
    """
    w = 1.0
    
    # 简历匹配：简历提到的技能对应章节，适当提高权重（体现「针对你的经历」）
    if resume_skills and track_chapters:
        for skill in resume_skills[:5]:  # 前几个技能
            for ch_key in track_chapters.keys():
                if _partial_ratio(chapter, ch_key) > 70 or _partial_ratio(skill, ch_key) > 60:
                    w *= 1.3  # 简历相关章节略增
                    break
    
    # 薄弱点：缺失章节应优先考察
    if missing_chapters and track_chapters:
        for m in missing_chapters:
            for ch_key in track_chapters.keys():
                if _partial_ratio(m, ch_key) > 70 and _partial_ratio(chapter, ch_key) > 70:
                    w *= 1.8  # 薄弱章节显著提高
                    break
    
    # 掌握度：低掌握度章节应多练（EDGE 中针对 misconception 的练习）
    if mastery_profile and mastery_profile.get_mastery(chapter) < 0.6:
        w *= 1.4
    
    return w
