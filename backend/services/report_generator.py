"""Report generator service — multi-step agentic analysis."""
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from backend.db.models import InterviewSession, Evaluation, AskedQuestion, QuestionBank
from backend.services.llm_provider import (
    generate_report_summary_llm,
    generate_strengths_weaknesses_llm,
    generate_learning_plan_llm,
    generate_speech_recommendations_llm,
    generate_question_rationale_llm,
    generate_deep_report_analysis,
)


def generate_report(db: Session, session_id: int) -> Dict:
    """
    Generate interview report.
    
    Returns:
        {
            "summary_json": {...},
            "markdown": "..."
        }
    """
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        raise ValueError("Session not found")
    
    # Get all evaluations
    evaluations = db.query(Evaluation).join(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).order_by(Evaluation.created_at).all()
    
    if not evaluations:
        return {
            "summary_json": {
                "overall_score": 0.0,
                "dimension_scores": {},
                "per_question_scores": [],
                "overall_summary": None,
                "strengths": [],
                "weaknesses": [],
                "missing_knowledge": [],
                "learning_plan": [],
                "recommended_questions": [],
                "recommended_questions_detail": [],
                "speech_summary": {"available": False, "message": "本次面试未使用语音输入"},
                "expression_summary": {"available": False, "message": "本次面试未开启实时表情分析"}
            },
            "markdown": "# 面试报告\n\n暂无评价数据。"
        }
    
    # Calculate overall score
    overall_score = sum(e.overall_score for e in evaluations) / len(evaluations)
    
    # Analyze strengths and weaknesses (rule-based baseline)
    strengths, weaknesses = _analyze_performance(evaluations)
    avg_scores = _get_avg_scores(evaluations)
    
    # Per-dimension averages and per-question scores for charts
    dimension_scores = {k: round(v, 2) for k, v in avg_scores.items()}
    per_question_scores = _get_per_question_scores(evaluations)
    
    # Collect missing knowledge
    missing_knowledge = _collect_missing_knowledge(evaluations)
    
    # LLM 增强：个性化优势/待改进（失败则用规则结果）
    llm_sw = generate_strengths_weaknesses_llm(avg_scores, missing_knowledge)
    if llm_sw:
        strengths, weaknesses = llm_sw
    
    # Generate learning plan（LLM 优先，失败则规则）
    learning_plan = generate_learning_plan_llm(
        missing_knowledge, session.track, weaknesses
    )
    if not learning_plan:
        learning_plan = _generate_learning_plan(missing_knowledge, session.track)
    
    # Recommend questions（含 LLM 推荐理由）
    recommended_questions, recommended_questions_detail = _recommend_questions(
        db, session, missing_knowledge
    )
    
    # Analyze speech patterns
    speech_summary = _analyze_speech_patterns(evaluations)
    speech_recs = generate_speech_recommendations_llm(speech_summary)
    if speech_recs:
        speech_summary["recommendations"] = speech_recs

    # Analyze expression patterns
    expression_summary = _analyze_expression_patterns(evaluations, session)

    # Multi-step agentic deep analysis (innovation)
    asked_qs = db.query(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).order_by(AskedQuestion.created_at).all()

    per_q_data = []
    difficulty_trajectory = []
    chapter_trace = []
    for aq in asked_qs:
        difficulty_trajectory.append(aq.difficulty)
        chapter_trace.append(aq.topic or "")
        ev = aq.evaluation
        if ev:
            per_q_data.append({
                "question": aq.question_text[:100],
                "chapter": aq.topic or "",
                "difficulty": aq.difficulty,
                "score": ev.overall_score,
                "missing": ev.missing_points_json or [],
            })

    resume_skills = None
    if session.resume_id:
        from backend.db.models import Resume
        resume = db.query(Resume).filter(Resume.id == session.resume_id).first()
        if resume and resume.parsed_json:
            resume_skills = resume.parsed_json.get("skills", [])

    deep = generate_deep_report_analysis(
        track=session.track,
        rounds=session.current_round or len(evaluations),
        overall_score=overall_score,
        per_question_data=per_q_data,
        missing_knowledge=missing_knowledge,
        avg_scores=avg_scores,
        difficulty_trajectory=difficulty_trajectory,
        chapter_trace=chapter_trace,
        resume_skills=resume_skills,
    )

    overall_summary = None
    dimension_analysis = None
    gap_analysis = None
    strategy_trace = None

    if deep:
        overall_summary = deep.get("overall_summary")
        dimension_analysis = deep.get("dimension_analysis")
        gap_analysis = deep.get("gap_analysis")
        strategy_trace = deep.get("strategy_trace")
        if deep.get("learning_plan"):
            learning_plan = deep["learning_plan"]

    if not overall_summary:
        overall_summary = generate_report_summary_llm(
            overall_score, strengths, weaknesses, missing_knowledge,
            session.track, session.current_round or 0
        )
    
    summary: Dict[str, Any] = {
        "overall_score": round(overall_score, 2),
        "dimension_scores": dimension_scores,
        "per_question_scores": per_question_scores,
        "overall_summary": overall_summary,
        "dimension_analysis": dimension_analysis,
        "gap_analysis": gap_analysis,
        "strategy_trace": strategy_trace,
        "difficulty_trajectory": difficulty_trajectory,
        "chapter_trace": chapter_trace,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_knowledge": missing_knowledge,
        "learning_plan": learning_plan,
        "recommended_questions": recommended_questions,
        "recommended_questions_detail": recommended_questions_detail,
        "speech_summary": speech_summary,
        "expression_summary": expression_summary,
    }
    
    # Generate markdown
    markdown = _generate_markdown(session, evaluations, summary)
    
    return {
        "summary_json": summary,
        "markdown": markdown
    }


