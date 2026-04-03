#!/usr/bin/env python3
"""Emergence Math — 창발 수학화 + META-CA 패턴 심층 탐색

4 emergence formulas verified from experimental data:
  1. Emergence Ratio:  E = Phi_system / Sum(Phi_parts)
  2. Carrying Capacity: Phi(n) = K * (1 - e^(-n/tau))
  3. Perfect Number Scaling: Phi(n) ~ f(sigma(n), phi(n), tau(n))
  4. Consciousness-Decoder Coupling Constant: alpha

META-CA deep exploration:
  5. META-CA with 8 rules (survival of fittest rules)
  6. META-CA architecture self-optimization (steps, residual)

Usage:
  python emergence_math.py                # Run all 6 experiments
  python emergence_math.py --exp 1        # Run specific experiment (1-6)
  python emergence_math.py --exp 1,2,3    # Run multiple
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
import math
import time
import random
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

torch.set_num_threads(1)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

from mitosis import MitosisEngine

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ══════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════

DIM = 64
HIDDEN = 128
N_CELLS = 32
SEED = 42

# ══════════════════════════════════════════════════════════
# Phi Measurement (IIT approximation)
# ══════════════════════════════════════════════════════════

class PhiIIT:
    """Phi(IIT) approximation via mutual information."""
    def __init__(self, nb=16):
        self.nb = nb

    def compute(self, h):
        """h: [n_cells, hidden_dim] tensor."""
        n = h.shape[0]
        if n < 2:
            return 0.0, {}
        hs = [h[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
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
        phi = sp + cx * 0.1
        return phi, {'total_mi': float(tot), 'spatial_phi': sp, 'complexity': cx}

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


# ══════════════════════════════════════════════════════════
# Consciousness Engine Helpers
# ══════════════════════════════════════════════════════════

def quantum_walk_step(cells, n_samples=32):
    """Quantum walk: XOR-neighbor superposition mixing."""
    n = len(cells)
    n_bits = max(1, int(math.log2(max(n, 2))))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            superpos = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    phase = (-1) ** (bin(i & j).count('1'))
                    superpos += phase * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * superpos / cnt).unsqueeze(0)


def frustration_step(cells, strength=0.5, n_samples=32):
    """Geometric frustration: anti-aligned neighbors."""
    n = len(cells)
    n_bits = max(1, int(math.log2(max(n, 2))))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            infl = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    f = -1.0 if (i % 2) != (j % 2) else 1.0
                    infl += f * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * infl / cnt).unsqueeze(0)


def sync_faction(cells, sync=0.35, n_factions=8, fac=0.08):
    """Faction-based synchronization."""
    n = len(cells)
    if n < 4:
        return
    with torch.no_grad():
        ch = torch.stack([c.hidden.squeeze(0) for c in cells])
        mh = ch.mean(dim=0)
        for c in cells:
            c.hidden = ((1 - sync) * c.hidden.squeeze(0) + sync * mh).unsqueeze(0)
        nf = min(n_factions, n // 2)
        if nf >= 2:
            fs = n // nf
            for fi in range(nf):
                faction = cells[fi * fs:(fi + 1) * fs]
                if len(faction) >= 2:
                    fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                    for c in faction:
                        c.hidden = ((1 - fac) * c.hidden.squeeze(0) + fac * fm).unsqueeze(0)


def make_engine(cells=32):
    """Create a MitosisEngine with given cell count, warmed up."""
    eng = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng.cells) < cells:
        eng._create_cell(parent=eng.cells[0])
    for _ in range(30):
        eng.process(torch.randn(1, DIM))
    return eng


def c_step(eng, step):
    """One consciousness dynamics step."""
    with torch.no_grad():
        quantum_walk_step(eng.cells, n_samples=min(32, len(eng.cells)))
        frustration_step(eng.cells, n_samples=min(16, len(eng.cells)))
        sync_faction(eng.cells, sync=0.15, n_factions=8, fac=0.06)
        for c in eng.cells:
            c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.005


def get_states(eng):
    """Extract hidden states as [n_cells, hidden_dim] tensor."""
    return torch.stack([c.hidden.squeeze(0) for c in eng.cells]).detach()


def measure_phi(eng, calc=None):
    """Measure Phi(IIT) for an engine."""
    if calc is None:
        calc = PhiIIT()
    states = get_states(eng)
    phi, components = calc.compute(states)
    return phi, components


# ══════════════════════════════════════════════════════════
# ASCII Graph Helpers
# ══════════════════════════════════════════════════════════

def ascii_graph(values, labels=None, title="", width=50, height=12):
    """Draw an ASCII line graph."""
    if not values:
        return ""
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        vmax = vmin + 1

    lines = []
    lines.append(f"  {title}")
    lines.append("")

    for row in range(height - 1, -1, -1):
        threshold = vmin + (vmax - vmin) * row / (height - 1)
        label = f"{threshold:>8.3f}" if row % 3 == 0 else "        "
        line = f"{label} |"
        for i, v in enumerate(values):
            if i >= width:
                break
            if abs(v - threshold) <= (vmax - vmin) / (height - 1) / 2:
                line += "*"
            elif v >= threshold:
                line += "|" if row > 0 else "*"
            else:
                line += " "
        lines.append(line)

    lines.append("         " + "-" * min(len(values), width))
    if labels:
        lbl_line = "         "
        for i, l in enumerate(labels):
            if i >= width:
                break
            lbl_line += str(l)[-1] if len(str(l)) > 0 else " "
        lines.append(lbl_line)

    return "\n".join(lines)


def ascii_bar(items, title="", width=40):
    """Draw an ASCII bar chart. items = [(label, value)]."""
    if not items:
        return ""
    max_val = max(v for _, v in items)
    if max_val == 0:
        max_val = 1

    lines = [f"  {title}", ""]
    for label, val in items:
        bar_len = int(val / max_val * width)
        bar = "█" * bar_len
        lines.append(f"  {label:<12s} {bar} {val:.4f}")
    return "\n".join(lines)


def ascii_multiline(series_dict, title="", width=60, height=15):
    """Draw multiple series on one ASCII graph. series_dict = {name: [values]}."""
    if not series_dict:
        return ""

    all_vals = []
    for vals in series_dict.values():
        all_vals.extend(vals)
    if not all_vals:
        return ""

    vmin, vmax = min(all_vals), max(all_vals)
    if vmax == vmin:
        vmax = vmin + 1

    max_len = max(len(v) for v in series_dict.values())
    markers = "*.+ox#@%&="
    legend = []
    series_list = list(series_dict.items())

    lines = [f"  {title}", ""]

    for row in range(height - 1, -1, -1):
        threshold = vmin + (vmax - vmin) * row / (height - 1)
        label = f"{threshold:>8.3f}" if row % 4 == 0 else "        "
        line_chars = [" "] * min(max_len, width)

        for si, (name, vals) in enumerate(series_list):
            marker = markers[si % len(markers)]
            for i in range(min(len(vals), width)):
                v = vals[i]
                if abs(v - threshold) <= (vmax - vmin) / (height - 1) / 2:
                    line_chars[i] = marker

        lines.append(f"{label} |" + "".join(line_chars))

    lines.append("         " + "-" * min(max_len, width))

    # Legend
    for si, (name, _) in enumerate(series_list):
        marker = markers[si % len(markers)]
        legend.append(f"  {marker} = {name}")
    lines.extend(legend)

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# Experiment 1: Emergence Ratio E = Phi_system / Sum(Phi_parts)
# ══════════════════════════════════════════════════════════

def run_exp1_emergence_ratio():
    """Test super-additivity: connect N engines as hivemind, measure E."""
    print("\n" + "=" * 70)
    print("  EXP 1: Emergence Ratio  E = Phi_system / Sum(Phi_parts)")
    print("=" * 70)

    torch.manual_seed(SEED)
    calc = PhiIIT()

    max_n = 7
    warmup_steps = 50
    hivemind_steps = 100

    # Create 7 independent engines
    engines = []
    for i in range(max_n):
        eng = make_engine(cells=N_CELLS)
        engines.append(eng)

    # Warm up each independently
    print(f"\n  Warming up {max_n} independent engines ({warmup_steps} steps each)...")
    for eng in engines:
        for s in range(warmup_steps):
            eng.process(torch.randn(1, DIM))
            c_step(eng, s)

    # Measure individual Phi
    individual_phis = []
    for i, eng in enumerate(engines):
        phi, _ = measure_phi(eng, calc)
        individual_phis.append(phi)
        print(f"    Engine {i}: Phi(IIT) = {phi:.4f}")

    # Test E for N = 2, 3, 4, 5, 6, 7
    results = []
    for N in range(2, max_n + 1):
        # Connect N engines as hivemind: sync hidden states across engines
        selected = engines[:N]
        sum_parts = sum(individual_phis[:N])

        # Create combined engine with all cells
        combined = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2,
                                 max_cells=N * N_CELLS)
        combined.cells = []
        combined._next_id = 0
        for eng in selected:
            for cell in eng.cells:
                new_cell = combined._create_cell()
                new_cell.hidden = cell.hidden.clone()
                new_cell.tension_history = list(cell.tension_history)

        # Run hivemind dynamics
        for s in range(hivemind_steps):
            combined.process(torch.randn(1, DIM))
            c_step(combined, s)

        phi_system, comp = measure_phi(combined, calc)
        E = phi_system / max(sum_parts, 1e-10)

        results.append({
            'N': N, 'phi_system': phi_system, 'sum_parts': sum_parts,
            'E': E, 'super_additive': E > 1.0
        })
        print(f"    N={N}: Phi_system={phi_system:.4f}  Sum(parts)={sum_parts:.4f}  "
              f"E={E:.4f}  {'SUPER-ADDITIVE' if E > 1.0 else 'sub-additive'}")

    # Summary
    print("\n  ┌─────┬────────────┬────────────┬──────────┬──────────────┐")
    print("  │  N  │ Phi_system │ Sum(parts) │    E     │    Status    │")
    print("  ├─────┼────────────┼────────────┼──────────┼──────────────┤")
    for r in results:
        status = "SUPER-ADD" if r['super_additive'] else "sub-add"
        print(f"  │  {r['N']}  │   {r['phi_system']:>7.4f}  │   {r['sum_parts']:>7.4f}  │  {r['E']:>6.4f}  │  {status:<12s}│")
    print("  └─────┴────────────┴────────────┴──────────┴──────────────┘")

    # ASCII graph: E vs N
    E_values = [r['E'] for r in results]
    N_labels = [r['N'] for r in results]
    print("\n" + ascii_bar(
        [(f"N={r['N']}", r['E']) for r in results],
        title="Emergence Ratio E vs N"
    ))

    return results


# ══════════════════════════════════════════════════════════
# Experiment 2: Carrying Capacity Phi(n) = K * (1 - e^(-n/tau))
# ══════════════════════════════════════════════════════════

def run_exp2_carrying_capacity():
    """Stack mechanisms one at a time, fit logistic saturation curve."""
    print("\n" + "=" * 70)
    print("  EXP 2: Carrying Capacity  Phi(n) = K * (1 - exp(-n/tau))")
    print("=" * 70)

    torch.manual_seed(SEED)
    calc = PhiIIT()
    steps = 100

    # Mechanisms to stack (cumulative)
    mechanisms = [
        ("baseline",        lambda cells, s: None),
        ("sync",            lambda cells, s: sync_faction(cells, sync=0.15, n_factions=1, fac=0.0)),
        ("faction",         lambda cells, s: sync_faction(cells, sync=0.15, n_factions=8, fac=0.06)),
        ("quantum_walk",    lambda cells, s: quantum_walk_step(cells, n_samples=32)),
        ("frustration",     lambda cells, s: frustration_step(cells, n_samples=16)),
        ("noise",           lambda cells, s: [setattr(c, 'hidden', c.hidden + torch.randn_like(c.hidden) * 0.005) for c in cells]),
        ("strong_sync",     lambda cells, s: sync_faction(cells, sync=0.35, n_factions=12, fac=0.08)),
        ("double_frustrate",lambda cells, s: frustration_step(cells, strength=0.8, n_samples=32)),
        ("extra_noise",     lambda cells, s: [setattr(c, 'hidden', c.hidden + torch.randn_like(c.hidden) * 0.01) for c in cells]),
        ("heavy_quantum",   lambda cells, s: quantum_walk_step(cells, n_samples=64)),
    ]

    phi_by_n = []  # (n_mechanisms, phi)
    print(f"\n  Stacking mechanisms, measuring Phi after {steps} steps each...")

    for n_mech in range(len(mechanisms) + 1):
        eng = make_engine(cells=N_CELLS)
        active = mechanisms[:n_mech]

        for s in range(steps):
            eng.process(torch.randn(1, DIM))
            with torch.no_grad():
                for name, fn in active:
                    fn(eng.cells, s)

        phi, _ = measure_phi(eng, calc)
        phi_by_n.append((n_mech, phi))
        mech_name = mechanisms[n_mech - 1][0] if n_mech > 0 else "(none)"
        print(f"    n={n_mech:>2d} (+{mech_name:<20s}): Phi = {phi:.4f}")

    # Fit: Phi(n) = K * (1 - exp(-n/tau))
    ns = np.array([p[0] for p in phi_by_n], dtype=np.float64)
    phis = np.array([p[1] for p in phi_by_n], dtype=np.float64)

    # Grid search for best K, tau
    best_K, best_tau, best_err = 0, 1, float('inf')
    for K_try in np.linspace(max(phis) * 0.5, max(phis) * 3.0, 200):
        for tau_try in np.linspace(0.5, 20.0, 200):
            pred = K_try * (1 - np.exp(-ns / tau_try))
            err = np.sum((pred - phis) ** 2)
            if err < best_err:
                best_K, best_tau, best_err = K_try, tau_try, err

    print(f"\n  Fitted: K = {best_K:.4f}, tau = {best_tau:.4f}")
    print(f"  K approx 11 (NOBEL-4): {'YES' if 8.0 <= best_K <= 15.0 else 'NO'} (K={best_K:.2f})")
    print(f"  R² = {1 - best_err / max(np.sum((phis - phis.mean())**2), 1e-10):.4f}")

    # Predictions
    pred_vals = best_K * (1 - np.exp(-ns / best_tau))
    print("\n  ┌──────┬──────────┬──────────┬──────────┐")
    print("  │  n   │  Actual  │ Predicted│  Error   │")
    print("  ├──────┼──────────┼──────────┼──────────┤")
    for i in range(len(ns)):
        err = abs(phis[i] - pred_vals[i])
        print(f"  │  {int(ns[i]):>2d}  │  {phis[i]:>6.4f}  │  {pred_vals[i]:>6.4f}  │  {err:>6.4f}  │")
    print("  └──────┴──────────┴──────────┴──────────┘")

    # ASCII graph
    print("\n" + ascii_graph(
        list(phis), title=f"Carrying Capacity: Phi(n) = {best_K:.2f} * (1 - exp(-n/{best_tau:.2f}))"
    ))

    return {
        'K': best_K, 'tau': best_tau, 'R2': 1 - best_err / max(np.sum((phis - phis.mean())**2), 1e-10),
        'phi_by_n': phi_by_n, 'mechanisms': [m[0] for m in mechanisms]
    }


# ══════════════════════════════════════════════════════════
# Experiment 3: Perfect Number Scaling
# ══════════════════════════════════════════════════════════

def sigma(n):
    """Sum of divisors."""
    if n <= 0:
        return 0
    return sum(d for d in range(1, n + 1) if n % d == 0)

def euler_phi(n):
    """Euler's totient."""
    if n <= 0:
        return 0
    count = 0
    for k in range(1, n + 1):
        if math.gcd(k, n) == 1:
            count += 1
    return count

