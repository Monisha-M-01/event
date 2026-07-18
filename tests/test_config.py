from backend.config import get_settings


def test_get_settings():
    settings = get_settings()
    assert settings.llm_model == "gemini-3.1-flash-lite"
    assert settings.rate_limit == "30/minute"
    assert settings.staff_access_code == "admin123"
    assert settings.llm_max_retries == 3
