"""Telemetry endpoints — feeds the KPI dashboard.

Three endpoints:
- GET /telemetry/summary: composite payload, all four metrics in one call
- GET /telemetry/conversion: just conversion-by-policy
- GET /telemetry/policy-comparison: side-by-side DRL vs CF for the headline chart
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import telemetry_service


router = APIRouter(prefix="/telemetry", tags=["telemetry"])


WindowLiteral = Literal["1h", "24h", "7d", "all"]


@router.get("/summary")
def get_summary(
    window: WindowLiteral = Query(default="24h"),
    db: Session = Depends(get_db),
) -> dict:
    """All four metrics in one call. The dashboard's first-paint endpoint."""
    return telemetry_service.summary(db, window=window)


@router.get("/conversion")
def get_conversion(
    window: WindowLiteral = Query(default="24h"),
    db: Session = Depends(get_db),
) -> dict:
    return {
        "window": window,
        "rows": telemetry_service.conversion_by_policy(db, window=window),
    }


@router.get("/policy-comparison")
def get_policy_comparison(
    window: WindowLiteral = Query(default="24h"),
    db: Session = Depends(get_db),
) -> dict:
    """Headline chart payload: side-by-side DRL vs CF conversion + reward.

    Always returns both policies even if one has zero events, so chart axes
    don't jump as data fills in.
    """
    conversion = telemetry_service.conversion_by_policy(db, window=window)
    rewards = telemetry_service.avg_reward_by_policy(db, window=window)

    by_policy = {
        "drl": {"shown": 0, "converted": 0, "rate": 0.0, "avg_reward": 0.0, "n_episodes": 0},
        "collab_filter": {"shown": 0, "converted": 0, "rate": 0.0, "avg_reward": 0.0, "n_episodes": 0},
    }

    for row in conversion:
        if row["policy"] in by_policy:
            by_policy[row["policy"]].update({
                "shown": row["shown"],
                "converted": row["converted"],
                "rate": row["rate"],
            })

    for row in rewards:
        if row["policy"] in by_policy:
            by_policy[row["policy"]].update({
                "avg_reward": row["avg_reward"],
                "n_episodes": row["n_episodes"],
            })

    return {
        "window": window,
        "policies": by_policy,
    }