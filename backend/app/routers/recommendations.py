"""Recommendation endpoint — serves the policy server.

Two endpoints:
- GET /recommendations: A/B-randomised, primary path. The dashboard reads from
  this to compare DRL vs CF.
- GET /recommendations/drl: forces DRL. Used for debugging and demo control.

Anonymous users get baseline-only (CF on empty cart → popularity).
The optional auth dependency lets the storefront call this endpoint regardless
of login state.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.policy_server import get_policy_server
from app.ml.state_builder import build_user_state
from app.models.cart import CartEvent
from app.models.product import Product
from app.models.user import User
from app.schemas.product import ProductSummary
from app.schemas.recommendation import RecommendationItem, RecommendationResponse
from app.security.dependencies import get_optional_current_user


log = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _current_cart_product_ids(db: Session, user: User) -> list[UUID]:
    """Lightweight cart contents lookup for baseline input.

    Returns deduplicated product IDs currently in the user's cart (positive net
    quantity). We don't need the full cart computation here — just the set of
    product IDs the CF baseline should compute similarity against.
    """
    rows = db.execute(
        select(CartEvent.product_id, CartEvent.action, CartEvent.quantity)
        .where(CartEvent.user_id == user.id)
        .order_by(CartEvent.occurred_at)
    ).all()

    net: dict = {}
    for product_id, action, qty in rows:
        if action == "add":
            net[product_id] = net.get(product_id, 0) + qty
        elif action == "remove":
            net[product_id] = net.get(product_id, 0) - qty
        elif action == "update_quantity":
            net[product_id] = qty
    return [pid for pid, qty in net.items() if qty > 0]


@router.get("", response_model=RecommendationResponse)
def get_recommendations(
    request: Request,
    session_id: str = Query(min_length=1, max_length=64),
    top_k: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> RecommendationResponse:
    """A/B-randomised recommendations.

    For anonymous users, always returns baseline. For authenticated users,
    50/50 split DRL vs CF — frontend doesn't know which it got, only the
    attribution payload reveals it.
    """
    server = get_policy_server()
    server.maybe_refresh(db)

    state = build_user_state(
        db,
        user_id=current_user.id if current_user else None,
        session_id=session_id,
    )

    if current_user is None:
        # Anonymous: baseline only
        product_uuids = server.recommend_baseline(cart_product_ids=[], top_k=top_k)
        policy: str = "collab_filter"
        q_values: list[float] = []
        model_id: UUID | None = None
    else:
        cart_pids = _current_cart_product_ids(db, current_user)
        policy, product_uuids, q_values, model_id = server.recommend_auto(
            state=state,
            cart_product_ids=cart_pids,
            top_k=top_k,
        )

    products = db.scalars(
        select(Product).where(Product.id.in_(product_uuids))
    ).all()
    products_by_id = {p.id: p for p in products}

    # Preserve the policy's ranking order — DB doesn't guarantee order from IN()
    items: list[RecommendationItem] = []
    for rank, pid in enumerate(product_uuids):
        product = products_by_id.get(pid)
        if product is None:
            continue                                                  # product deleted between recommend and serialize
        items.append(
            RecommendationItem(
                product=ProductSummary.model_validate(product),
                rank=rank,
                q_value=q_values[rank] if rank < len(q_values) else None,
            )
        )

    return RecommendationResponse(
        policy=policy,                                                # type: ignore[arg-type]
        model_id=model_id,
        items=items,
        session_state_snapshot={
            "state_vec": state.tolist(),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )