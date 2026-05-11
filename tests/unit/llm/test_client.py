from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from llm.client import LLMClient, LLMJSONError


def _make_response(content: str, total_tokens: int = 10) -> MagicMock:
    """Build a MagicMock that mimics the OpenAI chat completion response shape."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage = MagicMock()
    response.usage.total_tokens = total_tokens
    return response


@patch("llm.client.OpenAI")
def test_chat_returns_content_and_tokens(mock_openai_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_response("hello", 42)
    mock_openai_cls.return_value = mock_client

    client = LLMClient()
    content, tokens = client.chat(messages=[{"role": "user", "content": "hi"}])

    assert content == "hello"
    assert tokens == 42
    assert mock_client.chat.completions.create.call_count == 1


@patch("llm.client.OpenAI")
def test_json_mode_retry_on_malformed_then_succeeds(mock_openai_cls):
    bad = _make_response("not-json {", total_tokens=20)
    good = _make_response('{"ok": true}', total_tokens=30)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [bad, good]
    mock_openai_cls.return_value = mock_client

    client = LLMClient()
    content, tokens = client.chat(
        messages=[{"role": "user", "content": "give json"}],
        json_mode=True,
        max_retries=2,
    )

    assert json.loads(content) == {"ok": True}
    # Tokens summed across both attempts.
    assert tokens == 50
    assert mock_client.chat.completions.create.call_count == 2


@patch("llm.client.OpenAI")
def test_json_mode_raises_after_max_retries(mock_openai_cls):
    bad = _make_response("still not json", total_tokens=5)
    mock_client = MagicMock()
    # All three attempts return bad content.
    mock_client.chat.completions.create.side_effect = [bad, bad, bad]
    mock_openai_cls.return_value = mock_client

    client = LLMClient()
    with pytest.raises(LLMJSONError) as exc_info:
        client.chat(
            messages=[{"role": "user", "content": "give json"}],
            json_mode=True,
            max_retries=3,
        )

    assert "still not json" in str(exc_info.value)
    assert mock_client.chat.completions.create.call_count == 3


def test_ensure_json_instruction_adds_system_prompt():
    messages = [{"role": "user", "content": "hi"}]
    result = LLMClient._ensure_json_instruction(messages)

    assert result[0]["role"] == "system"
    assert "valid JSON only" in result[0]["content"]
    # Original user message preserved.
    assert result[1] == {"role": "user", "content": "hi"}
    # Original list not mutated.
    assert messages == [{"role": "user", "content": "hi"}]


def test_ensure_json_instruction_appends_to_existing_system():
    messages = [
        {"role": "system", "content": "You are an X."},
        {"role": "user", "content": "hi"},
    ]
    result = LLMClient._ensure_json_instruction(messages)

    assert result[0]["role"] == "system"
    assert "You are an X." in result[0]["content"]
    assert "valid JSON only" in result[0]["content"]
    assert result[1] == {"role": "user", "content": "hi"}
    # Original list not mutated.
    assert messages[0]["content"] == "You are an X."


@patch("llm.client.OpenAI")
def test_non_json_mode_no_retry(mock_openai_cls):
    # Even malformed-looking content is returned as-is in non-json mode.
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_response(
        "this looks like {bad json", total_tokens=7
    )
    mock_openai_cls.return_value = mock_client

    client = LLMClient()
    content, tokens = client.chat(
        messages=[{"role": "user", "content": "hi"}],
        json_mode=False,
        max_retries=3,
    )

    assert content == "this looks like {bad json"
    assert tokens == 7
    assert mock_client.chat.completions.create.call_count == 1
