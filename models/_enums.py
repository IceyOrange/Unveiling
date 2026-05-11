from enum import Enum


class RecordStatus(str, Enum):
    committed = "committed"
    retracted = "retracted"


class NodeStatus(str, Enum):
    untouched = "untouched"
    exploring = "exploring"
    closed = "closed"
    stuck = "stuck"


class PredictionStatus(str, Enum):
    pending = "pending"
    supported = "supported"
    refuted = "refuted"
    modified = "modified"


class EvidenceLayer(str, Enum):
    phenomenon = "phenomenon"
    mechanism = "mechanism"
    structure = "structure"


class EvidenceConfidence(str, Enum):
    strong = "strong"
    medium = "medium"
    weak = "weak"
    unexpected = "unexpected"


class Phase(str, Enum):
    inception = "inception"
    exploration = "exploration"
    convergence = "convergence"


class AgentName(str, Enum):
    search_lateral = "search_lateral"
    search_vertical = "search_vertical"
    deepdig = "deepdig"
    lens_op = "lens_op"
    debate = "debate"
    prediction_check = "prediction_check"
    inception = "inception"
    convergence = "convergence"


class OrchestratorRole(str, Enum):
    scheduler = "scheduler"
    judge = "judge"
    meta = "meta"
