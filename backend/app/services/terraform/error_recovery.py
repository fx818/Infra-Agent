"""
Automated Error Recovery Agent for Terraform deployments.

When a terraform apply fails, this agent analyses the error output,
applies a targeted fix to the .tf files in the workspace, and signals
the caller to retry.  At most ONE recovery attempt is made per deploy.

Supported recovery strategies:
  INVALID_CONFIG   – remove/fix the offending resource block
  PERMISSION_DENIED– remove resources the AWS account cannot create
  RESOURCE_CONFLICT– destroy-then-retry (import is fragile)
  DEPENDENCY_ERROR – remove dangling references
  NETWORK_ERROR    – simple retry (transient)
  PROVIDER_ERROR   – simple retry (transient)
  STATE_ERROR      – nuke .terraform/ and retry init
"""

import logging
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Helpers ─────────────────────────────────────────────────────────

def _read_tf_files(workspace_dir: Path) -> dict[str, str]:
    """Read all .tf files from the workspace into a dict."""
    files: dict[str, str] = {}
    for tf in sorted(workspace_dir.glob("*.tf")):
        files[tf.name] = tf.read_text(encoding="utf-8", errors="replace")
    return files


def _write_tf_files(workspace_dir: Path, files: dict[str, str]) -> None:
    """Write dict of .tf files back to workspace."""
    for name, content in files.items():
        (workspace_dir / name).write_text(content, encoding="utf-8")


def _remove_resource_block(content: str, resource_type: str, resource_name: str | None = None) -> str:
    """
    Remove a `resource "type" "name" { ... }` block using balanced-brace matching.

    If resource_name is None, removes ALL resources of the given type.
    Returns the modified content.
    """
    if resource_name:
        pattern = rf'resource\s+"{re.escape(resource_type)}"\s+"{re.escape(resource_name)}"'
    else:
        pattern = rf'resource\s+"{re.escape(resource_type)}"\s+"[^"]+"'

    result = content
    while True:
        match = re.search(pattern, result)
        if not match:
            break
        # Find the opening brace
        start = match.start()
        brace_pos = result.find("{", match.end())
        if brace_pos == -1:
            break
        # Balanced brace walk
        depth = 1
        pos = brace_pos + 1
        while pos < len(result) and depth > 0:
            if result[pos] == "{":
                depth += 1
            elif result[pos] == "}":
                depth -= 1
            pos += 1
        # Replace the entire block with a comment
        block_end = pos
        removed_text = result[start:block_end]
        comment = f"# [AUTO-RECOVERY] Removed {resource_type}" + (f".{resource_name}" if resource_name else "") + " due to deployment error\n"
        result = result[:start] + comment + result[block_end:]
        logger.info("Removed resource block: %s", removed_text[:120])
    return result


def _remove_data_block(content: str, data_type: str, data_name: str | None = None) -> str:
    """Remove a `data "type" "name" { ... }` block using balanced-brace matching."""
    if data_name:
        pattern = rf'data\s+"{re.escape(data_type)}"\s+"{re.escape(data_name)}"'
    else:
        pattern = rf'data\s+"{re.escape(data_type)}"\s+"[^"]+"'

    result = content
    while True:
        match = re.search(pattern, result)
        if not match:
            break
        start = match.start()
        brace_pos = result.find("{", match.end())
        if brace_pos == -1:
            break
        depth = 1
        pos = brace_pos + 1
        while pos < len(result) and depth > 0:
            if result[pos] == "{":
                depth += 1
            elif result[pos] == "}":
                depth -= 1
            pos += 1
        comment = f"# [AUTO-RECOVERY] Removed data.{data_type}" + (f".{data_name}" if data_name else "") + "\n"
        result = result[:start] + comment + result[pos:]
    return result


def _remove_dangling_references(content: str, resource_type: str, resource_name: str | None = None) -> str:
    """
    Replace references like `aws_cloudfront_distribution.xxx.yyy` with
    empty strings so remaining resources don't fail on absent refs.
    """
    if resource_name:
        # e.g.  aws_cloudfront_distribution.my_cdn.domain_name  →  ""
        pattern = rf'{re.escape(resource_type)}\.{re.escape(resource_name)}\.\w+'
    else:
        pattern = rf'{re.escape(resource_type)}\.\w+\.\w+'
    result = re.sub(pattern, '""  # ref removed by auto-recovery', content)
    return result


