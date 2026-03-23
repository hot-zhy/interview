"""Interview page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.components.secrets_bridge import bridge_secrets; bridge_secrets()

import streamlit as st
from backend.db.base import get_db
from backend.db.models import InterviewSession, Resume
from backend.services.interview_engine import (
    create_session, start_interview, submit_answer, get_session_turns
)
from backend.services.resume_track_matcher import check_resume_track_match
from backend.core.config import settings
from app.components.avatar import render_avatar
from app.components.auth_utils import init_session_state, check_auth
from app.components.styles import inject_global_styles, render_metric_card
from st_audiorec import st_audiorec
from app.components.auth_loader import load_auth_on_page_load
from app.components.expression_video import render_expression_video, get_accumulated_expressions, clear_accumulated_expressions
from app.components.sidebar import render_sidebar
from app.i18n import t
import base64
import json

st.set_page_config(page_title="Interview", layout="wide")
inject_global_styles()
load_auth_on_page_load()
init_session_state()


def _inject_interview_styles():
    st.markdown("""
    <style>
    /* Chat bubble styles */
    .chat-bubble {
        padding: 12px 16px;
        border-radius: 16px;
        margin: 6px 0;
        max-width: 88%;
        line-height: 1.6;
        font-size: 0.95rem;
        word-wrap: break-word;
    }
    .chat-bubble.interviewer {
        background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%);
        color: white;
        border-bottom-left-radius: 4px;
        margin-right: auto;
        box-shadow: 0 2px 8px rgba(99,102,241,0.2);
    }
    .chat-bubble.candidate {
        background: #ffffff;
        color: #1e293b;
        border: 1px solid #e2e8f0;
        border-bottom-right-radius: 4px;
        margin-left: auto;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .chat-role {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-bottom: 2px;
        font-weight: 600;
    }
    .chat-role.right { text-align: right; }

    /* Answer input area pinned at bottom */
    .answer-area {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px;
        margin-top: 8px;
        box-shadow: 0 -2px 8px rgba(0,0,0,0.04);
    }

    /* Side panel card */
    .side-panel-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)


def _render_chat_bubbles(turns):
    """Render chat history as styled bubbles."""
    for turn in turns:
        if turn["role"] == "interviewer":
            st.markdown(
                f'<div class="chat-role">{t("interview.interviewer")}</div>'
                f'<div class="chat-bubble interviewer">{turn["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="chat-role right">You</div>'
                f'<div class="chat-bubble candidate">{turn["content"]}</div>',
                unsafe_allow_html=True,
            )


