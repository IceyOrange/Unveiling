"""Phase 2 search agents: parallel lateral + vertical evidence collection.

Reads the latest lens from hypothesis_zone, derives search queries from
structural roles (not surface terms), calls Serper, then has the LLM extract
distinct CASES/EXAMPLES as EvidenceRecords.

Key invariant: one evidence record = one distinct case (e.g., "卢德运动" = 1 record).
"""

from __future__ import annotations

import json
from typing import Literal

from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    SearchDirection,
)
from models.blackboard import (
    EvidenceRecord,
    LensRecord,
    ScheduleLogEntry,
)
from models.state import State
from llm.client import LLMClient, LLMJSONError
from llm.degradation import DegradationLogger
from search.serper import search


# ---------------------------------------------------------------------------
# Prompt templates — strongly differentiated by direction
# ---------------------------------------------------------------------------

_LATERAL_QUERY_PROMPT = """\
You generate search queries for CONTEMPORARY CROSS-DOMAIN analogies.

A structural lens has abstracted a question into universal patterns. Your task \
is to find CURRENT-DAY, PRESENT-ERA cases from DIFFERENT domains that exhibit \
the same structural pattern RIGHT NOW.

Lens: {lens_name}
Rationale: {lens_rationale}
Structural entities: {entities_text}
Structural relationships: {relations_text}

CASES ALREADY FOUND (use these as insight — do NOT search for similar ones):
{existing_cases_text}

CRITICAL DISTINCTION — lateral searches ONLY for contemporary/present-day cases:
- ✅ Different industries/fields experiencing the SAME structural pattern TODAY
- ✅ Current debates, ongoing controversies, present-day phenomena
- ❌ NO historical cases — those belong to vertical search
- ❌ NO "工业革命", "卢德运动", "20世纪初" or any past-era references

DOMAINS to explore: energy, agriculture, medicine, biotech, social media, \
finance, education, sports, entertainment, military, urban planning, etc.

Each query: 5-15 words, in the same language as the lens rationale.

Generate 3 queries, each targeting a DIFFERENT current-era domain.
Output valid JSON only: {{"queries": ["q1", "q2", "q3"]}}
"""

_VERTICAL_QUERY_PROMPT = """\
You generate search queries for CROSS-PERIOD cases spanning different eras.

A structural lens has abstracted a question into universal patterns. Your task \
is to find cases from DIFFERENT TIME PERIODS that exhibit the same structural \
pattern. These cases can be from ANY domain — cross-domain is welcome here.

Lens: {lens_name}
Rationale: {lens_rationale}
Structural entities: {entities_text}
Structural relationships: {relations_text}

CASES ALREADY FOUND (use these as insight — do NOT search for similar ones):
{existing_cases_text}

APPROACH:
- Each query must target a DIFFERENT historical era/period
- Any domain is fine: technology, politics, religion, economics, military, \
culture, science, etc.
- Think chronologically: ancient world → medieval → early modern → industrial \
revolution → 20th century → late 20th century → 2000s → 2010s
- Use specific time periods, events, movements — not generic terms
- Do NOT repeat time periods already covered by existing cases

Each query: 5-15 words, in the same language as the lens rationale.

Generate 3 queries, each targeting a DIFFERENT time period.
Output valid JSON only: {{"queries": ["q1", "q2", "q3"]}}
"""

_VALIDATE_QUERIES_PROMPT = """\
You are a search query validator. Catch problems BEFORE expensive web searches.

Direction: {direction}
- "lateral" = CONTEMPORARY cross-domain cases ONLY. Must be current-era \
phenomena from DIFFERENT fields. ABSOLUTELY NO historical events or past eras.
- "vertical" = Cross-PERIOD cases from DIFFERENT historical eras. Any domain \
is fine. Can be cross-domain within vertical.

Cases already collected (both directions):
{existing_cases_text}

Candidate queries:
{queries_text}

For EACH query, judge:
1. DUPLICATE RISK: Would this find essentially the SAME case as one already \
collected? (e.g., "工业革命纺织工人" finds the same event as "卢德运动")
2. DIRECTION FIT:
   - If direction is "lateral": REJECT any query about historical/past events \
     (工业革命, 20世纪初, 中世纪, etc.). Lateral = current-era ONLY.
   - If direction is "vertical": REJECT any query about current/present-day \
     phenomena without a specific historical period.
3. DOMAIN COVERAGE: If a domain/period is already covered by existing cases, \
   the query should target a DIFFERENT one.

For problematic queries, provide a REPLACEMENT. Keep fine queries unchanged.

Output valid JSON with the SAME number of queries:
{{"queries": ["q1_or_replacement", "q2_or_replacement", "q3_or_replacement"]}}
"""


