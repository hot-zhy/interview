"""
实时视频预览与表情分析组件
后台线程采样帧并分析表情，结果持久化到 st.session_state
"""
import threading
import queue
import time
from typing import Dict, List, Any, Optional
import streamlit as st

_frame_queue: Optional[queue.Queue] = None
_analysis_lock = threading.Lock()
_analysis_list: List[Dict] = []
_worker_started: bool = False
_worker_lock = threading.Lock()

SESSION_KEY = "_expression_analyses"


def _ensure_frame_queue() -> queue.Queue:
    global _frame_queue
    if _frame_queue is None:
        _frame_queue = queue.Queue(maxsize=3)
    return _frame_queue


def _start_worker():
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True

    def worker():
        fq = _ensure_frame_queue()
        while True:
            try:
                item = fq.get(timeout=5.0)
                if item is None:
                    break
                img_bytes, timestamp = item
                try:
                    from backend.services.expression_analyzer import analyze_expression
                    result = analyze_expression(img_bytes, enforce_detection=False)
                    if result:
                        result["_timestamp"] = timestamp
                        with _analysis_lock:
                            _analysis_list.append(result)
                            if len(_analysis_list) > 60:
                                del _analysis_list[:30]
                except Exception:
                    pass
            except queue.Empty:
                continue
            except Exception:
                pass

    t = threading.Thread(target=worker, daemon=True)
    t.start()


def _ndarray_to_jpeg_bytes(img) -> bytes:
    from PIL import Image
    import io
    if len(img.shape) == 3 and img.shape[2] == 3:
        img_rgb = img[:, :, ::-1]
    else:
        img_rgb = img
    pil_img = Image.fromarray(img_rgb)
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _sync_to_session_state():
    """将后台线程的分析结果同步到 session_state（不清空，持续累积）"""
    with _analysis_lock:
        new_items = list(_analysis_list)
        _analysis_list.clear()
    if new_items:
        if SESSION_KEY not in st.session_state:
            st.session_state[SESSION_KEY] = []
        st.session_state[SESSION_KEY].extend(new_items)
        if len(st.session_state[SESSION_KEY]) > 100:
            st.session_state[SESSION_KEY] = st.session_state[SESSION_KEY][-80:]


def get_accumulated_expressions() -> List[Dict]:
    """获取累积的表情数据（不清空，由 clear 手动清）"""
    _sync_to_session_state()
    return list(st.session_state.get(SESSION_KEY, []))


def clear_accumulated_expressions():
    """提交成功后调用，清空已累积的表情数据"""
    st.session_state[SESSION_KEY] = []


def render_expression_video(session_id: int):
    # WebRTC P2P video needs TURN servers + camera — unavailable on cloud.
    import os
    _disabled = os.environ.get("DISABLE_WEBRTC", "").lower() in ("1", "true", "yes")
    if not _disabled:
        try:
            _val = st.secrets.get("DISABLE_WEBRTC", "")
            _disabled = str(_val).lower() in ("1", "true", "yes")
        except Exception:
            pass
    if _disabled:
        st.caption("表情分析在云端部署中暂不可用（本地运行时可用）")
        return

    fq = _ensure_frame_queue()
    _start_worker()

    try:
        from streamlit_webrtc import webrtc_streamer
    except ImportError:
        from app.i18n import t
        st.caption(t("expression_video.install_hint"))
        return

    frame_count = [0]

    def video_frame_callback(frame):
        frame_count[0] += 1
        if frame_count[0] % 90 == 0:
            try:
                img = frame.to_ndarray(format="bgr24")
                img_bytes = _ndarray_to_jpeg_bytes(img)
                ts = time.time()
                try:
                    fq.put_nowait((img_bytes, ts))
                except queue.Full:
                    try:
                        fq.get_nowait()
                    except queue.Empty:
                        pass
                    fq.put_nowait((img_bytes, ts))
            except Exception:
                pass
        return frame

    from app.i18n import t
    st.caption(t("interview.expression_caption"))
    ctx = webrtc_streamer(
        key=f"expression_video_{session_id}",
        video_frame_callback=video_frame_callback,
        media_stream_constraints={"video": True, "audio": False},
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    )

    _sync_to_session_state()
    n = len(st.session_state.get(SESSION_KEY, []))
    if n > 0:
        st.caption(t("interview.expression_samples", n=n))
