"""Monitoring tools: CloudWatch Alarm, Log Group, CloudTrail, Config, X-Ray, Health."""
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateCloudWatchAlarmTool(BaseTool):
    name = "create_cloudwatch_alarm"
    description = "Create an Amazon CloudWatch alarm that monitors a metric and triggers actions."
    category = "monitoring"
    parameters = {
        "type": "object",
        "properties": {
            "alarm_id": {"type": "string"}, "label": {"type": "string"},
            "metric_name": {"type": "string", "default": "CPUUtilization"},
            "namespace": {"type": "string", "default": "AWS/EC2"},
            "threshold": {"type": "number", "default": 80},
            "comparison_operator": {"type": "string", "default": "GreaterThanThreshold"},
            "evaluation_periods": {"type": "integer", "default": 2},
            "period": {"type": "integer", "description": "Period in seconds.", "default": 300},
        },
        "required": ["alarm_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        aid = params["alarm_id"]
        tf_code = f'''resource "aws_cloudwatch_metric_alarm" "{aid}" {{
  alarm_name          = "${{var.project_name}}-{aid}"
  comparison_operator = "{params.get('comparison_operator', 'GreaterThanThreshold')}"
  evaluation_periods  = {params.get('evaluation_periods', 2)}
  metric_name         = "{params.get('metric_name', 'CPUUtilization')}"
  namespace           = "{params.get('namespace', 'AWS/EC2')}"
  period              = {params.get('period', 300)}
  statistic           = "Average"
  threshold           = {params.get('threshold', 80)}
  alarm_description   = "{params.get('label', aid)}"
  tags = {{ Name = "${{var.project_name}}-{aid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=aid, type="aws_cloudwatch", label=params.get("label", aid), config=ToolNodeConfig()),
            terraform_code={"monitoring.tf": tf_code},
        )


class CreateLogGroupTool(BaseTool):
    name = "create_log_group"
    description = "Create an Amazon CloudWatch Logs log group for centralized logging."
    category = "monitoring"
    parameters = {
        "type": "object",
        "properties": {
            "log_id": {"type": "string"}, "label": {"type": "string"},
            "retention_days": {"type": "integer", "default": 14},
        },
        "required": ["log_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        lid = params["log_id"]
        tf_code = f'''resource "aws_cloudwatch_log_group" "{lid}" {{
  name              = "/custom/${{var.project_name}}/{lid}"
  retention_in_days = {params.get('retention_days', 14)}
  tags = {{ Name = "${{var.project_name}}-{lid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=lid, type="aws_cloudwatch_logs", label=params.get("label", lid), config=ToolNodeConfig()),
            terraform_code={"monitoring.tf": tf_code},
        )


class CreateCloudTrailTool(BaseTool):
    name = "create_cloudtrail"
    description = "Create an AWS CloudTrail trail for API activity logging and auditing."
    category = "monitoring"
    parameters = {
        "type": "object",
        "properties": {
            "trail_id": {"type": "string"}, "label": {"type": "string"},
            "s3_bucket_ref": {"type": "string", "description": "S3 bucket resource ID for logs."},
            "multi_region": {"type": "boolean", "default": True},
        },
        "required": ["trail_id", "label", "s3_bucket_ref"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["trail_id"]
        tf_code = f'''resource "aws_cloudtrail" "{tid}" {{
  name                          = "${{var.project_name}}-{tid}"
  s3_bucket_name                = aws_s3_bucket.{params['s3_bucket_ref']}.id
  is_multi_region_trail         = {str(params.get('multi_region', True)).lower()}
  enable_log_file_validation    = true
  include_global_service_events = true
  tags = {{ Name = "${{var.project_name}}-{tid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=tid, type="aws_cloudtrail", label=params.get("label", tid), config=ToolNodeConfig()),
            terraform_code={"monitoring.tf": tf_code},
            edges=[{"from": tid, "to": params["s3_bucket_ref"], "label": "logs to"}],
        )


class CreateConfigRuleTool(BaseTool):
    name = "create_config_rule"
    description = "Create an AWS Config rule for compliance monitoring of your AWS resources."
    category = "monitoring"
    parameters = {
        "type": "object",
        "properties": {
            "config_id": {"type": "string"}, "label": {"type": "string"},
            "rule_name": {"type": "string", "description": "AWS Config managed rule name.", "default": "encrypted-volumes"},
        },
        "required": ["config_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["config_id"]
        tf_code = f'''resource "aws_config_config_rule" "{cid}" {{
  name = "${{var.project_name}}-{cid}"
  source {{
    owner             = "AWS"
    source_identifier = "{params.get('rule_name', 'ENCRYPTED_VOLUMES').upper().replace('-', '_')}"
  }}
  tags = {{ Name = "${{var.project_name}}-{cid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=cid, type="aws_config", label=params.get("label", cid), config=ToolNodeConfig()),
            terraform_code={"monitoring.tf": tf_code},
        )


class CreateXRayGroupTool(BaseTool):
    name = "create_xray_group"
    description = "Create an AWS X-Ray group for distributed tracing and performance analysis."
    category = "monitoring"
    parameters = {
        "type": "object",
        "properties": {
            "xray_id": {"type": "string"}, "label": {"type": "string"},
            "filter_expression": {"type": "string", "default": "responsetime > 5"},
        },
        "required": ["xray_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        xid = params["xray_id"]
        tf_code = f'''resource "aws_xray_group" "{xid}" {{
  group_name        = "${{var.project_name}}-{xid}"
  filter_expression = "{params.get('filter_expression', 'responsetime > 5')}"
  tags = {{ Name = "${{var.project_name}}-{xid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=xid, type="aws_xray", label=params.get("label", xid), config=ToolNodeConfig()),
            terraform_code={"monitoring.tf": tf_code},
        )


class CreateHealthEventRuleTool(BaseTool):
    name = "create_health_event_rule"
    description = "Create an EventBridge rule to capture AWS Health events for proactive monitoring."
    category = "monitoring"
    parameters = {
        "type": "object",
        "properties": {
            "health_id": {"type": "string"}, "label": {"type": "string"},
        },
        "required": ["health_id", "label"],
    }

    def execute(self, params: dict[str, Any]) -> ToolResult:
        hid = params["health_id"]
        tf_code = f'''resource "aws_cloudwatch_event_rule" "{hid}" {{
  name        = "${{var.project_name}}-{hid}"
  description = "Capture AWS Health events"
  event_pattern = jsonencode({{
    source      = ["aws.health"]
    detail-type = ["AWS Health Event"]
  }})
  tags = {{ Name = "${{var.project_name}}-{hid}" }}
}}
'''
        return ToolResult(
            node=ToolNode(id=hid, type="aws_health", label=params.get("label", hid), config=ToolNodeConfig()),
            terraform_code={"monitoring.tf": tf_code},
        )
