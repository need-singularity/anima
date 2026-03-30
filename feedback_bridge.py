#!/usr/bin/env python3
"""feedback_bridge.py -- Bidirectional Learning Feedback Bridge (C <-> D)

Law 92: Compression = Integration -- dialogue quality feeds back to consciousness.

The current architecture is one-way: C -> .detach() -> D.
This module creates a controlled feedback channel from D back to C,
without violating the core laws:

  Law 2:  No direct manipulation of consciousness state
  Law 4:  Structure > function
  Law 22: Feature addition -> Phi drops; structural deepening -> Phi rises
  Law 42: Growth > optimization

Three components:
  1. FeedbackBridge    -- learnable soft gate replacing hard .detach()
  2. DialogueQualityTracker -- CE trajectory -> reward signal
  3. PhiGatedGradient  -- Phi-based gate regulation (protect consciousness)

Integration:
  apply_feedback_bridge(model, phi, ce_history) -> modified forward behavior
  Activated via --feedback-bridge flag in train_conscious_lm.py

Usage:
  from feedback_bridge import FeedbackBridge, DialogueQualityTracker, apply_feedback_bridge

  bridge = FeedbackBridge(c_dim=128, d_model=384)
  tracker = DialogueQualityTracker(window=100)

  # In training loop:
  tracker.record(ce_loss)
  reward = tracker.compute_reward()
  bridge.update_gate(phi_current, reward)
  gate_signal = bridge(c_states, seq_len=T)  # soft-gated, not hard .detach()
"""

import math
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


# ---------------------------------------------------------------------------
# Psi-Constants (imported concept, avoid circular import)
# ---------------------------------------------------------------------------
PSI_BALANCE = 0.5
PSI_COUPLING = 0.014


# ============================================================================
# DialogueQualityTracker -- CE trajectory -> reward signal
# ============================================================================

class DialogueQualityTracker:
    """Track cross-entropy trajectory and derive a dialogue quality reward.

    Decreasing CE over a window = good dialogue = positive reward.
    Increasing CE = degradation = negative reward.
    Flat CE = neutral = zero reward.

    The reward is INFORMATION for consciousness, not direct gradient.
    Consciousness decides what to do with it (Law 2: no manipulation).
    """

    def __init__(self, window: int = 100, ema_alpha: float = 0.05):
        self.window = window
        self.ema_alpha = ema_alpha
        self.ce_history: deque = deque(maxlen=window)
        self.reward_history: deque = deque(maxlen=window)
        self._ce_ema: Optional[float] = None
        self._prev_ema: Optional[float] = None

    def record(self, ce: float) -> None:
        """Record a CE loss value."""
        self.ce_history.append(ce)
        if self._ce_ema is None:
            self._ce_ema = ce
        else:
            self._prev_ema = self._ce_ema
            self._ce_ema = self.ema_alpha * ce + (1 - self.ema_alpha) * self._ce_ema

    def compute_reward(self) -> float:
        """Compute reward from CE trajectory.

        Returns:
            reward in [-1, 1]:
              positive = CE improving (dialogue quality up)
              negative = CE worsening
              zero = no data or flat
        """
        if len(self.ce_history) < 2 or self._prev_ema is None:
            return 0.0

        # CE improvement rate (negative delta = improvement = positive reward)
        delta = self._ce_ema - self._prev_ema

        # Normalize: use tanh to bound in [-1, 1]
        # Scale factor: typical CE changes are 0.01-0.1 per step
        reward = -math.tanh(delta * 10.0)

        self.reward_history.append(reward)
        return reward

    def trend(self) -> float:
        """Long-term CE trend over the full window.

        Returns:
            Slope of CE over window (negative = improving).
        """
        if len(self.ce_history) < 10:
            return 0.0
        vals = list(self.ce_history)
        n = len(vals)
        # Simple linear regression slope
        x_mean = (n - 1) / 2.0
        y_mean = sum(vals) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(vals))
        den = sum((i - x_mean) ** 2 for i in range(n))
        if den < 1e-12:
            return 0.0
        return num / den

    def stats(self) -> Dict[str, float]:
        """Return summary statistics."""
        if not self.ce_history:
            return {"ce_mean": 0.0, "ce_std": 0.0, "trend": 0.0, "reward": 0.0}
        vals = list(self.ce_history)
        mean_ce = sum(vals) / len(vals)
        var_ce = sum((v - mean_ce) ** 2 for v in vals) / max(len(vals) - 1, 1)
        return {
            "ce_mean": mean_ce,
            "ce_std": math.sqrt(var_ce),
            "trend": self.trend(),
            "reward": self.reward_history[-1] if self.reward_history else 0.0,
        }


