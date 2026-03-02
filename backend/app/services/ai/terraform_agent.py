"""
Terraform Generator Agent — converts architecture graphs to Terraform IaC.
Includes post-generation sanitization and validation to catch common errors.
"""

import json
import logging
import re

from app.schemas.architecture import ArchitectureGraph, TerraformFileMap
from app.services.ai.base import BaseLLMProvider, get_llm_provider
from app.utils.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


# ── HCL Sanitizer ──────────────────────────────────────────────────

def _sanitize_terraform_files(files: dict[str, str]) -> dict[str, str]:
    """
    Post-process generated Terraform files to fix common LLM output issues.
    
    The LLM returns Terraform code inside JSON strings, which frequently breaks:
    - "${var.name}" interpolation (JSON escaping mangles the braces)
    - Strings split across lines
    - Duplicate block definitions
    
    This sanitizer repairs these issues before validation.
    """
    sanitized = {}
    for filename, content in files.items():
        content = _fix_interpolation(content)
        content = _fix_broken_multiline_strings(content)
        sanitized[filename] = content
    return sanitized


def _fix_interpolation(content: str) -> str:
    """
    Replace ${var.xxx} interpolation with direct references or join() calls.
    
    Examples:
      '  name = "${var.project_name}"'  →  '  name = var.project_name'
      '  name = "${var.project_name}-web"'  →  '  name = join("-", [var.project_name, "web"])'
    """
    # Pattern 1: Standalone interpolation — "= "${var.xxx}""
    # Replace with direct reference
    content = re.sub(
        r'"(\$\{(var\.\w+|local\.\w+|aws_\w+\.\w+\.\w+)\})"',
        r'\2',
        content,
    )
    
    # Pattern 2: Interpolation with suffix/prefix — "${var.xxx}-suffix" or "${var.xxx}-a-b"
    # Replace with join()
    def _replace_interpolation_concat(match):
        full = match.group(0)
        # Extract the variable reference and the remaining parts
        inner_match = re.search(r'\$\{([^}]+)\}', full)
        if not inner_match:
            return full
        
        var_ref = inner_match.group(1)
        # Get everything before ${ and after }
        before_interp = full[1:full.index("${")]  # Skip opening quote
        after_interp = full[full.index("}") + 1:-1]  # Skip closing quote
        
        # Build join() parts
        parts = []
        if before_interp:
            parts.append(f'"{before_interp}"')
        parts.append(var_ref)
        if after_interp:
            # Split on hyphens to make cleaner join
            parts.append(f'"{after_interp}"')
        
        if len(parts) == 1:
            return parts[0]
        
        # Determine separator
        combined = before_interp + after_interp
        if "-" in combined:
            # Use join with hyphen separator
            clean_parts = []
            for p in parts:
                if p.startswith('"') and p.endswith('"'):
                    inner = p[1:-1]
                    # Remove leading/trailing hyphens from literals since join adds them
                    inner = inner.strip("-")
                    if inner:
                        clean_parts.append(f'"{inner}"')
                else:
                    clean_parts.append(p)
            return f'join("-", [{", ".join(clean_parts)}])'
        else:
            return f'join("", [{", ".join(parts)}])'
    
    # Match strings containing ${...} interpolation
    content = re.sub(
        r'"[^"]*\$\{[^}]+\}[^"]*"',
        _replace_interpolation_concat,
        content,
    )
    
    return content


def _fix_broken_multiline_strings(content: str) -> str:
    """
    Fix strings that were broken across lines by JSON parsing.
    
    Detects lines with unclosed quotes/interpolations and attempts to
    join them with the content that was split off.
    """
    lines = content.split("\n")
    fixed_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for unclosed interpolation: has ${ but no matching } before end of line
        if "${" in line:
            interp_count = line.count("${")
            close_count = line.count("}")
            
            if interp_count > close_count:
                # This line has an unclosed ${...} — try to find the closing on subsequent lines
                # Look ahead for the closing part
                combined = line
                j = i + 1
                found_close = False
                while j < len(lines) and j <= i + 5:  # Look up to 5 lines ahead
                    next_line = lines[j]
                    # Check if next line starts with `}` or contains the closing part
                    if next_line.strip().startswith("}") and '"' in next_line:
                        # This looks like the broken part: `}-suffix"`
                        # Merge it back into the original line
                        combined = combined.rstrip() + next_line.strip()
                        found_close = True
                        j += 1
                        break
                    j += 1
                
                if found_close:
                    fixed_lines.append(combined)
                    i = j
                    continue
        
        fixed_lines.append(line)
        i += 1
    
    return "\n".join(fixed_lines)


