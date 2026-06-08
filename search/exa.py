# Exa semantic search adapter — same interface as serper.py / websearch.py

from __future__ import annotations

import os

from exa_py import Exa
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def search(query: str, num: int = 8, far_search_hint: str = "", lang: str = "") -> list[dict]:
    """Search via Exa semantic/neural search API.

    Args:
        query: Search query string.
        num: Number of results to return.
        far_search_hint: Optional hint to bias query toward niche/structural analogies.
        lang: Output language label (e.g. "中文" or "English").

    Returns:
        List of result dicts with keys: title, link, snippet.

    Raises:
        ConnectionError: If Exa API is unreachable.
        requests.HTTPError: On non-2xx responses after retries.
    """
    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        raise ConnectionError("EXA_API_KEY environment variable is not set")

    actual_query = query
    if far_search_hint:
        actual_query = f"{query} {far_search_hint}"

    exa = Exa(api_key=api_key)

    try:
        response = exa.search(
            actual_query,
            type="auto",
            num_results=num,
            contents={"highlights": True},
        )
    except Exception as exc:
        raise ConnectionError(f"Exa API request failed: {exc}") from exc

    results = []
    for item in response.results:
        highlights = item.highlights if hasattr(item, "highlights") and item.highlights else []
        snippet = highlights[0] if highlights else getattr(item, "text", "")
        results.append({
            "title": getattr(item, "title", "") or "",
            "link": getattr(item, "url", "") or "",
            "snippet": snippet or "",
        })

    return results
