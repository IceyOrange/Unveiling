from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import openai
import pytest

from unveiling.llm.client import LLMClient, LLMJSONError


def _make_response(content: str, total_tokens: int = 10) -> MagicMock:
    """Build a MagicMock that mimics the OpenAI chat completion response shape."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    response.usage = MagicMock()
    response.usage.total_tokens = total_tokens
    return response


@patch("unveiling.llm.client.OpenAI")
def test_chat_returns_content_and_tokens(mock_openai_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_response("hello", 42)
    mock_openai_cls.return_value = mock_client

    client = LLMClient()
    content, tokens = client.chat(messages=[{"role": "user", "content": "hi"}])

    assert content == "hello"
    assert tokens == 42
    assert mock_client.chat.completions.create.call_count == 1


@patch("unveiling.llm.client.OpenAI")
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


@patch("unveiling.llm.client.OpenAI")
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


@patch("unveiling.llm.client.OpenAI")
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


@patch("tenacity.nap.time.sleep", lambda *_a, **_kw: None)
@patch("unveiling.llm.client.OpenAI")
def test_transient_error_retries_then_succeeds(mock_openai_cls):
    transient = openai.APIConnectionError(request=MagicMock())
    good = _make_response("hello", total_tokens=11)
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [transient, good]
    mock_openai_cls.return_value = mock_client

    client = LLMClient()
    content, tokens = client.chat(messages=[{"role": "user", "content": "hi"}])

    assert content == "hello"
    assert tokens == 11
    assert mock_client.chat.completions.create.call_count == 2


@patch("tenacity.nap.time.sleep", lambda *_a, **_kw: None)
@patch("unveiling.llm.client.OpenAI")
def test_transient_error_reraises_after_max_attempts(mock_openai_cls):
    transient = openai.APIConnectionError(request=MagicMock())
    mock_client = MagicMock()
    # 3 attempts (matches stop_after_attempt(3) in client.py); all fail.
    mock_client.chat.completions.create.side_effect = [transient, transient, transient]
    mock_openai_cls.return_value = mock_client

    client = LLMClient()
    with pytest.raises(openai.APIConnectionError):
        client.chat(messages=[{"role": "user", "content": "hi"}])

    assert mock_client.chat.completions.create.call_count == 3


@patch("tenacity.nap.time.sleep", lambda *_a, **_kw: None)
@patch("unveiling.llm.client.OpenAI")
def test_non_transient_error_does_not_retry(mock_openai_cls):
    # BadRequestError is not in the transient set and should fail fast.
    bad = openai.BadRequestError(
        message="bad", response=MagicMock(status_code=400), body=None
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = bad
    mock_openai_cls.return_value = mock_client

    client = LLMClient()
    with pytest.raises(openai.BadRequestError):
        client.chat(messages=[{"role": "user", "content": "hi"}])

    assert mock_client.chat.completions.create.call_count == 1


# ---------------------------------------------------------------------------
# Language injection
# ---------------------------------------------------------------------------

def test_inject_language_prepends_system_when_none_exists():
    messages = [{"role": "user", "content": "hi"}]
    result = LLMClient._inject_language(messages, "中文")

    assert result[0]["role"] == "system"
    assert "Write ALL natural-language content in 中文" in result[0]["content"]
    assert result[1] == {"role": "user", "content": "hi"}
    # Input list not mutated.
    assert messages == [{"role": "user", "content": "hi"}]


def test_inject_language_appends_to_existing_system():
    messages = [
        {"role": "system", "content": "You are an analyst."},
        {"role": "user", "content": "hi"},
    ]
    result = LLMClient._inject_language(messages, "English")

    assert result[0]["role"] == "system"
    assert "You are an analyst." in result[0]["content"]
    assert "Write ALL natural-language content in English" in result[0]["content"]
    # Original system message not mutated.
    assert messages[0]["content"] == "You are an analyst."


@pytest.mark.parametrize("language", ["English", "中文", "日本語", "Español"])
def test_inject_language_instruction_is_self_consistent(language):
    """Regression: the instruction must never tell the LLM to AVOID the same
    language it is supposed to write in. Earlier versions hard-coded
    'English' as the structural fallback, which contradicted itself when the
    user picked English ('write in English ... do NOT use English')."""
    result = LLMClient._inject_language([{"role": "user", "content": "hi"}], language)
    content = result[0]["content"]
    assert f"Write ALL natural-language content in {language}" in content
    # The instruction must not tell the LLM to NOT use the same language
    # that it was just told to write in.
    assert f"Do NOT use {language}" not in content


@patch("unveiling.llm.client.OpenAI")
def test_chat_constructor_language_reaches_system_message(mock_openai_cls):
    """End-to-end: language passed to LLMClient(...) must show up in the
    system message that gets sent to the API. The lab calls
    ``LLMClient(language=...)`` and then ``chat()`` with no language kwarg,
    so this path must work via the ``self.language`` fallback."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_response("ok", 1)
    mock_openai_cls.return_value = mock_client

    client = LLMClient(language="English")
    client.chat(messages=[{"role": "user", "content": "hi"}])

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert sent_messages[0]["role"] == "system"
    assert "Write ALL natural-language content in English" in sent_messages[0]["content"]


@patch("unveiling.llm.client.OpenAI")
def test_chat_language_kwarg_overrides_constructor(mock_openai_cls):
    """Explicit ``chat(language=...)`` should win over the constructor default."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_response("ok", 1)
    mock_openai_cls.return_value = mock_client

    client = LLMClient(language="English")
    client.chat(messages=[{"role": "user", "content": "hi"}], language="中文")

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert "Write ALL natural-language content in 中文" in sent_messages[0]["content"]
    assert "Write ALL natural-language content in English" not in sent_messages[0]["content"]


@patch("unveiling.llm.client.OpenAI")
def test_chat_empty_language_skips_injection(mock_openai_cls):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _make_response("ok", 1)
    mock_openai_cls.return_value = mock_client

    client = LLMClient()  # language defaults to ""
    client.chat(messages=[{"role": "user", "content": "hi"}])

    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    # Only the user message survives; no language system prompt prepended.
    assert sent_messages == [{"role": "user", "content": "hi"}]
