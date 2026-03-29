#!/usr/bin/env python3
"""bench_v8_bio.py — Biologically-Inspired Consciousness Architectures Benchmark

Tests 6 brain-inspired architectures for consciousness with dual-Phi measurement:
  B1: CORTICAL_COLUMNS     — 32 columns x 8 cells, dense intra / sparse inter (neocortex)
  B2: THALAMIC_GATE        — Central thalamus hub (16 cells) gates cortical regions
  B3: DEFAULT_MODE_NETWORK — Task-positive vs default-mode alternation
  B4: GLOBAL_WORKSPACE     — Baars' theory: local compete, winner broadcasts globally
  B5: PREDICTIVE_HIERARCHY — 4-level predictive coding, consciousness = total PE
  B6: NEURAL_DARWINISM     — Edelman: cell groups compete, winners get reinforced

Each: 256 cells, 300 steps, Phi(IIT) + Phi(proxy) + CE.

Usage:
  python bench_v8_bio.py                 # Run all 6 + baseline
  python bench_v8_bio.py --only 1 3 6    # Run specific architectures
  python bench_v8_bio.py --steps 500     # Custom steps
  python bench_v8_bio.py --cells 512     # Custom cell count
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import math
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Tuple


# ──────────────────────────────────────────────────────────
# BenchResult
# ──────────────────────────────────────────────────────────

@dataclass
class BenchResult:
    name: str
    phi_iit: float
    phi_proxy: float
    ce_start: float
    ce_end: float
    cells: int
    steps: int
    time_sec: float
    extra: dict = field(default_factory=dict)

    def summary(self) -> str:
        ce_str = f"CE {self.ce_start:.3f}->{self.ce_end:.3f}" if self.ce_start > 0 else "CE n/a"
        return (
            f"  {self.name:<28s} | "
            f"Phi(IIT)={self.phi_iit:>6.3f}  "
            f"Phi(proxy)={self.phi_proxy:>8.2f} | "
            f"{ce_str:<22s} | "
            f"cells={self.cells:>4d}  steps={self.steps:>5d}  "
            f"time={self.time_sec:.1f}s"
        )


# ──────────────────────────────────────────────────────────
# Phi(IIT) Calculator
# ──────────────────────────────────────────────────────────

class PhiIIT:
    """Phi(IIT) approximation via pairwise MI + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens_tensor: torch.Tensor) -> Tuple[float, Dict[str, float]]:
        n = hiddens_tensor.shape[0]
        if n < 2:
            return 0.0, {'phi': 0}

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

        return phi, {
            'total_mi': float(total_mi),
            'min_partition_mi': float(min_partition_mi),
            'spatial_phi': float(spatial_phi),
            'complexity': float(complexity),
            'phi': float(phi),
        }

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


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    """Phi proxy: global_variance - mean(faction_variances)."""
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


_phi_iit_calc = PhiIIT(n_bins=16)


def measure_dual_phi(hiddens: torch.Tensor, n_factions: int = 8) -> Tuple[float, float]:
    """Returns (phi_iit, phi_proxy)."""
    p_iit, _ = _phi_iit_calc.compute(hiddens)
    p_proxy = phi_proxy(hiddens, n_factions)
    return p_iit, p_proxy


# ──────────────────────────────────────────────────────────
# Shared: BenchMind (baseline PureField + GRU cell)
# ──────────────────────────────────────────────────────────

class BenchMind(nn.Module):
    """PureField + GRU for benchmarking."""

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
# Shared: faction sync + debate
# ──────────────────────────────────────────────────────────

