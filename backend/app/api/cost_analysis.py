"""
Cost Analysis API routes — real-time cost data from AWS Cost Explorer.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.cost_analysis import (
    CostAnalysisResponse,
    CostForecastRequest,
    CostQueryRequest,
)
from app.services.aws.cost_explorer import CostExplorerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cost-analysis", tags=["cost-analysis"])


def _get_cost_service() -> CostExplorerService:
    """Create a CostExplorerService with credentials from settings."""
    return CostExplorerService(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region=settings.AWS_DEFAULT_REGION,
    )


@router.post("/summary", response_model=CostAnalysisResponse)
async def get_cost_summary(
    payload: CostQueryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get cost summary from AWS Cost Explorer."""
    try:
        service = _get_cost_service()
        summary = await service.get_cost_summary(
            start_date=payload.start_date,
            end_date=payload.end_date,
            granularity=payload.granularity,
            group_by=payload.group_by,
            filter_service=payload.filter_service,
        )
        recommendations = await service.get_recommendations()

        return CostAnalysisResponse(
            summary=summary,
            recommendations=recommendations,
        ).model_dump()

    except Exception as e:
        logger.exception("Cost summary failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost data: {str(e)}",
        )


@router.post("/forecast", response_model=CostAnalysisResponse)
async def get_cost_forecast(
    payload: CostForecastRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get cost forecast from AWS Cost Explorer."""
    try:
        service = _get_cost_service()
        forecast = await service.get_cost_forecast(
            start_date=payload.start_date,
            end_date=payload.end_date,
            granularity=payload.granularity,
        )

        return CostAnalysisResponse(forecast=forecast).model_dump()

    except Exception as e:
        logger.exception("Cost forecast failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get forecast: {str(e)}",
        )


@router.get("/recommendations", response_model=CostAnalysisResponse)
async def get_cost_recommendations(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get cost optimization recommendations."""
    try:
        service = _get_cost_service()
        recommendations = await service.get_recommendations()
        return CostAnalysisResponse(recommendations=recommendations).model_dump()

    except Exception as e:
        logger.exception("Cost recommendations failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}",
        )

