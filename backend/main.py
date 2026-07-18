"""FanFlow AI — FastAPI application entry point.

Exposes REST endpoints for:
- /chat         → RAG + LLM fan assistant (multilingual)
- /crowd-status → Live zone crowd data with LLM guidance
- /alerts       → LLM-prioritized incident action cards
- /health       → Service health check

Security: CORS restricted, rate-limited, input-sanitized.
"""

from __future__ import annotations

import logging
import os
import time
from dotenv import load_dotenv

from collections import defaultdict
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel

load_dotenv()

from backend.alert_engine import AlertEngine
from backend.config import get_settings
from backend.crowd_simulator import CrowdSimulator
from backend.llm_client import LLMClient
from backend.models import (
    AlertOverview,
    ChatRequest,
    ChatResponse,
    CrowdOverview,
    HealthResponse,
)
from backend.rag_engine import RAGEngine
from backend.sanitizer import sanitize_query

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FanFlow AI",
    description=(
        "GenAI-powered stadium operations assistant for "
        "FIFA World Cup 2026 — multilingual fan chat, "
        "crowd monitoring, and incident management."
    ),
    version="1.0.0",
)

# --- CORS (restrict to known front-end origins) ---
_ALLOWED_ORIGINS = [
    "*",  # Allow all for deployment dynamically
    "http://localhost:3000",
    "http://localhost:5500",
    "http://localhost:8501",  # Streamlit default
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8501",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "null",  # file:// protocol sends origin "null"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Rate-limiting middleware (token-bucket per IP)
# ---------------------------------------------------------------------------

_rate_buckets: dict[str, list[float]] = defaultdict(list)


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next) -> Response:
    """Basic sliding-window rate limiter per client IP."""
    settings = get_settings()
    # Parse "30/minute" format
    parts = settings.rate_limit.split("/")
    max_requests = int(parts[0])
    window_seconds = 60 if parts[1] == "minute" else int(parts[1])

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    bucket = _rate_buckets[client_ip]

    # Prune old timestamps
    _rate_buckets[client_ip] = [t for t in bucket if now - t < window_seconds]
    bucket = _rate_buckets[client_ip]

    if len(bucket) >= max_requests:
        return Response(
            content='{"detail":"Rate limit exceeded. Please try again shortly."}',
            status_code=429,
            media_type="application/json",
        )

    bucket.append(now)
    return await call_next(request)


# ---------------------------------------------------------------------------
# Shared service instances (created once at startup)
# ---------------------------------------------------------------------------

_llm_client: LLMClient | None = None
_rag_engine: RAGEngine | None = None
_crowd_sim: CrowdSimulator | None = None
_alert_engine: AlertEngine | None = None


@app.on_event("startup")
async def startup() -> None:
    """Initialize shared services on application startup."""
    global _llm_client, _rag_engine, _crowd_sim, _alert_engine  # noqa: PLW0603

    logger.info("Starting FanFlow AI backend …")
    _llm_client = LLMClient()
    _rag_engine = RAGEngine(llm_client=_llm_client)
    _rag_engine.load_knowledge_base()
    _crowd_sim = CrowdSimulator(llm_client=_llm_client)
    _alert_engine = AlertEngine(llm_client=_llm_client)
    _alert_engine.load_templates()
    logger.info("All services initialized.")


# ---------------------------------------------------------------------------
# Frontend Routes & Auth
# ---------------------------------------------------------------------------

app.mount("/static", StaticFiles(directory="backend/static"), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse("backend/static/index.html")


@app.get("/fan", include_in_schema=False)
async def serve_fan(request: Request):
    role = request.cookies.get("fanflow_role")
    if not role:
        return RedirectResponse(url="/")
    return FileResponse("backend/static/fan.html")


@app.get("/staff", include_in_schema=False)
async def serve_staff(request: Request):
    role = request.cookies.get("fanflow_role")
    if role != "staff":
        return RedirectResponse(url="/")
    return FileResponse("backend/static/staff.html")


class LoginRequest(BaseModel):
    role: str
    name: str = ""
    access_code: str = ""


@app.post("/api/login", tags=["Auth"])
async def login(req: LoginRequest, response: Response):
    """
    Hackathon scope auth: simple shared access code validation.

    IN PRODUCTION:
    - Use JWTs or a proper session store (e.g., Redis).
    - Validate users against a DB with hashed passwords (bcrypt/argon2).
    - Use secure, HttpOnly, SameSite cookies.
    """
    if req.role == "staff":
        expected_code = os.getenv("STAFF_ACCESS_CODE", "admin123")
        print(
            f"DEBUG: Comparing submitted '{req.access_code}' vs expected '{expected_code}'"
        )
        if req.access_code != expected_code:
            raise HTTPException(status_code=401, detail="Invalid access code.")

    # Simple hackathon cookie
    response.set_cookie(key="fanflow_role", value=req.role, path="/")
    return {"status": "ok", "role": req.role, "name": req.name}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Service health check."""
    return HealthResponse()


@app.post("/api/chat", response_model=ChatResponse, tags=["Fan Assistant"])
async def chat(request: ChatRequest) -> ChatResponse:
    """RAG-powered multilingual fan assistant.

    Auto-detects the user's language and responds in kind.
    Input is sanitized against prompt injection and HTML.
    """
    assert _rag_engine is not None  # guaranteed by startup

    try:
        cleaned = sanitize_query(request.query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        answer, lang, zones = await _rag_engine.answer(cleaned)
    except Exception as exc:
        logger.error("Chat LLM error: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="I'm having trouble connecting right now — please ask a staff member nearby, or try again in a moment.",
        ) from exc

    return ChatResponse(
        answer=answer,
        detected_language=lang,
        source_zones=zones,
    )


@app.get("/api/crowd-status", response_model=CrowdOverview, tags=["Crowd Management"])
async def crowd_status() -> CrowdOverview:
    """Simulated per-zone crowd counts with LLM-generated guidance.

    Returns structured crowd data (ready for a real YOLOv8 feed) and
    plain-language recommendations for fan routing.
    """
    assert _crowd_sim is not None

    statuses = _crowd_sim.get_status()

    try:
        guidance = await _crowd_sim.get_guidance(statuses)
    except Exception as exc:
        logger.error("Crowd guidance LLM error: %s", exc)
        guidance = (
            "AI routing guidance temporarily unavailable — "
            "showing raw alert data below."
        )

    return CrowdOverview(
        zones=statuses,
        guidance=guidance,
        updated_at=datetime.now(timezone.utc),
    )


@app.get("/api/alerts", response_model=AlertOverview, tags=["Incident Management"])
async def alerts() -> AlertOverview:
    """Generate mock alerts and return LLM-prioritized action cards.

    Each call produces a fresh batch of simulated incidents —
    ranked by the LLM from most to least urgent.
    """
    assert _alert_engine is not None

    alert_list = _alert_engine.generate_mock_alerts(count=5)

    try:
        overview = await _alert_engine.prioritize_alerts(alert_list)
    except Exception as exc:
        logger.error("Alert prioritization LLM error: %s", exc)
        # Fallback: show raw alerts without AI summarization
        from backend.models import AlertCard

        overview = AlertOverview(
            cards=[
                AlertCard(
                    alert=a,
                    priority_rank=i + 1,
                    llm_summary=a.recommended_action,
                )
                for i, a in enumerate(alert_list)
            ],
            total_alerts=len(alert_list),
            critical_count=sum(1 for a in alert_list if a.severity.value >= 4),
            updated_at=datetime.now(timezone.utc),
        )

    return overview


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8082))
    uvicorn.run(app, host="0.0.0.0", port=port)
