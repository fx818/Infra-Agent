"""Create Route 53 tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateRoute53ZoneTool(BaseTool):
    name = "create_route53_zone"
    description = "Create an Amazon Route 53 hosted zone for DNS management."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "zone_id": {"type": "string"},
            "label": {"type": "string"},
            "domain_name": {"type": "string", "description": "Domain name (e.g., 'example.com')."},
            "is_private": {"type": "boolean", "default": False},
        },
        "required": ["zone_id", "label", "domain_name"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        zid = params["zone_id"]
        domain = params["domain_name"]
        tf_code = f'''resource "aws_route53_zone" "{zid}" {{
  name = "{domain}"
  tags = {{ Name = "${{var.project_name}}-{zid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=zid, type="aws_route53", label=params.get("label", zid),
                          config=ToolNodeConfig(extra={"domain": domain})),
            terraform_code={"networking.tf": tf_code},
        )
