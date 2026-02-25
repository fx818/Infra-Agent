"""AWS EventBridge tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateEventBridgeTool(BaseTool):
    name = "create_eventbridge"
    description = (
        "Create an Amazon EventBridge event bus and optional scheduled rule. "
        "Enables event-driven architectures by routing events between services."
    )
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "bus_id": {"type": "string", "description": "Unique identifier (e.g., 'main_bus')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "schedule_expression": {"type": "string", "description": "Optional cron/rate schedule (e.g., 'rate(5 minutes)').", "default": ""},
            "target_lambda_id": {"type": "string", "description": "Optional Lambda function ID to trigger on schedule.", "default": ""},
        },
        "required": ["bus_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        bid = params["bus_id"]
        schedule = params.get("schedule_expression", "")
        target_lambda = params.get("target_lambda_id", "")

        rule_block = ""
        if schedule:
            target_block = f'''
resource "aws_cloudwatch_event_target" "{bid}_target" {{
  rule      = aws_cloudwatch_event_rule.{bid}_rule.name
  event_bus_name = aws_cloudwatch_event_bus.{bid}.name
  target_id = "{bid}-target"
  arn       = aws_lambda_function.{target_lambda}.arn
}}''' if target_lambda else ""

            rule_block = f'''
resource "aws_cloudwatch_event_rule" "{bid}_rule" {{
  name                = "${{var.project_name}}-{bid}-rule"
  event_bus_name      = aws_cloudwatch_event_bus.{bid}.name
  schedule_expression = "{schedule}"
  state               = "ENABLED"
}}
{target_block}'''

        tf_code = f'''
resource "aws_cloudwatch_event_bus" "{bid}" {{
  name = "${{var.project_name}}-{bid}"
  tags = {{ Name = "${{var.project_name}}-{bid}" }}
}}
{rule_block}
'''
        return ToolResult(
            node=ToolNode(id=bid, type="aws_eventbridge", label=params.get("label", bid),
                          config=ToolNodeConfig(extra={"schedule": schedule})),
            terraform_code={"messaging.tf": tf_code},
        )
