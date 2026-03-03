"""
Prompt Enrichment Agent — rewrites a user's vague infrastructure request into a
detailed, AWS-service-explicit technical specification before passing it to the
ToolAgent.

This is the first step in the generation pipeline. Its output:
  - enriched_prompt : str   — detailed description with explicit service names
  - services        : list  — short list of AWS services mentioned  
  - architecture_pattern : str — detected pattern (e.g. "3-tier web application")
  - complexity      : str   — simple / medium / complex
"""

import json
import logging
from pathlib import Path
from typing import Any

from app.services.ai.base import BaseLLMProvider

logger = logging.getLogger(__name__)

_PROMPT_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / "prompts"
    / "prompt_enrichment_agent_prompt.md"
)

# Fallback if LLM fails — return the original prompt unchanged
_EMPTY_RESULT: dict[str, Any] = {
    "enriched_prompt": "",
    "services": [],
    "architecture_pattern": "unknown",
    "complexity": "medium",
}


class PromptEnrichmentAgent:
    """
    Pre-processing agent that converts a short/vague user prompt into a
    detailed, service-explicit AWS architecture description.

    Runs before the ToolAgent so that:
      1. The ToolRegistry keyword matcher selects the right tool categories.
      2. The ToolAgent LLM receives a precise brief with explicit service names,
         instance types, and data-flow descriptions rather than a vague sentence.
    """

    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm = llm
        self.system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")

    async def run(
        self,
        user_prompt: str,
        region: str = "us-east-1",
    ) -> dict[str, Any]:
        """
        Enrich the user's prompt.

        Args:
            user_prompt: Raw natural-language description from the user.
            region:      Target AWS region (included for context).

        Returns:
            Dict with keys:
              - enriched_prompt (str)
              - services (list[str])
              - architecture_pattern (str)
              - complexity (str)
              - original_prompt (str)   — the unchanged input, always preserved
        """
        logger.info(
            "PromptEnrichmentAgent: enriching prompt (%d chars)", len(user_prompt)
        )

        context = (
            f"Target AWS Region: {region}\n\n"
            f"User Request: {user_prompt}"
        )

        try:
            result = await self.llm.generate(
                system_prompt=self.system_prompt,
                user_prompt=context,
                temperature=0.3,
            )
        except Exception as exc:
            logger.warning(
                "PromptEnrichmentAgent: LLM call failed (%s) — using original prompt",
                exc,
            )
            return {**_EMPTY_RESULT, "enriched_prompt": user_prompt, "original_prompt": user_prompt}

        enriched = result.get("enriched_prompt", "").strip()
        services = result.get("services", [])
        pattern = result.get("architecture_pattern", "unknown")
        complexity = result.get("complexity", "medium")

        # Validate — if the LLM returned garbage, fall back to original
        if not enriched or len(enriched) < len(user_prompt):
            logger.warning(
                "PromptEnrichmentAgent: enriched prompt is shorter than original — using original"
            )
            enriched = user_prompt

        logger.info(
            "PromptEnrichmentAgent: done — pattern=%s, complexity=%s, services=%s",
            pattern,
            complexity,
            ", ".join(services[:10]),
        )

        return {
            "enriched_prompt": enriched,
            "services": services,
            "architecture_pattern": pattern,
            "complexity": complexity,
            "original_prompt": user_prompt,
        }
