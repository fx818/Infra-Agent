"""AWS Secrets Manager tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateSecretsManagerTool(BaseTool):
    name = "create_secrets_manager"
    description = (
        "Create an AWS Secrets Manager secret for storing database credentials, "
        "API keys, and other sensitive configuration. Supports automatic rotation."
    )
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "secret_id": {"type": "string", "description": "Unique identifier (e.g., 'db_credentials')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "secret_name": {"type": "string", "description": "AWS Secrets Manager secret name.", "default": ""},
            "description": {"type": "string", "description": "Description of what this secret stores.", "default": "Application secret"},
            "enable_rotation": {"type": "boolean", "description": "Enable automatic rotation.", "default": False},
            "rotation_days": {"type": "integer", "description": "Rotation interval in days.", "default": 30},
        },
        "required": ["secret_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["secret_id"]
        secret_name = params.get("secret_name") or f"${{var.project_name}}/{sid}"
        desc = params.get("description", "Application secret")
        enable_rotation = params.get("enable_rotation", False)
        rotation_days = params.get("rotation_days", 30)

        rotation_block = f'''
resource "aws_secretsmanager_secret_rotation" "{sid}_rotation" {{
  secret_id           = aws_secretsmanager_secret.{sid}.id
  rotation_lambda_arn = ""  # Add your rotation Lambda ARN here
  rotation_rules {{
    automatically_after_days = {rotation_days}
  }}
}}''' if enable_rotation else ""

        tf_code = f'''
resource "aws_secretsmanager_secret" "{sid}" {{
  name        = "{secret_name}"
  description = "{desc}"
  recovery_window_in_days = 7
  tags        = {{ Name = "${{var.project_name}}-{sid}" }}
}}

resource "aws_secretsmanager_secret_version" "{sid}_value" {{
  secret_id     = aws_secretsmanager_secret.{sid}.id
  secret_string = jsonencode({{ placeholder = "replace-with-actual-secret" }})
}}
{rotation_block}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_secrets_manager", label=params.get("label", sid),
                          config=ToolNodeConfig(extra={"rotation": enable_rotation})),
            terraform_code={"security.tf": tf_code},
        )
