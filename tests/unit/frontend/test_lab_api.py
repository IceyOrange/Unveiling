"""Unit tests for the Prompt Lab JSON API in ``frontend/app.py``.

These tests use Flask's test client and an isolated ``prompt_lab/`` directory
in ``tmp_path``, so they never touch the real prompt files. The LLM call in
``/api/prompts/<name>/run`` is monkeypatched — these tests never hit DeepSeek.
"""
from __future__ import annotations

import json

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DEMO_META = {
    "demo": {
        "label": "Demo prompt",
        "source": "tests/unit/frontend/test_lab_api.py",
        "phase": "test",
        "variables": ["question"],
        "var_labels": {"question": "Question"},
        "defaults": {"question": "default question"},
        "json_mode": True,
        "temperature": 0.4,
        "description": "Used by the lab API unit tests.",
    },
    "novars": {
        "label": "No-variable prompt",
        "source": "tests/unit/frontend/test_lab_api.py",
        "phase": "test",
        "variables": [],
        "var_labels": {},
        "defaults": {},
        "json_mode": False,
        "temperature": 0.7,
        "description": "Prompt with no variables — system-role analogue.",
    },
}


@pytest.fixture
def lab_dir(tmp_path, monkeypatch):
    """Point ``frontend.app._PROMPT_LAB_DIR`` at an isolated tmp directory."""
    d = tmp_path / "prompt_lab"
    d.mkdir()
    (d / "meta.json").write_text(
        json.dumps(DEMO_META, ensure_ascii=False), encoding="utf-8"
    )
    (d / "demo.txt").write_text("Hello, {question}!", encoding="utf-8")
    (d / "novars.txt").write_text("Static prompt body.", encoding="utf-8")

    import frontend.app as app_mod
    monkeypatch.setattr(app_mod, "_PROMPT_LAB_DIR", d)
    return d


@pytest.fixture
def client(lab_dir):
    """Flask test client with cleared run history."""
    import frontend.app as app_mod
    app_mod._run_history.clear()
    app_mod.app.config["TESTING"] = True
    return app_mod.app.test_client()


class _FakeLLMClient:
    """Stand-in for ``llm.client.LLMClient`` returning canned output."""

    last_kwargs: dict | None = None

    def __init__(self, *args, **kwargs):
        type(self).last_kwargs = kwargs

    def chat(self, messages, json_mode=False, temperature=0.7, **_):
        # Echo back the rendered prompt so tests can assert substitution.
        payload = {
            "echo": messages[-1]["content"],
            "json_mode": json_mode,
            "temperature": temperature,
        }
        return json.dumps(payload), 42


class _ExplodingLLMClient:
    """LLM client that always raises — used to test the 500 path."""

    def __init__(self, *_, **__):
        pass

    def chat(self, *_, **__):
        raise RuntimeError("boom")


# ---------------------------------------------------------------------------
# GET /api/prompts
# ---------------------------------------------------------------------------

def test_list_prompts_returns_metadata_for_each_entry(client):
    resp = client.get("/api/prompts")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    names = {p["name"] for p in data}
    assert names == {"demo", "novars"}
    demo = next(p for p in data if p["name"] == "demo")
    assert demo["label"] == "Demo prompt"
    assert demo["phase"] == "test"


# ---------------------------------------------------------------------------
# GET /api/prompts/<name>
# ---------------------------------------------------------------------------

def test_get_prompt_returns_full_payload(client):
    resp = client.get("/api/prompts/demo")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["name"] == "demo"
    assert data["text"] == "Hello, {question}!"
    assert data["variables"] == ["question"]
    assert data["discovered_variables"] == ["question"]
    assert data["defaults"] == {"question": "default question"}
    assert data["json_mode"] is True
    assert data["temperature"] == 0.4
    assert data["run_count"] == 0


def test_get_prompt_returns_404_for_unknown_name(client):
    resp = client.get("/api/prompts/does_not_exist")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "not found"}


# ---------------------------------------------------------------------------
# PUT /api/prompts/<name>
# ---------------------------------------------------------------------------

