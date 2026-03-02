"""Create VPC tool — provisions via boto3."""
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
        label = params.get("label", vid)
        cidr = params.get("cidr_block", "10.0.0.0/16")
        azs = params.get("availability_zones", 2)
        nat = params.get("enable_nat", True)

        configs = [
            {
                "service": "ec2",
                "action": "create_vpc",
                "params": {
                    "CidrBlock": cidr,
                    "TagSpecifications": [{"ResourceType": "vpc", "Tags": [
                        {"Key": "Name", "Value": f"__PROJECT__-vpc"},
                        {"Key": "ManagedBy", "Value": "nl2i"},
                    ]}],
                },
                "label": f"{label} — VPC",
                "resource_type": "aws_vpc",
                "resource_id_path": "Vpc.VpcId",
                "delete_action": "delete_vpc",
                "delete_params_key": "VpcId",
                "post_create": [
                    {"action": "modify_vpc_attribute", "params_template": {"VpcId": "__RESOURCE_ID__", "EnableDnsSupport": {"Value": True}}},
                    {"action": "modify_vpc_attribute", "params_template": {"VpcId": "__RESOURCE_ID__", "EnableDnsHostnames": {"Value": True}}},
                ],
            },
            {
                "service": "ec2",
                "action": "create_internet_gateway",
                "params": {
                    "TagSpecifications": [{"ResourceType": "internet-gateway", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-igw"}]}],
                },
                "label": f"{label} — Internet Gateway",
                "resource_type": "aws_internet_gateway",
                "resource_id_path": "InternetGateway.InternetGatewayId",
                "delete_action": "delete_internet_gateway",
                "delete_params_key": "InternetGatewayId",
                "post_create": [
                    {"action": "attach_internet_gateway", "params_template": {"InternetGatewayId": "__RESOURCE_ID__", "VpcId": "__VPC_ID__"}},
                ],
            },
        ]

        # Add subnets for each AZ
        for i in range(azs):
            # Calculate CIDR subnets (simple /24 allocation)
            public_cidr = f"10.0.{i}.0/24"
            private_cidr = f"10.0.{i + 10}.0/24"

            configs.append({
                "service": "ec2",
                "action": "create_subnet",
                "params": {
                    "VpcId": "__VPC_ID__",
                    "CidrBlock": public_cidr,
                    "AvailabilityZone": f"__REGION__{'abcdef'[i]}",
                    "MapPublicIpOnLaunch": True,
                    "TagSpecifications": [{"ResourceType": "subnet", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-public-{i}"}]}],
                },
                "label": f"{label} — Public Subnet {i}",
                "resource_type": "aws_subnet",
                "resource_id_path": "Subnet.SubnetId",
                "delete_action": "delete_subnet",
                "delete_params_key": "SubnetId",
            })

            configs.append({
                "service": "ec2",
                "action": "create_subnet",
                "params": {
                    "VpcId": "__VPC_ID__",
                    "CidrBlock": private_cidr,
                    "AvailabilityZone": f"__REGION__{'abcdef'[i]}",
                    "TagSpecifications": [{"ResourceType": "subnet", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-private-{i}"}]}],
                },
                "label": f"{label} — Private Subnet {i}",
                "resource_type": "aws_subnet",
                "resource_id_path": "Subnet.SubnetId",
                "delete_action": "delete_subnet",
                "delete_params_key": "SubnetId",
            })

        if nat:
            configs.extend([
                {
                    "service": "ec2",
                    "action": "allocate_address",
                    "params": {
                        "Domain": "vpc",
                        "TagSpecifications": [{"ResourceType": "elastic-ip", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-nat-eip"}]}],
                    },
                    "label": f"{label} — NAT EIP",
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
                        "TagSpecifications": [{"ResourceType": "natgateway", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-nat"}]}],
                    },
                    "label": f"{label} — NAT Gateway",
                    "resource_type": "aws_nat_gateway",
                    "resource_id_path": "NatGateway.NatGatewayId",
                    "delete_action": "delete_nat_gateway",
                    "delete_params_key": "NatGatewayId",
                    "waiter": "nat_gateway_available",
                },
            ])

        return ToolResult(
            node=ToolNode(id=vid, type="aws_vpc", label=label,
                          config=ToolNodeConfig(extra={"cidr_block": cidr, "azs": azs, "nat": nat})),
            boto3_config={"ec2": configs},
        )
