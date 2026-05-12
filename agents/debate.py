from __future__ import annotations

from models import DebateRecord, ScheduleLogEntry, State
from models._enums import OrchestratorRole
from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger


_DEBATE_PROMPT = """\
You are a critical examiner. Given evidence for a sub-question, ask ONE sharp, specific question that challenges the weakest or most questionable assumption in the evidence. Then provide a brief response that either defends the evidence or acknowledges the limitation.

Sub-question: {sub_question}

Evidence:
{evidence_text}

Output exactly two lines:
Question: <your critical question>
Response: <defense or acknowledgment>
"""


def debate_node(state: State) -> dict:
    """Debate agent: challenge evidence for a sub-question.

    Reads evidence related to target_sub_question_id, asks a critical
    question via LLM, and writes a DebateRecord.
    """
    target_id = state.target_sub_question_id
    if not target_id:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="debate",
                    role=OrchestratorRole.scheduler,
                    decision="noop",
                    reason="no target sub-question assigned",
                )
            ]
        }

    # Find sub-question content
    sub_question = ""
    latest = {}
    for node in state.issue_tree:
        latest[node.id] = node
    target = latest.get(target_id)
    if target:
        sub_question = target.content

    # Gather evidence for this sub-question
    related_evidence = [
        e for e in state.evidence_zone
        if e.sub_question_id == target_id and e.status == "committed"
    ]

    if not related_evidence:
        # No evidence yet — write a placeholder debate noting this
        return {
            "debate_zone": [
                DebateRecord(
                    author="debate",
                    round=1,
                    question="Why is there no evidence for this sub-question yet?",
                    response="Evidence has not been gathered. This sub-question needs search or deep-dig.",
                    sub_question_id=target_id,
                )
            ],
            "schedule_log": [
                ScheduleLogEntry(
                    author="debate",
                    role=OrchestratorRole.scheduler,
                    decision="debate_no_evidence",
                    reason=f"no committed evidence for {target_id}",
                )
            ],
        }

    evidence_text = "\n\n".join(
        f"[{i+1}] [{e.layer.value}] {e.content}"
        for i, e in enumerate(related_evidence[:5])
    )

    client = LLMClient(language=state.output_language)
    messages = [
        {
            "role": "user",
            "content": _DEBATE_PROMPT.format(
                sub_question=sub_question,
                evidence_text=evidence_text,
            ),
        }
    ]

    try:
        content, tokens = client.chat(messages, json_mode=False, temperature=0.7)
    except LLMJSONError as e:
        logger = DegradationLogger()
        return {
            "schedule_log": [
                logger.log_event(
                    role="debate",
                    scenario=f"LLM failure: {e}",
                    fallback_action="skip_debate",
                )
            ],
            "token_spent": state.token_spent + 1000,
        }

    # Parse Question/Response lines
    question = ""
    response = ""
    for line in content.splitlines():
        if line.startswith("Question:"):
            question = line[len("Question:"):].strip()
        elif line.startswith("Response:"):
            response = line[len("Response:"):].strip()

    if not question:
        question = "What is the strongest counter-argument to this evidence?"
    if not response:
        response = content[:500]

    # Determine round number
    existing_debates = [
        d for d in state.debate_zone if d.sub_question_id == target_id
    ]
    round_num = len(existing_debates) + 1

    return {
        "debate_zone": [
            DebateRecord(
                author="debate",
                round=round_num,
                question=question,
                response=response,
                sub_question_id=target_id,
                references=[e.id for e in related_evidence[:3]],
            )
        ],
        "schedule_log": [
            ScheduleLogEntry(
                author="debate",
                role=OrchestratorRole.scheduler,
                decision="debate_complete",
                reason=f"round {round_num} for {target_id}",
            )
        ],
        "token_spent": state.token_spent + tokens,
    }
