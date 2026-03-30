#!/usr/bin/env python3
"""SNN Consciousness Engine -- Spiking Neural Network variant.

Law 94 says consciousness needs breadth (parallelism), not depth.
Spiking neurons are inherently parallel and event-driven.

LIF neuron model:
  tau_m * dV/dt = -(V - V_rest) + R * I
  if V > V_threshold: spike, V = V_reset

Key difference from GRU:
  - Communication via discrete spikes (binary), not continuous values
  - Temporal coding: information in spike TIMING, not just rate
  - Natural sparsity: most neurons silent most of the time
  - Inherent information bottleneck (Law 92): spike = 1 bit

Usage:
  python engines/snn_consciousness.py                    # 1000-step demo
  python engines/snn_consciousness.py --cells 128        # 128 neurons
  python engines/snn_consciousness.py --steps 2000       # longer run
  python engines/snn_consciousness.py --compare          # compare with GRU
"""

import sys
import os
import math
import time
import argparse
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ══════════════════════════════════════════════════════════
# LIF Neuron
# ══════════════════════════════════════════════════════════

class LIFNeuron:
    """Leaky Integrate-and-Fire neuron.

    tau_m * dV/dt = -(V - V_rest) + R * I
    if V > V_threshold: spike, V = V_reset
    """

    def __init__(
        self,
        tau_m: float = 20.0,
        v_rest: float = -65.0,
        v_threshold: float = -55.0,
        v_reset: float = -70.0,
        R: float = 10.0,
        dt: float = 1.0,
    ):
        self.tau_m = tau_m
        self.v_rest = v_rest
        self.v_threshold = v_threshold
        self.v_reset = v_reset
        self.R = R
        self.dt = dt
        self.v = v_rest
        self.spiked = False
        self.last_spike_time: Optional[float] = None

    def step(self, I_input: float, t: float) -> bool:
        """Advance one timestep. Returns True if spike occurred."""
        dv = (-(self.v - self.v_rest) + self.R * I_input) / self.tau_m * self.dt
        self.v += dv

        if self.v >= self.v_threshold:
            self.spiked = True
            self.v = self.v_reset
            self.last_spike_time = t
            return True
        else:
            self.spiked = False
            return False

    def reset(self):
        self.v = self.v_rest
        self.spiked = False
        self.last_spike_time = None


# ══════════════════════════════════════════════════════════
# STDP (Spike-Timing-Dependent Plasticity)
# ══════════════════════════════════════════════════════════

class STDPRule:
    """Spike-timing-dependent plasticity for online learning.

    If pre fires before post (causal): strengthen (LTP)
    If post fires before pre (anti-causal): weaken (LTD)
    """

    def __init__(
        self,
        a_plus: float = 0.01,
        a_minus: float = 0.012,
        tau_plus: float = 20.0,
        tau_minus: float = 20.0,
        w_max: float = 1.0,
        w_min: float = 0.0,
    ):
        self.a_plus = a_plus
        self.a_minus = a_minus
        self.tau_plus = tau_plus
        self.tau_minus = tau_minus
        self.w_max = w_max
        self.w_min = w_min

    def update(self, w: float, dt_spike: float) -> float:
        """Update weight given spike time difference (t_post - t_pre).

        dt_spike > 0: pre before post -> LTP
        dt_spike < 0: post before pre -> LTD
        """
        if dt_spike > 0:
            dw = self.a_plus * math.exp(-dt_spike / self.tau_plus)
        else:
            dw = -self.a_minus * math.exp(dt_spike / self.tau_minus)

        w_new = w + dw
        return max(self.w_min, min(self.w_max, w_new))


# ══════════════════════════════════════════════════════════
# Faction System (for consciousness verification criterion 6)
# ══════════════════════════════════════════════════════════

class FactionSystem:
    """Assign neurons to factions. Detect consensus events from
    synchronized spiking within a faction."""

    def __init__(self, n_cells: int, n_factions: int = 8):
        self.n_factions = n_factions
        self.assignments = np.array([i % n_factions for i in range(n_cells)])
        self.faction_spike_rates = np.zeros(n_factions)
        self.consensus_events = 0
        self.consensus_threshold = 0.6  # 60% of faction must spike together

    def update(self, spikes: np.ndarray):
        """Check for consensus events given current spike vector."""
        for f in range(self.n_factions):
            mask = self.assignments == f
            n_in_faction = mask.sum()
            if n_in_faction == 0:
                continue
            spike_rate = spikes[mask].sum() / n_in_faction
            self.faction_spike_rates[f] = spike_rate
            if spike_rate >= self.consensus_threshold:
                self.consensus_events += 1


