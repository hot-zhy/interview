"""
面试话术模块 - 自适应出题与追问的过渡语
根据上下文（得分、是否追问、章节切换等）生成更自然的过渡语
"""
import random
from typing import List, Optional


# 首题开场
FIRST_QUESTION_INTROS = [
    "你好！欢迎参加本次面试。让我们开始第一题：\n\n{question}",
    "欢迎！我们直接开始吧。第一题：\n\n{question}",
    "你好，面试开始。请听题：\n\n{question}",
]

# 有简历时的个性化开场（体现「针对你」）
FIRST_QUESTION_WITH_RESUME = [
    "你好！根据你的简历，我们会结合你的经历来考察。第一题：\n\n{question}",
    "欢迎！我们根据你的背景做了题目安排。开始：\n\n{question}",
]

# 回答较好后，进入下一题（不同得分区间）
NEXT_QUESTION_AFTER_GOOD = [
    "回答得不错！我们继续下一题：\n\n{question}",
    "很好，思路清晰。下一题：\n\n{question}",
    "不错，继续。\n\n{question}",
]

NEXT_QUESTION_AFTER_FAIR = [
    "好的，我们继续。下一题：\n\n{question}",
    "收到，继续下一题：\n\n{question}",
]

NEXT_QUESTION_AFTER_WEAK = [
    "没关系，我们换个方向。下一题：\n\n{question}",
    "好的，我们继续看看其他方面。\n\n{question}",
]

# 追问后进入新题（从同一话题切出）
NEXT_AFTER_FOLLOWUP = [
    "好的，这部分我们先到这里。换个话题：\n\n{question}",
    "行，我们继续下一题：\n\n{question}",
    "好，下一题：\n\n{question}",
]

# 章节/话题切换时（若 next_direction 或 chapter 有信息可用）
NEXT_WITH_TOPIC_SHIFT = [
    "接下来我们聊聊{chapter}相关的内容：\n\n{question}",
    "换一个方向，看看你对{chapter}的掌握：\n\n{question}",
]

# 追问话术模板（多样化，避免生硬）
FOLLOWUP_TEMPLATES_WITH_POINT = [
    "关于刚才的回答，我想进一步了解：{point}。请详细说明一下。",
    "你提到了相关概念，那{point}这块能具体说说吗？",
    "有个点想深入问问：{point}。",
    "关于{point}，能展开讲讲你的理解吗？",
]

FOLLOWUP_TEMPLATES_GENERIC = [
    "能否再详细解释一下刚才提到的内容？",
    "能具体展开说说吗？",
    "这部分可以再深入一点吗？",
    "还有没有补充？",
]


def get_first_question_phrase(question: str, has_resume: bool = False) -> str:
    """首题开场语，有简历时使用个性化话术"""
    if has_resume:
        tpl = random.choice(FIRST_QUESTION_WITH_RESUME)
    else:
        tpl = random.choice(FIRST_QUESTION_INTROS)
    return tpl.format(question=question)


def get_next_question_phrase(
    question: str,
    last_score: Optional[float] = None,
    after_followup: bool = False,
    next_chapter: Optional[str] = None,
    next_direction: Optional[str] = None,
) -> str:
    """
    根据上下文生成下一题的过渡语。
    
    Args:
        question: 题目内容
        last_score: 上一题得分 (0-1)
        after_followup: 是否刚结束追问
        next_chapter: 下一题所属章节（用于话题切换提示）
        next_direction: 评估中的 next_direction 建议
    """
    # 若有章节信息且与上一题不同，可加话题切换感
    if next_chapter and next_chapter.strip():
        templates = [
            t.replace("{chapter}", next_chapter).replace("{question}", question)
            for t in NEXT_WITH_TOPIC_SHIFT
        ]
        # 随机使用，避免每次都一样
        if random.random() < 0.5:
            return random.choice(templates)
    
    if after_followup:
        return random.choice(NEXT_AFTER_FOLLOWUP).format(question=question)
    
    if last_score is not None:
        if last_score >= 0.75:
            return random.choice(NEXT_QUESTION_AFTER_GOOD).format(question=question)
        elif last_score >= 0.55:
            return random.choice(NEXT_QUESTION_AFTER_FAIR).format(question=question)
        else:
            return random.choice(NEXT_QUESTION_AFTER_WEAK).format(question=question)
    
    return random.choice(NEXT_QUESTION_AFTER_FAIR).format(question=question)


def get_followup_phrase(missing_points: List[str], feedback: str = "") -> str:
    """
    生成追问语（模板版，无 LLM 时使用）。
    
    Args:
        missing_points: 缺失点列表
        feedback: 评价反馈（可选）
    """
    if missing_points:
        point = missing_points[0]
        tpl = random.choice(FOLLOWUP_TEMPLATES_WITH_POINT)
        return tpl.format(point=point)
    return random.choice(FOLLOWUP_TEMPLATES_GENERIC)
