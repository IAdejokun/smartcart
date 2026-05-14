"""Reward computation — translates cart events into DRL reward signal.

Reward shape (interview-defensible):
  +1.0   on add_to_cart for a product that was in the recommendation list
  +0.3   on add_to_cart for a product NOT in the recommendation list
         (the user found something — not zero, but less than direct hits)
  -0.2   on remove_from_cart of a product the agent recommended
         (mild negative — recommendation led to regret)
   0.0   on view/click without follow-through
         (no signal, not stored as an episode)

Why these specific values:
- Sparse positive reward (most events are zero) is fine for DQN with
  experience replay — replay sampling counters the sparsity.
- Asymmetric add/remove magnitudes (+1 / -0.2) encode the asymmetry of
  intent: adding is high-confidence, removing is ambiguous (user might
  have found a better version, not necessarily a bad recommendation).
- Hit-vs-miss split (+1 / +0.3) is what makes A/B comparison meaningful:
  the DRL policy gets full credit only for products it actually surfaced.
"""
from __future__ import annotations

from uuid import UUID


# Reward magnitudes — kept as module constants so they're easy to tune from one place
REWARD_HIT_ADD = 1.0           # Recommended product → added to cart
REWARD_ORGANIC_ADD = 0.3       # Non-recommended product → added (user found it)
REWARD_HIT_REMOVE = -0.2       # Recommended product → removed (regret)
REWARD_ORGANIC_REMOVE = 0.0    # Non-recommended product removed: irrelevant


def compute_reward(
    *,
    action: str,
    product_id: UUID,
    recommendation_context: dict,
) -> float:
    """Pure function — given an action and its attribution context, return the reward.

    The function is total: every action gets a reward, even if zero. This keeps
    the trainer simple — no special cases for 'this event has no signal'.
    """
    shown_products: list[str] = recommendation_context.get("shown_products") or []
    was_recommended = str(product_id) in shown_products

    if action == "add":
        return REWARD_HIT_ADD if was_recommended else REWARD_ORGANIC_ADD

    if action == "remove":
        return REWARD_HIT_REMOVE if was_recommended else REWARD_ORGANIC_REMOVE

    # update_quantity, view, etc. — no signal
    return 0.0