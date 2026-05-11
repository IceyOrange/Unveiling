from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    NodeStatus,
    OrchestratorRole,
    PredictionStatus,
)
from models.blackboard import (
    BlackboardRecord,
    ConclusionRecord,
    DebateRecord,
    EvidenceRecord,
    IssueTreeNode,
    LensRecord,
    PredictionRecord,
    ScheduleLogEntry,
)


# ---------- BlackboardRecord (Invariant #3) ----------


def test_blackboard_record_default_status_is_committed():
    rec = BlackboardRecord(author="agent.search")
    assert rec.status == "committed"


def test_blackboard_record_accepts_retracted_status():
    rec = BlackboardRecord(author="agent.search", status="retracted")
    assert rec.status == "retracted"


def test_blackboard_record_rejects_draft_status():
    """Invariant #3: no draft state exists across the system."""
    with pytest.raises(ValidationError):
        BlackboardRecord(author="agent.search", status="draft")


def test_blackboard_record_rejects_arbitrary_status():
    with pytest.raises(ValidationError):
        BlackboardRecord(author="agent.search", status="in_progress")


def test_blackboard_record_auto_generates_id():
    rec_a = BlackboardRecord(author="x")
    rec_b = BlackboardRecord(author="x")
    assert isinstance(rec_a.id, str)
    assert len(rec_a.id) > 0
    assert rec_a.id != rec_b.id


def test_blackboard_record_auto_generates_timestamp():
    rec = BlackboardRecord(author="x")
    assert isinstance(rec.timestamp, datetime)


def test_blackboard_record_author_required():
    with pytest.raises(ValidationError):
        BlackboardRecord()  # type: ignore[call-arg]


def test_blackboard_record_extra_field_forbidden():
    """model_config has extra='forbid'."""
    with pytest.raises(ValidationError):
        BlackboardRecord(author="x", unknown_field="boom")  # type: ignore[call-arg]


def test_blackboard_record_default_references_empty_list():
    rec = BlackboardRecord(author="x")
    assert rec.references == []


def test_blackboard_record_default_retraction_reason_none():
    rec = BlackboardRecord(author="x")
    assert rec.retraction_reason is None


# ---------- IssueTreeNode ----------


def test_issue_tree_node_default_node_status_is_untouched():
    node = IssueTreeNode(author="orchestrator.meta", content="root question")
    assert node.node_status == NodeStatus.untouched


def test_issue_tree_node_rejects_invalid_node_status():
    with pytest.raises(ValidationError):
        IssueTreeNode(
            author="orchestrator.meta",
            content="root",
            node_status="frozen",  # type: ignore[arg-type]
        )


def test_issue_tree_node_accepts_valid_node_statuses():
    for status in (
        NodeStatus.untouched,
        NodeStatus.exploring,
        NodeStatus.closed,
        NodeStatus.stuck,
    ):
        node = IssueTreeNode(author="x", content="c", node_status=status)
        assert node.node_status == status


def test_issue_tree_node_content_required():
    with pytest.raises(ValidationError):
        IssueTreeNode(author="x")  # type: ignore[call-arg]


def test_issue_tree_node_extra_field_forbidden():
    with pytest.raises(ValidationError):
        IssueTreeNode(
            author="x",
            content="c",
            mystery="?",  # type: ignore[call-arg]
        )


# ---------- LensRecord (Invariant #6) ----------


def test_lens_record_root_has_no_parent():
    root = LensRecord(author="agent.lens_op", name="L0", rationale="initial")
    assert root.parent_lens_id is None


def test_lens_record_version_chain_constructible():
    """Invariant #6: lens evolution = add new version with parent_lens_id pointing
    to previous record's id. The chain must be constructible by passing the
    previous record's id."""
    v0 = LensRecord(author="agent.lens_op", name="L0", rationale="initial")
    v1 = LensRecord(
        author="agent.lens_op",
        name="L1",
        rationale="refined",
        parent_lens_id=v0.id,
    )
    v2 = LensRecord(
        author="agent.lens_op",
        name="L2",
        rationale="split",
        parent_lens_id=v1.id,
    )
    assert v1.parent_lens_id == v0.id
    assert v2.parent_lens_id == v1.id
    assert v0.parent_lens_id is None


def test_lens_record_requires_name_and_rationale():
    with pytest.raises(ValidationError):
        LensRecord(author="x")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        LensRecord(author="x", name="only-name")  # type: ignore[call-arg]


# ---------- PredictionRecord (Invariant #7) ----------


def _valid_prediction_kwargs():
    return dict(
        author="agent.prediction_check",
        claim="X will rise.",
        if_true_we_should_see="A",
        if_false_we_should_see="B",
        killer_evidence="C",
    )


def test_prediction_record_constructs_with_full_fields():
    p = PredictionRecord(**_valid_prediction_kwargs())
    assert p.claim == "X will rise."
    assert p.killer_evidence == "C"


def test_prediction_record_default_status_pending():
    """Invariant #7: default prediction_status is pending."""
    p = PredictionRecord(**_valid_prediction_kwargs())
    assert p.prediction_status == PredictionStatus.pending


def test_prediction_record_requires_killer_evidence():
    """Invariant #7: a prediction without killer_evidence is invalid."""
    kwargs = _valid_prediction_kwargs()
    del kwargs["killer_evidence"]
    with pytest.raises(ValidationError):
        PredictionRecord(**kwargs)


