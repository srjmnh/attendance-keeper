class ChatUI {
    constructor() {
        this.chatWindow = document.getElementById('chatbotWindow');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.chatSendBtn = document.getElementById('chatSendBtn');
        this.toggleBtn = document.getElementById('chatbotToggle');
        this.chatCloseBtn = document.getElementById('chatCloseBtn');
        
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Toggle chat window
        this.toggleBtn.addEventListener('click', () => {
            this.chatWindow.classList.toggle('hidden');
            if (!this.chatWindow.classList.contains('hidden')) {
                this.chatInput.focus();
            }
        });
        
        // Close chat window
        this.chatCloseBtn.addEventListener('click', () => {
            this.chatWindow.classList.add('hidden');
        });
        
        // Send message on button click
        this.chatSendBtn.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter key
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }
    
    addMessage(text, isUser = false) {
        const div = document.createElement('div');
        div.className = `chat ${isUser ? 'chat-end' : 'chat-start'}`;
        div.innerHTML = `
            <div class="chat-bubble ${isUser ? '' : 'chat-bubble-primary'}">
                ${this.formatMessage(text)}
            </div>
        `;
        this.chatMessages.appendChild(div);
        this.scrollToBottom();
    }
    
    formatMessage(text) {
        // Convert URLs to links
        text = text.replace(
            /(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim,
            '<a href="$1" class="link" target="_blank">$1</a>'
        );
        
        // Convert page references to links
        text = text.replace(
            /\((\/[a-zA-Z0-9\/\-_]+)\)/g,
            '(<a href="$1" class="link">$1</a>)'
        );
        
        // Convert line breaks to <br>
        return text.replace(/\n/g, '<br>');
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        // Clear input
        this.chatInput.value = '';
        
        // Add user message
        this.addMessage(message, true);
        
        try {
            // Show typing indicator
            const typingDiv = document.createElement('div');
            typingDiv.className = 'chat chat-start';
            typingDiv.innerHTML = `
                <div class="chat-bubble chat-bubble-primary opacity-50">
                    <span class="loading loading-dots"></span>
                </div>
            `;
            this.chatMessages.appendChild(typingDiv);
            this.scrollToBottom();
            
            // Send message to server
            const response = await fetch('/chat/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ prompt: message })
            });
            
            // Remove typing indicator
            typingDiv.remove();
            
            if (!response.ok) {
                throw new Error('Failed to get response');
            }
            
            const data = await response.json();
            
            // Add assistant's response
            this.addMessage(data.message);
            
            // Handle navigation if present
            if (data.navigation) {
                this.handleNavigation(data.navigation);
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.addMessage('Sorry, I encountered an error. Please try again.');
        }
    }
    
    handleNavigation(tab) {
        // Get the tab button
        const tabButton = document.querySelector(`[data-tab="${tab}"]`);
        if (tabButton) {
            // Trigger click on the tab
            tabButton.click();
            // Highlight the tab briefly
            tabButton.style.transition = 'background-color 0.3s';
            tabButton.style.backgroundColor = 'var(--primary-focus)';
            setTimeout(() => {
                tabButton.style.backgroundColor = '';
            }, 1000);
        }
    }
}

// Initialize chat when document is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatUI = new ChatUI();
}); 