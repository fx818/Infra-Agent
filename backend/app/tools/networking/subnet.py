"""Create Subnet tool."""
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
        vpc = params["vpc_id"]
        cidr = params["cidr_block"]
        public = params.get("is_public", False)
        tf_code = f'''resource "aws_subnet" "{sid}" {{
  vpc_id                  = aws_vpc.{vpc}.id
  cidr_block              = "{cidr}"
  availability_zone       = data.aws_availability_zones.available.names[{params.get('az_index', 0)}]
  map_public_ip_on_launch = {str(public).lower()}
  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_subnet", label=params.get("label", sid),
                          config=ToolNodeConfig(extra={"cidr_block": cidr, "is_public": public})),
            terraform_code={"networking.tf": tf_code},
            edges=[{"from": vpc, "to": sid, "label": "contains"}],
        )
