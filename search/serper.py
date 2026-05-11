from __future__ import annotations

import os

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def search(query: str, num: int = 8, far_search_hint: str = "") -> list[dict]:
    """Search Google via Serper API.

    Args:
        query: Search query string.
        num: Number of results to return (max 10 for free tier).
        far_search_hint: Optional hint to bias query toward冷门/structural analogies.

    Returns:
        List of result dicts with keys: title, link, snippet.

    Raises:
        ValueError: If SERPER_API_KEY is not configured.
        requests.HTTPError: On non-2xx responses after retries.
    """
    api_key = os.environ.get("SERPER_API_KEY", "")
    if not api_key:
        raise ValueError("SERPER_API_KEY not configured in environment")

    actual_query = query
    if far_search_hint:
        actual_query = f"{query} {far_search_hint}"

    resp = requests.post(
        "https://google.serper.dev/search",
        headers={
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        },
        json={"q": actual_query, "num": num},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })

    return results
