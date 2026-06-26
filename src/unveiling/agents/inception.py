"""Phase 1 agent: structural abstraction of the user's question.

Produces exactly one LensRecord containing abstracted entities and
relationships.  No issue tree, no predictions, no second abstraction pass.
"""

from __future__ import annotations

import json

from unveiling.llm.client import LLMClient, LLMJSONError
from unveiling.llm.degradation import DegradationLogger
from unveiling.llm.prompt_loader import load_lab_prompt
from unveiling.models._enums import Phase
from unveiling.models.blackboard import (
    AbstractedEntity,
    AbstractedRelation,
    CrossDomainAnalogue,
    HiddenDynamic,
    LensRecord,
    RootCauseLevel,
    ScheduleLogEntry,
)
from unveiling.models.state import State


def inception_node(state: State) -> dict:
    """Phase 1: abstract the user question into a structural lens.

    Returns a State-update dict with:
      - hypothesis_zone: [LensRecord]
      - schedule_log: [ScheduleLogEntry]
      - phase: Phase.exploration
      - token_spent: updated total
    """
    import time

    node_start = time.time()
    question = state.user_question
    total_tokens = 0

    logs: list[ScheduleLogEntry] = [
        ScheduleLogEntry(
            author="inception",
            decision="node_started",
            reason=f"started at {node_start:.3f}",
        )
    ]

    # --- Call LLM for structural abstraction ---
    # Prompts are reloaded from prompts/ on every call so edits made via the
    # /prompt-lab UI take effect on the next run without restarting the process.
    client = LLMClient(language=state.output_language)
    try:
        system_prompt = load_lab_prompt("inception_system")
        user_prompt = load_lab_prompt("inception_user").format(question=question)
        raw, tokens = client.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            json_mode=True,
            temperature=0.7,
        )
        total_tokens += tokens
        data = json.loads(raw)
    except (LLMJSONError, json.JSONDecodeError, Exception) as exc:
        return _fallback(state, question, exc)

    # --- Parse LLM output into typed models ---
    pattern_name = data.get("pattern_name", "Unknown Pattern")
    essence = data.get("essence", "")

    entities = [
        AbstractedEntity(
            surface=e.get("surface", ""),
            structural_role=e.get("structural_role", ""),
        )
        for e in data.get("entities", [])
        if e.get("surface")
    ]

    relationships = [
        AbstractedRelation(
            surface=r.get("surface", ""),
            structural=r.get("structural", ""),
        )
        for r in data.get("relationships", [])
        if r.get("surface")
    ]

    hidden_dynamics = [
        HiddenDynamic(
            observation=hd.get("observation", ""),
            layers=hd.get("layers", []),
        )
        for hd in data.get("hidden_dynamics", [])
        if hd.get("observation")
    ]

    cross_domain_analogues = [
        CrossDomainAnalogue(
            domain=a.get("domain", ""),
            analogous_pattern=a.get("analogous_pattern", ""),
            what_happened=a.get("what_happened", ""),
            lesson_for_original=a.get("lesson_for_original", ""),
        )
        for a in data.get("cross_domain_analogues", [])
        if a.get("domain")
    ]

    root_cause_chain = [
        RootCauseLevel(
            level=rc.get("level", i + 1),
            surface_why=rc.get("surface_why", ""),
            answer=rc.get("answer", ""),
            structural_why=rc.get("structural_why", ""),
        )
        for i, rc in enumerate(data.get("root_cause_chain", []))
        if rc.get("surface_why")
    ]

    lens = LensRecord(
        author="inception",
        name=pattern_name,
        rationale=essence,
        entities=entities,
        relationships=relationships,
        hidden_dynamics=hidden_dynamics,
        cross_domain_analogues=cross_domain_analogues,
        root_cause_chain=root_cause_chain,
    )

    log = ScheduleLogEntry(
        author="inception",
        decision="inception_complete",
        reason=(
            f"abstracted to pattern '{pattern_name}', "
            f"{len(entities)} entities, {len(relationships)} relationships"
        ),
    )

    elapsed_ms = int((time.time() - node_start) * 1000)
    logs.append(log)
    logs.append(
        ScheduleLogEntry(
            author="inception",
            decision="node_finished",
            reason=f"elapsed {elapsed_ms}ms",
        )
    )

    return {
        "hypothesis_zone": [lens],
        "schedule_log": logs,
        "token_spent": state.token_spent + total_tokens,
        "phase": Phase.exploration,
    }


def _fallback(state: State, question: str, exc: Exception) -> dict:
    """Degradation path: log failure and return a minimal placeholder lens."""
    logger = DegradationLogger()
    log = logger.log_event(
        agent_name="inception",
        scenario=f"LLM failure during inception: {exc}",
        fallback_action="placeholder_lens_with_raw_question",
    )

    lens = LensRecord(
        author="inception",
        name=question,
        rationale="Fallback lens — LLM abstraction failed; using raw question.",
        entities=[],
        relationships=[],
    )

    return {
        "hypothesis_zone": [lens],
        "schedule_log": [log],
        "token_spent": state.token_spent + 500,
        "phase": Phase.exploration,
    }
