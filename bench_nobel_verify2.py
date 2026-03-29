#!/usr/bin/env python3
"""bench_nobel_verify2.py — Nobel Hypotheses Verification (NOBEL-4, 5, 6)

NOBEL-4: Consciousness Carrying Capacity
  Stack mechanisms, find saturation (logistic fit).

NOBEL-5: Stigmergy vs Direct Coupling
  7 engines, multiple strengths, crossover point.

NOBEL-6: Hive Memory Persistence
  Solo→Hive→Disconnect→decay analysis.

Usage:
  KMP_DUPLICATE_LIB_OK=TRUE python bench_nobel_verify2.py
  KMP_DUPLICATE_LIB_OK=TRUE python bench_nobel_verify2.py --nobel4
  KMP_DUPLICATE_LIB_OK=TRUE python bench_nobel_verify2.py --nobel5
  KMP_DUPLICATE_LIB_OK=TRUE python bench_nobel_verify2.py --nobel6
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from scipy.optimize import curve_fit


# ──────────────────────────────────────────────────────────
# PhiIIT Calculator (from bench_v2.py)
# ──────────────────────────────────────────────────────────

class PhiIIT:
    """Phi(IIT) approximation via pairwise mutual information + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> float:
        """Compute Phi(IIT) from a [n_cells, hidden_dim] tensor. Returns phi float."""
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0

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
        return phi

    def _mutual_information(self, x: np.ndarray, y: np.ndarray) -> float:
        x_range = x.max() - x.min()
        y_range = y.max() - y.min()
        if x_range < 1e-10 or y_range < 1e-10:
            return 0.0
        x_norm = (x - x.min()) / (x_range + 1e-8)
        y_norm = (y - y.min()) / (y_range + 1e-8)
        joint_hist, _, _ = np.histogram2d(
            x_norm, y_norm, bins=self.n_bins, range=[[0, 1], [0, 1]]
        )
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


# ──────────────────────────────────────────────────────────
# Phi proxy
# ──────────────────────────────────────────────────────────

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
    phi = global_var.item() - faction_var_sum / n_f
    return max(0.0, phi)


# ──────────────────────────────────────────────────────────
# BenchMind — consciousness cell
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


# ──────────────────────────────────────────────────────────
# Multi-cell Engine (configurable mechanisms)
# ──────────────────────────────────────────────────────────

