"""Interview page."""
import base64
import hashlib
import html
import sys
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as st_components
from st_audiorec import st_audiorec

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.components.secrets_bridge import bridge_secrets

bridge_secrets()

from app.components.auth_loader import load_auth_on_page_load
from app.components.auth_utils import check_auth, init_session_state
from app.components.avatar import render_avatar
from app.components.expression_video import (
    clear_accumulated_expressions,
    get_accumulated_expressions,
    render_expression_video,
)
from app.components.sidebar import render_sidebar
from app.components.styles import inject_global_styles
from app.i18n import t
from backend.core.config import settings
from backend.db.base import get_db
from backend.db.models import AskedQuestion, InterviewSession, Resume
from backend.services.interview_engine import (
    create_session,
    get_session_turns,
    start_interview,
    submit_answer,
)
from backend.services.resume_track_matcher import check_resume_track_match


st.set_page_config(page_title="Interview", layout="wide")
inject_global_styles()
load_auth_on_page_load()
init_session_state()


def _inject_interview_styles():
    st.markdown(
        """
        <style>
        section.main > div.block-container {
            max-width: 1280px;
            padding-top: 0.75rem !important;
            padding-bottom: 1rem !important;
        }

        .interview-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 6px;
        }
        .interview-title {
            font-size: 1.05rem;
            font-weight: 750;
            color: #172033;
        }
        .interview-meta {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 10px;
            color: #64748b;
            font-size: 0.82rem;
        }
        .interview-meta strong { color: #172033; }

        .chat-panel {
            min-height: 420px;
        }
        .chat-role {
            color: #64748b;
            font-size: 0.72rem;
            font-weight: 700;
            margin: 6px 0 2px;
        }
        .chat-role.right { text-align: right; }
        .chat-bubble {
            border-radius: 14px;
            font-size: 0.94rem;
            line-height: 1.62;
            margin: 0 0 10px;
            max-width: 88%;
            padding: 11px 14px;
            white-space: normal;
            word-break: break-word;
        }
        .chat-bubble.interviewer {
            background: #f8fafc;
            border: 1px solid #dbe3ef;
            border-bottom-left-radius: 5px;
            color: #1e293b;
            margin-right: auto;
        }
        .chat-bubble.candidate {
            background: #eef2ff;
            border: 1px solid #c7d2fe;
            border-bottom-right-radius: 5px;
            color: #1e1b4b;
            margin-left: auto;
        }
        .chat-bubble.system {
            background: #ecfeff;
            border: 1px solid #a5f3fc;
            color: #155e75;
            max-width: 92%;
        }
        .analysis-steps {
            display: grid;
            gap: 7px;
            margin-top: 2px;
        }
        .analysis-step {
            align-items: center;
            display: flex;
            gap: 8px;
        }
        .analysis-dot {
            align-items: center;
            background: #cbd5e1;
            border-radius: 999px;
            color: #fff;
            display: inline-flex;
            flex: 0 0 18px;
            font-size: 0.72rem;
            height: 18px;
            justify-content: center;
            width: 18px;
        }
        .analysis-step.done .analysis-dot {
            background: #0f766e;
        }
        .analysis-step.active .analysis-dot {
            animation: pulseDot 1s ease-in-out infinite;
            background: #4f46e5;
        }
        .analysis-step.pending {
            color: #64748b;
        }
        .analysis-title {
            font-weight: 750;
            margin-bottom: 7px;
        }
        @keyframes pulseDot {
            0%, 100% { opacity: 0.55; transform: scale(0.92); }
            50% { opacity: 1; transform: scale(1); }
        }
        .followup-chip {
            display: inline-flex;
            align-items: center;
            background: #eef2ff;
            border: 1px solid #c7d2fe;
            border-radius: 999px;
            color: #3730a3;
            font-size: 0.78rem;
            font-weight: 650;
            margin: 0 0 8px;
            padding: 4px 10px;
        }
        .side-note {
            color: #64748b;
            font-size: 0.82rem;
            line-height: 1.5;
            margin-top: 0.5rem;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #e2e8f0;
            border-radius: 10px;
        }
        .stTextArea textarea {
            min-height: 108px !important;
        }
        @media (max-width: 900px) {
            .interview-topbar {
                align-items: flex-start;
                flex-direction: column;
            }
            .interview-meta { justify-content: flex-start; }
            .chat-bubble { max-width: 96%; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe_lines(content: str) -> str:
    return html.escape(content or "").replace("\n", "<br>")


def _bubble(role_label: str, content: str, css_class: str, align_right: bool = False):
    role_class = "chat-role right" if align_right else "chat-role"
    st.markdown(
        f'<div class="{role_class}">{html.escape(role_label)}</div>'
        f'<div class="chat-bubble {css_class}">{_safe_lines(content)}</div>',
        unsafe_allow_html=True,
    )


def _candidate_html(content: str) -> str:
    return (
        '<div class="chat-role right">你</div>'
        f'<div class="chat-bubble candidate">{_safe_lines(content)}</div>'
    )


def _system_html(title: str, content: str) -> str:
    return (
        f'<div class="chat-role">{html.escape(title)}</div>'
        f'<div class="chat-bubble system">{_safe_lines(content)}</div>'
    )


def _get_chat_notes(session_id: int):
    notes = st.session_state.setdefault("_interview_chat_notes", {})
    return notes.setdefault(str(session_id), [])


def _remember_chat_note(
    session_id: int,
    token: str,
    title: str,
    content: str,
    anchor_candidate_idx: int,
):
    notes = _get_chat_notes(session_id)
    if any(note.get("token") == token for note in notes):
        return
    notes.append(
        {
            "token": token,
            "title": title,
            "content": content,
            "anchor_candidate_idx": anchor_candidate_idx,
        }
    )


def _render_chat_timeline(turns, session_id: int, optimistic_candidate: str = ""):
    notes_by_anchor = {}
    unanchored_notes = []
    for note in _get_chat_notes(session_id):
        anchor = note.get("anchor_candidate_idx")
        if isinstance(anchor, int) and anchor > 0:
            notes_by_anchor.setdefault(anchor, []).append(note)
        else:
            unanchored_notes.append(note)

    candidate_idx = 0
    for turn in turns:
        if turn["role"] == "candidate":
            _bubble("你", turn["content"], "candidate", align_right=True)
            candidate_idx += 1
            for note in notes_by_anchor.get(candidate_idx, []):
                _bubble(note.get("title", "系统"), note.get("content", ""), "system")
        else:
            _bubble(t("interview.interviewer"), turn["content"], "interviewer")

    if optimistic_candidate:
        st.markdown(_candidate_html(optimistic_candidate), unsafe_allow_html=True)
        candidate_idx += 1
        for note in notes_by_anchor.get(candidate_idx, []):
            _bubble(note.get("title", "系统"), note.get("content", ""), "system")

    for note in unanchored_notes:
        _bubble(note.get("title", "系统"), note.get("content", ""), "system")


def _analysis_progress_html(candidate_text: str, active_step: int = 1) -> str:
    steps = [
        "收到回答并写入本轮记录",
        "评估语义匹配、关键点覆盖和表达清晰度",
        "判断是否需要追问或切换题目",
        "整理面试官评价并生成下一轮问题",
    ]
    rows = []
    for idx, label in enumerate(steps, start=1):
        if idx < active_step:
            state = "done"
            marker = "✓"
        elif idx == active_step:
            state = "active"
            marker = "…"
        else:
            state = "pending"
            marker = str(idx)
        rows.append(
            f'<div class="analysis-step {state}">'
            f'<span class="analysis-dot">{marker}</span>'
            f'<span>{html.escape(label)}</span>'
            f'</div>'
        )
    processing = (
        '<div class="chat-role">面试官 · AI 分析中</div>'
        '<div class="chat-bubble system">'
        '<div class="analysis-title">我正在分析你的回答，请稍等。</div>'
        f'<div class="analysis-steps">{"".join(rows)}</div>'
        '</div>'
    )
    return _candidate_html(candidate_text) + processing


def _scroll_chat_to_bottom():
    st_components.html(
        """
        <script>
        requestAnimationFrame(function () {
            var frame = window.frameElement;
            if (!frame) return;
            var node = frame.parentElement;
            while (node && node.scrollHeight <= node.clientHeight) {
                node = node.parentElement;
            }
            if (node) node.scrollTop = node.scrollHeight;
        });
        </script>
        """,
        height=0,
    )


def _build_eval_summary(result: dict) -> str:
    ev = result.get("evaluation", {}) or {}
    if not ev:
        return ""

    scores = ev.get("scores", {}) or {}
    missing = ev.get("missing_points", []) or []
    feedback = (ev.get("feedback", "") or "").strip()
    overall = float(ev.get("overall_score", 0.0) or 0.0)

    lines = [
        f"综合评分：{overall:.0%}",
        (
            "维度："
            f"正确 {float(scores.get('correctness', 0.0)):.0%} / "
            f"深度 {float(scores.get('depth', 0.0)):.0%} / "
            f"清晰 {float(scores.get('clarity', 0.0)):.0%} / "
            f"实用 {float(scores.get('practicality', 0.0)):.0%} / "
            f"权衡 {float(scores.get('tradeoffs', 0.0)):.0%}"
        ),
    ]
    if feedback:
        lines.append(f"反馈：{feedback[:160]}")
    if missing:
        lines.append("待补强：" + "；".join(str(point) for point in missing[:3]))
    return "\n".join(lines)


def _build_analysis_summary(result: dict) -> str:
    if "evaluation" not in result:
        return ""
    action = "继续追问" if result.get("followup") else "进入下一题"
    reason = (result.get("followup_reason") or "").strip()
    eval_summary = _build_eval_summary(result)

    lines = [
        "流程：已完成回答记录、语义评估、关键点检查和下一步决策。",
    ]
    if eval_summary:
        lines.append(eval_summary)
    if reason:
        lines.append(f"下一步：{action}。原因：{reason}")
    else:
        lines.append(f"下一步：{action}。")
    return "\n\n".join(lines)


def _collect_expression_payload():
    accumulated = get_accumulated_expressions()
    return {"analyses": accumulated} if accumulated else None


def _submit_and_update(
    db,
    session_id: int,
    answer: Optional[str],
    answer_type: str,
    token: str,
    anchor_candidate_idx: int,
    live_placeholder,
    display_answer: str,
    audio_data: Optional[dict] = None,
):
    live_placeholder.markdown(
        _analysis_progress_html(display_answer, active_step=2),
        unsafe_allow_html=True,
    )
    expr_data = _collect_expression_payload()
    result = submit_answer(
        db,
        session_id,
        answer_text=answer,
        answer_type=answer_type,
        audio_data=audio_data,
        expression_data=expr_data,
    )

    if "error" in result:
        live_placeholder.markdown(
            _candidate_html(display_answer)
            + _system_html(
                "面试官 · 分析失败",
                "分析过程中遇到异常，请再提交一次，我会继续当前问题。",
            ),
            unsafe_allow_html=True,
        )
        st.session_state["_pending_candidate_message"] = {}
        st.error(result["error"])
        return

    analysis_summary = _build_analysis_summary(result)
    if analysis_summary:
        _remember_chat_note(
            session_id,
            f"{token}:analysis",
            "面试官 · AI 分析与评价",
            analysis_summary,
            anchor_candidate_idx,
        )

    live_placeholder.markdown(
        _candidate_html(display_answer)
        + _system_html("面试官 · AI 分析与评价", analysis_summary),
        unsafe_allow_html=True,
    )

    ev = result.get("evaluation", {})
    if ev:
        st.session_state["_last_eval"] = ev
    st.session_state["_pending_candidate_message"] = {}
    st.session_state["_last_was_followup"] = bool(result.get("followup"))
    st.session_state["_last_followup_reason"] = result.get("followup_reason", "")
    clear_accumulated_expressions()
    st.session_state.avatar_state = "idle"
    st.rerun()


def main():
    render_sidebar()
    check_auth()
    _inject_interview_styles()

    user_id = st.session_state.user_id
    db = next(get_db())

    st.session_state.setdefault("current_session_id", None)
    st.session_state.setdefault("avatar_state", "idle")

    if not st.session_state.current_session_id:
        st.title(t("interview.title"))
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
                t("interview.rounds"),
                min_value=5,
                max_value=20,
                value=10,
                key="new_rounds",
            )

        resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
        use_resume = st.checkbox(t("interview.use_resume"), key="use_resume")
        resume_id = None
        if use_resume and resumes:
            resume_options = {
                f"{r.filename} ({r.created_at.strftime('%Y-%m-%d')})": r.id
                for r in resumes
            }
            selected_resume = st.selectbox(
                t("interview.select_resume"),
                options=list(resume_options.keys()),
            )
            resume_id = resume_options[selected_resume]
        elif use_resume and not resumes:
            st.warning(t("interview.upload_resume_first"))
            use_resume = False

        if st.button(t("interview.start_interview"), use_container_width=True, type="primary"):
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
                        db=db,
                        user_id=user_id,
                        track=track,
                        level=level,
                        resume_id=resume_id if use_resume else None,
                        total_rounds=total_rounds,
                    )
                    st.session_state.current_session_id = session.id
                    result = start_interview(db, session.id)
                    if result and "error" in result:
                        st.error(result["error"])
                    else:
                        st.rerun()
            except Exception as exc:
                st.error(f"Error: {exc}")
        return

    session_id = st.session_state.current_session_id
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session:
        st.error(t("interview.session_not_found"))
        st.session_state.current_session_id = None
        st.rerun()

    if session.current_round == 0 and session.status == "active":
        with st.spinner(t("interview.preparing")):
            result = start_interview(db, session_id)
            if result and "error" in result:
                st.error(result["error"])
                return
            st.rerun()

    progress_ratio = session.current_round / session.total_rounds if session.total_rounds else 0
    remain = max(session.total_rounds - session.current_round, 0)
    st.markdown(
        f"""
        <div class="interview-topbar">
            <div class="interview-title">{html.escape(session.track)}</div>
            <div class="interview-meta">
                <span>{t("interview.round")} <strong>{session.current_round}/{session.total_rounds}</strong></span>
                <span>{t("interview.difficulty")} <strong>{session.level}</strong></span>
                <span>剩余 <strong>{remain}</strong> 轮</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(min(max(progress_ratio, 0.0), 1.0))

    turns = get_session_turns(db, session_id)
    candidate_turns = [turn for turn in turns if turn.get("role") == "candidate"]
    candidate_count = len(candidate_turns)
    pending_candidate_state = st.session_state.get("_pending_candidate_message", {})
    optimistic_candidate = ""
    if pending_candidate_state.get("session_id") == session_id:
        pending_content = (pending_candidate_state.get("content") or "").strip()
        if pending_content:
            db_has_pending = any(
                (turn.get("content") or "").strip() == pending_content
                for turn in candidate_turns
            )
            if db_has_pending:
                st.session_state["_pending_candidate_message"] = {}
            else:
                optimistic_candidate = pending_content

    last_interviewer = next(
        (turn for turn in reversed(turns) if turn["role"] == "interviewer"),
        None,
    )
    text_to_speak = ""
    if last_interviewer:
        last_spoken = st.session_state.get("_avatar_last_spoken_id")
        if last_spoken != last_interviewer.get("id"):
            text_to_speak = last_interviewer["content"]
            st.session_state["_avatar_last_spoken_id"] = last_interviewer.get("id")

    col_side, col_main = st.columns([1, 3], gap="large")

    with col_side:
        render_avatar(st.session_state.avatar_state, text_to_speak=text_to_speak)
        render_expression_video(session_id)
        st.markdown(
            '<div class="side-note">回答时可以先组织思路；提交后系统会自动记录本轮反馈并进入追问或下一题。</div>',
            unsafe_allow_html=True,
        )

    with col_main:
        chat_container = st.container(height=460, border=True)
        with chat_container:
            _render_chat_timeline(turns, session_id, optimistic_candidate=optimistic_candidate)
            live_processing_placeholder = st.empty()
            _scroll_chat_to_bottom()

        if st.session_state.get("_last_was_followup"):
            st.markdown(
                '<div class="followup-chip">AI 追问：针对上一轮回答继续深入</div>',
                unsafe_allow_html=True,
            )
            st.session_state["_last_was_followup"] = False

        if session.status != "active":
            st.info(t("interview.interview_ended"))
            return

        answer_mode = st.radio(
            "",
            [t("interview.text_answer"), t("interview.voice_answer")],
            horizontal=True,
            key="answer_mode",
            label_visibility="collapsed",
        )

        if answer_mode == t("interview.text_answer"):
            with st.form(key=f"answer_form_{session_id}_{session.current_round}", clear_on_submit=True):
                answer_text = st.text_area(
                    "",
                    height=110,
                    key=f"answer_input_{session_id}_{session.current_round}",
                    placeholder=t("interview.answer_placeholder"),
                    label_visibility="collapsed",
                )
                submitted = st.form_submit_button(
                    t("interview.submit"),
                    use_container_width=True,
                    type="primary",
                )

            if submitted:
                answer_clean = (answer_text or "").strip()
                if not answer_clean:
                    st.warning(t("interview.please_input"))
                else:
                    st.session_state.avatar_state = "thinking"
                    st.session_state["_pending_candidate_message"] = {
                        "session_id": session_id,
                        "content": answer_clean,
                    }
                    token = (
                        f"r{session.current_round}:text:"
                        f"{hashlib.sha256(answer_clean.encode('utf-8')).hexdigest()[:10]}"
                    )
                    live_processing_placeholder.markdown(
                        _analysis_progress_html(answer_clean, active_step=1),
                        unsafe_allow_html=True,
                    )
                    _submit_and_update(
                        db,
                        session_id,
                        answer_clean,
                        "text",
                        token,
                        candidate_count + 1,
                        live_processing_placeholder,
                        answer_clean,
                    )
        else:
            st.caption(t("interview.audio_tip"))
            wav_audio_data = st_audiorec()
            if wav_audio_data is not None:
                min_audio_bytes = 8000
                if len(wav_audio_data) < min_audio_bytes:
                    st.warning(t("interview.audio_too_short"))
                else:
                    audio_hash = hashlib.sha256(wav_audio_data).hexdigest()
                    already_submitted = (
                        st.session_state.get("_audio_submitted_round") == session.current_round
                        and st.session_state.get("_audio_last_hash") == audio_hash
                    )
                    if not already_submitted and st.session_state.get("_audio_last_hash") != audio_hash:
                        st.session_state["_audio_last_hash"] = audio_hash
                        pending_text = "（语音回答已提交）"
                        st.session_state["_pending_candidate_message"] = {
                            "session_id": session_id,
                            "content": pending_text,
                        }
                        audio_data = {
                            "audioData": base64.b64encode(wav_audio_data).decode("utf-8"),
                            "audioFormat": "wav",
                            "duration": 0,
                        }
                        token = f"r{session.current_round}:audio:{audio_hash[:10]}"
                        st.session_state["_audio_submitted_round"] = session.current_round
                        live_processing_placeholder.markdown(
                            _analysis_progress_html(pending_text, active_step=1),
                            unsafe_allow_html=True,
                        )
                        _submit_and_update(
                            db,
                            session_id,
                            None,
                            "audio",
                            token,
                            candidate_count + 1,
                            live_processing_placeholder,
                            pending_text,
                            audio_data=audio_data,
                        )
            st.session_state.avatar_state = "listening"

    current_difficulty = session.level
    asked_qs = (
        db.query(AskedQuestion)
        .filter(AskedQuestion.session_id == session_id)
        .order_by(AskedQuestion.created_at.desc())
        .first()
    )
    if asked_qs:
        current_difficulty = asked_qs.difficulty

    with st.sidebar:
        st.markdown(f"### {t('interview.session_info')}")
        st.text(f"{t('interview.direction')}: {session.track}")
        st.text(f"{t('interview.difficulty')}: {current_difficulty}/5")
        st.text(f"{t('interview.status')}: {session.status}")
        st.text(f"{t('interview.rounds_count')}: {session.current_round}/{session.total_rounds}")
        st.markdown("---")
        if st.button(t("interview.end_interview"), use_container_width=True, type="secondary"):
            from backend.services.interview_engine import end_interview

            end_interview(db, session_id)
            st.session_state.current_session_id = None
            st.rerun()
        if st.button(t("interview.exit_session"), use_container_width=True):
            st.session_state.current_session_id = None
            st.rerun()


if __name__ == "__main__":
    main()
