from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session")
def e2e_env() -> None:
    """Ensure real API credentials are present; load .env if available."""
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    missing = [k for k in ("OPENAI_API_KEY", "SERPER_API_KEY") if not os.environ.get(k)]
    if missing:
        pytest.fail(
            f"e2e tests require {missing} in environment (or .env at repo root). "
            "Set them or skip e2e: pytest -m 'not e2e'"
        )


@pytest.fixture
def cheap_budget() -> int:
    """Small token budget so a runaway test cannot burn money."""
    return 50_000
