from __future__ import annotations

from unittest.mock import MagicMock, patch

from unveiling.search.engine import search


# ---------------------------------------------------------------------------
# Default priority chain: exa > serper > llm_fallback
# ---------------------------------------------------------------------------

@patch("unveiling.search.engine.serper_search")
@patch("unveiling.search.exa.search")
def test_default_uses_exa_first(mock_exa, mock_serper):
    mock_exa.return_value = [{"title": "exa", "link": "u", "snippet": "s"}]

    with patch.dict("os.environ", {}, clear=False):
        results = search("query")

    assert results == [{"title": "exa", "link": "u", "snippet": "s"}]
    mock_exa.assert_called_once()
    mock_serper.assert_not_called()


@patch("unveiling.search.llm_fallback.search")
@patch("unveiling.search.engine.serper_search")
@patch("unveiling.search.exa.search")
def test_default_falls_back_to_serper_on_exa_error(
    mock_exa, mock_serper, mock_llm
):
    mock_exa.side_effect = Exception("exa down")
    mock_serper.return_value = [{"title": "serper", "link": "u", "snippet": "s"}]

    with patch.dict("os.environ", {}, clear=False):
        results = search("query")

    assert results == [{"title": "serper", "link": "u", "snippet": "s"}]
    mock_exa.assert_called_once()
    mock_serper.assert_called_once()
    mock_llm.assert_not_called()


@patch("unveiling.search.llm_fallback.search")
@patch("unveiling.search.engine.serper_search")
@patch("unveiling.search.exa.search")
def test_default_falls_back_to_llm_on_all_errors(
    mock_exa, mock_serper, mock_llm
):
    mock_exa.side_effect = Exception("exa down")
    mock_serper.side_effect = Exception("serper down")
    mock_llm.return_value = [{"title": "llm", "link": "u", "snippet": "s"}]

    with patch.dict("os.environ", {}, clear=False):
        results = search("query")

    assert results == [{"title": "llm", "link": "u", "snippet": "s"}]
    mock_exa.assert_called_once()
    mock_serper.assert_called_once()
    mock_llm.assert_called_once()


# ---------------------------------------------------------------------------
# Explicit backend selection
# ---------------------------------------------------------------------------

@patch("unveiling.search.engine.serper_search")
def test_serper_engine_direct(mock_serper):
    mock_serper.return_value = [{"title": "sp", "link": "u", "snippet": "s"}]

    with patch.dict("os.environ", {"SEARCH_ENGINE": "serper"}, clear=False):
        results = search("query")

    assert results == [{"title": "sp", "link": "u", "snippet": "s"}]
    mock_serper.assert_called_once_with("query", num=8, far_search_hint="", lang="")


@patch("unveiling.search.wikipedia.search")
def test_wikipedia_engine_direct(mock_wikipedia):
    mock_wikipedia.return_value = [{"title": "wiki", "link": "u", "snippet": "s"}]

    with patch.dict("os.environ", {"SEARCH_ENGINE": "wikipedia"}, clear=False):
        results = search("query", num=3, far_search_hint="history")

    assert results == [{"title": "wiki", "link": "u", "snippet": "s"}]
    mock_wikipedia.assert_called_once_with("query", num=3, far_search_hint="history", lang="")


@patch("unveiling.search.exa.search")
def test_exa_engine_direct(mock_exa):
    mock_exa.return_value = [{"title": "exa", "link": "u", "snippet": "s"}]

    with patch.dict("os.environ", {"SEARCH_ENGINE": "exa"}, clear=False):
        results = search("query")

    assert results == [{"title": "exa", "link": "u", "snippet": "s"}]
    mock_exa.assert_called_once()


@patch("unveiling.search.engine.serper_search")
@patch("unveiling.search.exa.search")
def test_exa_fallback_to_serper(mock_exa, mock_serper):
    mock_exa.side_effect = Exception("exa crashed")
    mock_serper.return_value = [{"title": "fallback", "link": "u", "snippet": "s"}]

    with patch.dict("os.environ", {"SEARCH_ENGINE": "exa"}, clear=False):
        results = search("query")

    assert results == [{"title": "fallback", "link": "u", "snippet": "s"}]
    mock_exa.assert_called_once()
    mock_serper.assert_called_once()


@patch("unveiling.search.exa.search")
def test_passes_all_args(mock_exa):
    mock_exa.return_value = [{"title": "t", "link": "l", "snippet": "s"}]

    with patch.dict("os.environ", {}, clear=False):
        results = search("my query", num=5, far_search_hint="niche hint", lang="中文")

    mock_exa.assert_called_once_with(
        "my query", num=5, far_search_hint="niche hint", lang="中文"
    )
