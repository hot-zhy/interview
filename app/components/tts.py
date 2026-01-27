"""Text-to-Speech component using Web Speech API."""
import streamlit.components.v1 as components

def speak_text(text: str, lang: str = "zh-CN"):
    """
    Generate HTML/JS to speak text using Web Speech API.
    
    Args:
        text: Text to speak
        lang: Language code (default: zh-CN)
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script>
            function speak() {{
                if ('speechSynthesis' in window) {{
                    const utterance = new SpeechSynthesisUtterance();
                    utterance.text = {repr(text)};
                    utterance.lang = '{lang}';
                    utterance.rate = 0.9;
                    utterance.pitch = 1.0;
                    utterance.volume = 1.0;
                    
                    utterance.onstart = function() {{
                        console.log('Speech started');
                        // Trigger speaking state
                        if (window.parent) {{
                            window.parent.postMessage({{type: 'avatar_state', state: 'speaking'}}, '*');
                        }}
                    }};
                    
                    utterance.onend = function() {{
                        console.log('Speech ended');
                        // Return to idle state
                        if (window.parent) {{
                            window.parent.postMessage({{type: 'avatar_state', state: 'idle'}}, '*');
                        }}
                    }};
                    
                    utterance.onerror = function(event) {{
                        console.error('Speech error:', event);
                        // Return to idle state on error
                        if (window.parent) {{
                            window.parent.postMessage({{type: 'avatar_state', state: 'idle'}}, '*');
                        }}
                    }};
                    
                    window.speechSynthesis.speak(utterance);
                }} else {{
                    console.warn('Web Speech API not supported');
                    // Return to idle state
                    if (window.parent) {{
                        window.parent.postMessage({{type: 'avatar_state', state: 'idle'}}, '*');
                    }}
                }}
            }}
            
            // Auto-execute on load
            window.addEventListener('load', function() {{
                setTimeout(speak, 100);
            }});
        </script>
    </head>
    <body>
        <p style="display: none;">Speaking: {text[:50]}...</p>
    </body>
    </html>
    """
    components.html(html, height=1)

