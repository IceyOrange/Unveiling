from __future__ import annotations

from unveiling.agents.search import _build_records
from unveiling.models._enums import (
    EvidenceDomain,
    EvidenceEra,
    SearchDirection,
)
from unveiling.models.blackboard import LensRecord


def _lens() -> LensRecord:
    return LensRecord(author="t", name="lens", rationale="r")


def test_build_records_coerces_string_era_and_domain():
    """LLM returns era/domain as plain strings (per case_extraction prompt).

    EvidenceRecord is strict, so the strings must be coerced to enum members.
    Regression: records were silently dropped, yielding 0 cases every round.
    """
    cases = [
        {
            "case_name": "工业革命中的工匠认同危机",
            "layer": "mechanism",
            "confidence": "strong",
            "is_unexpected": False,
            "content": "body",
            "era": "industrial",
            "domain": "economy",
            "distance": 0.6,
            "distance_reason": "same era, different domain",
        }
    ]
    records = _build_records(cases, _lens(), SearchDirection.lateral, "search_lateral")

    assert len(records) == 1
    rec = records[0]
    assert rec.era == EvidenceEra.industrial
    assert rec.domain == EvidenceDomain.economy
    assert rec.distance == 0.6


def test_build_records_handles_invalid_metadata_without_dropping_record():
    """A bad era/domain/distance should null that field, not drop the case."""
    cases = [
        {
            "case_name": "案例",
            "layer": "phenomenon",
            "confidence": "medium",
            "is_unexpected": False,
            "content": "body",
            "era": "renaissance",   # not a valid EvidenceEra
            "domain": "sports",     # not a valid EvidenceDomain
            "distance": 5,          # out of [0, 1] range
        }
    ]
    records = _build_records(cases, _lens(), SearchDirection.vertical, "search_vertical")

    assert len(records) == 1
    rec = records[0]
    assert rec.era is None
    assert rec.domain is None
    assert rec.distance is None


def test_build_records_handles_missing_metadata():
    cases = [
        {
            "case_name": "案例",
            "layer": "phenomenon",
            "confidence": "weak",
            "is_unexpected": True,
            "content": "body",
        }
    ]
    records = _build_records(cases, _lens(), SearchDirection.lateral, "search_lateral")

    assert len(records) == 1
    assert records[0].era is None
    assert records[0].domain is None
