from __future__ import annotations

from graph.build import build_graph


EXPECTED_NODES = {
    "inception_node",
    "scheduler_node",
    "judge_node",
    "meta_node",
    "convergence_node",
    "search_lateral_node",
    "search_vertical_node",
    "deepdig_node",
    "lens_op_node",
    "debate_node",
    "prediction_check_node",
}


def test_build_graph_returns_compiled_graph():
    graph = build_graph()
    assert graph is not None
    assert hasattr(graph, "invoke")
    assert hasattr(graph, "stream")


def test_graph_has_expected_nodes():
    graph = build_graph()
    nodes = set(graph.get_graph().nodes.keys())
    missing = EXPECTED_NODES - nodes
    assert not missing, f"missing nodes: {missing}; actual: {nodes}"
