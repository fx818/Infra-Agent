"""Messaging tools: SQS, SNS, EventBridge, Step Functions, MQ, Kinesis, AppSync — provisions via boto3."""
import json
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateSQSQueueTool(BaseTool):
    name = "create_sqs_queue"
    description = "Create an Amazon SQS queue (standard or FIFO) for message queuing."
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "queue_id": {"type": "string"}, "label": {"type": "string"},
            "fifo": {"type": "boolean", "default": False},
            "visibility_timeout": {"type": "integer", "default": 30},
            "message_retention": {"type": "integer", "description": "Retention in seconds (60-1209600).", "default": 345600},
        },
        "required": ["queue_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        qid = params["queue_id"]
        label = params.get("label", qid)
        fifo = params.get("fifo", False)
        suffix = ".fifo" if fifo else ""
        attrs: dict[str, str] = {
            "VisibilityTimeout": str(params.get("visibility_timeout", 30)),
            "MessageRetentionPeriod": str(params.get("message_retention", 345600)),
        }
        if fifo:
            attrs["FifoQueue"] = "true"
        configs = [{
            "service": "sqs",
            "action": "create_queue",
            "params": {"QueueName": f"__PROJECT__-{qid}{suffix}", "Attributes": attrs, "tags": {"Name": f"__PROJECT__-{qid}"}},
            "label": label,
            "resource_type": "aws_sqs",
            "resource_id_path": "QueueUrl",
            "delete_action": "delete_queue",
            "delete_params_key": "QueueUrl",
        }]
        return ToolResult(
            node=ToolNode(id=qid, type="aws_sqs", label=label, config=ToolNodeConfig(extra={"fifo": fifo})),
            boto3_config={"sqs": configs},
        )


class CreateSNSTopicTool(BaseTool):
    name = "create_sns_topic"
    description = "Create an Amazon SNS topic for pub/sub messaging."
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "topic_id": {"type": "string"}, "label": {"type": "string"},
            "fifo_topic": {"type": "boolean", "default": False},
        },
        "required": ["topic_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["topic_id"]
        label = params.get("label", tid)
        fifo = params.get("fifo_topic", False)
        suffix = ".fifo" if fifo else ""
        attrs = {"FifoTopic": "true"} if fifo else {}
        configs = [{
            "service": "sns",
            "action": "create_topic",
            "params": {"Name": f"__PROJECT__-{tid}{suffix}", "Attributes": attrs, "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{tid}"}]},
            "label": label,
            "resource_type": "aws_sns",
            "resource_id_path": "TopicArn",
            "delete_action": "delete_topic",
            "delete_params_key": "TopicArn",
        }]
        return ToolResult(
            node=ToolNode(id=tid, type="aws_sns", label=label, config=ToolNodeConfig()),
            boto3_config={"sns": configs},
        )


