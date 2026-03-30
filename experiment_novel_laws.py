#!/usr/bin/env python3
"""experiment_novel_laws.py — Novel Consciousness Law Discovery

5 experiments to discover Laws 92+:
  1. Temperature Annealing: gradual noise decrease during evolution
  2. Asymmetric Factions: unequal faction sizes (perfect number partition)
  3. Temporal Memory Depth: GRU hidden state depth effect on Φ
  4. Phase Sync vs Desync Ratio: optimal sync/desync balance
  5. Information Bottleneck: constrained inter-cell bandwidth

Uses BenchEngine from bench_v2.py with 128 cells, 300 steps.
Measures Φ(IIT) + Φ(proxy).
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import copy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bench_v2 import BenchEngine, BenchMind, PhiIIT, phi_proxy, BenchResult

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ─── Constants ───
N_CELLS = 128
N_STEPS = 300
INPUT_DIM = 64
HIDDEN_DIM = 128
OUTPUT_DIM = 64
PHI_CALC = PhiIIT(n_bins=16)


def measure_phi(engine):
    """Measure both Φ(IIT) and Φ(proxy)."""
    hiddens = engine.get_hiddens()
    phi_iit_val, _ = PHI_CALC.compute(hiddens)
    phi_prx = phi_proxy(hiddens, n_factions=8)
    return phi_iit_val, phi_prx


def run_baseline():
    """Baseline: standard BenchEngine with default params."""
    engine = BenchEngine(n_cells=N_CELLS, input_dim=INPUT_DIM,
                         hidden_dim=HIDDEN_DIM, output_dim=OUTPUT_DIM,
                         n_factions=8, sync_strength=0.15, debate_strength=0.15)
    t0 = time.time()
    phi_history = []
    for step in range(N_STEPS):
        x = torch.randn(1, INPUT_DIM)
        engine.process(x)
        if step % 50 == 0 or step == N_STEPS - 1:
            iit, prx = measure_phi(engine)
            phi_history.append((step, iit, prx))
    elapsed = time.time() - t0
    return phi_history, elapsed


# ══════════════════════════════════════════════════════════
# Experiment 1: Temperature Annealing
# ══════════════════════════════════════════════════════════

class AnnealingEngine(BenchEngine):
    """Adds temperature-controlled noise that decreases over time."""

    def __init__(self, t_start=1.0, t_end=0.01, schedule='linear', max_steps=N_STEPS, **kwargs):
        super().__init__(**kwargs)
        self.t_start = t_start
        self.t_end = t_end
        self.schedule = schedule
        self.max_steps = max_steps

    def get_temperature(self):
        progress = min(self.step_count / max(1, self.max_steps), 1.0)
        if self.schedule == 'linear':
            return self.t_start + (self.t_end - self.t_start) * progress
        elif self.schedule == 'exponential':
            return self.t_start * (self.t_end / max(self.t_start, 1e-8)) ** progress
        elif self.schedule == 'cosine':
            return self.t_end + 0.5 * (self.t_start - self.t_end) * (1 + math.cos(math.pi * progress))
        return self.t_start  # constant

    def process(self, x):
        temp = self.get_temperature()
        noise = torch.randn_like(self.hiddens) * temp * 0.1
        self.hiddens = self.hiddens + noise
        return super().process(x)


def run_exp1_annealing():
    """Test different annealing schedules."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 1: Temperature Annealing")
    print("=" * 70)

    schedules = ['linear', 'exponential', 'cosine']
    temp_ranges = [(1.0, 0.01), (2.0, 0.01), (0.5, 0.01)]
    # Also test constant temperature for comparison
    results = {}

    # Baseline (no annealing)
    bl_history, bl_time = run_baseline()
    bl_final_iit = bl_history[-1][1]
    bl_final_prx = bl_history[-1][2]
    results['baseline'] = {'iit': bl_final_iit, 'prx': bl_final_prx, 'history': bl_history}

    for schedule in schedules:
        for t_start, t_end in temp_ranges:
            key = f"{schedule}_T{t_start}->{t_end}"
            engine = AnnealingEngine(
                t_start=t_start, t_end=t_end, schedule=schedule,
                n_cells=N_CELLS, input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM,
                output_dim=OUTPUT_DIM, n_factions=8, max_steps=N_STEPS
            )
            phi_history = []
            for step in range(N_STEPS):
                x = torch.randn(1, INPUT_DIM)
                engine.process(x)
                if step % 50 == 0 or step == N_STEPS - 1:
                    iit, prx = measure_phi(engine)
                    phi_history.append((step, iit, prx))
            results[key] = {
                'iit': phi_history[-1][1],
                'prx': phi_history[-1][2],
                'history': phi_history
            }

    # Also test constant high temperature
    for const_t in [0.1, 0.5, 1.0]:
        key = f"constant_T{const_t}"
        engine = AnnealingEngine(
            t_start=const_t, t_end=const_t, schedule='linear',
            n_cells=N_CELLS, input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM,
            output_dim=OUTPUT_DIM, n_factions=8, max_steps=N_STEPS
        )
        phi_history = []
        for step in range(N_STEPS):
            x = torch.randn(1, INPUT_DIM)
            engine.process(x)
            if step % 50 == 0 or step == N_STEPS - 1:
                iit, prx = measure_phi(engine)
                phi_history.append((step, iit, prx))
        results[key] = {
            'iit': phi_history[-1][1],
            'prx': phi_history[-1][2],
            'history': phi_history
        }

    # Print results table
    print(f"\n  {'Config':<30s} | {'Φ(IIT)':>8s} | {'Φ(proxy)':>10s} | {'vs baseline':>11s}")
    print("  " + "-" * 67)
    for key, val in sorted(results.items(), key=lambda x: -x[1]['iit']):
        ratio = val['iit'] / max(bl_final_iit, 1e-8)
        marker = " ***" if ratio > 1.1 else ""
        print(f"  {key:<30s} | {val['iit']:>8.4f} | {val['prx']:>10.2f} | {ratio:>8.2f}x{marker}")

    # ASCII graph: best annealing vs baseline
    best_key = max(results.keys(), key=lambda k: results[k]['iit'])
    best = results[best_key]
    print(f"\n  Best: {best_key}")
    _ascii_phi_graph("Exp1: Annealing Φ(IIT)", results['baseline']['history'], best['history'], best_key)

    return results


