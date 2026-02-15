"""
Tests for Pydantic schemas.
"""

import pytest
from app.schemas.architecture import (
    ArchitectureEdge,
    ArchitectureGraph,
    ArchitectureNode,
    CostBreakdown,
    CostEstimate,
    IntentOutput,
    NodeConfig,
    TerraformFileMap,
    VisualEdge,
    VisualGraph,
    VisualNode,
)
from app.schemas.user import AWSCredentials, UserCreate, UserPreferences
from app.schemas.project import ProjectCreate, ProjectGenerateRequest


class TestIntentOutput:
    def test_create_intent(self):
        intent = IntentOutput(
            app_type="web_api",
            scale="medium",
            latency_requirement="low",
            storage_type="relational",
            realtime=False,
            constraints=["serverless"],
        )
        assert intent.app_type == "web_api"
        assert intent.scale == "medium"
        assert intent.realtime is False

    def test_intent_defaults(self):
        intent = IntentOutput(app_type="web_api", scale="small")
        assert intent.latency_requirement == "moderate"
        assert intent.realtime is False
        assert intent.constraints == []


class TestArchitectureGraph:
    def test_create_graph(self):
        graph = ArchitectureGraph(
            nodes=[
                ArchitectureNode(id="api_gw", type="aws_apigatewayv2", label="API Gateway"),
                ArchitectureNode(id="lambda_fn", type="aws_lambda", label="Lambda"),
            ],
            edges=[
                ArchitectureEdge(**{"from": "api_gw", "to": "lambda_fn", "label": "invokes"}),
            ],
        )
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.edges[0].source == "api_gw"

    def test_empty_graph(self):
        graph = ArchitectureGraph()
        assert graph.nodes == []
        assert graph.edges == []

    def test_graph_serialization(self):
        graph = ArchitectureGraph(
            nodes=[ArchitectureNode(id="s3", type="aws_s3", label="Bucket")],
            edges=[],
        )
        data = graph.model_dump(by_alias=True)
        assert data["nodes"][0]["id"] == "s3"


class TestCostEstimate:
    def test_cost_estimate(self):
        cost = CostEstimate(
            estimated_monthly_cost=125.50,
            breakdown=[
                CostBreakdown(service="Lambda", estimated_monthly_cost=5.00, details="1M requests"),
                CostBreakdown(service="DynamoDB", estimated_monthly_cost=25.00),
            ],
        )
        assert cost.estimated_monthly_cost == 125.50
        assert len(cost.breakdown) == 2
        assert cost.currency == "USD"


class TestTerraformFileMap:
    def test_file_map(self):
        tfmap = TerraformFileMap(files={"main.tf": "resource...", "variables.tf": "variable..."})
        assert len(tfmap.files) == 2
        assert "main.tf" in tfmap.files


class TestUserSchemas:
    def test_user_create(self):
        user = UserCreate(email="test@example.com", password="securepass123")
        assert user.email == "test@example.com"

    def test_aws_credentials(self):
        creds = AWSCredentials(
            aws_access_key_id="AKIAIOSFODNN7EXAMPLE",
            aws_secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        )
        assert creds.assume_role_arn is None

    def test_user_preferences(self):
        prefs = UserPreferences(default_region="eu-west-1", default_vpc=False)
        assert prefs.naming_convention == "kebab-case"


class TestProjectSchemas:
    def test_project_create(self):
        proj = ProjectCreate(name="My Project", description="Test", region="us-west-2")
        assert proj.region == "us-west-2"

    def test_generate_request(self):
        req = ProjectGenerateRequest(natural_language_input="Build a REST API with DynamoDB")
        assert len(req.natural_language_input) >= 10
