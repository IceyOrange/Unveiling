from __future__ import annotations

from llm.degradation import DegradationLogger
from models._enums import OrchestratorRole
from models.blackboard import ScheduleLogEntry


def test_log_event_creates_schedule_log_entry():
    entry = DegradationLogger.log_event(
        role=OrchestratorRole.scheduler,
        scenario="json parse failed",
        fallback_action="raw_search_as_evidence",
    )

    assert isinstance(entry, ScheduleLogEntry)
    assert entry.degradation_flag is True
    assert entry.role == OrchestratorRole.scheduler
    assert entry.decision == "degradation"
    assert "json parse failed" in entry.reason
    assert "raw_search_as_evidence" in entry.reason
    assert entry.author == "orchestrator.scheduler"
    assert entry.status == "committed"


def test_log_event_for_judge_role():
    entry = DegradationLogger.log_event(
        role=OrchestratorRole.judge,
        scenario="LLM timeout after 3 retries",
        fallback_action="rule-based judge",
    )

    assert entry.role == OrchestratorRole.judge
    assert entry.author == "orchestrator.judge"
    assert entry.degradation_flag is True


def test_log_event_for_meta_role():
    entry = DegradationLogger.log_event(
        role=OrchestratorRole.meta,
        scenario="invalid response",
        fallback_action="skip meta review",
    )

    assert entry.role == OrchestratorRole.meta
    assert entry.author == "orchestrator.meta"


def test_log_event_accepts_agent_name_string():
    """Execution agents pass plain strings (e.g. 'inception'). Must not crash."""
    entry = DegradationLogger.log_event(
        role="inception",
        scenario="LLM JSON parse failed",
        fallback_action="fallback_to_minimal_tree",
    )

    assert isinstance(entry, ScheduleLogEntry)
    assert entry.degradation_flag is True
    assert entry.author == "orchestrator.inception"
    # Unknown agent names fall back to the scheduler role to satisfy the schema
    assert entry.role == OrchestratorRole.scheduler


def test_log_event_string_matching_enum_resolves_to_enum():
    """A string that happens to match an OrchestratorRole value resolves to that role."""
    entry = DegradationLogger.log_event(
        role="judge",
        scenario="ctx",
        fallback_action="rules",
    )

    assert entry.role == OrchestratorRole.judge
    assert entry.author == "orchestrator.judge"


def test_log_event_handles_all_execution_agent_names():
    """All 7 execution agents must be loggable without crash."""
    for name in (
        "inception",
        "convergence",
        "search",
        "deepdig",
        "lens_op",
        "debate",
        "prediction_check",
    ):
        entry = DegradationLogger.log_event(
            role=name,
            scenario="x",
            fallback_action="y",
        )
        assert entry.author == f"orchestrator.{name}"
        assert entry.degradation_flag is True
