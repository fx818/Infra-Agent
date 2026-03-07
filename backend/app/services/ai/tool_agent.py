"""
Tool Agent — orchestrates LLM tool-calling to build AWS architectures.

Replaces the previous pipeline of IntentAgent → ArchitectureAgent → TerraformAgent
with a single agent that uses tool calling. The LLM decides which AWS services
to provision by calling tools, and this agent assembles the results into
an ArchitectureGraph + boto3 deployment configs.
"""

import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.architecture import (
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
)
from app.services.ai.base import BaseLLMProvider
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent.parent / "prompts" / "tool_agent_prompt.md"

# ── Auto-edge inference rules ─────────────────────────────────────────────────
# Defines which service types naturally connect to which, with a default label.
# Used when the LLM doesn't call connect_services at all (0 edges produced).
_AUTO_EDGE_RULES: list[tuple[str, str, str]] = [
    # Entry points → Compute
    ("aws_route53",       "aws_cloudfront",    "routes to"),
    ("aws_route53",       "aws_elb",           "routes to"),
    ("aws_route53",       "aws_api_gateway",   "routes to"),
    ("aws_route53",       "aws_apigatewayv2",  "routes to"),
    ("aws_route53",       "aws_ec2",           "routes to"),
    ("aws_cloudfront",    "aws_s3",            "serves from"),
    ("aws_cloudfront",    "aws_elb",           "forwards to"),
    ("aws_cloudfront",    "aws_api_gateway",   "forwards to"),
    ("aws_cloudfront",    "aws_apigatewayv2",  "forwards to"),
    ("aws_elb",           "aws_ec2",           "routes to"),
    ("aws_elb",           "aws_ecs",           "routes to"),
    ("aws_elb",           "aws_eks",           "routes to"),
    ("aws_api_gateway",   "aws_lambda",        "invokes"),
    ("aws_api_gateway",   "aws_ecs",           "routes to"),
    ("aws_api_gateway",   "aws_ec2",           "routes to"),
    ("aws_apigatewayv2",  "aws_lambda",        "invokes"),
    ("aws_apigatewayv2",  "aws_ecs",           "routes to"),
    # Compute → Storage
    ("aws_ec2",           "aws_s3",            "reads/writes"),
    ("aws_ec2",           "aws_ebs",           "mounts"),
    ("aws_ec2",           "aws_efs",           "mounts"),
    ("aws_lambda",        "aws_s3",            "reads/writes"),
    ("aws_ecs",           "aws_s3",            "reads/writes"),
    ("aws_ecs",           "aws_efs",           "mounts"),
    ("aws_eks",           "aws_s3",            "reads/writes"),
    # Compute → Database
    ("aws_ec2",           "aws_rds",           "reads/writes"),
    ("aws_ec2",           "aws_aurora",        "reads/writes"),
    ("aws_ec2",           "aws_dynamodb",      "reads/writes"),
    ("aws_ec2",           "aws_elasticache",   "caches via"),
    ("aws_lambda",        "aws_dynamodb",      "reads/writes"),
    ("aws_lambda",        "aws_rds",           "reads/writes"),
    ("aws_lambda",        "aws_aurora",        "reads/writes"),
    ("aws_lambda",        "aws_elasticache",   "caches via"),
    ("aws_ecs",           "aws_rds",           "reads/writes"),
    ("aws_ecs",           "aws_aurora",        "reads/writes"),
    ("aws_ecs",           "aws_dynamodb",      "reads/writes"),
    ("aws_ecs",           "aws_elasticache",   "caches via"),
    ("aws_eks",           "aws_rds",           "reads/writes"),
    ("aws_eks",           "aws_dynamodb",      "reads/writes"),
    # Messaging
    ("aws_lambda",        "aws_sqs",           "publishes to"),
    ("aws_lambda",        "aws_sns",           "publishes to"),
    ("aws_lambda",        "aws_kinesis",       "publishes to"),
    ("aws_ec2",           "aws_sqs",           "publishes to"),
    ("aws_ec2",           "aws_sns",           "publishes to"),
    ("aws_ecs",           "aws_sqs",           "publishes to"),
    ("aws_ecs",           "aws_sns",           "publishes to"),
    ("aws_sqs",           "aws_lambda",        "triggers"),
    ("aws_sns",           "aws_lambda",        "triggers"),
    ("aws_sns",           "aws_sqs",           "fans out to"),
    ("aws_eventbridge",   "aws_lambda",        "triggers"),
    ("aws_eventbridge",   "aws_sqs",           "delivers to"),
    ("aws_eventbridge",   "aws_sns",           "delivers to"),
    ("aws_kinesis",       "aws_lambda",        "triggers"),
    ("aws_msk",           "aws_lambda",        "triggers"),
    # Security
    ("aws_cognito",       "aws_api_gateway",   "authenticates"),
    ("aws_cognito",       "aws_apigatewayv2",  "authenticates"),
    ("aws_waf",           "aws_cloudfront",    "protects"),
    ("aws_waf",           "aws_api_gateway",   "protects"),
    ("aws_secrets_manager", "aws_lambda",      "provides secrets"),
    ("aws_secrets_manager", "aws_ecs",         "provides secrets"),
    ("aws_secrets_manager", "aws_ec2",         "provides secrets"),
    ("aws_acm",           "aws_cloudfront",    "provides TLS"),
    ("aws_acm",           "aws_elb",           "provides TLS"),
    # DevOps
    ("aws_ecr",           "aws_ecs",           "provides images"),
    ("aws_ecr",           "aws_eks",           "provides images"),
    ("aws_codepipeline",  "aws_codebuild",     "triggers"),
    ("aws_codebuild",     "aws_ecr",           "pushes to"),
    ("aws_codepipeline",  "aws_ecs",           "deploys to"),
    ("aws_codepipeline",  "aws_lambda",        "deploys to"),
    # Analytics
    ("aws_kinesis",       "aws_s3",            "stores to"),
    ("aws_kinesis",       "aws_redshift",      "loads to"),
    ("aws_glue",          "aws_s3",            "reads/writes"),
    ("aws_glue",          "aws_redshift",      "loads to"),
    ("aws_athena",        "aws_s3",            "queries"),
    ("aws_msk",           "aws_s3",            "stores to"),
    # Monitoring
    ("aws_cloudwatch",    "aws_sns",           "alerts via"),
    ("aws_cloudwatch",    "aws_lambda",        "triggers"),
]

