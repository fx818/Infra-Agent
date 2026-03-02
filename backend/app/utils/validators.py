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


# ── Terraform type-error auto-fixer ─────────────────────────────
# Regex replacements applied sequentially to every .tf file
# to correct common LLM type errors before the code is written to disk.
_BOOL_STRING_FIXES: list[tuple[re.Pattern, str]] = [
    # assign_public_ip: "ENABLED" → true, "DISABLED" → false
    (re.compile(r'(assign_public_ip\s*=\s*)"ENABLED"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(assign_public_ip\s*=\s*)"DISABLED"', re.IGNORECASE), r'\1false'),
    (re.compile(r'(assign_public_ip\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(assign_public_ip\s*=\s*)"false"', re.IGNORECASE), r'\1false'),

    # enable_dns_hostnames/support: strings → bools
    (re.compile(r'(enable_dns(?:_hostnames|_support)\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(enable_dns(?:_hostnames|_support)\s*=\s*)"false"', re.IGNORECASE), r'\1false'),

    # multi_az: "true"/"false" strings → bools
    (re.compile(r'(multi_az\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(multi_az\s*=\s*)"false"', re.IGNORECASE), r'\1false'),

    # skip_final_snapshot: "true"/"false" → bools
    (re.compile(r'(skip_final_snapshot\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(skip_final_snapshot\s*=\s*)"false"', re.IGNORECASE), r'\1false'),

    # publicly_accessible: "true"/"false" → bools
    (re.compile(r'(publicly_accessible\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(publicly_accessible\s*=\s*)"false"', re.IGNORECASE), r'\1false'),

    # internal (LB): "true"/"false" → bools
    (re.compile(r'(internal\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(internal\s*=\s*)"false"', re.IGNORECASE), r'\1false'),

    # enabled: "true"/"false" → bools
    (re.compile(r'(enabled\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(enabled\s*=\s*)"false"', re.IGNORECASE), r'\1false'),

    # apply_immediately: "true"/"false" → bools
    (re.compile(r'(apply_immediately\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(apply_immediately\s*=\s*)"false"', re.IGNORECASE), r'\1false'),

    # Block public access booleans
    (re.compile(r'(block_public(?:_acls|_policy|_access)\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(block_public(?:_acls|_policy|_access)\s*=\s*)"false"', re.IGNORECASE), r'\1false'),
    (re.compile(r'(ignore_public_acls\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(ignore_public_acls\s*=\s*)"false"', re.IGNORECASE), r'\1false'),
    (re.compile(r'(restrict_public_buckets\s*=\s*)"true"', re.IGNORECASE), r'\1true'),
    (re.compile(r'(restrict_public_buckets\s*=\s*)"false"', re.IGNORECASE), r'\1false'),
]


def fix_terraform_type_errors(content: str) -> str:
    """
    Post-process Terraform content to fix common LLM type errors:
    - Convert string boolean values to real Terraform booleans (true/false)
    - Convert ENABLED/DISABLED strings to true/false for bool attributes

    This acts as a reliable safety net independent of the LLM prompt.
    """
    for pattern, replacement in _BOOL_STRING_FIXES:
        content, count = pattern.subn(replacement, content)
        if count:
            logger.debug("fix_terraform_type_errors: fixed %d occurrence(s) of %s", count, pattern.pattern)
    return content


# Detects an aws_ecs_task_definition block that is missing container_definitions
_ECS_TASK_DEF_PATTERN = re.compile(
    r'(resource\s+"aws_ecs_task_definition"\s+"(\w+)"\s*\{)((?:(?!container_definitions)[^}])*?)(\})',
    re.DOTALL,
)


def fix_missing_container_definitions(content: str) -> str:
    """
    Detect aws_ecs_task_definition blocks missing the required
    container_definitions argument and inject a working placeholder.

    Also ensures an aws_cloudwatch_log_group is present if a task definition is added.
    """
    def _inject(m: re.Match) -> str:
        block_open = m.group(1)
        resource_name = m.group(2)
        body = m.group(3)
        block_close = m.group(4)

        # Already has container_definitions (shouldn't hit, but be safe)
        if "container_definitions" in body:
            return m.group(0)

        logger.warning(
            "fix_missing_container_definitions: injecting placeholder container_definitions "
            "into aws_ecs_task_definition.%s", resource_name
        )

        placeholder = f'''
  container_definitions = jsonencode([
    {{
      name      = "{resource_name}"
      image     = "nginx:latest"
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {{
          containerPort = 80
          protocol      = "tcp"
        }}
      ]
    }}
  ])
'''
        return block_open + body.rstrip() + placeholder + block_close

    patched, count = _ECS_TASK_DEF_PATTERN.subn(_inject, content)
    if count:
        logger.info("fix_missing_container_definitions: patched %d ECS task definition(s)", count)
    return patched


def fix_terraform_files(files: dict[str, str]) -> dict[str, str]:
    """Apply all Terraform auto-fixers to every file in a Terraform file map."""
    result = {}
    for filename, content in files.items():
        content = fix_terraform_type_errors(content)
        content = fix_missing_container_definitions(content)
        result[filename] = content
    return result
