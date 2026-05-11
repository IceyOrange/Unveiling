from __future__ import annotations

from unittest.mock import patch

from agents.lens_op import lens_op_node
from models import (
    IssueTreeNode,
    LensRecord,
    State,
)
from models._enums import NodeStatus


def _seed() -> tuple[State, LensRecord, str]:
    driving = IssueTreeNode(
        author="inception",
        content="Driving Q",
        node_status=NodeStatus.untouched,
    )
    sub = IssueTreeNode(
        author="inception",
        content="A sub-question",
        parent_id=driving.id,
        node_status=NodeStatus.exploring,
    )
    lens = LensRecord(author="inception", name="Amazon", rationale="long-horizon strategy")
    state = State(
        user_question="Q",
        issue_tree=[driving, sub],
        hypothesis_zone=[lens],
        target_sub_question_id=sub.id,
    )
    return state, lens, sub.id


def test_lens_op_revision_creates_new_version():
    state, original_lens, _ = _seed()
    llm_output = (
        "Action: revise\n"
        "Reason: the analogy needs a tweak to account for new evidence.\n"
    )
    with patch("agents.lens_op.LLMClient") as mock_cls:
        mock_cls.return_value.chat.return_value = (llm_output, 120)
        update = lens_op_node(state)

    new_lenses = update.get("hypothesis_zone", [])
    assert len(new_lenses) == 1
    new = new_lenses[0]
    assert isinstance(new, LensRecord)
    assert new.parent_lens_id == original_lens.id
    assert new.id != original_lens.id
    # Original lens is unchanged (still in state)
    assert state.hypothesis_zone[0].id == original_lens.id
    assert state.hypothesis_zone[0].name == "Amazon"


def test_lens_op_keep_action_writes_nothing_to_hypothesis():
    state, _, _ = _seed()
    llm_output = (
        "Action: keep\n"
        "Reason: still illuminates the problem well.\n"
    )
    with patch("agents.lens_op.LLMClient") as mock_cls:
        mock_cls.return_value.chat.return_value = (llm_output, 90)
        update = lens_op_node(state)

    # No new lens record produced
    assert not update.get("hypothesis_zone")
    # But a schedule_log entry is written
    assert update["schedule_log"]
    assert update["schedule_log"][0].decision == "lens_keep"
