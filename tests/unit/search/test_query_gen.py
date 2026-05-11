from __future__ import annotations

from search.query_gen import build_queries


LENS = {"name": "Amazon", "rationale": "Early growth"}
SUB_Q = "Should AI companies burn cash?"


def test_build_queries_near_mode_returns_non_empty_strings():
    queries = build_queries(LENS, SUB_Q, mode="near")
    assert isinstance(queries, list)
    assert len(queries) >= 1
    for q in queries:
        assert isinstance(q, str)
        assert q.strip() != ""


def test_build_queries_far_mode_returns_non_empty_strings():
    queries = build_queries(LENS, SUB_Q, mode="far")
    assert isinstance(queries, list)
    assert len(queries) >= 1
    for q in queries:
        assert isinstance(q, str)
        assert q.strip() != ""


def test_build_queries_killer_evidence_mode_returns_non_empty_strings():
    queries = build_queries(LENS, SUB_Q, mode="killer_evidence")
    assert isinstance(queries, list)
    assert len(queries) >= 1
    for q in queries:
        assert isinstance(q, str)
        assert q.strip() != ""


def test_far_queries_differ_from_near_queries():
    near = build_queries(LENS, SUB_Q, mode="near")
    far = build_queries(LENS, SUB_Q, mode="far")

    # Sets should be disjoint to catch regressions where modes collapse.
    assert set(near).isdisjoint(set(far))


def test_killer_evidence_differs_from_near_and_far():
    near = build_queries(LENS, SUB_Q, mode="near")
    far = build_queries(LENS, SUB_Q, mode="far")
    killer = build_queries(LENS, SUB_Q, mode="killer_evidence")

    assert set(killer).isdisjoint(set(near))
    assert set(killer).isdisjoint(set(far))


def test_sub_question_appears_in_queries():
    """The sub-question text should appear in generated queries."""
    for mode in ("near", "far", "killer_evidence"):
        queries = build_queries(LENS, SUB_Q, mode=mode)
        assert any(SUB_Q in q for q in queries)