def _extract_failing_resources(error_output: str) -> list[tuple[str, str]]:
    """
    Parse terraform error output to find resource type + name pairs.

    Looks for patterns like:
      with aws_apprunner_service.blinkit_frontend,
      on compute.tf line 38, in resource "aws_apprunner_service" "blinkit_frontend":
    """
    pairs: list[tuple[str, str]] = []

    # Pattern 1: "with <type>.<name>,"
    for m in re.finditer(r'with\s+(aws_\w+)\.(\w+)', error_output):
        pairs.append((m.group(1), m.group(2)))

    # Pattern 2: 'resource "<type>" "<name>"'
    for m in re.finditer(r'resource\s+"(aws_\w+)"\s+"(\w+)"', error_output):
        pair = (m.group(1), m.group(2))
        if pair not in pairs:
            pairs.append(pair)

    return pairs


# ── Service-specific fixers ─────────────────────────────────────────

def _fix_api_gateway_no_methods(files: dict[str, str], error_output: str) -> tuple[bool, str]:
    """
    Fix: "The REST API doesn't contain any methods"

    This happens when aws_api_gateway_deployment exists but no methods
    or integrations were created on the REST API.  The fix removes
    the REST API Gateway v1 resources entirely — the next generation
    cycle should use API Gateway v2 (HTTP API) instead.
    """
    rest_api_types = [
        "aws_api_gateway_rest_api",
        "aws_api_gateway_deployment",
        "aws_api_gateway_stage",
        "aws_api_gateway_resource",
        "aws_api_gateway_method",
        "aws_api_gateway_method_response",
        "aws_api_gateway_integration",
        "aws_api_gateway_integration_response",
    ]

    removed_any = False
    for filename in list(files.keys()):
        original = files[filename]
        content = original
        for rtype in rest_api_types:
            content = _remove_resource_block(content, rtype)
            content = _remove_dangling_references(content, rtype)
        if content != original:
            files[filename] = content
            removed_any = True

    if removed_any:
        return True, "Removed REST API Gateway v1 resources (no methods defined). Deployment will proceed without API Gateway."
    return False, "Could not locate REST API Gateway resources to remove."


def _fix_cloudfront_access_denied(files: dict[str, str], error_output: str) -> tuple[bool, str]:
    """
    Fix: CloudFront AccessDenied / account verification required.

    Removes CloudFront distribution and OAI resources since the
    AWS account is not verified for CloudFront.
    """
    cf_types = [
        "aws_cloudfront_distribution",
        "aws_cloudfront_origin_access_identity",
        "aws_cloudfront_origin_access_control",
        "aws_cloudfront_cache_policy",
        "aws_cloudfront_response_headers_policy",
    ]

    removed_any = False
    for filename in list(files.keys()):
        original = files[filename]
        content = original
        for rtype in cf_types:
            content = _remove_resource_block(content, rtype)
            content = _remove_dangling_references(content, rtype)
        if content != original:
            files[filename] = content
            removed_any = True

    if removed_any:
        return True, "Removed CloudFront resources (AWS account not verified for CloudFront). Deployment will proceed without CDN."
    return False, "Could not locate CloudFront resources to remove."


def _fix_apprunner_create_failed(files: dict[str, str], error_output: str) -> tuple[bool, str]:
    """
    Fix: App Runner service CREATE_FAILED.

    Removes the App Runner service resource.  The architecture may
    still work without it (other compute resources remain).
    """
    ar_types = [
        "aws_apprunner_service",
        "aws_apprunner_auto_scaling_configuration_version",
        "aws_apprunner_custom_domain_association",
        "aws_apprunner_connection",
        "aws_apprunner_vpc_connector",
        "aws_apprunner_observability_configuration",
    ]

    removed_any = False
    for filename in list(files.keys()):
        original = files[filename]
        content = original
        for rtype in ar_types:
            content = _remove_resource_block(content, rtype)
            content = _remove_dangling_references(content, rtype)
        if content != original:
            files[filename] = content
            removed_any = True

    if removed_any:
        return True, "Removed App Runner resources (service creation failed). Deployment will proceed without App Runner."
    return False, "Could not locate App Runner resources to remove."