# Build a lookup: node_type → list of (target_type, label)
_SOURCE_MAP: dict[str, list[tuple[str, str]]] = {}
for _src, _tgt, _lbl in _AUTO_EDGE_RULES:
    _SOURCE_MAP.setdefault(_src, []).append((_tgt, _lbl))


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
        self._boto3_configs: dict[str, list[dict[str, Any]]] = {}

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
            Dict with "graph" (ArchitectureGraph), "boto3_configs" (dict of service → ops),
            and "summary" (LLM's explanation of the architecture).
        """
        logger.info("ToolAgent: starting for project=%s, region=%s", project_name, region)

        # Reset state
        self._nodes = []
        self._edges = []
        self._boto3_configs = {}

        # Sanitize project name
        safe_name = project_name.lower().replace(" ", "-").replace("_", "-")
        safe_name = "".join(c for c in safe_name if c.isalnum() or c == "-")

        # Build the full user prompt with context
        full_prompt = (
            f"## Architecture Specification\n\n{user_prompt}\n\n"
            f"## Configuration\n\n"
            f"- AWS Region: {region}\n"
            f"- Project Name: {safe_name}\n\n"
            f"**Your task**: Call a tool for EVERY service described in the Architecture Specification above. "
            f"Do NOT stop until every service has been provisioned via a tool call. "
            f"Then call `connect_services` for every pair of services that communicate. "
            f"Only provide a text summary AFTER all services and connections have been created."
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

        # Build the final graph
        graph = self._build_graph()

        logger.info(
            "ToolAgent: complete — %d nodes, %d edges, %d boto3 service groups",
            len(graph.nodes), len(graph.edges), len(self._boto3_configs),
        )

        return {
            "graph": graph,
            "boto3_configs": self._boto3_configs,
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

            # Merge boto3 configs — tag each op with the originating tool node ID
            # so the executor can build a cross-reference map.
            for service, ops in result.boto3_config.items():
                if service not in self._boto3_configs:
                    self._boto3_configs[service] = []
                for op in (ops if isinstance(ops, list) else [ops]):
                    op["_tool_node_id"] = result.node.id
                self._boto3_configs[service].extend(ops if isinstance(ops, list) else [ops])

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

        # Auto-infer edges when LLM skipped connect_services entirely.
        # Also supplement sparse edge lists so every obvious connection is shown.
        inferred = self._infer_edges(nodes)
        all_raw_edges = list(self._edges)  # LLM-produced edges come first
        existing_pairs: set[tuple[str, str]] = {
            (e.get("from", ""), e.get("to", "")) for e in all_raw_edges
        }
        for ie in inferred:
            pair = (ie["from"], ie["to"])
            if pair not in existing_pairs:
                all_raw_edges.append(ie)
                existing_pairs.add(pair)

        if not self._edges and inferred:
            logger.info("No LLM edges produced — used %d auto-inferred edges", len(inferred))

        edges = []
        for e in all_raw_edges:
            try:
                edges.append(ArchitectureEdge(
                    **{"from": e.get("from", ""), "to": e.get("to", ""), "label": e.get("label", "")}
                ))
            except Exception as ex:
                logger.warning("Failed to create edge from %s: %s", e, ex)

        return ArchitectureGraph(nodes=nodes, edges=edges)

    def _infer_edges(self, nodes: list[ArchitectureNode]) -> list[dict[str, Any]]:
        """
        Auto-generate edges based on known AWS service relationships.

        Iterates over all node pairs and applies _SOURCE_MAP rules to produce
        sensible default connections when the LLM didn't call connect_services.
        """
        # Build a quick lookup: node_type → list of node_ids that have that type
        type_to_ids: dict[str, list[str]] = {}
        for node in nodes:
            type_to_ids.setdefault(node.type, []).append(node.id)

        inferred: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()

        for src_type, targets in _SOURCE_MAP.items():
            src_ids = type_to_ids.get(src_type, [])
            if not src_ids:
                continue
            for tgt_type, label in targets:
                tgt_ids = type_to_ids.get(tgt_type, [])
                if not tgt_ids:
                    continue
                # Connect each source to the most relevant target (first one)
                # to avoid fan-out explosion with many same-type nodes.
                for src_id in src_ids:
                    tgt_id = tgt_ids[0]
                    pair = (src_id, tgt_id)
                    if pair not in seen:
                        inferred.append({"from": src_id, "to": tgt_id, "label": label})
                        seen.add(pair)

        return inferred


