"""RAG (Retrieval-Augmented Generation) engine for the Fan Assistant.

Loads the local stadium knowledge base and performs lightweight keyword
retrieval to find relevant zones.  Builds a minimal prompt for Claude
containing only the pertinent zone data — not the full dataset.

Accessibility queries are boosted so wheelchair routes, sensory-friendly
zones, and other accessibility data are treated as first-class.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Keywords that signal an accessibility-related query
_ACCESSIBILITY_KEYWORDS: set[str] = {
    "wheelchair",
    "accessible",
    "accessibility",
    "disability",
    "disabled",
    "ramp",
    "elevator",
    "lift",
    "sensory",
    "quiet",
    "hearing",
    "loop",
    "braille",
    "service animal",
    "service dog",
    "guide dog",
    "ada",
    "mobility",
    "impairment",
    "assistive",
    "special needs",
    # Multilingual accessibility terms (Spanish, French, Arabic transliterations)
    "silla de ruedas",
    "accesible",
    "discapacidad",
    "fauteuil roulant",
    "handicapé",
    "accessibilité",
}

# General retrieval keywords mapped to zone fields
_ZONE_KEYWORD_MAP: dict[str, list[str]] = {
    "food": ["food_court", "food_kiosk", "halal_food", "international_cuisine"],
    "eat": ["food_court", "food_kiosk", "halal_food", "international_cuisine"],
    "restaurant": ["food_court"],
    "halal": ["halal_food", "halal_options"],
    "kosher": ["kosher_options"],
    "vegetarian": ["vegetarian_options"],
    "prayer": ["prayer_room"],
    "medical": ["first_aid", "emergency_medical"],
    "first aid": ["first_aid", "emergency_medical"],
    "hospital": ["first_aid"],
    "pharmacy": ["pharmacy"],
    "child": ["family_zone", "kids_play_area", "child_wristband_station"],
    "kids": ["family_zone", "kids_play_area"],
    "baby": ["baby_changing_station", "baby_food_station", "nursing_room"],
    "family": ["family_zone"],
    "vip": ["vip_lounge"],
    "lounge": ["vip_lounge"],
    "parking": ["parking"],
    "wifi": ["wifi"],
    "lost": ["lost_and_found"],
    "found": ["lost_and_found"],
    "gate": [],  # handled specially
    "queue": [],
    "wait": [],
    "crowd": [],
    "busy": [],
    "toilet": ["restrooms"],
    "restroom": ["restrooms"],
    "bathroom": ["restrooms"],
    "water": ["water_fountain", "water_refill_station"],
    "charge": ["charging_station"],
    "phone": ["charging_station"],
    "merchandise": ["merchandise_shop"],
    "shop": ["merchandise_shop"],
    "atm": ["atm"],
    "money": ["atm"],
    "smoking": ["smoking_areas"],
    "emergency": ["emergency_exits", "emergency_medical"],
    "exit": ["emergency_exits"],
    "transport": ["public_transport"],
    "bus": ["public_transport"],
    "train": ["public_transport"],
    "taxi": ["public_transport"],
}


class RAGEngine:
    """Retrieval-Augmented Generation engine for stadium fan queries.

    Loads the knowledge base once and provides retrieval + prompt building.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._knowledge: dict[str, Any] = {}
        self._zones: list[dict[str, Any]] = []
        self._general_info: dict[str, Any] = {}
        self._llm = llm_client or LLMClient()
        self._loaded = False

    def load_knowledge_base(self, path: str | None = None) -> None:
        """Load the stadium knowledge base from disk.

        Args:
            path: Override path to the JSON file (defaults to config value).
        """
        kb_path = Path(path or get_settings().knowledge_base_path)
        with kb_path.open(encoding="utf-8") as fh:
            self._knowledge = json.load(fh)
        self._zones = self._knowledge.get("zones", [])
        self._general_info = self._knowledge.get("general_info", {})
        self._loaded = True
        logger.info("Knowledge base loaded: %d zones.", len(self._zones))

    def _ensure_loaded(self) -> None:
        """Load the knowledge base if not already loaded."""
        if not self._loaded:
            self.load_knowledge_base()

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def retrieve(self, query: str) -> list[dict[str, Any]]:
        """Retrieve zone data relevant to the user's query.

        Uses keyword matching with accessibility boosting.  Returns a
        minimal subset of zone records (typically 1-3) to keep the LLM
        prompt small and focused.

        Args:
            query: The user's sanitized question.

        Returns:
            List of zone dicts relevant to the query.
        """
        self._ensure_loaded()
        query_lower = query.lower()

        is_accessibility_query = any(
            kw in query_lower for kw in _ACCESSIBILITY_KEYWORDS
        )

        # Score each zone
        scored: list[tuple[float, dict[str, Any]]] = []

        for zone in self._zones:
            score = self._score_zone(zone, query_lower, is_accessibility_query)
            if score > 0:
                scored.append((score, zone))

        # Sort descending by score, take top 3
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [zone for _, zone in scored[:3]]

        # If nothing matched, return all zones so the LLM has some context
        if not results:
            results = self._zones[:3]

        logger.debug(
            "Retrieved %d zones for query: '%s'",
            len(results),
            query[:50],
        )
        return results

    def _score_zone(
        self,
        zone: dict[str, Any],
        query_lower: str,
        is_accessibility_query: bool,
    ) -> float:
        """Score a zone for relevance to the query.

        Args:
            zone: Zone record from the knowledge base.
            query_lower: Lowercased user query.
            is_accessibility_query: Whether accessibility keywords were detected.

        Returns:
            Relevance score (higher = more relevant).
        """
        score = 0.0
        zone_text = json.dumps(zone).lower()

        # Direct zone name / ID match
        if zone.get("zone_id", "").lower() in query_lower:
            score += 5.0
        if zone.get("name", "").lower() in query_lower:
            score += 5.0

        # Gate mentions
        for gate in zone.get("gates", []):
            gate_name = gate.get("name", "").lower()
            if gate_name in query_lower:
                score += 4.0

        # Section mentions
        for section in zone.get("sections", []):
            if section.lower() in query_lower:
                score += 3.0

        # Keyword matching against amenities
        for keyword, amenity_keys in _ZONE_KEYWORD_MAP.items():
            if keyword in query_lower:
                for amenity_key in amenity_keys:
                    if amenity_key in zone_text:
                        score += 2.0

        # Accessibility boosting
        if is_accessibility_query:
            accessibility = zone.get("accessibility", {})
            if accessibility.get("wheelchair_accessible"):
                score += 3.0
            if accessibility.get("sensory_friendly"):
                score += 2.0
            if accessibility.get("hearing_loop"):
                score += 1.5
            if accessibility.get("quiet_room_nearby"):
                score += 1.5

        # Crowd / queue queries — boost zones with notable status
        if any(kw in query_lower for kw in ("crowd", "busy", "queue", "wait", "line")):
            status = zone.get("current_status", {})
            density = status.get("density_level", "")
            if density == "critical":
                score += 3.0
            elif density == "high":
                score += 2.0
            elif density == "medium":
                score += 1.0

        return score

    # ------------------------------------------------------------------
    # General info retrieval
    # ------------------------------------------------------------------

    def retrieve_general_info(self, query: str) -> dict[str, Any]:
        """Retrieve general stadium info relevant to the query.

        Args:
            query: The user's sanitized question.

        Returns:
            Dict of relevant general info entries.
        """
        self._ensure_loaded()
        query_lower = query.lower()
        relevant: dict[str, Any] = {}

        for key, value in self._general_info.items():
            if key.replace("_", " ") in query_lower or key in query_lower:
                relevant[key] = value
            # Also check if any word in the query matches the key
            for word in query_lower.split():
                if word in key:
                    relevant[key] = value

        return relevant

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def build_prompt(
        self,
        query: str,
        context_zones: list[dict[str, Any]],
        general_info: dict[str, Any] | None = None,
    ) -> tuple[str, str]:
        """Build the system prompt and user message for the LLM.

        Args:
            query: The user's original question.
            context_zones: Retrieved zone data (minimal subset).
            general_info: Optional relevant general info.

        Returns:
            Tuple of (system_prompt, user_message).
        """
        zone_context = json.dumps(context_zones, indent=2, ensure_ascii=False)
        general_context = ""
        if general_info:
            general_context = "\n\nGeneral Stadium Information:\n" + json.dumps(
                general_info, indent=2, ensure_ascii=False
            )

        system_prompt = (
            "You are FanFlow AI, the official multilingual fan assistant for the "
            "FIFA World Cup 2026 at MetLife Stadium, East Rutherford, New Jersey.\n\n"
            "CRITICAL RULES:\n"
            "1. AUTO-DETECT the language of the user's query and RESPOND IN THE SAME "
            "LANGUAGE.  Always start your response with a language tag like "
            "[LANG:en], [LANG:es], [LANG:ar], etc.\n"
            "2. Provide accurate, concise, helpful directions and information based "
            "ONLY on the stadium data provided below.\n"
            "3. For ACCESSIBILITY queries (wheelchair, sensory-friendly, hearing loop, "
            "quiet rooms, service animals, etc.), provide DETAILED and empathetic "
            "guidance — these are first-class features, not afterthoughts.\n"
            "4. If information is not in the data, say so honestly rather than guessing.\n"
            "5. Keep responses brief (2-4 sentences) unless the question needs detail.\n"
            "6. For crowd/queue questions, suggest the least crowded alternatives.\n"
            "7. Always mention the FIFA World Cup 2026 context when relevant.\n\n"
            "STADIUM DATA (relevant zones):\n"
            f"{zone_context}"
            f"{general_context}"
        )

        user_message = query

        return system_prompt, user_message

    # ------------------------------------------------------------------
    # Full RAG pipeline
    # ------------------------------------------------------------------

    async def answer(self, query: str) -> tuple[str, str, list[str]]:
        """Run the full RAG pipeline: retrieve → build prompt → generate.

        Args:
            query: The user's sanitized question.

        Returns:
            Tuple of (answer_text, detected_language, source_zone_ids).
        """
        context_zones = self.retrieve(query)
        general_info = self.retrieve_general_info(query)
        system_prompt, user_message = self.build_prompt(
            query, context_zones, general_info
        )

        raw_response = await self._llm.generate(system_prompt, user_message)

        # Extract language tag
        detected_language = "en"
        if raw_response.startswith("[LANG:"):
            end = raw_response.index("]")
            detected_language = raw_response[6:end].strip()
            answer_text = raw_response[end + 1 :].strip()
        else:
            answer_text = raw_response.strip()

        source_zone_ids = [z.get("zone_id", "") for z in context_zones]

        return answer_text, detected_language, source_zone_ids
