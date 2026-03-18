"""Interview page."""
import streamlit as st
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import InterviewSession, Resume
from backend.services.interview_engine import (
    create_session, start_interview, submit_answer, get_session_turns
)
from backend.core.config import settings
from app.components.avatar import render_avatar
from app.components.tts import speak_text
from app.components.audio_submit import render_audio_submit
from app.components.auth_utils import init_session_state, check_auth
from st_audiorec import st_audiorec
from app.components.auth_loader import load_auth_on_page_load
from app.components.ui import inject_common_styles
import time
import base64
import json

st.set_page_config(page_title="面试", page_icon="💼", layout="wide")

# Load auth from localStorage first
load_auth_on_page_load()

# Initialize session state
init_session_state()

def main():
    inject_common_styles()
    check_auth()

    user_id = st.session_state.user_id
    db = next(get_db())

    st.title("💼 开始面试")
    st.divider()

    # Initialize session state
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "avatar_state" not in st.session_state:
        st.session_state.avatar_state = "idle"
    
    # Create new interview
    with st.expander("创建新面试", expanded=st.session_state.current_session_id is None):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            track = st.selectbox(
                "技术方向",
                options=list(settings.track_chapters.keys()),
                key="new_track"
            )
        
        with col2:
            level = st.selectbox(
                "初始难度",
                options=list(range(1, 6)),
                index=2,
                key="new_level"
            )
        
        with col3:
            total_rounds = st.number_input(
                "面试轮数",
                min_value=5,
                max_value=20,
                value=10,
                key="new_rounds"
            )
        
        # Resume selection
        resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
        use_resume = st.checkbox("基于简历定制题目", key="use_resume")
        resume_id = None
        
        if use_resume and resumes:
            resume_options = {f"{r.filename} ({r.created_at.strftime('%Y-%m-%d')})": r.id for r in resumes}
            selected_resume = st.selectbox("选择简历", options=list(resume_options.keys()))
            resume_id = resume_options[selected_resume]
        elif use_resume and not resumes:
            st.warning("请先上传简历")
            use_resume = False
        
        if st.button("开始面试", use_container_width=True, type="primary"):
            try:
                session = create_session(
                    db=db,
                    user_id=user_id,
                    track=track,
                    level=level,
                    resume_id=resume_id if use_resume else None,
                    total_rounds=total_rounds
                )
                st.session_state.current_session_id = session.id
                st.success("面试已创建！")
                st.rerun()
            except Exception as e:
                st.error(f"创建失败：{str(e)}")
    
    # Interview room
    if st.session_state.current_session_id:
        session_id = st.session_state.current_session_id
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        
        if not session:
            st.error("面试会话不存在")
            st.session_state.current_session_id = None
            st.rerun()
        
        st.divider()
        st.markdown(f"### 面试进行中 · {session.track}")
        st.caption(f"第 {session.current_round} / {session.total_rounds} 轮")

        # Initialize interview if needed
        if session.current_round == 0:
            if st.button("开始第一题", use_container_width=True, type="primary"):
                with st.spinner("正在准备题目..."):
                    result = start_interview(db, session_id)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.rerun()
        
        # Interview interface
        if session.current_round > 0:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### 👤 面试官")
                # Enhanced avatar with better realism
                render_avatar(st.session_state.avatar_state)
            
            with col2:
                st.markdown("#### 💬 对话区")
                # Display conversation history
                turns = get_session_turns(db, session_id)
                
                chat_container = st.container()
                with chat_container:
                    for idx, turn in enumerate(turns):
                        if turn["role"] == "interviewer":
                            with st.chat_message("assistant"):
                                st.markdown(turn["content"])
                                # Auto-speak for new interviewer messages
                                if idx == len(turns) - 1 and len(turns) > 0:
                                    try:
                                        speak_text(turn["content"])
                                        st.session_state.avatar_state = "speaking"
                                    except:
                                        pass
                        else:
                            with st.chat_message("user"):
                                st.markdown(turn["content"])
                
                # Answer input - support both text and audio
                if session.status == "active":
                    st.divider()
                    st.markdown("#### 💬 输入回答")
                    # Answer mode selection
                    answer_mode = st.radio(
                        "选择回答方式",
                        ["文字回答", "语音回答"],
                        horizontal=True,
                        key="answer_mode"
                    )
                    
                    answer_text = None
                    audio_data = None
                    
                    if answer_mode == "文字回答":
                        answer_text = st.text_area(
                            "输入你的回答",
                            height=150,
                            key="answer_input",
                            placeholder="在此输入你的回答..."
                        )
                        
                        # Update avatar state when user is typing
                        if answer_text:
                            st.session_state.avatar_state = "listening"
                    else:
                        # Audio recording: use component that returns bytes to Python (no hidden input / sessionStorage)
                        st.info("💡 点击下方录音按钮，录完后将自动提交；分析在后台进行，面试结束后可在报告中查看结果。")
                        # 不要在新轮次清空 _audio_last_hash，否则 rerun 后同段短录音会反复被当作“新录音”重复提交

                        wav_audio_data = st_audiorec()
                        if wav_audio_data is not None:
                            import hashlib
                            # 过短录音（如刚点 start 就 stop）不提交，避免误触导致整场面试被刷完
                            MIN_AUDIO_BYTES = 8000  # 约 0.25 秒 16kHz 16bit 单声道
                            if len(wav_audio_data) < MIN_AUDIO_BYTES:
                                st.warning("⚠️ 录音太短，请录制至少约 1 秒后再提交。")
                            else:
                                h = hashlib.sha256(wav_audio_data).hexdigest()
                                # 避免 rerun 后同一段音频被重复提交（同一轮次且同一 hash 视为已提交）
                                already_submitted = (
                                    st.session_state.get("_audio_submitted_round") == session.current_round
                                    and st.session_state.get("_audio_last_hash") == h
                                )
                                if not already_submitted and st.session_state.get("_audio_last_hash") != h:
                                    st.session_state["_audio_last_hash"] = h
                                    audio_data = {
                                        "audioData": base64.b64encode(wav_audio_data).decode("utf-8"),
                                        "audioFormat": "wav",
                                        "duration": 0,
                                    }
                                    with st.spinner("正在提交并分析语音回答..."):
                                        result = submit_answer(
                                            db, session_id, answer_text=None, answer_type="audio", audio_data=audio_data
                                        )
                                    if "error" in result:
                                        st.error(result["error"])
                                    else:
                                        # 标记本轮已提交，防止 rerun 后同段音频再次提交
                                        st.session_state["_audio_submitted_round"] = result.get("round", session.current_round + 1)
                                        st.session_state.avatar_state = "idle"
                                        st.rerun()

                        st.session_state.avatar_state = "listening"

                    st.caption("提交后将自动进入下一题，评价结果可在面试结束后的报告中查看。")
                    col_submit, col_end = st.columns([3, 1])
                    with col_submit:
                        submit_clicked = st.button("提交回答", use_container_width=True, type="primary")

                        if submit_clicked:
                            if answer_mode == "文字回答":
                                if not answer_text or not answer_text.strip():
                                    st.warning("请先输入回答")
                                else:
                                    with st.spinner("正在提交并评价..."):
                                        result = submit_answer(
                                            db, 
                                            session_id, 
                                            answer_text.strip(),
                                            answer_type="text"
                                        )
                                    if "error" in result:
                                        st.error(result["error"])
                                    else:
                                        # 分析结果在面试结束后于报告中统一查看
                                        st.session_state.avatar_state = "idle"
                                        st.rerun()
                            else:
                                # Audio mode: component auto-submits when recording is done. If user clicked submit, show upload fallback.
                                st.warning("⚠️ 请使用上方录音组件录完音（将自动提交），或在此上传录音文件")
                                uploaded_audio_fallback = st.file_uploader(
                                    "上传录音文件",
                                    type=['webm', 'wav', 'mp3', 'ogg'],
                                    key="audio_upload_fallback"
                                )
                                if uploaded_audio_fallback:
                                    audio_bytes = uploaded_audio_fallback.read()
                                    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
                                    ext = uploaded_audio_fallback.name.split('.')[-1] if '.' in uploaded_audio_fallback.name else "webm"
                                    audio_data = {
                                        "audioData": audio_b64,
                                        "audioFormat": ext,
                                        "duration": 0,
                                    }
                                    with st.spinner("正在提交并分析语音回答..."):
                                        result = submit_answer(
                                            db, session_id, answer_text=None, answer_type="audio", audio_data=audio_data
                                        )
                                    if "error" in result:
                                        st.error(result["error"])
                                    else:
                                        st.session_state.avatar_state = "idle"
                                        st.rerun()
                    
                    with col_end:
                        if st.button("结束面试", use_container_width=True, type="secondary"):
                            from backend.services.interview_engine import end_interview
                            result = end_interview(db, session_id)
                            st.session_state.current_session_id = None
                            st.success("面试已结束")
                            st.rerun()
                else:
                    st.info("面试已结束，请查看报告页面")
        
        # Session info sidebar
        with st.sidebar:
            st.markdown("### 面试信息")
            st.markdown(f"**方向** {session.track}  \n**难度** {session.level}  \n**状态** {session.status}  \n**进度** {session.current_round} / {session.total_rounds} 轮")
            st.divider()
            if st.button("退出当前面试", use_container_width=True):
                st.session_state.current_session_id = None
                st.rerun()

if __name__ == "__main__":
    main()

