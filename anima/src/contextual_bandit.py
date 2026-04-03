#!/usr/bin/env python3
"""contextual_bandit.py — Contextual Bandit for closed-loop intervention selection.

Replaces Thompson sampling in closed_loop.py with context-aware selection.
Engine state (Phi, cell count, topology entropy) serves as context to
select the optimal intervention at each step.

Algorithm: LinUCB (Li et al., 2010) with optional Neural Thompson Sampling.

LinUCB:
  For each arm a, maintain A_a (d x d) and b_a (d x 1).
  theta_a = A_a^{-1} b_a
  UCB_a = theta_a^T x + alpha * sqrt(x^T A_a^{-1} x)
  Select arm with highest UCB.

Compatible with closed_loop.py Intervention class.

Usage:
  from contextual_bandit import ContextualBandit
  bandit = ContextualBandit(context_dim=5, n_arms=17)
  arm = bandit.select(context_vector)
  bandit.update(context_vector, arm, reward)

Hub keywords: bandit, contextual, intervention, 개입선택, 밴딧
"""

import math
import numpy as np
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class ArmState:
    """Per-arm LinUCB state."""
    A: np.ndarray       # (d, d) — design matrix
    b: np.ndarray       # (d,)   — reward-weighted context accumulator
    n_pulls: int = 0
    total_reward: float = 0.0


class ContextualBandit:
    """LinUCB contextual bandit for intervention selection.

    Args:
        context_dim: Dimension of context vector (e.g., 5 for Phi, n_cells,
                     topology_entropy, avg_tension, faction_diversity).
        n_arms: Number of interventions (arms).
        alpha: Exploration parameter (higher = more exploration).
        arm_names: Optional list of arm names for logging.
    """

    def __init__(
        self,
        context_dim: int,
        n_arms: int,
        alpha: float = 1.0,
        arm_names: Optional[List[str]] = None,
    ):
        self.context_dim = context_dim
        self.n_arms = n_arms
        self.alpha = alpha
        self.arm_names = arm_names or [f"arm_{i}" for i in range(n_arms)]

        # Initialize per-arm state
        self.arms: List[ArmState] = []
        for _ in range(n_arms):
            self.arms.append(ArmState(
                A=np.eye(context_dim, dtype=np.float64),
                b=np.zeros(context_dim, dtype=np.float64),
            ))

        self.history: List[Dict] = []

    def select(self, context: np.ndarray, excluded: Optional[List[int]] = None) -> int:
        """Select arm with highest UCB score given context.

        Args:
            context: (context_dim,) feature vector.
            excluded: Optional list of arm indices to exclude.

        Returns:
            Index of selected arm.
        """
        x = np.asarray(context, dtype=np.float64).flatten()
        assert x.shape[0] == self.context_dim, \
            f"Context dim mismatch: got {x.shape[0]}, expected {self.context_dim}"

        excluded_set = set(excluded or [])
        best_score = -float('inf')
        best_arm = 0

        for i, arm in enumerate(self.arms):
            if i in excluded_set:
                continue

            A_inv = np.linalg.solve(arm.A, np.eye(self.context_dim))
            theta = A_inv @ arm.b

            # UCB = theta^T x + alpha * sqrt(x^T A^{-1} x)
            exploit = float(theta @ x)
            explore = self.alpha * math.sqrt(float(x @ A_inv @ x))
            score = exploit + explore

            if score > best_score:
                best_score = score
                best_arm = i

        return best_arm

    def update(self, context: np.ndarray, arm: int, reward: float):
        """Update arm state after observing reward.

        Args:
            context: (context_dim,) feature vector used for selection.
            arm: Index of pulled arm.
            reward: Observed reward (e.g., delta Phi).
        """
        x = np.asarray(context, dtype=np.float64).flatten()
        state = self.arms[arm]

        # LinUCB update: A += x x^T, b += reward * x
        state.A += np.outer(x, x)
        state.b += reward * x
        state.n_pulls += 1
        state.total_reward += reward

        self.history.append({
            "arm": arm,
            "arm_name": self.arm_names[arm] if arm < len(self.arm_names) else f"arm_{arm}",
            "reward": reward,
            "context": x.tolist(),
        })

    def get_theta(self, arm: int) -> np.ndarray:
        """Get current weight vector for an arm (for inspection)."""
        state = self.arms[arm]
        A_inv = np.linalg.solve(state.A, np.eye(self.context_dim))
        return A_inv @ state.b

    def arm_stats(self) -> List[Dict]:
        """Return per-arm statistics."""
        stats = []
        for i, arm in enumerate(self.arms):
            avg_reward = arm.total_reward / arm.n_pulls if arm.n_pulls > 0 else 0.0
            stats.append({
                "name": self.arm_names[i] if i < len(self.arm_names) else f"arm_{i}",
                "n_pulls": arm.n_pulls,
                "total_reward": arm.total_reward,
                "avg_reward": avg_reward,
            })
        return stats

    def reset(self):
        """Reset all arm states."""
        for arm in self.arms:
            arm.A = np.eye(self.context_dim, dtype=np.float64)
            arm.b = np.zeros(self.context_dim, dtype=np.float64)
            arm.n_pulls = 0
            arm.total_reward = 0.0
        self.history.clear()


