// Antigravity Admin Panel JavaScript

class AntigravityChat {
    constructor() {
        this.sessionId = 'session_' + Date.now();
        this.isOpen = false;
        this.messages = [];
        this.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        this.currentSource = null;
        this.init();
    }

    async init() {
        // Check if user is authorized
        try {
            const response = await fetch('/api/antigravity/status');
            if (response.ok) {
                const data = await response.json();
                if (data.authorized) {
                    this.showAdminButton();
                    console.log('✅ Antigravity authorized for IP:', data.ip);
                }
            }
        } catch (error) {
            console.log('Antigravity not available:', error);
        }
    }

    showAdminButton() {
        const button = document.getElementById('antigravity-trigger');
        if (button) {
            button.style.display = 'flex';
        }
    }

    toggle() {
        const modal = document.getElementById('antigravity-modal');
        this.isOpen = !this.isOpen;

        if (this.isOpen) {
            modal.classList.add('active');
            document.getElementById('antigravity-input').focus();

            // Load conversation history if exists
            if (this.messages.length === 0) {
                this.addMessage('system', 'Antigravity AI connected. How can I help you with the Sterling Lab website?');
            }
        } else {
            modal.classList.remove('active');
        }
    }

    addMessage(role, content) {
        this.messages.push({ role, content });

        const messagesContainer = document.getElementById('antigravity-messages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `ag-message ag-${role}`;

        if (role === 'system') {
            messageDiv.innerHTML = `<div class="ag-system-badge">SYSTEM</div><div class="ag-text">${this.escapeHtml(content)}</div>`;
        } else if (role === 'user') {
            messageDiv.innerHTML = `<div class="ag-text">${this.escapeHtml(content)}</div>`;
        } else if (role === 'assistant') {
            messageDiv.innerHTML = `
                <div class="ag-avatar">⚙️</div>
                <div class="ag-content">
                    <div class="ag-name">Antigravity</div>
                    <div class="ag-text">${this.formatMarkdown(content)}</div>
                </div>
            `;
        }

        messagesContainer.appendChild(messageDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    async sendMessage() {
        const input = document.getElementById('antigravity-input');
        const message = input.value.trim();

        if (!message) return;

        // Add user message
        this.addMessage('user', message);
        input.value = '';

        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'ag-message ag-assistant ag-typing';
        typingDiv.innerHTML = `
            <div class="ag-avatar">⚙️</div>
            <div class="ag-content">
                <div class="ag-name">Antigravity</div>
                <div class="ag-typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        document.getElementById('antigravity-messages').appendChild(typingDiv);

        try {
            const response = await fetch('/api/antigravity/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });

            // Remove typing indicator
            typingDiv.remove();

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
                                messageDiv.className = 'ag-message ag-assistant';
                                messageDiv.innerHTML = `
                                    <div class="ag-avatar">⚙️</div>
                                    <div class="ag-content">
                                        <div class="ag-name">Antigravity</div>
                                        <div class="ag-text"></div>
                                    </div>
                                `;
                                document.getElementById('antigravity-messages').appendChild(messageDiv);
                            }

                            messageDiv.querySelector('.ag-text').innerHTML = this.formatMarkdown(assistantMessage);
                            document.getElementById('antigravity-messages').scrollTop =
                                document.getElementById('antigravity-messages').scrollHeight;
                        }

                        if (data.done) {
                            this.messages.push({ role: 'assistant', content: assistantMessage });
                            // Generate TTS audio
                            this.playTTS(assistantMessage);
                        }

                        if (data.error) {
                            this.addMessage('system', 'Error: ' + data.error);
                        }
                    }
                }
            }

        } catch (error) {
            typingDiv.remove();
            this.addMessage('system', 'Error: ' + error.message);
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
    window.antigravity = new AntigravityChat();

    // Event listeners
    document.getElementById('antigravity-trigger')?.addEventListener('click', () => {
        window.antigravity.toggle();
    });

    document.getElementById('antigravity-close')?.addEventListener('click', () => {
        window.antigravity.toggle();
    });

    document.getElementById('antigravity-send')?.addEventListener('click', () => {
        window.antigravity.sendMessage();
    });

    document.getElementById('antigravity-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            window.antigravity.sendMessage();
        }
    });
});
