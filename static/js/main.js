// xixi的AI探索之旅 - 主JavaScript文件

class AIDeZhangChat {
    
    // 检测移动设备
    static isMobileDevice() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
    
    // 检测触摸设备
    static isTouchDevice() {
        return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
    }
    
    // 获取屏幕尺寸
    static getScreenSize() {
        return {
            width: window.innerWidth,
            height: window.innerHeight,
            isPortrait: window.innerHeight > window.innerWidth
        };
    }
    constructor() {
        this.chatHistory = document.getElementById('chatHistory');
        this.questionInput = document.getElementById('questionInput');
        this.sendButton = document.getElementById('sendButton');
        this.voiceButton = document.getElementById('voiceButton');
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.audioElement = document.getElementById('audioElement');
        this.audioPlayer = document.getElementById('audioPlayer');
        this.audioToggle = document.getElementById('audioToggle');
        this.audioStatus = document.getElementById('audioStatus');

        // 语音识别相关
        this.isRecording = false;
        this.recognition = null;

        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadInitialState();
        this.optimizeForMobile();
    }
    
    optimizeForMobile() {
        // 如果是移动设备，进行优化
        if (AIDeZhangChat.isMobileDevice()) {
            console.log('移动设备检测，进行优化...');
            
            // 添加移动端CSS类
            document.body.classList.add('mobile-device');
            
            // 如果是触摸设备
            if (AIDeZhangChat.isTouchDevice()) {
                document.body.classList.add('touch-device');
                
                // 优化触摸体验
                this.optimizeTouchExperience();
            }
            
            // 监听屏幕方向变化
            this.setupOrientationListener();
            
            // 优化虚拟键盘弹出时的布局
            this.setupKeyboardListener();
        }
    }
    
    optimizeTouchExperience() {
        // 增加按钮的触摸目标大小
        const buttons = document.querySelectorAll('button');
        buttons.forEach(btn => {
            if (btn.offsetWidth < 44 || btn.offsetHeight < 44) {
                btn.style.minWidth = '44px';
                btn.style.minHeight = '44px';
            }
        });
        
        // 防止双击缩放
        let lastTouchEnd = 0;
        document.addEventListener('touchend', (e) => {
            const now = Date.now();
            if (now - lastTouchEnd <= 300) {
                e.preventDefault();
            }
            lastTouchEnd = now;
        }, false);
    }
    