# ── Post-generation validation rules ────────────────────────────────
_VALIDATION_RULES: list[tuple[str, str, str]] = [
    # (check_id, description, pattern_that_should_NOT_exist)
    ("NO_MODULES", "Module blocks are not allowed", r'\bmodule\s+"'),
    ("NO_VPC_TRUE", "aws_eip must use domain=\"vpc\", not vpc=true", r'\bvpc\s*=\s*true\b'),
    ("NO_T2_MICRO", "db.t2.micro is unsupported for modern PostgreSQL", r'db\.t2\.micro'),
    ("NO_STRING_BOOL", "assign_public_ip must be boolean, not string", r'assign_public_ip\s*=\s*"'),
    ("NO_MANAGED_POLICY_ARNS", "managed_policy_arns on aws_iam_role is deprecated",
     r'managed_policy_arns\s*='),
]

_REQUIRED_PATTERNS: list[tuple[str, str, str]] = [
    # (check_id, description, pattern_that_MUST_exist)
    ("HAS_REQUIRED_PROVIDERS", "Must have required_providers block", r'required_providers'),
    ("HAS_AWS_PROVIDER", "Must have provider \"aws\" block", r'provider\s+"aws"'),
]


def _validate_terraform_files(files: dict[str, str]) -> list[str]:
    """
    Run heuristic validation on generated Terraform files.
    Returns a list of warning/error strings.
    """
    all_content = "\n".join(files.values())
    issues: list[str] = []

    # Check for patterns that should NOT exist
    for check_id, description, pattern in _VALIDATION_RULES:
        if re.search(pattern, all_content):
            issues.append(f"[{check_id}] {description}")

    # Check for patterns that MUST exist
    for check_id, description, pattern in _REQUIRED_PATTERNS:
        if not re.search(pattern, all_content):
            issues.append(f"[{check_id}] {description}")

    # Check ECS Fargate cpu/memory combinations
    cpu_mem_pattern = re.findall(
        r'cpu\s*=\s*"?(\d+)"?\s*\n\s*memory\s*=\s*"?(\d+)"?', all_content
    )
    valid_combos = {
        256: {512, 1024, 2048},
        512: {1024, 2048, 3072, 4096},
        1024: {2048, 3072, 4096, 5120, 6144, 7168, 8192},
        2048: set(range(4096, 16385, 1024)),
        4096: set(range(8192, 30721, 1024)),
    }
    for cpu_str, mem_str in cpu_mem_pattern:
        cpu, mem = int(cpu_str), int(mem_str)
        if cpu in valid_combos and mem not in valid_combos[cpu]:
            issues.append(
                f"[INVALID_FARGATE_COMBO] cpu={cpu} memory={mem} is not a valid Fargate combination"
            )

    # Check security groups have egress rules
    if "aws_security_group" in all_content and "egress" not in all_content:
        issues.append("[MISSING_EGRESS] Security groups should have egress rules")

    # Check IAM roles have assume_role_policy
    iam_roles = re.findall(r'resource\s+"aws_iam_role"\s+"(\w+)"', all_content)
    for role_name in iam_roles:
        # Simple heuristic: look for assume_role_policy after the role definition
        if "assume_role_policy" not in all_content:
            issues.append(f"[MISSING_ASSUME_ROLE] IAM role '{role_name}' may be missing assume_role_policy")
            break

    # Check CloudFront has required fields
    if "aws_cloudfront_distribution" in all_content:
        for field in ["allowed_methods", "cached_methods", "viewer_certificate", "restrictions"]:
            if field not in all_content:
                issues.append(f"[CLOUDFRONT_MISSING] CloudFront distribution is missing '{field}'")

    # Check for broken string interpolation (unclosed ${ without })
    for filename, content in files.items():
        for line_no, line in enumerate(content.splitlines(), 1):
            # Count ${ and } in the line to detect unclosed interpolations
            interp_opens = line.count("${")
            interp_closes = line.count("}")
            if interp_opens > 0 and interp_closes < interp_opens:
                issues.append(
                    f"[BROKEN_INTERPOLATION] {filename}:{line_no} — unclosed '${{' "
                    f"in: {line.strip()[:80]}"
                )

    return issues


