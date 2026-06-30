"""Phase 2 search agents: parallel lateral + vertical evidence collection.

Reads the latest lens from hypothesis_zone, derives search queries from
structural roles (not surface terms), calls the configured search engine, then has the LLM extract
distinct CASES/EXAMPLES as EvidenceRecords.

Key invariant: one evidence record = one distinct case (e.g., "卢德运动" = 1 record).
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import threading
import time
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
# Simple in-memory LRU cache for search results (query+lang -> results)
# ---------------------------------------------------------------------------
_search_cache: dict[tuple[str, str], tuple[list[dict], float]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes
_CACHE_MAX_SIZE = 64


def _cache_key(query: str, lang: str) -> tuple[str, str]:
    return (query.strip().lower(), lang)


def _get_cached(query: str, lang: str) -> list[dict] | None:
    key = _cache_key(query, lang)
    entry = _search_cache.get(key)
    if entry is None:
        return None
    results, ts = entry
    if time.time() - ts > _CACHE_TTL_SECONDS:
        del _search_cache[key]
        return None
    return results


def _set_cached(query: str, lang: str, results: list[dict]) -> None:
    key = _cache_key(query, lang)
    # Simple LRU eviction: if over limit, drop oldest by timestamp
    if len(_search_cache) >= _CACHE_MAX_SIZE:
        oldest = min(_search_cache, key=lambda k: _search_cache[k][1])
        del _search_cache[oldest]
    _search_cache[key] = (results, time.time())


# ---------------------------------------------------------------------------
# Global dedup set for case names across rounds (per-process)
# ---------------------------------------------------------------------------
_seen_case_names_global: set[str] = set()


def _is_global_duplicate(case_name: str) -> bool:
    key = case_name.strip().lower()
    if key in _seen_case_names_global:
        return True
    _seen_case_names_global.add(key)
    return False


def _reset_global_dedup() -> None:
    _seen_case_names_global.clear()
    _search_cache.clear()


# ---------------------------------------------------------------------------
# Prompt templates live in prompts/*.txt and are reloaded from disk on
# every call so edits saved via the /prompt-lab UI take effect on the next
# pipeline run without restarting the server.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Extraction prompt-size guard
# ---------------------------------------------------------------------------

# Some English-language providers (e.g. GitHub Models gpt-4o-mini) reject
# requests above ~8k tokens. We keep a conservative character budget so a
# single consolidated extraction call fits even when the lens is large.
_MAX_EXTRACTION_PROMPT_CHARS = 10000
_MAX_RESULTS_PER_EXTRACTION = 12
_MAX_SNIPPET_CHARS = 400
_MIN_RESULTS_PER_EXTRACTION = 4


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
            raw = [str(q).strip() for q in queries if q]
            return _lightweight_validate_queries(raw, direction)
    except (LLMJSONError, json.JSONDecodeError, Exception):
        pass

    roles = [e.structural_role for e in lens.entities] or ["analogy"]
    if direction == "lateral":
        hints = ["跨领域类比案例", "不同行业类似现象", "其他学科案例"]
    else:
        hints = ["历史案例", "不同时期类似事件", "历史沿革"]
    return [f"{r} {h}" for r, h in zip(roles, hints)]


def _lightweight_validate_queries(queries: list[str], direction: Literal["lateral", "vertical"]) -> list[str]:
    """Code-level dedupe + basic sanity checks. No extra LLM call."""
    seen: set[str] = set()
    out: list[str] = []
    for q in queries:
        if not q or len(q) < 5:
            continue
        lower = q.lower()
        if lower in seen:
            continue
        seen.add(lower)
        out.append(q)
    return out[:4]


def _validate_queries(
    client: LLMClient,
    queries: list[str],
    direction: Literal["lateral", "vertical"],
    existing_cases_text: str,
) -> list[str]:
    """DEPRECATED: validation is now merged into query generation prompts.

    Kept for backward compatibility with prompt-lab UI and any external
    callers; it simply returns the input queries unchanged.
    """
    return queries


def _run_search_queries(queries: list[str], lang: str = "") -> list[dict]:
    """Execute searches in parallel with a small thread pool."""
    all_results: list[dict] = []
    lock = threading.Lock()

    def _search_one(q: str) -> list[dict]:
        cached = _get_cached(q, lang)
        if cached is not None:
            return cached
        try:
            results = search(q, num=10, lang=lang)
        except Exception as exc:
            results = [{"title": "Search error", "snippet": str(exc), "link": ""}]
        _set_cached(q, lang, results)
        return results

    with ThreadPoolExecutor(max_workers=min(4, len(queries))) as pool:
        futures = {pool.submit(_search_one, q): q for q in queries}
        for future in as_completed(futures):
            try:
                res = future.result()
                with lock:
                    all_results.extend(res)
            except Exception:
                pass
    return all_results


def _extract_cases_single(
    client: LLMClient,
    lens: LensRecord,
    direction: Literal["lateral", "vertical"],
    result: dict,
    existing_case_names: list[str],
) -> tuple[list[dict], int]:
    """Extract zero or one case from a single search result."""
    result_text = f"[{result.get('title', '')}]\n{result.get('snippet', '')}"
    existing_text = ", ".join(existing_case_names) if existing_case_names else "(none)"

    prompt = load_lab_prompt("case_extraction_single").format(
        entities_text=_format_entities(lens.entities),
        relations_text=_format_relations(lens.relationships),
        direction=direction,
        result_text=result_text,
        existing_cases=existing_text,
    )
    content, tokens = client.chat(
        [{"role": "user", "content": prompt}],
        json_mode=True,
        temperature=0.3,
    )
    data = json.loads(content)
    case = data.get("case")
    if isinstance(case, dict) and case.get("case_name"):
        return [case], tokens
    return [], tokens


def _extract_cases_parallel(
    client: LLMClient,
    lens: LensRecord,
    direction: Literal["lateral", "vertical"],
    results: list[dict],
    existing_case_names: list[str],
    min_workers: int = 2,
    max_workers: int = 4,
    early_stop_at: int = 4,
) -> tuple[list[dict], int]:
    """Extract cases from all search results in a single LLM call.

    Instead of spawning many parallel mini-batch calls (which was the
    primary bottleneck — 330s lateral / 493s vertical), we consolidate
    the top search results into one prompt and ask the LLM to return
    up to ``early_stop_at`` high-quality cases in a single shot.

    The ``min_workers`` and ``max_workers`` parameters are kept for
    backward compatibility but are no longer used.
    """
    total_tokens = 0
    all_cases: list[dict] = []
    seen_names: set[str] = set(n.lower() for n in existing_case_names)

    # Truncate each search result and cap how many we feed into the single
    # consolidated extraction call. Some providers (e.g. GitHub Models
    # gpt-4o-mini) have a tight ~8k token request limit, so we keep the
    # prompt under a safe character budget.
    truncated_results = [
        {
            "title": str(r.get("title", ""))[:100],
            "snippet": str(r.get("snippet", ""))[:_MAX_SNIPPET_CHARS],
        }
        for r in results[:_MAX_RESULTS_PER_EXTRACTION]
    ]

    existing_text = ", ".join(existing_case_names) if existing_case_names else "(none)"
    prompt_template = load_lab_prompt("case_extraction")

    def _build_extraction_prompt(current_results: list[dict]) -> str:
        results_text = "\n\n".join(
            f"[{i + 1}] {r['title']}\n{r['snippet']}"
            for i, r in enumerate(current_results)
        )
        prompt = prompt_template.format(
            entities_text=_format_entities(lens.entities),
            relations_text=_format_relations(lens.relationships),
            direction=direction,
            results_text=results_text,
            existing_cases=existing_text,
        )
        prompt += (
            f"\n\nIMPORTANT: Return at most {early_stop_at} distinct, "
            f"high-quality cases. Do not pad the list with weak or generic entries."
        )
        return prompt

    prompt = _build_extraction_prompt(truncated_results)

    # Drop results from the tail if we're still over budget.
    while (
        len(prompt) > _MAX_EXTRACTION_PROMPT_CHARS
        and len(truncated_results) > _MIN_RESULTS_PER_EXTRACTION
    ):
        truncated_results = truncated_results[:-1]
        prompt = _build_extraction_prompt(truncated_results)

    # If the lens itself is very large, shorten all snippets uniformly.
    snippet_max = _MAX_SNIPPET_CHARS
    while len(prompt) > _MAX_EXTRACTION_PROMPT_CHARS and snippet_max > 100:
        snippet_max -= 100
        truncated_results = [
            {"title": r["title"], "snippet": r["snippet"][:snippet_max]}
            for r in truncated_results
        ]
        prompt = _build_extraction_prompt(truncated_results)

    content, tokens = client.chat(
        [{"role": "user", "content": prompt}],
        json_mode=True,
        temperature=0.3,
    )
    total_tokens += tokens

    data = json.loads(content)
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        cases = []

    for c in cases:
        name = str(c.get("case_name", "")).strip().lower()
        if name and name not in seen_names:
            seen_names.add(name)
            all_cases.append(c)

    # Hard cap: never return more than early_stop_at cases
    return all_cases[:early_stop_at], total_tokens


def _extract_cases_batch(
    client: LLMClient,
    lens: LensRecord,
    direction: Literal["lateral", "vertical"],
    results: list[dict],
    existing_case_names: list[str],
) -> tuple[list[dict], int]:
    """Extract cases from a small batch of search results (1-3 items)."""
    truncated = [
        {
            "title": str(r.get("title", ""))[:100],
            "snippet": str(r.get("snippet", ""))[:_MAX_SNIPPET_CHARS],
        }
        for r in results
    ]
    results_text = "\n\n".join(
        f"[{i + 1}] {r['title']}\n{r['snippet']}"
        for i, r in enumerate(truncated)
    )
    existing_text = ", ".join(existing_case_names) if existing_case_names else "(none)"

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


def _extract_cases(
    client: LLMClient,
    lens: LensRecord,
    direction: Literal["lateral", "vertical"],
    results: list[dict],
    existing_case_names: list[str],
) -> tuple[list[dict], int]:
    """Legacy monolithic extraction — kept for backward compatibility."""
    truncated = [
        {
            "title": str(r.get("title", ""))[:100],
            "snippet": str(r.get("snippet", ""))[:_MAX_SNIPPET_CHARS],
        }
        for r in results[:_MAX_RESULTS_PER_EXTRACTION]
    ]
    results_text = "\n\n".join(
        f"[{i + 1}] {r['title']}\n{r['snippet']}"
        for i, r in enumerate(truncated)
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


def _coerce_enum(enum_cls, value, default=None):
    """Coerce an LLM string into an enum member, tolerating bad/missing values.

    EvidenceRecord is strict (ConfigDict(strict=True)), so enum fields must
    receive actual enum instances — a raw string raises ValidationError. The
    LLM returns era/domain/layer/confidence as plain strings, so we normalize
    here. Unknown values fall back to ``default`` instead of dropping the case.
    """
    if value is None:
        return default
    try:
        return enum_cls(str(value).strip().lower())
    except (ValueError, TypeError):
        return default


def _coerce_distance(value):
    """Coerce distance into a float in [0, 1]; out-of-range/invalid -> None."""
    if value is None:
        return None
    try:
        d = float(value)
    except (ValueError, TypeError):
        return None
    if d < 0.0 or d > 1.0:
        return None
    return d


def _build_records(
    cases: list[dict],
    lens: LensRecord,
    direction: SearchDirection,
    author: str,
) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    for item in cases:
        case_name = str(item.get("case_name", "")).strip()
        if not case_name or _is_global_duplicate(case_name):
            continue
        try:
            era = _coerce_enum(EvidenceEra, item.get("era"))
            if era is None:
                era = (
                    EvidenceEra.industrial
                    if direction == SearchDirection.vertical
                    else EvidenceEra.contemporary
                )

            distance = _coerce_distance(item.get("distance"))
            if distance is None:
                distance = 0.7 if direction == SearchDirection.vertical else 0.5

            records.append(
                EvidenceRecord(
                    author=author,
                    source_lens_id=lens.id,
                    search_direction=direction,
                    case_name=case_name[:100],
                    layer=_coerce_enum(EvidenceLayer, item.get("layer"), EvidenceLayer.phenomenon),
                    confidence=_coerce_enum(
                        EvidenceConfidence, item.get("confidence"), EvidenceConfidence.medium
                    ),
                    is_unexpected=bool(item.get("is_unexpected", False)),
                    content=item.get("content", ""),
                    references=[lens.id],
                    era=era,
                    domain=_coerce_enum(EvidenceDomain, item.get("domain")),
                    distance=distance,
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
    import time

    node_start = time.time()
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
    logs: list[ScheduleLogEntry] = [
        ScheduleLogEntry(
            author=agent_name,
            decision="node_started",
            reason=f"started at {node_start:.3f}",
        )
    ]

    logs.append(
        ScheduleLogEntry(
            author=agent_name,
            decision="query_generation_started",
            reason=f"deriving {direction_key} queries from lens [{lens.id[:8]}]",
        )
    )
    qgen_start = time.time()
    queries = _generate_queries(client, lens, direction_key, existing_cases_text)
    qgen_elapsed_ms = int((time.time() - qgen_start) * 1000)
    logs.append(
        ScheduleLogEntry(
            author=agent_name,
            decision="query_generation_finished",
            reason=f"generated {len(queries)} queries in {qgen_elapsed_ms}ms",
        )
    )

    if not queries:
        logs.append(
            ScheduleLogEntry(
                author=agent_name,
                decision="search_no_queries",
                reason="LLM failed to generate any queries",
            )
        )
        return {
            "schedule_log": logs,
        }

    logs.append(
        ScheduleLogEntry(
            author=agent_name,
            decision="search_running",
            reason=f"running {len(queries)} {direction_key} queries",
        )
    )
    search_start = time.time()
    all_results = _run_search_queries(queries, lang=state.output_language)
    search_elapsed_ms = int((time.time() - search_start) * 1000)
    logs.append(
        ScheduleLogEntry(
            author=agent_name,
            decision="search_finished",
            reason=f"returned {len(all_results)} results in {search_elapsed_ms}ms",
        )
    )

    if not all_results:
        logs.append(
            ScheduleLogEntry(
                author=agent_name,
                decision="search_empty",
                reason=f"Search returned no results for {len(queries)} queries",
            )
        )
        return {
            "schedule_log": logs,
        }

    logs.append(
        ScheduleLogEntry(
            author=agent_name,
            decision="extraction_started",
            reason=f"extracting cases from {len(all_results)} {direction_key} results",
        )
    )

    tokens = 0
    cases: list[dict] = []
    existing_case_names = _get_existing_case_names(state)
    extraction_start = time.time()
    try:
        cases, tokens = _extract_cases_parallel(
            client, lens, direction_key, all_results, existing_case_names,
        )
    except (LLMJSONError, json.JSONDecodeError) as exc:
        logs.append(
            DegradationLogger.log_event(
                agent_name=agent_name,
                scenario=f"case extraction LLM failed: {exc}",
                fallback_action="skip evidence, log degradation",
            )
        )
        return {
            "schedule_log": logs,
            "token_spent": state.token_spent + tokens,
        }
    except Exception as exc:
        logs.append(
            DegradationLogger.log_event(
                agent_name=agent_name,
                scenario=f"unexpected error during case extraction: {exc}",
                fallback_action="skip evidence, log degradation",
            )
        )
        return {
            "schedule_log": logs,
            "token_spent": state.token_spent + tokens,
        }

    extraction_elapsed_ms = int((time.time() - extraction_start) * 1000)
    logs.append(
        ScheduleLogEntry(
            author=agent_name,
            decision="extraction_finished",
            reason=f"extracted {len(cases)} cases in {extraction_elapsed_ms}ms",
        )
    )

    evidence_records = _build_records(cases, lens, direction, agent_name)
    # Relaxed cap: allow more high-quality cases per round.
    evidence_records = evidence_records[:6]

    logs.append(
        ScheduleLogEntry(
            author=agent_name,
            decision="search_complete",
            reason=(
                f"found {len(evidence_records)} cases "
                f"({direction.value}) via lens [{lens.id[:8]}]"
            ),
        )
    )

    elapsed_ms = int((time.time() - node_start) * 1000)
    logs.append(
        ScheduleLogEntry(
            author=agent_name,
            decision="node_finished",
            reason=f"elapsed {elapsed_ms}ms",
        )
    )

    update: dict = {
        "evidence_zone": evidence_records,
        "schedule_log": logs,
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

    # Reset global dedup at the very first search round so a new analysis
    # doesn't carry over case names from a previous run.
    if state.lateral_rounds == 0 and state.vertical_rounds == 0:
        _reset_global_dedup()

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
    lateral_result = results.get("lateral", {})
    vertical_result = results.get("vertical", {})

    # Defensive: ensure results are dicts before calling .get()
    if not isinstance(lateral_result, dict):
        lateral_result = {}
    if not isinstance(vertical_result, dict):
        vertical_result = {}

    new_lateral: list[EvidenceRecord] = lateral_result.get("evidence_zone", [])
    new_vertical: list[EvidenceRecord] = vertical_result.get("evidence_zone", [])

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
    baseline_tokens = state.token_spent
    for direction, r in results.items():
        # Defensive: skip non-dict results (shouldn't happen but guards against race conditions)
        if not isinstance(r, dict):
            continue
        for k, v in r.items():
            if k in ("evidence_zone", "lateral_count", "vertical_count"):
                continue
            if k in merged and isinstance(merged[k], list) and isinstance(v, list):
                merged[k].extend(v)
            elif k == "token_spent":
                # Each running node returns its own cumulative token count (starting
                # from the same baseline). Only count the *increment* it produced.
                if isinstance(v, int):
                    total_new_tokens += max(0, v - baseline_tokens)

    # Per-direction counts and round increments
    merged["lateral_count"] = state.lateral_count + len(final_lateral)
    merged["vertical_count"] = state.vertical_count + len(final_vertical)
    merged["lateral_rounds"] = state.lateral_rounds + (1 if "lateral" in to_run else 0)
    merged["vertical_rounds"] = state.vertical_rounds + (1 if "vertical" in to_run else 0)
    merged["token_spent"] = state.token_spent + total_new_tokens

    return merged
