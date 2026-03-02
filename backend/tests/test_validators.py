"""
Tests for validators.
"""

import pytest
from app.schemas.architecture import ArchitectureEdge, ArchitectureGraph, ArchitectureNode
from app.utils.validators import (
    ALLOWED_AWS_SERVICES,
    sanitize_boto3_config,
    validate_architecture_graph,
)


class TestArchitectureGraphValidation:
    def test_valid_graph(self):
        graph = ArchitectureGraph(
            nodes=[
                ArchitectureNode(id="api", type="aws_apigatewayv2", label="API"),
                ArchitectureNode(id="fn", type="aws_lambda", label="Lambda"),
            ],
            edges=[
                ArchitectureEdge(**{"from": "api", "to": "fn"}),
            ],
        )
        errors = validate_architecture_graph(graph)
        assert errors == []

    def test_invalid_service_type(self):
        graph = ArchitectureGraph(
            nodes=[ArchitectureNode(id="x", type="aws_invalid_service", label="Bad")],
            edges=[],
        )
        errors = validate_architecture_graph(graph)
        assert len(errors) == 1
        assert "disallowed" in errors[0]

    def test_duplicate_node_ids(self):
        graph = ArchitectureGraph(
            nodes=[
                ArchitectureNode(id="dup", type="aws_lambda", label="A"),
                ArchitectureNode(id="dup", type="aws_s3", label="B"),
            ],
            edges=[],
        )
        errors = validate_architecture_graph(graph)
        assert any("Duplicate" in e for e in errors)

    def test_edge_references_nonexistent_node(self):
        graph = ArchitectureGraph(
            nodes=[ArchitectureNode(id="a", type="aws_lambda", label="A")],
            edges=[ArchitectureEdge(**{"from": "a", "to": "nonexistent"})],
        )
        errors = validate_architecture_graph(graph)
        assert any("non-existent" in e for e in errors)

    def test_self_loop(self):
        graph = ArchitectureGraph(
            nodes=[ArchitectureNode(id="a", type="aws_lambda", label="A")],
            edges=[ArchitectureEdge(**{"from": "a", "to": "a"})],
        )
        errors = validate_architecture_graph(graph)
        assert any("Self-loop" in e for e in errors)


class TestBoto3ConfigSanitization:
    def test_safe_config(self):
        config = {
            "ec2": [{"action": "run_instances", "params": {"InstanceType": "t3.micro"}}],
            "s3": [{"action": "create_bucket", "params": {"Bucket": "my-bucket"}}],
        }
        is_safe, found = sanitize_boto3_config(config)
        assert is_safe is True
        assert found == []

    def test_dangerous_action_create_user(self):
        config = {
            "iam": [{"action": "create_user", "params": {"UserName": "hacker"}}],
        }
        is_safe, found = sanitize_boto3_config(config)
        assert is_safe is False
        assert len(found) > 0

    def test_dangerous_action_delete_account(self):
        config = {
            "organizations": [{"action": "delete_account", "params": {}}],
        }
        is_safe, found = sanitize_boto3_config(config)
        assert is_safe is False

    def test_mixed_safe_and_dangerous(self):
        config = {
            "s3": [{"action": "create_bucket", "params": {"Bucket": "ok"}}],
            "iam": [
                {"action": "create_role", "params": {"RoleName": "good"}},
                {"action": "create_access_key", "params": {"UserName": "bad"}},
            ],
        }
        is_safe, found = sanitize_boto3_config(config)
        assert is_safe is False
        assert "iam.create_access_key" in found


class TestAllowedServices:
    def test_expected_services_present(self):
        expected = [
            "aws_lambda", "aws_apigatewayv2", "aws_dynamodb",
            "aws_sqs", "aws_ecs", "aws_rds", "aws_elasticache",
            "aws_s3", "aws_vpc", "aws_cloudfront", "aws_sns",
            "aws_iam_role", "aws_security_group", "aws_route53",
        ]
        for svc in expected:
            assert svc in ALLOWED_AWS_SERVICES
