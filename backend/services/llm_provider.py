"""LLM provider for enhanced evaluation (optional)."""
import json
import re
from typing import Dict, Optional
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
            return _evaluate_with_zhipuai(question, correct_answer, user_answer)
        except Exception as e:
            print(f"ZhipuAI evaluation failed: {e}")
    
    return None


def _evaluate_with_zhipuai(question: str, correct_answer: str, user_answer: str) -> Dict:
    """Evaluate using ZhipuAI GLM-4-Flash API."""
    try:
        import zhipuai
        client = zhipuai.ZhipuAI(api_key=settings.zhipuai_api_key)
        
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

请只输出JSON，不要添加任何其他文字："""
        
        response = client.chat.completions.create(
            model=settings.zhipuai_model,
            messages=[
                {"role": "system", "content": "你是一位严格的技术面试官，必须输出有效的JSON格式。只输出JSON，不要添加任何解释或markdown格式。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
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
                "next_direction": validated.next_direction
            }
        except ValidationError as e:
            raise ValueError(f"LLM output validation failed: {e}")
            
    except Exception as e:
        raise Exception(f"ZhipuAI API error: {str(e)}")


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

