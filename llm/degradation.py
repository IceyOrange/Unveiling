from __future__ import annotations

from models._enums import OrchestratorRole
from models.blackboard import ScheduleLogEntry


class DegradationLogger:
    """Produces ScheduleLogEntry records for Orchestrator degradation events.

    Every Orchestrator LLM failure must be logged to the schedule_log zone
    so the analysis-integrity summary can report it.
    """

    @staticmethod
    def log_event(
        role: OrchestratorRole | str,
        scenario: str,
        fallback_action: str,
    ) -> ScheduleLogEntry:
        """Create a ScheduleLogEntry describing a degradation event.

        Args:
            role: Which Orchestrator role or execution agent failed. Accepts
                either an ``OrchestratorRole`` enum value (scheduler/judge/meta)
                or a string identifying an execution agent (e.g. ``"inception"``,
                ``"search"``). Execution-agent failures are tagged against the
                scheduler role for schema purposes — the agent identity is
                preserved in ``author``.
            scenario: What went wrong (e.g., "LLM timeout after 3 retries").
            fallback_action: What the system did instead.

        Returns:
            A ScheduleLogEntry ready to be appended to the state.
        """
        if isinstance(role, OrchestratorRole):
            role_enum = role
            author_label = role.value
        else:
            # Agent-name string. Try to match an OrchestratorRole; otherwise
            # log under the scheduler role and keep the original name in author.
            try:
                role_enum = OrchestratorRole(role)
                author_label = role_enum.value
            except ValueError:
                role_enum = OrchestratorRole.scheduler
                author_label = str(role)

        return ScheduleLogEntry(
            author=f"orchestrator.{author_label}",
            role=role_enum,
            decision="degradation",
            reason=f"{scenario}. Fallback: {fallback_action}",
            degradation_flag=True,
        )
