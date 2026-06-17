"""Flask app for the prompt-tuning lab.

The full analysis flow runs from the CLI (``python main.py "..."``).  This Flask
process only serves the ``/prompt-lab`` page and its supporting JSON API so the
user can edit live prompts and run them against the LLM in isolation.

Prompts live in ``prompts/{name}.txt`` and are reloaded from disk on every
agent call, so saving from the UI takes effect on the next pipeline run with no
restart required.
"""

from __future__ import annotations

import json
import queue
import re
import sys
import threading
import time
import traceback
import uuid
from collections import deque
from pathlib import Path
from threading import Lock

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

_PROMPT_LAB_DIR = project_root / "prompts"

# In-memory ring buffer of recent lab runs, keyed by prompt name.  Kept tiny
# on purpose — this is a debugging UI, not durable storage.
_RUN_HISTORY_MAX = 12
_run_history: dict[str, deque[dict]] = {}
_run_history_lock = Lock()


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    demo = request.args.get("demo") == "1"
    return render_template("index.html", demo=demo)


@app.route("/prompt-lab")
def prompt_lab_page():
    return render_template("prompt-lab.html")


# ---------------------------------------------------------------------------
# Prompt Lab API
# ---------------------------------------------------------------------------

_BRACE_VAR_RE = re.compile(r"(?<!\{)\{([a-zA-Z_][a-zA-Z0-9_]*)\}(?!\})")


def _load_prompt_meta() -> dict:
    meta_path = _PROMPT_LAB_DIR / "meta.json"
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


def _read_prompt_file(name: str) -> str | None:
    path = _PROMPT_LAB_DIR / f"{name}.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _render_template(template: str, info: dict, inputs: dict) -> str:
    """Substitute `{var}` placeholders the same way agents do (`str.format`).

    Falls back to per-variable replace if `.format` raises (for templates that
    declare extra `{vars}` not yet listed in meta.json — useful when the user
    is mid-edit adding a new variable).
    """
    declared = list(info.get("variables", []))
    defaults = info.get("defaults", {})

    values: dict[str, str] = {}
    for var in declared:
        raw = inputs.get(var, defaults.get(var, ""))
        values[var] = "" if raw is None else str(raw)

    try:
        return template.format(**values)
    except (KeyError, IndexError, ValueError):
        # Defensive fallback: literal replace for declared vars only, leave
        # everything else (including `{{...}}` JSON examples) alone.
        rendered = template
        for var, val in values.items():
            rendered = rendered.replace("{" + var + "}", val)
        return rendered


def _discover_variables(template: str) -> list[str]:
    """Scan template for `{name}` placeholders that are NOT `{{...}}` escapes."""
    seen: set[str] = set()
    ordered: list[str] = []
    for match in _BRACE_VAR_RE.finditer(template):
        var = match.group(1)
        if var not in seen:
            seen.add(var)
            ordered.append(var)
    return ordered


def _record_run(name: str, entry: dict) -> None:
    with _run_history_lock:
        bucket = _run_history.setdefault(name, deque(maxlen=_RUN_HISTORY_MAX))
        bucket.appendleft(entry)


def _get_runs(name: str) -> list[dict]:
    with _run_history_lock:
        return list(_run_history.get(name, []))


@app.route("/api/prompts")
def api_list_prompts():
    meta = _load_prompt_meta()
    result = []
    for name, info in meta.items():
        result.append({
            "name": name,
            "label": info.get("label", name),
            "source": info.get("source", ""),
            "phase": info.get("phase", ""),
        })
    return jsonify(result)


@app.route("/api/prompts/<name>")
def api_get_prompt(name: str):
    meta = _load_prompt_meta()
    if name not in meta:
        return jsonify({"error": "not found"}), 404
    text = _read_prompt_file(name)
    if text is None:
        return jsonify({"error": "prompt file missing"}), 404
    info = meta[name]
    return jsonify({
        "name": name,
        "label": info.get("label", name),
        "source": info.get("source", ""),
        "phase": info.get("phase", ""),
        "description": info.get("description", ""),
        "text": text,
        "variables": info.get("variables", []),
        "discovered_variables": _discover_variables(text),
        "var_labels": info.get("var_labels", {}),
        "defaults": info.get("defaults", {}),
        "json_mode": info.get("json_mode", True),
        "temperature": info.get("temperature", 0.5),
        "run_count": len(_get_runs(name)),
    })


