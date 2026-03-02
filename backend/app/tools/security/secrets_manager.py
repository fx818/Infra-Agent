"""AWS Secrets Manager tool — provisions via boto3."""
import json
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
        label = params.get("label", sid)
        secret_name = params.get("secret_name") or f"__PROJECT__/{sid}"
        desc = params.get("description", "Application secret")

        configs = [
            {
                "service": "secretsmanager",
                "action": "create_secret",
                "params": {
                    "Name": secret_name,
                    "Description": desc,
                    "SecretString": json.dumps({"placeholder": "replace-with-actual-secret"}),
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}],
                },
                "label": label,
                "resource_type": "aws_secrets_manager",
                "resource_id_path": "ARN",
                "delete_action": "delete_secret",
                "delete_params": {"SecretId": secret_name, "RecoveryWindowInDays": 7},
            },
        ]

        return ToolResult(
            node=ToolNode(id=sid, type="aws_secrets_manager", label=label,
                          config=ToolNodeConfig(extra={"rotation": params.get("enable_rotation", False)})),
            boto3_config={"secretsmanager": configs},
        )
