"""Create Security Group tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateSecurityGroupTool(BaseTool):
    name = "create_security_group"
    description = "Create an AWS Security Group with ingress/egress rules for controlling network traffic."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "sg_id": {"type": "string"},
            "label": {"type": "string"},
            "vpc_id": {"type": "string", "description": "VPC resource ID."},
            "ingress_rules": {
                "type": "array",
                "description": "List of ingress rules.",
                "items": {
                    "type": "object",
                    "properties": {
                        "from_port": {"type": "integer"},
                        "to_port": {"type": "integer"},
                        "protocol": {"type": "string", "default": "tcp"},
                        "cidr_blocks": {"type": "array", "items": {"type": "string"}, "default": ["0.0.0.0/0"]},
                        "description": {"type": "string", "default": ""},
                    },
                },
                "default": [{"from_port": 443, "to_port": 443, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]}],
            },
        },
        "required": ["sg_id", "label", "vpc_id"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["sg_id"]
        label = params.get("label", sid)
        vpc = params["vpc_id"]
        rules = params.get("ingress_rules", [{"from_port": 443, "to_port": 443, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]}])

        # Build ingress IP permissions
        ip_permissions = []
        for r in rules:
            ip_permissions.append({
                "IpProtocol": r.get("protocol", "tcp"),
                "FromPort": r.get("from_port", 443),
                "ToPort": r.get("to_port", 443),
                "IpRanges": [{"CidrIp": c, "Description": r.get("description", "")} for c in r.get("cidr_blocks", ["0.0.0.0/0"])],
            })

        configs = [
            {
                "service": "ec2",
                "action": "create_security_group",
                "params": {
                    "GroupName": f"__PROJECT__-{sid}",
                    "Description": label,
                    "VpcId": f"__RESOLVE_REF__:{vpc}",
                    "TagSpecifications": [{"ResourceType": "security-group", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}]}],
                },
                "label": label,
                "resource_type": "aws_security_group",
                "resource_id_path": "GroupId",
                "delete_action": "delete_security_group",
                "delete_params_key": "GroupId",
            },
            {
                "service": "ec2",
                "action": "authorize_security_group_ingress",
                "params": {
                    "GroupId": "__RESOLVE_PREV__",
                    "IpPermissions": ip_permissions,
                },
                "label": f"{label} — Ingress Rules",
                "resource_type": "aws_sg_rules",
                "is_support": True,
            },
        ]

        return ToolResult(
            node=ToolNode(id=sid, type="aws_security_group", label=label,
                          config=ToolNodeConfig(extra={"vpc_id": vpc, "rules_count": len(rules)})),
            boto3_config={"ec2": configs},
            edges=[{"from": vpc, "to": sid, "label": "contains"}],
        )
