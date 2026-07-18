import pytest
import json
from unittest.mock import AsyncMock
from backend.crowd_simulator import CrowdSimulator
from backend.models import DensityLevel


@pytest.fixture
def crowd_simulator(tmp_path):
    mock_knowledge = {
        "zones": [
            {
                "zone_id": "z1",
                "name": "North Concourse",
                "capacity": 1000,
                "gates": [{"gate_id": "g1", "name": "Gate 1", "queue_time_minutes": 5}],
            }
        ]
    }

    knowledge_file = tmp_path / "stadium_knowledge.json"
    knowledge_file.write_text(json.dumps(mock_knowledge))

    sim = CrowdSimulator()
    # load zones manually to point to the tmp file
    with knowledge_file.open("r") as f:
        data = json.load(f)
    sim._zones = data.get("zones", [])
    sim._sensor._capacities = {z["zone_id"]: z["capacity"] for z in sim._zones}
    sim._sensor._current_counts = {
        z["zone_id"]: int(z["capacity"] * 0.5) for z in sim._zones
    }
    sim.update()
    return sim


def test_initialize_state(crowd_simulator):
    assert len(crowd_simulator._current_statuses) == 1
    status = crowd_simulator._current_statuses[0]
    assert status.zone_id == "z1"
    assert status.capacity == 1000


def test_get_status(crowd_simulator, monkeypatch):
    # Set a specific state in sensor feed
    monkeypatch.setattr(crowd_simulator._sensor, "get_zone_counts", lambda: {"z1": 500})
    crowd_simulator.update()
    statuses = crowd_simulator.get_status()

    assert len(statuses) == 1
    status = statuses[0]
    assert status.zone_id == "z1"
    assert status.occupancy_percent == 50.0
    assert status.density_level == DensityLevel.MEDIUM


@pytest.mark.asyncio
async def test_get_guidance(crowd_simulator):
    crowd_simulator._llm.generate = AsyncMock(return_value="Route fans to Gate 1")
    statuses = crowd_simulator.get_status()
    guidance = await crowd_simulator.get_guidance(statuses)

    assert guidance == "Route fans to Gate 1"
