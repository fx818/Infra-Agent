"""AWS NAT Gateway tool."""
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
        vpc_ref = params.get("vpc_id", "main_vpc")

        tf_code = f'''
resource "aws_eip" "{nid}_eip" {{
  domain = "vpc"
  tags   = {{ Name = "${{var.project_name}}-nat-eip" }}
}}

resource "aws_nat_gateway" "{nid}" {{
  allocation_id = aws_eip.{nid}_eip.id
  subnet_id     = aws_subnet.{vpc_ref}_public_0.id
  depends_on    = [aws_internet_gateway.{vpc_ref}_igw]
  tags          = {{ Name = "${{var.project_name}}-nat" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=nid, type="aws_nat_gateway", label=params.get("label", nid),
                          config=ToolNodeConfig(extra={"vpc_id": vpc_ref})),
            terraform_code={"networking.tf": tf_code},
        )
