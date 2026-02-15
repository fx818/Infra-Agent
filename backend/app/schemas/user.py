"""
Pydantic schemas for User operations.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AWSCredentials(BaseModel):
    """AWS credential input from user."""
    aws_access_key_id: str = Field(..., min_length=16)
    aws_secret_access_key: str = Field(..., min_length=16)
    aws_session_token: str | None = None
    assume_role_arn: str | None = None


class UserPreferences(BaseModel):
    """User configuration preferences."""
    default_region: str = "us-east-1"
    default_vpc: bool = True
    naming_convention: str = "kebab-case"  # kebab-case, snake_case, camelCase
    tags: dict[str, str] = Field(default_factory=dict)


class LLMConfig(BaseModel):
    """LLM configuration settings."""
    api_key: str | None = Field(None, description="OpenAI-compatible API Key")
    base_url: str = Field("https://api.openai.com/v1", description="LLM Base URL")
    model: str = Field("gpt-4o", description="Model name (e.g. gpt-4o, claude-3-opus)")

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: str
    preferences: UserPreferences | None = None
    llm_config: LLMConfig | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"

