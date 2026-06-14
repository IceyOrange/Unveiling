from __future__ import annotations

from unveiling.models import ScheduleLogEntry, State
from unveiling.models._enums import Phase
from unveiling.orchestrator.rules import (
    both_directions_done,
    search_coverage_met,
    token_budget_exceeded,
    TARGET_EXAMPLES,
    MAX_ROUNDS_PER_DIRECTION,
)


def scheduler_node(state: State) -> dict:
    """Decide whether to continue searching or move to convergence.

    Each direction (lateral/vertical) converges independently when it hits
    TARGET_EXAMPLES or exhausts MAX_ROUNDS_PER_DIRECTION. Phase 3 starts
    only when both directions are done.
    """
    if token_budget_exceeded(state):
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="unveiling.orchestrator.scheduler",
                    decision="force_convergence",
                    reason=(
                        f"token budget exceeded: {state.token_spent} "
                        f">= {state.budget_ceiling}"
                    ),
                )
            ],
            "phase": Phase.convergence,
        }

    if both_directions_done(state):
        coverage = "coverage met" if search_coverage_met(state) else "max rounds reached"
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="unveiling.orchestrator.scheduler",
                    decision="convergence",
                    reason=(
                        f"{coverage}: lateral={state.lateral_count} "
                        f"({state.lateral_rounds}/{MAX_ROUNDS_PER_DIRECTION} rounds), "
                        f"vertical={state.vertical_count} "
                        f"({state.vertical_rounds}/{MAX_ROUNDS_PER_DIRECTION} rounds)"
                    ),
                )
            ],
            "phase": Phase.convergence,
        }

    return {
        "schedule_log": [
            ScheduleLogEntry(
                author="unveiling.orchestrator.scheduler",
                decision="continue_search",
                reason=(
                    f"lateral={state.lateral_count}/{TARGET_EXAMPLES} "
                    f"({state.lateral_rounds}/{MAX_ROUNDS_PER_DIRECTION}), "
                    f"vertical={state.vertical_count}/{TARGET_EXAMPLES} "
                    f"({state.vertical_rounds}/{MAX_ROUNDS_PER_DIRECTION})"
                ),
            )
        ],
    }