@app.route("/api/prompts/<name>", methods=["PUT"])
def api_save_prompt(name: str):
    meta = _load_prompt_meta()
    if name not in meta:
        return jsonify({"error": "not found"}), 404
    data = request.get_json() or {}
    text = data.get("text", "")
    path = _PROMPT_LAB_DIR / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    return jsonify({
        "ok": True,
        "saved": name,
        "bytes": len(text.encode("utf-8")),
        "discovered_variables": _discover_variables(text),
    })


@app.route("/api/prompts/<name>/preview", methods=["POST"])
def api_preview_prompt(name: str):
    """Render the prompt with variable substitution but DO NOT call the LLM.

    Lets the user see exactly what would be sent before spending a token.
    """
    meta = _load_prompt_meta()
    if name not in meta:
        return jsonify({"error": "not found"}), 404
    info = meta[name]
    data = request.get_json() or {}

    template = data.get("text")
    if template is None:
        template = _read_prompt_file(name)
        if template is None:
            return jsonify({"error": "prompt file missing"}), 404

    inputs = data.get("inputs", {})
    rendered = _render_template(template, info, inputs)
    return jsonify({
        "rendered": rendered,
        "char_count": len(rendered),
        "line_count": rendered.count("\n") + 1,
        "discovered_variables": _discover_variables(template),
    })


@app.route("/api/prompts/<name>/runs")
def api_list_runs(name: str):
    """Return recent runs for a prompt (in-memory, lost on restart)."""
    meta = _load_prompt_meta()
    if name not in meta:
        return jsonify({"error": "not found"}), 404
    return jsonify({"runs": _get_runs(name)})


@app.route("/api/prompts/<name>/run", methods=["POST"])
def api_run_prompt(name: str):
    meta = _load_prompt_meta()
    if name not in meta:
        return jsonify({"error": "not found"}), 404
    info = meta[name]
    data = request.get_json() or {}

    template = data.get("text")
    if template is None:
        template = _read_prompt_file(name)
        if template is None:
            return jsonify({"error": "prompt file missing"}), 404

    inputs = data.get("inputs", {})
    language = data.get("language", "中文")

    try:
        rendered = _render_template(template, info, inputs)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"variable substitution failed: {exc}"}), 400

    json_mode = bool(data.get("json_mode", info.get("json_mode", True)))
    try:
        temperature = float(data.get("temperature", info.get("temperature", 0.5)))
    except (TypeError, ValueError):
        temperature = float(info.get("temperature", 0.5))

    from unveiling.llm.client import LLMClient

    started_at = time.time()
    try:
        client = LLMClient(language=language)
        content, tokens = client.chat(
            [{"role": "user", "content": rendered}],
            json_mode=json_mode,
            temperature=temperature,
        )
        elapsed_ms = int((time.time() - started_at) * 1000)
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.time() - started_at) * 1000)
        error_payload = {
            "id": str(uuid.uuid4()),
            "ts": int(started_at * 1000),
            "ok": False,
            "error": str(exc),
            "elapsed_ms": elapsed_ms,
            "tokens": 0,
            "temperature": temperature,
            "json_mode": json_mode,
            "language": language,
            "inputs": inputs,
            "rendered_preview": rendered[:600],
        }
        _record_run(name, error_payload)
        return jsonify({"error": str(exc), "output": "", "history": error_payload}), 500

    parsed = None
    if json_mode:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            pass

    history_entry = {
        "id": str(uuid.uuid4()),
        "ts": int(started_at * 1000),
        "ok": True,
        "tokens": tokens,
        "elapsed_ms": elapsed_ms,
        "temperature": temperature,
        "json_mode": json_mode,
        "language": language,
        "inputs": inputs,
        "rendered_preview": rendered[:600],
        "output_preview": content[:600],
    }
    _record_run(name, history_entry)

    return jsonify({
        "output": content,
        "parsed": parsed,
        "tokens": tokens,
        "elapsed_ms": elapsed_ms,
        "json_mode": json_mode,
        "temperature": temperature,
        "history": history_entry,
    })


# ---------------------------------------------------------------------------
# Analysis pipeline (LangGraph three-phase: inception → search → convergence)
# ---------------------------------------------------------------------------

_task_lock = Lock()
_task_queues: dict[str, queue.Queue] = {}
_task_results: dict[str, dict] = {}
_task_errors: dict[str, str] = {}


_PHASE_LABEL = {
    "inception": "抽象",
    "exploration": "搜集",
    "convergence": "收拢",
}


def _phase_label(phase: str) -> str:
    return _PHASE_LABEL.get(phase, phase)


