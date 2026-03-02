"""
Cost Analysis API routes — real-time cost data from AWS Cost Explorer.
Uses per-user AWS credentials (decrypted from aws_credentials_encrypted).
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.core.security import decrypt_credentials
from app.models.user import User
from app.schemas.cost_analysis import (
    CostAnalysisResponse,
    CostForecastRequest,
    CostQueryRequest,
)
from app.services.aws.cost_explorer import CostExplorerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cost-analysis", tags=["cost-analysis"])


def _get_cost_service_for_user(current_user: User) -> CostExplorerService:
    """Create a CostExplorerService using the current user's AWS credentials."""
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    if current_user.aws_credentials_encrypted:
        try:
            creds = json.loads(decrypt_credentials(current_user.aws_credentials_encrypted))
            aws_access_key_id = creds.get("aws_access_key_id")
            aws_secret_access_key = creds.get("aws_secret_access_key")
        except Exception as e:
            logger.warning("Failed to decrypt user credentials for cost analysis: %s", e)

    # Cost Explorer is a global service — always use us-east-1
    return CostExplorerService(
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region="us-east-1",
    )


@router.post("/summary", response_model=CostAnalysisResponse)
async def get_cost_summary(
    payload: CostQueryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Get cost summary from AWS Cost Explorer."""
    try:
        service = _get_cost_service_for_user(current_user)
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
        service = _get_cost_service_for_user(current_user)
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
        service = _get_cost_service_for_user(current_user)
        recommendations = await service.get_recommendations()
        return CostAnalysisResponse(recommendations=recommendations).model_dump()

    except Exception as e:
        logger.exception("Cost recommendations failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recommendations: {str(e)}",
        )


@router.get("/services")
async def list_aws_services(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Return distinct AWS service names from the user's billing data (last 3 months)."""
    from datetime import date, timedelta
    today = date.today()
    start = (today.replace(day=1) - timedelta(days=90)).replace(day=1).isoformat()
    end = today.isoformat()
    try:
        service = _get_cost_service_for_user(current_user)
        summary = await service.get_cost_summary(
            start_date=start, end_date=end, granularity="MONTHLY", group_by="SERVICE",
        )
        services = [svc for svc, cost in summary.group_totals.items() if cost > 0]
        return {"services": services}
    except Exception as e:
        logger.warning("Could not fetch service list: %s", e)
        return {"services": []}

