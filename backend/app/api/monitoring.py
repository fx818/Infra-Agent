"""
Monitoring API routes — infrastructure performance metrics.
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import decrypt_credentials
from app.models.deployment import Deployment
from app.models.project import Project
from app.models.user import User
from app.services.aws.cloudwatch import CloudWatchService
from app.services.boto3.state_tracker import StateTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["monitoring"])


@router.get("/{project_id}/metrics")
async def get_project_metrics(
    project_id: int,
    period_hours: int = 24,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
    current_user: Annotated[User, Depends(get_current_user)] = None,
) -> dict:
    """
    Get infrastructure performance metrics for a deployed project.

    Reads deployed resources from the database state tracker, then queries
    CloudWatch for each resource's metrics.
    """
    # Validate project ownership
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Get deployed resources from DB state tracker
    state_tracker = StateTracker(db)

    # Find the latest successful deployment
    dep_result = await db.execute(
        select(Deployment)
        .where(Deployment.project_id == project_id, Deployment.status.in_(["success", "deployed", "partial_deployed"]))
        .order_by(Deployment.created_at.desc())
        .limit(1)
    )
    deployment = dep_result.scalar_one_or_none()

    if not deployment:
        return {
            "project_id": project_id,
            "message": "No deployed infrastructure found. Deploy first.",
            "resources": [],
        }

    resources = state_tracker.get_resources(deployment)

    if not resources:
        return {
            "project_id": project_id,
            "message": "No resource state found. Deploy first.",
            "resources": [],
        }

    # Get AWS credentials
    aws_creds = {}
    if current_user.aws_credentials_encrypted:
        try:
            aws_creds = json.loads(decrypt_credentials(current_user.aws_credentials_encrypted))
        except Exception as e:
            logger.error("Failed to decrypt AWS credentials: %s", e)

    # Query CloudWatch
    try:
        cw_service = CloudWatchService(
            aws_access_key_id=aws_creds.get("aws_access_key_id"),
            aws_secret_access_key=aws_creds.get("aws_secret_access_key"),
            region_name=project.region,
        )

        # Map resources to CloudWatch queryable format
        queryable_resources = []
        for res in resources:
            res_type = res.get("resource_type", "")
            res_id = res.get("resource_id", "")
            if "lambda" in res_type:
                queryable_resources.append({"type": "aws_lambda", "name": res_id})
            elif "rds" in res_type or "db_instance" in res_type:
                queryable_resources.append({"type": "aws_rds", "name": res_id})
            elif "ec2" in res_type or "instance" in res_type:
                queryable_resources.append({"type": "aws_ec2", "name": res_id})
            elif "s3" in res_type:
                queryable_resources.append({"type": "aws_s3", "name": res_id})

        summary = await cw_service.get_resource_health_summary(queryable_resources, period_hours)
        summary["project_id"] = project_id
        summary["total_resources_in_state"] = len(resources)
        summary["resources"] = resources
        return summary

    except Exception as e:
        logger.error("Failed to get metrics: %s", e)
        return {
            "project_id": project_id,
            "error": str(e),
            "message": "Failed to fetch CloudWatch metrics. Check AWS credentials.",
            "total_resources_in_state": len(resources),
            "resources": resources,
        }
