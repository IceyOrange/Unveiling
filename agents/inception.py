"""Phase 1 agent: structural abstraction of the user's question.

Produces exactly one LensRecord containing abstracted entities and
relationships.  No issue tree, no predictions, no second abstraction pass.
"""

from __future__ import annotations

import json

from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger
from models._enums import Phase
from models.blackboard import (
    AbstractedEntity,
    AbstractedRelation,
    LensRecord,
    ScheduleLogEntry,
)
from models.state import State

_SYSTEM_PROMPT = """\
You are a structural analyst.  Given a user's question, identify the key \
entities and relationships it involves, then abstract each one to a \
structural level that enables cross-temporal and cross-spatial comparison.
"""

_USER_PROMPT_TEMPLATE = """\
Question: {question}

Identify every meaningful entity and relationship in this question and \
abstract them to structural roles that would allow comparison with \
analogous situations in other domains or time periods.

Output valid JSON with exactly these keys:
- "pattern_name": a short, concrete name for the structural pattern
- "essence": 2-3 sentences explaining why this pattern holds (forces, mechanisms)
- "entities": list of {{"surface": "<original term>", "structural_role": "<abstracted structural role>"}}
- "relationships": list of {{"surface": "<original relationship>", "structural": "<abstracted structural relationship>"}}

Rules:
- Surface terms come directly from the question; structural roles must be \
generic enough for cross-domain comparison but specific enough to be useful.
- Every entity and relationship in the question must appear.
- Output valid JSON only.  No markdown, no commentary.
"""


def inception_node(state: State) -> dict:
    """Phase 1: abstract the user question into a structural lens.

    Returns a State-update dict with:
      - hypothesis_zone: [LensRecord]
      - schedule_log: [ScheduleLogEntry]
      - phase: Phase.exploration
      - token_spent: updated total
    """
    question = state.user_question
    total_tokens = 0

    # --- Call LLM for structural abstraction ---
    client = LLMClient(language=state.output_language)
    try:
        raw, tokens = client.chat(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _USER_PROMPT_TEMPLATE.format(question=question)},
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

    lens = LensRecord(
        author="inception",
        name=pattern_name,
        rationale=essence,
        entities=entities,
        relationships=relationships,
    )

    log = ScheduleLogEntry(
        author="inception",
        decision="inception_complete",
        reason=(
            f"abstracted to pattern '{pattern_name}', "
            f"{len(entities)} entities, {len(relationships)} relationships"
        ),
    )

    return {
        "hypothesis_zone": [lens],
        "schedule_log": [log],
        "token_spent": state.token_spent + total_tokens,
        "phase": Phase.exploration,
    }


def _fallback(state: State, question: str, exc: Exception) -> dict:
    """Degradation path: log failure and return a minimal placeholder lens."""
    logger = DegradationLogger()
    log = logger.log_event(
        role="inception",
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
