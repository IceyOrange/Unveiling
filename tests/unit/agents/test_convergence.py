from __future__ import annotations

import json
from unittest.mock import patch

from agents.convergence import convergence_node
from models import (
    ConclusionRecord,
    EvidenceRecord,
    IssueTreeNode,
    ScheduleLogEntry,
    State,
)
from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    NodeStatus,
    OrchestratorRole,
    Phase,
)
from llm.client import LLMJSONError


def _seed_state() -> State:
    driving = IssueTreeNode(
        author="inception",
        content="Driving Q",
        node_status=NodeStatus.untouched,
    )
    sub = IssueTreeNode(
        author="inception",
        content="A sub-question",
        parent_id=driving.id,
        node_status=NodeStatus.closed,
    )
    ev = EvidenceRecord(
        author="search_lateral",
        source_lens_id="lens1",
        source_lens_version="v0",
        sub_question_id=sub.id,
        layer=EvidenceLayer.mechanism,
        confidence=EvidenceConfidence.strong,
        is_unexpected=False,
        content="A mechanism finding.",
    )
    return State(
        user_question="Q",
        issue_tree=[driving, sub],
        evidence_zone=[ev],
    )


def test_convergence_writes_tension_record():
    state = _seed_state()
    payload = {
        "core_conclusion": "Conclusion.",
        "tension": "Growth versus survival.",
        "boundary_condition": "Holds when runway > 18 months.",
        "convergent_finding": "Burn correlates with share gains.",
        "unresolved": "Long-run profitability.",
        "implication": "Be selective in betting.",
    }
    with patch("agents.convergence.LLMClient") as mock_cls:
        mock_cls.return_value.chat.return_value = (json.dumps(payload), 600)
        update = convergence_node(state)

    conclusions = update["conclusion_zone"]
    assert len(conclusions) == 1
    c = conclusions[0]
    assert isinstance(c, ConclusionRecord)
    assert c.tension == "Growth versus survival."
    assert c.boundary_condition.startswith("Holds when")
    assert c.unresolved == "Long-run profitability."
    assert update["phase"] == Phase.convergence


def test_convergence_fallback_on_json_error():
    """Fallback path: when LLM raises LLMJSONError, a placeholder ConclusionRecord
    is written and a degradation entry is logged. Exercises the real
    ``_fallback_conclusion`` so a future bug (e.g. invalid kwarg on
    ``ConclusionRecord``) is caught here.
    """
    state = _seed_state()
    with patch("agents.convergence.LLMClient") as mock_cls:
        mock_cls.return_value.chat.side_effect = LLMJSONError("bad json")
        update = convergence_node(state)

    # Placeholder conclusion still written
    assert "conclusion_zone" in update
    assert len(update["conclusion_zone"]) == 1
    c = update["conclusion_zone"][0]
    assert isinstance(c, ConclusionRecord)
    assert c.tension  # non-empty placeholder
    assert update["phase"] == Phase.convergence

    sched = update["schedule_log"]
    assert any(e.degradation_flag for e in sched)
    # The agent passes role="convergence" (a string); the logger must accept it
    # and tag the author accordingly.
    assert any(e.author == "orchestrator.convergence" for e in sched)
