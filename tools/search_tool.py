import os
import requests
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query string")


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Search the web using Google via Serper API. Returns relevant "
        "results with titles, URLs, and snippets. Use this to find information "
        "about topics, historical events, cross-domain examples, and evidence."
    )
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        api_key = os.environ.get("SERPER_API_KEY", "")
        if not api_key:
            return (
                f"Serper API key not configured. Set SERPER_API_KEY in .env. "
                f"Falling back to LLM knowledge for: '{query}'"
            )

        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                },
                json={"q": query, "num": 8},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("organic", []):
                title = item.get("title", "")
                link = item.get("link", "")
                snippet = item.get("snippet", "")
                results.append(f"- {title}\n  {link}\n  {snippet}")

            if results:
                return "\n\n".join(results)
            return f"No results found for: {query}"

        except Exception as e:
            return f"Search error: {e}. Falling back to LLM knowledge for: '{query}'"


def create_search_tool():
    return WebSearchTool()
