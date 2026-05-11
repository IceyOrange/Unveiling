from __future__ import annotations

from typing import Optional

from models._enums import NodeStatus, Phase
from models.blackboard import EvidenceRecord, IssueTreeNode
from models.state import State


def _latest_issue_tree(state: State) -> dict[str, IssueTreeNode]:
    """Build id -> latest node mapping from the append-only issue_tree list."""
    latest: dict[str, IssueTreeNode] = {}
    for node in state.issue_tree:
        latest[node.id] = node
    return latest


def pick_first_non_closed_subquestion(state: State) -> Optional[IssueTreeNode]:
    """Return the first leaf issue-tree node that is untouched or exploring.

    Fallback rule for Scheduler when LLM tie-breaker is unavailable.
    Only leaf nodes (sub-questions with no children) are scheduled for work.
    """
    latest = _latest_issue_tree(state)
    for node in latest.values():
        has_children = any(n.parent_id == node.id for n in latest.values())
        if not has_children and node.node_status in (NodeStatus.untouched, NodeStatus.exploring):
            return node
    return None


def all_leaves_closed_or_stuck(state: State) -> bool:
    """Check whether all leaf nodes in the issue tree are closed or stuck.

    A leaf is a node with no children. Empty tree = not converged.
    """
    if not state.issue_tree:
        return False

    latest = _latest_issue_tree(state)
    for node in latest.values():
        has_children = any(n.parent_id == node.id for n in latest.values())
        if not has_children:
            if node.node_status not in (NodeStatus.closed, NodeStatus.stuck):
                return False
    return True


def has_structure_or_mechanism_evidence(
    sub_question_id: str, evidence_zone: list[EvidenceRecord]
) -> bool:
    """Hard rule: a sub-question cannot be closed without structure or mechanism evidence."""
    for evidence in evidence_zone:
        if evidence.sub_question_id == sub_question_id:
            if evidence.layer in ("structure", "mechanism"):
                return True
    return False


def has_debate_round(sub_question_id: str, debate_zone: list) -> bool:
    """Hard rule: a sub-question should have at least one debate round before closing."""
    for debate in debate_zone:
        if getattr(debate, "sub_question_id", None) == sub_question_id:
            return True
    return False


def token_budget_exceeded(state: State) -> bool:
    return state.token_spent >= state.budget_ceiling


def get_phase_default_near_far_ratio(phase: Phase) -> float:
    """Return the default near/far search ratio for a lifecycle phase.

    0.0 = fully far, 1.0 = fully near.
    """
    if phase == Phase.inception:
        return 0.3  # far
    elif phase == Phase.exploration:
        return 0.5  # balanced
    elif phase == Phase.convergence:
        return 0.7  # near
    return 0.5
