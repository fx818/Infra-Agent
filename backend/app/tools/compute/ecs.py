"""Create ECS Service tool — provisions via boto3."""
import json
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


# Fargate valid CPU → memory ranges (MiB)
_FARGATE_VALID = {
    256:  [512, 1024, 2048],
    512:  list(range(1024, 4097, 1024)),
    1024: list(range(2048, 8193, 1024)),
    2048: list(range(4096, 16385, 1024)),
    4096: list(range(8192, 30721, 1024)),
    8192: list(range(16384, 61441, 4096)),
    16384: list(range(32768, 122881, 8192)),
}


def _valid_fargate_combo(cpu: int, memory: int) -> tuple[int, int]:
    """Snap to the nearest valid Fargate CPU/memory pair."""
    valid_cpus = sorted(_FARGATE_VALID.keys())
    actual_cpu = min(valid_cpus, key=lambda c: abs(c - cpu))
    valid_mems = _FARGATE_VALID[actual_cpu]
    actual_mem = min(valid_mems, key=lambda m: abs(m - memory))
    if actual_mem < valid_mems[0]:
        actual_mem = valid_mems[0]
    return actual_cpu, actual_mem


class CreateECSServiceTool(BaseTool):
    name = "create_ecs_service"
    description = (
        "Create an Amazon ECS Fargate service with cluster, task definition, IAM role, "
        "CloudWatch logs, and security group. Multiple ECS services share a single VPC."
    )
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "service_id": {
                "type": "string",
                "description": "Unique identifier for this service (e.g. 'api_service', 'worker').",
            },
            "label": {"type": "string", "description": "Human-readable label."},
            "cpu": {
                "type": "integer",
                "description": "Task CPU units. Valid: 256, 512, 1024, 2048, 4096.",
                "default": 256,
            },
            "memory": {
                "type": "integer",
                "description": "Task memory in MiB. Must be compatible with cpu.",
                "default": 512,
            },
            "container_port": {
                "type": "integer",
                "description": "Port the container listens on.",
                "default": 80,
            },
            "desired_count": {
                "type": "integer",
                "description": "Number of task replicas.",
                "default": 2,
            },
            "image": {
                "type": "string",
                "description": "Docker image URI.",
                "default": "nginx:latest",
            },
        },
        "required": ["service_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["service_id"]
        label = params.get("label", sid)
        cpu = int(params.get("cpu", 256))
        memory = int(params.get("memory", 512))
        cpu, memory = _valid_fargate_combo(cpu, memory)
        port = params.get("container_port", 80)
        count = params.get("desired_count", 2)
        image = params.get("image", "nginx:latest")
        safe_sid = sid.lower().replace("_", "-")

        configs = [
            # 1. Create ECS cluster
            {
                "service": "ecs",
                "action": "create_cluster",
                "params": {
                    "clusterName": f"__PROJECT__-{safe_sid}",
                    "tags": [{"key": "Name", "value": f"__PROJECT__-{safe_sid}"}],
                },
                "label": f"{label} — ECS Cluster",
                "resource_type": "aws_ecs_cluster",
                "resource_id_path": "cluster.clusterArn",
                "delete_action": "delete_cluster",
                "delete_params": {"cluster": f"__PROJECT__-{safe_sid}"},
            },
            # 2. Create IAM execution role
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{safe_sid}-exec-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{
                            "Effect": "Allow",
                            "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }],
                    }),
                },
                "label": f"{label} — Execution Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{safe_sid}-exec-role"},
            },
            # 3. Attach execution policy
            {
                "service": "iam",
                "action": "attach_role_policy",
                "params": {
                    "RoleName": f"__PROJECT__-{safe_sid}-exec-role",
                    "PolicyArn": "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
                },
                "label": f"{label} — Policy Attachment",
                "resource_type": "aws_iam_policy_attachment",
                "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {
                    "RoleName": f"__PROJECT__-{safe_sid}-exec-role",
                    "PolicyArn": "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
                },
            },
            # 4. Create CloudWatch log group
            {
                "service": "logs",
                "action": "create_log_group",
                "params": {
                    "logGroupName": f"/ecs/{safe_sid}",
                    "tags": {"Name": f"__PROJECT__-{safe_sid}-logs"},
                },
                "label": f"{label} — Log Group",
                "resource_type": "aws_cloudwatch_log_group",
                "resource_id_path": None,
                "delete_action": "delete_log_group",
                "delete_params": {"logGroupName": f"/ecs/{safe_sid}"},
            },
            # 5. Register task definition
            {
                "service": "ecs",
                "action": "register_task_definition",
                "params": {
                    "family": f"__PROJECT__-{safe_sid}",
                    "networkMode": "awsvpc",
                    "requiresCompatibilities": ["FARGATE"],
                    "cpu": str(cpu),
                    "memory": str(memory),
                    "executionRoleArn": f"__RESOLVE__:iam:create_role:{safe_sid}-exec-role:Role.Arn",
                    "containerDefinitions": [{
                        "name": safe_sid,
                        "image": image,
                        "cpu": cpu,
                        "memory": memory,
                        "essential": True,
                        "portMappings": [{"containerPort": port, "hostPort": port, "protocol": "tcp"}],
                        "logConfiguration": {
                            "logDriver": "awslogs",
                            "options": {
                                "awslogs-group": f"/ecs/{safe_sid}",
                                "awslogs-region": "__REGION__",
                                "awslogs-stream-prefix": "ecs",
                            },
                        },
                    }],
                },
                "label": f"{label} — Task Definition",
                "resource_type": "aws_ecs_task_definition",
                "resource_id_path": "taskDefinition.taskDefinitionArn",
                "delete_action": "deregister_task_definition",
                "delete_params_key": "taskDefinition",
            },
            # 6. Create ECS service (needs VPC/subnets — handled by executor)
            {
                "service": "ecs",
                "action": "create_service",
                "params": {
                    "cluster": f"__PROJECT__-{safe_sid}",
                    "serviceName": f"__PROJECT__-{safe_sid}-svc",
                    "taskDefinition": f"__PROJECT__-{safe_sid}",
                    "desiredCount": count,
                    "launchType": "FARGATE",
                    "networkConfiguration": {
                        "awsvpcConfiguration": {
                            "subnets": "__DEFAULT_SUBNETS__",
                            "assignPublicIp": "ENABLED",
                        },
                    },
                },
                "label": label,
                "resource_type": "aws_ecs_service",
                "resource_id_path": "service.serviceArn",
                "delete_action": "delete_service",
                "delete_params": {
                    "cluster": f"__PROJECT__-{safe_sid}",
                    "service": f"__PROJECT__-{safe_sid}-svc",
                    "force": True,
                },
            },
        ]

        return ToolResult(
            node=ToolNode(
                id=sid,
                type="aws_ecs",
                label=label,
                config=ToolNodeConfig(
                    memory=memory,
                    extra={"cpu": cpu, "container_port": port, "desired_count": count, "image": image},
                ),
            ),
            boto3_config={"ecs": configs},
        )