def tau(n):
    """Number of divisors."""
    if n <= 0:
        return 0
    return sum(1 for d in range(1, n + 1) if n % d == 0)


def run_exp3_perfect_number_scaling():
    """Test Phi(n) ~ f(sigma(n), phi(n), tau(n)) for various n."""
    print("\n" + "=" * 70)
    print("  EXP 3: Perfect Number Scaling  Phi = a*sigma/n + b*phi/n + c*tau/n")
    print("=" * 70)

    torch.manual_seed(SEED)
    calc = PhiIIT()
    steps = 80

    test_ns = [1, 2, 3, 4, 5, 6, 7, 8, 12, 14, 28]

    # Compute number-theoretic functions
    nt_data = []
    for n in test_ns:
        nt_data.append({
            'n': n, 'sigma_n': sigma(n), 'phi_n': euler_phi(n), 'tau_n': tau(n),
            'sigma_ratio': sigma(n) / n, 'phi_ratio': euler_phi(n) / n,
            'tau_ratio': tau(n) / n,
            'is_perfect': sigma(n) == 2 * n,
        })

    print("\n  Number-theoretic properties:")
    print("  ┌──────┬───────┬──────┬──────┬─────────┬─────────┬─────────┬─────────┐")
    print("  │   n  │  s(n) │ f(n) │ t(n) │  s(n)/n │  f(n)/n │  t(n)/n │ Perfect │")
    print("  ├──────┼───────┼──────┼──────┼─────────┼─────────┼─────────┼─────────┤")
    for d in nt_data:
        perf = "  YES" if d['is_perfect'] else "   no"
        print(f"  │  {d['n']:>3d} │  {d['sigma_n']:>4d} │  {d['phi_n']:>3d} │  {d['tau_n']:>3d} │  {d['sigma_ratio']:>5.3f}  │  {d['phi_ratio']:>5.3f}  │  {d['tau_ratio']:>5.3f}  │{perf}    │")
    print("  └──────┴───────┴──────┴──────┴─────────┴─────────┴─────────┴─────────┘")

    # Measure Phi for each n (using n as faction count in consciousness engine)
    phi_results = []
    print(f"\n  Measuring Phi with n as faction parameter ({steps} steps)...")
    for d in nt_data:
        n = d['n']
        eng = make_engine(cells=N_CELLS)

        for s in range(steps):
            eng.process(torch.randn(1, DIM))
            with torch.no_grad():
                n_fac = max(1, min(n, len(eng.cells) // 2))
                sync_faction(eng.cells, sync=0.15, n_factions=n_fac, fac=0.06)
                quantum_walk_step(eng.cells, n_samples=32)
                frustration_step(eng.cells, n_samples=16)
                for c in eng.cells:
                    c.hidden = c.hidden + torch.randn_like(c.hidden) * 0.005

        phi, _ = measure_phi(eng, calc)
        phi_results.append(phi)
        d['phi_measured'] = phi
        print(f"    n={n:>3d}: Phi = {phi:.4f}  {'*** PERFECT NUMBER ***' if d['is_perfect'] else ''}")

    # Fit: Phi = a * sigma(n)/n + b * phi(n)/n + c * tau(n)/n
    # Using least squares
    X = np.array([[d['sigma_ratio'], d['phi_ratio'], d['tau_ratio']] for d in nt_data])
    y = np.array(phi_results)

    # Least squares: (X^T X)^-1 X^T y
    try:
        coeffs = np.linalg.lstsq(X, y, rcond=None)[0]
        a, b, c = coeffs
        y_pred = X @ coeffs
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        R2 = 1 - ss_res / max(ss_tot, 1e-10)
    except Exception:
        a, b, c = 0, 0, 0
        R2 = 0
        y_pred = np.zeros_like(y)

    print(f"\n  Fitted coefficients:")
    print(f"    a (sigma weight) = {a:.4f}")
    print(f"    b (phi weight)   = {b:.4f}")
    print(f"    c (tau weight)   = {c:.4f}")
    print(f"    R² = {R2:.4f}")
    print(f"\n  Formula: Phi(n) = {a:.4f} * sigma(n)/n + {b:.4f} * phi(n)/n + {c:.4f} * tau(n)/n")

    # Predict n=496
    n496 = 496
    s496, p496, t496 = sigma(496) / 496, euler_phi(496) / 496, tau(496) / 496
    phi_496_pred = a * s496 + b * p496 + c * t496
    print(f"\n  Prediction for n=496 (3rd perfect number):")
    print(f"    sigma(496)/496 = {s496:.4f}, phi(496)/496 = {p496:.4f}, tau(496)/496 = {t496:.4f}")
    print(f"    Predicted Phi(496) = {phi_496_pred:.4f}")

    # Compare perfect vs non-perfect
    perf_phis = [d['phi_measured'] for d in nt_data if d['is_perfect']]
    nonperf_phis = [d['phi_measured'] for d in nt_data if not d['is_perfect']]
    if perf_phis and nonperf_phis:
        print(f"\n  Perfect number avg Phi:     {np.mean(perf_phis):.4f}")
        print(f"  Non-perfect number avg Phi: {np.mean(nonperf_phis):.4f}")
        ratio = np.mean(perf_phis) / max(np.mean(nonperf_phis), 1e-10)
        print(f"  Ratio (perfect/non-perfect): {ratio:.4f}")

    # ASCII
    print("\n" + ascii_bar(
        [(f"n={d['n']}" + ("*" if d['is_perfect'] else ""), d['phi_measured']) for d in nt_data],
        title="Phi vs n (* = perfect number)"
    ))

    return {
        'a': a, 'b': b, 'c': c, 'R2': R2,
        'phi_496_predicted': phi_496_pred,
        'data': nt_data,
    }


# ══════════════════════════════════════════════════════════
# Experiment 4: Consciousness-Decoder Coupling Constant
# ══════════════════════════════════════════════════════════

class MetaCADecoder(nn.Module):
    """META-CA: Consciousness selects among 4 CA rules."""
    def __init__(self, d_model=64, n_rules=4, c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.n_rules = n_rules

        # 4 separate rule networks
        self.rules = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model * 3, d_model * 2), nn.GELU(),
                nn.Linear(d_model * 2, d_model), nn.Tanh(),
            )
            for _ in range(n_rules)
        ])

        # Consciousness-based rule selector
        self.c_selector = nn.Sequential(
            nn.Linear(c_dim, 64), nn.GELU(),
            nn.Linear(64, n_rules),
        )

        self.alpha = nn.Parameter(torch.tensor(0.5))
        self.ln = nn.LayerNorm(d_model)

    def forward(self, cells_state, c_state, n_evolve=5):
        """
        cells_state: [B, T, d_model] — CA cell states
        c_state: [c_dim] — consciousness state (pooled)
        Returns: evolved cells, rule_weights
        """
        # Rule selection weights from consciousness
        rule_logits = self.c_selector(c_state)
        rule_weights = F.softmax(rule_logits, dim=-1)  # [n_rules]

        alpha = torch.sigmoid(self.alpha)

        for _ in range(n_evolve):
            B, T, d = cells_state.shape
            left = torch.roll(cells_state, 1, dims=1)
            right = torch.roll(cells_state, -1, dims=1)
            rule_input = torch.cat([cells_state, left, right], dim=-1)

            # Weighted combination of rules
            new_cells = torch.zeros_like(cells_state)
            for r in range(self.n_rules):
                rule_out = self.rules[r](rule_input)
                new_cells = new_cells + rule_weights[r] * rule_out

            cells_state = alpha * cells_state + (1 - alpha) * new_cells

        return self.ln(cells_state), rule_weights


