"""Create API Gateway tool — provisions via boto3."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateAPIGatewayTool(BaseTool):
    name = "create_api_gateway"
    description = "Create an Amazon API Gateway (HTTP or REST) for exposing APIs. Integrates with Lambda, ECS, etc."
    category = "networking"
    parameters = {
        "type": "object",
        "properties": {
            "gateway_id": {"type": "string"}, "label": {"type": "string"},
            "api_type": {"type": "string", "description": "'HTTP' or 'REST'.", "default": "HTTP"},
            "cors_enabled": {"type": "boolean", "default": True},
            "stage_name": {"type": "string", "default": "prod"},
        },
        "required": ["gateway_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        gid = params["gateway_id"]
        label = params.get("label", gid)
        api_type = params.get("api_type", "HTTP")
        stage = params.get("stage_name", "prod")

        if api_type == "HTTP":
            cors_config = {}
            if params.get("cors_enabled", True):
                cors_config = {
                    "AllowOrigins": ["*"],
                    "AllowMethods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "AllowHeaders": ["*"],
                    "MaxAge": 3600,
                }
            create_params = {
                "Name": f"__PROJECT__-{gid}",
                "ProtocolType": "HTTP",
                "Tags": {"Name": f"__PROJECT__-{gid}"},
            }
            if cors_config:
                create_params["CorsConfiguration"] = cors_config

            configs = [
                {
                    "service": "apigatewayv2",
                    "action": "create_api",
                    "params": create_params,
                    "label": label,
                    "resource_type": "aws_apigatewayv2",
                    "resource_id_path": "ApiId",
                    "delete_action": "delete_api",
                    "delete_params_key": "ApiId",
                },
                {
                    "service": "apigatewayv2",
                    "action": "create_stage",
                    "params": {
                        "ApiId": "__RESOLVE_PREV__",
                        "StageName": stage,
                        "AutoDeploy": True,
                    },
                    "label": f"{label} — Stage",
                    "resource_type": "aws_apigatewayv2_stage",
                    "resource_id_path": "StageName",
                    "is_support": True,
                },
            ]
        else:
            configs = [
                {
                    "service": "apigateway",
                    "action": "create_rest_api",
                    "params": {
                        "name": f"__PROJECT__-{gid}",
                        "tags": {"Name": f"__PROJECT__-{gid}"},
                    },
                    "label": label,
                    "resource_type": "aws_api_gateway_rest_api",
                    "resource_id_path": "id",
                    "delete_action": "delete_rest_api",
                    "delete_params_key": "restApiId",
                },
            ]

        return ToolResult(
            node=ToolNode(id=gid, type="aws_apigatewayv2", label=label,
                          config=ToolNodeConfig(extra={"api_type": api_type})),
            boto3_config={"apigateway": configs},
        )
