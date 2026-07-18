"""Alert engine for the Volunteer/Organizer Dashboard.

Generates mock stadium alerts from templates and uses the LLM to
rank and summarize them into prioritized action cards.
"""

from __future__ import annotations

import json
import logging
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.llm_client import LLMClient
from backend.models import (
    Alert,
    AlertCard,
    AlertOverview,
    AlertSeverity,
    AlertType,
)

logger = logging.getLogger(__name__)

# Placeholder values for template interpolation
_TEMPLATE_FILLS: dict[str, list[str]] = {
    "age": ["4", "6", "8", "10"],
    "clothing": [
        "red Brazil jersey and blue shorts",
        "white Argentina jersey",
        "yellow Colombia jersey and black cap",
        "green Mexico jersey with face paint",
    ],
    "occupants": ["2", "3", "4"],
    "minutes": ["10", "15", "20", "30"],
    "count": ["8", "12", "15", "20"],
    "queue_time": ["12", "15", "18", "22"],
}


class AlertEngine:
    """Generates, ranks, and summarizes stadium alerts.

    Uses mock templates for hackathon demo; designed to accept real
    alert feeds in production.
    """

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm = llm_client or LLMClient()
        self._templates: list[dict[str, Any]] = []
        self._zones: list[dict[str, Any]] = []
        self._active_alerts: list[Alert] = []

    def load_templates(
        self,
        alerts_path: str | None = None,
        knowledge_path: str | None = None,
    ) -> None:
        """Load alert templates and zone data.

        Args:
            alerts_path: Path to mock_alerts.json.
            knowledge_path: Path to stadium_knowledge.json.
        """
        settings = get_settings()
        a_path = Path(alerts_path or settings.alerts_path)
        k_path = Path(knowledge_path or settings.knowledge_base_path)

        with a_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        self._templates = data.get("alert_templates", [])

        with k_path.open(encoding="utf-8") as fh:
            kb = json.load(fh)
        self._zones = kb.get("zones", [])

        logger.info(
            "Alert engine loaded: %d templates, %d zones.",
            len(self._templates),
            len(self._zones),
        )

    def _fill_template(self, template: str, zone: dict[str, Any]) -> str:
        """Interpolate a template string with zone and random data.

        Args:
            template: Template string with {placeholder} markers.
            zone: Zone dict for context.

        Returns:
            Filled template string.
        """
        sections = zone.get("sections", ["A1"])
        gates = zone.get("gates", [{"name": "Gate 1"}])

        fills: dict[str, str] = {
            "zone": zone.get("name", "Unknown Zone"),
            "section": random.choice(sections),
            "gate": random.choice(gates).get("name", "Gate 1"),
        }

        # Fill optional placeholders from _TEMPLATE_FILLS
        for key, values in _TEMPLATE_FILLS.items():
            fills[key] = random.choice(values)

        result = template
        for key, value in fills.items():
            result = result.replace(f"{{{key}}}", value)

        return result

    def generate_mock_alerts(self, count: int = 5) -> list[Alert]:
        """Generate a batch of mock alerts from templates.

        Args:
            count: Number of alerts to generate (default 5).

        Returns:
            List of Alert model instances.
        """
        if not self._templates:
            self.load_templates()

        alerts: list[Alert] = []
        chosen_templates = random.choices(self._templates, k=count)

        for tmpl in chosen_templates:
            zone = random.choice(self._zones)
            sections = zone.get("sections", ["A1"])

            # Map template type to AlertType enum
            try:
                alert_type = AlertType(tmpl["type"])
            except ValueError:
                alert_type = AlertType.SECURITY

            alert = Alert(
                alert_id=str(uuid.uuid4())[:8],
                type=alert_type,
                severity=AlertSeverity(tmpl["severity"]),
                zone=zone.get("name", "Unknown"),
                section=random.choice(sections),
                description=self._fill_template(tmpl["description_template"], zone),
                recommended_action=self._fill_template(
                    tmpl.get("recommended_action", "Investigate immediately."),
                    zone,
                ),
                timestamp=datetime.now(timezone.utc),
            )
            alerts.append(alert)

        self._active_alerts = alerts
        logger.info("Generated %d mock alerts.", len(alerts))
        return alerts

    async def prioritize_alerts(
        self, alerts: list[Alert] | None = None
    ) -> AlertOverview:
        """Use the LLM to rank and summarize alerts into action cards.

        Args:
            alerts: List of alerts to prioritize (defaults to active).

        Returns:
            AlertOverview with ranked AlertCards.
        """
        if alerts is None:
            alerts = self._active_alerts

        if not alerts:
            return AlertOverview(
                cards=[],
                total_alerts=0,
                critical_count=0,
                updated_at=datetime.now(timezone.utc),
            )

        # Build compact alert summary for LLM
        alert_lines = []
        for i, alert in enumerate(alerts, 1):
            alert_lines.append(
                f"{i}. [{alert.type.value.upper()}] Severity {alert.severity.value}/5 "
                f"| {alert.zone} | {alert.description}"
            )
        alerts_text = "\n".join(alert_lines)

        system_prompt = (
            "You are FanFlow AI's alert management system for the "
            "FIFA World Cup 2026 at MetLife Stadium.\n"
            "You will receive a list of stadium alerts.  Your job:\n"
            "1. Rank them by urgency (life-threatening > safety > operational).\n"
            "2. For each alert, provide a 1-sentence action summary.\n"
            "3. Output a JSON array of objects with keys: "
            '"original_index" (1-based), "priority_rank" (1=most urgent), '
            '"summary" (1-sentence action).\n'
            "Return ONLY the JSON array, no other text."
        )

        try:
            raw = await self._llm.generate(
                system_prompt,
                alerts_text,
                use_cache=False,
                use_lite_model=True,
                caller_context="staff",
            )
            # Parse LLM JSON response
            # Strip markdown code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
            rankings: list[dict[str, Any]] = json.loads(cleaned)
        except Exception as exc:
            logger.warning("LLM ranking failed, using severity fallback: %s", exc)
            # Fallback: sort by severity descending
            rankings = [
                {
                    "original_index": i + 1,
                    "priority_rank": rank + 1,
                    "summary": alert.recommended_action,
                }
                for rank, (i, alert) in enumerate(
                    sorted(
                        enumerate(alerts),
                        key=lambda x: x[1].severity.value,
                        reverse=True,
                    )
                )
            ]

        # Build AlertCards
        cards: list[AlertCard] = []
        for ranking in rankings:
            idx = ranking.get("original_index", 1) - 1
            if 0 <= idx < len(alerts):
                cards.append(
                    AlertCard(
                        alert=alerts[idx],
                        priority_rank=ranking.get("priority_rank", idx + 1),
                        llm_summary=ranking.get(
                            "summary", alerts[idx].recommended_action
                        ),
                    )
                )

        cards.sort(key=lambda c: c.priority_rank)

        critical_count = sum(1 for a in alerts if a.severity.value >= 4)

        return AlertOverview(
            cards=cards,
            total_alerts=len(alerts),
            critical_count=critical_count,
            updated_at=datetime.now(timezone.utc),
        )
