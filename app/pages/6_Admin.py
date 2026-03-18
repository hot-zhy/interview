"""Admin page."""
import streamlit as st
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import (
    User, Resume, QuestionBank, InterviewSession, Evaluation, AskedQuestion
)
from sqlalchemy import func
from app.components.auth_utils import init_session_state, check_auth
from app.components.auth_loader import load_auth_on_page_load
from app.components.ui import inject_common_styles

st.set_page_config(page_title="管理后台", page_icon="⚙️")

# Load auth from localStorage first
load_auth_on_page_load()

# Initialize session state
init_session_state()

def main():
    inject_common_styles()
    check_auth()

    db = next(get_db())
    st.title("⚙️ 管理后台")
    st.divider()

    st.subheader("系统统计")
    col1, col2, col3, col4 = st.columns(4)
    
    user_count = db.query(User).count()
    resume_count = db.query(Resume).count()
    question_count = db.query(QuestionBank).count()
    session_count = db.query(InterviewSession).count()
    
    col1.metric("用户数", user_count)
    col2.metric("简历数", resume_count)
    col3.metric("题目数", question_count)
    col4.metric("面试数", session_count)
    st.divider()
    st.subheader("面试记录")
    
    sessions = db.query(InterviewSession).order_by(InterviewSession.started_at.desc()).limit(20).all()
    
    if sessions:
        for session in sessions:
            with st.expander(f"{session.track} - {session.user_id} ({session.started_at.strftime('%Y-%m-%d %H:%M')})"):
                col1, col2, col3 = st.columns(3)
                col1.text(f"状态: {session.status}")
                col2.text(f"轮数: {session.current_round}/{session.total_rounds}")
                col3.text(f"难度: {session.level}")
                
                # Get average score if completed
                if session.status == "completed":
                    avg_score = (
                        db.query(func.avg(Evaluation.overall_score))
                        .join(AskedQuestion, Evaluation.asked_question)
                        .filter(AskedQuestion.session_id == session.id)
                        .scalar()
                    )
                    
                    if avg_score:
                        st.metric("平均得分", f"{avg_score:.2f}")
    else:
        st.info("暂无面试记录")
    
    st.markdown("---")
    
    # Question bank statistics
    st.subheader("题库统计")
    
    if question_count > 0:
        # By chapter
        chapters = db.query(
            QuestionBank.chapter,
            func.count(QuestionBank.id).label('count')
        ).group_by(QuestionBank.chapter).all()
        
        st.markdown("#### 按章节")
        for chapter, count in chapters:
            st.text(f"{chapter}: {count} 题")
        
        # By difficulty
        difficulties = db.query(
            QuestionBank.difficulty,
            func.count(QuestionBank.id).label('count')
        ).group_by(QuestionBank.difficulty).all()
        
        st.markdown("#### 按难度")
        for diff, count in sorted(difficulties):
            st.text(f"难度 {diff}: {count} 题")

if __name__ == "__main__":
    main()