def test_put_prompt_writes_text_to_disk(client, lab_dir):
    new_text = "Updated body with {question} and {extra}."
    resp = client.put(
        "/api/prompts/demo",
        data=json.dumps({"text": new_text}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["ok"] is True
    assert body["saved"] == "demo"
    assert body["bytes"] == len(new_text.encode("utf-8"))
    # discovered_variables picks up the newly-introduced {extra}.
    assert body["discovered_variables"] == ["question", "extra"]
    on_disk = (lab_dir / "demo.txt").read_text(encoding="utf-8")
    assert on_disk == new_text


def test_put_prompt_404_for_unknown_name(client):
    resp = client.put(
        "/api/prompts/missing",
        data=json.dumps({"text": "x"}),
        content_type="application/json",
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/prompts/<name>/preview
# ---------------------------------------------------------------------------

def test_preview_substitutes_declared_variables(client):
    resp = client.post(
        "/api/prompts/demo/preview",
        data=json.dumps({"inputs": {"question": "what now"}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["rendered"] == "Hello, what now!"
    assert data["char_count"] == len("Hello, what now!")
    assert data["discovered_variables"] == ["question"]


def test_preview_uses_defaults_when_input_missing(client):
    resp = client.post(
        "/api/prompts/demo/preview",
        data=json.dumps({"inputs": {}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json()["rendered"] == "Hello, default question!"


def test_preview_with_unknown_variable_in_edited_text_does_not_crash(client):
    """User edits template adding a new {extra} before declaring it in meta."""
    edited = "Hi {question}, also {extra}!"
    resp = client.post(
        "/api/prompts/demo/preview",
        data=json.dumps({"text": edited, "inputs": {"question": "X"}}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    # Declared var substituted; undeclared {extra} left as-is via fallback.
    assert data["rendered"] == "Hi X, also {extra}!"
    assert "extra" in data["discovered_variables"]


# ---------------------------------------------------------------------------
# POST /api/prompts/<name>/run + GET /api/prompts/<name>/runs
# ---------------------------------------------------------------------------

def test_run_prompt_calls_llm_and_returns_output(client, monkeypatch):
    monkeypatch.setattr("llm.client.LLMClient", _FakeLLMClient)
    resp = client.post(
        "/api/prompts/demo/run",
        data=json.dumps({
            "inputs": {"question": "AI 焦虑"},
            "language": "中文",
            "temperature": 0.3,
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["tokens"] == 42
    assert body["temperature"] == 0.3
    assert body["json_mode"] is True  # meta default
    # Echoed payload proves the rendered prompt was passed to chat()
    parsed = body["parsed"]
    assert parsed is not None
    assert parsed["echo"] == "Hello, AI 焦虑!"
    assert parsed["temperature"] == 0.3
    # History was recorded
    assert _FakeLLMClient.last_kwargs == {"language": "中文"}
    assert body["history"]["ok"] is True


def test_run_prompt_records_history_visible_via_runs_endpoint(client, monkeypatch):
    monkeypatch.setattr("llm.client.LLMClient", _FakeLLMClient)
    client.post(
        "/api/prompts/demo/run",
        data=json.dumps({"inputs": {"question": "X"}}),
        content_type="application/json",
    )
    runs_resp = client.get("/api/prompts/demo/runs")
    assert runs_resp.status_code == 200
    runs = runs_resp.get_json()["runs"]
    assert len(runs) == 1
    assert runs[0]["ok"] is True
    assert runs[0]["tokens"] == 42
    assert runs[0]["inputs"] == {"question": "X"}


@pytest.mark.parametrize("language", ["English", "中文"])
def test_run_prompt_injects_selected_language_into_system_message(
    client, monkeypatch, language
):
    """End-to-end regression for the prompt-lab language selector.

    The previous wording of ``_inject_language`` hard-coded 'English' as the
    structural fallback, producing a self-contradicting instruction when the
    user picked English ('write in English ... do NOT use English'). This
    test exercises the real LLMClient (only the underlying OpenAI call is
    mocked) so the system message that would have been sent to DeepSeek is
    captured and asserted directly.
    """
    from unittest.mock import MagicMock

    captured: dict = {}

    def fake_create(self, *, messages, temperature):
        captured["messages"] = list(messages)
        captured["temperature"] = temperature
        resp = MagicMock()
        resp.choices = [MagicMock(message=MagicMock(content='{"ok": true}'))]
        resp.usage = MagicMock(total_tokens=7)
        return resp

    monkeypatch.setattr("llm.client.LLMClient._create_completion", fake_create)
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")

    resp = client.post(
        "/api/prompts/demo/run",
        data=json.dumps({
            "inputs": {"question": "AI"},
            "language": language,
        }),
        content_type="application/json",
    )
    assert resp.status_code == 200

    sys_msg = captured["messages"][0]
    assert sys_msg["role"] == "system"
    assert f"Write ALL natural-language content in {language}" in sys_msg["content"]
    # Regression: the instruction must never tell the LLM to avoid the same
    # language it was just told to write in.
    assert f"Do NOT use {language}" not in sys_msg["content"]


def test_run_prompt_llm_failure_returns_500_with_error_history(client, monkeypatch):
    monkeypatch.setattr("llm.client.LLMClient", _ExplodingLLMClient)
    resp = client.post(
        "/api/prompts/demo/run",
        data=json.dumps({"inputs": {"question": "X"}}),
        content_type="application/json",
    )
    assert resp.status_code == 500
    body = resp.get_json()
    assert "boom" in body["error"]
    assert body["history"]["ok"] is False
    # The failed run is still recorded so the UI can show it.
    runs = client.get("/api/prompts/demo/runs").get_json()["runs"]
    assert len(runs) == 1
    assert runs[0]["ok"] is False


def test_runs_endpoint_returns_empty_list_initially(client):
    resp = client.get("/api/prompts/demo/runs")
    assert resp.status_code == 200
    assert resp.get_json() == {"runs": []}


def test_runs_endpoint_404_for_unknown_prompt(client):
    resp = client.get("/api/prompts/no_such/runs")
    assert resp.status_code == 404
