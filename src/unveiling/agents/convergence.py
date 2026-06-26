from __future__ import annotations

import json

from unveiling.llm.client import LLMClient, LLMJSONError
from unveiling.llm.degradation import DegradationLogger
from unveiling.llm.prompt_loader import load_lab_prompt
from unveiling.models._enums import Phase
from unveiling.models.blackboard import ConclusionRecord, ScheduleLogEntry
from unveiling.models.state import State

# ---------------------------------------------------------------------------
# Prompt templates live in prompts/convergence_synthesize.txt and are
# reloaded from disk on every call so /prompt-lab UI edits take effect
# without restarting the server.
# ---------------------------------------------------------------------------


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


def _build_root_cause_chain(state: State) -> str:
    """Format the root cause chain from the latest lens."""
    if not state.hypothesis_zone:
        return "(No root cause chain)"

    chain = state.hypothesis_zone[-1].root_cause_chain
    if not chain:
        return "(No root cause chain produced during inception)"

    lines: list[str] = []
    for rc in chain:
        lines.append(
            f"Level {rc.level}: Q: {rc.surface_why}\n"
            f"  A: {rc.answer}\n"
            f"  Structural: {rc.structural_why}"
        )
    return "\n".join(lines)


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

    prompt = load_lab_prompt("convergence_synthesize").format(
        question=state.user_question,
        lens_summary=_build_lens_summary(state),
        root_cause_chain=_build_root_cause_chain(state),
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
            agent_name="convergence",
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
            agent_name="convergence",
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
        temporal_trajectory=data.get("temporal_trajectory", ""),
        taglines=data["taglines"] if isinstance(data.get("taglines"), dict) else {},
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
