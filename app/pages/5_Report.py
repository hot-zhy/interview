"""Report page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import InterviewSession, Report
from backend.services.report_generator import generate_report
from backend.core.logging import logger
from app.components.auth_utils import init_session_state, check_auth
from app.components.auth_loader import load_auth_on_page_load
from app.components.styles import inject_global_styles
from app.components.sidebar import render_sidebar
from app.i18n import t

st.set_page_config(page_title="Report", page_icon="📊", layout="wide")

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
    
    st.title(f"📊 {t('report.title')}")
    st.caption(t("report.subtitle"))
    st.markdown("---")
    
    sessions = db.query(InterviewSession).filter(
        InterviewSession.user_id == user_id,
        InterviewSession.status == "completed"
    ).order_by(InterviewSession.ended_at.desc()).all()
    
    if not sessions:
        st.info(f"📭 {t('report.no_sessions')}")
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
        if st.button(f"📄 {t('report.generate')}", use_container_width=True, type="primary"):
            with st.spinner(t("report.generating")):
                try:
                    report_data = generate_report(db, session_id)
                    
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
        
        # Summary metrics
        summary = report.summary_json
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📈 综合得分", f"{summary.get('overall_score', 0):.2f}")
        col2.metric("✅ 优势数量", len(summary.get('strengths', [])))
        col3.metric("⚠️ 待改进", len(summary.get('weaknesses', [])))
        col4.metric("📌 缺失知识点", len(summary.get('missing_knowledge', [])))
        
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
            "📥 下载报告 (Markdown)",
            data=report.markdown,
            file_name=f"interview_report_{session_id}.md",
            mime="text/markdown"
        )

if __name__ == "__main__":
    main()

