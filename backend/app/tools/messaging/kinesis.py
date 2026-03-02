"""AWS Kinesis Data Streams tool — provisions via boto3."""
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
        label = params.get("label", sid)
        shards = params.get("shard_count", 1)
        retention = params.get("retention_period_hours", 24)

        configs = [{
            "service": "kinesis",
            "action": "create_stream",
            "params": {
                "StreamName": f"__PROJECT__-{sid}",
                "ShardCount": shards,
                "StreamModeDetails": {"StreamMode": "PROVISIONED"},
                "Tags": {"Name": f"__PROJECT__-{sid}"},
            },
            "label": label,
            "resource_type": "aws_kinesis",
            "resource_id_path": None,
            "delete_action": "delete_stream",
            "delete_params": {"StreamName": f"__PROJECT__-{sid}", "EnforceConsumerDeletion": True},
            "waiter": "stream_exists",
            "waiter_params": {"StreamName": f"__PROJECT__-{sid}"},
        }]

        return ToolResult(
            node=ToolNode(id=sid, type="aws_kinesis", label=label,
                          config=ToolNodeConfig(extra={"shards": shards, "retention_hours": retention})),
            boto3_config={"kinesis": configs},
        )
