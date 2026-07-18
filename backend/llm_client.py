"""LLM client with retry, exponential backoff, and graceful error handling.

Wraps the Google GenAI SDK.  All Gemini API calls go through this module
so error handling, caching, and model selection are centralized.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from cachetools import TTLCache
from google import genai
from google.genai import types

from backend.config import get_settings

logger = logging.getLogger(__name__)

# User-friendly fallback messages (never expose raw errors to users)
FAN_FALLBACK_MESSAGE = (
    "I'm having trouble connecting right now — please ask a staff member "
    "nearby, or try again in a moment."
)
STAFF_FALLBACK_MESSAGE = (
    "AI routing guidance temporarily unavailable — showing raw alert data below."
)


class LLMClient:
    """Async client for LLM generation using Google GenAI.

    Features:
    - Automatic retry with exponential backoff for 429 (rate-limit) errors
    - Graceful fallback messages — raw API errors are NEVER returned to users
    - TTL-based response caching
    - Supports separate model tiers (flash for quality, flash-lite for speed)
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._cache: TTLCache[str, str] = TTLCache(
            maxsize=self.settings.cache_max_size,
            ttl=self.settings.cache_ttl_seconds,
        )
        if self.settings.gemini_api_key:
            self.client = genai.Client(api_key=self.settings.gemini_api_key)
        else:
            self.client = None
            logger.warning("No Gemini API key provided. Using mock responses.")

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        use_cache: bool = True,
        use_lite_model: bool = False,
        caller_context: str = "fan",
    ) -> str:
        """Return a generated response based on the prompt context.

        Args:
            system_prompt: The system instruction for the LLM.
            user_message: The user's message / prompt body.
            use_cache: Whether to check/store in the response cache.
            use_lite_model: If True, use the cheaper flash-lite model
                            (good for alert summarization, simple tasks).
            caller_context: Either "fan" or "staff" — controls which
                            fallback message is returned on error.
        """
        logger.info(
            "LLM generate called. use_cache=%s, lite=%s, context=%s",
            use_cache,
            use_lite_model,
            caller_context,
        )

        # Check cache
        cache_key = f"{system_prompt}:{user_message}"
        if use_cache and cache_key in self._cache:
            logger.info("Cache hit for LLM response")
            return self._cache[cache_key]

        if not self.client:
            # Fallback to mock responses if no API key
            return self._mock_response(system_prompt, user_message)

        # Select model
        model = (
            self.settings.llm_model_lite if use_lite_model else self.settings.llm_model
        )

        # Retry loop with exponential backoff for 429 errors
        last_error: Exception | None = None
        for attempt in range(self.settings.llm_max_retries):
            try:
                response = await self.client.aio.models.generate_content(
                    model=model,
                    contents=user_message,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=self.settings.llm_temperature,
                        max_output_tokens=self.settings.llm_max_tokens,
                    ),
                )
                result = response.text
                if use_cache:
                    self._cache[cache_key] = result
                return result

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Retry only on rate-limit (429) errors
                if "429" in error_str or "resource_exhausted" in error_str:
                    delay = self.settings.llm_retry_base_delay * (2**attempt)
                    logger.warning(
                        "Rate limited (429) on attempt %d/%d. "
                        "Retrying in %.1fs… [model=%s]",
                        attempt + 1,
                        self.settings.llm_max_retries,
                        delay,
                        model,
                    )
                    await asyncio.sleep(delay)
                    continue

                # Non-retryable error — break immediately
                logger.error(
                    "Gemini API error (non-retryable): %s [model=%s]", e, model
                )
                break

        # All retries exhausted or non-retryable error
        logger.error(
            "LLM generation failed after %d attempt(s): %s [model=%s]",
            self.settings.llm_max_retries,
            last_error,
            model,
        )

        # Return clean, user-friendly fallback — NEVER raw error text
        if caller_context == "staff":
            return STAFF_FALLBACK_MESSAGE
        return FAN_FALLBACK_MESSAGE

    def _mock_response(self, system_prompt: str, user_message: str) -> str:
        """Generate a mock response when no API key is configured."""
        # 1. Alert Prioritization Mock
        if "action summary" in system_prompt and "JSON array" in system_prompt:
            lines = [
                line
                for line in user_message.split("\n")
                if line.strip() and line[0].isdigit()
            ]
            rankings = []
            for i, line in enumerate(lines):
                rankings.append(
                    {
                        "original_index": i + 1,
                        "priority_rank": i + 1,
                        "summary": "[MOCK] Ensure safety protocols are followed immediately.",
                    }
                )
            return json.dumps(rankings)

        # 2. Crowd Guidance Mock
        if "guidance sentences" in system_prompt:
            return (
                "• [MOCK] Gate 3 is currently heavily congested; "
                "please divert to Gate 4 to save ~10 minutes.\n"
                "• [MOCK] South Stand density is critical. "
                "Avoid this area if possible and seek alternative routes."
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
