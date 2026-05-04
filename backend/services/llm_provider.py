"""LLM provider for enhanced evaluation (optional)."""
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from statistics import pstdev
import time
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
    user_answer: str,
    judge_count_override: Optional[int] = None,
) -> Optional[Dict]:
    """
    Evaluate answer using LLM (ZhipuAI GLM-4-Flash).
    
    Returns:
        Same format as evaluator_rules.evaluate_answer, or None if LLM unavailable
    """
    # Try ZhipuAI
    if settings.zhipuai_api_key:
        try:
            selected = judge_count_override if judge_count_override is not None else getattr(settings, "llm_multi_judge_count", 1)
            judge_count = max(1, min(int(selected), 8))
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
            import traceback
            print(f"[LLM eval] ZhipuAI evaluation failed: {e}")
            traceback.print_exc()
    
    return None


def _evaluate_with_zhipuai(
    question: str,
    correct_answer: str,
    user_answer: str,
    use_cot: bool = False,
    temperature: float = 0.3,
) -> Dict:
    """Evaluate using ZhipuAI GLM-4-Flash API."""
    import time as _t
    _start = _t.time()
    print(f"[LLM evaluate] calling {settings.zhipuai_model} (cot={use_cot})...")
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
        print(f"[LLM evaluate] response received in {_t.time() - _start:.1f}s")
        
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
            print(f"[LLM evaluate] score={validated.overall_score:.2f}, dims={validated.scores.model_dump()}")
            return {
                "scores": validated.scores.model_dump(),
                "overall_score": validated.overall_score,
                "feedback": validated.feedback,
                "missing_points": validated.missing_points,
                "next_direction": validated.next_direction,
                "reasoning": validated.reasoning,
            }
        except ValidationError as e:
            print(f"[LLM evaluate] validation failed: {e}")
            raise ValueError(f"LLM output validation failed: {e}")
            
    except Exception as e:
        print(f"[LLM evaluate] error: {e}")
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
    started = time.time()
    results: List[Dict] = []
    judge_details: List[Dict] = []
    parallel_enabled = bool(getattr(settings, "llm_multi_judge_parallel_enabled", True))
    max_parallel = max(1, int(getattr(settings, "llm_multi_judge_max_parallel", 4)))
    timeout_sec = max(1.0, float(getattr(settings, "llm_multi_judge_timeout_sec", 25.0)))
    min_results = max(1, int(getattr(settings, "llm_multi_judge_fail_open_min_results", 1)))

    def _run_single(i: int) -> Dict:
        temp = 0.2 + 0.1 * (i % 3)
        t0 = time.time()
        try:
            payload = _evaluate_with_zhipuai(
                question=question,
                correct_answer=correct_answer,
                user_answer=user_answer,
                use_cot=use_cot,
                temperature=temp,
            )
            return {
                "ok": bool(payload),
                "idx": i,
                "temperature": round(temp, 2),
                "duration_ms": round((time.time() - t0) * 1000.0, 1),
                "result": payload,
                "error": "",
            }
        except Exception as exc:
            return {
                "ok": False,
                "idx": i,
                "temperature": round(temp, 2),
                "duration_ms": round((time.time() - t0) * 1000.0, 1),
                "result": None,
                "error": str(exc)[:120],
            }

    if parallel_enabled and judge_count > 1:
        with ThreadPoolExecutor(max_workers=min(max_parallel, judge_count)) as pool:
            futures = [pool.submit(_run_single, i) for i in range(judge_count)]
            try:
                for fut in as_completed(futures, timeout=timeout_sec):
                    detail = fut.result()
                    judge_details.append(detail)
                    if detail["ok"] and detail.get("result"):
                        results.append(detail["result"])
            except TimeoutError:
                for fut in futures:
                    if not fut.done():
                        fut.cancel()
    else:
        for i in range(judge_count):
            detail = _run_single(i)
            judge_details.append(detail)
            if detail["ok"] and detail.get("result"):
                results.append(detail["result"])

    if len(results) < min_results:
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
    disagreement_std = round(float(pstdev(overall_vals)), 4) if len(overall_vals) > 1 else 0.0
    total_duration_ms = round((time.time() - started) * 1000.0, 1)

    return {
        "scores": merged_scores,
        "overall_score": merged_overall,
        "feedback": merged_feedback,
        "missing_points": merged_missing,
        "next_direction": merged_next_direction,
        "reasoning": merged_reasoning,
        "_multi_judge_meta": {
            "requested_judges": int(judge_count),
            "successful_judges": len(results),
            "failed_judges": max(0, int(judge_count) - len(results)),
            "parallel_used": bool(parallel_enabled and judge_count > 1),
            "max_parallel": int(max_parallel),
            "timeout_sec": float(timeout_sec),
            "disagreement_std": disagreement_std,
            "total_duration_ms": total_duration_ms,
            "judges": judge_details,
        },
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
        print("[LLM followup] skipped — no API key")
        return None
    
    try:
        import time as _t
        _start = _t.time()
        print(f"[LLM followup] calling {settings.zhipuai_model}...")
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
        print(f"[LLM followup] done in {_t.time() - _start:.1f}s — '{content[:60]}...'")
        if content and len(content) < 200:
            return content
        return None
    except Exception as e:
        print(f"[LLM followup] error: {e}")
        return None


def _call_zhipuai(system: str, user_content: str, temperature: float = 0.5, label: str = "generic") -> Optional[str]:
    """通用智谱 API 调用，返回 content 或 None。"""
    if not settings.zhipuai_api_key:
        print(f"[LLM {label}] skipped — no API key")
        return None
    try:
        import time as _t
        _start = _t.time()
        import zhipuai
        client = zhipuai.ZhipuAI(api_key=settings.zhipuai_api_key)
        print(f"[LLM {label}] calling {settings.zhipuai_model}...")
        response = client.chat.completions.create(
            model=settings.zhipuai_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content}
            ],
            temperature=temperature
        )
        content = response.choices[0].message.content.strip() or None
        elapsed = _t.time() - _start
        print(f"[LLM {label}] done in {elapsed:.1f}s — {len(content or '')} chars")
        return content
    except Exception as e:
        print(f"[LLM {label}] error: {e}")
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
    return _call_zhipuai(system, user, temperature=0.4, label="report_summary")


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
    content = _call_zhipuai(system, user, temperature=0.3, label="strengths_weaknesses")
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
    content = _call_zhipuai(system, user, temperature=0.4, label="learning_plan")
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
    content = _call_zhipuai(system, user, temperature=0.3, label="speech_recommendations")
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
    return _call_zhipuai(system, user, temperature=0.3, label="question_rationale")


