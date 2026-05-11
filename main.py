from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from frontend.slides.generator import generate_slides
from graph.build import build_graph
from models.state import State
from models._enums import Phase


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

    # Map mode to near/far ratio
    mode_ratio = {"focus": 0.8, "balance": 0.5, "explore": 0.2}

    state = State(
        user_question=args.question,
        # Mode ratio can be consumed by scheduler in future iterations
    )

    print(f"🚀 Unveiling analysis starting...")
    print(f"Question: {args.question}")
    print(f"Mode: {args.mode} (near/far ratio: {mode_ratio[args.mode]})")
    print("-" * 60)

    graph = build_graph()
    result = graph.invoke(state, {"recursion_limit": args.recursion_limit})

    print(f"\n✅ Analysis complete")
    print(f"Phase: {result['phase'].value}")
    print(f"Rounds: {result['round_count']}")
    print(f"Tokens spent: {result['token_spent']}")
    print("-" * 60)

    # Print issue tree
    print("\n📋 Issue Tree")
    latest = {}
    for node in result["issue_tree"]:
        latest[node.id] = node
    for node in latest.values():
        if node.parent_id is None:
            print(f"  🎯 {node.content}")
        else:
            status_emoji = {
                "untouched": "⬜",
                "exploring": "🔍",
                "closed": "✅",
                "stuck": "⚠️",
            }.get(node.node_status.value, "❓")
            print(f"    {status_emoji} {node.content}")

    # Print hypothesis zone (latest versions only)
    if result["hypothesis_zone"]:
        print("\n🔮 Hypotheses")
        latest_hypotheses = {}
        for h in result["hypothesis_zone"]:
            latest_hypotheses[h.id] = h
        for h in latest_hypotheses.values():
            if hasattr(h, "name"):
                print(f"  🔍 Lens: {h.name}")
            elif hasattr(h, "claim"):
                print(f"  📊 Prediction: {h.claim} [{h.prediction_status.value}]")

    # Print conclusion
    if result["conclusion_zone"]:
        print("\n📝 Conclusion")
        c = result["conclusion_zone"][-1]
        print(f"  Core finding: {c.convergent_finding}")
        print(f"  Tension: {c.tension}")
        print(f"  Boundary: {c.boundary_condition}")
        print(f"  Unresolved: {c.unresolved}")
        print(f"  Implication: {c.implication}")

    # Degradation summary
    degradation_events = [
        e for e in result["schedule_log"] if getattr(e, "degradation_flag", False)
    ]
    if degradation_events:
        print(f"\n⚠️  Degradation events: {len(degradation_events)}")
        for e in degradation_events:
            print(f"    - {e.author}: {e.reason}")

    # Integrity summary
    closed_count = sum(
        1 for n in latest.values()
        if n.parent_id is not None and n.node_status.value == "closed"
    )
    stuck_count = sum(
        1 for n in latest.values()
        if n.parent_id is not None and n.node_status.value == "stuck"
    )
    total_sub = sum(1 for n in latest.values() if n.parent_id is not None)
    print(f"\n📊 Integrity: {closed_count}/{total_sub} closed, {stuck_count} stuck")

    if result["phase"] != Phase.convergence:
        print("\n⚠️  Warning: analysis did not reach convergence phase")
        sys.exit(1)

    # Generate HTML output
    output_path = Path("output") / f"unveiling_{result['issue_tree'][0].id[:8]}.html"
    output_path.parent.mkdir(exist_ok=True)
    final_state = State(**result)
    generate_slides(final_state, output_path)
    print(f"\n📄 Output: {output_path.absolute()}")


if __name__ == "__main__":
    main()
