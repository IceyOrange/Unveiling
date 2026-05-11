from __future__ import annotations

from typing import Literal


def build_queries(
    lens: dict,
    sub_question: str,
    mode: Literal["near", "far", "killer_evidence"],
) -> list[str]:
    """Generate search queries for a given sub-question and mode.

    This is a minimal stub. Phase 6 will refine prompts for near/far/killer
    query generation based on the current lens.

    Args:
        lens: Current lens record (or scaffold lens during inception).
        sub_question: The sub-question to search for.
        mode: "near" for close analogies, "far" for distant analogies,
              "killer_evidence" for explicit counter-evidence.

    Returns:
        List of query strings to pass to search.serper.search().
    """
    if mode == "near":
        return [f"{sub_question} similar cases structural analogy"]
    elif mode == "far":
        return [
            f"{sub_question} historical precedent distant domain",
            f"{sub_question} counterintuitive example unrelated industry",
        ]
    elif mode == "killer_evidence":
        return [f"{sub_question} refutation counterexample failure case"]
    return [sub_question]