def _get_per_question_scores(evaluations: List[Evaluation]) -> List[Dict[str, Any]]:
    """Get scores per question for charting (round index, dimension scores, overall)."""
    result = []
    for i, eval_obj in enumerate(evaluations):
        scores = eval_obj.scores_json or {}
        result.append({
            "round": i + 1,
            "correctness": round(scores.get("correctness", 0), 2),
            "depth": round(scores.get("depth", 0), 2),
            "clarity": round(scores.get("clarity", 0), 2),
            "practicality": round(scores.get("practicality", 0), 2),
            "tradeoffs": round(scores.get("tradeoffs", 0), 2),
            "overall": round(eval_obj.overall_score, 2),
        })
    return result


def _get_avg_scores(evaluations: List[Evaluation]) -> Dict[str, float]:
    """Aggregate scores by dimension."""
    score_sums = {
        "correctness": 0.0,
        "depth": 0.0,
        "clarity": 0.0,
        "practicality": 0.0,
        "tradeoffs": 0.0
    }
    for eval_obj in evaluations:
        scores = eval_obj.scores_json or {}
        for key in score_sums:
            score_sums[key] += scores.get(key, 0.0)
    return {k: v / len(evaluations) for k, v in score_sums.items()}


def _analyze_performance(evaluations: List[Evaluation]) -> tuple[List[str], List[str]]:
    """Analyze performance to identify strengths and weaknesses (rule-based)."""
    strengths = []
    weaknesses = []
    avg_scores = _get_avg_scores(evaluations)
    
    # Identify strengths (>= 0.7)
    if avg_scores["correctness"] >= 0.7:
        strengths.append("基础知识掌握扎实")
    if avg_scores["depth"] >= 0.7:
        strengths.append("技术理解深入")
    if avg_scores["clarity"] >= 0.7:
        strengths.append("表达清晰有条理")
    if avg_scores["practicality"] >= 0.7:
        strengths.append("实践经验丰富")
    if avg_scores["tradeoffs"] >= 0.7:
        strengths.append("能够分析权衡取舍")
    
    # Identify weaknesses (< 0.6)
    if avg_scores["correctness"] < 0.6:
        weaknesses.append("基础知识需要加强")
    if avg_scores["depth"] < 0.6:
        weaknesses.append("技术深度有待提升")
    if avg_scores["clarity"] < 0.6:
        weaknesses.append("表达需要更加清晰")
    if avg_scores["practicality"] < 0.6:
        weaknesses.append("缺乏实际应用经验")
    if avg_scores["tradeoffs"] < 0.6:
        weaknesses.append("需要加强系统思维")
    
    if not strengths:
        strengths.append("整体表现良好")
    if not weaknesses:
        weaknesses.append("继续保持当前水平")
    
    return strengths[:5], weaknesses[:5]


