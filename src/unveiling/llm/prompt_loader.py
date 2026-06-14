from __future__ import annotations

from pathlib import Path


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LAB_DIR = _PROJECT_ROOT / "prompts"


def load_lab_prompt(name: str) -> str:
    """Read a prompt template from prompts/{name}.txt on every call.

    The lab is the single source of truth for live prompts. Agents call this at
    invocation time so that edits saved through the /prompt-lab UI take effect
    on the very next run — no process restart needed, no cache to clear.

    Args:
        name: Prompt file name without extension (e.g. "inception_user").

    Raises:
        FileNotFoundError: If the prompt file does not exist under prompts/.
    """
    path = _LAB_DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Lab prompt not found: {path}")
    return path.read_text(encoding="utf-8")


def lab_prompt_path(name: str) -> Path:
    """Return the filesystem path for a lab prompt file."""
    return _LAB_DIR / f"{name}.txt"


def list_lab_prompts() -> list[str]:
    """Return the names of all available lab prompts."""
    if not _LAB_DIR.exists():
        return []
    return sorted(p.stem for p in _LAB_DIR.glob("*.txt"))
