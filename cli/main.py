from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from unveiling.graph.build import build_graph
from shared.log_writer import write_analysis_log
from unveiling.models._enums import Phase
from unveiling.models.state import State


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
        if c.temporal_trajectory:
            print(f"  Temporal trajectory: {c.temporal_trajectory}")
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
    log_path = write_analysis_log(result)
    print(f"\nLog saved to: {log_path.absolute()}")

    if result["phase"] != Phase.convergence:
        print("\nWarning: analysis did not reach convergence phase")
        sys.exit(1)


if __name__ == "__main__":
    main()
