"""Cart schemas — add/remove actions and the recommendation_context payload.

The RecommendationContext is the bridge between user action and DRL reward
attribution. Every cart event stamps the recommendation that produced it
(or marks it as 'organic' if the product was browsed without a recommendation).
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecommendationContext(BaseModel):
    """Stamped onto cart_events.recommendation_context for reward attribution.

    Lets us answer: 'did this add-to-cart come from a DRL recommendation, the
    collaborative-filtering baseline, or organic browsing?' That's what makes
    the A/B dashboard possible.
    """
    # Disable Pydantic's `model_` namespace guard. We use 'model_id' to refer
    # to ML model identifiers, not Pydantic's internal methods. Same for any
    # future fields like model_version, model_path, etc.
    model_config = ConfigDict(protected_namespaces=())

    policy: Literal["drl", "collab_filter", "organic"] = "organic"
    model_id: UUID | None = None
    recommendation_rank: int | None = None
    shown_products: list[UUID] = Field(default_factory=list)
    session_state_snapshot: dict = Field(default_factory=dict)


class AddToCartRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(default=1, ge=1, le=99)
    session_id: str = Field(min_length=1, max_length=64)
    recommendation_context: RecommendationContext = Field(
        default_factory=RecommendationContext
    )


class RemoveFromCartRequest(BaseModel):
    product_id: UUID
    session_id: str = Field(min_length=1, max_length=64)


class CartItemResponse(BaseModel):
    """An aggregated view of what's currently in the user's cart."""
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    title: str
    price: float                                  # Computed: latest price * quantity
    quantity: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    item_count: int                               # Total quantity, not unique products
    subtotal: float