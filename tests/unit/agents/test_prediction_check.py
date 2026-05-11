from __future__ import annotations

import json
from unittest.mock import patch

from agents.prediction_check import prediction_check_node
from models import (
    EvidenceRecord,
    IssueTreeNode,
    PredictionRecord,
    State,
)
from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    NodeStatus,
    PredictionStatus,
)


def _seed() -> tuple[State, PredictionRecord, str]:
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
    pred = PredictionRecord(
        author="inception",
        claim="Burn yields dominance",
        if_true_we_should_see="Share gains amid losses",
        if_false_we_should_see="Mass insolvency",
        killer_evidence="10-K showing growing share despite losses",
        prediction_status=PredictionStatus.pending,
    )
    ev = EvidenceRecord(
        author="search_lateral",
        source_lens_id="lens1",
        source_lens_version="v0",
        sub_question_id=sub.id,
        layer=EvidenceLayer.phenomenon,
        confidence=EvidenceConfidence.strong,
        is_unexpected=False,
        content="Amazon shed losses while growing share.",
    )
    state = State(
        user_question="Q",
        issue_tree=[driving, sub],
        hypothesis_zone=[pred],
        evidence_zone=[ev],
        target_sub_question_id=sub.id,
    )
    return state, pred, sub.id


def test_prediction_check_updates_status():
    state, pred, _ = _seed()
    fake_results = [
        {"title": "10-K Amazon", "snippet": "Negative FCF, rising share.", "link": "u"},
    ]
    payload = {
        "status": "supported",
        "reason": "Filings align with prediction.",
        "killer_found": True,
    }
    with patch("agents.prediction_check.search") as mock_search, \
         patch("agents.prediction_check.LLMClient") as mock_cls:
        mock_search.return_value = fake_results
        mock_cls.return_value.chat.return_value = (json.dumps(payload), 300)
        update = prediction_check_node(state)

    hyp = update.get("hypothesis_zone", [])
    assert len(hyp) == 1
    new = hyp[0]
    assert isinstance(new, PredictionRecord)
    assert new.prediction_status == PredictionStatus.supported
    # Same claim preserved (it's a model_copy update)
    assert new.claim == pred.claim
    assert new.killer_evidence == pred.killer_evidence