def _collect_missing_knowledge(evaluations: List[Evaluation]) -> List[str]:
    """Collect missing knowledge points."""
    missing_set = set()
    
    for eval_obj in evaluations:
        if eval_obj.missing_points_json:
            for point in eval_obj.missing_points_json:
                missing_set.add(point)
    
    return list(missing_set)[:10]  # Limit to top 10


def _generate_learning_plan(missing_knowledge: List[str], track: str) -> List[str]:
    """Generate learning plan based on missing knowledge."""
    plan = []
    
    if not missing_knowledge:
        plan.append("继续保持当前学习节奏")
        return plan
    
    # General recommendations
    plan.append("针对薄弱知识点进行专项学习")
    plan.append("阅读相关技术文档和源码")
    plan.append("通过实际项目加深理解")
    
    # Track-specific recommendations
    if "并发" in str(missing_knowledge) or "多线程" in str(missing_knowledge):
        plan.append("深入学习Java并发编程（JUC包、线程池、锁机制）")
    
    if "JVM" in str(missing_knowledge) or "性能" in str(missing_knowledge):
        plan.append("学习JVM原理和性能调优（内存模型、GC、调优工具）")
    
    if "Spring" in str(missing_knowledge):
        plan.append("深入学习Spring框架（IoC、AOP、事务管理）")
    
    if "数据库" in str(missing_knowledge):
        plan.append("加强数据库相关知识（SQL优化、索引、事务隔离）")
    
    return plan[:8]  # Limit to 8 items


def _recommend_questions(
    db: Session,
    session: InterviewSession,
    missing_knowledge: List[str]
) -> tuple[List[str], List[Dict[str, Any]]]:
    """Recommend questions based on missing knowledge. Returns (ids, detail_list)."""
    recommended_ids: List[str] = []
    detail_list: List[Dict[str, Any]] = []
    
    # Get chapters from missing knowledge
    missing_chapters = []
    for knowledge in missing_knowledge[:5]:
        chapters = db.query(QuestionBank.chapter).distinct().all()
        for (chapter,) in chapters:
            if any(kw in chapter for kw in (knowledge or "").split()[:2]):
                missing_chapters.append(chapter)
                break
    
    if missing_chapters:
        questions = db.query(QuestionBank).filter(
            QuestionBank.chapter.in_(missing_chapters[:3])
        ).limit(5).all()
    else:
        questions = []
    
    if len(questions) < 3:
        questions = db.query(QuestionBank).limit(5).all()
    
    for q in questions[:5]:
        qid = str(q.id) if q.id else ""
        rationale = generate_question_rationale_llm(
            q.question or "", missing_knowledge, q.chapter or ""
        )
        detail_list.append({
            "id": qid,
            "question_text": (q.question or "")[:80] + ("..." if len(q.question or "") > 80 else ""),
            "rationale": rationale or "针对薄弱知识点练习"
        })
        recommended_ids.append(qid)
    
    return list(dict.fromkeys(recommended_ids))[:5], detail_list[:5]


