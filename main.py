from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from graph.build import build_graph
from models._enums import Phase
from models.state import State


def main() -> None:
    parser = argparse.ArgumentParser(description="Unveiling — Multi-agent analogy analysis")
    parser.add_argument("--question", "-q", required=True, help="Driving question to analyze")
    parser.add_argument("--context", "-c", default="", help="Optional user context")
    parser.add_argument(
        "--mode",
        "-m",
        choices=["focus", "balance", "explore"],
        default="balance",
        help="Analysis mode: focus (near), balance, explore (far)",
    )
    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=100,
        help="LangGraph recursion limit (default: 100)",
    )
    args = parser.parse_args()

    load_dotenv()

    state = State(user_question=args.question)

    print(f"Unveiling analysis starting...")
    print(f"Question: {args.question}")
    print(f"Mode: {args.mode}")
    print("-" * 60)

    graph = build_graph()
    step = 0
    result = None
    for chunk in graph.stream(state, {"recursion_limit": args.recursion_limit}):
        for node_name, updates in chunk.items():
            step += 1
            logs = updates.get("schedule_log", [])
            log_msg = ""
            if logs:
                last_log = logs[-1]
                log_msg = f" | {last_log.decision}: {last_log.reason[:80]}"
            print(f"  [{step:3d}] {node_name}{log_msg}")
            if result is None:
                result = updates
            else:
                for k, v in updates.items():
                    if k in result and isinstance(result[k], list) and isinstance(v, list):
                        result[k].extend(v)
                    else:
                        result[k] = v

    if result is None:
        print("No result produced")
        sys.exit(1)

    print(f"\nAnalysis complete")
    print(f"Phase: {result['phase'].value}")
    print(f"Tokens spent: {result['token_spent']}")
    print(f"Evidence collected: lateral={result.get('lateral_count', 0)}, vertical={result.get('vertical_count', 0)}")
    print("-" * 60)

    # Print lens
    if result.get("hypothesis_zone"):
        lens = result["hypothesis_zone"][-1]
        print(f"\nLens: {lens.name}")
        if lens.entities:
            print("  Entities:")
            for e in lens.entities:
                print(f"    {e.surface} -> {e.structural_role}")
        if lens.relationships:
            print("  Relationships:")
            for r in lens.relationships:
                print(f"    {r.surface} -> {r.structural}")

    # Print conclusion
    if result.get("conclusion_zone"):
        print("\nConclusion")
        c = result["conclusion_zone"][-1]
        print(f"  Core finding: {c.core_finding}")
        print(f"  Tension: {c.tension}")
        print(f"  Boundary: {c.boundary_condition}")
        print(f"  Unresolved: {c.unresolved}")
        print(f"  Implication: {c.implication}")

    # Degradation summary
    degradation_events = [
        e for e in result.get("schedule_log", []) if getattr(e, "degradation_flag", False)
    ]
    if degradation_events:
        print(f"\nDegradation events: {len(degradation_events)}")
        for e in degradation_events:
            print(f"  - {e.author}: {e.reason}")

    # Integrity summary
    total_evidence = len(result.get("evidence_zone", []))
    print(f"\nIntegrity: {total_evidence} evidence records, {len(degradation_events)} degradations")

    # ---- Detailed analysis log ----
    print("\n" + "=" * 60)
    print("DETAILED ANALYSIS LOG")
    print("=" * 60)

    # Schedule log
    print("\n--- Schedule Log ---")
    for i, log in enumerate(result.get("schedule_log", []), 1):
        print(f"  [{i:2d}] {log.author} | {log.decision} | {log.reason}")

    # Evidence breakdown
    evidence_list = result.get("evidence_zone", [])
    if evidence_list:
        lateral_ev = [e for e in evidence_list if e.search_direction.value == "lateral"]
        vertical_ev = [e for e in evidence_list if e.search_direction.value == "vertical"]
        print(f"\n--- Evidence Breakdown ---")
        print(f"  Lateral: {len(lateral_ev)} records")
        print(f"  Vertical: {len(vertical_ev)} records")

        print(f"\n--- Lateral Evidence (sample, first 5) ---")
        for i, e in enumerate(lateral_ev[:5], 1):
            print(f"  [{i}] [{e.layer.value}/{e.confidence.value}] {e.content[:100]}")

        print(f"\n--- Vertical Evidence (sample, first 5) ---")
        for i, e in enumerate(vertical_ev[:5], 1):
            print(f"  [{i}] [{e.layer.value}/{e.confidence.value}] {e.content[:100]}")

    # ---- Write analysis log to tmp/ ----
    _write_log(result)

    if result["phase"] != Phase.convergence:
        print("\nWarning: analysis did not reach convergence phase")
        sys.exit(1)


