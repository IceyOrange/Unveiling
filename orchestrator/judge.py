from __future__ import annotations

from models import ScheduleLogEntry, State
from models._enums import NodeStatus, OrchestratorRole
from orchestrator.rules import (
    has_debate_round,
    has_structure_or_mechanism_evidence,
)


def judge_node(state: State) -> dict:
    """Orchestrator Judge: evaluate whether a sub-question has reached
    minimum viable answer.

    Hard rule (no LLM call): no structure/mechanism evidence = cannot close.
    MVP uses simple heuristics; Phase 6 will add LLM nuance.
    """
    target_id = state.target_sub_question_id
    if not target_id:
        return {}

    target = None
    for node in state.issue_tree:
        if node.id == target_id:
            target = node
            break

    if target is None:
        return {}

    # Hard rule: cannot close without structure or mechanism evidence
    if not has_structure_or_mechanism_evidence(target_id, state.evidence_zone):
        if target.node_status != NodeStatus.closed:
            return {
                "issue_tree": [
                    target.model_copy(update={"node_status": NodeStatus.exploring})
                ],
                "schedule_log": [
                    ScheduleLogEntry(
                        author="orchestrator.judge",
                        role=OrchestratorRole.judge,
                        decision="keep_exploring",
                        reason=(
                            f"no structure or mechanism evidence "
                            f"for {target_id}"
                        ),
                    )
                ],
            }
        return {}

    # Hard rule: cannot close without at least one debate round
    if not has_debate_round(target_id, state.debate_zone):
        if target.node_status != NodeStatus.closed:
            return {
                "issue_tree": [
                    target.model_copy(update={"node_status": NodeStatus.exploring})
                ],
                "schedule_log": [
                    ScheduleLogEntry(
                        author="orchestrator.judge",
                        role=OrchestratorRole.judge,
                        decision="keep_exploring",
                        reason=f"no debate round for {target_id}",
                    )
                ],
            }
        return {}

    # MVP heuristic: enough evidence = close
    # TODO: replace with LLM judgment in Phase 6
    updated = target.model_copy(update={"node_status": NodeStatus.closed})

    return {
        "issue_tree": [updated],
        "schedule_log": [
            ScheduleLogEntry(
                author="orchestrator.judge",
                role=OrchestratorRole.judge,
                decision="close",
                reason="structure or mechanism evidence found",
            )
        ],
    }
