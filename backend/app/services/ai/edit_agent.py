"""
Edit Agent — modifies existing architecture graphs based on user prompts.
"""

import json
import logging

from app.schemas.architecture import ArchitectureGraph
from app.services.ai.base import BaseLLMProvider, get_llm_provider
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class EditAgent:
    """
    Takes an existing architecture graph and a modification prompt,
    then produces a modified graph preserving structure and dependencies.
    """

    def __init__(self, llm: BaseLLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()
        self.system_prompt = load_prompt("edit_agent_prompt.md")

    async def run(
        self,
        current_graph: ArchitectureGraph,
        modification_prompt: str,
    ) -> ArchitectureGraph:
        """
        Modify an existing architecture graph.

        Args:
            current_graph: The current architecture graph.
            modification_prompt: User's description of the desired modification.

        Returns:
            Modified ArchitectureGraph.
        """
        logger.info("EditAgent: processing modification (%d chars)", len(modification_prompt))

        # Serialize the current graph for the LLM
        graph_dict = current_graph.model_dump(by_alias=True)

        user_prompt = (
            f"## Current Architecture\n\n"
            f"```json\n{json.dumps(graph_dict, indent=2)}\n```\n\n"
            f"## Modification Request\n\n"
            f"{modification_prompt}"
        )

        result = await self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
        )

        modified_graph = ArchitectureGraph(**result)
        logger.info(
            "EditAgent: modified graph has %d nodes, %d edges",
            len(modified_graph.nodes), len(modified_graph.edges),
        )
        return modified_graph
