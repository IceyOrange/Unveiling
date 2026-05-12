from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.convergence import convergence_node
from agents.inception import inception_node
from agents.search import parallel_search_node
from graph.routing import route_after_scheduler
from models.state import State
from orchestrator.scheduler import scheduler_node


def build_graph():
    builder = StateGraph(State)

    # Phase 1: Abstract
    builder.add_node("inception_node", inception_node)

    # Phase 2: Search (parallel inside one node)
    builder.add_node("parallel_search_node", parallel_search_node)
    builder.add_node("scheduler_node", scheduler_node)

    # Phase 3: Converge
    builder.add_node("convergence_node", convergence_node)

    # Phase 1 → Phase 2
    builder.add_edge(START, "inception_node")
    builder.add_edge("inception_node", "scheduler_node")

    # Phase 2 loop
    builder.add_conditional_edges(
        "scheduler_node",
        route_after_scheduler,
        {
            "continue_search": "parallel_search_node",
            "convergence": "convergence_node",
        },
    )
    builder.add_edge("parallel_search_node", "scheduler_node")

    # Phase 3 → END
    builder.add_edge("convergence_node", END)

    return builder.compile()
