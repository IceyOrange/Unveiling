from __future__ import annotations

from models import ScheduleLogEntry, State
from models._enums import NodeStatus, OrchestratorRole, PredictionStatus
from orchestrator.rules import (
    has_debate_round,
    has_structure_or_mechanism_evidence,
)


def judge_node(state: State) -> dict:
    """Orchestrator Judge: evaluate whether a sub-question has reached
    minimum viable answer.

    Hard rules with escape hatches:
    - No structure/mechanism evidence → cannot close (escape after enough attempts)
    - No debate round → cannot close (escape after enough attempts)
    - All predictions pending → cannot close (escape after enough checks)
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

    attempts = state.attempt_counters.get(target_id, 0)
    MIN_ATTEMPTS_BEFORE_ESCAPE = 8

    # Hard rule: cannot close without structure or mechanism evidence
    # Escape hatch: after enough attempts, accept that search can't find deeper evidence
    if not has_structure_or_mechanism_evidence(target_id, state.evidence_zone):
        if attempts < MIN_ATTEMPTS_BEFORE_ESCAPE:
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
    # Escape hatch: after enough attempts, accept minimal debate coverage
    if not has_debate_round(target_id, state.debate_zone):
        if attempts < MIN_ATTEMPTS_BEFORE_ESCAPE:
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

    # Soft rule: if there are predictions and ALL are still pending, keep exploring
    # BUT escape hatch: if prediction_check has been attempted many times, accept that
    # predictions can't be verified via search and close anyway.
    # Dedup: hypothesis_zone is append-only, so get latest version per prediction ID.
    latest_preds: dict[str, object] = {}
    for h in state.hypothesis_zone:
        if hasattr(h, "prediction_status") and hasattr(h, "killer_evidence"):
            latest_preds[h.id] = h
    predictions = list(latest_preds.values())
    if predictions:
        all_pending = all(
            p.prediction_status == PredictionStatus.pending for p in predictions
        )
        if all_pending:
            # Count total prediction_check attempts across all predictions
            total_pred_checks = sum(
                1 for log in state.schedule_log
                if log.author == "prediction_check" and log.decision and log.decision.startswith("prediction_")
            )
            # After enough attempts, accept that search can't verify these predictions
            if total_pred_checks < len(latest_preds) + 2:
                return {
                    "issue_tree": [
                        target.model_copy(update={"node_status": NodeStatus.exploring})
                    ],
                    "schedule_log": [
                        ScheduleLogEntry(
                            author="orchestrator.judge",
                            role=OrchestratorRole.judge,
                            decision="keep_exploring",
                            reason="all predictions still pending, cannot close",
                        )
                    ],
                }

    # Force-stuck: if attempt count is very high, mark as stuck instead of exploring
    MAX_ATTEMPTS_BEFORE_STUCK = 14
    if attempts >= MAX_ATTEMPTS_BEFORE_STUCK:
        updated = target.model_copy(update={"node_status": NodeStatus.stuck})
        return {
            "issue_tree": [updated],
            "schedule_log": [
                ScheduleLogEntry(
                    author="orchestrator.judge",
                    role=OrchestratorRole.judge,
                    decision="stuck",
                    reason=f"{target_id} stuck after {attempts} attempts",
                )
            ],
        }

    # Close the sub-question
    updated = target.model_copy(update={"node_status": NodeStatus.closed})

    close_reason = "evidence and debate sufficient"
    if not has_structure_or_mechanism_evidence(target_id, state.evidence_zone):
        close_reason = "insufficient evidence depth, closing with available evidence"
    if predictions and all(p.prediction_status == PredictionStatus.pending for p in predictions):
        close_reason = "predictions unverifiable via search, closing with available evidence"

    return {
        "issue_tree": [updated],
        "schedule_log": [
            ScheduleLogEntry(
                author="orchestrator.judge",
                role=OrchestratorRole.judge,
                decision="close",
                reason=close_reason,
            )
        ],
    }
