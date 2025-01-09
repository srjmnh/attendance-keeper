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
            if (this.chatWindow.style.display === 'none' || this.chatWindow.style.display === '') {
                this.chatWindow.style.display = 'flex';
            } else {
                this.chatWindow.style.display = 'none';
            }
        });
        
        // Close chat window
        this.chatCloseBtn.addEventListener('click', () => {
            this.chatWindow.style.display = 'none';
        });
        
        // Send message on button click
        this.chatSendBtn.addEventListener('click', () => this.sendMessage());
        
        // Send message on Enter key
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }
    
    addMessage(text, sender) {
        const div = document.createElement('div');
        div.classList.add('message', sender);
        div.textContent = text;
        this.chatMessages.appendChild(div);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message) return;
        
        // Clear input
        this.chatInput.value = '';
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message })
            });
            
            const data = await response.json();
            
            if (data.error) {
                this.addMessage(data.error, 'assistant');
                return;
            }
            
            // Add assistant's response
            this.addMessage(data.message, 'assistant');
            
            // Handle navigation if present
            if (data.navigation) {
                this.handleNavigation(data.navigation);
            }
            
        } catch (error) {
            console.error('Chat error:', error);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
        }
    }
    
    handleNavigation(tab) {
        // Get the tab button
        const tabButton = document.querySelector(`#${tab}-tab`);
        if (tabButton) {
            // Trigger click on the tab
            tabButton.click();
            // Highlight the tab briefly
            tabButton.style.transition = 'background-color 0.3s';
            tabButton.style.backgroundColor = '#e3f2fd';
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