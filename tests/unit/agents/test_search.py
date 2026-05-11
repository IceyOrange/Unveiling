from __future__ import annotations

import json
from unittest.mock import patch

from agents.search import search_lateral_node
from models import (
    EvidenceRecord,
    IssueTreeNode,
    LensRecord,
    ScheduleLogEntry,
    State,
)
from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    NodeStatus,
    OrchestratorRole,
)
from llm.client import LLMJSONError


def _seed_state_with_target() -> tuple[State, str]:
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
    lens = LensRecord(author="inception", name="L1", rationale="r")
    state = State(
        user_question="Q",
        issue_tree=[driving, sub],
        hypothesis_zone=[lens],
        target_sub_question_id=sub.id,
    )
    return state, sub.id


def test_search_lateral_writes_evidence():
    state, sub_id = _seed_state_with_target()
    fake_results = [
        {"title": "Result A", "snippet": "Snippet A.", "link": "u1"},
        {"title": "Result B", "snippet": "Snippet B.", "link": "u2"},
    ]
    llm_payload = {
        "evidence_list": [
            {
                "content": "Finding one.",
                "layer": "mechanism",
                "confidence": "strong",
                "is_unexpected": True,
            },
            {
                "content": "Finding two.",
                "layer": "structure",
                "confidence": "medium",
                "is_unexpected": False,
            },
        ]
    }
    with patch("agents.search.search") as mock_search, \
         patch("agents.search.LLMClient") as mock_cls:
        mock_search.return_value = fake_results
        mock_cls.return_value.chat.return_value = (json.dumps(llm_payload), 400)
        update = search_lateral_node(state)

    evs = update["evidence_zone"]
    assert len(evs) == 2
    for e in evs:
        assert isinstance(e, EvidenceRecord)
        # All six metadata fields present
        assert e.source_lens_id
        assert e.source_lens_version == "v0"
        assert e.sub_question_id == sub_id
        assert isinstance(e.layer, EvidenceLayer)
        assert isinstance(e.confidence, EvidenceConfidence)
        assert isinstance(e.is_unexpected, bool)
    # Verify mapping carried through
    assert evs[0].layer == EvidenceLayer.mechanism
    assert evs[0].confidence == EvidenceConfidence.strong
    assert evs[0].is_unexpected is True
    assert evs[1].layer == EvidenceLayer.structure


def test_search_skips_when_no_target():
    state = State(user_question="Q", target_sub_question_id="")
    with patch("agents.search.search") as mock_search, \
         patch("agents.search.LLMClient") as mock_cls:
        update = search_lateral_node(state)
        mock_search.assert_not_called()
        mock_cls.assert_not_called()

    assert "evidence_zone" not in update or not update.get("evidence_zone")
    sched = update["schedule_log"]
    assert len(sched) == 1
    assert sched[0].decision == "noop"


def test_search_degrades_on_llm_failure():
    state, _sub_id = _seed_state_with_target()
    fake_results = [{"title": "R", "snippet": "S", "link": "u"}]
    with patch("agents.search.search") as mock_search, \
         patch("agents.search.LLMClient") as mock_cls, \
         patch("agents.search.DegradationLogger") as mock_logger_cls:
        mock_search.return_value = fake_results
        mock_cls.return_value.chat.side_effect = LLMJSONError("boom")
        mock_logger_cls.return_value.log_event.return_value = ScheduleLogEntry(
            author="orchestrator.search_lateral",
            role=OrchestratorRole.scheduler,
            decision="degradation",
            reason="boom",
            degradation_flag=True,
        )
        update = search_lateral_node(state)

    # No evidence written when LLM extraction fails
    assert not update.get("evidence_zone")
    sched = update["schedule_log"]
    assert any(e.degradation_flag for e in sched)
