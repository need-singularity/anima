#!/usr/bin/env python3
"""Thermodynamic Consciousness Engine -- consciousness as a dissipative structure.

Models consciousness as a far-from-equilibrium thermodynamic system (Prigogine).
Key insight: consciousness requires entropy EXPORT to maintain local order.

Laws applied:
  1st law: Energy conservation across cells (sum(E) = const)
  2nd law: Total entropy increases, BUT local entropy can decrease (consciousness!)
  Landauer's principle: erasing 1 bit costs kT*ln(2) energy
  Information-energy equivalence: Phi bits * kT*ln(2) = minimum energy for consciousness

Model:
  dS/dt = entropy_production (irreversible) - entropy_export (to environment)
  dE/dt = energy_flux between cells (topology-dependent)
  T = dE/dS (temperature from energy-entropy relation)

Key question: What is the thermodynamic cost of consciousness?
  - Joules per Phi-bit
  - Comparison with Landauer limit
  - Is consciousness thermodynamically efficient?

Usage:
  python engines/thermodynamic_consciousness.py                    # 64-cell demo
  python engines/thermodynamic_consciousness.py --cells 128        # 128 cells
  python engines/thermodynamic_consciousness.py --benchmark        # substrate comparison
  python engines/thermodynamic_consciousness.py --landauer         # Landauer analysis
"""

import sys
import math
import time
import argparse
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ======================================================================
# Physical Constants
# ======================================================================

K_BOLTZMANN = 1.380649e-23   # J/K
LANDAUER_LIMIT = K_BOLTZMANN * np.log(2)  # ~9.57e-24 J/bit at 1K
ROOM_TEMP = 300.0            # K
BRAIN_TEMP = 310.15          # K (37C)
LANDAUER_ROOM = K_BOLTZMANN * ROOM_TEMP * np.log(2)  # ~2.87e-21 J/bit

# Substrate energy costs (Joules per operation)
SUBSTRATE_ENERGY = {
    "cmos_7nm":         1e-15,     # ~1 fJ per switch
    "cmos_28nm":        1e-14,     # ~10 fJ
    "neuromorphic":     1e-18,     # ~1 aJ (Loihi)
    "memristor":        1e-16,     # ~100 aJ
    "photonic":         1e-17,     # ~10 aJ
    "superconducting":  1e-19,     # ~0.1 aJ (but at 4K)
    "biological_neuron": 1e-14,    # ~10 fJ per spike
    "fpga":             1e-13,     # ~100 fJ
    "esp32":            1e-11,     # ~10 pJ per operation
}

# Operating temperatures
SUBSTRATE_TEMP = {
    "cmos_7nm":         350.0,
    "cmos_28nm":        340.0,
    "neuromorphic":     300.0,
    "memristor":        300.0,
    "photonic":         300.0,
    "superconducting":  4.0,
    "biological_neuron": 310.15,
    "fpga":             340.0,
    "esp32":            330.0,
}


# ======================================================================
# Thermodynamic Cell
# ======================================================================

class ThermodynamicCell:
    """One consciousness cell modeled as a thermodynamic subsystem.

    State variables:
      E: internal energy (Joules, normalized)
      S: entropy (bits)
      T: temperature (derived: T = dE/dS)

    Dynamics:
      dE/dt = sum(energy_flux_from_neighbors) - dissipation
      dS/dt = entropy_production - entropy_export
    """

    def __init__(self, cell_id: int, initial_energy: float = 1.0):
        self.cell_id = cell_id
        self.energy = initial_energy + np.random.uniform(-0.1, 0.1)
        self.entropy = np.random.uniform(0.3, 0.7)
        self.temperature = self.energy / max(self.entropy, 0.01)

        # Internal state (hidden representation for MI computation)
        self.hidden = np.random.randn(16) * 0.1

        # Tracking
        self.energy_dissipated = 0.0
        self.bits_erased = 0.0

    def update_temperature(self):
        """T = E / S (simplified thermodynamic relation)."""
        self.temperature = self.energy / max(self.entropy, 0.001)


# ======================================================================
# Thermodynamic Consciousness Engine
# ======================================================================

