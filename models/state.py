from __future__ import annotations

from typing import Annotated, Union

from pydantic import BaseModel, ConfigDict, Field

from blackboard.reducers import merge_dicts, merge_lists, replace
from models._enums import Phase
from models.blackboard import (
    ConclusionRecord,
    DebateRecord,
    EvidenceRecord,
    IssueTreeNode,
    LensRecord,
    PredictionRecord,
    ScheduleLogEntry,
)

HypothesisRecord = Union[LensRecord, PredictionRecord]


class State(BaseModel):
    """LangGraph State = six-zone blackboard + Orchestrator internal state.

    All list fields use merge_lists reducer (append-only semantics).
    All dict fields use merge_dicts reducer (shallow merge).
    All scalar fields use replace reducer (overwrite).

    Nodes must return dict updates; LangGraph merges them via these reducers.
    Never mutate the incoming state object directly.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    # Six blackboard zones
    issue_tree: Annotated[list[IssueTreeNode], merge_lists] = Field(default_factory=list)
    hypothesis_zone: Annotated[list[HypothesisRecord], merge_lists] = Field(
        default_factory=list
    )
    evidence_zone: Annotated[list[EvidenceRecord], merge_lists] = Field(
        default_factory=list
    )
    debate_zone: Annotated[list[DebateRecord], merge_lists] = Field(
        default_factory=list
    )
    conclusion_zone: Annotated[list[ConclusionRecord], merge_lists] = Field(
        default_factory=list
    )
    schedule_log: Annotated[list[ScheduleLogEntry], merge_lists] = Field(
        default_factory=list
    )

    # Orchestrator internal state
    attempt_counters: Annotated[dict[str, int], merge_dicts] = Field(
        default_factory=dict
    )
    finding_density_window: Annotated[list[float], merge_lists] = Field(
        default_factory=list
    )
    token_spent: Annotated[int, replace] = 0
    round_count: Annotated[int, replace] = 0
    phase: Annotated[Phase, replace] = Phase.inception
    pending_tasks: Annotated[list[str], merge_lists] = Field(default_factory=list)
    degradation_count: Annotated[int, replace] = 0
    budget_ceiling: Annotated[int, replace] = 500_000

    # User input
    user_question: Annotated[str, replace] = ""

    # Scheduling fields (set by Scheduler, read by routing + agents)
    next_agent: Annotated[str, replace] = ""
    target_sub_question_id: Annotated[str, replace] = ""
