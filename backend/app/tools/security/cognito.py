"""AWS Cognito User Pool tool."""
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
        allow_self = params.get("allow_self_signup", True)
        mfa = params.get("mfa_enabled", False)
        callback_str = params.get("callback_urls", "http://localhost:3000/callback")
        callbacks = [u.strip() for u in callback_str.split(",")]
        callback_list = "\n    ".join(f'"{cb}",' for cb in callbacks)

        mfa_config = '"ON"' if mfa else '"OFF"'
        admin_only = "false" if allow_self else "true"

        tf_code = f'''
resource "aws_cognito_user_pool" "{pid}" {{
  name = "${{var.project_name}}-{pid}"

  admin_create_user_config {{
    allow_admin_create_user_only = {admin_only}
  }}

  password_policy {{
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }}

  mfa_configuration = {mfa_config}

  auto_verified_attributes = ["email"]

  schema {{
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true
  }}

  tags = {{ Name = "${{var.project_name}}-{pid}" }}
}}

resource "aws_cognito_user_pool_client" "{pid}_client" {{
  name         = "${{var.project_name}}-{pid}-client"
  user_pool_id = aws_cognito_user_pool.{pid}.id

  generate_secret                      = false
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["email", "openid", "profile"]
  supported_identity_providers         = ["COGNITO"]

  callback_urls = [
    {callback_list}
  ]
}}
'''
        return ToolResult(
            node=ToolNode(id=pid, type="aws_cognito", label=params.get("label", pid),
                          config=ToolNodeConfig(extra={"mfa": mfa, "self_signup": allow_self})),
            terraform_code={"security.tf": tf_code},
        )
