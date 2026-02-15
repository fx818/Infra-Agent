"""
Pydantic schemas for Chat operations.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    """Schema for creating a chat message."""
    content: str = Field(..., min_length=1)


class ChatMessageResponse(BaseModel):
    """Schema for chat message response."""
    id: int
    project_id: int
    role: str
    content: str
    architecture_version: int | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
