// Public Antigravity Chat Widget

class PublicChat {
    constructor() {
        this.sessionId = 'public_' + Date.now();
        this.isOpen = false;
        this.messages = [];
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
                this.addMessage('assistant', "Hi! I'm here to help you learn about Swayne Systems. I can answer questions about our AI technology, features, and architecture. What would you like to know?");
            }

            // Initialize Matrix effect
            this.initMatrix();
        } else {
            modal.classList.remove('active');
            this.stopMatrix();
        }
    }

    initMatrix() {
        if (this.matrixCanvas) return; // Already initialized

        const messagesContainer = document.getElementById('public-chat-messages');
        this.matrixCanvas = document.createElement('canvas');
        this.matrixCanvas.style.position = 'absolute';
        this.matrixCanvas.style.top = '0';
        this.matrixCanvas.style.left = '0';
        this.matrixCanvas.style.width = '100%';
        this.matrixCanvas.style.height = '100%';
        this.matrixCanvas.style.pointerEvents = 'none';
        this.matrixCanvas.style.opacity = '0.15';
        this.matrixCanvas.style.zIndex = '0';
        messagesContainer.insertBefore(this.matrixCanvas, messagesContainer.firstChild);

        const ctx = this.matrixCanvas.getContext('2d');
        this.matrixCanvas.width = messagesContainer.offsetWidth;
        this.matrixCanvas.height = messagesContainer.offsetHeight;

        const chars = '01アイウエオカキクケコサシスセソタチツテト';
        const fontSize = 14;
        const columns = this.matrixCanvas.width / fontSize;
        const drops = Array(Math.floor(columns)).fill(1);

        const draw = () => {
            ctx.fillStyle = 'rgba(10, 14, 26, 0.05)';
            ctx.fillRect(0, 0, this.matrixCanvas.width, this.matrixCanvas.height);
            ctx.fillStyle = '#10b981';
            ctx.font = fontSize + 'px monospace';

            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);

                if (drops[i] * fontSize > this.matrixCanvas.height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                drops[i]++;
            }
        };

        this.matrixInterval = setInterval(draw, 50);
    }

    stopMatrix() {
        if (this.matrixInterval) {
            clearInterval(this.matrixInterval);
            this.matrixInterval = null;
        }
        if (this.matrixCanvas) {
            this.matrixCanvas.remove();
            this.matrixCanvas = null;
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
                    <div class="pc-name">Swayne Systems</div>
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

        // Add instant "analyzing" feedback
        const analyzingDiv = document.createElement('div');
        analyzingDiv.className = 'pc-message pc-system';
        analyzingDiv.innerHTML = `<div class="pc-text" style="opacity:0.7; font-style:italic;">🔍 Analyzing your question...</div>`;
        document.getElementById('public-chat-messages').appendChild(analyzingDiv);
        document.getElementById('public-chat-messages').scrollTop =
            document.getElementById('public-chat-messages').scrollHeight;

        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'pc-message pc-assistant pc-typing';
        typingDiv.innerHTML = `
            <div class="pc-avatar">⚙️</div>
            <div class="pc-content">
                <div class="pc-name">Swayne Systems</div>
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

            // Remove typing and analyzing indicators
            analyzingDiv.remove();
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
                                        <div class="pc-name">Swayne Systems</div>
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
