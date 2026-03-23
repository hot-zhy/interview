"""
表情分析组件 — 使用 Streamlit 内置 st.camera_input()
无需 WebRTC / TURN 服务器，Cloud 和本地均可用。
浏览器打开摄像头实时预览，用户点击拍照，后端分析表情。
"""
import base64
from typing import Dict, List, Optional
import streamlit as st

SESSION_KEY = "_expression_analyses"


def get_accumulated_expressions() -> List[Dict]:
    """获取累积的表情数据"""
    return list(st.session_state.get(SESSION_KEY, []))


def clear_accumulated_expressions():
    """提交成功后调用，清空已累积的表情数据"""
    st.session_state[SESSION_KEY] = []


def render_expression_video(session_id: int):
    """渲染摄像头拍照组件，拍照后自动分析表情。"""
    from app.i18n import t

    st.caption(t("interview.expression_caption"))

    photo = st.camera_input(
        "📸 拍一张照片用于表情分析",
        key=f"expression_camera_{session_id}",
    )

    if photo is not None:
        image_bytes = photo.getvalue()
        b64_data = base64.b64encode(image_bytes).decode("utf-8")

        # Analyze expression
        result = _analyze_photo(b64_data)

        if result:
            if SESSION_KEY not in st.session_state:
                st.session_state[SESSION_KEY] = []
            st.session_state[SESSION_KEY].append(result)

            # Show brief result
            nervousness = result.get("nervousness", 0)
            confidence = result.get("confidence_level", 0)
            engagement = result.get("engagement", 0)

            cols = st.columns(3)
            cols[0].metric("紧张度", f"{nervousness:.0%}")
            cols[1].metric("自信度", f"{confidence:.0%}")
            cols[2].metric("专注度", f"{engagement:.0%}")

            if result.get("recommendation"):
                st.info(result["recommendation"])
        else:
            st.caption("未检测到面部，请确保光线充足、正对摄像头")


def _analyze_photo(b64_data: str) -> Optional[Dict]:
    """Analyze a single photo for expression. Returns result dict or None."""
    try:
        from backend.services.expression_analyzer import analyze_expression
        return analyze_expression(b64_data, enforce_detection=False)
    except ImportError:
        return _simple_expression_placeholder()
    except Exception:
        return None


def _simple_expression_placeholder() -> Dict:
    """Fallback when deepface is not installed — return neutral placeholder."""
    return {
        "nervousness": 0.3,
        "confidence_level": 0.6,
        "engagement": 0.7,
        "dominant_emotion": "neutral",
        "recommendation": "表情分析模块未安装 (deepface)，显示默认值",
    }
