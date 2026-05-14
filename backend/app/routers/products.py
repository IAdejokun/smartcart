"""Product endpoints — browse, search, detail.

These endpoints don't write to the DB. They're public (optional auth) so we can
later personalise the listing order based on the DRL agent for logged-in users
and fall back to popularity-ranked for anonymous traffic.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.product import (
    ProductDetail,
    ProductListResponse,
    ProductSummary,
)
from app.security.dependencies import get_optional_current_user


router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=ProductListResponse)
def list_products(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
    category: str | None = Query(default=None),
    search: str | None = Query(default=None, min_length=2),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ProductListResponse:
    """Paginated product browsing. Supports category filter and full-text search.

    Note: this endpoint stays popularity-ranked. The DRL personalised ordering
    lives at /recommendations — keeping browse and recommend as separate
    endpoints gives us a clean A/B comparison: same user, same query, two policies.
    """
    stmt = select(Product)
    count_stmt = select(func.count()).select_from(Product)

    if category:
        stmt = stmt.where(Product.category == category)
        count_stmt = count_stmt.where(Product.category == category)

    if search:
        # Simple ILIKE match for MVP. Postgres full-text search is a Sprint-N+ upgrade.
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(Product.title.ilike(pattern), Product.category.ilike(pattern))
        )
        count_stmt = count_stmt.where(
            or_(Product.title.ilike(pattern), Product.category.ilike(pattern))
        )

    # Popularity ranking by review count then rating — the cold-start baseline
    stmt = stmt.order_by(desc(Product.review_count), desc(Product.avg_rating))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    items = db.scalars(stmt).all()
    total = db.scalar(count_stmt) or 0

    return ProductListResponse(
        items=[ProductSummary.model_validate(p) for p in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/categories", response_model=list[str])
def list_categories(db: Session = Depends(get_db)) -> list[str]:
    """All distinct categories in the catalogue. Used by the storefront filter sidebar."""
    stmt = select(Product.category).distinct().order_by(Product.category)
    return list(db.scalars(stmt).all())


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: UUID, db: Session = Depends(get_db)) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    return product