# Unified search router — picks backend based on SEARCH_ENGINE env var.

from __future__ import annotations

import os

from search.serper import search as serper_search


def search(query: str, num: int = 8, far_search_hint: str = "", lang: str = "") -> list[dict]:
    """Route to the configured search backend.

    Priority when SEARCH_ENGINE is not set:
        Exa -> Serper -> LLM fallback

    Wikipedia is kept as an explicit option (SEARCH_ENGINE=wikipedia)
    and is used as a knowledge enrichment layer after cases are found.

    Args:
        query: Search query string.
        num: Number of results to return.
        far_search_hint: Optional hint to bias query toward niche/structural analogies.
        lang: Output language label (e.g. "中文" or "English").

    Returns:
        List of result dicts with keys: title, link, snippet.
    """
    engine = os.environ.get("SEARCH_ENGINE", "")

    if engine == "serper":
        return serper_search(query, num=num, far_search_hint=far_search_hint, lang=lang)

    if engine == "wikipedia":
        from search.wikipedia import search as wikipedia_search
        return wikipedia_search(query, num=num, far_search_hint=far_search_hint, lang=lang)

    if engine == "exa":
        from search.exa import search as exa_search
        try:
            return exa_search(query, num=num, far_search_hint=far_search_hint, lang=lang)
        except Exception:
            return serper_search(query, num=num, far_search_hint=far_search_hint, lang=lang)

    # Auto-priority when SEARCH_ENGINE is not set: exa > serper > llm_fallback
    from search.exa import search as exa_search
    try:
        return exa_search(query, num=num, far_search_hint=far_search_hint, lang=lang)
    except Exception:
        pass

    try:
        return serper_search(query, num=num, far_search_hint=far_search_hint, lang=lang)
    except Exception:
        pass

    from search.llm_fallback import search as llm_fallback_search
    return llm_fallback_search(query, num=num, far_search_hint=far_search_hint, lang=lang)
