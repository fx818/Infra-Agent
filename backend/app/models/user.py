"""
User ORM model.
"""

import datetime
from sqlalchemy import Integer, String, Text, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Encrypted JSON blob: {"aws_access_key_id": "...", "aws_secret_access_key": "..."}
    aws_credentials_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON blob of user preferences (region, default VPC, naming conventions, etc.)
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Encrypted LLM API Key
    llm_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # JSON blob for LLM preferences: {"model": "gpt-4", "base_url": "..."}
    llm_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(  # noqa: F821
        "Project", back_populates="user", cascade="all, delete-orphan"
    )
