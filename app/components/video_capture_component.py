"""Streamlit custom component: live webcam video with background frame capture.

Shows a live video preview in the browser. Every `interval_ms` milliseconds,
a JPEG frame is captured in JavaScript and sent to Python as base64.
Works on Streamlit Cloud — no WebRTC / TURN needed.
"""
import os
import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_capture_frontend")

_video_capture = components.declare_component("video_capture", path=_FRONTEND_DIR)


def video_capture(interval_ms: int = 5000, height: int = 240, key=None):
    """Render live webcam and return the latest captured frame as base64 str.

    Returns None until the first frame is captured.
    """
    return _video_capture(interval_ms=interval_ms, height=height, key=key, default=None)
