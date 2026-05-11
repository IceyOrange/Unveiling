from __future__ import annotations

from typing import Optional

from models.blackboard import BlackboardRecord
from models.state import State


class BlackboardStore:
    """Read-only snapshot index over a State instance.

    Provides O(1) record lookup and reference tracking.
    After each LangGraph state update, create a fresh Store.
    """

    def __init__(self, state: State):
        self.state = state
        self._record_index: dict[str, BlackboardRecord] = {}
        self._ref_index: dict[str, list[str]] = {}  # referenced_id -> [referrer_ids]
        self._zone_map: dict[str, str] = {}  # record_id -> zone_name
        self._build_index()

    def _build_index(self) -> None:
        zones = [
            "issue_tree",
            "hypothesis_zone",
            "evidence_zone",
            "debate_zone",
            "conclusion_zone",
            "schedule_log",
        ]
        for zone_name in zones:
            zone = getattr(self.state, zone_name)
            for record in zone:
                self._record_index[record.id] = record
                self._zone_map[record.id] = zone_name
                for ref in record.references:
                    self._ref_index.setdefault(ref, []).append(record.id)

    def get_record(self, record_id: str) -> Optional[BlackboardRecord]:
        return self._record_index.get(record_id)

    def get_zone(self, zone_name: str) -> list[BlackboardRecord]:
        return list(getattr(self.state, zone_name, []))

    def get_dependents(self, record_id: str) -> list[str]:
        """Return IDs of records that directly reference record_id."""
        return list(self._ref_index.get(record_id, []))

    def get_zone_for_record(self, record_id: str) -> Optional[str]:
        return self._zone_map.get(record_id)

    @staticmethod
    def append(zone_name: str, record: BlackboardRecord) -> dict:
        """Return a state update dict that appends a single record to a zone."""
        return {zone_name: [record]}

    def retract(self, record_id: str, reason: str) -> dict:
        """Return a state update dict that marks a record as retracted.

        Creates a new record instance with status="retracted".
        The list reducer appends it; the index will point to the latest version.
        """
        record = self._record_index.get(record_id)
        if record is None:
            return {}

        zone_name = self._zone_map.get(record_id)
        if zone_name is None:
            return {}

        updated = record.model_copy(
            update={"status": "retracted", "retraction_reason": reason}
        )
        return {zone_name: [updated]}
