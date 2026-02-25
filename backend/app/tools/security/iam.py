"""Security tools: IAM, Cognito, KMS, Secrets Manager, WAF, Shield, ACM, GuardDuty."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateIAMRoleTool(BaseTool):
    name = "create_iam_role"
    description = "Create an AWS IAM role with trusted service principal and managed policies."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "role_id": {"type": "string"}, "label": {"type": "string"},
            "trusted_service": {"type": "string", "description": "AWS service principal (e.g., 'lambda.amazonaws.com').", "default": "lambda.amazonaws.com"},
            "managed_policy_arns": {"type": "array", "items": {"type": "string"}, "default": []},
        },
        "required": ["role_id", "label", "trusted_service"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        rid = params["role_id"]
        policies = params.get("managed_policy_arns", [])
        attachments = ""
        for i, arn in enumerate(policies):
            attachments += f'''
resource "aws_iam_role_policy_attachment" "{rid}_policy_{i}" {{
  role       = aws_iam_role.{rid}.name
  policy_arn = "{arn}"
}}
'''
        tf_code = f'''resource "aws_iam_role" "{rid}" {{
  name = "${{var.project_name}}-{rid}"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {{ Service = "{params.get('trusted_service', 'lambda.amazonaws.com')}" }}
    }}]
  }})
  tags = {{ Name = "${{var.project_name}}-{rid}" }}
}}
{attachments}'''
        return ToolResult(
            node=ToolNode(id=rid, type="aws_iam", label=params.get("label", rid), config=ToolNodeConfig()),
            terraform_code={"security.tf": tf_code},
        )


class CreateCognitoUserPoolTool(BaseTool):
    name = "create_cognito_user_pool"
    description = "Create an Amazon Cognito User Pool for user authentication and authorization."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "pool_id": {"type": "string"}, "label": {"type": "string"},
            "auto_verify": {"type": "array", "items": {"type": "string"}, "default": ["email"]},
            "password_min_length": {"type": "integer", "default": 8},
        },
        "required": ["pool_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        pid = params["pool_id"]
        auto_verify = ', '.join(f'"{v}"' for v in params.get("auto_verify", ["email"]))
        tf_code = f'''resource "aws_cognito_user_pool" "{pid}" {{
  name                     = "${{var.project_name}}-{pid}"
  auto_verified_attributes = [{auto_verify}]
  password_policy {{
    minimum_length = {params.get('password_min_length', 8)}
  }}
  tags = {{ Name = "${{var.project_name}}-{pid}" }}
}}

resource "aws_cognito_user_pool_client" "{pid}_client" {{
  name         = "${{var.project_name}}-{pid}-client"
  user_pool_id = aws_cognito_user_pool.{pid}.id
  explicit_auth_flows = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
}}
'''
        return ToolResult(
            node=ToolNode(id=pid, type="aws_cognito", label=params.get("label", pid), config=ToolNodeConfig()),
            terraform_code={"security.tf": tf_code},
        )


class CreateKMSKeyTool(BaseTool):
    name = "create_kms_key"
    description = "Create an AWS KMS encryption key for data encryption."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "key_id": {"type": "string"}, "label": {"type": "string"},
            "key_usage": {"type": "string", "default": "ENCRYPT_DECRYPT"},
            "rotation_enabled": {"type": "boolean", "default": True},
        },
        "required": ["key_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        kid = params["key_id"]
        tf_code = f'''resource "aws_kms_key" "{kid}" {{
  description             = "${{var.project_name}}-{kid}"
  key_usage               = "{params.get('key_usage', 'ENCRYPT_DECRYPT')}"
  enable_key_rotation     = {str(params.get('rotation_enabled', True)).lower()}
  tags = {{ Name = "${{var.project_name}}-{kid}" }}
}}

resource "aws_kms_alias" "{kid}_alias" {{
  name          = "alias/${{var.project_name}}-{kid}"
  target_key_id = aws_kms_key.{kid}.key_id
}}
'''
        return ToolResult(
            node=ToolNode(id=kid, type="aws_kms", label=params.get("label", kid), config=ToolNodeConfig()),
            terraform_code={"security.tf": tf_code},
        )


class CreateSecretTool(BaseTool):
    name = "create_secret"
    description = "Create an AWS Secrets Manager secret for storing sensitive configuration."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "secret_id": {"type": "string"}, "label": {"type": "string"},
            "description": {"type": "string", "default": "Managed secret"},
        },
        "required": ["secret_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["secret_id"]
        tf_code = f'''resource "aws_secretsmanager_secret" "{sid}" {{
  name        = "${{var.project_name}}-{sid}"
  description = "{params.get('description', 'Managed secret')}"
  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_secrets_manager", label=params.get("label", sid), config=ToolNodeConfig()),
            terraform_code={"security.tf": tf_code},
        )


class CreateWAFWebACLTool(BaseTool):
    name = "create_waf_web_acl"
    description = "Create an AWS WAF Web ACL for protecting web applications from common exploits."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "waf_id": {"type": "string"}, "label": {"type": "string"},
            "scope": {"type": "string", "description": "'REGIONAL' or 'CLOUDFRONT'.", "default": "REGIONAL"},
        },
        "required": ["waf_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        wid = params["waf_id"]
        tf_code = f'''resource "aws_wafv2_web_acl" "{wid}" {{
  name  = "${{var.project_name}}-{wid}"
  scope = "{params.get('scope', 'REGIONAL')}"
  default_action {{ allow {{}} }}
  visibility_config {{
    cloudwatch_metrics_enabled = true
    metric_name                = "${{var.project_name}}-{wid}"
    sampled_requests_enabled   = true
  }}
  tags = {{ Name = "${{var.project_name}}-{wid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=wid, type="aws_waf", label=params.get("label", wid), config=ToolNodeConfig()),
            terraform_code={"security.tf": tf_code},
        )


class CreateShieldProtectionTool(BaseTool):
    name = "create_shield_protection"
    description = "Enable AWS Shield Advanced protection for DDoS mitigation on a resource."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "shield_id": {"type": "string"}, "label": {"type": "string"},
            "resource_arn": {"type": "string", "description": "ARN of the resource to protect."},
        },
        "required": ["shield_id", "label", "resource_arn"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["shield_id"]
        tf_code = f'''resource "aws_shield_protection" "{sid}" {{
  name         = "${{var.project_name}}-{sid}"
  resource_arn = "{params['resource_arn']}"
  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_shield", label=params.get("label", sid), config=ToolNodeConfig()),
            terraform_code={"security.tf": tf_code},
        )


class CreateACMCertificateTool(BaseTool):
    name = "create_acm_certificate"
    description = "Request an AWS ACM SSL/TLS certificate for a domain."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "cert_id": {"type": "string"}, "label": {"type": "string"},
            "domain_name": {"type": "string", "description": "Primary domain (e.g., 'example.com')."},
            "validation_method": {"type": "string", "default": "DNS"},
        },
        "required": ["cert_id", "label", "domain_name"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cert_id"]
        tf_code = f'''resource "aws_acm_certificate" "{cid}" {{
  domain_name       = "{params['domain_name']}"
  validation_method = "{params.get('validation_method', 'DNS')}"
  tags = {{ Name = "${{var.project_name}}-{cid}" }}
  lifecycle {{ create_before_destroy = true }}
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_acm", label=params.get("label", cid), config=ToolNodeConfig()),
            terraform_code={"security.tf": tf_code},
        )


class CreateGuardDutyDetectorTool(BaseTool):
    name = "create_guardduty_detector"
    description = "Enable Amazon GuardDuty for intelligent threat detection."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "gd_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["gd_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        gid = params["gd_id"]
        tf_code = f'''resource "aws_guardduty_detector" "{gid}" {{
  enable = true
  tags = {{ Name = "${{var.project_name}}-{gid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=gid, type="aws_guardduty", label=params.get("label", gid), config=ToolNodeConfig()),
            terraform_code={"security.tf": tf_code},
        )