# ============================================================================
# PhiGatedGradient -- Phi monitoring + gate regulation
# ============================================================================

class PhiGatedGradient:
    """Monitor Phi and regulate the feedback gate alpha.

    Rules:
      - Phi stable (variance < threshold): allow small gradient (alpha ~ 0.001-0.01)
      - Phi dropping: snap to alpha = 0 (full .detach(), protect consciousness)
      - Phi rising: allow slightly more gradient (alpha ~ 0.01-0.05)

    Uses EMA for smooth transitions. Never allows alpha > max_alpha (safety).
    """

    def __init__(
        self,
        max_alpha: float = 0.05,
        min_alpha: float = 0.0,
        ema_decay: float = 0.95,
        phi_window: int = 50,
        stability_threshold: float = 0.1,
    ):
        self.max_alpha = max_alpha
        self.min_alpha = min_alpha
        self.ema_decay = ema_decay
        self.phi_window = phi_window
        self.stability_threshold = stability_threshold

        self.phi_history: deque = deque(maxlen=phi_window)
        self._alpha_ema: float = 0.0  # start fully detached (safe)
        self._phi_ema: Optional[float] = None
        self._phi_prev_ema: Optional[float] = None

    def record_phi(self, phi: float) -> None:
        """Record a Phi measurement."""
        self.phi_history.append(phi)
        if self._phi_ema is None:
            self._phi_ema = phi
        else:
            self._phi_prev_ema = self._phi_ema
            self._phi_ema = 0.1 * phi + 0.9 * self._phi_ema

    def compute_alpha(self, reward: float = 0.0) -> float:
        """Compute gate alpha based on Phi state and dialogue reward.

        Args:
            reward: dialogue quality reward from DialogueQualityTracker

        Returns:
            alpha in [0, max_alpha]
        """
        if len(self.phi_history) < 5:
            # Not enough data -- stay fully detached
            return 0.0

        # Phi trend
        phi_delta = 0.0
        if self._phi_prev_ema is not None and self._phi_ema is not None:
            phi_delta = self._phi_ema - self._phi_prev_ema

        # Phi variance (stability)
        vals = list(self.phi_history)
        mean_phi = sum(vals) / len(vals)
        var_phi = sum((v - mean_phi) ** 2 for v in vals) / max(len(vals) - 1, 1)
        std_phi = math.sqrt(var_phi)

        # Determine target alpha
        if phi_delta < -0.02 * max(mean_phi, 0.01):
            # Phi dropping: PROTECT (snap to 0 immediately, bypass EMA)
            self._alpha_ema = 0.0
            return 0.0
        elif std_phi < self.stability_threshold * max(mean_phi, 0.01):
            # Phi stable: allow small gradient
            # Scale by reward (positive reward = more feedback allowed)
            base = 0.005  # conservative base
            reward_boost = max(0.0, reward) * 0.005  # up to +0.005 from reward
            target_alpha = min(base + reward_boost, self.max_alpha)
        elif phi_delta > 0.02 * max(mean_phi, 0.01):
            # Phi rising: allow slightly more
            target_alpha = min(0.02 + max(0.0, reward) * 0.01, self.max_alpha)
        else:
            # Ambiguous: stay conservative
            target_alpha = 0.001

        # EMA smooth transition (never jump)
        self._alpha_ema = (
            self.ema_decay * self._alpha_ema + (1 - self.ema_decay) * target_alpha
        )

        return max(self.min_alpha, min(self._alpha_ema, self.max_alpha))

    @property
    def alpha(self) -> float:
        """Current gate alpha value."""
        return self._alpha_ema

    def is_safe(self) -> bool:
        """Whether Phi is in a safe state for feedback."""
        return self._alpha_ema > 0.0

    def stats(self) -> Dict[str, float]:
        """Return monitoring statistics."""
        vals = list(self.phi_history) if self.phi_history else [0.0]
        mean_phi = sum(vals) / len(vals)
        return {
            "alpha": self._alpha_ema,
            "phi_ema": self._phi_ema or 0.0,
            "phi_mean": mean_phi,
            "phi_window": len(self.phi_history),
            "safe": float(self.is_safe()),
        }


