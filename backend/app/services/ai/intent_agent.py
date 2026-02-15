"""
Intent Agent — extracts structured intent from natural language requirements.
"""

import logging

from app.schemas.architecture import IntentOutput
from app.services.ai.base import BaseLLMProvider, get_llm_provider
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class IntentAgent:
    """
    Analyzes a natural language requirement and extracts a structured intent
    describing the application type, scale, latency, storage, and constraints.
    """

    def __init__(self, llm: BaseLLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()
        self.system_prompt = load_prompt("intent_agent_prompt.md")

    async def run(self, natural_language_input: str) -> IntentOutput:
        """
        Process natural language input and return structured intent.

        Args:
            natural_language_input: The user's project requirement in plain English.

        Returns:
            IntentOutput with app_type, scale, latency, storage, realtime, constraints.
        """
        logger.info("IntentAgent: processing input (%d chars)", len(natural_language_input))

        result = await self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=natural_language_input,
            temperature=0.1,
        )

        intent = IntentOutput(**result)
        logger.info(
            "IntentAgent: app_type=%s, scale=%s, realtime=%s",
            intent.app_type, intent.scale, intent.realtime,
        )
        return intent
