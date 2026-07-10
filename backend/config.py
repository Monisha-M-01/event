"""Application configuration loaded from environment variables.

Uses pydantic-settings to ensure secrets (API keys) are NEVER hardcoded.
Create a `.env` file from `.env.example` before running.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve paths relative to project root (one level up from backend/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """FanFlow AI configuration.

    All sensitive values are read from environment variables or a `.env` file
    located at the project root.  Never commit `.env` to version control.
    """

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- Anthropic / LLM ---
    anthropic_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.3

    # --- Caching ---
    cache_max_size: int = 256
    cache_ttl_seconds: int = 300  # 5 minutes

    # --- Rate limiting ---
    rate_limit: str = "30/minute"

    # --- Crowd simulator ---
    crowd_update_interval_seconds: int = 5

    # --- Paths ---
    knowledge_base_path: str = str(_PROJECT_ROOT / "data" / "stadium_knowledge.json")
    alerts_path: str = str(_PROJECT_ROOT / "data" / "mock_alerts.json")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings (singleton)."""
    return Settings()
