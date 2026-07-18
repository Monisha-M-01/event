import pytest
from datetime import datetime
from backend.models import (
    DensityLevel,
    AlertType,
    AlertSeverity,
    ChatRequest,
    ChatResponse,
    GateStatus,
    CrowdStatus,
    CrowdOverview,
    Alert,
    AlertCard,
    AlertOverview,
    HealthResponse,
)


def test_chat_request_valid():
    req = ChatRequest(query="Where is the restroom?")
    assert req.query == "Where is the restroom?"
    assert req.session_id is None


def test_chat_response_valid():
    resp = ChatResponse(
        answer="It's near section 102", detected_language="en", source_zones=["Z1"]
    )
    assert resp.answer == "It's near section 102"
    assert resp.detected_language == "en"
    assert resp.source_zones == ["Z1"]


def test_crowd_status_valid():
    gate = GateStatus(gate_id="G1", name="North Gate", queue_time_minutes=5)
    status = CrowdStatus(
        zone_id="Z1",
        zone_name="North Concourse",
        crowd_count=100,
        capacity=200,
        density_level=DensityLevel.MEDIUM,
        occupancy_percent=50.0,
        gates=[gate],
    )
    assert status.occupancy_percent == 50.0


def test_alert_card_valid():
    alert = Alert(
        alert_id="A1",
        type=AlertType.MEDICAL,
        severity=AlertSeverity.CRITICAL,
        zone="Z1",
        section="S102",
        description="Medical emergency",
        recommended_action="Dispatch medics",
        timestamp=datetime.now(),
    )
    card = AlertCard(
        alert=alert, priority_rank=1, llm_summary="Immediate medical dispatch required"
    )
    assert card.priority_rank == 1


def test_health_response():
    resp = HealthResponse()
    assert resp.status == "ok"