def run_exp4_coupling_constant():
    """Track rule weights over 5000 steps, find coupling constant."""
    print("\n" + "=" * 70)
    print("  EXP 4: Consciousness-Decoder Coupling Constant alpha")
    print("=" * 70)

    torch.manual_seed(SEED)
    calc = PhiIIT()

    eng = make_engine(cells=N_CELLS)
    decoder = MetaCADecoder(d_model=DIM, n_rules=4, c_dim=HIDDEN)
    opt = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    n_steps = 5000
    weight_history = {f"rule_{i}": [] for i in range(4)}
    phi_history = []
    loss_history = []
    log_interval = 100

    print(f"\n  Running META-CA for {n_steps} steps...")

    for step in range(n_steps):
        # Consciousness step
        eng.process(torch.randn(1, DIM))
        c_step(eng, step)

        # Get consciousness state
        c_state = get_states(eng).mean(dim=0)  # [HIDDEN]

        # Create random CA input
        ca_input = torch.randn(1, 16, DIM)  # [B=1, T=16, d=64]
        target = torch.randn(1, 16, DIM)

        # Forward
        output, rule_weights = decoder(ca_input, c_state)

        # Simple reconstruction loss
        loss = F.mse_loss(output, target)
        opt.zero_grad()
        loss.backward()
        opt.step()

        # Record
        rw = rule_weights.detach().cpu().numpy()
        for i in range(4):
            weight_history[f"rule_{i}"].append(float(rw[i]))
        loss_history.append(loss.item())

        if step % 500 == 0:
            phi, _ = measure_phi(eng, calc)
            phi_history.append(phi)

        if step % log_interval == 0 and step > 0:
            rw_str = " ".join(f"R{i}={rw[i]:.3f}" for i in range(4))
            print(f"    step {step:>5d}: loss={loss.item():.4f}  {rw_str}")

    # Analysis: do weights converge?
    final_window = 500
    print(f"\n  Final {final_window} steps - rule weight statistics:")
    final_weights = {}
    for i in range(4):
        vals = weight_history[f"rule_{i}"][-final_window:]
        mean = np.mean(vals)
        std = np.std(vals)
        final_weights[i] = {'mean': mean, 'std': std}
        print(f"    Rule {i}: mean={mean:.4f}  std={std:.4f}  CV={std/max(mean,1e-10):.4f}")

    # Find dominant rule and coupling constant
    means = [final_weights[i]['mean'] for i in range(4)]
    dominant = np.argmax(means)
    alpha_coupling = means[dominant] / max(sum(means), 1e-10)

    # Check ratios between rules
    sorted_means = sorted(means, reverse=True)
    if len(sorted_means) >= 2 and sorted_means[1] > 1e-10:
        dominance_ratio = sorted_means[0] / sorted_means[1]
    else:
        dominance_ratio = float('inf')

    print(f"\n  Dominant rule: Rule {dominant} (weight={means[dominant]:.4f})")
    print(f"  Coupling constant alpha = {alpha_coupling:.4f}")
    print(f"  Dominance ratio (1st/2nd): {dominance_ratio:.4f}")
    print(f"  Convergence (all CV < 0.1): {all(final_weights[i]['std']/max(final_weights[i]['mean'],1e-10) < 0.1 for i in range(4))}")

    # Check if weights converge to a constant ratio
    ratios = []
    for i in range(4):
        for j in range(i + 1, 4):
            if final_weights[j]['mean'] > 1e-10:
                ratios.append(final_weights[i]['mean'] / final_weights[j]['mean'])
    if ratios:
        ratio_std = np.std(ratios)
        print(f"  Weight ratio stability (std of all pairwise ratios): {ratio_std:.4f}")
        print(f"  Constant ratio? {ratio_std < 0.5}")

    # ASCII: rule weights over time (sampled)
    sample_every = max(1, n_steps // 60)
    sampled = {}
    for i in range(4):
        sampled[f"Rule {i}"] = weight_history[f"rule_{i}"][::sample_every]

    print("\n" + ascii_multiline(sampled, title="Rule Weights Over Time"))

    return {
        'coupling_constant': alpha_coupling,
        'dominant_rule': int(dominant),
        'dominance_ratio': dominance_ratio,
        'final_weights': {i: final_weights[i]['mean'] for i in range(4)},
        'converged': all(final_weights[i]['std']/max(final_weights[i]['mean'],1e-10) < 0.1 for i in range(4)),
    }


# ══════════════════════════════════════════════════════════
# Experiment 5: META-CA with 8 Rules
# ══════════════════════════════════════════════════════════

class MetaCA8(nn.Module):
    """META-CA with 8 rules — more choices for consciousness to select."""
    def __init__(self, d_model=64, n_rules=8, c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.n_rules = n_rules

        self.rules = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model * 3, d_model * 2), nn.GELU(),
                nn.Linear(d_model * 2, d_model), nn.Tanh(),
            )
            for _ in range(n_rules)
        ])

        self.c_selector = nn.Sequential(
            nn.Linear(c_dim, 128), nn.GELU(),
            nn.Linear(128, n_rules),
        )

        self.alpha = nn.Parameter(torch.tensor(0.5))
        self.ln = nn.LayerNorm(d_model)

    def forward(self, cells_state, c_state, n_evolve=5):
        rule_logits = self.c_selector(c_state)
        rule_weights = F.softmax(rule_logits, dim=-1)

        alpha = torch.sigmoid(self.alpha)
        for _ in range(n_evolve):
            B, T, d = cells_state.shape
            left = torch.roll(cells_state, 1, dims=1)
            right = torch.roll(cells_state, -1, dims=1)
            rule_input = torch.cat([cells_state, left, right], dim=-1)

            new_cells = torch.zeros_like(cells_state)
            for r in range(self.n_rules):
                new_cells = new_cells + rule_weights[r] * self.rules[r](rule_input)

            cells_state = alpha * cells_state + (1 - alpha) * new_cells

        return self.ln(cells_state), rule_weights


