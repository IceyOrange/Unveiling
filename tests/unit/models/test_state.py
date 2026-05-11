from __future__ import annotations

import pytest
from pydantic import ValidationError

from blackboard.reducers import merge_dicts, merge_lists
from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    NodeStatus,
    OrchestratorRole,
    Phase,
)
from models.blackboard import (
    ConclusionRecord,
    DebateRecord,
    EvidenceRecord,
    IssueTreeNode,
    LensRecord,
    PredictionRecord,
    ScheduleLogEntry,
)
from models.state import State


def test_state_instantiates_with_defaults():
    s = State()
    assert s.issue_tree == []
    assert s.hypothesis_zone == []
    assert s.evidence_zone == []
    assert s.debate_zone == []
    assert s.conclusion_zone == []
    assert s.schedule_log == []


def test_state_has_all_six_blackboard_zones():
    s = State()
    for zone in (
        "issue_tree",
        "hypothesis_zone",
        "evidence_zone",
        "debate_zone",
        "conclusion_zone",
        "schedule_log",
    ):
        assert hasattr(s, zone), f"State missing zone: {zone}"
        assert getattr(s, zone) == []


def test_state_scalar_defaults():
    s = State()
    assert s.token_spent == 0
    assert s.round_count == 0
    assert s.budget_ceiling == 500_000
    assert s.phase == Phase.inception
    assert s.degradation_count == 0
    assert s.user_question == ""
    assert s.next_agent == ""
    assert s.target_sub_question_id == ""


def test_state_dict_and_list_internal_defaults():
    s = State()
    assert s.attempt_counters == {}
    assert s.finding_density_window == []
    assert s.pending_tasks == []


def test_state_rejects_unknown_field():
    """model_config has extra='forbid'."""
    with pytest.raises(ValidationError):
        State(mystery_field=42)  # type: ignore[call-arg]


def test_state_rejects_invalid_phase():
    with pytest.raises(ValidationError):
        State(phase="middle")  # type: ignore[arg-type]


# ---------- Reducer simulation (LangGraph merge semantics) ----------


def _evidence(content: str = "x") -> EvidenceRecord:
    return EvidenceRecord(
        author="agent.search",
        source_lens_id="lens-1",
        source_lens_version="v0",
        sub_question_id="q-1",
        layer=EvidenceLayer.phenomenon,
        confidence=EvidenceConfidence.medium,
        is_unexpected=False,
        content=content,
    )


def test_merge_lists_simulates_parallel_branch_evidence_append():
    s = State()
    new_records = [_evidence("e1"), _evidence("e2")]
    merged = merge_lists(s.evidence_zone, new_records)
    assert len(merged) == 2
    assert merged[0].content == "e1"
    assert merged[1].content == "e2"
    # Original state untouched (invariant: don't mutate state)
    assert s.evidence_zone == []


def test_merge_lists_preserves_existing_evidence_then_appends():
    e0 = _evidence("e0")
    s = State(evidence_zone=[e0])
    merged = merge_lists(s.evidence_zone, [_evidence("e1")])
    assert [r.content for r in merged] == ["e0", "e1"]


def test_merge_lists_appends_issue_tree_node():
    s = State()
    node = IssueTreeNode(
        author="orchestrator.meta",
        content="q-root",
        node_status=NodeStatus.exploring,
    )
    merged = merge_lists(s.issue_tree, [node])
    assert len(merged) == 1
    assert merged[0].node_status == NodeStatus.exploring


def test_merge_lists_appends_hypothesis_zone_lens_and_prediction():
    s = State()
    lens = LensRecord(author="agent.lens_op", name="L0", rationale="r")
    pred = PredictionRecord(
        author="agent.prediction_check",
        claim="c",
        if_true_we_should_see="t",
        if_false_we_should_see="f",
        killer_evidence="k",
    )
    merged = merge_lists(s.hypothesis_zone, [lens, pred])
    assert len(merged) == 2


def test_merge_lists_appends_debate_zone():
    s = State()
    d = DebateRecord(author="agent.debate", round=1, question="?", response="!")
    merged = merge_lists(s.debate_zone, [d])
    assert len(merged) == 1


def test_merge_lists_appends_conclusion_zone():
    s = State()
    c = ConclusionRecord(
        author="agent.convergence",
        convergent_finding="cf",
        tension="t",
        boundary_condition="bc",
        unresolved="u",
        implication="i",
    )
    merged = merge_lists(s.conclusion_zone, [c])
    assert len(merged) == 1


def test_merge_lists_appends_schedule_log():
    s = State()
    log = ScheduleLogEntry(
        author="orchestrator.scheduler",
        role=OrchestratorRole.scheduler,
        decision="search_lateral",
        reason="kick off",
    )
    merged = merge_lists(s.schedule_log, [log])
    assert len(merged) == 1
    assert merged[0].role == OrchestratorRole.scheduler


def test_merge_dicts_attempt_counters():
    s = State()
    merged = merge_dicts(s.attempt_counters, {"q1": 1})
    assert merged == {"q1": 1}
    # Doesn't mutate
    assert s.attempt_counters == {}


def test_merge_dicts_attempt_counters_overwrite_and_extend():
    s = State(attempt_counters={"q1": 1, "q2": 2})
    merged = merge_dicts(s.attempt_counters, {"q2": 5, "q3": 1})
    assert merged == {"q1": 1, "q2": 5, "q3": 1}


def test_state_accepts_explicit_zone_values_at_construction():
    e = _evidence("seed")
    s = State(evidence_zone=[e], token_spent=42, phase=Phase.exploration)
    assert len(s.evidence_zone) == 1
    assert s.evidence_zone[0].content == "seed"
    assert s.token_spent == 42
    assert s.phase == Phase.exploration
