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
from app.models.project import Project
from app.models.user import User
from app.services.aws.cloudwatch import CloudWatchService
from app.services.terraform.state_manager import StateManager
from app.services.terraform.workspace_manager import WorkspaceManager

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

    Reads deployed resources from terraform state, then queries
    CloudWatch for each resource's metrics.
    """
    # Validate project ownership
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.user_id == current_user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check workspace state
    workspace_mgr = WorkspaceManager()
    state_mgr = StateManager()
    workspace_dir = workspace_mgr.get_workspace_path(project_id)

    if not state_mgr.has_state(workspace_dir):
        return {
            "project_id": project_id,
            "message": "No deployed infrastructure found. Deploy first.",
            "resources": [],
        }

    # Get deployed resources
    resources = state_mgr.get_resources(workspace_dir)

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

        # Map terraform resources to CloudWatch queryable format
        queryable_resources = []
        for res in resources:
            if res["type"] in ("aws_lambda_function", "aws_db_instance"):
                queryable_resources.append({
                    "type": "aws_lambda" if "lambda" in res["type"] else "aws_rds",
                    "name": res["attributes"].get("function_name") or res["attributes"].get("identifier") or res["name"],
                })

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
