from __future__ import annotations

import json
from uuid import uuid4

from models import IssueTreeNode, LensRecord, PredictionRecord, ScheduleLogEntry, State
from models._enums import NodeStatus, OrchestratorRole, Phase, PredictionStatus
from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger


INCEPTION_PROMPT = """\
You are an analytical framework designer. Your job is to take a user's question and build a rigorous analytical structure around it.

User question: {question}

Produce a JSON object with exactly these keys:
- "driving_question": a clarified, precise restatement of the user's question
- "sub_questions": list of 3-5 strings, each a MECE (mutually exclusive, collectively exhaustive) sub-question that breaks down the driving question. These must cover all key dimensions without overlap.
- "lenses": list of 2-3 objects, each with "name" (a short, evocative name for an abstract analogy lens) and "rationale" (1-2 sentences explaining why this lens illuminates the driving question)
- "predictions": list of 2-3 objects, each with:
    - "claim": a falsifiable claim about the driving question
    - "if_true_we_should_see": what evidence would support this claim
    - "if_false_we_should_see": what evidence would refute this claim
    - "killer_evidence": a specific, observable piece of evidence that would decisively settle the claim (must be concrete, not vague)

Rules:
- Every prediction MUST have a concrete killer_evidence. If you cannot think of one, discard that prediction.
- Sub-questions must be MECE: together they cover the full question, and none overlap.
- Lenses should be cross-domain analogies (e.g., biological evolution, financial bubbles, military strategy), not restatements of the question itself.
- Output valid JSON only. No markdown, no commentary outside the JSON.
"""


def inception_node(state: State) -> dict:
    """Inception agent: generate issue tree, lenses, and predictions via LLM.

    MVP implementation uses a single LLM call with structured JSON output.
    Falls back to a minimal placeholder if LLM fails.
    """
    question = state.user_question or "Should AI companies burn cash for expansion?"

    client = LLMClient()
    messages = [{"role": "user", "content": INCEPTION_PROMPT.format(question=question)}]

    try:
        content, tokens = client.chat(messages, json_mode=True, temperature=0.7)
        data = json.loads(content)
    except (LLMJSONError, json.JSONDecodeError) as e:
        logger = DegradationLogger()
        return {
            "schedule_log": [
                logger.log_event(
                    role="inception",
                    scenario=f"LLM JSON failure: {e}",
                    fallback_action="fallback_to_placeholder_inception",
                )
            ],
            "token_spent": state.token_spent + 1000,  # rough estimate
            **_fallback_inception(question),
        }

    # Build issue tree
    driving = IssueTreeNode(
        author="inception",
        content=data["driving_question"],
        node_status=NodeStatus.untouched,
    )
    issue_tree = [driving]
    for sq in data.get("sub_questions", []):
        issue_tree.append(
            IssueTreeNode(
                author="inception",
                content=sq,
                parent_id=driving.id,
                node_status=NodeStatus.untouched,
            )
        )

    # Build lenses
    lenses = []
    for lens_data in data.get("lenses", []):
        lenses.append(
            LensRecord(
                author="inception",
                name=lens_data["name"],
                rationale=lens_data["rationale"],
            )
        )

    # Build predictions (filter out any missing killer_evidence)
    predictions = []
    for pred_data in data.get("predictions", []):
        killer = pred_data.get("killer_evidence", "").strip()
        if not killer:
            continue
        predictions.append(
            PredictionRecord(
                author="inception",
                claim=pred_data["claim"],
                if_true_we_should_see=pred_data["if_true_we_should_see"],
                if_false_we_should_see=pred_data["if_false_we_should_see"],
                killer_evidence=killer,
                prediction_status=PredictionStatus.pending,
            )
        )

    return {
        "issue_tree": issue_tree,
        "hypothesis_zone": lenses + predictions,
        "schedule_log": [
            ScheduleLogEntry(
                author="inception",
                role=OrchestratorRole.scheduler,
                decision="inception_complete",
                reason=f"generated {len(issue_tree)} nodes, {len(lenses)} lenses, {len(predictions)} predictions",
            )
        ],
        "token_spent": state.token_spent + tokens,
        "phase": Phase.exploration,
    }


def _fallback_inception(question: str) -> dict:
    """Minimal fallback when LLM fails."""
    driving = IssueTreeNode(
        author="inception",
        content=question,
        node_status=NodeStatus.untouched,
    )
    child = IssueTreeNode(
        author="inception",
        content="What are the key structural factors that determine the outcome?",
        parent_id=driving.id,
        node_status=NodeStatus.untouched,
    )
    return {
        "issue_tree": [driving, child],
        "hypothesis_zone": [],
        "phase": Phase.exploration,
    }
