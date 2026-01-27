"""Avatar component for digital interviewer with enhanced realism."""
import streamlit.components.v1 as components

def render_avatar(state: str = "idle"):
    """
    Render enhanced 2D avatar with realistic animations.
    
    Args:
        state: "idle", "speaking", "listening", or "thinking"
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                overflow: hidden;
            }}
            .avatar-container {{
                position: relative;
                width: 280px;
                height: 350px;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .avatar-wrapper {{
                position: relative;
                width: 250px;
                height: 250px;
            }}
            .avatar {{
                width: 250px;
                height: 250px;
                border-radius: 50%;
                background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 50%, #e17055 100%);
                position: relative;
                box-shadow: 0 15px 40px rgba(0,0,0,0.4),
                            inset 0 -20px 40px rgba(0,0,0,0.1),
                            inset 0 20px 40px rgba(255,255,255,0.2);
                animation: {'pulse 1.2s ease-in-out infinite' if state == 'speaking' else 
                           'breathe 3s ease-in-out infinite' if state == 'idle' else
                           'listen 1s ease-in-out infinite' if state == 'listening' else 'none'};
                overflow: hidden;
            }}
            .face {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 180px;
                height: 200px;
            }}
            /* Eyes */
            .eye-container {{
                position: absolute;
                width: 60px;
                height: 40px;
            }}
            .eye-left {{
                left: 30px;
                top: 60px;
            }}
            .eye-right {{
                right: 30px;
                top: 60px;
            }}
            .eye {{
                width: 28px;
                height: 28px;
                background: #2d3436;
                border-radius: 50%;
                position: relative;
                box-shadow: inset 0 2px 4px rgba(0,0,0,0.3),
                            inset 0 -2px 4px rgba(255,255,255,0.1);
                animation: {'none' if state == 'speaking' else 'blink 4s infinite'};
            }}
            .eye::before {{
                content: '';
                position: absolute;
                width: 12px;
                height: 12px;
                background: white;
                border-radius: 50%;
                top: 6px;
                left: 8px;
                box-shadow: 0 0 8px rgba(255,255,255,0.8);
            }}
            .eyebrow {{
                position: absolute;
                width: 35px;
                height: 8px;
                background: #2d3436;
                border-radius: 8px;
                top: -12px;
                left: -3px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }}
            /* Nose */
            .nose {{
                position: absolute;
                width: 20px;
                height: 25px;
                border: 2px solid #d63031;
                border-top: none;
                border-radius: 0 0 20px 20px;
                left: 50%;
                top: 90px;
                transform: translateX(-50%);
                opacity: 0.3;
            }}
            /* Mouth */
            .mouth {{
                position: absolute;
                width: {'70px' if state == 'speaking' else '50px'};
                height: {'45px' if state == 'speaking' else '25px'};
                border: {'4px' if state == 'speaking' else '3px'} solid #2d3436;
                border-top: none;
                border-radius: 0 0 {'70px 70px' if state == 'speaking' else '50px 50px'};
                left: 50%;
                top: 140px;
                transform: translateX(-50%);
                animation: {'talk 0.25s ease-in-out infinite' if state == 'speaking' else 'none'};
                background: {'#2d3436' if state == 'speaking' else 'transparent'};
            }}
            .mouth::after {{
                content: '';
                position: absolute;
                width: 8px;
                height: 8px;
                background: #2d3436;
                border-radius: 50%;
                bottom: -4px;
                left: 50%;
                transform: translateX(-50%);
                display: {'block' if state == 'speaking' else 'none'};
            }}
            /* Cheeks */
            .cheek {{
                position: absolute;
                width: 40px;
                height: 30px;
                background: radial-gradient(circle, rgba(255,182,193,0.4) 0%, transparent 70%);
                border-radius: 50%;
                top: 100px;
            }}
            .cheek-left {{
                left: 10px;
            }}
            .cheek-right {{
                right: 10px;
            }}
            /* Hair */
            .hair {{
                position: absolute;
                width: 250px;
                height: 120px;
                background: linear-gradient(135deg, #2d3436 0%, #636e72 100%);
                border-radius: 50% 50% 0 0;
                top: -60px;
                left: 0;
                box-shadow: 0 5px 15px rgba(0,0,0,0.3);
            }}
            .hair::before {{
                content: '';
                position: absolute;
                width: 60px;
                height: 40px;
                background: linear-gradient(135deg, #2d3436 0%, #636e72 100%);
                border-radius: 50%;
                top: -20px;
                left: 50%;
                transform: translateX(-50%);
            }}
            /* Status indicator */
            .status-indicator {{
                position: absolute;
                bottom: -30px;
                left: 50%;
                transform: translateX(-50%);
                padding: 5px 15px;
                background: rgba(255,255,255,0.9);
                border-radius: 20px;
                font-size: 12px;
                font-weight: bold;
                color: #2d3436;
                box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                white-space: nowrap;
            }}
            .status-indicator.{state} {{
                animation: {'pulse-text 1.5s ease-in-out infinite' if state == 'speaking' or state == 'listening' else 'none'};
            }}
            /* Animations */
            @keyframes blink {{
                0%, 90%, 100% {{ 
                    height: 28px;
                    transform: scaleY(1);
                }}
                92%, 98% {{ 
                    height: 2px;
                    transform: scaleY(0.1);
                }}
            }}
            @keyframes talk {{
                0%, 100% {{ 
                    height: 45px;
                    width: 70px;
                }}
                50% {{ 
                    height: 30px;
                    width: 60px;
                }}
            }}
            @keyframes pulse {{
                0%, 100% {{ 
                    transform: scale(1);
                    box-shadow: 0 15px 40px rgba(0,0,0,0.4),
                                inset 0 -20px 40px rgba(0,0,0,0.1),
                                inset 0 20px 40px rgba(255,255,255,0.2);
                }}
                50% {{ 
                    transform: scale(1.08);
                    box-shadow: 0 20px 50px rgba(0,0,0,0.5),
                                inset 0 -20px 40px rgba(0,0,0,0.1),
                                inset 0 20px 40px rgba(255,255,255,0.3);
                }}
            }}
            @keyframes breathe {{
                0%, 100% {{ 
                    transform: scale(1);
                }}
                50% {{ 
                    transform: scale(1.02);
                }}
            }}
            @keyframes listen {{
                0%, 100% {{ 
                    transform: scale(1) rotate(0deg);
                }}
                25% {{ 
                    transform: scale(1.03) rotate(-1deg);
                }}
                75% {{ 
                    transform: scale(1.03) rotate(1deg);
                }}
            }}
            @keyframes pulse-text {{
                0%, 100% {{ 
                    opacity: 1;
                    transform: translateX(-50%) scale(1);
                }}
                50% {{ 
                    opacity: 0.7;
                    transform: translateX(-50%) scale(1.05);
                }}
            }}
            .name {{
                text-align: center;
                color: white;
                margin-top: 20px;
                font-size: 18px;
                font-weight: bold;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }}
        </style>
    </head>
    <body>
        <div class="avatar-container">
            <div class="avatar-wrapper">
                <div class="hair"></div>
                <div class="avatar">
                    <div class="face">
                        <div class="cheek cheek-left"></div>
                        <div class="cheek cheek-right"></div>
                        <div class="eye-container eye-left">
                            <div class="eyebrow"></div>
                            <div class="eye"></div>
                        </div>
                        <div class="eye-container eye-right">
                            <div class="eyebrow"></div>
                            <div class="eye"></div>
                        </div>
                        <div class="nose"></div>
                        <div class="mouth"></div>
                    </div>
                </div>
                <div class="status-indicator {state}">
                    {'🗣️ 正在说话' if state == 'speaking' else 
                     '👂 正在聆听' if state == 'listening' else 
                     '💭 思考中' if state == 'thinking' else 
                     '😊 待机中'}
                </div>
            </div>
            <div class="name">AI 面试官</div>
        </div>
    </body>
    </html>
    """
    components.html(html, height=380)

