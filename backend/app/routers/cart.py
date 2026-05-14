"""Cart endpoints — the reward-emitting hot path.

Every add/remove writes to cart_events. The recommendation_context is stamped
on every event, providing the attribution data that feeds the A/B dashboard
and (eventually) the DRL trainer's reward computation.

Cart state is computed on-demand from cart_events rather than stored as a
separate aggregate. This keeps cart_events as the unambiguous source of truth
and means there's no aggregate-vs-event drift to debug.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import BackgroundTasks
from app.ml.episode_writer import write_cart_episode
from app.ml.state_builder import build_user_state
from app.ml.trainer import maybe_trigger_training      # we'll define this in 6.3


from app.database import get_db
from app.models.cart import CartEvent
from app.models.product import Product
from app.models.user import User
from app.schemas.cart import (
    AddToCartRequest,
    CartItemResponse,
    CartResponse,
    RemoveFromCartRequest,
)
from app.security.dependencies import get_current_active_user


router = APIRouter(prefix="/cart", tags=["cart"])


def _compute_current_cart(db: Session, user: User) -> CartResponse:
    """Replays this user's cart_events to compute current cart state.

    Aggregation rule: net quantity per product = sum(adds) - sum(removes).
    Items with net quantity <= 0 are excluded. Items are joined with the
    products table for current price and title — historical prices are not
    preserved (that's a separate audit concern, not a cart concern).
    """
    stmt = (
        select(CartEvent.product_id, CartEvent.action, CartEvent.quantity)
        .where(CartEvent.user_id == user.id)
        .order_by(CartEvent.occurred_at)
    )
    rows = db.execute(stmt).all()

    # Reduce to net quantity per product
    net_by_product: dict = defaultdict(int)
    for product_id, action, quantity in rows:
        if action == "add":
            net_by_product[product_id] += quantity
        elif action == "remove":
            net_by_product[product_id] -= quantity
        elif action == "update_quantity":
            net_by_product[product_id] = quantity                # Absolute, not relative

    active_product_ids = [pid for pid, qty in net_by_product.items() if qty > 0]
    if not active_product_ids:
        return CartResponse(items=[], item_count=0, subtotal=0.0)

    products = db.scalars(
        select(Product).where(Product.id.in_(active_product_ids))
    ).all()
    products_by_id = {p.id: p for p in products}

    items: list[CartItemResponse] = []
    subtotal = Decimal("0.00")
    item_count = 0
    for product_id in active_product_ids:
        product = products_by_id.get(product_id)
        if product is None:                                       # Product was deleted from catalogue
            continue
        qty = net_by_product[product_id]
        line_total = product.price * qty
        subtotal += line_total
        item_count += qty
        items.append(
            CartItemResponse(
                product_id=product.id,
                title=product.title,
                price=float(line_total),
                quantity=qty,
            )
        )

    return CartResponse(items=items, item_count=item_count, subtotal=float(subtotal))


@router.get("", response_model=CartResponse)
def get_cart(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartResponse:
    return _compute_current_cart(db, current_user)


@router.post("/add", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: AddToCartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartResponse:
    """Append an 'add' cart event AND emit a training episode."""
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # CRITICAL: capture state BEFORE writing the cart event, otherwise the
    # tuple's "state" already reflects the action being taken
    pre_event_state = build_user_state(
        db,
        user_id=current_user.id,
        session_id=payload.session_id,
    )

    event = CartEvent(
        user_id=current_user.id,
        product_id=payload.product_id,
        action="add",
        quantity=payload.quantity,
        session_id=payload.session_id,
        recommendation_context=payload.recommendation_context.model_dump(mode="json"),
    )
    db.add(event)
    db.commit()

    # Episode writeback — synchronous so the next_state captures this event
    write_cart_episode(
        db,
        user_id=current_user.id,
        session_id=payload.session_id,
        product_id=payload.product_id,
        action="add",
        recommendation_context=payload.recommendation_context.model_dump(mode="json"),
        pre_event_state=pre_event_state,
    )
    db.commit()

    # Trainer trigger — runs as background task to avoid blocking the response
    background_tasks.add_task(maybe_trigger_training, "cart_event")

    return _compute_current_cart(db, current_user)


@router.post("/remove", response_model=CartResponse)
def remove_from_cart(
    payload: RemoveFromCartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> CartResponse:
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    current_cart = _compute_current_cart(db, current_user)
    current_qty = next(
        (item.quantity for item in current_cart.items if item.product_id == payload.product_id),
        0,
    )
    if current_qty <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product is not in cart",
        )

    pre_event_state = build_user_state(
        db,
        user_id=current_user.id,
        session_id=payload.session_id,
    )

    event = CartEvent(
        user_id=current_user.id,
        product_id=payload.product_id,
        action="remove",
        quantity=current_qty,
        session_id=payload.session_id,
        recommendation_context={},
    )
    db.add(event)
    db.commit()

    write_cart_episode(
        db,
        user_id=current_user.id,
        session_id=payload.session_id,
        product_id=payload.product_id,
        action="remove",
        recommendation_context={},
        pre_event_state=pre_event_state,
    )
    db.commit()

    background_tasks.add_task(maybe_trigger_training, "cart_event")

    return _compute_current_cart(db, current_user)