def _serialize_lens(lens) -> dict:
    return {
        "id": getattr(lens, "id", ""),
        "name": getattr(lens, "name", ""),
        "rationale": getattr(lens, "rationale", ""),
        "parent_lens_id": getattr(lens, "parent_lens_id", None),
        "entities": [
            {
                "surface": getattr(e, "surface", ""),
                "structural_role": getattr(e, "structural_role", ""),
            }
            for e in getattr(lens, "entities", [])
        ],
        "relationships": [
            {
                "surface": getattr(r, "surface", ""),
                "structural": getattr(r, "structural", ""),
            }
            for r in getattr(lens, "relationships", [])
        ],
        "hidden_dynamics": [
            {
                "observation": getattr(hd, "observation", ""),
                "layers": list(getattr(hd, "layers", [])),
            }
            for hd in getattr(lens, "hidden_dynamics", [])
        ],
        "cross_domain_analogues": [
            {
                "domain": getattr(a, "domain", ""),
                "analogous_pattern": getattr(a, "analogous_pattern", ""),
                "what_happened": getattr(a, "what_happened", ""),
                "lesson_for_original": getattr(a, "lesson_for_original", ""),
            }
            for a in getattr(lens, "cross_domain_analogues", [])
        ],
        "root_cause_chain": [
            {
                "level": getattr(rc, "level", 0),
                "surface_why": getattr(rc, "surface_why", ""),
                "answer": getattr(rc, "answer", ""),
                "structural_why": getattr(rc, "structural_why", ""),
            }
            for rc in getattr(lens, "root_cause_chain", [])
        ],
    }


def _serialize_evidence(ev) -> dict:
    sd = getattr(ev, "search_direction", None)
    layer = getattr(ev, "layer", None)
    conf = getattr(ev, "confidence", None)
    return {
        "id": getattr(ev, "id", ""),
        "case_name": getattr(ev, "case_name", ""),
        "content": getattr(ev, "content", ""),
        "search_direction": sd.value if hasattr(sd, "value") else str(sd),
        "layer": layer.value if hasattr(layer, "value") else str(layer),
        "confidence": conf.value if hasattr(conf, "value") else str(conf),
        "is_unexpected": bool(getattr(ev, "is_unexpected", False)),
        "source_lens_id": getattr(ev, "source_lens_id", ""),
        "status": getattr(ev, "status", "committed"),
    }


def _serialize_conclusion(c) -> dict:
    return {
        "id": getattr(c, "id", ""),
        "core_finding": getattr(c, "core_finding", ""),
        "tension": getattr(c, "tension", ""),
        "boundary_condition": getattr(c, "boundary_condition", ""),
        "unresolved": getattr(c, "unresolved", ""),
        "implication": getattr(c, "implication", ""),
        "temporal_trajectory": getattr(c, "temporal_trajectory", ""),
        "taglines": dict(getattr(c, "taglines", {}) or {}),
        "references": list(getattr(c, "references", [])),
    }


def _serialize_log(entry) -> dict:
    decision = getattr(entry, "decision", "") or ""
    reason = getattr(entry, "reason", "") or ""
    blob = f"{decision} {reason}".lower()
    is_degradation = (
        "fallback" in blob
        or "degradation" in blob
        or "降级" in (decision + reason)
        or "failed" in blob
        or "skip" in blob
    )
    ts = getattr(entry, "timestamp", None)
    return {
        "id": getattr(entry, "id", ""),
        "author": getattr(entry, "author", ""),
        "decision": decision,
        "reason": reason,
        "is_degradation": is_degradation,
        "timestamp": ts.isoformat() if ts is not None and hasattr(ts, "isoformat") else None,
    }


def _emit(q: queue.Queue, event) -> None:
    """Push an event onto the SSE queue. None is a sentinel meaning 'end'."""
    try:
        q.put(event, block=False)
    except queue.Full:
        pass


def _apply_update(running: dict, update: dict) -> dict:
    """Apply a LangGraph node update onto our running snapshot.

    Append-only lists get extended; other fields get replaced.
    """
    for key, value in update.items():
        if key in (
            "hypothesis_zone",
            "evidence_zone",
            "conclusion_zone",
            "schedule_log",
        ):
            if isinstance(value, list):
                running.setdefault(key, []).extend(value)
        else:
            running[key] = value
    return running


