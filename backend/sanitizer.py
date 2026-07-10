"""Input sanitization for user-facing chatbot queries.

Security measures:
- Strips HTML / script tags
- Enforces maximum query length
- Blocks common prompt-injection patterns
- Returns cleaned string or raises ValueError
"""

from __future__ import annotations

import re

# Maximum allowed characters in a single query
MAX_QUERY_LENGTH: int = 500

# Regex patterns for prompt-injection detection (case-insensitive)
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"ignore\s+(all\s+)?above\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\s*\|?\s*system\s*\|?\s*>", re.IGNORECASE),
    re.compile(r"act\s+as\s+(a|an)\s+(different|new)", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?prompt", re.IGNORECASE),
]

# Regex to strip HTML tags
_HTML_TAG_RE: re.Pattern[str] = re.compile(r"<[^>]+>")


def sanitize_query(query: str) -> str:
    """Validate and sanitize a user chat query.

    Args:
        query: Raw user input string.

    Returns:
        Sanitized query string, safe for inclusion in an LLM prompt.

    Raises:
        ValueError: If the query is empty, too long, or contains
            prompt-injection patterns.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    # Strip HTML / script tags
    cleaned = _HTML_TAG_RE.sub("", query)

    # Collapse excessive whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # Enforce length limit
    if len(cleaned) > MAX_QUERY_LENGTH:
        raise ValueError(
            f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters "
            f"(got {len(cleaned)})."
        )

    # Check for prompt-injection patterns
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(cleaned):
            raise ValueError(
                "Query contains disallowed patterns. "
                "Please rephrase your question about the stadium."
            )

    return cleaned
