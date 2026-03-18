"""Avatar component - 面试官头像，说话时播放视频，读完后停止。"""
import streamlit.components.v1 as components
import json

# 面试场景：专业人士在办公室/视频会议中（Mixkit 免费素材）
VIDEO_URL = "https://assets.mixkit.co/videos/44753/44753-720.mp4"  # 职场女性在通话
POSTER_IMAGE = "https://assets.mixkit.co/videos/44753/44753-thumb-720-0.jpg"  # 视频首帧
FALLBACK_IMAGE = "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&h=400&fit=crop"  # 备用静态图


def render_avatar(state: str = "idle", text_to_speak: str = ""):
    """
    渲染面试官：有 text_to_speak 时播放视频并朗读，读完后自动停止视频显示静态图。
    
    Args:
        state: "idle", "speaking", "listening", "thinking"
        text_to_speak: 需要朗读的文本，非空时播放视频+TTS，读完后停止视频
    """
    status_text = {
        "speaking": "正在说话",
        "listening": "正在聆听",
        "thinking": "思考中",
        "idle": "待机中",
    }.get(state, "待机中")

    # 转义 JS 中的文本
    text_js = json.dumps(text_to_speak) if text_to_speak else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .avatar-container {{ display: flex; flex-direction: column; align-items: center; padding: 16px; }}
            .avatar-frame {{
                position: relative;
                width: 220px; height: 220px;
                border-radius: 50%;
                overflow: hidden;
                box-shadow: 0 12px 40px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.08);
                border: 4px solid rgba(255,255,255,0.95);
                background: #e2e8f0;
            }}
            .avatar-frame.speaking {{ animation: frame-speak 1.5s ease-in-out infinite; }}
            .avatar-frame.idle {{ animation: frame-idle 3s ease-in-out infinite; }}
            .avatar-video, .avatar-poster {{
                width: 100%; height: 100%;
                object-fit: cover;
                object-position: center 15%;
            }}
            .avatar-poster {{ display: none; }}
            .avatar-frame.show-poster .avatar-video {{ display: none; }}
            .avatar-frame.show-poster .avatar-poster {{ display: block; }}
            .status-badge {{ display: flex; align-items: center; gap: 8px; margin-top: 14px; padding: 8px 18px; background: #fff; border-radius: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); font-size: 13px; color: #475569; font-weight: 500; }}
            .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background: {'#22c55e' if state == 'speaking' else '#6366f1' if state == 'listening' else '#94a3b8'}; }}
            .status-dot.pulse {{ animation: dot-pulse 1.2s ease-in-out infinite; }}
            .avatar-title {{ margin-top: 6px; font-size: 14px; color: #64748b; font-weight: 500; }}
            @keyframes frame-speak {{ 0%,100% {{ transform: scale(1); }} 50% {{ transform: scale(1.03); }} }}
            @keyframes frame-idle {{ 0%,100% {{ transform: scale(1); }} 50% {{ transform: scale(1.02); }} }}
            @keyframes dot-pulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:0.6; transform:scale(1.3); }} }}
        </style>
    </head>
    <body>
        <div class="avatar-container">
            <div class="avatar-frame {'speaking' if text_to_speak else 'idle'} {'show-poster' if not text_to_speak else ''}" id="frame">
                <video class="avatar-video" id="vid" muted playsinline
                       poster="{POSTER_IMAGE}"
                       onerror="this.style.display='none'; document.getElementById('poster').style.display='block';">
                    <source src="{VIDEO_URL}" type="video/mp4" />
                </video>
                <img class="avatar-poster" id="poster" src="{POSTER_IMAGE}" alt="面试官"
                     onerror="this.src='{FALLBACK_IMAGE}'" />
            </div>
            <div class="status-badge">
                <span class="status-dot {'pulse' if state in ('speaking','listening') else ''}"></span>
                <span id="status">{status_text}</span>
            </div>
            <div class="avatar-title">AI 面试官</div>
        </div>
        <script>
            (function() {{
                var text = {text_js};
                var frame = document.getElementById('frame');
                var vid = document.getElementById('vid');
                var poster = document.getElementById('poster');
                var statusEl = document.getElementById('status');
                
                function showVideo() {{
                    frame.classList.add('speaking');
                    frame.classList.remove('show-poster');
                    if (vid) {{ vid.style.display = 'block'; vid.play(); }}
                    if (poster) poster.style.display = 'none';
                    if (statusEl) statusEl.textContent = '正在说话';
                }}
                function showPoster() {{
                    frame.classList.remove('speaking');
                    frame.classList.add('show-poster');
                    if (vid) {{ vid.pause(); vid.currentTime = 0; vid.style.display = 'none'; }}
                    if (poster) poster.style.display = 'block';
                    if (statusEl) statusEl.textContent = '待机中';
                }}
                
                if (text && text.length > 0 && 'speechSynthesis' in window) {{
                    showVideo();
                    var u = new SpeechSynthesisUtterance(text);
                    u.lang = 'zh-CN';
                    u.rate = 0.9;
                    u.onend = u.onerror = function() {{ showPoster(); }};
                    window.speechSynthesis.speak(u);
                }} else {{
                    showPoster();
                }}
            }})();
        </script>
    </body>
    </html>
    """
    components.html(html, height=340)

