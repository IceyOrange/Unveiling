from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from unveiling.search.exa import search


class FakeExaResult:
    def __init__(self, title: str, url: str, highlights: list[str] | None = None, text: str = ""):
        self.title = title
        self.url = url
        self.highlights = highlights or []
        self.text = text


class FakeExaResponse:
    def __init__(self, results: list[FakeExaResult]):
        self.results = results


def _make_exa_mock(results: list[FakeExaResult]):
    fake_response = FakeExaResponse(results)
    mock_exa = MagicMock()
    mock_exa.search.return_value = fake_response
    return mock_exa


@patch("unveiling.search.exa.Exa")
def test_search_success(mock_exa_cls):
    mock_exa_cls.return_value = _make_exa_mock([
        FakeExaResult("T1", "http://a", highlights=["Snippet A"], text="Text A"),
        FakeExaResult("T2", "http://b", highlights=[], text="Text B"),
    ])

    with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}, clear=False):
        results = search("query", num=5)

    assert len(results) == 2
    assert results[0] == {"title": "T1", "link": "http://a", "snippet": "Snippet A"}
    assert results[1] == {"title": "T2", "link": "http://b", "snippet": "Text B"}

    call_args = mock_exa_cls.return_value.search.call_args
    assert call_args[0][0] == "query"
    assert call_args.kwargs["num_results"] == 5


@patch("unveiling.search.exa.Exa")
def test_search_empty_results(mock_exa_cls):
    mock_exa_cls.return_value = _make_exa_mock([])

    with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}, clear=False):
        results = search("query")

    assert results == []


@patch("unveiling.search.exa.Exa")
def test_search_with_far_search_hint(mock_exa_cls):
    mock_exa_cls.return_value = _make_exa_mock([])

    with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}, clear=False):
        search("base query", far_search_hint="historical analogy")

    call_args = mock_exa_cls.return_value.search.call_args
    assert call_args[0][0] == "base query historical analogy"


@patch("unveiling.search.exa.Exa")
def test_search_uses_env_api_key(mock_exa_cls):
    mock_exa_cls.return_value = _make_exa_mock([])

    with patch.dict("os.environ", {"EXA_API_KEY": "my-secret-key"}, clear=False):
        search("query")

    mock_exa_cls.assert_called_once_with(api_key="my-secret-key")


def test_search_missing_api_key():
    with patch.dict("os.environ", {"EXA_API_KEY": ""}, clear=False):
        with pytest.raises(ConnectionError) as exc_info:
            search("query")
    assert "EXA_API_KEY" in str(exc_info.value)


@patch("unveiling.search.exa.Exa")
def test_search_api_exception(mock_exa_cls):
    mock_exa_cls.return_value.search.side_effect = RuntimeError("network failure")

    with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}, clear=False):
        with pytest.raises(ConnectionError) as exc_info:
            search("query")

    assert "Exa API request failed" in str(exc_info.value)


@patch("unveiling.search.exa.Exa")
def test_search_result_without_highlights_uses_text(mock_exa_cls):
    mock_exa_cls.return_value = _make_exa_mock([
        FakeExaResult("T", "http://x", highlights=[], text="Fallback text"),
    ])

    with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}, clear=False):
        results = search("query")

    assert results[0]["snippet"] == "Fallback text"


@patch("unveiling.search.exa.Exa")
def test_search_result_without_highlights_or_text(mock_exa_cls):
    mock_exa_cls.return_value = _make_exa_mock([
        FakeExaResult("T", "http://x", highlights=[], text=""),
    ])

    with patch.dict("os.environ", {"EXA_API_KEY": "test-key"}, clear=False):
        results = search("query")

    assert results[0]["snippet"] == ""
