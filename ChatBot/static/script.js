// Generate a unique session ID
function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

// DOM Elements
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const chatMessages = document.getElementById('chat-messages');
const newChatBtn = document.getElementById('new-chat-btn');
const chatList = document.getElementById('chat-list');

// State
let currentSessionId = generateSessionId();
let chatSessions = new Map();

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadChatSessions();
    createNewChat();
});

newChatBtn.addEventListener('click', createNewChat);

chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = messageInput.value.trim();
    if (!message) return;

    // Add user message to chat
    addMessage(message, 'user');
    messageInput.value = '';

    // Show typing indicator
    showTypingIndicator();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message,
                session_id: currentSessionId
            })
        });

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        // Remove typing indicator and add bot response
        removeTypingIndicator();
        addMessage(data.response, 'bot', data.timestamp);

        // Update chat list
        updateChatList();
    } catch (error) {
        removeTypingIndicator();
        addMessage('Sorry, there was an error processing your request. Please try again.', 'bot');
        console.error('Error:', error);
    }
});

// Functions
async function createNewChat() {
    currentSessionId = generateSessionId();
    chatMessages.innerHTML = '';
    addMessage('Hello! I am your Amrita Bengaluru Campus Admission Assistant. How can I help you today?', 'bot');
    updateChatList();
}

async function loadChatSessions() {
    try {
        const response = await fetch('/api/chat/sessions');
        let sessions = await response.json();

        if (sessions.error) {
            throw new Error(sessions.error);
        }

        // Sort sessions by last_activity descending (latest first)
        sessions.sort((a, b) => new Date(b.last_activity) - new Date(a.last_activity));

        chatList.innerHTML = '';
        sessions.forEach(session => {
            addChatToList(session.session_id, new Date(session.last_activity), session.summary);
        });
    } catch (error) {
        console.error('Error loading chat sessions:', error);
    }
}

function addChatToList(sessionId, lastActivity, summary) {
    const chatItem = document.createElement('div');
    chatItem.className = 'chat-item flex items-center justify-between p-3 hover:bg-gray-100 cursor-pointer';
    chatItem.dataset.sessionId = sessionId;

    const chatInfo = document.createElement('div');
    chatInfo.className = 'flex-1';

    const chatTitle = document.createElement('div');
    chatTitle.className = 'font-medium';
    chatTitle.textContent = summary || `Chat ${sessionId.split('_')[1]}`;

    const chatTime = document.createElement('div');
    chatTime.className = 'text-sm text-gray-500';
    chatTime.textContent = formatDateLocal(lastActivity);

    chatInfo.appendChild(chatTitle);
    chatInfo.appendChild(chatTime);

    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'delete-chat text-red-500 hover:text-red-700 ml-2';
    deleteBtn.innerHTML = '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>';

    deleteBtn.addEventListener('click', async (e) => {
        e.stopPropagation();
        if (confirm('Are you sure you want to delete this chat?')) {
            await deleteChat(sessionId);
        }
    });

    chatItem.appendChild(chatInfo);
    chatItem.appendChild(deleteBtn);

    chatItem.addEventListener('click', () => switchChat(sessionId));

    chatList.appendChild(chatItem);
}

async function switchChat(sessionId) {
    currentSessionId = sessionId;
    chatMessages.innerHTML = '';

    try {
        const response = await fetch(`/api/chat/history/${sessionId}`);
        const history = await response.json();

        if (history.error) {
            throw new Error(history.error);
        }

        history.forEach(chat => {
            addMessage(chat.message, 'user', chat.timestamp);
            addMessage(chat.response, 'bot', chat.timestamp);
        });

        // Update active chat in sidebar
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.toggle('active', item.dataset.sessionId === sessionId);
        });

        scrollToBottom();
    } catch (error) {
        console.error('Error loading chat history:', error);
        addMessage('Error loading chat history. Please try again.', 'bot');
    }
}

async function deleteChat(sessionId) {
    try {
        const response = await fetch(`/api/chat/session/${sessionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            const chatItem = document.querySelector(`.chat-item[data-session-id="${sessionId}"]`);
            if (chatItem) {
                chatItem.remove();
            }

            if (sessionId === currentSessionId) {
                createNewChat();
            }
        }
    } catch (error) {
        console.error('Error deleting chat:', error);
    }
}

function addMessage(message, sender, timestamp = new Date().toISOString()) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}-message p-3 mb-2 max-w-[80%] ${sender === 'user' ? 'ml-auto' : 'mr-auto'}`;

    const messageContent = document.createElement('div');
    messageContent.className = 'text-sm';
    if (sender === 'bot') {
        // Render Markdown as HTML for bot messages
        messageContent.innerHTML = marked.parse(message);
    } else {
        // User messages as plain text
        messageContent.textContent = message;
    }

    const messageTime = document.createElement('div');
    messageTime.className = 'text-xs text-gray-500 mt-1';
    messageTime.textContent = formatDateLocal(timestamp);

    messageDiv.appendChild(messageContent);
    messageDiv.appendChild(messageTime);

    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function showTypingIndicator() {
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator bot-message p-3 mb-2 max-w-[80%] mr-auto';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    indicator.id = 'typing-indicator';
    chatMessages.appendChild(indicator);
    scrollToBottom();
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) {
        indicator.remove();
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatDateLocal(date) {
    if (!(date instanceof Date)) date = new Date(date);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + date.toLocaleDateString();
}

function updateChatList() {
    const chatItem = document.querySelector(`.chat-item[data-session-id="${currentSessionId}"]`);
    if (chatItem) {
        chatItem.classList.add('active');
    }
} 