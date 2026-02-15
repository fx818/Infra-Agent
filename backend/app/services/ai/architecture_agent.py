"""
Architecture Agent — designs AWS infrastructure from structured intent.
"""

import json
import logging

from app.schemas.architecture import ArchitectureGraph, IntentOutput
from app.services.ai.base import BaseLLMProvider, get_llm_provider
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class ArchitectureAgent:
    """
    Takes structured intent and generates a complete AWS architecture
    graph with nodes (services) and edges (connections).
    """

    def __init__(self, llm: BaseLLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()
        self.system_prompt = load_prompt("architecture_agent_prompt.md")

    async def run(self, intent: IntentOutput) -> ArchitectureGraph:
        """
        Generate an architecture graph from structured intent.

        Args:
            intent: Structured intent describing the desired application.

        Returns:
            ArchitectureGraph with AWS service nodes and dependency edges.
        """
        logger.info("ArchitectureAgent: designing for app_type=%s, scale=%s", intent.app_type, intent.scale)

        user_prompt = (
            f"Design an AWS architecture for the following requirements:\n\n"
            f"{json.dumps(intent.model_dump(), indent=2)}"
        )

        result = await self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        graph = ArchitectureGraph(**result)
        logger.info(
            "ArchitectureAgent: generated %d nodes, %d edges",
            len(graph.nodes), len(graph.edges),
        )
        return graph
