"""Crowd density simulator with pluggable sensor feed design.

Provides a mock sensor feed that generates realistic crowd count fluctuations
per zone.  Structured so a real YOLOv8 computer-vision feed can replace the
mock feed without changing the rest of the application.

The simulator refreshes every N seconds (configurable) and maintains
current state in memory.
"""

from __future__ import annotations

import json
import logging
import random
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from backend.config import get_settings
from backend.llm_client import LLMClient
from backend.models import CrowdStatus, DensityLevel, GateStatus

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Abstract sensor feed (for future YOLOv8 integration)
# ---------------------------------------------------------------------------

class AbstractSensorFeed(ABC):
    """Base class for crowd sensor data sources.

    Implement this interface to plug in a real sensor feed (e.g., YOLOv8
    camera-based counting) instead of the mock simulator.
    """

    @abstractmethod
    def get_zone_counts(self) -> dict[str, int]:
        """Return current crowd count per zone_id.

        Returns:
            Mapping of zone_id → current person count.
        """
        ...


# ---------------------------------------------------------------------------
# Mock sensor feed
# ---------------------------------------------------------------------------

class MockSensorFeed(AbstractSensorFeed):
    """Simulated sensor feed using random walk around baseline values."""

    def __init__(self, zones: list[dict[str, Any]]) -> None:
        self._zones = zones
        self._current_counts: dict[str, int] = {}
        self._capacities: dict[str, int] = {}

        for zone in zones:
            zone_id = zone["zone_id"]
            capacity = zone["capacity"]
            initial = zone.get("current_status", {}).get("crowd_count", capacity // 2)
            self._current_counts[zone_id] = initial
            self._capacities[zone_id] = capacity

    def get_zone_counts(self) -> dict[str, int]:
        """Simulate a sensor update with random walk (±5-15%)."""
        for zone_id, count in self._current_counts.items():
            capacity = self._capacities[zone_id]
            # Random change: ±5% to ±15% of capacity
            max_delta = max(1, int(capacity * random.uniform(0.05, 0.15)))
            delta = random.randint(-max_delta, max_delta)
            new_count = max(0, min(capacity, count + delta))
            self._current_counts[zone_id] = new_count

        return dict(self._current_counts)


# ---------------------------------------------------------------------------
# Crowd simulator
# ---------------------------------------------------------------------------

class CrowdSimulator:
    """Manages crowd state across all zones and generates LLM guidance.

    Attributes:
        zones: List of zone definitions from the knowledge base.
        sensor_feed: The sensor data source (mock or real).
    """

    def __init__(
        self,
        sensor_feed: AbstractSensorFeed | None = None,
        llm_client: LLMClient | None = None,
        knowledge_base_path: str | None = None,
    ) -> None:
        kb_path = Path(knowledge_base_path or get_settings().knowledge_base_path)
        with kb_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        self._zones: list[dict[str, Any]] = data.get("zones", [])
        self._zone_lookup: dict[str, dict[str, Any]] = {
            z["zone_id"]: z for z in self._zones
        }

        self._sensor: AbstractSensorFeed = sensor_feed or MockSensorFeed(self._zones)
        self._llm = llm_client or LLMClient()
        self._last_update: float = 0.0
        self._current_statuses: list[CrowdStatus] = []

    # ------------------------------------------------------------------
    # Density classification
    # ------------------------------------------------------------------

    @staticmethod
    def classify_density(count: int, capacity: int) -> DensityLevel:
        """Classify crowd density based on occupancy percentage.

        Args:
            count: Current crowd count.
            capacity: Zone capacity.

        Returns:
            DensityLevel enum value.
        """
        if capacity <= 0:
            return DensityLevel.LOW
        pct = (count / capacity) * 100
        if pct >= 90:
            return DensityLevel.CRITICAL
        if pct >= 70:
            return DensityLevel.HIGH
        if pct >= 40:
            return DensityLevel.MEDIUM
        return DensityLevel.LOW

    # ------------------------------------------------------------------
    # Status snapshot
    # ------------------------------------------------------------------

    def update(self) -> list[CrowdStatus]:
        """Refresh crowd counts from the sensor feed and classify.

        Returns:
            List of CrowdStatus objects for all zones.
        """
        counts = self._sensor.get_zone_counts()
        statuses: list[CrowdStatus] = []

        for zone in self._zones:
            zone_id = zone["zone_id"]
            count = counts.get(zone_id, 0)
            capacity = zone["capacity"]
            density = self.classify_density(count, capacity)
            occupancy_pct = round((count / capacity) * 100, 1) if capacity > 0 else 0.0

            gates = [
                GateStatus(
                    gate_id=g["gate_id"],
                    name=g["name"],
                    queue_time_minutes=max(
                        1, g["queue_time_minutes"] + random.randint(-2, 3)
                    ),
                )
                for g in zone.get("gates", [])
            ]

            statuses.append(
                CrowdStatus(
                    zone_id=zone_id,
                    zone_name=zone["name"],
                    crowd_count=count,
                    capacity=capacity,
                    density_level=density,
                    occupancy_percent=occupancy_pct,
                    gates=gates,
                )
            )

        self._current_statuses = statuses
        self._last_update = time.time()
        return statuses

    def get_status(self) -> list[CrowdStatus]:
        """Return current crowd statuses, updating if stale.

        Returns:
            List of current CrowdStatus objects.
        """
        interval = get_settings().crowd_update_interval_seconds
        if time.time() - self._last_update >= interval:
            self.update()
        return self._current_statuses

    # ------------------------------------------------------------------
    # LLM guidance
    # ------------------------------------------------------------------

    async def get_guidance(self, statuses: list[CrowdStatus] | None = None) -> str:
        """Generate actionable crowd guidance text via the LLM.

        Args:
            statuses: Optional pre-computed statuses (defaults to current).

        Returns:
            LLM-generated guidance string.
        """
        if statuses is None:
            statuses = self.get_status()

        # Build compact summary for LLM (minimal context)
        zone_summary = []
        for s in statuses:
            gate_info = ", ".join(
                f"{g.name}: {g.queue_time_minutes}min wait" for g in s.gates
            )
            zone_summary.append(
                f"- {s.zone_name}: {s.crowd_count}/{s.capacity} "
                f"({s.density_level.value}) | Gates: {gate_info}"
            )

        status_text = "\n".join(zone_summary)

        system_prompt = (
            "You are FanFlow AI's crowd management system for the "
            "FIFA World Cup 2026 at MetLife Stadium.\n"
            "Generate 2-4 short, actionable guidance sentences for fans based on "
            "the current crowd data below.\n"
            "Focus on: which areas to avoid, best alternate routes/gates, "
            "and estimated time savings.\n"
            "Format: bullet points, concise, direct.\n"
            "Example: '• Gate 3 congested (12min wait) — use Gate 5 instead, saves ~10 min.'"
        )

        user_message = f"Current stadium crowd status:\n{status_text}"

        return await self._llm.generate(
            system_prompt,
            user_message,
            use_cache=False,
            use_lite_model=True,
            caller_context="staff",
        )