_CASE_EXTRACTION_PROMPT = """\
You are a case extractor for a structural analogy system.

Structural lens:
Entities: {entities_text}
Relationships: {relations_text}

Search direction: {direction}
Search results:
{results_text}

Already collected cases (DO NOT duplicate): {existing_cases}

Task: Identify DISTINCT CASES/EXAMPLES from the search results. Each "case" is \
ONE specific historical event, industry phenomenon, or real-world example.

A case must be:
- A concrete, identifiable real-world example (not a generic observation)
- Named specifically (e.g., "卢德运动", "核能争议", "互联网泡沫", \
NOT "技术焦虑案例1")
- Summarized in 2-3 sentences: what happened + structural relevance to the lens

CRITICAL RULES:
- ONE record per case. NEVER split the same case into multiple records.
  "卢德运动" = 1 record. "工业革命中的纺织工人抗议" = same case, do not add.
- Skip cases already in the "already collected" list above
- Only include cases actually supported by the search results
- Maximum 5 cases per extraction
- Better fewer strong cases than many weak ones

Output valid JSON (no markdown):
{{"cases": [
  {{
    "case_name": "short case name (2-6 words)",
    "content": "2-3 sentences: what happened and why structurally relevant",
    "layer": "phenomenon" | "mechanism" | "structure",
    "confidence": "strong" | "medium" | "weak",
    "is_unexpected": true/false
  }}
]}}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _latest_lens(state: State) -> LensRecord | None:
    if not state.hypothesis_zone:
        return None
    return state.hypothesis_zone[-1]


def _format_entities(entities: list) -> str:
    if not entities:
        return "(none)"
    return "\n".join(
        f"- [{e.structural_role}] (surface: {e.surface})" for e in entities
    )


def _format_relations(relations: list) -> str:
    if not relations:
        return "(none)"
    return "\n".join(
        f"- [{r.structural}] (surface: {r.surface})" for r in relations
    )


def _get_existing_case_names(state: State) -> list[str]:
    return [e.case_name for e in state.evidence_zone if e.case_name]


def _format_existing_cases(state: State) -> str:
    """Format all cases on the blackboard for query generation insight."""
    cases = [e for e in state.evidence_zone if e.status == "committed" and e.case_name]
    if not cases:
        return "(none yet)"
    return "\n".join(
        f"- [{e.search_direction.value}] {e.case_name}: {e.content[:80]}"
        for e in cases
    )


def _generate_queries(
    client: LLMClient,
    lens: LensRecord,
    direction: Literal["lateral", "vertical"],
    existing_cases_text: str,
) -> list[str]:
    template = _LATERAL_QUERY_PROMPT if direction == "lateral" else _VERTICAL_QUERY_PROMPT
    prompt = template.format(
        lens_name=lens.name,
        lens_rationale=lens.rationale,
        entities_text=_format_entities(lens.entities),
        relations_text=_format_relations(lens.relationships),
        existing_cases_text=existing_cases_text,
    )
    try:
        content, _ = client.chat(
            [{"role": "user", "content": prompt}],
            json_mode=True,
            temperature=0.7,
        )
        data = json.loads(content)
        queries = data.get("queries", [])
        if isinstance(queries, list):
            return [str(q) for q in queries[:4]]
    except (LLMJSONError, json.JSONDecodeError, Exception):
        pass

    roles = [e.structural_role for e in lens.entities] or ["analogy"]
    if direction == "lateral":
        hints = ["跨领域类比案例", "不同行业类似现象", "其他学科案例"]
    else:
        hints = ["历史案例", "不同时期类似事件", "历史沿革"]
    return [f"{r} {h}" for r, h in zip(roles, hints)]


def _validate_queries(
    client: LLMClient,
    queries: list[str],
    direction: Literal["lateral", "vertical"],
    existing_cases_text: str,
) -> list[str]:
    """LLM pre-search validation: catch duplicates and direction mismatches."""
    queries_text = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(queries))
    prompt = _VALIDATE_QUERIES_PROMPT.format(
        direction=direction,
        existing_cases_text=existing_cases_text,
        queries_text=queries_text,
    )
    try:
        content, _ = client.chat(
            [{"role": "user", "content": prompt}],
            json_mode=True,
            temperature=0.3,
        )
        data = json.loads(content)
        validated = data.get("queries", [])
        if isinstance(validated, list) and len(validated) >= len(queries):
            return [str(q) for q in validated[:len(queries)]]
    except (LLMJSONError, json.JSONDecodeError, Exception):
        pass
    return queries


def _run_serper_queries(queries: list[str]) -> list[dict]:
    all_results: list[dict] = []
    for q in queries:
        try:
            results = search(q, num=5)
            all_results.extend(results)
        except Exception as exc:
            all_results.append({
                "title": "Search error",
                "snippet": str(exc),
                "link": "",
            })
    return all_results


def _extract_cases(
    client: LLMClient,
    lens: LensRecord,
    direction: Literal["lateral", "vertical"],
    results: list[dict],
    existing_case_names: list[str],
) -> tuple[list[dict], int]:
    results_text = "\n\n".join(
        f"[{i + 1}] {r.get('title', '')}\n{r.get('snippet', '')}"
        for i, r in enumerate(results[:8])
    )

    existing_text = (
        ", ".join(existing_case_names) if existing_case_names else "(none)"
    )

    prompt = _CASE_EXTRACTION_PROMPT.format(
        entities_text=_format_entities(lens.entities),
        relations_text=_format_relations(lens.relationships),
        direction=direction,
        results_text=results_text,
        existing_cases=existing_text,
    )

    content, tokens = client.chat(
        [{"role": "user", "content": prompt}],
        json_mode=True,
        temperature=0.3,
    )
    data = json.loads(content)
    return data.get("cases", []), tokens


def _build_records(
    cases: list[dict],
    lens: LensRecord,
    direction: SearchDirection,
    author: str,
) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for item in cases:
        try:
            layer_str = item.get("layer", "phenomenon")
            conf_str = item.get("confidence", "medium")
            records.append(
                EvidenceRecord(
                    author=author,
                    source_lens_id=lens.id,
                    search_direction=direction,
                    case_name=item.get("case_name", "")[:100],
                    layer=EvidenceLayer(layer_str),
                    confidence=EvidenceConfidence(conf_str),
                    is_unexpected=bool(item.get("is_unexpected", False)),
                    content=item.get("content", ""),
                    references=[lens.id],
                )
            )
        except Exception:
            continue
    return records


def _dedup_across_directions(
    records: list[EvidenceRecord],
) -> list[EvidenceRecord]:
    """Remove duplicate cases that appear in both lateral and vertical."""
    seen: set[str] = set()
    deduped: list[EvidenceRecord] = []
    for r in records:
        key = r.case_name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(r)
    return deduped


# ---------------------------------------------------------------------------
# Node functions (LangGraph entry points)
# ---------------------------------------------------------------------------

def search_lateral_node(state: State) -> dict:
    return _search_node(state, "search_lateral", SearchDirection.lateral)


def search_vertical_node(state: State) -> dict:
    return _search_node(state, "search_vertical", SearchDirection.vertical)


def _search_node(
    state: State,
    agent_name: str,
    direction: SearchDirection,
) -> dict:
    lens = _latest_lens(state)
    if lens is None:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author=agent_name,
                    decision="noop",
                    reason="no lens in hypothesis_zone — nothing to search for",
                )
            ],
        }

    direction_key: Literal["lateral", "vertical"] = direction.value

    client = LLMClient(language=state.output_language)
    existing_cases_text = _format_existing_cases(state)
    queries = _generate_queries(client, lens, direction_key, existing_cases_text)

    # Pre-search validation: catch duplicates and direction mismatches
    if queries:
        queries = _validate_queries(client, queries, direction_key, existing_cases_text)

    if not queries:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author=agent_name,
                    decision="search_no_queries",
                    reason="LLM failed to generate any queries",
                )
            ],
        }

    all_results = _run_serper_queries(queries)

    if not all_results:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author=agent_name,
                    decision="search_empty",
                    reason=f"Serper returned no results for {len(queries)} queries",
                )
            ],
        }

    tokens = 0
    cases: list[dict] = []
    existing_case_names = _get_existing_case_names(state)
    try:
        cases, tokens = _extract_cases(
            client, lens, direction_key, all_results, existing_case_names,
        )
    except (LLMJSONError, json.JSONDecodeError) as exc:
        deg = DegradationLogger.log_event(
            agent_name=agent_name,
            scenario=f"case extraction LLM failed: {exc}",
            fallback_action="skip evidence, log degradation",
        )
        return {
            "schedule_log": [deg],
            "token_spent": state.token_spent + tokens,
        }
    except Exception as exc:
        deg = DegradationLogger.log_event(
            agent_name=agent_name,
            scenario=f"unexpected error during case extraction: {exc}",
            fallback_action="skip evidence, log degradation",
        )
        return {
            "schedule_log": [deg],
            "token_spent": state.token_spent + tokens,
        }

    evidence_records = _build_records(cases, lens, direction, agent_name)

    log_entry = ScheduleLogEntry(
        author=agent_name,
        decision="search_complete",
        reason=(
            f"found {len(evidence_records)} cases "
            f"({direction.value}) via lens [{lens.id[:8]}]"
        ),
    )

    update: dict = {
        "evidence_zone": evidence_records,
        "schedule_log": [log_entry],
        "token_spent": state.token_spent + tokens,
    }

    if direction == SearchDirection.lateral:
        update["lateral_count"] = state.lateral_count + len(evidence_records)
    else:
        update["vertical_count"] = state.vertical_count + len(evidence_records)

    return update


# ---------------------------------------------------------------------------
# Parallel entry point for LangGraph
# ---------------------------------------------------------------------------

def parallel_search_node(state: State) -> dict:
    """Run only directions that haven't independently converged yet.

    Each direction converges on its own: when it hits TARGET_EXAMPLES or
    exhausts MAX_ROUNDS_PER_DIRECTION. Once a direction is done it is
    skipped in subsequent rounds. Phase 3 starts when both are done.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from orchestrator.rules import direction_done

    lateral_done = direction_done(state.lateral_count, state.lateral_rounds)
    vertical_done = direction_done(state.vertical_count, state.vertical_rounds)

    # Determine which directions still need searching
    to_run: list[str] = []
    if not lateral_done:
        to_run.append("lateral")
    if not vertical_done:
        to_run.append("vertical")

    if not to_run:
        return {"schedule_log": []}

    results: dict[str, dict] = {}

    with ThreadPoolExecutor(max_workers=len(to_run)) as pool:
        futures = {}
        if "lateral" in to_run:
            futures[pool.submit(search_lateral_node, state)] = "lateral"
        if "vertical" in to_run:
            futures[pool.submit(search_vertical_node, state)] = "vertical"

        for future in as_completed(futures):
            direction = futures[future]
            try:
                results[direction] = future.result()
            except Exception:
                results[direction] = {
                    "schedule_log": [
                        DegradationLogger.log_event(
                            agent_name=f"search_{direction}",
                            scenario="search crashed",
                            fallback_action="skip this direction",
                        )
                    ],
                }

    # Collect new evidence
    new_lateral: list[EvidenceRecord] = results.get("lateral", {}).get("evidence_zone", [])
    new_vertical: list[EvidenceRecord] = results.get("vertical", {}).get("evidence_zone", [])

    # Dedup across directions (only relevant when both ran)
    all_new = new_lateral + new_vertical
    if new_lateral and new_vertical:
        deduped = _dedup_across_directions(all_new)
    else:
        deduped = all_new

    deduped_ids = {r.id for r in deduped}
    final_lateral = [r for r in new_lateral if r.id in deduped_ids]
    final_vertical = [r for r in new_vertical if r.id in deduped_ids]

    # Merge
    merged: dict = {
        "evidence_zone": deduped,
        "schedule_log": [],
    }

    total_new_tokens = 0
    for direction, r in results.items():
        for k, v in r.items():
            if k in ("evidence_zone", "lateral_count", "vertical_count"):
                continue
            if k in merged and isinstance(merged[k], list) and isinstance(v, list):
                merged[k].extend(v)
            elif k == "token_spent":
                total_new_tokens += (v if isinstance(v, int) else 0)

    # Per-direction counts and round increments
    merged["lateral_count"] = state.lateral_count + len(final_lateral)
    merged["vertical_count"] = state.vertical_count + len(final_vertical)
    merged["lateral_rounds"] = state.lateral_rounds + (1 if "lateral" in to_run else 0)
    merged["vertical_rounds"] = state.vertical_rounds + (1 if "vertical" in to_run else 0)
    merged["token_spent"] = state.token_spent + total_new_tokens

    return merged
