from __future__ import annotations

from unittest.mock import patch

from agents.debate import debate_node
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


def _seed(with_evidence: bool = True) -> tuple[State, str]:
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
    evidence = []
    if with_evidence:
        evidence.append(
            EvidenceRecord(
                author="search_lateral",
                source_lens_id=lens.id,
                source_lens_version="v0",
                sub_question_id=sub.id,
                layer=EvidenceLayer.phenomenon,
                confidence=EvidenceConfidence.medium,
                is_unexpected=False,
                content="An observable.",
            )
        )
    state = State(
        user_question="Q",
        issue_tree=[driving, sub],
        hypothesis_zone=[lens],
        evidence_zone=evidence,
        target_sub_question_id=sub.id,
    )
    return state, sub.id


def test_debate_writes_record_with_sub_question_id():
    state, sub_id = _seed(with_evidence=True)
    llm_output = (
        "Question: Is the sample biased toward survivors?\n"
        "Response: Yes, the evidence under-weights failed firms.\n"
    )
    with patch("agents.debate.LLMClient") as mock_cls:
        mock_cls.return_value.chat.return_value = (llm_output, 180)
        update = debate_node(state)

    debates = update.get("debate_zone", [])
    assert len(debates) == 1
    d = debates[0]
    assert isinstance(d, DebateRecord)
    assert d.sub_question_id == sub_id
    assert d.round == 1
    assert "biased" in d.question
    assert "failed firms" in d.response


def test_debate_handles_no_evidence_case():
    state, sub_id = _seed(with_evidence=False)
    with patch("agents.debate.LLMClient") as mock_cls:
        update = debate_node(state)
        mock_cls.assert_not_called()

    debates = update.get("debate_zone", [])
    assert len(debates) == 1
    d = debates[0]
    assert isinstance(d, DebateRecord)
    assert d.sub_question_id == sub_id
    assert d.round == 1
    # Placeholder content
    assert d.question
    assert d.response
