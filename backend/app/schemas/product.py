"""Product schemas — list, detail, search response."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductSummary(BaseModel):
    """Slim product record for grid views and recommendation tiles.

    extra_data is included so the frontend can render product images. We keep
    the Pydantic model permissive (extra_data: dict) and let the frontend's
    TypeScript types narrow the expected shape.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asin: str
    title: str
    category: str
    price: Decimal
    avg_rating: float
    review_count: int
    extra_data: dict = Field(default_factory=dict)


class ProductDetail(ProductSummary):
    """Same as ProductSummary for now — kept distinct for future divergence."""
    pass


class ProductListResponse(BaseModel):
    items: list[ProductSummary]
    total: int
    page: int
    page_size: int