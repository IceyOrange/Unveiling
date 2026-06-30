from __future__ import annotations

import json

from unveiling.agents.search import (
    _build_records,
    _extract_cases_parallel,
    _MAX_EXTRACTION_PROMPT_CHARS,
    _reset_global_dedup,
)
from unveiling.models._enums import (
    EvidenceDomain,
    EvidenceEra,
    SearchDirection,
)
from unveiling.models.blackboard import (
    AbstractedEntity,
    AbstractedRelation,
    LensRecord,
)


def _lens() -> LensRecord:
    return LensRecord(author="t", name="lens", rationale="r")


def setup_function():
    """Reset global dedup before each test so cases don't leak across tests."""
    _reset_global_dedup()


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
    """A bad era/domain/distance should fall back to sensible defaults, not drop the case."""
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
    assert rec.era == EvidenceEra.industrial  # vertical fallback
    assert rec.domain is None
    assert rec.distance == 0.7  # vertical fallback


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
    assert records[0].era == EvidenceEra.contemporary  # lateral fallback
    assert records[0].domain is None
    assert records[0].distance == 0.5  # lateral fallback


def test_extract_cases_parallel_truncates_prompt_to_fit_budget(monkeypatch):
    """English provider (gpt-4o-mini on GitHub Models) rejects >8k-token requests.

    Regression: _extract_cases_parallel sent 18 full search snippets (~46k chars),
    causing a 413 tokens_limit_reached error, zero evidence, and a hidden scatter
    chart (no coordinate axes).
    """

    class FakeClient:
        def chat(self, messages, **kwargs):
            self.captured_prompt = messages[0]["content"]
            return json.dumps({"cases": []}), 0

    lens = LensRecord(author="t", name="lens", rationale="r")
    lens.entities = [AbstractedEntity(surface="AI", structural_role="new method")]
    lens.relationships = [
        AbstractedRelation(surface="AI replaces jobs", structural="replacement threat")
    ]

    # 20 enormous snippets would previously blow past the provider limit.
    big_results = [
        {"title": f"Result {i}", "snippet": "word " * 3000}
        for i in range(20)
    ]

    client = FakeClient()
    _extract_cases_parallel(client, lens, "lateral", big_results, [])

    assert len(client.captured_prompt) <= _MAX_EXTRACTION_PROMPT_CHARS
    # We should still keep at least the minimum number of results.
    assert "[1]" in client.captured_prompt
    assert "[4]" in client.captured_prompt
