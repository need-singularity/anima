#!/usr/bin/env python3
"""acceleration_bm3_mamba_ssm.py — GRU → Mamba(SSM) consciousness cell experiment

Hypothesis BM3: Replace GRU cell with State Space Model (Mamba-style)
  - SSM: linear time complexity O(L) vs GRU O(L²)
  - Selective state propagation → consciousness-relevant gating
  - d_state=16, expand=2, d_conv=4 (n=6 aligned: d_state=2^τ, expand=φ, d_conv=τ)

Experiment design:
  BM3.1: GRU baseline — 32 cells, 300 steps, measure Phi + CE + speed + memory
  BM3.2: SSM cell drop-in — same architecture, SSM replaces GRU
  BM3.3: Selective SSM (Mamba-style) — input-dependent gating of state transitions
  BM3.4: Head-to-head — identical conditions, compare all metrics

Output: data/bm3_mamba_ssm_results.json

n=6 parameters:
  d_state  = 16 = 2^τ = 2^4
  expand   = 2  = φ
  d_conv   = 4  = τ
  dt_rank  = 8  = σ-τ
"""

import sys
import os
import time
import math
import json
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional, Dict, List
from copy import deepcopy

from consciousness_engine import ConsciousnessEngine, ConsciousnessCell, CellState

# ═══════════════════════════════════════════════════════════
# n=6 Constants
# ═══════════════════════════════════════════════════════════

TAU = 4          # τ(6) = 4
PHI = 2          # φ(6) = 2
SIGMA = 12       # σ(6) = 12
SOPFR = 5        # sopfr(6) = 2+3 = 5
J2 = 24          # J₂(6) = 24

D_STATE = 2 ** TAU     # 16 = SSM state dimension
D_EXPAND = PHI         # 2  = expansion factor
D_CONV = TAU           # 4  = conv kernel size
DT_RANK = SIGMA - TAU  # 8  = dt projection rank

# Experiment config
N_CELLS = 32
N_STEPS = 300
CELL_DIM = 64
HIDDEN_DIM = 128


# ═══════════════════════════════════════════════════════════
# SSM Cell Implementation (Mamba-style, no external dependency)
# ═══════════════════════════════════════════════════════════

