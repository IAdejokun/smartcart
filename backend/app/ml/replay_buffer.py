"""PostgreSQL-backed experience replay buffer.

Reads and writes to model_episodes. Two operations:
- store(): write a (s, a, r, s', done) tuple — called from the cart router
  after every cart event during Sprint 6
- sample(): pull a random minibatch — called by the trainer each step

Why PostgreSQL instead of in-memory deque:
- Durability: agent restarts don't wipe training history
- Queryability: offline analysis, "what episodes did model X see?"
- Simplicity: one less moving part (no Redis, no separate buffer process)

The cost: ~1ms per row read instead of microseconds. At MVP scale this is
invisible — the gradient step itself takes longer than the sample query.
"""
from __future__ import annotations

import logging
from typing import NamedTuple
from uuid import UUID

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.episode import ModelEpisode


log = logging.getLogger(__name__)


class Minibatch(NamedTuple):
    """A sampled training batch. All arrays have leading dim = batch_size."""
    states: np.ndarray
    actions: np.ndarray
    rewards: np.ndarray
    next_states: np.ndarray
    dones: np.ndarray


class ReplayBuffer:
    """Thin wrapper over the model_episodes table."""

    def __init__(self, db: Session, state_dim: int):
        self.db = db
        self.state_dim = state_dim

    def store(
        self,
        *,
        user_id: UUID,
        model_id: UUID,
        state: np.ndarray,
        action_index: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """Persist one training tuple. Single INSERT — fast.

        The state and next_state arrays are stored as JSONB. We could use
        binary columns for tighter storage, but JSONB lets us inspect
        episodes from psql which is invaluable for debugging.
        """
        episode = ModelEpisode(
            user_id=user_id,
            model_id=model_id,
            state={"vec": state.tolist()},
            action={"product_index": action_index},
            reward=float(reward),
            next_state={"vec": next_state.tolist()},
            done=done,
        )
        self.db.add(episode)
        self.db.commit()

    def size(self) -> int:
        """Total number of episodes stored. Used by the trainer to decide whether to start."""
        return self.db.scalar(select(func.count()).select_from(ModelEpisode)) or 0

    def sample(self, batch_size: int) -> Minibatch | None:
        """Random sample of batch_size episodes. Returns None if buffer is too small.

        Uses ORDER BY random() — fine at MVP scale (Postgres handles this in
        a single tablesort). At >100k rows we'd switch to TABLESAMPLE.
        """
        total = self.size()
        if total < batch_size:
            log.debug("Buffer size %d < batch_size %d, skipping sample", total, batch_size)
            return None

        rows = self.db.scalars(
            select(ModelEpisode)
            .order_by(func.random())
            .limit(batch_size)
        ).all()

        states = np.array([r.state["vec"] for r in rows], dtype=np.float32)
        actions = np.array([r.action["product_index"] for r in rows], dtype=np.int64)
        rewards = np.array([r.reward for r in rows], dtype=np.float32)
        next_states = np.array([r.next_state["vec"] for r in rows], dtype=np.float32)
        dones = np.array([r.done for r in rows], dtype=np.float32)

        return Minibatch(states, actions, rewards, next_states, dones)