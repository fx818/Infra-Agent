"""
Validators — Terraform sanitization, service whitelist, graph validation.
"""

import re
import logging

from app.schemas.architecture import ArchitectureGraph

logger = logging.getLogger(__name__)

# ── AWS Service Whitelist ────────────────────────────────────────
ALLOWED_AWS_SERVICES: set[str] = {
    "aws_lambda",
    "aws_apigatewayv2",
    "aws_dynamodb",
    "aws_sqs",
    "aws_ecs",
    "aws_rds",
    "aws_elasticache",
    "aws_s3",
    "aws_vpc",
    "aws_cloudfront",
    "aws_sns",
    "aws_iam_role",
    "aws_security_group",
    "aws_route53",
}

# ── Terraform dangerous patterns ────────────────────────────────
_DANGEROUS_PATTERNS: list[re.Pattern] = [
    re.compile(r"provisioner\s+\"local-exec\"", re.IGNORECASE),
    re.compile(r"provisioner\s+\"remote-exec\"", re.IGNORECASE),
    re.compile(r"external\s+data", re.IGNORECASE),
    re.compile(r"null_resource", re.IGNORECASE),
    re.compile(r"local_file", re.IGNORECASE),
    re.compile(r"template_file", re.IGNORECASE),
    re.compile(r"\$\{.*\bfile\(", re.IGNORECASE),  # file() function
    re.compile(r"\$\{.*\btemplatefile\(", re.IGNORECASE),
]


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


def sanitize_terraform_content(content: str) -> tuple[bool, list[str]]:
    """
    Check Terraform content for dangerous patterns.

    Args:
        content: Raw Terraform file content.

    Returns:
        Tuple of (is_safe, list of found dangerous patterns).
    """
    found: list[str] = []

    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(content):
            found.append(pattern.pattern)

    if found:
        logger.warning("Dangerous Terraform patterns found: %s", found)

    return len(found) == 0, found


def sanitize_terraform_files(files: dict[str, str]) -> tuple[bool, dict[str, list[str]]]:
    """
    Validate all Terraform files in a file map.

    Returns:
        Tuple of (all_safe, dict mapping filename → list of issues).
    """
    all_safe = True
    issues: dict[str, list[str]] = {}

    for filename, content in files.items():
        is_safe, found = sanitize_terraform_content(content)
        if not is_safe:
            all_safe = False
            issues[filename] = found

    return all_safe, issues
