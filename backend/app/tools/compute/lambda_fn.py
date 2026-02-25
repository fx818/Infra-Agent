"""Create Lambda Function tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateLambdaFunctionTool(BaseTool):
    name = "create_lambda_function"
    description = (
        "Create an AWS Lambda serverless function. Configure runtime, memory, "
        "timeout, and handler. Ideal for event-driven workloads, API backends, "
        "data processing, and microservices."
    )
    category = "compute"
    parameters = {
        "type": "object",
        "properties": {
            "function_id": {
                "type": "string",
                "description": "Unique identifier for this function (e.g., 'user_handler', 'process_order').",
            },
            "label": {"type": "string", "description": "Human-readable label."},
            "runtime": {
                "type": "string",
                "description": "Lambda runtime (e.g., 'python3.12', 'nodejs20.x', 'java21').",
                "default": "python3.12",
            },
            "memory": {
                "type": "integer",
                "description": "Memory in MB (128-10240).",
                "default": 256,
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds (1-900).",
                "default": 30,
            },
            "handler": {
                "type": "string",
                "description": "Handler function path.",
                "default": "index.handler",
            },
        },
        "required": ["function_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        fid = params["function_id"]
        label = params.get("label", fid)
        runtime = params.get("runtime", "python3.12")
        memory = params.get("memory", 256)
        timeout = params.get("timeout", 30)
        handler = params.get("handler", "index.handler")

        tf_code = f'''resource "aws_lambda_function" "{fid}" {{
  function_name = "${{var.project_name}}-{fid}"
  role          = aws_iam_role.{fid}_role.arn
  handler       = "{handler}"
  runtime       = "{runtime}"
  memory_size   = {memory}
  timeout       = {timeout}
  filename      = "{fid}.zip"

  tags = {{
    Name = "${{var.project_name}}-{fid}"
  }}
}}

resource "aws_iam_role" "{fid}_role" {{
  name = "${{var.project_name}}-{fid}-role"

  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {{ Service = "lambda.amazonaws.com" }}
    }}]
  }})
}}

resource "aws_iam_role_policy_attachment" "{fid}_basic" {{
  role       = aws_iam_role.{fid}_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}}

resource "aws_cloudwatch_log_group" "{fid}_logs" {{
  name              = "/aws/lambda/${{var.project_name}}-{fid}"
  retention_in_days = 14
}}
'''
        return ToolResult(
            node=ToolNode(
                id=fid, type="aws_lambda", label=label,
                config=ToolNodeConfig(runtime=runtime, memory=memory, extra={"timeout": timeout, "handler": handler}),
            ),
            terraform_code={"compute.tf": tf_code},
        )
