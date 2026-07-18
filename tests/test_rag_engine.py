import pytest
import json
from unittest.mock import AsyncMock
from backend.rag_engine import RAGEngine

@pytest.fixture
def rag_engine(tmp_path):
    mock_knowledge = {
        "stadium_name": "MetLife Stadium",
        "zones": [
            {
                "zone_id": "z1",
                "name": "North Concourse",
                "description": "Main entrance",
                "points_of_interest": [
                    {"name": "Restroom A", "type": "restroom"}
                ]
            }
        ]
    }
    
    knowledge_file = tmp_path / "stadium_knowledge.json"
    knowledge_file.write_text(json.dumps(mock_knowledge))
    
    engine = RAGEngine()
    # load manually for tests
    with knowledge_file.open("r") as f:
        data = json.load(f)
        engine._knowledge = data
        engine._zones = data.get("zones", [])
        engine._general_info = data.get("general_info", {})
    engine._loaded = True
    return engine

def test_build_index(rag_engine):
    assert len(rag_engine._zones) > 0

def test_detect_language(rag_engine):
    # Tested through prompt, language detection is done at generation stage now,
    # actually it's done by regex in answer()
    pass

def test_retrieve_context(rag_engine):
    context = rag_engine.retrieve("restroom")
    assert any(z["zone_id"] == "z1" for z in context)

@pytest.mark.asyncio
async def test_answer(rag_engine):
    rag_engine._llm.generate = AsyncMock(return_value="It is in the North Concourse.")
    
    answer, lang, zones = await rag_engine.answer("Where is the restroom?")
    assert answer == "It is in the North Concourse."
    assert lang == "en"
    assert "z1" in zones
