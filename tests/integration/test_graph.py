from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from graph.build import build_graph
from models.state import State
from models._enums import Phase


def _mock_inception_response():
    return json.dumps({
        "driving_question": "Should AI companies burn cash for expansion?",
        "sub_questions": [
            "What are the unit economics of cash burn?",
            "What is the competitive landscape?",
        ],
        "lenses": [{"name": "Amazon", "rationale": "Early growth strategy"}],
        "predictions": [{
            "claim": "Cash burn leads to market dominance",
            "if_true_we_should_see": "Market share growth",
            "if_false_we_should_see": "Bankruptcy filings",
            "killer_evidence": "Quarterly earnings showing sustained losses but growing market share",
        }],
    })


def _mock_convergence_response():
    return json.dumps({
        "convergent_finding": "Cash burn is risky but sometimes necessary.",
        "tension": "Growth vs survival trade-off.",
        "boundary_condition": "Requires 18+ months runway.",
        "unresolved": "Long-term profitability unclear.",
        "implication": "Depends on market conditions.",
    })


def _mock_search_response():
    return json.dumps({
        "evidence_list": [
            {
                "content": "Cash burn common in high-growth phases.",
                "layer": "structure",
                "confidence": "strong",
                "is_unexpected": False,
            }
        ]
    })


def test_graph_converges_with_mocked_llm():
    """End-to-end graph test with mocked LLM to avoid API costs."""
    graph = build_graph()
    state = State(user_question="Should AI companies burn cash for expansion?")

    call_count = 0
    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        # First call = inception, subsequent calls = search/convergence
        if call_count == 1:
            return _mock_inception_response(), 500
        # Check if it's a convergence prompt by looking at the messages
        messages = args[0] if args else kwargs.get("messages", [])
        prompt = messages[0].get("content", "") if messages else ""
        if "synthesis analyst" in prompt or "tension-style" in prompt:
            return _mock_convergence_response(), 600
        return _mock_search_response(), 400

    with patch("llm.client.OpenAI") as mock_openai, \
         patch("agents.inception.LLMClient.chat") as mock_inception, \
         patch("agents.convergence.LLMClient.chat") as mock_conv, \
         patch("agents.search.LLMClient.chat") as mock_search, \
         patch("agents.search.search") as mock_serper:

        mock_openai.return_value = MagicMock()

        mock_inception.side_effect = side_effect
        mock_conv.side_effect = side_effect
        mock_search.side_effect = side_effect
        mock_serper.return_value = [
            {"title": "Test", "snippet": "Cash burn is common.", "link": "http://example.com"}
        ]

        result = graph.invoke(state, {"recursion_limit": 50})

    assert result["phase"] == Phase.convergence
    assert result["round_count"] > 0
    assert len(result["issue_tree"]) >= 3  # driving + 2 sub-questions
    assert len(result["conclusion_zone"]) == 1
    assert result["conclusion_zone"][0].tension != ""
