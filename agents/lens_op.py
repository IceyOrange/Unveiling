from __future__ import annotations

from models import LensRecord, ScheduleLogEntry, State
from models._enums import OrchestratorRole
from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger


_LENS_REVISION_PROMPT = """\
You are a lens curator. Given the current evidence for a sub-question, evaluate whether the existing lens still illuminates the problem effectively.

Sub-question: {sub_question}

Existing lens: {lens_name}
Lens rationale: {lens_rationale}

Recent evidence:
{evidence_text}

Output exactly:
Action: <keep|revise|replace>
NewName: <if revise or replace, provide a fresh short vivid name for the evolved lens; if keep, output "same">
Reason: <one sentence explaining why>

Rules:
- "keep" if the lens still provides useful insight
- "revise" if the lens needs tweaking but the core idea is sound — give it a NEW name that reflects the tweak, do NOT append "(revised)" or "(updated)"
- "replace" if the evidence contradicts the lens — give it a completely new name
- Names should be vivid and accessible, not academic. Use metaphors, everyday language.
- Output plain text only, no JSON.
"""


def lens_op_node(state: State) -> dict:
    """Lens operation agent: evaluate and evolve lenses based on new evidence.

    MVP: evaluates the most recently used lens and creates a revised version
    if needed. Never mutates existing lenses — always appends new versions.
    """
    target_id = state.target_sub_question_id
    if not target_id:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="lens_op",
                    role=OrchestratorRole.scheduler,
                    decision="noop",
                    reason="no target sub-question assigned",
                )
            ]
        }

    # Find sub-question content
    sub_question = ""
    latest = {}
    for node in state.issue_tree:
        latest[node.id] = node
    target = latest.get(target_id)
    if target:
        sub_question = target.content

    # Find existing lenses
    lenses = [h for h in state.hypothesis_zone if hasattr(h, "name")]
    if not lenses:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="lens_op",
                    role=OrchestratorRole.scheduler,
                    decision="noop",
                    reason="no lenses to evaluate",
                )
            ]
        }

    # Use the most recently created/updated lens
    current_lens = lenses[-1]

    # Gather recent evidence for this sub-question
    related_evidence = [
        e for e in state.evidence_zone
        if e.sub_question_id == target_id and e.status == "committed"
    ][-5:]  # Last 5 pieces

    evidence_text = "\n\n".join(
        f"[{e.layer.value}] {e.content}"
        for e in related_evidence
    ) or "No evidence yet."

    client = LLMClient(language=state.output_language)
    messages = [
        {
            "role": "user",
            "content": _LENS_REVISION_PROMPT.format(
                sub_question=sub_question,
                lens_name=current_lens.name,
                lens_rationale=current_lens.rationale,
                evidence_text=evidence_text,
            ),
        }
    ]

    try:
        content, tokens = client.chat(messages, json_mode=False, temperature=0.5)
    except LLMJSONError as e:
        logger = DegradationLogger()
        return {
            "schedule_log": [
                logger.log_event(
                    role="lens_op",
                    scenario=f"LLM failure: {e}",
                    fallback_action="keep_lens",
                )
            ],
            "token_spent": state.token_spent + 1000,
        }

    # Parse action
    action = "keep"
    reason = ""
    new_name = ""
    for line in content.splitlines():
        if line.startswith("Action:"):
            action = line[len("Action:"):].strip().lower()
        elif line.startswith("Reason:"):
            reason = line[len("Reason:"):].strip()
        elif line.startswith("NewName:"):
            new_name = line[len("NewName:"):].strip()

    if action == "keep" or not reason:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="lens_op",
                    role=OrchestratorRole.scheduler,
                    decision="lens_keep",
                    reason=reason or f"{current_lens.name} remains appropriate",
                )
            ],
            "token_spent": state.token_spent + tokens,
        }

    # Create revised lens with a fresh name
    if not new_name or new_name.lower() == "same":
        new_name = current_lens.name

    new_lens = LensRecord(
        author="lens_op",
        parent_lens_id=current_lens.id,
        name=new_name,
        rationale=reason,
    )

    return {
        "hypothesis_zone": [new_lens],
        "schedule_log": [
            ScheduleLogEntry(
                author="lens_op",
                role=OrchestratorRole.scheduler,
                decision=f"lens_{action}",
                reason=f"evolved {current_lens.name} → {new_lens.name}",
            )
        ],
        "token_spent": state.token_spent + tokens,
    }
