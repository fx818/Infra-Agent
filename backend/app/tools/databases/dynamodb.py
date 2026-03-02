"""AWS DynamoDB tool — provisions via boto3."""
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
        label = params.get("label", tid)
        pk = params.get("partition_key", "id")
        sk = params.get("sort_key", "")
        billing = params.get("billing_mode", "PAY_PER_REQUEST")
        streams = params.get("enable_streams", False)
        pitr = params.get("enable_point_in_time_recovery", True)

        tbl_name = params.get("table_name") or f"__PROJECT__-{tid}"

        key_schema = [{"AttributeName": pk, "KeyType": "HASH"}]
        attr_defs = [{"AttributeName": pk, "AttributeType": "S"}]

        if sk:
            key_schema.append({"AttributeName": sk, "KeyType": "RANGE"})
            attr_defs.append({"AttributeName": sk, "AttributeType": "S"})

        create_params: dict[str, Any] = {
            "TableName": tbl_name,
            "KeySchema": key_schema,
            "AttributeDefinitions": attr_defs,
            "BillingMode": billing,
            "Tags": [{"Key": "Name", "Value": tbl_name}],
        }

        if billing == "PROVISIONED":
            create_params["ProvisionedThroughput"] = {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}

        if streams:
            create_params["StreamSpecification"] = {"StreamEnabled": True, "StreamViewType": "NEW_AND_OLD_IMAGES"}

        configs: list[dict[str, Any]] = [{
            "service": "dynamodb",
            "action": "create_table",
            "params": create_params,
            "label": label,
            "resource_type": "aws_dynamodb",
            "resource_id_path": "TableDescription.TableArn",
            "delete_action": "delete_table",
            "delete_params": {"TableName": tbl_name},
            "waiter": "table_exists",
            "waiter_params": {"TableName": tbl_name},
        }]

        if pitr:
            configs.append({
                "service": "dynamodb",
                "action": "update_continuous_backups",
                "params": {
                    "TableName": tbl_name,
                    "PointInTimeRecoverySpecification": {"PointInTimeRecoveryEnabled": True},
                },
                "label": f"{label} — PITR",
                "resource_type": "aws_dynamodb_pitr",
                "is_support": True,
            })

        return ToolResult(
            node=ToolNode(id=tid, type="aws_dynamodb", label=label,
                          config=ToolNodeConfig(extra={"billing_mode": billing, "pk": pk})),
            boto3_config={"dynamodb": configs},
        )
