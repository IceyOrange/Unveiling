from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from queue import Queue
from threading import Thread

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from graph.build import build_graph
from models._enums import EvidenceConfidence, EvidenceLayer, NodeStatus, Phase, PredictionStatus
from models.blackboard import (
    ConclusionRecord,
    DebateRecord,
    EvidenceRecord,
    IssueTreeNode,
    LensRecord,
    PredictionRecord,
    ScheduleLogEntry,
)
from models.state import State
from frontend.payload import latest_issue_tree, serialize_state
from frontend.slides.generator import generate_slides

load_dotenv()

app = Flask(__name__, template_folder="templates", static_folder="static")

_PROMPT_LAB_DIR = project_root / "prompt_lab"

_tasks: dict[str, dict] = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    mode = data.get("mode", "balance")
    language = data.get("language", "中文")
    if not question:
        return {"error": "question is required"}, 400

    task_id = str(uuid.uuid4())
    _tasks[task_id] = {
        "question": question,
        "mode": mode,
        "status": "running",
        "result": None,
        "queue": Queue(),
    }

    thread = Thread(target=_run_analysis, args=(task_id, question, mode, language), daemon=True)
    thread.start()

    return {"task_id": task_id}


@app.route("/progress/<task_id>")
def progress(task_id: str):
    if task_id not in _tasks:
        return {"error": "task not found"}, 404

    def event_stream():
        queue = _tasks[task_id]["queue"]
        while True:
            event = queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(
        stream_with_context(event_stream()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/result/<task_id>")
def result(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        return {"error": "task not found"}, 404
    if task["status"] == "running":
        return {"status": "running"}, 202
    if task["status"] == "error":
        return {"status": "error", "error": task.get("error", "unknown error")}, 200
    return task["result"]


@app.route("/demo-result")
def demo_result():
    return _demo_result()


@app.route("/deck/<task_id>")
def deck(task_id: str):
    """Render the Unveiling Paper deck as an embeddable HTML fragment.

    Used by the result page's top-half iframe. `task_id == "demo"` short-circuits
    to the canned demo payload so the home-page "查看示例输出" flow works
    without a real run.
    """
    if task_id == "demo":
        payload = _demo_result()
    else:
        task = _tasks.get(task_id)
        if not task:
            return Response("task not found", status=404, mimetype="text/plain")
        if task["status"] != "done":
            return Response("task not ready", status=409, mimetype="text/plain")
        payload = task["result"]

    html = generate_slides(payload, embed=True)
    return Response(html, mimetype="text/html")


def _run_analysis(task_id: str, question: str, mode: str, language: str = "中文") -> None:
    """Run analysis graph; stream rich events; serialise final state."""
    queue: Queue = _tasks[task_id]["queue"]

    def emit(event: dict) -> None:
        queue.put(event)

    accumulated: dict = {
        "issue_tree": [],
        "hypothesis_zone": [],
        "evidence_zone": [],
        "debate_zone": [],
        "conclusion_zone": [],
        "schedule_log": [],
        "phase": Phase.inception,
        "degradation_count": 0,
        "round_count": 0,
        "token_spent": 0,
        "user_question": question,
        "output_language": language,
    }

    seen_lens_ids: set[str] = set()
    seen_evidence_ids: set[str] = set()
    seen_debate_ids: set[str] = set()
    seen_prediction_state: dict[str, str] = {}
    seen_node_state: dict[str, str] = {}
    last_phase = Phase.inception

    try:
        emit({"type": "started", "question": question, "mode": mode})

        graph = build_graph()
        initial = State(user_question=question, output_language=language)

        for chunk in graph.stream(initial, {"recursion_limit": 100}):
            for node_name, updates in chunk.items():
                _accumulate(accumulated, updates)
                events = _build_events(
                    node_name,
                    updates,
                    accumulated,
                    seen_lens_ids,
                    seen_evidence_ids,
                    seen_debate_ids,
                    seen_prediction_state,
                    seen_node_state,
                    last_phase,
                )
                last_phase = accumulated["phase"]
                for ev in events:
                    emit(ev)

        final_state = State(**{k: v for k, v in accumulated.items() if k in State.model_fields})
        _tasks[task_id]["result"] = serialize_state(final_state)
        _tasks[task_id]["status"] = "done"
        emit({"type": "done"})
    except Exception as exc:  # noqa: BLE001
        _tasks[task_id]["status"] = "error"
        _tasks[task_id]["error"] = str(exc)
        emit({"type": "error", "error": str(exc)})
    finally:
        queue.put(None)


def _accumulate(state: dict, updates: dict) -> None:
    """Mirror LangGraph's reducer logic into our local snapshot."""
    list_fields = {
        "issue_tree",
        "hypothesis_zone",
        "evidence_zone",
        "debate_zone",
        "conclusion_zone",
        "schedule_log",
    }
    for key, value in updates.items():
        if key in list_fields and isinstance(value, list):
            state[key].extend(value)
        elif key in state:
            state[key] = value


def _build_events(
    node_name: str,
    updates: dict,
    accumulated: dict,
    seen_lens: set[str],
    seen_evidence: set[str],
    seen_debate: set[str],
    seen_pred: dict[str, str],
    seen_node: dict[str, str],
    last_phase: Phase,
) -> list[dict]:
    """Translate an accumulated update into one or more UI events."""
    events: list[dict] = []
    current_phase = accumulated["phase"]
    phase_str = current_phase.value if hasattr(current_phase, "value") else str(current_phase)

    if current_phase != last_phase:
        events.append({"type": "phase", "phase": phase_str})

    issue_tree_snapshot = latest_issue_tree(accumulated["issue_tree"])
    events.append(
        {
            "type": "issue_tree",
            "phase": phase_str,
            "tree": [_node_to_dict(n) for n in issue_tree_snapshot],
            "active_sub_question_id": _active_sub_question(accumulated, node_name),
            "round_count": accumulated.get("round_count", 0),
        }
    )

    new_logs = updates.get("schedule_log", []) or []
    if new_logs:
        latest_log: ScheduleLogEntry = new_logs[-1]
        narration = _humanize_narration(latest_log, node_name, issue_tree_snapshot)
        if narration:
            events.append(
                {
                    "type": "narration",
                    "text": narration,
                    "author": latest_log.author,
                    "degradation": bool(latest_log.degradation_flag),
                }
            )
        if latest_log.degradation_flag:
            events.append(
                {
                    "type": "bubble",
                    "kind": "degradation",
                    "title": "降级",
                    "detail": latest_log.reason,
                }
            )

    for record in updates.get("hypothesis_zone", []) or []:
        if isinstance(record, LensRecord) and record.id not in seen_lens:
            seen_lens.add(record.id)
            kind = "lens_initial" if record.parent_lens_id is None else "lens_evolved"
            title = "新透镜" if record.parent_lens_id is None else "透镜演化"
            events.append(
                {
                    "type": "bubble",
                    "kind": kind,
                    "title": title,
                    "detail": record.name,
                }
            )
        elif isinstance(record, PredictionRecord):
            prev = seen_pred.get(record.id)
            current = record.prediction_status.value if hasattr(record.prediction_status, "value") else str(record.prediction_status)
            seen_pred[record.id] = current
            if prev is None:
                events.append(
                    {
                        "type": "bubble",
                        "kind": "prediction_new",
                        "title": "可证伪预判",
                        "detail": record.claim,
                    }
                )
            elif prev != current and current in {"supported", "refuted", "modified"}:
                label = {"supported": "预判被支持", "refuted": "预判被驳斥", "modified": "预判被修正"}[current]
                events.append(
                    {
                        "type": "bubble",
                        "kind": f"prediction_{current}",
                        "title": label,
                        "detail": record.claim,
                    }
                )

    for record in updates.get("evidence_zone", []) or []:
        if record.id in seen_evidence:
            continue
        seen_evidence.add(record.id)
        layer = record.layer.value if hasattr(record.layer, "value") else str(record.layer)
        if record.is_unexpected:
            kind = "evidence_unexpected"
            title = "意外发现"
        elif layer == "structure":
            kind = "evidence_structure"
            title = "结构层证据"
        elif layer == "mechanism":
            kind = "evidence_mechanism"
            title = "机制层证据"
        else:
            continue
        events.append(
            {
                "type": "bubble",
                "kind": kind,
                "title": title,
                "detail": record.content[:120],
            }
        )

    for record in updates.get("debate_zone", []) or []:
        if record.id in seen_debate:
            continue
        seen_debate.add(record.id)
        events.append(
            {
                "type": "bubble",
                "kind": "debate",
                "title": f"辩论 · 回合 {record.round}",
                "detail": record.question[:120],
            }
        )

    for node in issue_tree_snapshot:
        if node.parent_id is None:
            continue
        status = node.node_status.value if hasattr(node.node_status, "value") else str(node.node_status)
        if seen_node.get(node.id) == status:
            continue
        if status in {"closed", "stuck"}:
            kind = f"sub_question_{status}"
            title = "子问题闭合" if status == "closed" else "子问题卡住"
            events.append(
                {
                    "type": "bubble",
                    "kind": kind,
                    "title": title,
                    "detail": node.content[:120],
                }
            )
        seen_node[node.id] = status

    return events


def _node_to_dict(node: IssueTreeNode) -> dict:
    return {
        "id": node.id,
        "content": node.content,
        "status": node.node_status.value if hasattr(node.node_status, "value") else str(node.node_status),
        "parent_id": node.parent_id,
    }


def _active_sub_question(accumulated: dict, node_name: str) -> str | None:
    """Best-effort guess at the sub-question being advanced right now."""
    if node_name in {"convergence_node", "inception_node"}:
        return None
    for log in reversed(accumulated["schedule_log"]):
        text = f"{log.decision} {log.reason}"
        for node in latest_issue_tree(accumulated["issue_tree"]):
            if node.parent_id is None:
                continue
            if node.id and node.id[:8] in text:
                return node.id
    exploring = [n for n in latest_issue_tree(accumulated["issue_tree"]) if n.parent_id is not None and n.node_status == NodeStatus.exploring]
    if exploring:
        return exploring[0].id
    return None


def _humanize_narration(log: ScheduleLogEntry, node_name: str, tree: list[IssueTreeNode]) -> str:
    """Compose a one-sentence narration about what the system is doing."""
    decision = log.decision or ""
    reason = log.reason or ""
    node_label = node_name.replace("_node", "")

    if log.degradation_flag:
        return reason[:80] or "已切换降级路径"

    if decision == "convergence_complete":
        return "正在合成张力式结论"

    mapping = {
        "search_lateral": "正在做横向类比搜索",
        "search_vertical": "正在做纵向跨时期搜索",
        "deepdig": "正在向更深层级追问",
        "lens_op": "正在调整或新增透镜",
        "debate": "正在发起质疑回合",
        "prediction_check": "正在检验可证伪预判",
        "inception": "正在建立问题树与初始透镜",
    }
    base = mapping.get(node_label)
    if base:
        return base + (f"——{reason[:60]}" if reason else "")
    if decision:
        return f"{node_label}：{decision[:60]}"
    return f"{node_label} 完成"


def _demo_result() -> dict:
    """Static demo payload so the result screen can be inspected without running the graph."""
    return {
        "driving_question": "AI 公司现在应不应该烧钱扩张？",
        "driving_question_record": "AI 公司现在应不应该烧钱扩张？",
        "phase": "convergence",
        "integrity": {
            "sub_questions_total": 5,
            "sub_questions_closed": 4,
            "sub_questions_stuck": 1,
            "killer_evidence_total": 8,
            "killer_evidence_confirmed": 5,
            "lens_evolution_depth": 3,
            "lens_initial_count": 3,
            "degradation_count": 2,
            "round_count": 37,
            "token_spent": 16459,
        },
        "sub_questions": [
            {
                "id": "sq-1",
                "content": "现金消耗的边界在哪里？",
                "status": "closed",
                "minimum_viable_answer": "每月烧≥总现金 12% 是关键警戒线。",
                "evidence_count": 6,
                "structure_layer_count": 2,
                "mechanism_layer_count": 3,
                "unexpected_count": 1,
                "top_evidence": [
                    {
                        "content": "2001 互联网泡沫期间，月烧>15% 的公司 9 个月内倒闭率达 78%。",
                        "layer": "structure",
                        "confidence": "strong",
                        "is_unexpected": False,
                        "sub_question_id": "sq-1",
                        "source_lens_id": "lens-1",
                        "source_lens_version": "v2",
                    }
                ],
                "conclusion": {
                    "convergent_finding": "12% 月烧率是横跨多个时代的失败警戒线。",
                    "tension": "扩张速度的诱惑与生存窗口的硬约束之间的紧张关系。",
                    "boundary_condition": "在资本通道顺畅时此界限可上移；通道收紧时下移。",
                    "unresolved": "AI 行业的资本密度是否结构性改变这条界限？",
                    "implication": "判断烧钱合理性应先算月烧/总现金比例，超 12% 即需重新评估。",
                    "references": [],
                },
            },
            {
                "id": "sq-2",
                "content": "哪些扩张能形成可防御的护城河？",
                "status": "closed",
                "minimum_viable_answer": "数据/网络效应 >> 用户补贴。",
                "evidence_count": 4,
                "structure_layer_count": 1,
                "mechanism_layer_count": 2,
                "unexpected_count": 1,
                "top_evidence": [],
                "conclusion": None,
            },
            {
                "id": "sq-3",
                "content": "资本来源对扩张方式的影响？",
                "status": "closed",
                "minimum_viable_answer": "VC 驱动的扩张比战略融资更短视。",
                "evidence_count": 3,
                "structure_layer_count": 0,
                "mechanism_layer_count": 2,
                "unexpected_count": 0,
                "top_evidence": [],
                "conclusion": None,
            },
            {
                "id": "sq-4",
                "content": "替代策略的比较有效性？",
                "status": "stuck",
                "minimum_viable_answer": None,
                "evidence_count": 1,
                "structure_layer_count": 0,
                "mechanism_layer_count": 0,
                "unexpected_count": 0,
                "top_evidence": [],
                "conclusion": None,
            },
            {
                "id": "sq-5",
                "content": "退出窗口（IPO/被收购）的决定性因素？",
                "status": "closed",
                "minimum_viable_answer": "退出窗口由资本市场情绪主导，与基本面脱钩。",
                "evidence_count": 5,
                "structure_layer_count": 2,
                "mechanism_layer_count": 1,
                "unexpected_count": 2,
                "top_evidence": [],
                "conclusion": None,
            },
        ],
        "lens_chains": [
            {
                "chain": [
                    {"id": "l1-v1", "name": "黄金热 1849", "rationale": "矿工烧钱买装备和矿权，希望在他人之前挖到金子。", "parent_id": None},
                    {"id": "l1-v2", "name": "黄金热 1849 · 修正版", "rationale": "辩论后修正：强调'信息不对称'比'速度'更关键。", "parent_id": "l1-v1"},
                ]
            },
            {
                "chain": [
                    {"id": "l2-v1", "name": "火箭升空", "rationale": "燃料过少坠落，过多浪费。框架烧钱为必要但危险的加速阶段。", "parent_id": None},
                    {"id": "l2-v2", "name": "火箭升空 · 分裂", "rationale": "分裂出'逃逸速度'子透镜——市场份额阈值。", "parent_id": "l2-v1"},
                    {"id": "l2-v3", "name": "火箭升空 · 整合", "rationale": "整合返回参数指标体系。", "parent_id": "l2-v2"},
                ]
            },
            {
                "chain": [
                    {"id": "l3-v1", "name": "生物变态发育", "rationale": "毛毛虫吃储能成蝴蝶，过度进食致死。强调清晰的转化目标与生存约束。", "parent_id": None},
                ]
            },
        ],
        "predictions": [
            {
                "id": "p1",
                "claim": "烧钱扩张的 AI 公司将获得市场主导和更高长期利润。",
                "status": "refuted",
                "killer_evidence": "至少 5 家同类公司在烧完资金后未实现市场主导。",
                "if_true_we_should_see": "TOP 烧钱者的 5 年留存率高于行业均值。",
                "if_false_we_should_see": "TOP 烧钱者的 5 年留存率与行业均值无显著差。",
            },
            {
                "id": "p2",
                "claim": "烧钱只在有可防御护城河时合理。",
                "status": "supported",
                "killer_evidence": "存在反例：无护城河仍长期烧钱的公司均失败。",
                "if_true_we_should_see": "无护城河的烧钱公司多数 5 年内退出市场。",
                "if_false_we_should_see": "无护城河的烧钱公司同样能存活至少 5 年。",
            },
            {
                "id": "p3",
                "claim": "投资人情绪是烧钱可持续的主要决定因素。",
                "status": "pending",
                "killer_evidence": "估值高峰期的烧钱率显著高于估值低谷期。",
                "if_true_we_should_see": "估值期与烧钱率正相关。",
                "if_false_we_should_see": "估值期与烧钱率无关或负相关。",
            },
        ],
        "evidence": [],
        "debates": [],
        "conclusion": {
            "convergent_finding": "烧钱是高风险赌注；只有在它能换来可防御护城河时才值得。",
            "tension": "抢占市场份额的扩张速度 ⟷ 烧钱失败的财务风险，返回率不确定时尤其尖锐——而替代策略也需要前置投入。",
            "boundary_condition": "成立于：高竞争压力 + 不可预测的市场时机；失效于：已有可规模化盈利模型，或资本通道无忧。",
            "unresolved": "烧钱与成功是因果还是幸存者偏差？替代策略与烧钱的定量对比仍未量化。",
            "implication": "对原始问题：烧钱扩张的合理性应建立在'可防御护城河 + 资本通道可见性'双重前提之上；缺一不可。",
            "references": [],
        },
    }


# ============================================================================
# Prompt Lab
# ============================================================================

def _load_prompt_meta() -> dict:
    meta_path = _PROMPT_LAB_DIR / "meta.json"
    if not meta_path.exists():
        return {}
    return json.loads(meta_path.read_text(encoding="utf-8"))


@app.route("/prompt-lab")
def prompt_lab_page():
    return render_template("prompt-lab.html")


@app.route("/api/prompts")
def api_list_prompts():
    meta = _load_prompt_meta()
    result = []
    for name, info in meta.items():
        result.append({
            "name": name,
            "label": info.get("label", name),
            "source": info.get("source", ""),
        })
    return jsonify(result)


@app.route("/api/prompts/<name>")
def api_get_prompt(name: str):
    meta = _load_prompt_meta()
    if name not in meta:
        return jsonify({"error": "not found"}), 404
    prompt_path = _PROMPT_LAB_DIR / f"{name}.txt"
    if not prompt_path.exists():
        return jsonify({"error": "prompt file missing"}), 404
    info = meta[name]
    return jsonify({
        "name": name,
        "label": info.get("label", name),
        "source": info.get("source", ""),
        "text": prompt_path.read_text(encoding="utf-8"),
        "variables": info.get("variables", []),
        "var_labels": info.get("var_labels", {}),
        "defaults": info.get("defaults", {}),
        "json_mode": info.get("json_mode", True),
        "temperature": info.get("temperature", 0.5),
    })


@app.route("/api/prompts/<name>", methods=["PUT"])
def api_save_prompt(name: str):
    meta = _load_prompt_meta()
    if name not in meta:
        return jsonify({"error": "not found"}), 404
    data = request.get_json() or {}
    text = data.get("text", "")
    prompt_path = _PROMPT_LAB_DIR / f"{name}.txt"
    prompt_path.write_text(text, encoding="utf-8")
    # Also update the in-memory prompt if abstraction
    if name == "abstraction":
        from llm import abstraction as _abs_mod
        _abs_mod._ABSTRACTION_PROMPT = text
    return jsonify({"ok": True, "saved": name})


@app.route("/api/prompts/<name>/run", methods=["POST"])
def api_run_prompt(name: str):
    meta = _load_prompt_meta()
    if name not in meta:
        return jsonify({"error": "not found"}), 404
    info = meta[name]
    data = request.get_json() or {}

    # Get prompt text (from request if edited, else from file)
    prompt_template = data.get("text", "") or (
        _PROMPT_LAB_DIR / f"{name}.txt"
    ).read_text(encoding="utf-8")

    # Get variable values
    inputs = data.get("inputs", {})
    language = data.get("language", "中文")

    # Substitute variables
    try:
        rendered = prompt_template
        for var_name in info.get("variables", []):
            value = inputs.get(var_name, info.get("defaults", {}).get(var_name, ""))
            rendered = rendered.replace(f"{{{var_name}}}", str(value))
    except Exception as e:
        return jsonify({"error": f"variable substitution failed: {e}"}), 400

    # Call LLM
    from llm.client import LLMClient
    json_mode = info.get("json_mode", True)
    temperature = info.get("temperature", 0.5)

    try:
        client = LLMClient(language=language)
        content, tokens = client.chat(
            [{"role": "user", "content": rendered}],
            json_mode=json_mode,
            temperature=temperature,
        )
    except Exception as e:
        return jsonify({"error": str(e), "output": ""}), 500

    # Try to parse as JSON for pretty display
    parsed = None
    raw = content
    if json_mode:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            pass

    return jsonify({
        "output": raw,
        "parsed": parsed,
        "tokens": tokens,
        "json_mode": json_mode,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
