"""Audio recorder component that can directly submit audio data to Python."""
import streamlit.components.v1 as components
import streamlit as st
import json

def render_audio_submit(key: str = "audio_submit"):
    """
    Render audio recorder component that can directly submit audio to Python.
    Returns the audio data in session_state when recording is complete.
    """
    # Initialize session state
    if f"audio_submit_data_{key}" not in st.session_state:
        st.session_state[f"audio_submit_data_{key}"] = None
    if f"audio_submit_ready_{key}" not in st.session_state:
        st.session_state[f"audio_submit_ready_{key}"] = False
    
    html = f"""
    <div id="audio-submit-wrapper-{key}" style="margin: 10px 0; padding: 10px; border: 1px solid #e0e0e0; border-radius: 8px; background: #f9f9f9;">
        <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <button id="record-button-{key}" style="
                padding: 10px 20px;
                font-size: 14px;
                border: 2px solid #667eea;
                border-radius: 25px;
                background: white;
                color: #667eea;
                cursor: pointer;
                transition: all 0.3s;
                font-weight: bold;
            ">开始录音</button>
            <span id="recording-status-{key}" style="font-size: 12px; color: #666;"></span>
            <span id="recording-time-{key}" style="font-size: 12px; color: #ff6b6b; font-weight: bold; min-width: 50px;"></span>
        </div>
        <div id="audio-preview-{key}" style="margin-top: 10px; display: none;">
            <audio id="audio-player-{key}" controls style="width: 100%;"></audio>
            <p id="submit-status-{key}" style="font-size: 12px; color: #666; margin-top: 5px;"></p>
        </div>
    </div>
    
    <script>
    (function() {{
        let mediaRecorder = null;
        let audioChunks = [];
        let recordingStartTime = null;
        let recordingTimer = null;
        let isRecording = false;
        let audioStream = null;
        
        const recordButton = document.getElementById('record-button-{key}');
        const statusSpan = document.getElementById('recording-status-{key}');
        const timeSpan = document.getElementById('recording-time-{key}');
        const audioPreview = document.getElementById('audio-preview-{key}');
        const audioPlayer = document.getElementById('audio-player-{key}');
        const submitStatus = document.getElementById('submit-status-{key}');
        
        if (!recordButton) {{
            console.error('Record button not found');
            return;
        }}
        
        // Check if browser supports MediaRecorder
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
            statusSpan.textContent = '浏览器不支持录音功能（请使用 Chrome 或 Edge）';
            statusSpan.style.color = '#ff6b6b';
            recordButton.disabled = true;
            recordButton.style.opacity = '0.5';
            return;
        }}
        
        recordButton.onclick = function(e) {{
            e.preventDefault();
            e.stopPropagation();
            
            if (!isRecording) {{
                startRecording();
            }} else {{
                stopRecording();
            }}
            return false;
        }};
        
        function startRecording() {{
            navigator.mediaDevices.getUserMedia({{ audio: true }})
                .then(function(stream) {{
                    audioStream = stream;
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = function(event) {{
                        if (event.data.size > 0) {{
                            audioChunks.push(event.data);
                        }}
                    }};
                    
                    mediaRecorder.onstop = function() {{
                        const audioBlob = new Blob(audioChunks, {{ type: 'audio/webm' }});
                        const audioUrl = URL.createObjectURL(audioBlob);
                        
                        // Show audio preview
                        audioPlayer.src = audioUrl;
                        audioPreview.style.display = 'block';
                        
                        // Convert blob to base64 for transmission
                        const reader = new FileReader();
                        reader.onloadend = function() {{
                            const base64Audio = reader.result.split(',')[1];
                            const duration = (Date.now() - recordingStartTime) / 1000;
                            
                            // Store in sessionStorage
                            const audioData = {{
                                audioData: base64Audio,
                                audioFormat: 'webm',
                                duration: duration,
                                timestamp: Date.now()
                            }};
                            
                            sessionStorage.setItem('audio_data_{key}', JSON.stringify(audioData));
                            console.log('Audio recorded and stored, duration:', duration, 's');
                            
                            statusSpan.textContent = '录音已保存';
                            statusSpan.style.color = '#51cf66';
                            submitStatus.textContent = '录音完成，可以点击"提交回答"按钮';
                            submitStatus.style.color = '#51cf66';
                            
                            // Send data to Streamlit via postMessage
                            // This will be handled by the parent component
                            if (window.parent && window.parent !== window) {{
                                window.parent.postMessage({{
                                    type: 'audio_data_ready',
                                    key: '{key}',
                                    data: audioData
                                }}, '*');
                            }}
                        }};
                        reader.readAsDataURL(audioBlob);
                        
                        // Stop all tracks
                        if (audioStream) {{
                            audioStream.getTracks().forEach(track => track.stop());
                            audioStream = null;
                        }}
                    }};
                    
                    mediaRecorder.start();
                    isRecording = true;
                    recordingStartTime = Date.now();
                    
                    recordButton.innerHTML = '停止录音';
                    recordButton.style.background = '#ff6b6b';
                    recordButton.style.color = 'white';
                    recordButton.style.borderColor = '#ff6b6b';
                    statusSpan.textContent = '正在录音...';
                    statusSpan.style.color = '#ff6b6b';
                    timeSpan.textContent = '00:00';
                    
                    // Start timer
                    recordingTimer = setInterval(function() {{
                        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
                        const minutes = Math.floor(elapsed / 60);
                        const seconds = elapsed % 60;
                        timeSpan.textContent = String(minutes).padStart(2, '0') + ':' + String(seconds).padStart(2, '0');
                    }}, 1000);
                }})
                .catch(function(error) {{
                    console.error('Error accessing microphone:', error);
                    statusSpan.textContent = '无法访问麦克风: ' + error.message;
                    statusSpan.style.color = '#ff6b6b';
                }});
        }}
        
        function stopRecording() {{
            if (mediaRecorder && isRecording) {{
                mediaRecorder.stop();
                isRecording = false;
                
                if (recordingTimer) {{
                    clearInterval(recordingTimer);
                    recordingTimer = null;
                }}
                
                recordButton.innerHTML = '开始录音';
                recordButton.style.background = 'white';
                recordButton.style.color = '#667eea';
                recordButton.style.borderColor = '#667eea';
            }}
        }}
        
        // Listen for messages from parent (Streamlit)
        window.addEventListener('message', function(event) {{
            if (event.data && event.data.type === 'get_audio_data' && event.data.key === '{key}') {{
                const audioDataStr = sessionStorage.getItem('audio_data_{key}');
                if (audioDataStr) {{
                    const audioData = JSON.parse(audioDataStr);
                    if (window.parent && window.parent !== window) {{
                        window.parent.postMessage({{
                            type: 'audio_data_response',
                            key: '{key}',
                            data: audioData
                        }}, '*');
                    }}
                }}
            }}
        }});
    }})();
    </script>
    """
    
    # Render component
    components.html(html, height=150, width=600, key=f"audio_submit_{key}")
    
    # Try to get audio data from sessionStorage via JavaScript
    # We'll use a workaround: create a hidden input that JavaScript can populate
    audio_data_js = f"""
    <script>
    (function() {{
        // Listen for audio data ready message
        window.addEventListener('message', function(event) {{
            if (event.data && event.data.type === 'audio_data_ready' && event.data.key === '{key}') {{
                // Store in a way that Python can access
                // Use a hidden input with a unique ID
                const inputId = 'audio_data_input_{key}';
                let input = document.getElementById(inputId);
                if (!input) {{
                    input = document.createElement('input');
                    input.type = 'hidden';
                    input.id = inputId;
                    input.name = 'audio_data';
                    document.body.appendChild(input);
                }}
                input.value = JSON.stringify(event.data.data);
                
                // Also store in sessionStorage for retrieval
                sessionStorage.setItem('audio_data_for_python_{key}', JSON.stringify(event.data.data));
                
                console.log('Audio data stored for Python access');
            }}
        }});
        
        // On page load, check if audio data exists
        const existingData = sessionStorage.getItem('audio_data_{key}');
        if (existingData) {{
            try {{
                const audioData = JSON.parse(existingData);
                // Trigger the ready event
                if (window.parent && window.parent !== window) {{
                    window.parent.postMessage({{
                        type: 'audio_data_ready',
                        key: '{key}',
                        data: audioData
                    }}, '*');
                }}
            }} catch(e) {{
                console.error('Error parsing existing audio data:', e);
            }}
        }}
    }})();
    </script>
    """
    st.components.v1.html(audio_data_js, height=0, width=0)
    
    # Return audio data if available
    # Since we can't directly read from JavaScript, we'll use a workaround
    # Check sessionStorage via another JavaScript call that sets a query param
    return st.session_state.get(f"audio_submit_data_{key}")

