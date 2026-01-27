"""Interview page."""
import streamlit as st
from sqlalchemy.orm import Session
from backend.db.base import get_db
from backend.db.models import InterviewSession, Resume
from backend.services.interview_engine import (
    create_session, start_interview, submit_answer, get_session_turns
)
from backend.core.config import settings
from app.components.avatar import render_avatar
from app.components.tts import speak_text
from app.components.ui import show_evaluation
from app.components.audio_submit import render_audio_submit
from app.components.audio_recorder import render_audio_recorder
from app.components.auth_utils import init_session_state, check_auth
from app.components.auth_loader import load_auth_on_page_load
import time
import base64
import json

st.set_page_config(page_title="面试", page_icon="💼", layout="wide")

# Load auth from localStorage first
load_auth_on_page_load()

# Initialize session state
init_session_state()

def main():
    check_auth()
    
    user_id = st.session_state.user_id
    db = next(get_db())
    
    st.title("💼 开始面试")
    st.markdown("---")
    
    # Initialize session state
    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = None
    if "avatar_state" not in st.session_state:
        st.session_state.avatar_state = "idle"
    
    # Create new interview
    with st.expander("创建新面试", expanded=st.session_state.current_session_id is None):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            track = st.selectbox(
                "技术方向",
                options=list(settings.track_chapters.keys()),
                key="new_track"
            )
        
        with col2:
            level = st.selectbox(
                "初始难度",
                options=list(range(1, 6)),
                index=2,
                key="new_level"
            )
        
        with col3:
            total_rounds = st.number_input(
                "面试轮数",
                min_value=5,
                max_value=20,
                value=10,
                key="new_rounds"
            )
        
        # Resume selection
        resumes = db.query(Resume).filter(Resume.user_id == user_id).all()
        use_resume = st.checkbox("基于简历定制题目", key="use_resume")
        resume_id = None
        
        if use_resume and resumes:
            resume_options = {f"{r.filename} ({r.created_at.strftime('%Y-%m-%d')})": r.id for r in resumes}
            selected_resume = st.selectbox("选择简历", options=list(resume_options.keys()))
            resume_id = resume_options[selected_resume]
        elif use_resume and not resumes:
            st.warning("请先上传简历")
            use_resume = False
        
        if st.button("开始面试", use_container_width=True, type="primary"):
            try:
                session = create_session(
                    db=db,
                    user_id=user_id,
                    track=track,
                    level=level,
                    resume_id=resume_id if use_resume else None,
                    total_rounds=total_rounds
                )
                st.session_state.current_session_id = session.id
                st.success("面试已创建！")
                st.rerun()
            except Exception as e:
                st.error(f"创建失败：{str(e)}")
    
    # Interview room
    if st.session_state.current_session_id:
        session_id = st.session_state.current_session_id
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        
        if not session:
            st.error("面试会话不存在")
            st.session_state.current_session_id = None
            st.rerun()
        
        st.markdown("---")
        st.markdown(f"### 面试进行中 - {session.track} (第 {session.current_round}/{session.total_rounds} 轮)")
        
        # Initialize interview if needed
        if session.current_round == 0:
            if st.button("开始第一题", use_container_width=True, type="primary"):
                with st.spinner("正在准备题目..."):
                    result = start_interview(db, session_id)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.rerun()
        
        # Interview interface
        if session.current_round > 0:
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.markdown("#### 👤 面试官")
                # Enhanced avatar with better realism
                render_avatar(st.session_state.avatar_state)
            
            with col2:
                st.markdown("#### 💬 对话区")
                
                # Display conversation history
                turns = get_session_turns(db, session_id)
                
                chat_container = st.container()
                with chat_container:
                    for idx, turn in enumerate(turns):
                        if turn["role"] == "interviewer":
                            with st.chat_message("assistant"):
                                st.markdown(turn["content"])
                                # Auto-speak for new interviewer messages
                                if idx == len(turns) - 1 and len(turns) > 0:
                                    try:
                                        speak_text(turn["content"])
                                        st.session_state.avatar_state = "speaking"
                                    except:
                                        pass
                        else:
                            with st.chat_message("user"):
                                st.markdown(turn["content"])
                
                # Answer input - support both text and audio
                if session.status == "active":
                    st.markdown("---")
                    st.markdown("#### 💬 输入回答")
                    
                    # Answer mode selection
                    answer_mode = st.radio(
                        "选择回答方式",
                        ["文字回答", "语音回答"],
                        horizontal=True,
                        key="answer_mode"
                    )
                    
                    answer_text = None
                    audio_data = None
                    
                    if answer_mode == "文字回答":
                        answer_text = st.text_area(
                            "输入你的回答",
                            height=150,
                            key="answer_input",
                            placeholder="在此输入你的回答..."
                        )
                        
                        # Update avatar state when user is typing
                        if answer_text:
                            st.session_state.avatar_state = "listening"
                    else:
                        # Audio recording - direct submit (no manual upload needed)
                        st.info("💡 点击下方按钮开始录音，录音完成后点击停止，然后直接点击提交回答")
                        render_audio_recorder(key="answer_audio")
                        
                        # JavaScript to auto-handle audio on submit
                        # When submit button is clicked, automatically extract audio from sessionStorage
                        # and create a file-like object for Python
                        auto_handle_audio_js = f"""
                        <script>
                        (function() {{
                            // This script runs when submit button is clicked
                            // It extracts audio from sessionStorage and makes it available to Python
                            
                            function setupAudioAutoSubmit() {{
                                // Find submit button
                                const checkInterval = setInterval(function() {{
                                    const submitBtn = document.querySelector('button[kind="primaryFormSubmit"]') ||
                                                     Array.from(document.querySelectorAll('button')).find(btn => 
                                                         btn.textContent && btn.textContent.trim() === '提交回答');
                                    
                                    if (submitBtn && !submitBtn.dataset.audioHandlerAdded) {{
                                        submitBtn.dataset.audioHandlerAdded = 'true';
                                        clearInterval(checkInterval);
                                        
                                        // Add click handler
                                        submitBtn.addEventListener('click', function(e) {{
                                            // Check if audio mode is selected
                                            const radios = document.querySelectorAll('input[type="radio"]');
                                            let isAudioMode = false;
                                            radios.forEach(radio => {{
                                                if (radio.checked) {{
                                                    const label = document.querySelector(`label[for="${{radio.id}}"]`);
                                                    if (label && label.textContent && label.textContent.includes('语音')) {{
                                                        isAudioMode = true;
                                                    }}
                                                }}
                                            }});
                                            
                                            if (isAudioMode) {{
                                                // Get audio data from sessionStorage
                                                const audioDataStr = sessionStorage.getItem('audio_data_answer_audio');
                                                if (audioDataStr) {{
                                                    try {{
                                                        const audioData = JSON.parse(audioDataStr);
                                                        const base64Data = audioData.audioData;
                                                        const format = audioData.audioFormat || 'webm';
                                                        
                                                        // Store in a way Python can access
                                                        // We'll use a hidden input with the base64 data
                                                        // Note: This has size limits, but works for most audio
                                                        const inputId = 'hidden_audio_base64_answer_audio';
                                                        let input = document.getElementById(inputId);
                                                        if (!input) {{
                                                            input = document.createElement('input');
                                                            input.type = 'hidden';
                                                            input.id = inputId;
                                                            input.name = 'audio_base64';
                                                            document.body.appendChild(input);
                                                        }}
                                                        input.value = base64Data;
                                                        
                                                        // Also store metadata
                                                        const metaInputId = 'hidden_audio_meta_answer_audio';
                                                        let metaInput = document.getElementById(metaInputId);
                                                        if (!metaInput) {{
                                                            metaInput = document.createElement('input');
                                                            metaInput.type = 'hidden';
                                                            metaInput.id = metaInputId;
                                                            metaInput.name = 'audio_meta';
                                                            document.body.appendChild(metaInput);
                                                        }}
                                                        metaInput.value = JSON.stringify({{
                                                            format: format,
                                                            duration: audioData.duration
                                                        }});
                                                        
                                                        // Store in sessionStorage for Python to check
                                                        sessionStorage.setItem('audio_submit_ready', 'true');
                                                        sessionStorage.setItem('audio_base64_data', base64Data);
                                                        sessionStorage.setItem('audio_format', format);
                                                        
                                                        console.log('Audio data prepared for Python submission');
                                                    }} catch(err) {{
                                                        console.error('Error preparing audio:', err);
                                                    }}
                                                }} else {{
                                                    console.warn('No audio data in sessionStorage');
                                                }}
                                            }}
                                        }}, true);
                                    }}
                                }}, 500);
                            }}
                            
                            setupAudioAutoSubmit();
                        }})();
                        </script>
                        """
                        st.components.v1.html(auto_handle_audio_js, height=0, width=0)
                        
                        # Check if audio data is ready for submission
                        # We'll check this when submit button is clicked
                        
                        # JavaScript helper to auto-download recorded audio for upload
                        auto_download_js = """
                        <script>
                        (function() {
                            // Check if audio was recorded and not yet downloaded
                            const audioDataStr = sessionStorage.getItem('audio_data_answer_audio');
                            const downloadedFlag = sessionStorage.getItem('audio_downloaded_answer_audio');
                            
                            if (audioDataStr && !downloadedFlag) {
                                try {
                                    const audioData = JSON.parse(audioDataStr);
                                    const base64Data = audioData.audioData;
                                    const format = audioData.audioFormat || 'webm';
                                    
                                    // Create and trigger download
                                    const link = document.createElement('a');
                                    link.href = 'data:audio/' + format + ';base64,' + base64Data;
                                    link.download = 'recording.' + format;
                                    link.style.display = 'none';
                                    document.body.appendChild(link);
                                    
                                    // Auto-click after a short delay
                                    setTimeout(() => {
                                        link.click();
                                        document.body.removeChild(link);
                                        
                                        // Mark as downloaded
                                        sessionStorage.setItem('audio_downloaded_answer_audio', 'true');
                                        
                                        // Show message
                                        const msg = document.createElement('div');
                                        msg.id = 'audio-download-msg';
                                        msg.innerHTML = '💡 录音文件已自动下载，请使用上方的"上传音频文件"功能上传该文件';
                                        msg.style.cssText = 'padding: 10px; background: #e3f2fd; border-radius: 5px; margin: 10px 0; color: #1976d2;';
                                        const uploader = document.querySelector('[data-testid="stFileUploader"]');
                                        if (uploader && uploader.parentElement) {
                                            uploader.parentElement.insertBefore(msg, uploader);
                                        }
                                    }, 500);
                                } catch(e) {
                                    console.error('Error creating download:', e);
                                }
                            }
                        })();
                        </script>
                        """
                        st.components.v1.html(auto_download_js, height=0, width=0)
                        
                        # JavaScript to get audio data from sessionStorage and create download
                        audio_helper_js = """
                        <script>
                        (function() {
                            // Function to get audio data and create download link
                            window.getAudioDataForSubmit = function() {
                                try {
                                    const audioDataStr = sessionStorage.getItem('audio_data_answer_audio');
                                    if (audioDataStr) {
                                        return JSON.parse(audioDataStr);
                                    }
                                } catch(e) {
                                    console.error('Error getting audio data:', e);
                                }
                                return null;
                            };
                            
                            // Function to create audio file from base64
                            window.createAudioFile = function() {
                                const audioData = window.getAudioDataForSubmit();
                                if (!audioData) return null;
                                
                                const base64Data = audioData.audioData;
                                const format = audioData.audioFormat || 'webm';
                                const binaryString = atob(base64Data);
                                const bytes = new Uint8Array(binaryString.length);
                                for (let i = 0; i < binaryString.length; i++) {
                                    bytes[i] = binaryString.charCodeAt(i);
                                }
                                const blob = new Blob([bytes], { type: `audio/${format}` });
                                return new File([blob], `recording.${format}`, { type: `audio/${format}` });
                            };
                        })();
                        </script>
                        """
                        st.components.v1.html(audio_helper_js, height=0, width=0)
                        
                        st.session_state.avatar_state = "listening"
                    
                    # Hidden text input to receive audio base64 data from JavaScript
                    audio_base64_input = st.text_input(
                        "Audio Base64 (hidden)",
                        value="",
                        key="audio_base64_hidden",
                        label_visibility="collapsed"
                    )
                    
                    # JavaScript to auto-populate hidden input from sessionStorage when audio is recorded
                    auto_populate_js = """
                    <script>
                    (function() {
                        let lastAudioData = null;
                        
                        function populateAudioData() {
                            const audioDataStr = sessionStorage.getItem('audio_data_answer_audio');
                            if (audioDataStr && audioDataStr !== lastAudioData) {
                                lastAudioData = audioDataStr;
                                
                                // Find the hidden text input by looking for input with empty value
                                // that's in a Streamlit text input container
                                const allInputs = Array.from(document.querySelectorAll('input[type="text"]'));
                                
                                // Try to find input that's empty and in a stTextInput container
                                let hiddenInput = null;
                                for (let input of allInputs) {
                                    const container = input.closest('[data-testid*="stTextInput"]');
                                    if (container && input.value === '') {
                                        hiddenInput = input;
                                        break;
                                    }
                                }
                                
                                // If still not found, use the last empty input
                                if (!hiddenInput) {
                                    hiddenInput = allInputs.find(inp => inp.value === '');
                                }
                                
                                if (hiddenInput) {
                                    hiddenInput.value = audioDataStr;
                                    // Trigger multiple events to ensure Streamlit detects the change
                                    hiddenInput.dispatchEvent(new Event('input', { bubbles: true }));
                                    hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
                                    hiddenInput.dispatchEvent(new Event('blur', { bubbles: true }));
                                    console.log('Auto-populated audio data into hidden input, size:', audioDataStr.length);
                                }
                            }
                        }
                        
                        // Run immediately and also set up interval to check for new recordings
                        populateAudioData();
                        setInterval(populateAudioData, 500);
                    })();
                    </script>
                    """
                    st.components.v1.html(auto_populate_js, height=0, width=0)
                    
                    col_submit, col_end = st.columns([3, 1])
                    with col_submit:
                        if st.button("提交回答", use_container_width=True, type="primary"):
                            if answer_mode == "文字回答":
                                if not answer_text or not answer_text.strip():
                                    st.warning("请先输入回答")
                                else:
                                    with st.spinner("正在评价..."):
                                        result = submit_answer(
                                            db, 
                                            session_id, 
                                            answer_text.strip(),
                                            answer_type="text"
                                        )
                                    
                                    if "error" in result:
                                        st.error(result["error"])
                                    else:
                                        # Show evaluation
                                        if "evaluation" in result:
                                            show_evaluation(result["evaluation"])
                                        
                                        # Update avatar state
                                        st.session_state.avatar_state = "idle"
                                        
                                        st.rerun()
                            else:
                                # Audio answer - get audio data from hidden input populated by JavaScript
                                # JavaScript will extract audio from sessionStorage and populate the hidden input
                                
                                # Set up JavaScript to extract audio and populate hidden input when submit is clicked
                                extract_audio_js = f"""
                                <script>
                                (function() {{
                                    function setupAudioExtraction() {{
                                        // Find submit button
                                        const submitBtn = Array.from(document.querySelectorAll('button')).find(btn => 
                                            btn.textContent && btn.textContent.trim() === '提交回答');
                                        
                                        if (submitBtn && !submitBtn.dataset.audioExtractorSetup) {{
                                            submitBtn.dataset.audioExtractorSetup = 'true';
                                            
                                            submitBtn.addEventListener('click', function(e) {{
                                                // Small delay to ensure Streamlit has processed the click
                                                setTimeout(function() {{
                                                    // Check if we're in audio mode
                                                    const audioModeRadios = document.querySelectorAll('input[type="radio"]');
                                                    let isAudioMode = false;
                                                    audioModeRadios.forEach(radio => {{
                                                        if (radio.checked) {{
                                                            const label = document.querySelector(`label[for="${{radio.id}}"]`);
                                                            if (label && label.textContent && label.textContent.includes('语音')) {{
                                                                isAudioMode = true;
                                                            }}
                                                        }}
                                                    }});
                                                    
                                                    if (isAudioMode) {{
                                                        // Get audio data from sessionStorage
                                                        const audioDataStr = sessionStorage.getItem('audio_data_answer_audio');
                                                        if (audioDataStr) {{
                                                            try {{
                                                                // Find the hidden text input by looking for input with key 'audio_base64_hidden'
                                                                // Streamlit creates inputs with data-testid attributes
                                                                const allInputs = Array.from(document.querySelectorAll('input[type="text"]'));
                                                                let foundInput = null;
                                                                
                                                                // Try to find input that's hidden (has display:none or is in a hidden container)
                                                                for (let input of allInputs) {{
                                                                    const style = window.getComputedStyle(input);
                                                                    const parent = input.closest('[data-testid*="stTextInput"]');
                                                                    if (parent && (style.display === 'none' || input.value === '')) {{
                                                                        foundInput = input;
                                                                        break;
                                                                    }}
                                                                }}
                                                                
                                                                // If not found, try finding by position (should be near submit button)
                                                                if (!foundInput && allInputs.length > 0) {{
                                                                    // Find input that's empty and closest to submit button
                                                                    const submitRect = submitBtn.getBoundingClientRect();
                                                                    foundInput = allInputs.reduce((closest, input) => {{
                                                                        if (input.value !== '') return closest;
                                                                        const inputRect = input.getBoundingClientRect();
                                                                        if (!closest) return input;
                                                                        const closestRect = closest.getBoundingClientRect();
                                                                        const dist1 = Math.abs(inputRect.top - submitRect.top);
                                                                        const dist2 = Math.abs(closestRect.top - submitRect.top);
                                                                        return dist1 < dist2 ? input : closest;
                                                                    }}, null);
                                                                }}
                                                                
                                                                if (foundInput) {{
                                                                    // Store audio data as JSON string in the input
                                                                    foundInput.value = audioDataStr;
                                                                    foundInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                                                    foundInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                                                    // Also trigger focus/blur to ensure Streamlit detects the change
                                                                    foundInput.focus();
                                                                    foundInput.blur();
                                                                    console.log('Audio data populated in hidden input, length:', audioDataStr.length);
                                                                }} else {{
                                                                    console.warn('Could not find hidden input to populate');
                                                                    // Fallback: store in a data attribute on the submit button
                                                                    submitBtn.dataset.audioData = audioDataStr;
                                                                }}
                                                            }} catch(err) {{
                                                                console.error('Error extracting audio:', err);
                                                            }}
                                                        }} else {{
                                                            console.warn('No audio data in sessionStorage');
                                                        }}
                                                    }}
                                                }}, 100);
                                            }}, true);
                                        }} else if (!submitBtn) {{
                                            setTimeout(setupAudioExtraction, 500);
                                        }}
                                    }}
                                    
                                    if (document.readyState === 'loading') {{
                                        document.addEventListener('DOMContentLoaded', setupAudioExtraction);
                                    }} else {{
                                        setupAudioExtraction();
                                    }}
                                }})();
                                </script>
                                """
                                st.components.v1.html(extract_audio_js, height=0, width=0)
                                
                                # Check if audio data was populated in the hidden input
                                if audio_base64_input and audio_base64_input.strip():
                                    try:
                                        # Parse JSON data from hidden input
                                        audio_data_dict = json.loads(audio_base64_input)
                                        
                                        # Process audio answer
                                        with st.spinner("正在分析语音回答..."):
                                            result = submit_answer(
                                                db,
                                                session_id,
                                                answer_text=None,
                                                answer_type="audio",
                                                audio_data=audio_data_dict
                                            )
                                        
                                        if "error" in result:
                                            st.error(result["error"])
                                        else:
                                            # Show evaluation
                                            if "evaluation" in result:
                                                show_evaluation(result["evaluation"])
                                            
                                            # Update avatar state
                                            st.session_state.avatar_state = "idle"
                                            
                                            # Clear audio data from session state
                                            if "audio_base64_hidden" in st.session_state:
                                                st.session_state.audio_base64_hidden = ""
                                            
                                            st.rerun()
                                    except json.JSONDecodeError:
                                        st.error("音频数据格式错误，请重新录音")
                                    except Exception as e:
                                        st.error(f"处理音频时出错：{str(e)}")
                                else:
                                    # No audio data yet - show fallback uploader
                                    uploaded_audio_fallback = st.file_uploader(
                                        "如果自动提交失败，请上传录音文件",
                                        type=['webm', 'wav', 'mp3', 'ogg'],
                                        key="audio_upload_fallback"
                                    )
                                    
                                    if uploaded_audio_fallback:
                                        # Process uploaded audio file
                                        import base64
                                        audio_bytes = uploaded_audio_fallback.read()
                                        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
                                        
                                        audio_data = {
                                            "audioData": audio_base64,
                                            "audioFormat": uploaded_audio_fallback.name.split('.')[-1] if '.' in uploaded_audio_fallback.name else "webm",
                                            "duration": 0
                                        }
                                        
                                        with st.spinner("正在分析语音回答..."):
                                            result = submit_answer(
                                                db,
                                                session_id,
                                                answer_text=None,
                                                answer_type="audio",
                                                audio_data=audio_data
                                            )
                                        
                                        if "error" in result:
                                            st.error(result["error"])
                                        else:
                                            # Show evaluation
                                            if "evaluation" in result:
                                                show_evaluation(result["evaluation"])
                                            
                                            # Update avatar state
                                            st.session_state.avatar_state = "idle"
                                            
                                            st.rerun()
                                    else:
                                        # Check if audio exists in sessionStorage and show helpful message
                                        check_audio_js = """
                                        <script>
                                        (function() {
                                            const audioDataStr = sessionStorage.getItem('audio_data_answer_audio');
                                            if (audioDataStr) {
                                                console.log('Audio data available in sessionStorage, ready to submit');
                                            }
                                        })();
                                        </script>
                                        """
                                        st.components.v1.html(check_audio_js, height=0, width=0)
                    
                    with col_end:
                        if st.button("结束面试", use_container_width=True, type="secondary"):
                            from backend.services.interview_engine import end_interview
                            result = end_interview(db, session_id)
                            st.session_state.current_session_id = None
                            st.success("面试已结束")
                            st.rerun()
                else:
                    st.info("面试已结束，请查看报告页面")
        
        # Session info sidebar
        with st.sidebar:
            st.markdown("### 面试信息")
            st.text(f"方向: {session.track}")
            st.text(f"难度: {session.level}")
            st.text(f"状态: {session.status}")
            st.text(f"轮数: {session.current_round}/{session.total_rounds}")
            
            if st.button("退出当前面试", use_container_width=True):
                st.session_state.current_session_id = None
                st.rerun()

if __name__ == "__main__":
    main()

