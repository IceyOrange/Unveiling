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


class EvidenceEra(str, Enum):
    ancient = "ancient"
    medieval = "medieval"
    early_modern = "early_modern"
    industrial = "industrial"
    contemporary = "contemporary"
    future = "future"


class EvidenceDomain(str, Enum):
    original = "original"
    technology = "technology"
    economy = "economy"
    politics = "politics"
    culture = "culture"
    art = "art"
    religion = "religion"
    military = "military"
    science = "science"
    education = "education"
    media = "media"
    law = "law"
    medicine = "medicine"
    social = "social"
    other = "other"


class Phase(str, Enum):
    inception = "inception"
    exploration = "exploration"
    convergence = "convergence"
