"""
Pydantic schemas for the Cost Analysis feature.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CostQueryRequest(BaseModel):
    """Request body for querying AWS cost data."""
    start_date: str = Field(..., description="Start date in YYYY-MM-DD format.")
    end_date: str = Field(..., description="End date in YYYY-MM-DD format.")
    granularity: str = Field(default="DAILY", description="DAILY, MONTHLY, or HOURLY.")
    group_by: str = Field(default="SERVICE", description="Dimension to group by: SERVICE, REGION, USAGE_TYPE, etc.")
    filter_service: str | None = Field(default=None, description="Optional filter to a specific AWS service.")


class CostDataPoint(BaseModel):
    """A single cost data point."""
    date: str
    amount: float
    unit: str = "USD"
    group: str = ""


class CostSummary(BaseModel):
    """Summary of cost data for a given period."""
    total_cost: float
    currency: str = "USD"
    start_date: str
    end_date: str
    granularity: str
    data_points: list[CostDataPoint] = Field(default_factory=list)
    group_totals: dict[str, float] = Field(default_factory=dict, description="Totals grouped by the group_by dimension.")


class CostForecastRequest(BaseModel):
    """Request body for cost forecasting."""
    start_date: str = Field(..., description="Forecast start (YYYY-MM-DD).")
    end_date: str = Field(..., description="Forecast end (YYYY-MM-DD).")
    granularity: str = Field(default="MONTHLY")


class CostForecast(BaseModel):
    """Forecasted cost data."""
    total_forecasted: float
    currency: str = "USD"
    start_date: str
    end_date: str
    data_points: list[CostDataPoint] = Field(default_factory=list)


class CostRecommendation(BaseModel):
    """A cost optimization recommendation."""
    service: str
    recommendation: str
    estimated_savings: float = 0.0
    priority: str = Field(default="medium", description="low, medium, high")


class CostAnalysisResponse(BaseModel):
    """Full cost analysis response combining summary, forecast, and recommendations."""
    summary: CostSummary | None = None
    forecast: CostForecast | None = None
    recommendations: list[CostRecommendation] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
