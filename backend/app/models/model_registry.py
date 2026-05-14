"""Model registry — versioned, evaluated, swappable trained models."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.episode import ModelEpisode


ALGORITHMS = ("dqn", "collab_filter", "popularity_baseline")


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    version: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False)

    hyperparameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(500), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    episodes: Mapped[list[ModelEpisode]] = relationship(
        back_populates="model", lazy="select"
    )

    __table_args__ = (
        CheckConstraint(
            f"algorithm IN {ALGORITHMS}",
            name="ck_model_registry_algorithm",
        ),
        Index(
            "ix_model_registry_active",
            "algorithm",
            postgresql_where=text("is_active = true"),
        ),
    )