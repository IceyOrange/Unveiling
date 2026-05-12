from __future__ import annotations

from models._enums import Phase
from models.state import State


def route_after_scheduler(state: State) -> str:
    """Route from scheduler_node: continue searching or converge."""
    if state.phase == Phase.convergence:
        return "convergence"
    return "continue_search"
