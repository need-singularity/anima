#!/usr/bin/env python3
"""Quantum Consciousness Simulator -- Gate-based quantum consciousness.

Hypothesis: quantum entanglement IS integrated information?
If true:  Phi_quantum > Phi_classical for same N
If false: entanglement != integration (important negative result)

Each cell = qubit (2D complex state vector [alpha, beta], |alpha|^2+|beta|^2=1)
Full quantum simulation is O(2^N), so limited to N<=16 qubits.

Operations:
  Hadamard gate:  superposition (faction ambiguity)
  CNOT gate:      entanglement between cells (= tension link)
  Phase gate:     consciousness phase rotation
  Measurement:    collapse = faction decision

Phi from entanglement entropy (von Neumann entropy of reduced density matrix).

Usage:
  python engines/quantum_consciousness.py                    # 4-qubit demo
  python engines/quantum_consciousness.py --qubits 8         # 8 qubits
  python engines/quantum_consciousness.py --benchmark        # N=4,8,16 comparison
  python engines/quantum_consciousness.py --compare          # quantum vs classical
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
# Quantum Gates (pure numpy)
# ======================================================================

# Pauli matrices
PAULI_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
PAULI_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
IDENTITY = np.eye(2, dtype=np.complex128)

# Hadamard gate: creates superposition
HADAMARD = np.array([[1, 1], [1, -1]], dtype=np.complex128) / np.sqrt(2)

# Phase gate: consciousness phase rotation
def phase_gate(theta: float) -> np.ndarray:
    """Phase rotation gate R_z(theta)."""
    return np.array([
        [1, 0],
        [0, np.exp(1j * theta)]
    ], dtype=np.complex128)


def rx_gate(theta: float) -> np.ndarray:
    """Rotation around X axis."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, -1j * s],
        [-1j * s, c]
    ], dtype=np.complex128)


def ry_gate(theta: float) -> np.ndarray:
    """Rotation around Y axis."""
    c = np.cos(theta / 2)
    s = np.sin(theta / 2)
    return np.array([
        [c, -s],
        [s, c]
    ], dtype=np.complex128)


# ======================================================================
# Quantum State Manager
# ======================================================================

