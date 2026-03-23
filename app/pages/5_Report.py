"""Report page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.components.secrets_bridge import bridge_secrets; bridge_secrets()

import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import InterviewSession, Report, Evaluation, AskedQuestion
from backend.services.report_generator import generate_report
from backend.core.logging import logger
from app.components.auth_utils import init_session_state, check_auth
from app.components.auth_loader import load_auth_on_page_load
from app.components.styles import inject_global_styles
from app.components.sidebar import render_sidebar
from app.i18n import t

# Dimension labels for charts
DIM_LABELS = {
    "correctness": "正确性",
    "depth": "深度",
    "clarity": "清晰度",
    "practicality": "实用性",
    "tradeoffs": "权衡分析",
}

st.set_page_config(page_title="Report", layout="wide")

# Inject global styles
inject_global_styles()

# Load auth from localStorage first
load_auth_on_page_load()

# Initialize session state
init_session_state()

def main():
    render_sidebar()
    check_auth()
    
    user_id = st.session_state.user_id
    db = next(get_db())
    
    st.title(t('report.title'))
    st.caption(t("report.subtitle"))
    st.markdown("---")
    
    sessions = db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id,
        InterviewSession.status == "completed"
    ).order_by(InterviewSession.ended_at.desc()).all()
    
    if not sessions:
        st.info(t('report.no_sessions'))
        return
    
    session_options = {
        f"{s.track} - {s.started_at.strftime('%Y-%m-%d %H:%M')}": s.id
        for s in sessions
    }
    selected_session = st.selectbox(
        t("report.select_session"),
        options=list(session_options.keys()),
        key="report_session"
    )
    
    session_id = session_options[selected_session]
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    
    # Check if report exists
    report = db.query(Report).filter(Report.session_id == session_id).first()
    
    if not report:
        if st.button(t('report.generate'), use_container_width=True, type="primary"):
            with st.spinner(t("report.generating")):
                try:
                    with st.status("正在生成面试报告...", expanded=True) as gen_status:
                        st.write("📊 汇总评分数据...")
                        st.write("🤖 AI 深度分析面试表现...")
                        st.write("📝 生成个性化评估报告...")
                        report_data = generate_report(db, session_id)
                        gen_status.update(label="✅ 报告生成完成", state="complete")
                    
                    report = Report(
                        session_id=session_id,
                        summary_json=report_data["summary_json"],
                        markdown=report_data["markdown"]
                    )
                    db.add(report)
                    db.commit()
                    db.refresh(report)
                    
                    st.success(t("report.generate_success"))
                    st.rerun()
                except Exception as e:
                    logger.error(f"Report generation error: {e}")
                    st.error(f"生成失败：{str(e)}")
    else:
        # Display report
        st.markdown("---")
        if st.button("重新生成报告（AI深度分析）", key="regen_report", type="secondary"):
            try:
                with st.status("正在重新生成报告...", expanded=True) as regen_status:
                    st.write("📊 汇总评分数据...")
                    st.write("🤖 AI 多步深度分析...")
                    st.write("📝 生成个性化报告...")
                    report_data = generate_report(db, session_id)
                    regen_status.update(label="✅ 报告更新完成", state="complete")
                report.summary_json = report_data["summary_json"]
                report.markdown = report_data["markdown"]
                db.commit()
                st.success("报告已更新")
                st.rerun()
            except Exception as e:
                logger.error(f"Report regeneration error: {e}")
                st.error(f"重新生成失败：{str(e)}")

        # Summary metrics
        summary = report.summary_json

        # Fallback: compute dimension_scores from evaluations for old reports
        if not summary.get("dimension_scores") or not summary.get("per_question_scores"):
            evals = db.query(Evaluation).join(AskedQuestion).filter(
                AskedQuestion.session_id == session_id
            ).order_by(Evaluation.created_at).all()
            if evals:
                dim_sums = {"correctness": 0, "depth": 0, "clarity": 0, "practicality": 0, "tradeoffs": 0}
                per_q = []
                for i, e in enumerate(evals):
                    s = e.scores_json or {}
                    for k in dim_sums:
                        dim_sums[k] += s.get(k, 0)
                    per_q.append({
                        "round": i + 1,
                        "correctness": round(s.get("correctness", 0), 2),
                        "depth": round(s.get("depth", 0), 2),
                        "clarity": round(s.get("clarity", 0), 2),
                        "practicality": round(s.get("practicality", 0), 2),
                        "tradeoffs": round(s.get("tradeoffs", 0), 2),
                        "overall": round(e.overall_score, 2),
                    })
                if not summary.get("dimension_scores"):
                    summary["dimension_scores"] = {k: round(v / len(evals), 2) for k, v in dim_sums.items()}
                if not summary.get("per_question_scores"):
                    summary["per_question_scores"] = per_q

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("综合得分", f"{summary.get('overall_score', 0):.2f}")
        col2.metric("优势数量", len(summary.get('strengths', [])))
        col3.metric("待改进", len(summary.get('weaknesses', [])))
        col4.metric("缺失知识点", len(summary.get('missing_knowledge', [])))

        # LLM-generated overall summary callout
        if summary.get("overall_summary"):
            st.info(f"**AI 综合评估**: {summary['overall_summary']}")

        # Strategy trace (agentic innovation)
        if summary.get("strategy_trace"):
            with st.expander("🤖 AI 面试策略解读", expanded=False):
                st.write(summary["strategy_trace"])
                if summary.get("difficulty_trajectory"):
                    st.caption(f"难度轨迹: {' → '.join(str(d) for d in summary['difficulty_trajectory'])}")
                if summary.get("chapter_trace"):
                    st.caption(f"章节轨迹: {' → '.join(summary['chapter_trace'])}")

        # Knowledge gap analysis
        if summary.get("gap_analysis"):
            with st.expander("🔍 知识缺口深度分析", expanded=False):
                st.write(summary["gap_analysis"])

        # Dimension scores charts
        dim_scores = summary.get("dimension_scores", {})
        per_q_scores = summary.get("per_question_scores", [])

        if dim_scores:
            st.subheader("各维度评分")
            # Bar chart: dimension averages
            dim_order = ["correctness", "depth", "clarity", "practicality", "tradeoffs"]
            chart_data = pd.DataFrame([
                {"维度": DIM_LABELS.get(k, k), "得分": dim_scores.get(k, 0)}
                for k in dim_order if k in dim_scores
            ])
            if not chart_data.empty:
                bar_df = chart_data.set_index("维度")[["得分"]]
                st.bar_chart(bar_df, height=300)

            # Radar chart (if plotly available)
            try:
                import plotly.graph_objects as go
                dim_names = [DIM_LABELS.get(k, k) for k in dim_order if k in dim_scores]
                dim_vals = [dim_scores.get(k, 0) for k in dim_order if k in dim_scores]
                if dim_names and dim_vals:
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=dim_vals + [dim_vals[0]],
                        theta=dim_names + [dim_names[0]],
                        fill='toself',
                        name='各维度得分'
                    ))
                    fig.update_layout(
                        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                        showlegend=False,
                        title="五维评分雷达图",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                pass

        if per_q_scores:
            st.subheader("各题得分趋势")
            df = pd.DataFrame(per_q_scores)
            if not df.empty:
                line_df = df.set_index("round").rename(columns={
                    "correctness": "正确性",
                    "depth": "深度",
                    "clarity": "清晰度",
                    "practicality": "实用性",
                    "tradeoffs": "权衡",
                    "overall": "综合"
                })
                st.line_chart(line_df, height=300)

        st.markdown("---")
        
        # Display markdown report with custom table styling
        st.markdown("""
        <style>
        table {
            width: 100% !important;
            border-collapse: collapse;
            margin: 10px 0;
        }
        table th, table td {
            padding: 8px 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        table th {
            background-color: #f8f9fa;
            font-weight: bold;
            border-top: 2px solid #333;
            border-bottom: 2px solid #333;
        }
        table tr:last-child td {
            border-bottom: 2px solid #333;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown(report.markdown)
        
        # Download button
        st.download_button(
            "下载报告 (Markdown)",
            data=report.markdown,
            file_name=f"interview_report_{session_id}.md",
            mime="text/markdown"
        )

if __name__ == "__main__":
    main()

