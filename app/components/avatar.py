"""Avatar component - digital human style talking interviewer."""
import streamlit.components.v1 as components

# 数字人视频：真人说话视频循环播放（Mixkit 免费素材）
# 专业演讲者正对镜头，中性背景，适合面试场景
VIDEO_SPEAKING = "https://assets.mixkit.co/videos/36779/36779-720.mp4"  # 女性演讲者（专业、中性背景）
VIDEO_IDLE = "https://assets.mixkit.co/videos/36779/36779-720.mp4"     # 待机同视频，保持生动
# 备用：若视频加载失败，使用静态图
FALLBACK_IMAGE = "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=400&h=400&fit=crop"


def render_avatar(state: str = "idle"):
    """
    渲染数字人风格面试官：说话时播放真人视频，待机时也保持动态。
    
    Args:
        state: "idle", "speaking", "listening", or "thinking"
    """
    status_text = {
        "speaking": "正在说话",
        "listening": "正在聆听",
        "thinking": "思考中",
        "idle": "待机中",
    }.get(state, "待机中")

    # 说话时用更活跃的视频，待机/聆听用稍柔和的
    video_src = VIDEO_SPEAKING if state == "speaking" else VIDEO_IDLE
    # 说话时视频更突出（轻微缩放），待机时柔和呼吸
    frame_class = "speak" if state == "speaking" else "idle"
    pulse_class = "pulse" if state in ("speaking", "listening") else ""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                background: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            .avatar-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 16px;
            }}
            .avatar-frame {{
                position: relative;
                width: 220px;
                height: 220px;
                border-radius: 50%;
                overflow: hidden;
                box-shadow: 0 12px 40px rgba(0,0,0,0.15),
                            0 4px 12px rgba(0,0,0,0.1),
                            inset 0 1px 0 rgba(255,255,255,0.6);
                border: 4px solid rgba(255,255,255,0.95);
                background: #1e293b;
            }}
            .avatar-frame.speak {{
                animation: frame-speak 1.8s ease-in-out infinite;
            }}
            .avatar-frame.idle {{
                animation: frame-idle 3s ease-in-out infinite;
            }}
            .avatar-video {{
                width: 100%;
                height: 100%;
                object-fit: cover;
                object-position: center 20%;
            }}
            .avatar-fallback {{
                position: absolute;
                top: 0; left: 0;
                width: 100%; height: 100%;
                background: linear-gradient(135deg, #334155 0%, #1e293b 100%);
                display: none;
            }}
            .avatar-fallback img {{
                width: 100%; height: 100%;
                object-fit: cover;
                object-position: center top;
            }}
            .status-badge {{
                display: flex;
                align-items: center;
                gap: 8px;
                margin-top: 14px;
                padding: 8px 18px;
                background: #ffffff;
                border-radius: 24px;
                box-shadow: 0 2px 12px rgba(0,0,0,0.08);
                font-size: 13px;
                color: #475569;
                font-weight: 500;
            }}
            .status-dot {{
                width: 8px; height: 8px;
                border-radius: 50%;
                background: {'#22c55e' if state == 'speaking' else '#6366f1' if state == 'listening' else '#94a3b8'};
            }}
            .status-dot.pulse {{
                animation: dot-pulse 1.2s ease-in-out infinite;
            }}
            .avatar-title {{
                margin-top: 6px;
                font-size: 14px;
                color: #64748b;
                font-weight: 500;
            }}
            @keyframes frame-speak {{
                0%, 100% {{ transform: scale(1); box-shadow: 0 12px 40px rgba(0,0,0,0.15); }}
                50% {{ transform: scale(1.04); box-shadow: 0 16px 48px rgba(34,197,94,0.25); }}
            }}
            @keyframes frame-idle {{
                0%, 100% {{ transform: scale(1); }}
                50% {{ transform: scale(1.02); }}
            }}
            @keyframes dot-pulse {{
                0%, 100% {{ opacity: 1; transform: scale(1); }}
                50% {{ opacity: 0.6; transform: scale(1.3); }}
            }}
        </style>
    </head>
    <body>
        <div class="avatar-container">
            <div class="avatar-frame {frame_class}">
                <video class="avatar-video" autoplay loop muted playsinline
                       poster="{FALLBACK_IMAGE}"
                       onerror="this.style.display='none'; var f=this.nextElementSibling; if(f){{ f.style.display='block'; }}">
                    <source src="{video_src}" type="video/mp4" />
                </video>
                <div class="avatar-fallback">
                    <img src="{FALLBACK_IMAGE}" alt="面试官" />
                </div>
            </div>
            <div class="status-badge">
                <span class="status-dot {pulse_class}"></span>
                <span>{status_text}</span>
            </div>
            <div class="avatar-title">AI 面试官</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=340)

