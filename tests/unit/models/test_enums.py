from __future__ import annotations

from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    NodeStatus,
    OrchestratorRole,
    Phase,
    PredictionStatus,
    RecordStatus,
)


def test_record_status_members():
    assert RecordStatus.committed.value == "committed"
    assert RecordStatus.retracted.value == "retracted"


def test_node_status_members():
    assert set(m.value for m in NodeStatus) == {
        "untouched",
        "exploring",
        "closed",
        "stuck",
    }


def test_prediction_status_members():
    assert set(m.value for m in PredictionStatus) == {
        "pending",
        "supported",
        "refuted",
        "modified",
    }


def test_evidence_layer_members():
    assert set(m.value for m in EvidenceLayer) == {
        "phenomenon",
        "mechanism",
        "structure",
    }


def test_evidence_confidence_members():
    assert set(m.value for m in EvidenceConfidence) == {
        "strong",
        "medium",
        "weak",
        "unexpected",
    }


def test_phase_members():
    assert set(m.value for m in Phase) == {
        "inception",
        "exploration",
        "convergence",
    }


def test_orchestrator_role_members():
    assert set(m.value for m in OrchestratorRole) == {
        "scheduler",
        "judge",
        "meta",
    }
