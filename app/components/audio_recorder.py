"""Audio recorder component for voice answers."""
import streamlit.components.v1 as components

def render_audio_recorder(key: str = "audio_recorder"):
    """
    Render audio recorder component.
    Records audio and stores it in sessionStorage for submission.
    """
    html = f"""
    <div id="audio-recorder-wrapper-{key}" style="margin: 10px 0; padding: 10px; border: 1px solid #e0e0e0; border-radius: 8px; background: #f9f9f9;">
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
            ">🎤 开始录音</button>
            <span id="recording-status-{key}" style="font-size: 12px; color: #666;"></span>
            <span id="recording-time-{key}" style="font-size: 12px; color: #ff6b6b; font-weight: bold; min-width: 50px;"></span>
        </div>
        <div id="audio-preview-{key}" style="margin-top: 10px; display: none;">
            <audio id="audio-player-{key}" controls style="width: 100%;"></audio>
            <p style="font-size: 12px; color: #666; margin-top: 5px;">✅ 录音完成，可以点击"提交回答"按钮</p>
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
        
        if (!recordButton) {{
            console.error('Record button not found');
            return;
        }}
        
        // Check if browser supports MediaRecorder
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {{
            statusSpan.textContent = '⚠️ 浏览器不支持录音功能（请使用 Chrome 或 Edge）';
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
                            // Clear download flag so it can be downloaded again if needed
                            sessionStorage.removeItem('audio_downloaded_{key}');
                            console.log('Audio recorded and stored, duration:', duration, 's');
                            
                            statusSpan.textContent = '✅ 录音已保存，正在自动提交分析...';
                            statusSpan.style.color = '#51cf66';
                            
                            // Notify page to auto-submit so backend starts analysis without extra click
                            try {{
                                window.dispatchEvent(new CustomEvent('audio_recording_stopped_{key}'));
                            }} catch (e) {{ console.warn('Dispatch event:', e); }}
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
                    
                    recordButton.innerHTML = '🛑 停止录音';
                    recordButton.style.background = '#ff6b6b';
                    recordButton.style.color = 'white';
                    recordButton.style.borderColor = '#ff6b6b';
                    statusSpan.textContent = '🎤 正在录音...';
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
                    statusSpan.textContent = '⚠️ 无法访问麦克风: ' + error.message;
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
                
                recordButton.innerHTML = '🎤 开始录音';
                recordButton.style.background = 'white';
                recordButton.style.color = '#667eea';
                recordButton.style.borderColor = '#667eea';
            }}
        }}
    }})();
    </script>
    """
    components.html(html, height=150, width=600)
