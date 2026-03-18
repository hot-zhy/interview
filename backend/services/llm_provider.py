"""LLM provider for enhanced evaluation (optional)."""
import json
import re
from collections import Counter
from typing import Dict, List, Optional
from pydantic import BaseModel, ValidationError
from backend.core.config import settings
from backend.schemas.evaluation import Scores


class EvaluationOutput(BaseModel):
    """Structured LLM evaluation output."""
    scores: Scores
    overall_score: float
    feedback: str
    missing_points: list[str]
    next_direction: str
    reasoning: Optional[str] = None


def evaluate_with_llm(
    question: str,
    correct_answer: str,
    user_answer: str
) -> Optional[Dict]:
    """
    Evaluate answer using LLM (ZhipuAI GLM-4-Flash).
    
    Returns:
        Same format as evaluator_rules.evaluate_answer, or None if LLM unavailable
    """
    # Try ZhipuAI
    if settings.zhipuai_api_key:
        try:
            judge_count = max(1, min(int(getattr(settings, "llm_multi_judge_count", 1)), 5))
            use_cot = bool(getattr(settings, "llm_use_cot", False))
            if judge_count > 1:
                return _evaluate_with_multi_judge(
                    question=question,
                    correct_answer=correct_answer,
                    user_answer=user_answer,
                    judge_count=judge_count,
                    use_cot=use_cot,
                )
            return _evaluate_with_zhipuai(
                question=question,
                correct_answer=correct_answer,
                user_answer=user_answer,
                use_cot=use_cot,
            )
        except Exception as e:
            print(f"ZhipuAI evaluation failed: {e}")
    
    return None


