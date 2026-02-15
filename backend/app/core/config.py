"""
Centralized application configuration.

All settings are loaded from environment variables / .env file.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "NL2I Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./nl2i.db"

    # ── Redis ────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth / JWT ───────────────────────────────────────
    SECRET_KEY: str = "change-me-to-a-random-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # ── LLM Provider ────────────────────────────────────
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"

    # ── AWS ──────────────────────────────────────────────
    AWS_DEFAULT_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # ── Terraform ────────────────────────────────────────
    TERRAFORM_WORKSPACES_DIR: str = "./workspaces"

    # ── Credential Encryption ────────────────────────────
    CREDENTIAL_ENCRYPTION_KEY: str = "change-me-to-a-32-byte-base64-key"

    @property
    def workspaces_path(self) -> Path:
        """Resolved absolute path for terraform workspaces."""
        return Path(self.TERRAFORM_WORKSPACES_DIR).resolve()


settings = Settings()
