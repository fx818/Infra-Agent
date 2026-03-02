"""Monitoring tools: CloudWatch Alarm, Log Group, CloudTrail, Config, X-Ray, Health — provisions via boto3."""
import json
from typing import Any
from app.tools.base import BaseTool, ToolResult, ToolNode, ToolNodeConfig


class CreateCloudWatchAlarmTool(BaseTool):
    name = "create_cloudwatch_alarm"
    description = "Create an Amazon CloudWatch alarm that monitors a metric and triggers actions."
    category = "monitoring"
    parameters = {"type": "object", "properties": {
        "alarm_id": {"type": "string"}, "label": {"type": "string"},
        "metric_name": {"type": "string", "default": "CPUUtilization"},
        "namespace": {"type": "string", "default": "AWS/EC2"},
        "threshold": {"type": "number", "default": 80},
        "comparison_operator": {"type": "string", "default": "GreaterThanThreshold"},
        "evaluation_periods": {"type": "integer", "default": 2},
        "period": {"type": "integer", "default": 300},
    }, "required": ["alarm_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        aid = params["alarm_id"]; label = params.get("label", aid)
        configs = [{"service": "cloudwatch", "action": "put_metric_alarm",
            "params": {
                "AlarmName": f"__PROJECT__-{aid}",
                "ComparisonOperator": params.get("comparison_operator", "GreaterThanThreshold"),
                "EvaluationPeriods": params.get("evaluation_periods", 2),
                "MetricName": params.get("metric_name", "CPUUtilization"),
                "Namespace": params.get("namespace", "AWS/EC2"),
                "Period": params.get("period", 300),
                "Statistic": "Average",
                "Threshold": params.get("threshold", 80),
                "AlarmDescription": label,
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{aid}"}],
            },
            "label": label, "resource_type": "aws_cloudwatch_alarm",
            "resource_id_path": None,
            "delete_action": "delete_alarms",
            "delete_params": {"AlarmNames": [f"__PROJECT__-{aid}"]}}]
        return ToolResult(node=ToolNode(id=aid, type="aws_cloudwatch", label=label, config=ToolNodeConfig()), boto3_config={"cloudwatch": configs})


class CreateLogGroupTool(BaseTool):
    name = "create_log_group"
    description = "Create an Amazon CloudWatch Logs log group for centralized logging."
    category = "monitoring"
    parameters = {"type": "object", "properties": {
        "log_id": {"type": "string"}, "label": {"type": "string"},
        "retention_days": {"type": "integer", "default": 14},
    }, "required": ["log_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        lid = params["log_id"]; label = params.get("label", lid)
        log_name = f"/custom/__PROJECT__/{lid}"
        configs = [
            {"service": "logs", "action": "create_log_group",
             "params": {"logGroupName": log_name, "tags": {"Name": f"__PROJECT__-{lid}"}},
             "label": label, "resource_type": "aws_cloudwatch_logs",
             "resource_id_path": None,
             "delete_action": "delete_log_group", "delete_params": {"logGroupName": log_name}},
            {"service": "logs", "action": "put_retention_policy",
             "params": {"logGroupName": log_name, "retentionInDays": params.get("retention_days", 14)},
             "label": f"{label} — Retention", "resource_type": "aws_log_retention", "is_support": True},
        ]
        return ToolResult(node=ToolNode(id=lid, type="aws_cloudwatch_logs", label=label, config=ToolNodeConfig()), boto3_config={"logs": configs})


class CreateCloudTrailTool(BaseTool):
    name = "create_cloudtrail"
    description = "Create an AWS CloudTrail trail for API activity logging and auditing."
    category = "monitoring"
    parameters = {"type": "object", "properties": {
        "trail_id": {"type": "string"}, "label": {"type": "string"},
        "s3_bucket_ref": {"type": "string", "description": "S3 bucket resource ID for logs."},
        "multi_region": {"type": "boolean", "default": True},
    }, "required": ["trail_id", "label", "s3_bucket_ref"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        tid = params["trail_id"]; label = params.get("label", tid)
        configs = [{"service": "cloudtrail", "action": "create_trail",
            "params": {
                "Name": f"__PROJECT__-{tid}",
                "S3BucketName": f"__PROJECT__-{params['s3_bucket_ref']}",
                "IsMultiRegionTrail": params.get("multi_region", True),
                "EnableLogFileValidation": True,
                "IncludeGlobalServiceEvents": True,
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{tid}"}],
            },
            "label": label, "resource_type": "aws_cloudtrail",
            "resource_id_path": "TrailARN",
            "delete_action": "delete_trail", "delete_params": {"Name": f"__PROJECT__-{tid}"}}]
        return ToolResult(
            node=ToolNode(id=tid, type="aws_cloudtrail", label=label, config=ToolNodeConfig()),
            boto3_config={"cloudtrail": configs},
            edges=[{"from": tid, "to": params["s3_bucket_ref"], "label": "logs to"}])


class CreateConfigRuleTool(BaseTool):
    name = "create_config_rule"
    description = "Create an AWS Config rule for compliance monitoring."
    category = "monitoring"
    parameters = {"type": "object", "properties": {
        "config_id": {"type": "string"}, "label": {"type": "string"},
        "rule_name": {"type": "string", "default": "encrypted-volumes"},
    }, "required": ["config_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        cid = params["config_id"]; label = params.get("label", cid)
        rule = params.get("rule_name", "ENCRYPTED_VOLUMES").upper().replace("-", "_")
        configs = [{"service": "config", "action": "put_config_rule",
            "params": {"ConfigRule": {
                "ConfigRuleName": f"__PROJECT__-{cid}",
                "Source": {"Owner": "AWS", "SourceIdentifier": rule},
            }},
            "label": label, "resource_type": "aws_config_rule",
            "resource_id_path": None,
            "delete_action": "delete_config_rule",
            "delete_params": {"ConfigRuleName": f"__PROJECT__-{cid}"}}]
        return ToolResult(node=ToolNode(id=cid, type="aws_config", label=label, config=ToolNodeConfig()), boto3_config={"config": configs})


class CreateXRayGroupTool(BaseTool):
    name = "create_xray_group"
    description = "Create an AWS X-Ray group for distributed tracing."
    category = "monitoring"
    parameters = {"type": "object", "properties": {
        "xray_id": {"type": "string"}, "label": {"type": "string"},
        "filter_expression": {"type": "string", "default": "responsetime > 5"},
    }, "required": ["xray_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        xid = params["xray_id"]; label = params.get("label", xid)
        configs = [{"service": "xray", "action": "create_group",
            "params": {"GroupName": f"__PROJECT__-{xid}",
                "FilterExpression": params.get("filter_expression", "responsetime > 5"),
                "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{xid}"}]},
            "label": label, "resource_type": "aws_xray_group",
            "resource_id_path": "Group.GroupARN",
            "delete_action": "delete_group", "delete_params": {"GroupName": f"__PROJECT__-{xid}"}}]
        return ToolResult(node=ToolNode(id=xid, type="aws_xray", label=label, config=ToolNodeConfig()), boto3_config={"xray": configs})


class CreateHealthEventRuleTool(BaseTool):
    name = "create_health_event_rule"
    description = "Create an EventBridge rule to capture AWS Health events."
    category = "monitoring"
    parameters = {"type": "object", "properties": {
        "health_id": {"type": "string"}, "label": {"type": "string"},
    }, "required": ["health_id", "label"]}

    def execute(self, params: dict[str, Any]) -> ToolResult:
        hid = params["health_id"]; label = params.get("label", hid)
        configs = [{"service": "events", "action": "put_rule",
            "params": {"Name": f"__PROJECT__-{hid}", "Description": "Capture AWS Health events",
                "EventPattern": json.dumps({"source": ["aws.health"], "detail-type": ["AWS Health Event"]}),
                "State": "ENABLED", "Tags": [{"Key": "Name", "Value": f"__PROJECT__-{hid}"}]},
            "label": label, "resource_type": "aws_health_rule",
            "resource_id_path": "RuleArn",
            "delete_action": "delete_rule", "delete_params": {"Name": f"__PROJECT__-{hid}"}}]
        return ToolResult(node=ToolNode(id=hid, type="aws_health", label=label, config=ToolNodeConfig()), boto3_config={"events": configs})
