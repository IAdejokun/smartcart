"""Deep Q-Network agent for SmartCart product recommendation.

Architecture:
  Input:  STATE_DIM (=13) float features
  Hidden: Linear(13 → 128) → ReLU → Linear(128 → 64) → ReLU
  Output: Linear(64 → ACTION_DIM) — Q-value per product

Training algorithm: standard DQN with experience replay and target network.
- Online network is updated every step from a sampled minibatch.
- Target network is a delayed copy, synced every TARGET_SYNC_STEPS.
- Loss is MSE between predicted Q(s, a) and r + γ·max_a' Q_target(s', a').

Why two networks (online + target):
Without a target network, the regression target moves every gradient step,
which destabilises learning. Freezing the target for N steps is the standard
DQN-paper trick (Mnih et al., 2015) — it's what made Atari DQN actually work.
"""
from __future__ import annotations

import logging
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


log = logging.getLogger(__name__)

# Hyperparameters — kept as module constants for explicitness. In a future sprint
# these move to the model_registry.hyperparameters JSONB so versioning is honest.
GAMMA = 0.95                 # Discount factor — modest, since SmartCart sessions are short
LEARNING_RATE = 1e-3
BATCH_SIZE = 64
TARGET_SYNC_STEPS = 200      # Sync target network every N gradient steps
EPSILON_START = 0.30         # Initial exploration rate — start moderate, decay
EPSILON_END = 0.05           # Floor — keep some exploration for online learning
EPSILON_DECAY_STEPS = 5000   # Linear decay over this many steps


class QNetwork(nn.Module):
    """13-dim state → ACTION_DIM Q-values. Two hidden layers, ReLU activations."""

    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        self.fc1 = nn.Linear(state_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.head = nn.Linear(64, action_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return self.head(x)


class DQNAgent:
    """DQN with experience replay and target network.

    Designed to be called from two contexts:
    - Inference (recommend): no gradient, no replay sampling, just forward pass
    - Training (train_step): samples a minibatch, computes loss, backprops
    """

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        *,
        device: str | None = None,
    ):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

        self.online_net = QNetwork(state_dim, action_dim).to(self.device)
        self.target_net = QNetwork(state_dim, action_dim).to(self.device)
        # Initialise target as a copy of online — they diverge during training, then re-sync
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()

        self.optimizer = torch.optim.Adam(self.online_net.parameters(), lr=LEARNING_RATE)
        self.steps_done = 0

    # --- Inference ---

    @torch.no_grad()
    def recommend(
        self,
        state: np.ndarray,
        *,
        top_k: int = 5,
        epsilon: float | None = None,
    ) -> tuple[list[int], list[float]]:
        """Returns (top_k product indices, their Q-values).

        Uses ε-greedy: with probability ε, returns top_k random products to keep
        exploration alive even after the agent thinks it has converged. Critical
        in production — pure exploitation creates filter bubbles.
        """
        if epsilon is None:
            epsilon = self._current_epsilon()

        if random.random() < epsilon:
            # Exploration: random top_k. Q-values are reported as zeros (honest signalling)
            indices = random.sample(range(self.action_dim), top_k)
            return indices, [0.0] * top_k

        # Exploitation: forward pass, take argmax_k
        state_tensor = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
        q_values = self.online_net(state_tensor).squeeze(0)         # shape: (action_dim,)
        top_q, top_indices = torch.topk(q_values, k=top_k)
        return top_indices.cpu().tolist(), top_q.cpu().tolist()

    # --- Training ---

    def train_step(
        self,
        states: np.ndarray,           # (B, state_dim)
        actions: np.ndarray,          # (B,) — the action *taken* (single product index)
        rewards: np.ndarray,          # (B,)
        next_states: np.ndarray,      # (B, state_dim)
        dones: np.ndarray,            # (B,) — bool/float
    ) -> float:
        """One gradient step. Returns the scalar loss for logging."""
        s = torch.from_numpy(states).float().to(self.device)
        a = torch.from_numpy(actions).long().to(self.device)
        r = torch.from_numpy(rewards).float().to(self.device)
        s_next = torch.from_numpy(next_states).float().to(self.device)
        done = torch.from_numpy(dones).float().to(self.device)

        # Q(s, a) — predicted Q-value for the action taken
        q_pred = self.online_net(s).gather(1, a.unsqueeze(1)).squeeze(1)

        # max_a' Q_target(s', a') — bootstrapped target. No grad on the target network.
        with torch.no_grad():
            q_next_max = self.target_net(s_next).max(dim=1).values
            q_target = r + GAMMA * q_next_max * (1 - done)

        loss = F.mse_loss(q_pred, q_target)

        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping — DQN's standard safety net against exploding Q-values
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), max_norm=10.0)
        self.optimizer.step()

        self.steps_done += 1
        if self.steps_done % TARGET_SYNC_STEPS == 0:
            self.target_net.load_state_dict(self.online_net.state_dict())
            log.info("Synced target network at step %d", self.steps_done)

        return float(loss.item())

    def _current_epsilon(self) -> float:
        """Linear decay from EPSILON_START to EPSILON_END over EPSILON_DECAY_STEPS."""
        progress = min(self.steps_done / EPSILON_DECAY_STEPS, 1.0)
        return EPSILON_START + progress * (EPSILON_END - EPSILON_START)

    # --- Persistence ---

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "online_net": self.online_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "steps_done": self.steps_done,
            "state_dim": self.state_dim,
            "action_dim": self.action_dim,
        }, path)
        log.info("Saved agent to %s", path)

    def load(self, path: str | Path) -> None:
        # weights_only=False is the right call here — we wrote these checkpoints
        # ourselves and they contain optimizer state plus tensor weights. Setting
        # this explicitly silences PyTorch's future-default warning.
        ckpt = torch.load(path, map_location=self.device, weights_only=False)
        # Defensive: refuse to load a checkpoint with mismatched dimensions
        if ckpt["state_dim"] != self.state_dim or ckpt["action_dim"] != self.action_dim:
            raise ValueError(
                f"Checkpoint dim mismatch: expected ({self.state_dim}, {self.action_dim}), "
                f"got ({ckpt['state_dim']}, {ckpt['action_dim']})"
            )
        self.online_net.load_state_dict(ckpt["online_net"])
        self.target_net.load_state_dict(ckpt["target_net"])
        self.optimizer.load_state_dict(ckpt["optimizer"])
        self.steps_done = ckpt["steps_done"]
        log.info("Loaded agent from %s (steps=%d)", path, self.steps_done)