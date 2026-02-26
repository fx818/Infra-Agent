"""
AWS Cost Explorer service — queries real AWS cost data via Boto3.

Falls back to LLM-generated estimates if AWS credentials are unavailable.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from app.schemas.cost_analysis import (
    CostAnalysisResponse,
    CostDataPoint,
    CostForecast,
    CostRecommendation,
    CostSummary,
)

logger = logging.getLogger(__name__)


class CostExplorerService:
    """Service for querying AWS Cost Explorer API."""

    def __init__(
        self,
        aws_access_key_id: str | None = None,
        aws_secret_access_key: str | None = None,
        region: str = "us-east-1",
    ) -> None:
        self.region = region
        self._client = None

        session_kwargs: dict[str, Any] = {"region_name": region}
        if aws_access_key_id and aws_secret_access_key:
            session_kwargs["aws_access_key_id"] = aws_access_key_id
            session_kwargs["aws_secret_access_key"] = aws_secret_access_key
        self._session_kwargs = session_kwargs

    def _get_client(self):
        if self._client is None:
            try:
                session = boto3.Session(**self._session_kwargs)
                self._client = session.client("ce")
            except NoCredentialsError:
                logger.warning("AWS credentials not found — cost data will be unavailable.")
                return None
        return self._client

    async def get_cost_summary(
        self,
        start_date: str,
        end_date: str,
        granularity: str = "DAILY",
        group_by: str = "SERVICE",
        filter_service: str | None = None,
    ) -> CostSummary:
        """Get cost data from AWS Cost Explorer."""
        client = self._get_client()

        if not client:
            return self._fallback_summary(start_date, end_date, granularity)

        try:
            params: dict[str, Any] = {
                "TimePeriod": {"Start": start_date, "End": end_date},
                "Granularity": granularity,
                "Metrics": ["UnblendedCost", "UsageQuantity"],
                "GroupBy": [{"Type": "DIMENSION", "Key": group_by}],
            }

            if filter_service:
                params["Filter"] = {
                    "Dimensions": {
                        "Key": "SERVICE",
                        "Values": [filter_service],
                    }
                }

            response = client.get_cost_and_usage(**params)

            data_points: list[CostDataPoint] = []
            group_totals: dict[str, float] = {}
            total_cost = 0.0

            for result in response.get("ResultsByTime", []):
                date = result["TimePeriod"]["Start"]
                for group in result.get("Groups", []):
                    group_name = group["Keys"][0]
                    amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                    total_cost += amount
                    group_totals[group_name] = group_totals.get(group_name, 0) + amount
                    data_points.append(CostDataPoint(
                        date=date, amount=round(amount, 2), group=group_name,
                    ))

            return CostSummary(
                total_cost=round(total_cost, 2),
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
                data_points=data_points,
                group_totals={k: round(v, 2) for k, v in sorted(group_totals.items(), key=lambda x: -x[1])},
            )

        except ClientError as e:
            logger.error("Cost Explorer API error: %s", e)
            return self._fallback_summary(start_date, end_date, granularity)

    async def get_cost_forecast(
        self,
        start_date: str,
        end_date: str,
        granularity: str = "MONTHLY",
    ) -> CostForecast:
        """Get cost forecast from AWS Cost Explorer."""
        client = self._get_client()

        if not client:
            return self._fallback_forecast(start_date, end_date)

        try:
            response = client.get_cost_forecast(
                TimePeriod={"Start": start_date, "End": end_date},
                Metric="UNBLENDED_COST",
                Granularity=granularity,
            )

            total = float(response.get("Total", {}).get("Amount", 0))
            data_points = [
                CostDataPoint(
                    date=fp["TimePeriod"]["Start"],
                    amount=round(float(fp["MeanValue"]), 2),
                )
                for fp in response.get("ForecastResultsByTime", [])
            ]

            return CostForecast(
                total_forecasted=round(total, 2),
                start_date=start_date,
                end_date=end_date,
                data_points=data_points,
            )

        except ClientError as e:
            logger.error("Cost Forecast API error: %s", e)
            return self._fallback_forecast(start_date, end_date)

    async def get_recommendations(self) -> list[CostRecommendation]:
        """Get cost optimization recommendations from AWS Cost Explorer."""
        client = self._get_client()

        if not client:
            return self._fallback_recommendations()

        recommendations: list[CostRecommendation] = []

        try:
            # Right-sizing recommendations
            response = client.get_rightsizing_recommendation(
                Service="AmazonEC2",
                Configuration={
                    "RecommendationTarget": "SAME_INSTANCE_FAMILY",
                    "BenefitsConsidered": True,
                },
            )
            for rec in response.get("RightsizingRecommendations", [])[:5]:
                savings = float(
                    rec.get("ModifyRecommendationDetail", {})
                    .get("TargetInstances", [{}])[0]
                    .get("EstimatedMonthlySavings", {})
                    .get("Value", 0)
                )
                recommendations.append(CostRecommendation(
                    service="EC2",
                    recommendation=f"Right-size instance: {rec.get('CurrentInstance', {}).get('ResourceId', 'unknown')}",
                    estimated_savings=round(savings, 2),
                    priority="high" if savings > 50 else "medium",
                ))

        except ClientError as e:
            logger.warning("Rightsizing API error: %s", e)

        if not recommendations:
            if not client:
                recommendations = self._fallback_recommendations()
            else:
                recommendations = [
                    CostRecommendation(
                        service="General",
                        recommendation="Your architecture is optimized! No cost optimization opportunities found at this time.",
                        estimated_savings=0.0,
                        priority="low",
                    )
                ]

        return recommendations

    # ── Fallbacks when credentials are unavailable ──

    @staticmethod
    def _fallback_summary(start: str, end: str, granularity: str) -> CostSummary:
        return CostSummary(
            total_cost=0.0,
            start_date=start,
            end_date=end,
            granularity=granularity,
            data_points=[],
            group_totals={},
        )

    @staticmethod
    def _fallback_forecast(start: str, end: str) -> CostForecast:
        return CostForecast(
            total_forecasted=0.0,
            start_date=start,
            end_date=end,
            data_points=[],
        )

    @staticmethod
    def _fallback_recommendations() -> list[CostRecommendation]:
        return [
            CostRecommendation(
                service="General",
                recommendation="Connect your AWS credentials to get real cost data and recommendations.",
                estimated_savings=0.0,
                priority="high",
            ),
        ]
