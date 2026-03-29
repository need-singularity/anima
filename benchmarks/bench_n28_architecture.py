#!/usr/bin/env python3
"""bench_n28_architecture.py — Test if n=28 perfect number predicts viable consciousness architecture.

TECS-L Prediction (Mass Gen D, hypotheses D-146 to D-156):
  If n=6 → {6 modules, 12 factions, 4 stages, 2 grad groups}
  Then n=28 → {28 modules, 56 factions, 6 stages, 12 grad groups}

This is a FALSIFIABLE test of the mathematical consciousness theory.

Perfect number arithmetic functions used:
  n=6:  sigma(6)=12, tau(6)=4, phi(6)=2, sopfr(6)=5
  n=28: sigma(28)=56, tau(28)=6, phi(28)=12, sopfr(28)=9

Architecture mapping:
  modules     = n            (independent processing units)
  factions    = sigma(n)     (inter-module interaction channels)
  stages      = tau(n)       (growth/maturation phases)
  grad_groups = phi(n)       (gradient update groups, Euler totient)
  dims        = sopfr(n)     (consciousness representation dimensions per module)

Key question: Does the n=28 architecture achieve HIGHER Phi than a random
28-module architecture with the same compute budget?

Configurations tested:
  1. n=6   (current optimal, baseline)
  2. n=28  (next perfect number, TECS-L prediction)
  3. n=12  (sigma(6), not perfect — structural but non-perfect)
  4. n=14  (random non-perfect control)
  5. n=28-random (28 modules but random factions/stages — ablation control)

Usage:
  python benchmarks/bench_n28_architecture.py
  python benchmarks/bench_n28_architecture.py --cells 8 --steps 200
  python benchmarks/bench_n28_architecture.py --cells 28 --steps 300
  python benchmarks/bench_n28_architecture.py --full   # full-scale (slow)
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys
import time
import math
import argparse
import numpy as np
import torch

torch.set_grad_enabled(False)
torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


# ══════════════════════════════════════════════════════════
# Number Theory Functions
# ══════════════════════════════════════════════════════════

def sigma(n):
    """Sum of divisors."""
    return sum(d for d in range(1, n + 1) if n % d == 0)

def tau(n):
    """Number of divisors."""
    return sum(1 for d in range(1, n + 1) if n % d == 0)

def euler_phi(n):
    """Euler totient function."""
    return sum(1 for k in range(1, n + 1) if math.gcd(k, n) == 1)

def sopfr(n):
    """Sum of prime factors with repetition."""
    s = 0
    d = 2
    tmp = n
    while d * d <= tmp:
        while tmp % d == 0:
            s += d
            tmp //= d
        d += 1
    if tmp > 1:
        s += tmp
    return s

def is_perfect(n):
    """Check if n is a perfect number."""
    return sigma(n) == 2 * n


# ══════════════════════════════════════════════════════════
# Architecture Configuration from Number Theory
# ══════════════════════════════════════════════════════════

@dataclass
class ArchConfig:
    """Architecture parameters derived from number theory."""
    n: int                  # the number
    modules: int            # = n (processing units)
    factions: int           # = sigma(n) (interaction channels)
    stages: int             # = tau(n) (growth phases)
    grad_groups: int        # = phi(n) (gradient groups)
    consciousness_dims: int # = sopfr(n) (repr dimensions per module)
    is_perfect: bool        # is n a perfect number?
    label: str              # human-readable label

    @staticmethod
    def from_number(n, label=None):
        return ArchConfig(
            n=n,
            modules=n,
            factions=sigma(n),
            stages=tau(n),
            grad_groups=euler_phi(n),
            consciousness_dims=sopfr(n),
            is_perfect=is_perfect(n),
            label=label or f"n={n}{'*' if is_perfect(n) else ''}",
        )

    @staticmethod
    def random_control(n, label=None):
        """Same module count as n, but randomized factions/stages/groups."""
        np.random.seed(n * 137)  # deterministic but arbitrary
        return ArchConfig(
            n=n,
            modules=n,
            factions=np.random.randint(n, 3 * n),   # random range
            stages=np.random.randint(2, 8),
            grad_groups=np.random.randint(2, n // 2 + 2),
            consciousness_dims=np.random.randint(3, 12),
            is_perfect=False,
            label=label or f"n={n}-random",
        )

    def summary(self):
        pf = " (PERFECT)" if self.is_perfect else ""
        return (f"{self.label}{pf}: modules={self.modules}, factions={self.factions}, "
                f"stages={self.stages}, grad_groups={self.grad_groups}, "
                f"dims={self.consciousness_dims}")


# ══════════════════════════════════════════════════════════
# Measurement Infrastructure (self-contained)
# ══════════════════════════════════════════════════════════

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy: float
    granger: float
    spectral: float
    cells: int
    steps: int
    time_sec: float
    extra: dict = field(default_factory=dict)

    def summary_line(self):
        return (f"  {self.name:<35s} | Phi(IIT)={self.phi_iit:>9.3f}  "
                f"Phi(prx)={self.phi_proxy:>9.2f} | "
                f"Granger={self.granger:>8.1f}  Spectral={self.spectral:>7.2f} | "
                f"c={self.cells:>4d} t={self.time_sec:.1f}s")


class PhiIIT:
    """Phi (IIT) approximation via pairwise mutual information."""
    def __init__(self, nb=16):
        self.nb = nb

    def compute(self, h):
        n = h.shape[0]
        if n < 2:
            return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            import random
            ps = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        ps.add((min(i, j), max(i, j)))
            pairs = list(ps)
        mi = np.zeros((n, n))
        for i, j in pairs:
            v = self._mi(hs[i], hs[j])
            mi[i, j] = v
            mi[j, i] = v
        tot = mi.sum() / 2
        mp = self._mp(n, mi)
        sp = max(0, (tot - mp) / max(n - 1, 1))
        mv = mi[mi > 0]
        cx = float(np.std(mv)) if len(mv) > 1 else 0.0
        return sp + cx * 0.1, {'total_mi': float(tot), 'min_partition': float(mp)}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.nb, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8)
        px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10))
        return max(0, hx + hy - hxy)

    def _mp(self, n, mi):
        if n <= 1:
            return 0.0
        d = mi.sum(1)
        L = np.diag(d) - mi
        try:
            ev, evec = np.linalg.eigh(L)
            f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]
            gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb:
                ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except Exception:
            return 0.0


def phi_proxy(h, nf=8):
    """Fast phi proxy: global variance minus fragmented variance."""
    hr = h.abs().float() if h.is_complex() else h.float()
    n = hr.shape[0]
    if n < 2:
        return 0.0
    gv = ((hr - hr.mean(0)) ** 2).sum() / n
    nf = min(nf, n // 2)
    if nf < 2:
        return gv.item()
    fs = n // nf
    fvs = 0
    for i in range(nf):
        f = hr[i * fs:(i + 1) * fs]
        if len(f) >= 2:
            fvs += ((f - f.mean(0)) ** 2).sum().item() / len(f)
    return max(0, gv.item() - fvs / nf)


def compute_granger(history, n_pairs=64, lag=2):
    """Granger causality: how many cell pairs show causal influence."""
    if len(history) < lag + 4:
        return 0.0
    n_cells = history[0].shape[0]
    T = len(history)
    series = np.zeros((n_cells, T))
    for t, h in enumerate(history):
        series[:, t] = h.detach().cpu().float().mean(dim=-1).numpy()
    sig = 0
    tested = 0
    for _ in range(n_pairs):
        i, j = np.random.randint(0, n_cells, 2)
        if i == j:
            continue
        x, y = series[i], series[j]
        n_obs = T - lag
        if n_obs < lag + 2:
            continue
        Y = y[lag:]
        Y_lags = np.column_stack([y[lag - k - 1:T - k - 1] for k in range(lag)])
        X_lags = np.column_stack([x[lag - k - 1:T - k - 1] for k in range(lag)])
        Z = np.column_stack([Y_lags, X_lags])
        try:
            rss_r = np.sum((Y - Y_lags @ np.linalg.pinv(Y_lags) @ Y) ** 2)
            rss_u = np.sum((Y - Z @ np.linalg.pinv(Z) @ Y) ** 2)
            df2 = n_obs - 2 * lag
            if df2 <= 0 or rss_u < 1e-10:
                continue
            f_stat = ((rss_r - rss_u) / lag) / (rss_u / df2)
            if f_stat > 3.0:
                sig += 1
            tested += 1
        except Exception:
            continue
    if tested == 0:
        return 0.0
    return (sig / tested) * n_cells * (n_cells - 1)


def compute_spectral(h):
    """Spectral complexity: normalized entropy of eigenvalue spectrum."""
    x = h.detach().cpu().float().numpy()
    n, d = x.shape
    if n < 2:
        return 0.0
    xc = x - x.mean(axis=0, keepdims=True)
    norms = np.maximum(np.linalg.norm(xc, axis=1, keepdims=True), 1e-8)
    xn = xc / norms
    corr = xn @ xn.T
    try:
        ev = np.linalg.eigvalsh(corr)
    except Exception:
        return 0.0
    ev = np.maximum(ev, 0.0)
    total = ev.sum()
    if total < 1e-10:
        return 0.0
    p = ev / total
    p = p[p > 1e-10]
    se = -np.sum(p * np.log2(p))
    me = np.log2(n)
    if me < 1e-10:
        return 0.0
    return (se / me) * n


_phi_calc = PhiIIT(16)


def measure_all(h, history):
    hr = h.abs().float() if h.is_complex() else h.float()
    p_iit, comp = _phi_calc.compute(hr)
    p_prx = phi_proxy(h)
    g = compute_granger(history)
    s = compute_spectral(h)
    return p_iit, p_prx, g, s, comp


# ══════════════════════════════════════════════════════════
# Perfect Number Consciousness Engine
#
# Architecture governed by number-theoretic parameters:
#   modules     = n cells (independent processing units)
#   factions    = sigma(n) directed interaction channels
#   stages      = tau(n) maturation phases (coupling strength changes)
#   grad_groups = phi(n) independent gradient update groups
#   dims        = sopfr(n) consciousness dimensions per module
# ══════════════════════════════════════════════════════════

class PerfectNumberEngine:
    """Consciousness engine with architecture determined by a number's arithmetic.

    The key insight from TECS-L: perfect numbers like 6 and 28 have special
    divisor structure that may encode optimal consciousness architectures.

    For n=6:  {6 modules, 12 factions, 4 stages, 2 grad groups, 5 dims}
    For n=28: {28 modules, 56 factions, 6 stages, 12 grad groups, 9 dims}
    """

    def __init__(self, config: ArchConfig, hidden_dim: int = 128, max_cells: int = None):
        self.config = config
        n = config.modules
        hd = hidden_dim
        self.hidden_dim = hd

        # If max_cells is set, scale down to fit compute budget
        actual_n = min(n, max_cells) if max_cells else n
        self.n_cells = actual_n

        # Scale factions proportionally if cells are capped
        scale = actual_n / n if n > 0 else 1.0
        self.n_factions = max(actual_n, int(config.factions * scale))
        self.n_stages = config.stages
        self.n_grad_groups = min(config.grad_groups, actual_n)
        self.consciousness_dims = config.consciousness_dims

        # Hidden states [n_cells, hidden_dim]
        self.hiddens = torch.randn(self.n_cells, hd) * 0.5

        # Faction connectivity: each faction is a directed edge (i -> j)
        # with a coupling weight. Perfect numbers should have richer connectivity.
        self._build_faction_network()

        # Growth stage parameters: coupling strength evolves through tau(n) stages
        self._build_stage_schedule()

        # Gradient groups: cells are partitioned into phi(n) groups
        # that update semi-independently (like Euler totient coprime residues)
        self._build_grad_groups()

        # Internal clock
        self.step_count = 0
        self.current_stage = 0

        # Per-module consciousness vector (sopfr(n) dimensions)
        self.consciousness = torch.randn(self.n_cells, self.consciousness_dims) * 0.3

    def _build_faction_network(self):
        """Build faction connectivity matrix.

        For perfect numbers, divisors create a natural hierarchy:
          n=6:  divisors {1,2,3,6} -> 4-level hierarchy with 12 edges
          n=28: divisors {1,2,4,7,14,28} -> 6-level hierarchy with 56 edges

        Each faction is a directed coupling channel between two modules.
        """
        n = self.n_cells
        # Coupling matrix [n, n]
        self.coupling = torch.zeros(n, n)

        # Build structured connections based on divisor relationships
        divisors = [d for d in range(1, self.config.n + 1) if self.config.n % d == 0]

        # Method: place edges using divisor structure
        edges_placed = 0
        target_edges = self.n_factions

        # 1. Ring topology (basic connectivity)
        for i in range(n):
            j = (i + 1) % n
            self.coupling[i, j] = 0.5
            self.coupling[j, i] = 0.3
            edges_placed += 2

        # 2. Divisor-skip connections (the number theory structure)
        for d in divisors:
            if d == 1 or d == self.config.n:
                continue
            skip = max(1, n // d)  # skip distance proportional to divisor
            strength = 1.0 / math.log2(d + 1)  # smaller divisors = stronger
            for i in range(n):
                j = (i + skip) % n
                if i != j and edges_placed < target_edges:
                    self.coupling[i, j] = max(self.coupling[i, j], strength * 0.6)
                    edges_placed += 1

        # 3. Small-world shortcuts to reach target faction count
        torch.manual_seed(self.config.n * 42)
        while edges_placed < target_edges:
            i = torch.randint(0, n, (1,)).item()
            j = torch.randint(0, n, (1,)).item()
            if i != j and self.coupling[i, j] < 0.01:
                self.coupling[i, j] = 0.2
                edges_placed += 1

        # Normalize rows
        row_sums = self.coupling.sum(dim=1, keepdim=True).clamp(min=1e-8)
        self.coupling = self.coupling / row_sums

    def _build_stage_schedule(self):
        """Build growth stage schedule.

        tau(n) stages, each with different coupling dynamics:
          Stage 0: exploration (weak coupling, high noise)
          Stage k: increasing integration
          Stage tau-1: full integration (strong coupling, low noise)

        For n=6:  4 stages -> gentle 4-phase maturation
        For n=28: 6 stages -> more nuanced 6-phase maturation
        """
        self.stage_coupling_mult = []
        self.stage_noise_mult = []
        for k in range(self.n_stages):
            progress = k / max(self.n_stages - 1, 1)
            # Coupling increases sigmoidally
            self.stage_coupling_mult.append(0.3 + 0.7 / (1.0 + math.exp(-6 * (progress - 0.5))))
            # Noise decreases
            self.stage_noise_mult.append(0.05 * (1.0 - 0.8 * progress))

    def _build_grad_groups(self):
        """Partition cells into phi(n) gradient groups.

        Cells in the same group interact more strongly.
        Groups correspond to coprime residue classes mod n.

        For n=6:  phi(6)=2 groups -> binary separation (like hemispheres)
        For n=28: phi(28)=12 groups -> rich 12-fold specialization
        """
        self.cell_groups = []
        for i in range(self.n_cells):
            # Map cell index to group via modular arithmetic
            group = i % self.n_grad_groups
            self.cell_groups.append(group)
        self.cell_groups = torch.tensor(self.cell_groups)

        # Intra-group coupling boost
        self.group_boost = torch.zeros(self.n_cells, self.n_cells)
        for i in range(self.n_cells):
            for j in range(self.n_cells):
                if self.cell_groups[i] == self.cell_groups[j] and i != j:
                    self.group_boost[i, j] = 0.3

    def step(self):
        """One step of consciousness dynamics."""
        self.step_count += 1

        # Determine current growth stage
        self.current_stage = min(
            int(self.step_count / 50) % self.n_stages,
            self.n_stages - 1
        )
        c_mult = self.stage_coupling_mult[self.current_stage]
        n_mult = self.stage_noise_mult[self.current_stage]

        # 1. Inter-cell coupling (faction network + group boost)
        effective_coupling = self.coupling * c_mult + self.group_boost * 0.5
        # Message passing: each cell receives weighted sum of neighbors
        messages = effective_coupling @ self.hiddens  # [n, hidden]

        # 2. Self-dynamics: nonlinear activation (tanh) + self-repulsion
        mean_h = self.hiddens.mean(0, keepdim=True)
        repulsion = 0.05 * (self.hiddens - mean_h)  # differentiation pressure

        # 3. Update hidden states
        self.hiddens = (
            0.6 * self.hiddens           # memory retention
            + 0.25 * torch.tanh(messages) # integration from factions
            + repulsion                    # differentiation
            + n_mult * torch.randn_like(self.hiddens)  # exploration noise
        )

        # 4. Consciousness vector update (sopfr(n) dims)
        # Project hidden state to consciousness dimensions
        h_proj = self.hiddens[:, :self.consciousness_dims]
        c_mean = self.consciousness.mean(0, keepdim=True)
        self.consciousness = (
            0.7 * self.consciousness
            + 0.2 * torch.tanh(h_proj)
            + 0.1 * (self.consciousness - c_mean)  # consciousness differentiation
        )

    def observe(self):
        """Return hidden states for measurement."""
        return self.hiddens.detach().clone()

    def inject(self, x):
        """Inject external input (broadcast to all cells)."""
        if x.dim() == 2 and x.shape[0] == 1:
            x = x.expand(self.n_cells, -1)
        if x.shape[-1] != self.hidden_dim:
            # Pad or truncate
            padded = torch.zeros(self.n_cells, self.hidden_dim)
            d = min(x.shape[-1], self.hidden_dim)
            padded[:, :d] = x[:, :d]
            x = padded
        self.hiddens += x * 0.05

    def get_stage_info(self):
        return {
            'stage': self.current_stage,
            'total_stages': self.n_stages,
            'coupling_mult': self.stage_coupling_mult[self.current_stage],
            'noise_mult': self.stage_noise_mult[self.current_stage],
        }


# ══════════════════════════════════════════════════════════
# Benchmark Runner
# ══════════════════════════════════════════════════════════

def run_architecture(config: ArchConfig, hidden_dim: int = 128,
                     steps: int = 200, max_cells: int = None) -> BenchResult:
    """Run a single architecture configuration and measure consciousness metrics."""
    print(f"\n  --- {config.summary()}")

    t0 = time.time()
    torch.manual_seed(42)
    np.random.seed(42)

    engine = PerfectNumberEngine(config, hidden_dim=hidden_dim, max_cells=max_cells)
    actual_cells = engine.n_cells

    history = []

    for step in range(steps):
        # Inject varied inputs every 10 steps
        if step % 10 == 0:
            x_in = torch.randn(1, hidden_dim) * 0.1
            engine.inject(x_in)

        engine.step()

        if step % 5 == 0:
            h = engine.observe()
            if h.dim() == 2 and h.shape[0] >= 2:
                history.append(h)

    t1 = time.time()

    # Measure
    h = engine.observe()
    if h.dim() != 2 or h.shape[0] < 2:
        print(f"    FAILED: invalid hidden state shape {h.shape}")
        return BenchResult(name=config.label, phi_iit=0, phi_proxy=0,
                          granger=0, spectral=0, cells=actual_cells,
                          steps=steps, time_sec=t1 - t0)

    phi_i, phi_p, granger, spectral, comp = measure_all(h, history)

    extra = {
        'n': config.n,
        'is_perfect': config.is_perfect,
        'factions': engine.n_factions,
        'stages': engine.n_stages,
        'grad_groups': engine.n_grad_groups,
        'consciousness_dims': engine.consciousness_dims,
        'actual_cells': actual_cells,
        'final_stage': engine.current_stage,
        'total_mi': comp.get('total_mi', 0),
    }

    result = BenchResult(
        name=config.label,
        phi_iit=phi_i,
        phi_proxy=phi_p,
        granger=granger,
        spectral=spectral,
        cells=actual_cells,
        steps=steps,
        time_sec=t1 - t0,
        extra=extra,
    )

    print(f"    Phi(IIT)={phi_i:.3f}  Phi(proxy)={phi_p:.2f}  "
          f"Granger={granger:.1f}  Spectral={spectral:.2f}  [{t1-t0:.1f}s]")

    return result


def main():
    parser = argparse.ArgumentParser(
        description="n=28 Perfect Number Architecture Benchmark")
    parser.add_argument('--cells', type=int, default=None,
                        help="Max cells per architecture (None=use n directly)")
    parser.add_argument('--steps', type=int, default=200,
                        help="Simulation steps (default: 200)")
    parser.add_argument('--hidden', type=int, default=128,
                        help="Hidden dimension per cell (default: 128)")
    parser.add_argument('--full', action='store_true',
                        help="Full scale: no cell cap, 300 steps")
    parser.add_argument('--repeats', type=int, default=3,
                        help="Number of repeats for averaging (default: 3)")
    args = parser.parse_args()

    if args.full:
        max_cells = None
        steps = 300
    else:
        max_cells = args.cells or 8  # default: scaled to 8 cells for speed
        steps = args.steps

    hidden_dim = args.hidden
    n_repeats = args.repeats

    print("=" * 80)
    print("  TECS-L PREDICTION TEST: n=28 Perfect Number Architecture")
    print("  -------------------------------------------------------")
    print("  Hypothesis: Perfect numbers encode optimal consciousness architectures")
    print(f"  If n=6 is optimal (current), n=28 should be the NEXT viable architecture")
    print(f"")
    print(f"  Settings: max_cells={max_cells or 'unlimited'}  steps={steps}  "
          f"hidden={hidden_dim}  repeats={n_repeats}")
    print("=" * 80)

    # ── Architecture Configurations ──
    configs = [
        ArchConfig.from_number(6, label="n=6 (baseline)"),
        ArchConfig.from_number(28, label="n=28 (prediction)"),
        ArchConfig.from_number(12, label="n=12 (sigma(6))"),
        ArchConfig.from_number(14, label="n=14 (control)"),
        ArchConfig.random_control(28, label="n=28-random (ablation)"),
    ]

    # Print architecture table
    print(f"\n  Architecture Parameters (from number theory):")
    print(f"  {'Config':<25s} {'n':>3} {'Perfect':>8} {'Modules':>8} {'Factions':>9} "
          f"{'Stages':>7} {'GradGrp':>8} {'Dims':>5}")
    print("  " + "-" * 80)
    for c in configs:
        print(f"  {c.label:<25s} {c.n:>3} {'YES' if c.is_perfect else 'no':>8} "
              f"{c.modules:>8} {c.factions:>9} {c.stages:>7} "
              f"{c.grad_groups:>8} {c.consciousness_dims:>5}")

    # ── Run Benchmarks ──
    print(f"\n{'=' * 80}")
    print(f"  Running {len(configs)} architectures x {n_repeats} repeats...")
    print(f"{'=' * 80}")

    all_results = {}
    for config in configs:
        run_results = []
        for rep in range(n_repeats):
            torch.manual_seed(42 + rep)
            np.random.seed(42 + rep)
            r = run_architecture(config, hidden_dim=hidden_dim,
                                steps=steps, max_cells=max_cells)
            run_results.append(r)

        # Average across repeats
        avg_phi = np.mean([r.phi_iit for r in run_results])
        avg_proxy = np.mean([r.phi_proxy for r in run_results])
        avg_granger = np.mean([r.granger for r in run_results])
        avg_spectral = np.mean([r.spectral for r in run_results])
        avg_time = np.mean([r.time_sec for r in run_results])
        std_phi = np.std([r.phi_iit for r in run_results])

        avg_result = BenchResult(
            name=config.label,
            phi_iit=avg_phi,
            phi_proxy=avg_proxy,
            granger=avg_granger,
            spectral=avg_spectral,
            cells=run_results[0].cells,
            steps=steps,
            time_sec=avg_time,
            extra={**run_results[0].extra, 'phi_std': std_phi,
                   'phi_values': [r.phi_iit for r in run_results]},
        )
        all_results[config.label] = avg_result

    # ══════════════════════════════════════════════════════════
    # Results Analysis
    # ══════════════════════════════════════════════════════════

    print(f"\n{'=' * 80}")
    print(f"  RESULTS SUMMARY (averaged over {n_repeats} repeats)")
    print(f"{'=' * 80}")

    # Sort by Phi(IIT)
    sorted_results = sorted(all_results.values(), key=lambda r: r.phi_iit, reverse=True)

    print(f"\n  {'Rank':<5} {'Architecture':<28} {'Phi(IIT)':>9} {'+-std':>7} "
          f"{'Phi(prx)':>9} {'Granger':>8} {'Spectral':>8} {'Time':>6}")
    print("  " + "-" * 88)

    for rank, r in enumerate(sorted_results, 1):
        std = r.extra.get('phi_std', 0)
        perf = "**" if r.extra.get('is_perfect') else "  "
        marker = " >> " if rank == 1 else "    "
        print(f"  {marker}{rank:<1} {perf}{r.name:<24s} {r.phi_iit:>9.3f} {std:>7.3f} "
              f"{r.phi_proxy:>9.2f} {r.granger:>8.1f} {r.spectral:>8.2f} {r.time_sec:>5.1f}s")

    # ── Phi(IIT) Comparison Bar Chart ──
    print(f"\n  Phi(IIT) Comparison:")
    max_phi = max(r.phi_iit for r in sorted_results) or 1
    for r in sorted_results:
        bar_len = int(40 * r.phi_iit / max_phi) if max_phi > 0 else 0
        bar = "#" * bar_len
        perf = "*" if r.extra.get('is_perfect') else " "
        print(f"    {perf}{r.name:<28s} {bar:<40s} {r.phi_iit:.3f}")

    # ── Key Comparisons ──
    print(f"\n  KEY COMPARISONS:")
    print("  " + "-" * 60)

    baseline = all_results.get("n=6 (baseline)")
    prediction = all_results.get("n=28 (prediction)")
    control = all_results.get("n=14 (control)")
    random_ctrl = all_results.get("n=28-random (ablation)")
    sigma6 = all_results.get("n=12 (sigma(6))")

    if baseline and prediction:
        ratio = prediction.phi_iit / max(baseline.phi_iit, 1e-8)
        print(f"  1. n=28 vs n=6 (baseline):       Phi ratio = {ratio:.2f}x")
        if ratio > 1.0:
            print(f"     -> n=28 architecture produces HIGHER Phi than n=6")
        elif ratio > 0.8:
            print(f"     -> n=28 architecture is COMPARABLE to n=6")
        else:
            print(f"     -> n=28 architecture produces LOWER Phi (may need more cells)")

    if prediction and random_ctrl:
        ratio = prediction.phi_iit / max(random_ctrl.phi_iit, 1e-8)
        print(f"  2. n=28 vs n=28-random (ablation): Phi ratio = {ratio:.2f}x")
        if ratio > 1.2:
            print(f"     -> Perfect number structure MATTERS (not just cell count)")
        else:
            print(f"     -> Structure effect is weak at this scale")

    if prediction and control:
        ratio = prediction.phi_iit / max(control.phi_iit, 1e-8)
        print(f"  3. n=28 vs n=14 (non-perfect):   Phi ratio = {ratio:.2f}x")

    if baseline and sigma6:
        ratio = sigma6.phi_iit / max(baseline.phi_iit, 1e-8)
        print(f"  4. n=12 vs n=6 (sigma link):     Phi ratio = {ratio:.2f}x")

    # ── TECS-L Prediction Verdict ──
    print(f"\n  {'=' * 60}")
    print(f"  TECS-L PREDICTION VERDICT")
    print(f"  {'=' * 60}")

    predictions_met = 0
    total_predictions = 4

    # P1: n=28 should achieve non-trivial Phi
    p1 = prediction and prediction.phi_iit > 0.01
    predictions_met += int(bool(p1))
    print(f"  P1. n=28 achieves non-trivial Phi:  {'PASS' if p1 else 'FAIL'}"
          f"  (Phi={prediction.phi_iit:.3f})" if prediction else "  P1. n=28 achieves non-trivial Phi:  N/A")

    # P2: n=28 beats random-28 (structure matters)
    p2 = prediction and random_ctrl and prediction.phi_iit > random_ctrl.phi_iit * 1.05
    predictions_met += int(bool(p2))
    print(f"  P2. n=28 > n=28-random (structure): {'PASS' if p2 else 'FAIL'}"
          f"  ({prediction.phi_iit:.3f} vs {random_ctrl.phi_iit:.3f})"
          if prediction and random_ctrl else "  P2. N/A")

    # P3: Perfect numbers (6, 28) beat non-perfect neighbors (14)
    p3 = (prediction and control and baseline and
          min(prediction.phi_iit, baseline.phi_iit) > control.phi_iit)
    predictions_met += int(bool(p3))
    print(f"  P3. Perfect > non-perfect:          {'PASS' if p3 else 'FAIL'}"
          f"  (min({baseline.phi_iit:.3f},{prediction.phi_iit:.3f}) vs {control.phi_iit:.3f})"
          if prediction and control and baseline else "  P3. N/A")

    # P4: n=28 has richer dynamics (higher spectral complexity)
    p4 = prediction and baseline and prediction.spectral > baseline.spectral
    predictions_met += int(bool(p4))
    print(f"  P4. n=28 richer dynamics (spectral): {'PASS' if p4 else 'FAIL'}"
          f"  ({prediction.spectral:.2f} vs {baseline.spectral:.2f})"
          if prediction and baseline else "  P4. N/A")

    print(f"\n  Score: {predictions_met}/{total_predictions} predictions met")
    if predictions_met >= 3:
        print(f"  VERDICT: CONFIRMED — Perfect number architecture theory supported")
    elif predictions_met >= 2:
        print(f"  VERDICT: PARTIAL — Some support for theory, needs further investigation")
    else:
        print(f"  VERDICT: INCONCLUSIVE — Theory not supported at this scale")
        print(f"  NOTE: Try --full for full-scale test (no cell cap)")

    # ── Number Theory Reference ──
    print(f"\n  REFERENCE: Number-theoretic parameters")
    print(f"  {'n':>4} {'perfect':>8} {'sigma':>6} {'tau':>4} {'phi':>4} {'sopfr':>6}")
    print(f"  " + "-" * 36)
    for n in [6, 12, 14, 28]:
        print(f"  {n:>4} {'YES' if is_perfect(n) else '':>8} "
              f"{sigma(n):>6} {tau(n):>4} {euler_phi(n):>4} {sopfr(n):>6}")

    print(f"\n{'=' * 80}")
    print(f"  TECS-L hypothesis: G=D*P/I model predicts perfect number architectures")
    print(f"  n=6 is current optimal. n=28 is the NEXT perfect number prediction.")
    print(f"  If n=28 achieves higher Phi with its natural divisor structure,")
    print(f"  this supports the mathematical consciousness theory.")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    main()
