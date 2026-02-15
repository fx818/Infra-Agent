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

        # Create placeholder Lambda zip packages referenced by the .tf files
        self._create_lambda_packages(workspace, all_content)

        return workspace

    @staticmethod
    def _sanitize_tf_content(content: str) -> str:
        """
        Auto-fix common LLM-generated Terraform mistakes:
        1. API Gateway route target must use "integrations/${id}" format
        """
        # Fix:  target = aws_apigatewayv2_integration.xxx.id
        #   to: target = "integrations/${aws_apigatewayv2_integration.xxx.id}"
        fixed = _APIGW_ROUTE_TARGET_BARE.sub(
            r'\1"integrations/${\2}"', content
        )
        if fixed != content:
            print("[WORKSPACE] Auto-fixed API Gateway route target format")
        return fixed

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
