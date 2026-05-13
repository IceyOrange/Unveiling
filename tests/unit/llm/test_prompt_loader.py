from __future__ import annotations

import pytest

from llm import prompt_loader


def test_load_lab_prompt_reads_existing_file():
    body = prompt_loader.load_lab_prompt("inception_user")
    assert "{question}" in body  # the variable placeholder must survive


def test_load_lab_prompt_inception_system_has_no_variables():
    body = prompt_loader.load_lab_prompt("inception_system")
    assert body.strip()  # non-empty


def test_load_lab_prompt_not_found():
    with pytest.raises(FileNotFoundError):
        prompt_loader.load_lab_prompt("nonexistent_prompt_xyz")


def test_list_lab_prompts_covers_pipeline():
    names = prompt_loader.list_lab_prompts()
    # All 7 live prompts must be present in the lab.
    for required in [
        "inception_system",
        "inception_user",
        "lateral_query",
        "vertical_query",
        "validate_queries",
        "case_extraction",
        "convergence_synthesize",
    ]:
        assert required in names, f"missing lab prompt: {required}"


def test_load_lab_prompt_reads_fresh_each_call(tmp_path, monkeypatch):
    # Point the loader at a temporary lab and verify it re-reads the file
    # on every call (no caching).
    monkeypatch.setattr(prompt_loader, "_LAB_DIR", tmp_path)
    target = tmp_path / "hot_reload.txt"
    target.write_text("v1", encoding="utf-8")
    assert prompt_loader.load_lab_prompt("hot_reload") == "v1"
    target.write_text("v2", encoding="utf-8")
    assert prompt_loader.load_lab_prompt("hot_reload") == "v2"


def test_lab_prompt_path_returns_expected_path():
    p = prompt_loader.lab_prompt_path("inception_user")
    assert p.name == "inception_user.txt"
    assert p.exists()
