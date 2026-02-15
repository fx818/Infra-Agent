"""
AWS CloudWatch integration — fetches performance metrics for deployed resources.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

logger = logging.getLogger(__name__)


class CloudWatchService:
    """
    Fetches CloudWatch metrics for deployed AWS resources.

    Returns structured JSON summaries of resource health,
    performance metrics, and downtime information.
    """

    def __init__(
        self,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region_name: str = "us-east-1",
    ) -> None:
        session_kwargs: dict[str, Any] = {"region_name": region_name}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key

        self.session = boto3.Session(**session_kwargs)
        self.cloudwatch = self.session.client("cloudwatch")

    async def get_lambda_metrics(
        self,
        function_name: str,
        period_hours: int = 24,
    ) -> dict[str, Any]:
        """
        Get Lambda function metrics.

        Returns invocations, errors, duration, and throttles.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=period_hours)

        metrics = {}
        metric_names = ["Invocations", "Errors", "Duration", "Throttles"]

        for metric_name in metric_names:
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace="AWS/Lambda",
                    MetricName=metric_name,
                    Dimensions=[{"Name": "FunctionName", "Value": function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,  # 1 hour
                    Statistics=["Sum", "Average", "Maximum"],
                )
                datapoints = response.get("Datapoints", [])
                if datapoints:
                    latest = sorted(datapoints, key=lambda d: d["Timestamp"])[-1]
                    metrics[metric_name.lower()] = {
                        "sum": latest.get("Sum", 0),
                        "average": latest.get("Average", 0),
                        "maximum": latest.get("Maximum", 0),
                    }
                else:
                    metrics[metric_name.lower()] = {"sum": 0, "average": 0, "maximum": 0}
            except (ClientError, NoCredentialsError) as e:
                logger.error("Failed to get %s metric: %s", metric_name, e)
                metrics[metric_name.lower()] = {"error": str(e)}

        return {
            "service": "lambda",
            "resource": function_name,
            "period_hours": period_hours,
            "metrics": metrics,
        }

    async def get_rds_metrics(
        self,
        db_instance_id: str,
        period_hours: int = 24,
    ) -> dict[str, Any]:
        """Get RDS instance metrics: CPU, connections, storage."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=period_hours)

        metrics = {}
        metric_configs = [
            ("CPUUtilization", ["Average", "Maximum"]),
            ("DatabaseConnections", ["Sum", "Average"]),
            ("FreeStorageSpace", ["Average"]),
            ("ReadLatency", ["Average"]),
            ("WriteLatency", ["Average"]),
        ]

        for metric_name, stats in metric_configs:
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace="AWS/RDS",
                    MetricName=metric_name,
                    Dimensions=[{"Name": "DBInstanceIdentifier", "Value": db_instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=stats,
                )
                datapoints = response.get("Datapoints", [])
                if datapoints:
                    latest = sorted(datapoints, key=lambda d: d["Timestamp"])[-1]
                    metrics[metric_name.lower()] = {
                        s.lower(): latest.get(s, 0) for s in stats
                    }
                else:
                    metrics[metric_name.lower()] = {s.lower(): 0 for s in stats}
            except (ClientError, NoCredentialsError) as e:
                logger.error("Failed to get %s metric: %s", metric_name, e)
                metrics[metric_name.lower()] = {"error": str(e)}

        return {
            "service": "rds",
            "resource": db_instance_id,
            "period_hours": period_hours,
            "metrics": metrics,
        }

    async def get_resource_health_summary(
        self,
        resources: list[dict[str, str]],
        period_hours: int = 24,
    ) -> dict[str, Any]:
        """
        Get a health summary for a list of deployed resources.

        Args:
            resources: List of {"type": "aws_lambda", "name": "my-func"} dicts.
            period_hours: Look-back period in hours.

        Returns:
            Structured health summary with per-resource metrics.
        """
        summary: dict[str, Any] = {
            "period_hours": period_hours,
            "resources": [],
            "overall_health": "healthy",
        }

        for resource in resources:
            resource_type = resource.get("type", "")
            resource_name = resource.get("name", "")

            try:
                if resource_type == "aws_lambda":
                    metrics = await self.get_lambda_metrics(resource_name, period_hours)
                elif resource_type == "aws_rds":
                    metrics = await self.get_rds_metrics(resource_name, period_hours)
                else:
                    metrics = {
                        "service": resource_type,
                        "resource": resource_name,
                        "metrics": {"note": "Metrics not yet supported for this service type"},
                    }

                summary["resources"].append(metrics)
            except Exception as e:
                logger.error("Failed to get metrics for %s/%s: %s", resource_type, resource_name, e)
                summary["resources"].append({
                    "service": resource_type,
                    "resource": resource_name,
                    "error": str(e),
                })
                summary["overall_health"] = "degraded"

        return summary
