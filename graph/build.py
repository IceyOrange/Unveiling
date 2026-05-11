from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.convergence import convergence_node
from agents.debate import debate_node
from agents.deepdig import deepdig_node
from agents.inception import inception_node
from agents.lens_op import lens_op_node
from agents.prediction_check import prediction_check_node
from agents.search import search_lateral_node, search_vertical_node
from models import ScheduleLogEntry, State
from graph.routing import (
    route_after_judge,
    route_after_meta,
    route_after_scheduler,
)
from orchestrator.judge import judge_node
from orchestrator.meta import meta_node
from orchestrator.scheduler import scheduler_node


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------
def build_graph():
    builder = StateGraph(State)

    # Orchestrator + lifecycle nodes
    builder.add_node("inception_node", inception_node)
    builder.add_node("scheduler_node", scheduler_node)
    builder.add_node("judge_node", judge_node)
    builder.add_node("meta_node", meta_node)
    builder.add_node("convergence_node", convergence_node)

    # Execution agent nodes (placeholders)
    builder.add_node("search_lateral_node", search_lateral_node)
    builder.add_node("search_vertical_node", search_vertical_node)
    builder.add_node("deepdig_node", deepdig_node)
    builder.add_node("lens_op_node", lens_op_node)
    builder.add_node("debate_node", debate_node)
    builder.add_node("prediction_check_node", prediction_check_node)

    # Edges
    builder.add_edge(START, "inception_node")
    builder.add_edge("inception_node", "scheduler_node")

    builder.add_conditional_edges(
        "scheduler_node",
        route_after_scheduler,
        {
            "search_lateral": "search_lateral_node",
            "search_vertical": "search_vertical_node",
            "deepdig": "deepdig_node",
            "lens_op": "lens_op_node",
            "debate": "debate_node",
            "prediction_check": "prediction_check_node",
            "judge": "judge_node",
            "meta": "meta_node",
            "convergence": "convergence_node",
        },
    )

    # All agents loop back to scheduler
    for agent_node in (
        "search_lateral_node",
        "search_vertical_node",
        "deepdig_node",
        "lens_op_node",
        "debate_node",
        "prediction_check_node",
    ):
        builder.add_edge(agent_node, "scheduler_node")

    builder.add_edge("judge_node", "scheduler_node")

    builder.add_conditional_edges(
        "meta_node",
        route_after_meta,
        {
            "inception": "inception_node",
            "scheduler": "scheduler_node",
        },
    )

    builder.add_edge("convergence_node", END)

    return builder.compile()
