"""AWS NAT Gateway tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateNatGatewayTool(BaseTool):
    name = "create_nat_gateway"
    description = (
        "Create an AWS NAT Gateway to allow instances in private subnets to "
        "connect to the internet while preventing inbound connections."
    )
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "nat_id": {"type": "string", "description": "Unique identifier (e.g., 'main_nat')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "vpc_id": {"type": "string", "description": "The VPC ID this NAT gateway belongs to."},
            "subnet_id": {"type": "string", "description": "Public subnet ID to place the NAT GW in.", "default": ""},
        },
        "required": ["nat_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        nid = params["nat_id"]
        label = params.get("label", nid)
        configs = [
            {
                "service": "ec2",
                "action": "allocate_address",
                "params": {
                    "Domain": "vpc",
                    "TagSpecifications": [{"ResourceType": "elastic-ip", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{nid}-eip"}]}],
                },
                "label": f"{label} — EIP",
                "resource_type": "aws_eip",
                "resource_id_path": "AllocationId",
                "delete_action": "release_address",
                "delete_params_key": "AllocationId",
            },
            {
                "service": "ec2",
                "action": "create_nat_gateway",
                "params": {
                    "AllocationId": "__RESOLVE_PREV__",
                    "SubnetId": "__FIRST_PUBLIC_SUBNET__",
                    "TagSpecifications": [{"ResourceType": "natgateway", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{nid}"}]}],
                },
                "label": label,
                "resource_type": "aws_nat_gateway",
                "resource_id_path": "NatGateway.NatGatewayId",
                "delete_action": "delete_nat_gateway",
                "delete_params_key": "NatGatewayId",
                "waiter": "nat_gateway_available",
            },
        ]
        return ToolResult(
            node=ToolNode(id=nid, type="aws_nat_gateway", label=label,
                          config=ToolNodeConfig(extra={"vpc_id": params.get("vpc_id", "")})),
            boto3_config={"ec2": configs},
        )
