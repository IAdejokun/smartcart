"""Cart event model — high-intent signal, the source of DRL reward."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.product import Product


CART_ACTIONS = ("add", "remove", "update_quantity")


class CartEvent(Base):
    __tablename__ = "cart_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)

    recommendation_context: Mapped[dict] = mapped_column(
        JSONB, default=dict, nullable=False
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[User] = relationship(back_populates="cart_events")
    product: Mapped[Product] = relationship(back_populates="cart_events")

    __table_args__ = (
        CheckConstraint(
            f"action IN {CART_ACTIONS}",
            name="ck_cart_events_action",
        ),
        Index("ix_cart_events_user_action_time", "user_id", "action", "occurred_at"),
        Index(
            "ix_cart_events_recommendation_context",
            "recommendation_context",
            postgresql_using="gin",
        ),
    )