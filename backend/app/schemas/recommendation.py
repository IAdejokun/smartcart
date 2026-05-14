"""Recommendation response schemas.

The shape is designed for the frontend's twin needs:
1. Render the products (so each item carries the full product summary)
2. Stamp the recommendation_context onto cart events (so attribution closes the loop)
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.product import ProductSummary


class RecommendationItem(BaseModel):
    """One recommended product, with its position and Q-value (where applicable)."""
    product: ProductSummary
    rank: int                                       # 0-indexed position in the shown list
    q_value: float | None = None                    # Populated for DRL, None for baseline


class RecommendationResponse(BaseModel):
    """Server returns this; frontend stamps the relevant fields back into cart_events."""
    model_config = ConfigDict(protected_namespaces=())

    policy: Literal["drl", "collab_filter", "organic"]
    model_id: UUID | None = None                    # None for baseline (no model)
    items: list[RecommendationItem]
    session_state_snapshot: dict = Field(default_factory=dict)