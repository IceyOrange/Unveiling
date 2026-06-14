"""Run Unveiling analysis with verbose per-node logging."""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime

from dotenv import load_dotenv

from unveiling.graph.build import build_graph
from unveiling.models._enums import Phase
from unveiling.models.state import State

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger("unveiling.run")

QUESTION = "AI 焦虑"


def main():
    state = State(user_question=QUESTION)
    graph = build_graph()

    logger.info("=" * 70)
    logger.info("Starting analysis: %s", QUESTION)
    logger.info("=" * 70)

    accumulated = {}
    round_num = 0

    for chunk in graph.stream(state, {"recursion_limit": 100}):
        for node_name, updates in chunk.items():
            round_num += 1
            ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            print(f"\n{'='*72}", flush=True)
            print(f"[{ts}] ROUND {round_num} ── NODE: {node_name}", flush=True)
            print(f"{'='*72}", flush=True)

            _print_updates(node_name, updates)

            # Accumulate phase for display
            if "phase" in updates:
                accumulated["phase"] = updates["phase"]
            if "round_count" in updates:
                accumulated["round_count"] = updates["round_count"]
            if "token_spent" in updates:
                accumulated["token_spent"] = updates["token_spent"]
            if "next_agent" in updates:
                accumulated["next_agent"] = updates["next_agent"]
            if "target_sub_question_id" in updates:
                accumulated["target_sub_question_id"] = updates["target_sub_question_id"]

            phase_val = accumulated.get("phase", Phase.inception)
            phase_str = phase_val.value if hasattr(phase_val, "value") else str(phase_val)
            print(
                f"  ── phase={phase_str}  round={accumulated.get('round_count', '?')}  "
                f"tokens={accumulated.get('token_spent', 0)}  "
                f"next_agent={accumulated.get('next_agent', '?')}  "
                f"target_sq={accumulated.get('target_sub_question_id', '?')[:12]}",
                flush=True,
            )

    print(f"\n{'#'*72}", flush=True)
    print(f"ANALYSIS COMPLETE — {round_num} rounds total", flush=True)
    print(f"{'#'*72}", flush=True)


def _print_updates(node_name: str, updates: dict):
    for key, value in updates.items():
        if key == "schedule_log":
            for entry in value:
                deg = " ⚠️ DEGRADATION" if entry.degradation_flag else ""
                print(f"  📋 schedule_log: decision={entry.decision}", flush=True)
                print(f"     author={entry.author}  role={entry.role}{deg}", flush=True)
                print(f"     reason: {entry.reason}", flush=True)

        elif key == "issue_tree":
            for node in value:
                status = node.node_status.value if hasattr(node.node_status, "value") else str(node.node_status)
                parent = node.parent_id or "ROOT"
                print(
                    f"  🌳 issue_tree: [{status}] parent={parent[:12]}  "
                    f"content={node.content[:80]}",
                    flush=True,
                )

        elif key == "hypothesis_zone":
            for record in value:
                rtype = type(record).__name__
                if rtype == "LensRecord":
                    print(f"  🔮 lens: name={record.name}", flush=True)
                    print(f"     rationale: {record.rationale[:120] if record.rationale else 'N/A'}", flush=True)
                    print(f"     parent_lens={record.parent_lens_id}", flush=True)
                elif rtype == "PredictionRecord":
                    ps = record.prediction_status.value if hasattr(record.prediction_status, "value") else str(record.prediction_status)
                    print(f"  📊 prediction [{ps}]: {record.claim[:100]}", flush=True)
                    print(f"     killer_evidence: {record.killer_evidence[:100] if record.killer_evidence else 'N/A'}", flush=True)

        elif key == "evidence_zone":
            for ev in value:
                layer = ev.layer.value if hasattr(ev.layer, "value") else str(ev.layer)
                conf = ev.confidence.value if hasattr(ev.confidence, "value") else str(ev.confidence)
                unexpected = " ⚡UNEXPECTED" if ev.is_unexpected else ""
                print(
                    f"  📎 evidence [{layer}/{conf}]{unexpected}: "
                    f"{ev.content[:120]}",
                    flush=True,
                )
                print(
                    f"     source_lens={ev.source_lens_id[:12] if ev.source_lens_id else 'N/A'}  "
                    f"sub_q={ev.sub_question_id[:12] if ev.sub_question_id else 'N/A'}",
                    flush=True,
                )

        elif key == "debate_zone":
            for d in value:
                print(f"  ⚔️  debate round={d.round}: {d.question[:100]}", flush=True)
                print(f"     response: {d.response[:120] if d.response else 'N/A'}", flush=True)

        elif key == "conclusion_zone":
            for c in value:
                print(f"  📝 conclusion:", flush=True)
                print(f"     finding: {c.convergent_finding[:120]}", flush=True)
                print(f"     tension: {c.tension[:120] if c.tension else 'N/A'}", flush=True)
                print(f"     boundary: {c.boundary_condition[:120] if c.boundary_condition else 'N/A'}", flush=True)
                print(f"     unresolved: {c.unresolved[:120] if c.unresolved else 'N/A'}", flush=True)
                print(f"     implication: {c.implication[:120] if c.implication else 'N/A'}", flush=True)

        elif key == "phase":
            phase_val = value.value if hasattr(value, "value") else str(value)
            print(f"  🔄 phase → {phase_val}", flush=True)

        elif key in ("round_count", "token_spent", "next_agent", "target_sub_question_id"):
            print(f"  🔧 {key} = {value}", flush=True)

        elif key == "attempt_counters":
            for sq_id, count in value.items():
                print(f"  🔧 attempt_counter: {sq_id[:12]} → {count}", flush=True)

        else:
            # Catch-all for anything we haven't handled
            val_str = str(value)[:200]
            print(f"  ❓ {key}: {val_str}", flush=True)


if __name__ == "__main__":
    main()