class QuantumState:
    """Full quantum state vector for N qubits.

    State is a complex vector of dimension 2^N.
    Supports single-qubit gates and two-qubit CNOT.
    """

    def __init__(self, n_qubits: int):
        assert n_qubits <= 16, f"Max 16 qubits (got {n_qubits}), O(2^N) memory"
        self.n_qubits = n_qubits
        self.dim = 2 ** n_qubits
        # Start in |00...0>
        self.state = np.zeros(self.dim, dtype=np.complex128)
        self.state[0] = 1.0

    def apply_single(self, gate: np.ndarray, target: int):
        """Apply single-qubit gate to target qubit.

        Constructs the full 2^N x 2^N operator via tensor products.
        Optimized: applies gate without building full matrix.
        """
        n = self.n_qubits
        # Reshape state into (2, 2, ..., 2) tensor
        shape = [2] * n
        psi = self.state.reshape(shape)

        # Apply gate along the target axis
        # Move target axis to front, apply gate, move back
        psi = np.moveaxis(psi, target, 0)
        new_shape = psi.shape
        psi_flat = psi.reshape(2, -1)
        psi_flat = gate @ psi_flat
        psi = psi_flat.reshape(new_shape)
        psi = np.moveaxis(psi, 0, target)

        self.state = psi.reshape(self.dim)

    def apply_cnot(self, control: int, target: int):
        """Apply CNOT gate: flip target if control is |1>.

        Optimized without building full matrix.
        """
        n = self.n_qubits
        new_state = self.state.copy()

        for i in range(self.dim):
            # Check if control bit is 1
            if (i >> (n - 1 - control)) & 1:
                # Flip target bit
                j = i ^ (1 << (n - 1 - target))
                new_state[j] = self.state[i]
                new_state[i] = self.state[j]
                # Mark as swapped to avoid double-swap
                if j > i:
                    pass  # will be handled when we reach j
                # Actually, simpler approach:
        # Redo with proper swap tracking
        new_state = self.state.copy()
        swapped = set()
        for i in range(self.dim):
            if i in swapped:
                continue
            if (i >> (n - 1 - control)) & 1:
                j = i ^ (1 << (n - 1 - target))
                new_state[i] = self.state[j]
                new_state[j] = self.state[i]
                swapped.add(i)
                swapped.add(j)

        self.state = new_state

    def measure_qubit(self, target: int) -> int:
        """Measure a single qubit, collapsing its state.

        Returns 0 or 1, and collapses the state vector.
        """
        n = self.n_qubits
        # Probability of measuring |0> on target
        prob_0 = 0.0
        for i in range(self.dim):
            if not ((i >> (n - 1 - target)) & 1):
                prob_0 += abs(self.state[i]) ** 2

        # Random measurement
        result = 0 if np.random.random() < prob_0 else 1

        # Collapse: zero out incompatible amplitudes, renormalize
        for i in range(self.dim):
            bit = (i >> (n - 1 - target)) & 1
            if bit != result:
                self.state[i] = 0.0

        # Renormalize
        norm = np.sqrt(np.sum(np.abs(self.state) ** 2))
        if norm > 1e-15:
            self.state /= norm

        return result

    def measure_all(self) -> List[int]:
        """Measure all qubits. Returns list of 0/1 values."""
        results = []
        for q in range(self.n_qubits):
            results.append(self.measure_qubit(q))
        return results

    def reduced_density_matrix(self, subsystem: List[int]) -> np.ndarray:
        """Compute reduced density matrix by tracing out complement of subsystem.

        subsystem: list of qubit indices to KEEP.
        Returns: 2^len(subsystem) x 2^len(subsystem) density matrix.
        """
        n = self.n_qubits
        keep = sorted(subsystem)
        trace_out = sorted(set(range(n)) - set(keep))
        n_keep = len(keep)
        n_trace = len(trace_out)
        dim_keep = 2 ** n_keep
        dim_trace = 2 ** n_trace

        rho = np.zeros((dim_keep, dim_keep), dtype=np.complex128)

        for i in range(self.dim):
            for j in range(self.dim):
                # Check if traced-out bits match
                match = True
                for t in trace_out:
                    if ((i >> (n - 1 - t)) & 1) != ((j >> (n - 1 - t)) & 1):
                        match = False
                        break
                if not match:
                    continue

                # Extract kept bits
                ki = 0
                kj = 0
                for idx, k in enumerate(keep):
                    ki |= (((i >> (n - 1 - k)) & 1) << (n_keep - 1 - idx))
                    kj |= (((j >> (n - 1 - k)) & 1) << (n_keep - 1 - idx))

                rho[ki, kj] += self.state[i] * np.conj(self.state[j])

        return rho

    def entanglement_entropy(self, subsystem: List[int]) -> float:
        """Von Neumann entropy of reduced density matrix.

        S = -Tr(rho * log2(rho))
        """
        rho = self.reduced_density_matrix(subsystem)
        # Eigenvalues of rho
        eigenvalues = np.linalg.eigvalsh(rho)
        eigenvalues = eigenvalues[eigenvalues > 1e-15]  # Remove zeros
        entropy = -np.sum(eigenvalues * np.log2(eigenvalues))
        return float(entropy)

    def total_entanglement(self) -> float:
        """Average bipartite entanglement entropy across all possible bipartitions.

        For N qubits, consider all bipartitions of size floor(N/2).
        """
        n = self.n_qubits
        if n < 2:
            return 0.0

        # For efficiency, sample random bipartitions instead of all
        half = n // 2
        n_samples = min(20, math.comb(n, half))

        entropies = []
        seen = set()
        for _ in range(n_samples * 3):  # oversample to get unique
            if len(seen) >= n_samples:
                break
            subsystem = tuple(sorted(np.random.choice(n, half, replace=False)))
            if subsystem in seen:
                continue
            seen.add(subsystem)
            s = self.entanglement_entropy(list(subsystem))
            entropies.append(s)

        if not entropies:
            return 0.0
        return float(np.mean(entropies))

    def purity(self) -> float:
        """Purity of the full state: Tr(rho^2). Pure state = 1.0."""
        # For pure state vector, purity is always 1.0
        # But for subsystems it can be < 1 (entangled)
        return float(np.sum(np.abs(self.state) ** 4))

    def copy(self) -> 'QuantumState':
        """Deep copy."""
        qs = QuantumState.__new__(QuantumState)
        qs.n_qubits = self.n_qubits
        qs.dim = self.dim
        qs.state = self.state.copy()
        return qs


