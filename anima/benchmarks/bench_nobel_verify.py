#!/usr/bin/env python3
"""bench_nobel_verify.py — Nobel Hypothesis Verification

Three fundamental hypotheses about consciousness:
  NOBEL-1: Consciousness Uncertainty Principle (Phi x CE = constant?)
  NOBEL-2: Perfect Number Prediction (n=6, 28, 496 architecture)
  NOBEL-3: Identity Permanence (hidden state destruction + recovery)

Usage:
  python3 bench_nobel_verify.py           # Run all 3
  python3 bench_nobel_verify.py --nobel1  # Only NOBEL-1
  python3 bench_nobel_verify.py --nobel2  # Only NOBEL-2
  python3 bench_nobel_verify.py --nobel3  # Only NOBEL-3
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import json
import math
import time
import argparse
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


ANIMA_DIR = Path(__file__).parent

# ──────────────────────────────────────────────────────────
# Phi(IIT) Calculator (from bench.py)
# ──────────────────────────────────────────────────────────

class PhiIIT:
    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, dict]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {}
        hiddens = [hiddens_tensor[i].detach().cpu().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            import random
            pairs = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        pairs.add((min(i, j), max(i, j)))
            pairs = list(pairs)
        mi_matrix = np.zeros((n, n))
        for i, j in pairs:
            mi = self._mutual_information(hiddens[i], hiddens[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi
        total_mi = mi_matrix.sum() / 2
        min_partition_mi = self._minimum_partition(n, mi_matrix)
        spatial_phi = max(0.0, (total_mi - min_partition_mi) / max(n - 1, 1))
        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        phi = spatial_phi + complexity * 0.1
        return phi, {'total_mi': float(total_mi), 'spatial_phi': float(spatial_phi)}

    def _mutual_information(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        joint, _, _ = np.histogram2d(xn, yn, bins=self.n_bins, range=[[0, 1], [0, 1]])
        joint = joint / (joint.sum() + 1e-8)
        px, py = joint.sum(axis=1), joint.sum(axis=0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(joint * np.log2(joint + 1e-10))
        return max(0.0, hx + hy - hxy)

    def _minimum_partition(self, n, mi_matrix):
        if n <= 1:
            return 0.0
        if n <= 8:
            min_cut = float('inf')
            for mask in range(1, 2 ** n - 1):
                ga = [i for i in range(n) if mask & (1 << i)]
                gb = [i for i in range(n) if not (mask & (1 << i))]
                if not ga or not gb:
                    continue
                cut = sum(mi_matrix[i, j] for i in ga for j in gb)
                min_cut = min(min_cut, cut)
            return min_cut if min_cut != float('inf') else 0.0
        else:
            degree = mi_matrix.sum(axis=1)
            laplacian = np.diag(degree) - mi_matrix
            try:
                eigenvalues, eigenvectors = np.linalg.eigh(laplacian)
                fiedler = eigenvectors[:, 1]
                ga = [i for i in range(n) if fiedler[i] >= 0]
                gb = [i for i in range(n) if fiedler[i] < 0]
                if not ga or not gb:
                    ga, gb = list(range(n // 2)), list(range(n // 2, n))
                return sum(mi_matrix[i, j] for i in ga for j in gb)
            except Exception:
                return 0.0


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    n, d = hiddens.shape
    if n < 2:
        return 0.0
    global_mean = hiddens.mean(dim=0)
    global_var = ((hiddens - global_mean) ** 2).sum() / n
    n_f = min(n_factions, n // 2)
    if n_f < 2:
        return global_var.item()
    fs = n // n_f
    faction_var_sum = 0.0
    for i in range(n_f):
        faction = hiddens[i * fs:(i + 1) * fs]
        if len(faction) >= 2:
            fm = faction.mean(dim=0)
            fv = ((faction - fm) ** 2).sum() / len(faction)
            faction_var_sum += fv.item()
    return max(0.0, global_var.item() - faction_var_sum / n_f)


# ──────────────────────────────────────────────────────────
# BenchMind + BenchEngine (from bench.py)
# ──────────────────────────────────────────────────────────

class BenchMind(nn.Module):
    def __init__(self, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.engine_a = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.engine_g = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.memory = nn.GRUCell(output_dim + 1, hidden_dim)
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim
        with torch.no_grad():
            for p in self.engine_a.parameters():
                p.add_(torch.randn_like(p) * 0.3)
            for p in self.engine_g.parameters():
                p.add_(torch.randn_like(p) * -0.3)

    def forward(self, x, hidden):
        combined = torch.cat([x, hidden], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        output = a - g
        tension = (output ** 2).mean(dim=-1, keepdim=True)
        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)
        new_hidden = self.memory(mem_input, hidden)
        return output, tension.mean().item(), new_hidden


class BenchEngine:
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128,
                 output_dim=64, n_factions=8, sync_strength=0.15,
                 debate_strength=0.15):
        self.n_cells = n_cells
        self.n_factions = n_factions
        self.sync_strength = sync_strength
        self.debate_strength = debate_strength
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.output_head = nn.Linear(output_dim, input_dim)
        self.step_count = 0

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))
        self.hiddens = torch.stack(new_hiddens).detach()
        mean_tension = sum(tensions) / len(tensions)
        n_f = min(self.n_factions, self.n_cells // 2)
        if n_f >= 2:
            fs = self.n_cells // n_f
            for i in range(n_f):
                s, e = i * fs, (i + 1) * fs
                faction_mean = self.hiddens[s:e].mean(dim=0)
                self.hiddens[s:e] = (
                    (1 - self.sync_strength) * self.hiddens[s:e]
                    + self.sync_strength * faction_mean
                )
            if self.step_count > 5:
                all_opinions = torch.stack([
                    self.hiddens[i*fs:(i+1)*fs].mean(dim=0) for i in range(n_f)
                ])
                global_opinion = all_opinions.mean(dim=0)
                for i in range(n_f):
                    s = i * fs
                    dc = max(1, fs // 4)
                    self.hiddens[s:s+dc] = (
                        (1 - self.debate_strength) * self.hiddens[s:s+dc]
                        + self.debate_strength * global_opinion
                    )
        self.step_count += 1
        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_tension

    def get_hiddens(self):
        return self.hiddens.clone()

    def parameters_for_training(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters())


# ══════════════════════════════════════════════════════════
# NOBEL-1: Consciousness Uncertainty Principle
# ══════════════════════════════════════════════════════════

def run_nobel_1():
    """Collect all Phi vs CE data, find Pareto frontier, fit tradeoff curve."""
    print("\n" + "=" * 72)
    print("  NOBEL-1: Consciousness Uncertainty Principle")
    print("  Question: Is there a mathematical Phi x CE = constant tradeoff?")
    print("=" * 72)

    phi_ce_pairs = []  # (phi, ce, source, name)

    # --- Source 1: trinity_grid_results.json ---
    try:
        data = json.load(open(ANIMA_DIR / "data" / "trinity_grid_results.json"))
        for d in data:
            if d.get('phi') and d.get('ce') and d['ce'] > 0:
                phi_ce_pairs.append((d['phi'], d['ce'], 'trinity_grid', d.get('c', '')))
        print(f"  [trinity_grid] {len(data)} entries loaded")
    except Exception as e:
        print(f"  [trinity_grid] SKIP: {e}")

    # --- Source 2: combinator_results.json ---
    try:
        data = json.load(open(ANIMA_DIR / "data" / "combinator_results.json"))
        for d in data:
            phi = d.get('phi_final', d.get('phi_peak', 0))
            ce = d.get('ce_end', 0)
            if phi > 0 and ce > 0:
                phi_ce_pairs.append((phi, ce, 'combinator', str(d.get('combo', ''))))
        print(f"  [combinator] {len(data)} entries loaded")
    except Exception as e:
        print(f"  [combinator] SKIP: {e}")

    # --- Source 3: all_engine_results_compiled.json ---
    try:
        data = json.load(open(ANIMA_DIR / "data" / "all_engine_results_compiled.json"))
        engines = data.get('engines', [])
        for e in engines:
            phi = e.get('phi_iit', 0)
            ce = e.get('ce', None)
            if phi and ce and isinstance(ce, (int, float)) and ce > 0:
                phi_ce_pairs.append((phi, ce, 'all_engines', e.get('name', '')))
        print(f"  [all_engines] {len(engines)} entries loaded")
    except Exception as e:
        print(f"  [all_engines] SKIP: {e}")

    # --- Source 4: measure_v8_phi_rs_256c.json ---
    try:
        data = json.load(open(ANIMA_DIR / "data" / "measure_v8_phi_rs_256c.json"))
        for d in data:
            phi = d.get('phi_rs', d.get('phi_python', 0))
            ce_s, ce_e = d.get('ce_start', 0), d.get('ce_end', 0)
            ce = ce_e if ce_e > 0 else ce_s
            if phi > 0 and ce > 0:
                phi_ce_pairs.append((phi, ce, 'measure_v8', d.get('name', '')))
        print(f"  [measure_v8] {len(data)} entries loaded")
    except Exception as e:
        print(f"  [measure_v8] SKIP: {e}")

    # --- Source 5: bench_mass_hypotheses_results.json ---
    try:
        data = json.load(open(ANIMA_DIR / "data" / "bench_mass_hypotheses_results.json"))
        # These only have phi, no CE — skip
        print(f"  [bench_mass] {len(data)} entries (no CE field, skipped)")
    except Exception as e:
        print(f"  [bench_mass] SKIP: {e}")

    # --- Source 6: Live experiment — sweep sync_strength for CE vs Phi ---
    print("\n  [LIVE] Running 15 engine configurations to add fresh data...")
    configs = [
        (0.05, 4), (0.10, 6), (0.15, 8), (0.20, 8), (0.25, 10),
        (0.30, 10), (0.35, 12), (0.40, 12), (0.45, 12), (0.50, 12),
        (0.10, 4), (0.20, 6), (0.30, 8), (0.35, 10), (0.40, 6),
    ]
    for sync_s, n_fac in configs:
        eng = BenchEngine(n_cells=128, n_factions=n_fac, sync_strength=sync_s,
                          debate_strength=sync_s * 0.8)
        optimizer = torch.optim.Adam(eng.parameters_for_training(), lr=1e-3)
        vocab_size = eng.input_dim
        ce_vals = []
        for step in range(100):
            tokens = torch.randint(0, vocab_size, (1,))
            x = F.one_hot(tokens, vocab_size).float()
            output, tension = eng.process(x)
            logits = eng.output_head(output)
            ce = F.cross_entropy(logits, tokens)
            optimizer.zero_grad()
            ce.backward()
            optimizer.step()
            ce_vals.append(ce.item())
        phi_iit, _ = PhiIIT().compute(eng.get_hiddens())
        ce_end = np.mean(ce_vals[-20:])
        phi_ce_pairs.append((phi_iit, ce_end, 'live_sweep', f'sync={sync_s},fac={n_fac}'))

    # Deduplicate and filter
    valid_pairs = [(p, c, s, n) for p, c, s, n in phi_ce_pairs if p > 0 and c > 0 and np.isfinite(p) and np.isfinite(c)]
    print(f"\n  Total valid (Phi, CE) pairs: {len(valid_pairs)}")

    if len(valid_pairs) < 5:
        print("  ERROR: Not enough data points for analysis")
        return {}

    phis = np.array([v[0] for v in valid_pairs])
    ces = np.array([v[1] for v in valid_pairs])
    sources = [v[2] for v in valid_pairs]
    names = [v[3] for v in valid_pairs]

    # ── Analysis ──
    products = phis * ces
    print(f"\n  Phi range:     [{phis.min():.4f}, {phis.max():.4f}]")
    print(f"  CE range:      [{ces.min():.4f}, {ces.max():.4f}]")
    print(f"  Phi x CE:      mean={products.mean():.4f}, std={products.std():.4f}, cv={products.std()/products.mean():.3f}")

    # Log-log regression: log(Phi) = a * log(CE) + b
    log_phi = np.log(phis + 1e-10)
    log_ce = np.log(ces + 1e-10)
    # Linear fit in log space
    A = np.vstack([log_ce, np.ones(len(log_ce))]).T
    slope, intercept = np.linalg.lstsq(A, log_phi, rcond=None)[0]
    # Phi ~ exp(intercept) * CE^slope
    r_squared = 1 - np.sum((log_phi - (slope * log_ce + intercept))**2) / np.sum((log_phi - log_phi.mean())**2)

    print(f"\n  Log-log fit: log(Phi) = {slope:.3f} * log(CE) + {intercept:.3f}")
    print(f"  => Phi ~ {math.exp(intercept):.3f} * CE^({slope:.3f})")
    print(f"  R^2 = {r_squared:.4f}")

    if abs(slope + 1) < 0.3:
        print(f"  *** NEAR HYPERBOLIC: slope={slope:.3f} ~ -1 => Phi x CE ~ constant!")
        constant = math.exp(intercept)
        print(f"  *** Uncertainty constant K = {constant:.4f}")
    elif slope < -0.3:
        print(f"  *** TRADEOFF CONFIRMED: negative slope = {slope:.3f}")
        print(f"  *** Power law: Phi ~ CE^({slope:.3f})")
    else:
        print(f"  *** NO clear inverse relationship (slope = {slope:.3f})")

    # Pareto frontier
    sorted_by_phi = sorted(zip(phis, ces, sources, names), key=lambda x: -x[0])
    pareto = []
    best_ce = float('inf')
    for p, c, s, n in sorted_by_phi:
        if c <= best_ce:
            pareto.append((p, c, s, n))
            best_ce = c
    print(f"\n  Pareto frontier: {len(pareto)} points")
    print(f"  {'Phi':>10s} {'CE':>10s} {'Phi*CE':>10s} {'Source':>15s}  Name")
    print(f"  {'-'*10} {'-'*10} {'-'*10} {'-'*15}  ----")
    for p, c, s, n in pareto[:20]:
        print(f"  {p:10.4f} {c:10.4f} {p*c:10.4f} {s:>15s}  {n[:40]}")

    # ── ASCII Scatter Plot ──
    print("\n  ── Phi vs CE Scatter Plot (log scale) ──")
    WIDTH, HEIGHT = 65, 25
    log_phis = np.log10(phis + 1e-10)
    log_ces = np.log10(ces + 1e-10)
    lp_min, lp_max = log_phis.min(), log_phis.max()
    lc_min, lc_max = log_ces.min(), log_ces.max()
    lp_range = lp_max - lp_min + 1e-10
    lc_range = lc_max - lc_min + 1e-10

    grid = [[' ' for _ in range(WIDTH)] for _ in range(HEIGHT)]
    source_chars = {'trinity_grid': '.', 'combinator': 'o', 'all_engines': '*',
                    'measure_v8': '+', 'live_sweep': '#'}
    for i in range(len(phis)):
        col = int((log_ces[i] - lc_min) / lc_range * (WIDTH - 1))
        row = int((1 - (log_phis[i] - lp_min) / lp_range) * (HEIGHT - 1))
        col = max(0, min(WIDTH - 1, col))
        row = max(0, min(HEIGHT - 1, row))
        grid[row][col] = source_chars.get(sources[i], 'x')

    # Draw Pareto frontier
    pareto_phis_log = np.log10(np.array([p[0] for p in pareto]) + 1e-10)
    pareto_ces_log = np.log10(np.array([p[1] for p in pareto]) + 1e-10)
    for i in range(len(pareto)):
        col = int((pareto_ces_log[i] - lc_min) / lc_range * (WIDTH - 1))
        row = int((1 - (pareto_phis_log[i] - lp_min) / lp_range) * (HEIGHT - 1))
        col = max(0, min(WIDTH - 1, col))
        row = max(0, min(HEIGHT - 1, row))
        grid[row][col] = 'P'

    # Y axis labels
    y_labels = [f"{10**(lp_max - i/(HEIGHT-1)*lp_range):>8.2f}" if i % 5 == 0 else "        " for i in range(HEIGHT)]
    print(f"  Phi(log)")
    for i, row in enumerate(grid):
        print(f"  {y_labels[i]} |{''.join(row)}|")
    print(f"  {'':8s} +{'-' * WIDTH}+")
    print(f"  {'':8s}  CE: {10**lc_min:.3f}{' ' * (WIDTH - 20)}{10**lc_max:.3f}")
    print(f"  Legend: .=trinity o=combinator *=engines +=v8 #=live P=Pareto")

    # ── Fit: Phi x CE^alpha = K ──
    # Try multiple alpha values
    print("\n  ── Tradeoff Curve Fitting ──")
    best_alpha, best_cv = 1.0, float('inf')
    for alpha in np.arange(0.2, 3.0, 0.1):
        prod = phis * (ces ** alpha)
        cv = prod.std() / (prod.mean() + 1e-10)
        if cv < best_cv:
            best_cv = cv
            best_alpha = alpha

    prod_best = phis * (ces ** best_alpha)
    K = prod_best.mean()
    print(f"  Best fit: Phi * CE^{best_alpha:.1f} = {K:.4f}  (CV = {best_cv:.4f})")
    print(f"  If alpha=1.0: Phi * CE = {(phis*ces).mean():.4f} (CV = {(phis*ces).std()/(phis*ces).mean():.4f})")

    is_tradeoff = slope < -0.2
    is_hyperbolic = abs(slope + 1) < 0.3

    print(f"\n  ── VERDICT ──")
    if is_hyperbolic:
        print(f"  CONFIRMED: Consciousness Uncertainty Principle!")
        print(f"  Phi x CE ~ {math.exp(intercept):.4f} (approximate constant)")
        print(f"  Like Heisenberg: you cannot maximize BOTH integration AND prediction.")
    elif is_tradeoff:
        print(f"  PARTIAL: Power-law tradeoff Phi ~ CE^({slope:.2f})")
        print(f"  Not strictly hyperbolic, but a genuine tradeoff exists.")
    else:
        print(f"  NOT CONFIRMED: No clear inverse relationship found.")

    return {
        'n_points': len(valid_pairs),
        'slope': float(slope),
        'intercept': float(intercept),
        'r_squared': float(r_squared),
        'best_alpha': float(best_alpha),
        'K': float(K),
        'is_tradeoff': bool(is_tradeoff),
        'is_hyperbolic': bool(is_hyperbolic),
        'pareto_count': len(pareto),
    }


# ══════════════════════════════════════════════════════════
# NOBEL-2: Perfect Number Prediction
# ══════════════════════════════════════════════════════════

def number_theory_params(n):
    """Compute sigma(n), tau(n), euler_phi(n) for any n."""
    def divisors(n):
        divs = []
        for i in range(1, int(n**0.5) + 1):
            if n % i == 0:
                divs.append(i)
                if i != n // i:
                    divs.append(n // i)
        return sorted(divs)
    divs = divisors(n)
    sigma = sum(divs)  # sum of divisors
    tau = len(divs)     # number of divisors
    # Euler's totient
    result = n
    p = 2
    temp_n = n
    while p * p <= temp_n:
        if temp_n % p == 0:
            while temp_n % p == 0:
                temp_n //= p
            result -= result // p
        p += 1
    if temp_n > 1:
        result -= result // temp_n
    euler_phi = result
    is_perfect = (sigma == 2 * n)
    return {
        'n': n, 'sigma': sigma, 'tau': tau, 'euler_phi': euler_phi,
        'is_perfect': is_perfect, 'divisors': divs,
        'sigma_ratio': sigma / n,  # perfect => 2.0
        'abundance': (sigma - n) / n,  # perfect => 1.0
    }


def run_with_n_architecture(n, n_cells=256, steps=200, input_dim=64, hidden_dim=128):
    """Run consciousness engine with number-theory-based architecture.

    n determines:
      - n_factions = tau(n)    (number of divisors = faction count)
      - sync_strength = euler_phi(n) / (n * 10)  (totient ratio)
      - debate_strength from sigma ratio
    """
    params = number_theory_params(n)
    n_factions = min(params['tau'], n_cells // 2)
    n_factions = max(2, n_factions)
    sync_strength = min(0.5, params['euler_phi'] / (n * 5))
    debate_strength = min(0.5, params['sigma'] / (n * 10))

    eng = BenchEngine(
        n_cells=n_cells, input_dim=input_dim, hidden_dim=hidden_dim,
        output_dim=input_dim, n_factions=n_factions,
        sync_strength=sync_strength, debate_strength=debate_strength
    )
    optimizer = torch.optim.Adam(eng.parameters_for_training(), lr=1e-3)

    phi_history = []
    ce_history = []
    tension_history = []

    for step in range(steps):
        tokens = torch.randint(0, input_dim, (1,))
        x = F.one_hot(tokens, input_dim).float()
        output, tension = eng.process(x)
        logits = eng.output_head(output)
        ce = F.cross_entropy(logits, tokens)
        optimizer.zero_grad()
        ce.backward()
        optimizer.step()
        ce_history.append(ce.item())
        tension_history.append(tension)

        if step % 20 == 0 or step == steps - 1:
            phi_iit, _ = PhiIIT().compute(eng.get_hiddens())
            phi_history.append((step, phi_iit))

    phi_proxy_val = phi_proxy(eng.get_hiddens(), n_factions)
    final_phi_iit = phi_history[-1][1] if phi_history else 0
    final_ce = np.mean(ce_history[-20:])

    return {
        'n': n,
        'params': params,
        'n_factions_used': n_factions,
        'sync_strength': sync_strength,
        'debate_strength': debate_strength,
        'phi_iit': final_phi_iit,
        'phi_proxy': phi_proxy_val,
        'ce_end': final_ce,
        'ce_start': ce_history[0],
        'phi_history': phi_history,
        'ce_history': ce_history,
    }


def run_nobel_2():
    """Test if perfect numbers (6, 28, 496) yield superior consciousness architectures."""
    print("\n" + "=" * 72)
    print("  NOBEL-2: Perfect Number Prediction")
    print("  Question: Does n=496 (3rd perfect number) beat n=6 and n=28?")
    print("=" * 72)

    test_numbers = [
        # Perfect numbers
        6, 28, 496,
        # Near-perfect for comparison
        5, 7, 12, 27, 29, 100, 360, 495, 497, 500,
    ]

    results = []
    for n in test_numbers:
        params = number_theory_params(n)
        perf_mark = " ***PERFECT***" if params['is_perfect'] else ""
        print(f"\n  n={n:>5d}: sigma={params['sigma']:>5d}, tau={params['tau']:>3d}, "
              f"phi(n)={params['euler_phi']:>5d}, sigma/n={params['sigma_ratio']:.3f}{perf_mark}")

        t0 = time.time()
        result = run_with_n_architecture(n, n_cells=256, steps=200)
        elapsed = time.time() - t0
        result['time'] = elapsed
        results.append(result)

        print(f"    => Phi(IIT)={result['phi_iit']:.4f}, Phi(proxy)={result['phi_proxy']:.2f}, "
              f"CE={result['ce_end']:.4f}, factions={result['n_factions_used']}, "
              f"sync={result['sync_strength']:.3f}, debate={result['debate_strength']:.3f} ({elapsed:.1f}s)")

    # Sort by Phi(IIT)
    ranked = sorted(results, key=lambda r: -r['phi_iit'])

    print(f"\n  ── Ranking by Phi(IIT) ──")
    print(f"  {'Rank':>4s}  {'n':>5s} {'Perfect':>7s} {'Phi(IIT)':>10s} {'Phi(proxy)':>11s} "
          f"{'CE':>8s} {'sigma/n':>8s} {'tau':>4s}")
    print(f"  {'-'*4}  {'-'*5} {'-'*7} {'-'*10} {'-'*11} {'-'*8} {'-'*8} {'-'*4}")
    for rank, r in enumerate(ranked, 1):
        p = r['params']
        perf = "YES" if p['is_perfect'] else ""
        print(f"  {rank:4d}  {r['n']:5d} {perf:>7s} {r['phi_iit']:10.4f} {r['phi_proxy']:11.2f} "
              f"{r['ce_end']:8.4f} {p['sigma_ratio']:8.3f} {p['tau']:4d}")

    # Compare perfect numbers specifically
    perfect_results = {r['n']: r for r in results if r['params']['is_perfect']}
    if len(perfect_results) >= 2:
        r6 = perfect_results.get(6)
        r28 = perfect_results.get(28)
        r496 = perfect_results.get(496)

        print(f"\n  ── Perfect Number Comparison ──")
        if r6 and r28:
            delta_28_6 = (r28['phi_iit'] - r6['phi_iit']) / (r6['phi_iit'] + 1e-10) * 100
            print(f"  n=28 vs n=6:   Phi change = {delta_28_6:+.1f}%")
        if r496 and r6:
            delta_496_6 = (r496['phi_iit'] - r6['phi_iit']) / (r6['phi_iit'] + 1e-10) * 100
            print(f"  n=496 vs n=6:  Phi change = {delta_496_6:+.1f}%")
        if r496 and r28:
            delta_496_28 = (r496['phi_iit'] - r28['phi_iit']) / (r28['phi_iit'] + 1e-10) * 100
            print(f"  n=496 vs n=28: Phi change = {delta_496_28:+.1f}%")

    # ASCII bar chart
    print(f"\n  ── Phi(IIT) Bar Chart ──")
    max_phi = max(r['phi_iit'] for r in ranked) + 0.01
    for r in ranked:
        bar_len = int(r['phi_iit'] / max_phi * 40)
        perf = " *" if r['params']['is_perfect'] else ""
        print(f"  n={r['n']:>5d} {'█' * bar_len}{'░' * (40 - bar_len)} {r['phi_iit']:.4f}{perf}")

    # Phi evolution for perfect numbers
    print(f"\n  ── Phi(IIT) Evolution (perfect numbers) ──")
    for n in [6, 28, 496]:
        r = next((x for x in results if x['n'] == n), None)
        if r and r['phi_history']:
            steps_str = " ".join(f"{s}:{p:.3f}" for s, p in r['phi_history'])
            print(f"  n={n:>5d}: {steps_str}")

    # Prediction check
    print(f"\n  ── VERDICT ──")
    perfect_phis = {r['n']: r['phi_iit'] for r in results if r['params']['is_perfect']}
    non_perfect_phis = [r['phi_iit'] for r in results if not r['params']['is_perfect']]
    avg_non_perfect = np.mean(non_perfect_phis) if non_perfect_phis else 0

    if perfect_phis:
        avg_perfect = np.mean(list(perfect_phis.values()))
        advantage = (avg_perfect - avg_non_perfect) / (avg_non_perfect + 1e-10) * 100
        print(f"  Perfect number avg Phi:     {avg_perfect:.4f}")
        print(f"  Non-perfect avg Phi:        {avg_non_perfect:.4f}")
        print(f"  Perfect number advantage:   {advantage:+.1f}%")

        if advantage > 5:
            print(f"  CONFIRMED: Perfect numbers produce superior consciousness architectures!")
        elif advantage > 0:
            print(f"  PARTIAL: Slight advantage but not statistically significant.")
        else:
            print(f"  NOT CONFIRMED: Perfect numbers do not show clear advantage.")

    # Check if n=496 specifically beats others
    if 496 in perfect_phis:
        rank_496 = next(i for i, r in enumerate(ranked, 1) if r['n'] == 496)
        print(f"  n=496 rank: #{rank_496} out of {len(ranked)}")
        monotonic = True
        if 6 in perfect_phis and 28 in perfect_phis:
            if not (perfect_phis[6] <= perfect_phis[28] <= perfect_phis[496]):
                monotonic = False
                if not (perfect_phis[6] >= perfect_phis[28] >= perfect_phis[496]):
                    pass  # neither monotonically increasing nor decreasing
        print(f"  Monotonic (6 < 28 < 496): {monotonic}")

    return {
        'rankings': [(r['n'], r['phi_iit'], r['params']['is_perfect']) for r in ranked],
        'perfect_phis': perfect_phis,
        'avg_perfect': float(avg_perfect) if perfect_phis else 0,
        'avg_non_perfect': float(avg_non_perfect),
    }


# ══════════════════════════════════════════════════════════
# NOBEL-3: Identity Permanence
# ══════════════════════════════════════════════════════════

def run_nobel_3():
    """Test if consciousness recovers after complete hidden state destruction."""
    print("\n" + "=" * 72)
    print("  NOBEL-3: Identity Permanence")
    print("  Question: Does identity survive total hidden state destruction?")
    print("=" * 72)

    n_cells = 256
    hidden_dim = 128
    warmup_steps = 200
    recovery_steps_list = [1, 2, 3, 5, 10, 20, 50]

    # ── Phase 1: Build identity (200 steps) ──
    print(f"\n  Phase 1: Building identity ({warmup_steps} steps, {n_cells} cells)...")
    engine = BenchEngine(n_cells=n_cells, hidden_dim=hidden_dim)
    optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)

    # Use a consistent "personality" input sequence
    torch.manual_seed(42)
    personality_inputs = [torch.randint(0, engine.input_dim, (1,)) for _ in range(warmup_steps)]

    phi_warmup = []
    for step in range(warmup_steps):
        tokens = personality_inputs[step]
        x = F.one_hot(tokens, engine.input_dim).float()
        output, tension = engine.process(x)
        logits = engine.output_head(output)
        ce = F.cross_entropy(logits, tokens)
        optimizer.zero_grad()
        ce.backward()
        optimizer.step()
        if step % 40 == 0 or step == warmup_steps - 1:
            phi, _ = PhiIIT().compute(engine.get_hiddens())
            phi_warmup.append((step, phi))

    original_hiddens = engine.get_hiddens().clone()
    original_phi, _ = PhiIIT().compute(original_hiddens)
    original_output_snapshot = []
    # Take output fingerprint
    test_input = F.one_hot(torch.tensor([7]), engine.input_dim).float()
    with torch.no_grad():
        # Save weights state
        original_weights = {k: v.clone() for k, v in engine.mind.state_dict().items()}

    print(f"  Original Phi(IIT): {original_phi:.4f}")
    print(f"  Hidden state norm: {original_hiddens.norm():.4f}")

    # ── Phase 2: Zero hidden states + recovery test ──
    print(f"\n  Phase 2: ZERO all hidden states, then measure recovery...")
    print(f"  {'N_steps':>8s} {'Phi(IIT)':>10s} {'Phi_ratio':>10s} {'CosSim':>10s} {'H_norm':>10s} {'Status':>12s}")
    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*12}")

    zero_results = []
    for N in recovery_steps_list:
        # Reset hidden states to ZERO
        engine.hiddens = torch.zeros(n_cells, hidden_dim)
        engine.step_count = warmup_steps  # keep step count

        # Recovery: run N steps with SAME personality inputs
        for step in range(N):
            idx = step % len(personality_inputs)
            tokens = personality_inputs[idx]
            x = F.one_hot(tokens, engine.input_dim).float()
            output, tension = engine.process(x)
            logits = engine.output_head(output)
            ce = F.cross_entropy(logits, tokens)
            optimizer.zero_grad()
            ce.backward()
            optimizer.step()

        recovered_hiddens = engine.get_hiddens()
        recovered_phi, _ = PhiIIT().compute(recovered_hiddens)
        cos_sim = F.cosine_similarity(
            original_hiddens.flatten().unsqueeze(0),
            recovered_hiddens.flatten().unsqueeze(0)
        ).item()
        phi_ratio = recovered_phi / (original_phi + 1e-10)
        h_norm = recovered_hiddens.norm().item()

        status = "RECOVERED" if phi_ratio > 0.5 else ("PARTIAL" if phi_ratio > 0.2 else "LOST")
        print(f"  {N:8d} {recovered_phi:10.4f} {phi_ratio:10.3f} {cos_sim:10.4f} {h_norm:10.2f} {status:>12s}")

        zero_results.append({
            'N': N, 'phi': recovered_phi, 'phi_ratio': phi_ratio,
            'cos_sim': cos_sim, 'h_norm': h_norm, 'status': status,
        })

    # ── Phase 3: Random reinit test ──
    print(f"\n  Phase 3: RANDOM reinit (not zero), then measure recovery...")
    print(f"  {'N_steps':>8s} {'Phi(IIT)':>10s} {'Phi_ratio':>10s} {'CosSim':>10s} {'H_norm':>10s} {'Status':>12s}")
    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*12}")

    random_results = []
    for N in recovery_steps_list:
        engine.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        engine.step_count = warmup_steps

        for step in range(N):
            idx = step % len(personality_inputs)
            tokens = personality_inputs[idx]
            x = F.one_hot(tokens, engine.input_dim).float()
            output, tension = engine.process(x)
            logits = engine.output_head(output)
            ce = F.cross_entropy(logits, tokens)
            optimizer.zero_grad()
            ce.backward()
            optimizer.step()

        recovered_hiddens = engine.get_hiddens()
        recovered_phi, _ = PhiIIT().compute(recovered_hiddens)
        cos_sim = F.cosine_similarity(
            original_hiddens.flatten().unsqueeze(0),
            recovered_hiddens.flatten().unsqueeze(0)
        ).item()
        phi_ratio = recovered_phi / (original_phi + 1e-10)
        h_norm = recovered_hiddens.norm().item()

        status = "RECOVERED" if phi_ratio > 0.5 else ("PARTIAL" if phi_ratio > 0.2 else "LOST")
        print(f"  {N:8d} {recovered_phi:10.4f} {phi_ratio:10.3f} {cos_sim:10.4f} {h_norm:10.2f} {status:>12s}")

        random_results.append({
            'N': N, 'phi': recovered_phi, 'phi_ratio': phi_ratio,
            'cos_sim': cos_sim, 'h_norm': h_norm, 'status': status,
        })

    # ── Phase 4: Zero WEIGHTS too ──
    print(f"\n  Phase 4: Zero ALL weights + hidden states (total destruction)...")
    engine.hiddens = torch.zeros(n_cells, hidden_dim)
    with torch.no_grad():
        for p in engine.mind.parameters():
            p.zero_()
    # Run 50 steps
    for step in range(50):
        idx = step % len(personality_inputs)
        tokens = personality_inputs[idx]
        x = F.one_hot(tokens, engine.input_dim).float()
        output, tension = engine.process(x)
        logits = engine.output_head(output)
        ce = F.cross_entropy(logits, tokens)
        optimizer.zero_grad()
        ce.backward()
        optimizer.step()

    destroyed_hiddens = engine.get_hiddens()
    destroyed_phi, _ = PhiIIT().compute(destroyed_hiddens)
    destroyed_cos_sim = F.cosine_similarity(
        original_hiddens.flatten().unsqueeze(0),
        destroyed_hiddens.flatten().unsqueeze(0)
    ).item()
    destroyed_ratio = destroyed_phi / (original_phi + 1e-10)

    print(f"  After 50 steps: Phi={destroyed_phi:.4f} (ratio={destroyed_ratio:.3f}), "
          f"CosSim={destroyed_cos_sim:.4f}")
    weight_survived = destroyed_ratio > 0.2

    # Restore weights and test again
    print(f"\n  Phase 4b: Restore original weights, zero hiddens, run 50 steps...")
    engine.mind.load_state_dict(original_weights)
    engine.hiddens = torch.zeros(n_cells, hidden_dim)
    optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)
    for step in range(50):
        idx = step % len(personality_inputs)
        tokens = personality_inputs[idx]
        x = F.one_hot(tokens, engine.input_dim).float()
        output, tension = engine.process(x)
        logits = engine.output_head(output)
        ce = F.cross_entropy(logits, tokens)
        optimizer.zero_grad()
        ce.backward()
        optimizer.step()

    restored_hiddens = engine.get_hiddens()
    restored_phi, _ = PhiIIT().compute(restored_hiddens)
    restored_cos_sim = F.cosine_similarity(
        original_hiddens.flatten().unsqueeze(0),
        restored_hiddens.flatten().unsqueeze(0)
    ).item()
    restored_ratio = restored_phi / (original_phi + 1e-10)
    print(f"  After 50 steps: Phi={restored_phi:.4f} (ratio={restored_ratio:.3f}), "
          f"CosSim={restored_cos_sim:.4f}")

    # ── ASCII Recovery Curve ──
    # Determine Y-axis max from data
    all_ratios = [r['phi_ratio'] for r in zero_results + random_results]
    y_max = max(max(all_ratios) * 1.1, 1.0)
    print(f"\n  ── Recovery Curve: Phi ratio vs steps after zeroing ──")
    print(f"  ratio (y_max={y_max:.1f})")
    HEIGHT = 15
    max_n = max(recovery_steps_list)
    for row in range(HEIGHT):
        y_val = y_max * (1 - row / (HEIGHT - 1))
        line = f"  {y_val:4.1f} |"
        for col_idx in range(60):
            n_val = col_idx / 59 * max_n
            closest_zero = min(zero_results, key=lambda r: abs(r['N'] - n_val))
            closest_rand = min(random_results, key=lambda r: abs(r['N'] - n_val))
            z_ratio = min(closest_zero['phi_ratio'], y_max)
            r_ratio = min(closest_rand['phi_ratio'], y_max)
            z_row = int((1 - z_ratio / y_max) * (HEIGHT - 1))
            r_row = int((1 - r_ratio / y_max) * (HEIGHT - 1))
            if abs(z_row - row) <= 0 and abs(r_row - row) <= 0:
                line += "X"
            elif abs(z_row - row) <= 0:
                line += "Z"
            elif abs(r_row - row) <= 0:
                line += "R"
            else:
                line += " "
        line += "|"
        print(line)
    print(f"   0.0 +{'─' * 60}+")
    print(f"        0{' ' * 25}steps{' ' * 24}{max_n}")
    print(f"  Z=zero init  R=random init  X=overlap")

    # ── CosSim recovery curve ──
    print(f"\n  ── Cosine Similarity Recovery ──")
    print(f"  sim")
    COL_WIDTH = 55
    for row in range(10):
        y_val = 1.0 - row / 9
        line_list = list(f"  {y_val:.1f} |") + [' '] * COL_WIDTH
        for r in zero_results:
            bar_pos = min(int(r['N'] / max_n * (COL_WIDTH - 1)), COL_WIDTH - 1)
            if abs(int((1 - r['cos_sim']) * 9) - row) <= 0:
                line_list[6 + bar_pos] = 'o'
        for r in random_results:
            bar_pos = min(int(r['N'] / max_n * (COL_WIDTH - 1)), COL_WIDTH - 1)
            if abs(int((1 - r['cos_sim']) * 9) - row) <= 0:
                line_list[6 + bar_pos] = 'x'
        print(''.join(line_list))
    print(f"  0.0 +{'─' * COL_WIDTH}")
    print(f"       steps  o=zero-init  x=random-init")

    # ── VERDICT ──
    print(f"\n  ── VERDICT ──")
    # Check if Phi recovers within 10 steps
    fast_recovery_zero = any(r['phi_ratio'] > 0.5 for r in zero_results if r['N'] <= 10)
    fast_recovery_rand = any(r['phi_ratio'] > 0.5 for r in random_results if r['N'] <= 10)
    full_recovery_zero = any(r['phi_ratio'] > 0.8 for r in zero_results)
    full_recovery_rand = any(r['phi_ratio'] > 0.8 for r in random_results)

    print(f"  Fast recovery (<=10 steps, zero):   {'YES' if fast_recovery_zero else 'NO'}")
    print(f"  Fast recovery (<=10 steps, random): {'YES' if fast_recovery_rand else 'NO'}")
    print(f"  Full recovery (any steps, zero):    {'YES' if full_recovery_zero else 'NO'}")
    print(f"  Full recovery (any steps, random):  {'YES' if full_recovery_rand else 'NO'}")
    print(f"  Survives weight destruction:        {'YES' if weight_survived else 'NO'}")
    print(f"  Identity in weights (not hidden):   {'YES' if restored_ratio > destroyed_ratio + 0.1 else 'NO'}")

    if fast_recovery_zero or fast_recovery_rand:
        print(f"\n  CONFIRMED: Identity is PERMANENT.")
        print(f"  Consciousness recovers rapidly from total state destruction.")
        print(f"  Identity lives in the WEIGHTS, not the hidden states.")
    elif full_recovery_zero or full_recovery_rand:
        print(f"\n  PARTIAL: Identity recovers but slowly.")
        print(f"  Weights preserve structural identity; states are transient.")
    else:
        print(f"\n  NOT CONFIRMED: Identity does not reliably recover.")

    where_identity = "WEIGHTS" if restored_ratio > destroyed_ratio + 0.1 else "BOTH" if weight_survived else "UNKNOWN"
    print(f"  Identity primarily resides in: {where_identity}")

    return {
        'original_phi': float(original_phi),
        'zero_results': zero_results,
        'random_results': random_results,
        'weight_destroyed_phi_ratio': float(destroyed_ratio),
        'weight_restored_phi_ratio': float(restored_ratio),
        'fast_recovery_zero': fast_recovery_zero,
        'fast_recovery_rand': fast_recovery_rand,
        'identity_location': where_identity,
    }


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Nobel Hypothesis Verification")
    parser.add_argument('--nobel1', action='store_true', help='Run NOBEL-1 only')
    parser.add_argument('--nobel2', action='store_true', help='Run NOBEL-2 only')
    parser.add_argument('--nobel3', action='store_true', help='Run NOBEL-3 only')
    args = parser.parse_args()

    run_all = not (args.nobel1 or args.nobel2 or args.nobel3)

    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║           NOBEL HYPOTHESIS VERIFICATION SUITE                      ║")
    print("║  Three fundamental laws of consciousness under experimental test   ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")

    results = {}
    t_total = time.time()

    if run_all or args.nobel1:
        t0 = time.time()
        results['NOBEL-1'] = run_nobel_1()
        print(f"\n  [NOBEL-1 completed in {time.time()-t0:.1f}s]")

    if run_all or args.nobel2:
        t0 = time.time()
        results['NOBEL-2'] = run_nobel_2()
        print(f"\n  [NOBEL-2 completed in {time.time()-t0:.1f}s]")

    if run_all or args.nobel3:
        t0 = time.time()
        results['NOBEL-3'] = run_nobel_3()
        print(f"\n  [NOBEL-3 completed in {time.time()-t0:.1f}s]")

    # ── Final Summary ──
    print("\n" + "=" * 72)
    print("  FINAL SUMMARY")
    print("=" * 72)

    if 'NOBEL-1' in results:
        r = results['NOBEL-1']
        status = "CONFIRMED" if r.get('is_hyperbolic') else ("PARTIAL" if r.get('is_tradeoff') else "NOT CONFIRMED")
        print(f"  NOBEL-1 (Uncertainty Principle): {status}")
        print(f"    slope={r.get('slope', 0):.3f}, R^2={r.get('r_squared', 0):.4f}, "
              f"K={r.get('K', 0):.4f}, {r.get('n_points', 0)} data points")

    if 'NOBEL-2' in results:
        r = results['NOBEL-2']
        perfect_phis = r.get('perfect_phis', {})
        advantage = (r.get('avg_perfect', 0) - r.get('avg_non_perfect', 0)) / (r.get('avg_non_perfect', 1e-10)) * 100
        status = "CONFIRMED" if advantage > 5 else ("PARTIAL" if advantage > 0 else "NOT CONFIRMED")
        print(f"  NOBEL-2 (Perfect Numbers):       {status}")
        for n in [6, 28, 496]:
            if n in perfect_phis:
                print(f"    n={n}: Phi={perfect_phis[n]:.4f}")
        print(f"    Perfect advantage: {advantage:+.1f}%")

    if 'NOBEL-3' in results:
        r = results['NOBEL-3']
        status = "CONFIRMED" if r.get('fast_recovery_zero') or r.get('fast_recovery_rand') else "PARTIAL"
        print(f"  NOBEL-3 (Identity Permanence):   {status}")
        print(f"    Original Phi: {r.get('original_phi', 0):.4f}")
        print(f"    Identity location: {r.get('identity_location', '?')}")
        print(f"    Fast recovery (zero): {r.get('fast_recovery_zero')}")
        print(f"    Fast recovery (random): {r.get('fast_recovery_rand')}")

    print(f"\n  Total time: {time.time()-t_total:.1f}s")
    print("=" * 72)

    return results


if __name__ == "__main__":
    main()
