"""
Architecture ORM model (versioned).
"""

import datetime
from sqlalchemy import Integer, Text, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Architecture(Base):
    __tablename__ = "architectures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # JSON blobs
    intent_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    graph_json: Mapped[dict] = mapped_column(JSON, nullable=False)  # {nodes: [...], edges: [...]}
    terraform_files_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # {"main.tf": "...", ...}
    cost_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    visual_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="architectures")  # noqa: F821
