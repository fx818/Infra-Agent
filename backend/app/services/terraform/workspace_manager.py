"""
Terraform Workspace Manager — creates and manages per-project workspace directories.
"""

import io
import logging
import re
import shutil
import zipfile
from pathlib import Path

from app.core.config import settings
from app.utils.validators import fix_missing_container_definitions, fix_terraform_type_errors

logger = logging.getLogger(__name__)

# Matches   filename = "something.zip"   in .tf files
_ZIP_FILENAME_PATTERN = re.compile(r'filename\s*=\s*"([^"]+\.zip)"')

# Matches bare target = aws_apigatewayv2_integration.XXX.id  (missing integrations/ prefix)
# This is a very common LLM mistake — the API Gateway v2 API requires "integrations/${id}"
_APIGW_ROUTE_TARGET_BARE = re.compile(
    r'(target\s*=\s*)(aws_apigatewayv2_integration\.\w+\.id)'
)

# A minimal Lambda handler that returns a 200 response
_LAMBDA_PLACEHOLDER_CODE = '''\
def handler(event, context):
    """Placeholder Lambda handler created by NL2I."""
    return {
        "statusCode": 200,
        "body": "Hello from NL2I placeholder Lambda!"
    }
'''


class WorkspaceManager:
    """
    Manages isolated Terraform workspace directories, one per project.

    Each workspace contains:
    - .tf configuration files
    - .terraform/ directory (after init)
    - terraform.tfstate (after apply)
    """

    def __init__(self) -> None:
        self.base_dir = settings.workspaces_path

    def get_workspace_path(self, project_id: int) -> Path:
        """Get the workspace directory path for a project."""
        return self.base_dir / str(project_id)

    def create_workspace(self, project_id: int) -> Path:
        """
        Create a workspace directory for a project.

        Args:
            project_id: The project's database ID.

        Returns:
            Path to the created workspace directory.
        """
        workspace = self.get_workspace_path(project_id)
        workspace.mkdir(parents=True, exist_ok=True)
        logger.info("Workspace created at %s", workspace)
        return workspace

    def write_terraform_files(self, project_id: int, files: dict[str, str]) -> Path:
        """
        Write Terraform configuration files to a project's workspace.

        After writing .tf files, scans for Lambda `filename = "*.zip"` references
        and creates placeholder deployment packages so terraform apply won't fail.

        Args:
            project_id: The project's database ID.
            files: Dict mapping filename → content (e.g. {"main.tf": "..."}).

        Returns:
            Path to the workspace directory.
        """
        workspace = self.create_workspace(project_id)

        # Clean up existing Terraform configuration files to avoid conflicts (e.g. modules vs monolithic)
        # BUT preserve state and .terraform directory
        for item in workspace.iterdir():
            if item.is_file() and item.suffix == ".tf":
                try:
                    item.unlink()
                    logger.debug("Deleted old config file: %s", item.name)
                except Exception as e:
                    logger.warning("Failed to delete %s: %s", item.name, e)

        all_content = ""
        for filename, content in files.items():
            # Sanitize filename — only allow safe characters
            safe_name = filename.replace("..", "").replace("/", "_").replace("\\", "_")
            if not safe_name.endswith(".tf") and not safe_name.endswith(".tfvars"):
                safe_name += ".tf"

            # Auto-fix common LLM-generated terraform mistakes
            content = self._sanitize_tf_content(content)

            file_path = workspace / safe_name
            file_path.write_text(content, encoding="utf-8")
            logger.debug("Wrote %s (%d bytes)", file_path, len(content))
            all_content += content + "\n"

        logger.info("Wrote %d Terraform files to %s", len(files), workspace)

        # Cross-file deduplication: remove duplicate resource/data blocks by ID
        self._deduplicate_resources(workspace)

        # Create placeholder Lambda zip packages referenced by the .tf files
        self._create_lambda_packages(workspace, all_content)

        return workspace

    @staticmethod
    def _sanitize_tf_content(content: str) -> str:
        """
        Auto-fix common LLM-generated Terraform mistakes before writing to disk:
        1. Fix broken ${} interpolation (the #1 cause of deployment failures)
        2. API Gateway route target must use "integrations/${id}" format
        3. String boolean values converted to real booleans (assign_public_ip, etc.)
        4. Missing container_definitions injected into ECS task definitions
        """
        # Fix broken multi-line interpolation first
        # (e.g., family = "${var.project_name\n  ...\n}-suffix")
        content = WorkspaceManager._fix_broken_interpolation(content)

        # Convert remaining ${var.xxx} to join() or direct references
        content = WorkspaceManager._convert_interpolation_to_join(content)

        # Sanitize AWS identifiers: underscores -> hyphens in identifier fields
        content = WorkspaceManager._sanitize_aws_identifiers(content)

        # Fix API Gateway route target format
        content = _APIGW_ROUTE_TARGET_BARE.sub(
            r'\1"integrations/${\2}"', content
        )

        # Fix string boolean values (e.g., assign_public_ip = "DISABLED" → false)
        content = fix_terraform_type_errors(content)

        # Inject missing container_definitions in ECS task definitions
        content = fix_missing_container_definitions(content)

        return content

    @staticmethod
    def _fix_broken_interpolation(content: str) -> str:
        """
        Fix strings broken across lines by JSON encoding/decoding.
        
        Detects: family = "${var.project_name
                   ...many lines...
                 }-suffix"
        And merges them back into a single line.
        """
        lines = content.split("\n")
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # Check for unclosed interpolation: has ${ but no matching }
            if "${" in line:
                interp_count = line.count("${")
                close_count = line.count("}")

                if interp_count > close_count:
                    # Look ahead for the closing }-suffix" part
                    j = i + 1
                    found_close = False
                    while j < len(lines) and j <= i + 30:
                        next_line = lines[j]
                        stripped = next_line.strip()
                        if stripped.startswith("}") and '"' in stripped:
                            # Found the broken continuation — merge it
                            # Extract the suffix part (e.g., "}-web_app_ecs")
                            suffix = stripped  # e.g., '}-web_app_ecs"'
                            merged = line.rstrip() + suffix
                            fixed_lines.append(merged)
                            # Skip all lines between (they were duplicated content)
                            i = j + 1
                            found_close = True
                            break
                        j += 1

                    if found_close:
                        continue

            fixed_lines.append(line)
            i += 1

        return "\n".join(fixed_lines)

    @staticmethod
    def _convert_interpolation_to_join(content: str) -> str:
        """
        Convert ${var.xxx} interpolation to join() or direct references.
        
        - "${var.xxx}" → var.xxx (standalone)
        - "${var.xxx}-suffix" → join("-", [var.xxx, "suffix"])
        - "/prefix/${var.xxx}-suffix" → join("", ["/prefix/", join("-", [var.xxx, "suffix"])])
        """
        # Pattern 1: Standalone — "${var.xxx}" → var.xxx
        content = re.sub(
            r'"(\$\{(var\.\w+)\})"',
            r'\2',
            content,
        )

        # Pattern 2: Simple concat — "${var.xxx}-suffix" → join("-", [var.xxx, "suffix"])
        def _replace_concat(match):
            full = match.group(0)
            # Don't touch API Gateway route target (integrations/${...})
            if "integrations/" in full:
                return full
            # Don't touch strings inside jsonencode() — those are JSON values
            # (We can't easily detect this, so skip strings with awslogs)
            if "awslogs" in full:
                return full

            inner_match = re.search(r'\$\{([^}]+)\}', full)
            if not inner_match:
                return full

            var_ref = inner_match.group(1)
            before = full[1:full.index("${")]
            after = full[full.index("}") + 1:-1]

            # Simple case: just var reference with hyphen suffix
            if not before and after.startswith("-"):
                suffix = after[1:]  # Remove leading hyphen
                return f'join("-", [{var_ref}, "{suffix}"])'
            elif not before and after.startswith("/"):
                suffix = after[1:]
                return f'join("/", [{var_ref}, "{suffix}"])'
            elif before and after:
                return f'join("", ["{before}", {var_ref}, "{after}"])'
            elif before:
                return f'join("", ["{before}", {var_ref}])'
            elif after:
                return f'join("", [{var_ref}, "{after}"])'
            else:
                return var_ref

        content = re.sub(
            r'"[^"\n]*\$\{[^}]+\}[^"\n]*"',
            _replace_concat,
            content,
        )

        return content

    @staticmethod
    def _sanitize_aws_identifiers(content: str) -> str:
        """
        AWS services like RDS, ElastiCache, Redshift, etc. only allow
        lowercase alphanumeric characters and hyphens in identifiers.
        Replace underscores with hyphens in identifier fields and in
        string literals inside join() calls used for resource naming.
        """
        # Fix identifier fields: cluster_identifier, cluster_id, identifier
        # Pattern: cluster_identifier = join("-", [var.project_name, "some_thing"])
        # The "some_thing" needs to become "some-thing"
        def _fix_join_strings(match):
            full = match.group(0)
            # Replace underscores with hyphens only in quoted strings inside the join
            def _fix_inner_string(s_match):
                val = s_match.group(1)
                # Don't touch var references or function calls
                if val.startswith('var.') or val.startswith('aws_'):
                    return s_match.group(0)
                return '"' + val.replace('_', '-') + '"'
            return re.sub(r'"([^"]+)"', _fix_inner_string, full)

        # Fix join() calls on lines with identifier-type fields
        id_fields = (
            r'cluster_identifier|cluster_id|identifier|fargate_profile_name|'
            r'function_name|db_instance_identifier|replication_group_id|'
            r'database_name'
        )
        content = re.sub(
            rf'^(\s*(?:{id_fields})\s*=\s*join\(.+)$',
            lambda m: _fix_join_strings(m),
            content,
            flags=re.MULTILINE,
        )

        return content


    @staticmethod
    def _deduplicate_resources(workspace: "Path") -> None:
        """
        Cross-file resource deduplication.

        Deduplicates both:
          resource "type" "name" { ... }  
          data     "type" "name" { ... }

        The first file (alphabetical order) wins. Duplicates in later files
        are replaced with a single comment line. Uses balanced brace matching
        so entire blocks are removed — no orphan braces left behind.
        """
        tf_files = sorted(workspace.glob("*.tf"))  # deterministic order

        # Regex to find start-of-block declarations
        BLOCK_START = re.compile(
            r'^(resource|data)\s+"([^"]+)"\s+"([^"]+)"\s*\{',
            re.MULTILINE,
        )

        def _extract_block(text: str, start: int) -> str:
            """Extract a complete { ... } block starting at 'start' index."""
            depth = 0
            i = start
            n = len(text)
            while i < n:
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        return text[start:i + 1]
                i += 1
            return text[start:]  # unterminated block — return rest

        seen: set[str] = set()  # "resource_type.resource_name" or "data.type.name"

        for tf_file in tf_files:
            content = tf_file.read_text(encoding="utf-8", errors="ignore")
            modified = content
            offset = 0  # track shifting due to replacements

            for m in BLOCK_START.finditer(content):
                keyword  = m.group(1)   # "resource" or "data"
                rtype    = m.group(2)   # e.g. "aws_subnet"
                rname    = m.group(3)   # e.g. "public_subnet_1"
                key      = f"{keyword}.{rtype}.{rname}"

                # Find the opening brace of the block in the original content
                brace_pos = content.index('{', m.start())
                block = _extract_block(content, brace_pos)
                full_match = content[m.start():brace_pos + len(block)]

                if key in seen:
                    # Replace the full block with a comment
                    replacement = f"# Removed duplicate: {keyword} \"{rtype}\" \"{rname}\"\n"
                    logger.warning(
                        "Deduplicating %s \"%s\" \"%s\" in %s",
                        keyword, rtype, rname, tf_file.name,
                    )
                    modified = modified.replace(full_match, replacement, 1)
                else:
                    seen.add(key)

            if modified != content:
                tf_file.write_text(modified, encoding="utf-8")


    def _create_lambda_packages(self, workspace: Path, tf_content: str) -> None:
        """
        Scan terraform content for `filename = "*.zip"` references and create
        placeholder zip deployment packages if they don't already exist.
        """
        zip_refs = _ZIP_FILENAME_PATTERN.findall(tf_content)
        for zip_name in set(zip_refs):
            zip_path = workspace / zip_name
            if zip_path.exists():
                print(f"[WORKSPACE] Lambda package already exists: {zip_name}")
                continue

            print(f"[WORKSPACE] Creating placeholder Lambda package: {zip_name}")
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("index.py", _LAMBDA_PLACEHOLDER_CODE)
            zip_path.write_bytes(buf.getvalue())
            print(f"[WORKSPACE] Created {zip_name} ({zip_path.stat().st_size} bytes)")

    def delete_workspace(self, project_id: int) -> None:
        """
        Delete a project's workspace directory and all contents.

        Args:
            project_id: The project's database ID.
        """
        workspace = self.get_workspace_path(project_id)
        if workspace.exists():
            shutil.rmtree(workspace)
            logger.info("Deleted workspace at %s", workspace)

    def workspace_exists(self, project_id: int) -> bool:
        """Check if a workspace exists for the given project."""
        return self.get_workspace_path(project_id).exists()

    def list_files(self, project_id: int) -> list[str]:
        """List all files in a project's workspace."""
        workspace = self.get_workspace_path(project_id)
        if not workspace.exists():
            return []
        return [f.name for f in workspace.iterdir() if f.is_file()]
