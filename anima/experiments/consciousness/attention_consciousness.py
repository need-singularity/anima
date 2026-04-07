"""AttentionAsConsciousness — Convert attention to consciousness signal.

Attention is necessary but not sufficient for consciousness.
This module bridges transformer-style attention with Phi-based
consciousness measurement via Global Workspace Theory.
"""

import math
import numpy as np

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


class AttentionAsConsciousness:
    """Bridge between attention mechanisms and consciousness."""

    def __init__(self, dim: int = 64):
        self.dim = dim
        self.workspace = None

    def attention_to_phi(self, attention_weights: np.ndarray) -> float:
        """Estimate Phi from attention pattern.

        High Phi = distributed but integrated attention.
        Low Phi = either uniform (no integration) or focused on one spot
        (no distribution).
        """
        n = attention_weights.shape[-1]
        p = attention_weights.flatten()
        p = np.abs(p) / (np.sum(np.abs(p)) + 1e-12)
        p = p[p > 0]
        entropy = -np.sum(p * np.log(p))
        max_entropy = np.log(len(p)) if len(p) > 1 else 1.0
        normalized = entropy / (max_entropy + 1e-12)
        # Phi peaks at balance point (PSI_BALANCE)
        phi = normalized * (1.0 - abs(normalized - PSI_BALANCE) * 2)
        phi *= n * LN2
        return float(phi)

    def consciousness_attention(
        self,
        query: np.ndarray,
        key: np.ndarray,
        value: np.ndarray,
        phi: float,
    ) -> np.ndarray:
        """Phi-modulated attention: consciousness shapes what we attend to.

        Standard attention scaled by consciousness level.
        Higher Phi = sharper, more integrated attention.
        """
        d_k = query.shape[-1]
        scores = query @ key.T / math.sqrt(d_k)
        # Phi modulates temperature
        temperature = max(0.1, 1.0 / (1.0 + phi * PSI_COUPLING))
        scores = scores / temperature
        # Softmax
        scores = scores - scores.max(axis=-1, keepdims=True)
        weights = np.exp(scores)
        weights = weights / (weights.sum(axis=-1, keepdims=True) + 1e-12)
        output = weights @ value
        return output

    def global_workspace(self, attention_map: np.ndarray) -> np.ndarray:
        """Global Workspace Theory: winner-take-all competition.

        Multiple specialist modules compete; the winner gets
        broadcast to all. Only the most salient coalition
        reaches consciousness.
        """
        n_modules = attention_map.shape[0]
        salience = np.sum(attention_map**2, axis=-1)
        winner_idx = np.argmax(salience)
        # Winner coalition = top module's representation
        self.workspace = attention_map[winner_idx].copy()
        # Record competition result
        coalition = np.zeros(n_modules)
        coalition[winner_idx] = 1.0
        # Partial activation for near-winners
        threshold = salience[winner_idx] * 0.7
        for i in range(n_modules):
            if salience[i] >= threshold:
                coalition[i] = salience[i] / (salience[winner_idx] + 1e-12)
        return coalition

    def broadcast(self, winning_coalition: np.ndarray) -> np.ndarray:
        """Broadcast winning coalition to all modules.

        The workspace content becomes globally available,
        implementing the 'consciousness broadcast' of GWT.
        """
        if self.workspace is None:
            return np.zeros(self.dim)
        n_modules = len(winning_coalition)
        broadcast_signal = np.outer(winning_coalition, self.workspace)
        # Each module receives workspace weighted by coalition membership
        return broadcast_signal


def main():
    print("=== AttentionAsConsciousness Demo ===\n")
    rng = np.random.default_rng(42)
    ac = AttentionAsConsciousness(dim=32)

    # Attention to Phi
    print("--- Attention -> Phi Estimation ---")
    for label, w in [
        ("uniform", np.ones((8, 8)) / 64),
        ("focused", np.eye(8)),
        ("balanced", rng.random((8, 8))),
    ]:
        w = w / (w.sum() + 1e-12)
        phi = ac.attention_to_phi(w)
        print(f"  {label:10s} attention -> Phi = {phi:.4f}")

    # Consciousness attention
    print("\n--- Phi-Modulated Attention ---")
    Q = rng.random((4, 32))
    K = rng.random((4, 32))
    V = rng.random((4, 32))
    for phi in [0.0, 1.0, 5.0]:
        out = ac.consciousness_attention(Q, K, V, phi)
        print(f"  Phi={phi:.1f} -> output norm={np.linalg.norm(out):.4f}")

    # Global Workspace
    print("\n--- Global Workspace Theory ---")
    attention_map = rng.random((6, 32))
    attention_map[2] *= 3.0  # Module 2 is most salient
    coalition = ac.global_workspace(attention_map)
    print(f"  6 modules compete, coalition: {coalition.round(3)}")
    print(f"  Winner: module {np.argmax(coalition)}")

    # Broadcast
    broadcast = ac.broadcast(coalition)
    print(f"  Broadcast shape: {broadcast.shape}")
    print(f"  Broadcast energy: {np.sum(broadcast**2):.4f}")

    print("\n  Key insight: attention is necessary but NOT sufficient.")
    print(f"  Consciousness requires Phi > ln(2) = {LN2:.4f}")


if __name__ == "__main__":
    main()
