from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    SearchDirection,
)


class BlackboardRecord(BaseModel):
    """Base class for all blackboard records.

    Invariant: status is only ever "committed" or "retracted".
    No draft state exists across the system.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    status: Literal["committed", "retracted"] = "committed"
    author: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    references: list[str] = Field(default_factory=list)
    retraction_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Lens sub-structures: abstracted entities and relationships
# ---------------------------------------------------------------------------


class AbstractedEntity(BaseModel):
    """A single entity from the user's question, abstracted to structural level."""

    model_config = ConfigDict(strict=True, extra="forbid")

    surface: str           # original term, e.g. "AI"
    structural_role: str   # abstracted structural role, e.g. "前卫生产力"


class AbstractedRelation(BaseModel):
    """A relationship between entities, abstracted to structural level."""

    model_config = ConfigDict(strict=True, extra="forbid")

    surface: str      # original relationship, e.g. "AI引发焦虑"
    structural: str   # abstracted structural relationship


# ---------------------------------------------------------------------------
# Blackboard zone records
# ---------------------------------------------------------------------------


class LensRecord(BlackboardRecord):
    """假设区 record for the analytical lens.

    Carries the Phase 1 abstraction result: entities and relationships
    abstracted to structural level, enabling cross-temporal/spatial comparison.

    Invariant: lens演化只能"加新版本"，不能"原地改".
    parent_lens_id points to the previous version in the chain.
    """

    parent_lens_id: Optional[str] = None
    name: str
    rationale: str
    entities: list[AbstractedEntity] = Field(default_factory=list)
    relationships: list[AbstractedRelation] = Field(default_factory=list)


class EvidenceRecord(BlackboardRecord):
    """证据区 record.

    Invariant: all metadata fields must be present.
    Missing metadata renders the evidence invalid.
    """

    source_lens_id: str
    search_direction: SearchDirection
    case_name: str
    layer: EvidenceLayer
    confidence: EvidenceConfidence
    is_unexpected: bool
    content: str


class ConclusionRecord(BlackboardRecord):
    """结论区 record.

    Written during convergence phase. Tension-style output.
    """

    core_finding: str
    tension: str
    boundary_condition: str
    unresolved: str
    implication: str


class ScheduleLogEntry(BlackboardRecord):
    """调度日志区 record.

    Append-only. Tracks Orchestrator decisions and degradation events.
    """

    decision: str
    reason: str
    degradation_flag: bool = False
