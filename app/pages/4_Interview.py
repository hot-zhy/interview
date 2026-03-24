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
import html
import time
import hashlib
import streamlit.components.v1 as st_components

st.set_page_config(page_title="Interview", layout="wide")
inject_global_styles()
load_auth_on_page_load()
init_session_state()


def _inject_interview_styles():
    st.markdown("""
    <style>
    /* Lock viewport — no page-level scrolling during interview */
    section.main > div.block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 0 !important;
        max-height: 100vh;
        overflow: hidden;
    }

    /* Chat bubble styles */
    .chat-bubble {
        padding: 10px 14px;
        border-radius: 14px;
        margin: 4px 0;
        max-width: 90%;
        line-height: 1.55;
        font-size: 0.9rem;
        word-wrap: break-word;
    }
    .chat-bubble.interviewer {
        background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%);
        color: white;
        border-bottom-left-radius: 4px;
        margin-right: auto;
        box-shadow: 0 2px 8px rgba(99,102,241,0.2);
    }
    .chat-bubble.interviewer.thinking {
        background: #eef2ff;
        color: #3730a3;
        border: 1px solid #c7d2fe;
        box-shadow: none;
    }
    .chat-bubble.interviewer.eval {
        background: #ecfeff;
        color: #155e75;
        border: 1px solid #a5f3fc;
        box-shadow: none;
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
        font-size: 0.7rem;
        color: #94a3b8;
        margin-bottom: 1px;
        font-weight: 600;
    }
    .chat-role.right { text-align: right; }
    .typing-cursor {
        animation: blink 1s steps(1, end) infinite;
        margin-left: 2px;
    }
    @keyframes blink {
        50% { opacity: 0; }
    }
    </style>
    """, unsafe_allow_html=True)


def _render_interviewer_bubble(content: str):
    safe = html.escape(content).replace("\n", "<br>")
    st.markdown(
        f'<div class="chat-role">{t("interview.interviewer")}</div>'
        f'<div class="chat-bubble interviewer">{safe}</div>',
        unsafe_allow_html=True,
    )


def _candidate_html(content: str) -> str:
    safe = html.escape(content).replace("\n", "<br>")
    return (
        '<div class="chat-role right">You</div>'
        f'<div class="chat-bubble candidate">{safe}</div>'
    )


def _render_candidate_bubble(content: str):
    st.markdown(_candidate_html(content), unsafe_allow_html=True)


def _render_eval_bubble(content: str):
    safe = html.escape(content).replace("\n", "<br>")
    st.markdown(
        '<div class="chat-role">面试官 · 评估结果</div>'
        f'<div class="chat-bubble interviewer eval">{safe}</div>',
        unsafe_allow_html=True,
    )


def _get_thinking_logs(session_id: int):
    """Get persisted UI-only thinking logs for a session."""
    store = st.session_state.setdefault("_thinking_logs", {})
    key = str(session_id)
    if key not in store:
        store[key] = []
    logs = store[key]
    normalized = []
    for idx, item in enumerate(logs):
        if isinstance(item, dict) and "kind" in item:
            normalized.append(item)
        elif isinstance(item, dict) and "content" in item:
            normalized.append(
                {
                    "kind": "thinking",
                    "content": item.get("content", ""),
                    "anchor_candidate_idx": 999999,
                    "stage": f"legacy_{idx}",
                    "submit_token": f"legacy_{idx}",
                    "order": idx,
                }
            )
    store[key] = normalized
    return store[key]


def _thinking_html(content: str, live: bool = False) -> str:
    safe = html.escape(content).replace("\n", "<br>")
    cursor = '<span class="typing-cursor">▋</span>' if live else ""
    return (
        '<div class="chat-role">面试官 · 思考中</div>'
        f'<div class="chat-bubble interviewer thinking">{safe}{cursor}</div>'
    )


def _get_event_order_counter(session_id: int) -> int:
    key = str(session_id)
    counters = st.session_state.setdefault("_thinking_order_counter", {})
    if key not in counters:
        counters[key] = len(_get_thinking_logs(session_id))
    counters[key] += 1
    return counters[key]


def _append_chat_event(
    session_id: int,
    *,
    kind: str,
    content: str,
    anchor_candidate_idx: int,
    submit_token: str,
    stage: str,
):
    seen = _get_thinking_stage_seen(session_id)
    stage_key = f"{submit_token}:{stage}"
    if seen.get(stage_key):
        return
    _get_thinking_logs(session_id).append(
        {
            "kind": kind,
            "content": content,
            "anchor_candidate_idx": anchor_candidate_idx,
            "submit_token": submit_token,
            "stage": stage,
            "order": _get_event_order_counter(session_id),
        }
    )
    seen[stage_key] = True


