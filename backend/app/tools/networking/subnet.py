"""Create Subnet tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateSubnetTool(BaseTool):
    name = "create_subnet"
    description = "Create an additional subnet in an existing VPC. Use when you need subnets beyond what create_vpc provides."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "subnet_id": {"type": "string"},
            "label": {"type": "string"},
            "vpc_id": {"type": "string", "description": "VPC resource ID this subnet belongs to."},
            "cidr_block": {"type": "string", "default": "10.0.100.0/24"},
            "is_public": {"type": "boolean", "default": False},
            "az_index": {"type": "integer", "description": "AZ index (0, 1, 2).", "default": 0},
        },
        "required": ["subnet_id", "label", "vpc_id", "cidr_block"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["subnet_id"]
        label = params.get("label", sid)
        cidr = params["cidr_block"]
        public = params.get("is_public", False)
        az_idx = params.get("az_index", 0)
        configs = [{
            "service": "ec2",
            "action": "create_subnet",
            "params": {
                "VpcId": f"__RESOLVE_REF__:{params['vpc_id']}",
                "CidrBlock": cidr,
                "AvailabilityZone": f"__REGION__{'abcdef'[az_idx]}",
                "MapPublicIpOnLaunch": public,
                "TagSpecifications": [{"ResourceType": "subnet", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}]}],
            },
            "label": label,
            "resource_type": "aws_subnet",
            "resource_id_path": "Subnet.SubnetId",
            "delete_action": "delete_subnet",
            "delete_params_key": "SubnetId",
        }]
        return ToolResult(
            node=ToolNode(id=sid, type="aws_subnet", label=label,
                          config=ToolNodeConfig(extra={"cidr_block": cidr, "is_public": public})),
            boto3_config={"ec2": configs},
            edges=[{"from": params["vpc_id"], "to": sid, "label": "contains"}],
        )
