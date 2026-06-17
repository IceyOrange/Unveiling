"""Phase 2 search agents: parallel lateral + vertical evidence collection.

Reads the latest lens from hypothesis_zone, derives search queries from
structural roles (not surface terms), calls the configured search engine, then has the LLM extract
distinct CASES/EXAMPLES as EvidenceRecords.

Key invariant: one evidence record = one distinct case (e.g., "卢德运动" = 1 record).
"""

from __future__ import annotations

import json
from typing import Literal

from unveiling.models._enums import (
    EvidenceConfidence,
    EvidenceDomain,
    EvidenceEra,
    EvidenceLayer,
    SearchDirection,
)
from unveiling.models.blackboard import (
    EvidenceRecord,
    LensRecord,
    ScheduleLogEntry,
)
from unveiling.models.state import State
from unveiling.llm.client import LLMClient, LLMJSONError
from unveiling.llm.degradation import DegradationLogger
from unveiling.llm.prompt_loader import load_lab_prompt
from unveiling.search.engine import search


# ---------------------------------------------------------------------------
# Prompt templates live in prompts/*.txt and are reloaded from disk on
# every call so edits saved via the /prompt-lab UI take effect on the next
# pipeline run without restarting the server.
# ---------------------------------------------------------------------------


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


def _format_hidden_dynamics(dynamics: list) -> str:
    if not dynamics:
        return "(none detected)"
    lines: list[str] = []
    for d in dynamics:
        lines.append(f"- \"{d.observation}\"")
        for layer in d.layers:
            lines.append(f"  · {layer}")
    return "\n".join(lines)


def _format_analogue_hints(analogues: list) -> str:
    if not analogues:
        return "(none)"
    lines: list[str] = []
    for a in analogues:
        lines.append(
            f"- [{a.domain}] {a.analogous_pattern}\n"
            f"  What happened: {a.what_happened}\n"
            f"  Potential lesson: {a.lesson_for_original}"
        )
    return "\n".join(lines)


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
    prompt_name = "lateral_query" if direction == "lateral" else "vertical_query"
    template = load_lab_prompt(prompt_name)
    prompt = template.format(
        lens_name=lens.name,
        lens_rationale=lens.rationale,
        entities_text=_format_entities(lens.entities),
        relations_text=_format_relations(lens.relationships),
        existing_cases_text=existing_cases_text,
        hidden_dynamics_text=_format_hidden_dynamics(lens.hidden_dynamics),
        analogue_hints_text=_format_analogue_hints(lens.cross_domain_analogues),
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
            return [str(q) for q in queries[:2]]
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
    prompt = load_lab_prompt("validate_queries").format(
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


def _run_search_queries(queries: list[str], lang: str = "") -> list[dict]:
    all_results: list[dict] = []
    for q in queries:
        try:
            results = search(q, num=5, lang=lang)
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

    prompt = load_lab_prompt("case_extraction").format(
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


def _enrich_cases_with_wiki(cases: list[dict], lang: str) -> list[dict]:
    """Enrich each case with authoritative knowledge.

    Step 1: Try Wikipedia first (free, structured, authoritative).
    Step 2: If Wikipedia returns empty, fallback to the default search
    engine chain (Exa → Serper) for broader web coverage.

    Only one source is appended per case: Wikipedia wins when available.
    Failures are silently skipped so the main pipeline never breaks.
    """
    from unveiling.search.wikipedia import search as wiki_search

    for case in cases:
        case_name = case.get("case_name", "")
        if not case_name:
            continue

        # Step 1: Wikipedia
        wiki_results: list[dict] = []
        try:
            wiki_results = wiki_search(case_name, num=1, lang=lang)
        except Exception:
            pass

        if wiki_results:
            wiki = wiki_results[0]
            existing = case.get("content", "")
            block = (
                f"\n\n[知识补充] {wiki['title']}\n"
                f"摘要: {wiki['snippet'][:400]}\n"
                f"链接: {wiki['link']}"
            )
            case["content"] = (existing + block).strip()
            continue

        # Step 2: Fallback to web search (Exa → Serper via engine default)
        try:
            web_results = search(case_name, num=1, lang=lang)
            if web_results:
                web = web_results[0]
                existing = case.get("content", "")
                block = (
                    f"\n\n[知识补充] {web['title']}\n"
                    f"摘要: {web['snippet'][:400]}\n"
                    f"链接: {web['link']}"
                )
                case["content"] = (existing + block).strip()
        except Exception:
            continue

    return cases


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
                    era=item.get("era") or None,
                    domain=item.get("domain") or None,
                    distance=item.get("distance") if item.get("distance") is not None else None,
                    distance_reason=item.get("distance_reason") or None,
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

    all_results = _run_search_queries(queries, lang=state.output_language)

    if not all_results:
        return {
            "schedule_log": [
                ScheduleLogEntry(
                    author=agent_name,
                    decision="search_empty",
                    reason=f"Search returned no results for {len(queries)} queries",
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

    # Enrich discovered cases with Wikipedia summaries for depth.
    cases = _enrich_cases_with_wiki(cases, state.output_language)

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

    from unveiling.orchestrator.rules import direction_done

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
