from __future__ import annotations

import pytest

from llm import prompt_loader


def test_load_prompt_strips_frontmatter():
    body = prompt_loader.load_prompt("scheduler")
    assert "---" not in body.split("\n")[:1]
    assert "Scheduler Agent Prompt" in body
    assert "Output Schema (JSON)" in body


def test_load_prompt_caches():
    body1 = prompt_loader.load_prompt("scheduler")
    body2 = prompt_loader.load_prompt("scheduler")
    assert body1 is body2  # same object due to cache


def test_load_prompt_not_found():
    with pytest.raises(FileNotFoundError):
        prompt_loader.load_prompt("nonexistent_prompt_xyz")


def test_list_prompts_includes_scheduler():
    names = prompt_loader.list_prompts()
    assert "scheduler" in names
    assert "judge" in names
    assert "meta" in names


def test_clear_cache():
    prompt_loader.load_prompt("scheduler")
    assert "scheduler" in prompt_loader._CACHE
    prompt_loader.clear_cache()
    assert "scheduler" not in prompt_loader._CACHE