def main():
    render_sidebar()
    check_auth()
    _inject_interview_styles()

    user_id = st.session_state.user_id
    db = next(get_db())

    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "avatar_state" not in st.session_state:
        st.session_state.avatar_state = "idle"

    # ── Setup section (only when no active session) ──
    if not st.session_state.current_session_id:
        st.title(t('interview.title'))
        st.caption(t("interview.subtitle"))
        st.markdown("---")

        col1, col2, col3 = st.columns(3)
        with col1:
            track = st.selectbox(
                t("interview.track"),
                options=list(settings.track_chapters.keys()),
                key="new_track",
            )
        with col2:
            level = st.selectbox(
                t("interview.initial_level"),
                options=list(range(1, 6)),
                index=2,
                key="new_level",
            )
        with col3:
            total_rounds = st.number_input(
                t("interview.rounds"), min_value=5, max_value=20, value=10, key="new_rounds"
            )

        resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
        use_resume = st.checkbox(t("interview.use_resume"), key="use_resume")
        resume_id = None
        if use_resume and resumes:
            resume_options = {f"{r.filename} ({r.created_at.strftime('%Y-%m-%d')})": r.id for r in resumes}
            selected_resume = st.selectbox(t("interview.select_resume"), options=list(resume_options.keys()))
            resume_id = resume_options[selected_resume]
        elif use_resume and not resumes:
            st.warning(t("interview.upload_resume_first"))
            use_resume = False

        if st.button(t('interview.start_interview'), use_container_width=True, type="primary"):
            # 若使用简历，先校验简历与岗位方向是否匹配
            if use_resume and resume_id:
                resume = db.query(Resume).filter(Resume.id == resume_id).first()
                if resume:
                    skills = (resume.parsed_json or {}).get("skills") or []
                    matched, _ = check_resume_track_match(skills, track)
                    if not matched:
                        st.error(t("interview.resume_track_mismatch"))
                        return
            try:
                with st.spinner(t("interview.preparing")):
                    session = create_session(
                        db=db, user_id=user_id, track=track, level=level,
                        resume_id=resume_id if use_resume else None,
                        total_rounds=total_rounds,
                    )
                    st.session_state.current_session_id = session.id
                    result = start_interview(db, session.id)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        return

    # ── Active interview ──
    session_id = st.session_state.current_session_id
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        st.error(t("interview.session_not_found"))
        st.session_state.current_session_id = None
        st.rerun()

    # Compact header: title + stats + end button in one row
    progress_ratio = session.current_round / session.total_rounds if session.total_rounds else 0
    remain = max(session.total_rounds - session.current_round, 0)
    st.markdown(f"""
    <div style="display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:8px;">
        <div style="font-size:1.15rem; font-weight:700; color:#1e293b;">{session.track}</div>
        <div style="display:flex; gap:18px; font-size:0.85rem; color:#64748b;">
            <span>{t("interview.round")} <b style="color:#1e293b;">{session.current_round}/{session.total_rounds}</b></span>
            <span>{t("interview.difficulty")} <b style="color:#1e293b;">{session.level}</b></span>
            <span><b style="color:#1e293b;">{remain}</b> left</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.progress(min(max(progress_ratio, 0.0), 1.0))

    if session.current_round == 0:
        with st.spinner(t("interview.preparing")):
            result = start_interview(db, session_id)
            if "error" in result:
                st.error(result["error"])
                return
            else:
                st.rerun()

    # ── Main layout: [avatar+video] | [chat+answer] ──
    turns = get_session_turns(db, session_id)
    last_interviewer = next((turn for turn in reversed(turns) if turn["role"] == "interviewer"), None)
    text_to_speak = ""
    if last_interviewer:
        last_spoken = st.session_state.get("_avatar_last_spoken_id")
        if last_spoken != last_interviewer.get("id"):
            text_to_speak = last_interviewer["content"]
            st.session_state["_avatar_last_spoken_id"] = last_interviewer.get("id")

    col_side, col_main = st.columns([1, 2.5])

    # Left panel: avatar + expression
    with col_side:
        render_avatar(st.session_state.avatar_state, text_to_speak=text_to_speak)
        render_expression_video(session_id)

    # Right panel: unified chat + answer
    with col_main:
        # Chat history
        chat_container = st.container(height=420)
        with chat_container:
            _render_chat_bubbles(turns)

        # Answer input (directly below chat, no tab switch)
        if session.status != "active":
            st.info(t("interview.interview_ended"))
            return

        answer_mode = st.radio(
            "", [t("interview.text_answer"), t("interview.voice_answer")],
            horizontal=True, key="answer_mode", label_visibility="collapsed",
        )

        if answer_mode == t("interview.text_answer"):
            answer_text = st.text_area(
                "", height=120, key="answer_input",
                placeholder=t("interview.answer_placeholder"),
                label_visibility="collapsed",
            )
            if answer_text:
                st.session_state.avatar_state = "listening"

            if st.button(t('interview.submit'), use_container_width=True, type="primary"):
                if not answer_text or not answer_text.strip():
                    st.warning(t("interview.please_input"))
                else:
                    accumulated = get_accumulated_expressions()
                    expr_data = {"analyses": accumulated} if accumulated else None
                    with st.status("正在评估你的回答...", expanded=True) as status:
                        st.write("🔍 分析回答内容...")
                        result = submit_answer(
                            db, session_id, answer_text.strip(),
                            answer_type="text", expression_data=expr_data,
                        )
                        if "error" not in result:
                            st.write("📊 计算自适应难度...")
                            st.write("📋 选择下一个问题...")
                            status.update(label="✅ 评估完成", state="complete")
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        # Show evaluation feedback before moving to next question
                        ev = result.get("evaluation", {})
                        if ev:
                            st.session_state["_last_eval"] = ev
                        clear_accumulated_expressions()
                        st.session_state.avatar_state = "idle"
                        st.rerun()
        else:
            st.caption(t('interview.audio_tip'))
            wav_audio_data = st_audiorec()
            if wav_audio_data is not None:
                import hashlib
                MIN_AUDIO_BYTES = 8000
                if len(wav_audio_data) < MIN_AUDIO_BYTES:
                    st.warning(t('interview.audio_too_short'))
                else:
                    h = hashlib.sha256(wav_audio_data).hexdigest()
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
                        accumulated = get_accumulated_expressions()
                        expr_data = {"analyses": accumulated} if accumulated else None
                        with st.status("正在处理语音回答...", expanded=True) as status:
                            st.write("🎤 识别语音内容...")
                            result = submit_answer(
                                db, session_id, answer_text=None,
                                answer_type="audio", audio_data=audio_data,
                                expression_data=expr_data,
                            )
                            if "error" not in result:
                                st.write("🔍 分析回答内容...")
                                st.write("📋 选择下一个问题...")
                                status.update(label="✅ 评估完成", state="complete")
                        if "error" in result:
                            st.error(result["error"])
                        else:
                            ev = result.get("evaluation", {})
                            if ev:
                                st.session_state["_last_eval"] = ev
                            clear_accumulated_expressions()
                            st.session_state["_audio_submitted_round"] = result.get("round", session.current_round + 1)
                            st.session_state.avatar_state = "idle"
                            st.rerun()
            st.session_state.avatar_state = "listening"

    # Show last evaluation feedback (if available)
    last_eval = st.session_state.get("_last_eval")
    if last_eval and session.status == "active":
        with col_main:
            with st.expander("📊 上一题评估反馈", expanded=False):
                score = last_eval.get("overall_score", 0)
                cols = st.columns(6)
                cols[0].metric("综合", f"{score:.0%}")
                for i, (dim, label) in enumerate([
                    ("correctness", "正确"), ("depth", "深度"), ("clarity", "清晰"),
                    ("practicality", "实用"), ("tradeoffs", "权衡")
                ]):
                    val = last_eval.get("scores", {}).get(dim, 0)
                    cols[i + 1].metric(label, f"{val:.0%}")
                fb = last_eval.get("feedback", "")
                if fb:
                    st.caption(fb[:200])
                missing = last_eval.get("missing_points", [])
                if missing:
                    st.caption("缺失点: " + " · ".join(missing[:3]))

    # Sidebar info with adaptive difficulty
    current_difficulty = session.level
    asked_qs = db.query(AskedQuestion).filter(
        AskedQuestion.session_id == session_id
    ).order_by(AskedQuestion.created_at.desc()).first()
    if asked_qs:
        current_difficulty = asked_qs.difficulty

    with st.sidebar:
        st.markdown(f"### {t('interview.session_info')}")
        st.text(f"{t('interview.direction')}: {session.track}")
        diff_arrow = ""
        if current_difficulty > session.level:
            diff_arrow = " ↑"
        elif current_difficulty < session.level:
            diff_arrow = " ↓"
        st.text(f"{t('interview.difficulty')}: {current_difficulty}/5{diff_arrow}")
        st.text(f"{t('interview.status')}: {session.status}")
        st.text(f"{t('interview.rounds_count')}: {session.current_round}/{session.total_rounds}")
        st.markdown("---")
        if st.button(t('interview.end_interview'), use_container_width=True, type="secondary"):
            from backend.services.interview_engine import end_interview
            end_interview(db, session_id)
            st.session_state.current_session_id = None
            st.rerun()
        if st.button(t('interview.exit_session'), use_container_width=True):
            st.session_state.current_session_id = None
            st.rerun()


if __name__ == "__main__":
    main()