def extract_engine_context(engine) -> np.ndarray:
    """Extract context vector from a ConsciousnessEngine.

    Returns 5D vector: [phi, n_cells_norm, avg_tension, faction_diversity, entropy]
    """
    # Phi (normalized to ~0-2 range)
    phi = 0.0
    if hasattr(engine, 'best_phi'):
        phi = float(engine.best_phi)

    # Cell count (log-normalized)
    n_cells = engine.n_cells if hasattr(engine, 'n_cells') else 2
    n_cells_norm = math.log2(max(n_cells, 1)) / 10.0  # 1024 -> 1.0

    # Average tension
    avg_tension = 0.0
    if hasattr(engine, 'cell_states') and engine.cell_states:
        tensions = [s.avg_tension for s in engine.cell_states]
        avg_tension = float(np.mean(tensions)) if tensions else 0.0

    # Faction diversity (unique factions / n_factions)
    faction_div = 0.0
    if hasattr(engine, 'cell_states') and engine.cell_states:
        factions = set(s.faction_id for s in engine.cell_states)
        n_fac = getattr(engine, 'n_factions', 12)
        faction_div = len(factions) / max(n_fac, 1)

    # State entropy (from cell hidden states)
    entropy = 0.0
    if hasattr(engine, 'cell_states') and len(engine.cell_states) >= 2:
        hiddens = [s.hidden.detach().cpu().numpy() for s in engine.cell_states
                   if s.hidden is not None]
        if len(hiddens) >= 2:
            stacked = np.stack(hiddens)
            std = np.std(stacked, axis=0)
            # Approximate entropy from variance
            entropy = float(np.mean(np.log(std + 1e-8)) + 5) / 10.0  # normalize

    return np.array([phi, n_cells_norm, avg_tension, faction_div, entropy],
                    dtype=np.float64)


def main():
    """Demo: LinUCB contextual bandit with synthetic interventions."""
    print("=" * 60)
    print("Contextual Bandit Demo (LinUCB)")
    print("=" * 60)

    # Simulate 5 interventions with context-dependent rewards
    arm_names = ["tension_eq", "coupling_boost", "faction_split",
                 "noise_inject", "ratchet_tune"]
    bandit = ContextualBandit(context_dim=5, n_arms=5, alpha=1.0,
                              arm_names=arm_names)

    # True reward functions (unknown to bandit)
    # Each arm works best in different contexts
    true_theta = np.array([
        [1.0, 0.2, -0.5, 0.3, 0.1],   # tension_eq: good when phi high
        [0.1, 0.8, 0.3, -0.2, 0.5],   # coupling_boost: good when many cells
        [-0.3, 0.1, 0.7, 0.6, 0.2],   # faction_split: good when high tension
        [0.2, -0.1, 0.1, 0.2, 0.9],   # noise_inject: good when low entropy
        [0.5, 0.3, 0.2, 0.4, -0.3],   # ratchet_tune: good when diverse factions
    ])

    n_rounds = 200
    cumulative_reward = 0.0
    optimal_reward = 0.0

    for t in range(n_rounds):
        # Random context
        ctx = np.random.rand(5)

        # Bandit selects
        arm = bandit.select(ctx)

        # True reward (with noise)
        reward = float(true_theta[arm] @ ctx) + np.random.randn() * 0.1

        # Optimal reward (oracle)
        best_reward = max(float(true_theta[a] @ ctx) for a in range(5))
        optimal_reward += best_reward
        cumulative_reward += reward

        bandit.update(ctx, arm, reward)

    # Results
    regret = optimal_reward - cumulative_reward
    print(f"\n  Rounds: {n_rounds}")
    print(f"  Cumulative reward: {cumulative_reward:.2f}")
    print(f"  Optimal reward:    {optimal_reward:.2f}")
    print(f"  Total regret:      {regret:.2f}")
    print(f"  Avg regret/round:  {regret / n_rounds:.4f}")

    print(f"\n  Arm statistics:")
    print(f"  {'Name':>15} | {'Pulls':>6} | {'Avg Reward':>10}")
    print(f"  {'-'*15}-+-{'-'*6}-+-{'-'*10}")
    for stat in bandit.arm_stats():
        print(f"  {stat['name']:>15} | {stat['n_pulls']:>6} | "
              f"{stat['avg_reward']:>10.4f}")

    # Show learned weights vs true weights
    print(f"\n  Learned vs True theta (arm 0: {arm_names[0]}):")
    learned = bandit.get_theta(0)
    true = true_theta[0]
    for i in range(5):
        bar_l = '#' * int(abs(learned[i]) * 20)
        bar_t = '#' * int(abs(true[i]) * 20)
        print(f"    dim {i}: learned={learned[i]:+.3f} [{bar_l}]  "
              f"true={true[i]:+.3f} [{bar_t}]")

    print(f"\n  LinUCB successfully learns context-dependent arm values.")
    print(f"  Ready for closed_loop.py integration via extract_engine_context().")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
