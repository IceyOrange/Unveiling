from __future__ import annotations

import json

from models import PredictionRecord, ScheduleLogEntry, State
from models._enums import OrchestratorRole, PredictionStatus
from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger
from search.serper import search


_PREDICTION_CHECK_PROMPT = """\
You are a hypothesis tester. Given a falsifiable prediction and search results, evaluate whether the prediction is supported, refuted, or needs modification.

Prediction: {claim}
If true we should see: {if_true}
If false we should see: {if_false}
Killer evidence to look for: {killer_evidence}

Search results:
{results_text}

Output a JSON object with:
- "status": "supported" | "refuted" | "modified" | "pending"
- "reason": brief explanation of your evaluation
- "killer_found": true if the specific killer_evidence was found or clearly contradicted, false otherwise

Rules:
- "supported" only if the evidence strongly aligns with the prediction
- "refuted" only if the evidence directly contradicts the prediction
- "modified" if the prediction needs adjustment based on new evidence
- "pending" if the search results are inconclusive
- Output valid JSON only.
"""


def prediction_check_node(state: State) -> dict:
    """Prediction check agent: evaluate a pending prediction against search evidence.

    Picks the first pending prediction that hasn't been checked too many times,
    searches for killer evidence, and updates the prediction status.
    """
    # Count how many times each prediction has been checked (via schedule_log)
    # Reason format: "pred_{id}: {analysis}" — extract the prefix to count per prediction
    check_counts: dict[str, int] = {}
    for log in state.schedule_log:
        if log.author == "prediction_check" and log.decision and log.decision.startswith("prediction_"):
            if log.reason and log.reason.startswith("pred_"):
                pred_id = log.reason.split(":")[0]  # "pred_{uuid}"
                check_counts[pred_id] = check_counts.get(pred_id, 0) + 1

    # Find a pending prediction that hasn't been checked too many times
    MAX_CHECK_ATTEMPTS = 2
    target_pred = None
    for h in state.hypothesis_zone:
        if hasattr(h, "prediction_status") and h.prediction_status == PredictionStatus.pending:
            pred_key = f"pred_{h.id}"
            attempts = check_counts.get(pred_key, 0)
            if attempts < MAX_CHECK_ATTEMPTS:
                target_pred = h
                break

    if target_pred is None:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="prediction_check",
                    role=OrchestratorRole.scheduler,
                    decision="noop",
                    reason="no pending predictions to check (all exhausted or resolved)",
                )
            ]
        }

    # Search for killer evidence and related terms
    queries = [
        target_pred.killer_evidence,
        target_pred.claim,
    ]

    all_results = []
    for q in queries:
        try:
            results = search(q, num=5)
            all_results.extend(results)
        except Exception as e:
            all_results.append({"title": "Search error", "snippet": str(e), "link": ""})

    results_text = "\n\n".join(
        f"[{i+1}] {r.get('title', '')}\n{r.get('snippet', '')}"
        for i, r in enumerate(all_results[:8])
    ) or "No search results."

    client = LLMClient(language=state.output_language)
    messages = [
        {
            "role": "user",
            "content": _PREDICTION_CHECK_PROMPT.format(
                claim=target_pred.claim,
                if_true=target_pred.if_true_we_should_see,
                if_false=target_pred.if_false_we_should_see,
                killer_evidence=target_pred.killer_evidence,
                results_text=results_text,
            ),
        }
    ]

    try:
        content, tokens = client.chat(messages, json_mode=True, temperature=0.3)
        data = json.loads(content)
    except (LLMJSONError, json.JSONDecodeError) as e:
        logger = DegradationLogger()
        return {
            "schedule_log": [
                logger.log_event(
                    role="prediction_check",
                    scenario=f"LLM JSON failure: {e}",
                    fallback_action="keep_pending",
                )
            ],
            "token_spent": state.token_spent + tokens + 1000,
        }

    status_str = data.get("status", "pending")
    try:
        new_status = PredictionStatus(status_str)
    except ValueError:
        new_status = PredictionStatus.pending

    # Create updated prediction record
    updated = target_pred.model_copy(update={"prediction_status": new_status})

    return {
        "hypothesis_zone": [updated],
        "schedule_log": [
            ScheduleLogEntry(
                author="prediction_check",
                role=OrchestratorRole.scheduler,
                decision=f"prediction_{new_status.value}",
                reason=f"pred_{target_pred.id}: {data.get('reason', 'no reason provided')}",
            )
        ],
        "token_spent": state.token_spent + tokens,
    }
