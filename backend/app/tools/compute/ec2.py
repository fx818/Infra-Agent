"""Create EC2 Instance tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateEC2InstanceTool(BaseTool):
    name = "create_ec2_instance"
    description = (
        "Provision an Amazon EC2 virtual server instance. Supports configurable "
        "instance type, AMI, key pair, security groups, and storage. Use for "
        "traditional server workloads, web servers, application servers, etc."
    )
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "instance_id": {
                "type": "string",
                "description": "Unique identifier for this instance in the architecture (e.g., 'web_server', 'app_server').",
            },
            "label": {
                "type": "string",
                "description": "Human-readable label (e.g., 'Web Server').",
            },
            "instance_type": {
                "type": "string",
                "description": "EC2 instance type (e.g., 't3.micro', 't3.medium', 'm5.large', 'c5.xlarge').",
                "default": "t3.micro",
            },
            "ami": {
                "type": "string",
                "description": "AMI ID or reference (e.g., 'amazon-linux-2', 'ubuntu-22.04'). Use 'amazon-linux-2' for default.",
                "default": "amazon-linux-2",
            },
            "storage_gb": {
                "type": "integer",
                "description": "Root EBS volume size in GB.",
                "default": 20,
            },
            "associate_public_ip": {
                "type": "boolean",
                "description": "Whether to assign a public IP address.",
                "default": True,
            },
            "key_pair_name": {
                "type": "string",
                "description": "SSH key pair name for access. Leave empty to skip.",
                "default": "",
            },
        },
        "required": ["instance_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        iid = params["instance_id"]
        label = params.get("label", iid)
        instance_type = params.get("instance_type", "t3.micro")
        ami = params.get("ami", "amazon-linux-2")
        storage_gb = params.get("storage_gb", 20)
        public_ip = params.get("associate_public_ip", True)

        ami_lookup = {
            "amazon-linux-2": 'data.aws_ami.amazon_linux_2.id',
            "ubuntu-22.04": 'data.aws_ami.ubuntu_22_04.id',
        }
        ami_ref = ami_lookup.get(ami, f'"{ami}"')

        tf_code = f'''resource "aws_instance" "{iid}" {{
  ami           = {ami_ref}
  instance_type = "{instance_type}"

  root_block_device {{
    volume_size = {storage_gb}
    volume_type = "gp3"
  }}

  associate_public_ip_address = {str(public_ip).lower()}

  tags = {{
    Name = "${{var.project_name}}-{iid}"
  }}
}}
'''

        if ami in ami_lookup:
            data_block = ''
            if ami == "amazon-linux-2":
                data_block = '''data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}
'''
            elif ami == "ubuntu-22.04":
                data_block = '''data "aws_ami" "ubuntu_22_04" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}
'''
            tf_code = data_block + "\n" + tf_code

        return ToolResult(
            node=ToolNode(
                id=iid,
                type="aws_ec2",
                label=label,
                config=ToolNodeConfig(
                    instance_type=instance_type,
                    extra={"ami": ami, "storage_gb": storage_gb},
                ),
            ),
            terraform_code={"compute.tf": tf_code},
        )
