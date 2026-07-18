import pytest
import os
import json
from unittest.mock import AsyncMock
from backend.alert_engine import AlertEngine
from backend.models import AlertType, AlertSeverity, Alert

@pytest.fixture
def alert_engine(tmp_path):
    # Create a mock alerts template
    mock_alerts = {
        "alert_templates": [
            {
                "type": "medical",
                "severity": 5,
                "description_template": "Medical incident at {zone}, section {section}",
                "recommended_action": "Dispatch medical team."
            }
        ]
    }
    
    mock_knowledge = {
        "zones": [
            {
                "name": "North Concourse",
                "sections": ["101"],
                "gates": [{"name": "Gate 1"}]
            }
        ]
    }
    
    alerts_file = tmp_path / "mock_alerts.json"
    alerts_file.write_text(json.dumps(mock_alerts))
    
    knowledge_file = tmp_path / "stadium_knowledge.json"
    knowledge_file.write_text(json.dumps(mock_knowledge))
    
    engine = AlertEngine()
    engine.load_templates(alerts_path=str(alerts_file), knowledge_path=str(knowledge_file))
    return engine

def test_load_templates(alert_engine):
    assert len(alert_engine._templates) == 1
    assert len(alert_engine._zones) == 1

def test_fill_template(alert_engine):
    zone = alert_engine._zones[0]
    result = alert_engine._fill_template("Incident at {zone} {section}", zone)
    assert result == "Incident at North Concourse 101"

def test_generate_mock_alerts(alert_engine):
    alerts = alert_engine.generate_mock_alerts(count=2)
    assert len(alerts) == 2
    assert alerts[0].type == AlertType.MEDICAL
    assert alerts[0].severity == AlertSeverity.CRITICAL
    assert alerts[0].zone == "North Concourse"

@pytest.mark.asyncio
async def test_prioritize_alerts_empty(alert_engine):
    overview = await alert_engine.prioritize_alerts([])
    assert overview.total_alerts == 0
    assert len(overview.cards) == 0

@pytest.mark.asyncio
async def test_prioritize_alerts_fallback(alert_engine):
    # LLM will fail or we don't mock it, it will use fallback
    alerts = alert_engine.generate_mock_alerts(count=2)
    # The llm_client should be mocked if we want to avoid network requests
    # But since we didn't mock, it will try to call the real LLM and might fail, 
    # triggering the fallback. Let's force fallback by injecting a broken LLM.
    alert_engine._llm.generate = AsyncMock(side_effect=Exception("LLM offline"))
    
    overview = await alert_engine.prioritize_alerts(alerts)
    assert overview.total_alerts == 2
    assert len(overview.cards) == 2