def _render_chat_timeline(turns, session_id: int, optimistic_candidate: str = ""):
    logs = sorted(_get_thinking_logs(session_id), key=lambda x: x.get("order", 0))
    events_by_anchor = {}
    for item in logs:
        anchor = int(item.get("anchor_candidate_idx", 999999))
        events_by_anchor.setdefault(anchor, []).append(item)

    def _render_events(anchor_idx: int):
        for event in events_by_anchor.get(anchor_idx, []):
            if event.get("kind") == "evaluation":
                _render_eval_bubble(event.get("content", ""))
            else:
                st.markdown(_thinking_html(event.get("content", "")), unsafe_allow_html=True)

    candidate_idx = 0
    for turn in turns:
        if turn["role"] == "interviewer":
            _render_interviewer_bubble(turn["content"])
        else:
            _render_candidate_bubble(turn["content"])
            candidate_idx += 1
            _render_events(candidate_idx)

    if optimistic_candidate:
        _render_candidate_bubble(optimistic_candidate)
        candidate_idx += 1
        _render_events(candidate_idx)

    remaining = sorted(k for k in events_by_anchor.keys() if k > candidate_idx)
    for key in remaining:
        _render_events(key)


def _get_thinking_stage_seen(session_id: int):
    """Get stage de-dup cache for a session."""
    store = st.session_state.setdefault("_thinking_stage_seen", {})
    key = str(session_id)
    if key not in store:
        store[key] = {}
    return store[key]


def _show_thinking_stage(
    session_id: int,
    placeholder,
    submit_token: str,
    anchor_candidate_idx: int,
    stage: str,
    content: str,
    delay: float = 0.008,
):
    """Render typewriter thinking and persist once per submit stage."""
    _typewriter_thinking(placeholder, content, delay=delay)
    _append_chat_event(
        session_id,
        kind="thinking",
        content=content,
        anchor_candidate_idx=anchor_candidate_idx,
        submit_token=submit_token,
        stage=stage,
    )


def _eval_html(content: str, live: bool = False) -> str:
    safe = html.escape(content).replace("\n", "<br>")
    cursor = '<span class="typing-cursor">▋</span>' if live else ""
    return (
        '<div class="chat-role">面试官 · 评估结果</div>'
        f'<div class="chat-bubble interviewer eval">{safe}{cursor}</div>'
    )


def _show_eval_stage(
    session_id: int,
    placeholder,
    submit_token: str,
    anchor_candidate_idx: int,
    stage: str,
    content: str,
    delay: float = 0.006,
):
    """Typewriter eval bubble and persist."""
    if not content:
        return
    step = 2 if len(content) > 80 else 1
    for i in range(step, len(content) + 1, step):
        placeholder.markdown(_eval_html(content[:i], live=True), unsafe_allow_html=True)
        time.sleep(delay)
    placeholder.markdown(_eval_html(content, live=False), unsafe_allow_html=True)
    _append_chat_event(
        session_id,
        kind="evaluation",
        content=content,
        anchor_candidate_idx=anchor_candidate_idx,
        submit_token=submit_token,
        stage=stage,
    )


def _typewriter_thinking(placeholder, content: str, delay: float = 0.008):
    if not content:
        return
    step = 2 if len(content) > 80 else 1
    for i in range(step, len(content) + 1, step):
        placeholder.markdown(_thinking_html(content[:i], live=True), unsafe_allow_html=True)
        time.sleep(delay)
    placeholder.markdown(_thinking_html(content, live=False), unsafe_allow_html=True)


def _build_thinking_summary(result: dict) -> str:
    ev = result.get("evaluation", {}) or {}
    score = float(ev.get("overall_score", 0.0) or 0.0)
    missing = ev.get("missing_points", []) or []
    feedback = (ev.get("feedback", "") or "").strip()
    decision = "我会继续追问，针对你还不够扎实的点深入确认。" if result.get("followup") else "我会切换到下一题，继续扩展你的能力覆盖。"
    lines = [
        "我先快速拆解你这道题的回答：",
        f"- 语义匹配与关键点覆盖已完成，当前综合评估约 {score:.0%}。",
        f"- 识别到待补强点 {len(missing)} 个，已用于下一步提问策略。",
        f"- 决策：{decision}",
    ]
    if feedback:
        lines.append(f"- 评语摘要：{feedback[:100]}")
    return "\n".join(lines)