    setupOrientationListener() {
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.adjustLayoutForOrientation();
            }, 300);
        });
    }
    
    setupKeyboardListener() {
        // 监听虚拟键盘弹出/收起
        const input = this.questionInput;
        if (input) {
            input.addEventListener('focus', () => {
                setTimeout(() => {
                    this.scrollToBottom();
                }, 300);
            });
            
            input.addEventListener('blur', () => {
                setTimeout(() => {
                    this.scrollToBottom();
                }, 300);
            });
        }
    }
    
    adjustLayoutForOrientation() {
        const screen = AIDeZhangChat.getScreenSize();
        const chatHistory = this.chatHistory;
        
        if (chatHistory) {
            if (screen.isPortrait) {
                // 竖屏模式
                chatHistory.style.maxHeight = '50vh';
            } else {
                // 横屏模式
                chatHistory.style.maxHeight = '30vh';
            }
        }
    }
    
    setupEventListeners() {
        // 发送按钮点击事件
        this.sendButton.addEventListener('click', () => this.askQuestion());

        // 语音按钮点击事件（语音识别功能）
        this.voiceButton.addEventListener('click', () => this.toggleVoiceInput());

        // 输入框回车发送
        this.questionInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.askQuestion();
            }
        });

        // 音频切换
        this.audioToggle.addEventListener('change', (e) => {
            this.savePreference('audioEnabled', e.target.checked);
            console.log('语音回复：' + (e.target.checked ? '开启' : '关闭'));
        });
    }
    
    loadInitialState() {
        // 加载用户偏好
        const audioEnabled = this.getPreference('audioEnabled', true);
        this.audioToggle.checked = audioEnabled;
    }
    
    savePreference(key, value) {
        localStorage.setItem(`zxf_${key}`, JSON.stringify(value));
    }
    
    getPreference(key, defaultValue) {
        const value = localStorage.getItem(`zxf_${key}`);
        return value ? JSON.parse(value) : defaultValue;
    }
    
    async askQuestion() {
        const question = this.questionInput.value.trim();
        
        if (!question) {
            this.showError('请输入问题');
            return;
        }
        
        // 添加用户消息
        this.addUserMessage(question);
        
        // 清空输入框
        this.questionInput.value = '';
        
        // 显示加载状态
        this.showLoading(true);
        
        try {
            // 发送请求
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question: question })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();

            // Debug log to see what's returned from backend
            console.log('Backend response:', {
                answer: data.answer ? 'present' : 'missing',
                audio_base64: data.audio_base64 ? 'present (' + data.audio_base64.length + ' bytes)' : 'missing',
                audio_format: data.audio_format || 'missing',
                error: data.error
            });

            // Update audio status
            if (data.audio_base64) {
                this.updateAudioStatus('有语音');
            } else {
                this.updateAudioStatus('无语音');
            }

            // 添加AI回复
            this.addAIMessage(data.answer, data.audio_base64, data.audio_format);

            // 处理音频
            if (data.audio_base64 && this.audioToggle.checked) {
                const format = data.audio_format || 'mp3';
                this.playAudio(data.audio_base64, format);
            }
            
        } catch (error) {
            console.error('请求失败:', error);
            this.addErrorMessage('抱歉，AI助手暂时无法回答。请稍后再试！');
        } finally {
            // 隐藏加载状态
            this.showLoading(false);
        }
    }
    
    addUserMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'user-message';
        messageDiv.setAttribute('role', 'article');
        messageDiv.setAttribute('aria-label', '你的消息');
        
        const time = this.getCurrentTime();
        const formattedText = this.escapeHtml(text);
        
        messageDiv.innerHTML = `
            <div class="message-content user">
                <div class="message-header">
                    <span class="sender-name">你</span>
                    <span class="message-time" aria-label="发送时间：${time}">${time}</span>
                </div>
                <div class="message-text">${formattedText}</div>
            </div>
            <div class="message-avatar user" aria-hidden="true">
                <i class="fas fa-user"></i>
            </div>
        `;
        
        this.chatHistory.appendChild(messageDiv);
        this.scrollToBottom();
        
        // 移动端优化：添加触摸反馈
        if (AIDeZhangChat.isTouchDevice()) {
            this.addMessageTouchFeedback(messageDiv);
        }
    }
    
    addAIMessage(text, audioBase64 = null, audioFormat = 'mp3') {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'ai-message';
        messageDiv.setAttribute('role', 'article');
        messageDiv.setAttribute('aria-label', 'AI助手的回复');

        const time = this.getCurrentTime();
        const audioId = `audio-${Date.now()}`;

        // Always create audio button, enable/disable based on availability
        const hasAudio = !!audioBase64;
        let audioButtonHtml = `
            <button class="btn-audio-play ${hasAudio ? '' : 'disabled'}" id="btn-${audioId}" 
                    onclick="${hasAudio ? `window.chatApp.toggleAudio('${audioId}')` : ''}"
                    aria-label="${hasAudio ? '播放语音回复' : '暂无语音回复'}">
                <i class="fas fa-volume-${hasAudio ? 'up' : 'off'}"></i>
                <span class="btn-text">${hasAudio ? '播放语音' : '暂无语音'}</span>
            </button>
        `;

        let audioElementHtml = '';
        if (audioBase64) {
            audioElementHtml = `
                <audio id="${audioId}" src="data:audio/${audioFormat};base64,${audioBase64}" style="display:none;"></audio>
            `;
        }

        messageDiv.innerHTML = `
            <div class="message-avatar" aria-hidden="true">
                <i class="fas fa-user-tie"></i>
            </div>
            <div class="message-content">
                <div class="message-header">
                    <span class="sender-name">AI助手</span>
                    <span class="message-time" aria-label="回复时间：${time}">${time}</span>
                </div>
                <div class="message-text">${this.formatAnswer(text)}</div>
                <div class="message-actions">${audioButtonHtml}</div>
                ${audioElementHtml}
            </div>
        `;

        this.chatHistory.appendChild(messageDiv);
        this.scrollToBottom();

        // Debug log
        console.log('AI Message - hasAudio:', hasAudio, 'audioBase64 length:', audioBase64 ? audioBase64.length : 0);

        // Auto-play audio if toggle is enabled
        if (audioBase64 && this.audioToggle.checked) {
            const audioEl = messageDiv.querySelector('audio');
            audioEl.play().catch(e => {
                console.warn('自动播放失败:', e);
            });
        }
        
        // 移动端优化：添加触摸反馈
        if (AIDeZhangChat.isTouchDevice()) {
            this.addMessageTouchFeedback(messageDiv);
        }
    }
    
    addMessageTouchFeedback(messageDiv) {
        // 为消息添加触摸反馈
        let touchStartY = 0;
        let touchStartX = 0;
        
        messageDiv.addEventListener('touchstart', (e) => {
            touchStartY = e.touches[0].clientY;
            touchStartX = e.touches[0].clientX;
            messageDiv.style.transition = 'transform 0.1s ease';
            messageDiv.style.transform = 'scale(0.98)';
        }, { passive: true });
        
        messageDiv.addEventListener('touchend', () => {
            messageDiv.style.transform = 'scale(1)';
        }, { passive: true });
        
        messageDiv.addEventListener('touchcancel', () => {
            messageDiv.style.transform = 'scale(1)';
        }, { passive: true });
    }
    
    addErrorMessage(text) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'error-message';
        messageDiv.setAttribute('role', 'alert');
        messageDiv.setAttribute('aria-label', '错误提示');
        
        messageDiv.innerHTML = `
            <div class="message-avatar error" aria-hidden="true">
                <i class="fas fa-exclamation-triangle"></i>
            </div>
            <div class="message-content error">
                <div class="message-header">
                    <span class="sender-name">系统提示</span>
                </div>
                <div class="message-text">${this.escapeHtml(text)}</div>
            </div>
        `;
        
        this.chatHistory.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    formatAnswer(text) {
        // 简单的格式化处理
        let formatted = this.escapeHtml(text);
        
        // 将换行转换为<br>
        formatted = formatted.replace(/\n/g, '<br>');
        
        // 加粗处理（**text** -> <strong>text</strong>）
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // 斜体处理（*text* -> <em>text</em>）
        formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        return formatted;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    getCurrentTime() {
        const now = new Date();
        return now.toLocaleTimeString('zh-CN', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    showLoading(show) {
        if (show) {
            this.loadingOverlay.style.display = 'flex';
            this.sendButton.disabled = true;
            this.questionInput.disabled = true;
        } else {
            this.loadingOverlay.style.display = 'none';
            this.sendButton.disabled = false;
            this.questionInput.disabled = false;
            this.questionInput.focus();
        }
    }
    
    showError(message) {
        alert(message);
    }

    updateAudioStatus(status) {
        if (this.audioStatus) {
            this.audioStatus.textContent = '语音状态: ' + status;
        }
    }
    
    playAudio(base64Data, format = 'mp3') {
        if (!base64Data) return;

        this.audioPlayer.style.display = 'block';
        this.audioElement.src = `data:audio/${format};base64,${base64Data}`;
        this.audioElement.play().catch(e => {
            console.warn('音频播放失败:', e);
        });
    }

    toggleAudio(audioId) {
        const audioEl = document.getElementById(audioId);
        if (!audioEl) return;

        if (audioEl.paused) {
            audioEl.play();
        } else {
            audioEl.pause();
        }
    }

    toggleVoiceInput() {
        // 检查浏览器是否支持语音识别
        if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
            alert('您的浏览器不支持语音识别功能，请使用Chrome或Edge浏览器。');
            return;
        }

        // 如果正在录音，停止录音
        if (this.isRecording) {
            this.stopRecording();
            return;
        }

        // 开始录音
        this.startRecording();
    }

    startRecording() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        this.recognition = new SpeechRecognition();
        this.recognition.lang = 'zh-CN';
        this.recognition.continuous = true;
        this.recognition.interimResults = true;

        this.recognition.onstart = () => {
            this.isRecording = true;
            this.voiceButton.classList.add('active');
            this.questionInput.classList.add('recording');
            this.questionInput.placeholder = '正在聆听...';
            console.log('语音识别已启动');
        };

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }

            // 更新输入框内容
            if (finalTranscript) {
                this.questionInput.value = finalTranscript;
            } else {
                this.questionInput.value = interimTranscript;
            }
        };

        this.recognition.onerror = (event) => {
            console.error('语音识别错误:', event.error);
            let errorMsg = '语音识别出错: ';
            switch (event.error) {
                case 'no-speech':
                    errorMsg += '未检测到语音';
                    break;
                case 'audio-capture':
                    errorMsg += '无法获取麦克风';
                    break;
                case 'not-allowed':
                    errorMsg += '麦克风权限被拒绝';
                    break;
                default:
                    errorMsg += event.error;
            }
            this.showError(errorMsg);
            this.stopRecording();
        };

        this.recognition.onend = () => {
            // 如果用户主动停止，不自动重启
            if (this.isRecording) {
                console.log('语音识别已结束');
                this.stopRecording();
            }
        };

        this.recognition.start();
    }

    stopRecording() {
        if (this.recognition) {
            this.recognition.stop();
            this.recognition = null;
        }
        this.isRecording = false;
        this.voiceButton.classList.remove('active');
        this.questionInput.classList.remove('recording');
        this.questionInput.placeholder = '输入你的问题，比如：\'计算机专业前景怎么样？\' 或 \'普通家庭学什么专业好？\'...';
    }

    scrollToBottom() {
        this.chatHistory.scrollTop = this.chatHistory.scrollHeight;
    }
}