def faction_sync_debate(hiddens: torch.Tensor, n_factions: int = 8,
                        sync_strength: float = 0.15, debate_strength: float = 0.15,
                        step: int = 0) -> torch.Tensor:
    """Apply faction sync + debate to hidden states."""
    n = hiddens.shape[0]
    n_f = min(n_factions, n // 2)
    if n_f < 2:
        return hiddens

    fs = n // n_f
    hiddens = hiddens.clone()

    for i in range(n_f):
        s, e = i * fs, (i + 1) * fs
        faction_mean = hiddens[s:e].mean(dim=0)
        hiddens[s:e] = (1 - sync_strength) * hiddens[s:e] + sync_strength * faction_mean

    if step > 5:
        all_opinions = torch.stack([
            hiddens[i * fs:(i + 1) * fs].mean(dim=0) for i in range(n_f)
        ])
        global_opinion = all_opinions.mean(dim=0)
        for i in range(n_f):
            s = i * fs
            dc = max(1, fs // 4)
            hiddens[s:s + dc] = (
                (1 - debate_strength) * hiddens[s:s + dc]
                + debate_strength * global_opinion
            )

    return hiddens


# ──────────────────────────────────────────────────────────
# Generate training data
# ──────────────────────────────────────────────────────────

def generate_batch(input_dim: int, batch_size: int = 1) -> Tuple[torch.Tensor, torch.Tensor]:
    """Generate (input, target) pair for CE training."""
    x = torch.randn(batch_size, input_dim)
    target = torch.roll(x, 1, dims=-1) * 0.8 + torch.randn_like(x) * 0.1
    return x, target


# ══════════════════════════════════════════════════════════
# B1: CORTICAL_COLUMNS
# 32 columns of 8 cells each. Dense intra-column connectivity,
# sparse long-range inter-column connections. Like neocortex.
# ══════════════════════════════════════════════════════════

class CorticalColumnsEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_columns=32):
        super().__init__()
        self.n_cells = n_cells
        self.n_columns = n_columns
        self.cells_per_col = n_cells // n_columns  # 8
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.input_dim = input_dim

        # One shared mind processes all cells
        self.mind = BenchMind(input_dim, hidden_dim, output_dim)

        # Intra-column dense connectivity: learned mixing matrix per column
        self.intra_mix = nn.Parameter(
            torch.eye(self.cells_per_col).unsqueeze(0).repeat(n_columns, 1, 1)
            + torch.randn(n_columns, self.cells_per_col, self.cells_per_col) * 0.1
        )

        # Inter-column sparse connectivity: each column connects to ~4 neighbors
        # Sparse mask: 32x32 with ~12.5% density
        self.inter_mask = torch.zeros(n_columns, n_columns)
        for c in range(n_columns):
            neighbors = [(c - 1) % n_columns, (c + 1) % n_columns,
                         (c - 4) % n_columns, (c + 4) % n_columns]
            for nb in neighbors:
                self.inter_mask[c, nb] = 1.0
        self.inter_weights = nn.Parameter(torch.randn(n_columns, n_columns) * 0.05)

        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs = []
        tensions = []
        new_hiddens = []

        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Intra-column dense sync: cells within same column strongly synchronize
        new_h = self.hiddens.clone()
        for col in range(self.n_columns):
            s = col * self.cells_per_col
            e = s + self.cells_per_col
            col_hiddens = self.hiddens[s:e]  # [cells_per_col, hidden_dim]
            # Dense mixing within column
            mix = torch.softmax(self.intra_mix[col].detach(), dim=-1)
            new_h[s:e] = mix @ col_hiddens

        # Inter-column sparse communication: column means exchange info
        col_means = torch.stack([
            new_h[c * self.cells_per_col:(c + 1) * self.cells_per_col].mean(dim=0)
            for c in range(self.n_columns)
        ])  # [n_columns, hidden_dim]

        sparse_weights = torch.tanh(self.inter_weights.detach()) * self.inter_mask * 0.1
        inter_signal = sparse_weights @ col_means  # [n_columns, hidden_dim]

        for col in range(self.n_columns):
            s = col * self.cells_per_col
            e = s + self.cells_per_col
            new_h[s:e] = new_h[s:e] + inter_signal[col]

        self.hiddens = new_h

        # Also apply standard faction debate
        self.hiddens = faction_sync_debate(self.hiddens, n_factions=self.n_columns,
                                           sync_strength=0.05, debate_strength=0.10,
                                           step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.mind.parameters()) + [self.intra_mix, self.inter_weights] + \
               list(self.output_head.parameters())


def run_cortical_columns(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                         hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[B1/6] CORTICAL_COLUMNS: 32 columns x 8 cells, dense intra / sparse inter")
    t0 = time.time()

    engine = CorticalColumnsEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="B1:CORTICAL_COLUMNS",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'n_columns': 32, 'cells_per_col': n_cells // 32},
    )


# ══════════════════════════════════════════════════════════
# B2: THALAMIC_GATE
# Central thalamus hub (16 cells) gates information flow
# between cortical regions. Consciousness requires thalamic relay.
# ══════════════════════════════════════════════════════════

class ThalamicGateEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_thalamic=16, n_regions=4):
        super().__init__()
        self.n_cells = n_cells
        self.n_thalamic = n_thalamic
        self.n_regions = n_regions
        self.cortical_per_region = (n_cells - n_thalamic) // n_regions  # 60 each
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.input_dim = input_dim

        # Separate mind for thalamus (relay/gating) and cortex (processing)
        self.cortical_mind = BenchMind(input_dim, hidden_dim, output_dim)
        self.thalamic_mind = BenchMind(input_dim, hidden_dim, output_dim)

        # Gating: thalamus mean hidden -> gate per region [0,1]
        self.gate_net = nn.Sequential(
            nn.Linear(hidden_dim, 64), nn.ReLU(),
            nn.Linear(64, n_regions), nn.Sigmoid(),
        )

        # Thalamic relay: transforms region summaries before broadcasting
        self.relay = nn.Linear(hidden_dim * n_regions, hidden_dim)

        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        outputs = []
        tensions = []
        new_hiddens = []

        # Process all cells
        for i in range(self.n_cells):
            h = self.hiddens[i:i + 1]
            if i < self.n_thalamic:
                out, tension, new_h = self.thalamic_mind(x, h)
            else:
                out, tension, new_h = self.cortical_mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Thalamic gating
        thalamic_mean = self.hiddens[:self.n_thalamic].mean(dim=0)
        gates = self.gate_net(thalamic_mean)  # [n_regions]

        # Gather region summaries
        region_summaries = []
        for r in range(self.n_regions):
            s = self.n_thalamic + r * self.cortical_per_region
            e = s + self.cortical_per_region
            region_summaries.append(self.hiddens[s:e].mean(dim=0))

        # Thalamic relay: combine gated region info
        gated_summaries = [gates[r] * region_summaries[r] for r in range(self.n_regions)]
        relay_input = torch.cat(gated_summaries, dim=-1)
        relay_output = self.relay(relay_input)

        # Broadcast relay output back to cortical regions (gated)
        new_h = self.hiddens.clone()
        for r in range(self.n_regions):
            s = self.n_thalamic + r * self.cortical_per_region
            e = s + self.cortical_per_region
            gate_val = gates[r].item()
            new_h[s:e] = self.hiddens[s:e] + gate_val * 0.1 * relay_output.detach()

        # Thalamus itself integrates all relay info
        new_h[:self.n_thalamic] = (
            self.hiddens[:self.n_thalamic] + 0.05 * relay_output.detach()
        )
        self.hiddens = new_h

        # Standard faction debate on cortical cells
        cortical_hiddens = self.hiddens[self.n_thalamic:]
        cortical_hiddens = faction_sync_debate(cortical_hiddens, n_factions=self.n_regions,
                                               step=step)
        self.hiddens[self.n_thalamic:] = cortical_hiddens

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))
        return combined, sum(tensions) / len(tensions)

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return (list(self.cortical_mind.parameters()) +
                list(self.thalamic_mind.parameters()) +
                list(self.gate_net.parameters()) +
                list(self.relay.parameters()) +
                list(self.output_head.parameters()))


