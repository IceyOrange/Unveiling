"""Shared analysis log writer for both CLI and web paths."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def write_analysis_log(result: dict) -> Path:
    """Write a detailed analysis log to data/tmp/ and return the path.

    Args:
        result: A dict with the same shape as LangGraph's accumulated state.
            Expected keys: user_question, phase, token_spent, lateral_count,
            vertical_count, hypothesis_zone, evidence_zone, conclusion_zone,
            schedule_log.

    Returns:
        Path to the written log file.
    """
    log_dir = Path("data/tmp")
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = log_dir / f"analysis_{timestamp}.log"

    lines: list[str] = []
    lines.append("=" * 70)
    lines.append("UNVEILING ANALYSIS LOG")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    # Meta
    phase_val = result.get("phase", "unknown")
    phase_str = phase_val.value if hasattr(phase_val, "value") else str(phase_val)
    lines.append(f"\nQuestion: {result.get('user_question', 'N/A')}")
    lines.append(f"Phase: {phase_str}")
    lines.append(f"Tokens spent: {result.get('token_spent', 0)}")
    lines.append(
        f"Evidence: lateral={result.get('lateral_count', 0)}, "
        f"vertical={result.get('vertical_count', 0)}"
    )

    # Lens
    hypothesis_zone = result.get("hypothesis_zone", [])
    if hypothesis_zone:
        lens = hypothesis_zone[-1]
        lines.append(f"\n{'=' * 70}")
        lines.append("LENS (Phase 1 Abstraction)")
        lines.append(f"{'=' * 70}")
        lines.append(f"Name: {_attr(lens, 'name')}")
        lines.append(f"Rationale: {_attr(lens, 'rationale')}")

        entities = _attr(lens, "entities", [])
        if entities:
            lines.append("\nEntities:")
            for e in entities:
                lines.append(f"  {_attr(e, 'surface')} -> {_attr(e, 'structural_role')}")

        relationships = _attr(lens, "relationships", [])
        if relationships:
            lines.append("\nRelationships:")
            for r in relationships:
                lines.append(f"  {_attr(r, 'surface')} -> {_attr(r, 'structural')}")

        root_cause_chain = _attr(lens, "root_cause_chain", [])
        if root_cause_chain:
            lines.append("\nRoot Cause Chain:")
            for rc in root_cause_chain:
                lines.append(
                    f"  L{_attr(rc, 'level', '?')}: "
                    f"{_attr(rc, 'surface_why')}\n"
                    f"    A: {_attr(rc, 'answer')}\n"
                    f"    Structural: {_attr(rc, 'structural_why')}"
                )

    # Schedule log
    lines.append(f"\n{'=' * 70}")
    lines.append("SCHEDULE LOG")
    lines.append(f"{'=' * 70}")
    for i, log in enumerate(result.get("schedule_log", []), 1):
        lines.append(
            f"  [{i:2d}] {_attr(log, 'author')} | "
            f"{_attr(log, 'decision')} | {_attr(log, 'reason')}"
        )

    # Evidence — full detail
    evidence_list = result.get("evidence_zone", [])
    if evidence_list:
        lateral_ev = [
            e for e in evidence_list
            if _enum_val(_attr(e, "search_direction")) == "lateral"
        ]
        vertical_ev = [
            e for e in evidence_list
            if _enum_val(_attr(e, "search_direction")) == "vertical"
        ]

        lines.append(f"\n{'=' * 70}")
        lines.append(f"EVIDENCE — LATERAL ({len(lateral_ev)} cases)")
        lines.append(f"{'=' * 70}")
        for i, e in enumerate(lateral_ev, 1):
            unexpected = " [UNEXPECTED]" if _attr(e, "is_unexpected", False) else ""
            lines.append(
                f"\n  [{i}] {_attr(e, 'case_name')} "
                f"[{_enum_val(_attr(e, 'layer'))}/{_enum_val(_attr(e, 'confidence'))}]"
                f"{unexpected}"
            )
            lines.append(f"  {_attr(e, 'content')}")
            lines.append(
                f"  id={_attr(e, 'id', '')[:8]} "
                f"lens={_attr(e, 'source_lens_id', '')[:8]}"
            )

        lines.append(f"\n{'=' * 70}")
        lines.append(f"EVIDENCE — VERTICAL ({len(vertical_ev)} cases)")
        lines.append(f"{'=' * 70}")
        for i, e in enumerate(vertical_ev, 1):
            unexpected = " [UNEXPECTED]" if _attr(e, "is_unexpected", False) else ""
            lines.append(
                f"\n  [{i}] {_attr(e, 'case_name')} "
                f"[{_enum_val(_attr(e, 'layer'))}/{_enum_val(_attr(e, 'confidence'))}]"
                f"{unexpected}"
            )
            lines.append(f"  {_attr(e, 'content')}")
            lines.append(
                f"  id={_attr(e, 'id', '')[:8]} "
                f"lens={_attr(e, 'source_lens_id', '')[:8]}"
            )

    # Conclusion
    conclusion_zone = result.get("conclusion_zone", [])
    if conclusion_zone:
        lines.append(f"\n{'=' * 70}")
        lines.append("CONCLUSION (Phase 3)")
        lines.append(f"{'=' * 70}")
        c = conclusion_zone[-1]
        lines.append(f"\nCore Finding:\n  {_attr(c, 'core_finding')}")
        lines.append(f"\nTension:\n  {_attr(c, 'tension')}")
        lines.append(f"\nBoundary Condition:\n  {_attr(c, 'boundary_condition')}")
        lines.append(f"\nUnresolved:\n  {_attr(c, 'unresolved')}")
        lines.append(f"\nImplication:\n  {_attr(c, 'implication')}")

        temporal = _attr(c, "temporal_trajectory", "")
        if temporal:
            lines.append(f"\nTemporal Trajectory:\n  {temporal}")

    # Degradation
    degradation_events = [
        e for e in result.get("schedule_log", [])
        if _attr(e, "degradation_flag", False)
    ]
    if degradation_events:
        lines.append(f"\n{'=' * 70}")
        lines.append(f"DEGRADATION EVENTS ({len(degradation_events)})")
        lines.append(f"{'=' * 70}")
        for e in degradation_events:
            lines.append(f"  - {_attr(e, 'author')}: {_attr(e, 'reason')}")

    lines.append(f"\n{'=' * 70}")
    lines.append("END OF LOG")
    lines.append(f"{'=' * 70}")

    log_path.write_text("\n".join(lines), encoding="utf-8")
    return log_path


def _attr(obj: object, name: str, default: object = "") -> object:
    """getattr that handles both Pydantic models and plain dicts."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _enum_val(v: object) -> str:
    """Get the string value of an enum or return str(v)."""
    if v is None:
        return ""
    if hasattr(v, "value"):
        return v.value
    return str(v)
