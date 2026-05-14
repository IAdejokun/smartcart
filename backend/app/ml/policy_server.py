"""Policy server — singleton holding the loaded DQN agent and CF baseline.

Public API is the recommend() method, which dispatches to the policy chosen
by the caller (or A/B-randomised when in 'auto' mode). Both policies share
the same input shape (state vector + cart contents) and output shape
(top-K product UUIDs + Q-values), so the routers don't need to know which
one served any given request.

Threading model:
- One process, one PolicyServer instance
- Read-mostly: inference is the hot path, model swaps are rare
- The active model is reloaded from model_registry every
  DRL_ACTIVE_MODEL_REFRESH_SECONDS (default 60s)
- A reload happens on a best-effort background tick, not on the request path
"""
from __future__ import annotations

import logging
import random
import time
from threading import Lock
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.ml.agent import DQNAgent
from app.ml.baseline import CollabFilterBaseline
from app.ml.state_builder import STATE_DIM
from app.models.model_registry import ModelRegistry
from app.models.product import Product


log = logging.getLogger(__name__)


class PolicyServer:
    """Singleton that owns trained models and serves inference."""

    _instance: "PolicyServer | None" = None
    _lock = Lock()

    def __new__(cls):
        # Classic Python singleton — first call constructs, later calls return same instance
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self._initialised = True

        # Action space: ordered list of product UUIDs. Index in this list = action_index in agent.
        self._product_ids: list[UUID] = []
        self._product_index: dict[UUID, int] = {}

        self._agent: DQNAgent | None = None
        self._active_model_id: UUID | None = None
        self._baseline = CollabFilterBaseline()

        self._last_refresh_ts: float = 0.0

    # --- Initialisation ---

    def initialise(self, db: Session) -> None:
        """Called once at app startup. Loads the active model + fits baseline."""
        log.info("Initialising PolicyServer")
        self._refresh_action_space(db)
        self._load_active_model(db)
        self._baseline.fit(db)
        log.info(
            "PolicyServer ready: %d products, agent=%s, baseline=fitted",
            len(self._product_ids),
            "loaded" if self._agent else "none",
        )

    def _refresh_action_space(self, db: Session) -> None:
        """Rebuilds the product UUID → action index mapping. Stable order: products.id ASC.

        Action space changes only when the catalogue changes — rare in production,
        but possible during seeding or admin operations.
        """
        products = db.scalars(select(Product).order_by(Product.id)).all()
        self._product_ids = [p.id for p in products]
        self._product_index = {pid: i for i, pid in enumerate(self._product_ids)}


    def _load_active_model(self, db: Session) -> None:
        """Loads the most recently activated DQN model, if any."""
        active = db.scalar(
            select(ModelRegistry)
            .where(
                ModelRegistry.algorithm == "dqn",
                ModelRegistry.is_active.is_(True),
            )
            .order_by(ModelRegistry.trained_at.desc())
        )

        if active is None:
            log.info("No active DQN model in registry — initialising random-weights agent")
            self._agent = DQNAgent(state_dim=STATE_DIM, action_dim=len(self._product_ids))
            self._active_model_id = None
            return

        if self._active_model_id == active.id:
            return

        # Sentinel: rows with placeholder artifact paths are FK anchors, not loadable models.
        # This handles the bootstrap-random row and any future placeholder pattern cleanly.
        if active.artifact_path in ("<no_checkpoint>", "", None):
            log.info(
                "Active model %s has placeholder artifact path — using random-weights agent",
                active.version,
            )
            self._agent = DQNAgent(state_dim=STATE_DIM, action_dim=len(self._product_ids))
            self._active_model_id = active.id
            return

        agent = DQNAgent(state_dim=STATE_DIM, action_dim=len(self._product_ids))
        try:
            agent.load(active.artifact_path)
        except FileNotFoundError:
            log.warning(
                "Active model %s missing on disk at %s — falling back to fresh agent",
                active.version, active.artifact_path,
            )
            agent = DQNAgent(state_dim=STATE_DIM, action_dim=len(self._product_ids))
            self._active_model_id = None
            self._agent = agent
            return

        self._agent = agent
        self._active_model_id = active.id
        log.info("Loaded active DQN model %s (id=%s)", active.version, active.id)
        
        
    def maybe_refresh(self, db: Session) -> None:
        """Periodic refresh — checks if a newer active model has been registered.

        Called opportunistically; not on every request. Costs one indexed lookup.
        """
        now = time.time()
        if now - self._last_refresh_ts < settings.drl_active_model_refresh_seconds:
            return
        self._last_refresh_ts = now
        self._load_active_model(db)

    # --- Inference ---

    def recommend_drl(
        self,
        state: np.ndarray,
        *,
        top_k: int = 5,
    ) -> tuple[list[UUID], list[float], UUID | None]:
        """Returns (product_uuids, q_values, model_id_for_attribution)."""
        if self._agent is None:
            raise RuntimeError("PolicyServer.recommend_drl called before initialise()")

        action_indices, q_values = self._agent.recommend(state, top_k=top_k)
        product_uuids = [self._product_ids[i] for i in action_indices]
        return product_uuids, q_values, self._active_model_id

    def recommend_baseline(
        self,
        cart_product_ids: list[UUID],
        *,
        top_k: int = 5,
    ) -> list[UUID]:
        return self._baseline.recommend(cart_product_ids, top_k=top_k)

    def recommend_auto(
        self,
        *,
        state: np.ndarray,
        cart_product_ids: list[UUID],
        top_k: int = 5,
        drl_share: float = 0.5,
    ) -> tuple[str, list[UUID], list[float], UUID | None]:
        """A/B-randomised dispatcher.

        Returns (policy_used, product_uuids, q_values, model_id).
        Q-values list is empty for baseline path (it doesn't produce them).
        """
        if random.random() < drl_share:
            uuids, q_values, model_id = self.recommend_drl(state, top_k=top_k)
            return "drl", uuids, q_values, model_id
        else:
            uuids = self.recommend_baseline(cart_product_ids, top_k=top_k)
            return "collab_filter", uuids, [], None

    # --- Action-space translation (for trainer) ---

    def product_to_index(self, product_id: UUID) -> int | None:
        return self._product_index.get(product_id)

    def index_to_product(self, index: int) -> UUID | None:
        if 0 <= index < len(self._product_ids):
            return self._product_ids[index]
        return None

    # --- Training delegation ---

    @property
    def agent(self) -> DQNAgent | None:
        """Exposed for the trainer. Routers should never touch this directly."""
        return self._agent


# Module-level singleton accessor — what the routers and trainer import
def get_policy_server() -> PolicyServer:
    return PolicyServer()