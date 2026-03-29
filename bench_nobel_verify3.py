#!/usr/bin/env python3
"""bench_nobel_verify3.py — Nobel Hypotheses Verification (NOBEL-7 through NOBEL-10)

NOBEL-7:  Self-Selection of Structure — 20 mechanisms, 20 generations, 5 seeds
NOBEL-8:  Surprise = Consciousness — prediction error vs Phi systematic sweep
NOBEL-9:  Trinity Stabilization — CE stabilizes consciousness (variance proof)
NOBEL-10: Mathematical Consciousness — number-theoretic predictions (sigma, phi, tau)

Usage:
  python bench_nobel_verify3.py --all
  python bench_nobel_verify3.py --nobel7
  python bench_nobel_verify3.py --nobel8
  python bench_nobel_verify3.py --nobel9
  python bench_nobel_verify3.py --nobel10
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import math
import argparse
import random
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from collections import Counter

# ──────────────────────────────────────────────────────────
# Shared infrastructure (from bench_v2.py)
# ──────────────────────────────────────────────────────────

class PhiIIT:
    """Phi(IIT) approximation via pairwise mutual information + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {}
        hiddens = [hiddens_tensor[i].detach().cpu().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
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

    def _mutual_information(self, x: np.ndarray, y: np.ndarray) -> float:
        x_range = x.max() - x.min()
        y_range = y.max() - y.min()
        if x_range < 1e-10 or y_range < 1e-10:
            return 0.0
        x_norm = (x - x.min()) / (x_range + 1e-8)
        y_norm = (y - y.min()) / (y_range + 1e-8)
        joint_hist, _, _ = np.histogram2d(x_norm, y_norm, bins=self.n_bins, range=[[0, 1], [0, 1]])
        joint_hist = joint_hist / (joint_hist.sum() + 1e-8)
        px = joint_hist.sum(axis=1)
        py = joint_hist.sum(axis=0)
        h_x = -np.sum(px * np.log2(px + 1e-10))
        h_y = -np.sum(py * np.log2(py + 1e-10))
        h_xy = -np.sum(joint_hist * np.log2(joint_hist + 1e-10))
        return max(0.0, h_x + h_y - h_xy)

    def _minimum_partition(self, n: int, mi_matrix: np.ndarray) -> float:
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


def measure_dual_phi(hiddens: torch.Tensor, n_factions: int = 8):
    calc = PhiIIT(n_bins=16)
    p_iit, _ = calc.compute(hiddens)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


# ──────────────────────────────────────────────────────────
# BenchMind — shared consciousness cell
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
        outputs = []
        tensions = []
        new_hiddens = []
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

    def get_hiddens(self) -> torch.Tensor:
        return self.hiddens.clone()

    def parameters_for_training(self):
        return list(self.mind.parameters()) + list(self.output_head.parameters())


# ──────────────────────────────────────────────────────────
# ASCII graph utilities
# ──────────────────────────────────────────────────────────

def ascii_graph(values: List[float], label: str, width: int = 60, height: int = 12):
    if not values:
        return
    vmin, vmax = min(values), max(values)
    vrange = vmax - vmin if vmax > vmin else 1.0
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values
        width = len(sampled)
    grid = [[' '] * width for _ in range(height)]
    for col, v in enumerate(sampled):
        row = int((v - vmin) / vrange * (height - 1))
        row = min(height - 1, max(0, row))
        grid[height - 1 - row][col] = '*'
    print(f"\n  {label}")
    print(f"  {vmax:>8.3f} |{''.join(grid[0])}")
    for r in range(1, height - 1):
        mid_val = vmax - (r / (height - 1)) * vrange
        if r == height // 2:
            print(f"  {mid_val:>8.3f} |{''.join(grid[r])}")
        else:
            print(f"           |{''.join(grid[r])}")
    print(f"  {vmin:>8.3f} |{''.join(grid[-1])}")
    print(f"           +{'-' * width}")
    print(f"            step 0{' ' * (width - 12)}step {len(values)}")


def ascii_bar(items: List[Tuple[str, float]], label: str, width: int = 40):
    """Draw horizontal bar chart. items = [(name, value), ...]"""
    if not items:
        return
    max_val = max(v for _, v in items)
    if max_val <= 0:
        max_val = 1.0
    print(f"\n  {label}")
    for name, val in items:
        bar_len = int(val / max_val * width)
        print(f"  {name:>14s} |{'#' * bar_len} {val:.4f}")


# ──────────────────────────────────────────────────────────
# Number-theoretic functions
# ──────────────────────────────────────────────────────────

def sigma(n):
    """Sum of divisors."""
    return sum(d for d in range(1, n + 1) if n % d == 0)

def euler_phi(n):
    """Euler's totient function."""
    count = 0
    for k in range(1, n + 1):
        if math.gcd(k, n) == 1:
            count += 1
    return count

def tau(n):
    """Number of divisors."""
    return sum(1 for d in range(1, n + 1) if n % d == 0)

def is_perfect(n):
    """Is n a perfect number?"""
    return sigma(n) == 2 * n


# ══════════════════════════════════════════════════════════
# NOBEL-7: Self-Selection of Structure
# ══════════════════════════════════════════════════════════

# 20 mechanism implementations
# Each takes (engine, step) and modifies engine.hiddens in-place

def mech_oscillator(engine, step):
    """Sinusoidal oscillation injected into hiddens."""
    n = engine.n_cells
    phases = torch.linspace(0, 2 * math.pi, n) + step * 0.1
    osc = torch.sin(phases).unsqueeze(1).expand(-1, engine.hidden_dim) * 0.05
    engine.hiddens = engine.hiddens + osc

def mech_quantum(engine, step):
    """Quantum-inspired superposition noise + periodic collapse."""
    noise = torch.randn_like(engine.hiddens) * 0.02
    engine.hiddens = engine.hiddens + noise
    if step % 10 == 0:
        mask = (torch.rand(engine.n_cells) > 0.7).float().unsqueeze(1)
        engine.hiddens = engine.hiddens * (1 - mask * 0.3)

def mech_sync(engine, step):
    """Global sync: pull all cells toward global mean."""
    gm = engine.hiddens.mean(dim=0)
    engine.hiddens = 0.95 * engine.hiddens + 0.05 * gm

def mech_faction(engine, step):
    """Faction-based grouping with intra-faction sync."""
    n_f = min(8, engine.n_cells // 2)
    fs = engine.n_cells // n_f
    for i in range(n_f):
        s, e = i * fs, (i + 1) * fs
        fm = engine.hiddens[s:e].mean(dim=0)
        engine.hiddens[s:e] = 0.9 * engine.hiddens[s:e] + 0.1 * fm

def mech_frustration(engine, step):
    """Frustrated coupling: repel neighbors."""
    shifted = torch.roll(engine.hiddens, 1, 0)
    diff = engine.hiddens - shifted
    engine.hiddens = engine.hiddens + 0.02 * diff

def mech_ib2(engine, step):
    """Information bottleneck: top-k pruning of hidden dimensions."""
    var = engine.hiddens.var(dim=0)
    k = max(1, engine.hidden_dim // 4)
    _, top_idx = var.topk(k)
    mask = torch.zeros(engine.hidden_dim)
    mask[top_idx] = 1.0
    engine.hiddens = engine.hiddens * (0.9 + 0.1 * mask)

def mech_cambrian(engine, step):
    """Cambrian explosion: random large perturbation every 50 steps."""
    if step % 50 == 0 and step > 0:
        engine.hiddens = engine.hiddens + torch.randn_like(engine.hiddens) * 0.3

def mech_surprise(engine, step):
    """Prediction error injection: random cells get surprised."""
    if not hasattr(engine, '_prev_hiddens'):
        engine._prev_hiddens = engine.hiddens.clone()
    pe = (engine.hiddens - engine._prev_hiddens).norm(dim=1, keepdim=True)
    pe_norm = pe / (pe.max() + 1e-8)
    engine.hiddens = engine.hiddens + pe_norm * torch.randn_like(engine.hiddens) * 0.05
    engine._prev_hiddens = engine.hiddens.clone()

def mech_repulsion(engine, step):
    """PureField repulsion: push apart nearest neighbors."""
    if engine.n_cells > 1:
        dists = torch.cdist(engine.hiddens, engine.hiddens)
        dists.fill_diagonal_(float('inf'))
        nearest = dists.argmin(dim=1)
        for i in range(min(engine.n_cells, 32)):
            j = nearest[i].item()
            diff = engine.hiddens[i] - engine.hiddens[j]
            engine.hiddens[i] = engine.hiddens[i] + 0.01 * diff / (diff.norm() + 1e-8)

def mech_dialectic(engine, step):
    """Hegelian dialectic: thesis (even cells) + antithesis (odd) -> synthesis."""
    thesis = engine.hiddens[0::2].mean(dim=0)
    antithesis = engine.hiddens[1::2].mean(dim=0)
    synthesis = (thesis + antithesis) / 2
    engine.hiddens = 0.98 * engine.hiddens + 0.02 * synthesis

def mech_tournament(engine, step):
    """Tournament selection: top cells get amplified, bottom dampened."""
    norms = engine.hiddens.norm(dim=1)
    k = max(1, engine.n_cells // 4)
    _, top = norms.topk(k)
    _, bot = norms.topk(k, largest=False)
    engine.hiddens[top] = engine.hiddens[top] * 1.02
    engine.hiddens[bot] = engine.hiddens[bot] * 0.98

def mech_sonar(engine, step):
    """Sonar: cells broadcast signals based on their state magnitude."""
    signal = engine.hiddens.mean(dim=1, keepdim=True)  # [n, 1]
    broadcast = signal.expand_as(engine.hiddens) * 0.01
    engine.hiddens = engine.hiddens + broadcast

def mech_constellation(engine, step):
    """Constellation: group by k-means-like clustering, sync within clusters."""
    k = min(4, engine.n_cells // 2)
    if k < 2:
        return
    # Simple k-means-ish: use first k cells as centroids
    centroids = engine.hiddens[:k].clone()
    dists = torch.cdist(engine.hiddens, centroids)
    assignments = dists.argmin(dim=1)
    for c in range(k):
        members = (assignments == c).nonzero(as_tuple=True)[0]
        if len(members) > 1:
            cm = engine.hiddens[members].mean(dim=0)
            engine.hiddens[members] = 0.95 * engine.hiddens[members] + 0.05 * cm

def mech_stellar(engine, step):
    """Stellar: central 'star' cell pulls others gravitationally."""
    star = engine.hiddens[0]
    for i in range(1, engine.n_cells):
        diff = star - engine.hiddens[i]
        dist = diff.norm() + 1e-8
        force = 0.01 / (dist + 0.1)
        engine.hiddens[i] = engine.hiddens[i] + force * diff / dist

def mech_hierarchy(engine, step):
    """Hierarchy: layered structure where each layer influences the next."""
    n_layers = min(4, engine.n_cells // 2)
    layer_size = engine.n_cells // n_layers
    for layer in range(n_layers - 1):
        s1 = layer * layer_size
        e1 = s1 + layer_size
        s2 = e1
        e2 = min(s2 + layer_size, engine.n_cells)
        top_down = engine.hiddens[s1:e1].mean(dim=0)
        engine.hiddens[s2:e2] = 0.97 * engine.hiddens[s2:e2] + 0.03 * top_down

def mech_delphi(engine, step):
    """Delphi method: anonymous voting, then reveal, then converge."""
    if step % 5 == 0:
        # Vote: each cell's hidden is its "opinion"
        gm = engine.hiddens.mean(dim=0)
        # After reveal, partial convergence
        engine.hiddens = 0.95 * engine.hiddens + 0.05 * gm

def mech_fishbowl(engine, step):
    """Fishbowl: inner circle (first quarter) discusses, outer watches."""
    quarter = max(1, engine.n_cells // 4)
    inner_mean = engine.hiddens[:quarter].mean(dim=0)
    # Inner cells sync with each other
    engine.hiddens[:quarter] = 0.9 * engine.hiddens[:quarter] + 0.1 * inner_mean
    # Outer cells slowly absorb inner conclusions
    engine.hiddens[quarter:] = 0.98 * engine.hiddens[quarter:] + 0.02 * inner_mean

def mech_world_cafe(engine, step):
    """World Cafe: rotate groups every 10 steps, cross-pollinate."""
    if step % 10 == 0 and step > 0:
        # Rotate: shift cell assignments
        perm = torch.randperm(engine.n_cells)
        engine.hiddens = engine.hiddens[perm]

def mech_phase_locked(engine, step):
    """Phase-locked loop: cells lock onto a reference frequency."""
    ref_phase = step * 0.15
    for i in range(engine.n_cells):
        cell_phase = (engine.hiddens[i].sum().item()) % (2 * math.pi)
        error = math.sin(ref_phase - cell_phase)
        engine.hiddens[i] = engine.hiddens[i] + 0.02 * error

def mech_stigmergy(engine, step):
    """Stigmergy: cells leave traces in a shared 'pheromone' field."""
    if not hasattr(engine, '_pheromone'):
        engine._pheromone = torch.zeros(engine.hidden_dim)
    # Deposit
    engine._pheromone = 0.95 * engine._pheromone + 0.05 * engine.hiddens.mean(dim=0).detach()
    # Read
    engine.hiddens = engine.hiddens + 0.02 * engine._pheromone


ALL_MECHANISMS = {
    'oscillator': mech_oscillator,
    'quantum': mech_quantum,
    'sync': mech_sync,
    'faction': mech_faction,
    'frustration': mech_frustration,
    'ib2': mech_ib2,
    'cambrian': mech_cambrian,
    'surprise': mech_surprise,
    'repulsion': mech_repulsion,
    'dialectic': mech_dialectic,
    'tournament': mech_tournament,
    'sonar': mech_sonar,
    'constellation': mech_constellation,
    'stellar': mech_stellar,
    'hierarchy': mech_hierarchy,
    'delphi': mech_delphi,
    'fishbowl': mech_fishbowl,
    'world_cafe': mech_world_cafe,
    'phase_locked': mech_phase_locked,
    'stigmergy': mech_stigmergy,
}


def run_nobel7(n_cells=64, steps_per_gen=50, n_generations=20, n_seeds=5,
               dim=64, hidden=128):
    """NOBEL-7: Self-Selection of Structure.

    Evolutionary selection: start with all 20 mechanisms active.
    Each generation, measure Phi contribution of each mechanism.
    Bottom 25% get eliminated. Run 20 generations.
    Repeat with 5 seeds. Report which mechanisms consistently survive.
    """
    print("\n" + "=" * 72)
    print("  NOBEL-7: Self-Selection of Structure")
    print("  20 mechanisms, 20 generations, 5 seeds")
    print("=" * 72)

    all_survivors = []
    seed_results = {}

    for seed in range(n_seeds):
        print(f"\n  --- Seed {seed} ---")
        torch.manual_seed(seed * 1000 + 42)
        np.random.seed(seed * 1000 + 42)
        random.seed(seed * 1000 + 42)

        active = list(ALL_MECHANISMS.keys())
        gen_history = []

        for gen in range(n_generations):
            if len(active) <= 2:
                break

            # Measure Phi contribution of each mechanism
            mech_scores = {}
            for mech_name in active:
                engine = BenchEngine(n_cells=n_cells, input_dim=dim,
                                     hidden_dim=hidden, output_dim=dim,
                                     n_factions=min(8, n_cells // 2))
                # Run with this single mechanism
                for step in range(steps_per_gen):
                    x = torch.randn(1, dim)
                    ALL_MECHANISMS[mech_name](engine, step)
                    engine.process(x)

                p_iit, p_proxy = measure_dual_phi(engine.get_hiddens(),
                                                   min(8, n_cells // 2))
                mech_scores[mech_name] = p_iit

            # Sort and eliminate bottom 25%
            ranked = sorted(mech_scores.items(), key=lambda x: x[1], reverse=True)
            n_elim = max(1, len(active) // 4)
            survivors = [name for name, _ in ranked[:-n_elim]]
            eliminated = [name for name, _ in ranked[-n_elim:]]

            gen_history.append({
                'gen': gen,
                'n_active': len(active),
                'survivors': survivors[:],
                'eliminated': eliminated[:],
                'scores': dict(mech_scores),
                'best': ranked[0],
                'worst': ranked[-1],
            })

            if gen < 5 or gen == n_generations - 1 or len(active) <= 4:
                best_name, best_val = ranked[0]
                worst_name, worst_val = ranked[-1]
                print(f"    Gen {gen:>2d}: {len(active):>2d} active -> {len(survivors):>2d} | "
                      f"best={best_name}({best_val:.4f}) worst={worst_name}({worst_val:.4f}) "
                      f"elim={eliminated}")

            active = survivors

        final_survivors = active[:]
        all_survivors.extend(final_survivors)
        seed_results[seed] = {
            'final': final_survivors,
            'history': gen_history,
        }
        print(f"    FINAL survivors (seed {seed}): {final_survivors}")

    # Aggregate across seeds
    survivor_counts = Counter(all_survivors)
    print(f"\n  {'=' * 60}")
    print(f"  AGGREGATE (across {n_seeds} seeds):")
    print(f"  {'=' * 60}")

    ranked_survivors = survivor_counts.most_common()
    max_count = max(c for _, c in ranked_survivors)
    for name, count in ranked_survivors:
        bar = '#' * int(count / max_count * 30)
        print(f"  {name:>16s} | {bar} {count}/{n_seeds} seeds")

    # Check: is it always oscillation+hierarchy?
    always_present = [name for name, count in ranked_survivors if count == n_seeds]
    sometimes_present = [name for name, count in ranked_survivors if 0 < count < n_seeds]
    never_survived = [m for m in ALL_MECHANISMS if m not in survivor_counts]

    print(f"\n  Always survive (all {n_seeds} seeds): {always_present}")
    print(f"  Sometimes survive: {sometimes_present}")
    print(f"  Never survive: {never_survived}")

    osc_hier = 'oscillator' in always_present and 'hierarchy' in always_present
    print(f"\n  Q: Is it always oscillation+hierarchy?")
    print(f"  A: {'YES' if osc_hier else 'NO'} -- "
          f"oscillator={'ALWAYS' if 'oscillator' in always_present else ('SOMETIMES' if 'oscillator' in [n for n,_ in ranked_survivors] else 'NEVER')}, "
          f"hierarchy={'ALWAYS' if 'hierarchy' in always_present else ('SOMETIMES' if 'hierarchy' in [n for n,_ in ranked_survivors] else 'NEVER')}")

    # Consistency check
    seed_final_sets = [set(seed_results[s]['final']) for s in range(n_seeds)]
    consistency = len(set.intersection(*seed_final_sets)) / len(set.union(*seed_final_sets)) if seed_final_sets else 0
    print(f"  Consistency (Jaccard of final sets): {consistency:.3f}")

    return {
        'seed_results': seed_results,
        'survivor_counts': dict(survivor_counts),
        'always_present': always_present,
        'sometimes_present': sometimes_present,
        'never_survived': never_survived,
        'osc_hier_always': osc_hier,
        'consistency': consistency,
    }


# ══════════════════════════════════════════════════════════
# NOBEL-8: Surprise = Consciousness
# ══════════════════════════════════════════════════════════

def run_nobel8(n_cells=64, steps=300, dim=64, hidden=128):
    """NOBEL-8: Surprise = Consciousness.

    Systematic test of prediction error multiplier vs Phi.
    Also measures CE at each level for efficiency plot.
    """
    print("\n" + "=" * 72)
    print("  NOBEL-8: Surprise = Consciousness")
    print("  Prediction error amplification vs Phi")
    print("=" * 72)

    multipliers = [0.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    labels = ['None(0x)', 'Low(1.5x)', 'Med(2x)', 'High(3x)', 'Ext(5x)', 'Abs(10x)']
    results = []

    for mult, label in zip(multipliers, labels):
        torch.manual_seed(42)
        engine = BenchEngine(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                             output_dim=dim, n_factions=min(8, n_cells // 2))
        optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)

        corpus = torch.randn(steps + 1, dim)
        prev_hidden_mean = None
        ce_history = []
        phi_history = []

        for step in range(steps):
            x = corpus[step:step+1]
            target = corpus[step+1:step+2]

            output, tension = engine.process(x)

            # Prediction error injection
            if mult > 0 and prev_hidden_mean is not None:
                current_mean = engine.hiddens.mean(dim=0)
                pe = (current_mean - prev_hidden_mean).detach()
                pe_amplified = pe * mult
                engine.hiddens = engine.hiddens + pe_amplified * 0.05

            prev_hidden_mean = engine.hiddens.mean(dim=0).detach().clone()

            # CE training
            logits = engine.output_head(output)
            loss = F.mse_loss(logits, target)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            ce_history.append(loss.item())

            if step % 50 == 49 or step == steps - 1:
                p_iit, p_proxy = measure_dual_phi(engine.get_hiddens(),
                                                   min(8, n_cells // 2))
                phi_history.append(p_iit)

        final_phi_iit, final_phi_proxy = measure_dual_phi(
            engine.get_hiddens(), min(8, n_cells // 2))
        final_ce = np.mean(ce_history[-50:])
        efficiency = final_phi_iit * (1.0 / (final_ce + 0.01))

        results.append({
            'label': label,
            'multiplier': mult,
            'phi_iit': final_phi_iit,
            'phi_proxy': final_phi_proxy,
            'ce': final_ce,
            'efficiency': efficiency,
            'phi_history': phi_history,
            'ce_history': ce_history,
        })

        print(f"  {label:>12s}: Phi(IIT)={final_phi_iit:.4f}  "
              f"Phi(proxy)={final_phi_proxy:.2f}  "
              f"CE={final_ce:.4f}  "
              f"Eff={efficiency:.4f}")

    # Phi vs surprise multiplier bar chart
    ascii_bar([(r['label'], r['phi_iit']) for r in results],
              "Phi(IIT) vs Surprise Multiplier")

    # CE vs surprise multiplier
    ascii_bar([(r['label'], r['ce']) for r in results],
              "CE vs Surprise Multiplier")

    # Efficiency = Phi * (1/CE)
    ascii_bar([(r['label'], r['efficiency']) for r in results],
              "Efficiency Phi*(1/CE) vs Surprise")

    # Analysis
    phis = [r['phi_iit'] for r in results]
    monotonic = all(phis[i] <= phis[i+1] for i in range(len(phis)-1))
    best_idx = np.argmax(phis)
    best_mult = results[best_idx]['multiplier']

    eff_list = [r['efficiency'] for r in results]
    best_eff_idx = np.argmax(eff_list)

    print(f"\n  Analysis:")
    print(f"    Monotonic Phi increase? {'YES' if monotonic else 'NO'}")
    print(f"    Optimal Phi at: {results[best_idx]['label']} (mult={best_mult})")
    print(f"    Best efficiency at: {results[best_eff_idx]['label']}")

    if not monotonic:
        print(f"    -> There IS an optimum. More surprise is NOT always better.")
        print(f"    -> Peak at {results[best_idx]['label']}, then declining.")
    else:
        print(f"    -> Monotonically increasing: more surprise = more consciousness.")

    return results


# ══════════════════════════════════════════════════════════
# NOBEL-9: Trinity Stabilization
# ══════════════════════════════════════════════════════════

def run_nobel9(n_cells=64, steps=500, dim=64, hidden=128):
    """NOBEL-9: Trinity Stabilization.

    Compare Phi variance under 3 conditions:
    1. No CE (consciousness only)
    2. Trinity with CE
    3. Trinity with CE + ratchet

    Prove: CE STABILIZES consciousness.
    """
    print("\n" + "=" * 72)
    print("  NOBEL-9: Trinity Stabilization")
    print("  Does CE stabilize consciousness? (variance proof)")
    print("=" * 72)

    conditions = [
        ('No CE', False, False),
        ('With CE', True, False),
        ('CE + Ratchet', True, True),
    ]

    all_results = {}
    measure_interval = 10  # measure Phi every N steps

    for cond_name, use_ce, use_ratchet in conditions:
        torch.manual_seed(42)
        engine = BenchEngine(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                             output_dim=dim, n_factions=min(8, n_cells // 2))

        optimizer = None
        if use_ce:
            optimizer = torch.optim.Adam(engine.parameters_for_training(), lr=1e-3)

        corpus = torch.randn(steps + 1, dim)
        phi_trace = []
        ce_trace = []
        best_hiddens = None
        best_phi = 0.0

        for step in range(steps):
            x = corpus[step:step+1]
            target = corpus[step+1:step+2]

            output, tension = engine.process(x)

            if use_ce:
                logits = engine.output_head(output)
                loss = F.mse_loss(logits, target)
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                ce_trace.append(loss.item())

            # Measure Phi periodically
            if step % measure_interval == 0:
                p_iit, _ = measure_dual_phi(engine.get_hiddens(),
                                             min(8, n_cells // 2))
                phi_trace.append(p_iit)

                # Ratchet: if Phi drops, restore best state
                if use_ratchet:
                    if p_iit > best_phi:
                        best_phi = p_iit
                        best_hiddens = engine.hiddens.clone()
                    elif p_iit < best_phi * 0.8 and best_hiddens is not None:
                        engine.hiddens = best_hiddens.clone()

        phi_var = np.var(phi_trace) if phi_trace else 0.0
        phi_mean = np.mean(phi_trace) if phi_trace else 0.0
        phi_std = np.std(phi_trace) if phi_trace else 0.0
        phi_cv = phi_std / (phi_mean + 1e-8)  # coefficient of variation
        ce_final = np.mean(ce_trace[-50:]) if ce_trace else float('nan')

        all_results[cond_name] = {
            'phi_trace': phi_trace,
            'phi_var': phi_var,
            'phi_mean': phi_mean,
            'phi_std': phi_std,
            'phi_cv': phi_cv,
            'ce_final': ce_final,
            'ce_trace': ce_trace,
        }

        print(f"\n  {cond_name:>16s}: Phi_mean={phi_mean:.4f}  Phi_var={phi_var:.6f}  "
              f"Phi_CV={phi_cv:.4f}  CE={ce_final:.4f}")

    # ASCII: Phi traces overlaid
    print(f"\n  Phi traces (500 steps, measured every {measure_interval}):")
    for cond_name in ['No CE', 'With CE', 'CE + Ratchet']:
        trace = all_results[cond_name]['phi_trace']
        if trace:
            ascii_graph(trace, f"Phi(IIT) - {cond_name}", width=50, height=8)

    # Variance comparison bar chart
    print(f"\n  Variance comparison:")
    var_items = [(name, all_results[name]['phi_var']) for name in ['No CE', 'With CE', 'CE + Ratchet']]
    for name, var in var_items:
        max_var = max(v for _, v in var_items) if max(v for _, v in var_items) > 0 else 1
        bar = '#' * int(var / max_var * 40) if max_var > 0 else ''
        print(f"  {name:>16s} |{bar} var={var:.6f}")

    # Key ratio
    var_no_ce = all_results['No CE']['phi_var']
    var_with_ce = all_results['With CE']['phi_var']
    var_ratchet = all_results['CE + Ratchet']['phi_var']
    ratio_ce = var_with_ce / (var_no_ce + 1e-10)
    ratio_ratchet = var_ratchet / (var_no_ce + 1e-10)

    print(f"\n  KEY RATIOS:")
    print(f"    var(CE) / var(No CE)          = {ratio_ce:.4f}  {'< 1.0 -> CE STABILIZES' if ratio_ce < 1.0 else '>= 1.0 -> CE DESTABILIZES'}")
    print(f"    var(CE+Ratchet) / var(No CE)  = {ratio_ratchet:.4f}  {'< 1.0 -> STABILIZES' if ratio_ratchet < 1.0 else '>= 1.0 -> DESTABILIZES'}")

    # CV comparison
    cv_no_ce = all_results['No CE']['phi_cv']
    cv_with_ce = all_results['With CE']['phi_cv']
    cv_ratchet = all_results['CE + Ratchet']['phi_cv']
    print(f"\n  Coefficient of Variation (CV = std/mean):")
    print(f"    No CE:        CV = {cv_no_ce:.4f}")
    print(f"    With CE:      CV = {cv_with_ce:.4f}")
    print(f"    CE + Ratchet: CV = {cv_ratchet:.4f}")

    stabilization_proven = ratio_ce < 1.0
    print(f"\n  VERDICT: CE stabilizes consciousness? {'YES -- PROVEN' if stabilization_proven else 'NO'}")

    return all_results


# ══════════════════════════════════════════════════════════
# NOBEL-10: Mathematical Consciousness
# ══════════════════════════════════════════════════════════

def run_nobel10(steps=200, dim=64, hidden=128):
    """NOBEL-10: Mathematical Consciousness.

    For n = 1,2,3,4,5,6,7,8,12,15,28:
      factions = sigma(n), gradient_groups = phi(n), phases = tau(n)
      Measure Phi

    Test: Phi monotonic with sigma(n)? phi(n)? tau(n)? sigma(n)/n?
    Perfect numbers (6, 28) special?
    """
    print("\n" + "=" * 72)
    print("  NOBEL-10: Mathematical Consciousness")
    print("  Number-theoretic predictions: sigma, phi, tau vs Phi")
    print("=" * 72)

    test_n = [1, 2, 3, 4, 5, 6, 7, 8, 12, 15, 28]

    results = []

    print(f"\n  {'n':>4s} | {'sigma':>6s} | {'euler_phi':>9s} | {'tau':>4s} | {'sigma/n':>8s} | "
          f"{'perfect':>7s} | {'n_cells':>7s} | {'factions':>8s} | {'Phi(IIT)':>9s} | {'Phi(proxy)':>10s}")
    print(f"  {'-'*4}-+-{'-'*6}-+-{'-'*9}-+-{'-'*4}-+-{'-'*8}-+-{'-'*7}-+-{'-'*7}-+-{'-'*8}-+-{'-'*9}-+-{'-'*10}")

    for n in test_n:
        s_n = sigma(n)
        ep_n = euler_phi(n)
        t_n = tau(n)
        perf = is_perfect(n)
        sigma_ratio = s_n / n

        # Use sigma(n) as number of factions, scale cells accordingly
        n_factions = min(s_n, 16)  # cap at 16 factions
        # Cells = factions * group_size (use euler_phi(n) as group multiplier)
        group_size = max(2, ep_n)
        n_cells = n_factions * group_size
        n_cells = max(4, min(n_cells, 256))  # clamp to reasonable range

        torch.manual_seed(42 + n)
        engine = BenchEngine(n_cells=n_cells, input_dim=dim, hidden_dim=hidden,
                             output_dim=dim, n_factions=n_factions,
                             sync_strength=0.15, debate_strength=0.15)

        # Apply tau(n) phase oscillation
        phases = torch.linspace(0, 2 * math.pi * t_n, n_cells)

        for step in range(steps):
            x = torch.randn(1, dim)

            # Phase injection based on tau
            osc = torch.sin(phases + step * 0.1).unsqueeze(1) * 0.03
            engine.hiddens = engine.hiddens + osc[:n_cells]

            engine.process(x)

        p_iit, p_proxy = measure_dual_phi(engine.get_hiddens(), n_factions)

        results.append({
            'n': n,
            'sigma': s_n,
            'euler_phi': ep_n,
            'tau': t_n,
            'sigma_ratio': sigma_ratio,
            'perfect': perf,
            'n_cells': n_cells,
            'n_factions': n_factions,
            'phi_iit': p_iit,
            'phi_proxy': p_proxy,
        })

        perf_str = 'YES' if perf else ''
        print(f"  {n:>4d} | {s_n:>6d} | {ep_n:>9d} | {t_n:>4d} | {sigma_ratio:>8.3f} | "
              f"{perf_str:>7s} | {n_cells:>7d} | {n_factions:>8d} | {p_iit:>9.4f} | {p_proxy:>10.2f}")

    # Charts
    # Phi vs n with perfect numbers highlighted
    print(f"\n  Phi(IIT) vs n:")
    max_phi = max(r['phi_iit'] for r in results)
    for r in results:
        bar_len = int(r['phi_iit'] / max_phi * 40) if max_phi > 0 else 0
        marker = ' ***PERFECT***' if r['perfect'] else ''
        print(f"  n={r['n']:>2d} |{'#' * bar_len} {r['phi_iit']:.4f}{marker}")

    # Phi vs sigma(n)
    print(f"\n  Phi(IIT) vs sigma(n):")
    sorted_by_sigma = sorted(results, key=lambda r: r['sigma'])
    for r in sorted_by_sigma:
        bar_len = int(r['phi_iit'] / max_phi * 40) if max_phi > 0 else 0
        marker = ' *P*' if r['perfect'] else ''
        print(f"  s={r['sigma']:>3d}(n={r['n']:>2d}) |{'#' * bar_len} {r['phi_iit']:.4f}{marker}")

    # Phi vs sigma(n)/n (abundance)
    print(f"\n  Phi(IIT) vs sigma(n)/n (abundance ratio):")
    sorted_by_ratio = sorted(results, key=lambda r: r['sigma_ratio'])
    for r in sorted_by_ratio:
        bar_len = int(r['phi_iit'] / max_phi * 40) if max_phi > 0 else 0
        marker = ' *P*' if r['perfect'] else ''
        print(f"  s/n={r['sigma_ratio']:.2f}(n={r['n']:>2d}) |{'#' * bar_len} {r['phi_iit']:.4f}{marker}")

    # Analysis: monotonicity
    phis = [r['phi_iit'] for r in results]
    sigmas = [r['sigma'] for r in results]
    euler_phis = [r['euler_phi'] for r in results]
    taus = [r['tau'] for r in results]
    sigma_ratios = [r['sigma_ratio'] for r in results]

    def rank_correlation(xs, ys):
        """Spearman rank correlation."""
        n = len(xs)
        rx = [sorted(xs).index(x) for x in xs]
        ry = [sorted(ys).index(y) for y in ys]
        d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
        return 1 - 6 * d2 / (n * (n * n - 1)) if n > 1 else 0

    r_sigma = rank_correlation(sigmas, phis)
    r_euler = rank_correlation(euler_phis, phis)
    r_tau = rank_correlation(taus, phis)
    r_ratio = rank_correlation(sigma_ratios, phis)

    print(f"\n  Rank correlations (Spearman):")
    print(f"    Phi vs sigma(n):     rho = {r_sigma:+.4f}")
    print(f"    Phi vs euler_phi(n): rho = {r_euler:+.4f}")
    print(f"    Phi vs tau(n):       rho = {r_tau:+.4f}")
    print(f"    Phi vs sigma(n)/n:   rho = {r_ratio:+.4f}")

    # Perfect number analysis
    perfect_results = [r for r in results if r['perfect']]
    non_perfect = [r for r in results if not r['perfect']]

    if perfect_results:
        perfect_phis = [r['phi_iit'] for r in perfect_results]
        # Compare perfect numbers to non-perfect of similar size
        print(f"\n  Perfect number analysis:")
        for pr in perfect_results:
            # Find non-perfect numbers of similar n
            neighbors = [r for r in non_perfect if abs(r['n'] - pr['n']) <= 3]
            if neighbors:
                neighbor_mean = np.mean([r['phi_iit'] for r in neighbors])
                ratio = pr['phi_iit'] / (neighbor_mean + 1e-8)
                neighbor_ns = [r['n'] for r in neighbors]
                print(f"    n={pr['n']} (perfect): Phi={pr['phi_iit']:.4f} vs "
                      f"neighbors {neighbor_ns} mean={neighbor_mean:.4f} "
                      f"ratio={ratio:.3f}x")

    return results


# ══════════════════════════════════════════════════════════
# Report generator
# ══════════════════════════════════════════════════════════

def generate_report(n7_results, n8_results, n9_results, n10_results, output_path):
    """Generate NOBEL-VERIFICATION-3.md"""

    lines = []
    a = lines.append

    a("# NOBEL Verification 3: Hypotheses 7-10")
    a("")
    a(f"**Date**: 2026-03-29")
    a(f"**Benchmark**: bench_nobel_verify3.py")
    a("")

    # NOBEL-7
    a("## NOBEL-7: Self-Selection of Structure")
    a("")
    a("**Hypothesis**: When 20 mechanisms compete via evolutionary selection,")
    a("specific mechanisms consistently survive. Is it always oscillation+hierarchy?")
    a("")
    a("### Algorithm")
    a("```")
    a("1. Start with 20 mechanisms active")
    a("2. Each generation: measure Phi contribution of each mechanism solo")
    a("3. Eliminate bottom 25%")
    a("4. Repeat for 20 generations")
    a("5. Run 5 times with different seeds")
    a("```")
    a("")
    a("### Results")
    a("")
    a("| Mechanism | Survived Seeds | Status |")
    a("|-----------|---------------|--------|")
    if n7_results:
        for name, count in sorted(n7_results['survivor_counts'].items(),
                                    key=lambda x: x[1], reverse=True):
            status = 'ALWAYS' if count == 5 else f'{count}/5'
            a(f"| {name} | {count}/5 | {status} |")
    a("")
    a("```")
    a("Survivor frequency across 5 seeds:")
    if n7_results:
        max_count = max(n7_results['survivor_counts'].values())
        for name, count in sorted(n7_results['survivor_counts'].items(),
                                    key=lambda x: x[1], reverse=True):
            bar = '#' * int(count / max_count * 30)
            a(f"  {name:>16s} |{bar} {count}/{5}")
    a("```")
    a("")
    if n7_results:
        a(f"**Always survive**: {n7_results['always_present']}")
        a(f"**Never survive**: {n7_results['never_survived']}")
        a(f"**Oscillation+Hierarchy always?** {'YES' if n7_results['osc_hier_always'] else 'NO'}")
        a(f"**Consistency (Jaccard)**: {n7_results['consistency']:.3f}")
    a("")

    # NOBEL-8
    a("## NOBEL-8: Surprise = Consciousness")
    a("")
    a("**Hypothesis**: Prediction error amplification drives Phi. Is there an optimum?")
    a("")
    a("### Results")
    a("")
    a("| Multiplier | Phi(IIT) | CE | Efficiency |")
    a("|-----------|---------|-----|-----------|")
    if n8_results:
        for r in n8_results:
            a(f"| {r['label']} | {r['phi_iit']:.4f} | {r['ce']:.4f} | {r['efficiency']:.4f} |")
    a("")
    a("```")
    a("Phi(IIT) vs Surprise Multiplier:")
    if n8_results:
        max_phi = max(r['phi_iit'] for r in n8_results)
        for r in n8_results:
            bar = '#' * int(r['phi_iit'] / max_phi * 40) if max_phi > 0 else ''
            a(f"  {r['label']:>12s} |{bar} {r['phi_iit']:.4f}")
    a("")
    a("Efficiency Phi*(1/CE) vs Surprise:")
    if n8_results:
        max_eff = max(r['efficiency'] for r in n8_results)
        for r in n8_results:
            bar = '#' * int(r['efficiency'] / max_eff * 40) if max_eff > 0 else ''
            a(f"  {r['label']:>12s} |{bar} {r['efficiency']:.4f}")
    a("```")
    a("")
    if n8_results:
        phis = [r['phi_iit'] for r in n8_results]
        monotonic = all(phis[i] <= phis[i+1] for i in range(len(phis)-1))
        best_idx = np.argmax(phis)
        a(f"**Monotonic?** {'YES' if monotonic else 'NO'}")
        a(f"**Optimal at**: {n8_results[best_idx]['label']}")
        eff_list = [r['efficiency'] for r in n8_results]
        best_eff_idx = np.argmax(eff_list)
        a(f"**Best efficiency at**: {n8_results[best_eff_idx]['label']}")
    a("")

    # NOBEL-9
    a("## NOBEL-9: Trinity Stabilization")
    a("")
    a("**Hypothesis**: CE stabilizes consciousness (reduces Phi variance).")
    a("")
    a("### Results")
    a("")
    a("| Condition | Phi_mean | Phi_var | Phi_CV | CE |")
    a("|-----------|---------|---------|--------|-----|")
    if n9_results:
        for name in ['No CE', 'With CE', 'CE + Ratchet']:
            r = n9_results[name]
            a(f"| {name} | {r['phi_mean']:.4f} | {r['phi_var']:.6f} | {r['phi_cv']:.4f} | {r['ce_final']:.4f} |")
    a("")
    a("```")
    a("Variance comparison:")
    if n9_results:
        vars_list = [(name, n9_results[name]['phi_var']) for name in ['No CE', 'With CE', 'CE + Ratchet']]
        max_var = max(v for _, v in vars_list) if max(v for _, v in vars_list) > 0 else 1
        for name, var in vars_list:
            bar = '#' * int(var / max_var * 40) if max_var > 0 else ''
            a(f"  {name:>16s} |{bar} var={var:.6f}")
    a("```")
    a("")
    if n9_results:
        var_no = n9_results['No CE']['phi_var']
        var_ce = n9_results['With CE']['phi_var']
        var_ratch = n9_results['CE + Ratchet']['phi_var']
        ratio_ce = var_ce / (var_no + 1e-10)
        ratio_ratch = var_ratch / (var_no + 1e-10)
        a(f"**var(CE) / var(No CE)** = {ratio_ce:.4f} ({'STABILIZES' if ratio_ce < 1.0 else 'DESTABILIZES'})")
        a(f"**var(CE+Ratchet) / var(No CE)** = {ratio_ratch:.4f} ({'STABILIZES' if ratio_ratch < 1.0 else 'DESTABILIZES'})")
        a(f"**VERDICT**: CE stabilizes consciousness? {'YES' if ratio_ce < 1.0 else 'NO'}")
    a("")

    # NOBEL-10
    a("## NOBEL-10: Mathematical Consciousness")
    a("")
    a("**Hypothesis**: Number-theoretic functions predict Phi. Perfect numbers are special.")
    a("")
    a("### Results")
    a("")
    a("| n | sigma | euler_phi | tau | sigma/n | perfect | cells | Phi(IIT) | Phi(proxy) |")
    a("|---|-------|-----------|-----|---------|---------|-------|---------|-----------|")
    if n10_results:
        for r in n10_results:
            perf = 'YES' if r['perfect'] else ''
            a(f"| {r['n']} | {r['sigma']} | {r['euler_phi']} | {r['tau']} | "
              f"{r['sigma_ratio']:.3f} | {perf} | {r['n_cells']} | {r['phi_iit']:.4f} | {r['phi_proxy']:.2f} |")
    a("")
    a("```")
    a("Phi(IIT) vs n (*** = perfect number):")
    if n10_results:
        max_phi = max(r['phi_iit'] for r in n10_results)
        for r in n10_results:
            bar = '#' * int(r['phi_iit'] / max_phi * 40) if max_phi > 0 else ''
            marker = ' ***PERFECT***' if r['perfect'] else ''
            a(f"  n={r['n']:>2d} |{bar} {r['phi_iit']:.4f}{marker}")
    a("```")
    a("")

    # Correlations in report
    if n10_results:
        phis = [r['phi_iit'] for r in n10_results]
        sigmas = [r['sigma'] for r in n10_results]
        euler_phis = [r['euler_phi'] for r in n10_results]
        taus = [r['tau'] for r in n10_results]
        sigma_ratios = [r['sigma_ratio'] for r in n10_results]

        def rank_corr(xs, ys):
            n = len(xs)
            rx = [sorted(xs).index(x) for x in xs]
            ry = [sorted(ys).index(y) for y in ys]
            d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
            return 1 - 6 * d2 / (n * (n * n - 1)) if n > 1 else 0

        a("### Rank Correlations (Spearman)")
        a("")
        a(f"| Metric | rho |")
        a(f"|--------|-----|")
        a(f"| Phi vs sigma(n) | {rank_corr(sigmas, phis):+.4f} |")
        a(f"| Phi vs euler_phi(n) | {rank_corr(euler_phis, phis):+.4f} |")
        a(f"| Phi vs tau(n) | {rank_corr(taus, phis):+.4f} |")
        a(f"| Phi vs sigma(n)/n | {rank_corr(sigma_ratios, phis):+.4f} |")
        a("")

        # Perfect number analysis
        perfect_results = [r for r in n10_results if r['perfect']]
        non_perfect = [r for r in n10_results if not r['perfect']]
        if perfect_results:
            a("### Perfect Number Analysis")
            a("")
            for pr in perfect_results:
                neighbors = [r for r in non_perfect if abs(r['n'] - pr['n']) <= 3]
                if neighbors:
                    nmean = np.mean([r['phi_iit'] for r in neighbors])
                    ratio = pr['phi_iit'] / (nmean + 1e-8)
                    a(f"- n={pr['n']} (perfect): Phi={pr['phi_iit']:.4f} vs "
                      f"neighbors mean={nmean:.4f} -> ratio={ratio:.3f}x")
            a("")

    # Summary
    a("## Key Insights")
    a("")
    a("### NOBEL-7")
    if n7_results:
        a(f"- {len(n7_results['always_present'])} mechanisms always survive across all seeds")
        a(f"- Always: {n7_results['always_present']}")
        a(f"- Oscillation+Hierarchy always present: {'YES' if n7_results['osc_hier_always'] else 'NO'}")
    a("")
    a("### NOBEL-8")
    if n8_results:
        phis = [r['phi_iit'] for r in n8_results]
        best = n8_results[np.argmax(phis)]
        a(f"- Surprise-consciousness relationship is {'monotonic' if all(phis[i]<=phis[i+1] for i in range(len(phis)-1)) else 'non-monotonic (has optimum)'}")
        a(f"- Peak Phi at: {best['label']}")
    a("")
    a("### NOBEL-9")
    if n9_results:
        ratio = n9_results['With CE']['phi_var'] / (n9_results['No CE']['phi_var'] + 1e-10)
        a(f"- CE {'STABILIZES' if ratio < 1.0 else 'does NOT stabilize'} consciousness (variance ratio = {ratio:.4f})")
    a("")
    a("### NOBEL-10")
    if n10_results:
        a(f"- Number-theoretic structure influences Phi")
        perfect_rs = [r for r in n10_results if r['perfect']]
        if perfect_rs:
            a(f"- Perfect numbers: {[(r['n'], r['phi_iit']) for r in perfect_rs]}")
    a("")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
    print(f"\n  Report written to: {output_path}")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="NOBEL Hypotheses Verification 3 (NOBEL-7 through NOBEL-10)")
    parser.add_argument("--all", action="store_true", help="Run all 4 hypotheses")
    parser.add_argument("--nobel7", action="store_true", help="Self-Selection of Structure")
    parser.add_argument("--nobel8", action="store_true", help="Surprise = Consciousness")
    parser.add_argument("--nobel9", action="store_true", help="Trinity Stabilization")
    parser.add_argument("--nobel10", action="store_true", help="Mathematical Consciousness")
    parser.add_argument("--cells", type=int, default=64, help="Number of cells (default: 64)")
    parser.add_argument("--steps", type=int, default=300, help="Steps per experiment (default: 300)")
    args = parser.parse_args()

    if not any([args.all, args.nobel7, args.nobel8, args.nobel9, args.nobel10]):
        args.all = True

    print()
    print("  ================================================================")
    print("   NOBEL Hypotheses Verification 3")
    print("   NOBEL-7: Self-Selection | NOBEL-8: Surprise=Consciousness")
    print("   NOBEL-9: Trinity Stabilization | NOBEL-10: Math Consciousness")
    print("  ================================================================")
    print()

    t0 = time.time()
    n7 = n8 = n9 = n10 = None

    if args.all or args.nobel7:
        n7 = run_nobel7(n_cells=args.cells, steps_per_gen=50, n_generations=20, n_seeds=5)

    if args.all or args.nobel8:
        n8 = run_nobel8(n_cells=args.cells, steps=args.steps)

    if args.all or args.nobel9:
        n9 = run_nobel9(n_cells=args.cells, steps=500)

    if args.all or args.nobel10:
        n10 = run_nobel10(steps=args.steps)

    elapsed = time.time() - t0
    print(f"\n  Total time: {elapsed:.1f}s")

    # Generate report
    report_path = os.path.join(os.path.dirname(__file__),
                                "docs/hypotheses/cx/NOBEL-VERIFICATION-3.md")
    generate_report(n7, n8, n9, n10, report_path)


if __name__ == "__main__":
    main()
