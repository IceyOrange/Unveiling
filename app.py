import os
import uuid
import json
import threading
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, send_from_directory

load_dotenv()

from crew import SpatioTemporalCrew

app = Flask(__name__)

TASKS_DIR = Path(__file__).parent / "output"
TASKS_DIR.mkdir(exist_ok=True)

ANALYSIS_TASKS = {}

AGENT_LABELS = {
    "abstracter": "Abstracter — 生成抽象透镜",
    "vertical_discovery": "Vertical Discovery — 穿越时间搜索",
    "horizontal_discovery": "Horizontal Discovery — 穿越领域搜索",
    "comparator": "Comparator — 逐个对比分析",
    "causal_reviewer": "Causal Reviewer — 因果审查",
    "synthesizer": "Synthesizer — 综合整合",
    "visualization_agent": "Visualization — 生成幻灯片",
}

AGENT_ORDER = [
    "abstracter", "vertical_discovery", "horizontal_discovery",
    "comparator", "causal_reviewer", "synthesizer", "visualization_agent",
]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    topic = data.get("topic", "").strip()
    style_preset = data.get("style_preset", "swiss-modern")

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    task_id = str(uuid.uuid4())[:8]
    ANALYSIS_TASKS[task_id] = {
        "topic": topic,
        "style_preset": style_preset,
        "status": "running",
        "current_agent": "abstracter",
        "progress": 0,
        "result_file": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
    }

    thread = threading.Thread(
        target=_run_analysis,
        args=(task_id, topic, style_preset),
        daemon=True,
    )
    thread.start()

    return jsonify({"task_id": task_id, "topic": topic})


@app.route("/progress/<task_id>")
def progress(task_id):
    task = ANALYSIS_TASKS.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404

    def event_stream():
        import queue
        q = queue.Queue()
        task["_queue"] = q

        while True:
            try:
                msg = q.get(timeout=30)
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
                if msg.get("status") in ("completed", "error"):
                    break
            except queue.Empty:
                yield f": keepalive\n\n"

        task.pop("_queue", None)

    return Response(event_stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/result/<task_id>")
def result(task_id):
    task = ANALYSIS_TASKS.get(task_id)
    if not task:
        return jsonify({"error": "Task not found"}), 404
    if task["status"] != "completed":
        return jsonify({"error": "Analysis not completed yet"}), 400

    return jsonify({
        "task_id": task_id,
        "topic": task["topic"],
        "result_file": task["result_file"],
        "filename": Path(task["result_file"]).name if task["result_file"] else None,
    })


@app.route("/slides/<path:filename>")
def serve_slide(filename):
    return send_from_directory(str(TASKS_DIR), filename)


def _run_analysis(task_id, topic, style_preset):
    task = ANALYSIS_TASKS[task_id]

    try:
        crew_instance = SpatioTemporalCrew()

        def make_task_callback(task_name):
            def callback(output):
                idx = AGENT_ORDER.index(task_name) if task_name in AGENT_ORDER else 0
                progress_pct = int(((idx + 1) / len(AGENT_ORDER)) * 100)
                task["current_agent"] = task_name
                task["progress"] = progress_pct
                _notify(task_id, {
                    "status": "running",
                    "agent": task_name,
                    "label": AGENT_LABELS.get(task_name, task_name),
                    "progress": progress_pct,
                })
            return callback

        crew_obj = crew_instance.crew()
        task_names = [
            "abstraction_task", "vertical_discovery_task", "horizontal_discovery_task",
            "comparison_task", "causal_review_task", "synthesis_task", "visualization_task",
        ]
        for t_name in task_names:
            matched = [t for t in crew_obj.tasks if t.name == t_name]
            if matched:
                matched[0].callback = make_task_callback(t_name.replace("_task", ""))

        _notify(task_id, {
            "status": "running",
            "agent": "abstracter",
            "label": AGENT_LABELS["abstracter"],
            "progress": 5,
        })

        result = crew_obj.kickoff(inputs={"topic": topic})

        output_files = list(TASKS_DIR.glob("*.html"))
        if output_files:
            latest = max(output_files, key=lambda p: p.stat().st_mtime)
            task["result_file"] = str(latest)

        task["status"] = "completed"
        task["progress"] = 100
        _notify(task_id, {
            "status": "completed",
            "progress": 100,
            "result_file": task["result_file"],
        })

    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        _notify(task_id, {"status": "error", "error": str(e)})


def _notify(task_id, msg):
    task = ANALYSIS_TASKS.get(task_id)
    if task and "_queue" in task:
        task["_queue"].put(msg)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
