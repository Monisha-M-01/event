"""Pydantic models for FanFlow AI API requests and responses.

All models use strict validation and descriptive fields for
self-documenting API contracts.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DensityLevel(str, Enum):
    """Crowd density classification for a zone."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Categories of stadium alerts."""

    MEDICAL = "medical"
    OVERCROWDING = "overcrowding"
    LOST_CHILD = "lost_child"
    SECURITY = "security"
    EQUIPMENT_FAILURE = "equipment_failure"
    WEATHER = "weather"
    ACCESSIBILITY = "accessibility"
    VIP = "vip"
    FIRE = "fire"
    INFRASTRUCTURE = "infrastructure"


class AlertSeverity(int, Enum):
    """Alert severity levels (1 = informational, 5 = critical)."""

    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


# ---------------------------------------------------------------------------
# Chat (Module 1)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Incoming fan assistant chat request."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Fan's question about the stadium, navigation, or services.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session identifier for conversation continuity.",
    )


class ChatResponse(BaseModel):
    """Fan assistant response with detected language and source data."""

    answer: str = Field(..., description="LLM-generated answer in the user's language.")
    detected_language: str = Field(
        ..., description="ISO 639-1 code of the detected input language."
    )
    source_zones: list[str] = Field(
        default_factory=list,
        description="Zone IDs used as context for this answer.",
    )


# ---------------------------------------------------------------------------
# Crowd Status (Module 2)
# ---------------------------------------------------------------------------

class GateStatus(BaseModel):
    """Current status of a single gate."""

    gate_id: str
    name: str
    queue_time_minutes: int


class CrowdStatus(BaseModel):
    """Real-time crowd status for a single zone."""

    zone_id: str
    zone_name: str
    crowd_count: int = Field(..., ge=0)
    capacity: int = Field(..., gt=0)
    density_level: DensityLevel
    occupancy_percent: float = Field(..., ge=0.0, le=100.0)
    gates: list[GateStatus] = Field(default_factory=list)


class CrowdOverview(BaseModel):
    """Aggregated crowd status across all zones with LLM guidance."""

    zones: list[CrowdStatus]
    guidance: str = Field(
        ..., description="LLM-generated actionable crowd guidance text."
    )
    updated_at: datetime


# ---------------------------------------------------------------------------
# Alerts (Module 3)
# ---------------------------------------------------------------------------

class Alert(BaseModel):
    """A single stadium alert event."""

    alert_id: str
    type: AlertType
    severity: AlertSeverity
    zone: str
    section: str
    description: str
    recommended_action: str
    timestamp: datetime


class AlertCard(BaseModel):
    """LLM-prioritized alert action card for the dashboard."""

    alert: Alert
    priority_rank: int = Field(..., ge=1)
    llm_summary: str = Field(
        ..., description="LLM-generated concise summary with recommended response."
    )


class AlertOverview(BaseModel):
    """Ranked collection of alert action cards."""

    cards: list[AlertCard]
    total_alerts: int
    critical_count: int
    updated_at: datetime


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """API health check response."""

    status: str = "ok"
    service: str = "FanFlow AI"
    version: str = "1.0.0"
