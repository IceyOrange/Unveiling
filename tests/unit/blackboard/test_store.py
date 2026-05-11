from __future__ import annotations

from datetime import datetime, timezone

from blackboard.store import BlackboardStore
from models._enums import EvidenceConfidence, EvidenceLayer, NodeStatus
from models.blackboard import (
    BlackboardRecord,
    EvidenceRecord,
    IssueTreeNode,
    ScheduleLogEntry,
)
from models._enums import OrchestratorRole
from models.state import State


def _make_state() -> State:
    return State()


def test_store_index_builds():
    node = IssueTreeNode(author="test", content="Q1", node_status=NodeStatus.untouched)
    state = _make_state()
    state.issue_tree.append(node)
    store = BlackboardStore(state)
    assert store.get_record(node.id) == node
    assert store.get_zone("issue_tree") == [node]


def test_store_get_dependents():
    parent = BlackboardRecord(author="test")
    child = BlackboardRecord(author="test", references=[parent.id])
    state = _make_state()
    state.schedule_log.append(parent)  # any zone works
    state.schedule_log.append(child)
    store = BlackboardStore(state)
    assert store.get_dependents(parent.id) == [child.id]


def test_store_get_zone_for_record():
    ev = EvidenceRecord(
        author="test",
        source_lens_id="l1",
        source_lens_version="v0",
        sub_question_id="q1",
        layer=EvidenceLayer.phenomenon,
        confidence=EvidenceConfidence.medium,
        is_unexpected=False,
        content="finding",
    )
    state = _make_state()
    state.evidence_zone.append(ev)
    store = BlackboardStore(state)
    assert store.get_zone_for_record(ev.id) == "evidence_zone"


def test_store_append_helper():
    record = ScheduleLogEntry(
        author="test",
        role=OrchestratorRole.scheduler,
        decision="noop",
        reason="test",
    )
    update = BlackboardStore.append("schedule_log", record)
    assert update == {"schedule_log": [record]}


def test_store_retract_returns_updated_record():
    node = IssueTreeNode(author="test", content="Q1", node_status=NodeStatus.exploring)
    state = _make_state()
    state.issue_tree.append(node)
    store = BlackboardStore(state)
    update = store.retract(node.id, "wrong direction")
    updated = update["issue_tree"][0]
    assert updated.status == "retracted"
    assert updated.retraction_reason == "wrong direction"
    assert updated.id == node.id


def test_store_retract_unknown_id_returns_empty():
    store = BlackboardStore(State())
    assert store.retract("nonexistent", "reason") == {}
