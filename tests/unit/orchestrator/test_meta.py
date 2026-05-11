from __future__ import annotations

from models._enums import OrchestratorRole
from models.state import State
from orchestrator.meta import meta_node


def test_meta_returns_no_revision():
    state = State()

    update = meta_node(state)

    assert "schedule_log" in update
    entry = update["schedule_log"][0]
    assert entry.decision == "no_revision"
    assert entry.role == OrchestratorRole.meta
    assert entry.author == "orchestrator.meta"


def test_meta_no_revision_regardless_of_state():
    # Even with rich blackboard state, MVP meta always returns no_revision.
    state = State(round_count=42, token_spent=123_456)
    update = meta_node(state)
    entry = update["schedule_log"][0]
    assert entry.decision == "no_revision"
