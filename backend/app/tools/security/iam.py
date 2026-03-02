"""Security tools: IAM Role, KMS, WAF, Shield, ACM, GuardDuty — provisions via boto3."""
import json
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateIAMRoleTool(BaseTool):
    name = "create_iam_role"
    description = "Create an AWS IAM role with policies for service-to-service access."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "role_id": {"type": "string"}, "label": {"type": "string"},
            "service_principal": {"type": "string", "description": "AWS service (e.g., 'lambda.amazonaws.com').", "default": "lambda.amazonaws.com"},
            "managed_policies": {"type": "array", "items": {"type": "string"}, "default": []},
        },
        "required": ["role_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        rid = params["role_id"]
        label = params.get("label", rid)
        service = params.get("service_principal", "lambda.amazonaws.com")
        policies = params.get("managed_policies", [])

        configs = [{
            "service": "iam",
            "action": "create_role",
            "params": {
                "RoleName": f"__PROJECT__-{rid}",
                "AssumeRolePolicyDocument": json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{"Effect": "Allow", "Principal": {"Service": service}, "Action": "sts:AssumeRole"}],
                }),
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rid}"}],
            },
            "label": label,
            "resource_type": "aws_iam_role",
            "resource_id_path": "Role.Arn",
            "delete_action": "delete_role",
            "delete_params": {"RoleName": f"__PROJECT__-{rid}"},
        }]

        for policy_arn in policies:
            configs.append({
                "service": "iam",
                "action": "attach_role_policy",
                "params": {"RoleName": f"__PROJECT__-{rid}", "PolicyArn": policy_arn},
                "label": f"{label} — Policy",
                "resource_type": "aws_iam_policy_attachment",
                "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {"RoleName": f"__PROJECT__-{rid}", "PolicyArn": policy_arn},
            })

        return ToolResult(
            node=ToolNode(id=rid, type="aws_iam_role", label=label,
                          config=ToolNodeConfig(extra={"service_principal": service})),
            boto3_config={"iam": configs},
        )


class CreateKMSKeyTool(BaseTool):
    name = "create_kms_key"
    description = "Create an AWS KMS key for encryption."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "key_id": {"type": "string"}, "label": {"type": "string"},
            "description": {"type": "string", "default": "Application encryption key"},
            "enable_rotation": {"type": "boolean", "default": True},
        },
        "required": ["key_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        kid = params["key_id"]
        label = params.get("label", kid)
        configs = [{
            "service": "kms",
            "action": "create_key",
            "params": {
                "Description": params.get("description", "Application encryption key"),
                "Tags": [{"TagKey": "Name", "TagValue": f"__PROJECT__-{kid}"}],
            },
            "label": label,
            "resource_type": "aws_kms_key",
            "resource_id_path": "KeyMetadata.KeyId",
            "delete_action": "schedule_key_deletion",
            "delete_params_key": "KeyId",
        }]
        if params.get("enable_rotation", True):
            configs.append({
                "service": "kms",
                "action": "enable_key_rotation",
                "params": {"KeyId": "__RESOLVE_PREV__"},
                "label": f"{label} — Rotation",
                "resource_type": "aws_kms_rotation",
                "is_support": True,
            })
        return ToolResult(
            node=ToolNode(id=kid, type="aws_kms", label=label, config=ToolNodeConfig()),
            boto3_config={"kms": configs},
        )


class CreateWAFACLTool(BaseTool):
    name = "create_waf_acl"
    description = "Create an AWS WAFv2 Web ACL for protecting web applications."
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
        label = params.get("label", wid)
        scope = params.get("scope", "REGIONAL")
        configs = [{
            "service": "wafv2",
            "action": "create_web_acl",
            "params": {
                "Name": f"__PROJECT__-{wid}",
                "Scope": scope,
                "DefaultAction": {"Allow": {}},
                "VisibilityConfig": {
                    "SampledRequestsEnabled": True,
                    "CloudWatchMetricsEnabled": True,
                    "MetricName": f"__PROJECT__-{wid}",
                },
                "Rules": [],
            },
            "label": label,
            "resource_type": "aws_wafv2_web_acl",
            "resource_id_path": "Summary.Id",
            "delete_action": "delete_web_acl",
            "delete_params": {"Name": f"__PROJECT__-{wid}", "Scope": scope, "Id": "__RESOURCE_ID__", "LockToken": "__LOCK_TOKEN__"},
        }]
        return ToolResult(
            node=ToolNode(id=wid, type="aws_waf", label=label, config=ToolNodeConfig()),
            boto3_config={"wafv2": configs},
        )


class CreateShieldProtectionTool(BaseTool):
    name = "create_shield_protection"
    description = "Enable AWS Shield Advanced protection for a resource."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "shield_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["shield_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["shield_id"]
        label = params.get("label", sid)
        configs = [{
            "service": "shield",
            "action": "create_subscription",
            "params": {},
            "label": label,
            "resource_type": "aws_shield",
            "is_lookup": True,
        }]
        return ToolResult(
            node=ToolNode(id=sid, type="aws_shield", label=label, config=ToolNodeConfig()),
            boto3_config={"shield": configs},
        )


class CreateACMCertificateTool(BaseTool):
    name = "create_acm_certificate"
    description = "Request an AWS ACM SSL/TLS certificate."
    category = "security"
    parameters = {
        "type": "object",
        "properties": {
            "cert_id": {"type": "string"}, "label": {"type": "string"},
            "domain_name": {"type": "string", "description": "Primary domain name."},
            "validation_method": {"type": "string", "default": "DNS"},
        },
        "required": ["cert_id", "label", "domain_name"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["cert_id"]
        label = params.get("label", cid)
        domain = params["domain_name"]
        configs = [{
            "service": "acm",
            "action": "request_certificate",
            "params": {
                "DomainName": domain,
                "ValidationMethod": params.get("validation_method", "DNS"),
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{cid}"}],
            },
            "label": label,
            "resource_type": "aws_acm_certificate",
            "resource_id_path": "CertificateArn",
            "delete_action": "delete_certificate",
            "delete_params_key": "CertificateArn",
        }]
        return ToolResult(
            node=ToolNode(id=cid, type="aws_acm", label=label,
                          config=ToolNodeConfig(extra={"domain": domain})),
            boto3_config={"acm": configs},
        )


class CreateGuardDutyDetectorTool(BaseTool):
    name = "create_guardduty_detector"
    description = "Enable Amazon GuardDuty for threat detection."
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
        label = params.get("label", gid)
        configs = [{
            "service": "guardduty",
            "action": "create_detector",
            "params": {"Enable": True, "Tags": {"Name": f"__PROJECT__-{gid}"}},
            "label": label,
            "resource_type": "aws_guardduty",
            "resource_id_path": "DetectorId",
            "delete_action": "delete_detector",
            "delete_params_key": "DetectorId",
        }]
        return ToolResult(
            node=ToolNode(id=gid, type="aws_guardduty", label=label, config=ToolNodeConfig()),
            boto3_config={"guardduty": configs},
        )
