"""
Terraform Generator Agent — converts architecture graphs to Terraform IaC.
"""

import json
import logging

from app.schemas.architecture import ArchitectureGraph, TerraformFileMap
from app.services.ai.base import BaseLLMProvider, get_llm_provider
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class TerraformAgent:
    """
    Takes an architecture graph and generates production-ready
    Terraform configuration files.
    """

    def __init__(self, llm: BaseLLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()
        self.system_prompt = load_prompt("terraform_agent_prompt.md")

    async def run(
        self,
        graph: ArchitectureGraph,
        region: str = "us-east-1",
        project_name: str = "nl2i-project",
    ) -> TerraformFileMap:
        """
        Generate Terraform files from an architecture graph.

        Args:
            graph: The architecture graph to convert.
            region: AWS region for the deployment.
            project_name: Project name used for resource naming.

        Returns:
            TerraformFileMap with filename → content mapping.
        """
        logger.info(
            "TerraformAgent: generating for %d nodes, region=%s",
            len(graph.nodes), region,
        )

        # Sanitize project name for AWS resource naming
        safe_project_name = project_name.lower().replace(" ", "-").replace("_", "-")
        safe_project_name = "".join(c for c in safe_project_name if c.isalnum() or c == "-")

        graph_dict = graph.model_dump(by_alias=True)

        user_prompt = (
            f"## Architecture Graph\n\n"
            f"```json\n{json.dumps(graph_dict, indent=2)}\n```\n\n"
            f"## Configuration\n\n"
            f"- AWS Region: {region}\n"
            f"- Project Name: {safe_project_name}\n\n"
            f"Generate the complete Terraform configuration files."
        )

        result = await self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        terraform_files = TerraformFileMap(**result)
        logger.info(
            "TerraformAgent: generated %d files: %s",
            len(terraform_files.files),
            list(terraform_files.files.keys()),
        )
        return terraform_files
