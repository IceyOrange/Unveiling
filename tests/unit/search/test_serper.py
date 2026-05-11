from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from search.serper import search


def _make_response(json_body: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status_code} error")
    else:
        resp.raise_for_status.return_value = None
    return resp


@patch.dict("os.environ", {"SERPER_API_KEY": "test-key"})
@patch("search.serper.requests.post")
def test_search_success(mock_post):
    mock_post.return_value = _make_response({
        "organic": [{"title": "t", "snippet": "s", "link": "u"}]
    })

    results = search("query")

    assert results == [{"title": "t", "link": "u", "snippet": "s"}]


@patch.dict("os.environ", {"SERPER_API_KEY": "test-key"})
@patch("search.serper.requests.post")
def test_search_empty_results(mock_post):
    mock_post.return_value = _make_response({"organic": []})

    results = search("query")

    assert results == []


@patch.dict("os.environ", {"SERPER_API_KEY": ""}, clear=False)
@patch("search.serper.requests.post")
def test_search_missing_api_key(mock_post):
    with pytest.raises(ValueError) as exc_info:
        search("query")

    assert "SERPER_API_KEY" in str(exc_info.value)
    mock_post.assert_not_called()


@patch.dict("os.environ", {"SERPER_API_KEY": "test-key"})
@patch("search.serper.requests.post")
def test_search_passes_query_correctly(mock_post):
    mock_post.return_value = _make_response({"organic": []})

    search("my special query", num=5)

    assert mock_post.call_count == 1
    call_args = mock_post.call_args
    # URL
    assert call_args.args[0] == "https://google.serper.dev/search"
    # Headers
    headers = call_args.kwargs["headers"]
    assert headers["X-API-KEY"] == "test-key"
    assert headers["Content-Type"] == "application/json"
    # Body
    body = call_args.kwargs["json"]
    assert body["q"] == "my special query"
    assert body["num"] == 5


@patch.dict("os.environ", {"SERPER_API_KEY": "test-key"})
@patch("search.serper.requests.post")
def test_search_appends_far_search_hint(mock_post):
    mock_post.return_value = _make_response({"organic": []})

    search("base query", far_search_hint="historical analogy")

    body = mock_post.call_args.kwargs["json"]
    assert body["q"] == "base query historical analogy"


@patch.dict("os.environ", {"SERPER_API_KEY": "test-key"})
@patch("search.serper.requests.post")
def test_search_retries_on_failure_then_succeeds(mock_post):
    # First two calls raise, third succeeds. tenacity should retry.
    success = _make_response({"organic": [{"title": "ok", "link": "l", "snippet": "s"}]})
    fail = MagicMock()
    fail.raise_for_status.side_effect = requests.HTTPError("500 server error")

    mock_post.side_effect = [fail, fail, success]

    # Patch wait_exponential's sleep to avoid waiting in tests.
    with patch("tenacity.nap.time.sleep"):
        results = search("query")

    assert results == [{"title": "ok", "link": "l", "snippet": "s"}]
    assert mock_post.call_count == 3
