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


def _score_band(score: float) -> str:
    if score >= 0.8:
        return "优秀"
    if score >= 0.65:
        return "良好"
    if score >= 0.5:
        return "可提升"
    return "风险"


def _render_ai_visual_report(summary: dict):
    visual = summary.get("visual_analytics") or {}
    llm_scoring = summary.get("llm_scoring") or {}
    dim_scores = summary.get("dimension_scores", {}) or {}
    per_q_scores = summary.get("per_question_scores", []) or []

    st.subheader("AI 评分仪表盘")
    score = float(summary.get("overall_score", 0) or 0)
    cols = st.columns(5)
    cols[0].metric("LLM 综合评分", f"{score:.2f}", _score_band(score))
    cols[1].metric("趋势变化", f"{visual.get('score_delta', 0):+.2f}")
    cols[2].metric("最佳轮次", visual.get("best_round") or "-", f"{visual.get('best_score', 0):.2f}")
    cols[3].metric("短板轮次", visual.get("weakest_round") or "-", f"{visual.get('weakest_score', 0):.2f}")
    cols[4].metric("LLM 重评分", f"{llm_scoring.get('rescored', 0)}/{llm_scoring.get('total', 0)}")

    if llm_scoring:
        st.caption(f"评分模型：{llm_scoring.get('model') or '未配置'} · {llm_scoring.get('message', '')}")

    try:
        import plotly.graph_objects as go
        import plotly.express as px

        gauge_col, radar_col = st.columns([1, 1])
        with gauge_col:
            gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=score,
                delta={"reference": 0.65},
                number={"valueformat": ".2f"},
                gauge={
                    "axis": {"range": [0, 1]},
                    "bar": {"color": "#2563eb"},
                    "steps": [
                        {"range": [0, 0.5], "color": "#fee2e2"},
                        {"range": [0.5, 0.75], "color": "#fef3c7"},
                        {"range": [0.75, 1], "color": "#dcfce7"},
                    ],
                    "threshold": {"line": {"color": "#ef4444", "width": 4}, "value": 0.6},
                },
                title={"text": "综合能力评分"},
            ))
            gauge.update_layout(height=330, margin=dict(l=20, r=20, t=60, b=20))
            st.plotly_chart(gauge, use_container_width=True)

        with radar_col:
            dim_order = ["correctness", "depth", "clarity", "practicality", "tradeoffs"]
            names = [DIM_LABELS.get(k, k) for k in dim_order]
            vals = [float(dim_scores.get(k, 0) or 0) for k in dim_order]
            radar = go.Figure()
            radar.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=names + [names[0]],
                fill="toself",
                name="能力画像",
                line_color="#0891b2",
            ))
            radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=False,
                title="五维能力雷达",
                height=330,
                margin=dict(l=30, r=30, t=60, b=20),
            )
            st.plotly_chart(radar, use_container_width=True)

        if per_q_scores:
            df = pd.DataFrame(per_q_scores)
            trend = px.line(
                df,
                x="round",
                y=["overall", "correctness", "depth", "clarity", "practicality", "tradeoffs"],
                markers=True,
                title="逐轮评分趋势",
                labels={"value": "得分", "round": "轮次", "variable": "维度"},
            )
            trend.update_yaxes(range=[0, 1])
            st.plotly_chart(trend, use_container_width=True)

        heatmap_rows = visual.get("heatmap_rows") or []
        if heatmap_rows:
            heat_df = pd.DataFrame(heatmap_rows)
            z_cols = ["correctness", "depth", "clarity", "practicality", "tradeoffs", "overall"]
            heat = go.Figure(data=go.Heatmap(
                z=heat_df[z_cols].values,
                x=[DIM_LABELS.get(c, "综合") if c != "overall" else "综合" for c in z_cols],
                y=[f"第{r}轮" for r in heat_df["round"]],
                colorscale="RdYlGn",
                zmin=0,
                zmax=1,
                colorbar=dict(title="得分"),
            ))
            heat.update_layout(title="逐题维度热力图", height=max(320, 42 * len(heat_df) + 120))
            st.plotly_chart(heat, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            chapter_summary = visual.get("chapter_summary") or []
            if chapter_summary:
                ch_df = pd.DataFrame(chapter_summary)
                fig = px.bar(ch_df, x="avg_score", y="chapter", orientation="h", color="avg_score",
                             range_x=[0, 1], color_continuous_scale="Tealgrn",
                             title="章节掌握度排行")
                st.plotly_chart(fig, use_container_width=True)
        with c2:
            diff_summary = visual.get("difficulty_summary") or []
            if diff_summary:
                diff_df = pd.DataFrame(diff_summary)
                fig = px.bar(diff_df, x="difficulty", y="avg_score", color="avg_score",
                             range_y=[0, 1], color_continuous_scale="Bluered",
                             title="不同难度表现")
                st.plotly_chart(fig, use_container_width=True)

    except Exception as exc:
        st.caption(f"高级图表加载失败，已降级显示基础图表：{exc}")

    insight_cols = st.columns(3)
    insight_cols[0].info(f"强项维度：{DIM_LABELS.get(visual.get('strongest_dimension'), visual.get('strongest_dimension') or '-')}")
    insight_cols[1].warning(f"短板维度：{DIM_LABELS.get(visual.get('weakest_dimension'), visual.get('weakest_dimension') or '-')}")
    insight_cols[2].success(f"报告结论：{_score_band(score)}")


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

        _render_ai_visual_report(summary)

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