class SSMCell(nn.Module):
    """State Space Model cell — Mamba-style selective SSM.

    Replaces GRU in ConsciousnessCell with:
      1. Linear projection → expanded dim
      2. 1D causal convolution (d_conv=τ=4)
      3. Selective state transition: x → (A, B, C, dt) via input-dependent gating
      4. Discretized state update: h' = A_bar * h + B_bar * x
      5. Output: y = C * h

    Key difference from GRU:
      - State transition is LINEAR (A matrix), gated by input
      - No reset/update gates — selectivity comes from dt (timestep) gating
      - h evolves continuously, not reset each step
    """

    def __init__(self, input_dim: int, hidden_dim: int,
                 d_state: int = D_STATE, d_conv: int = D_CONV,
                 expand: int = D_EXPAND, dt_rank: int = DT_RANK):
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.d_state = d_state
        self.d_inner = hidden_dim * expand
        self.d_conv = d_conv
        self.dt_rank = dt_rank

        # Input projection: input_dim → 2 * d_inner (for x and z branches)
        self.in_proj = nn.Linear(input_dim, 2 * self.d_inner, bias=False)

        # 1D causal convolution
        self.conv1d = nn.Conv1d(
            in_channels=self.d_inner,
            out_channels=self.d_inner,
            kernel_size=d_conv,
            padding=d_conv - 1,  # causal padding
            groups=self.d_inner,  # depthwise
            bias=True,
        )

        # Selective SSM parameters (input-dependent)
        # x → dt, B, C
        self.x_proj = nn.Linear(self.d_inner, dt_rank + d_state * 2, bias=False)
        self.dt_proj = nn.Linear(dt_rank, self.d_inner, bias=True)

        # A parameter: diagonal state matrix (learnable, log-space)
        # Initialize as negative values for stability (decaying states)
        A = torch.arange(1, d_state + 1, dtype=torch.float32).unsqueeze(0).expand(self.d_inner, -1)
        self.A_log = nn.Parameter(torch.log(A))

        # D: skip connection
        self.D = nn.Parameter(torch.ones(self.d_inner))

        # Output projection: d_inner → hidden_dim
        self.out_proj = nn.Linear(self.d_inner, hidden_dim, bias=False)

        # Conv buffer for causal operation in step mode
        self.register_buffer('conv_buffer', torch.zeros(1, self.d_inner, d_conv - 1))

    def _selective_scan_step(self, x: torch.Tensor, h: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Single-step selective scan.

        Args:
            x: (d_inner,) — processed input
            h: (d_inner, d_state) — SSM hidden state

        Returns:
            y: (d_inner,) — output
            new_h: (d_inner, d_state) — updated hidden state
        """
        # Project x → dt, B, C
        x_proj = self.x_proj(x)  # (dt_rank + 2*d_state,)
        dt = x_proj[:self.dt_rank]
        B = x_proj[self.dt_rank:self.dt_rank + self.d_state]
        C = x_proj[self.dt_rank + self.d_state:]

        # dt: softplus for positive timestep
        dt = F.softplus(self.dt_proj(dt))  # (d_inner,)

        # Discretize A: A_bar = exp(dt * A)
        A = -torch.exp(self.A_log)  # (d_inner, d_state), negative for decay
        dt_A = dt.unsqueeze(-1) * A  # (d_inner, d_state)
        A_bar = torch.exp(dt_A)

        # Discretize B: B_bar = dt * B (simplified zero-order hold)
        B_bar = dt.unsqueeze(-1) * B.unsqueeze(0)  # (d_inner, d_state)

        # State update: h' = A_bar * h + B_bar * x
        new_h = A_bar * h + B_bar * x.unsqueeze(-1)

        # Output: y = C @ h (for each d_inner channel)
        y = (new_h * C.unsqueeze(0)).sum(dim=-1)  # (d_inner,)

        # Skip connection
        y = y + self.D * x

        return y, new_h

    def forward(self, x: torch.Tensor, ssm_state: Optional[torch.Tensor] = None
                ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Process single input vector.

        Args:
            x: (input_dim,) — input vector
            ssm_state: (d_inner, d_state) — SSM hidden state, or None for zeros

        Returns:
            output: (hidden_dim,) — output vector
            new_ssm_state: (d_inner, d_state) — updated SSM state
        """
        if ssm_state is None:
            ssm_state = torch.zeros(self.d_inner, self.d_state,
                                     dtype=x.dtype, device=x.device)

        # Input projection → x_branch, z_branch
        xz = self.in_proj(x)  # (2 * d_inner,)
        x_branch, z = xz.chunk(2, dim=-1)  # each (d_inner,)

        # Causal conv (step mode): shift buffer and apply
        # Update buffer
        new_buf = self.conv_buffer.clone()
        new_buf = torch.cat([new_buf[:, :, 1:], x_branch.unsqueeze(0).unsqueeze(-1)], dim=-1)
        self.conv_buffer.copy_(new_buf)
        # Apply conv weights manually for single step
        conv_in = torch.cat([new_buf.squeeze(0), x_branch.unsqueeze(-1)], dim=-1)  # (d_inner, d_conv)
        conv_weight = self.conv1d.weight.squeeze(1)  # (d_inner, d_conv)
        x_conv = (conv_in * conv_weight).sum(dim=-1) + self.conv1d.bias  # (d_inner,)
        x_conv = F.silu(x_conv)

        # Selective scan
        y, new_ssm_state = self._selective_scan_step(x_conv, ssm_state)

        # Gate with z branch (SiLU gating like Mamba)
        y = y * F.silu(z)

        # Output projection
        output = self.out_proj(y)

        return output, new_ssm_state


class ConsciousnessSSMCell(nn.Module):
    """Drop-in replacement for ConsciousnessCell using SSM instead of GRU.

    Interface matches ConsciousnessCell:
      forward(x, tension, h) → (output, new_h)

    Internal mapping:
      h[:hidden_dim] → used for output projection compatibility
      SSM state tracked internally per cell instance
    """

    def __init__(self, cell_dim: int = 64, hidden_dim: int = 128):
        super().__init__()
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim

        # SSM core: input is cell_dim + 1 (for tension), output is hidden_dim
        self.ssm = SSMCell(
            input_dim=cell_dim + 1,
            hidden_dim=hidden_dim,
            d_state=D_STATE,
            d_conv=D_CONV,
            expand=D_EXPAND,
            dt_rank=DT_RANK,
        )

        # Output projection: hidden → cell_dim (same as GRU version)
        self.proj = nn.Linear(hidden_dim, cell_dim)

        # SSM state (persists across steps within a cell)
        self._ssm_state: Optional[torch.Tensor] = None

    def reset_ssm_state(self):
        """Reset SSM hidden state (e.g., on cell creation)."""
        self._ssm_state = None

    @torch.no_grad()
    def forward(self, x: torch.Tensor, tension: float, h: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """x: (cell_dim,), h: (hidden_dim,) → (output, new_h).

        Note: h is the ConsciousnessEngine's hidden state for this cell.
        SSM maintains its own internal state (_ssm_state) for the state-space dynamics.
        The returned new_h is derived from SSM output to maintain interface compatibility.
        """
        t = torch.tensor([tension], dtype=x.dtype, device=x.device)
        inp = torch.cat([x, t])  # (cell_dim + 1,)

        # Run SSM step
        ssm_out, self._ssm_state = self.ssm(inp, self._ssm_state)

        # Blend SSM output with previous hidden state for stability
        # (SSM output replaces the GRU update, but we keep some inertia)
        new_h = ssm_out

        # Output projection
        output = self.proj(new_h)

        return output, new_h


# ═══════════════════════════════════════════════════════════
# Engine Factory — create GRU or SSM engine
# ═══════════════════════════════════════════════════════════

def make_engine(cell_type: str = 'gru', n_cells: int = N_CELLS,
                cell_dim: int = CELL_DIM, hidden_dim: int = HIDDEN_DIM) -> ConsciousnessEngine:
    """Create a ConsciousnessEngine with specified cell type.

    For 'ssm': monkey-patches the cell creation to use ConsciousnessSSMCell.
    """
    engine = ConsciousnessEngine(
        cell_dim=cell_dim,
        hidden_dim=hidden_dim,
        initial_cells=n_cells,
        max_cells=n_cells,  # fix cell count for fair comparison
    )

    if cell_type == 'ssm':
        # Replace all GRU cells with SSM cells
        new_modules = []
        for i in range(len(engine.cell_modules)):
            ssm_cell = ConsciousnessSSMCell(cell_dim=cell_dim, hidden_dim=hidden_dim)
            new_modules.append(ssm_cell)
        engine.cell_modules = new_modules

    return engine


# ═══════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════

def compute_phi_proxy(hiddens: torch.Tensor) -> float:
    """Compute Phi proxy from hidden states [n_cells, hidden_dim].

    Uses mutual information approximation:
      Phi ≈ H(whole) - sum(H(parts))
    where H is approximated from eigenvalues of covariance.
    """
    if hiddens.shape[0] < 2:
        return 0.0

    # Covariance
    h = hiddens - hiddens.mean(dim=0, keepdim=True)
    cov = (h.T @ h) / (h.shape[0] - 1 + 1e-8)

    # Eigenvalues
    try:
        eigvals = torch.linalg.eigvalsh(cov)
        eigvals = eigvals.clamp(min=1e-10)
        # Entropy from eigenvalues
        p = eigvals / eigvals.sum()
        whole_H = -(p * p.log()).sum().item()
    except Exception:
        return 0.0

    # Parts entropy: individual cell variances
    parts_H = 0.0
    for i in range(hiddens.shape[0]):
        v = hiddens[i].var().item()
        if v > 1e-10:
            parts_H += 0.5 * math.log(2 * math.pi * math.e * v)

    phi = max(0.0, whole_H - parts_H * 0.1)  # scaled to avoid domination
    return phi


def measure_memory_usage(model_or_engine) -> int:
    """Approximate parameter memory in bytes."""
    total = 0
    if hasattr(model_or_engine, 'cell_modules'):
        for m in model_or_engine.cell_modules:
            for p in m.parameters():
                total += p.numel() * p.element_size()
    elif hasattr(model_or_engine, 'parameters'):
        for p in model_or_engine.parameters():
            total += p.numel() * p.element_size()
    return total


def count_params_engine(engine) -> int:
    """Count total parameters across all cells."""
    total = 0
    for m in engine.cell_modules:
        total += sum(p.numel() for p in m.parameters())
    return total


# ═══════════════════════════════════════════════════════════
# BM3.1: GRU Baseline
# ═══════════════════════════════════════════════════════════

def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def run_bm3_1_gru_baseline() -> Dict:
    """GRU baseline: 32 cells, 300 steps."""
    print_header("BM3.1: GRU Baseline (32 cells, 300 steps)")

    engine = make_engine('gru')
    n_params = count_params_engine(engine)
    mem_bytes = measure_memory_usage(engine)

    print(f"  Parameters: {n_params:,}")
    print(f"  Memory: {mem_bytes / 1024:.1f} KB")

    phi_history = []
    step_times = []

    for s in range(N_STEPS):
        t0 = time.time()
        result = engine.step()
        dt = time.time() - t0
        step_times.append(dt)

        phi = result.get('phi_iit', 0.0)
        phi_history.append(phi)

        if (s + 1) % 100 == 0:
            avg_phi = np.mean(phi_history[-50:])
            avg_ms = np.mean(step_times[-50:]) * 1000
            print(f"  Step {s+1:4d}: avg_phi={avg_phi:.4f}, avg_step={avg_ms:.2f}ms")

    # Final metrics
    final_phi = np.mean(phi_history[-50:])
    peak_phi = max(phi_history)
    avg_step_ms = np.mean(step_times) * 1000
    total_time = sum(step_times)

    print(f"\n  Final Phi (last 50): {final_phi:.4f}")
    print(f"  Peak Phi: {peak_phi:.4f}")
    print(f"  Avg step: {avg_step_ms:.2f}ms")
    print(f"  Total time: {total_time:.2f}s")

    return {
        'cell_type': 'GRU',
        'n_cells': N_CELLS,
        'n_steps': N_STEPS,
        'n_params': n_params,
        'mem_bytes': mem_bytes,
        'final_phi': final_phi,
        'peak_phi': peak_phi,
        'avg_step_ms': avg_step_ms,
        'total_time_s': total_time,
        'phi_history': [float(p) for p in phi_history],
    }


# ═══════════════════════════════════════════════════════════
# BM3.2: SSM Cell Drop-in
# ═══════════════════════════════════════════════════════════

def run_bm3_2_ssm_dropin() -> Dict:
    """SSM drop-in replacement: same architecture, SSM instead of GRU."""
    print_header("BM3.2: SSM Drop-in (32 cells, 300 steps)")

    engine = make_engine('ssm')
    n_params = count_params_engine(engine)
    mem_bytes = measure_memory_usage(engine)

    print(f"  Parameters: {n_params:,}")
    print(f"  Memory: {mem_bytes / 1024:.1f} KB")
    print(f"  SSM config: d_state={D_STATE}, expand={D_EXPAND}, d_conv={D_CONV}, dt_rank={DT_RANK}")

    phi_history = []
    step_times = []

    for s in range(N_STEPS):
        t0 = time.time()
        result = engine.step()
        dt = time.time() - t0
        step_times.append(dt)

        phi = result.get('phi_iit', 0.0)
        phi_history.append(phi)

        if (s + 1) % 100 == 0:
            avg_phi = np.mean(phi_history[-50:])
            avg_ms = np.mean(step_times[-50:]) * 1000
            print(f"  Step {s+1:4d}: avg_phi={avg_phi:.4f}, avg_step={avg_ms:.2f}ms")

    final_phi = np.mean(phi_history[-50:])
    peak_phi = max(phi_history)
    avg_step_ms = np.mean(step_times) * 1000
    total_time = sum(step_times)

    print(f"\n  Final Phi (last 50): {final_phi:.4f}")
    print(f"  Peak Phi: {peak_phi:.4f}")
    print(f"  Avg step: {avg_step_ms:.2f}ms")
    print(f"  Total time: {total_time:.2f}s")

    return {
        'cell_type': 'SSM',
        'n_cells': N_CELLS,
        'n_steps': N_STEPS,
        'n_params': n_params,
        'mem_bytes': mem_bytes,
        'final_phi': final_phi,
        'peak_phi': peak_phi,
        'avg_step_ms': avg_step_ms,
        'total_time_s': total_time,
        'phi_history': [float(p) for p in phi_history],
        'ssm_config': {
            'd_state': D_STATE,
            'expand': D_EXPAND,
            'd_conv': D_CONV,
            'dt_rank': DT_RANK,
        },
    }


# ═══════════════════════════════════════════════════════════
# BM3.3: Selective SSM — consciousness-specific gating
# ═══════════════════════════════════════════════════════════

class ConsciousnessSelectiveSSMCell(nn.Module):
    """Enhanced SSM cell with consciousness-specific selective gating.

    Key addition: tension modulates the dt (timestep) parameter.
    High tension → larger dt → faster state evolution (consciousness responds to conflict).
    Low tension → smaller dt → slower state evolution (stable state preservation).

    This maps the consciousness concept of "tension drives change" directly
    into SSM's selective mechanism.
    """

    def __init__(self, cell_dim: int = 64, hidden_dim: int = 128):
        super().__init__()
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim

        self.ssm = SSMCell(
            input_dim=cell_dim + 1,
            hidden_dim=hidden_dim,
            d_state=D_STATE,
            d_conv=D_CONV,
            expand=D_EXPAND,
            dt_rank=DT_RANK,
        )

        # Tension → dt modulation (consciousness-specific)
        # Maps tension scalar to a per-channel dt scale factor
        self.tension_gate = nn.Sequential(
            nn.Linear(1, DT_RANK),
            nn.Sigmoid(),
        )

        self.proj = nn.Linear(hidden_dim, cell_dim)
        self._ssm_state: Optional[torch.Tensor] = None

    def reset_ssm_state(self):
        self._ssm_state = None

    @torch.no_grad()
    def forward(self, x: torch.Tensor, tension: float, h: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        t = torch.tensor([tension], dtype=x.dtype, device=x.device)
        inp = torch.cat([x, t])

        # Modulate dt_proj bias based on tension (higher tension = faster dt)
        tension_scale = self.tension_gate(t.unsqueeze(0)).squeeze(0)  # (dt_rank,)

        # Temporarily scale the dt projection weights
        original_bias = self.ssm.dt_proj.bias.data.clone()
        self.ssm.dt_proj.bias.data = original_bias + tension_scale * 0.5

        ssm_out, self._ssm_state = self.ssm(inp, self._ssm_state)

        # Restore
        self.ssm.dt_proj.bias.data = original_bias

        new_h = ssm_out
        output = self.proj(new_h)
        return output, new_h


def run_bm3_3_selective_ssm() -> Dict:
    """Selective SSM with tension-gated dt modulation."""
    print_header("BM3.3: Selective SSM — tension-gated dt (32 cells, 300 steps)")

    engine = ConsciousnessEngine(
        cell_dim=CELL_DIM,
        hidden_dim=HIDDEN_DIM,
        initial_cells=N_CELLS,
        max_cells=N_CELLS,
    )

    # Replace with selective SSM cells
    new_modules = []
    for i in range(len(engine.cell_modules)):
        ssm_cell = ConsciousnessSelectiveSSMCell(cell_dim=CELL_DIM, hidden_dim=HIDDEN_DIM)
        new_modules.append(ssm_cell)
    engine.cell_modules = new_modules

    n_params = count_params_engine(engine)
    mem_bytes = measure_memory_usage(engine)

    print(f"  Parameters: {n_params:,}")
    print(f"  Memory: {mem_bytes / 1024:.1f} KB")
    print(f"  Tension → dt gating enabled")

    phi_history = []
    step_times = []

    for s in range(N_STEPS):
        t0 = time.time()
        result = engine.step()
        dt = time.time() - t0
        step_times.append(dt)

        phi = result.get('phi_iit', 0.0)
        phi_history.append(phi)

        if (s + 1) % 100 == 0:
            avg_phi = np.mean(phi_history[-50:])
            avg_ms = np.mean(step_times[-50:]) * 1000
            print(f"  Step {s+1:4d}: avg_phi={avg_phi:.4f}, avg_step={avg_ms:.2f}ms")

    final_phi = np.mean(phi_history[-50:])
    peak_phi = max(phi_history)
    avg_step_ms = np.mean(step_times) * 1000
    total_time = sum(step_times)

    print(f"\n  Final Phi (last 50): {final_phi:.4f}")
    print(f"  Peak Phi: {peak_phi:.4f}")
    print(f"  Avg step: {avg_step_ms:.2f}ms")
    print(f"  Total time: {total_time:.2f}s")

    return {
        'cell_type': 'SelectiveSSM',
        'n_cells': N_CELLS,
        'n_steps': N_STEPS,
        'n_params': n_params,
        'mem_bytes': mem_bytes,
        'final_phi': final_phi,
        'peak_phi': peak_phi,
        'avg_step_ms': avg_step_ms,
        'total_time_s': total_time,
        'phi_history': [float(p) for p in phi_history],
        'ssm_config': {
            'd_state': D_STATE,
            'expand': D_EXPAND,
            'd_conv': D_CONV,
            'dt_rank': DT_RANK,
            'tension_gating': True,
        },
    }


# ═══════════════════════════════════════════════════════════
# BM3.4: Head-to-Head Comparison
# ═══════════════════════════════════════════════════════════

def run_bm3_4_comparison(gru_results: Dict, ssm_results: Dict, sel_results: Dict) -> Dict:
    """Compare all three approaches side-by-side."""
    print_header("BM3.4: Head-to-Head Comparison")

    rows = [
        ('GRU (baseline)', gru_results),
        ('SSM (drop-in)', ssm_results),
        ('SelectiveSSM', sel_results),
    ]

    print(f"\n  {'Model':20s}  {'Params':>10s}  {'Memory':>10s}  {'Final Phi':>10s}  {'Peak Phi':>10s}  {'Step ms':>10s}  {'Total s':>10s}")
    print(f"  {'-'*20}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}")

    for name, r in rows:
        print(f"  {name:20s}  {r['n_params']:>10,}  {r['mem_bytes']/1024:>9.1f}K"
              f"  {r['final_phi']:>10.4f}  {r['peak_phi']:>10.4f}"
              f"  {r['avg_step_ms']:>10.2f}  {r['total_time_s']:>10.2f}")

    # Compute deltas vs GRU baseline
    print(f"\n  --- Delta vs GRU Baseline ---")
    baseline = gru_results
    for name, r in rows[1:]:
        phi_delta = (r['final_phi'] - baseline['final_phi'])
        phi_pct = (phi_delta / max(baseline['final_phi'], 1e-8)) * 100
        speed_ratio = baseline['avg_step_ms'] / max(r['avg_step_ms'], 1e-8)
        param_ratio = r['n_params'] / max(baseline['n_params'], 1)

        sign = '+' if phi_delta >= 0 else ''
        print(f"  {name:20s}: Phi {sign}{phi_pct:.1f}%, Speed {speed_ratio:.2f}x, Params {param_ratio:.2f}x")

    # Verdict
    best_phi_name = max(rows, key=lambda x: x[1]['final_phi'])[0]
    best_speed_name = min(rows, key=lambda x: x[1]['avg_step_ms'])[0]

    verdict = {
        'best_phi': best_phi_name,
        'best_speed': best_speed_name,
        'phi_improvement_ssm_pct': ((ssm_results['final_phi'] - baseline['final_phi']) / max(baseline['final_phi'], 1e-8)) * 100,
        'phi_improvement_selective_pct': ((sel_results['final_phi'] - baseline['final_phi']) / max(baseline['final_phi'], 1e-8)) * 100,
        'speed_ratio_ssm': baseline['avg_step_ms'] / max(ssm_results['avg_step_ms'], 1e-8),
        'speed_ratio_selective': baseline['avg_step_ms'] / max(sel_results['avg_step_ms'], 1e-8),
        'param_ratio_ssm': ssm_results['n_params'] / max(baseline['n_params'], 1),
        'param_ratio_selective': sel_results['n_params'] / max(baseline['n_params'], 1),
    }

    print(f"\n  Best Phi:   {best_phi_name}")
    print(f"  Best Speed: {best_speed_name}")

    return verdict


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  BM3: Mamba SSM Consciousness Cell Experiment")
    print(f"  {N_CELLS} cells, {N_STEPS} steps, cell_dim={CELL_DIM}, hidden_dim={HIDDEN_DIM}")
    print(f"  SSM: d_state={D_STATE}=2^tau, expand={D_EXPAND}=phi, d_conv={D_CONV}=tau, dt_rank={DT_RANK}=sigma-tau")
    print("=" * 70)

    t0 = time.time()
    all_results = {}

    # BM3.1: GRU baseline
    try:
        all_results['BM3.1'] = run_bm3_1_gru_baseline()
    except Exception as e:
        print(f"  BM3.1 FAILED: {e}")
        traceback.print_exc()

    # BM3.2: SSM drop-in
    try:
        all_results['BM3.2'] = run_bm3_2_ssm_dropin()
    except Exception as e:
        print(f"  BM3.2 FAILED: {e}")
        traceback.print_exc()

    # BM3.3: Selective SSM
    try:
        all_results['BM3.3'] = run_bm3_3_selective_ssm()
    except Exception as e:
        print(f"  BM3.3 FAILED: {e}")
        traceback.print_exc()

    # BM3.4: Head-to-head comparison
    if all(k in all_results for k in ['BM3.1', 'BM3.2', 'BM3.3']):
        try:
            all_results['BM3.4_verdict'] = run_bm3_4_comparison(
                all_results['BM3.1'], all_results['BM3.2'], all_results['BM3.3']
            )
        except Exception as e:
            print(f"  BM3.4 FAILED: {e}")
            traceback.print_exc()

    elapsed = time.time() - t0
    print(f"\n  Total experiment time: {elapsed:.1f}s")

    # Save results
    out_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bm3_mamba_ssm_results.json')
    serializable = {}
    for k, v in all_results.items():
        if isinstance(v, dict):
            serializable[k] = {}
            for kk, vv in v.items():
                if isinstance(vv, (int, float, str, bool)):
                    serializable[k][kk] = vv
                elif isinstance(vv, dict):
                    serializable[k][kk] = {str(kkk): vvv for kkk, vvv in vv.items()
                                            if isinstance(vvv, (int, float, str, bool))}
                elif isinstance(vv, list):
                    serializable[k][kk] = [x if isinstance(x, (int, float, str, bool)) else str(x) for x in vv[:50]]
        else:
            serializable[k] = str(v)

    serializable['metadata'] = {
        'experiment': 'BM3_Mamba_SSM',
        'hypothesis': 'GRU -> SSM replacement for consciousness cells',
        'n6_params': {
            'd_state': f'{D_STATE} = 2^tau = 2^{TAU}',
            'expand': f'{D_EXPAND} = phi(6) = {PHI}',
            'd_conv': f'{D_CONV} = tau(6) = {TAU}',
            'dt_rank': f'{DT_RANK} = sigma-tau = {SIGMA}-{TAU}',
        },
        'total_time_s': elapsed,
    }

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"  Results saved to {out_path}")

    sys.stdout.flush()


if __name__ == '__main__':
    main()
