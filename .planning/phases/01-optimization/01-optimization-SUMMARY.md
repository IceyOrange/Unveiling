---
phase: "01"
plan: "optimization"
subsystem: "search + frontend streaming"
tags: ["performance", "parallelization", "streaming", "caching"]
dependency_graph:
  requires: []
  provides: ["faster-evidence-streaming", "parallel-extraction"]
  affects: ["src/frontend/app.py", "src/frontend/static/js/app.js", "src/unveiling/agents/search.py", "prompts/*.txt"]
tech-stack:
  added: []
  patterns: ["ThreadPoolExecutor", "in-memory LRU cache", "global dedup set", "SSE flush optimization"]
key-files:
  created:
    - "prompts/case_extraction_single.txt"
  modified:
    - "src/frontend/app.py"
    - "src/frontend/static/js/app.js"
    - "src/unveiling/agents/search.py"
    - "prompts/lateral_query.txt"
    - "prompts/vertical_query.txt"
    - "tests/unit/search/test_build_records.py"
decisions:
  - "Merged query validation into generation prompts to save one LLM call per direction per round"
  - "Used ThreadPoolExecutor instead of asyncio to avoid refactoring the sync LangGraph pipeline"
  - "Decoupled card reveal from dot animation so users see textual evidence immediately"
  - "Relaxed per-round cap from 3 to 6 while keeping TARGET_EXAMPLES=5 in rules.py"
  - "Added global case-name dedup across rounds to prevent duplicate cases without losing quality"
metrics:
  duration: "~18 minutes"
  completed_date: "2026-06-25"
---

# Phase 01 Plan optimization: Evidence Streaming Performance Summary

## One-liner
Parallelized search queries, merged LLM validation into generation, decoupled frontend card/dot animations, and added per-result parallel extraction with early termination to make analogy evidence appear faster and one-by-one.

## Tasks Completed

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Remove SSE artificial delay for evidence_batch events | cd3b379 | src/frontend/app.py |
| 2 | Parallelize search queries within each direction | 8f077f7 | src/unveiling/agents/search.py |
| 3 | Merge query generation and validation into one LLM call | 9cd151b | prompts/lateral_query.txt, prompts/vertical_query.txt, src/unveiling/agents/search.py |
| 4 | Decouple evidence card reveal from scatter frame animation | cb7393e | src/frontend/static/js/app.js |
| 5 | Implement per-result / streaming case extraction | a07253d | src/unveiling/agents/search.py, prompts/case_extraction_single.txt |
| 6 | Relax 3-case cap and add early termination | 6e3b4b1 | src/unveiling/agents/search.py |
| 7 | Add query result cache / cross-round dedup | da5ea7d | src/unveiling/agents/search.py |
| Test fix | Reset global dedup before each build_records test | 8616e40 | tests/unit/search/test_build_records.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Global dedup caused unit test failure**
- **Found during:** Task 7 / verification
- **Issue:** `_build_records` now calls `_is_global_duplicate`, which persisted across test cases, causing `test_build_records_handles_missing_metadata` to return 0 records because "案例" was already seen in a prior test.
- **Fix:** Added `setup_function()` to `tests/unit/search/test_build_records.py` that calls `_reset_global_dedup()` before each test.
- **Files modified:** `tests/unit/search/test_build_records.py`
- **Commit:** 8616e40

### None - plan executed exactly as written (other than the above auto-fix).

## Known Stubs

No intentional stubs were introduced. The `_validate_queries` function is kept as a no-op stub for backward compatibility with the prompt-lab UI and any external callers, but it is no longer invoked in the hot path.

## Threat Flags

No new security-relevant surface was introduced. The in-memory cache and global dedup sets are per-process and do not persist across server restarts. No new network endpoints or auth paths were added.

## Self-Check: PASSED

- [x] `src/frontend/app.py` exists and compiles
- [x] `src/frontend/static/js/app.js` exists and JS syntax is valid
- [x] `src/unveiling/agents/search.py` exists and compiles
- [x] `prompts/case_extraction_single.txt` exists
- [x] `prompts/lateral_query.txt` exists
- [x] `prompts/vertical_query.txt` exists
- [x] All 7 optimization commits exist in git log
- [x] 80/80 unit tests pass (pytest -m "not e2e")
- [x] Flask dev server responds on port 5001