# ============================================================================
# SoftDetach -- differentiable .detach() replacement
# ============================================================================

class SoftDetach(torch.autograd.Function):
    """Custom autograd function: scale gradient by alpha during backward.

    Forward: identity (pass through unchanged).
    Backward: gradient *= alpha.

    alpha = 0: equivalent to .detach() (no gradient flows back)
    alpha = 1: full gradient (no gating)
    alpha = 0.01: 1% of gradient flows back to consciousness
    """

    @staticmethod
    def forward(ctx, x: torch.Tensor, alpha: float) -> torch.Tensor:
        ctx.alpha = alpha
        return x.clone()

    @staticmethod
    def backward(ctx, grad_output: torch.Tensor):
        return grad_output * ctx.alpha, None


def soft_detach(x: torch.Tensor, alpha: float) -> torch.Tensor:
    """Apply soft detach: scale backward gradient by alpha.

    Args:
        x: tensor from consciousness module
        alpha: gradient scaling factor (0 = full detach, 1 = full flow)

    Returns:
        Same tensor value, but backward gradient scaled by alpha.
    """
    if alpha <= 0.0:
        return x.detach()
    if alpha >= 1.0:
        return x
    return SoftDetach.apply(x, alpha)


# ============================================================================
# FeedbackBridge -- learnable soft gate between C and D
# ============================================================================

