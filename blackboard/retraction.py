from __future__ import annotations

from blackboard.store import BlackboardStore


def resolve_cascade(store: BlackboardStore, retracted_id: str) -> list[str]:
    """Find all downstream records transitively dependent on retracted_id.

    Uses BFS over the references graph. Returns a list of affected record IDs.
    Does NOT auto-retract — the Orchestrator decides what to do with dependents.

    Args:
        store: BlackboardStore snapshot.
        retracted_id: ID of the record that was retracted.

    Returns:
        List of dependent record IDs (excluding retracted_id itself).
    """
    affected: list[str] = []
    visited: set[str] = set()
    queue = [retracted_id]

    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        dependents = store.get_dependents(current)
        for dep_id in dependents:
            if dep_id not in visited:
                affected.append(dep_id)
                queue.append(dep_id)

    return affected
