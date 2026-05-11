from __future__ import annotations

from models._enums import EvidenceConfidence, EvidenceLayer, NodeStatus, Phase
from models.blackboard import (
    DebateRecord,
    EvidenceRecord,
    IssueTreeNode,
    ScheduleLogEntry,
)
from models._enums import OrchestratorRole
from models.state import State
from orchestrator.rules import (
    all_leaves_closed_or_stuck,
    get_phase_default_near_far_ratio,
    has_debate_round,
    has_structure_or_mechanism_evidence,
    pick_first_non_closed_subquestion,
    token_budget_exceeded,
)


def _make_node(content: str, status: NodeStatus, parent_id: str | None = None) -> IssueTreeNode:
    return IssueTreeNode(author="test", content=content, node_status=status, parent_id=parent_id)


def test_pick_first_non_closed_leaf():
    root = _make_node("Root", NodeStatus.exploring)
    child = _make_node("Child", NodeStatus.untouched, parent_id=root.id)
    state = State()
    state.issue_tree.extend([root, child])
    result = pick_first_non_closed_subquestion(state)
    # root has a child, so only child is a leaf
    assert result is not None
    assert result.id == child.id


def test_pick_first_skips_closed():
    open_node = _make_node("Open", NodeStatus.exploring)
    closed_node = _make_node("Closed", NodeStatus.closed)
    state = State()
    state.issue_tree.extend([open_node, closed_node])
    result = pick_first_non_closed_subquestion(state)
    assert result is not None
    assert result.id == open_node.id


def test_pick_first_none_when_all_closed():
    node = _make_node("Closed", NodeStatus.closed)
    state = State()
    state.issue_tree.append(node)
    assert pick_first_non_closed_subquestion(state) is None


def test_all_leaves_closed_or_stuck_true():
    leaf1 = _make_node("A", NodeStatus.closed)
    leaf2 = _make_node("B", NodeStatus.stuck)
    state = State()
    state.issue_tree.extend([leaf1, leaf2])
    assert all_leaves_closed_or_stuck(state) is True


def test_all_leaves_closed_or_stuck_false():
    leaf = _make_node("A", NodeStatus.exploring)
    state = State()
    state.issue_tree.append(leaf)
    assert all_leaves_closed_or_stuck(state) is False


def test_all_leaves_empty_tree():
    assert all_leaves_closed_or_stuck(State()) is False


def test_has_structure_or_mechanism_evidence_true():
    ev = EvidenceRecord(
        author="test",
        source_lens_id="l1",
        source_lens_version="v0",
        sub_question_id="q1",
        layer=EvidenceLayer.mechanism,
        confidence=EvidenceConfidence.medium,
        is_unexpected=False,
        content="m",
    )
    assert has_structure_or_mechanism_evidence("q1", [ev]) is True


def test_has_structure_or_mechanism_evidence_false():
    ev = EvidenceRecord(
        author="test",
        source_lens_id="l1",
        source_lens_version="v0",
        sub_question_id="q1",
        layer=EvidenceLayer.phenomenon,
        confidence=EvidenceConfidence.medium,
        is_unexpected=False,
        content="p",
    )
    assert has_structure_or_mechanism_evidence("q1", [ev]) is False


def test_has_debate_round_true():
    dr = DebateRecord(author="test", round=1, question="Q?", response="R.", sub_question_id="q1")
    assert has_debate_round("q1", [dr]) is True


def test_has_debate_round_false():
    dr = DebateRecord(author="test", round=1, question="Q?", response="R.", sub_question_id="q2")
    assert has_debate_round("q1", [dr]) is False


def test_token_budget_exceeded():
    state = State(token_spent=500_000, budget_ceiling=500_000)
    assert token_budget_exceeded(state) is True


def test_token_budget_not_exceeded():
    state = State(token_spent=100, budget_ceiling=500_000)
    assert token_budget_exceeded(state) is False


def test_phase_near_far_ratios():
    assert get_phase_default_near_far_ratio(Phase.inception) == 0.3
    assert get_phase_default_near_far_ratio(Phase.exploration) == 0.5
    assert get_phase_default_near_far_ratio(Phase.convergence) == 0.7
