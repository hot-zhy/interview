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

