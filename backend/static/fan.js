// Auth Check
const authData = JSON.parse(sessionStorage.getItem("fanflow_auth") || "null");
if (!authData) {
  window.location.href = "/";
} else {
  document.addEventListener("DOMContentLoaded", () => {
    const authInfo = document.getElementById("auth-info");
    const logoutBtn = document.getElementById("logout-btn");
    if (authInfo) authInfo.textContent = `Logged in as ${authData.name} · ${authData.role === 'staff' ? 'Staff' : 'Fan'}`;
    if (logoutBtn) {
      logoutBtn.addEventListener("click", () => {
        sessionStorage.removeItem("fanflow_auth");
        document.cookie = "fanflow_role=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.location.href = "/";
      });
    }
  });
}

const API_BASE_URL = window.location.origin;

// DOM Elements
const chatContainer = document.getElementById('chat-container');
const chatForm = document.getElementById('chat-form');
const chatInput = document.getElementById('chat-input');
const typingIndicator = document.getElementById('typing-indicator');
const quickReplyBtns = document.querySelectorAll('.quick-reply-btn');
const accessibilityToggle = document.getElementById('accessibility-toggle');
const languageSelect = document.getElementById('language-select');

// State
let sessionId = crypto.randomUUID();

// Event Listeners
chatForm.addEventListener('submit', handleChatSubmit);
accessibilityToggle.addEventListener('click', toggleHighContrast);

quickReplyBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const query = btn.getAttribute('data-query');
    sendMessage(query);
  });
});

// Functions
async function handleChatSubmit(e) {
  e.preventDefault();
  const query = chatInput.value.trim();
  if (!query) return;
  
  chatInput.value = '';
  await sendMessage(query);
}

async function sendMessage(text) {
  // 1. Add User Message
  appendMessage('user', text);
  
  // 2. Show Typing Indicator
  showTypingIndicator();
  
  try {
    // 3. Call FastAPI Backend
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: text,
        session_id: sessionId
      })
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    const data = await response.json();
    
    // 4. Hide Typing Indicator & Add Bot Message
    hideTypingIndicator();
    appendMessage('bot', data.answer);
    
    // Optional: Update language selector if detected language differs
    if (data.detected_language && languageSelect.value !== data.detected_language) {
      // Only update if it exists in our options
      const options = Array.from(languageSelect.options).map(o => o.value);
      if (options.includes(data.detected_language)) {
        languageSelect.value = data.detected_language;
      }
    }

  } catch (error) {
    console.error('Chat error:', error);
    hideTypingIndicator();
    appendMessage('system', 'Sorry, I am having trouble connecting to the stadium network. Please try again later.');
  }
}

function appendMessage(sender, text) {
  const msgDiv = document.createElement('div');
  msgDiv.className = `message ${sender}-message`;
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-content';
  contentDiv.textContent = text;
  
  msgDiv.appendChild(contentDiv);
  
  // Insert before typing indicator
  chatContainer.insertBefore(msgDiv, typingIndicator);
  scrollToBottom();
}

function showTypingIndicator() {
  typingIndicator.classList.remove('hidden');
  scrollToBottom();
}

function hideTypingIndicator() {
  typingIndicator.classList.add('hidden');
}

function scrollToBottom() {
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function toggleHighContrast() {
  document.body.classList.toggle('theme-standard');
  document.body.classList.toggle('theme-high-contrast');
  
  const isHighContrast = document.body.classList.contains('theme-high-contrast');
  accessibilityToggle.setAttribute('aria-pressed', isHighContrast);
}