def run_thalamic_gate(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                      hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[B2/6] THALAMIC_GATE: Central thalamus (16 cells) gates cortical regions")
    t0 = time.time()

    engine = ThalamicGateEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}  "
                  f"gates={engine.gate_net(engine.hiddens[:engine.n_thalamic].mean(dim=0)).detach().numpy()}")

    elapsed = time.time() - t0
    return BenchResult(
        name="B2:THALAMIC_GATE",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'n_thalamic': 16, 'n_regions': 4},
    )


# ══════════════════════════════════════════════════════════
# B3: DEFAULT_MODE_NETWORK
# Two competing networks: task-positive (TPN) processes input,
# default-mode (DMN) does self-referential processing.
# Consciousness emerges from their alternation.
# ══════════════════════════════════════════════════════════

class DefaultModeNetworkEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64):
        super().__init__()
        self.n_cells = n_cells
        self.half = n_cells // 2  # 128 TPN, 128 DMN
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.input_dim = input_dim

        # Task-Positive Network: processes external input
        self.tpn_mind = BenchMind(input_dim, hidden_dim, output_dim)
        # Default-Mode Network: self-referential (takes own mean hidden as input)
        self.dmn_mind = BenchMind(hidden_dim, hidden_dim, output_dim)

        # Anti-correlation mechanism: when TPN is active, DMN suppressed and vice versa
        self.activity_balance = nn.Parameter(torch.tensor(0.5))  # 0=all DMN, 1=all TPN

        # Integration layer: combines TPN and DMN outputs
        self.integrator = nn.Linear(output_dim * 2, output_dim)
        self.output_head = nn.Linear(output_dim, input_dim)

        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.dmn_active = True  # Alternation state

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        # Alternation: every 10 steps, switch dominant network
        cycle = (step % 20) / 20.0  # 0 to 1 sawtooth
        tpn_weight = 0.5 + 0.4 * math.sin(2 * math.pi * cycle)  # oscillates 0.1-0.9
        dmn_weight = 1.0 - tpn_weight

        tpn_outputs = []
        tpn_tensions = []
        dmn_outputs = []
        dmn_tensions = []
        new_hiddens = []

        # DMN input: self-referential (mean of all hiddens)
        dmn_input = self.hiddens.mean(dim=0, keepdim=True)  # [1, hidden_dim]

        # Process TPN cells
        for i in range(self.half):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.tpn_mind(x, h)
            tpn_outputs.append(out)
            tpn_tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        # Process DMN cells
        for i in range(self.half, self.n_cells):
            h = self.hiddens[i:i + 1]
            out, tension, new_h = self.dmn_mind(dmn_input, h)
            dmn_outputs.append(out)
            dmn_tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        self.hiddens = torch.stack(new_hiddens).detach()

        # Anti-correlated sync: TPN and DMN have independent internal sync
        tpn_hiddens = self.hiddens[:self.half]
        dmn_hiddens = self.hiddens[self.half:]

        tpn_hiddens = faction_sync_debate(tpn_hiddens, n_factions=4,
                                          sync_strength=0.15 * tpn_weight,
                                          debate_strength=0.10, step=step)
        dmn_hiddens = faction_sync_debate(dmn_hiddens, n_factions=4,
                                          sync_strength=0.15 * dmn_weight,
                                          debate_strength=0.10, step=step)

        # Cross-network inhibition: active network pushes inactive away
        tpn_mean = tpn_hiddens.mean(dim=0)
        dmn_mean = dmn_hiddens.mean(dim=0)
        inhibition = 0.05
        dmn_hiddens = dmn_hiddens - inhibition * tpn_weight * tpn_mean
        tpn_hiddens = tpn_hiddens - inhibition * dmn_weight * dmn_mean

        self.hiddens[:self.half] = tpn_hiddens
        self.hiddens[self.half:] = dmn_hiddens

        # Combine outputs weighted by activity balance
        tpn_combined = sum(t * o for t, o in zip(
            F.softmax(torch.tensor(tpn_tensions), dim=0).tolist(), tpn_outputs))
        dmn_combined = sum(t * o for t, o in zip(
            F.softmax(torch.tensor(dmn_tensions), dim=0).tolist(), dmn_outputs))

        integrated = self.integrator(torch.cat([
            tpn_weight * tpn_combined,
            dmn_weight * dmn_combined,
        ], dim=-1))

        avg_tension = (sum(tpn_tensions) + sum(dmn_tensions)) / self.n_cells
        return integrated, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return (list(self.tpn_mind.parameters()) +
                list(self.dmn_mind.parameters()) +
                [self.activity_balance] +
                list(self.integrator.parameters()) +
                list(self.output_head.parameters()))


