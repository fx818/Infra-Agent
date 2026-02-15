"""
Cost Estimator Agent — estimates monthly AWS costs from architecture graphs.

Uses a hybrid approach: static pricing heuristics for well-known services,
with LLM fallback for complex estimation.
"""

import json
import logging

from app.schemas.architecture import (
    ArchitectureGraph,
    CostBreakdown,
    CostEstimate,
)
from app.services.ai.base import BaseLLMProvider, get_llm_provider
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)

# ── Static pricing table (US East, on-demand, monthly estimates) ────────────
# These are rough heuristics for MVP cost estimation.
_STATIC_PRICING: dict[str, dict[str, float]] = {
    "aws_lambda": {
        "small": 1.50,
        "medium": 5.00,
        "large": 25.00,
        "enterprise": 100.00,
    },
    "aws_apigatewayv2": {
        "small": 1.00,
        "medium": 3.50,
        "large": 10.00,
        "enterprise": 35.00,
    },
    "aws_dynamodb": {
        "small": 5.00,
        "medium": 25.00,
        "large": 100.00,
        "enterprise": 500.00,
    },
    "aws_sqs": {
        "small": 0.40,
        "medium": 2.00,
        "large": 8.00,
        "enterprise": 40.00,
    },
    "aws_ecs": {
        "small": 30.00,
        "medium": 75.00,
        "large": 200.00,
        "enterprise": 800.00,
    },
    "aws_rds": {
        "small": 15.00,
        "medium": 50.00,
        "large": 200.00,
        "enterprise": 800.00,
    },
    "aws_elasticache": {
        "small": 12.50,
        "medium": 50.00,
        "large": 150.00,
        "enterprise": 500.00,
    },
    "aws_s3": {
        "small": 1.00,
        "medium": 5.00,
        "large": 25.00,
        "enterprise": 100.00,
    },
    "aws_vpc": {
        "small": 35.00,
        "medium": 35.00,
        "large": 70.00,
        "enterprise": 140.00,
    },
    "aws_cloudfront": {
        "small": 1.00,
        "medium": 10.00,
        "large": 85.00,
        "enterprise": 500.00,
    },
    "aws_sns": {
        "small": 0.50,
        "medium": 2.50,
        "large": 10.00,
        "enterprise": 50.00,
    },
    "aws_route53": {
        "small": 1.00,
        "medium": 1.50,
        "large": 2.50,
        "enterprise": 5.00,
    },
    # Free-tier / negligible cost services
    "aws_iam_role": {"small": 0, "medium": 0, "large": 0, "enterprise": 0},
    "aws_security_group": {"small": 0, "medium": 0, "large": 0, "enterprise": 0},
}


class CostAgent:
    """
    Estimates monthly AWS costs for an architecture graph.

    Primary approach: static pricing heuristics.
    Fallback: LLM-based estimation for more detailed breakdowns.
    """

    def __init__(self, llm: BaseLLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()
        self.system_prompt = load_prompt("cost_agent_prompt.md")

    async def run(
        self,
        graph: ArchitectureGraph,
        scale: str = "medium",
        use_llm: bool = False,
    ) -> CostEstimate:
        """
        Estimate costs for the given architecture.

        Args:
            graph: The architecture graph.
            scale: Expected scale (small, medium, large, enterprise).
            use_llm: If True, use LLM for detailed estimation.

        Returns:
            CostEstimate with total and per-service breakdown.
        """
        if use_llm:
            return await self._estimate_with_llm(graph, scale)
        return self._estimate_static(graph, scale)

    def _estimate_static(self, graph: ArchitectureGraph, scale: str) -> CostEstimate:
        """Estimate using static pricing heuristics."""
        logger.info("CostAgent: static estimation for %d nodes, scale=%s", len(graph.nodes), scale)

        breakdown: list[CostBreakdown] = []
        total = 0.0

        for node in graph.nodes:
            pricing = _STATIC_PRICING.get(node.type, {})
            cost = pricing.get(scale, pricing.get("medium", 0))
            total += cost
            if cost > 0:
                breakdown.append(CostBreakdown(
                    service=f"{node.type} ({node.id})",
                    estimated_monthly_cost=round(cost, 2),
                    details=f"Scale: {scale}, label: {node.label}",
                ))

        return CostEstimate(
            estimated_monthly_cost=round(total, 2),
            currency="USD",
            breakdown=breakdown,
        )

    async def _estimate_with_llm(self, graph: ArchitectureGraph, scale: str) -> CostEstimate:
        """Estimate using the LLM for more detailed analysis."""
        logger.info("CostAgent: LLM estimation for %d nodes, scale=%s", len(graph.nodes), scale)

        graph_dict = graph.model_dump(by_alias=True)
        user_prompt = (
            f"## Architecture\n\n```json\n{json.dumps(graph_dict, indent=2)}\n```\n\n"
            f"## Scale: {scale}\n\n"
            f"Estimate the monthly cost for this architecture."
        )

        result = await self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        return CostEstimate(**result)