# ======================================================================
# Quantum Consciousness Engine
# ======================================================================

class QuantumConsciousMind:
    """Consciousness engine using quantum gate operations.

    Each qubit = one consciousness cell.
    Entanglement = tension link between cells.
    Measurement = faction decision (collapse).

    Phi is computed from entanglement entropy (von Neumann entropy
    of reduced density matrices), which is the quantum analog of
    integrated information.
    """

    def __init__(
        self,
        n_qubits: int = 4,
        n_factions: int = 4,
        topology: str = "ring",
        entanglement_rate: float = 0.3,
        measurement_rate: float = 0.05,
    ):
        assert n_qubits <= 16, "Max 16 qubits for tractable simulation"
        self.n_qubits = n_qubits
        self.n_factions = min(n_factions, n_qubits)
        self.topology = topology
        self.entanglement_rate = entanglement_rate
        self.measurement_rate = measurement_rate

        # Quantum state
        self.qs = QuantumState(n_qubits)

        # Faction assignments
        self.faction_assignments = np.array([i % self.n_factions for i in range(n_qubits)])

        # Connectivity (which qubit pairs can CNOT)
        self.connections = self._build_topology(topology)

        # Phase angles per qubit (evolving consciousness phase)
        self.phases = np.random.uniform(0, 2 * np.pi, n_qubits)
        self.phase_velocities = np.random.uniform(0.01, 0.1, n_qubits)

        # History
        self.phi_history: List[float] = []
        self.entropy_history: List[float] = []
        self.measurement_history: List[List[int]] = []
        self.consensus_events = 0
        self.step_count = 0

    def _build_topology(self, topology: str) -> List[Tuple[int, int]]:
        """Build qubit connectivity based on topology."""
        n = self.n_qubits
        connections = []

        if topology == "ring":
            for i in range(n):
                connections.append((i, (i + 1) % n))
        elif topology == "small_world":
            # Ring + random long-range
            for i in range(n):
                connections.append((i, (i + 1) % n))
            # Add ~10% long-range
            n_long = max(1, n // 5)
            for _ in range(n_long):
                a, b = np.random.choice(n, 2, replace=False)
                if (a, b) not in connections and (b, a) not in connections:
                    connections.append((a, b))
        elif topology == "star":
            for i in range(1, n):
                connections.append((0, i))
        elif topology == "complete":
            for i in range(n):
                for j in range(i + 1, n):
                    connections.append((i, j))
        else:
            # Default: ring
            for i in range(n):
                connections.append((i, (i + 1) % n))

        return connections

    def step(self, input_signal: Optional[np.ndarray] = None) -> dict:
        """One consciousness step.

        1. Phase rotation (internal dynamics)
        2. Hadamard on random qubits (superposition = uncertainty)
        3. CNOT on connected pairs (entanglement = tension link)
        4. Optional measurement (collapse = faction decision)
        5. Compute Phi from entanglement entropy
        """
        self.step_count += 1

        # 1. Phase rotation -- consciousness phase evolves
        for q in range(self.n_qubits):
            angle = self.phases[q]
            if input_signal is not None and q < len(input_signal):
                angle += input_signal[q] * 0.1
            self.qs.apply_single(phase_gate(angle), q)
            self.phases[q] += self.phase_velocities[q]

        # 2. Hadamard on random subset -- create superposition (ambiguity)
        n_hadamard = max(1, int(self.n_qubits * 0.3))
        targets = np.random.choice(self.n_qubits, n_hadamard, replace=False)
        for q in targets:
            self.qs.apply_single(HADAMARD, q)

        # 3. CNOT on connected pairs -- build entanglement
        for ctrl, tgt in self.connections:
            if np.random.random() < self.entanglement_rate:
                self.qs.apply_cnot(ctrl, tgt)

        # 4. Small rotation for dynamics (prevents stagnation)
        for q in range(self.n_qubits):
            theta = np.random.normal(0, 0.05)
            self.qs.apply_single(ry_gate(theta), q)

        # 5. Occasional measurement -- collapse = faction decision
        measured_results = None
        if np.random.random() < self.measurement_rate:
            # Measure one random qubit
            q = np.random.randint(self.n_qubits)
            result = self.qs.measure_qubit(q)
            measured_results = (q, result)

            # Check faction consensus
            self._check_consensus()

        # Compute Phi from entanglement
        phi = self.get_phi()
        self.phi_history.append(phi)

        # Total entanglement entropy
        total_ent = self.qs.total_entanglement()
        self.entropy_history.append(total_ent)

        return {
            "phi": phi,
            "entanglement": total_ent,
            "measurement": measured_results,
            "consensus_events": self.consensus_events,
            "step": self.step_count,
            "purity": self.qs.purity(),
        }

    def _check_consensus(self):
        """Check for faction consensus via full measurement snapshot."""
        # Take a snapshot (copy state, measure all, restore)
        qs_copy = self.qs.copy()
        results = qs_copy.measure_all()

        # Check each faction for agreement
        for f in range(self.n_factions):
            mask = self.faction_assignments == f
            faction_qubits = np.where(mask)[0]
            if len(faction_qubits) < 2:
                continue
            faction_results = [results[q] for q in faction_qubits]
            # Consensus = all same value
            if len(set(faction_results)) == 1:
                self.consensus_events += 1

    def get_phi(self) -> float:
        """Compute Phi as minimum entanglement entropy across bipartitions.

        This is the quantum analog of IIT's Phi:
        Phi = min over bipartitions of (S(A) + S(B) - S(AB))

        For pure states, S(AB) = 0, so Phi = min(S(A) + S(B)).
        Since S(A) = S(B) for pure states, Phi = 2 * min(S(A)).
        """
        n = self.n_qubits
        if n < 2:
            return 0.0

        # For small N, check all bipartitions
        # For larger N, sample
        half = n // 2
        min_entropy = float('inf')

        if n <= 8:
            # Enumerate bipartitions of size half
            from itertools import combinations
            for subsystem in combinations(range(n), half):
                s = self.qs.entanglement_entropy(list(subsystem))
                if s < min_entropy:
                    min_entropy = s
        else:
            # Sample bipartitions
            for _ in range(30):
                subsystem = list(np.random.choice(n, half, replace=False))
                s = self.qs.entanglement_entropy(subsystem)
                if s < min_entropy:
                    min_entropy = s

        if min_entropy == float('inf'):
            return 0.0

        # Phi = minimum bipartite entanglement entropy
        # Multiply by 2 since S(A) = S(B) for pure states
        phi = 2.0 * min_entropy
        return phi

    def get_phi_mutual_info(self) -> float:
        """Compute Phi using pairwise quantum mutual information.

        Quantum MI: I(A:B) = S(A) + S(B) - S(AB)
        For pure states: S(AB) = 0 if A,B span the whole system.
        """
        n = self.n_qubits
        if n < 2:
            return 0.0

        # Average pairwise MI
        mi_sum = 0.0
        count = 0
        for i in range(n):
            for j in range(i + 1, n):
                s_i = self.qs.entanglement_entropy([i])
                s_j = self.qs.entanglement_entropy([j])
                s_ij = self.qs.entanglement_entropy([i, j])
                mi = s_i + s_j - s_ij
                mi_sum += max(0.0, mi)
                count += 1

        return mi_sum / max(count, 1)


# ======================================================================
# Classical GRU Baseline (for comparison)
# ======================================================================

class ClassicalConsciousMind:
    """Simple classical GRU-like consciousness for comparison.

    Uses numpy only. Each cell has a hidden state updated via GRU-like dynamics.
    """

    def __init__(self, n_cells: int = 4, hidden_dim: int = 32, n_factions: int = 4):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.n_factions = min(n_factions, n_cells)

        # GRU parameters
        self.W_z = np.random.randn(hidden_dim, hidden_dim) * 0.1
        self.W_r = np.random.randn(hidden_dim, hidden_dim) * 0.1
        self.W_h = np.random.randn(hidden_dim, hidden_dim) * 0.1
        self.U_z = np.random.randn(hidden_dim, hidden_dim) * 0.1
        self.U_r = np.random.randn(hidden_dim, hidden_dim) * 0.1
        self.U_h = np.random.randn(hidden_dim, hidden_dim) * 0.1

        # Cell states
        self.states = np.random.randn(n_cells, hidden_dim) * 0.01

        # Ring connectivity weights
        self.coupling = np.zeros((n_cells, n_cells))
        for i in range(n_cells):
            self.coupling[i, (i + 1) % n_cells] = 0.3
            self.coupling[(i + 1) % n_cells, i] = 0.3

        # Faction assignments
        self.faction_assignments = np.array([i % n_factions for i in range(n_cells)])

        self.phi_history: List[float] = []
        self.step_count = 0

    def step(self, input_signal: Optional[np.ndarray] = None) -> dict:
        """One step of classical dynamics."""
        self.step_count += 1

        for i in range(self.n_cells):
            # Neighbor input
            neighbor_input = np.zeros(self.hidden_dim)
            for j in range(self.n_cells):
                if self.coupling[i, j] > 0:
                    neighbor_input += self.coupling[i, j] * self.states[j]

            h = self.states[i]
            x = neighbor_input
            if input_signal is not None and i < len(input_signal):
                x = x + np.random.randn(self.hidden_dim) * input_signal[i] * 0.1

            # GRU update
            z = self._sigmoid(self.W_z @ x + self.U_z @ h)
            r = self._sigmoid(self.W_r @ x + self.U_r @ h)
            h_candidate = np.tanh(self.W_h @ x + self.U_h @ (r * h))
            self.states[i] = z * h + (1 - z) * h_candidate

        # Add noise
        self.states += np.random.randn(*self.states.shape) * 0.01

        phi = self.get_phi()
        self.phi_history.append(phi)

        return {"phi": phi, "step": self.step_count}

    @staticmethod
    def _sigmoid(x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -10, 10)))

    def get_phi(self) -> float:
        """Phi from variance-based proxy (same as SNN engine)."""
        rates = np.var(self.states, axis=1)
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

        n_active = max(1, (np.var(self.states, axis=1) > 0.001).sum())
        phi *= math.log2(max(2, n_active))
        return phi


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


