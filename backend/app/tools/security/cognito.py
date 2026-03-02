"""AWS Cognito User Pool tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateCognitoTool(BaseTool):
    name = "create_cognito"
    description = (
        "Create an Amazon Cognito User Pool for user authentication and authorization. "
        "Handles sign-up, sign-in, MFA, and OAuth2/OIDC flows."
    )
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "pool_id": {"type": "string", "description": "Unique identifier (e.g., 'user_pool')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "allow_self_signup": {"type": "boolean", "description": "Allow users to self-register.", "default": True},
            "mfa_enabled": {"type": "boolean", "description": "Require MFA for login.", "default": False},
            "callback_urls": {"type": "string", "description": "Comma-separated allowed OAuth callback URLs.", "default": "http://localhost:3000/callback"},
        },
        "required": ["pool_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["pool_id"]
        label = params.get("label", pid)
        allow_self = params.get("allow_self_signup", True)
        mfa = params.get("mfa_enabled", False)
        callback_str = params.get("callback_urls", "http://localhost:3000/callback")
        callbacks = [u.strip() for u in callback_str.split(",")]

        configs = [
            {
                "service": "cognito-idp",
                "action": "create_user_pool",
                "params": {
                    "PoolName": f"__PROJECT__-{pid}",
                    "AdminCreateUserConfig": {"AllowAdminCreateUserOnly": not allow_self},
                    "Policies": {
                        "PasswordPolicy": {
                            "MinimumLength": 8,
                            "RequireLowercase": True,
                            "RequireNumbers": True,
                            "RequireSymbols": True,
                            "RequireUppercase": True,
                        },
                    },
                    "MfaConfiguration": "ON" if mfa else "OFF",
                    "AutoVerifiedAttributes": ["email"],
                    "Schema": [{"Name": "email", "AttributeDataType": "String", "Required": True, "Mutable": True}],
                    "UserPoolTags": {"Name": f"__PROJECT__-{pid}"},
                },
                "label": label,
                "resource_type": "aws_cognito_user_pool",
                "resource_id_path": "UserPool.Id",
                "delete_action": "delete_user_pool",
                "delete_params_key": "UserPoolId",
            },
            {
                "service": "cognito-idp",
                "action": "create_user_pool_client",
                "params": {
                    "UserPoolId": "__RESOLVE_PREV__",
                    "ClientName": f"__PROJECT__-{pid}-client",
                    "GenerateSecret": False,
                    "AllowedOAuthFlows": ["code"],
                    "AllowedOAuthFlowsUserPoolClient": True,
                    "AllowedOAuthScopes": ["email", "openid", "profile"],
                    "SupportedIdentityProviders": ["COGNITO"],
                    "CallbackURLs": callbacks,
                },
                "label": f"{label} — Client",
                "resource_type": "aws_cognito_user_pool_client",
                "resource_id_path": "UserPoolClient.ClientId",
                "is_support": True,
            },
        ]

        return ToolResult(
            node=ToolNode(id=pid, type="aws_cognito", label=label,
                          config=ToolNodeConfig(extra={"mfa": mfa, "self_signup": allow_self})),
            boto3_config={"cognito-idp": configs},
        )
