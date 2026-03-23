"""Interview page."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.components.secrets_bridge import bridge_secrets; bridge_secrets()

import streamlit as st
from backend.db.base import get_db
from backend.db.models import InterviewSession, Resume, AskedQuestion
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

    /* AI thinking bubble (like ChatGPT reasoning) */
    .thinking-bubble {
        max-width: 85%;
        padding: 10px 16px;
        margin: 6px 0;
        border-radius: 12px;
        background: linear-gradient(135deg, #f0f4ff 0%, #e8eeff 100%);
        border: 1px dashed #a5b4fc;
        font-size: 0.85rem;
        color: #4338ca;
        line-height: 1.5;
    }
    .thinking-bubble .step {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 2px 0;
    }
    .thinking-bubble .step.active {
        font-weight: 600;
    }
    .thinking-bubble .step.done {
        color: #16a34a;
    }
    .thinking-label {
        font-size: 0.7rem;
        color: #6366f1;
        font-weight: 700;
        margin-bottom: 4px;
        letter-spacing: 0.5px;
    }

    /* Eval result card in chat */
    .eval-card {
        max-width: 85%;
        padding: 12px 16px;
        margin: 6px 0;
        border-radius: 12px;
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        font-size: 0.85rem;
    }
    .eval-card .score-row {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        margin: 6px 0;
    }
    .eval-card .score-item {
        text-align: center;
        min-width: 48px;
    }
    .eval-card .score-item .val {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e293b;
    }
    .eval-card .score-item .lbl {
        font-size: 0.65rem;
        color: #94a3b8;
    }
    .eval-card .feedback {
        margin-top: 8px;
        font-size: 0.8rem;
        color: #475569;
        line-height: 1.4;
    }
    </style>
    """, unsafe_allow_html=True)


def _show_thinking(placeholder, message: str, step: int = 1):
    """Show a ChatGPT-style thinking indicator inside the chat area."""
    steps_html = ""
    all_steps = [
        ("🔍", "分析回答内容，提取知识点"),
        ("🤖", "AI 评估回答质量（5维度评分）"),
        ("📊", "计算自适应难度，更新面试状态"),
        ("📋", "智能选择下一个问题"),
    ]
    for i, (icon, text) in enumerate(all_steps):
        if i < step:
            steps_html += f'<div class="step done">{icon} ✓ {text}</div>'
        elif i == step:
            steps_html += f'<div class="step active">{icon} ⏳ {text}...</div>'
        else:
            steps_html += f'<div class="step">{icon} {text}</div>'

    placeholder.markdown(
        f'<div class="thinking-label">💭 AI 思考中</div>'
        f'<div class="thinking-bubble">{steps_html}</div>',
        unsafe_allow_html=True,
    )


def _render_eval_card(ev: dict) -> str:
    """Build HTML for an inline evaluation card."""
    scores = ev.get("scores", {})
    overall = ev.get("overall_score", 0)
    feedback = ev.get("feedback", "")
    provenance = ev.get("_provenance", "")
    prov_tag = "AI评估" if provenance == "llm" else "规则评估" if provenance == "rule" else "混合评估"

    dims = [("综合", overall), ("正确", scores.get("correctness", 0)),
            ("深度", scores.get("depth", 0)), ("清晰", scores.get("clarity", 0)),
            ("实用", scores.get("practicality", 0)), ("权衡", scores.get("tradeoffs", 0))]

    items = "".join(
        f'<div class="score-item"><div class="val">{v:.0%}</div><div class="lbl">{k}</div></div>'
        for k, v in dims
    )
    fb_html = f'<div class="feedback">{feedback[:150]}{"..." if len(feedback) > 150 else ""}</div>' if feedback else ""
    return (
        f'<div class="thinking-label">📊 {prov_tag}</div>'
        f'<div class="eval-card">'
        f'<div class="score-row">{items}</div>'
        f'{fb_html}'
        f'</div>'
    )


def _render_chat_bubbles(turns):
    """Render chat history as styled bubbles, with thinking/eval cards interleaved."""
    eval_history = st.session_state.get("_eval_history", {})

    for i, turn in enumerate(turns):
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
            # Show eval card after each candidate answer (if we have data)
            turn_id = str(turn.get("id", i))
            ev = eval_history.get(turn_id)
            if ev:
                st.markdown(_render_eval_card(ev), unsafe_allow_html=True)


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

        # Follow-up indicator
        if st.session_state.get("_last_was_followup"):
            st.markdown(
                '<div style="display:inline-block;background:#6366f1;color:white;'
                'padding:2px 10px;border-radius:12px;font-size:13px;margin-bottom:8px">'
                '🔍 AI 追问 — 针对你上一个回答的知识缺口深入探查</div>',
                unsafe_allow_html=True,
            )
            st.session_state["_last_was_followup"] = False

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

                    # Show thinking process inside the chat area
                    with chat_container:
                        thinking_placeholder = st.empty()
                        _show_thinking(thinking_placeholder, "🔍 正在分析你的回答...", step=1)

                    result = submit_answer(
                        db, session_id, answer_text.strip(),
                        answer_type="text", expression_data=expr_data,
                    )

                    if "error" in result:
                        with chat_container:
                            thinking_placeholder.empty()
                        st.error(result["error"])
                    else:
                        with chat_container:
                            _show_thinking(thinking_placeholder, "📊 评估完成，正在选择下一题...", step=2)

                        ev = result.get("evaluation", {})
                        if ev:
                            st.session_state["_last_eval"] = ev
                            # Store eval keyed by the latest candidate turn ID
                            candidate_turns = [t for t in get_session_turns(db, session_id) if t["role"] == "candidate"]
                            if candidate_turns:
                                if "_eval_history" not in st.session_state:
                                    st.session_state["_eval_history"] = {}
                                st.session_state["_eval_history"][str(candidate_turns[-1]["id"])] = ev
                        st.session_state["_last_was_followup"] = result.get("followup", False)
                        st.session_state["_last_followup_reason"] = result.get("followup_reason", "")
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
                        with chat_container:
                            thinking_placeholder = st.empty()
                            _show_thinking(thinking_placeholder, "🎤 正在识别语音并分析...", step=1)
                        result = submit_answer(
                            db, session_id, answer_text=None,
                            answer_type="audio", audio_data=audio_data,
                            expression_data=expr_data,
                        )
                        if "error" in result:
                            with chat_container:
                                thinking_placeholder.empty()
                            st.error(result["error"])
                        else:
                            with chat_container:
                                _show_thinking(thinking_placeholder, "📊 评估完成，正在选择下一题...", step=2)
                            ev = result.get("evaluation", {})
                            if ev:
                                st.session_state["_last_eval"] = ev
                                candidate_turns = [t for t in get_session_turns(db, session_id) if t["role"] == "candidate"]
                                if candidate_turns:
                                    if "_eval_history" not in st.session_state:
                                        st.session_state["_eval_history"] = {}
                                    st.session_state["_eval_history"][str(candidate_turns[-1]["id"])] = ev
                            st.session_state["_last_was_followup"] = result.get("followup", False)
                            st.session_state["_last_followup_reason"] = result.get("followup_reason", "")
                            clear_accumulated_expressions()
                            st.session_state["_audio_submitted_round"] = result.get("round", session.current_round + 1)
                            st.session_state.avatar_state = "idle"
                            st.rerun()
            st.session_state.avatar_state = "listening"

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
