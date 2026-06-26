from __future__ import annotations

from unveiling.models.state import State

TARGET_EXAMPLES = 5           # ideal target per direction
MIN_EXAMPLES = 3              # minimum viable per direction
MAX_ROUNDS_PER_DIRECTION = 3  # safety limit per direction


def direction_done(count: int, rounds: int) -> bool:
    """A direction is done when it hits target or exhausts its rounds."""
    return count >= TARGET_EXAMPLES or rounds >= MAX_ROUNDS_PER_DIRECTION


def both_directions_done(state: State) -> bool:
    """True when lateral AND vertical have each independently converged."""
    return (
        direction_done(state.lateral_count, state.lateral_rounds)
        and direction_done(state.vertical_count, state.vertical_rounds)
    )


def search_coverage_met(state: State) -> bool:
    """Both directions hit the ideal target (10 each)."""
    return (
        state.lateral_count >= TARGET_EXAMPLES
        and state.vertical_count >= TARGET_EXAMPLES
    )


def token_budget_exceeded(state: State) -> bool:
    return state.token_spent >= state.budget_ceiling