def _run_analysis(task_id: str, question: str, mode: str, language: str) -> None:
    """Background worker: build graph, stream updates, push SSE events."""
    q = _task_queues[task_id]

    # Lazy imports — graph wiring touches LangGraph, LLM client, etc.
    try:
        from unveiling.graph.build import build_graph
        from unveiling.models.state import State
    except Exception as exc:
        _emit(q, {"kind": "error", "error": f"import failed: {exc}",
                  "traceback": traceback.format_exc()})
        _emit(q, None)
        with _task_lock:
            _task_errors[task_id] = str(exc)
        return

    _emit(q, {
        "kind": "meta",
        "question": question,
        "mode": mode,
        "language": language,
        "task_id": task_id,
    })
    _emit(q, {"kind": "phase", "phase": "inception", "label": _phase_label("inception")})

    try:
        graph = build_graph()
    except Exception as exc:
        _emit(q, {"kind": "error", "error": f"graph build failed: {exc}",
                  "traceback": traceback.format_exc()})
        _emit(q, None)
        with _task_lock:
            _task_errors[task_id] = str(exc)
        return

    initial = State(user_question=question, output_language=language)

    running: dict = {
        "hypothesis_zone": [],
        "evidence_zone": [],
        "conclusion_zone": [],
        "schedule_log": [],
        "lateral_count": 0,
        "vertical_count": 0,
        "lateral_rounds": 0,
        "vertical_rounds": 0,
        "token_spent": 0,
        "phase": "inception",
    }
    seen_lens: set[str] = set()
    seen_evidence: set[str] = set()
    seen_conclusion: set[str] = set()
    seen_logs: set[str] = set()

    try:
        for chunk in graph.stream(initial, {"recursion_limit": 30}):
            for node, update in chunk.items():
                if not isinstance(update, dict):
                    continue

                _apply_update(running, update)

                # New lenses
                for lens in update.get("hypothesis_zone", []) or []:
                    lid = getattr(lens, "id", "")
                    if lid and lid not in seen_lens:
                        seen_lens.add(lid)
                        _emit(q, {"kind": "lens", "lens": _serialize_lens(lens), "node": node})

                # New evidence (batch per chunk)
                new_evidence = []
                for ev in update.get("evidence_zone", []) or []:
                    eid = getattr(ev, "id", "")
                    if eid and eid not in seen_evidence:
                        seen_evidence.add(eid)
                        new_evidence.append(ev)
                if new_evidence:
                    _emit(q, {
                        "kind": "evidence_batch",
                        "evidence": [_serialize_evidence(e) for e in new_evidence],
                        "lateral_count": running.get("lateral_count", 0),
                        "vertical_count": running.get("vertical_count", 0),
                        "lateral_rounds": running.get("lateral_rounds", 0),
                        "vertical_rounds": running.get("vertical_rounds", 0),
                        "node": node,
                    })

                # New conclusions
                for c in update.get("conclusion_zone", []) or []:
                    cid = getattr(c, "id", "")
                    if cid and cid not in seen_conclusion:
                        seen_conclusion.add(cid)
                        _emit(q, {"kind": "conclusion",
                                  "conclusion": _serialize_conclusion(c), "node": node})

                # New schedule entries
                for le in update.get("schedule_log", []) or []:
                    lid = getattr(le, "id", "")
                    if lid and lid not in seen_logs:
                        seen_logs.add(lid)
                        _emit(q, {"kind": "schedule",
                                  "entry": _serialize_log(le), "node": node})

                # Phase change
                if "phase" in update:
                    phase_val = update["phase"]
                    phase_str = phase_val.value if hasattr(phase_val, "value") else str(phase_val)
                    _emit(q, {"kind": "phase", "phase": phase_str,
                              "label": _phase_label(phase_str), "node": node})

                # Tokens / progress
                if "token_spent" in update:
                    _emit(q, {"kind": "tokens", "tokens": running.get("token_spent", 0)})

                if any(k in update for k in (
                    "lateral_count", "vertical_count", "lateral_rounds", "vertical_rounds"
                )):
                    _emit(q, {
                        "kind": "progress",
                        "lateral_count": running.get("lateral_count", 0),
                        "vertical_count": running.get("vertical_count", 0),
                        "lateral_rounds": running.get("lateral_rounds", 0),
                        "vertical_rounds": running.get("vertical_rounds", 0),
                    })

        result_payload = {
            "task_id": task_id,
            "question": question,
            "mode": mode,
            "language": language,
            "lateral_count": running.get("lateral_count", 0),
            "vertical_count": running.get("vertical_count", 0),
            "lateral_rounds": running.get("lateral_rounds", 0),
            "vertical_rounds": running.get("vertical_rounds", 0),
            "token_spent": running.get("token_spent", 0),
            "phase": running.get("phase", "convergence"),
            "lenses": [_serialize_lens(l) for l in running.get("hypothesis_zone", [])],
            "evidence": [_serialize_evidence(e) for e in running.get("evidence_zone", [])],
            "conclusion": (
                _serialize_conclusion(running["conclusion_zone"][-1])
                if running.get("conclusion_zone") else None
            ),
            "schedule_log": [_serialize_log(le) for le in running.get("schedule_log", [])],
        }
        with _task_lock:
            _task_results[task_id] = result_payload

        # Write detailed log to tmp/ (same as CLI path)
        try:
            from shared.log_writer import write_analysis_log
            log_path = write_analysis_log(running)
            result_payload["log_path"] = str(log_path)
        except Exception:
            pass  # log writing failure should not break the response

        _emit(q, {"kind": "done", "result": result_payload})
    except Exception as exc:
        with _task_lock:
            _task_errors[task_id] = str(exc)
        _emit(q, {"kind": "error", "error": str(exc),
                  "traceback": traceback.format_exc()})
    finally:
        _emit(q, None)


