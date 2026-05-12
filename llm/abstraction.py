from __future__ import annotations

import json

from llm.client import LLMClient, LLMJSONError


_ABSTRACTION_PROMPT = """\
Below is a question or topic. Identify its structural essence — what is this thing REALLY about, at the level of forces, mechanisms, and causal dynamics?

Input:
{input_text}

{context_section}

Think like a sharp analyst making a first-cut diagnosis. Your job is NOT to invent a clever metaphor — it is to surface the real forces and mechanisms at play so that the topic can be rigorously investigated and compared across domains.

Output a JSON object:
- "pattern_name": a SHORT, CONCRETE description of the core dynamic. Think analytical framework, not metaphor. Good examples: "前卫生产力引发的替代焦虑", "技术革命期的技能错配", "注意力经济对认知的重塑". Bad examples: "追影困局", "Shadow Chasing Trap", "守城效应".
- "essence": 2-3 sentences identifying (a) the core nature of the subject — what IS this thing structurally, and (b) the key causal mechanisms — WHY does it produce the observed effects. Be specific. Name actual forces, processes, and dynamics.
- "core_tension": the fundamental conflict or paradox, expressed in concrete terms tied to the actual subject matter. Not a philosophical riddle — a real, investigable tension between opposing forces.
- "dimensions": 2-4 specific investigative angles. Each should be a concrete question about actual mechanisms, causes, historical precedents, or structural factors that a researcher could actually search for evidence about.

Rules:
- Stay grounded in the actual subject matter. The abstraction should identify structural FORCES and MECHANISMS, not strip away content into a universal metaphor.
- The abstraction must still enable cross-domain comparison — identify the structural role (e.g., "frontier productive force", "attention capture mechanism") so that analogous cases from other domains or time periods can be found.
- Do NOT invent metaphors, allegories, or poetic images. Do NOT use names like "X困局", "Y效应", "Z陷阱".
- STYLE: clear, specific, analytical. Write like a thoughtful analyst, not a poet.
- Output valid JSON only. No markdown, no commentary.
"""


def abstract(input_text: str, context: str = "", language: str = "") -> tuple[dict, int]:
    """Core cognitive primitive: take concrete or semi-abstract input, return a structural abstraction.

    Callable by any agent, any number of times:
    - inception: abstract("AI 焦虑") → initial pattern + dimensions
    - deepdig: abstract(evidence_text, context="sub-question: ...") → deeper structural finding
    - lens_op: abstract(evidence + current_lens, context="evolve lens") → evolved pattern
    - can call recursively: abstract(result) → even deeper

    Returns:
        (abstraction_dict, tokens_consumed)
        abstraction_dict keys: pattern_name, essence, core_tension, dimensions
    """
    context_section = f"Context:\n{context}" if context else ""
    prompt = _ABSTRACTION_PROMPT.format(
        input_text=input_text,
        context_section=context_section,
    )

    client = LLMClient(language=language)
    content, tokens = client.chat(
        [{"role": "user", "content": prompt}],
        json_mode=True,
        temperature=0.7,
    )

    return json.loads(content), tokens
