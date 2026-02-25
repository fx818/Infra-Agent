"""Create API Gateway tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateAPIGatewayTool(BaseTool):
    name = "create_api_gateway"
    description = "Create an Amazon API Gateway (HTTP or REST) for exposing APIs. Integrates with Lambda, ECS, etc."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "gateway_id": {"type": "string"},
            "label": {"type": "string"},
            "api_type": {"type": "string", "description": "'HTTP' or 'REST'.", "default": "HTTP"},
            "cors_enabled": {"type": "boolean", "default": True},
            "stage_name": {"type": "string", "default": "prod"},
        },
        "required": ["gateway_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        gid = params["gateway_id"]
        api_type = params.get("api_type", "HTTP")
        if api_type == "HTTP":
            tf_code = f'''resource "aws_apigatewayv2_api" "{gid}" {{
  name          = "${{var.project_name}}-{gid}"
  protocol_type = "HTTP"
  cors_configuration {{
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["*"]
    max_age       = 3600
  }}
}}

resource "aws_apigatewayv2_stage" "{gid}_stage" {{
  api_id      = aws_apigatewayv2_api.{gid}.id
  name        = "{params.get('stage_name', 'prod')}"
  auto_deploy = true
}}
'''
        else:
            tf_code = f'''resource "aws_api_gateway_rest_api" "{gid}" {{
  name = "${{var.project_name}}-{gid}"
}}

resource "aws_api_gateway_deployment" "{gid}_deploy" {{
  rest_api_id = aws_api_gateway_rest_api.{gid}.id
}}

resource "aws_api_gateway_stage" "{gid}_stage" {{
  rest_api_id   = aws_api_gateway_rest_api.{gid}.id
  deployment_id = aws_api_gateway_deployment.{gid}_deploy.id
  stage_name    = "{params.get('stage_name', 'prod')}"
}}
'''
        return ToolResult(
            node=ToolNode(id=gid, type="aws_apigatewayv2", label=params.get("label", gid),
                          config=ToolNodeConfig(extra={"api_type": api_type})),
            terraform_code={"networking.tf": tf_code},
        )
