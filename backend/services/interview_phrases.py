"""
面试话术模块 - 自适应出题与追问的过渡语
根据上下文（得分、是否追问、章节切换等）生成更自然的过渡语
"""
import random
from typing import List, Optional


FIRST_QUESTION_INTROS = [
    "你好！欢迎参加本次面试。让我们开始第一题：\n\n{question}",
    "欢迎！我们直接开始吧。第一题：\n\n{question}",
    "你好，面试开始。请听题：\n\n{question}",
]

FIRST_QUESTION_WITH_RESUME = [
    "你好！根据你的简历，我们会结合你的经历来考察。第一题：\n\n{question}",
    "欢迎！我们根据你的背景做了题目安排。开始：\n\n{question}",
]

NEXT_QUESTION_AFTER_GOOD = [
    "回答得不错！我们继续下一题：\n\n{question}",
    "很好，思路清晰。下一题：\n\n{question}",
    "分析到位，继续保持。来看这道：\n\n{question}",
    "你对这块理解得挺好的。我们提升一下难度：\n\n{question}",
    "漂亮，关键点都覆盖到了。我们看另一个话题：\n\n{question}",
]

NEXT_QUESTION_AFTER_FAIR = [
    "好的，我们继续。下一题：\n\n{question}",
    "收到，继续下一题：\n\n{question}",
    "嗯，有一定理解。我们看看下一个问题：\n\n{question}",
    "了解了，我们继续往下走：\n\n{question}",
]

NEXT_QUESTION_AFTER_WEAK = [
    "没关系，我们换个方向。下一题：\n\n{question}",
    "好的，我们继续看看其他方面：\n\n{question}",
    "这部分先放一下，我们来看另一个知识点：\n\n{question}",
    "没事，这块后面可以再补强。我们看这道：\n\n{question}",
]

NEXT_AFTER_FOLLOWUP = [
    "好的，这部分我们先到这里。换个话题：\n\n{question}",
    "行，追问就到这里。我们看看新的方向：\n\n{question}",
    "好，这个知识点我们探得差不多了。下一题：\n\n{question}",
    "了解，我们继续。来看另一道题：\n\n{question}",
]

NEXT_WITH_TOPIC_SHIFT_GOOD = [
    "答得不错！接下来我们切到{chapter}方向，看看你的掌握：\n\n{question}",
    "刚才那道回答很好。我们聊聊{chapter}相关的：\n\n{question}",
    "漂亮！换到{chapter}这边试试：\n\n{question}",
]

NEXT_WITH_TOPIC_SHIFT_FAIR = [
    "好，我们换个方向，看看{chapter}这块：\n\n{question}",
    "接下来我们聊聊{chapter}相关的内容：\n\n{question}",
    "换一个方向，看看你对{chapter}的掌握：\n\n{question}",
    "了解，我们接着看看{chapter}方面的问题：\n\n{question}",
]

NEXT_WITH_TOPIC_SHIFT_WEAK = [
    "没关系，我们切到{chapter}方向看看：\n\n{question}",
    "这个先放一放，我们看看{chapter}方面你怎么样：\n\n{question}",
    "好的，换到{chapter}试试，这块可能更适合你：\n\n{question}",
]

FOLLOWUP_TEMPLATES_WITH_POINT = [
    "你刚才提到了一些要点，不过关于{point}这方面，能再深入聊聊吗？",
    "回答得不错，我想追问一下：{point}在实际应用中你是怎么理解的？",
    "关于{point}，你能结合实际项目经验说说吗？",
    "这块我想再深入一下：{point}的底层原理你了解吗？",
    "你提到了相关的概念，那在{point}方面，有什么需要特别注意的？",
]

FOLLOWUP_TEMPLATES_GENERIC = [
    "你的回答覆盖了部分要点，能否再补充一些关键细节？",
    "这个问题还有一些重要的方面你没有提到，能再想想吗？",
    "从实际项目的角度，你觉得这个问题还有哪些值得讨论的？",
    "能否从原理层面再深入解释一下？",
    "如果在实际开发中遇到这个问题，你会怎么处理？",
]


def get_first_question_phrase(question: str, has_resume: bool = False) -> str:
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
    if next_chapter and next_chapter.strip():
        if last_score is not None and last_score >= 0.75:
            pool = NEXT_WITH_TOPIC_SHIFT_GOOD
        elif last_score is not None and last_score < 0.55:
            pool = NEXT_WITH_TOPIC_SHIFT_WEAK
        else:
            pool = NEXT_WITH_TOPIC_SHIFT_FAIR
        return random.choice(pool).replace("{chapter}", next_chapter).replace("{question}", question)

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
    if missing_points:
        point = missing_points[0]
        tpl = random.choice(FOLLOWUP_TEMPLATES_WITH_POINT)
        return tpl.format(point=point)
    return random.choice(FOLLOWUP_TEMPLATES_GENERIC)
