"""
Pydantic schemas for Project operations.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    region: str = "us-east-1"
    natural_language_input: str | None = None


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: int
    name: str
    description: str | None = None
    status: str
    region: str
    natural_language_input: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class ProjectGenerateRequest(BaseModel):
    """Request to generate architecture from natural language."""
    natural_language_input: str = Field(..., min_length=10)


class ProjectEditRequest(BaseModel):
    """Request to edit existing architecture."""
    modification_prompt: str = Field(..., min_length=5)
