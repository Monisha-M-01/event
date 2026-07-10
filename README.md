# 🏟️ FanFlow AI — FIFA World Cup 2026™

**FanFlow AI** is a GenAI-powered stadium operations prototype built for the FIFA World Cup 2026 at MetLife Stadium. It features a hybrid architecture combining a mobile-first fan chat interface, a robust FastAPI backend (RAG + LLM), and a real-time Streamlit dashboard for organizers.

---

## 🏗️ Architecture

We use a **Hybrid Architecture** rather than a pure Streamlit app to ensure the prototype reflects production-grade engineering principles:

1. **FastAPI Backend (`/backend`)**: The single source of truth. It handles the LLM integrations, RAG retrieval against stadium data, crowd simulation, and incident ranking. Exposing this as a REST API means multiple clients can share the exact same logic.
2. **Fan-Facing Chat UI (`/frontend`)**: A custom HTML/CSS/JS mobile-first web app. This is the "product" the fans use. By building this natively, we achieve a polished, accessible, and fast UI with chat bubbles, typing indicators, and high-contrast modes that Streamlit cannot easily provide.
3. **Organizer Dashboard (`/dashboard`)**: A Streamlit application. Since this is an internal tool for volunteers and staff, Streamlit is perfect. It rapidly renders live crowd data tables and alert feeds by calling the FastAPI backend.

---

## 🏆 Hackathon Judging Criteria

This prototype is meticulously designed to hit every judging criterion:

- **Code Quality**: Strict separation of concerns (backend vs frontend vs dashboard). Features type hints (`-> str`), docstrings, modular Python files, and zero duplicated logic between frontends.
- **Security**: No hardcoded API keys (uses `.env` + `pydantic-settings`). Implements strict input sanitization to block prompt injection/HTML in the chat, token-bucket rate limiting per IP, and CORS restricted to known origins.
- **Efficiency**: The LLM client uses LRU caching with TTL for repeated queries. The RAG engine retrieves only the 3 most relevant stadium zones to keep the prompt small, saving tokens and latency. Endpoints are fully async.
- **Testing**: Includes a `pytest` suite testing endpoint behavior, input validation, and rate-limiting logic using FastAPI's `TestClient`.
- **Accessibility**: The fan UI includes a High-Contrast mode toggle, native screen-reader support via `aria-` labels, proper semantic HTML, and the LLM specifically boosts accessibility-related RAG queries (wheelchair routes, sensory rooms).
- **Problem Statement Alignment**: The UI copy, dataset, and LLM system prompts explicitly target the FIFA WC 2026 MetLife Stadium experience. Features focus heavily on multilingual navigation, real-time crowd diversion, and incident response.

---

## 🚀 Setup & Run Instructions

### 1. Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# EDIT .env to add your ANTHROPIC_API_KEY
```

### 2. Start the Backend (Terminal 1)
Make sure you are in the project root directory.
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

### 3. Start the Organizer Dashboard (Terminal 2)
Make sure you are in the project root directory.
```bash
python -m streamlit run dashboard/app.py
```

### 4. Open the Fan UI
Simply open `frontend/index.html` in your web browser (e.g., via Live Server extension or just double-clicking the file). It will connect to `localhost:8000`.

---

## 🎤 Demo Script (3-5 Sentences)

"Welcome to FanFlow AI, our intelligent stadium operations platform for the 2026 World Cup. On the right, our Streamlit dashboard gives organizers live, AI-ranked incident alerts and crowd density metrics, simulating data from stadium sensors. On the left, fans use our mobile-first, highly accessible web app to get instant, multilingual navigation assistance. By separating our architecture into a central FastAPI backend serving both frontends, we guarantee consistent answers, robust security, and seamless scalability for 80,000 fans."
