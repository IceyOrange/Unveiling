# Wikipedia search adapter — same interface as serper.py / websearch.py

from __future__ import annotations

import time

import wikipediaapi
from tenacity import retry, stop_after_attempt, wait_exponential


# Map frontend language labels to Wikipedia language codes.
_LANG_MAP = {
    "中文": "zh",
    "English": "en",
}


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def _search(wiki, query: str, num: int) -> list[tuple[str, wikipediaapi.Page]]:
    """Search Wikipedia and return (title, page) pairs."""
    results = wiki.search(query, limit=num)
    return list(results.pages.items())


def search(query: str, num: int = 5, far_search_hint: str = "", lang: str = "") -> list[dict]:
    """Search Wikipedia articles by keyword.

    Args:
        query: Search keyword.
        num: Maximum number of results to return.
        far_search_hint: Appended to query; kept for interface parity.
        lang: Output language label (e.g. "中文" or "English").
              Mapped to Wikipedia language codes; defaults to "zh".

    Returns:
        List of result dicts with keys: title, link, snippet.
    """
    actual_query = f"{query} {far_search_hint}" if far_search_hint else query

    wiki_lang = _LANG_MAP.get(lang, "zh")

    wiki = wikipediaapi.Wikipedia(
        language=wiki_lang,
        user_agent="Unveiling/1.0 (research@unveiling.local)",
    )

    try:
        pages = _search(wiki, actual_query, num)
    except Exception:
        return []

    results: list[dict] = []
    for title, page in pages:
        if not page.exists():
            continue
        results.append({
            "title": page.title,
            "link": page.fullurl,
            "snippet": (page.summary or "")[:400],
        })
        # Throttle consecutive requests to avoid Wikimedia rate limits.
        time.sleep(0.5)

    return results
