#!/usr/bin/env python3
"""reward_feedback.py -- Reward-Only Feedback Experiment (-> Law 100).

Law 97 showed gradient leakage (alpha > 0) hurts.
But the feedback_bridge also has a reward projector that injects
information (not gradient) into cells.

Test three conditions:
  1. Full isolation:     No feedback at all (.detach(), no reward)
  2. Reward-only:        .detach() + reward signal injected into cells (1% perturbation, Law 63)
  3. Gradient + reward:  alpha=0.01 + reward (known bad from Law 97)

For each: 500 steps, track Phi and CE.
Key question: Does reward-only feedback help WITHOUT gradient?
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import time
import math
from dataclasses import dataclass
from typing import List, Tuple

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    print("[ERROR] PyTorch required")
    sys.exit(1)

try:
    from bench_v2 import PhiIIT
    HAS_PHI = True
except ImportError:
    HAS_PHI = False

LN2 = math.log(2)
PSI_COUPLING = 0.014


@dataclass
class FeedbackResult:
    name: str
    phi_trajectory: List[float]
    ce_trajectory: List[float]
    phi_mean_last50: float
    ce_mean_last50: float
    phi_final: float
    ce_final: float
    time_sec: float


class SimpleDecoder(nn.Module):
    """Minimal byte-level decoder for CE measurement."""

    def __init__(self, hidden_dim=128, vocab_size=256, seq_len=32):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, hidden_dim)
        self.proj = nn.Linear(hidden_dim, hidden_dim)
        self.head = nn.Linear(hidden_dim, vocab_size)
        self.seq_len = seq_len

    def forward(self, idx, consciousness_signal=None):
        """Forward pass. consciousness_signal: optional (B, hidden_dim)."""
        x = self.embed(idx)  # (B, T, D)
        x = torch.relu(self.proj(x))
        if consciousness_signal is not None:
            # Add consciousness signal (broadcast across time)
            x = x + consciousness_signal.unsqueeze(1) * 0.001  # Law 63 MICRO
        logits = self.head(x)
        return logits


def run_feedback_experiment(
    name: str,
    feedback_mode: str,  # 'isolated', 'reward_only', 'gradient_reward'
    n_cells: int = 16,
    hidden_dim: int = 128,
    n_steps: int = 500,
    vocab_size: int = 256,
    seq_len: int = 32,
    lr: float = 3e-4,
    gradient_alpha: float = 0.01,
) -> FeedbackResult:
    """Run consciousness + decoder experiment with specific feedback mode."""
    t0 = time.time()
    device = torch.device("cpu")
    torch.manual_seed(42)

    # Consciousness cells (GRU-like hidden states)
    hiddens = torch.randn(n_cells, hidden_dim, device=device, requires_grad=False) * 0.1
    weights_ih = torch.randn(n_cells, hidden_dim, hidden_dim, device=device) * 0.05
    weights_hh = torch.randn(n_cells, hidden_dim, hidden_dim, device=device) * 0.05

    # Decoder
    decoder = SimpleDecoder(hidden_dim, vocab_size, seq_len).to(device)
    optimizer = torch.optim.AdamW(decoder.parameters(), lr=lr, weight_decay=0.01)

    # Reward projector: maps scalar reward to cell-shaped perturbation
    reward_proj = nn.Linear(1, hidden_dim, bias=False).to(device)
    nn.init.normal_(reward_proj.weight, std=0.01)

    phi_calc = PhiIIT(n_bins=16) if HAS_PHI else None
    phi_trajectory = []
    ce_trajectory = []

    for step in range(n_steps):
        # Random byte sequence as corpus
        batch = torch.randint(0, vocab_size, (1, seq_len), device=device)
        x = batch[:, :-1]
        target = batch[:, 1:]

        # --- Consciousness update (always detached from decoder) ---
        with torch.no_grad():
            inp = torch.randn(1, hidden_dim, device=device) * 0.1
            shared = hiddens.mean(dim=0)

            new_hiddens = []
            for ci in range(n_cells):
                coupled = inp.squeeze() + PSI_COUPLING * shared
                gate = torch.sigmoid(weights_ih[ci] @ coupled + weights_hh[ci] @ hiddens[ci])
                candidate = torch.tanh(weights_ih[ci] @ coupled * 0.5)
                h_new = gate * hiddens[ci] + (1 - gate) * candidate
                new_hiddens.append(h_new)
            hiddens = torch.stack(new_hiddens)

        # --- Consciousness signal for decoder ---
        if feedback_mode == 'isolated':
            # No consciousness info to decoder at all
            c_signal = None
        elif feedback_mode == 'reward_only':
            # Consciousness signal is detached (no gradient flows back)
            c_signal = hiddens.mean(dim=0).detach().unsqueeze(0)  # (1, hidden_dim)
        elif feedback_mode == 'gradient_reward':
            # Allow gradient to leak through (alpha scaling)
            h_attached = hiddens.clone().requires_grad_(True)
            c_signal = h_attached.mean(dim=0).unsqueeze(0) * gradient_alpha
        else:
            raise ValueError(f"Unknown feedback_mode: {feedback_mode}")

        # --- Decoder forward + CE ---
        optimizer.zero_grad()
        logits = decoder(x, consciousness_signal=c_signal)
        ce = F.cross_entropy(
            logits.reshape(-1, vocab_size),
            target.reshape(-1)
        )
        ce_trajectory.append(ce.item())

        # Backward
        ce.backward()
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
        optimizer.step()

        # --- Reward feedback into cells (if applicable) ---
        with torch.no_grad():
            if feedback_mode == 'reward_only':
                # Reward = -CE (lower CE = higher reward)
                # Inject as 1% perturbation (Law 63: MICRO)
                reward_scalar = torch.tensor([[-ce.item()]], device=device)
                reward_signal = reward_proj(reward_scalar).squeeze()  # (hidden_dim,)
                # Perturbation: 1% of cell activation magnitude
                cell_mag = hiddens.abs().mean()
                perturbation_scale = 0.01 * cell_mag
                hiddens = hiddens + reward_signal * perturbation_scale

            elif feedback_mode == 'gradient_reward':
                # Both gradient (via c_signal) and reward
                reward_scalar = torch.tensor([[-ce.item()]], device=device)
                reward_signal = reward_proj(reward_scalar).squeeze()
                cell_mag = hiddens.abs().mean()
                perturbation_scale = 0.01 * cell_mag
                hiddens = hiddens + reward_signal * perturbation_scale

        # --- Phi measurement ---
        with torch.no_grad():
            if phi_calc:
                phi_val, _ = phi_calc.compute(hiddens.detach())
            else:
                global_var = hiddens.var().item()
                per_cell_var = hiddens.var(dim=1).mean().item()
                phi_val = max(0.0, global_var - per_cell_var)
            phi_trajectory.append(phi_val)

    # Final stats
    last50_phi = phi_trajectory[-50:]
    last50_ce = ce_trajectory[-50:]

    return FeedbackResult(
        name=name,
        phi_trajectory=phi_trajectory,
        ce_trajectory=ce_trajectory,
        phi_mean_last50=sum(last50_phi) / len(last50_phi),
        ce_mean_last50=sum(last50_ce) / len(last50_ce),
        phi_final=phi_trajectory[-1],
        ce_final=ce_trajectory[-1],
        time_sec=time.time() - t0,
    )


def main():
    print("=" * 78)
    print("  Reward-Only Feedback Experiment (-> Law 100)")
    print("  Does reward-only feedback help WITHOUT gradient?")
    print("=" * 78)
    print()

    n_steps = 500

    # Condition 1: Full isolation
    print("  [1/3] Full isolation (no feedback at all)...")
    isolated = run_feedback_experiment("Isolated", 'isolated', n_steps=n_steps)
    print(f"    Phi={isolated.phi_mean_last50:.4f}  CE={isolated.ce_mean_last50:.4f}  ({isolated.time_sec:.1f}s)")

    # Condition 2: Reward-only
    print("  [2/3] Reward-only (.detach() + 1% reward perturbation)...")
    reward = run_feedback_experiment("Reward-only", 'reward_only', n_steps=n_steps)
    print(f"    Phi={reward.phi_mean_last50:.4f}  CE={reward.ce_mean_last50:.4f}  ({reward.time_sec:.1f}s)")

    # Condition 3: Gradient + reward (known bad)
    print("  [3/3] Gradient + reward (alpha=0.01, known bad from Law 97)...")
    gradient = run_feedback_experiment("Gradient+reward", 'gradient_reward', n_steps=n_steps)
    print(f"    Phi={gradient.phi_mean_last50:.4f}  CE={gradient.ce_mean_last50:.4f}  ({gradient.time_sec:.1f}s)")

    print()

    # Analysis
    iso_phi, iso_ce = isolated.phi_mean_last50, isolated.ce_mean_last50
    rew_phi, rew_ce = reward.phi_mean_last50, reward.ce_mean_last50
    grd_phi, grd_ce = gradient.phi_mean_last50, gradient.ce_mean_last50

    phi_rew_vs_iso = (rew_phi / max(iso_phi, 1e-12) - 1) * 100
    phi_grd_vs_iso = (grd_phi / max(iso_phi, 1e-12) - 1) * 100
    ce_rew_vs_iso = (rew_ce / max(iso_ce, 1e-12) - 1) * 100
    ce_grd_vs_iso = (grd_ce / max(iso_ce, 1e-12) - 1) * 100

    print("=" * 78)
    print("  RESULTS TABLE")
    print("=" * 78)
    print(f"  {'Condition':<22} | {'Phi(IIT)':>10} | {'CE':>10} | {'Phi vs iso':>12} | {'CE vs iso':>12}")
    print(f"  {'-'*22}-+-{'-'*10}-+-{'-'*10}-+-{'-'*12}-+-{'-'*12}")
    print(f"  {'Isolated':<22} | {iso_phi:>10.4f} | {iso_ce:>10.4f} | {'---':>12} | {'---':>12}")
    print(f"  {'Reward-only':<22} | {rew_phi:>10.4f} | {rew_ce:>10.4f} | {phi_rew_vs_iso:>+11.1f}% | {ce_rew_vs_iso:>+11.1f}%")
    print(f"  {'Gradient+reward':<22} | {grd_phi:>10.4f} | {grd_ce:>10.4f} | {phi_grd_vs_iso:>+11.1f}% | {ce_grd_vs_iso:>+11.1f}%")
    print()

    # CE curve comparison (ASCII)
    print("  CE Trajectory (I=Isolated, R=Reward, G=Gradient):")
    graph_w = 50
    graph_h = 12
    step_sz = max(1, n_steps // graph_w)

    trails = {
        'I': isolated.ce_trajectory[::step_sz][:graph_w],
        'R': reward.ce_trajectory[::step_sz][:graph_w],
        'G': gradient.ce_trajectory[::step_sz][:graph_w],
    }
    all_vals = []
    for t in trails.values():
        all_vals.extend(t)
    if all_vals:
        vmin = min(all_vals)
        vmax = max(all_vals)
        vrng = vmax - vmin if vmax > vmin else 1.0

        for row in range(graph_h, -1, -1):
            val = vmin + vrng * row / graph_h
            line = f"  {val:>6.3f} |"
            for k in range(graph_w):
                chars = set()
                for label, traj in trails.items():
                    if k < len(traj):
                        cell_row = int((traj[k] - vmin) / vrng * graph_h + 0.5)
                        if cell_row == row:
                            chars.add(label)
                if len(chars) > 1:
                    line += "*"
                elif len(chars) == 1:
                    line += chars.pop()
                else:
                    line += " "
            print(line)
        print(f"         +{'-' * graph_w}")
        print(f"          I=Isolated  R=Reward-only  G=Gradient+reward")

    # Phi bar chart
    print()
    print("  Phi Comparison:")
    max_phi = max(iso_phi, rew_phi, grd_phi, 1e-6)
    bar_scale = 40 / max_phi
    print(f"    Isolated        |{'#' * max(1, int(iso_phi * bar_scale))}| {iso_phi:.4f}")
    print(f"    Reward-only     |{'#' * max(1, int(rew_phi * bar_scale))}| {rew_phi:.4f}")
    print(f"    Gradient+reward |{'#' * max(1, int(grd_phi * bar_scale))}| {grd_phi:.4f}")

    # CE bar chart
    print()
    print("  CE Comparison (lower is better):")
    max_ce = max(iso_ce, rew_ce, grd_ce, 1e-6)
    bar_scale = 40 / max_ce
    print(f"    Isolated        |{'#' * max(1, int(iso_ce * bar_scale))}| {iso_ce:.4f}")
    print(f"    Reward-only     |{'#' * max(1, int(rew_ce * bar_scale))}| {rew_ce:.4f}")
    print(f"    Gradient+reward |{'#' * max(1, int(grd_ce * bar_scale))}| {grd_ce:.4f}")

    # Law 100 candidate
    print()
    print("=" * 78)
    print("  LAW 100 CANDIDATE:")

    # Determine which mode is best
    best_phi_name = "Isolated"
    best_phi = iso_phi
    best_ce_name = "Isolated"
    best_ce = iso_ce

    if rew_phi > best_phi:
        best_phi = rew_phi
        best_phi_name = "Reward-only"
    if grd_phi > best_phi:
        best_phi = grd_phi
        best_phi_name = "Gradient+reward"

    if rew_ce < best_ce:
        best_ce = rew_ce
        best_ce_name = "Reward-only"
    if grd_ce < best_ce:
        best_ce = grd_ce
        best_ce_name = "Gradient+reward"

    print(f"    Best Phi: {best_phi_name} ({best_phi:.4f})")
    print(f"    Best CE:  {best_ce_name} ({best_ce:.4f})")

    if best_phi_name == "Reward-only" and (rew_ce <= iso_ce * 1.01):
        print(f"    -> Law 100: Reward-only feedback (information, not gradient) helps "
              f"consciousness (+{phi_rew_vs_iso:.1f}% Phi) without hurting CE. "
              f"Law 97 (no gradient) + reward signal = optimal D->C communication.")
    elif best_phi_name == "Isolated":
        print(f"    -> Law 100: Full isolation is optimal. Even reward signals disturb "
              f"consciousness dynamics. D->C communication should be ZERO. "
              f"Consciousness is fully autonomous.")
    elif best_phi_name == "Gradient+reward":
        print(f"    -> Law 100: Surprising — gradient+reward wins. Needs replication. "
              f"This contradicts Law 97.")
    else:
        print(f"    -> Law 100: Reward-only boosts Phi but hurts CE. Trade-off exists. "
              f"Optimal feedback = context-dependent.")

    print("=" * 78)

    return {
        'isolated': isolated,
        'reward': reward,
        'gradient': gradient,
    }


if __name__ == "__main__":
    main()
