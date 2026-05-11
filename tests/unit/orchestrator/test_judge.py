from __future__ import annotations

from models._enums import EvidenceConfidence, EvidenceLayer, NodeStatus
from models.blackboard import (
    DebateRecord,
    EvidenceRecord,
    IssueTreeNode,
)
from models.state import State
from orchestrator.judge import judge_node


def _evidence(
    sub_question_id: str, layer: EvidenceLayer = EvidenceLayer.phenomenon
) -> EvidenceRecord:
    return EvidenceRecord(
        author="test",
        source_lens_id="l1",
        source_lens_version="v0",
        sub_question_id=sub_question_id,
        layer=layer,
        confidence=EvidenceConfidence.medium,
        is_unexpected=False,
        content="e",
    )


def test_judge_no_target_returns_empty():
    state = State(target_sub_question_id="")
    assert judge_node(state) == {}


def test_judge_unknown_target_returns_empty():
    # target_sub_question_id is set, but no matching node in issue_tree.
    state = State(target_sub_question_id="missing-id")
    assert judge_node(state) == {}


def test_judge_keeps_exploring_without_structure_evidence():
    target = IssueTreeNode(
        author="test", content="Q", node_status=NodeStatus.exploring
    )
    state = State(target_sub_question_id=target.id)
    state.issue_tree.append(target)
    # Only phenomenon-layer evidence — fails the structure/mechanism hard rule.
    state.evidence_zone.append(_evidence(target.id, EvidenceLayer.phenomenon))

    update = judge_node(state)

    assert "issue_tree" in update
    promoted = update["issue_tree"][0]
    assert promoted.id == target.id
    assert promoted.node_status == NodeStatus.exploring
    log = update["schedule_log"][0]
    assert log.decision == "keep_exploring"
    assert "no structure or mechanism evidence" in log.reason


def test_judge_keeps_exploring_without_debate():
    target = IssueTreeNode(
        author="test", content="Q", node_status=NodeStatus.exploring
    )
    state = State(target_sub_question_id=target.id)
    state.issue_tree.append(target)
    state.evidence_zone.append(_evidence(target.id, EvidenceLayer.structure))
    # No DebateRecord -> fails the debate hard rule.

    update = judge_node(state)

    assert "issue_tree" in update
    promoted = update["issue_tree"][0]
    assert promoted.node_status == NodeStatus.exploring
    log = update["schedule_log"][0]
    assert log.decision == "keep_exploring"
    assert "no debate round" in log.reason


def test_judge_closes_when_both_conditions_met():
    target = IssueTreeNode(
        author="test", content="Q", node_status=NodeStatus.exploring
    )
    state = State(target_sub_question_id=target.id)
    state.issue_tree.append(target)
    state.evidence_zone.append(_evidence(target.id, EvidenceLayer.mechanism))
    state.debate_zone.append(
        DebateRecord(
            author="test",
            round=1,
            question="why?",
            response="because.",
            sub_question_id=target.id,
        )
    )

    update = judge_node(state)

    assert "issue_tree" in update
    closed = update["issue_tree"][0]
    assert closed.id == target.id
    assert closed.node_status == NodeStatus.closed
    log = update["schedule_log"][0]
    assert log.decision == "close"
