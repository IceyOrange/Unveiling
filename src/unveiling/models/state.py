from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from unveiling.blackboard.reducers import merge_dicts, merge_lists, replace
from unveiling.models._enums import Phase
from unveiling.models.blackboard import (
    ConclusionRecord,
    EvidenceRecord,
    LensRecord,
    ScheduleLogEntry,
)


class State(BaseModel):
    """LangGraph State = four-zone blackboard + scheduling state.

    Phase 1 (inception) writes hypothesis_zone.
    Phase 2 (exploration) writes evidence_zone in parallel.
    Phase 3 (convergence) writes conclusion_zone.

    All list fields use merge_lists reducer (append-only semantics).
    All scalar fields use replace reducer (overwrite).
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    # Four blackboard zones
    hypothesis_zone: Annotated[list[LensRecord], merge_lists] = Field(
        default_factory=list
    )
    evidence_zone: Annotated[list[EvidenceRecord], merge_lists] = Field(
        default_factory=list
    )
    conclusion_zone: Annotated[list[ConclusionRecord], merge_lists] = Field(
        default_factory=list
    )
    schedule_log: Annotated[list[ScheduleLogEntry], merge_lists] = Field(
        default_factory=list
    )

    # Search coverage (Phase 2)
    lateral_count: Annotated[int, replace] = 0
    vertical_count: Annotated[int, replace] = 0
    lateral_rounds: Annotated[int, replace] = 0
    vertical_rounds: Annotated[int, replace] = 0

    # Orchestrator internal state
    token_spent: Annotated[int, replace] = 0
    phase: Annotated[Phase, replace] = Phase.inception
    budget_ceiling: Annotated[int, replace] = 500_000

    # User input
    user_question: Annotated[str, replace] = ""
    output_language: Annotated[str, replace] = "中文"