def _write_log(result: dict) -> None:
    """Write detailed analysis log to tmp/ directory."""
    log_dir = Path("tmp")
    log_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"analysis_{timestamp}.log"

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("UNVEILING ANALYSIS LOG")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    # Meta
    lines.append(f"\nQuestion: {result.get('user_question', 'N/A')}")
    lines.append(f"Phase: {result['phase'].value}")
    lines.append(f"Tokens spent: {result['token_spent']}")
    lines.append(f"Evidence: lateral={result.get('lateral_count', 0)}, vertical={result.get('vertical_count', 0)}")

    # Lens
    if result.get("hypothesis_zone"):
        lens = result["hypothesis_zone"][-1]
        lines.append(f"\n{'=' * 70}")
        lines.append("LENS (Phase 1 Abstraction)")
        lines.append(f"{'=' * 70}")
        lines.append(f"Name: {lens.name}")
        lines.append(f"Rationale: {lens.rationale}")
        if lens.entities:
            lines.append("\nEntities:")
            for e in lens.entities:
                lines.append(f"  {e.surface} -> {e.structural_role}")
        if lens.relationships:
            lines.append("\nRelationships:")
            for r in lens.relationships:
                lines.append(f"  {r.surface} -> {r.structural}")

    # Schedule log
    lines.append(f"\n{'=' * 70}")
    lines.append("SCHEDULE LOG")
    lines.append(f"{'=' * 70}")
    for i, log in enumerate(result.get("schedule_log", []), 1):
        lines.append(f"  [{i:2d}] {log.author} | {log.decision} | {log.reason}")

    # Evidence — full detail
    evidence_list = result.get("evidence_zone", [])
    if evidence_list:
        lateral_ev = [e for e in evidence_list if e.search_direction.value == "lateral"]
        vertical_ev = [e for e in evidence_list if e.search_direction.value == "vertical"]

        lines.append(f"\n{'=' * 70}")
        lines.append(f"EVIDENCE — LATERAL ({len(lateral_ev)} cases)")
        lines.append(f"{'=' * 70}")
        for i, e in enumerate(lateral_ev, 1):
            lines.append(f"\n  [{i}] {e.case_name} [{e.layer.value}/{e.confidence.value}]" + (" [UNEXPECTED]" if e.is_unexpected else ""))
            lines.append(f"  {e.content}")
            lines.append(f"  id={e.id[:8]} lens={e.source_lens_id[:8]}")

        lines.append(f"\n{'=' * 70}")
        lines.append(f"EVIDENCE — VERTICAL ({len(vertical_ev)} cases)")
        lines.append(f"{'=' * 70}")
        for i, e in enumerate(vertical_ev, 1):
            lines.append(f"\n  [{i}] {e.case_name} [{e.layer.value}/{e.confidence.value}]" + (" [UNEXPECTED]" if e.is_unexpected else ""))
            lines.append(f"  {e.content}")
            lines.append(f"  id={e.id[:8]} lens={e.source_lens_id[:8]}")

    # Conclusion
    if result.get("conclusion_zone"):
        lines.append(f"\n{'=' * 70}")
        lines.append("CONCLUSION (Phase 3)")
        lines.append(f"{'=' * 70}")
        c = result["conclusion_zone"][-1]
        lines.append(f"\nCore Finding:\n  {c.core_finding}")
        lines.append(f"\nTension:\n  {c.tension}")
        lines.append(f"\nBoundary Condition:\n  {c.boundary_condition}")
        lines.append(f"\nUnresolved:\n  {c.unresolved}")
        lines.append(f"\nImplication:\n  {c.implication}")

    # Degradation
    degradation_events = [
        e for e in result.get("schedule_log", []) if getattr(e, "degradation_flag", False)
    ]
    if degradation_events:
        lines.append(f"\n{'=' * 70}")
        lines.append(f"DEGRADATION EVENTS ({len(degradation_events)})")
        lines.append(f"{'=' * 70}")
        for e in degradation_events:
            lines.append(f"  - {e.author}: {e.reason}")

    lines.append(f"\n{'=' * 70}")
    lines.append("END OF LOG")
    lines.append(f"{'=' * 70}")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nLog saved to: {log_path.absolute()}")


if __name__ == "__main__":
    main()
