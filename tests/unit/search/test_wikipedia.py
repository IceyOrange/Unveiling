from __future__ import annotations

from unittest.mock import MagicMock, patch

from unveiling.search.wikipedia import search


class FakePagesDict:
    def __init__(self, pages: dict[str, object]):
        self._pages = pages

    def items(self):
        return self._pages.items()

    def keys(self):
        return self._pages.keys()


class FakeSearchResults:
    def __init__(self, pages: dict[str, object]):
        self.pages = FakePagesDict(pages)
        self.totalhits = len(pages)
        self.suggestion = None


class FakePage:
    def __init__(self, title: str, exists: bool = True, summary: str = ""):
        self.title = title
        self._exists = exists
        self.summary = summary
        self.fullurl = f"https://zh.wikipedia.org/wiki/{title.replace(' ', '_')}"

    def exists(self):
        return self._exists


class FakeWiki:
    def __init__(self, pages: dict[str, FakePage]):
        self._pages = pages

    def search(self, query: str, limit: int = 10):
        # Return up to `limit` pages
        sliced = dict(list(self._pages.items())[:limit])
        return FakeSearchResults(sliced)


def test_search_returns_structured_results():
    pages = {
        "人工智能": FakePage("人工智能", summary="AI is a field of computer science."),
        "机器学习": FakePage("机器学习", summary="ML is a subset of AI."),
    }
    fake = FakeWiki(pages)

    with patch("unveiling.search.wikipedia.wikipediaapi.Wikipedia", return_value=fake):
        results = search("AI", num=5)

    assert len(results) == 2
    assert results[0]["title"] == "人工智能"
    assert "snippet" in results[0]
    assert results[0]["link"].startswith("https://zh.wikipedia.org")


def test_search_respects_num_limit():
    pages = {
        "A": FakePage("A", summary="summary A"),
        "B": FakePage("B", summary="summary B"),
        "C": FakePage("C", summary="summary C"),
    }
    fake = FakeWiki(pages)

    with patch("unveiling.search.wikipedia.wikipediaapi.Wikipedia", return_value=fake):
        results = search("test", num=2)

    assert len(results) == 2


def test_search_appends_far_search_hint():
    captured_query: list[str] = []

    class TrackedFakeWiki(FakeWiki):
        def search(self, query: str, limit: int = 10):
            captured_query.append(query)
            return FakeSearchResults({})

    fake = TrackedFakeWiki({})

    with patch("unveiling.search.wikipedia.wikipediaapi.Wikipedia", return_value=fake):
        search("AI", num=5, far_search_hint="history")

    assert captured_query == ["AI history"]


def test_search_skips_nonexistent_pages():
    pages = {
        " exists ": FakePage(" exists ", summary="ok"),
        "missing": FakePage("missing", exists=False),
    }
    fake = FakeWiki(pages)

    with patch("unveiling.search.wikipedia.wikipediaapi.Wikipedia", return_value=fake):
        results = search("test", num=5)

    assert len(results) == 1
    assert results[0]["title"] == " exists "


def test_search_gracefully_handles_search_exception():
    class BrokenWiki:
        def search(self, query: str, limit: int = 10):
            raise RuntimeError("network failure")

    with patch("unveiling.search.wikipedia.wikipediaapi.Wikipedia", return_value=BrokenWiki()):
        results = search("test", num=5)

    assert results == []


def test_search_uses_chinese_for_zh():
    captured_lang: list[str] = []

    class TrackingWiki(FakeWiki):
        def __init__(self, language, *args, **kwargs):
            captured_lang.append(language)
            super().__init__({})

    with patch("unveiling.search.wikipedia.wikipediaapi.Wikipedia", side_effect=TrackingWiki):
        search("test", num=5, lang="中文")

    assert captured_lang == ["zh"]


def test_search_uses_english_for_english():
    captured_lang: list[str] = []

    class TrackingWiki(FakeWiki):
        def __init__(self, language, *args, **kwargs):
            captured_lang.append(language)
            super().__init__({})

    with patch("unveiling.search.wikipedia.wikipediaapi.Wikipedia", side_effect=TrackingWiki):
        search("test", num=5, lang="English")

    assert captured_lang == ["en"]


def test_search_defaults_to_zh_for_unknown_lang():
    captured_lang: list[str] = []

    class TrackingWiki(FakeWiki):
        def __init__(self, language, *args, **kwargs):
            captured_lang.append(language)
            super().__init__({})

    with patch("unveiling.search.wikipedia.wikipediaapi.Wikipedia", side_effect=TrackingWiki):
        search("test", num=5, lang="Français")

    assert captured_lang == ["zh"]
