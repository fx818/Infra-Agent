"""
Abstract LLM provider and OpenAI-compatible implementation.

The provider layer is designed to be pluggable — swap the base URL
and model name in .env to point at any OpenAI-compatible API
(OpenAI, Azure OpenAI, Anthropic via proxy, vLLM, Ollama, etc.).
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """
        Generate a structured JSON response from the LLM.

        Args:
            system_prompt: System instruction for the LLM.
            user_prompt: User message / context.
            response_format: Optional JSON schema hint for structured output.
            temperature: Sampling temperature.

        Returns:
            Parsed JSON dict from the LLM response.
        """
        ...


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    LLM provider using the OpenAI Python SDK.

    Works with any API that exposes the OpenAI chat completions interface.
    Configure via LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL in .env.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("API Key must be provided. Global default is disabled.")

        self.client = AsyncOpenAI(
            base_url=base_url or settings.LLM_BASE_URL,
            api_key=api_key,
        )
        self.model = model or settings.LLM_MODEL

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """Call the LLM and return parsed JSON."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        # Request JSON mode if supported
        if response_format:
            kwargs["response_format"] = response_format
        else:
            kwargs["response_format"] = {"type": "json_object"}

        logger.info("LLM request: model=%s, temperature=%s", self.model, temperature)

        response = await self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"

        logger.debug("LLM raw response: %s", content[:500])

        # Parse JSON from the response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0].strip()
                return json.loads(json_str)
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0].strip()
                return json.loads(json_str)
            raise ValueError(f"LLM response is not valid JSON: {content[:200]}")


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get the configured LLM provider."""
    raise NotImplementedError("Global LLM provider is disabled. Use user-specific provider.")
