class ChatUI {
    constructor() {
        this.chatWindow = document.getElementById('chatbotWindow');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.chatSendBtn = document.getElementById('chatSendBtn');
        this.chatToggle = document.getElementById('chatbotToggle');
        this.chatCloseBtn = document.getElementById('chatCloseBtn');
        this.isTyping = false;
        
        this.setupEventListeners();
        
        // Auto open chat after a short delay on login page
        if (window.location.pathname.includes('/auth/login')) {
            setTimeout(() => {
                this.openChat();
                this.startWelcomeSequence();
            }, 1500);
        }
    }
    
    setupEventListeners() {
        // Toggle chat window
        this.chatToggle.addEventListener('click', () => this.toggleChat());
        
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
    
    openChat() {
        this.chatWindow.classList.remove('hidden');
        this.chatInput.focus();
    }
    
    toggleChat() {
        this.chatWindow.classList.toggle('hidden');
        if (!this.chatWindow.classList.contains('hidden')) {
            this.chatInput.focus();
            if (this.chatMessages.children.length === 0) {
                this.startWelcomeSequence();
            }
        }
    }
    
    async startWelcomeSequence() {
        // Initial greeting
        await this.addMessageWithDelay("👋 Hi there! I'm your AI assistant!", 0);
        
        // Context-aware welcome message
        if (window.location.pathname.includes('/auth/login')) {
            await this.addMessageWithDelay("I see you're at the login page! Need help signing in? I can help you with:", 1000);
            await this.addMessageWithDelay("• Logging in to your account\n• Resetting your password\n• Finding your student/teacher ID\n• General system navigation", 1500);
            await this.addMessageWithDelay("Just let me know what you need! 😊", 2000);
        } else {
            await this.addMessageWithDelay("How can I help you with attendance today?", 1000);
        }
    }
    
    async addMessageWithDelay(message, delay) {
        await new Promise(resolve => setTimeout(resolve, delay));
        this.addMessage(message);
    }
    
    addMessage(message, isUser = false) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat ${isUser ? 'chat-end' : 'chat-start'} mb-3`;
        
        messageDiv.innerHTML = `
            <div class="chat-bubble ${isUser ? 'bg-primary text-white' : 'bg-gray-100 text-gray-800'} px-4 py-2 rounded-2xl shadow-sm max-w-[85%] animate-fade-in">
                <div class="chat-content">
                    <p class="text-sm leading-relaxed whitespace-pre-wrap">${message}</p>
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    updateTypingAnimation(isTyping) {
        this.isTyping = isTyping;
        if (isTyping) {
            this.chatToggle.classList.add('animate-spin-slow');
        } else {
            this.chatToggle.classList.remove('animate-spin-slow');
        }
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        this.chatInput.value = '';
        this.addMessage(message, true);
        
        try {
            this.updateTypingAnimation(true);
            const typingDiv = document.createElement('div');
            typingDiv.className = 'chat chat-start';
            typingDiv.innerHTML = `
                <div class="chat-bubble bg-gray-100 text-gray-800 px-4 py-2 rounded-2xl">
                    <div class="flex items-center gap-2">
                        <i class="ri-robot-line text-primary animate-bounce"></i>
                        <span class="text-sm text-gray-500">AI is thinking...</span>
                    </div>
                </div>
            `;
            this.chatMessages.appendChild(typingDiv);
            this.scrollToBottom();
            
            const response = await fetch('/chat/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
                },
                body: JSON.stringify({ prompt: message })
            });
            
            typingDiv.remove();
            this.updateTypingAnimation(false);
            
            if (!response.ok) {
                throw new Error('Failed to get response');
            }
            
            const data = await response.json();
            this.addMessage(data.message);
            
            // Handle navigation
            if (data.navigation) {
                // Add a small delay to show the chatbot's response before navigating
                setTimeout(() => {
                    // Check if it's a relative or absolute path
                    const baseUrl = window.location.origin;
                    const navigationUrl = data.navigation.startsWith('/') 
                        ? `${baseUrl}${data.navigation}`
                        : `${baseUrl}/${data.navigation}`;
                    
                    // Navigate to the new page
                    window.location.href = navigationUrl;
                }, 1000);
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.updateTypingAnimation(false);
            this.addMessage('Sorry, I encountered an error. Please try again.');
        }
    }
    
    handleNavigation(tab) {
        const tabButton = document.querySelector(`[data-tab="${tab}"]`);
        if (tabButton) {
            tabButton.click();
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