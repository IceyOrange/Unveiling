from __future__ import annotations

from unveiling.models._enums import Phase
from unveiling.models.state import State


def route_after_scheduler(state: State) -> str:
    """Route from scheduler_node: continue searching or converge."""
    if state.phase == Phase.convergence:
        return "convergence"
    return "continue_search"