@app.route("/analyze", methods=["POST"])
def api_analyze():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    mode = data.get("mode", "balance")
    language = data.get("language", "中文")

    task_id = str(uuid.uuid4())
    with _task_lock:
        _task_queues[task_id] = queue.Queue()

    thread = threading.Thread(
        target=_run_analysis,
        args=(task_id, question, mode, language),
        daemon=True,
    )
    thread.start()
    return jsonify({"task_id": task_id})


@app.route("/progress/<task_id>")
def api_progress(task_id: str):
    with _task_lock:
        q = _task_queues.get(task_id)
    if q is None:
        return jsonify({"error": "unknown task_id"}), 404

    def stream():
        yield "retry: 2000\n\n"
        while True:
            try:
                event = q.get(timeout=30)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            if event is None:
                yield "event: end\ndata: {}\n\n"
                break
            payload = json.dumps(event, ensure_ascii=False)
            yield f"data: {payload}\n\n"

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.route("/result/<task_id>")
def api_result(task_id: str):
    with _task_lock:
        result = _task_results.get(task_id)
        error = _task_errors.get(task_id)
    if result is not None:
        return jsonify({"status": "done", "result": result})
    if error is not None:
        return jsonify({"status": "error", "error": error}), 500
    with _task_lock:
        exists = task_id in _task_queues
    if exists:
        return jsonify({"status": "running"}), 202
    return jsonify({"error": "unknown task_id"}), 404


# ---------------------------------------------------------------------------
# Pipeline Lab endpoints
# ---------------------------------------------------------------------------


@app.route("/api/pipeline/run", methods=["POST"])
def api_pipeline_run():
    """Generic LLM call for pipeline debugging. Accepts arbitrary messages."""
    data = request.get_json() or {}
    messages = data.get("messages", [])
    if not messages:
        return jsonify({"error": "messages required"}), 400

    json_mode = bool(data.get("json_mode", True))
    try:
        temperature = float(data.get("temperature", 0.7))
    except (TypeError, ValueError):
        temperature = 0.7
    language = data.get("language", "中文")

    from unveiling.llm.client import LLMClient

    started_at = time.time()
    try:
        client = LLMClient(language=language)
        content, tokens = client.chat(
            messages, json_mode=json_mode, temperature=temperature
        )
        elapsed_ms = int((time.time() - started_at) * 1000)
    except Exception as exc:
        elapsed_ms = int((time.time() - started_at) * 1000)
        return jsonify({"error": str(exc), "elapsed_ms": elapsed_ms}), 500

    parsed = None
    if json_mode:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            pass

    return jsonify({
        "output": content,
        "parsed": parsed,
        "tokens": tokens,
        "elapsed_ms": elapsed_ms,
    })


@app.route("/api/serper/search", methods=["POST"])
def api_serper_search():
    """Run Serper queries for pipeline debugging."""
    data = request.get_json() or {}
    queries = data.get("queries", [])
    if not queries:
        return jsonify({"error": "queries required"}), 400

    from unveiling.search.serper import search

    all_results: list[dict] = []
    for q in queries:
        try:
            results = search(q, num=5)
            all_results.extend(results)
        except Exception as exc:
            all_results.append({"title": "Search error", "snippet": str(exc), "link": ""})

    return jsonify({"results": all_results})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
