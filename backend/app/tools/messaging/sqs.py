"""Messaging tools: SQS, SNS, EventBridge, Step Functions, MQ, Kinesis, AppSync."""
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
        fifo = params.get("fifo", False)
        suffix = ".fifo" if fifo else ""
        tf_code = f'''resource "aws_sqs_queue" "{qid}" {{
  name                       = "${{var.project_name}}-{qid}{suffix}"
  {"fifo_queue = true" if fifo else ""}
  visibility_timeout_seconds = {params.get('visibility_timeout', 30)}
  message_retention_seconds  = {params.get('message_retention', 345600)}
  tags = {{ Name = "${{var.project_name}}-{qid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=qid, type="aws_sqs", label=params.get("label", qid),
                          config=ToolNodeConfig(extra={"fifo": fifo})),
            terraform_code={"messaging.tf": tf_code},
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
        fifo = params.get("fifo_topic", False)
        suffix = ".fifo" if fifo else ""
        tf_code = f'''resource "aws_sns_topic" "{tid}" {{
  name       = "${{var.project_name}}-{tid}{suffix}"
  {"fifo_topic = true" if fifo else ""}
  tags = {{ Name = "${{var.project_name}}-{tid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=tid, type="aws_sns", label=params.get("label", tid), config=ToolNodeConfig()),
            terraform_code={"messaging.tf": tf_code},
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
        schedule = params.get("schedule", "")
        pattern = params.get("event_pattern", "")
        schedule_line = f'  schedule_expression = "{schedule}"' if schedule else ""
        pattern_line = f'  event_pattern = jsonencode({pattern})' if pattern else ""
        tf_code = f'''resource "aws_cloudwatch_event_rule" "{rid}" {{
  name        = "${{var.project_name}}-{rid}"
{schedule_line}
{pattern_line}
  tags = {{ Name = "${{var.project_name}}-{rid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=rid, type="aws_eventbridge", label=params.get("label", rid), config=ToolNodeConfig()),
            terraform_code={"messaging.tf": tf_code},
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
        tf_code = f'''resource "aws_sfn_state_machine" "{sid}" {{
  name     = "${{var.project_name}}-{sid}"
  role_arn = aws_iam_role.{sid}_sfn_role.arn
  type     = "{params.get('type', 'STANDARD')}"
  definition = jsonencode({{
    Comment = "{params.get('label', sid)}"
    StartAt = "Start"
    States = {{
      Start = {{ Type = "Pass", End = true }}
    }}
  }})
}}

resource "aws_iam_role" "{sid}_sfn_role" {{
  name = "${{var.project_name}}-{sid}-sfn-role"
  assume_role_policy = jsonencode({{
    Version = "2012-10-17"
    Statement = [{{ Action = "sts:AssumeRole", Effect = "Allow", Principal = {{ Service = "states.amazonaws.com" }} }}]
  }})
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_step_functions", label=params.get("label", sid), config=ToolNodeConfig()),
            terraform_code={"messaging.tf": tf_code},
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
        tf_code = f'''resource "aws_mq_broker" "{mid}" {{
  broker_name        = "${{var.project_name}}-{mid}"
  engine_type        = "{params.get('engine_type', 'RabbitMQ')}"
  engine_version     = "3.11.20"
  host_instance_type = "{params.get('instance_type', 'mq.m5.large')}"
  deployment_mode    = "SINGLE_INSTANCE"
  user {{
    username = "admin"
    password = var.db_password
  }}
  tags = {{ Name = "${{var.project_name}}-{mid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=mid, type="aws_mq", label=params.get("label", mid),
                          config=ToolNodeConfig(engine=params.get("engine_type", "RabbitMQ"))),
            terraform_code={"messaging.tf": tf_code},
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
        tf_code = f'''resource "aws_kinesis_stream" "{sid}" {{
  name             = "${{var.project_name}}-{sid}"
  shard_count      = {params.get('shard_count', 1)}
  retention_period = {params.get('retention_hours', 24)}
  tags = {{ Name = "${{var.project_name}}-{sid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=sid, type="aws_kinesis", label=params.get("label", sid), config=ToolNodeConfig()),
            terraform_code={"messaging.tf": tf_code},
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
        tf_code = f'''resource "aws_appsync_graphql_api" "{aid}" {{
  name                = "${{var.project_name}}-{aid}"
  authentication_type = "{params.get('auth_type', 'API_KEY')}"
  schema = <<EOF
type Query {{
  hello: String
}}
EOF
  tags = {{ Name = "${{var.project_name}}-{aid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=aid, type="aws_appsync", label=params.get("label", aid), config=ToolNodeConfig()),
            terraform_code={"messaging.tf": tf_code},
        )