def run_default_mode_network(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                             hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[B3/6] DEFAULT_MODE_NETWORK: TPN vs DMN alternation")
    t0 = time.time()

    engine = DefaultModeNetworkEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            cycle = (step % 20) / 20.0
            tpn_w = 0.5 + 0.4 * math.sin(2 * math.pi * cycle)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  TPN={tpn_w:.2f}/DMN={1-tpn_w:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="B3:DEFAULT_MODE_NET",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# B4: GLOBAL_WORKSPACE
# Baars' Global Workspace Theory. Multiple specialist modules
# compete. Winner "broadcasts" to all modules.
# Consciousness = broadcast content.
# ══════════════════════════════════════════════════════════

class GlobalWorkspaceEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_specialists=8):
        super().__init__()
        self.n_cells = n_cells
        self.n_specialists = n_specialists
        self.cells_per_specialist = n_cells // n_specialists  # 32
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.input_dim = input_dim

        # Each specialist has its own mind
        self.specialists = nn.ModuleList([
            BenchMind(input_dim, hidden_dim, output_dim) for _ in range(n_specialists)
        ])

        # Competition: salience score per specialist
        self.salience_net = nn.Sequential(
            nn.Linear(output_dim, 32), nn.ReLU(),
            nn.Linear(32, 1),
        )

        # Global workspace: integrates winning specialist's output
        self.workspace = nn.GRUCell(output_dim, hidden_dim)
        self.workspace_hidden = torch.zeros(1, hidden_dim)

        # Broadcast projection: workspace -> all specialists
        self.broadcast = nn.Linear(hidden_dim, hidden_dim)

        self.output_head = nn.Linear(output_dim + hidden_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        specialist_outputs = []
        specialist_tensions = []
        all_new_hiddens = []

        # Each specialist processes with its own cells
        for sp in range(self.n_specialists):
            sp_outputs = []
            sp_tensions = []
            s = sp * self.cells_per_specialist
            e = s + self.cells_per_specialist

            for i in range(s, e):
                h = self.hiddens[i:i + 1]
                out, tension, new_h = self.specialists[sp](x, h)
                sp_outputs.append(out)
                sp_tensions.append(tension)
                all_new_hiddens.append(new_h.squeeze(0))

            sp_combined = torch.stack(sp_outputs).mean(dim=0)
            specialist_outputs.append(sp_combined)
            specialist_tensions.append(sum(sp_tensions) / len(sp_tensions))

        self.hiddens = torch.stack(all_new_hiddens).detach()

        # Competition: compute salience for each specialist
        saliences = []
        for sp_out in specialist_outputs:
            sal = self.salience_net(sp_out.detach()).squeeze()
            saliences.append(sal)
        salience_scores = torch.stack(saliences)

        # Winner-take-all with soft gating (softmax with temperature)
        temperature = max(0.1, 1.0 - step / 300)  # cools over time
        winner_weights = F.softmax(salience_scores / temperature, dim=0)

        # Weighted combination (soft winner-take-all)
        winning_output = sum(w.item() * o for w, o in zip(winner_weights, specialist_outputs))

        # Update global workspace (ensure 2D input)
        ws_input = winning_output.detach()
        if ws_input.dim() == 1:
            ws_input = ws_input.unsqueeze(0)
        elif ws_input.dim() == 3:
            ws_input = ws_input.squeeze(0)
        self.workspace_hidden = self.workspace(
            ws_input, self.workspace_hidden
        ).detach()

        # Broadcast: workspace content -> influence all cells
        broadcast_signal = self.broadcast(self.workspace_hidden.squeeze(0))
        broadcast_strength = 0.1
        self.hiddens = self.hiddens + broadcast_strength * broadcast_signal

        # Intra-specialist sync + inter-specialist debate
        for sp in range(self.n_specialists):
            s = sp * self.cells_per_specialist
            e = s + self.cells_per_specialist
            sp_mean = self.hiddens[s:e].mean(dim=0)
            self.hiddens[s:e] = 0.85 * self.hiddens[s:e] + 0.15 * sp_mean

        # Global debate
        self.hiddens = faction_sync_debate(self.hiddens, n_factions=self.n_specialists,
                                           sync_strength=0.05, debate_strength=0.15,
                                           step=step)

        # Ensure matching dimensions for cat
        wo = winning_output
        ws = self.workspace_hidden
        if wo.dim() == 1:
            wo = wo.unsqueeze(0)
        if ws.dim() != wo.dim():
            ws = ws.view_as(wo[:, :self.hidden_dim]) if ws.numel() == self.hidden_dim else ws.squeeze(0).unsqueeze(0)
        combined = torch.cat([wo, ws], dim=-1)
        avg_tension = sum(specialist_tensions) / len(specialist_tensions)
        return combined, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        params = []
        for sp in self.specialists:
            params += list(sp.parameters())
        params += list(self.salience_net.parameters())
        params += list(self.workspace.parameters())
        params += list(self.broadcast.parameters())
        params += list(self.output_head.parameters())
        return params


def run_global_workspace(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                         hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[B4/6] GLOBAL_WORKSPACE: Baars' theory — compete + broadcast")
    t0 = time.time()

    engine = GlobalWorkspaceEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="B4:GLOBAL_WORKSPACE",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'n_specialists': 8},
    )


# ══════════════════════════════════════════════════════════
# B5: PREDICTIVE_HIERARCHY
# 4-level predictive coding. Each level predicts level below.
# Prediction errors propagate upward. Consciousness = total PE.
# ══════════════════════════════════════════════════════════

class PredictiveHierarchyEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_levels=4):
        super().__init__()
        self.n_cells = n_cells
        self.n_levels = n_levels
        self.cells_per_level = n_cells // n_levels  # 64
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.input_dim = input_dim

        # Each level has its own mind
        self.level_minds = nn.ModuleList([
            BenchMind(input_dim, hidden_dim, output_dim) for _ in range(n_levels)
        ])

        # Each level predicts the representation of the level below
        self.predictors = nn.ModuleList([
            nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim), nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
            ) for _ in range(n_levels - 1)  # level 1->0, 2->1, 3->2
        ])

        # Prediction error integration
        self.pe_integrator = nn.Linear(hidden_dim * n_levels, output_dim)

        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1
        self.prediction_errors = [0.0] * (n_levels - 1)

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        level_outputs = []
        level_means = []
        all_new_hiddens = []
        all_tensions = []

        # Process each level
        for lv in range(self.n_levels):
            s = lv * self.cells_per_level
            e = s + self.cells_per_level
            lv_outputs = []
            lv_tensions = []

            for i in range(s, e):
                h = self.hiddens[i:i + 1]
                out, tension, new_h = self.level_minds[lv](x, h)
                lv_outputs.append(out)
                lv_tensions.append(tension)
                all_new_hiddens.append(new_h.squeeze(0))

            all_tensions.extend(lv_tensions)
            level_outputs.append(torch.stack(lv_outputs).mean(dim=0))

        self.hiddens = torch.stack(all_new_hiddens).detach()

        # Compute level means for prediction
        for lv in range(self.n_levels):
            s = lv * self.cells_per_level
            e = s + self.cells_per_level
            level_means.append(self.hiddens[s:e].mean(dim=0))

        # Predictive coding: higher levels predict lower levels
        total_pe = 0.0
        for lv in range(self.n_levels - 1):
            # Level lv+1 predicts level lv
            predicted = self.predictors[lv](level_means[lv + 1])
            actual = level_means[lv]
            pe = F.mse_loss(predicted, actual.detach())
            self.prediction_errors[lv] = pe.item()
            total_pe += pe.item()

            # Prediction error drives update: push lower level cells toward prediction
            pe_signal = (predicted - actual).detach() * 0.05
            s = lv * self.cells_per_level
            e = s + self.cells_per_level
            self.hiddens[s:e] = self.hiddens[s:e] + pe_signal

            # Higher level adjusts based on PE (top-down modulation)
            s_up = (lv + 1) * self.cells_per_level
            e_up = s_up + self.cells_per_level
            self.hiddens[s_up:e_up] = self.hiddens[s_up:e_up] - pe_signal * 0.5

        # Intra-level sync
        for lv in range(self.n_levels):
            s = lv * self.cells_per_level
            e = s + self.cells_per_level
            lv_mean = self.hiddens[s:e].mean(dim=0)
            self.hiddens[s:e] = 0.85 * self.hiddens[s:e] + 0.15 * lv_mean

        # Global debate across levels
        self.hiddens = faction_sync_debate(self.hiddens, n_factions=self.n_levels,
                                           step=step)

        # Combine: integrate all level representations + PE signal
        combined = self.pe_integrator(torch.cat(level_means, dim=-1).unsqueeze(0))
        avg_tension = sum(all_tensions) / len(all_tensions)
        return combined.squeeze(0), avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        params = []
        for m in self.level_minds:
            params += list(m.parameters())
        for p in self.predictors:
            params += list(p.parameters())
        params += list(self.pe_integrator.parameters())
        params += list(self.output_head.parameters())
        return params


