# LLM fallback search — generates results when all web engines fail.

from __future__ import annotations

import json

from unveiling.llm.client import LLMClient, LLMJSONError


def search(query: str, num: int = 8, far_search_hint: str = "", lang: str = "") -> list[dict]:
    """Generate search results via LLM when Exa and Serper are unavailable.

    Results are LLM-generated and may contain hallucinations. They should
    be treated as "unverified hypotheses" rather than ground truth.
    The enrichment layer (Wikipedia → web search) will attempt to validate
    them when case names are extracted.

    Args:
        query: Search query string.
        num: Number of results to request.
        far_search_hint: Optional hint to bias query toward niche/structural analogies.
        lang: Output language label (e.g. "中文" or "English").

    Returns:
        List of result dicts with keys: title, link, snippet.
    """
    actual_query = f"{query} {far_search_hint}" if far_search_hint else query

    client = LLMClient(language=lang)

    prompt = (
        f"根据以下查询，生成 {num} 条相关的知识条目。\n\n"
        f"查询：{actual_query}\n\n"
        "请输出 JSON：\n"
        '{"results": [\n'
        '    {"title": "...", "url": "...", "description": "..."},\n'
        "    ...\n"
        "]}\n\n"
        "注意：\n"
        "- 每个条目必须有具体的标题\n"
        "- 描述要包含关键事实和细节\n"
        "- 如果查询涉及类比，返回的条目应该是真实存在的案例\n"
        "- 来源链接如果不确定可以留空"
    )

    try:
        content, _ = client.chat(
            [{"role": "user", "content": prompt}],
            json_mode=True,
            temperature=0.7,
        )
        data = json.loads(content)
        results = data.get("results", [])
        return [
            {
                "title": str(r.get("title", "")),
                "link": str(r.get("url", "")),
                "snippet": str(r.get("description", "")),
            }
            for r in results
        ]
    except (LLMJSONError, json.JSONDecodeError, Exception):
        return []
