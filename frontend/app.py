from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from queue import Queue
from threading import Thread

# Add project root to path so imports work when running from frontend/
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from flask import Flask, Response, render_template, request, stream_with_context

from graph.build import build_graph
from models._enums import Phase
from models.state import State

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

# In-memory task store
_tasks: dict[str, dict] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    mode = data.get("mode", "balance")
    if not question:
        return {"error": "question is required"}, 400

    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "question": question,
        "mode": mode,
        "status": "running",
        "result": None,
    }

    # Start analysis in background thread
    thread = Thread(target=_run_analysis, args=(task_id, question, mode))
    thread.start()

    return {"task_id": task_id}


@app.route("/progress/<task_id>")
def progress(task_id: str):
    if task_id not in _tasks:
        return {"error": "task not found"}, 404

    def event_stream():
        queue = _tasks[task_id].get("queue")
        if queue is None:
            yield f"data: {json.dumps({'error': 'no queue'})}\n\n"
            return

        while True:
            event = queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
    )


@app.route("/result/<task_id>")
def result(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        return {"error": "task not found"}, 404
    if task["status"] != "done":
        return {"status": task["status"]}, 202
    return task["result"]


def _run_analysis(task_id: str, question: str, mode: str) -> None:
    """Run the analysis graph and stream events to the task's queue."""
    queue: Queue = Queue()
    _tasks[task_id]["queue"] = queue

    graph = build_graph()
    state = State(user_question=question)

    def emit(event: dict):
        queue.put(event)

    try:
        for chunk in graph.stream(state, {"recursion_limit": 100}):
            for node, updates in chunk.items():
                event = {"node": node}

                if "phase" in updates:
                    event["phase"] = updates["phase"].value if hasattr(updates["phase"], "value") else str(updates["phase"])

                if "schedule_log" in updates and updates["schedule_log"]:
                    entry = updates["schedule_log"][0]
                    event["decision"] = entry.decision
                    event["author"] = entry.author

                if "issue_tree" in updates and updates["issue_tree"]:
                    event["issue_tree_update"] = [
                        {
                            "id": n.id[:8],
                            "content": n.content[:80],
                            "status": n.node_status.value if hasattr(n.node_status, "value") else str(n.node_status),
                        }
                        for n in updates["issue_tree"]
                    ]

                if "evidence_zone" in updates and updates["evidence_zone"]:
                    event["evidence_count"] = len(updates["evidence_zone"])

                if "debate_zone" in updates and updates["debate_zone"]:
                    event["debate_count"] = len(updates["debate_zone"])

                emit(event)

        # Final state
        final_state = State(**chunk) if chunk else state
        _tasks[task_id]["result"] = _serialize_result(final_state)
        _tasks[task_id]["status"] = "done"
        emit({"done": True})

    except Exception as e:
        _tasks[task_id]["status"] = "error"
        emit({"error": str(e)})
    finally:
        queue.put(None)


def _serialize_result(state: State) -> dict:
    """Convert final State to JSON-serializable dict."""
    latest = {}
    for node in state.issue_tree:
        latest[node.id] = node

    issue_tree = []
    for node in latest.values():
        issue_tree.append({
            "id": node.id,
            "content": node.content,
            "status": node.node_status.value,
            "parent_id": node.parent_id,
        })

    lenses = []
    predictions = []
    for h in state.hypothesis_zone:
        if hasattr(h, "name"):
            lenses.append({"name": h.name, "rationale": h.rationale})
        elif hasattr(h, "claim"):
            predictions.append({
                "claim": h.claim,
                "status": h.prediction_status.value,
                "killer_evidence": h.killer_evidence,
            })

    conclusion = None
    if state.conclusion_zone:
        c = state.conclusion_zone[-1]
        conclusion = {
            "convergent_finding": c.convergent_finding,
            "tension": c.tension,
            "boundary_condition": c.boundary_condition,
            "unresolved": c.unresolved,
            "implication": c.implication,
        }

    return {
        "phase": state.phase.value if hasattr(state.phase, "value") else str(state.phase),
        "round_count": state.round_count,
        "token_spent": state.token_spent,
        "issue_tree": issue_tree,
        "lenses": lenses,
        "predictions": predictions,
        "conclusion": conclusion,
        "evidence_count": len(state.evidence_zone),
        "debate_count": len(state.debate_zone),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
