from __future__ import annotations

from models._enums import Phase
from models.state import State
from orchestrator.rules import all_leaves_closed_or_stuck, token_budget_exceeded


def route_after_scheduler(state: State) -> str:
    """Route from scheduler_node to the next node.

    Returns a key that must match the mapping in graph/build.py.
    """
    if state.phase == Phase.convergence:
        return "convergence"

    if state.next_agent == "meta":
        return "meta"

    if state.next_agent in {
        "search_lateral",
        "search_vertical",
        "deepdig",
        "lens_op",
        "debate",
        "prediction_check",
    }:
        return state.next_agent

    # Fallback: if no agent selected, try judge or converge
    if state.target_sub_question_id:
        return "judge"

    return "convergence"


def route_after_judge(state: State) -> str:
    """Always return to scheduler after judge."""
    return "scheduler"


def route_after_meta(state: State) -> str:
    """Route from meta_node: back to inception if phase was reset, else scheduler."""
    if state.phase == Phase.inception:
        return "inception"
    return "scheduler"


def should_converge(state: State) -> bool:
    """Standalone check used by frontend and CLI."""
    return token_budget_exceeded(state) or all_leaves_closed_or_stuck(state)
