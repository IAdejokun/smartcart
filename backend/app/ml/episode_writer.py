"""Episode writeback — turns cart events and interactions into model_episodes.

Called from the cart router after every add/remove, and from the product router
after every view/click. The function is sync (uses the same DB session as the
caller) and idempotent on input — calling it twice for the same cart event will
produce two episodes, which is by design: each row represents a learning
opportunity, not a unique event.

Why the writeback lives in the ML layer:
The episode tuple shape (state, action, reward, next_state, done) is an ML
concern. Putting this logic in the cart router would couple cart logic to the
ML pipeline. Keeping it here lets the cart router ask 'translate this event
to an episode' without knowing how.
"""
from __future__ import annotations

import logging
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.policy_server import get_policy_server
from app.ml.replay_buffer import ReplayBuffer
from app.ml.reward import compute_reward
from app.ml.state_builder import STATE_DIM, build_user_state
from app.models.model_registry import ModelRegistry


log = logging.getLogger(__name__)


def _bootstrap_model_id(db: Session) -> UUID | None:
    """Returns the active DQN model_id, or creates a placeholder if none exists.

    model_episodes.model_id is NOT NULL with FK to model_registry. During the
    cold-start phase (no trained model yet), we still need to write episodes —
    so we lazily create a 'bootstrap' registry row for the random-weights agent.
    """
    active = db.scalar(
        select(ModelRegistry).where(
            ModelRegistry.algorithm == "dqn",
            ModelRegistry.is_active.is_(True),
        )
    )
    if active is not None:
        return active.id

    # Look for an existing bootstrap row to avoid duplicates on every call
    bootstrap = db.scalar(
        select(ModelRegistry).where(
            ModelRegistry.algorithm == "dqn",
            ModelRegistry.version == "bootstrap-random",
        )
    )
    if bootstrap is not None:
        return bootstrap.id

    bootstrap = ModelRegistry(
        version="bootstrap-random",
        algorithm="dqn",
        hyperparameters={"note": "Random-weights cold-start agent — placeholder for FK only"},
        metrics={},
        artifact_path="<no_checkpoint>",
        is_active=False,                 # ← bootstrap is FK target, not loadable
    )
    
    db.add(bootstrap)
    db.flush()                                                       # populates ID without commit
    log.info("Created bootstrap model registry entry: %s", bootstrap.id)
    return bootstrap.id


def write_cart_episode(
    db: Session,
    *,
    user_id: UUID,
    session_id: str,
    product_id: UUID,
    action: str,
    recommendation_context: dict,
    pre_event_state: np.ndarray,
) -> None:
    """Write one episode for a cart event (add/remove).

    pre_event_state must be captured BEFORE the cart event modifies the user's
    cart contents — otherwise the (s, a, r, s') tuple is wrong. The cart router
    is responsible for this ordering.
    """
    server = get_policy_server()
    action_index = server.product_to_index(product_id)
    if action_index is None:
        log.debug("Skipping episode for product %s — not in current action space", product_id)
        return

    reward = compute_reward(
        action=action,
        product_id=product_id,
        recommendation_context=recommendation_context,
    )

    # next_state is the state AFTER the cart event has landed in the DB
    next_state = build_user_state(db, user_id=user_id, session_id=session_id)

    # Done flag: cart events don't end episodes naturally — sessions do.
    # For SmartCart's MVP, we treat 'done' as session timeout, which is
    # conservatively False here. Future work: explicit session-end marker.
    done = False

    model_id = _bootstrap_model_id(db)
    if model_id is None:
        log.warning("No model_id available for episode writeback — skipping")
        return

    buffer = ReplayBuffer(db, state_dim=STATE_DIM)
    buffer.store(
        user_id=user_id,
        model_id=model_id,
        state=pre_event_state,
        action_index=action_index,
        reward=reward,
        next_state=next_state,
        done=done,
    )


def write_interaction_episode(
    db: Session,
    *,
    user_id: UUID,
    session_id: str,
    product_id: UUID | None,
    pre_event_state: np.ndarray,
) -> None:
    """Write one zero-reward episode for a view/click event.

    These episodes contribute exploration data — they tell the agent which
    state-action combinations *didn't* lead to reward, which is necessary
    for learning correct Q-values. The trainer uses stratified sampling
    to prevent these from dominating the gradient signal.
    """
    if product_id is None:
        return                                                        # search/category_browse — no specific action

    server = get_policy_server()
    action_index = server.product_to_index(product_id)
    if action_index is None:
        return

    next_state = build_user_state(db, user_id=user_id, session_id=session_id)
    model_id = _bootstrap_model_id(db)
    if model_id is None:
        return

    buffer = ReplayBuffer(db, state_dim=STATE_DIM)
    buffer.store(
        user_id=user_id,
        model_id=model_id,
        state=pre_event_state,
        action_index=action_index,
        reward=0.0,
        next_state=next_state,
        done=False,
    )