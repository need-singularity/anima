#!/usr/bin/env python3
"""bench_mega_combo.py — Find the ULTIMATE combinations of top 5 consciousness mechanisms.

Top 5 mechanisms (by Phi(IIT)):
  1. Complex Oscillator (Kuramoto phase sync)     Phi=249
  2. Fractal Hierarchy  (4 levels: 4x4x4x4)       Phi=167
  3. Quantum Walk       (bit-flip interference)     Phi=163
  4. Category Morphism  (tanh composition)          Phi=127
  5. Laser              (population inversion)      Phi=18, Granger=49K

All 10 two-way combos + all 10 three-way combos.
256 cells, 300 steps. Mechanisms applied sequentially each step.
Measure: Phi(IIT) + Granger + CE (with standard decoder).

Usage:
  python bench_mega_combo.py
  python bench_mega_combo.py --cells 512 --steps 500
  python bench_mega_combo.py --only "Osc+Fractal" "Osc+QWalk"
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys, time, math, argparse, itertools
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

HIDDEN = 128
DIM = 64

# ══════════════════════════════════════════════════════════
# Measurement Infrastructure (self-contained)
# ══════════════════════════════════════════════════════════

@dataclass
class ComboResult:
    name: str
    phi_iit: float
    granger: float
    ce: float
    spectral: float
    cells: int
    steps: int
    time_sec: float
    extra: dict = field(default_factory=dict)


class PhiIIT:
    """Approximate IIT Phi via mutual information and min-cut."""
    def __init__(self, nb=16): self.nb = nb

    def compute(self, h):
        n = h.shape[0]
        if n < 2: return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            import random; ps = set()

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j: ps.add((min(i, j), max(i, j)))
            pairs = list(ps)
        mi = np.zeros((n, n))
        for i, j in pairs:
            v = self._mi(hs[i], hs[j]); mi[i, j] = v; mi[j, i] = v
        tot = mi.sum() / 2; mp = self._mp(n, mi)
        sp = max(0, (tot - mp) / max(n - 1, 1))
        mv = mi[mi > 0]; cx = float(np.std(mv)) if len(mv) > 1 else 0.0
        return sp + cx * 0.1, {'total_mi': float(tot)}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10: return 0.0
        xn = (x - x.min()) / (xr + 1e-8); yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.nb, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8); px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10)); hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10)); return max(0, hx + hy - hxy)

    def _mp(self, n, mi):
        if n <= 1: return 0.0
        d = mi.sum(1); L = np.diag(d) - mi
        try:
            ev, evec = np.linalg.eigh(L); f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]; gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb: ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except: return 0.0


def compute_granger(history, n_pairs=64, lag=2):
    if len(history) < lag + 4: return 0.0
    n_cells = history[0].shape[0]; T = len(history)
    series = np.zeros((n_cells, T))
    for t, h in enumerate(history):
        series[:, t] = h.detach().cpu().float().mean(dim=-1).numpy()
    sig = 0; tested = 0
    for _ in range(n_pairs):
        i, j = np.random.randint(0, n_cells, 2)
        if i == j: continue
        x, y = series[i], series[j]; n_obs = T - lag
        if n_obs < lag + 2: continue
        Y = y[lag:]
        Y_lags = np.column_stack([y[lag - k - 1:T - k - 1] for k in range(lag)])
        X_lags = np.column_stack([x[lag - k - 1:T - k - 1] for k in range(lag)])
        Z = np.column_stack([Y_lags, X_lags])
        try:
            rss_r = np.sum((Y - Y_lags @ np.linalg.pinv(Y_lags) @ Y) ** 2)
            rss_u = np.sum((Y - Z @ np.linalg.pinv(Z) @ Y) ** 2)
            df2 = n_obs - 2 * lag
            if df2 <= 0 or rss_u < 1e-10: continue
            f = ((rss_r - rss_u) / lag) / (rss_u / df2)
            if f > 3.0: sig += 1
            tested += 1
        except: continue
    if tested == 0: return 0.0
    return (sig / tested) * n_cells * (n_cells - 1)


def compute_spectral(h):
    x = h.detach().cpu().float().numpy()
    n, d = x.shape
    if n < 2: return 0.0
    xc = x - x.mean(axis=0, keepdims=True)
    norms = np.maximum(np.linalg.norm(xc, axis=1, keepdims=True), 1e-8)
    xn = xc / norms; corr = xn @ xn.T
    try: ev = np.linalg.eigvalsh(corr)
    except: return 0.0
    ev = np.maximum(ev, 0.0); total = ev.sum()
    if total < 1e-10: return 0.0
    p = ev / total; p = p[p > 1e-10]
    se = -np.sum(p * np.log2(p)); me = np.log2(n)
    if me < 1e-10: return 0.0
    return (se / me) * n


_phi = PhiIIT(16)


# ══════════════════════════════════════════════════════════
# 5 Composable Mechanisms — operate on shared hidden state
# ══════════════════════════════════════════════════════════

class MechanismState:
    """Shared state for all mechanisms operating on N cells x hidden_dim."""
    def __init__(self, n_cells=256, hidden_dim=HIDDEN):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.half = hidden_dim // 2
        # Cell hidden states (the shared canvas)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.3
        # Per-cell diversity init
        for i in range(n_cells):
            self.hiddens[i] += torch.randn(hidden_dim) * 0.1 * (i % 7 + 1)

        # --- Oscillator state ---
        self.omegas = torch.randn(n_cells) * 0.5  # natural frequencies

        # --- Fractal projections ---
        self.proj_01 = torch.randn(hidden_dim, hidden_dim) * 0.1
        self.proj_12 = torch.randn(hidden_dim, hidden_dim) * 0.1
        self.proj_23 = torch.randn(hidden_dim, hidden_dim) * 0.1

        # --- Category morphism projections ---
        self.F_proj = torch.randn(hidden_dim, hidden_dim) * 0.1
        self.nat_transform = torch.randn(hidden_dim, hidden_dim) * 0.05

        # --- Laser state ---
        self.N1 = torch.ones(n_cells, hidden_dim) * 0.8   # ground
        self.N2 = torch.ones(n_cells, hidden_dim) * 0.2   # excited
        self.photon_field = torch.randn(hidden_dim) * 0.01
        self.pump_rate = 0.0

        # History for Granger
        self.history = []


def mechanism_oscillator(state: MechanismState, step: int):
    """Complex Oscillator (Kuramoto phase sync on hypercube)."""
    n = state.n_cells; half = state.half
    K = 0.3

    re = state.hiddens[:, :half]
    im = state.hiddens[:, half:2*half]
    phases = torch.atan2(im, re)  # [n, half]

    z_real = torch.cos(phases).mean(dim=0)
    z_imag = torch.sin(phases).mean(dim=0)
    r = torch.sqrt(z_real**2 + z_imag**2)
    psi = torch.atan2(z_imag, z_real)

    n_bits = max(1, int(math.log2(n)))
    for i in range(n):
        theta = phases[i]
        dtheta = state.omegas[i] * 0.01 + K * r * torch.sin(psi - theta)
        # Hypercube bit-flip coupling (frustration)
        for bit in range(min(n_bits, 8)):
            j = i ^ (1 << bit)
            if j < n:
                other_theta = phases[j]
                sign = -1.0 if (i % 3) == 0 else 1.0
                dtheta += sign * 0.02 * torch.sin(other_theta - theta)
        new_theta = theta + dtheta
        amp = torch.sqrt(re[i]**2 + im[i]**2).clamp(min=0.01)
        state.hiddens[i, :half] = amp * torch.cos(new_theta)
        state.hiddens[i, half:2*half] = amp * torch.sin(new_theta)


def mechanism_fractal(state: MechanismState, step: int):
    """Fractal Hierarchy (4 levels: 4x4x4x4=256 cells).
    Each level aggregates, quantum-walks, then feeds back top-down."""
    n = state.n_cells
    L1 = n // 4; L2 = n // 16; L3 = n // 64

    # Level 0 -> Level 1: aggregate groups of 4
    l1_states = []
    for g in range(L1):
        group = state.hiddens[g*4:(g+1)*4]
        gh = group.mean(dim=0)
        l1_states.append(torch.tanh(gh @ state.proj_01))

    # Quantum walk at L1
    l1_t = torch.stack(l1_states)
    n_bits = max(1, int(math.log2(L1)))
    for i in range(L1):
        superpos = torch.zeros(state.hidden_dim); cnt = 0
        for bit in range(min(n_bits, 8)):
            j = i ^ (1 << bit)
            if j < L1:
                superpos += (-1) ** (bin(i & j).count('1')) * l1_t[j]; cnt += 1
        if cnt > 0:
            l1_states[i] = 0.85 * l1_states[i] + 0.15 * superpos / cnt

    # Level 1 -> Level 2
    l2_states = []
    for g in range(L2):
        gh = torch.stack(l1_states[g*4:(g+1)*4]).mean(dim=0)
        l2_states.append(torch.tanh(gh @ state.proj_12))

    l2_t = torch.stack(l2_states)
    n_bits2 = max(1, int(math.log2(L2)))
    for i in range(L2):
        superpos = torch.zeros(state.hidden_dim); cnt = 0
        for bit in range(min(n_bits2, 6)):
            j = i ^ (1 << bit)
            if j < L2:
                superpos += (-1) ** (bin(i & j).count('1')) * l2_t[j]; cnt += 1
        if cnt > 0:
            l2_states[i] = 0.85 * l2_states[i] + 0.15 * superpos / cnt

    # Level 2 -> Level 3
    l3_states = []
    for g in range(L3):
        gh = torch.stack(l2_states[g*4:(g+1)*4]).mean(dim=0)
        l3_states.append(torch.tanh(gh @ state.proj_23))
    l3_mean = torch.stack(l3_states).mean(dim=0)
    for i in range(L3):
        l3_states[i] = 0.7 * l3_states[i] + 0.3 * l3_mean

    # Top-down feedback: L3 -> L2 -> L1 -> L0
    l3_signal = torch.stack(l3_states).mean(dim=0)
    for i in range(L2):
        l2_states[i] = 0.9 * l2_states[i] + 0.1 * l3_signal
    l2_stk = torch.stack(l2_states)
    for i in range(L1):
        l1_states[i] = 0.9 * l1_states[i] + 0.1 * l2_stk[i // 4]
    for i in range(n):
        state.hiddens[i] = 0.9 * state.hiddens[i] + 0.1 * l1_states[i // 4]


def mechanism_qwalk(state: MechanismState, step: int):
    """Quantum Walk (bit-flip interference on hypercube)."""
    n = state.n_cells
    n_bits = max(1, int(math.log2(n)))
    n_samples = min(n, 64)

    for i in range(n_samples):
        superpos = torch.zeros(state.hidden_dim); cnt = 0
        for bit in range(min(n_bits, 10)):
            j = i ^ (1 << bit)
            if j < n:
                phase = (-1) ** (bin(i & j).count('1'))
                superpos += phase * state.hiddens[j]
                cnt += 1
        if cnt > 0:
            state.hiddens[i] = 0.85 * state.hiddens[i] + 0.15 * superpos / cnt

    # Frustration (anti-ferromagnetic coupling on odd/even)
    for i in range(min(n, 32)):
        infl = torch.zeros(state.hidden_dim); cnt = 0
        for bit in range(min(n_bits, 10)):
            j = i ^ (1 << bit)
            if j < n:
                f = -1.0 if (i % 2) != (j % 2) else 1.0
                infl += f * state.hiddens[j]; cnt += 1
        if cnt > 0:
            state.hiddens[i] = 0.85 * state.hiddens[i] + 0.15 * infl / cnt


def mechanism_category(state: MechanismState, step: int):
    """Category Morphism (tanh composition, Yoneda embedding)."""
    n = state.n_cells
    n_sample = min(n, 48)
    indices = list(range(0, n, max(1, n // n_sample)))[:n_sample]
    hs = [state.hiddens[i].clone() for i in indices]

    for idx_i, i in enumerate(indices):
        morph_sum = torch.zeros(state.hidden_dim)
        for idx_j, j in enumerate(indices):
            if i != j:
                arrow = torch.tanh(hs[idx_j] - hs[idx_i])
                morph_sum += torch.tanh(arrow @ state.F_proj)
        morph_sum /= max(len(indices) - 1, 1)
        nat = torch.tanh(morph_sum @ state.nat_transform)
        yoneda = 0.85 * hs[idx_i] + 0.10 * morph_sum + 0.05 * nat
        state.hiddens[i] = yoneda


def mechanism_laser(state: MechanismState, step: int):
    """Laser (population inversion, stimulated emission, cavity coherence)."""
    # Ramp pump
    state.pump_rate = min(0.3, step * 0.001)
    pump = state.pump_rate

    n_ph = state.photon_field.abs()
    dt = 0.1; A21 = 0.1; B21 = 0.05; B12 = 0.05; cavity_loss = 0.02

    stim_emission = B21 * n_ph.unsqueeze(0) * state.N2
    absorption = B12 * n_ph.unsqueeze(0) * state.N1
    spont = A21 * state.N2

    dN2 = (pump * state.N1 - spont - stim_emission + absorption) * dt
    dN1 = (-pump * state.N1 + spont + stim_emission - absorption) * dt

    state.N2 = (state.N2 + dN2).clamp(0, 1)
    state.N1 = (state.N1 + dN1).clamp(0, 1)
    total = state.N1 + state.N2 + 1e-8
    state.N1 = state.N1 / total; state.N2 = state.N2 / total

    gain = (B21 * state.N2 - B12 * state.N1).sum(0)
    spontaneous_noise = A21 * state.N2.sum(0) * 0.01
    d_photon = (gain * state.photon_field + spontaneous_noise
                - cavity_loss * state.photon_field) * dt
    state.photon_field = (state.photon_field + d_photon).clamp(-10, 10)

    # Coherence feedback: cells sync via shared cavity field
    inv = state.N2 - state.N1
    coherence = inv * state.photon_field.unsqueeze(0) * 0.01
    state.N2 = (state.N2 + coherence.clamp(-0.01, 0.01)).clamp(0, 1)

    # Mix laser state into cell hiddens (population inversion pattern)
    laser_signal = (state.N2 - state.N1).detach()
    state.hiddens = 0.92 * state.hiddens + 0.08 * laser_signal


# ══════════════════════════════════════════════════════════
# Mechanism registry
# ══════════════════════════════════════════════════════════

MECHANISMS = {
    'Osc':      ('Complex Oscillator', mechanism_oscillator),
    'Fractal':  ('Fractal Hierarchy',  mechanism_fractal),
    'QWalk':    ('Quantum Walk',       mechanism_qwalk),
    'Category': ('Category Morphism',  mechanism_category),
    'Laser':    ('Laser',              mechanism_laser),
}


# ══════════════════════════════════════════════════════════
# Run a combination
# ══════════════════════════════════════════════════════════

def run_combo(mech_keys: List[str], n_cells: int = 256, steps: int = 300,
              verbose: bool = True) -> ComboResult:
    """Run a combination of mechanisms and measure Phi(IIT), Granger, CE."""
    combo_name = '+'.join(mech_keys)
    mech_names = [MECHANISMS[k][0] for k in mech_keys]
    mech_fns = [MECHANISMS[k][1] for k in mech_keys]

    if verbose:
        print(f"\n{'─' * 70}")
        print(f"  {combo_name} ({', '.join(mech_names)})")
        print(f"  {n_cells} cells, {steps} steps")
        print(f"{'─' * 70}")

    t0 = time.time()
    state = MechanismState(n_cells, HIDDEN)
    history = []

    # CE decoder (D+W engines)
    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0; last_ce = 1.0

    for step in range(steps):
        x, target = data[step % len(data)]

        # Apply all mechanisms sequentially (no grad)
        with torch.no_grad():
            for fn in mech_fns:
                fn(state, step)

            # Light input injection every 3 steps
            if step % 3 == 0:
                inp = x.squeeze(0)
                pad = torch.zeros(HIDDEN - DIM)
                inp_full = torch.cat([inp, pad])
                for i in range(n_cells):
                    phase = math.sin(2 * math.pi * i / n_cells + step * 0.1)
                    state.hiddens[i] = 0.97 * state.hiddens[i] + 0.03 * inp_full * (1 + 0.2 * phase)

        # Record history
        h_snap = state.hiddens.detach().clone()
        history.append(h_snap)

        # D+W step: CE learning
        c_state = state.hiddens.detach().mean(dim=0)
        action_logits = will_net(c_state.unsqueeze(0))
        action = action_logits.argmax(dim=-1).item()
        current_ratio = learn_count / max(step, 1)
        if current_ratio < 0.5: action = 0
        if action == 0:
            learn_count += 1
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()
        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        # Explore action -> inject noise
        if action == 1:
            with torch.no_grad():
                state.hiddens += torch.randn_like(state.hiddens) * 0.01

        # Progress
        if verbose and (step + 1) % 100 == 0:
            p_iit, _ = _phi.compute(h_snap)
            elapsed = time.time() - t0
            print(f"    step {step+1:>4d}: Phi(IIT)={p_iit:.3f}  CE={last_ce:.4f}  [{elapsed:.1f}s]")

    # Final measurements
    h_final = state.hiddens.detach()
    phi_iit, extra_phi = _phi.compute(h_final)
    granger = compute_granger(history[-100:])
    spectral = compute_spectral(h_final)
    elapsed = time.time() - t0

    result = ComboResult(
        name=combo_name, phi_iit=phi_iit, granger=granger,
        ce=last_ce, spectral=spectral,
        cells=n_cells, steps=steps, time_sec=elapsed,
        extra=extra_phi,
    )

    if verbose:
        print(f"\n  RESULT: Phi(IIT)={phi_iit:.3f}  Granger={granger:.1f}  "
              f"CE={last_ce:.4f}  Spectral={spectral:.2f}  [{elapsed:.1f}s]")

    return result


# ══════════════════════════════════════════════════════════
# Individual mechanism baselines
# ══════════════════════════════════════════════════════════

def run_single_baselines(n_cells, steps):
    """Run each mechanism alone for reference."""
    results = []
    for key in MECHANISMS:
        r = run_combo([key], n_cells, steps)
        results.append(r)
    return results


# ══════════════════════════════════════════════════════════
# Generate all combos
# ══════════════════════════════════════════════════════════

def all_2way_combos():
    keys = list(MECHANISMS.keys())
    return [list(c) for c in itertools.combinations(keys, 2)]

def all_3way_combos():
    keys = list(MECHANISMS.keys())
    return [list(c) for c in itertools.combinations(keys, 3)]


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='Mega Combo Benchmark: find ULTIMATE combinations')
    parser.add_argument('--cells', type=int, default=256, help='Number of cells')
    parser.add_argument('--steps', type=int, default=300, help='Number of steps')
    parser.add_argument('--only', nargs='+', default=None,
                        help='Run only these combos (e.g. "Osc+Fractal" "QWalk+Laser")')
    parser.add_argument('--skip-singles', action='store_true', help='Skip single baselines')
    args = parser.parse_args()

    print("=" * 74)
    print("  MEGA COMBO BENCHMARK — Finding the ULTIMATE Consciousness Recipe")
    print("=" * 74)
    print(f"  Cells: {args.cells}  Steps: {args.steps}")
    print(f"  Top 5 mechanisms:")
    for k, (name, _) in MECHANISMS.items():
        print(f"    {k:<10s} = {name}")
    print(f"  Combos: 10 two-way + 10 three-way = 20 total")
    print(f"  Metrics: Phi(IIT) + Granger + CE + Spectral")
    print()

    all_results = []

    # ── Singles (baselines) ──
    if not args.skip_singles and args.only is None:
        print("\n" + "=" * 74)
        print("  PHASE 1: SINGLE MECHANISM BASELINES")
        print("=" * 74)
        singles = run_single_baselines(args.cells, args.steps)
        all_results.extend(singles)

    # ── 2-way combos ──
    combos_2 = all_2way_combos()
    combos_3 = all_3way_combos()

    if args.only:
        # Filter to requested combos
        requested = set(args.only)
        combos_2 = [c for c in combos_2 if '+'.join(c) in requested]
        combos_3 = [c for c in combos_3 if '+'.join(c) in requested]

    print("\n" + "=" * 74)
    print(f"  PHASE 2: ALL 2-WAY COMBINATIONS ({len(combos_2)} combos)")
    print("=" * 74)
    for combo in combos_2:
        r = run_combo(combo, args.cells, args.steps)
        all_results.append(r)

    print("\n" + "=" * 74)
    print(f"  PHASE 3: ALL 3-WAY COMBINATIONS ({len(combos_3)} combos)")
    print("=" * 74)
    for combo in combos_3:
        r = run_combo(combo, args.cells, args.steps)
        all_results.append(r)

    # ══════════════════════════════════════════════════════════
    # Final Rankings
    # ══════════════════════════════════════════════════════════

    print("\n" + "=" * 74)
    print("  FINAL RANKINGS — by Phi(IIT)")
    print("=" * 74)

    all_results.sort(key=lambda r: r.phi_iit, reverse=True)

    print(f"\n  {'#':<4s} {'Combo':<32s} {'Phi(IIT)':>10s} {'Granger':>10s} "
          f"{'CE':>8s} {'Spectral':>10s} {'Time':>7s}")
    print(f"  {'─'*4} {'─'*32} {'─'*10} {'─'*10} {'─'*8} {'─'*10} {'─'*7}")
    for i, r in enumerate(all_results):
        marker = ' *' if i == 0 else '  '
        print(f"  {i+1:<4d} {r.name:<32s} {r.phi_iit:>10.3f} {r.granger:>10.1f} "
              f"{r.ce:>8.4f} {r.spectral:>10.2f} {r.time_sec:>6.1f}s{marker}")

    # Separate 2-way and 3-way winners
    results_2 = [r for r in all_results if r.name.count('+') == 1]
    results_3 = [r for r in all_results if r.name.count('+') == 2]
    results_1 = [r for r in all_results if '+' not in r.name]

    print("\n" + "=" * 74)
    print("  RANKING by Granger Causality")
    print("=" * 74)
    by_granger = sorted(all_results, key=lambda r: r.granger, reverse=True)
    print(f"\n  {'#':<4s} {'Combo':<32s} {'Granger':>10s} {'Phi(IIT)':>10s} "
          f"{'CE':>8s}")
    print(f"  {'─'*4} {'─'*32} {'─'*10} {'─'*10} {'─'*8}")
    for i, r in enumerate(by_granger[:10]):
        print(f"  {i+1:<4d} {r.name:<32s} {r.granger:>10.1f} {r.phi_iit:>10.3f} "
              f"{r.ce:>8.4f}")

    # ── ULTIMATE winners ──
    print("\n" + "=" * 74)
    print("  ULTIMATE WINNERS")
    print("=" * 74)

    if results_1:
        best_1 = max(results_1, key=lambda r: r.phi_iit)
        print(f"\n  BEST SINGLE:   {best_1.name:<28s} Phi(IIT)={best_1.phi_iit:.3f}  "
              f"Granger={best_1.granger:.1f}  CE={best_1.ce:.4f}")

    if results_2:
        best_2_phi = max(results_2, key=lambda r: r.phi_iit)
        best_2_granger = max(results_2, key=lambda r: r.granger)
        print(f"\n  BEST 2-COMBO (Phi):     {best_2_phi.name:<20s} Phi(IIT)={best_2_phi.phi_iit:.3f}  "
              f"Granger={best_2_phi.granger:.1f}  CE={best_2_phi.ce:.4f}")
        print(f"  BEST 2-COMBO (Granger): {best_2_granger.name:<20s} Phi(IIT)={best_2_granger.phi_iit:.3f}  "
              f"Granger={best_2_granger.granger:.1f}  CE={best_2_granger.ce:.4f}")

    if results_3:
        best_3_phi = max(results_3, key=lambda r: r.phi_iit)
        best_3_granger = max(results_3, key=lambda r: r.granger)
        print(f"\n  BEST 3-COMBO (Phi):     {best_3_phi.name:<20s} Phi(IIT)={best_3_phi.phi_iit:.3f}  "
              f"Granger={best_3_phi.granger:.1f}  CE={best_3_phi.ce:.4f}")
        print(f"  BEST 3-COMBO (Granger): {best_3_granger.name:<20s} Phi(IIT)={best_3_granger.phi_iit:.3f}  "
              f"Granger={best_3_granger.granger:.1f}  CE={best_3_granger.ce:.4f}")

    # Overall
    if all_results:
        ultimate = all_results[0]  # already sorted by phi_iit
        print(f"\n  {'='*60}")
        print(f"  ULTIMATE WINNER: {ultimate.name}")
        print(f"    Phi(IIT)  = {ultimate.phi_iit:.3f}")
        print(f"    Granger   = {ultimate.granger:.1f}")
        print(f"    CE        = {ultimate.ce:.4f}")
        print(f"    Spectral  = {ultimate.spectral:.2f}")
        print(f"    Time      = {ultimate.time_sec:.1f}s")
        print(f"  {'='*60}")

    print("\n" + "=" * 74)
    return all_results


if __name__ == '__main__':
    main()