# ======================================================================
# Agentic LLM capabilities (topic planning, deep analysis, trace)
# ======================================================================

def suggest_next_topic_llm(
    track: str,
    chapters_covered: List[str],
    chapter_scores: Dict[str, float],
    missing_concepts: List[str],
    resume_skills: Optional[List[str]],
    available_chapters: List[str],
    current_difficulty: int,
    avg_score: float,
) -> Optional[Dict[str, str]]:
    """LLM-as-topic-planner: reason about what chapter to explore next.

    Returns {"chapter": str, "reasoning": str} or None.
    """
    system = """你是一位资深面试策略规划师。根据面试状态决定下一题应考察哪个章节。
输出严格JSON：{"chapter": "章节名", "reasoning": "一句话理由"}
只输出JSON，不要其他文字。"""
    covered_str = ", ".join(f"{c}(得分{chapter_scores.get(c, 0):.0%})" for c in chapters_covered) if chapters_covered else "尚未考察"
    missing_str = "、".join(missing_concepts[:5]) if missing_concepts else "无"
    resume_str = "、".join(resume_skills[:5]) if resume_skills else "未提供"
    avail_str = "、".join(available_chapters) if available_chapters else "无"

    user = f"""面试方向：{track}
当前难度：{current_difficulty}/5，平均得分：{avg_score:.0%}
已考察章节：{covered_str}
候选人缺失的知识点：{missing_str}
简历技能：{resume_str}
可选章节（必须从中选择）：{avail_str}

请选择最应该考察的章节并说明理由。优先考虑：
1. 候选人明显薄弱但尚未充分考察的领域
2. 与简历技能相关但还未验证的领域
3. 覆盖度不足的重要领域"""

    content = _call_zhipuai(system, user, temperature=0.3, label="topic_planner")
    if not content:
        return None
    try:
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        data = json.loads(content.strip())
        ch = data.get("chapter", "")
        if ch and isinstance(ch, str):
            return {"chapter": ch, "reasoning": data.get("reasoning", "")}
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def generate_followup_with_context(
    original_question: str,
    user_answer: str,
    correct_answer: str,
    feedback: str,
    missing_points: List[str],
    followup_count: int,
    score_history: Optional[List[float]] = None,
    chapter_trace: Optional[List[str]] = None,
) -> Optional[str]:
    """Memory-aware follow-up: uses full interview context for richer probing."""
    if not settings.zhipuai_api_key:
        return None

    missing_str = "；".join(missing_points[:3]) if missing_points else "无"
    depth_hint = "首次追问，聚焦核心知识缺口" if followup_count == 0 else "二次追问，换角度或追问实践应用"

    trajectory = ""
    if score_history and len(score_history) >= 2:
        recent = score_history[-3:]
        trend = "上升" if recent[-1] > recent[0] else ("下降" if recent[-1] < recent[0] else "稳定")
        trajectory = f"\n候选人近期表现趋势：{trend}（最近得分：{', '.join(f'{s:.0%}' for s in recent)}）"

    system = "你是资深Java面试官。生成一句精准的追问，帮助深入评估候选人的真实理解水平。只输出追问内容，不要引号或前缀。"
    user = f"""原题：{original_question}
候选人回答：{user_answer[:600]}
标准答案要点：{correct_answer[:400]}
评价反馈：{feedback}
识别到的知识缺口：{missing_str}{trajectory}

这是{depth_hint}。要求：
- 针对候选人回答中的具体错误或遗漏设计追问
- 避免重复已问过的内容
- 语气自然专业，30字以内
- 如果候选人对某概念有误解，设计能暴露误解的追问"""

    return _call_zhipuai(system, user, temperature=0.5, label="followup_context")


