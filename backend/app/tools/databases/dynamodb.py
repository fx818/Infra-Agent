"""AWS DynamoDB tool."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateDynamoDBTool(BaseTool):
    name = "create_dynamodb"
    description = (
        "Create an Amazon DynamoDB table — a fully managed NoSQL database. "
        "Great for serverless architectures, session storage, and low-latency lookups."
    )
    category = "databases"
    parameters = {
        "type": "object",
        "properties": {
            "table_id": {"type": "string", "description": "Unique identifier (e.g., 'user_table')."},
            "label": {"type": "string", "description": "Human-readable label."},
            "table_name": {"type": "string", "description": "DynamoDB table name.", "default": ""},
            "partition_key": {"type": "string", "description": "Partition key attribute name.", "default": "id"},
            "sort_key": {"type": "string", "description": "Optional sort key attribute name.", "default": ""},
            "billing_mode": {"type": "string", "description": "PAY_PER_REQUEST or PROVISIONED.", "default": "PAY_PER_REQUEST"},
            "enable_streams": {"type": "boolean", "description": "Enable DynamoDB Streams.", "default": False},
            "enable_point_in_time_recovery": {"type": "boolean", "description": "Enable PITR backup.", "default": True},
        },
        "required": ["table_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["table_id"]
        table_name = params.get("table_name") or f"${{var.project_name}}-{tid}"
        pk = params.get("partition_key", "id")
        sk = params.get("sort_key", "")
        billing = params.get("billing_mode", "PAY_PER_REQUEST")
        streams = params.get("enable_streams", False)
        pitr = params.get("enable_point_in_time_recovery", True)

        sk_block = f'''
  range_key = "{sk}"''' if sk else ""

        sk_attr = f'''
  attribute {{
    name = "{sk}"
    type = "S"
  }}''' if sk else ""

        billing_block = ""
        if billing == "PROVISIONED":
            billing_block = '''
  read_capacity  = 5
  write_capacity = 5'''

        streams_block = f'''
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"''' if streams else ""

        tf_code = f'''
resource "aws_dynamodb_table" "{tid}" {{
  name         = "{table_name}"
  billing_mode = "{billing}"{billing_block}
  hash_key     = "{pk}"{sk_block}{streams_block}

  attribute {{
    name = "{pk}"
    type = "S"
  }}{sk_attr}

  point_in_time_recovery {{
    enabled = {str(pitr).lower()}
  }}

  tags = {{ Name = "${{var.project_name}}-{tid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=tid, type="aws_dynamodb", label=params.get("label", tid),
                          config=ToolNodeConfig(extra={"billing_mode": billing, "pk": pk})),
            terraform_code={"databases.tf": tf_code},
        )
