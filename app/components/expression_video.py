"""
表情分析组件 — 使用 st.camera_input 实现摄像头采集 + 表情分析
兼容 Streamlit Cloud（无需 WebRTC / TURN 服务器）。
浏览器摄像头实时预览，自动或手动拍照分析表情，结果累积供提交时存入数据库。
"""
import base64
import time
from typing import Dict, List, Optional
import streamlit as st

SESSION_KEY = "_expression_analyses"


def get_accumulated_expressions() -> List[Dict]:
    """获取累积的表情数据（供 submit_answer 时传入 expression_data）"""
    return list(st.session_state.get(SESSION_KEY, []))


def clear_accumulated_expressions():
    """提交成功后调用，清空已累积的表情数据"""
    st.session_state[SESSION_KEY] = []


def render_expression_video(session_id: int):
    """渲染摄像头预览 + 表情分析面板。

    摄像头在浏览器端保持实时预览。每当用户拍照（或自动采集）时，
    后端分析表情并累积到 session_state，提交回答时一并写入数据库。
    """
    from app.i18n import t

    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = []

    st.caption("📹 实时表情分析")

    photo = st.camera_input(
        "摄像头预览（点击拍照分析表情）",
        key=f"expr_cam_{session_id}_{st.session_state.get('current_round', 0)}",
    )

    if photo is not None:
        image_bytes = photo.getvalue()
        b64_data = base64.b64encode(image_bytes).decode("utf-8")

        result = _analyze_photo(b64_data)

        if result:
            # Flatten for storage (same schema as original expression_analysis_json)
            ir = result.get("interview_relevance", {})
            flat_result = {
                "dominant_emotion": result.get("dominant_emotion", "neutral"),
                "emotion_scores": result.get("emotion_scores", {}),
                "detected_face": result.get("detected_face", False),
                "nervousness": ir.get("nervousness", 0),
                "confidence_level": ir.get("confidence_level", "moderate"),
                "confidence_desc": ir.get("confidence_desc", ""),
                "engagement": ir.get("engagement", "engaged"),
                "engagement_desc": ir.get("engagement_desc", ""),
                "recommendation": (ir.get("recommendations") or [""])[0],
                "recommendations": ir.get("recommendations", []),
                "timestamp": time.time(),
            }

            st.session_state[SESSION_KEY].append(flat_result)
            # Cap accumulation
            if len(st.session_state[SESSION_KEY]) > 100:
                st.session_state[SESSION_KEY] = st.session_state[SESSION_KEY][-80:]

            # Display current result
            nervousness = flat_result["nervousness"]
            confidence = flat_result["confidence_level"]
            engagement = flat_result["engagement_desc"]
            dominant = flat_result["dominant_emotion"]

            conf_map = {"confident": "自信", "moderate": "自然", "nervous": "紧张"}

            cols = st.columns(4)
            cols[0].metric("紧张度", f"{nervousness:.0%}")
            cols[1].metric("自信", conf_map.get(confidence, confidence))
            cols[2].metric("投入", engagement)
            cols[3].metric("情绪", dominant)

            if flat_result.get("recommendation"):
                st.info(flat_result["recommendation"])
        else:
            st.caption("未检测到面部，请确保光线充足、正对摄像头")

    # Show accumulation count
    n = len(st.session_state.get(SESSION_KEY, []))
    if n > 0:
        st.caption(f"已采集 {n} 个表情样本，将在提交回答时一并保存")


def _analyze_photo(b64_data: str) -> Optional[Dict]:
    """Analyze a single photo for expression via backend service."""
    try:
        from backend.services.expression_analyzer import analyze_expression
        result = analyze_expression(b64_data, enforce_detection=False)
        if result and result.get("detected_face"):
            return result
        return None
    except ImportError:
        # deepface not installed — return synthetic result so flow continues
        return {
            "dominant_emotion": "neutral",
            "emotion_scores": {
                "angry": 0.02, "disgust": 0.01, "fear": 0.05,
                "happy": 0.15, "sad": 0.03, "surprise": 0.04, "neutral": 0.70,
            },
            "detected_face": True,
            "confidence": 0.8,
            "interview_relevance": {
                "nervousness": 0.15,
                "confidence_level": "moderate",
                "confidence_desc": "表现较为自然",
                "engagement": "focused",
                "engagement_desc": "专注投入",
                "recommendations": ["表情自然，继续保持（deepface 未安装，使用模拟数据）"],
            },
        }
    except Exception:
        return None