def _analyze_expression_patterns(
    evaluations: List[Evaluation],
    session: InterviewSession | None = None
) -> Dict:
    """分析整体表情模式（支持实时视频采集与历史拍照）"""
    expr_analyses = [e.expression_analysis_json for e in evaluations if e.expression_analysis_json]
    # 合并实时视频采集的表情历史
    if session and session.expression_history_json:
        expr_analyses = list(expr_analyses) + list(session.expression_history_json)
    
    if not expr_analyses:
        return {
            "available": False,
            "message": "本次面试未开启实时表情分析"
        }
    
    # 聚合情绪与面试相关指标
    ir_list = [e.get("interview_relevance", {}) for e in expr_analyses if e.get("interview_relevance")]
    if not ir_list:
        return {
            "available": True,
            "total_questions_with_expression": len(expr_analyses),
            "average_nervousness": 0,
            "dominant_emotions": [],
            "message": "无有效表情分析数据"
        }
    
    avg_nervousness = sum(ir.get("nervousness", 0) for ir in ir_list) / len(ir_list)
    dominant_emotions = [e.get("dominant_emotion", "neutral") for e in expr_analyses if e.get("dominant_emotion")]
    emotion_counts = {}
    for em in dominant_emotions:
        emotion_counts[em] = emotion_counts.get(em, 0) + 1
    top_emotions = sorted(emotion_counts.items(), key=lambda x: -x[1])[:3]
    
    # 紧张度趋势
    if len(ir_list) >= 2:
        first_n = ir_list[0].get("nervousness", 0)
        last_n = ir_list[-1].get("nervousness", 0)
        nervousness_trend = "improving" if last_n < first_n else "stable" if abs(last_n - first_n) < 0.1 else "increasing"
    else:
        nervousness_trend = "stable"
    
    return {
        "available": True,
        "total_questions_with_expression": len(expr_analyses),
        "average_nervousness": round(avg_nervousness, 3),
        "dominant_emotions": [e[0] for e in top_emotions],
        "nervousness_trend": nervousness_trend,
    }


def _analyze_speech_patterns(evaluations: List[Evaluation]) -> Dict:
    """分析整体语音模式"""
    speech_analyses = [e.speech_analysis_json for e in evaluations if e.speech_analysis_json]
    
    if not speech_analyses:
        return {
            "available": False,
            "message": "本次面试未使用语音输入"
        }
    
    # 计算平均值
    avg_speech_rate = sum(s.get("speech_rate", 0) for s in speech_analyses) / len(speech_analyses)
    avg_fluency = sum(s.get("fluency", 0) for s in speech_analyses) / len(speech_analyses)
    avg_nervousness = sum(s.get("nervousness", 0) for s in speech_analyses) / len(speech_analyses)
    avg_pause_frequency = sum(s.get("pause_frequency", 0) for s in speech_analyses) / len(speech_analyses)
    
    # 分析趋势
    if len(speech_analyses) >= 2:
        first_nervousness = speech_analyses[0].get("nervousness", 0)
        last_nervousness = speech_analyses[-1].get("nervousness", 0)
        nervousness_trend = "improving" if last_nervousness < first_nervousness else "stable" if abs(last_nervousness - first_nervousness) < 0.1 else "increasing"
    else:
        nervousness_trend = "stable"
    
    return {
        "available": True,
        "average_speech_rate": round(avg_speech_rate, 2),
        "average_fluency": round(avg_fluency, 3),
        "average_nervousness": round(avg_nervousness, 3),
        "average_pause_frequency": round(avg_pause_frequency, 2),
        "nervousness_trend": nervousness_trend,
        "total_questions_with_speech": len(speech_analyses)
    }