# ── Main recovery logic ─────────────────────────────────────────────

class ErrorRecoveryAgent:
    """
    Analyses terraform apply errors and attempts ONE automated fix
    before the caller retries the deployment.
    """

    # Maps regex patterns in error output → specific fixer functions.
    # Each fixer receives (files_dict, error_output) and returns (bool, str).
    _SPECIFIC_FIXERS: list[tuple[str, callable]] = [
        (r"REST API doesn't contain any methods", _fix_api_gateway_no_methods),
        (r"CreateDeployment.*BadRequestException", _fix_api_gateway_no_methods),
        (r"apprunner.*CREATE_FAILED", _fix_apprunner_create_failed),
        (r"App Runner.*CREATE_FAILED", _fix_apprunner_create_failed),
        (r"CloudFront.*AccessDenied", _fix_cloudfront_access_denied),
        (r"account must be verified.*CloudFront", _fix_cloudfront_access_denied),
        (r"AccessDenied.*CloudFront", _fix_cloudfront_access_denied),
    ]

    async def recover(
        self,
        error_category: str,
        error_output: str,
        workspace_dir: Path,
        project_id: int,
        db=None,
    ) -> tuple[bool, str]:
        """
        Attempt to automatically recover from a terraform apply failure.

        Args:
            error_category: One of the classified categories (PERMISSION_DENIED, etc.)
            error_output: Full terraform output containing error details.
            workspace_dir: Path to the terraform workspace with .tf files.
            project_id: Project ID (for logging).
            db: Optional DB session (unused for now, reserved for future use).

        Returns:
            (recovered, description) — recovered=True means the caller should retry.
        """
        logger.info(
            "[AUTO-RECOVERY] project=%d category=%s — attempting recovery",
            project_id, error_category,
        )
        print(f"[AUTO-RECOVERY] project={project_id} category={error_category}")

        # ── Step 1: Try specific pattern-based fixers first ──────────
        files = _read_tf_files(workspace_dir)
        if not files:
            return False, "No .tf files found in workspace."

        descriptions: list[str] = []

        for pattern, fixer in self._SPECIFIC_FIXERS:
            if re.search(pattern, error_output, re.IGNORECASE):
                recovered, desc = fixer(files, error_output)
                if recovered:
                    descriptions.append(desc)
                    logger.info("[AUTO-RECOVERY] fixer matched: %s", desc)

        # If any specific fixers fired, write the modified files and signal retry
        if descriptions:
            _write_tf_files(workspace_dir, files)
            combined_desc = " | ".join(descriptions)
            print(f"[AUTO-RECOVERY] ✓ Applied fixes: {combined_desc}")
            return True, combined_desc

        # ── Step 2: Category-based fallback strategies ───────────────

        if error_category in ("NETWORK_ERROR", "PROVIDER_ERROR"):
            print("[AUTO-RECOVERY] Transient error — signaling simple retry")
            return True, f"Transient {error_category} detected — retrying deployment."

        if error_category == "STATE_ERROR":
            return self._fix_state_error(workspace_dir)

        if error_category == "PERMISSION_DENIED":
            return self._fix_permission_denied(files, error_output, workspace_dir)

        if error_category in ("INVALID_CONFIG", "DEPENDENCY_ERROR"):
            return self._fix_config_error(files, error_output, workspace_dir)

        if error_category == "RESOURCE_CONFLICT":
            return self._fix_resource_conflict(files, error_output, workspace_dir)

        logger.info("[AUTO-RECOVERY] No recovery strategy for category=%s", error_category)
        print(f"[AUTO-RECOVERY] ✗ No recovery strategy for {error_category}")
        return False, f"No automated recovery available for {error_category}."

    # ── Category strategies ─────────────────────────────────────────

    def _fix_state_error(self, workspace_dir: Path) -> tuple[bool, str]:
        """Delete .terraform directory and signal retry (re-init)."""
        tf_dir = workspace_dir / ".terraform"
        if tf_dir.exists():
            shutil.rmtree(tf_dir, ignore_errors=True)
            logger.info("[AUTO-RECOVERY] Deleted .terraform/ directory")
        lock_file = workspace_dir / ".terraform.lock.hcl"
        if lock_file.exists():
            lock_file.unlink(missing_ok=True)
        print("[AUTO-RECOVERY] ✓ Cleared terraform state/cache — retry will re-init")
        return True, "Cleared .terraform/ directory and lock file. Re-initializing."

    def _fix_permission_denied(
        self, files: dict[str, str], error_output: str, workspace_dir: Path,
    ) -> tuple[bool, str]:
        """
        For permission errors, try to identify which resource failed and remove it.
        """
        failing = _extract_failing_resources(error_output)
        if not failing:
            return False, "Could not identify which resource caused the permission error."

        removed: list[str] = []
        for rtype, rname in failing:
            for filename in list(files.keys()):
                original = files[filename]
                content = _remove_resource_block(original, rtype, rname)
                content = _remove_dangling_references(content, rtype, rname)
                if content != original:
                    files[filename] = content
                    removed.append(f"{rtype}.{rname}")

        if removed:
            _write_tf_files(workspace_dir, files)
            desc = f"Removed {len(removed)} resource(s) lacking permissions: {', '.join(removed)}"
            print(f"[AUTO-RECOVERY] ✓ {desc}")
            return True, desc

        return False, "Permission denied but could not identify removable resources."

    def _fix_config_error(
        self, files: dict[str, str], error_output: str, workspace_dir: Path,
    ) -> tuple[bool, str]:
        """
        For INVALID_CONFIG / DEPENDENCY_ERROR, identify the failing resource
        and remove it from the .tf files.
        """
        failing = _extract_failing_resources(error_output)
        if not failing:
            # Try to extract from "Reference to undeclared resource" patterns
            undeclared = re.findall(
                r'Reference to undeclared resource\b.*?"(aws_\w+)"\s+"(\w+)"',
                error_output,
            )
            if undeclared:
                failing = undeclared

        if not failing:
            return False, "Could not identify which resource caused the config error."

        removed: list[str] = []
        for rtype, rname in failing:
            for filename in list(files.keys()):
                original = files[filename]
                content = _remove_resource_block(original, rtype, rname)
                content = _remove_dangling_references(content, rtype, rname)
                if content != original:
                    files[filename] = content
                    removed.append(f"{rtype}.{rname}")

        if removed:
            _write_tf_files(workspace_dir, files)
            desc = f"Removed {len(removed)} misconfigured resource(s): {', '.join(removed)}"
            print(f"[AUTO-RECOVERY] ✓ {desc}")
            return True, desc

        return False, "Config/dependency error but could not identify removable resources."

    def _fix_resource_conflict(
        self, files: dict[str, str], error_output: str, workspace_dir: Path,
    ) -> tuple[bool, str]:
        """
        For RESOURCE_CONFLICT (already exists), the safest approach is
        to remove the conflicting resource and let the user re-deploy.
        terraform import is fragile and needs exact state, so we avoid it.
        """
        failing = _extract_failing_resources(error_output)
        if not failing:
            return False, "Could not identify the conflicting resource."

        removed: list[str] = []
        for rtype, rname in failing:
            for filename in list(files.keys()):
                original = files[filename]
                content = _remove_resource_block(original, rtype, rname)
                content = _remove_dangling_references(content, rtype, rname)
                if content != original:
                    files[filename] = content
                    removed.append(f"{rtype}.{rname}")

        if removed:
            _write_tf_files(workspace_dir, files)
            desc = f"Removed {len(removed)} conflicting resource(s): {', '.join(removed)}. They may already exist in AWS."
            print(f"[AUTO-RECOVERY] ✓ {desc}")
            return True, desc

        return False, "Resource conflict but could not identify removable resources."