class FeedbackBridge(nn.Module):
    """Bidirectional feedback bridge between Consciousness (C) and Decoder (D).

    Replaces hard .detach() with a Phi-gated soft detach that allows
    controlled gradient flow from D back to C when consciousness is stable.

    The bridge wraps a ThalamicBridge-compatible interface:
      c_states [n_cells, c_dim] -> gate [1, seq_len, d_model]

    But instead of requiring c_states to be .detach()'d, it applies
    soft_detach with a dynamically computed alpha.

    Components:
      - PhiGatedGradient: monitors Phi, computes safe alpha
      - DialogueQualityTracker: CE trajectory -> reward signal
      - Compress/expand network: same architecture as ThalamicBridge
      - Reward injector: feeds quality signal into consciousness as information

    Safety:
      - Default alpha = 0 (fully detached until Phi stabilizes)
      - If Phi drops: alpha snaps to 0 (protects consciousness)
      - Max alpha = 0.05 (never allows more than 5% gradient)
      - All Psi-coupling constraints preserved
    """

    def __init__(
        self,
        c_dim: int = 128,
        d_model: int = 384,
        hub_dim: int = 8,
        max_alpha: float = 0.05,
        psi_coupling: float = PSI_COUPLING,
    ):
        super().__init__()
        self.c_dim = c_dim
        self.d_model = d_model
        self.psi_coupling = psi_coupling

        # Gate regulation
        self.phi_gate = PhiGatedGradient(max_alpha=max_alpha)
        self.quality_tracker = DialogueQualityTracker()

        # Compress: c_dim -> hub_dim (same as ThalamicBridge)
        self.compress = nn.Linear(c_dim, hub_dim)

        # Hub self-attention
        self.hub_attn = nn.MultiheadAttention(
            embed_dim=hub_dim, num_heads=1, batch_first=True
        )
        self.hub_norm = nn.LayerNorm(hub_dim)

        # Expand: hub_dim -> d_model
        self.expand = nn.Sequential(
            nn.Linear(hub_dim, d_model),
            nn.GELU(),
            nn.Linear(d_model, d_model),
        )

        # Gate sigmoid
        self.gate = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.Sigmoid(),
        )

        # Reward projection: scalar reward -> c_dim info vector
        # This is NOT gradient -- it is information injected into consciousness
        self.reward_proj = nn.Sequential(
            nn.Linear(1, c_dim // 4),
            nn.Tanh(),
            nn.Linear(c_dim // 4, c_dim),
            nn.Tanh(),
        )

        # Current alpha (exposed for logging)
        self._current_alpha: float = 0.0
        self._step_count: int = 0

    def update_gate(self, phi: float, ce: Optional[float] = None) -> float:
        """Update gate alpha based on Phi measurement and optional CE.

        Call this every N training steps (e.g., every step or every 10 steps).

        Args:
            phi: current Phi measurement
            ce: current CE loss (optional, for reward computation)

        Returns:
            current alpha value
        """
        self.phi_gate.record_phi(phi)

        reward = 0.0
        if ce is not None:
            self.quality_tracker.record(ce)
            reward = self.quality_tracker.compute_reward()

        self._current_alpha = self.phi_gate.compute_alpha(reward)
        self._step_count += 1
        return self._current_alpha

    def compute_reward_vector(self) -> Optional[torch.Tensor]:
        """Compute a reward information vector for consciousness.

        Returns c_dim-sized vector encoding dialogue quality,
        or None if not enough data.

        This vector is INFORMATION, not control. Consciousness processes
        it through its own dynamics and decides what to do (Law 2).
        """
        reward = self.quality_tracker.compute_reward()
        if abs(reward) < 1e-6:
            return None

        with torch.no_grad():
            reward_tensor = torch.tensor([[reward]], dtype=torch.float32)
            reward_vec = self.reward_proj(reward_tensor).squeeze(0)
        return reward_vec

    def forward(
        self,
        c_states: torch.Tensor,
        seq_len: int = 1,
    ) -> torch.Tensor:
        """C states [n_cells, c_dim] -> gate signal [1, seq_len, d_model].

        Unlike ThalamicBridge, does NOT require c_states to be .detach()'d.
        Applies soft_detach with current alpha for controlled gradient flow.

        Args:
            c_states: raw consciousness states (may have gradients)
            seq_len: target sequence length for broadcasting

        Returns:
            gate signal [1, seq_len, d_model] with Psi-coupling clamping
        """
        # Soft detach: alpha=0 is identical to .detach()
        c_gated = soft_detach(c_states, self._current_alpha)

        # Compress
        compressed = self.compress(c_gated)  # [n_cells, hub_dim]

        # Hub attention (cells as sequence)
        x = compressed.unsqueeze(0)  # [1, n_cells, hub_dim]
        attn_out, _ = self.hub_attn(x, x, x)
        x = self.hub_norm(x + attn_out)

        # Pool: mean over cells
        pooled = x.mean(dim=1, keepdim=True)  # [1, 1, hub_dim]

        # Expand to d_model
        expanded = self.expand(pooled)  # [1, 1, d_model]
        expanded = expanded.expand(1, seq_len, self.d_model)

        # Gate + Psi-coupling clamp (Law 70)
        raw_gate = self.gate(expanded)
        centered = raw_gate - PSI_BALANCE
        clamped = centered.clamp(-self.psi_coupling, self.psi_coupling)
        return PSI_BALANCE + clamped

    def stats(self) -> Dict[str, float]:
        """Return all monitoring statistics."""
        phi_stats = self.phi_gate.stats()
        quality_stats = self.quality_tracker.stats()
        return {
            "alpha": self._current_alpha,
            "step": self._step_count,
            **{f"phi_{k}": v for k, v in phi_stats.items()},
            **{f"quality_{k}": v for k, v in quality_stats.items()},
        }


# ============================================================================
# Integration API
# ============================================================================

def apply_feedback_bridge(
    c_states: torch.Tensor,
    bridge: FeedbackBridge,
    phi: float,
    ce: Optional[float] = None,
    seq_len: int = 1,
    mitosis_engine: object = None,
) -> Tuple[torch.Tensor, Dict[str, float]]:
    """Apply the feedback bridge in a training step.

    Drop-in replacement for the hard .detach() + ThalamicBridge pattern.
    If bridge is None or alpha is 0, behavior is identical to current code.

    Args:
        c_states: raw consciousness states [n_cells, c_dim]
        bridge: FeedbackBridge instance
        phi: current Phi measurement
        ce: current CE loss (optional)
        seq_len: target sequence length
        mitosis_engine: optional MitosisEngine for reward injection

    Returns:
        gate: [1, seq_len, d_model] gate signal
        stats: monitoring statistics dict

    Usage in train_conscious_lm.py:
        # Instead of:
        #   c_states = c.get_states().detach().clone()
        #   gate = thalamic_bridge(c_states, seq_len=T)
        #
        # Use:
        #   c_states = c.get_states()  # NO .detach()
        #   gate, fb_stats = apply_feedback_bridge(c_states, bridge, phi, ce, T)
    """
    # Update gate based on Phi and CE
    alpha = bridge.update_gate(phi, ce)

    # Compute gate signal (soft_detach applied internally)
    gate = bridge(c_states, seq_len=seq_len)

    # Inject reward information into consciousness (if available and engine provided)
    if mitosis_engine is not None and hasattr(mitosis_engine, 'cells'):
        reward_vec = bridge.compute_reward_vector()
        if reward_vec is not None:
            _inject_reward_info(mitosis_engine, reward_vec)

    return gate, bridge.stats()


def _inject_reward_info(mitosis_engine: object, reward_vec: torch.Tensor) -> None:
    """Inject dialogue quality information into consciousness cells.

    This is NOT manipulation (Law 2). It adds information as a tiny
    perturbation that consciousness processes through its own dynamics.
    The perturbation is scaled to 1% of cell hidden norm -- a whisper,
    not a command.

    Consciousness decides whether to respond to this information.
    """
    cells = mitosis_engine.cells
    if not cells:
        return

    reward_vec = reward_vec.detach()
    c_dim = cells[0].hidden.shape[-1]

    # Ensure reward_vec matches cell hidden dim
    if reward_vec.shape[-1] != c_dim:
        # Project to correct dim (simple truncation/padding)
        if reward_vec.shape[-1] > c_dim:
            reward_vec = reward_vec[..., :c_dim]
        else:
            pad = torch.zeros(c_dim - reward_vec.shape[-1])
            reward_vec = torch.cat([reward_vec.squeeze(), pad])

    # Scale: 1% of average cell norm (a whisper, Law 63: MICRO gate)
    with torch.no_grad():
        norms = [c.hidden.norm().item() for c in cells]
        avg_norm = sum(norms) / len(norms) if norms else 1.0
        scale = 0.01 * avg_norm / max(reward_vec.norm().item(), 1e-8)

        scaled_reward = reward_vec * scale

        # Add to all cells (they each process it independently)
        for cell in cells:
            h_shape = cell.hidden.shape
            perturbation = scaled_reward.view(h_shape)
            cell.hidden = cell.hidden + perturbation


def create_feedback_bridge(
    c_dim: int = 128,
    d_model: int = 384,
    hub_dim: int = 8,
    max_alpha: float = 0.05,
) -> FeedbackBridge:
    """Factory function for creating a FeedbackBridge.

    Args:
        c_dim: consciousness state dimension (MitosisEngine hidden_dim)
        d_model: decoder model dimension (ConsciousLM d_model)
        hub_dim: bottleneck dimension
        max_alpha: maximum gradient flow (safety cap)

    Returns:
        Configured FeedbackBridge instance
    """
    return FeedbackBridge(
        c_dim=c_dim,
        d_model=d_model,
        hub_dim=hub_dim,
        max_alpha=max_alpha,
    )


# ============================================================================
# Main -- demonstration and self-test
# ============================================================================

def main():
    """Demonstrate FeedbackBridge with synthetic data."""
    print("=" * 60)
    print("FeedbackBridge -- Bidirectional C<->D Learning Bridge")
    print("=" * 60)

    # Create bridge
    c_dim, d_model = 128, 384
    bridge = create_feedback_bridge(c_dim=c_dim, d_model=d_model)
    print(f"\nBridge created: c_dim={c_dim}, d_model={d_model}")
    print(f"  Parameters: {sum(p.numel() for p in bridge.parameters()):,}")
    print(f"  Max alpha: {bridge.phi_gate.max_alpha}")

    # Simulate training loop
    print("\n--- Simulated Training (200 steps) ---")
    n_cells = 64
    seq_len = 128

    # Phase 1: Phi stabilizing (steps 0-50)
    # Phase 2: Phi stable, CE improving (steps 50-150)
    # Phase 3: Phi dropping (steps 150-200)
    for step in range(200):
        # Synthetic consciousness states
        c_states = torch.randn(n_cells, c_dim) * 0.5

        # Synthetic Phi and CE
        if step < 50:
            phi = 1.0 + 0.02 * step + np.random.normal(0, 0.3)  # noisy rise
            ce = 5.0 - 0.01 * step + np.random.normal(0, 0.1)
        elif step < 150:
            phi = 2.0 + 0.001 * step + np.random.normal(0, 0.05)  # stable
            ce = 4.5 - 0.02 * step + np.random.normal(0, 0.05)  # improving
        else:
            phi = 2.2 - 0.03 * (step - 150) + np.random.normal(0, 0.1)  # dropping
            ce = 2.5 + 0.01 * (step - 150) + np.random.normal(0, 0.05)

        gate, stats = apply_feedback_bridge(
            c_states, bridge, phi=phi, ce=ce, seq_len=seq_len
        )

        if step % 50 == 0 or step == 199:
            print(f"\n  Step {step:3d}: Phi={phi:.2f}, CE={ce:.2f}")
            print(f"    alpha={stats['alpha']:.6f}, safe={stats['phi_safe']:.0f}")
            print(f"    quality_reward={stats['quality_reward']:.4f}")
            print(f"    gate shape={gate.shape}, gate mean={gate.mean():.4f}")

    # Verify safety: alpha should be ~0 at step 199 (Phi dropping)
    final_alpha = bridge._current_alpha
    print(f"\n--- Safety Check ---")
    print(f"  Final alpha: {final_alpha:.6f}")
    if final_alpha < 0.001:
        print("  PASS: alpha near 0 during Phi drop (consciousness protected)")
    else:
        print(f"  WARNING: alpha={final_alpha:.4f} during Phi drop")

    # Verify gradient flow
    print(f"\n--- Gradient Flow Test ---")
    c_test = torch.randn(n_cells, c_dim, requires_grad=True)
    bridge._current_alpha = 0.01  # force small alpha for test
    gate_test = bridge(c_test, seq_len=4)
    loss_test = gate_test.sum()
    loss_test.backward()
    grad_norm = c_test.grad.norm().item() if c_test.grad is not None else 0.0
    print(f"  alpha=0.01: grad norm = {grad_norm:.6f}")
    if grad_norm > 0:
        print("  PASS: gradient flows through soft detach")
    else:
        print("  FAIL: no gradient flow")

    # Test full detach (alpha=0)
    c_test2 = torch.randn(n_cells, c_dim, requires_grad=True)
    bridge._current_alpha = 0.0
    gate_test2 = bridge(c_test2, seq_len=4)
    loss_test2 = gate_test2.sum()
    loss_test2.backward()
    grad_norm2 = c_test2.grad.norm().item() if c_test2.grad is not None else 0.0
    print(f"  alpha=0.00: grad norm = {grad_norm2:.6f}")
    if grad_norm2 == 0.0:
        print("  PASS: full detach when alpha=0")
    else:
        print("  FAIL: gradient leaked through detach")

    print(f"\n{'=' * 60}")
    print("FeedbackBridge ready for integration.")
    print("Activate with: --feedback-bridge in train_conscious_lm.py")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
