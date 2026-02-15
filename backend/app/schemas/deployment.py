"""
Pydantic schemas for Deployment operations.
"""

from datetime import datetime

from pydantic import BaseModel


class DeployRequest(BaseModel):
    """Request to deploy or destroy infrastructure."""
    action: str = "apply"  # plan, apply, destroy


class DeploymentResponse(BaseModel):
    """Deployment status response."""
    id: int
    project_id: int
    architecture_version: int
    action: str
    status: str
    logs: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
