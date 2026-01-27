"""Speech input component using Web Speech API."""
import streamlit.components.v1 as components

def render_speech_input(key: str = "speech_input"):
    """
    Render speech input component with Web Speech API.
    Creates a visible microphone button that triggers speech recognition.
    """
    html = f"""
    <div id="speech-input-wrapper-{key}" style="margin: 10px 0; padding: 10px; border: 1px solid #e0e0e0; border-radius: 8px; background: #f9f9f9;">
        <button id="mic-button-{key}" style="
            padding: 10px 20px;
            font-size: 14px;
            border: 2px solid #667eea;
            border-radius: 25px;
            background: white;
            color: #667eea;
            cursor: pointer;
            transition: all 0.3s;
            font-weight: bold;
            margin-right: 10px;
        ">🎤 点击说话</button>
        <span id="speech-status-{key}" style="font-size: 12px; color: #666;"></span>
    </div>
    
    <script>
    (function() {{
        // Get the correct window object
        let win = window;
        try {{
            if (window.parent && window.parent !== window) {{
                win = window.parent;
            }}
        }} catch(e) {{
            console.warn('Cannot access parent window:', e);
        }}
        
        let recognition = null;
        let isListening = false;
        let speechStartTime = null;
        let timestamps = [];
        let pauses = [];
        let lastEndTime = 0;
        let interimCount = 0;
        let totalConfidence = 0;
        let confidenceCount = 0;
        
        // Wait for DOM to be ready
        function initSpeechInput() {{
            // Check if browser supports speech recognition
            const SpeechRecognition = win.SpeechRecognition || win.webkitSpeechRecognition;
            
            const micButton = document.getElementById('mic-button-{key}');
            const statusDiv = document.getElementById('speech-status-{key}');
            
            if (!micButton || !statusDiv) {{
                console.error('Speech input elements not found, retrying...');
                setTimeout(initSpeechInput, 100);
                return;
            }}
            
            console.log('Speech input initialized, button found:', micButton);
            
            if (!SpeechRecognition) {{
                console.warn('Speech recognition not supported in this browser');
                statusDiv.textContent = '⚠️ 浏览器不支持语音识别（请使用 Chrome 或 Edge）';
                statusDiv.style.color = '#ff6b6b';
                micButton.disabled = true;
                micButton.style.opacity = '0.5';
                return;
            }}
            
            recognition = new SpeechRecognition();
            recognition.lang = 'zh-CN';
            recognition.continuous = false;
            recognition.interimResults = true;
            
            // Find textarea - wait for it to be available
            function findTextarea() {{
                const selectors = [
                    'textarea[data-testid*="stTextArea"]',
                    'textarea[aria-label*="回答"]',
                    'textarea[placeholder*="回答"]',
                    'textarea'
                ];
                
                // Try current document first
                for (const selector of selectors) {{
                    const textarea = document.querySelector(selector);
                    if (textarea) return textarea;
                }}
                
                // Try parent window
                try {{
                    for (const selector of selectors) {{
                        const textarea = win.document.querySelector(selector);
                        if (textarea) return textarea;
                    }}
                }} catch(e) {{
                    console.warn('Cannot access parent document:', e);
                }}
                
                return null;
            }}
            
            // Button click handler - use direct assignment for better compatibility
            micButton.onclick = function(e) {{
                e.preventDefault();
                e.stopPropagation();
                console.log('Mic button clicked, isListening:', isListening);
                
                if (!isListening) {{
                    startListening();
                }} else {{
                    stopListening();
                }}
                return false;
            }};
            
            // Also add event listener as backup
            micButton.addEventListener('click', function(e) {{
                e.preventDefault();
                e.stopPropagation();
                console.log('Mic button clicked (listener), isListening:', isListening);
                
                if (!isListening) {{
                    startListening();
                }} else {{
                    stopListening();
                }}
            }}, true);
        
            function startListening() {{
                if (!recognition || isListening) {{
                    console.log('Cannot start: recognition=', !!recognition, 'isListening=', isListening);
                    return;
                }}
                
                console.log('Starting speech recognition...');
                isListening = true;
                speechStartTime = Date.now();
                timestamps = [];
                pauses = [];
                lastEndTime = 0;
                interimCount = 0;
                totalConfidence = 0;
                confidenceCount = 0;
                
                // Update button and status
                const micButton = document.getElementById('mic-button-{key}');
                const statusDiv = document.getElementById('speech-status-{key}');
                
                if (micButton) {{
                    micButton.innerHTML = '🛑 停止录音';
                    micButton.style.background = '#ff6b6b';
                    micButton.style.color = 'white';
                    micButton.style.borderColor = '#ff6b6b';
                }}
                
                if (statusDiv) {{
                    statusDiv.textContent = '🎤 正在聆听...';
                    statusDiv.style.color = '#ff6b6b';
                }}
                
                try {{
                    recognition.start();
                }} catch(e) {{
                    console.error('Error starting recognition:', e);
                    isListening = false;
                    if (statusDiv) {{
                        statusDiv.textContent = '⚠️ 启动失败: ' + e.message;
                        statusDiv.style.color = '#ff6b6b';
                    }}
                }}
            }}
            
            function stopListening() {{
                if (!recognition || !isListening) return;
                
                console.log('Stopping speech recognition...');
                isListening = false;
                
                try {{
                    recognition.stop();
                }} catch(e) {{
                    console.error('Error stopping recognition:', e);
                }}
                
                const micButton = document.getElementById('mic-button-{key}');
                const statusDiv = document.getElementById('speech-status-{key}');
                
                if (micButton) {{
                    micButton.innerHTML = '🎤 点击说话';
                    micButton.style.background = 'white';
                    micButton.style.color = '#667eea';
                    micButton.style.borderColor = '#667eea';
                }}
            }}
            
            recognition.onstart = function() {{
                console.log('Speech recognition started');
                const statusDiv = document.getElementById('speech-status-{key}');
                if (statusDiv) {{
                    statusDiv.textContent = '🎤 正在聆听...';
                    statusDiv.style.color = '#ff6b6b';
                }}
            }};
            
            recognition.onresult = function(event) {{
                let interimTranscript = '';
                let finalTranscript = '';
                const textarea = findTextarea();
                const statusDiv = document.getElementById('speech-status-{key}');
                
                for (let i = event.resultIndex; i < event.results.length; i++) {{
                    const result = event.results[i][0];
                    const transcript = result.transcript;
                    const confidence = result.confidence || 0.8;
                    
                    if (event.results[i].isFinal) {{
                        finalTranscript += transcript;
                        // Record timestamp for final results
                        const startTime = event.timeStamp - (speechStartTime || event.timeStamp);
                        const endTime = startTime + (transcript.length * 0.1); // Estimate: ~0.1s per char
                        
                        if (lastEndTime > 0) {{
                            const pause = (startTime - lastEndTime) / 1000; // Convert to seconds
                            if (pause > 0.3) {{ // Only count pauses > 0.3s
                                pauses.push(pause);
                            }}
                        }}
                        
                        timestamps.push([transcript, startTime / 1000, endTime / 1000]);
                        lastEndTime = endTime;
                        totalConfidence += confidence;
                        confidenceCount++;
                    }} else {{
                        interimTranscript += transcript;
                        interimCount++;
                    }}
                }}
                
                // Update textarea with recognized text
                if (textarea) {{
                    const currentValue = textarea.value || '';
                    if (finalTranscript) {{
                        textarea.value = currentValue + finalTranscript;
                        // Trigger input event to update Streamlit
                        const inputEvent = new Event('input', {{ bubbles: true }});
                        textarea.dispatchEvent(inputEvent);
                    }} else if (interimTranscript && statusDiv) {{
                        // Show interim results
                        statusDiv.textContent = '正在识别: ' + interimTranscript;
                        statusDiv.style.color = '#667eea';
                    }}
                }}
            }};
            
            recognition.onerror = function(event) {{
                console.error('Speech recognition error:', event.error);
                stopListening();
                
                const statusDiv = document.getElementById('speech-status-{key}');
                if (!statusDiv) return;
                
                let errorMsg = '';
                if (event.error === 'no-speech') {{
                    errorMsg = '⚠️ 未检测到语音，请重试';
                }} else if (event.error === 'not-allowed') {{
                    errorMsg = '⚠️ 请允许麦克风权限';
                }} else {{
                    errorMsg = '⚠️ 识别出错: ' + event.error;
                }}
                
                statusDiv.textContent = errorMsg;
                statusDiv.style.color = '#ff6b6b';
                setTimeout(() => {{
                    statusDiv.textContent = '';
                }}, 3000);
            }};
            
            recognition.onend = function() {{
                console.log('Speech recognition ended, isListening:', isListening);
                
                const textarea = findTextarea();
                const statusDiv = document.getElementById('speech-status-{key}');
                
                // Store speech data
                if (!isListening && timestamps.length > 0) {{
                    const duration = (Date.now() - speechStartTime) / 1000;
                    const avgConfidence = confidenceCount > 0 ? totalConfidence / confidenceCount : 0.8;
                    
                    const speechData = {{
                        timestamps: timestamps,
                        confidence: avgConfidence,
                        duration: duration,
                        pauses: pauses,
                        interim_results: interimCount
                    }};
                    
                    // Store in textarea data attribute
                    if (textarea) {{
                        textarea.setAttribute('data-speech-data', JSON.stringify(speechData));
                        console.log('Speech data stored:', speechData);
                    }}
                    
                    if (statusDiv) {{
                        statusDiv.textContent = '✅ 识别完成';
                        statusDiv.style.color = '#51cf66';
                        setTimeout(() => {{
                            statusDiv.textContent = '';
                        }}, 2000);
                    }}
                }}
                
                if (isListening) {{
                    // Auto-restart if still in listening mode
                    setTimeout(() => {{
                        if (isListening) {{
                            try {{
                                recognition.start();
                            }} catch(e) {{
                                console.error('Error restarting recognition:', e);
                                isListening = false;
                            }}
                        }}
                    }}, 100);
                }}
            }};
        }}
        
        // Initialize when DOM is ready
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', initSpeechInput);
        }} else {{
            // DOM already ready
            setTimeout(initSpeechInput, 100);
        }}
    }})();
    </script>
    """
    components.html(html, height=80, width=600)
