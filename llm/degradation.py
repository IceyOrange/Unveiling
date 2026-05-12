from __future__ import annotations

from models.blackboard import ScheduleLogEntry


class DegradationLogger:
    """Produces ScheduleLogEntry records for degradation events.

    Every LLM failure must be logged to the schedule_log zone
    so the analysis-integrity summary can report it.
    """

    @staticmethod
    def log_event(
        agent_name: str,
        scenario: str,
        fallback_action: str,
    ) -> ScheduleLogEntry:
        """Create a ScheduleLogEntry describing a degradation event.

        Args:
            agent_name: Which agent failed (e.g. "inception", "search_lateral").
            scenario: What went wrong (e.g., "LLM timeout after 3 retries").
            fallback_action: What the system did instead.
        """
        return ScheduleLogEntry(
            author=agent_name,
            decision="degradation",
            reason=f"{scenario}. Fallback: {fallback_action}",
            degradation_flag=True,
        )
