from __future__ import annotations

import pytest

from agents.inception import inception_node
from models import IssueTreeNode, State
from models._enums import Phase


def _run_inception(question: str, budget: int) -> dict:
    state = State(user_question=question, budget_ceiling=budget)
    update = inception_node(state)

    issue_nodes = [n for n in update.get("issue_tree", []) if isinstance(n, IssueTreeNode)]
    assert len(issue_nodes) >= 1, "inception must produce at least one IssueTreeNode"

    schedule_log = update.get("schedule_log", [])
    assert len(schedule_log) >= 1, "inception must write to schedule_log"

    assert update.get("token_spent", 0) > 0, "inception must spend tokens"
    assert update.get("phase") == Phase.exploration

    degradation_count = sum(1 for e in schedule_log if getattr(e, "degradation_flag", False))
    assert degradation_count <= 1, f"too many degradations: {degradation_count}"

    print(f"\n--- Issue tree for: {question!r} ---")
    for n in issue_nodes:
        prefix = "[root]" if n.parent_id is None else "  - "
        print(f"{prefix} {n.content}")
    print(f"tokens={update.get('token_spent')}, degradations={degradation_count}")

    return update


@pytest.mark.e2e
def test_e2e_inception_finance_theme(e2e_env, cheap_budget):
    _run_inception("AI 公司应该烧钱扩张吗？", cheap_budget)


@pytest.mark.e2e
def test_e2e_inception_tech_theme(e2e_env, cheap_budget):
    _run_inception("开源软件能可持续发展吗？", cheap_budget)


@pytest.mark.e2e
def test_e2e_inception_education_theme(e2e_env, cheap_budget):
    _run_inception("在线教育能否取代线下教育？", cheap_budget)
