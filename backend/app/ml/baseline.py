"""Item-based collaborative filtering — the A/B opponent for the DRL agent.

Algorithm:
1. Build the co-cart matrix: M[i][j] = how many users put both products i and j in their carts
2. Compute item-item cosine similarity from M
3. Recommend = top-k products most similar (by cosine) to the user's current cart contents
   Falls back to global popularity for users with empty carts.

Why this baseline:
- Parameter-free (no training, no tuning) → defensible A/B comparison
- Interpretable (you can explain *why* it suggested something: 'similar to items you cart')
- Strong enough to be a real test (popular CF beats popularity-ranked recommendation
  in essentially every published benchmark)

The matrix is rebuilt periodically (Sprint 6 will wire this into the trainer's
schedule). For MVP, it rebuilds on first inference and caches in-memory.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cart import CartEvent
from app.models.product import Product


log = logging.getLogger(__name__)


class CollabFilterBaseline:
    """Item-based CF over the co-cart matrix."""

    def __init__(self):
        self._product_ids: list[UUID] = []                       # ordered list of all product IDs
        self._product_index: dict[UUID, int] = {}                # UUID → matrix row/col index
        self._similarity: np.ndarray | None = None               # (N, N) cosine sim
        self._popularity: np.ndarray | None = None               # (N,) global add count, normalised
        self._fitted = False

    def fit(self, db: Session) -> None:
        """Build co-cart and similarity matrices from cart_events.

        O(N²) memory — fine for 800 products (~6MB of float32). At larger
        catalogue sizes you'd switch to a sparse representation.
        """
        # Stable product ordering — matrix indices must be deterministic
        products = db.scalars(select(Product).order_by(Product.id)).all()
        self._product_ids = [p.id for p in products]
        self._product_index = {pid: i for i, pid in enumerate(self._product_ids)}
        n = len(self._product_ids)

        if n == 0:
            log.warning("No products in catalogue — baseline will return empty recommendations")
            self._similarity = np.zeros((0, 0), dtype=np.float32)
            self._popularity = np.zeros(0, dtype=np.float32)
            self._fitted = True
            return

        # Build user → set-of-cart-products mapping
        cart_rows = db.execute(
            select(CartEvent.user_id, CartEvent.product_id)
            .where(CartEvent.action == "add")
        ).all()

        user_carts: dict[UUID, set[UUID]] = defaultdict(set)
        for user_id, product_id in cart_rows:
            user_carts[user_id].add(product_id)

        # Co-occurrence matrix
        cooc = np.zeros((n, n), dtype=np.float32)
        popularity = np.zeros(n, dtype=np.float32)
        for products_in_cart in user_carts.values():
            indices = [self._product_index[p] for p in products_in_cart if p in self._product_index]
            for i in indices:
                popularity[i] += 1
                for j in indices:
                    cooc[i][j] += 1

        # Cosine similarity: cooc[i][j] / sqrt(cooc[i][i] * cooc[j][j])
        # Diagonal of cooc is the count of users who carted product i — same as popularity
        norms = np.sqrt(np.diag(cooc))
        norms[norms == 0] = 1.0                                   # avoid div-by-zero for unseen products
        self._similarity = cooc / np.outer(norms, norms)
        np.fill_diagonal(self._similarity, 0.0)                   # don't recommend a product as similar to itself

        self._popularity = popularity / max(popularity.sum(), 1.0)
        self._fitted = True
        log.info("Fitted CF baseline: %d products, %d users contributing", n, len(user_carts))

    def recommend(
        self,
        cart_product_ids: list[UUID],
        *,
        top_k: int = 5,
    ) -> list[UUID]:
        """Top-k recommendations given the user's current cart.

        Score = sum of similarities from each cart item to each candidate.
        Empty cart falls back to global popularity.
        """
        if not self._fitted or self._similarity is None or self._popularity is None:
            raise RuntimeError("CollabFilterBaseline.recommend called before fit()")

        n = len(self._product_ids)
        if n == 0:
            return []

        # Map cart items to indices, dropping any that aren't in the catalogue
        cart_indices = [
            self._product_index[pid]
            for pid in cart_product_ids
            if pid in self._product_index
        ]

        if not cart_indices:
            # Cold-start: rank by global popularity
            top_idx = np.argsort(-self._popularity)[:top_k]
        else:
            # Sum similarity rows for each cart item, then mask the cart itself
            scores = self._similarity[cart_indices].sum(axis=0)
            scores[cart_indices] = -np.inf                        # don't recommend things already in cart
            top_idx = np.argsort(-scores)[:top_k]

        return [self._product_ids[i] for i in top_idx]