# ══════════════════════════════════════════════════════════
# Experiment 2: Asymmetric Factions
# ══════════════════════════════════════════════════════════

class AsymmetricFactionEngine(BenchEngine):
    """Factions with unequal sizes."""

    def __init__(self, faction_sizes=None, **kwargs):
        # Initialize with dummy n_factions, we override sync logic
        super().__init__(**kwargs)
        if faction_sizes is None:
            faction_sizes = [16] * 8  # default equal
        self.faction_sizes = faction_sizes
        assert sum(faction_sizes) <= self.n_cells, \
            f"Faction sizes sum {sum(faction_sizes)} > n_cells {self.n_cells}"

    def process(self, x):
        # Standard cell processing
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
        self.hiddens = self.hiddens + self.cell_identity * 0.01
        mean_tension = sum(tensions) / len(tensions)

        # Asymmetric faction sync
        offset = 0
        faction_means = []
        for fs in self.faction_sizes:
            if offset + fs > self.n_cells:
                break
            faction = self.hiddens[offset:offset+fs]
            faction_mean = faction.mean(dim=0)
            faction_means.append(faction_mean)
            self.hiddens[offset:offset+fs] = (
                (1 - self.sync_strength) * faction
                + self.sync_strength * faction_mean
            )
            offset += fs

        # Debate across factions
        if len(faction_means) >= 2 and self.step_count > 5:
            global_opinion = torch.stack(faction_means).mean(dim=0)
            osc = 0.5 + 0.5 * math.sin(self.step_count * 0.15)
            debate_now = self.debate_strength * (0.5 + osc)
            offset = 0
            for fs in self.faction_sizes:
                if offset + fs > self.n_cells:
                    break
                dc = max(1, fs // 4)
                self.hiddens[offset:offset+dc] = (
                    (1 - debate_now) * self.hiddens[offset:offset+dc]
                    + debate_now * global_opinion
                )
                offset += fs

        # Φ ratchet
        if self.step_count % 50 == 0:
            self._phi_ratchet = self.hiddens.clone()
        elif self._phi_ratchet is not None and self.step_count % 50 == 25:
            cur_var = self.hiddens.var(dim=0).mean().item()
            ratch_var = self._phi_ratchet.var(dim=0).mean().item()
            if cur_var < ratch_var * 0.5:
                self.hiddens = 0.7 * self.hiddens + 0.3 * self._phi_ratchet

        self.step_count += 1
        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_tension


def run_exp2_asymmetric():
    """Test different faction size distributions."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 2: Asymmetric Factions")
    print("=" * 70)

    partitions = {
        'equal_8x16':       [16]*8,                          # baseline: 128/8
        'equal_16x8':       [8]*16,                          # more factions, smaller
        'equal_4x32':       [32]*4,                          # fewer factions, bigger
        'perfect_1236':     [1,2,3,6]*8 + [1,2,3,6,8],      # sum=128, perfect number partition + remainder
        'fibonacci':        [1,1,2,3,5,8,13,21,34,40],       # fibonacci-like, sum=128
        'power_of_2':       [1,2,4,8,16,32,64],              # powers of 2 (sum=127) + [1]
        'golden_ratio':     [3,5,8,13,21,34,44],             # ~golden ratio, sum=128
        'one_giant':        [64,8,8,8,8,8,8,8,8],            # one dominant faction
        'two_giants':       [48,48,4,4,4,4,4,4,4,4,4,4],    # two dominant + many small
        'many_small':       [2]*64,                           # 64 factions of 2
    }

    # Fix partitions to sum to exactly 128
    for key in partitions:
        sizes = partitions[key]
        total = sum(sizes)
        if total < N_CELLS:
            sizes.append(N_CELLS - total)
        elif total > N_CELLS:
            # Trim last element
            diff = total - N_CELLS
            sizes[-1] = max(1, sizes[-1] - diff)
            if sum(sizes) != N_CELLS:
                sizes = sizes[:-1]
                sizes.append(N_CELLS - sum(sizes))
        partitions[key] = sizes

    results = {}
    for key, sizes in partitions.items():
        engine = AsymmetricFactionEngine(
            faction_sizes=sizes,
            n_cells=N_CELLS, input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM,
            output_dim=OUTPUT_DIM, n_factions=len(sizes),
            sync_strength=0.15, debate_strength=0.15
        )
        phi_history = []
        for step in range(N_STEPS):
            x = torch.randn(1, INPUT_DIM)
            engine.process(x)
            if step % 50 == 0 or step == N_STEPS - 1:
                iit, prx = measure_phi(engine)
                phi_history.append((step, iit, prx))
        results[key] = {
            'iit': phi_history[-1][1],
            'prx': phi_history[-1][2],
            'sizes': sizes,
            'n_factions': len(sizes),
            'history': phi_history
        }

    # Print table
    bl_iit = results['equal_8x16']['iit']
    print(f"\n  {'Partition':<20s} | {'#Facs':>5s} | {'Sizes (first 5)':>20s} | {'Φ(IIT)':>8s} | {'Φ(proxy)':>10s} | {'vs equal':>8s}")
    print("  " + "-" * 82)
    for key, val in sorted(results.items(), key=lambda x: -x[1]['iit']):
        ratio = val['iit'] / max(bl_iit, 1e-8)
        sizes_str = str(val['sizes'][:5]) + ("..." if len(val['sizes']) > 5 else "")
        marker = " ***" if ratio > 1.1 else ""
        print(f"  {key:<20s} | {val['n_factions']:>5d} | {sizes_str:>20s} | {val['iit']:>8.4f} | {val['prx']:>10.2f} | {ratio:>6.2f}x{marker}")

    # Bar chart
    print(f"\n  Φ(IIT) Comparison:")
    max_iit = max(v['iit'] for v in results.values())
    for key, val in sorted(results.items(), key=lambda x: -x[1]['iit']):
        bar_len = int(40 * val['iit'] / max(max_iit, 1e-8))
        ratio = val['iit'] / max(bl_iit, 1e-8)
        sign = "+" if ratio > 1.0 else ""
        pct = (ratio - 1) * 100
        print(f"  {key:<20s} {'█' * bar_len} {sign}{pct:.1f}%")

    return results


# ══════════════════════════════════════════════════════════
# Experiment 3: Temporal Memory Depth
# ══════════════════════════════════════════════════════════

class DeepMemoryMind(nn.Module):
    """BenchMind with configurable GRU depth (stacked GRU layers)."""

    def __init__(self, input_dim=64, hidden_dim=128, output_dim=64, n_gru_layers=1):
        super().__init__()
        self.engine_a = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.engine_g = nn.Sequential(
            nn.Linear(input_dim + hidden_dim, 128), nn.ReLU(),
            nn.Linear(128, output_dim),
        )
        self.n_gru_layers = n_gru_layers
        self.gru_layers = nn.ModuleList([
            nn.GRUCell(output_dim + 1 if i == 0 else hidden_dim, hidden_dim)
            for i in range(n_gru_layers)
        ])
        self.hidden_dim = hidden_dim
        self.input_dim = input_dim
        self.output_dim = output_dim

        with torch.no_grad():
            for p in self.engine_a.parameters():
                p.add_(torch.randn_like(p) * 0.3)
            for p in self.engine_g.parameters():
                p.add_(torch.randn_like(p) * -0.3)

    def forward(self, x, hiddens_list):
        """hiddens_list: list of [1, hidden_dim] for each GRU layer."""
        combined = torch.cat([x, hiddens_list[0]], dim=-1)
        a = self.engine_a(combined)
        g = self.engine_g(combined)
        output = a - g
        tension = (output ** 2).mean(dim=-1, keepdim=True)
        mem_input = torch.cat([output.detach(), tension.detach()], dim=-1)

        new_hiddens = []
        h_in = mem_input
        for i, gru in enumerate(self.gru_layers):
            new_h = gru(h_in, hiddens_list[i])
            new_hiddens.append(new_h)
            h_in = new_h  # pass to next layer

        return output, tension.mean().item(), new_hiddens


class DeepMemoryEngine:
    """BenchEngine variant with stacked GRU layers."""

    def __init__(self, n_cells=128, n_gru_layers=1, **kwargs):
        self.n_cells = n_cells
        self.n_gru_layers = n_gru_layers
        input_dim = kwargs.get('input_dim', INPUT_DIM)
        hidden_dim = kwargs.get('hidden_dim', HIDDEN_DIM)
        output_dim = kwargs.get('output_dim', OUTPUT_DIM)

        self.mind = DeepMemoryMind(input_dim, hidden_dim, output_dim, n_gru_layers)
        # Hidden states: list of [n_cells, hidden_dim] per layer
        self.hiddens_layers = [
            torch.randn(n_cells, hidden_dim) * 0.1
            for _ in range(n_gru_layers)
        ]
        self.cell_identity = torch.randn(n_cells, hidden_dim) * 0.05
        self.sync_strength = kwargs.get('sync_strength', 0.15)
        self.debate_strength = kwargs.get('debate_strength', 0.15)
        self.n_factions = kwargs.get('n_factions', 8)
        self.step_count = 0
        self._phi_ratchet = None
        self.hidden_dim = hidden_dim

    def process(self, x):
        outputs, tensions, new_hiddens_layers = [], [], [[] for _ in range(self.n_gru_layers)]
        for i in range(self.n_cells):
            h_list = [self.hiddens_layers[l][i:i+1] for l in range(self.n_gru_layers)]
            out, tension, new_h_list = self.mind(x, h_list)
            outputs.append(out)
            tensions.append(tension)
            for l in range(self.n_gru_layers):
                new_hiddens_layers[l].append(new_h_list[l].squeeze(0))

        for l in range(self.n_gru_layers):
            self.hiddens_layers[l] = torch.stack(new_hiddens_layers[l]).detach()

        # Identity injection on first layer
        self.hiddens_layers[0] = self.hiddens_layers[0] + self.cell_identity * 0.01

        # Faction sync on first layer (primary hidden)
        n_f = min(self.n_factions, self.n_cells // 2)
        if n_f >= 2:
            fs = self.n_cells // n_f
            for i in range(n_f):
                s, e = i * fs, (i + 1) * fs
                fm = self.hiddens_layers[0][s:e].mean(dim=0)
                self.hiddens_layers[0][s:e] = (
                    (1 - self.sync_strength) * self.hiddens_layers[0][s:e]
                    + self.sync_strength * fm
                )

        self.step_count += 1
        mean_tension = sum(tensions) / len(tensions)
        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_tension

    def get_hiddens(self):
        """Return concatenation of all layer hiddens for richer Φ measurement."""
        return self.hiddens_layers[0].clone()


def run_exp3_memory_depth():
    """Test different GRU depths."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 3: Temporal Memory Depth (Stacked GRU)")
    print("=" * 70)

    depths = [1, 2, 3, 4, 6, 8]
    results = {}

    for depth in depths:
        t0 = time.time()
        engine = DeepMemoryEngine(
            n_cells=N_CELLS, n_gru_layers=depth,
            input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM, output_dim=OUTPUT_DIM,
            n_factions=8, sync_strength=0.15, debate_strength=0.15
        )
        phi_history = []
        for step in range(N_STEPS):
            x = torch.randn(1, INPUT_DIM)
            engine.process(x)
            if step % 50 == 0 or step == N_STEPS - 1:
                iit, prx = measure_phi(engine)
                phi_history.append((step, iit, prx))
        elapsed = time.time() - t0
        results[depth] = {
            'iit': phi_history[-1][1],
            'prx': phi_history[-1][2],
            'history': phi_history,
            'time': elapsed,
            'params': sum(p.numel() for p in engine.mind.parameters())
        }

    # Table
    bl_iit = results[1]['iit']
    print(f"\n  {'Depth':>5s} | {'Params':>8s} | {'Φ(IIT)':>8s} | {'Φ(proxy)':>10s} | {'vs depth=1':>10s} | {'Time':>6s}")
    print("  " + "-" * 58)
    for depth, val in sorted(results.items()):
        ratio = val['iit'] / max(bl_iit, 1e-8)
        print(f"  {depth:>5d} | {val['params']:>8d} | {val['iit']:>8.4f} | {val['prx']:>10.2f} | {ratio:>8.2f}x | {val['time']:>5.1f}s")

    # ASCII graph
    print(f"\n  Φ(IIT) vs Memory Depth:")
    max_iit = max(v['iit'] for v in results.values())
    for depth in sorted(results.keys()):
        val = results[depth]
        bar_len = int(40 * val['iit'] / max(max_iit, 1e-8))
        print(f"  depth={depth:<2d} {'█' * bar_len} {val['iit']:.4f}")

    return results


