"""
Tests for the Cost Agent (static pricing).
"""

import pytest
from app.schemas.architecture import ArchitectureEdge, ArchitectureGraph, ArchitectureNode
from app.services.ai.cost_agent import CostAgent


class TestCostAgentStatic:
    """Test cost estimation using static pricing heuristics."""

    @pytest.fixture
    def simple_graph(self) -> ArchitectureGraph:
        return ArchitectureGraph(
            nodes=[
                ArchitectureNode(id="api", type="aws_apigatewayv2", label="API Gateway"),
                ArchitectureNode(id="fn", type="aws_lambda", label="Lambda"),
                ArchitectureNode(id="db", type="aws_dynamodb", label="DynamoDB"),
            ],
            edges=[
                ArchitectureEdge(**{"from": "api", "to": "fn"}),
                ArchitectureEdge(**{"from": "fn", "to": "db"}),
            ],
        )

    @pytest.mark.asyncio
    async def test_basic_cost_estimation(self, simple_graph):
        agent = CostAgent()
        cost = await agent.run(simple_graph, scale="medium", use_llm=False)

        assert cost.estimated_monthly_cost > 0
        assert cost.currency == "USD"
        assert len(cost.breakdown) == 3  # 3 non-zero-cost services

    @pytest.mark.asyncio
    async def test_scale_affects_cost(self, simple_graph):
        agent = CostAgent()
        small_cost = await agent.run(simple_graph, scale="small", use_llm=False)
        large_cost = await agent.run(simple_graph, scale="large", use_llm=False)

        assert large_cost.estimated_monthly_cost > small_cost.estimated_monthly_cost

    @pytest.mark.asyncio
    async def test_empty_graph_zero_cost(self):
        agent = CostAgent()
        graph = ArchitectureGraph(nodes=[], edges=[])
        cost = await agent.run(graph, scale="medium", use_llm=False)

        assert cost.estimated_monthly_cost == 0
        assert cost.breakdown == []

    @pytest.mark.asyncio
    async def test_iam_role_zero_cost(self):
        agent = CostAgent()
        graph = ArchitectureGraph(
            nodes=[ArchitectureNode(id="role", type="aws_iam_role", label="Role")],
            edges=[],
        )
        cost = await agent.run(graph, scale="medium", use_llm=False)

        assert cost.estimated_monthly_cost == 0
        assert cost.breakdown == []

    @pytest.mark.asyncio
    async def test_large_architecture_cost(self):
        agent = CostAgent()
        graph = ArchitectureGraph(
            nodes=[
                ArchitectureNode(id="cf", type="aws_cloudfront", label="CDN"),
                ArchitectureNode(id="api", type="aws_apigatewayv2", label="API"),
                ArchitectureNode(id="ecs", type="aws_ecs", label="ECS"),
                ArchitectureNode(id="rds", type="aws_rds", label="RDS"),
                ArchitectureNode(id="cache", type="aws_elasticache", label="Redis"),
                ArchitectureNode(id="s3", type="aws_s3", label="S3"),
                ArchitectureNode(id="vpc", type="aws_vpc", label="VPC"),
            ],
            edges=[],
        )
        cost = await agent.run(graph, scale="enterprise", use_llm=False)

        assert cost.estimated_monthly_cost > 500
        assert len(cost.breakdown) >= 6
