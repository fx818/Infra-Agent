"""
Configuration Console API — user preferences, AWS credentials, region settings.
"""

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.security import decrypt_credentials, encrypt_credentials
from app.models.user import User
from app.schemas.user import AWSCredentials, UserPreferences, LLMConfig

router = APIRouter(prefix="/config", tags=["configuration"])


@router.get("/", response_model=UserPreferences)
async def get_config(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPreferences:
    """Get the current user's configuration preferences."""
    if current_user.preferences:
        return UserPreferences(**current_user.preferences)
    return UserPreferences()


@router.put("/", response_model=UserPreferences)
async def update_config(
    payload: UserPreferences,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPreferences:
    """Update the current user's configuration preferences."""
    current_user.preferences = payload.model_dump()
    await db.commit()
    return payload


@router.delete("/", response_model=UserPreferences)
async def reset_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserPreferences:
    """Reset configuration preferences to defaults."""
    current_user.preferences = {}
    await db.commit()
    return UserPreferences()


@router.put("/aws-credentials")
async def set_aws_credentials(
    payload: AWSCredentials,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """
    Store AWS credentials (encrypted).

    Supports access key + secret, or assume role via STS ARN.
    """
    # Encrypt and store
    creds_json = json.dumps(payload.model_dump())
    current_user.aws_credentials_encrypted = encrypt_credentials(creds_json)
    await db.commit()

    return {"message": "AWS credentials stored securely"}


@router.get("/aws-credentials/status")
async def check_aws_credentials(
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Check if AWS credentials are configured (without revealing them)."""
    has_creds = current_user.aws_credentials_encrypted is not None
    return {
        "configured": has_creds,
        "message": "AWS credentials are configured" if has_creds else "No AWS credentials set",
    }


@router.delete("/aws-credentials")
async def delete_aws_credentials(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Remove stored AWS credentials."""
    current_user.aws_credentials_encrypted = None
    await db.commit()
    return {"message": "AWS credentials removed"}


@router.get("/llm", response_model=LLMConfig)
async def get_llm_config(
    current_user: Annotated[User, Depends(get_current_user)],
) -> LLMConfig:
    """Get the current user's LLM configuration."""
    # prefs = current_user.preferences or {}  # Not actually used here
    llm_prefs = current_user.llm_preferences or {}
    
    # Decrypt API key if present
    api_key_encrypted = current_user.llm_api_key_encrypted
    api_key = decrypt_credentials(api_key_encrypted) if api_key_encrypted else None

    # Mask API key for security
    masked_key = f"sk-...{api_key[-4:]}" if api_key and len(api_key) > 4 else None

    return LLMConfig(
        api_key=masked_key,  # Don't return full key
        base_url=llm_prefs.get("base_url", "https://api.openai.com/v1"),
        model=llm_prefs.get("model", "gpt-4o"),
    )


@router.put("/llm", response_model=LLMConfig)
async def update_llm_config(
    payload: LLMConfig,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> LLMConfig:
    """Update the current user's LLM configuration."""
    # 1. Update preferences (model, base_url)
    current_prefs = current_user.llm_preferences or {}
    current_prefs["base_url"] = payload.base_url
    current_prefs["model"] = payload.model
    current_user.llm_preferences = current_prefs

    # 2. Update API Key if provided (ignore masked values)
    if payload.api_key and not payload.api_key.startswith("sk-..."):
        current_user.llm_api_key_encrypted = encrypt_credentials(payload.api_key)

    await db.commit()

    # Return masked/updated config
    return await get_llm_config(current_user)


@router.delete("/llm")
async def reset_llm_config(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> dict:
    """Reset LLM configuration."""
    current_user.llm_api_key_encrypted = None
    current_user.llm_preferences = {}
    await db.commit()
    return {"message": "LLM configuration reset"}