def _evaluate_with_zhipuai(
    question: str,
    correct_answer: str,
    user_answer: str,
    use_cot: bool = False,
    temperature: float = 0.3,
) -> Dict:
    """Evaluate using ZhipuAI GLM-4-Flash API."""
    try:
        import zhipuai
        client = zhipuai.ZhipuAI(api_key=settings.zhipuai_api_key)

        cot_json_field = '\n    "reasoning": "简要推理（若启用CoT）",' if use_cot else ""
        cot_instruction = (
            "\n请先进行简短分析，再输出JSON；reasoning 字段用1-2句概括评分依据。"
            if use_cot else ""
        )
        prompt = f"""你是一位资深Java技术面试官。请对候选人的回答进行评价。

题目：{question}

标准答案：{correct_answer}

候选人回答：{user_answer}

请严格按照以下JSON格式输出评价结果，不要添加任何其他内容：

{{
    "scores": {{
        "correctness": 0.0-1.0,
        "depth": 0.0-1.0,
        "clarity": 0.0-1.0,
        "practicality": 0.0-1.0,
        "tradeoffs": 0.0-1.0
    }},
{cot_json_field}
    "overall_score": 0.0-1.0,
    "feedback": "文字反馈",
    "missing_points": ["缺失点1", "缺失点2"],
    "next_direction": "下一题方向建议"
}}

评分标准：
- correctness: 答案正确性（0-1）
- depth: 技术深度（0-1）
- clarity: 表达清晰度（0-1）
- practicality: 实用性/实践性（0-1）
- tradeoffs: 是否讨论权衡取舍（0-1）
- overall_score: 综合得分（0-1）
{cot_instruction}

请只输出JSON，不要添加任何其他文字："""
        
        response = client.chat.completions.create(
            model=settings.zhipuai_model,
            messages=[
                {"role": "system", "content": "你是一位严格的技术面试官，必须输出有效的JSON格式。只输出JSON，不要添加任何解释或markdown格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        # Extract JSON from response if there's extra text
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(0)
        
        result_dict = json.loads(result_text)
        
        # Validate with Pydantic
        try:
            validated = EvaluationOutput(**result_dict)
            return {
                "scores": validated.scores.model_dump(),
                "overall_score": validated.overall_score,
                "feedback": validated.feedback,
                "missing_points": validated.missing_points,
                "next_direction": validated.next_direction,
                "reasoning": validated.reasoning,
            }
        except ValidationError as e:
            raise ValueError(f"LLM output validation failed: {e}")
            
    except Exception as e:
        raise Exception(f"ZhipuAI API error: {str(e)}")


def _evaluate_with_multi_judge(
    question: str,
    correct_answer: str,
    user_answer: str,
    judge_count: int,
    use_cot: bool = False,
) -> Optional[Dict]:
    """
    Multi-judge LLM evaluation:
    - Run multiple independent evaluations
    - Aggregate numeric scores by mean
    - Merge missing points by frequency
    """
    results: List[Dict] = []
    for i in range(judge_count):
        # Slight temperature diversity to reduce identical outputs.
        temp = 0.2 + 0.1 * (i % 3)
        try:
            r = _evaluate_with_zhipuai(
                question=question,
                correct_answer=correct_answer,
                user_answer=user_answer,
                use_cot=use_cot,
                temperature=temp,
            )
            if r:
                results.append(r)
        except Exception:
            continue

    if not results:
        return None

    dimensions = ["correctness", "depth", "clarity", "practicality", "tradeoffs"]
    merged_scores: Dict[str, float] = {}
    for dim in dimensions:
        vals = [float(r.get("scores", {}).get(dim, 0.0)) for r in results]
        merged_scores[dim] = round(sum(vals) / len(vals), 4)

    overall_vals = [float(r.get("overall_score", 0.0)) for r in results]
    merged_overall = round(sum(overall_vals) / len(overall_vals), 4)

    missing_counter: Counter[str] = Counter()
    for r in results:
        for p in r.get("missing_points", []) or []:
            point = str(p).strip()
            if point:
                missing_counter[point] += 1
    merged_missing = [p for p, _ in missing_counter.most_common(5)]

    next_dirs = [str(r.get("next_direction", "")).strip() for r in results if str(r.get("next_direction", "")).strip()]
    merged_next_direction = Counter(next_dirs).most_common(1)[0][0] if next_dirs else ""

    # Prefer the longest feedback as a richer explanation.
    merged_feedback = max((str(r.get("feedback", "")) for r in results), key=len, default="")

    reasonings = [str(r.get("reasoning", "")).strip() for r in results if str(r.get("reasoning", "")).strip()]
    merged_reasoning = " | ".join(reasonings[:2]) if reasonings else None

    return {
        "scores": merged_scores,
        "overall_score": merged_overall,
        "feedback": merged_feedback,
        "missing_points": merged_missing,
        "next_direction": merged_next_direction,
        "reasoning": merged_reasoning,
    }


def generate_followup_with_llm(
    original_question: str,
    user_answer: str,
    feedback: str,
    missing_points: list[str],
    followup_count: int = 0,
    correct_answer: str = "",
) -> Optional[str]:
    """
    使用 LLM 生成更自然的追问（Misconception-Aware，参考 EDGE/Gap-Focused）。
    
    Args:
        original_question: 原题
        user_answer: 用户回答
        feedback: 评价反馈
        missing_points: 缺失点列表
        followup_count: 已追问次数（0=首次追问，1=二次追问）
        correct_answer: 标准答案（用于定位 gap，可选）
    
    Returns:
        追问内容，或 None（LLM 不可用时）
    """
    if not settings.zhipuai_api_key:
        return None
    
    try:
        import zhipuai
        client = zhipuai.ZhipuAI(api_key=settings.zhipuai_api_key)
        
        missing_str = "；".join(missing_points[:3]) if missing_points else "无"
        depth_hint = "第一次追问，针对知识缺口提问" if followup_count == 0 else "第二次追问，可换角度或追问实践场景"
        
        gap_hint = ""
        if correct_answer and user_answer:
            gap_hint = f"""
【Gap 分析】标准答案要点：{correct_answer[:300]}...
候选人回答中未覆盖或理解有偏差的部分，正是追问的切入点。请生成能帮助澄清误解、补全知识的追问。
"""
        
        prompt = f"""你是一位资深的Java技术面试官，正在进行个性化追问。请基于候选人的回答与知识缺口，生成一句自然、有针对性的追问。

原题：{original_question}
候选人回答：{user_answer[:500]}
评价反馈：{feedback}
缺失/可深入的点：{missing_str}
{gap_hint}

要求（Misconception-Aware 追问）：
- 针对候选人回答中的具体缺口或模糊点提问，而非泛泛而谈
- 语气自然，像真人面试官在追问，例如「你刚才提到了X，那Y和Z的关系能具体说说吗」「在实际项目中遇到A场景你会怎么处理」
- 不要直接照抄缺失点，用换一种说法或换个角度
- 一句话即可，30字以内
- 这是{depth_hint}

请直接输出追问内容，不要加引号或前缀："""
        
        response = client.chat.completions.create(
            model=settings.zhipuai_model,
            messages=[
                {"role": "system", "content": "你是面试官，生成一句简短的追问。只输出追问内容，不要其他文字。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        
        content = response.choices[0].message.content.strip()
        if content and len(content) < 200:  # 避免过长
            return content
        return None
    except Exception:
        return None


def _call_zhipuai(system: str, user_content: str, temperature: float = 0.5) -> Optional[str]:
    """通用智谱 API 调用，返回 content 或 None。"""
    if not settings.zhipuai_api_key:
        return None
    try:
        import zhipuai
        client = zhipuai.ZhipuAI(api_key=settings.zhipuai_api_key)
        response = client.chat.completions.create(
            model=settings.zhipuai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content.strip() or None
    except Exception:
        return None


def generate_report_summary_llm(
    overall_score: float,
    strengths: List[str],
    weaknesses: List[str],
    missing_knowledge: List[str],
    track: str,
    rounds: int
) -> Optional[str]:
    """
    使用 LLM 生成 2-3 句个性化综合总结。
    失败返回 None，调用方回退到规则逻辑。
    """
    system = "你是资深技术面试官，用简洁专业的语言写面试总结。2-3句话，50字以内。"
    user = f"""面试方向：{track}，共{rounds}轮。
综合得分：{overall_score:.2f}/1.0。
优势：{', '.join(strengths[:3]) if strengths else '无'}。
待改进：{', '.join(weaknesses[:3]) if weaknesses else '无'}。
缺失知识点：{', '.join(missing_knowledge[:5]) if missing_knowledge else '无'}。

请输出一句简洁的总结，不要加引号或前缀："""
    return _call_zhipuai(system, user, temperature=0.4)


def generate_strengths_weaknesses_llm(
    avg_scores: Dict[str, float],
    missing_knowledge: List[str]
) -> Optional[tuple[List[str], List[str]]]:
    """
    使用 LLM 生成个性化优势/待改进描述。
    返回 (strengths, weaknesses) 或 None。
    """
    system = """你是资深技术面试官。根据分项得分和缺失点，生成优势与待改进列表。
要求：每条10-20字，具体、可操作。优势3-5条，待改进3-5条。
输出格式（严格JSON）：{"strengths": ["...", "..."], "weaknesses": ["...", "..."]}
只输出JSON，不要其他文字。"""
    scores_str = ", ".join(f"{k}:{v:.2f}" for k, v in avg_scores.items())
    missing_str = ", ".join(missing_knowledge[:5]) if missing_knowledge else "无"
    user = f"分项得分：{scores_str}。缺失点：{missing_str}。"
    content = _call_zhipuai(system, user, temperature=0.3)
    if not content:
        return None
    try:
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        data = json.loads(content.strip())
        s = data.get("strengths", [])
        w = data.get("weaknesses", [])
        if isinstance(s, list) and isinstance(w, list):
            return (s[:5], w[:5])
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def generate_learning_plan_llm(
    missing_knowledge: List[str],
    track: str,
    weaknesses: List[str]
) -> Optional[List[str]]:
    """
    使用 LLM 根据缺失知识点和 track 生成个性化学习建议。
    返回 4-6 条建议，失败返回 None。
    """
    if not missing_knowledge and not weaknesses:
        return None
    system = """你是资深技术导师。根据面试表现，给出具体、可执行的学习建议。
每条15-30字，4-6条。格式：直接输出，每行一条，不要编号或前缀。"""
    missing_str = "；".join(missing_knowledge[:8])
    weak_str = "；".join(weaknesses[:3]) if weaknesses else ""
    user = f"面试方向：{track}。缺失知识点：{missing_str}。待改进：{weak_str}。"
    content = _call_zhipuai(system, user, temperature=0.4)
    if not content:
        return None
    lines = [ln.strip() for ln in content.split("\n") if ln.strip()][:6]
    return lines if lines else None


def generate_speech_recommendations_llm(
    speech_summary: Dict
) -> Optional[List[str]]:
    """
    根据语音分析指标生成改进建议。
    """
    if not speech_summary.get("available"):
        return None
    system = "你是面试辅导专家。根据语音指标给出1-3条简短改进建议，每条15字以内。直接输出，每行一条。"
    user = f"""语速：{speech_summary.get('average_speech_rate', 0)}字/分；
流畅度：{speech_summary.get('average_fluency', 0)}；
紧张度：{speech_summary.get('average_nervousness', 0)}；
停顿频率：{speech_summary.get('average_pause_frequency', 0)}次/分；
紧张度趋势：{speech_summary.get('nervousness_trend', 'stable')}。"""
    content = _call_zhipuai(system, user, temperature=0.3)
    if not content:
        return None
    lines = [ln.strip() for ln in content.split("\n") if ln.strip()][:3]
    return lines if lines else None


def generate_question_rationale_llm(
    question_text: str,
    missing_knowledge: List[str],
    chapter: str
) -> Optional[str]:
    """
    为推荐题目生成推荐理由（一句话，20字以内）。
    """
    system = "你是面试辅导专家。用一句话说明为何推荐这道题，20字以内。直接输出，不要引号。"
    missing_str = "、".join(missing_knowledge[:3]) if missing_knowledge else "巩固"
    user = f"题目：{question_text[:100]}...。章节：{chapter}。候选人需加强：{missing_str}。"
    return _call_zhipuai(system, user, temperature=0.3)

