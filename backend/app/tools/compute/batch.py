"""Create AWS Batch Job tool — provisions via boto3."""
import json
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateBatchJobTool(BaseTool):
    name = "create_batch_job"
    description = "Create an AWS Batch compute environment and job queue for batch processing workloads."
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "batch_id": {"type": "string", "description": "Unique identifier."},
            "label": {"type": "string"},
            "compute_type": {"type": "string", "description": "'FARGATE' or 'EC2'.", "default": "FARGATE"},
            "max_vcpus": {"type": "integer", "default": 16},
        },
        "required": ["batch_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        bid = params["batch_id"]
        label = params.get("label", bid)
        ctype = params.get("compute_type", "FARGATE")
        vcpus = params.get("max_vcpus", 16)

        configs = [
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{bid}-batch-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow", "Principal": {"Service": "batch.amazonaws.com"}}],
                    }),
                },
                "label": f"{label} — Batch Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{bid}-batch-role"},
            },
            {
                "service": "iam",
                "action": "attach_role_policy",
                "params": {"RoleName": f"__PROJECT__-{bid}-batch-role", "PolicyArn": "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"},
                "label": f"{label} — Batch Policy", "resource_type": "aws_iam_policy_attachment", "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {"RoleName": f"__PROJECT__-{bid}-batch-role", "PolicyArn": "arn:aws:iam::aws:policy/service-role/AWSBatchServiceRole"},
            },
            {
                "service": "batch",
                "action": "create_compute_environment",
                "params": {
                    "computeEnvironmentName": f"__PROJECT__-{bid}",
                    "type": "MANAGED",
                    "computeResources": {
                        "type": ctype,
                        "maxvCpus": vcpus,
                        "subnets": "__DEFAULT_SUBNETS__",
                        "securityGroupIds": "__DEFAULT_SG__",
                    },
                    "serviceRole": f"__RESOLVE__:iam:create_role:{bid}-batch-role:Role.Arn",
                },
                "label": f"{label} — Compute Env",
                "resource_type": "aws_batch_compute_environment",
                "resource_id_path": "computeEnvironmentArn",
                "delete_action": "delete_compute_environment",
                "delete_params": {"computeEnvironment": f"__PROJECT__-{bid}"},
            },
            {
                "service": "batch",
                "action": "create_job_queue",
                "params": {
                    "jobQueueName": f"__PROJECT__-{bid}-queue",
                    "state": "ENABLED",
                    "priority": 1,
                    "computeEnvironmentOrder": [{"order": 1, "computeEnvironment": f"__PROJECT__-{bid}"}],
                },
                "label": f"{label} — Job Queue",
                "resource_type": "aws_batch_job_queue",
                "resource_id_path": "jobQueueArn",
                "delete_action": "delete_job_queue",
                "delete_params": {"jobQueue": f"__PROJECT__-{bid}-queue"},
            },
        ]

        return ToolResult(
            node=ToolNode(id=bid, type="aws_batch", label=label,
                          config=ToolNodeConfig(extra={"compute_type": ctype, "max_vcpus": vcpus})),
            boto3_config={"batch": configs},
        )