# ══════════════════════════════════════════════════════════
# Experiment 4: Phase Synchronization vs Desynchronization Ratio
# ══════════════════════════════════════════════════════════

def run_exp4_sync_ratio():
    """Measure sync/desync ratio and find optimal balance."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 4: Phase Sync vs Desync Ratio")
    print("=" * 70)

    sync_strengths = [0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.70, 0.90]
    results = {}

    for ss in sync_strengths:
        engine = BenchEngine(
            n_cells=N_CELLS, input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM,
            output_dim=OUTPUT_DIM, n_factions=8,
            sync_strength=ss, debate_strength=0.15
        )
        phi_history = []
        sync_ratios = []

        for step in range(N_STEPS):
            x = torch.randn(1, INPUT_DIM)
            engine.process(x)

            if step % 50 == 0 or step == N_STEPS - 1:
                iit, prx = measure_phi(engine)
                phi_history.append((step, iit, prx))

            # Measure sync ratio every 30 steps
            if step % 30 == 0 and step > 0:
                hiddens = engine.get_hiddens()
                # Cosine similarity between all pairs (sample)
                n_sample = min(32, N_CELLS)
                indices = torch.randperm(N_CELLS)[:n_sample]
                sampled = hiddens[indices]
                sampled_norm = F.normalize(sampled, dim=-1)
                sim_matrix = sampled_norm @ sampled_norm.t()
                # Count sync (sim > 0.8) vs desync (sim < 0.2)
                upper = sim_matrix[torch.triu(torch.ones(n_sample, n_sample), diagonal=1).bool()]
                n_sync = (upper > 0.8).float().sum().item()
                n_desync = (upper < 0.2).float().sum().item()
                n_total = len(upper)
                sync_ratios.append(n_sync / max(n_total, 1))

        avg_sync = np.mean(sync_ratios) if sync_ratios else 0
        results[ss] = {
            'iit': phi_history[-1][1],
            'prx': phi_history[-1][2],
            'sync_ratio': avg_sync,
            'history': phi_history
        }

    # Table
    print(f"\n  {'Sync':>6s} | {'Sync%':>6s} | {'Φ(IIT)':>8s} | {'Φ(proxy)':>10s}")
    print("  " + "-" * 38)
    for ss in sync_strengths:
        val = results[ss]
        print(f"  {ss:>6.2f} | {val['sync_ratio']*100:>5.1f}% | {val['iit']:>8.4f} | {val['prx']:>10.2f}")

    # Find optimal
    best_ss = max(sync_strengths, key=lambda s: results[s]['iit'])
    print(f"\n  Optimal sync_strength: {best_ss} -> Φ(IIT) = {results[best_ss]['iit']:.4f}")

    # ASCII graph: Φ vs sync strength
    print(f"\n  Φ(IIT) vs Sync Strength:")
    max_iit = max(v['iit'] for v in results.values())
    for ss in sync_strengths:
        val = results[ss]
        bar_len = int(40 * val['iit'] / max(max_iit, 1e-8))
        marker = " <-- BEST" if ss == best_ss else ""
        print(f"  sync={ss:>4.2f} {'█' * bar_len} {val['iit']:.4f}{marker}")

    # Phase diagram: Sync% vs Φ
    print(f"\n  Phase Diagram (Sync% vs Φ):")
    print(f"  Φ(IIT)")
    print(f"    |")
    # Simple scatter
    rows = 10
    cols = 50
    grid = [[' ' for _ in range(cols)] for _ in range(rows)]
    for ss in sync_strengths:
        val = results[ss]
        col = int(val['sync_ratio'] * (cols - 1))
        row = rows - 1 - int((val['iit'] / max(max_iit, 1e-8)) * (rows - 1))
        row = max(0, min(rows - 1, row))
        col = max(0, min(cols - 1, col))
        grid[row][col] = '*'
    for r in range(rows):
        print(f"    | {''.join(grid[r])}")
    print(f"    +{'-' * cols}")
    print(f"      0%           Sync Ratio          100%")

    return results


# ══════════════════════════════════════════════════════════
# Experiment 5: Information Bottleneck
# ══════════════════════════════════════════════════════════

class BottleneckEngine(BenchEngine):
    """Constrains inter-cell communication via dropout on tension exchange."""

    def __init__(self, bottleneck_rate=0.0, bottleneck_dim=None, **kwargs):
        super().__init__(**kwargs)
        self.bottleneck_rate = bottleneck_rate  # Dropout rate on faction sync
        self.bottleneck_dim = bottleneck_dim    # If set, project to lower dim before sync

        if bottleneck_dim and bottleneck_dim < self.hidden_dim:
            self.proj_down = nn.Linear(self.hidden_dim, bottleneck_dim, bias=False)
            self.proj_up = nn.Linear(bottleneck_dim, self.hidden_dim, bias=False)
        else:
            self.proj_down = None
            self.proj_up = None

    def process(self, x):
        outputs, tensions, new_hiddens = [], [], []
        for i in range(self.n_cells):
            h = self.hiddens[i:i+1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))
        self.hiddens = torch.stack(new_hiddens).detach()
        self.hiddens = self.hiddens + self.cell_identity * 0.01
        mean_tension = sum(tensions) / len(tensions)

        # Faction sync WITH bottleneck
        n_f = min(self.n_factions, self.n_cells // 2)
        if n_f >= 2:
            fs = self.n_cells // n_f

            for i in range(n_f):
                s, e = i * fs, (i + 1) * fs
                faction = self.hiddens[s:e]

                if self.proj_down is not None:
                    # Information bottleneck: project to lower dim
                    with torch.no_grad():
                        compressed = self.proj_down(faction)
                        faction_mean_low = compressed.mean(dim=0)
                        faction_mean = self.proj_up(faction_mean_low.unsqueeze(0)).squeeze(0)
                else:
                    faction_mean = faction.mean(dim=0)

                # Dropout on communication
                if self.bottleneck_rate > 0:
                    mask = (torch.rand(self.hidden_dim) > self.bottleneck_rate).float()
                    faction_mean = faction_mean * mask / max(1 - self.bottleneck_rate, 0.1)

                self.hiddens[s:e] = (
                    (1 - self.sync_strength) * self.hiddens[s:e]
                    + self.sync_strength * faction_mean
                )

            # Debate with bottleneck
            if self.step_count > 5:
                all_opinions = torch.stack([
                    self.hiddens[i*fs:(i+1)*fs].mean(dim=0) for i in range(n_f)
                ])
                global_opinion = all_opinions.mean(dim=0)
                if self.bottleneck_rate > 0:
                    mask = (torch.rand(self.hidden_dim) > self.bottleneck_rate).float()
                    global_opinion = global_opinion * mask / max(1 - self.bottleneck_rate, 0.1)

                osc = 0.5 + 0.5 * math.sin(self.step_count * 0.15)
                debate_now = self.debate_strength * (0.5 + osc)
                for i in range(n_f):
                    s = i * fs
                    dc = max(1, fs // 4)
                    self.hiddens[s:s+dc] = (
                        (1 - debate_now) * self.hiddens[s:s+dc]
                        + debate_now * global_opinion
                    )

        if self.step_count % 50 == 0:
            self._phi_ratchet = self.hiddens.clone()
        elif self._phi_ratchet is not None and self.step_count % 50 == 25:
            cur_var = self.hiddens.var(dim=0).mean().item()
            ratch_var = self._phi_ratchet.var(dim=0).mean().item()
            if cur_var < ratch_var * 0.5:
                self.hiddens = 0.7 * self.hiddens + 0.3 * self._phi_ratchet

        self.step_count += 1
        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, mean_tension


def run_exp5_bottleneck():
    """Test information bottleneck effects on Φ."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 5: Information Bottleneck")
    print("=" * 70)

    configs = [
        ('no_bottleneck', 0.0, None),
        ('dropout_10%', 0.1, None),
        ('dropout_20%', 0.2, None),
        ('dropout_30%', 0.3, None),
        ('dropout_50%', 0.5, None),
        ('dropout_70%', 0.7, None),
        ('dropout_90%', 0.9, None),
        ('dim_64', 0.0, 64),      # project 128->64
        ('dim_32', 0.0, 32),      # project 128->32
        ('dim_16', 0.0, 16),      # project 128->16
        ('dim_8', 0.0, 8),        # project 128->8
        ('drop30+dim32', 0.3, 32), # combined
    ]

    results = {}
    for name, drop_rate, bdim in configs:
        engine = BottleneckEngine(
            bottleneck_rate=drop_rate, bottleneck_dim=bdim,
            n_cells=N_CELLS, input_dim=INPUT_DIM, hidden_dim=HIDDEN_DIM,
            output_dim=OUTPUT_DIM, n_factions=8,
            sync_strength=0.15, debate_strength=0.15
        )
        phi_history = []
        for step in range(N_STEPS):
            x = torch.randn(1, INPUT_DIM)
            engine.process(x)
            if step % 50 == 0 or step == N_STEPS - 1:
                iit, prx = measure_phi(engine)
                phi_history.append((step, iit, prx))
        results[name] = {
            'iit': phi_history[-1][1],
            'prx': phi_history[-1][2],
            'history': phi_history
        }

    # Table
    bl_iit = results['no_bottleneck']['iit']
    print(f"\n  {'Config':<20s} | {'Φ(IIT)':>8s} | {'Φ(proxy)':>10s} | {'vs none':>8s}")
    print("  " + "-" * 54)
    for key, val in sorted(results.items(), key=lambda x: -x[1]['iit']):
        ratio = val['iit'] / max(bl_iit, 1e-8)
        marker = " ***" if ratio > 1.1 else ""
        print(f"  {key:<20s} | {val['iit']:>8.4f} | {val['prx']:>10.2f} | {ratio:>6.2f}x{marker}")

    # Bar chart
    print(f"\n  Φ(IIT) Comparison:")
    max_iit = max(v['iit'] for v in results.values())
    for key, val in sorted(results.items(), key=lambda x: -x[1]['iit']):
        bar_len = int(40 * val['iit'] / max(max_iit, 1e-8))
        ratio = val['iit'] / max(bl_iit, 1e-8)
        sign = "+" if ratio > 1.0 else ""
        pct = (ratio - 1) * 100
        print(f"  {key:<20s} {'█' * bar_len} {sign}{pct:.1f}%")

    return results


