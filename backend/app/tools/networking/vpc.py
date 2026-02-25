"""Create VPC tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateVPCTool(BaseTool):
    name = "create_vpc"
    description = (
        "Create an Amazon VPC with public/private subnets, internet gateway, "
        "and route tables. Foundation for most AWS architectures requiring "
        "network isolation."
    )
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "vpc_id": {"type": "string", "description": "Unique identifier (e.g., 'main_vpc')."},
            "label": {"type": "string"},
            "cidr_block": {"type": "string", "description": "VPC CIDR block.", "default": "10.0.0.0/16"},
            "availability_zones": {"type": "integer", "description": "Number of AZs (2 or 3).", "default": 2},
            "enable_nat": {"type": "boolean", "description": "Create NAT gateway for private subnets.", "default": True},
        },
        "required": ["vpc_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        vid = params["vpc_id"]
        cidr = params.get("cidr_block", "10.0.0.0/16")
        azs = params.get("availability_zones", 2)
        nat = params.get("enable_nat", True)

        subnet_blocks = []
        for i in range(azs):
            subnet_blocks.append(f'''
resource "aws_subnet" "{vid}_public_{i}" {{
  vpc_id            = aws_vpc.{vid}.id
  cidr_block        = cidrsubnet(aws_vpc.{vid}.cidr_block, 8, {i})
  availability_zone = data.aws_availability_zones.available.names[{i}]
  map_public_ip_on_launch = true
  tags = {{ Name = "${{var.project_name}}-public-{i}" }}
}}

resource "aws_subnet" "{vid}_private_{i}" {{
  vpc_id            = aws_vpc.{vid}.id
  cidr_block        = cidrsubnet(aws_vpc.{vid}.cidr_block, 8, {i + 10})
  availability_zone = data.aws_availability_zones.available.names[{i}]
  tags = {{ Name = "${{var.project_name}}-private-{i}" }}
}}''')

        nat_block = ""
        if nat:
            nat_block = f'''
resource "aws_eip" "{vid}_nat_eip" {{
  domain = "vpc"
  tags = {{ Name = "${{var.project_name}}-nat-eip" }}
}}

resource "aws_nat_gateway" "{vid}_nat" {{
  allocation_id = aws_eip.{vid}_nat_eip.id
  subnet_id     = aws_subnet.{vid}_public_0.id
  tags = {{ Name = "${{var.project_name}}-nat" }}
}}

resource "aws_route_table" "{vid}_private" {{
  vpc_id = aws_vpc.{vid}.id
  route {{
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.{vid}_nat.id
  }}
  tags = {{ Name = "${{var.project_name}}-private-rt" }}
}}
'''

        tf_code = f'''data "aws_availability_zones" "available" {{
  state = "available"
}}

resource "aws_vpc" "{vid}" {{
  cidr_block           = "{cidr}"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = {{ Name = "${{var.project_name}}-vpc" }}
}}

resource "aws_internet_gateway" "{vid}_igw" {{
  vpc_id = aws_vpc.{vid}.id
  tags = {{ Name = "${{var.project_name}}-igw" }}
}}

resource "aws_route_table" "{vid}_public" {{
  vpc_id = aws_vpc.{vid}.id
  route {{
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.{vid}_igw.id
  }}
  tags = {{ Name = "${{var.project_name}}-public-rt" }}
}}
{"".join(subnet_blocks)}
{nat_block}
'''
        return ToolResult(
            node=ToolNode(id=vid, type="aws_vpc", label=params.get("label", vid),
                          config=ToolNodeConfig(extra={"cidr_block": cidr, "azs": azs, "nat": nat})),
            terraform_code={"networking.tf": tf_code},
        )
