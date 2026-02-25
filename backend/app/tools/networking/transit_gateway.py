"""AWS Transit Gateway tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateTransitGatewayTool(BaseTool):
    name = "create_transit_gateway"
    description = (
        "Create an AWS Transit Gateway to connect multiple VPCs and on-premises networks "
        "through a central hub. Ideal for hub-and-spoke network architectures."
    )
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "tgw_id": {"type": "string", "description": "Unique identifier (e.g., 'main_tgw')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "description": {"type": "string", "description": "Transit gateway description.", "default": "Transit Gateway"},
            "amazon_side_asn": {"type": "integer", "description": "BGP ASN for the Amazon side.", "default": 64512},
        },
        "required": ["tgw_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["tgw_id"]
        asn = params.get("amazon_side_asn", 64512)
        desc = params.get("description", "Transit Gateway")

        tf_code = f'''
resource "aws_ec2_transit_gateway" "{tid}" {{
  description                     = "{desc}"
  amazon_side_asn                 = {asn}
  auto_accept_shared_attachments  = "enable"
  default_route_table_association = "enable"
  default_route_table_propagation = "enable"
  tags = {{ Name = "${{var.project_name}}-tgw" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=tid, type="aws_transit_gateway", label=params.get("label", tid),
                          config=ToolNodeConfig(extra={"asn": asn})),
            terraform_code={"networking.tf": tf_code},
        )
