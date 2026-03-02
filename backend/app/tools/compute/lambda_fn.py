"""Create Lambda Function tool — provisions via boto3."""
import json
import io
import zipfile
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


def _placeholder_zip() -> bytes:
    """Create a minimal Lambda deployment zip in memory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.py", 'def handler(event, ctx):\n    return {"statusCode": 200, "body": "Hello from NL2I"}\n')
    return buf.getvalue()


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

        configs = [
            # 1. Create IAM role for Lambda
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{fid}-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }],
                    }),
                    "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{fid}-role"}],
                },
                "label": f"{label} — IAM Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{fid}-role"},
            },
            # 2. Attach basic execution policy
            {
                "service": "iam",
                "action": "attach_role_policy",
                "params": {
                    "RoleName": f"__PROJECT__-{fid}-role",
                    "PolicyArn": "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                },
                "label": f"{label} — Policy Attachment",
                "resource_type": "aws_iam_policy_attachment",
                "is_support": True,
                "delete_action": "detach_role_policy",
                "delete_params": {
                    "RoleName": f"__PROJECT__-{fid}-role",
                    "PolicyArn": "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                },
            },
            # 3. Create the Lambda function
            {
                "service": "lambda",
                "action": "create_function",
                "params": {
                    "FunctionName": f"__PROJECT__-{fid}",
                    "Runtime": runtime,
                    "Role": f"__RESOLVE__:iam:create_role:{fid}-role:Role.Arn",
                    "Handler": handler,
                    "MemorySize": memory,
                    "Timeout": timeout,
                    "Code": {"ZipFile": "__PLACEHOLDER_ZIP__"},
                    "Tags": {"Name": f"__PROJECT__-{fid}"},
                },
                "label": label,
                "resource_type": "aws_lambda_function",
                "resource_id_path": "FunctionArn",
                "delete_action": "delete_function",
                "delete_params": {"FunctionName": f"__PROJECT__-{fid}"},
                "waiter": "function_active_v2",
                "needs_role_delay": True,
            },
        ]

        return ToolResult(
            node=ToolNode(
                id=fid, type="aws_lambda", label=label,
                config=ToolNodeConfig(runtime=runtime, memory=memory, extra={"timeout": timeout, "handler": handler}),
            ),
            boto3_config={"lambda": configs},
        )
