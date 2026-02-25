"""
Tool Agent — orchestrates LLM tool-calling to build AWS architectures.

Replaces the previous pipeline of IntentAgent → ArchitectureAgent → TerraformAgent
with a single agent that uses tool calling. The LLM decides which AWS services
to provision by calling tools, and this agent assembles the results into
an ArchitectureGraph + TerraformFileMap.
"""

import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.architecture import (
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
    TerraformFileMap,
)
from app.services.ai.base import BaseLLMProvider
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "tool_agent_prompt.md"


class ToolAgent:
    """
    Orchestrator agent that uses LLM tool-calling to design AWS architectures.

    Instead of generating architecture JSON and Terraform code directly,
    this agent provides the LLM with callable AWS service tools. The LLM
    calls tools like `create_ec2_instance`, `create_s3_bucket`, etc. to
    build the architecture, and this agent assembles the results.
    """

    def __init__(self, llm: BaseLLMProvider) -> None:
        self.llm = llm
        self.registry = ToolRegistry()
        self.system_prompt = _PROMPT_PATH.read_text(encoding="utf-8")

        # Accumulated state during one run
        self._nodes: list[dict[str, Any]] = []
        self._edges: list[dict[str, Any]] = []
        self._terraform_files: dict[str, str] = {}

    async def run(
        self,
        user_prompt: str,
        region: str = "us-east-1",
        project_name: str = "nl2i-project",
    ) -> dict[str, Any]:
        """
        Run the tool-calling loop to build an architecture.

        Args:
            user_prompt: Natural language description of the desired infrastructure.
            region: AWS region for deployment.
            project_name: Project name for resource naming.

        Returns:
            Dict with "graph" (ArchitectureGraph), "terraform" (TerraformFileMap),
            and "summary" (LLM's explanation of the architecture).
        """
        logger.info("ToolAgent: starting for project=%s, region=%s", project_name, region)

        # Reset state
        self._nodes = []
        self._edges = []
        self._terraform_files = {}

        # Sanitize project name
        safe_name = project_name.lower().replace(" ", "-").replace("_", "-")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")

        # Build the full user prompt with context
        full_prompt = (
            f"## User Request\n\n{user_prompt}\n\n"
            f"## Configuration\n\n"
            f"- AWS Region: {region}\n"
            f"- Project Name: {safe_name}\n\n"
            f"Design and provision the complete AWS architecture by calling the appropriate tools. "
            f"After creating all services, use `connect_services` to define how they interact. "
            f"When done, provide a summary of the architecture you built."
        )

        # Get relevant tool definitions (filtered by user prompt to reduce tokens)
        openai_tools = self.registry.get_relevant_openai_tools(user_prompt)
        logger.info("ToolAgent: selected %d relevant tools for LLM", len(openai_tools))

        # Run the tool-calling loop
        result = await self.llm.generate_with_tools(
            system_prompt=self.system_prompt,
            user_prompt=full_prompt,
            tools=openai_tools,
            tool_executor=self._execute_tool,
            temperature=0.2,
        )

        # Add provider/region terraform boilerplate
        self._terraform_files["providers.tf"] = self._generate_provider_tf(region, safe_name)

        # Build the final graph
        graph = self._build_graph()
        terraform = TerraformFileMap(files=self._terraform_files)

        logger.info(
            "ToolAgent: complete — %d nodes, %d edges, %d terraform files",
            len(graph.nodes), len(graph.edges), len(terraform.files),
        )

        return {
            "graph": graph,
            "terraform": terraform,
            "summary": result.get("message", ""),
            "tool_calls_count": len(result.get("tool_calls", [])),
        }

    async def _execute_tool(self, name: str, args: dict[str, Any]) -> str:
        """Execute a tool by name and return the result as a JSON string."""
        tool = self.registry.get_tool_by_name(name)
        if not tool:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            result = tool.execute(args)

            # Don't add edge-only results as nodes
            if not result.metadata.get("is_edge_only"):
                self._nodes.append(result.node.model_dump(by_alias=True))

            # Collect edges
            for edge in result.edges:
                self._edges.append(edge)

            # Merge terraform code
            for filename, code in result.terraform_code.items():
                if filename in self._terraform_files:
                    self._terraform_files[filename] += "\n" + code
                else:
                    self._terraform_files[filename] = code

            return json.dumps({
                "status": "success",
                "node_id": result.node.id,
                "node_type": result.node.type,
                "message": f"Successfully created {result.node.label} ({result.node.type})",
            })

        except Exception as e:
            logger.error("Tool execution error: %s — %s", name, e)
            return json.dumps({"status": "error", "message": str(e)})

    def _build_graph(self) -> ArchitectureGraph:
        """Assemble the accumulated nodes and edges into an ArchitectureGraph."""
        nodes = []
        for n in self._nodes:
            try:
                nodes.append(ArchitectureNode(
                    id=n["id"],
                    type=n["type"],
                    label=n["label"],
                    config=n.get("config", {}),
                ))
            except Exception as e:
                logger.warning("Failed to create node from %s: %s", n, e)

        edges = []
        for e in self._edges:
            try:
                edges.append(ArchitectureEdge(
                    **{"from": e.get("from", ""), "to": e.get("to", ""), "label": e.get("label", "")}
                ))
            except Exception as ex:
                logger.warning("Failed to create edge from %s: %s", e, ex)

        return ArchitectureGraph(nodes=nodes, edges=edges)

    @staticmethod
    def _generate_provider_tf(region: str, project_name: str) -> str:
        """Generate the Terraform provider and variable definitions."""
        return f'''terraform {{
  required_version = ">= 1.0"
  required_providers {{
    aws = {{
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }}
  }}
}}

provider "aws" {{
  region = var.region
}}

variable "region" {{
  type    = string
  default = "{region}"
}}

variable "project_name" {{
  type    = string
  default = "{project_name}"
}}
'''