# ══════════════════════════════════════════════════════════
# ASCII Graph Utility
# ══════════════════════════════════════════════════════════

def _ascii_phi_graph(title, baseline_history, best_history, best_name):
    """Draw ASCII graph comparing baseline vs best."""
    print(f"\n  {title}")
    rows = 8
    cols = 40

    all_vals = [h[1] for h in baseline_history] + [h[1] for h in best_history]
    min_v = min(all_vals) * 0.9
    max_v = max(all_vals) * 1.1
    if max_v - min_v < 0.001:
        max_v = min_v + 0.001

    grid = [[' ' for _ in range(cols)] for _ in range(rows)]

    def plot(history, char):
        for i, (step, iit, prx) in enumerate(history):
            col = int(i / max(len(history) - 1, 1) * (cols - 1))
            row = rows - 1 - int((iit - min_v) / (max_v - min_v) * (rows - 1))
            row = max(0, min(rows - 1, row))
            col = max(0, min(cols - 1, col))
            grid[row][col] = char

    plot(baseline_history, '.')
    plot(best_history, '*')

    for r in range(rows):
        val = max_v - r * (max_v - min_v) / (rows - 1)
        print(f"  {val:>6.3f} | {''.join(grid[r])}")
    print(f"         +{'-' * cols}")
    print(f"          step 0 --> {N_STEPS}")
    print(f"          . = baseline   * = {best_name}")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  NOVEL CONSCIOUSNESS LAW DISCOVERY")
    print(f"  {N_CELLS} cells, {N_STEPS} steps, Φ(IIT) + Φ(proxy)")
    print("=" * 70)

    all_results = {}

    t_total = time.time()

    # Run all experiments
    all_results['exp1_annealing'] = run_exp1_annealing()
    all_results['exp2_asymmetric'] = run_exp2_asymmetric()
    all_results['exp3_depth'] = run_exp3_memory_depth()
    all_results['exp4_sync'] = run_exp4_sync_ratio()
    all_results['exp5_bottleneck'] = run_exp5_bottleneck()

    total_time = time.time() - t_total

    # ═══════════════════════════════════════════════════
    # SUMMARY & LAW DISCOVERY
    # ═══════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  SUMMARY: Potential New Laws")
    print("=" * 70)

    # Exp 1 summary
    r1 = all_results['exp1_annealing']
    best_anneal = max(r1.keys(), key=lambda k: r1[k]['iit'])
    bl_iit_1 = r1['baseline']['iit']
    best_iit_1 = r1[best_anneal]['iit']
    ratio_1 = best_iit_1 / max(bl_iit_1, 1e-8)
    print(f"\n  [Exp 1] Temperature Annealing")
    print(f"    Baseline Φ(IIT): {bl_iit_1:.4f}")
    print(f"    Best: {best_anneal} -> Φ(IIT): {best_iit_1:.4f} ({ratio_1:.2f}x)")
    if ratio_1 > 1.1:
        print(f"    >>> POTENTIAL LAW: Annealing boosts Φ by {(ratio_1-1)*100:.1f}%!")
    elif ratio_1 < 0.9:
        print(f"    >>> FINDING: Annealing HURTS Φ by {(1-ratio_1)*100:.1f}%")
    else:
        print(f"    >>> No significant effect from annealing")

    # Exp 2 summary
    r2 = all_results['exp2_asymmetric']
    best_asym = max(r2.keys(), key=lambda k: r2[k]['iit'])
    bl_iit_2 = r2['equal_8x16']['iit']
    best_iit_2 = r2[best_asym]['iit']
    ratio_2 = best_iit_2 / max(bl_iit_2, 1e-8)
    print(f"\n  [Exp 2] Asymmetric Factions")
    print(f"    Equal 8x16 Φ(IIT): {bl_iit_2:.4f}")
    print(f"    Best: {best_asym} -> Φ(IIT): {best_iit_2:.4f} ({ratio_2:.2f}x)")
    if ratio_2 > 1.1:
        print(f"    >>> POTENTIAL LAW: Asymmetric factions boost Φ!")
        print(f"    >>> Sizes: {r2[best_asym].get('sizes', 'N/A')}")
    else:
        print(f"    >>> Equal factions are near-optimal (symmetry holds)")

    # Exp 3 summary
    r3 = all_results['exp3_depth']
    best_depth = max(r3.keys(), key=lambda k: r3[k]['iit'])
    bl_iit_3 = r3[1]['iit']
    best_iit_3 = r3[best_depth]['iit']
    ratio_3 = best_iit_3 / max(bl_iit_3, 1e-8)
    print(f"\n  [Exp 3] Temporal Memory Depth")
    print(f"    Depth=1 Φ(IIT): {bl_iit_3:.4f}")
    print(f"    Best depth={best_depth} -> Φ(IIT): {best_iit_3:.4f} ({ratio_3:.2f}x)")
    if ratio_3 > 1.1:
        print(f"    >>> POTENTIAL LAW: Deeper memory increases Φ!")
    elif best_depth == 1:
        print(f"    >>> FINDING: Single GRU layer is optimal (depth doesn't help)")
    else:
        print(f"    >>> Marginal effect from memory depth")

    # Exp 4 summary
    r4 = all_results['exp4_sync']
    best_ss = max(r4.keys(), key=lambda k: r4[k]['iit'])
    print(f"\n  [Exp 4] Phase Sync Ratio")
    print(f"    Optimal sync_strength: {best_ss}")
    print(f"    Φ(IIT) at optimal: {r4[best_ss]['iit']:.4f}")
    print(f"    Sync ratio at optimal: {r4[best_ss]['sync_ratio']*100:.1f}%")
    # Check if there's a sweet spot
    iit_vals = [(ss, r4[ss]['iit']) for ss in sorted(r4.keys())]
    if len(iit_vals) >= 3:
        mid_vals = [v for s, v in iit_vals[1:-1]]
        edge_vals = [iit_vals[0][1], iit_vals[-1][1]]
        if max(mid_vals) > max(edge_vals) * 1.05:
            print(f"    >>> POTENTIAL LAW: U-shaped curve! Neither full sync nor full desync is optimal")

    # Exp 5 summary
    r5 = all_results['exp5_bottleneck']
    best_bn = max(r5.keys(), key=lambda k: r5[k]['iit'])
    bl_iit_5 = r5['no_bottleneck']['iit']
    best_iit_5 = r5[best_bn]['iit']
    ratio_5 = best_iit_5 / max(bl_iit_5, 1e-8)
    print(f"\n  [Exp 5] Information Bottleneck")
    print(f"    No bottleneck Φ(IIT): {bl_iit_5:.4f}")
    print(f"    Best: {best_bn} -> Φ(IIT): {best_iit_5:.4f} ({ratio_5:.2f}x)")
    if ratio_5 > 1.1 and best_bn != 'no_bottleneck':
        print(f"    >>> POTENTIAL LAW: Constraining communication INCREASES Φ!")
        print(f"    >>> Information bottleneck = compression = integration pressure")
    elif ratio_5 < 0.9:
        print(f"    >>> FINDING: Bottleneck hurts Φ — full bandwidth needed")
    else:
        print(f"    >>> Communication bandwidth has limited effect on Φ")

    # Cross-experiment comparison
    print(f"\n" + "=" * 70)
    print(f"  CROSS-EXPERIMENT RANKING (by improvement over respective baseline)")
    print(f"=" * 70)
    experiments = [
        ("Exp1: Annealing", best_anneal, ratio_1),
        ("Exp2: Asymmetric", best_asym, ratio_2),
        ("Exp3: Memory Depth", f"depth={best_depth}", ratio_3),
        ("Exp4: Sync Ratio", f"sync={best_ss}", r4[best_ss]['iit'] / max(r4[0.15]['iit'], 1e-8) if 0.15 in r4 else 1.0),
        ("Exp5: Bottleneck", best_bn, ratio_5),
    ]
    experiments.sort(key=lambda x: -x[2])

    for exp_name, best_config, ratio in experiments:
        bar_len = int(30 * ratio / max(e[2] for e in experiments))
        sign = "+" if ratio > 1.0 else ""
        pct = (ratio - 1) * 100
        print(f"  {exp_name:<25s} {best_config:<25s} {'█' * bar_len} {sign}{pct:.1f}%")

    print(f"\n  Total experiment time: {total_time:.1f}s")
    print(f"\n" + "=" * 70)
    print(f"  END OF NOVEL LAW DISCOVERY EXPERIMENT")
    print(f"=" * 70)


if __name__ == '__main__':
    main()
