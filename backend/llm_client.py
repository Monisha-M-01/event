"""Mock LLM client for Hackathon demo.

Replaces the real Anthropic API call with mocked responses based on
simple heuristic checks of the prompt. This allows the frontend and 
dashboard to function fully without needing a real API key.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cachetools import TTLCache

from backend.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Mock async client for LLM generation."""

    def __init__(self) -> None:
        settings = get_settings()
        self._cache: TTLCache[str, str] = TTLCache(
            maxsize=settings.cache_max_size,
            ttl=settings.cache_ttl_seconds,
        )

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        use_cache: bool = True,
    ) -> str:
        """Return a mock generated response based on the prompt context."""
        logger.info("Mock LLM called. use_cache=%s", use_cache)
        
        # 1. Alert Prioritization Mock
        if "action summary" in system_prompt and "JSON array" in system_prompt:
            # Count how many alerts were provided in the user message
            lines = [line for line in user_message.split("\n") if line.strip() and line[0].isdigit()]
            rankings = []
            for i, line in enumerate(lines):
                # Reverse rank for fun, or just sequential
                rankings.append({
                    "original_index": i + 1,
                    "priority_rank": i + 1,
                    "summary": "[MOCK] Ensure safety protocols are followed immediately."
                })
            return json.dumps(rankings)
            
        # 2. Crowd Guidance Mock
        if "guidance sentences" in system_prompt:
            return (
                "• [MOCK] Gate 3 is currently heavily congested; please divert to Gate 4 to save ~10 minutes.\n"
                "• [MOCK] South Stand density is critical. Avoid this area if possible and seek alternative routes."
            )
            
        # 3. Fan Assistant Chat Mock
        return (
            "[LANG:en] (Mock AI): Welcome to MetLife Stadium! This is a mock "
            "response generated locally because no API key was provided. I am "
            "ready to assist you with stadium navigation and event info!"
        )

    def clear_cache(self) -> None:
        """Manually clear the response cache."""
        self._cache.clear()
        logger.info("LLM response cache cleared.")