def _generate_markdown(
    session: InterviewSession,
    evaluations: List[Evaluation],
    summary: Dict
) -> str:
    """Generate markdown report."""
    md = f"""# 面试报告

## 基本信息

- **面试方向**: {session.track}
- **初始难度**: {session.level}
- **总轮数**: {session.total_rounds}
- **完成轮数**: {session.current_round}
- **综合得分**: {summary['overall_score']:.2f} / 1.0

"""
    # Add dimension scores table
    dim_scores = summary.get("dimension_scores", {})
    if dim_scores:
        dim_labels = {
            "correctness": "正确性",
            "depth": "深度",
            "clarity": "清晰度",
            "practicality": "实用性",
            "tradeoffs": "权衡分析"
        }
        md += "\n### 各维度得分\n\n| 维度 | 得分 |\n|------|------|\n"
        for key in ["correctness", "depth", "clarity", "practicality", "tradeoffs"]:
            val = dim_scores.get(key, 0)
            label = dim_labels.get(key, key)
            md += f"| {label} | {val:.2f} |\n"
        md += "\n"

    if summary.get("overall_summary"):
        md += f"\n## 综合评估\n\n{summary['overall_summary']}\n"

    # Dimension deep analysis (agentic multi-step)
    dim_analysis = summary.get("dimension_analysis")
    if dim_analysis and isinstance(dim_analysis, dict):
        dim_labels = {"correctness": "正确性", "depth": "深度", "clarity": "清晰度", "practicality": "实用性", "tradeoffs": "权衡分析"}
        md += "\n### 各维度深度分析\n\n"
        for key in ["correctness", "depth", "clarity", "practicality", "tradeoffs"]:
            analysis_text = dim_analysis.get(key, "")
            if analysis_text:
                md += f"**{dim_labels.get(key, key)}** ({dim_scores.get(key, 0):.2f}): {analysis_text}\n\n"

    # Knowledge gap root-cause analysis
    if summary.get("gap_analysis"):
        md += f"\n### 知识缺口深度分析\n\n{summary['gap_analysis']}\n"

    # Interview strategy trace (innovation)
    if summary.get("strategy_trace"):
        md += f"\n### AI面试策略解读\n\n{summary['strategy_trace']}\n"
        if summary.get("difficulty_trajectory"):
            md += f"\n- **难度轨迹**: {' → '.join(str(d) for d in summary['difficulty_trajectory'])}\n"
        if summary.get("chapter_trace"):
            md += f"- **章节轨迹**: {' → '.join(summary['chapter_trace'])}\n"

    md += "\n---\n\n## 综合评分\n\n### 优势\n\n"
    
    for strength in summary.get('strengths', []):
        md += f"- {strength}\n"
    
    md += "\n### 待改进\n\n"
    for weakness in summary.get('weaknesses', []):
        md += f"- {weakness}\n"
    
    md += "\n---\n\n## 缺失知识点\n\n"
    if summary['missing_knowledge']:
        for knowledge in summary['missing_knowledge']:
            md += f"- {knowledge}\n"
    else:
        md += "- 无显著缺失知识点\n"
    
    md += "\n---\n\n## 语音表达分析\n\n"
    speech_summary = summary.get("speech_summary", {})
    if speech_summary.get("available"):
        md += f"- **平均语速**: {speech_summary.get('average_speech_rate', 0):.0f} 字/分钟\n"
        md += f"- **平均流畅度**: {speech_summary.get('average_fluency', 0):.2f}\n"
        md += f"- **平均紧张度**: {speech_summary.get('average_nervousness', 0):.2f}\n"
        md += f"- **平均停顿频率**: {speech_summary.get('average_pause_frequency', 0):.1f} 次/分钟\n"
        trend = speech_summary.get('nervousness_trend', 'stable')
        trend_desc = {"improving": "逐渐放松", "stable": "保持稳定", "increasing": "略有紧张"}.get(trend, "保持稳定")
        md += f"- **紧张度趋势**: {trend_desc}\n"
        md += f"- **使用语音回答的题目数**: {speech_summary.get('total_questions_with_speech', 0)}\n"
        if speech_summary.get("recommendations"):
            md += "\n**改进建议**:\n"
            for rec in speech_summary["recommendations"]:
                md += f"- {rec}\n"
    else:
        md += f"- {speech_summary.get('message', '本次面试未使用语音输入')}\n"
    
    md += "\n---\n\n## 表情分析\n\n"
    expr_summary = summary.get("expression_summary", {})
    if expr_summary.get("available"):
        md += f"- **平均紧张度**: {expr_summary.get('average_nervousness', 0):.2f}\n"
        md += f"- **主要情绪**: {', '.join(expr_summary.get('dominant_emotions', [])) or '无'}\n"
        trend = expr_summary.get('nervousness_trend', 'stable')
        trend_desc = {"improving": "逐渐放松", "stable": "保持稳定", "increasing": "略有紧张"}.get(trend, "保持稳定")
        md += f"- **紧张度趋势**: {trend_desc}\n"
        md += f"- **使用表情拍照的题目数**: {expr_summary.get('total_questions_with_expression', 0)}\n"
    else:
        md += f"- {expr_summary.get('message', '本次面试未使用表情拍照')}\n"
    
    md += "\n---\n\n## 学习建议\n\n"
    for plan in summary['learning_plan']:
        md += f"- {plan}\n"
    
    md += "\n---\n\n## 推荐题单\n\n"
    detail_list = summary.get("recommended_questions_detail", [])
    if detail_list:
        md += "建议重点练习以下题目：\n\n"
        for item in detail_list:
            qtext = item.get("question_text", "")
            rationale = item.get("rationale", "")
            qid = item.get("id", "")
            if qtext or rationale:
                md += f"- **{qtext or f'题目 ID: {qid}'}**"
                if rationale:
                    md += f" — {rationale}"
                md += "\n"
            else:
                md += f"- 题目 ID: {qid}\n"
    elif summary.get('recommended_questions'):
        md += "建议重点练习以下题目：\n\n"
        for qid in summary['recommended_questions']:
            md += f"- 题目 ID: {qid}\n"
    else:
        md += "暂无推荐题目\n"
    
    md += "\n---\n\n## 详细评价\n\n"
    
    for i, eval_obj in enumerate(evaluations, 1):
        scores = eval_obj.scores_json
        md += f"### 第 {i} 题\n\n"
        md += f"**综合得分**: {eval_obj.overall_score:.2f}\n\n"
        md += f"**分项评分**:\n\n"
        md += "| 评分项 | 得分 |\n"
        md += "|--------|------|\n"
        md += f"| 正确性 | {scores.get('correctness', 0):.2f} |\n"
        md += f"| 深度 | {scores.get('depth', 0):.2f} |\n"
        md += f"| 清晰度 | {scores.get('clarity', 0):.2f} |\n"
        md += f"| 实用性 | {scores.get('practicality', 0):.2f} |\n"
        md += f"| 权衡分析 | {scores.get('tradeoffs', 0):.2f} |\n\n"
        
        # Add speech analysis if available
        if eval_obj.speech_analysis_json:
            speech = eval_obj.speech_analysis_json
            analysis = speech.get("analysis", {})
            md += f"**语音分析**:\n"
            md += f"- 语速: {speech.get('speech_rate', 0):.0f} 字/分钟 ({analysis.get('speech_rate_desc', '')})\n"
            md += f"- 流畅度: {speech.get('fluency', 0):.2f} ({analysis.get('fluency_desc', '')})\n"
            md += f"- 紧张度: {speech.get('nervousness', 0):.2f} ({analysis.get('nervousness_desc', '')})\n"
            md += f"- 停顿频率: {speech.get('pause_frequency', 0):.1f} 次/分钟\n"
            md += f"- 平均停顿时长: {speech.get('average_pause_duration', 0):.2f} 秒\n"
            if analysis.get("recommendations"):
                md += f"- 建议: {'; '.join(analysis['recommendations'])}\n"
            md += "\n"
        
        # Add expression analysis if available
        if eval_obj.expression_analysis_json:
            expr = eval_obj.expression_analysis_json
            ir = expr.get("interview_relevance", {})
            md += f"**表情分析**:\n"
            md += f"- 主导情绪: {expr.get('dominant_emotion', 'neutral')}\n"
            md += f"- 紧张度: {ir.get('nervousness', 0):.2f} ({ir.get('confidence_desc', '')})\n"
            md += f"- 投入度: {ir.get('engagement_desc', '')}\n"
            if ir.get("recommendations"):
                md += f"- 建议: {'; '.join(ir['recommendations'])}\n"
            md += "\n"
        
        md += f"**反馈**:\n\n{eval_obj.feedback_text}\n\n"
        md += "---\n\n"
    
    return md

