from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional


_CACHE: dict[str, str] = {}

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DIR = _PROJECT_ROOT / "docs" / "prompts"


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def load_prompt(name: str) -> str:
    """Load a prompt template from docs/prompts/{name}.md.

    Strips YAML frontmatter and returns only the markdown body.
    Results are cached for the lifetime of the process.

    Args:
        name: Prompt file name without extension (e.g. "scheduler").

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    if name in _CACHE:
        return _CACHE[name]

    path = _PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    text = path.read_text(encoding="utf-8")
    body = FRONTMATTER_RE.sub("", text, count=1).strip()

    _CACHE[name] = body
    return body


def get_prompt_path(name: str) -> Path:
    """Return the filesystem path for a prompt file."""
    return _PROMPTS_DIR / f"{name}.md"


def list_prompts() -> list[str]:
    """Return the names of all available prompt files."""
    if not _PROMPTS_DIR.exists():
        return []
    return sorted(p.stem for p in _PROMPTS_DIR.glob("*.md"))


def clear_cache() -> None:
    """Clear the in-memory prompt cache."""
    _CACHE.clear()
