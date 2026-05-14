"""User state vector construction — profile + session.

State design (interview-defensible):

  PROFILE COMPONENTS (long-term, computed from full interaction history):
    - One-hot category preferences (5 dims, one per category)
    - Average price band the user transacts in (1 dim, log-scaled, normalized)
    - Lifetime add-to-cart count (1 dim, log-scaled)

  SESSION COMPONENTS (short-term, last N events in current session):
    - Last 5 viewed product categories, one-hot averaged (5 dims)
    - Session length so far in seconds (1 dim, log-scaled)
    - Number of products viewed this session (1 dim, log-scaled)

  COLD-START FALLBACK:
    - For users with no history, profile components are zeros, session is partial.
    - The network learns to handle this naturally because we generate cold-start
      training tuples during seeding.

Total dimensionality: 13. Small enough to train fast, large enough to
encode meaningful preference signal.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from uuid import UUID

import numpy as np
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.cart import CartEvent
from app.models.interaction import Interaction
from app.models.product import Product


# Must match the categories seeded in scripts/seed_amazon_catalogue.py
# Order matters — these are positional features in the state vector.
CATEGORY_INDEX = {
    "Electronics": 0,
    "Books": 1,
    "Home_and_Kitchen": 2,
    "Beauty_and_Personal_Care": 3,
    "Toys_and_Games": 4,
}
NUM_CATEGORIES = len(CATEGORY_INDEX)
STATE_DIM = NUM_CATEGORIES + 1 + 1 + NUM_CATEGORIES + 1 + 1  # = 13


def _safe_log_scale(x: float, ceiling: float = 1000.0) -> float:
    """Log-scaled normalisation to [0, 1]. Handles zero gracefully.

    log scaling is the right choice for counts and prices — these are
    long-tail distributions where linear scaling would compress 99% of
    users into the bottom 1% of the feature space.
    """
    return math.log1p(x) / math.log1p(ceiling)


def _category_vector(category: str | None) -> np.ndarray:
    """One-hot encode a category. Unknown/None → all zeros."""
    vec = np.zeros(NUM_CATEGORIES, dtype=np.float32)
    if category and category in CATEGORY_INDEX:
        vec[CATEGORY_INDEX[category]] = 1.0
    return vec


def build_user_state(
    db: Session,
    user_id: UUID | None,
    session_id: str,
    *,
    session_window_minutes: int = 30,
) -> np.ndarray:
    """Builds a (STATE_DIM,) float32 vector. Anonymous users get a zero-profile state.

    Anonymous handling: user_id=None returns profile components as zeros, session
    components computed from session_id-scoped interactions only. The state vector
    shape is unchanged so the network always sees the same input dimensionality.
    """
    state = np.zeros(STATE_DIM, dtype=np.float32)

    # === PROFILE COMPONENTS (zeros for anonymous users) ===
    if user_id is not None:
        # Lifetime category preferences from cart_events
        cart_history = db.execute(
            select(Product.category, CartEvent.action, CartEvent.quantity)
            .join(Product, CartEvent.product_id == Product.id)
            .where(CartEvent.user_id == user_id)
        ).all()

        category_counts = np.zeros(NUM_CATEGORIES, dtype=np.float32)
        total_adds = 0
        total_price_signal = 0.0
        price_count = 0
        for category, action, quantity in cart_history:
            if action == "add" and category in CATEGORY_INDEX:
                category_counts[CATEGORY_INDEX[category]] += quantity
                total_adds += quantity

        # Normalise category preferences to a probability vector
        if total_adds > 0:
            state[0:NUM_CATEGORIES] = category_counts / total_adds

        # Average price band — pull from products the user has added
        if total_adds > 0:
            price_rows = db.execute(
                select(Product.price)
                .join(CartEvent, CartEvent.product_id == Product.id)
                .where(CartEvent.user_id == user_id, CartEvent.action == "add")
            ).all()
            prices = [float(p[0]) for p in price_rows]
            if prices:
                avg_price = sum(prices) / len(prices)
                state[NUM_CATEGORIES] = _safe_log_scale(avg_price, ceiling=500.0)

        # Lifetime add count — log-scaled
        state[NUM_CATEGORIES + 1] = _safe_log_scale(total_adds, ceiling=100.0)

    # === SESSION COMPONENTS (always computed) ===
    session_window_start = datetime.now(timezone.utc) - timedelta(minutes=session_window_minutes)

    session_interactions = db.execute(
        select(Product.category, Interaction.occurred_at)
        .join(Product, Interaction.product_id == Product.id, isouter=True)
        .where(
            Interaction.session_id == session_id,
            Interaction.occurred_at >= session_window_start,
        )
        .order_by(desc(Interaction.occurred_at))
        .limit(5)
    ).all()

    if session_interactions:
        # Average category one-hots over the recent session events
        session_cat_vec = np.zeros(NUM_CATEGORIES, dtype=np.float32)
        for category, _ in session_interactions:
            session_cat_vec += _category_vector(category)
        session_cat_vec /= len(session_interactions)
        state[NUM_CATEGORIES + 2 : 2 * NUM_CATEGORIES + 2] = session_cat_vec

        # Session length in seconds
        oldest = session_interactions[-1][1]
        newest = session_interactions[0][1]
        if oldest and newest:
            session_length_s = (newest - oldest).total_seconds()
            state[2 * NUM_CATEGORIES + 2] = _safe_log_scale(session_length_s, ceiling=3600.0)

    # Total session interaction count
    session_count = db.scalar(
        select(Interaction.id)
        .where(
            Interaction.session_id == session_id,
            Interaction.occurred_at >= session_window_start,
        )
        .order_by(desc(Interaction.occurred_at))
        .limit(50)  # Cap for performance
    )
    if session_count is not None:
        # Re-query for actual count (the above just confirms existence)
        from sqlalchemy import func as sa_func
        actual_count = db.scalar(
            select(sa_func.count())
            .select_from(Interaction)
            .where(
                Interaction.session_id == session_id,
                Interaction.occurred_at >= session_window_start,
            )
        ) or 0
        state[2 * NUM_CATEGORIES + 3] = _safe_log_scale(actual_count, ceiling=50.0)

    return state