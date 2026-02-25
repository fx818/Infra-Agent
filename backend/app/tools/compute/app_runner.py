"""Create App Runner Service tool."""
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
        tf_code = f'''resource "aws_apprunner_service" "{sid}" {{
  service_name = "${{var.project_name}}-{sid}"
  source_configuration {{
    image_repository {{
      image_configuration {{
        port = "{params.get('port', 80)}"
      }}
      image_identifier      = "{params.get('image_uri', 'public.ecr.aws/nginx/nginx:latest')}"
      image_repository_type = "ECR_PUBLIC"
    }}
    auto_deployments_enabled = false
  }}
  instance_configuration {{
    cpu    = "{params.get('cpu', 1024)}"
    memory = "{params.get('memory', 2048)}"
  }}
  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_app_runner", label=params.get("label", sid),
                          config=ToolNodeConfig(memory=params.get("memory", 2048), extra={"cpu": params.get("cpu", 1024)})),
            terraform_code={"compute.tf": tf_code},
        )
