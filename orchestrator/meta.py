from __future__ import annotations

from models import ScheduleLogEntry, State
from models._enums import NodeStatus, OrchestratorRole


def meta_node(state: State) -> dict:
    """Orchestrator Meta: evaluate whether the analysis framework needs revision.

    Heuristic-based evaluation (no LLM call for MVP):
    1. Check for stuck sub-questions — suggest retry if attempts are low
    2. Check for excessive lens revisions — warn if a lens has been revised > 3 times
    3. Check for high attempt counts with no progress — suggest marking stuck
    """
    reasons = []
    revision_type = None
    proposed_action = None

    # 1. Count lens revision depth
    lens_chain_lengths: dict[str, int] = {}
    for h in state.hypothesis_zone:
        if hasattr(h, "parent_lens_id") and h.parent_lens_id:
            # Walk the chain
            depth = 1
            current_parent = h.parent_lens_id
            while current_parent:
                depth += 1
                found_parent = False
                for h2 in state.hypothesis_zone:
                    if hasattr(h2, "id") and h2.id == current_parent and hasattr(h2, "parent_lens_id"):
                        current_parent = h2.parent_lens_id
                        found_parent = True
                        break
                if not found_parent:
                    break
            lens_chain_lengths[h.id] = depth

    max_chain = max(lens_chain_lengths.values()) if lens_chain_lengths else 0
    if max_chain > 3:
        reasons.append(f"lens revised {max_chain} times without stabilization")

    # 2. Check for high-attempt sub-questions still exploring
    latest_nodes: dict[str, object] = {}
    for node in state.issue_tree:
        latest_nodes[node.id] = node

    for node in latest_nodes.values():
        if node.parent_id is None:
            continue
        attempts = state.attempt_counters.get(node.id, 0)
        if attempts >= 12 and node.node_status == NodeStatus.exploring:
            reasons.append(
                f"sub-question '{node.content[:50]}' has {attempts} attempts but still exploring"
            )
            if revision_type is None:
                revision_type = "retry_stuck_sub_question"
                proposed_action = f"mark '{node.content[:50]}' as stuck"

    # 3. Check for stuck sub-questions with low attempts — suggest retry
    stuck_nodes = [
        n for n in latest_nodes.values()
        if n.parent_id is not None and n.node_status == NodeStatus.stuck
    ]
    for sn in stuck_nodes:
        attempts = state.attempt_counters.get(sn.id, 0)
        if attempts < 3:
            reasons.append(
                f"stuck sub-question '{sn.content[:50]}' only has {attempts} attempts"
            )
            if revision_type is None:
                revision_type = "retry_stuck_sub_question"
                proposed_action = f"retry '{sn.content[:50]}' with different search strategy"

    # If any concerns found, log them but default to no revision for MVP
    # (actual restructuring requires more sophisticated logic)
    if reasons:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="orchestrator.meta",
                    role=OrchestratorRole.meta,
                    decision="no_revision",
                    reason=f"meta noted concerns but held: {'; '.join(reasons)}",
                )
            ],
        }

    return {
        "schedule_log": [
            ScheduleLogEntry(
                author="orchestrator.meta",
                role=OrchestratorRole.meta,
                decision="no_revision",
                reason="analysis framework is healthy",
            )
        ],
    }