def test_prediction_record_requires_claim():
    kwargs = _valid_prediction_kwargs()
    del kwargs["claim"]
    with pytest.raises(ValidationError):
        PredictionRecord(**kwargs)


def test_prediction_record_requires_if_true_and_if_false_branches():
    base = _valid_prediction_kwargs()
    k1 = dict(base)
    del k1["if_true_we_should_see"]
    with pytest.raises(ValidationError):
        PredictionRecord(**k1)
    k2 = dict(base)
    del k2["if_false_we_should_see"]
    with pytest.raises(ValidationError):
        PredictionRecord(**k2)


def test_prediction_record_accepts_all_status_values():
    for status in PredictionStatus:
        p = PredictionRecord(**_valid_prediction_kwargs(), prediction_status=status)
        assert p.prediction_status == status


# ---------- EvidenceRecord (Invariant #5) ----------


def _valid_evidence_kwargs():
    return dict(
        author="agent.search",
        source_lens_id="lens-1",
        source_lens_version="v0",
        sub_question_id="q-1",
        layer=EvidenceLayer.mechanism,
        confidence=EvidenceConfidence.medium,
        is_unexpected=False,
        content="An observation.",
    )


def test_evidence_record_with_all_metadata_succeeds():
    e = EvidenceRecord(**_valid_evidence_kwargs())
    assert e.source_lens_id == "lens-1"
    assert e.source_lens_version == "v0"
    assert e.sub_question_id == "q-1"
    assert e.layer == EvidenceLayer.mechanism
    assert e.confidence == EvidenceConfidence.medium
    assert e.is_unexpected is False


@pytest.mark.parametrize(
    "missing_field",
    [
        "source_lens_id",
        "source_lens_version",
        "sub_question_id",
        "layer",
        "confidence",
        "is_unexpected",
    ],
)
def test_evidence_record_rejects_missing_metadata(missing_field):
    """Invariant #5: every evidence record must carry the 6 metadata fields."""
    kwargs = _valid_evidence_kwargs()
    del kwargs[missing_field]
    with pytest.raises(ValidationError):
        EvidenceRecord(**kwargs)


def test_evidence_record_rejects_invalid_layer():
    kwargs = _valid_evidence_kwargs()
    kwargs["layer"] = "metaphysics"  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        EvidenceRecord(**kwargs)


def test_evidence_record_rejects_invalid_confidence():
    kwargs = _valid_evidence_kwargs()
    kwargs["confidence"] = "very-strong"  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        EvidenceRecord(**kwargs)


def test_evidence_record_extra_field_forbidden():
    kwargs = _valid_evidence_kwargs()
    kwargs["extra"] = "no"  # type: ignore[index]
    with pytest.raises(ValidationError):
        EvidenceRecord(**kwargs)


# ---------- DebateRecord ----------


def test_debate_record_minimal_construction():
    d = DebateRecord(author="agent.debate", round=1, question="q?", response="r.")
    assert d.round == 1
    assert d.question == "q?"
    assert d.response == "r."
    assert d.sub_question_id is None
    assert d.cross_layer_failure_note is None


def test_debate_record_accepts_optional_sub_question_and_failure_note():
    d = DebateRecord(
        author="agent.debate",
        round=2,
        question="q?",
        response="r.",
        sub_question_id="q-7",
        cross_layer_failure_note="止于现象层",
    )
    assert d.sub_question_id == "q-7"
    assert d.cross_layer_failure_note == "止于现象层"


def test_debate_record_requires_round_question_response():
    with pytest.raises(ValidationError):
        DebateRecord(author="x", question="?", response="!")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        DebateRecord(author="x", round=1, response="!")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        DebateRecord(author="x", round=1, question="?")  # type: ignore[call-arg]


# ---------- ConclusionRecord ----------


def test_conclusion_record_construction():
    c = ConclusionRecord(
        author="agent.convergence",
        convergent_finding="cf",
        tension="t",
        boundary_condition="bc",
        unresolved="u",
        implication="i",
    )
    assert c.sub_question_id is None
    assert c.convergent_finding == "cf"
    assert c.tension == "t"


def test_conclusion_record_requires_all_tension_fields():
    base = dict(
        author="x",
        convergent_finding="cf",
        tension="t",
        boundary_condition="bc",
        unresolved="u",
        implication="i",
    )
    for field in ("convergent_finding", "tension", "boundary_condition", "unresolved", "implication"):
        kw = dict(base)
        del kw[field]
        with pytest.raises(ValidationError):
            ConclusionRecord(**kw)


# ---------- ScheduleLogEntry ----------


def test_schedule_log_entry_default_degradation_flag_false():
    log = ScheduleLogEntry(
        author="orchestrator.scheduler",
        role=OrchestratorRole.scheduler,
        decision="search_lateral",
        reason="q-1 needs widening",
    )
    assert log.degradation_flag is False


def test_schedule_log_entry_accepts_degradation_event():
    log = ScheduleLogEntry(
        author="orchestrator.judge",
        role=OrchestratorRole.judge,
        decision="fallback-rule",
        reason="LLM timeout",
        degradation_flag=True,
    )
    assert log.degradation_flag is True


def test_schedule_log_entry_rejects_invalid_role():
    with pytest.raises(ValidationError):
        ScheduleLogEntry(
            author="x",
            role="overseer",  # type: ignore[arg-type]
            decision="d",
            reason="r",
        )
