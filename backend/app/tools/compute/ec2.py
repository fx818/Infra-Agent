"""Create EC2 Instance tool — provisions via boto3."""
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

        # For well-known AMI names, we'll resolve at deploy time via SSM
        ami_ssm_map = {
            "amazon-linux-2": "/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2",
            "ubuntu-22.04": "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id",
        }
        ssm_path = ami_ssm_map.get(ami)

        configs = []

        # If using a well-known AMI, resolve via SSM first
        if ssm_path:
            configs.append({
                "service": "ssm",
                "action": "get_parameter",
                "params": {"Name": ssm_path},
                "resource_id_path": "Parameter.Value",
                "label": f"{label} — AMI Lookup",
                "resource_type": "ami_lookup",
                "is_lookup": True,
            })

        configs.append({
            "service": "ec2",
            "action": "run_instances",
            "params": {
                "ImageId": ami if ami not in ami_ssm_map else "__SSM_RESOLVED__",
                "InstanceType": instance_type,
                "MinCount": 1,
                "MaxCount": 1,
                "BlockDeviceMappings": [{
                    "DeviceName": "/dev/xvda",
                    "Ebs": {"VolumeSize": storage_gb, "VolumeType": "gp3"},
                }],
                "TagSpecifications": [{
                    "ResourceType": "instance",
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{iid}"}],
                }],
            },
            "label": label,
            "resource_type": "aws_instance",
            "resource_id_path": "Instances[0].InstanceId",
            "delete_action": "terminate_instances",
            "delete_params_key": "InstanceIds",
            "waiter": "instance_running",
        })

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
            boto3_config={"ec2": configs},
        )