class CreateEventBridgeRuleTool(BaseTool):
    name = "create_eventbridge_rule"
    description = "Create an Amazon EventBridge rule for event-driven architectures."
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "rule_id": {"type": "string"}, "label": {"type": "string"},
            "schedule": {"type": "string", "description": "Schedule expression or leave empty for event pattern.", "default": ""},
            "event_pattern": {"type": "string", "description": "JSON event pattern.", "default": ""},
        },
        "required": ["rule_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        rid = params["rule_id"]
        label = params.get("label", rid)
        put_params: dict[str, Any] = {"Name": f"__PROJECT__-{rid}", "State": "ENABLED", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{rid}"}]}
        if params.get("schedule"):
            put_params["ScheduleExpression"] = params["schedule"]
        if params.get("event_pattern"):
            put_params["EventPattern"] = params["event_pattern"]
        configs = [{
            "service": "events",
            "action": "put_rule",
            "params": put_params,
            "label": label,
            "resource_type": "aws_eventbridge_rule",
            "resource_id_path": "RuleArn",
            "delete_action": "delete_rule",
            "delete_params": {"Name": f"__PROJECT__-{rid}"},
        }]
        return ToolResult(
            node=ToolNode(id=rid, type="aws_eventbridge", label=label, config=ToolNodeConfig()),
            boto3_config={"events": configs},
        )


class CreateStepFunctionTool(BaseTool):
    name = "create_step_function"
    description = "Create an AWS Step Functions state machine for workflow orchestration."
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "sfn_id": {"type": "string"}, "label": {"type": "string"},
            "type": {"type": "string", "description": "'STANDARD' or 'EXPRESS'.", "default": "STANDARD"},
        },
        "required": ["sfn_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["sfn_id"]
        label = params.get("label", sid)
        sfn_type = params.get("type", "STANDARD")
        configs = [
            {
                "service": "iam",
                "action": "create_role",
                "params": {
                    "RoleName": f"__PROJECT__-{sid}-sfn-role",
                    "AssumeRolePolicyDocument": json.dumps({
                        "Version": "2012-10-17",
                        "Statement": [{"Action": "sts:AssumeRole", "Effect": "Allow", "Principal": {"Service": "states.amazonaws.com"}}],
                    }),
                },
                "label": f"{label} — Role",
                "resource_type": "aws_iam_role",
                "resource_id_path": "Role.Arn",
                "delete_action": "delete_role",
                "delete_params": {"RoleName": f"__PROJECT__-{sid}-sfn-role"},
            },
            {
                "service": "stepfunctions",
                "action": "create_state_machine",
                "params": {
                    "name": f"__PROJECT__-{sid}",
                    "roleArn": f"__RESOLVE__:iam:create_role:{sid}-sfn-role:Role.Arn",
                    "type": sfn_type,
                    "definition": json.dumps({"Comment": label, "StartAt": "Start", "States": {"Start": {"Type": "Pass", "End": True}}}),
                    "tags": [{"key": "Name", "value": f"__PROJECT__-{sid}"}],
                },
                "label": label,
                "resource_type": "aws_step_functions",
                "resource_id_path": "stateMachineArn",
                "delete_action": "delete_state_machine",
                "delete_params_key": "stateMachineArn",
            },
        ]
        return ToolResult(
            node=ToolNode(id=sid, type="aws_step_functions", label=label, config=ToolNodeConfig()),
            boto3_config={"stepfunctions": configs},
        )


class CreateMQBrokerTool(BaseTool):
    name = "create_mq_broker"
    description = "Create an Amazon MQ broker (ActiveMQ or RabbitMQ) for message brokering."
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "mq_id": {"type": "string"}, "label": {"type": "string"},
            "engine_type": {"type": "string", "description": "'ActiveMQ' or 'RabbitMQ'.", "default": "RabbitMQ"},
            "instance_type": {"type": "string", "default": "mq.m5.large"},
        },
        "required": ["mq_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        mid = params["mq_id"]
        label = params.get("label", mid)
        engine = params.get("engine_type", "RabbitMQ")
        engine_versions = {"RabbitMQ": "3.11.20", "ActiveMQ": "5.17.6"}
        configs = [{
            "service": "mq",
            "action": "create_broker",
            "params": {
                "BrokerName": f"__PROJECT__-{mid}",
                "EngineType": engine.upper(),
                "EngineVersion": engine_versions.get(engine, "3.11.20"),
                "HostInstanceType": params.get("instance_type", "mq.m5.large"),
                "DeploymentMode": "SINGLE_INSTANCE",
                "Users": [{"Username": "admin", "Password": "ChangeMe123!"}],
                "PubliclyAccessible": False,
                "Tags": {"Name": f"__PROJECT__-{mid}"},
            },
            "label": label,
            "resource_type": "aws_mq",
            "resource_id_path": "BrokerId",
            "delete_action": "delete_broker",
            "delete_params_key": "BrokerId",
        }]
        return ToolResult(
            node=ToolNode(id=mid, type="aws_mq", label=label, config=ToolNodeConfig(engine=engine)),
            boto3_config={"mq": configs},
        )


class CreateKinesisStreamTool(BaseTool):
    name = "create_kinesis_stream"
    description = "Create an Amazon Kinesis Data Stream for real-time data streaming."
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "stream_id": {"type": "string"}, "label": {"type": "string"},
            "shard_count": {"type": "integer", "default": 1},
            "retention_hours": {"type": "integer", "default": 24},
        },
        "required": ["stream_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        sid = params["stream_id"]
        label = params.get("label", sid)
        configs = [{
            "service": "kinesis",
            "action": "create_stream",
            "params": {
                "StreamName": f"__PROJECT__-{sid}",
                "ShardCount": params.get("shard_count", 1),
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
            node=ToolNode(id=sid, type="aws_kinesis", label=label, config=ToolNodeConfig()),
            boto3_config={"kinesis": configs},
        )


class CreateAppSyncAPITool(BaseTool):
    name = "create_appsync_api"
    description = "Create an AWS AppSync GraphQL API for building real-time applications."
    category = "messaging"
    parameters = {
        "type": "object",
        "properties": {
            "api_id": {"type": "string"}, "label": {"type": "string"},
            "auth_type": {"type": "string", "description": "'API_KEY', 'AMAZON_COGNITO_USER_POOLS', 'AWS_IAM'.", "default": "API_KEY"},
        },
        "required": ["api_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        aid = params["api_id"]
        label = params.get("label", aid)
        configs = [{
            "service": "appsync",
            "action": "create_graphql_api",
            "params": {
                "name": f"__PROJECT__-{aid}",
                "authenticationType": params.get("auth_type", "API_KEY"),
                "tags": {"Name": f"__PROJECT__-{aid}"},
            },
            "label": label,
            "resource_type": "aws_appsync",
            "resource_id_path": "graphqlApi.apiId",
            "delete_action": "delete_graphql_api",
            "delete_params_key": "apiId",
        }]
        return ToolResult(
            node=ToolNode(id=aid, type="aws_appsync", label=label, config=ToolNodeConfig()),
            boto3_config={"appsync": configs},
        )
