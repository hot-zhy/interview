"""Interview page."""
import base64
import hashlib
import html
import json
import sys
from pathlib import Path
from typing import Optional

import streamlit as st
import streamlit.components.v1 as st_components
from st_audiorec import st_audiorec

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

st.set_page_config(page_title="Interview", layout="wide")

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
from backend.db.models import AskedQuestion, Evaluation, InterviewSession, InterviewTurn, Resume
from backend.services.interview_engine import (
    create_session,
    get_session_turns,
    is_resume_qa_session,
    start_interview,
    submit_answer,
)
from backend.services.resume_track_matcher import check_resume_track_match

inject_global_styles()
load_auth_on_page_load()
init_session_state()


def _inject_interview_styles():
    st.markdown(
        """
        <style>
        section.main > div.block-container {
            max-width: 1280px;
            padding-top: 0.85rem !important;
            padding-bottom: 1rem !important;
        }

        .interview-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            margin-bottom: 10px;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.82);
            border: 1px solid rgba(116, 139, 171, 0.24);
            border-radius: 8px;
            box-shadow: 0 18px 50px rgba(33, 56, 96, 0.10);
            backdrop-filter: blur(16px);
        }
        .interview-title {
            font-size: 1.08rem;
            font-weight: 800;
            color: #172033;
            letter-spacing: 0;
        }
        .interview-meta {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
            gap: 8px;
            color: #64748b;
            font-size: 0.82rem;
        }
        .interview-meta span {
            background: rgba(8, 145, 178, 0.08);
            border: 1px solid rgba(8, 145, 178, 0.16);
            border-radius: 8px;
            padding: 5px 8px;
        }
        .interview-meta strong { color: #172033; }

        [data-testid="stProgress"] > div {
            background: rgba(148, 163, 184, 0.18);
            border-radius: 999px;
            height: 9px;
        }
        [data-testid="stProgress"] div div div {
            background: linear-gradient(90deg, #2563eb 0%, #0891b2 55%, #7c3aed 100%) !important;
        }

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
            border-radius: 8px;
            font-size: 0.94rem;
            line-height: 1.62;
            margin: 0 0 10px;
            max-width: 88%;
            padding: 12px 14px;
            white-space: normal;
            word-break: break-word;
        }
        .chat-bubble.interviewer {
            background: rgba(255, 255, 255, 0.90);
            border: 1px solid rgba(116, 139, 171, 0.24);
            color: #1e293b;
            margin-right: auto;
            box-shadow: 0 12px 34px rgba(33, 56, 96, 0.08);
        }
        .chat-bubble.candidate {
            background: linear-gradient(135deg, rgba(37, 99, 235, 0.92) 0%, rgba(8, 145, 178, 0.88) 100%);
            border: 1px solid rgba(255, 255, 255, 0.28);
            color: #ffffff;
            margin-left: auto;
            box-shadow: 0 14px 36px rgba(37, 99, 235, 0.18);
        }
        .chat-bubble.system {
            background: rgba(236, 254, 255, 0.88);
            border: 1px solid rgba(8, 145, 178, 0.24);
            color: #164e63;
            max-width: 92%;
            box-shadow: 0 12px 34px rgba(8, 145, 178, 0.10);
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
            border-radius: 8px;
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
        .typewriter-caret {
            display: inline-block;
            margin-left: 2px;
            color: #2563eb;
            animation: caretBlink 0.8s steps(1) infinite;
        }
        @keyframes pulseDot {
            0%, 100% { opacity: 0.55; transform: scale(0.92); }
            50% { opacity: 1; transform: scale(1); }
        }
        @keyframes caretBlink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
        }
        .thinking-detail {
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px dashed rgba(8, 145, 178, 0.20);
            display: grid;
            gap: 8px;
        }
        .thinking-row {
            display: grid;
            grid-template-columns: 72px 1fr;
            gap: 10px;
            align-items: center;
            font-size: 0.82rem;
            color: #1e293b;
        }
        .thinking-label {
            color: #64748b;
            font-weight: 700;
        }
        .thinking-row.conclusion {
            align-items: start;
            background: rgba(37, 99, 235, 0.06);
            border: 1px solid rgba(37, 99, 235, 0.14);
            border-radius: 8px;
            padding: 8px 10px;
        }
        .thinking-row.conclusion .thinking-label {
            color: #1d4ed8;
        }
        .thinking-conclusion {
            color: #1e293b;
            font-weight: 720;
            line-height: 1.5;
        }
        .thinking-score {
            font-weight: 800;
            color: #0f766e;
            font-size: 1rem;
        }
        .thinking-chips {
            display: inline-flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-left: 8px;
        }
        .thinking-chip {
            background: rgba(8, 145, 178, 0.10);
            color: #0f766e;
            border-radius: 999px;
            padding: 2px 8px;
            font-size: 0.72rem;
            font-weight: 650;
        }
        .thinking-tags {
            display: inline-flex;
            flex-wrap: wrap;
            gap: 4px;
        }
        .thinking-tag {
            background: rgba(244, 114, 182, 0.10);
            color: #be185d;
            border-radius: 6px;
            padding: 2px 8px;
            font-size: 0.74rem;
        }
        .thinking-feedback {
            color: #334155;
            line-height: 1.5;
        }
        .thinking-action {
            color: #1d4ed8;
            font-weight: 700;
        }
        .thinking-timeline ul {
            margin: 4px 0 0;
            padding-left: 0;
            list-style: none;
            display: grid;
            gap: 3px;
        }
        .thinking-timeline li {
            display: flex;
            justify-content: space-between;
            font-size: 0.74rem;
            color: #475569;
            border-left: 2px solid rgba(37, 99, 235, 0.40);
            padding-left: 8px;
        }
        .timeline-elapsed {
            color: #94a3b8;
            font-variant-numeric: tabular-nums;
        }
        .followup-chip {
            display: inline-flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.86);
            border: 1px solid rgba(37, 99, 235, 0.24);
            border-radius: 8px;
            color: #1d4ed8;
            font-size: 0.78rem;
            font-weight: 650;
            margin: 0 0 8px;
            padding: 4px 10px;
        }
        .side-note {
            color: #526176;
            font-size: 0.82rem;
            line-height: 1.5;
            margin-top: 0.5rem;
            border: 1px solid rgba(116, 139, 171, 0.20);
            border-radius: 8px;
            padding: 10px 12px;
            background: rgba(255, 255, 255, 0.72);
        }
        .stTextArea textarea {
            min-height: 108px !important;
        }
        [data-testid="column"] > div {
            gap: 0.7rem;
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
    render_html: bool = False,
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
            "html": render_html,
        }
    )


def _render_note(note: dict):
    if note.get("html"):
        st.markdown(note.get("content", ""), unsafe_allow_html=True)
    else:
        _bubble(note.get("title", "系统"), note.get("content", ""), "system")


def _analysis_turn_html(content: str) -> str:
    try:
        payload = json.loads(content or "{}")
    except Exception:
        return _system_html("面试官 · AI 分析与评价", content or "")

    evaluation = payload.get("evaluation") or {}
    action = payload.get("action") or "ask_next"
    reason = payload.get("reason") or ""
    flow_html = _analysis_steps_bubble_html(
        title="面试官 · AI 分析中（已完成）",
        subtitle="本轮分析流程已完成，并已保留在对话记录中。",
        active_step=4,
        completed=True,
        extra_detail_html=_format_thinking_detail(
            {
                "stage": "ready",
                "evaluation_payload": evaluation,
                "action": action,
                "action_reason": reason,
                "timeline": [],
            }
        ),
    )
    return flow_html


def _render_chat_timeline(turns, session_id: int, optimistic_candidate: str = "", saved_notes=None):
    notes_by_anchor = {}
    unanchored_notes = []
    saved_notes = saved_notes or []
    has_analysis_turns = any(turn.get("role") == "analysis" for turn in turns)
    saved_anchors = {
        note.get("anchor_candidate_idx")
        for note in saved_notes
        if isinstance(note.get("anchor_candidate_idx"), int)
    }
    for note in saved_notes:
        anchor = note.get("anchor_candidate_idx")
        if isinstance(anchor, int) and anchor > 0:
            notes_by_anchor.setdefault(anchor, []).append(note)
        else:
            unanchored_notes.append(note)

    for note in ([] if has_analysis_turns else _get_chat_notes(session_id)):
        anchor = note.get("anchor_candidate_idx")
        if (
            anchor in saved_anchors
            and str(note.get("title", "")).startswith("面试官 · AI 分析")
        ):
            continue
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
                _render_note(note)
        elif turn["role"] == "analysis":
            st.markdown(_analysis_turn_html(turn["content"]), unsafe_allow_html=True)
        else:
            _bubble(t("interview.interviewer"), turn["content"], "interviewer")

    if optimistic_candidate:
        st.markdown(_candidate_html(optimistic_candidate), unsafe_allow_html=True)
        candidate_idx += 1
        for note in notes_by_anchor.get(candidate_idx, []):
            _render_note(note)

    for note in unanchored_notes:
        _render_note(note)


def _analysis_progress_html(candidate_text: str, active_step: int = 1) -> str:
    return _candidate_html(candidate_text) + _analysis_steps_bubble_html(
        title="面试官 · AI 分析中",
        subtitle="我正在分析你的回答，请稍等。",
        active_step=active_step,
    )


def _analysis_steps_bubble_html(
    title: str = "面试官 · AI 分析中",
    subtitle: str = "我正在分析你的回答，请稍等。",
    active_step: int = 1,
    completed: bool = False,
    extra_detail_html: str = "",
) -> str:
    steps = [
        "收到回答并写入本轮记录",
        "评估语义匹配、关键点覆盖和表达清晰度",
        "判断是否需要追问或切换题目",
        "整理面试官评价并生成下一轮问题",
    ]
    rows = []
    for idx, label in enumerate(steps, start=1):
        if completed or idx < active_step:
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
    caret_html = " " if completed else '<span class="typewriter-caret">|</span>'
    processing = (
        f'<div class="chat-role">{html.escape(title)}</div>'
        '<div class="chat-bubble system">'
        f'<div class="analysis-title">{html.escape(subtitle)}'
        f'{caret_html}</div>'
        f'<div class="analysis-steps">{"".join(rows)}</div>'
        f'{extra_detail_html}'
        '</div>'
    )
    return processing


def _build_persistent_analysis_flow(result: dict) -> str:
    action = "继续追问" if result.get("followup") else "进入下一题"
    steps = [
        "已收到回答并写入本轮面试记录。",
        "已完成语义匹配、关键点覆盖和表达清晰度评估。",
        "已根据评分、缺失点和上下文判断是否需要追问。",
        f"已整理面试官评价，并决定下一步：{action}。",
    ]
    return "AI 分析流程：\n" + "\n".join(f"✓ {step}" for step in steps)


# ---------------------------------------------------------------
# 简历专项问答：实时 agent 思考过程渲染
# ---------------------------------------------------------------

_STAGE_TO_STEP = {
    "received": 1,
    "evaluating": 2,
    "evaluated": 2,
    "planning": 3,
    "action_picked": 3,
    "generating_followup": 4,
    "generating_next": 4,
    "ready": 4,
}

_STAGE_TITLE = {
    "received": "已接收回答，开始分析",
    "evaluating": "正在调用 LLM 对回答多维评分",
    "evaluated": "评分完成",
    "planning": "正在判断追问还是切下一题",
    "action_picked": "决策完成",
    "generating_followup": "正在结合简历证据生成针对性追问",
    "generating_next": "正在沿着简历下一条证据生成新问题",
    "ready": "已就绪",
}

_ACTION_LABEL = {
    "follow_up": "决定追问",
    "ask_next": "切换下一题",
    "ask_resume_next": "进入下一组简历证据",
    "terminate": "结束本组简历专项问答",
}


def _format_thinking_detail(state: dict) -> str:
    """Render the rich detail block under the step list."""
    rows = []
    eval_payload = state.get("evaluation_payload") or {}
    action = state.get("action")
    reason = state.get("action_reason")
    if eval_payload:
        overall = float(eval_payload.get("overall_score") or 0.0)
        scores = eval_payload.get("scores") or {}
        missing = eval_payload.get("missing_points") or []
        feedback = (eval_payload.get("feedback") or "").strip()
        if action:
            conclusion = f"本轮综合评分 {overall:.0%}，下一步：{_ACTION_LABEL.get(action, action)}。"
            if reason:
                conclusion += f"依据：{str(reason)[:120]}"
            rows.append(
                '<div class="thinking-row conclusion">'
                '<span class="thinking-label">结论</span>'
                f'<span class="thinking-conclusion">{html.escape(conclusion)}</span>'
                '</div>'
            )
        dim_html = ""
        if scores:
            chips = []
            for key, label in [
                ("correctness", "正确"),
                ("depth", "深度"),
                ("clarity", "清晰"),
                ("practicality", "实用"),
                ("tradeoffs", "权衡"),
            ]:
                if key in scores:
                    chips.append(
                        f'<span class="thinking-chip">{label} {float(scores.get(key, 0)):.0%}</span>'
                    )
            if chips:
                dim_html = '<div class="thinking-chips">' + "".join(chips) + "</div>"
        rows.append(
            '<div class="thinking-row">'
            f'<span class="thinking-label">综合评分</span>'
            f'<span class="thinking-score">{overall:.0%}</span>'
            f'{dim_html}'
            '</div>'
        )
        if missing:
            tags = "".join(
                f'<span class="thinking-tag">{html.escape(str(point))}</span>'
                for point in missing[:4]
            )
            rows.append(
                '<div class="thinking-row">'
                '<span class="thinking-label">缺失要点</span>'
                f'<span class="thinking-tags">{tags}</span>'
                '</div>'
            )
        if feedback:
            rows.append(
                '<div class="thinking-row">'
                '<span class="thinking-label">面试官反馈</span>'
                f'<span class="thinking-feedback">{html.escape(feedback[:180])}</span>'
                '</div>'
            )

    if action:
        rows.append(
            '<div class="thinking-row">'
            '<span class="thinking-label">下一步</span>'
            f'<span class="thinking-action">{_ACTION_LABEL.get(action, action)}</span>'
            '</div>'
        )
    if reason:
        rows.append(
            '<div class="thinking-row">'
            '<span class="thinking-label">决策依据</span>'
            f'<span class="thinking-feedback">{html.escape(str(reason)[:160])}</span>'
            '</div>'
        )

    timeline = state.get("timeline") or []
    if timeline:
        items = "".join(
            f'<li><span class="timeline-stage">{html.escape(item.get("title", ""))}</span>'
            f'<span class="timeline-elapsed">{item.get("elapsed", "")}</span></li>'
            for item in timeline
        )
        rows.append(
            f'<div class="thinking-timeline"><div class="thinking-label">流程日志</div><ul>{items}</ul></div>'
        )

    if not rows:
        return ""
    return '<div class="thinking-detail">' + "".join(rows) + "</div>"


def _render_thinking_state(
    placeholder,
    candidate_text: str,
    state: dict,
    completed: bool = False,
    animate: bool = True,
) -> None:
    import time as _time_mod

    stage = state.get("stage") or "received"
    active_step = _STAGE_TO_STEP.get(stage, 1)
    title = "面试官 · AI 分析中" + (("（已完成）") if completed else "")
    subtitle = _STAGE_TITLE.get(stage, "正在分析你的回答…")
    detail_html = _format_thinking_detail(state)

    def _paint(text: str) -> None:
        placeholder.markdown(
            _candidate_html(candidate_text)
            + _analysis_steps_bubble_html(
                title=title,
                subtitle=text,
                active_step=active_step,
                completed=completed,
                extra_detail_html=detail_html,
            ),
            unsafe_allow_html=True,
        )

    last_subtitle = state.get("_rendered_subtitle", "")
    should_type = animate and not completed and subtitle != last_subtitle
    if should_type:
        start_at = len(last_subtitle) if subtitle.startswith(last_subtitle) else 0
        for idx in range(start_at + 1, len(subtitle) + 1):
            _paint(subtitle[:idx])
            _time_mod.sleep(0.012)
    else:
        _paint(subtitle)
    state["_rendered_subtitle"] = subtitle
    _scroll_chat_to_bottom()


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


def _build_saved_analysis_notes(db, session_id: int):
    has_persisted_analysis = (
        db.query(InterviewTurn)
        .filter(
            InterviewTurn.session_id == session_id,
            InterviewTurn.role == "analysis",
        )
        .count()
        > 0
    )
    if has_persisted_analysis:
        return []

    candidate_turns = (
        db.query(InterviewTurn)
        .filter(
            InterviewTurn.session_id == session_id,
            InterviewTurn.role == "candidate",
        )
        .order_by(InterviewTurn.created_at)
        .all()
    )
    evaluations = (
        db.query(Evaluation)
        .join(AskedQuestion)
        .filter(AskedQuestion.session_id == session_id)
        .order_by(Evaluation.created_at)
        .all()
    )
    notes = []
    used_candidate_indexes = set()

    def _anchor_for_evaluation(evaluation: Evaluation, fallback_idx: int) -> int:
        answer = (evaluation.answer_text or "").strip()
        for idx, turn in enumerate(candidate_turns, start=1):
            if idx in used_candidate_indexes:
                continue
            content = (turn.content or "").strip()
            if answer and (content == answer or _normalize_candidate_display_content(answer) == content):
                used_candidate_indexes.add(idx)
                return idx
        for idx, _turn in enumerate(candidate_turns, start=1):
            if idx not in used_candidate_indexes:
                used_candidate_indexes.add(idx)
                return idx
        return fallback_idx

    for fallback_idx, evaluation in enumerate(evaluations, start=1):
        candidate_idx = _anchor_for_evaluation(evaluation, fallback_idx)
        result = {
            "evaluation": {
                "scores": evaluation.scores_json or {},
                "overall_score": evaluation.overall_score,
                "feedback": evaluation.feedback_text,
                "missing_points": evaluation.missing_points_json or [],
                "next_direction": evaluation.next_direction,
            },
            "followup": False,
            "followup_reason": evaluation.next_direction or "",
        }
        flow_html = _analysis_steps_bubble_html(
            title="面试官 · AI 分析中（已完成）",
            subtitle="本轮分析流程已完成，以下步骤会保留在对话中。",
            active_step=4,
            completed=True,
            extra_detail_html=_format_thinking_detail(
                {
                    "stage": "ready",
                    "evaluation_payload": result["evaluation"],
                    "action": "follow_up" if result.get("followup") else "ask_next",
                    "action_reason": result.get("followup_reason", ""),
                    "timeline": [],
                }
            ),
        )
        summary = _build_analysis_summary(result)
        notes.append(
            {
                "token": f"db:{evaluation.id}:flow",
                "title": "面试官 · AI 分析中（已完成）",
                "content": flow_html,
                "anchor_candidate_idx": candidate_idx,
                "html": True,
            }
        )
        if summary:
            notes.append(
                {
                    "token": f"db:{evaluation.id}:summary",
                    "title": "面试官 · AI 分析与评价",
                    "content": summary,
                    "anchor_candidate_idx": candidate_idx,
                    "html": False,
                }
            )
    return notes


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
    is_resume_qa: bool = False,
):
    import time as _time_mod

    thinking_state = {
        "stage": "received",
        "evaluation_payload": None,
        "action": None,
        "action_reason": None,
        "timeline": [],
    }
    start_ts = _time_mod.time()

    def _stage_label(stage: str) -> str:
        return _STAGE_TITLE.get(stage, stage)

    def _on_event(stage: str, payload: dict) -> None:
        elapsed = f"{_time_mod.time() - start_ts:.1f}s"
        thinking_state["stage"] = stage
        thinking_state["_rendered_subtitle"] = ""
        thinking_state.setdefault("timeline", []).append({
            "title": _stage_label(stage),
            "elapsed": elapsed,
        })
        if stage == "evaluated":
            thinking_state["evaluation_payload"] = payload
        elif stage == "action_picked":
            thinking_state["action"] = payload.get("action")
            thinking_state["action_reason"] = payload.get("reason")
        _render_thinking_state(live_placeholder, display_answer, thinking_state)

    _render_thinking_state(live_placeholder, display_answer, thinking_state)
    expr_data = _collect_expression_payload()
    result = submit_answer(
        db,
        session_id,
        answer_text=answer,
        answer_type=answer_type,
        audio_data=audio_data,
        expression_data=expr_data,
        on_event=_on_event,
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

    _render_thinking_state(
        live_placeholder, display_answer, thinking_state, completed=True, animate=False
    )
    _scroll_chat_to_bottom()

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
        resume_qa_mode = st.checkbox(
            "简历专项问答（追问结束即停止）",
            key="resume_qa_mode",
            help="只围绕所选简历进行一组针对性问答；不再切换到题库下一题。",
        )
        if resume_qa_mode:
            use_resume = True
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
            resume_qa_mode = False

        if st.button(t("interview.start_interview"), use_container_width=True, type="primary"):
            if resume_qa_mode and not resume_id:
                st.error("请先选择一份简历，再开始简历专项问答。")
                return
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
                    session_track = f"{track} · 简历专项" if resume_qa_mode else track
                    session = create_session(
                        db=db,
                        user_id=user_id,
                        track=session_track,
                        level=level,
                        resume_id=resume_id if use_resume else None,
                        total_rounds=3 if resume_qa_mode else total_rounds,
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

    resume_qa_session = is_resume_qa_session(session)

    progress_ratio = session.current_round / session.total_rounds if session.total_rounds else 0
    remain = max(session.total_rounds - session.current_round, 0)
    display_track = session.track
    st.markdown(
        f"""
        <div class="interview-topbar">
            <div class="interview-title">{html.escape(display_track)}</div>
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
            saved_analysis_notes = _build_saved_analysis_notes(db, session_id)
            _render_chat_timeline(
                turns,
                session_id,
                optimistic_candidate=optimistic_candidate,
                saved_notes=saved_analysis_notes,
            )
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
                        is_resume_qa=resume_qa_session,
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
                            is_resume_qa=resume_qa_session,
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
        st.text(f"{t('interview.direction')}: {display_track}")
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
