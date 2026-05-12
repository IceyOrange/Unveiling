"""Serialize an analysis ``State`` into the payload consumed by the result
screen and the slide-deck generator.

Lives outside ``frontend/app.py`` so callers that don't speak Flask (the CLI
in ``main.py``, the slide generator in ``frontend/slides/generator.py``,
unit tests) can build payloads without importing the web app.
"""

from __future__ import annotations

from models._enums import NodeStatus
from models.blackboard import (
    ConclusionRecord,
    EvidenceRecord,
    IssueTreeNode,
    LensRecord,
    PredictionRecord,
)
from models.state import State


def latest_issue_tree(records: list[IssueTreeNode]) -> list[IssueTreeNode]:
    """Issue-tree zone is append-only — collapse to the latest version per id."""
    latest: dict[str, IssueTreeNode] = {}
    for record in records:
        latest[record.id] = record
    return list(latest.values())


def serialize_state(state: State) -> dict:
    """Build the rich payload consumed by the result screen + slide deck."""

    latest_nodes = latest_issue_tree(state.issue_tree)
    sub_questions = [n for n in latest_nodes if n.parent_id is not None]
    closed = [n for n in sub_questions if n.node_status == NodeStatus.closed]
    stuck = [n for n in sub_questions if n.node_status == NodeStatus.stuck]

    latest_lens: dict[str, LensRecord] = {}
    latest_pred: dict[str, PredictionRecord] = {}
    for h in state.hypothesis_zone:
        if isinstance(h, LensRecord):
            latest_lens[h.id] = h
        elif isinstance(h, PredictionRecord):
            latest_pred[h.id] = h

    lens_chains = _build_lens_chains(list(latest_lens.values()))
    max_chain_len = max((len(chain) for chain in lens_chains), default=0)

    predictions: list[dict] = []
    confirmed = 0
    for p in latest_pred.values():
        status = p.prediction_status.value if hasattr(p.prediction_status, "value") else str(p.prediction_status)
        if status in {"supported", "refuted"}:
            confirmed += 1
        predictions.append(
            {
                "id": p.id,
                "claim": p.claim,
                "status": status,
                "killer_evidence": p.killer_evidence,
                "if_true_we_should_see": p.if_true_we_should_see,
                "if_false_we_should_see": p.if_false_we_should_see,
            }
        )

    evidence_records = [e for e in state.evidence_zone if e.status == "committed"]
    confidence_rank = {"strong": 0, "unexpected": 1, "medium": 2, "weak": 3}
    layer_rank = {"structure": 0, "mechanism": 1, "phenomenon": 2}

    def evidence_sort_key(e: EvidenceRecord) -> tuple:
        conf = e.confidence.value if hasattr(e.confidence, "value") else str(e.confidence)
        layer = e.layer.value if hasattr(e.layer, "value") else str(e.layer)
        return (confidence_rank.get(conf, 9), layer_rank.get(layer, 9))

    evidence_records.sort(key=evidence_sort_key)
    evidence_payload = [
        {
            "id": e.id,
            "content": e.content,
            "layer": e.layer.value if hasattr(e.layer, "value") else str(e.layer),
            "confidence": e.confidence.value if hasattr(e.confidence, "value") else str(e.confidence),
            "is_unexpected": e.is_unexpected,
            "sub_question_id": e.sub_question_id,
            "source_lens_id": e.source_lens_id,
            "source_lens_version": e.source_lens_version,
        }
        for e in evidence_records
    ]

    evidence_by_sub_q: dict[str, list[dict]] = {}
    for payload in evidence_payload:
        evidence_by_sub_q.setdefault(payload["sub_question_id"], []).append(payload)

    conclusions = [c for c in state.conclusion_zone if c.status == "committed"]
    primary_conclusion = conclusions[-1] if conclusions else None
    per_sub_q_conclusions: dict[str, dict] = {}
    for c in conclusions:
        if c.sub_question_id:
            per_sub_q_conclusions[c.sub_question_id] = _conclusion_to_dict(c)

    sub_question_payload: list[dict] = []
    for n in sub_questions:
        related_evidence = evidence_by_sub_q.get(n.id, [])
        sub_question_payload.append(
            {
                "id": n.id,
                "content": n.content,
                "status": n.node_status.value if hasattr(n.node_status, "value") else str(n.node_status),
                "minimum_viable_answer": n.minimum_viable_answer,
                "evidence_count": len(related_evidence),
                "structure_layer_count": sum(1 for e in related_evidence if e["layer"] == "structure"),
                "mechanism_layer_count": sum(1 for e in related_evidence if e["layer"] == "mechanism"),
                "unexpected_count": sum(1 for e in related_evidence if e["is_unexpected"]),
                "top_evidence": related_evidence[:3],
                "conclusion": per_sub_q_conclusions.get(n.id),
            }
        )

    debate_payload = [
        {
            "id": d.id,
            "round": d.round,
            "question": d.question,
            "response": d.response,
            "sub_question_id": d.sub_question_id,
        }
        for d in state.debate_zone
        if d.status == "committed"
    ]

    driving = next((n for n in latest_nodes if n.parent_id is None), None)

    integrity = {
        "sub_questions_total": len(sub_questions),
        "sub_questions_closed": len(closed),
        "sub_questions_stuck": len(stuck),
        "killer_evidence_total": len(latest_pred),
        "killer_evidence_confirmed": confirmed,
        "lens_evolution_depth": max_chain_len,
        "lens_initial_count": len(lens_chains),
        "degradation_count": state.degradation_count,
        "round_count": state.round_count,
        "token_spent": state.token_spent,
    }

    return {
        "driving_question": state.user_question,
        "driving_question_record": driving.content if driving else state.user_question,
        "phase": state.phase.value if hasattr(state.phase, "value") else str(state.phase),
        "integrity": integrity,
        "sub_questions": sub_question_payload,
        "lens_chains": [
            {
                "chain": [
                    {"id": l.id, "name": l.name, "rationale": l.rationale, "parent_id": l.parent_lens_id}
                    for l in chain
                ]
            }
            for chain in lens_chains
        ],
        "predictions": predictions,
        "evidence": evidence_payload,
        "debates": debate_payload,
        "conclusion": _conclusion_to_dict(primary_conclusion) if primary_conclusion else None,
    }


def _conclusion_to_dict(c: ConclusionRecord) -> dict:
    return {
        "convergent_finding": c.convergent_finding,
        "tension": c.tension,
        "boundary_condition": c.boundary_condition,
        "unresolved": c.unresolved,
        "implication": c.implication,
        "references": c.references,
    }


def _build_lens_chains(lenses: list[LensRecord]) -> list[list[LensRecord]]:
    """Reconstruct lens version chains from parent pointers."""
    by_id = {l.id: l for l in lenses}  # noqa: F841 — kept for clarity / future use
    children: dict[str | None, list[LensRecord]] = {}
    for l in lenses:
        children.setdefault(l.parent_lens_id, []).append(l)

    chains: list[list[LensRecord]] = []
    for root in children.get(None, []):
        chain = [root]
        cursor = root
        while True:
            next_versions = children.get(cursor.id, [])
            if not next_versions:
                break
            cursor = next_versions[0]
            chain.append(cursor)
        chains.append(chain)
    return chains
