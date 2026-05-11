from __future__ import annotations

import json

from models import ConclusionRecord, ScheduleLogEntry, State
from models._enums import NodeStatus, OrchestratorRole, Phase
from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger


CONVERGENCE_PROMPT = """\
You are a synthesis analyst. Your job is to produce a tension-style conclusion from a completed analysis.

Issue tree (sub-questions and their final statuses):
{issue_tree_summary}

Evidence summary:
{evidence_summary}

Prediction outcomes:
{prediction_summary}

Debate / cross-layer failures:
{debate_summary}

Produce a JSON object with exactly these keys:
- "core_conclusion": one sentence that captures the central finding
- "tension": the central conflict or trade-off this analysis reveals (not a summary of findings, but the underlying tension)
- "boundary_condition": under what conditions the conclusion holds vs. breaks down
- "convergent_finding": the most robust finding that survived scrutiny
- "unresolved": what remains genuinely uncertain after this analysis
- "implication": what this means for the original driving question

Rules:
- Tension must be real: identify a genuine conflict, not just "there are pros and cons".
- Boundary condition must be specific enough to be testable.
- Unresolved must not be empty — every honest analysis leaves something open.
- Output valid JSON only. No markdown, no commentary outside the JSON.
"""


def convergence_node(state: State) -> dict:
    """Convergence agent: synthesize final tension-style output from blackboard state.

    MVP: single LLM call with structured summary of all zones.
    """
    # Build summaries
    latest_nodes = {}
    for node in state.issue_tree:
        latest_nodes[node.id] = node

    issue_tree_summary = "\n".join(
        f"- [{n.node_status.value}] {n.content}"
        for n in latest_nodes.values()
        if n.parent_id is not None  # only sub-questions
    )

    evidence_summary = "\n".join(
        f"- [{e.layer.value}, {e.confidence.value}] {e.content[:120]}"
        for e in state.evidence_zone
        if e.status == "committed"
    ) or "No committed evidence."

    # Use latest version of each prediction (append-only zone)
    latest_predictions = {}
    for p in state.hypothesis_zone:
        if hasattr(p, "prediction_status"):
            latest_predictions[p.id] = p

    prediction_summary = "\n".join(
        f"- [{p.prediction_status.value}] {p.claim}"
        for p in latest_predictions.values()
    ) or "No predictions."

    debate_summary = "\n".join(
        f"- [round {d.round}] Q: {d.question} A: {d.response}"
        for d in state.debate_zone
    ) or "No debates."

    prompt = CONVERGENCE_PROMPT.format(
        issue_tree_summary=issue_tree_summary,
        evidence_summary=evidence_summary,
        prediction_summary=prediction_summary,
        debate_summary=debate_summary,
    )

    client = LLMClient()
    messages = [{"role": "user", "content": prompt}]

    try:
        content, tokens = client.chat(messages, json_mode=True, temperature=0.5)
        data = json.loads(content)
    except (LLMJSONError, json.JSONDecodeError) as e:
        logger = DegradationLogger()
        return {
            "schedule_log": [
                logger.log_event(
                    role="convergence",
                    scenario=f"LLM JSON failure: {e}",
                    fallback_action="fallback_to_minimal_conclusion",
                )
            ],
            "token_spent": state.token_spent + 1000,
            **_fallback_conclusion(state),
        }

    conclusion = ConclusionRecord(
        author="convergence",
        convergent_finding=data.get("convergent_finding", ""),
        tension=data.get("tension", ""),
        boundary_condition=data.get("boundary_condition", ""),
        unresolved=data.get("unresolved", ""),
        implication=data.get("implication", ""),
    )

    return {
        "conclusion_zone": [conclusion],
        "schedule_log": [
            ScheduleLogEntry(
                author="convergence",
                role=OrchestratorRole.scheduler,
                decision="convergence_complete",
                reason="synthesized final tension-style conclusion",
            )
        ],
        "token_spent": state.token_spent + tokens,
        "phase": Phase.convergence,
    }


def _fallback_conclusion(state: State) -> dict:
    """Minimal fallback when LLM fails."""
    return {
        "conclusion_zone": [
            ConclusionRecord(
                author="convergence",
                convergent_finding="Analysis completed but synthesis failed.",
                tension="Unable to determine tension due to LLM failure.",
                boundary_condition="Unknown.",
                unresolved="Synthesis was not generated.",
                implication="Review evidence zone manually.",
            )
        ],
        "phase": Phase.convergence,
    }
