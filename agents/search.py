from __future__ import annotations

import json
from uuid import uuid4

from models import EvidenceRecord, ScheduleLogEntry, State
from models._enums import EvidenceConfidence, EvidenceLayer, OrchestratorRole
from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger
from search.serper import search


_EVIDENCE_EXTRACTION_PROMPT = """\
You are an evidence extractor. Given search results for a sub-question, extract structured evidence.

Sub-question: {sub_question}

Search results:
{results_text}

Produce a JSON object with exactly these keys:
- "evidence_list": list of objects, each with:
    - "content": a concise summary of the finding (1-2 sentences)
    - "layer": "phenomenon" | "mechanism" | "structure"
    - "confidence": "strong" | "medium" | "weak" | "unexpected"
    - "is_unexpected": true if this finding is surprising or counterintuitive, false otherwise

Rules:
- phenomenon = observable facts or outcomes
- mechanism = causal processes or how things work
- structure = deep structural patterns or invariant relationships
- Be conservative: only include findings actually supported by the search results
- Output valid JSON only. No markdown, no commentary outside the JSON.
"""


def _search_node(state: State, agent_name: str, mode: str) -> dict:
    """Shared search implementation for lateral (far) and vertical (near) search."""
    target_id = state.target_sub_question_id
    if not target_id:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author=agent_name,
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

    # Build queries
    if mode == "far":
        queries = [
            f"{sub_question} historical precedent different domain",
            f"{sub_question} counterintuitive analogy unrelated industry",
        ]
    else:
        queries = [
            f"{sub_question} case study structural analysis",
            f"{sub_question} empirical evidence mechanism",
        ]

    # Execute searches
    all_results = []
    for q in queries:
        try:
            results = search(q, num=5)
            all_results.extend(results)
        except Exception as e:
            all_results.append({"title": "Search error", "snippet": str(e), "link": ""})

    if not all_results:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author=agent_name,
                    role=OrchestratorRole.scheduler,
                    decision="search_empty",
                    reason=f"no results for sub-question {target_id}",
                )
            ]
        }

    # Format results for LLM
    results_text = "\n\n".join(
        f"[{i+1}] {r.get('title', '')}\n{r.get('snippet', '')}"
        for i, r in enumerate(all_results[:8])  # limit context
    )

    # Extract evidence via LLM
    client = LLMClient()
    messages = [
        {
            "role": "user",
            "content": _EVIDENCE_EXTRACTION_PROMPT.format(
                sub_question=sub_question,
                results_text=results_text,
            ),
        }
    ]

    evidence_list = []
    tokens = 0
    try:
        content, tokens = client.chat(messages, json_mode=True, temperature=0.3)
        data = json.loads(content)
        evidence_list = data.get("evidence_list", [])
    except (LLMJSONError, json.JSONDecodeError) as e:
        logger = DegradationLogger()
        return {
            "schedule_log": [
                logger.log_event(
                    role=agent_name,
                    scenario=f"evidence extraction failed: {e}",
                    fallback_action="write_raw_search_as_evidence",
                )
            ],
            "token_spent": state.token_spent + tokens + 1000,
        }

    # Build EvidenceRecords
    evidence_zone = []
    source_lens_id = state.hypothesis_zone[0].id if state.hypothesis_zone else "no_lens"
    for item in evidence_list:
        layer_str = item.get("layer", "phenomenon")
        confidence_str = item.get("confidence", "medium")
        evidence_zone.append(
            EvidenceRecord(
                author=agent_name,
                source_lens_id=source_lens_id,
                source_lens_version="v0",
                sub_question_id=target_id,
                layer=EvidenceLayer(layer_str),
                confidence=EvidenceConfidence(confidence_str),
                is_unexpected=item.get("is_unexpected", False),
                content=item.get("content", ""),
            )
        )

    return {
        "evidence_zone": evidence_zone,
        "schedule_log": [
            ScheduleLogEntry(
                author=agent_name,
                role=OrchestratorRole.scheduler,
                decision="search_complete",
                reason=f"extracted {len(evidence_zone)} evidence items for {target_id}",
            )
        ],
        "token_spent": state.token_spent + tokens,
    }


def search_lateral_node(state: State) -> dict:
    """Far search: cross-domain analogies and distant precedents."""
    return _search_node(state, "search_lateral", mode="far")


def search_vertical_node(state: State) -> dict:
    """Near search: same-domain case studies and empirical evidence."""
    return _search_node(state, "search_vertical", mode="near")
