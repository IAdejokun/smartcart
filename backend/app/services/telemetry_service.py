"""Telemetry computation — the four dashboard metrics."""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, case, func, select
from sqlalchemy.orm import Session

from app.models.cart import CartEvent
from app.models.episode import ModelEpisode
from app.models.model_registry import ModelRegistry


def _window_start(window: str) -> datetime:
    now = datetime.now(timezone.utc)
    if window == "1h":
        return now - timedelta(hours=1)
    if window == "24h":
        return now - timedelta(hours=24)
    if window == "7d":
        return now - timedelta(days=7)
    return datetime(1970, 1, 1, tzinfo=timezone.utc)


# ============================================================
# 1. Conversion rate per policy
# ============================================================

def conversion_by_policy(db: Session, window: str = "24h") -> list[dict]:
    """For each policy, count shown vs converted (add_to_cart).

    Uses a SQLAlchemy case() expression to guard against malformed
    recommendation_context — only call jsonb_array_length when shown_products
    is actually an array. Rows where it's missing or scalar contribute 0.
    """
    start = _window_start(window)

    # Defensive shown-count: array_length(shown_products) only when it's actually an array
    shown_products_expr = CartEvent.recommendation_context["shown_products"]
    n_shown_expr = case(
        (
            func.jsonb_typeof(shown_products_expr) == "array",
            func.jsonb_array_length(shown_products_expr),
        ),
        else_=0,
    ).label("n_shown")

    rows = db.execute(
        select(
            CartEvent.recommendation_context["policy"].astext.label("policy"),
            CartEvent.action,
            n_shown_expr,
        )
        .where(CartEvent.occurred_at >= start)
    ).all()

    stats: dict[str, dict[str, int]] = {
        "drl": {"shown": 0, "converted": 0},
        "collab_filter": {"shown": 0, "converted": 0},
        "organic": {"shown": 0, "converted": 0},
    }

    for policy, action, n_shown in rows:
        policy = policy or "organic"
        if policy not in stats:
            continue
        if action == "add":
            stats[policy]["converted"] += 1
            stats[policy]["shown"] += int(n_shown or 0)

    out = []
    for policy, s in stats.items():
        rate = (s["converted"] / s["shown"]) if s["shown"] > 0 else 0.0
        out.append({
            "policy": policy,
            "shown": s["shown"],
            "converted": s["converted"],
            "rate": round(rate, 4),
        })
    return out


# ============================================================
# 2. Average reward per policy
# ============================================================

def avg_reward_by_policy(db: Session, window: str = "24h") -> list[dict]:
    """Average non-zero reward per policy from model_episodes."""
    start = _window_start(window)

    rows = db.execute(
        select(
            ModelRegistry.algorithm.label("algorithm"),
            func.avg(ModelEpisode.reward).label("avg_reward"),
            func.count(ModelEpisode.id).label("n_episodes"),
        )
        .join(ModelRegistry, ModelEpisode.model_id == ModelRegistry.id)
        .where(
            ModelEpisode.recorded_at >= start,
            ModelEpisode.reward != 0.0,
        )
        .group_by(ModelRegistry.algorithm)
    ).all()

    return [
        {
            "policy": "drl" if r.algorithm == "dqn" else r.algorithm,
            "avg_reward": round(float(r.avg_reward), 4),
            "n_episodes": int(r.n_episodes),
        }
        for r in rows
    ]


# ============================================================
# 3. Q-value entropy proxy
# ============================================================

def q_value_entropy_timeline(db: Session, window: str = "24h", buckets: int = 12) -> list[dict]:
    """Time-bucketed proxy for recommendation diversity.

    Fetches DRL cart events in window and buckets in Python — at MVP scale
    (tens of events per day) this is faster than fighting Postgres date_bin
    type-cast quirks and works identically across DB versions.
    """
    start = _window_start(window)
    now = datetime.now(timezone.utc)
    duration_seconds = (now - start).total_seconds()
    bucket_seconds = max(int(duration_seconds // buckets), 60)

    rows = db.execute(
        select(
            CartEvent.occurred_at,
            CartEvent.recommendation_context["shown_products"].label("shown_products"),
        )
        .where(
            CartEvent.occurred_at >= start,
            CartEvent.recommendation_context["policy"].astext == "drl",
        )
        .order_by(CartEvent.occurred_at)
    ).all()

    buckets_map: dict[int, dict] = {}
    for occurred_at, shown_products in rows:
        seconds_since_start = int((occurred_at - start).total_seconds())
        bucket_idx = seconds_since_start // bucket_seconds
        bucket_start_ts = start + timedelta(seconds=bucket_idx * bucket_seconds)

        if bucket_idx not in buckets_map:
            buckets_map[bucket_idx] = {
                "bucket_start": bucket_start_ts.isoformat(),
                "top_products": set(),
                "n_events": 0,
            }

        buckets_map[bucket_idx]["n_events"] += 1

        # shown_products may be a list (well-formed), or scalar, or None.
        # Only extract rank-0 if it's a non-empty list.
        if isinstance(shown_products, list) and len(shown_products) > 0:
            buckets_map[bucket_idx]["top_products"].add(shown_products[0])

    out = []
    for bucket_idx in sorted(buckets_map.keys()):
        b = buckets_map[bucket_idx]
        distinct = len(b["top_products"])
        entropy_proxy = math.log(distinct) if distinct > 1 else 0.0
        out.append({
            "bucket_start": b["bucket_start"],
            "distinct_top_products": distinct,
            "n_events": b["n_events"],
            "entropy_proxy": round(entropy_proxy, 4),
        })
    return out


# ============================================================
# 4. Epsilon decay curve
# ============================================================

def epsilon_curve(db: Session, n_points: int = 20) -> list[dict]:
    """Reconstructs the epsilon decay curve from persisted ModelRegistry rows."""
    from app.ml.agent import EPSILON_DECAY_STEPS, EPSILON_END, EPSILON_START

    rows = db.scalars(
        select(ModelRegistry)
        .where(ModelRegistry.algorithm == "dqn")
        .order_by(ModelRegistry.trained_at.desc())
        .limit(n_points)
    ).all()

    out = []
    for r in reversed(rows):
        steps = int(r.metrics.get("steps_done", 0))
        progress = min(steps / EPSILON_DECAY_STEPS, 1.0)
        epsilon = EPSILON_START + progress * (EPSILON_END - EPSILON_START)
        out.append({
            "version": r.version,
            "steps_done": steps,
            "epsilon": round(epsilon, 4),
            "trained_at": r.trained_at.isoformat() if r.trained_at else None,
        })
    return out


# ============================================================
# Headline summary
# ============================================================

def summary(db: Session, window: str = "24h") -> dict:
    return {
        "window": window,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "conversion_by_policy": conversion_by_policy(db, window=window),
        "avg_reward_by_policy": avg_reward_by_policy(db, window=window),
        "q_value_entropy_timeline": q_value_entropy_timeline(db, window=window),
        "epsilon_curve": epsilon_curve(db),
    }