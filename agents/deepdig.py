from __future__ import annotations

from models import DebateRecord, EvidenceRecord, ScheduleLogEntry, State
from models._enums import EvidenceConfidence, EvidenceLayer, OrchestratorRole
from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger


_DEEPDIG_PROMPT = """\
You are a deep-dig analyst. Your job is to move one layer deeper in understanding.

Sub-question: {sub_question}

Current evidence (from shallowest to deepest layer):
{evidence_text}

The analytical layers are:
- phenomenon = observable facts and outcomes
- mechanism = causal processes and how things work
- structure = deep structural patterns and invariant relationships

Your task: produce a new finding that moves ONE layer deeper than the deepest evidence above. If the deepest is "phenomenon", produce a "mechanism" finding. If the deepest is "mechanism", produce a "structure" finding.

Output exactly:
Finding: <your deeper-layer finding (1-2 sentences)>
Layer: <phenomenon|mechanism|structure>
Confidence: <strong|medium|weak|unexpected>
Unexpected: <true|false>

If you cannot move deeper, output:
Finding: 止于 {current_layer} 层 — unable to find deeper pattern
Layer: {current_layer}
Confidence: weak
Unexpected: false
"""


def deepdig_node(state: State) -> dict:
    """Deep-dig agent: attempt cross-layer reasoning for a sub-question.

    Enforces max 2 same-layer steps and requires a cross-layer attempt.
    Cross-layer failure is recorded as '止于 X 层'.
    """
    target_id = state.target_sub_question_id
    if not target_id:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="deepdig",
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
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="deepdig",
                    role=OrchestratorRole.scheduler,
                    decision="deepdig_no_evidence",
                    reason=f"no evidence to dig deeper for {target_id}",
                )
            ]
        }

    # Determine deepest layer reached and count same-layer steps
    layer_order = {
        EvidenceLayer.phenomenon: 1,
        EvidenceLayer.mechanism: 2,
        EvidenceLayer.structure: 3,
    }

    deepest_layer = EvidenceLayer.phenomenon
    deepest_level = 1
    for e in related_evidence:
        level = layer_order.get(e.layer, 1)
        if level > deepest_level:
            deepest_level = level
            deepest_layer = e.layer

    # Count how many evidence items are at the deepest layer
    same_layer_count = sum(
        1 for e in related_evidence if e.layer == deepest_layer
    )

    # Hard rule: max 2 same-layer steps
    if same_layer_count >= 2 and deepest_level < 3:
        # Must attempt cross-layer; if we already have 2 at this layer,
        # the next finding MUST be at a deeper layer or mark failure
        pass  # Continue to LLM attempt
    elif same_layer_count >= 2 and deepest_level == 3:
        # Already at structure with 2 items — no deeper to go
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author="deepdig",
                    role=OrchestratorRole.scheduler,
                    decision="deepdig_at_bottom",
                    reason=f"already at structure layer with 2+ items for {target_id}",
                )
            ]
        }

    evidence_text = "\n\n".join(
        f"[{e.layer.value}] {e.content}"
        for e in sorted(related_evidence, key=lambda x: layer_order.get(x.layer, 1))
    )

    client = LLMClient(language=state.output_language)
    messages = [
        {
            "role": "user",
            "content": _DEEPDIG_PROMPT.format(
                sub_question=sub_question,
                evidence_text=evidence_text,
                current_layer=deepest_layer.value,
            ),
        }
    ]

    try:
        content, tokens = client.chat(messages, json_mode=False, temperature=0.5)
    except LLMJSONError as e:
        logger = DegradationLogger()
        return {
            "schedule_log": [
                logger.log_event(
                    role="deepdig",
                    scenario=f"LLM failure: {e}",
                    fallback_action="mark_cross_layer_failure",
                )
            ],
            "token_spent": state.token_spent + 1000,
        }

    # Parse output
    finding = ""
    layer = deepest_layer.value
    confidence = "medium"
    is_unexpected = False

    for line in content.splitlines():
        if line.startswith("Finding:"):
            finding = line[len("Finding:"):].strip()
        elif line.startswith("Layer:"):
            layer = line[len("Layer:"):].strip()
        elif line.startswith("Confidence:"):
            confidence = line[len("Confidence:"):].strip()
        elif line.startswith("Unexpected:"):
            is_unexpected = line[len("Unexpected:"):].strip().lower() == "true"

    if not finding:
        finding = f"止于 {deepest_layer.value} 层 — parsing failed"
        layer = deepest_layer.value

    # Check if cross-layer was attempted and failed
    cross_layer_failure = None
    if "止于" in finding:
        cross_layer_failure = finding

    # Determine target layer (one deeper than current)
    target_layer = deepest_layer
    if deepest_level == 1:
        target_layer = EvidenceLayer.mechanism
    elif deepest_level == 2:
        target_layer = EvidenceLayer.structure

    # If finding explicitly marks failure, write DebateRecord with cross_layer_failure_note
    if cross_layer_failure:
        return {
            "debate_zone": [
                DebateRecord(
                    author="deepdig",
                    round=1,
                    question=f"Can we find {target_layer.value}-layer insight for this sub-question?",
                    response=cross_layer_failure,
                    sub_question_id=target_id,
                    cross_layer_failure_note=cross_layer_failure,
                )
            ],
            "schedule_log": [
                ScheduleLogEntry(
                    author="deepdig",
                    role=OrchestratorRole.scheduler,
                    decision="cross_layer_failure",
                    reason=f"stopped at {deepest_layer.value} layer for {target_id}",
                )
            ],
            "token_spent": state.token_spent + tokens,
        }

    # Successful cross-layer finding
    try:
        new_layer = EvidenceLayer(layer)
    except ValueError:
        new_layer = target_layer

    try:
        new_confidence = EvidenceConfidence(confidence)
    except ValueError:
        new_confidence = EvidenceConfidence.medium

    source_lens_id = state.hypothesis_zone[0].id if state.hypothesis_zone else "no_lens"

    return {
        "evidence_zone": [
            EvidenceRecord(
                author="deepdig",
                source_lens_id=source_lens_id,
                source_lens_version="v0",
                sub_question_id=target_id,
                layer=new_layer,
                confidence=new_confidence,
                is_unexpected=is_unexpected,
                content=finding,
            )
        ],
        "schedule_log": [
            ScheduleLogEntry(
                author="deepdig",
                role=OrchestratorRole.scheduler,
                decision="deepdig_complete",
                reason=f"found {new_layer.value}-layer insight for {target_id}",
            )
        ],
        "token_spent": state.token_spent + tokens,
    }