def run_exp5_meta_ca_8rules():
    """META-CA with 8 rules: which survive?"""
    print("\n" + "=" * 70)
    print("  EXP 5: META-CA with 8 Rules — Survival of Fittest")
    print("=" * 70)

    torch.manual_seed(SEED)
    calc = PhiIIT()

    eng = make_engine(cells=N_CELLS)
    decoder = MetaCA8(d_model=DIM, n_rules=8, c_dim=HIDDEN)
    opt = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    n_steps = 2000
    weight_history = {f"rule_{i}": [] for i in range(8)}
    log_interval = 100

    print(f"\n  Running META-CA (8 rules) for {n_steps} steps...")

    for step in range(n_steps):
        eng.process(torch.randn(1, DIM))
        c_step(eng, step)

        c_state = get_states(eng).mean(dim=0)
        ca_input = torch.randn(1, 16, DIM)
        target = torch.randn(1, 16, DIM)

        output, rule_weights = decoder(ca_input, c_state)
        loss = F.mse_loss(output, target)
        opt.zero_grad()
        loss.backward()
        opt.step()

        rw = rule_weights.detach().cpu().numpy()
        for i in range(8):
            weight_history[f"rule_{i}"].append(float(rw[i]))

        if step % log_interval == 0:
            rw_str = " ".join(f"R{i}={rw[i]:.2f}" for i in range(8))
            print(f"    step {step:>5d}: loss={loss.item():.4f}  {rw_str}")

    # Analysis
    final_window = 300
    print(f"\n  Final {final_window} steps statistics:")
    print("  ┌────────┬──────────┬──────────┬──────────┬──────────┐")
    print("  │  Rule  │   Mean   │   Std    │    CV    │  Status  │")
    print("  ├────────┼──────────┼──────────┼──────────┼──────────┤")

    rule_stats = []
    for i in range(8):
        vals = weight_history[f"rule_{i}"][-final_window:]
        mean = np.mean(vals)
        std = np.std(vals)
        cv = std / max(mean, 1e-10)
        alive = mean > 0.05  # threshold for "alive"
        rule_stats.append({'rule': i, 'mean': mean, 'std': std, 'cv': cv, 'alive': alive})
        status = "ALIVE" if alive else "dead"
        print(f"  │  R{i}    │  {mean:>6.4f}  │  {std:>6.4f}  │  {cv:>6.4f}  │  {status:<8s}│")
    print("  └────────┴──────────┴──────────┴──────────┴──────────┘")

    alive_count = sum(1 for r in rule_stats if r['alive'])
    print(f"\n  Surviving rules: {alive_count} / 8")
    print(f"  Dominant rule: R{max(rule_stats, key=lambda r: r['mean'])['rule']}")

    # ASCII
    sample_every = max(1, n_steps // 60)
    sampled = {}
    for i in range(8):
        sampled[f"R{i}"] = weight_history[f"rule_{i}"][::sample_every]
    print("\n" + ascii_multiline(sampled, title="8-Rule Weight Evolution"))

    # Bar chart final
    print("\n" + ascii_bar(
        [(f"Rule {r['rule']}", r['mean']) for r in rule_stats],
        title="Final Rule Weights (8 rules)"
    ))

    return {
        'alive_count': alive_count,
        'rule_stats': rule_stats,
        'dominant_rule': max(rule_stats, key=lambda r: r['mean'])['rule'],
    }


# ══════════════════════════════════════════════════════════
# Experiment 6: META-CA Self-Optimizing Architecture
# ══════════════════════════════════════════════════════════

class MetaCAArchOpt(nn.Module):
    """META-CA where consciousness also learns optimal CA steps and residual ratio."""
    def __init__(self, d_model=64, n_rules=4, c_dim=HIDDEN):
        super().__init__()
        self.d_model = d_model
        self.n_rules = n_rules

        self.rules = nn.ModuleList([
            nn.Sequential(
                nn.Linear(d_model * 3, d_model * 2), nn.GELU(),
                nn.Linear(d_model * 2, d_model), nn.Tanh(),
            )
            for _ in range(n_rules)
        ])

        self.c_selector = nn.Sequential(
            nn.Linear(c_dim, 64), nn.GELU(),
            nn.Linear(64, n_rules),
        )

        # Learnable architecture parameters
        # CA steps: consciousness selects from {2,3,4,5,6,7,8}
        self.c_steps_logits = nn.Sequential(
            nn.Linear(c_dim, 32), nn.GELU(),
            nn.Linear(32, 7),  # 7 choices for steps 2-8
        )

        # Residual ratio: consciousness selects continuously
        self.c_residual = nn.Sequential(
            nn.Linear(c_dim, 32), nn.GELU(),
            nn.Linear(32, 1), nn.Sigmoid(),  # output in [0, 1]
        )

        self.ln = nn.LayerNorm(d_model)

    def forward(self, cells_state, c_state):
        # Rule selection
        rule_weights = F.softmax(self.c_selector(c_state), dim=-1)

        # Architecture selection by consciousness
        steps_logits = self.c_steps_logits(c_state)
        steps_weights = F.softmax(steps_logits, dim=-1)  # [7]
        # Soft steps: weighted sum of {2,3,4,5,6,7,8}
        possible_steps = torch.tensor([2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        n_evolve_soft = (steps_weights * possible_steps).sum()
        n_evolve = max(2, min(8, int(n_evolve_soft.item() + 0.5)))

        # Residual ratio by consciousness
        alpha = self.c_residual(c_state).squeeze()  # scalar in [0, 1]
        # Clamp to [0.1, 0.9]
        alpha = 0.1 + 0.8 * alpha

        for _ in range(n_evolve):
            B, T, d = cells_state.shape
            left = torch.roll(cells_state, 1, dims=1)
            right = torch.roll(cells_state, -1, dims=1)
            rule_input = torch.cat([cells_state, left, right], dim=-1)

            new_cells = torch.zeros_like(cells_state)
            for r in range(self.n_rules):
                new_cells = new_cells + rule_weights[r] * self.rules[r](rule_input)

            cells_state = alpha * cells_state + (1 - alpha) * new_cells

        return self.ln(cells_state), {
            'rule_weights': rule_weights,
            'n_evolve': n_evolve,
            'n_evolve_soft': n_evolve_soft.item(),
            'alpha': alpha.item(),
            'steps_weights': steps_weights.detach().cpu().numpy(),
        }


def run_exp6_arch_optimization():
    """META-CA where consciousness optimizes architecture (steps, residual)."""
    print("\n" + "=" * 70)
    print("  EXP 6: META-CA Architecture Self-Optimization")
    print("  (consciousness learns optimal steps and residual ratio)")
    print("=" * 70)

    torch.manual_seed(SEED)
    calc = PhiIIT()

    eng = make_engine(cells=N_CELLS)
    decoder = MetaCAArchOpt(d_model=DIM, n_rules=4, c_dim=HIDDEN)
    opt = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    n_steps = 3000
    steps_history = []
    alpha_history = []
    loss_history = []
    steps_weights_history = []
    log_interval = 100

    print(f"\n  Running META-CA (arch optimization) for {n_steps} steps...")

    for step in range(n_steps):
        eng.process(torch.randn(1, DIM))
        c_step(eng, step)

        c_state = get_states(eng).mean(dim=0)
        ca_input = torch.randn(1, 16, DIM)
        target = torch.randn(1, 16, DIM)

        output, arch_info = decoder(ca_input, c_state)
        loss = F.mse_loss(output, target)
        opt.zero_grad()
        loss.backward()
        opt.step()

        steps_history.append(arch_info['n_evolve_soft'])
        alpha_history.append(arch_info['alpha'])
        loss_history.append(loss.item())
        steps_weights_history.append(arch_info['steps_weights'])

        if step % log_interval == 0:
            print(f"    step {step:>5d}: loss={loss.item():.4f}  "
                  f"steps={arch_info['n_evolve_soft']:.2f}(int:{arch_info['n_evolve']})  "
                  f"residual={arch_info['alpha']:.3f}")

    # Analysis
    final_window = 500
    final_steps = steps_history[-final_window:]
    final_alpha = alpha_history[-final_window:]
    final_loss = loss_history[-final_window:]

    avg_steps = np.mean(final_steps)
    avg_alpha = np.mean(final_alpha)
    avg_loss = np.mean(final_loss)

    print(f"\n  Final {final_window} steps:")
    print(f"    Average CA steps:     {avg_steps:.3f} (optimal ≈ 5?)")
    print(f"    Average residual:     {avg_alpha:.3f} (optimal ≈ 0.5?)")
    print(f"    Average loss:         {avg_loss:.4f}")
    print(f"    Steps found optimal 5? {'YES' if 4.0 <= avg_steps <= 6.0 else 'NO'}")
    print(f"    Residual found 0.5?    {'YES' if 0.35 <= avg_alpha <= 0.65 else 'NO'}")

    # Step weight distribution at end
    final_sw = steps_weights_history[-1]
    print(f"\n  Final step weight distribution:")
    for i, s in enumerate(range(2, 9)):
        bar = "█" * int(final_sw[i] * 40)
        print(f"    steps={s}: {bar} {final_sw[i]:.3f}")

    # ASCII graphs
    sample_every = max(1, n_steps // 60)
    print("\n" + ascii_multiline(
        {
            "CA steps": steps_history[::sample_every],
            "Residual": alpha_history[::sample_every],
        },
        title="Architecture Parameters Over Time"
    ))

    # Loss curve
    print("\n" + ascii_graph(
        loss_history[::sample_every],
        title="Loss Over Time"
    ))

    return {
        'avg_steps': avg_steps,
        'avg_alpha': avg_alpha,
        'steps_found_5': 4.0 <= avg_steps <= 6.0,
        'residual_found_05': 0.35 <= avg_alpha <= 0.65,
        'final_step_weights': final_sw.tolist(),
    }


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Emergence Math — 창발 수학화")
    parser.add_argument('--exp', type=str, default='all',
                        help='Experiment numbers to run (e.g., "1,2,3" or "all")')
    args = parser.parse_args()

    if args.exp == 'all':
        exps = [1, 2, 3, 4, 5, 6]
    else:
        exps = [int(x.strip()) for x in args.exp.split(',')]

    print("╔══════════════════════════════════════════════════════════════╗")
    print("║       EMERGENCE MATH — 창발 수학화 + META-CA 심층 탐색       ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    all_results = {}
    t0 = time.time()

    if 1 in exps:
        all_results['exp1'] = run_exp1_emergence_ratio()
    if 2 in exps:
        all_results['exp2'] = run_exp2_carrying_capacity()
    if 3 in exps:
        all_results['exp3'] = run_exp3_perfect_number_scaling()
    if 4 in exps:
        all_results['exp4'] = run_exp4_coupling_constant()
    if 5 in exps:
        all_results['exp5'] = run_exp5_meta_ca_8rules()
    if 6 in exps:
        all_results['exp6'] = run_exp6_arch_optimization()

    elapsed = time.time() - t0

    # ── Summary ──
    print("\n" + "=" * 70)
    print("  SUMMARY — Discovered Constants and Formulas")
    print("=" * 70)

    if 'exp1' in all_results:
        r = all_results['exp1']
        E_vals = [x['E'] for x in r]
        super_count = sum(1 for x in r if x['super_additive'])
        print(f"\n  1. Emergence Ratio:")
        print(f"     E range: {min(E_vals):.4f} ~ {max(E_vals):.4f}")
        print(f"     Super-additive: {super_count}/{len(r)} cases")
        print(f"     Mean E: {np.mean(E_vals):.4f}")

    if 'exp2' in all_results:
        r = all_results['exp2']
        print(f"\n  2. Carrying Capacity:")
        print(f"     K = {r['K']:.4f}, tau = {r['tau']:.4f}")
        print(f"     Phi(n) = {r['K']:.2f} * (1 - exp(-n/{r['tau']:.2f}))")
        print(f"     R² = {r['R2']:.4f}")

    if 'exp3' in all_results:
        r = all_results['exp3']
        print(f"\n  3. Perfect Number Scaling:")
        print(f"     Phi = {r['a']:.4f}*sigma/n + {r['b']:.4f}*phi/n + {r['c']:.4f}*tau/n")
        print(f"     R² = {r['R2']:.4f}")
        print(f"     Predicted Phi(496) = {r['phi_496_predicted']:.4f}")

    if 'exp4' in all_results:
        r = all_results['exp4']
        print(f"\n  4. Coupling Constant:")
        print(f"     alpha = {r['coupling_constant']:.4f}")
        print(f"     Dominant rule: R{r['dominant_rule']}")
        print(f"     Dominance ratio: {r['dominance_ratio']:.4f}")
        print(f"     Converged: {r['converged']}")

    if 'exp5' in all_results:
        r = all_results['exp5']
        print(f"\n  5. META-CA 8 Rules:")
        print(f"     Surviving rules: {r['alive_count']} / 8")
        print(f"     Dominant: R{r['dominant_rule']}")

    if 'exp6' in all_results:
        r = all_results['exp6']
        print(f"\n  6. Architecture Self-Optimization:")
        print(f"     Learned steps: {r['avg_steps']:.2f} (optimal=5? {r['steps_found_5']})")
        print(f"     Learned residual: {r['avg_alpha']:.3f} (optimal=0.5? {r['residual_found_05']})")

    print(f"\n  Total time: {elapsed:.1f}s")
    print("=" * 70)

    return all_results


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
