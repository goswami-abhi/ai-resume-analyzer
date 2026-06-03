// Client Chatbot Logic

document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chatbot-input');
    const sendBtn = document.getElementById('chatbot-send-btn');
    const messageContainer = document.getElementById('chatbot-messages');
    
    // Extract analysis ID from current URL (assumed to be of the form: /result/<id>)
    const urlParts = window.location.pathname.split('/');
    const analysisId = urlParts[urlParts.length - 1];

    if (!chatInput || !sendBtn || !messageContainer || !analysisId) return;

    // Send Message Trigger
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    function sendMessage() {
        const text = chatInput.value.trim();
        if (!text) return;

        // Append User Message Bubble
        appendBubble('user', text);
        chatInput.value = '';

        // Append Loading / Thinking bubble
        const thinkingId = appendBubble('assistant', '<i class="fa-solid fa-spinner fa-spin"></i> Thinking...');
        messageContainer.scrollTop = messageContainer.scrollHeight;

        // POST request to Flask chat route
        fetch(`/chat/${analysisId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: text })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Server communication issue");
            }
            return response.json();
        })
        .then(data => {
            // Remove thinking message
            removeBubble(thinkingId);
            
            // Format and append assistant's markdown response
            appendBubble('assistant', data.response);
            messageContainer.scrollTop = messageContainer.scrollHeight;
        })
        .catch(err => {
            console.error(err);
            removeBubble(thinkingId);
            appendBubble('assistant', 'Sorry, I encountered an issue connecting to the career service. Please try again.');
            messageContainer.scrollTop = messageContainer.scrollHeight;
        });
    }

    function appendBubble(role, content) {
        const bubble = document.createElement('div');
        bubble.className = `chat-bubble ${role}`;
        
        // Simple HTML/Markdown formatting to support lists and bold texts in responses
        if (role === 'assistant' && content.includes('\n')) {
            bubble.innerHTML = formatMarkdown(content);
        } else {
            bubble.innerHTML = content;
        }

        const id = 'bubble_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        bubble.setAttribute('id', id);
        messageContainer.appendChild(bubble);
        messageContainer.scrollTop = messageContainer.scrollHeight;
        return id;
    }

    function removeBubble(id) {
        const el = document.getElementById(id);
        if (el) {
            el.remove();
        }
    }

    // Helper function to format basic markdown responses from LLMs
    function formatMarkdown(text) {
        // Bullet points formatting
        let formatted = text.replace(/^\s*-\s+(.*)$/gmi, '<li>$1</li>');
        // Group list items
        formatted = formatted.replace(/(<li>.*<\/li>)/gs, '<ul class="bullet-list" style="margin: 8px 0;">$1</ul>');
        // Bold formatting
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Newlines to breaks (excluding tags)
        formatted = formatted.split('\n').join('<br>');
        return formatted;
    }
});
