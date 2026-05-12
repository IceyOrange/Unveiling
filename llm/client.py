from __future__ import annotations

import json
import os
from typing import Optional

import openai
from openai import OpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


# Transient errors worth retrying; auth and request-shape errors propagate immediately.
_TRANSIENT_OPENAI_ERRORS = (
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.RateLimitError,
    openai.InternalServerError,
)


class LLMJSONError(Exception):
    """Raised when JSON parsing fails after all retries."""

    pass


class LLMClient:
    """DeepSeek client wrapper with retry, JSON parsing, and token accounting.

    Since DeepSeek does not support response_format, json_mode injects
    an instruction and retries on malformed output.
    """

    def __init__(self, model: Optional[str] = None, language: str = ""):
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            base_url=os.environ.get("OPENAI_API_BASE", "https://api.deepseek.com"),
        )
        self.model = model or os.environ.get("OPENAI_MODEL_NAME", "deepseek-chat")
        self.language = language

    def chat(
        self,
        messages: list[dict],
        json_mode: bool = False,
        max_retries: int = 3,
        temperature: float = 0.7,
        language: str = "",
    ) -> tuple[str, int]:
        """Send a chat completion request.

        Args:
            messages: OpenAI-style message list.
            json_mode: If True, enforce JSON-only output with retry loop.
            max_retries: Maximum JSON parse retries (only when json_mode=True).
            temperature: Sampling temperature.
            language: If set, instruct the LLM to respond in this language (e.g. "中文", "English").

        Returns:
            Tuple of (content, tokens_consumed).

        Raises:
            LLMJSONError: If json_mode is True and parsing fails after all retries.
        """
        effective_language = language or self.language
        if effective_language:
            messages = self._inject_language(messages, effective_language)
        if json_mode:
            messages = self._ensure_json_instruction(messages)

        total_tokens = 0
        current_messages = list(messages)

        for attempt in range(max_retries):
            response = self._create_completion(
                messages=current_messages,
                temperature=0.1 if json_mode else temperature,
            )

            content = response.choices[0].message.content or ""
            total_tokens += response.usage.total_tokens if response.usage else 0

            if not json_mode:
                return content, total_tokens

            try:
                json.loads(content)
                return content, total_tokens
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    current_messages = current_messages + [
                        {"role": "assistant", "content": content},
                        {
                            "role": "user",
                            "content": (
                                "That was not valid JSON. "
                                "Please respond with valid JSON only, "
                                "without markdown formatting or explanatory text."
                            ),
                        },
                    ]
                    continue
                else:
                    raise LLMJSONError(
                        f"Failed to parse JSON after {max_retries} attempts. "
                        f"Last response: {content[:200]}"
                    )

        return "", total_tokens

    @retry(
        retry=retry_if_exception_type(_TRANSIENT_OPENAI_ERRORS),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def _create_completion(self, *, messages: list[dict], temperature: float):
        """Single completion call with tenacity retry on transient transport errors."""
        return self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )

    @staticmethod
    def _inject_language(messages: list[dict], language: str) -> list[dict]:
        instruction = (
            f"IMPORTANT: Write ALL text content in {language}. "
            f"This includes names, descriptions, explanations, findings, questions, "
            f"and any other natural-language text. "
            f"Only keep JSON keys and structural formatting in English. "
            f"Do NOT use English for content that should be in {language}."
        )

        if messages and messages[0].get("role") == "system":
            updated = list(messages)
            updated[0] = {
                "role": "system",
                "content": messages[0]["content"] + "\n\n" + instruction,
            }
            return updated

        return [{"role": "system", "content": instruction}] + list(messages)

    @staticmethod
    def _ensure_json_instruction(messages: list[dict]) -> list[dict]:
        instruction = (
            "Respond with valid JSON only. "
            "Do not include markdown formatting or explanatory text."
        )

        if messages and messages[0].get("role") == "system":
            updated = list(messages)
            updated[0] = {
                "role": "system",
                "content": messages[0]["content"] + "\n\n" + instruction,
            }
            return updated

        return [{"role": "system", "content": instruction}] + list(messages)
