"""AWS Kinesis Data Streams tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateKinesisStreamTool(BaseTool):
    name = "create_kinesis_stream"
    description = (
        "Create an Amazon Kinesis Data Stream for real-time data streaming and analytics. "
        "Ideal for log ingestion, clickstream data, and IoT telemetry."
    )
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "stream_id": {"type": "string", "description": "Unique identifier (e.g., 'events_stream')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "shard_count": {"type": "integer", "description": "Number of shards (throughput units).", "default": 1},
            "retention_period_hours": {"type": "integer", "description": "Data retention in hours (24-8760).", "default": 24},
        },
        "required": ["stream_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["stream_id"]
        shards = params.get("shard_count", 1)
        retention = params.get("retention_period_hours", 24)

        tf_code = f'''
resource "aws_kinesis_stream" "{sid}" {{
  name             = "${{var.project_name}}-{sid}"
  shard_count      = {shards}
  retention_period = {retention}

  stream_mode_details {{
    stream_mode = "PROVISIONED"
  }}

  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_kinesis", label=params.get("label", sid),
                          config=ToolNodeConfig(extra={"shards": shards, "retention_hours": retention})),
            terraform_code={"messaging.tf": tf_code},
        )
