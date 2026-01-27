"""Report generator service."""
from typing import Dict, List
from sqlalchemy.orm import Session
from backend.db.models import InterviewSession, Evaluation, AskedQuestion, QuestionBank
from backend.services.question_selector import _get_asked_chapters


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
                "strengths": [],
                "weaknesses": [],
                "missing_knowledge": [],
                "learning_plan": [],
                "recommended_questions": []
            },
            "markdown": "# 面试报告\n\n暂无评价数据。"
        }
    
    # Calculate overall score
    overall_score = sum(e.overall_score for e in evaluations) / len(evaluations)
    
    # Analyze strengths and weaknesses
    strengths, weaknesses = _analyze_performance(evaluations)
    
    # Collect missing knowledge
    missing_knowledge = _collect_missing_knowledge(evaluations)
    
    # Generate learning plan
    learning_plan = _generate_learning_plan(missing_knowledge, session.track)
    
    # Recommend questions
    recommended_questions = _recommend_questions(db, session, missing_knowledge)
    
    # Analyze speech patterns across all evaluations
    speech_summary = _analyze_speech_patterns(evaluations)
    
    summary = {
        "overall_score": round(overall_score, 2),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_knowledge": missing_knowledge,
        "learning_plan": learning_plan,
        "recommended_questions": recommended_questions,
        "speech_summary": speech_summary
    }
    
    # Generate markdown
    markdown = _generate_markdown(session, evaluations, summary)
    
    return {
        "summary_json": summary,
        "markdown": markdown
    }


def _analyze_performance(evaluations: List[Evaluation]) -> tuple[List[str], List[str]]:
    """Analyze performance to identify strengths and weaknesses."""
    strengths = []
    weaknesses = []
    
    # Aggregate scores by dimension
    score_sums = {
        "correctness": 0.0,
        "depth": 0.0,
        "clarity": 0.0,
        "practicality": 0.0,
        "tradeoffs": 0.0
    }
    
    for eval_obj in evaluations:
        scores = eval_obj.scores_json
        for key in score_sums:
            score_sums[key] += scores.get(key, 0.0)
    
    avg_scores = {k: v / len(evaluations) for k, v in score_sums.items()}
    
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
) -> List[str]:
    """Recommend questions based on missing knowledge."""
    recommended = []
    
    # Get chapters from missing knowledge
    missing_chapters = []
    for knowledge in missing_knowledge[:5]:
        # Try to match with chapters
        chapters = db.query(QuestionBank.chapter).distinct().all()
        for (chapter,) in chapters:
            if any(kw in chapter for kw in knowledge.split()[:2]):
                missing_chapters.append(chapter)
                break
    
    # Get questions from these chapters
    if missing_chapters:
        questions = db.query(QuestionBank).filter(
            QuestionBank.chapter.in_(missing_chapters[:3])
        ).limit(5).all()
        recommended = [q.id for q in questions]
    
    # If not enough, get random questions
    if len(recommended) < 3:
        all_questions = db.query(QuestionBank).limit(10).all()
        recommended.extend([q.id for q in all_questions[:5]])
    
    return list(set(recommended))[:5]


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

---

## 综合评分

### 优势

"""
    
    for strength in summary['strengths']:
        md += f"- ✅ {strength}\n"
    
    md += "\n### 待改进\n\n"
    for weakness in summary['weaknesses']:
        md += f"- ⚠️ {weakness}\n"
    
    md += "\n---\n\n## 缺失知识点\n\n"
    if summary['missing_knowledge']:
        for knowledge in summary['missing_knowledge']:
            md += f"- 📌 {knowledge}\n"
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
        trend_desc = {"improving": "逐渐放松", "stable": "保持稳定", "increasing": "略有紧张"}[trend]
        md += f"- **紧张度趋势**: {trend_desc}\n"
        md += f"- **使用语音回答的题目数**: {speech_summary.get('total_questions_with_speech', 0)}\n"
    else:
        md += f"- {speech_summary.get('message', '本次面试未使用语音输入')}\n"
    
    md += "\n---\n\n## 学习建议\n\n"
    for plan in summary['learning_plan']:
        md += f"- 📚 {plan}\n"
    
    md += "\n---\n\n## 推荐题单\n\n"
    if summary['recommended_questions']:
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
        
        md += f"**反馈**:\n\n{eval_obj.feedback_text}\n\n"
        md += "---\n\n"
    
    return md

