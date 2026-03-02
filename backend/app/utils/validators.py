"""
Validators — boto3 config sanitization, service whitelist, graph validation.
"""

import logging
from app.schemas.architecture import ArchitectureGraph

logger = logging.getLogger(__name__)

# ── AWS Service Whitelist ────────────────────────────────────────
ALLOWED_AWS_SERVICES: set[str] = {
    "aws_lambda", "aws_apigatewayv2", "aws_dynamodb", "aws_sqs",
    "aws_ecs", "aws_rds", "aws_elasticache", "aws_s3", "aws_vpc",
    "aws_cloudfront", "aws_sns", "aws_iam_role", "aws_security_group",
    "aws_route53", "aws_ec2", "aws_eks", "aws_fargate", "aws_batch",
    "aws_app_runner", "aws_elastic_beanstalk", "aws_lightsail",
    "aws_cognito", "aws_kms", "aws_waf", "aws_acm", "aws_guardduty",
    "aws_kinesis", "aws_eventbridge", "aws_step_functions", "aws_mq",
    "aws_appsync", "aws_secrets_manager", "aws_athena", "aws_glue",
    "aws_emr", "aws_sagemaker", "aws_msk", "aws_opensearch",
    "aws_ses", "aws_pinpoint", "aws_amplify", "aws_iot",
    "aws_connect", "aws_cloudformation", "aws_codepipeline",
    "aws_codebuild", "aws_codecommit", "aws_codedeploy", "aws_ecr",
    "aws_cloudwatch", "aws_cloudtrail", "aws_xray", "aws_health",
    "aws_ebs", "aws_efs", "aws_fsx", "aws_aurora", "aws_neptune",
    "aws_documentdb", "aws_redshift", "aws_keyspaces", "aws_timestream",
    "aws_nat_gateway", "aws_elb", "aws_transit_gateway",
    "aws_direct_connect", "aws_global_accelerator",
    "aws_subnet", "aws_route_table", "aws_internet_gateway",
    "_edge_",
}

# ── Dangerous boto3 action patterns ─────────────────────────────
# Actions that should never appear in AI-generated configs
_DANGEROUS_ACTIONS: set[str] = {
    "delete_account", "close_account",
    "create_user",  # IAM users shouldn't be created by the tool
    "put_user_policy",
    "create_login_profile",
    "create_access_key",
}


def validate_architecture_graph(graph: ArchitectureGraph) -> list[str]:
    """
    Validate an architecture graph for correctness and safety.

    Returns:
        List of validation error messages. Empty list = valid.
    """
    errors: list[str] = []

    # Check for valid node types
    for node in graph.nodes:
        if node.type not in ALLOWED_AWS_SERVICES:
            errors.append(f"Node '{node.id}' uses disallowed service type: {node.type}")

    # Check for unique node IDs
    node_ids = [n.id for n in graph.nodes]
    seen = set()
    for nid in node_ids:
        if nid in seen:
            errors.append(f"Duplicate node ID: {nid}")
        seen.add(nid)

    # Validate edges reference existing nodes
    for edge in graph.edges:
        if edge.source not in seen:
            errors.append(f"Edge references non-existent source node: {edge.source}")
        if edge.target not in seen:
            errors.append(f"Edge references non-existent target node: {edge.target}")

    # Check for self-loops
    for edge in graph.edges:
        if edge.source == edge.target:
            errors.append(f"Self-loop detected on node: {edge.source}")

    if errors:
        logger.warning("Graph validation found %d errors", len(errors))
    else:
        logger.info("Graph validation passed for %d nodes, %d edges", len(graph.nodes), len(graph.edges))

    return errors


def sanitize_boto3_config(configs: dict) -> tuple[bool, list[str]]:
    """
    Check boto3 config for dangerous API calls.

    Args:
        configs: Boto3 config dict (service -> list of operations).

    Returns:
        Tuple of (is_safe, list of found dangerous actions).
    """
    found: list[str] = []

    for service, operations in configs.items():
        if not isinstance(operations, list):
            continue
        for op in operations:
            action = op.get("action", "")
            if action in _DANGEROUS_ACTIONS:
                found.append(f"{service}.{action}")

    if found:
        logger.warning("Dangerous boto3 actions found: %s", found)

    return len(found) == 0, found
