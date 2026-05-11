from __future__ import annotations

from models._enums import NodeStatus, Phase
from models.blackboard import IssueTreeNode
from models.state import State
from graph.routing import (
    route_after_judge,
    route_after_meta,
    route_after_scheduler,
    should_converge,
)


# ---------------------------------------------------------------------------
# route_after_scheduler
# ---------------------------------------------------------------------------
def test_route_after_scheduler_convergence_phase():
    state = State(phase=Phase.convergence)
    assert route_after_scheduler(state) == "convergence"


def test_route_after_scheduler_meta():
    state = State(next_agent="meta")
    assert route_after_scheduler(state) == "meta"


def test_route_after_scheduler_search_lateral():
    state = State(next_agent="search_lateral")
    assert route_after_scheduler(state) == "search_lateral"


def test_route_after_scheduler_search_vertical():
    state = State(next_agent="search_vertical")
    assert route_after_scheduler(state) == "search_vertical"


def test_route_after_scheduler_deepdig():
    state = State(next_agent="deepdig")
    assert route_after_scheduler(state) == "deepdig"


def test_route_after_scheduler_lens_op():
    state = State(next_agent="lens_op")
    assert route_after_scheduler(state) == "lens_op"


def test_route_after_scheduler_debate():
    state = State(next_agent="debate")
    assert route_after_scheduler(state) == "debate"


def test_route_after_scheduler_prediction_check():
    state = State(next_agent="prediction_check")
    assert route_after_scheduler(state) == "prediction_check"


def test_route_after_scheduler_fallback_to_judge_with_target():
    state = State(next_agent="", target_sub_question_id="q1")
    assert route_after_scheduler(state) == "judge"


def test_route_after_scheduler_fallback_to_convergence_no_target():
    state = State(next_agent="", target_sub_question_id="")
    assert route_after_scheduler(state) == "convergence"


def test_route_after_scheduler_unknown_agent_no_target_returns_convergence():
    # An unrecognised next_agent value with no target falls through to convergence
    state = State(next_agent="bogus_agent", target_sub_question_id="")
    assert route_after_scheduler(state) == "convergence"


def test_route_after_scheduler_convergence_overrides_next_agent():
    # Phase=convergence wins even when next_agent is a valid agent string
    state = State(phase=Phase.convergence, next_agent="search_lateral")
    assert route_after_scheduler(state) == "convergence"


# ---------------------------------------------------------------------------
# route_after_judge
# ---------------------------------------------------------------------------
def test_route_after_judge_always_scheduler():
    state = State()
    assert route_after_judge(state) == "scheduler"


def test_route_after_judge_scheduler_even_in_convergence():
    state = State(phase=Phase.convergence)
    assert route_after_judge(state) == "scheduler"


# ---------------------------------------------------------------------------
# route_after_meta
# ---------------------------------------------------------------------------
def test_route_after_meta_inception_phase():
    state = State(phase=Phase.inception)
    assert route_after_meta(state) == "inception"


def test_route_after_meta_exploration_phase():
    state = State(phase=Phase.exploration)
    assert route_after_meta(state) == "scheduler"


def test_route_after_meta_convergence_phase():
    state = State(phase=Phase.convergence)
    assert route_after_meta(state) == "scheduler"


# ---------------------------------------------------------------------------
# should_converge
# ---------------------------------------------------------------------------
def test_should_converge_true_on_token_budget_exceeded():
    state = State(token_spent=600_000, budget_ceiling=500_000)
    assert should_converge(state) is True


def test_should_converge_true_on_all_leaves_closed():
    leaf = IssueTreeNode(author="test", content="x", node_status=NodeStatus.closed)
    state = State()
    state.issue_tree.append(leaf)
    assert should_converge(state) is True


def test_should_converge_true_on_all_leaves_stuck():
    leaf = IssueTreeNode(author="test", content="x", node_status=NodeStatus.stuck)
    state = State()
    state.issue_tree.append(leaf)
    assert should_converge(state) is True


def test_should_converge_false_when_exploring():
    leaf = IssueTreeNode(author="test", content="x", node_status=NodeStatus.exploring)
    state = State(token_spent=100, budget_ceiling=500_000)
    state.issue_tree.append(leaf)
    assert should_converge(state) is False


def test_should_converge_false_on_empty_state():
    # Empty issue tree means all_leaves_closed_or_stuck returns False
    state = State(token_spent=0, budget_ceiling=500_000)
    assert should_converge(state) is False
