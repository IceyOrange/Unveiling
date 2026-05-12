from __future__ import annotations

import json

from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger
from models._enums import Phase
from models.blackboard import ConclusionRecord, ScheduleLogEntry
from models.state import State

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_SYNTHESIZE_PROMPT = """\
You are a synthesis analyst performing the final convergence of a cross-domain \
analogy analysis.

USER'S ORIGINAL QUESTION:
{question}

CURRENT LENS (structural abstraction frame):
{lens_summary}

ALL COMMITTED EVIDENCE ({evidence_count} records):
{evidence_detail}

STEP 1 — SYNTHESIZE PATTERNS
Look across ALL evidence records for structural commonalities that go deeper \
than surface similarities. What patterns repeat across the ~20 cases? This is \
the deeper abstraction that earlier phases deliberately did not perform.

STEP 2 — FIND TENSIONS
From the synthesized patterns, identify genuine structural conflicts — not \
"there are pros and cons" but real incompatibilities, forced choices, or \
paradoxes that emerge from the structure itself.

STEP 3 — CHALLENGE
Look for counter-evidence, confirmation bias, and cases that do not fit. \
Be honest about what the evidence does NOT support.

STEP 4 — CONCLUDE
Based on steps 1-3, produce the final conclusion.

Respond with a single JSON object with exactly these keys:
- "core_finding": the single most robust structural insight from this analysis
- "tension": the genuine structural conflict this analysis reveals \
(not a summary of findings, but the underlying tension)
- "boundary_condition": specific conditions under which the core finding holds \
vs. breaks down — must be concrete enough to be testable
- "unresolved": what remains genuinely uncertain after this analysis \
(must not be empty — every honest analysis leaves something open)
- "implication": what this means as an answer to the original question

Rules:
- Tension must be a real conflict, not "there are pros and cons".
- Boundary condition must be specific enough to be falsifiable.
- Unresolved must not be empty.
- Do not overclaim — stay within what the evidence actually supports.
- Output valid JSON only. No markdown, no commentary outside the JSON.
"""


# ---------------------------------------------------------------------------
# Helper: build text summaries from blackboard zones
# ---------------------------------------------------------------------------

def _build_lens_summary(state: State) -> str:
    """Summarize the latest lens from hypothesis_zone."""
    if not state.hypothesis_zone:
        return "(No lens record)"

    lens = state.hypothesis_zone[-1]
    parts = [f"Name: {lens.name}", f"Rationale: {lens.rationale}"]
    if lens.entities:
        parts.append(
            "Entities: "
            + ", ".join(
                f"{e.surface} → {e.structural_role}" for e in lens.entities
            )
        )
    if lens.relationships:
        parts.append(
            "Relationships: "
            + ", ".join(
                f"{r.surface} → {r.structural}" for r in lens.relationships
            )
        )
    return "\n".join(parts)


def _build_evidence_detail(state: State) -> str:
    """Format all committed evidence with full metadata."""
    committed = [e for e in state.evidence_zone if e.status == "committed"]
    if not committed:
        return "(No committed evidence)"

    lines: list[str] = []
    for e in committed:
        lines.append(
            f"[{e.search_direction.value}, {e.layer.value}, {e.confidence.value}"
            f"{', unexpected' if e.is_unexpected else ''}] "
            f"{e.case_name}: {e.content[:200]}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Fallback when LLM fails
# ---------------------------------------------------------------------------

def _fallback_conclusion(state: State) -> dict:
    """Produce a minimal honest conclusion when the LLM synthesis fails."""
    return {
        "conclusion_zone": [
            ConclusionRecord(
                author="convergence",
                core_finding="Analysis completed but synthesis failed due to LLM error.",
                tension="Unable to determine tension due to synthesis failure.",
                boundary_condition="Unknown — review evidence zone manually.",
                unresolved="Full synthesis was not generated; all findings remain uncertain.",
                implication=(
                    f"Review the {len(state.evidence_zone)} evidence records "
                    f"for the original question: {state.user_question}"
                ),
            )
        ],
        "phase": Phase.convergence,
    }


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------

def convergence_node(state: State) -> dict:
    """Convergence agent: synthesize patterns → find tensions → challenge → conclude.

    Multi-step process executed via LLM calls within a single LangGraph node.
    For MVP, steps 1-4 are combined into one comprehensive LLM call that
    receives all evidence and produces the final ConclusionRecord.
    """
    committed_evidence = [
        e for e in state.evidence_zone if e.status == "committed"
    ]

    prompt = _SYNTHESIZE_PROMPT.format(
        question=state.user_question,
        lens_summary=_build_lens_summary(state),
        evidence_count=len(committed_evidence),
        evidence_detail=_build_evidence_detail(state),
    )

    client = LLMClient(language=state.output_language)
    messages = [{"role": "user", "content": prompt}]

    try:
        content, tokens = client.chat(messages, json_mode=True, temperature=0.4)
        data = json.loads(content)
    except (LLMJSONError, json.JSONDecodeError, Exception) as exc:
        # Catch broad Exception to cover transient OpenAI errors that escape
        # tenacity retry (e.g. all retries exhausted).
        degradation = DegradationLogger.log_event(
            role="convergence",
            scenario=f"LLM call failed during convergence: {exc}",
            fallback_action="fallback_to_minimal_conclusion",
        )
        return {
            "schedule_log": [degradation],
            "token_spent": state.token_spent + 500,
            **_fallback_conclusion(state),
        }

    # Validate required keys exist (don't silently accept missing fields)
    required_keys = [
        "core_finding", "tension", "boundary_condition",
        "unresolved", "implication",
    ]
    missing = [k for k in required_keys if not data.get(k)]
    if missing:
        degradation = DegradationLogger.log_event(
            role="convergence",
            scenario=f"LLM output missing required keys: {missing}",
            fallback_action="fallback_to_minimal_conclusion",
        )
        return {
            "schedule_log": [degradation],
            "token_spent": state.token_spent + tokens,
            **_fallback_conclusion(state),
        }

    conclusion = ConclusionRecord(
        author="convergence",
        references=[e.id for e in committed_evidence[:20]],
        core_finding=data["core_finding"],
        tension=data["tension"],
        boundary_condition=data["boundary_condition"],
        unresolved=data["unresolved"],
        implication=data["implication"],
    )

    log = ScheduleLogEntry(
        author="convergence",
        decision="convergence_complete",
        reason=(
            f"Synthesized conclusion from {len(committed_evidence)} evidence records "
            f"via single-pass LLM call."
        ),
    )

    return {
        "conclusion_zone": [conclusion],
        "schedule_log": [log],
        "token_spent": state.token_spent + tokens,
        "phase": Phase.convergence,
    }