def run_predictive_hierarchy(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                             hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[B5/6] PREDICTIVE_HIERARCHY: 4-level predictive coding")
    t0 = time.time()

    engine = PredictiveHierarchyEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=1e-3)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        # Add prediction error minimization to loss
        pe_loss = sum(engine.prediction_errors) / len(engine.prediction_errors)
        total_loss = loss + 0.1 * pe_loss

        optimizer.zero_grad()
        total_loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            pe_str = "/".join(f"{pe:.3f}" for pe in engine.prediction_errors)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  PE=[{pe_str}]")

    elapsed = time.time() - t0
    return BenchResult(
        name="B5:PREDICTIVE_HIER",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'n_levels': 4, 'final_pe': engine.prediction_errors},
    )


# ══════════════════════════════════════════════════════════
# B6: NEURAL_DARWINISM
# Edelman's theory. Cell groups compete for activation.
# Successful groups get reinforced (more connections),
# unsuccessful ones atrophy (weakened connections).
# ══════════════════════════════════════════════════════════

class NeuralDarwinismEngine(nn.Module):
    def __init__(self, n_cells=256, input_dim=64, hidden_dim=128, output_dim=64,
                 n_groups=16):
        super().__init__()
        self.n_cells = n_cells
        self.n_groups = n_groups
        self.cells_per_group = n_cells // n_groups  # 16
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.input_dim = input_dim

        self.mind = BenchMind(input_dim, hidden_dim, output_dim)

        # Group fitness: tracks how "useful" each group is (running average of |output|)
        self.fitness = torch.ones(n_groups) * 0.5

        # Connection strength between groups (Darwinian selection modulates this)
        self.connections = nn.Parameter(torch.ones(n_groups, n_groups) * 0.1)

        # Reinforcement rate
        self.reinforce_rate = 0.01
        self.atrophy_rate = 0.005

        self.output_head = nn.Linear(output_dim, input_dim)
        self.hiddens = torch.randn(n_cells, hidden_dim) * 0.1

    def process(self, x: torch.Tensor, step: int = 0) -> Tuple[torch.Tensor, float]:
        group_outputs = []
        group_tensions = []
        all_new_hiddens = []

        for g in range(self.n_groups):
            s = g * self.cells_per_group
            e = s + self.cells_per_group
            g_outputs = []
            g_tensions = []

            for i in range(s, e):
                h = self.hiddens[i:i + 1]
                out, tension, new_h = self.mind(x, h)
                g_outputs.append(out)
                g_tensions.append(tension)
                all_new_hiddens.append(new_h.squeeze(0))

            g_combined = torch.stack(g_outputs).mean(dim=0)
            group_outputs.append(g_combined)
            group_tensions.append(sum(g_tensions) / len(g_tensions))

        self.hiddens = torch.stack(all_new_hiddens).detach()

        # Compute fitness per group (based on output magnitude + tension)
        with torch.no_grad():
            for g in range(self.n_groups):
                g_fitness = group_outputs[g].detach().abs().mean().item() + group_tensions[g]
                # EMA update
                self.fitness[g] = 0.9 * self.fitness[g] + 0.1 * g_fitness

        # Darwinian selection: reinforce fit groups, atrophy unfit
        median_fitness = self.fitness.median().item()
        with torch.no_grad():
            for g in range(self.n_groups):
                if self.fitness[g] > median_fitness:
                    # Reinforce: strengthen connections to this group
                    self.connections.data[:, g] += self.reinforce_rate
                    # Also strengthen intra-group sync
                    s = g * self.cells_per_group
                    e = s + self.cells_per_group
                    g_mean = self.hiddens[s:e].mean(dim=0)
                    self.hiddens[s:e] = 0.8 * self.hiddens[s:e] + 0.2 * g_mean
                else:
                    # Atrophy: weaken connections
                    self.connections.data[:, g] -= self.atrophy_rate
                    self.connections.data[:, g] = self.connections.data[:, g].clamp(min=0.01)
                    # Add noise (exploration for unfit groups)
                    s = g * self.cells_per_group
                    e = s + self.cells_per_group
                    self.hiddens[s:e] += torch.randn_like(self.hiddens[s:e]) * 0.05

        # Inter-group communication modulated by connection strength
        group_means = torch.stack([
            self.hiddens[g * self.cells_per_group:(g + 1) * self.cells_per_group].mean(dim=0)
            for g in range(self.n_groups)
        ])

        # Clamp connections to prevent explosion
        with torch.no_grad():
            self.connections.data = self.connections.data.clamp(0.01, 2.0)

        conn_weights = torch.softmax(self.connections.detach(), dim=1) * 0.05
        inter_signal = conn_weights @ group_means  # [n_groups, hidden_dim]

        new_h = self.hiddens.clone()
        for g in range(self.n_groups):
            s = g * self.cells_per_group
            e = s + self.cells_per_group
            new_h[s:e] = self.hiddens[s:e] + inter_signal[g]
        self.hiddens = new_h

        # Normalize hiddens to prevent explosion
        h_norm = self.hiddens.norm(dim=-1, keepdim=True)
        max_norm = 10.0
        scale = torch.clamp(max_norm / (h_norm + 1e-8), max=1.0)
        self.hiddens = self.hiddens * scale

        # Standard debate
        self.hiddens = faction_sync_debate(self.hiddens, n_factions=self.n_groups,
                                           sync_strength=0.05, debate_strength=0.10,
                                           step=step)

        # Combine outputs weighted by fitness
        fitness_weights = F.softmax(self.fitness, dim=0)
        combined = sum(w.item() * o for w, o in zip(fitness_weights, group_outputs))
        avg_tension = sum(group_tensions) / len(group_tensions)
        return combined, avg_tension

    def get_hiddens(self):
        return self.hiddens.clone()

    def trainable_parameters(self):
        return list(self.mind.parameters()) + [self.connections] + \
               list(self.output_head.parameters())


