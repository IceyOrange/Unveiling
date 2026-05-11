from __future__ import annotations

from models._enums import NodeStatus, Phase
from models.blackboard import IssueTreeNode
from models.state import State
from orchestrator.scheduler import META_INTERVAL, _decide_agent, scheduler_node


def _node(content: str, status: NodeStatus, parent_id: str | None = None) -> IssueTreeNode:
    return IssueTreeNode(
        author="test", content=content, node_status=status, parent_id=parent_id
    )


def test_scheduler_forces_convergence_on_budget():
    state = State(token_spent=600_000, budget_ceiling=500_000)
    # Add a non-closed leaf so we know convergence triggers via budget, not via
    # all_leaves_closed_or_stuck.
    state.issue_tree.append(_node("Open", NodeStatus.exploring))

    update = scheduler_node(state)

    assert update["phase"] == Phase.convergence
    assert "schedule_log" in update
    log = update["schedule_log"][0]
    assert log.decision == "force_convergence"
    assert "token budget exceeded" in log.reason


def test_scheduler_triggers_meta_at_interval():
    state = State(round_count=META_INTERVAL)
    state.issue_tree.append(_node("Open", NodeStatus.exploring))

    update = scheduler_node(state)

    assert update["next_agent"] == "meta"
    assert update["round_count"] == META_INTERVAL + 1
    log = update["schedule_log"][0]
    assert log.decision == "meta_evaluation"


def test_scheduler_picks_first_non_closed_subquestion():
    open_node = _node("Open", NodeStatus.untouched)
    closed_node = _node("Closed", NodeStatus.closed)
    state = State()
    state.issue_tree.extend([open_node, closed_node])

    update = scheduler_node(state)

    assert update["target_sub_question_id"] == open_node.id
    # Default counter for unseen target is 0 -> agents[0] = search_lateral
    assert update["next_agent"] == "search_lateral"


def test_scheduler_promotes_untouched_to_exploring():
    target = _node("T", NodeStatus.untouched)
    state = State()
    state.issue_tree.append(target)

    update = scheduler_node(state)

    promoted = update["issue_tree"][0]
    assert promoted.id == target.id
    assert promoted.node_status == NodeStatus.exploring


def test_scheduler_does_not_emit_issue_tree_update_for_exploring_target():
    target = _node("T", NodeStatus.exploring)
    state = State()
    state.issue_tree.append(target)

    update = scheduler_node(state)

    # If target was already exploring, no new IssueTreeNode entry is added.
    assert "issue_tree" not in update
    assert update["target_sub_question_id"] == target.id


def test_scheduler_increments_attempt_counter():
    target = _node("T", NodeStatus.exploring)
    state = State()
    state.issue_tree.append(target)
    state.attempt_counters[target.id] = 2

    update = scheduler_node(state)

    assert update["attempt_counters"] == {target.id: 3}


def test_scheduler_routes_to_judge_every_6th_cycle():
    target = _node("T", NodeStatus.exploring)
    state = State()
    state.issue_tree.append(target)
    state.attempt_counters[target.id] = 6  # _decide_agent: counter%6==0 -> judge

    assert _decide_agent(state, target) == "judge"

    update = scheduler_node(state)
    assert update["next_agent"] == "judge"


def test_scheduler_convergence_when_no_leaf_non_closed():
    state = State()
    state.issue_tree.append(_node("Done1", NodeStatus.closed))
    state.issue_tree.append(_node("Done2", NodeStatus.stuck))

    update = scheduler_node(state)

    assert update["phase"] == Phase.convergence
    log = update["schedule_log"][0]
    assert log.decision == "convergence"
    assert "closed or stuck" in log.reason


def test_decide_agent_cycles_through_agents():
    target = _node("T", NodeStatus.exploring)
    state = State()
    state.issue_tree.append(target)
    expected = [
        "search_lateral",
        "search_vertical",
        "deepdig",
        "lens_op",
        "debate",
        "prediction_check",
    ]
    for counter, agent in enumerate(expected):
        state.attempt_counters[target.id] = counter
        assert _decide_agent(state, target) == agent
