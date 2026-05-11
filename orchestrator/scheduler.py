from __future__ import annotations

from models import ScheduleLogEntry, State
from models._enums import NodeStatus, OrchestratorRole, Phase
from orchestrator.rules import (
    all_leaves_closed_or_stuck,
    pick_first_non_closed_subquestion,
    token_budget_exceeded,
)

META_INTERVAL = 5


def scheduler_node(state: State) -> dict:
    """Orchestrator Scheduler: decide what to do next.

    Rule-led, LLM tie-breaker (MVP: rules only).
    Reads issue_tree; writes schedule_log, next_agent, target_sub_question_id.
    """
    # 1. Convergence check
    if token_budget_exceeded(state):
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="orchestrator.scheduler",
                    role=OrchestratorRole.scheduler,
                    decision="force_convergence",
                    reason=(
                        f"token budget exceeded: "
                        f"{state.token_spent} >= {state.budget_ceiling}"
                    ),
                )
            ],
            "phase": Phase.convergence,
        }

    if all_leaves_closed_or_stuck(state):
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="orchestrator.scheduler",
                    role=OrchestratorRole.scheduler,
                    decision="convergence",
                    reason="all leaf nodes are closed or stuck",
                )
            ],
            "phase": Phase.convergence,
        }

    # 2. Meta trigger
    if state.round_count > 0 and state.round_count % META_INTERVAL == 0:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="orchestrator.scheduler",
                    role=OrchestratorRole.scheduler,
                    decision="meta_evaluation",
                    reason=f"round {state.round_count} reached meta interval",
                )
            ],
            "round_count": state.round_count + 1,
            "next_agent": "meta",
        }

    # 3. Pick target sub-question
    target = pick_first_non_closed_subquestion(state)
    if target is None:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="orchestrator.scheduler",
                    role=OrchestratorRole.scheduler,
                    decision="convergence",
                    reason="no non-closed sub-questions found",
                )
            ],
            "phase": Phase.convergence,
        }

    # 4. Decide agent
    next_agent = _decide_agent(state, target)

    # 5. Update node status untouched -> exploring
    updates: dict = {}
    if target.node_status == NodeStatus.untouched:
        updates["issue_tree"] = [
            target.model_copy(update={"node_status": NodeStatus.exploring})
        ]

    # 6. Update attempt counter
    counter = state.attempt_counters.get(target.id, 0)
    updates["attempt_counters"] = {target.id: counter + 1}

    # 7. Log and return routing info
    updates["schedule_log"] = [
        ScheduleLogEntry(
            author="orchestrator.scheduler",
            role=OrchestratorRole.scheduler,
            decision=f"schedule {next_agent}",
            reason=(
                f"target sub-question {target.id} "
                f"status={target.node_status.value}"
            ),
        )
    ]
    updates["round_count"] = state.round_count + 1
    updates["next_agent"] = next_agent
    updates["target_sub_question_id"] = target.id

    return updates


def _decide_agent(state: State, target) -> str:
    """Rule-based agent selection for MVP.

    Full cycle per sub-question:
    search_lateral → search_vertical → deepdig → lens_op → debate → prediction_check → judge
    """
    counter = state.attempt_counters.get(target.id, 0)
    agents = [
        "search_lateral",
        "search_vertical",
        "deepdig",
        "lens_op",
        "debate",
        "prediction_check",
    ]
    # Every 6th attempt (after full cycle): judge; otherwise cycle through agents
    if counter > 0 and counter % 6 == 0:
        return "judge"
    return agents[counter % len(agents)]
