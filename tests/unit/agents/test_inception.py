from __future__ import annotations

import json
from unittest.mock import patch

from agents.inception import inception_node
from models import (
    IssueTreeNode,
    LensRecord,
    PredictionRecord,
    ScheduleLogEntry,
    State,
)
from models._enums import OrchestratorRole, Phase, PredictionStatus
from llm.client import LLMJSONError


def _valid_inception_json() -> str:
    return json.dumps(
        {
            "driving_question": "Should AI companies burn cash for expansion?",
            "sub_questions": [
                "What are the unit economics?",
                "How does competition behave?",
                "What is the runway risk?",
            ],
            "lenses": [
                {"name": "Amazon", "rationale": "Long-horizon growth strategy."},
                {"name": "Dot-com", "rationale": "Bubble-era cash burn parallels."},
            ],
            "predictions": [
                {
                    "claim": "Sustained burn yields dominance",
                    "if_true_we_should_see": "Growing market share despite losses",
                    "if_false_we_should_see": "Mass insolvencies",
                    "killer_evidence": "10-K filings showing 3+ years of negative FCF with rising share",
                },
                {
                    "claim": "Predictions without killer evidence",
                    "if_true_we_should_see": "X",
                    "if_false_we_should_see": "Y",
                    "killer_evidence": "   ",  # empty after strip
                },
            ],
        }
    )


def test_inception_creates_issue_tree():
    state = State(user_question="Should AI companies burn cash for expansion?")
    with patch("agents.inception.LLMClient") as mock_cls:
        mock_cls.return_value.chat.return_value = (_valid_inception_json(), 500)
        update = inception_node(state)

    issue_tree = update["issue_tree"]
    assert any(n.parent_id is None for n in issue_tree), "must have a driving node"
    sub_qs = [n for n in issue_tree if n.parent_id is not None]
    assert len(sub_qs) == 3
    assert all(isinstance(n, IssueTreeNode) for n in issue_tree)

    hyp = update["hypothesis_zone"]
    lenses = [h for h in hyp if isinstance(h, LensRecord)]
    preds = [h for h in hyp if isinstance(h, PredictionRecord)]
    assert len(lenses) == 2
    # Only one prediction has valid killer_evidence
    assert len(preds) == 1
    assert preds[0].prediction_status == PredictionStatus.pending

    assert update["phase"] == Phase.exploration
    assert update["token_spent"] == 500


def test_inception_fallback_on_json_error():
    state = State(user_question="What is fair?")
    with patch("agents.inception.LLMClient") as mock_cls, \
         patch("agents.inception.DegradationLogger") as mock_logger_cls:
        mock_cls.return_value.chat.side_effect = LLMJSONError("boom")
        mock_logger_cls.return_value.log_event.return_value = ScheduleLogEntry(
            author="orchestrator.inception",
            role=OrchestratorRole.scheduler,
            decision="degradation",
            reason="boom",
            degradation_flag=True,
        )
        update = inception_node(state)

    # Fallback still produces a minimal issue tree
    assert "issue_tree" in update
    assert len(update["issue_tree"]) >= 1
    assert update["phase"] == Phase.exploration

    # A schedule_log entry indicating degradation
    sched = update["schedule_log"]
    assert any(e.degradation_flag for e in sched)


def test_inception_discards_predictions_without_killer_evidence():
    """All predictions returned but only those with non-empty killer_evidence kept."""
    raw = {
        "driving_question": "Q?",
        "sub_questions": ["s1"],
        "lenses": [{"name": "L", "rationale": "r"}],
        "predictions": [
            {
                "claim": "c1",
                "if_true_we_should_see": "t",
                "if_false_we_should_see": "f",
                "killer_evidence": "concrete observable",
            },
            {
                "claim": "c2",
                "if_true_we_should_see": "t",
                "if_false_we_should_see": "f",
                "killer_evidence": "",  # discarded
            },
            {
                "claim": "c3",
                "if_true_we_should_see": "t",
                "if_false_we_should_see": "f",
                "killer_evidence": "   ",  # discarded after strip
            },
        ],
    }
    state = State(user_question="Q")
    with patch("agents.inception.LLMClient") as mock_cls:
        mock_cls.return_value.chat.return_value = (json.dumps(raw), 100)
        update = inception_node(state)

    preds = [h for h in update["hypothesis_zone"] if isinstance(h, PredictionRecord)]
    assert len(preds) == 1
    assert preds[0].claim == "c1"
    assert preds[0].killer_evidence == "concrete observable"
