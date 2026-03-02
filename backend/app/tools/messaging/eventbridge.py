"""AWS EventBridge tool — provisions via boto3."""
import json
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
            "schedule_expression": {"type": "string", "description": "Optional cron/rate schedule.", "default": ""},
            "target_lambda_id": {"type": "string", "description": "Optional Lambda function ID to trigger.", "default": ""},
        },
        "required": ["bus_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        bid = params["bus_id"]
        label = params.get("label", bid)
        schedule = params.get("schedule_expression", "")

        configs: list[dict[str, Any]] = [{
            "service": "events",
            "action": "create_event_bus",
            "params": {
                "Name": f"__PROJECT__-{bid}",
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{bid}"}],
            },
            "label": label,
            "resource_type": "aws_eventbridge_bus",
            "resource_id_path": "EventBusArn",
            "delete_action": "delete_event_bus",
            "delete_params": {"Name": f"__PROJECT__-{bid}"},
        }]

        if schedule:
            configs.append({
                "service": "events",
                "action": "put_rule",
                "params": {
                    "Name": f"__PROJECT__-{bid}-rule",
                    "EventBusName": f"__PROJECT__-{bid}",
                    "ScheduleExpression": schedule,
                    "State": "ENABLED",
                },
                "label": f"{label} — Rule",
                "resource_type": "aws_eventbridge_rule",
                "resource_id_path": "RuleArn",
                "delete_action": "delete_rule",
                "delete_params": {"Name": f"__PROJECT__-{bid}-rule", "EventBusName": f"__PROJECT__-{bid}"},
            })

        return ToolResult(
            node=ToolNode(id=bid, type="aws_eventbridge", label=label,
                          config=ToolNodeConfig(extra={"schedule": schedule})),
            boto3_config={"events": configs},
        )