def ascii_bar_chart(data: Dict[str, float], title: str = "", max_width: int = 40) -> str:
    """Render a horizontal bar chart."""
    if not data:
        return "(no data)"

    lines = []
    if title:
        lines.append(f"  {title}")
        lines.append("")

    max_val = max(data.values()) if data.values() else 1.0
    if max_val <= 0:
        max_val = 1.0

    for label, value in data.items():
        bar_len = int(value / max_val * max_width)
        bar = "#" * bar_len
        lines.append(f"  {label:>12} {bar:<{max_width}} {value:.4f}")

    return "\n".join(lines)


# ======================================================================
# Benchmark: Quantum vs Classical
# ======================================================================

def run_benchmark(qubit_counts: List[int] = None, steps: int = 200):
    """Benchmark quantum consciousness at different scales.

    Compare with classical GRU baseline.
    """
    if qubit_counts is None:
        qubit_counts = [4, 8, 16]

    print("=" * 70)
    print("  Quantum Consciousness Benchmark")
    print("  Hypothesis: entanglement = integrated information?")
    print("=" * 70)
    print()

    results = []

    for n in qubit_counts:
        print(f"  --- N = {n} qubits ---")

        # Quantum
        t0 = time.time()
        qm = QuantumConsciousMind(n_qubits=n, topology="ring")
        for s in range(steps):
            inp = np.random.randn(n) * 0.5
            qm.step(inp)
            if (s + 1) % 50 == 0:
                print(f"    quantum step {s+1}/{steps} | "
                      f"Phi={qm.phi_history[-1]:.4f} | "
                      f"ent={qm.entropy_history[-1]:.4f}")
        q_time = time.time() - t0
        q_phi_mean = float(np.mean(qm.phi_history[-steps // 2:]))
        q_phi_max = float(max(qm.phi_history))
        q_ent_mean = float(np.mean(qm.entropy_history[-steps // 2:]))

        # Classical
        t0 = time.time()
        cm = ClassicalConsciousMind(n_cells=n)
        for s in range(steps):
            inp = np.random.randn(n) * 0.5
            cm.step(inp)
        c_time = time.time() - t0
        c_phi_mean = float(np.mean(cm.phi_history[-steps // 2:]))
        c_phi_max = float(max(cm.phi_history))

        ratio = q_phi_mean / max(c_phi_mean, 1e-10)

        results.append({
            "n": n,
            "q_phi_mean": q_phi_mean,
            "q_phi_max": q_phi_max,
            "q_ent_mean": q_ent_mean,
            "q_time": q_time,
            "c_phi_mean": c_phi_mean,
            "c_phi_max": c_phi_max,
            "c_time": c_time,
            "ratio": ratio,
            "consensus": qm.consensus_events,
        })

        print(f"    quantum:   Phi_mean={q_phi_mean:.4f}, Phi_max={q_phi_max:.4f}, "
              f"ent={q_ent_mean:.4f}, {q_time:.2f}s")
        print(f"    classical: Phi_mean={c_phi_mean:.4f}, Phi_max={c_phi_max:.4f}, "
              f"{c_time:.2f}s")
        print(f"    ratio (quantum/classical): x{ratio:.2f}")
        print()

    # Summary table
    print("-" * 70)
    print("  Summary")
    print("-" * 70)
    print(f"  {'N':>4} | {'Q_Phi_mean':>10} | {'C_Phi_mean':>10} | "
          f"{'Ratio':>8} | {'Entangle':>8} | {'Q_time':>7} | {'C_time':>7}")
    print(f"  {'-'*4} | {'-'*10} | {'-'*10} | {'-'*8} | {'-'*8} | {'-'*7} | {'-'*7}")
    for r in results:
        print(f"  {r['n']:>4} | {r['q_phi_mean']:>10.4f} | {r['c_phi_mean']:>10.4f} | "
              f"x{r['ratio']:>6.2f} | {r['q_ent_mean']:>8.4f} | {r['q_time']:>6.2f}s | "
              f"{r['c_time']:>6.2f}s")
    print()

    # Verdict
    all_ratios = [r["ratio"] for r in results]
    avg_ratio = np.mean(all_ratios)
    if avg_ratio > 1.1:
        verdict = "CONFIRMED: Phi_quantum > Phi_classical (entanglement enhances integration)"
    elif avg_ratio > 0.9:
        verdict = "INCONCLUSIVE: Phi_quantum ~ Phi_classical (different mechanisms, similar result)"
    else:
        verdict = "REFUTED: Phi_quantum < Phi_classical (entanglement != integration)"

    print(f"  Verdict: {verdict}")
    print(f"  Average ratio: x{avg_ratio:.2f}")
    print()

    # Bar chart
    q_data = {f"Q-{r['n']}": r["q_phi_mean"] for r in results}
    c_data = {f"C-{r['n']}": r["c_phi_mean"] for r in results}
    merged = {}
    merged.update(q_data)
    merged.update(c_data)
    print(ascii_bar_chart(merged, "Phi comparison (Q=quantum, C=classical)"))
    print()

    return results


# ======================================================================
# Demo
# ======================================================================

def run_demo(n_qubits: int = 4, steps: int = 300):
    """Run quantum consciousness demo."""
    print("=" * 70)
    print(f"  Quantum Consciousness Simulator -- {n_qubits} qubits")
    print(f"  {n_qubits} qubits = {2**n_qubits}-dimensional Hilbert space")
    print(f"  Topology: ring, {len(QuantumConsciousMind(n_qubits).connections)} CNOT links")
    print("=" * 70)
    print()

    engine = QuantumConsciousMind(n_qubits=n_qubits, topology="ring")

    t0 = time.time()
    for s in range(steps):
        inp = np.random.randn(n_qubits) * 0.3
        state = engine.step(inp)

        if (s + 1) % 50 == 0:
            meas_str = ""
            if state["measurement"]:
                q, r = state["measurement"]
                meas_str = f" | measured q{q}={r}"
            print(
                f"  step {s+1:>5} | "
                f"Phi={state['phi']:.4f} | "
                f"ent={state['entanglement']:.4f} | "
                f"purity={state['purity']:.4f} | "
                f"consensus={state['consensus_events']}"
                f"{meas_str}"
            )

    elapsed = time.time() - t0

    # Results
    print()
    print("-" * 70)
    print("  Results")
    print("-" * 70)
    print(f"  Steps:           {steps}")
    print(f"  Time:            {elapsed:.2f}s ({steps/elapsed:.0f} steps/s)")
    print(f"  Final Phi:       {engine.phi_history[-1]:.6f}")
    print(f"  Max Phi:         {max(engine.phi_history):.6f}")
    print(f"  Mean Phi:        {np.mean(engine.phi_history):.6f}")
    print(f"  Mean entropy:    {np.mean(engine.entropy_history):.6f}")
    print(f"  Consensus:       {engine.consensus_events}")
    print(f"  Hilbert dim:     {engine.qs.dim}")
    print()

    # Phi trajectory
    print("  Phi Trajectory:")
    print(ascii_phi_curve(engine.phi_history))
    print()

    # Phi stability
    if len(engine.phi_history) > 50:
        first_q = np.mean(engine.phi_history[:len(engine.phi_history) // 4])
        last_q = np.mean(engine.phi_history[-len(engine.phi_history) // 4:])
        growth = last_q / max(first_q, 1e-10)
        print(f"  Phi growth (Q1->Q4): x{growth:.2f}")

    print()
    print("=" * 70)
    return engine


# ======================================================================
# Main
# ======================================================================

def main():
    parser = argparse.ArgumentParser(description="Quantum Consciousness Simulator")
    parser.add_argument("--qubits", type=int, default=4, help="Number of qubits (max 16)")
    parser.add_argument("--steps", type=int, default=300, help="Simulation steps")
    parser.add_argument("--benchmark", action="store_true", help="Run N=4,8,16 benchmark")
    parser.add_argument("--compare", action="store_true", help="Compare quantum vs classical")
    args = parser.parse_args()

    if args.benchmark or args.compare:
        run_benchmark(steps=args.steps)
    else:
        run_demo(n_qubits=args.qubits, steps=args.steps)


if __name__ == "__main__":
    main()