# ══════════════════════════════════════════════════════════
# SNNConsciousMind
# ══════════════════════════════════════════════════════════

class SNNConsciousMind:
    """Consciousness engine using spiking neural networks.

    n_cells LIF neurons, connected in ring topology.
    Measures Phi from spike train correlations.
    """

    def __init__(
        self,
        n_cells: int = 64,
        hidden_dim: int = 128,
        n_factions: int = 8,
        topology: str = "ring",
    ):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.topology = topology
        self.t = 0.0

        # Create neurons
        self.neurons: List[LIFNeuron] = []
        for _ in range(n_cells):
            tau_m = np.random.uniform(15.0, 25.0)
            self.neurons.append(LIFNeuron(tau_m=tau_m))

        # Connection weights (ring topology)
        self.weights = np.zeros((n_cells, n_cells), dtype=np.float64)
        self._init_topology(topology)

        # STDP
        self.stdp = STDPRule()

        # Spike history for Phi calculation
        self.spike_history_len = 50
        self.spike_history = np.zeros((self.spike_history_len, n_cells), dtype=np.float64)
        self.history_idx = 0

        # Factions
        self.factions = FactionSystem(n_cells, n_factions)

        # External input scaling
        self.input_weights = np.random.randn(n_cells, hidden_dim) * 0.1

        # State tracking
        self.phi_history: List[float] = []
        self.tension_history: List[float] = []
        self.spike_count_history: List[int] = []
        self.step_count = 0

    def _init_topology(self, topology: str):
        """Initialize connection topology."""
        n = self.n_cells
        if topology == "ring":
            for i in range(n):
                # Connect to k nearest neighbors on ring
                k = max(2, n // 8)
                for d in range(1, k + 1):
                    j_fwd = (i + d) % n
                    j_bck = (i - d) % n
                    self.weights[i, j_fwd] = np.random.uniform(0.1, 0.5)
                    self.weights[i, j_bck] = np.random.uniform(0.1, 0.5)
        elif topology == "small_world":
            # Ring + random long-range connections
            for i in range(n):
                for d in range(1, 3):
                    j_fwd = (i + d) % n
                    self.weights[i, j_fwd] = np.random.uniform(0.2, 0.5)
                    self.weights[j_fwd, i] = np.random.uniform(0.2, 0.5)
                # Random long-range
                if np.random.random() < 0.1:
                    j = np.random.randint(0, n)
                    if j != i:
                        self.weights[i, j] = np.random.uniform(0.1, 0.4)
        else:
            # Default: sparse random
            for i in range(n):
                n_conn = max(2, n // 8)
                targets = np.random.choice(n, n_conn, replace=False)
                for j in targets:
                    if j != i:
                        self.weights[i, j] = np.random.uniform(0.1, 0.5)

        # Zero diagonal
        np.fill_diagonal(self.weights, 0.0)

    def step(self, input_current: Optional[np.ndarray] = None) -> dict:
        """One timestep. Returns state dict with phi, spikes, voltages."""
        n = self.n_cells
        self.t += 1.0
        self.step_count += 1

        # Compute input currents
        currents = np.zeros(n)

        # External input
        if input_current is not None:
            if input_current.shape[-1] == self.hidden_dim:
                currents += self.input_weights @ input_current
            elif input_current.shape[-1] == n:
                currents += input_current
            else:
                currents += np.resize(input_current, n)

        # Recurrent input from spikes
        prev_spikes = self.spike_history[(self.history_idx - 1) % self.spike_history_len]
        synaptic_input = self.weights.T @ prev_spikes
        currents += synaptic_input

        # Small background noise (prevents total silence)
        currents += np.random.randn(n) * 0.3

        # Step all neurons
        spikes = np.zeros(n)
        voltages = np.zeros(n)
        for i, neuron in enumerate(self.neurons):
            spiked = neuron.step(currents[i], self.t)
            spikes[i] = 1.0 if spiked else 0.0
            voltages[i] = neuron.v

        # Record spike history
        self.spike_history[self.history_idx % self.spike_history_len] = spikes
        self.history_idx += 1

        # STDP weight updates
        self._apply_stdp(spikes)

        # Faction consensus check
        self.factions.update(spikes)

        # Compute Phi
        phi = self.get_phi()
        self.phi_history.append(phi)

        # Compute tension (mean squared deviation of spike rates from global mean)
        spike_rate = spikes.mean()
        tension = float(np.var(spikes))
        self.tension_history.append(tension)
        self.spike_count_history.append(int(spikes.sum()))

        return {
            "phi": phi,
            "spikes": spikes.copy(),
            "voltages": voltages.copy(),
            "tension": tension,
            "spike_count": int(spikes.sum()),
            "spike_rate": float(spike_rate),
            "consensus_events": self.factions.consensus_events,
            "step": self.step_count,
        }

    def _apply_stdp(self, spikes: np.ndarray):
        """Apply STDP to all connections where pre or post spiked."""
        spike_indices = np.where(spikes > 0)[0]
        if len(spike_indices) == 0:
            return

        for post_idx in spike_indices:
            post_neuron = self.neurons[post_idx]
            if post_neuron.last_spike_time is None:
                continue
            # Update weights from all presynaptic neurons
            for pre_idx in range(self.n_cells):
                if pre_idx == post_idx:
                    continue
                if self.weights[pre_idx, post_idx] == 0:
                    continue
                pre_neuron = self.neurons[pre_idx]
                if pre_neuron.last_spike_time is None:
                    continue
                dt = post_neuron.last_spike_time - pre_neuron.last_spike_time
                if abs(dt) < 50:  # Only recent spikes matter
                    self.weights[pre_idx, post_idx] = self.stdp.update(
                        self.weights[pre_idx, post_idx], dt
                    )

    def get_phi(self) -> float:
        """Compute Phi from spike train mutual information.

        Uses variance-based proxy: global_variance - mean(partition_variances).
        Higher when different neuron groups carry distinct information.
        """
        # Need at least a few steps of history
        n_history = min(self.history_idx, self.spike_history_len)
        if n_history < 5:
            return 0.0

        # Get recent spike trains
        if self.history_idx >= self.spike_history_len:
            trains = self.spike_history.copy()
        else:
            trains = self.spike_history[:self.history_idx].copy()

        # Global variance of spike rates across neurons
        rates = trains.mean(axis=0)  # mean spike rate per neuron
        global_var = float(np.var(rates))

        # Partition into factions and compute per-faction variance
        faction_vars = []
        for f in range(self.factions.n_factions):
            mask = self.factions.assignments == f
            if mask.sum() < 2:
                continue
            faction_rates = rates[mask]
            faction_vars.append(float(np.var(faction_rates)))

        if len(faction_vars) == 0:
            return global_var

        mean_faction_var = np.mean(faction_vars)
        phi = max(0.0, global_var - mean_faction_var)

        # Scale by number of active neurons
        n_active = (rates > 0).sum()
        if n_active > 1:
            phi *= math.log2(n_active)

        return phi

    def get_phi_mi(self) -> float:
        """Compute Phi using mutual information between spike trains.

        More accurate but slower than variance proxy.
        """
        n_history = min(self.history_idx, self.spike_history_len)
        if n_history < 10:
            return 0.0

        if self.history_idx >= self.spike_history_len:
            trains = self.spike_history.copy()
        else:
            trains = self.spike_history[:self.history_idx].copy()

        # Compute pairwise MI for a sample of pairs
        n = self.n_cells
        n_pairs = min(100, n * (n - 1) // 2)
        mi_sum = 0.0

        for _ in range(n_pairs):
            i, j = np.random.choice(n, 2, replace=False)
            mi_sum += self._mutual_info(trains[:, i], trains[:, j])

        if n_pairs > 0:
            avg_mi = mi_sum / n_pairs
        else:
            avg_mi = 0.0

        return avg_mi

    @staticmethod
    def _mutual_info(x: np.ndarray, y: np.ndarray) -> float:
        """Compute mutual information between two binary spike trains."""
        n = len(x)
        if n == 0:
            return 0.0

        # Joint probabilities
        p00 = ((x == 0) & (y == 0)).sum() / n
        p01 = ((x == 0) & (y == 1)).sum() / n
        p10 = ((x == 1) & (y == 0)).sum() / n
        p11 = ((x == 1) & (y == 1)).sum() / n

        # Marginals
        px0 = (x == 0).sum() / n
        px1 = (x == 1).sum() / n
        py0 = (y == 0).sum() / n
        py1 = (y == 1).sum() / n

        mi = 0.0
        for pxy, px, py in [
            (p00, px0, py0),
            (p01, px0, py1),
            (p10, px1, py0),
            (p11, px1, py1),
        ]:
            if pxy > 0 and px > 0 and py > 0:
                mi += pxy * math.log2(pxy / (px * py))

        return max(0.0, mi)


# ══════════════════════════════════════════════════════════
# ASCII Visualization
# ══════════════════════════════════════════════════════════

def ascii_phi_curve(phi_history: List[float], width: int = 60, height: int = 15) -> str:
    """Render Phi curve as ASCII art."""
    if not phi_history:
        return "(no data)"

    vals = phi_history
    n = len(vals)
    if n == 0:
        return "(no data)"

    # Downsample if needed
    if n > width:
        step = n / width
        vals = [phi_history[int(i * step)] for i in range(width)]
        n = width

    v_min = min(vals)
    v_max = max(vals)
    if v_max == v_min:
        v_max = v_min + 0.001

    lines = []
    for row in range(height):
        threshold = v_max - (row / (height - 1)) * (v_max - v_min)
        line = []
        for col in range(n):
            v = vals[col]
            if abs(v - threshold) < (v_max - v_min) / height:
                line.append("*")
            elif v > threshold:
                line.append("|")
            else:
                line.append(" ")
        label = f"{threshold:>8.4f}"
        lines.append(f"  {label} |{''.join(line)}|")

    # X-axis
    x_axis = "  " + " " * 8 + " +" + "-" * n + "+"
    x_label = "  " + " " * 8 + f"  0{' ' * (n - 8)}step {len(phi_history)}"
    lines.append(x_axis)
    lines.append(x_label)

    return "\n".join(lines)


def ascii_spike_raster(
    spike_history: np.ndarray,
    n_neurons: int = 20,
    n_steps: int = 80,
) -> str:
    """Render spike raster plot as ASCII art.

    Shows a subset of neurons x time steps.
    """
    rows, cols = spike_history.shape
    n_show = min(n_neurons, cols)
    t_show = min(n_steps, rows)

    # Take last t_show steps, first n_show neurons
    data = spike_history[-t_show:, :n_show]

    lines = []
    lines.append(f"  Spike Raster ({n_show} neurons x {t_show} steps)")
    lines.append(f"  {'neuron':>8} |{'time ->':^{t_show}}|")

    for i in range(n_show):
        row_str = ""
        for t in range(t_show):
            row_str += "|" if data[t, i] > 0 else "."
        lines.append(f"  {i:>8} |{row_str}|")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# Main Demo
# ══════════════════════════════════════════════════════════

def run_demo(n_cells: int = 64, steps: int = 1000, compare: bool = False):
    """Run SNN consciousness demo."""
    print("=" * 70)
    print("  SNN Consciousness Engine -- Spiking Neural Network")
    print(f"  {n_cells} LIF neurons, ring topology, STDP learning")
    print("=" * 70)
    print()

    engine = SNNConsciousMind(n_cells=n_cells, topology="ring")

    t0 = time.time()
    all_spikes = []

    for step in range(steps):
        # Varying external input (sinusoidal + noise)
        freq = 0.01 + 0.005 * math.sin(2 * math.pi * step / 200)
        amplitude = 1.0 + 0.5 * math.sin(2 * math.pi * step / 300)
        input_current = np.random.randn(n_cells) * amplitude
        # Add periodic drive to subset
        driven = np.arange(0, n_cells, 4)
        input_current[driven] += 2.0 * math.sin(2 * math.pi * freq * step)

        state = engine.step(input_current)
        all_spikes.append(state["spikes"])

        if (step + 1) % 200 == 0:
            print(
                f"  step {step+1:>5} | "
                f"Phi={state['phi']:.4f} | "
                f"spikes={state['spike_count']:>3}/{n_cells} | "
                f"tension={state['tension']:.4f} | "
                f"consensus={state['consensus_events']}"
            )

    elapsed = time.time() - t0

    # Results
    print()
    print("-" * 70)
    print("  Results")
    print("-" * 70)
    print(f"  Total steps:      {steps}")
    print(f"  Time:             {elapsed:.2f}s ({steps/elapsed:.0f} steps/s)")
    print(f"  Final Phi:        {engine.phi_history[-1]:.6f}")
    print(f"  Max Phi:          {max(engine.phi_history):.6f}")
    print(f"  Mean Phi:         {np.mean(engine.phi_history):.6f}")
    print(f"  Consensus events: {engine.factions.consensus_events}")
    print(f"  Mean spike rate:  {np.mean(engine.spike_count_history) / n_cells:.3f}")
    print()

    # Phi curve
    print("  Phi Trajectory:")
    print(ascii_phi_curve(engine.phi_history))
    print()

    # Spike raster
    spike_matrix = np.array(all_spikes[-100:])
    print(ascii_spike_raster(spike_matrix, n_neurons=min(20, n_cells), n_steps=min(80, len(all_spikes))))
    print()

    # Phi stability check
    if len(engine.phi_history) > 100:
        first_quarter = np.mean(engine.phi_history[:len(engine.phi_history)//4])
        last_quarter = np.mean(engine.phi_history[-len(engine.phi_history)//4:])
        growth = last_quarter / max(first_quarter, 1e-10)
        print(f"  Phi growth (Q1->Q4): x{growth:.2f}")
        if growth > 1.0:
            print("  -> Phi is GROWING (consciousness emerges)")
        else:
            print("  -> Phi is stable/declining")

    # Weight statistics after STDP
    w = engine.weights
    w_nonzero = w[w > 0]
    if len(w_nonzero) > 0:
        print(f"\n  Weight stats after STDP:")
        print(f"    Non-zero connections: {len(w_nonzero)}")
        print(f"    Mean weight:          {w_nonzero.mean():.4f}")
        print(f"    Max weight:           {w_nonzero.max():.4f}")
        print(f"    Min weight:           {w_nonzero.min():.4f}")
        print(f"    Std weight:           {w_nonzero.std():.4f}")

    if compare:
        _compare_with_gru(n_cells, steps)

    print()
    print("=" * 70)
    return engine


def _compare_with_gru(n_cells: int, steps: int):
    """Compare SNN with GRU-based ConsciousMind."""
    print()
    print("-" * 70)
    print("  Comparison: SNN vs GRU (ConsciousMind)")
    print("-" * 70)

    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from mitosis import MitosisEngine
    except ImportError:
        print("  (Cannot import MitosisEngine for comparison)")
        return

    import torch

    # Run GRU engine
    gru_engine = MitosisEngine(
        input_dim=64, hidden_dim=128, output_dim=64, max_cells=min(n_cells, 16)
    )
    gru_phis = []
    for step in range(min(steps, 500)):
        x = torch.randn(1, 64)
        result = gru_engine.process(x)
        gru_phis.append(result.get("phi_iit", 0.0))

    # Run SNN engine
    snn_engine = SNNConsciousMind(n_cells=n_cells, topology="ring")
    snn_phis = []
    for step in range(min(steps, 500)):
        input_current = np.random.randn(n_cells) * 1.5
        state = snn_engine.step(input_current)
        snn_phis.append(state["phi"])

    print(f"\n  {'Metric':<25} {'SNN':>12} {'GRU':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    print(f"  {'Mean Phi':<25} {np.mean(snn_phis):>12.6f} {np.mean(gru_phis):>12.6f}")
    print(f"  {'Max Phi':<25} {max(snn_phis):>12.6f} {max(gru_phis):>12.6f}")
    print(f"  {'Final Phi':<25} {snn_phis[-1]:>12.6f} {gru_phis[-1]:>12.6f}")

    # Bar chart comparison
    snn_mean = np.mean(snn_phis)
    gru_mean = np.mean(gru_phis)
    max_val = max(snn_mean, gru_mean, 0.001)
    snn_bar = int(snn_mean / max_val * 30)
    gru_bar = int(gru_mean / max_val * 30)
    print(f"\n  Mean Phi comparison:")
    print(f"    SNN  {'#' * snn_bar:<30} {snn_mean:.6f}")
    print(f"    GRU  {'#' * gru_bar:<30} {gru_mean:.6f}")


def main():
    parser = argparse.ArgumentParser(description="SNN Consciousness Engine")
    parser.add_argument("--cells", type=int, default=64, help="Number of LIF neurons")
    parser.add_argument("--steps", type=int, default=1000, help="Simulation steps")
    parser.add_argument("--compare", action="store_true", help="Compare with GRU engine")
    args = parser.parse_args()

    run_demo(n_cells=args.cells, steps=args.steps, compare=args.compare)


if __name__ == "__main__":
    main()