def generate_resume_question_llm(
    resume_parsed: Dict,
    track: str,
    difficulty: int,
) -> Optional[Dict[str, str]]:
    """Generate a personalized first question based on the candidate's resume.

    Returns {"question": str, "reference_answer": str} or None.
    """
    if not settings.zhipuai_api_key:
        return None

    skills = resume_parsed.get("skills", [])
    experience = resume_parsed.get("experience", [])
    projects = resume_parsed.get("projects", [])
    education = resume_parsed.get("education", [])

    skills_str = "、".join(skills[:10]) if skills else "未提供"
    exp_str = "；".join(str(e)[:80] for e in experience[:3]) if experience else "未提供"
    proj_str = "；".join(str(p)[:80] for p in projects[:3]) if projects else "未提供"
    edu_str = "；".join(str(e)[:60] for e in education[:2]) if education else "未提供"

    diff_desc = {1: "入门级", 2: "初级", 3: "中级", 4: "高级", 5: "专家级"}.get(difficulty, "中级")

    system = """你是资深Java技术面试官。根据候选人简历生成一道个性化的面试题。
输出严格JSON：{"question": "面试题内容", "reference_answer": "参考答案要点（100-200字）"}
只输出JSON，不要其他文字。"""

    user = f"""面试方向：{track}
难度要求：{diff_desc}（{difficulty}/5）

候选人简历：
- 技能：{skills_str}
- 工作经历：{exp_str}
- 项目经历：{proj_str}
- 教育背景：{edu_str}

要求：
- 题目要结合候选人简历中的具体技能或项目经验
- 例如：如果简历提到了Spring Boot项目，可以问Spring相关的深入问题
- 如果简历提到了高并发经验，可以问并发相关的实际场景题
- 难度要匹配{diff_desc}水平
- 题目30-80字，参考答案100-200字，覆盖3-5个关键知识点"""

    content = _call_zhipuai(system, user, temperature=0.5, label="resume_question")
    if not content:
        return None
    try:
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content)
            content = re.sub(r"\n?```$", "", content)
        data = json.loads(content.strip())
        q = data.get("question", "")
        a = data.get("reference_answer", "")
        if q and len(q) > 5 and a:
            return {"question": q, "reference_answer": a}
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def generate_deep_report_analysis(
    track: str,
    rounds: int,
    overall_score: float,
    per_question_data: List[Dict],
    missing_knowledge: List[str],
    avg_scores: Dict[str, float],
    difficulty_trajectory: List[int],
    chapter_trace: List[str],
    resume_skills: Optional[List[str]] = None,
) -> Optional[Dict]:
    """Multi-step agentic report: deep analysis with interview trace.

    Returns a dict with keys: overall_summary, dimension_analysis,
    gap_analysis, learning_plan, strategy_trace. Any key may be None.
    """
    if not settings.zhipuai_api_key:
        return None

    result = {}

    # Build Q&A context string (compact)
    qa_lines = []
    for i, qd in enumerate(per_question_data[:15], 1):
        qa_lines.append(
            f"Q{i}[{qd.get('chapter','?')},难度{qd.get('difficulty',0)}]: "
            f"{qd.get('question','')[:80]}... → 得分{qd.get('score',0):.0%}"
            f"{' (缺失:' + ','.join(qd.get('missing',[])) + ')' if qd.get('missing') else ''}"
        )
    qa_context = "\n".join(qa_lines)

    scores_str = ", ".join(f"{k}:{v:.2f}" for k, v in avg_scores.items())
    diff_str = "→".join(str(d) for d in difficulty_trajectory) if difficulty_trajectory else "无"
    ch_str = "→".join(chapter_trace) if chapter_trace else "无"
    missing_str = "、".join(missing_knowledge[:10]) if missing_knowledge else "无"
    resume_str = "、".join(resume_skills[:5]) if resume_skills else "未提供"

    base_context = f"""面试方向：{track}，共{rounds}轮
综合得分：{overall_score:.2f}/1.0
分项平均：{scores_str}
难度轨迹：{diff_str}
章节轨迹：{ch_str}
简历技能：{resume_str}
缺失知识点：{missing_str}

逐题记录：
{qa_context}"""

    # Step 1: Overall narrative summary
    s1 = _call_zhipuai(
        "你是资深面试评估专家。根据完整面试数据写一段个性化综合评估（100-150字），分析候选人的技术能力特点、表现趋势和关键亮点/不足。不要泛泛而谈，要结合具体的答题表现。",
        base_context, temperature=0.4, label="report_step1_summary"
    )
    result["overall_summary"] = s1

    # Step 2: Per-dimension deep analysis
    dim_analysis = _call_zhipuai(
        """你是面试评估专家。对五个评分维度逐一深入分析，结合具体答题表现说明得分原因。
输出格式（严格JSON）：
{"correctness": "分析...", "depth": "分析...", "clarity": "分析...", "practicality": "分析...", "tradeoffs": "分析..."}
每个维度30-50字，引用具体题目表现。只输出JSON。""",
        base_context, temperature=0.3, label="report_step2_dimensions"
    )
    if dim_analysis:
        try:
            if dim_analysis.startswith("```"):
                dim_analysis = re.sub(r"^```\w*\n?", "", dim_analysis)
                dim_analysis = re.sub(r"\n?```$", "", dim_analysis)
            result["dimension_analysis"] = json.loads(dim_analysis.strip())
        except (json.JSONDecodeError, TypeError):
            result["dimension_analysis"] = None

    # Step 3: Knowledge gap root-cause analysis
    s3 = _call_zhipuai(
        "你是技术能力诊断专家。分析候选人知识缺口的根本原因和关联性，不要简单列举缺失点，而是找出底层能力短板。80-120字。",
        base_context, temperature=0.4, label="report_step3_gaps"
    )
    result["gap_analysis"] = s3

    # Step 4: Personalized learning plan
    plan = _call_zhipuai(
        """你是技术学习规划师。根据面试暴露的具体问题，制定个性化学习计划。
要求：5-8条，每条包含具体学习内容和建议资源/方法，20-40字。
格式：每行一条，不要编号。""",
        base_context, temperature=0.4, label="report_step4_learning"
    )
    if plan:
        result["learning_plan"] = [ln.strip() for ln in plan.split("\n") if ln.strip()][:8]

    # Step 5: Interview strategy trace (innovation — explain what the agent did)
    s5 = _call_zhipuai(
        f"""你是AI面试系统的策略分析师。解释这场面试中自适应系统做了哪些决策以及为什么：
- 难度如何调整（轨迹：{diff_str}）
- 为什么选择了这些章节（轨迹：{ch_str}）
- 面试节奏和终止时机是否合理
用80-120字概述系统策略，让候选人理解AI面试官的出题逻辑。""",
        base_context, temperature=0.4, label="report_step5_strategy"
    )
    result["strategy_trace"] = s5

    return result if any(result.values()) else None

