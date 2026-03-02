"""Create App Runner Service tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateAppRunnerServiceTool(BaseTool):
    name = "create_app_runner_service"
    description = "Create an AWS App Runner service for deploying containerized web apps and APIs with automatic scaling."
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "service_id": {"type": "string", "description": "Unique identifier."},
            "label": {"type": "string"},
            "image_uri": {"type": "string", "description": "Container image URI.", "default": "public.ecr.aws/nginx/nginx:latest"},
            "port": {"type": "integer", "default": 80},
            "cpu": {"type": "integer", "description": "CPU units (1024, 2048, 4096).", "default": 1024},
            "memory": {"type": "integer", "description": "Memory in MB (2048, 3072, 4096).", "default": 2048},
        },
        "required": ["service_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["service_id"]
        label = params.get("label", sid)
        image = params.get("image_uri", "public.ecr.aws/nginx/nginx:latest")
        port = params.get("port", 80)
        cpu_val = params.get("cpu", 1024)
        mem_val = params.get("memory", 2048)

        configs = [{
            "service": "apprunner",
            "action": "create_service",
            "params": {
                "ServiceName": f"__PROJECT__-{sid}",
                "SourceConfiguration": {
                    "ImageRepository": {
                        "ImageIdentifier": image,
                        "ImageRepositoryType": "ECR_PUBLIC",
                        "ImageConfiguration": {"Port": str(port)},
                    },
                    "AutoDeploymentsEnabled": False,
                },
                "InstanceConfiguration": {
                    "Cpu": str(cpu_val),
                    "Memory": str(mem_val),
                },
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{sid}"}],
            },
            "label": label,
            "resource_type": "aws_apprunner_service",
            "resource_id_path": "Service.ServiceArn",
            "delete_action": "delete_service",
            "delete_params_key": "ServiceArn",
        }]

        return ToolResult(
            node=ToolNode(id=sid, type="aws_app_runner", label=label,
                          config=ToolNodeConfig(memory=mem_val, extra={"cpu": cpu_val})),
            boto3_config={"apprunner": configs},
        )
