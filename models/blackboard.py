from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from models._enums import (
    EvidenceConfidence,
    EvidenceLayer,
    NodeStatus,
    OrchestratorRole,
    PredictionStatus,
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


class IssueTreeNode(BlackboardRecord):
    """问题区 record. Represents a node in the issue tree.

    Blackboard lifecycle: status (committed/retracted).
    Analytical lifecycle: node_status (untouched/exploring/closed/stuck).
    """

    parent_id: Optional[str] = None
    driving_question_id: Optional[str] = None
    content: str
    node_status: NodeStatus = NodeStatus.untouched
    minimum_viable_answer: Optional[str] = None


class LensRecord(BlackboardRecord):
    """假设区 record for an abstract lens.

    Invariant: lens演化只能"加新版本"，不能"原地改".
    parent_lens_id points to the previous version in the chain.
    """

    parent_lens_id: Optional[str] = None
    name: str
    rationale: str


class PredictionRecord(BlackboardRecord):
    """假设区 record for a falsifiable prediction.

    Invariant: every prediction must carry killer_evidence.
    A prediction without killer_evidence is invalid and must be discarded.
    """

    claim: str
    if_true_we_should_see: str
    if_false_we_should_see: str
    killer_evidence: str
    prediction_status: PredictionStatus = PredictionStatus.pending


class EvidenceRecord(BlackboardRecord):
    """证据区 record.

    Invariant: all 6 metadata fields must be present.
    Missing metadata renders the evidence invalid.
    """

    source_lens_id: str
    source_lens_version: str
    sub_question_id: str
    layer: EvidenceLayer
    confidence: EvidenceConfidence
    is_unexpected: bool
    content: str


class DebateRecord(BlackboardRecord):
    """辩论区 record.

    Stores a question-response round or a deep-dig cross-layer failure note.
    """

    round: int
    question: str
    response: str
    sub_question_id: Optional[str] = None
    cross_layer_failure_note: Optional[str] = None


class ConclusionRecord(BlackboardRecord):
    """结论区 record.

    Written during convergence phase. Tension-style output per sub-question.
    """

    sub_question_id: Optional[str] = None
    convergent_finding: str
    tension: str
    boundary_condition: str
    unresolved: str
    implication: str


class ScheduleLogEntry(BlackboardRecord):
    """调度日志区 record.

    Append-only. Tracks Orchestrator decisions and degradation events.
    """

    role: OrchestratorRole
    decision: str
    reason: str
    degradation_flag: bool = False
