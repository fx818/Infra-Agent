"""Create Security Group tool."""
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
        vpc = params["vpc_id"]
        rules = params.get("ingress_rules", [{"from_port": 443, "to_port": 443, "protocol": "tcp", "cidr_blocks": ["0.0.0.0/0"]}])
        ingress_blocks = ""
        for r in rules:
            cidrs = ', '.join(f'"{c}"' for c in r.get("cidr_blocks", ["0.0.0.0/0"]))
            ingress_blocks += f'''
  ingress {{
    from_port   = {r.get('from_port', 443)}
    to_port     = {r.get('to_port', 443)}
    protocol    = "{r.get('protocol', 'tcp')}"
    cidr_blocks = [{cidrs}]
    description = "{r.get('description', '')}"
  }}
'''
        tf_code = f'''resource "aws_security_group" "{sid}" {{
  name        = "${{var.project_name}}-{sid}"
  description = "{params.get('label', sid)}"
  vpc_id      = aws_vpc.{vpc}.id
{ingress_blocks}
  egress {{
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }}

  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_security_group", label=params.get("label", sid),
                          config=ToolNodeConfig(extra={"vpc_id": vpc, "rules_count": len(rules)})),
            terraform_code={"networking.tf": tf_code},
            edges=[{"from": vpc, "to": sid, "label": "contains"}],
        )