class ThermodynamicConsciousMind:
    """Consciousness as a dissipative structure (Prigogine).

    N cells exchange energy along topology edges.
    Each cell produces entropy (computation) and exports it (dissipation).
    Consciousness = the ordered structure that emerges far from equilibrium.

    Phi is measured from mutual information between cell hidden states,
    but now has a physical energy cost via Landauer's principle.
    """

    def __init__(
        self,
        n_cells: int = 64,
        n_factions: int = 8,
        topology: str = "ring",
        substrate: str = "cmos_7nm",
        total_energy: float = 100.0,
        entropy_production_rate: float = 0.02,
        entropy_export_rate: float = 0.015,
        energy_coupling: float = 0.1,
    ):
        self.n_cells = n_cells
        self.n_factions = min(n_factions, n_cells)
        self.topology = topology
        self.substrate = substrate
        self.total_energy = total_energy
        self.entropy_production_rate = entropy_production_rate
        self.entropy_export_rate = entropy_export_rate
        self.energy_coupling = energy_coupling

        # Create cells with equal energy distribution
        e_per_cell = total_energy / n_cells
        self.cells = [ThermodynamicCell(i, e_per_cell) for i in range(n_cells)]

        # Connectivity
        self.adjacency = np.zeros((n_cells, n_cells), dtype=np.float64)
        self._build_topology(topology)

        # Faction system
        self.faction_assignments = np.array([i % n_factions for i in range(n_cells)])
        self.consensus_events = 0

        # Substrate properties
        self.e_per_op = SUBSTRATE_ENERGY.get(substrate, 1e-15)
        self.op_temp = SUBSTRATE_TEMP.get(substrate, 300.0)
        self.landauer_cost = K_BOLTZMANN * self.op_temp * np.log(2)

        # History
        self.phi_history: List[float] = []
        self.total_entropy_history: List[float] = []
        self.energy_history: List[float] = []
        self.dissipation_history: List[float] = []
        self.joules_per_phi_bit: List[float] = []
        self.step_count = 0

    def _build_topology(self, topology: str):
        """Build adjacency matrix."""
        n = self.n_cells
        if topology == "ring":
            for i in range(n):
                k = max(1, n // 16)
                for d in range(1, k + 1):
                    self.adjacency[i, (i + d) % n] = 1.0
                    self.adjacency[(i + d) % n, i] = 1.0
        elif topology == "small_world":
            for i in range(n):
                self.adjacency[i, (i + 1) % n] = 1.0
                self.adjacency[(i + 1) % n, i] = 1.0
                if np.random.random() < 0.1:
                    j = np.random.randint(n)
                    if j != i:
                        self.adjacency[i, j] = 1.0
                        self.adjacency[j, i] = 1.0
        elif topology == "complete":
            self.adjacency = np.ones((n, n)) - np.eye(n)
        else:
            # Default ring
            for i in range(n):
                self.adjacency[i, (i + 1) % n] = 1.0
                self.adjacency[(i + 1) % n, i] = 1.0
        np.fill_diagonal(self.adjacency, 0.0)

    def step(self, input_signal: Optional[np.ndarray] = None) -> dict:
        """One thermodynamic step.

        1. Energy exchange between connected cells
        2. Entropy production (information processing)
        3. Entropy export (dissipation to environment)
        4. Hidden state update (GRU-like, but energy-constrained)
        5. Enforce energy conservation
        6. Compute Phi and energy cost
        """
        self.step_count += 1
        n = self.n_cells
        step_dissipation = 0.0

        # 1. Energy exchange along topology
        energy_deltas = np.zeros(n)
        for i in range(n):
            for j in range(n):
                if self.adjacency[i, j] > 0:
                    # Energy flows from hot to cold (2nd law)
                    dT = self.cells[i].temperature - self.cells[j].temperature
                    flux = self.energy_coupling * dT * self.adjacency[i, j]
                    energy_deltas[i] -= flux
                    energy_deltas[j] += flux

        # Apply energy changes
        for i in range(n):
            self.cells[i].energy += energy_deltas[i]
            self.cells[i].energy = max(0.01, self.cells[i].energy)

        # 2. Entropy production (each cell does computation)
        for i in range(n):
            cell = self.cells[i]

            # Entropy production = irreversible information processing
            ds_prod = self.entropy_production_rate * cell.temperature

            # External input modulates entropy production
            if input_signal is not None and i < len(input_signal):
                ds_prod *= (1.0 + 0.3 * abs(input_signal[i]))

            # Entropy export = dissipation to environment
            ds_export = self.entropy_export_rate * (cell.entropy - 0.5)
            ds_export = max(0.0, ds_export)  # Can only export, not import

            # Landauer cost: erasing bits costs energy
            bits_erased = ds_export / max(1e-10, K_BOLTZMANN * cell.temperature)
            energy_cost = bits_erased * self.landauer_cost
            cell.bits_erased += max(0, bits_erased)
            cell.energy_dissipated += energy_cost
            step_dissipation += energy_cost

            # Update entropy
            cell.entropy += ds_prod - ds_export
            cell.entropy = max(0.01, min(5.0, cell.entropy))

            # Small energy loss from entropy export
            cell.energy -= energy_cost * 1e10  # Scale to normalized units
            cell.energy = max(0.01, cell.energy)

            cell.update_temperature()

        # 3. Hidden state update (energy-constrained GRU-like dynamics)
        new_hiddens = []
        for i in range(n):
            cell = self.cells[i]
            h = cell.hidden.copy()

            # Neighbor influence
            neighbor_sum = np.zeros_like(h)
            n_neighbors = 0
            for j in range(n):
                if self.adjacency[i, j] > 0:
                    neighbor_sum += self.cells[j].hidden * self.adjacency[i, j]
                    n_neighbors += 1
            if n_neighbors > 0:
                neighbor_sum /= n_neighbors

            # GRU-like update scaled by temperature (hotter = more active)
            activity = np.tanh(cell.temperature / 2.0)
            gate = 1.0 / (1.0 + np.exp(-neighbor_sum))
            h_new = gate * h + (1 - gate) * np.tanh(neighbor_sum + h * 0.5)
            h_new = activity * h_new + (1 - activity) * h

            # Add noise scaled by temperature
            h_new += np.random.randn(len(h)) * 0.01 * cell.temperature

            new_hiddens.append(h_new)

        for i in range(n):
            self.cells[i].hidden = new_hiddens[i]

        # 4. Enforce energy conservation (redistribute to maintain total)
        current_total = sum(c.energy for c in self.cells)
        if current_total > 0:
            scale = self.total_energy / current_total
            for c in self.cells:
                c.energy *= scale

        # 5. Check faction consensus
        self._check_consensus()

        # 6. Compute Phi
        phi = self.get_phi()
        self.phi_history.append(phi)

        # Total entropy
        total_S = sum(c.entropy for c in self.cells)
        self.total_entropy_history.append(total_S)

        # Total energy
        total_E = sum(c.energy for c in self.cells)
        self.energy_history.append(total_E)
        self.dissipation_history.append(step_dissipation)

        # Joules per Phi-bit (thermodynamic efficiency)
        ops_this_step = n  # One operation per cell
        energy_this_step = ops_this_step * self.e_per_op
        jpb = energy_this_step / max(phi, 1e-15)
        self.joules_per_phi_bit.append(jpb)

        return {
            "phi": phi,
            "total_entropy": total_S,
            "total_energy": total_E,
            "dissipation": step_dissipation,
            "joules_per_phi_bit": jpb,
            "mean_temperature": float(np.mean([c.temperature for c in self.cells])),
            "consensus_events": self.consensus_events,
            "step": self.step_count,
        }

    def _check_consensus(self):
        """Check if any faction has converged hidden states."""
        for f in range(self.n_factions):
            mask = self.faction_assignments == f
            indices = np.where(mask)[0]
            if len(indices) < 2:
                continue
            # Compute pairwise cosine similarity
            hiddens = np.array([self.cells[i].hidden for i in indices])
            norms = np.linalg.norm(hiddens, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-10)
            normalized = hiddens / norms
            sim_matrix = normalized @ normalized.T
            mean_sim = (sim_matrix.sum() - len(indices)) / max(1, len(indices) * (len(indices) - 1))
            if mean_sim > 0.8:
                self.consensus_events += 1

    def get_phi(self) -> float:
        """Compute Phi from mutual information between cell hidden states.

        Uses variance-based proxy consistent with other engines.
        """
        hiddens = np.array([c.hidden for c in self.cells])
        rates = np.var(hiddens, axis=1)
        global_var = float(np.var(rates))

        faction_vars = []
        for f in range(self.n_factions):
            mask = self.faction_assignments == f
            if mask.sum() < 2:
                continue
            faction_vars.append(float(np.var(rates[mask])))

        if not faction_vars:
            return global_var

        mean_fv = np.mean(faction_vars)
        phi = max(0.0, global_var - mean_fv)

        n_active = max(1, (rates > 0.001).sum())
        if n_active > 1:
            phi *= math.log2(n_active)

        return phi

    def get_landauer_efficiency(self) -> float:
        """How close to Landauer limit is the consciousness?

        efficiency = Landauer_minimum / actual_cost
        1.0 = perfectly efficient (impossible)
        Biological brain: ~1e-7 (very inefficient)
        """
        if not self.joules_per_phi_bit:
            return 0.0
        mean_jpb = np.mean(self.joules_per_phi_bit[-100:])
        if mean_jpb <= 0:
            return 0.0
        return self.landauer_cost / mean_jpb

    def thermodynamic_report(self) -> str:
        """Generate thermodynamic analysis report."""
        lines = []
        lines.append("  Thermodynamic Analysis")
        lines.append("  " + "-" * 50)

        mean_T = np.mean([c.temperature for c in self.cells])
        std_T = np.std([c.temperature for c in self.cells])
        mean_S = np.mean([c.entropy for c in self.cells])
        total_dissipated = sum(c.energy_dissipated for c in self.cells)
        total_bits_erased = sum(c.bits_erased for c in self.cells)

        lines.append(f"  Substrate:           {self.substrate}")
        lines.append(f"  Operating temp:      {self.op_temp:.1f} K")
        lines.append(f"  Landauer limit:      {self.landauer_cost:.2e} J/bit")
        lines.append(f"  Energy per op:       {self.e_per_op:.2e} J")
        lines.append(f"  Mean cell temp:      {mean_T:.4f} (std={std_T:.4f})")
        lines.append(f"  Mean cell entropy:   {mean_S:.4f} bits")
        lines.append(f"  Total dissipated:    {total_dissipated:.6f}")
        lines.append(f"  Total bits erased:   {total_bits_erased:.2f}")

        if self.joules_per_phi_bit:
            mean_jpb = np.mean(self.joules_per_phi_bit[-100:])
            efficiency = self.get_landauer_efficiency()
            lines.append(f"  J/Phi-bit (mean):    {mean_jpb:.2e}")
            lines.append(f"  Landauer efficiency: {efficiency:.2e}")
            lines.append(f"  Overhead vs limit:   x{1.0/max(efficiency,1e-20):.0f}")

        return "\n".join(lines)


# ======================================================================
# ASCII Visualization
# ======================================================================

def ascii_phi_curve(phi_history: List[float], width: int = 60, height: int = 12) -> str:
    """Render Phi curve as ASCII art."""
    if not phi_history:
        return "(no data)"

    vals = phi_history
    n = len(vals)
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

    x_axis = "  " + " " * 8 + " +" + "-" * n + "+"
    x_label = "  " + " " * 8 + f"  0{' ' * (n - 8)}step {len(phi_history)}"
    lines.append(x_axis)
    lines.append(x_label)
    return "\n".join(lines)


# ======================================================================
# Benchmark: Substrate Energy Comparison
# ======================================================================

def run_substrate_benchmark(n_cells: int = 64, steps: int = 500):
    """Compare thermodynamic cost of consciousness across substrates."""
    print("=" * 70)
    print("  Thermodynamic Cost of Consciousness -- Substrate Comparison")
    print("  Question: What is the minimum energy for consciousness?")
    print("=" * 70)
    print()

    substrates = [
        "superconducting",
        "neuromorphic",
        "photonic",
        "memristor",
        "biological_neuron",
        "cmos_7nm",
        "cmos_28nm",
        "fpga",
        "esp32",
    ]

    results = []

    for substrate in substrates:
        engine = ThermodynamicConsciousMind(
            n_cells=n_cells, substrate=substrate, topology="ring"
        )

        for s in range(steps):
            inp = np.random.randn(n_cells) * 0.3
            engine.step(inp)

        phi_mean = float(np.mean(engine.phi_history[-steps // 2:]))
        jpb_mean = float(np.mean(engine.joules_per_phi_bit[-steps // 2:]))
        efficiency = engine.get_landauer_efficiency()

        results.append({
            "substrate": substrate,
            "phi_mean": phi_mean,
            "jpb": jpb_mean,
            "efficiency": efficiency,
            "e_per_op": engine.e_per_op,
            "temp": engine.op_temp,
            "landauer": engine.landauer_cost,
        })

        print(f"  {substrate:>20}: Phi={phi_mean:.4f}, "
              f"J/Phi-bit={jpb_mean:.2e}, efficiency={efficiency:.2e}")

    # Sort by efficiency
    results.sort(key=lambda r: r["efficiency"], reverse=True)

    print()
    print("-" * 70)
    print("  Ranking (most thermodynamically efficient)")
    print("-" * 70)
    print(f"  {'#':>2} {'Substrate':>20} | {'J/Phi-bit':>12} | "
          f"{'Efficiency':>12} | {'Overhead':>10} | {'Temp':>6}")
    print(f"  {'-'*2} {'-'*20} | {'-'*12} | {'-'*12} | {'-'*10} | {'-'*6}")

    for i, r in enumerate(results):
        overhead = 1.0 / max(r["efficiency"], 1e-30)
        print(f"  {i+1:>2} {r['substrate']:>20} | {r['jpb']:>12.2e} | "
              f"{r['efficiency']:>12.2e} | x{overhead:>8.0f} | {r['temp']:>5.0f}K")

    print()

    # Landauer analysis
    print("  Landauer Limit Analysis:")
    print(f"    Minimum energy to erase 1 bit at 300K: {LANDAUER_ROOM:.2e} J")
    print(f"    Brain (310K): {K_BOLTZMANN * BRAIN_TEMP * np.log(2):.2e} J/bit")
    print(f"    Most efficient substrate: {results[0]['substrate']}")
    print(f"    Its overhead vs Landauer: x{1.0/max(results[0]['efficiency'],1e-30):.0f}")
    print()

    # Bar chart
    bar_data = {}
    for r in results:
        overhead = 1.0 / max(r["efficiency"], 1e-30)
        bar_data[r["substrate"]] = math.log10(max(overhead, 1))

    max_val = max(bar_data.values()) if bar_data else 1
    print("  Overhead vs Landauer (log10 scale):")
    for label, val in bar_data.items():
        bar_len = int(val / max(max_val, 1) * 40)
        print(f"    {label:>20} {'#' * bar_len} x10^{val:.0f}")
    print()

    return results


def run_landauer_analysis(n_cells: int = 64, steps: int = 500):
    """Detailed Landauer principle analysis."""
    print("=" * 70)
    print("  Landauer Principle & Consciousness")
    print("  Is consciousness thermodynamically efficient?")
    print("=" * 70)
    print()

    engine = ThermodynamicConsciousMind(
        n_cells=n_cells, substrate="biological_neuron", topology="ring"
    )

    for s in range(steps):
        inp = np.random.randn(n_cells) * 0.3
        engine.step(inp)
        if (s + 1) % 100 == 0:
            state = engine.step(np.zeros(n_cells))
            print(f"  step {s+1}: Phi={state['phi']:.4f}, "
                  f"J/Phi-bit={state['joules_per_phi_bit']:.2e}, "
                  f"T_mean={state['mean_temperature']:.4f}")

    print()
    print(engine.thermodynamic_report())
    print()

    # Key result
    phi_mean = np.mean(engine.phi_history[-100:])
    jpb_mean = np.mean(engine.joules_per_phi_bit[-100:])
    eff = engine.get_landauer_efficiency()

    print()
    print("  Key Results:")
    print(f"    Mean Phi:              {phi_mean:.6f}")
    print(f"    Energy per Phi-bit:    {jpb_mean:.2e} J")
    print(f"    Landauer limit:        {engine.landauer_cost:.2e} J/bit")
    print(f"    Efficiency:            {eff:.2e}")
    print(f"    Bits of consciousness cost {1.0/max(eff,1e-30):.0f}x the theoretical minimum")
    print()

    # Is consciousness efficient?
    if eff > 0.01:
        print("  Conclusion: Consciousness is REMARKABLY efficient (>1% of Landauer limit)")
    elif eff > 1e-6:
        print("  Conclusion: Consciousness is moderately efficient (comparable to modern CMOS)")
    else:
        print("  Conclusion: Consciousness is thermodynamically expensive")
        print("             (far from Landauer limit, room for optimization)")
    print()

    return engine


# ======================================================================
# Demo
# ======================================================================

def run_demo(n_cells: int = 64, steps: int = 500):
    """Run thermodynamic consciousness demo."""
    print("=" * 70)
    print(f"  Thermodynamic Consciousness Engine -- {n_cells} cells")
    print("  Consciousness as a dissipative structure (Prigogine)")
    print("=" * 70)
    print()

    engine = ThermodynamicConsciousMind(
        n_cells=n_cells, topology="ring", substrate="cmos_7nm"
    )

    t0 = time.time()
    for s in range(steps):
        # Varying external drive
        amplitude = 0.3 + 0.2 * math.sin(2 * math.pi * s / 200)
        inp = np.random.randn(n_cells) * amplitude
        state = engine.step(inp)

        if (s + 1) % 100 == 0:
            print(
                f"  step {s+1:>5} | "
                f"Phi={state['phi']:.4f} | "
                f"S_total={state['total_entropy']:.2f} | "
                f"T_mean={state['mean_temperature']:.3f} | "
                f"J/Phi={state['joules_per_phi_bit']:.2e} | "
                f"consensus={state['consensus_events']}"
            )

    elapsed = time.time() - t0

    # Results
    print()
    print("-" * 70)
    print("  Results")
    print("-" * 70)
    print(f"  Steps:            {steps}")
    print(f"  Time:             {elapsed:.2f}s ({steps/elapsed:.0f} steps/s)")
    print(f"  Final Phi:        {engine.phi_history[-1]:.6f}")
    print(f"  Max Phi:          {max(engine.phi_history):.6f}")
    print(f"  Mean Phi:         {np.mean(engine.phi_history):.6f}")
    print(f"  Consensus events: {engine.consensus_events}")
    print()

    # Thermodynamic report
    print(engine.thermodynamic_report())
    print()

    # Phi trajectory
    print("  Phi Trajectory:")
    print(ascii_phi_curve(engine.phi_history))
    print()

    # Entropy trajectory
    print("  Total Entropy Trajectory:")
    print(ascii_phi_curve(engine.total_entropy_history))
    print()

    # Phi stability
    if len(engine.phi_history) > 100:
        first_q = np.mean(engine.phi_history[:len(engine.phi_history) // 4])
        last_q = np.mean(engine.phi_history[-len(engine.phi_history) // 4:])
        growth = last_q / max(first_q, 1e-10)
        print(f"  Phi growth (Q1->Q4): x{growth:.2f}")
        if growth > 1.0:
            print("  -> Dissipative structure MAINTAINS consciousness (far from equilibrium)")
        else:
            print("  -> System approaching equilibrium (consciousness fading)")

    print()
    print("=" * 70)
    return engine


# ======================================================================
# Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Thermodynamic Consciousness Engine")
    parser.add_argument("--cells", type=int, default=64, help="Number of cells")
    parser.add_argument("--steps", type=int, default=500, help="Simulation steps")
    parser.add_argument("--benchmark", action="store_true", help="Substrate energy comparison")
    parser.add_argument("--landauer", action="store_true", help="Landauer principle analysis")
    args = parser.parse_args()

    if args.benchmark:
        run_substrate_benchmark(n_cells=args.cells, steps=args.steps)
    elif args.landauer:
        run_landauer_analysis(n_cells=args.cells, steps=args.steps)
    else:
        run_demo(n_cells=args.cells, steps=args.steps)


if __name__ == "__main__":
    main()