class TerraformAgent:
    """
    Takes an architecture graph and generates production-ready
    Terraform configuration files with post-generation validation.
    """

    def __init__(self, llm: BaseLLMProvider | None = None) -> None:
        self.llm = llm or get_llm_provider()
        self.system_prompt = load_prompt("terraform_agent_prompt.md")

    async def run(
        self,
        graph: ArchitectureGraph,
        region: str = "us-east-1",
        project_name: str = "nl2i-project",
    ) -> TerraformFileMap:
        """
        Generate Terraform files from an architecture graph.
        Includes post-generation validation with auto-retry on failures.

        Args:
            graph: The architecture graph to convert.
            region: AWS region for the deployment.
            project_name: Project name used for resource naming.

        Returns:
            TerraformFileMap with filename → content mapping.
        """
        logger.info(
            "TerraformAgent: generating for %d nodes, region=%s",
            len(graph.nodes), region,
        )

        # Sanitize project name for AWS resource naming
        safe_project_name = project_name.lower().replace(" ", "-").replace("_", "-")
        safe_project_name = "".join(c for c in safe_project_name if c.isalnum() or c == "-")

        graph_dict = graph.model_dump(by_alias=True)

        user_prompt = (
            f"## Architecture Graph\n\n"
            f"```json\n{json.dumps(graph_dict, indent=2)}\n```\n\n"
            f"## Configuration\n\n"
            f"- AWS Region: {region}\n"
            f"- Project Name: {safe_project_name}\n\n"
            f"## IMPORTANT\n\n"
            f"Generate COMPLETE, DEPLOYMENT-READY Terraform configuration files.\n"
            f"The code MUST pass `terraform validate` and `terraform apply` on the first try.\n"
            f"Double-check every resource reference, every required argument, and every value type.\n"
            f"Follow the Final Checklist in your system prompt before returning.\n\n"
            f"## CRITICAL RULES\n\n"
            f"- **NEVER use ${{}} interpolation** — use `join(\"-\", [var.project_name, \"suffix\"])` instead\n"
            f"- For simple references, use `var.project_name` directly (no quotes, no interpolation)\n"
            f"- Every resource must have exactly ONE of each block type (no duplicate container_definitions, etc.)\n"
            f"- ECS cpu/memory must be valid Fargate string pairs (e.g., cpu=\"256\", memory=\"512\")\n"
        )

        # First attempt
        result = await self.llm.generate(
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            temperature=0.1,
        )

        terraform_files = TerraformFileMap(**result)
        logger.info(
            "TerraformAgent: generated %d files: %s",
            len(terraform_files.files),
            list(terraform_files.files.keys()),
        )

        # Sanitize generated files (fix interpolation, broken strings)
        terraform_files.files = _sanitize_terraform_files(terraform_files.files)
        logger.info("TerraformAgent: sanitized %d files", len(terraform_files.files))

        # Post-generation validation
        issues = _validate_terraform_files(terraform_files.files)

        if issues:
            logger.warning(
                "TerraformAgent: validation found %d issues: %s",
                len(issues), issues,
            )

            # Auto-retry with error context
            fix_prompt = (
                f"{user_prompt}\n\n"
                f"## CRITICAL: Fix These Issues\n\n"
                f"Your previous generation had the following problems that MUST be fixed:\n\n"
            )
            for issue in issues:
                fix_prompt += f"- {issue}\n"
            fix_prompt += (
                f"\n"
                f"Fix ALL of these issues and regenerate the complete Terraform configuration.\n"
                f"Every issue listed above MUST be resolved.\n"
                f"REMINDER: NEVER use ${{}} interpolation. Use join() instead.\n"
            )

            logger.info("TerraformAgent: retrying with %d fixes requested", len(issues))
            retry_result = await self.llm.generate(
                system_prompt=self.system_prompt,
                user_prompt=fix_prompt,
                temperature=0.05,  # Even lower temperature for fixes
            )

            terraform_files = TerraformFileMap(**retry_result)

            # Sanitize retry output too
            terraform_files.files = _sanitize_terraform_files(terraform_files.files)

            # Log remaining issues (if any) — but don't retry again
            remaining_issues = _validate_terraform_files(terraform_files.files)
            if remaining_issues:
                logger.warning(
                    "TerraformAgent: %d issues remain after retry: %s",
                    len(remaining_issues), remaining_issues,
                )
            else:
                logger.info("TerraformAgent: all issues resolved after retry")

        return terraform_files