def _build_eval_summary(result: dict) -> str:
    ev = result.get("evaluation", {}) or {}
    scores = ev.get("scores", {}) or {}
    missing = ev.get("missing_points", []) or []
    lines = [
        f"综合评分：{float(ev.get('overall_score', 0.0) or 0.0):.0%}",
        "维度评分："
        f" 正确 {float(scores.get('correctness', 0.0)):.0%}"
        f" / 深度 {float(scores.get('depth', 0.0)):.0%}"
        f" / 清晰 {float(scores.get('clarity', 0.0)):.0%}"
        f" / 实用 {float(scores.get('practicality', 0.0)):.0%}"
        f" / 权衡 {float(scores.get('tradeoffs', 0.0)):.0%}",
    ]
    feedback = (ev.get("feedback", "") or "").strip()
    if feedback:
        lines.append(f"反馈：{feedback[:140]}")
    if missing:
        lines.append("待补强点：" + " · ".join(missing[:3]))
    return "\n".join(lines)


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
    <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:2px;">
        <div style="font-size:1rem; font-weight:700; color:#1e293b;">{session.track}</div>
        <div style="display:flex; gap:14px; font-size:0.8rem; color:#64748b;">
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
    candidate_turns = [turn for turn in turns if turn.get("role") == "candidate"]
    candidate_count = len(candidate_turns)
    pending_candidate_state = st.session_state.get("_pending_candidate_message", {})
    optimistic_candidate = ""
    if pending_candidate_state.get("session_id") == session_id:
        pending_content = (pending_candidate_state.get("content") or "").strip()
        if pending_content:
            db_has_pending = any((turn.get("content") or "").strip() == pending_content for turn in candidate_turns)
            if db_has_pending:
                st.session_state["_pending_candidate_message"] = {}
            else:
                optimistic_candidate = pending_content
    last_interviewer = next((turn for turn in reversed(turns) if turn["role"] == "interviewer"), None)
    text_to_speak = ""
    if last_interviewer:
        last_spoken = st.session_state.get("_avatar_last_spoken_id")
        if last_spoken != last_interviewer.get("id"):
            text_to_speak = last_interviewer["content"]
            st.session_state["_avatar_last_spoken_id"] = last_interviewer.get("id")

    col_side, col_main = st.columns([1, 3])

    # Left panel: avatar + expression
    with col_side:
        render_avatar(st.session_state.avatar_state, text_to_speak=text_to_speak)
        render_expression_video(session_id)

    # Right panel: unified chat + answer
    with col_main:
        # Chat history
        chat_container = st.container(height=400)
        with chat_container:
            _render_chat_timeline(turns, session_id, optimistic_candidate=optimistic_candidate)
            live_candidate_placeholder = st.empty()
            live_thinking_placeholder = st.empty()
            st_components.html(
                """<script>
                requestAnimationFrame(function(){
                    var f=window.frameElement;if(!f)return;
                    // Find the scrollable chat wrapper
                    var p=f.closest('[data-testid="stVerticalBlockBorderWrapper"]');
                    if(!p)p=f.parentElement;
                    while(p&&p.scrollHeight<=p.clientHeight)p=p.parentElement;
                    if(p){
                        // Dynamic height: viewport minus header(~90px) + input area(~200px) + margins(~30px)
                        var targetH=window.innerHeight-320;
                        if(targetH<250)targetH=250;
                        p.style.maxHeight=targetH+'px';
                        p.style.height=targetH+'px';
                        p.scrollTop=p.scrollHeight;
                    }
                });
                </script>""",
                height=0,
            )

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
                "", height=90, key=f"answer_input_{session.current_round}",
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
                    answer_clean = answer_text.strip()
                    st.session_state["_pending_candidate_message"] = {
                        "session_id": session_id,
                        "content": answer_clean,
                    }
                    live_candidate_placeholder.markdown(_candidate_html(answer_clean), unsafe_allow_html=True)
                    submit_token = f"r{session.current_round}:text:{hashlib.sha256(answer_clean.encode('utf-8')).hexdigest()[:10]}"
                    anchor_candidate_idx = candidate_count + 1
                    _show_thinking_stage(
                        session_id,
                        live_thinking_placeholder,
                        submit_token,
                        anchor_candidate_idx,
                        "received",
                        "收到你的回答，我正在分析关键点覆盖、表达深度和策略方向...",
                    )
                    _show_thinking_stage(
                        session_id,
                        live_thinking_placeholder,
                        submit_token,
                        anchor_candidate_idx,
                        "llm_eval",
                        "正在进行大模型动态评估：语义理解、关键点覆盖、逻辑结构和可落地性。",
                        delay=0.006,
                    )
                    result = submit_answer(
                        db, session_id, answer_clean,
                        answer_type="text", expression_data=expr_data,
                    )
                    if "error" in result:
                        _show_thinking_stage(
                            session_id,
                            live_thinking_placeholder,
                            submit_token,
                            anchor_candidate_idx,
                            "error",
                            "分析过程中出现异常，请你再提交一次，我会继续。",
                            delay=0.006,
                        )
                        st.session_state["_pending_candidate_message"] = {}
                        st.error(result["error"])
                    else:
                        _show_thinking_stage(
                            session_id,
                            live_thinking_placeholder,
                            submit_token,
                            anchor_candidate_idx,
                            "next_loading",
                            "分析完成，正在组织下一题，请稍等...",
                            delay=0.006,
                        )
                        _show_thinking_stage(
                            session_id,
                            live_thinking_placeholder,
                            submit_token,
                            anchor_candidate_idx,
                            "thinking_summary",
                            _build_thinking_summary(result),
                            delay=0.005,
                        )
                        _show_eval_stage(
                            session_id,
                            live_thinking_placeholder,
                            submit_token,
                            anchor_candidate_idx,
                            "evaluation_summary",
                            _build_eval_summary(result),
                            delay=0.004,
                        )
                        time.sleep(0.3)
                        ev = result.get("evaluation", {})
                        if ev:
                            st.session_state["_last_eval"] = ev
                        st.session_state["_pending_candidate_message"] = {}
                        st.session_state["_last_was_followup"] = result.get("followup", False)
                        st.session_state["_last_followup_reason"] = result.get("followup_reason", "")
                        clear_accumulated_expressions()
                        st.session_state.avatar_state = "idle"
                        st.rerun()
        else:
            st.caption(t('interview.audio_tip'))
            wav_audio_data = st_audiorec()
            if wav_audio_data is not None:
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
                        audio_pending_text = "（语音回答已提交）"
                        st.session_state["_pending_candidate_message"] = {
                            "session_id": session_id,
                            "content": audio_pending_text,
                        }
                        live_candidate_placeholder.markdown(_candidate_html(audio_pending_text), unsafe_allow_html=True)
                        submit_token = f"r{session.current_round}:audio:{h[:10]}"
                        anchor_candidate_idx = candidate_count + 1
                        _show_thinking_stage(
                            session_id,
                            live_thinking_placeholder,
                            submit_token,
                            anchor_candidate_idx,
                            "received",
                            "语音已收到，我正在识别内容并进行回答分析...",
                        )
                        _show_thinking_stage(
                            session_id,
                            live_thinking_placeholder,
                            submit_token,
                            anchor_candidate_idx,
                            "llm_eval",
                            "正在进行大模型动态评估：语义理解、关键点覆盖、逻辑结构和可落地性。",
                            delay=0.006,
                        )
                        result = submit_answer(
                            db, session_id, answer_text=None,
                            answer_type="audio", audio_data=audio_data,
                            expression_data=expr_data,
                        )
                        if "error" in result:
                            _show_thinking_stage(
                                session_id,
                                live_thinking_placeholder,
                                submit_token,
                                anchor_candidate_idx,
                                "error",
                                "语音分析中遇到一点问题，请再试一次。",
                                delay=0.006,
                            )
                            st.session_state["_pending_candidate_message"] = {}
                            st.error(result["error"])
                        else:
                            _show_thinking_stage(
                                session_id,
                                live_thinking_placeholder,
                                submit_token,
                                anchor_candidate_idx,
                                "next_loading",
                                "分析完成，正在组织下一题，请稍等...",
                                delay=0.006,
                            )
                            _show_thinking_stage(
                                session_id,
                                live_thinking_placeholder,
                                submit_token,
                                anchor_candidate_idx,
                                "thinking_summary",
                                _build_thinking_summary(result),
                                delay=0.005,
                            )
                            _show_eval_stage(
                                session_id,
                                live_thinking_placeholder,
                                submit_token,
                                anchor_candidate_idx,
                                "evaluation_summary",
                                _build_eval_summary(result),
                                delay=0.004,
                            )
                            time.sleep(0.3)
                            ev = result.get("evaluation", {})
                            if ev:
                                st.session_state["_last_eval"] = ev
                            st.session_state["_pending_candidate_message"] = {}
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