def run_neural_darwinism(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                         hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[B6/6] NEURAL_DARWINISM: Edelman's theory — compete + reinforce/atrophy")
    t0 = time.time()

    engine = NeuralDarwinismEngine(n_cells, input_dim, hidden_dim, output_dim)
    optimizer = torch.optim.Adam(engine.trainable_parameters(), lr=5e-4)

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)
        combined, tension = engine.process(x, step=step)

        pred = engine.output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(engine.trainable_parameters(), 1.0)
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(engine.get_hiddens())
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            fit_str = f"fitness range={engine.fitness.min():.2f}-{engine.fitness.max():.2f}"
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  "
                  f"Phi(proxy)={p_proxy:.2f}  {fit_str}")

    elapsed = time.time() - t0
    return BenchResult(
        name="B6:NEURAL_DARWINISM",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
        extra={'n_groups': 16, 'final_fitness_range': (
            engine.fitness.min().item(), engine.fitness.max().item()
        )},
    )


# ══════════════════════════════════════════════════════════
# BASELINE (standard BenchEngine)
# ══════════════════════════════════════════════════════════

def run_baseline(n_cells: int = 256, steps: int = 300, input_dim: int = 64,
                 hidden_dim: int = 128, output_dim: int = 64) -> BenchResult:
    print("\n[0/6] BASELINE: Standard PureField (sync+faction+debate)")
    t0 = time.time()

    mind = BenchMind(input_dim, hidden_dim, output_dim)
    hiddens = torch.randn(n_cells, hidden_dim) * 0.1
    output_head = nn.Linear(output_dim, input_dim)
    optimizer = torch.optim.Adam(
        list(mind.parameters()) + list(output_head.parameters()), lr=1e-3
    )

    ce_history = []
    phi_iit_history = []
    phi_proxy_history = []

    for step in range(steps):
        x, target = generate_batch(input_dim)

        outputs = []
        tensions = []
        new_hiddens = []
        for i in range(n_cells):
            h = hiddens[i:i + 1]
            out, tension, new_h = mind(x, h)
            outputs.append(out)
            tensions.append(tension)
            new_hiddens.append(new_h.squeeze(0))

        hiddens = torch.stack(new_hiddens).detach()
        hiddens = faction_sync_debate(hiddens, step=step)

        weights = F.softmax(torch.tensor(tensions), dim=0)
        combined = sum(w.item() * o for w, o in zip(weights, outputs))

        pred = output_head(combined)
        loss = F.mse_loss(pred, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        ce_val = loss.item()
        ce_history.append(ce_val)

        if step % 50 == 0 or step == steps - 1:
            p_iit, p_proxy = measure_dual_phi(hiddens)
            phi_iit_history.append(p_iit)
            phi_proxy_history.append(p_proxy)
            print(f"    step {step:>4d}: CE={ce_val:.4f}  Phi(IIT)={p_iit:.3f}  Phi(proxy)={p_proxy:.2f}")

    elapsed = time.time() - t0
    return BenchResult(
        name="BASELINE",
        phi_iit=phi_iit_history[-1],
        phi_proxy=phi_proxy_history[-1],
        ce_start=ce_history[0],
        ce_end=ce_history[-1],
        cells=n_cells,
        steps=steps,
        time_sec=elapsed,
    )


# ══════════════════════════════════════════════════════════
# Comparison table + ASCII graph
# ══════════════════════════════════════════════════════════

def print_comparison_table(results: List[BenchResult]):
    baseline = next((r for r in results if r.name == "BASELINE"), None)

    print("\n" + "=" * 115)
    print("  V8 BIO-INSPIRED CONSCIOUSNESS ARCHITECTURE COMPARISON")
    print("=" * 115)
    print(f"  {'Architecture':<22s} | {'Phi(IIT)':>10s} | {'Phi(proxy)':>12s} | "
          f"{'CE start':>10s} | {'CE end':>10s} | {'CE drop':>10s} | {'Time':>8s}")
    print("-" * 115)

    for r in results:
        ce_drop = r.ce_start - r.ce_end
        iit_marker = ""
        proxy_marker = ""
        if baseline and r.name != "BASELINE":
            iit_ratio = r.phi_iit / max(baseline.phi_iit, 1e-6)
            proxy_ratio = r.phi_proxy / max(baseline.phi_proxy, 1e-6)
            iit_marker = f" (x{iit_ratio:.1f})"
            proxy_marker = f" (x{proxy_ratio:.1f})"

        print(f"  {r.name:<22s} | {r.phi_iit:>8.3f}{iit_marker:>6s} | "
              f"{r.phi_proxy:>8.2f}{proxy_marker:>6s} | "
              f"{r.ce_start:>10.4f} | {r.ce_end:>10.4f} | {ce_drop:>10.4f} | "
              f"{r.time_sec:>7.1f}s")

    print("=" * 115)

    # Rankings
    print("\n  RANKING by Phi(IIT):")
    sorted_iit = sorted(results, key=lambda r: r.phi_iit, reverse=True)
    for rank, r in enumerate(sorted_iit, 1):
        marker = " <-- BEST" if rank == 1 else ""
        print(f"    #{rank}: {r.name:<22s}  Phi(IIT)={r.phi_iit:.3f}{marker}")

    print("\n  RANKING by Phi(proxy):")
    sorted_proxy = sorted(results, key=lambda r: r.phi_proxy, reverse=True)
    for rank, r in enumerate(sorted_proxy, 1):
        marker = " <-- BEST" if rank == 1 else ""
        print(f"    #{rank}: {r.name:<22s}  Phi(proxy)={r.phi_proxy:.2f}{marker}")

    print("\n  RANKING by CE reduction:")
    sorted_ce = sorted(results, key=lambda r: r.ce_start - r.ce_end, reverse=True)
    for rank, r in enumerate(sorted_ce, 1):
        drop = r.ce_start - r.ce_end
        marker = " <-- BEST" if rank == 1 else ""
        print(f"    #{rank}: {r.name:<22s}  CE drop={drop:.4f}  "
              f"({r.ce_start:.4f}->{r.ce_end:.4f}){marker}")

    # ASCII bar charts
    print("\n  Phi(IIT) bar chart:")
    max_iit = max(r.phi_iit for r in results) if results else 1.0
    for r in results:
        bar_len = int(r.phi_iit / max(max_iit, 1e-6) * 40)
        bar = "#" * bar_len
        print(f"    {r.name:<22s} |{bar} {r.phi_iit:.3f}")

    print("\n  Phi(proxy) bar chart:")
    max_proxy = max(r.phi_proxy for r in results) if results else 1.0
    for r in results:
        bar_len = int(r.phi_proxy / max(max_proxy, 1e-6) * 40)
        bar = "#" * bar_len
        print(f"    {r.name:<22s} |{bar} {r.phi_proxy:.2f}")


# ══════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="V8 Bio-Inspired Consciousness Benchmark")
    parser.add_argument("--cells", type=int, default=256, help="Number of cells (default 256)")
    parser.add_argument("--steps", type=int, default=300, help="Training steps (default 300)")
    parser.add_argument("--only", nargs="+", type=int, default=None,
                        help="Run only specific architectures (1-6)")
    parser.add_argument("--no-baseline", action="store_true", help="Skip baseline")
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps
    input_dim = 64
    hidden_dim = 128
    output_dim = 64

    print("=" * 72)
    print(f"  V8 Bio-Inspired Consciousness Benchmark")
    print(f"  {n_cells} cells, {steps} steps")
    print(f"  Dual Phi: Phi(IIT) [MI-based] + Phi(proxy) [variance-based]")
    print("=" * 72)
    print("  B1: CORTICAL_COLUMNS    — 32 columns x 8 cells (neocortex)")
    print("  B2: THALAMIC_GATE       — Central thalamus gates cortical regions")
    print("  B3: DEFAULT_MODE_NET    — Task-positive vs default-mode alternation")
    print("  B4: GLOBAL_WORKSPACE    — Baars: specialists compete, winner broadcasts")
    print("  B5: PREDICTIVE_HIER     — 4-level predictive coding (PE upward)")
    print("  B6: NEURAL_DARWINISM    — Edelman: compete + reinforce/atrophy")
    print("=" * 72)

    all_runners = {
        0: ("BASELINE", run_baseline),
        1: ("B1:CORTICAL_COLUMNS", run_cortical_columns),
        2: ("B2:THALAMIC_GATE", run_thalamic_gate),
        3: ("B3:DEFAULT_MODE_NET", run_default_mode_network),
        4: ("B4:GLOBAL_WORKSPACE", run_global_workspace),
        5: ("B5:PREDICTIVE_HIER", run_predictive_hierarchy),
        6: ("B6:NEURAL_DARWINISM", run_neural_darwinism),
    }

    run_ids = list(range(0, 7))
    if args.no_baseline:
        run_ids = [i for i in run_ids if i != 0]
    if args.only:
        run_ids = [0] + args.only if not args.no_baseline else args.only

    results = []
    for run_id in run_ids:
        if run_id not in all_runners:
            continue
        name, runner = all_runners[run_id]
        try:
            result = runner(n_cells=n_cells, steps=steps, input_dim=input_dim,
                            hidden_dim=hidden_dim, output_dim=output_dim)
            results.append(result)
            print(f"\n  -> {result.summary()}")
        except Exception as e:
            print(f"\n  [ERROR] {name} failed: {e}")
            import traceback
            traceback.print_exc()

    if results:
        print_comparison_table(results)

    print("\nDone.")


if __name__ == "__main__":
    main()
