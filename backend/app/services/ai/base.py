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

# Maximum tool-calling iterations to prevent infinite loops
MAX_TOOL_CALL_ITERATIONS = 30


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

    @abstractmethod
    async def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_executor: Any,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """
        Generate a response using tool calling.

        The LLM is given a list of tools and can call them iteratively.
        The tool_executor is called for each tool invocation.

        Args:
            system_prompt: System instruction for the LLM.
            user_prompt: User message / context.
            tools: List of OpenAI-format tool definitions.
            tool_executor: Callable(name, args) -> str that executes tools.
            temperature: Sampling temperature.

        Returns:
            Dict with "message" (final LLM text), "tool_calls" (list of all calls made).
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

    async def generate_with_tools(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_executor: Any,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        """
        Run LLM tool-calling via prompt-based approach.

        Instead of relying on native tool-calling API support (which not all
        models/providers handle correctly), we embed tool definitions in the
        system prompt and ask the LLM to output tool calls as JSON. We parse
        and execute them, then feed results back iteratively.
        """
        # Build compact tool descriptions for the prompt
        tool_descriptions = []
        for t in tools:
            fn = t["function"]
            params_summary = ", ".join(
                f'{k}: {v.get("type", "string")}'
                for k, v in fn.get("parameters", {}).get("properties", {}).items()
            )
            required = fn.get("parameters", {}).get("required", [])
            tool_descriptions.append(
                f'- **{fn["name"]}**({params_summary}) — {fn["description"][:100]}'
                f'\n  Required: {", ".join(required) if required else "none"}'
            )

        tools_text = "\n".join(tool_descriptions)

        tool_calling_instructions = f"""
## Available Tools

{tools_text}

## How to Call Tools

To call tools, respond with a JSON array of tool calls:

```json
[{{"name": "tool_name", "parameters": {{"param1": "value1"}}}}]
```

Call one or more tools per response. After I return results, you may call more tools.
When you are DONE creating all resources, respond with a plain text summary (no JSON array).
"""

        full_system_prompt = system_prompt + "\n" + tool_calling_instructions

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        all_tool_calls: list[dict[str, Any]] = []

        for iteration in range(MAX_TOOL_CALL_ITERATIONS):
            logger.info(
                "Tool-call iteration %d: model=%s, %d messages",
                iteration + 1, self.model, len(messages),
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )

            content = response.choices[0].message.content or ""
            logger.debug("LLM response (iter %d): %s", iteration + 1, content[:500])

            # Try to parse tool calls from the response
            parsed_calls = self._extract_tool_calls(content)

            if not parsed_calls:
                # No tool calls found — this is the final summary
                logger.info(
                    "Tool-calling complete after %d iterations, %d total tool calls",
                    iteration + 1, len(all_tool_calls),
                )
                return {
                    "message": content,
                    "tool_calls": all_tool_calls,
                }

            # Execute each parsed tool call
            results_text_parts = []
            for call in parsed_calls:
                fn_name = call.get("name", "")
                fn_args = call.get("parameters", {})

                logger.info("Executing tool: %s(%s)", fn_name, json.dumps(fn_args)[:200])

                try:
                    result_str = await tool_executor(fn_name, fn_args)
                except Exception as e:
                    logger.error("Tool execution failed: %s — %s", fn_name, e)
                    result_str = json.dumps({"error": str(e)})

                all_tool_calls.append({
                    "name": fn_name,
                    "arguments": fn_args,
                    "result": result_str,
                })
                results_text_parts.append(f"**{fn_name}**: {result_str}")

            # Feed results back as an assistant+user pair
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": "Tool results:\n\n" + "\n\n".join(results_text_parts)
                    + "\n\nContinue creating resources or provide a final summary if done.",
            })

        logger.warning("Hit max tool-call iterations (%d)", MAX_TOOL_CALL_ITERATIONS)
        return {
            "message": "Architecture generation completed (max iterations reached).",
            "tool_calls": all_tool_calls,
        }

    @staticmethod
    def _extract_tool_calls(content: str) -> list[dict[str, Any]]:
        """Extract tool call JSON arrays from LLM response text.

        Handles:
        - ```json [...] ``` code blocks
        - Raw JSON arrays [...]
        - Single tool call objects {...}
        """
        import re

        # Try to find JSON in code blocks first
        code_block_match = re.search(r"```(?:json)?\s*\n?(\[[\s\S]*?\])\s*\n?```", content)
        if code_block_match:
            try:
                parsed = json.loads(code_block_match.group(1))
                if isinstance(parsed, list) and len(parsed) > 0 and "name" in parsed[0]:
                    return parsed
            except json.JSONDecodeError:
                pass

        # Try to find a raw JSON array
        array_match = re.search(r"\[\s*\{[\s\S]*?\}\s*\]", content)
        if array_match:
            try:
                parsed = json.loads(array_match.group(0))
                if isinstance(parsed, list) and len(parsed) > 0 and "name" in parsed[0]:
                    return parsed
            except json.JSONDecodeError:
                pass

        # Try to find a single JSON object with "name" key
        obj_match = re.search(r"\{[^{}]*\"name\"[^{}]*\}", content)
        if obj_match:
            try:
                parsed = json.loads(obj_match.group(0))
                if "name" in parsed:
                    return [parsed]
            except json.JSONDecodeError:
                pass

        return []


def get_llm_provider() -> BaseLLMProvider:
    """Factory function to get the configured LLM provider."""
    raise NotImplementedError("Global LLM provider is disabled. Use user-specific provider.")
