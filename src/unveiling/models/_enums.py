from enum import Enum


class RecordStatus(str, Enum):
    committed = "committed"
    retracted = "retracted"


class EvidenceLayer(str, Enum):
    phenomenon = "phenomenon"
    mechanism = "mechanism"
    structure = "structure"


class EvidenceConfidence(str, Enum):
    strong = "strong"
    medium = "medium"
    weak = "weak"
    unexpected = "unexpected"


class SearchDirection(str, Enum):
    lateral = "lateral"
    vertical = "vertical"


class Phase(str, Enum):
    inception = "inception"
    exploration = "exploration"
    convergence = "convergence"