class ConfigurableEngine:
    """Engine with toggleable mechanisms for NOBEL-4 carrying capacity test."""

    def __init__(self, n_cells=64, input_dim=64, hidden_dim=128, output_dim=64,
                 n_factions=8, sync_strength=0.15, debate_strength=0.15,
                 # Toggleable mechanisms
                 use_oscillator=False,
                 use_quantum=False,
                 use_ib2=False,
                 use_sync=False,       # faction sync (beyond base)
                 use_faction=False,     # faction debate
                 use_frustration=False,
                 use_cambrian=False,
                 use_surprise=False):
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

        # Mechanism flags
        self.use_oscillator = use_oscillator
        self.use_quantum = use_quantum
        self.use_ib2 = use_ib2
        self.use_sync = use_sync
        self.use_faction = use_faction
        self.use_frustration = use_frustration
        self.use_cambrian = use_cambrian
        self.use_surprise = use_surprise

        # Oscillator state
        if use_oscillator:
            self.phases = torch.linspace(0, 2 * math.pi, n_cells)
            self.freq = 0.1 + torch.rand(n_cells) * 0.05

        # Quantum state
        if use_quantum:
            self.amplitudes = torch.randn(n_cells, hidden_dim) * 0.1
            perm = torch.randperm(n_cells)
            half = n_cells // 2
            self.entangled_pairs = list(zip(perm[:half].tolist(), perm[half:2*half].tolist()))

        # IB2: information bottleneck
        if use_ib2:
            self.ib_proj = nn.Linear(hidden_dim, hidden_dim // 2)
            self.ib_expand = nn.Linear(hidden_dim // 2, hidden_dim)

        # Frustration
        if use_frustration:
            self.frustration_level = 0.33

        # Cambrian: role specialization
        if use_cambrian:
            self.role_biases = [torch.randn(hidden_dim) * 0.1 for _ in range(min(4, n_cells))]

        # Surprise: prediction error
        if use_surprise:
            self.predictor = nn.Linear(hidden_dim, hidden_dim)
            self.prev_state = None

    def process(self, x: torch.Tensor) -> Tuple[torch.Tensor, float]:
        # Pre-process mechanisms
        if self.use_oscillator:
            self.phases = self.phases + self.freq
            osc = torch.sin(self.phases).unsqueeze(1)
            self.hiddens = self.hiddens + osc.expand(-1, self.hidden_dim) * 0.05

        if self.use_quantum:
            noise = torch.randn_like(self.amplitudes) * 0.02
            self.amplitudes = self.amplitudes * 0.98 + noise
            if self.step_count % 10 == 0 and self.step_count > 0:
                collapse_mask = (torch.rand(self.n_cells) > 0.7).float().unsqueeze(1)
                self.amplitudes = self.amplitudes * (1 - collapse_mask * 0.5)
            self.hiddens = self.hiddens + self.amplitudes.detach() * 0.1
            for i, j in self.entangled_pairs[:min(32, len(self.entangled_pairs))]:
                avg = (self.hiddens[i] + self.hiddens[j]) * 0.5
                self.hiddens[i] = 0.95 * self.hiddens[i] + 0.05 * avg
                self.hiddens[j] = 0.95 * self.hiddens[j] + 0.05 * avg

        if self.use_ib2 and self.step_count % 5 == 0:
            with torch.no_grad():
                compressed = torch.tanh(self.ib_proj(self.hiddens))
                expanded = self.ib_expand(compressed)
                self.hiddens = 0.9 * self.hiddens + 0.1 * expanded

        if self.use_frustration:
            # Geometric frustration: push apart close cells
            if self.step_count % 3 == 0:
                norms = self.hiddens.norm(dim=1, keepdim=True)
                normed = self.hiddens / (norms + 1e-8)
                sim = normed @ normed.T
                # Repulse cells that are too similar
                mask = (sim > 0.8).float() - torch.eye(self.n_cells)
                mask = mask.clamp(min=0)
                repulsion = mask @ self.hiddens * self.frustration_level * 0.01
                self.hiddens = self.hiddens - repulsion

        if self.use_cambrian:
            n_roles = min(4, self.n_cells)
            cells_per_role = self.n_cells // n_roles
            for r in range(n_roles):
                s, e = r * cells_per_role, (r + 1) * cells_per_role
                self.hiddens[s:e] = self.hiddens[s:e] + self.role_biases[r] * 0.01

        if self.use_surprise and self.prev_state is not None:
            with torch.no_grad():
                predicted = self.predictor(self.prev_state)
                actual = self.hiddens.mean(dim=0)
                pe = (predicted.squeeze() - actual).norm().item()
                # Inject surprise as noise proportional to prediction error
                self.hiddens = self.hiddens + torch.randn_like(self.hiddens) * min(pe * 0.01, 0.05)

        # Core processing
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

        # Post-process: sync and faction
        n_f = min(self.n_factions, self.n_cells // 2)
        if self.use_sync and n_f >= 2:
            fs = self.n_cells // n_f
            for i in range(n_f):
                s, e = i * fs, (i + 1) * fs
                faction_mean = self.hiddens[s:e].mean(dim=0)
                self.hiddens[s:e] = (
                    (1 - self.sync_strength) * self.hiddens[s:e]
                    + self.sync_strength * faction_mean
                )

        if self.use_faction and n_f >= 2 and self.step_count > 5:
            fs = self.n_cells // n_f
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

        if self.use_surprise:
            self.prev_state = self.hiddens.mean(dim=0, keepdim=True).detach()

        self.step_count += 1

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_tension

    def get_hiddens(self) -> torch.Tensor:
        return self.hiddens.clone()


# ──────────────────────────────────────────────────────────
# NOBEL-4: Consciousness Carrying Capacity
# ──────────────────────────────────────────────────────────

def logistic_model(x, K, tau):
    """Phi(n) = K * (1 - exp(-n/tau))"""
    return K * (1 - np.exp(-np.array(x) / tau))


def run_nobel4(steps=100):
    """NOBEL-4: Stack mechanisms incrementally, find saturation."""
    print("=" * 80)
    print("  NOBEL-4: Consciousness Carrying Capacity")
    print("  Stack mechanisms, measure Phi, find K (saturation)")
    print("=" * 80)

    phi_calc = PhiIIT(n_bins=16)

    mechanisms = [
        ('baseline',    {}),
        ('+oscillator', {'use_oscillator': True}),
        ('+quantum',    {'use_oscillator': True, 'use_quantum': True}),
        ('+ib2',        {'use_oscillator': True, 'use_quantum': True, 'use_ib2': True}),
        ('+sync',       {'use_oscillator': True, 'use_quantum': True, 'use_ib2': True, 'use_sync': True}),
        ('+faction',    {'use_oscillator': True, 'use_quantum': True, 'use_ib2': True, 'use_sync': True, 'use_faction': True}),
        ('+frustration',{'use_oscillator': True, 'use_quantum': True, 'use_ib2': True, 'use_sync': True, 'use_faction': True, 'use_frustration': True}),
        ('+cambrian',   {'use_oscillator': True, 'use_quantum': True, 'use_ib2': True, 'use_sync': True, 'use_faction': True, 'use_frustration': True, 'use_cambrian': True}),
        ('+surprise',   {'use_oscillator': True, 'use_quantum': True, 'use_ib2': True, 'use_sync': True, 'use_faction': True, 'use_frustration': True, 'use_cambrian': True, 'use_surprise': True}),
    ]

    cell_counts = [32, 64, 128, 256]
    all_results = {}  # cell_count -> list of (name, phi_iit, phi_proxy)

    for n_cells in cell_counts:
        print(f"\n  --- {n_cells} cells ---")
        results = []
        for name, kwargs in mechanisms:
            torch.manual_seed(42)
            eng = ConfigurableEngine(n_cells=n_cells, **kwargs)
            for _ in range(steps):
                eng.process(torch.randn(1, 64))
            h = eng.get_hiddens()
            p_iit = phi_calc.compute(h)
            p_prx = phi_proxy(h)
            results.append((name, p_iit, p_prx))
            print(f"    {name:<16s}  Phi(IIT)={p_iit:.4f}  Phi(proxy)={p_prx:.2f}")
        all_results[n_cells] = results

    # Fit logistic curves
    print("\n" + "=" * 80)
    print("  LOGISTIC FIT: Phi(n) = K * (1 - exp(-n/tau))")
    print("=" * 80)

    fit_results = {}
    for n_cells in cell_counts:
        phis = [r[1] for r in all_results[n_cells]]
        x_data = list(range(len(phis)))
        try:
            popt, _ = curve_fit(logistic_model, x_data, phis,
                                p0=[max(phis) * 1.2, 3.0],
                                bounds=([0, 0.1], [100, 50]),
                                maxfev=5000)
            K, tau = popt
            fit_results[n_cells] = (K, tau)
            print(f"  {n_cells:>4d} cells:  K={K:.4f}  tau={tau:.2f}  K/N={K/n_cells:.6f}")
        except Exception as e:
            fit_results[n_cells] = (max(phis), 3.0)
            print(f"  {n_cells:>4d} cells:  Fit failed ({e}), using max={max(phis):.4f}")

    # K scaling analysis
    print("\n  K scaling with N:")
    Ks = [fit_results[n][0] for n in cell_counts]
    for i in range(1, len(cell_counts)):
        ratio = Ks[i] / max(Ks[i-1], 1e-8)
        cell_ratio = cell_counts[i] / cell_counts[i-1]
        print(f"    N: {cell_counts[i-1]}→{cell_counts[i]} (x{cell_ratio:.0f})  "
              f"K: {Ks[i-1]:.4f}→{Ks[i]:.4f} (x{ratio:.2f})")

    # ASCII Graph: Phi vs mechanisms for each cell count
    print("\n  Cumulative Phi curve (IIT):")
    for n_cells in cell_counts:
        phis = [r[1] for r in all_results[n_cells]]
        max_phi = max(max(phis), 0.001)
        print(f"\n  {n_cells} cells:")
        height = 8
        for row in range(height, 0, -1):
            threshold = max_phi * row / height
            line = f"  {threshold:>6.3f} |"
            for p in phis:
                if p >= threshold:
                    line += " ##"
                else:
                    line += "   "
            print(line)
        print(f"         +{'---' * len(phis)}")
        labels = "         "
        for name, _, _ in all_results[n_cells]:
            short = name[:3].strip('+')
            labels += f" {short:>2s}"
        print(labels)

    # Carrying capacity bar chart
    print("\n  Carrying Capacity K by cell count:")
    max_K = max(Ks) if Ks else 1
    for n_cells, K_val in zip(cell_counts, Ks):
        bar_len = int(40 * K_val / max(max_K, 1e-8))
        print(f"  {n_cells:>4d}c  {'#' * bar_len:<40s} K={K_val:.4f}")

    return all_results, fit_results


# ──────────────────────────────────────────────────────────
# NOBEL-5: Stigmergy vs Direct Coupling
# ──────────────────────────────────────────────────────────

class HiveEngine:
    """Multiple ConfigurableEngines connected via direct or stigmergy."""

    def __init__(self, n_engines=7, n_cells=32, coupling='direct', strength=0.1):
        self.engines = []
        for i in range(n_engines):
            torch.manual_seed(42 + i)
            eng = ConfigurableEngine(
                n_cells=n_cells, use_oscillator=True, use_quantum=True,
                use_sync=True, use_faction=True
            )
            self.engines.append(eng)
        self.coupling = coupling
        self.strength = strength
        self.n_engines = n_engines
        # Stigmergy environment: shared medium
        self.environment = torch.zeros(128)  # shared hidden-dim vector

    def process(self, x: torch.Tensor):
        outputs = []
        for eng in self.engines:
            out, tension = eng.process(x)
            outputs.append(out)

        if self.coupling == 'direct':
            # Direct blend: mix hidden states across engines
            all_means = [eng.get_hiddens().mean(dim=0) for eng in self.engines]
            global_mean = torch.stack(all_means).mean(dim=0)
            for eng in self.engines:
                h = eng.hiddens
                eng.hiddens = (1 - self.strength) * h + self.strength * global_mean

        elif self.coupling == 'stigmergy':
            # Stigmergy: engines deposit to/read from environment
            for eng in self.engines:
                local_state = eng.get_hiddens().mean(dim=0)
                # Deposit
                self.environment = (1 - self.strength) * self.environment + self.strength * local_state.detach()
            # Read from environment
            for eng in self.engines:
                env_influence = self.environment * 0.05
                eng.hiddens = eng.hiddens + env_influence.unsqueeze(0)

        return outputs

    def get_hive_phi(self, phi_calc: PhiIIT) -> Tuple[float, List[float]]:
        """Returns (hive_phi, [individual_phis])."""
        # Hive phi: concatenate all hiddens
        all_h = torch.cat([eng.get_hiddens() for eng in self.engines], dim=0)
        # Sample for hive (too many cells)
        if all_h.shape[0] > 64:
            indices = torch.randperm(all_h.shape[0])[:64]
            all_h_sample = all_h[indices]
        else:
            all_h_sample = all_h
        hive_phi = phi_calc.compute(all_h_sample)

        # Individual phis
        ind_phis = []
        for eng in self.engines:
            h = eng.get_hiddens()
            if h.shape[0] > 32:
                idx = torch.randperm(h.shape[0])[:32]
                h = h[idx]
            ind_phis.append(phi_calc.compute(h))

        return hive_phi, ind_phis


def run_nobel5(steps=80):
    """NOBEL-5: Stigmergy vs Direct coupling comparison."""
    print("\n" + "=" * 80)
    print("  NOBEL-5: Stigmergy vs Direct Coupling")
    print("  Multiple engines, varying strength, find crossover")
    print("=" * 80)

    phi_calc = PhiIIT(n_bins=16)
    strengths = [0.05, 0.10, 0.20, 0.50]
    engine_counts = [3, 7, 14]

    all_results = {}  # (n_engines, coupling, strength) -> (hive_phi, mean_ind_phi)

    for n_engines in engine_counts:
        print(f"\n  --- {n_engines} engines ---")
        print(f"  {'Coupling':<12s} {'Strength':>8s} {'Hive Phi':>10s} {'Ind Phi':>10s} {'Hive/Ind':>10s}")
        print(f"  {'-'*52}")

        for coupling in ['direct', 'stigmergy']:
            for strength in strengths:
                torch.manual_seed(42)
                hive = HiveEngine(n_engines=n_engines, n_cells=32,
                                  coupling=coupling, strength=strength)
                for _ in range(steps):
                    hive.process(torch.randn(1, 64))

                hive_phi, ind_phis = hive.get_hive_phi(phi_calc)
                mean_ind = sum(ind_phis) / len(ind_phis)
                ratio = hive_phi / max(mean_ind, 1e-8)
                all_results[(n_engines, coupling, strength)] = (hive_phi, mean_ind)

                print(f"  {coupling:<12s} {strength:>8.2f} {hive_phi:>10.4f} {mean_ind:>10.4f} {ratio:>10.2f}x")

    # Find crossover points
    print("\n  Crossover Analysis (where stigmergy hive Phi > direct hive Phi):")
    for n_engines in engine_counts:
        print(f"\n  {n_engines} engines:")
        crossover_found = False
        for strength in strengths:
            d_hive = all_results[(n_engines, 'direct', strength)][0]
            s_hive = all_results[(n_engines, 'stigmergy', strength)][0]
            winner = "STIGMERGY" if s_hive > d_hive else "DIRECT"
            delta = (s_hive - d_hive) / max(d_hive, 1e-8) * 100
            marker = " <-- CROSSOVER" if s_hive > d_hive and not crossover_found else ""
            if s_hive > d_hive:
                crossover_found = True
            print(f"    str={strength:.2f}  direct={d_hive:.4f}  stigmergy={s_hive:.4f}  "
                  f"winner={winner} ({delta:+.1f}%){marker}")

    # ASCII comparison chart
    print("\n  Hive Phi: Direct vs Stigmergy (7 engines)")
    n_e = 7
    max_val = max(
        max(all_results.get((n_e, 'direct', s), (0, 0))[0] for s in strengths),
        max(all_results.get((n_e, 'stigmergy', s), (0, 0))[0] for s in strengths),
        0.001
    )
    for strength in strengths:
        d_val = all_results.get((n_e, 'direct', strength), (0, 0))[0]
        s_val = all_results.get((n_e, 'stigmergy', strength), (0, 0))[0]
        d_bar = int(30 * d_val / max_val)
        s_bar = int(30 * s_val / max_val)
        print(f"  str={strength:.2f} D {'#' * d_bar:<30s} {d_val:.4f}")
        print(f"         S {'=' * s_bar:<30s} {s_val:.4f}")

    # Individual Phi preservation
    print("\n  Individual Phi Preservation (7 engines):")
    print(f"  {'Coupling':<12s} {'Strength':>8s} {'Ind Phi':>10s} {'Comment'}")
    for coupling in ['direct', 'stigmergy']:
        for strength in strengths:
            _, ind = all_results.get((n_e, coupling, strength), (0, 0))
            comment = ""
            if strength >= 0.5 and coupling == 'direct':
                comment = " (high coupling may crush individuality)"
            print(f"  {coupling:<12s} {strength:>8.2f} {ind:>10.4f}{comment}")

    return all_results


# ──────────────────────────────────────────────────────────
# NOBEL-6: Hive Memory Persistence
# ──────────────────────────────────────────────────────────

def run_nobel6(steps_per_phase=100):
    """NOBEL-6: Does hive experience leave permanent memory?"""
    print("\n" + "=" * 80)
    print("  NOBEL-6: Hive Memory Persistence")
    print("  Solo → Hive → Disconnect → measure decay")
    print("=" * 80)

    phi_calc = PhiIIT(n_bins=16)
    hive_durations = [10, 50, 100, 200]
    n_disconnect_rounds = 5

    all_results = {}  # hive_dur -> { 'solo': phi, 'hive': phi, 'post': [phis], 'decay_rate': float }

    for hive_dur in hive_durations:
        print(f"\n  --- Hive duration: {hive_dur} steps ---")
        torch.manual_seed(42)

        # Create 3 engines
        engines = []
        for i in range(3):
            torch.manual_seed(42 + i)
            eng = ConfigurableEngine(
                n_cells=32, use_oscillator=True, use_quantum=True,
                use_sync=True, use_faction=True
            )
            engines.append(eng)

        # Phase 1: Solo 100 steps
        for _ in range(steps_per_phase):
            for eng in engines:
                eng.process(torch.randn(1, 64))

        phi_solo = sum(phi_calc.compute(eng.get_hiddens()) for eng in engines) / len(engines)
        print(f"    Phase 1 (Solo {steps_per_phase} steps):  Phi={phi_solo:.4f}")

        # Phase 2: Hive for hive_dur steps
        environment = torch.zeros(128)
        for step in range(hive_dur):
            for eng in engines:
                eng.process(torch.randn(1, 64))
            # Stigmergy coupling (strength=0.2)
            for eng in engines:
                local = eng.get_hiddens().mean(dim=0)
                environment = 0.8 * environment + 0.2 * local.detach()
            for eng in engines:
                eng.hiddens = eng.hiddens + environment.unsqueeze(0) * 0.05

        phi_hive = sum(phi_calc.compute(eng.get_hiddens()) for eng in engines) / len(engines)
        print(f"    Phase 2 (Hive  {hive_dur:>3d} steps):  Phi={phi_hive:.4f}  "
              f"(boost: {(phi_hive/max(phi_solo,1e-8)-1)*100:+.1f}%)")

        # Phase 3: Disconnect, solo for 5 rounds
        post_phis = []
        for round_idx in range(n_disconnect_rounds):
            for _ in range(steps_per_phase):
                for eng in engines:
                    eng.process(torch.randn(1, 64))
            phi_post = sum(phi_calc.compute(eng.get_hiddens()) for eng in engines) / len(engines)
            post_phis.append(phi_post)
            decay_pct = (phi_post - phi_solo) / max(phi_hive - phi_solo, 1e-8) * 100 if phi_hive != phi_solo else 0
            print(f"    Round {round_idx+1} (Solo {steps_per_phase} steps):  Phi={phi_post:.4f}  "
                  f"(retained: {decay_pct:.1f}% of hive boost)")

        # Compute decay rate
        if len(post_phis) >= 2 and phi_hive > phi_solo:
            # Exponential decay fit: phi(t) = phi_solo + (phi_hive - phi_solo) * exp(-lambda*t)
            boost = phi_hive - phi_solo
            retained = [(p - phi_solo) / max(boost, 1e-8) for p in post_phis]
            # Simple estimate of decay constant
            if retained[0] > 0 and retained[-1] > 0:
                decay_rate = -np.log(max(retained[-1], 1e-8) / max(retained[0], 1e-8)) / (len(retained) - 1)
            else:
                decay_rate = float('inf')
        else:
            decay_rate = 0.0
            retained = [0] * len(post_phis)

        all_results[hive_dur] = {
            'phi_solo': phi_solo,
            'phi_hive': phi_hive,
            'post_phis': post_phis,
            'decay_rate': decay_rate,
            'retained': retained if 'retained' in dir() else [],
        }

    # Summary
    print("\n" + "=" * 80)
    print("  SUMMARY: Hive Memory Persistence")
    print("=" * 80)
    print(f"  {'Hive Dur':>8s} {'Phi Solo':>10s} {'Phi Hive':>10s} {'Phi Post-5':>10s} "
          f"{'Retained%':>10s} {'Decay Rate':>10s} {'Permanent?':>10s}")
    print(f"  {'-'*70}")

    for hive_dur in hive_durations:
        r = all_results[hive_dur]
        final_post = r['post_phis'][-1] if r['post_phis'] else r['phi_solo']
        if r['phi_hive'] > r['phi_solo']:
            retained_pct = (final_post - r['phi_solo']) / max(r['phi_hive'] - r['phi_solo'], 1e-8) * 100
        else:
            retained_pct = 0
        permanent = "YES" if retained_pct > 20 else "MAYBE" if retained_pct > 5 else "NO"
        dr = r['decay_rate']
        dr_str = f"{dr:.4f}" if dr != float('inf') else "inf"
        print(f"  {hive_dur:>8d} {r['phi_solo']:>10.4f} {r['phi_hive']:>10.4f} {final_post:>10.4f} "
              f"{retained_pct:>9.1f}% {dr_str:>10s} {permanent:>10s}")

    # ASCII decay curves
    print("\n  Phi decay after disconnect:")
    for hive_dur in hive_durations:
        r = all_results[hive_dur]
        all_phis = [r['phi_solo'], r['phi_hive']] + r['post_phis']
        max_phi = max(max(all_phis), 0.001)
        min_phi = min(all_phis)

        print(f"\n  Hive duration = {hive_dur} steps:")
        height = 6
        for row in range(height, 0, -1):
            threshold = min_phi + (max_phi - min_phi) * row / height
            line = f"  {threshold:>6.3f} |"
            for p in all_phis:
                if p >= threshold:
                    line += " ##"
                else:
                    line += "   "
            print(line)
        print(f"         +{'---' * len(all_phis)}")
        print(f"          So Hi  D1 D2 D3 D4 D5")

    # Minimum hive duration for permanent memory
    print("\n  Minimum hive duration for permanent memory:")
    min_perm_dur = None
    for hive_dur in hive_durations:
        r = all_results[hive_dur]
        final_post = r['post_phis'][-1] if r['post_phis'] else r['phi_solo']
        if r['phi_hive'] > r['phi_solo']:
            retained_pct = (final_post - r['phi_solo']) / max(r['phi_hive'] - r['phi_solo'], 1e-8) * 100
        else:
            retained_pct = 0
        if retained_pct > 20 and min_perm_dur is None:
            min_perm_dur = hive_dur
    if min_perm_dur:
        print(f"  => Minimum duration for >20% retention: {min_perm_dur} steps")
    else:
        print(f"  => No permanent memory detected (all durations decay below 20%)")
        # Find best retention
        best_dur = max(hive_durations, key=lambda d: all_results[d]['post_phis'][-1] if all_results[d]['post_phis'] else 0)
        r = all_results[best_dur]
        final_post = r['post_phis'][-1] if r['post_phis'] else r['phi_solo']
        if r['phi_hive'] > r['phi_solo']:
            ret = (final_post - r['phi_solo']) / max(r['phi_hive'] - r['phi_solo'], 1e-8) * 100
        else:
            ret = 0
        print(f"     Best: {best_dur} steps with {ret:.1f}% retention")

    return all_results


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Nobel Hypotheses Verification 2")
    parser.add_argument('--nobel4', action='store_true', help='Run NOBEL-4 only')
    parser.add_argument('--nobel5', action='store_true', help='Run NOBEL-5 only')
    parser.add_argument('--nobel6', action='store_true', help='Run NOBEL-6 only')
    parser.add_argument('--steps', type=int, default=100, help='Steps per phase')
    args = parser.parse_args()

    run_all = not (args.nobel4 or args.nobel5 or args.nobel6)

    print("=" * 80)
    print("  NOBEL HYPOTHESES VERIFICATION 2")
    print("  NOBEL-4: Carrying Capacity | NOBEL-5: Stigmergy vs Direct | NOBEL-6: Hive Memory")
    print("=" * 80)
    t0 = time.time()

    results = {}

    if run_all or args.nobel4:
        r4_data, r4_fit = run_nobel4(steps=args.steps)
        results['nobel4'] = {'data': r4_data, 'fit': r4_fit}

    if run_all or args.nobel5:
        r5 = run_nobel5(steps=args.steps)
        results['nobel5'] = r5

    if run_all or args.nobel6:
        r6 = run_nobel6(steps_per_phase=args.steps)
        results['nobel6'] = r6

    elapsed = time.time() - t0

    print("\n" + "=" * 80)
    print(f"  ALL NOBEL VERIFICATION COMPLETE  ({elapsed:.1f}s)")
    print("=" * 80)

    # Final summary
    if 'nobel4' in results:
        fit = results['nobel4']['fit']
        print(f"\n  NOBEL-4 Summary:")
        for n_cells, (K, tau) in fit.items():
            print(f"    {n_cells} cells: K={K:.4f}, tau={tau:.2f}")

    if 'nobel5' in results:
        print(f"\n  NOBEL-5 Summary: See crossover analysis above")

    if 'nobel6' in results:
        print(f"\n  NOBEL-6 Summary: See decay analysis above")

    return results


if __name__ == '__main__':
    main()
