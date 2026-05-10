import os
import uuid
import json
import re
import threading
import traceback
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from crewai import Crew, Process

load_dotenv()

from crew import SpatioTemporalCrew
from tools.slide_generator import SlideGeneratorTool
from tools.shared_blackboard import get_blackboard, reset_blackboard
from brainstorm import BrainstormRoom

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
    "comparator", "causal_reviewer", "synthesizer",
]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    topic = data.get("topic", "").strip()
    style_preset = data.get("style_preset", "swiss-modern")
    language = data.get("language", "zh")

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    import queue
    task_id = str(uuid.uuid4())[:8]
    ANALYSIS_TASKS[task_id] = {
        "topic": topic,
        "style_preset": style_preset,
        "language": language,
        "status": "running",
        "current_agent": "abstracter",
        "progress": 0,
        "result_file": None,
        "error": None,
        "created_at": datetime.now().isoformat(),
        "_queue": queue.Queue(),
        "_buffer": [],
    }

    thread = threading.Thread(
        target=_run_analysis,
        args=(task_id, topic, style_preset, language),
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
        # Use existing queue or create new
        q = task.get("_queue")
        if q is None:
            q = queue.Queue()
            task["_queue"] = q

        # Flush buffered messages first
        buffered = task.pop("_buffer", [])
        for msg in buffered:
            q.put(msg)

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


def _extract_json(output):
    """Robustly extract JSON dict from agent output (string or dict)."""
    if output is None:
        return {}
    if isinstance(output, dict):
        return output
    if not isinstance(output, str):
        output = str(output)
    # Try direct JSON parse
    text = output.strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # Extract JSON from markdown code block
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    # Extract first {...} or [...]
    m = re.search(r'(\{.*\})', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    m = re.search(r'(\[.*\])', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1))
        except Exception:
            pass
    return {}


def _extract_thought(task_name, output):
    if output is None:
        return "正在分析..."

    data = _extract_json(output)

    try:
        lenses = data.get("lenses")
        if lenses:
            names = [l.get("lens_name", "") for l in lenses[:2]]
            suffix = "..." if len(lenses) > 2 else ""
            return f"提炼出 {len(lenses)} 个抽象透镜：{', '.join(names)}{suffix}"

        instances = data.get("instances")
        if instances:
            first = instances[0].get("name", "") if instances else ""
            return f"发现 {len(instances)} 个相关实例，如「{first}」等"

        v_comps = data.get("vertical_comparisons")
        if v_comps is not None:
            v = len(v_comps)
            h = len(data.get("horizontal_comparisons", []))
            return f"完成 {v} 组纵向对比、{h} 组横向对比"

        validated = data.get("validated")
        if validated is not None:
            v = len(validated)
            r = len(data.get("rejected", []))
            return f"验证通过 {v} 条有效共性，剔除 {r} 条伪相关"

        insights = data.get("insights")
        if insights:
            return f"生成 {len(insights)} 个跨维度综合洞察"

        if data.get("core_thesis"):
            return "综合所有证据，构建核心论点与预测"
    except Exception:
        pass

    return f"{AGENT_LABELS.get(task_name, task_name)} 分析完成"


def _run_analysis(task_id, topic, style_preset, language="zh"):
    task = ANALYSIS_TASKS[task_id]

    # Reset blackboard for new analysis
    reset_blackboard()
    blackboard = get_blackboard()

    lang_map = {
        "zh": "所有输出必须使用中文（包括实例名称、分析内容和洞察描述）。",
        "en": "All outputs must be in English (including instance names, analysis content, and insight descriptions).",
    }
    lang_instruction = lang_map.get(language, lang_map["zh"])

    try:
        crew_instance = SpatioTemporalCrew()

        def make_task_callback(task_name):
            def callback(output):
                idx = AGENT_ORDER.index(task_name) if task_name in AGENT_ORDER else 0
                progress_pct = int(((idx + 1) / len(AGENT_ORDER)) * 100)
                task["current_agent"] = task_name
                task["progress"] = progress_pct

                thought = _extract_thought(task_name, output)
                next_agent = AGENT_ORDER[idx + 1] if idx + 1 < len(AGENT_ORDER) else None

                # Get blackboard messages after this agent
                bb_messages = blackboard.read(last_n=20)

                _notify(task_id, {
                    "status": "running",
                    "agent": task_name,
                    "label": AGENT_LABELS.get(task_name, task_name),
                    "progress": progress_pct,
                    "thought": thought,
                    "next_agent": next_agent,
                    "blackboard_messages": bb_messages,
                })
            return callback

        crew_obj = crew_instance.crew()

        # Inject language instruction into all task descriptions
        for t in crew_obj.tasks:
            t.description = t.description + f"\n\n【语言要求 / Language Requirement】{lang_instruction}"

        task_names = [
            "abstraction_task", "vertical_discovery_task", "horizontal_discovery_task",
            "comparison_task", "causal_review_task", "synthesis_task",
        ]
        for t_name in task_names:
            matched = [t for t in crew_obj.tasks if t.name == t_name]
            if matched:
                matched[0].callback = make_task_callback(t_name.replace("_task", ""))

        # ── Step 1: Run Abstracter to get initial lenses ──
        _notify(task_id, {
            "status": "running",
            "agent": "abstracter",
            "label": AGENT_LABELS["abstracter"],
            "progress": 5,
            "thought": f"开始分析「{topic}」，正在提炼抽象透镜...",
        })

        # Create a mini-crew just for abstraction
        abstraction_task = [t for t in crew_obj.tasks if t.name == "abstraction_task"][0]
        abstraction_agent = [a for a in crew_obj.agents if "abstract" in a.role.lower()][0]
        abstraction_crew = Crew(
            agents=[abstraction_agent],
            tasks=[abstraction_task],
            process=Process.sequential,
        )
        abstraction_result = abstraction_crew.kickoff(inputs={"topic": topic})

        # Extract lenses
        lenses = []
        if abstraction_task.output:
            data = _extract_json(abstraction_task.output)
            try:
                lenses = [l.get("lens_name", "") for l in data.get("lenses", [])]
            except Exception:
                pass

        # ── Step 2: Brainstorm Room — Multi-round discussion ──
        if lenses:
            _notify(task_id, {
                "status": "running",
                "agent": "brainstorm",
                "label": "Brainstorm Room — 多轮讨论",
                "progress": 15,
                "thought": f"抽象透镜已提炼：{', '.join(lenses[:2])}... 启动头脑风暴会议室",
            })

            # Get agent instances
            vertical_agent = None
            horizontal_agent = None
            abstracter_agent = None
            for agent in crew_obj.agents:
                if "vertical" in agent.role.lower():
                    vertical_agent = agent
                elif "horizontal" in agent.role.lower():
                    horizontal_agent = agent
                elif "abstract" in agent.role.lower():
                    abstracter_agent = agent

            if vertical_agent and horizontal_agent and abstracter_agent:
                room = BrainstormRoom(
                    vertical_agent=vertical_agent,
                    horizontal_agent=horizontal_agent,
                    abstracter_agent=abstracter_agent,
                    max_rounds=3,
                )
                brainstorm_result = room.run(topic=topic, lenses=lenses)

                # Update lenses with refined ones
                if brainstorm_result.get("final_lenses"):
                    lenses = brainstorm_result["final_lenses"]

                # Inject brainstorm results into remaining tasks
                brainstorm_summary = brainstorm_result.get("discussion_summary", "")
                for t in crew_obj.tasks:
                    if t.name != "abstraction_task":
                        t.description = t.description + f"\n\n【头脑风暴讨论摘要】{brainstorm_summary[:500]}...\n最终透镜：{', '.join(lenses)}"

                _notify(task_id, {
                    "status": "running",
                    "agent": "brainstorm",
                    "label": "Brainstorm Room — 多轮讨论",
                    "progress": 30,
                    "thought": f"头脑风暴完成！共 {brainstorm_result['rounds']} 轮讨论。最终透镜：{', '.join(lenses[:2])}...",
                    "blackboard_messages": len(brainstorm_result.get("messages", [])),
                })

        # ── Step 3: Run remaining tasks (Vertical, Horizontal, Comparator, etc.) ──
        _notify(task_id, {
            "status": "running",
            "agent": "vertical_discovery",
            "label": AGENT_LABELS["vertical_discovery"],
            "progress": 35,
            "thought": "头脑风暴结束，继续执行分析流水线...",
        })

        # Remove abstraction task (already done)
        remaining_tasks = [t for t in crew_obj.tasks if t.name != "abstraction_task"]
        remaining_agents = [a for a in crew_obj.agents if "abstract" not in a.role.lower()]

        # Create new crew with remaining tasks (sequential since CrewAI 1.x doesn't support parallel)
        remaining_crew = Crew(
            agents=remaining_agents,
            tasks=remaining_tasks,
            process=Process.sequential,
            verbose=True,
        )
        remaining_result = remaining_crew.kickoff(inputs={"topic": topic})

        # ── Direct slide generation from structured task outputs ──
        # Combine outputs from both crews
        all_tasks = [t for t in crew_obj.tasks if t.name == "abstraction_task"]
        all_tasks += list(remaining_crew.tasks)

        lenses = []
        v_instances = []
        h_instances = []
        v_comparisons = []
        h_comparisons = []
        validated = []
        rejected = []
        insights = []
        thesis = ""
        prediction = ""
        recommendations = []

        for t in all_tasks:
            output = t.output
            if output is None:
                continue

            data = _extract_json(output)
            if not data:
                continue

            if t.name == "abstraction_task":
                try:
                    lenses = [l.get("lens_name", "") for l in data.get("lenses", [])]
                except Exception:
                    pass
            elif t.name == "vertical_discovery_task":
                try:
                    v_instances = [
                        {
                            "name": i.get("name", ""),
                            "era_or_domain": i.get("era_or_domain", ""),
                            "brief": i.get("brief", ""),
                        }
                        for i in data.get("instances", [])
                    ]
                except Exception:
                    pass
            elif t.name == "horizontal_discovery_task":
                try:
                    h_instances = [
                        {
                            "name": i.get("name", ""),
                            "era_or_domain": i.get("era_or_domain", ""),
                            "brief": i.get("brief", ""),
                        }
                        for i in data.get("instances", [])
                    ]
                except Exception:
                    pass
            elif t.name == "comparison_task":
                try:
                    v_comparisons = [
                        {
                            "instance_name": c.get("instance_name", ""),
                            "instance_era_or_domain": c.get("instance_era_or_domain", ""),
                            "commonalities": c.get("commonalities", []),
                            "distinctions": c.get("distinctions", []),
                            "insight": c.get("insight", ""),
                        }
                        for c in data.get("vertical_comparisons", [])
                    ]
                    h_comparisons = [
                        {
                            "instance_name": c.get("instance_name", ""),
                            "instance_era_or_domain": c.get("instance_era_or_domain", ""),
                            "commonalities": c.get("commonalities", []),
                            "distinctions": c.get("distinctions", []),
                            "insight": c.get("insight", ""),
                        }
                        for c in data.get("horizontal_comparisons", [])
                    ]
                except Exception:
                    pass
            elif t.name == "causal_review_task":
                try:
                    validated = [
                        {
                            "commonality": v.get("commonality", ""),
                            "causal_chain": v.get("causal_chain", ""),
                            "confidence": v.get("confidence", 0.5),
                        }
                        for v in data.get("validated", [])
                    ]
                    rejected = [
                        {
                            "commonality": r.get("commonality", ""),
                            "rejection_reason": r.get("rejection_reason", ""),
                        }
                        for r in data.get("rejected", [])
                    ]
                except Exception:
                    pass
            elif t.name == "synthesis_task":
                try:
                    thesis = data.get("core_thesis", "")
                    prediction = data.get("prediction", "")
                    insights = [
                        {
                            "title": i.get("title", ""),
                            "description": i.get("description", ""),
                            "vertical_evidence": i.get("vertical_evidence", ""),
                            "horizontal_evidence": i.get("horizontal_evidence", ""),
                            "implication": i.get("implication", ""),
                        }
                        for i in data.get("insights", [])
                    ]
                    recommendations = data.get("recommendations", [])
                except Exception:
                    pass

        _notify(task_id, {
            "status": "running",
            "agent": "visualization_agent",
            "label": AGENT_LABELS["visualization_agent"],
            "progress": 95,
            "thought": "正在生成演示文稿...",
        })

        slide_tool = SlideGeneratorTool()
        slide_tool._run(
            topic=topic,
            lenses_json=json.dumps(lenses, ensure_ascii=False),
            vertical_instances_json=json.dumps(v_instances, ensure_ascii=False),
            horizontal_instances_json=json.dumps(h_instances, ensure_ascii=False),
            vertical_comparisons_json=json.dumps(v_comparisons, ensure_ascii=False),
            horizontal_comparisons_json=json.dumps(h_comparisons, ensure_ascii=False),
            validated_commonalities_json=json.dumps(validated, ensure_ascii=False),
            rejected_commonalities_json=json.dumps(rejected, ensure_ascii=False),
            insights_json=json.dumps(insights, ensure_ascii=False),
            core_thesis=thesis,
            prediction=prediction,
            recommendations_json=json.dumps(recommendations, ensure_ascii=False),
            style_preset=style_preset,
        )

        output_files = list(TASKS_DIR.glob("*.html"))
        if output_files:
            latest = max(output_files, key=lambda p: p.stat().st_mtime)
            task["result_file"] = str(latest)

        task["status"] = "completed"
        task["progress"] = 100

        # Get blackboard discussion summary
        bb_stats = blackboard.get_stats()
        bb_summary = blackboard.get_summary()

        _notify(task_id, {
            "status": "completed",
            "progress": 100,
            "result_file": task["result_file"],
            "thought": f"分析完成！共提炼 {len(lenses)} 个透镜，发现 {len(v_instances)} 个历史实例和 {len(h_instances)} 个跨领域实例。讨论板共 {bb_stats['total_messages']} 条消息。",
            "blackboard_messages": bb_stats["total_messages"],
            "blackboard_summary": bb_summary,
        })

    except Exception as e:
        task["status"] = "error"
        task["error"] = str(e)
        _notify(task_id, {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
        })


def _notify(task_id, msg):
    task = ANALYSIS_TASKS.get(task_id)
    if not task:
        return
    q = task.get("_queue")
    if q is not None:
        q.put(msg)
    else:
        # Buffer messages until queue is ready
        task.setdefault("_buffer", []).append(msg)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=True, port=port)
