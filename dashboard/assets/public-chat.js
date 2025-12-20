// Public Antigravity Chat Widget

class PublicChat {
    constructor() {
        this.sessionId = 'public_' + Date.now();
        this.isOpen = false;
        this.messages = [];
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        this.currentSource = null;
        this.init();
    }

    init() {
        // Always show public chat bubble (no auth check needed)
        console.log('✅ Public Antigravity chat initialized');
    }

    toggle() {
        const modal = document.getElementById('public-chat-modal');
        this.isOpen = !this.isOpen;

        if (this.isOpen) {
            modal.classList.add('active');
            document.getElementById('public-chat-input').focus();

            // Add welcome message if first time
            if (this.messages.length === 0) {
                this.addMessage('assistant', "Hi! I'm Antigravity, the AI assistant for Sterling Lab. I can answer questions about our AI technology, features, and architecture. What would you like to know?");
            }
        } else {
            modal.classList.remove('active');
        }
    }

    addMessage(role, content) {
        this.messages.push({ role, content });

        const messagesContainer = document.getElementById('public-chat-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `pc-message pc-${role}`;

        if (role === 'user') {
            messageDiv.innerHTML = `<div class=" pc-text">${this.escapeHtml(content)}</div>`;
        } else if (role === 'assistant') {
            messageDiv.innerHTML = `
                <div class="pc-avatar">⚙️</div>
                <div class="pc-content">
                    <div class="pc-name">Antigravity</div>
                    <div class="pc-text">${this.formatMarkdown(content)}</div>
                </div>
            `;
        } else if (role === 'error') {
            messageDiv.className = 'pc-message pc-error';
            messageDiv.innerHTML = `<div class="pc-text">⚠️ ${this.escapeHtml(content)}</div>`;
        }

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async sendMessage() {
        const input = document.getElementById('public-chat-input');
        const message = input.value.trim();

        if (!message) return;

        // Add user message
        this.addMessage('user', message);
        input.value = '';

        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'pc-message pc-assistant pc-typing';
        typingDiv.innerHTML = `
            <div class="pc-avatar">⚙️</div>
            <div class="pc-content">
                <div class="pc-name">Antigravity</div>
                <div class="pc-typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        document.getElementById('public-chat-messages').appendChild(typingDiv);

        try {
            const response = await fetch('/api/antigravity/public/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });

            // Remove typing indicator
            typingDiv.remove();

            if (response.status === 429) {
                const data = await response.json();
                this.addMessage('error', data.message || 'Rate limit exceeded. Please try again later.');
                return;
            }

            if (!response.ok) {
                throw new Error('Failed to get response');
            }

            // Handle streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let assistantMessage = '';
            let messageDiv = null;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = JSON.parse(line.slice(6));

                        if (data.chunk) {
                            assistantMessage += data.chunk;

                            // Create or update message div
                            if (!messageDiv) {
                                messageDiv = document.createElement('div');
                                messageDiv.className = 'pc-message pc-assistant';
                                messageDiv.innerHTML = `
                                    <div class="pc-avatar">⚙️</div>
                                    <div class="pc-content">
                                        <div class="pc-name">Antigravity</div>
                                        <div class="pc-text"></div>
                                    </div>
                                `;
                                document.getElementById('public-chat-messages').appendChild(messageDiv);
                            }

                            messageDiv.querySelector('.pc-text').innerHTML = this.formatMarkdown(assistantMessage);
                            document.getElementById('public-chat-messages').scrollTop =
                                document.getElementById('public-chat-messages').scrollHeight;
                        }

                        if (data.done) {
                            this.messages.push({ role: 'assistant', content: assistantMessage });
                            // Generate TTS audio
                            this.playTTS(assistantMessage);
                        }

                        if (data.error) {
                            this.addMessage('error', data.error);
                        }
                    }
                }
            }

        } catch (error) {
            typingDiv.remove();
            this.addMessage('error', 'Sorry, something went wrong. Please try again.');
        }
    }

    formatMarkdown(text) {
        // Basic markdown formatting
        let html = this.escapeHtml(text);

        // Code blocks
        html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');

        // Inline code
        html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

        // Bold
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Line breaks
        html = html.replace(/\n/g, '<br>');

        return html;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async playTTS(text) {
        try {
            const response = await fetch('/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: text })
            });

            if (response.ok) {
                const audioBlob = await response.blob();
                await this.playAudioBlob(audioBlob);
            }
        } catch (error) {
            console.error('TTS failed:', error);
        }
    }

    async playAudioBlob(blob) {
        try {
            this.stopAudio();
            const arrayBuffer = await blob.arrayBuffer();
            const audioBuffer = await this.audioCtx.decodeAudioData(arrayBuffer);
            const source = this.audioCtx.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioCtx.destination);
            source.start(0);
            this.currentSource = source;
            source.onended = () => {
                if (this.currentSource === source) this.currentSource = null;
            };
        } catch (error) {
            console.error('Audio playback failed:', error);
        }
    }

    stopAudio() {
        if (this.currentSource) {
            this.currentSource.stop();
            this.currentSource = null;
        }
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.publicChat = new PublicChat();

    // Event listeners
    document.getElementById('public-chat-trigger')?.addEventListener('click', () => {
        window.publicChat.toggle();
    });

    document.getElementById('public-chat-close')?.addEventListener('click', () => {
        window.publicChat.toggle();
    });

    document.getElementById('public-chat-send')?.addEventListener('click', () => {
        window.publicChat.sendMessage();
    });

    document.getElementById('public-chat-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            window.publicChat.sendMessage();
        }
    });
});
