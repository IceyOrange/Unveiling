from __future__ import annotations

from unittest.mock import patch

from agents.deepdig import deepdig_node
from models import (
    DebateRecord,
    EvidenceRecord,
    IssueTreeNode,
    LensRecord,
    State,
)
from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    NodeStatus,
)


def _seed(deepest_layer: EvidenceLayer = EvidenceLayer.phenomenon) -> tuple[State, str]:
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
    lens = LensRecord(author="inception", name="L", rationale="r")
    ev = EvidenceRecord(
        author="search_lateral",
        source_lens_id=lens.id,
        source_lens_version="v0",
        sub_question_id=sub.id,
        layer=deepest_layer,
        confidence=EvidenceConfidence.medium,
        is_unexpected=False,
        content="An existing finding.",
    )
    state = State(
        user_question="Q",
        issue_tree=[driving, sub],
        hypothesis_zone=[lens],
        evidence_zone=[ev],
        target_sub_question_id=sub.id,
    )
    return state, sub.id


def test_deepdig_records_finding():
    state, sub_id = _seed(EvidenceLayer.phenomenon)
    llm_output = (
        "Finding: A causal mechanism we can name.\n"
        "Layer: mechanism\n"
        "Confidence: strong\n"
        "Unexpected: true\n"
    )
    with patch("agents.deepdig.LLMClient") as mock_cls:
        mock_cls.return_value.chat.return_value = (llm_output, 200)
        update = deepdig_node(state)

    evs = update.get("evidence_zone", [])
    assert len(evs) == 1
    new = evs[0]
    assert isinstance(new, EvidenceRecord)
    assert new.layer == EvidenceLayer.mechanism
    assert new.confidence == EvidenceConfidence.strong
    assert new.is_unexpected is True
    assert new.sub_question_id == sub_id
    assert "causal" in new.content


def test_deepdig_writes_failure_note_when_cannot_progress():
    state, sub_id = _seed(EvidenceLayer.mechanism)
    llm_output = (
        "Finding: 止于 mechanism 层 — unable to find deeper pattern\n"
        "Layer: mechanism\n"
        "Confidence: weak\n"
        "Unexpected: false\n"
    )
    with patch("agents.deepdig.LLMClient") as mock_cls:
        mock_cls.return_value.chat.return_value = (llm_output, 150)
        update = deepdig_node(state)

    # No new evidence written
    assert not update.get("evidence_zone")
    debates = update.get("debate_zone", [])
    assert len(debates) == 1
    d = debates[0]
    assert isinstance(d, DebateRecord)
    assert d.sub_question_id == sub_id
    assert d.cross_layer_failure_note is not None
    assert "止于" in d.cross_layer_failure_note