// 添加额外的CSS样式
const additionalStyles = `
.user-message, .ai-message, .error-message {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
    animation: fadeIn 0.5s ease-out;
}

.user-message {
    flex-direction: row-reverse;
}

.user-message .message-content {
    background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
    border-top-right-radius: 0;
    border-top-left-radius: 15px;
}

.user-message .message-content::before {
    left: auto;
    right: -10px;
    border-width: 10px 0 0 10px;
    border-color: #e3f2fd transparent transparent transparent;
}

.user-message .message-avatar {
    background: linear-gradient(135deg, #2196f3 0%, #1976d2 100%);
}

.ai-message .message-avatar {
    background: linear-gradient(135deg, #3498db 0%, #2c3e50 100%);
}

.error-message .message-avatar {
    background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
}

.error-message .message-content {
    background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
    border-color: #ffcdd2;
}

.error-message .message-content::before {
    border-color: #ffebee transparent transparent transparent;
}

.message-avatar {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.5rem;
    flex-shrink: 0;
}

.message-content {
    flex: 1;
    padding: 20px;
    border-radius: 15px;
    position: relative;
    border: 1px solid transparent;
}

.message-content::before {
    content: '';
    position: absolute;
    top: 0;
    left: -10px;
    border-width: 10px 10px 0 0;
    border-style: solid;
}

.message-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
}

.sender-name {
    font-weight: 700;
    font-size: 1.1rem;
}

.user-message .sender-name {
    color: #1976d2;
}

.ai-message .sender-name {
    color: #2c3e50;
}

.error-message .sender-name {
    color: #c0392b;
}

.message-time {
    font-size: 0.9rem;
    color: #7f8c8d;
}

.message-text {
    line-height: 1.7;
    color: #2c3e50;
}

.user-message .message-text {
    color: #1565c0;
}

.error-message .message-text {
    color: #c62828;
}
`;

// 添加样式到页面
const styleElement = document.createElement('style');
styleElement.textContent = additionalStyles;
document.head.appendChild(styleElement);

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    window.chatApp = new AIDeZhangChat();
});

// 全局函数供HTML内联调用
window.askQuestion = function() {
    if (window.chatApp) {
        window.chatApp.askQuestion();
    }
};

window.toggleVoice = function() {
    if (window.chatApp) {
        window.chatApp.toggleVoiceInput();
    }
};

window.toggleAudio = function(audioId) {
    if (window.chatApp) {
        window.chatApp.toggleAudio(audioId);
    }
};