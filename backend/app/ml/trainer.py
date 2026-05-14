"""Background trainer — pulls minibatches, runs gradient steps, swaps active model.

Promotion gating (Sprint 7):
After a training run completes, we compare the new model's avg_train_loss
against the currently-active model's avg_train_loss. The new model is promoted
to active if:
  - improvement margin >= MIN_PROMOTION_MARGIN (default 10%)
  - new model has been trained for at least MIN_PROMOTION_STEPS (default 200)
  - active model is not the bootstrap-random row (always promotes the first real model)

This is honest about being an MVP heuristic — production would gate on online
conversion rate or held-out reward prediction. The min-margin and min-steps
guards prevent thrashing on noise and immature models respectively.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.ml.agent import BATCH_SIZE
from app.ml.policy_server import get_policy_server
from app.ml.replay_buffer import Minibatch, ReplayBuffer
from app.ml.state_builder import STATE_DIM
from app.models.episode import ModelEpisode
from app.models.model_registry import ModelRegistry


log = logging.getLogger(__name__)

_train_lock = Lock()
_last_training_ts: float = 0.0
_events_since_last_train: int = 0
_TRAINING_CADENCE_SECONDS = 60
_MIN_INTERVAL_SECONDS = 5
_TRAIN_STEPS_PER_RUN = 50
_NONZERO_FRACTION = 0.6
_MODEL_ARTIFACTS_DIR = Path("model_artifacts")

# --- Promotion gating thresholds ---
_MIN_PROMOTION_MARGIN = 0.10        # New loss must be at least 10% below active loss
_MIN_PROMOTION_STEPS = 200          # Refuse to promote a model with fewer than N gradient steps


def maybe_trigger_training(reason: str) -> None:
    """Best-effort trainer firing. Always returns quickly — actual work runs under lock."""
    global _last_training_ts, _events_since_last_train

    now = time.time()
    if now - _last_training_ts < _MIN_INTERVAL_SECONDS:
        return

    if reason == "cart_event":
        _events_since_last_train += 1
        threshold = settings.drl_training_trigger_threshold
        if _events_since_last_train < threshold and (now - _last_training_ts) < _TRAINING_CADENCE_SECONDS:
            return

    if not _train_lock.acquire(blocking=False):
        log.debug("Trainer already running, skipping fire (reason=%s)", reason)
        return

    try:
        _last_training_ts = now
        _events_since_last_train = 0
        log.info("Trainer firing (reason=%s)", reason)
        _run_training()
    except Exception:
        log.exception("Training run failed")
    finally:
        _train_lock.release()


def _run_training() -> None:
    db = SessionLocal()
    try:
        server = get_policy_server()
        agent = server.agent
        if agent is None:
            return

        buffer = ReplayBuffer(db, state_dim=STATE_DIM)
        if buffer.size() < BATCH_SIZE:
            log.info("Buffer size %d < batch_size %d, skipping training", buffer.size(), BATCH_SIZE)
            return

        losses: list[float] = []
        for _ in range(_TRAIN_STEPS_PER_RUN):
            minibatch = _stratified_sample(db, batch_size=BATCH_SIZE)
            if minibatch is None:
                break
            loss = agent.train_step(
                states=minibatch.states,
                actions=minibatch.actions,
                rewards=minibatch.rewards,
                next_states=minibatch.next_states,
                dones=minibatch.dones,
            )
            losses.append(loss)

        if not losses:
            return

        avg_loss = float(np.mean(losses))
        log.info(
            "Training run complete: %d steps, avg_loss=%.4f, agent.steps_done=%d",
            len(losses), avg_loss, agent.steps_done,
        )

        new_entry = _persist_checkpoint(db, agent, avg_loss=avg_loss)
        _maybe_promote(db, new_entry, agent_steps=agent.steps_done)

    finally:
        db.close()


def _stratified_sample(db: Session, batch_size: int) -> Minibatch | None:
    """Sample a minibatch with a guaranteed fraction of non-zero-reward episodes."""
    nonzero_size = int(batch_size * _NONZERO_FRACTION)
    zero_size = batch_size - nonzero_size

    nonzero_rows = db.scalars(
        select(ModelEpisode)
        .where(ModelEpisode.reward != 0.0)
        .order_by(func.random())
        .limit(nonzero_size)
    ).all()

    zero_rows = db.scalars(
        select(ModelEpisode)
        .where(ModelEpisode.reward == 0.0)
        .order_by(func.random())
        .limit(zero_size)
    ).all()

    rows = list(nonzero_rows) + list(zero_rows)
    if len(rows) == 0:
        return None

    states = np.array([r.state["vec"] for r in rows], dtype=np.float32)
    actions = np.array([r.action["product_index"] for r in rows], dtype=np.int64)
    rewards = np.array([r.reward for r in rows], dtype=np.float32)
    next_states = np.array([r.next_state["vec"] for r in rows], dtype=np.float32)
    dones = np.array([r.done for r in rows], dtype=np.float32)

    return Minibatch(states, actions, rewards, next_states, dones)


def _persist_checkpoint(db: Session, agent, *, avg_loss: float) -> ModelRegistry:
    """Save the agent's weights and register a new ModelRegistry entry (is_active=False)."""
    _MODEL_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    version = f"dqn-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
    artifact_path = _MODEL_ARTIFACTS_DIR / f"{version}.pt"
    agent.save(artifact_path)

    entry = ModelRegistry(
        version=version,
        algorithm="dqn",
        hyperparameters={
            "state_dim": agent.state_dim,
            "action_dim": agent.action_dim,
            "lr": 1e-3,
            "gamma": 0.95,
        },
        metrics={
            "avg_train_loss": avg_loss,
            "steps_done": agent.steps_done,
        },
        artifact_path=str(artifact_path),
        is_active=False,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    log.info("Persisted checkpoint: %s (avg_loss=%.4f)", version, avg_loss)
    return entry


def _maybe_promote(db: Session, candidate: ModelRegistry, *, agent_steps: int) -> None:
    """Decide whether to flip the candidate's is_active to True.

    Rules:
    - Min step count gate: the candidate must have at least _MIN_PROMOTION_STEPS gradient steps
    - If the active model is the bootstrap-random row, always promote (any real model > random)
    - Otherwise, candidate's avg_train_loss must be >= _MIN_PROMOTION_MARGIN below active's
    """
    if agent_steps < _MIN_PROMOTION_STEPS:
        log.debug(
            "Skipping promotion: candidate has %d steps (< %d required)",
            agent_steps, _MIN_PROMOTION_STEPS,
        )
        return

    active = db.scalar(
        select(ModelRegistry).where(
            ModelRegistry.algorithm == "dqn",
            ModelRegistry.is_active.is_(True),
        )
    )

    promote = False
    reason = ""

    if active is None:
        promote = True
        reason = "no active model"
    elif active.version == "bootstrap-random":
        promote = True
        reason = "active is bootstrap-random"
    else:
        active_loss = float(active.metrics.get("avg_train_loss", float("inf")))
        candidate_loss = float(candidate.metrics.get("avg_train_loss", float("inf")))
        if active_loss == 0:
            return  # avoid div-by-zero on degenerate case
        improvement = (active_loss - candidate_loss) / active_loss
        if improvement >= _MIN_PROMOTION_MARGIN:
            promote = True
            reason = f"loss improvement {improvement:.1%} >= {_MIN_PROMOTION_MARGIN:.0%}"
        else:
            log.info(
                "Skipping promotion: improvement %.1%% < %.0f%% margin (active=%.4f, candidate=%.4f)",
                improvement * 100, _MIN_PROMOTION_MARGIN * 100, active_loss, candidate_loss,
            )

    if not promote:
        return

    # Atomic swap: deactivate all DQN models, then activate the candidate
    db.execute(
        update(ModelRegistry)
        .where(ModelRegistry.algorithm == "dqn", ModelRegistry.is_active.is_(True))
        .values(is_active=False)
    )
    candidate.is_active = True
    db.commit()
    log.info("Promoted model %s to active (%s)", candidate.version, reason)