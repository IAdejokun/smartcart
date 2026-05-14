"""Model episode — a (state, action, reward, next_state, done) tuple."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.model_registry import ModelRegistry


class ModelEpisode(Base):
    __tablename__ = "model_episodes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    model_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("model_registry.id", ondelete="RESTRICT"),
        nullable=False,
    )

    state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    action: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reward: Mapped[float] = mapped_column(Float, nullable=False)
    next_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="episodes")
    model: Mapped[ModelRegistry] = relationship(back_populates="episodes")

    __table_args__ = (
        Index("ix_episodes_recorded_at", "recorded_at"),
        Index("ix_episodes_model_time", "model_id", "recorded_at"),
    )