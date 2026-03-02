"""AWS Transit Gateway tool — provisions via boto3."""
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
        label = params.get("label", tid)
        asn = params.get("amazon_side_asn", 64512)
        desc = params.get("description", "Transit Gateway")

        configs = [{
            "service": "ec2",
            "action": "create_transit_gateway",
            "params": {
                "Description": desc,
                "Options": {
                    "AmazonSideAsn": asn,
                    "AutoAcceptSharedAttachments": "enable",
                    "DefaultRouteTableAssociation": "enable",
                    "DefaultRouteTablePropagation": "enable",
                },
                "TagSpecifications": [{"ResourceType": "transit-gateway", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-tgw"}]}],
            },
            "label": label,
            "resource_type": "aws_transit_gateway",
            "resource_id_path": "TransitGateway.TransitGatewayId",
            "delete_action": "delete_transit_gateway",
            "delete_params_key": "TransitGatewayId",
        }]

        return ToolResult(
            node=ToolNode(id=tid, type="aws_transit_gateway", label=label,
                          config=ToolNodeConfig(extra={"asn": asn})),
            boto3_config={"ec2": configs},
        )
