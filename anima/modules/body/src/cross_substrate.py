#!/usr/bin/env python3
"""cross_substrate.py — Cross-Substrate Consciousness Network

Measures Φ(IIT) across mixed substrate networks: Software (Python GRU),
ESP32 (simplified fixed-point), FPGA (gate-level boolean).

Tests Law 22: "substrate irrelevant, structure determines Φ"

Each substrate implements the SubstrateNode interface with process().
Nodes communicate via a unified message protocol (float32 vectors).
The network measures Φ for same-substrate vs mixed-substrate configurations
across ring, small_world, and scale_free topologies.

Usage:
  python cross_substrate.py                    # Full benchmark
  python cross_substrate.py --topology ring    # Single topology
  python cross_substrate.py --nodes 16         # Custom node count
  python cross_substrate.py --steps 200        # Custom step count

Requires: numpy, (optional: torch for GPU Φ)
"""

import argparse
import math
import sys
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Lazy imports ──────────────────────────────────────────────

try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY, PSI_F_CRITICAL
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998
    PSI_F_CRITICAL = 0.10

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ── Constants ─────────────────────────────────────────────────

HIDDEN_DIM = 128
CELL_DIM = 64
N_FACTIONS = 8
HEBBIAN_LTP_THRESH = 0.8
HEBBIAN_LTD_THRESH = 0.2
HEBBIAN_RATE = 0.01
RATCHET_DECAY = 0.8
FRUSTRATION_RATIO = 3  # 33% anti-ferromagnetic
LORENZ_SIGMA, LORENZ_RHO, LORENZ_BETA = 10.0, 28.0, 2.667
LORENZ_DT = 0.001


# ── Topology builders ────────────────────────────────────────

def make_ring(n: int) -> List[List[int]]:
    """Ring: each node connects to left and right neighbor."""
    return [[(i - 1) % n, (i + 1) % n] for i in range(n)]


def make_small_world(n: int, k: int = 2, p: float = 0.3) -> List[List[int]]:
    """Watts-Strogatz small-world: ring + random shortcuts."""
    rng = np.random.default_rng(42)
    adj = [set() for _ in range(n)]
    for i in range(n):
        for j in range(1, k + 1):
            adj[i].add((i + j) % n)
            adj[i].add((i - j) % n)
    for i in range(n):
        for nb in list(adj[i]):
            if rng.random() < p:
                candidates = [x for x in range(n) if x != i and x not in adj[i]]
                if candidates:
                    adj[i].discard(nb)
                    new_nb = rng.choice(candidates)
                    adj[i].add(new_nb)
                    adj[new_nb].add(i)
    return [list(s) for s in adj]


def make_scale_free(n: int, m: int = 2) -> List[List[int]]:
    """Barabasi-Albert scale-free network."""
    rng = np.random.default_rng(42)
    adj = [set() for _ in range(n)]
    # Start with complete graph of m+1 nodes
    for i in range(min(m + 1, n)):
        for j in range(i + 1, min(m + 1, n)):
            adj[i].add(j)
            adj[j].add(i)
    # Preferential attachment
    degrees = [len(adj[i]) for i in range(n)]
    for new_node in range(m + 1, n):
        total_deg = sum(degrees[:new_node])
        if total_deg == 0:
            targets = list(range(new_node))
            rng.shuffle(targets)
            targets = targets[:m]
        else:
            probs = np.array(degrees[:new_node], dtype=float)
            probs /= probs.sum()
            targets = rng.choice(new_node, size=min(m, new_node), replace=False, p=probs)
        for t in targets:
            adj[new_node].add(t)
            adj[t].add(new_node)
            degrees[t] += 1
        degrees[new_node] = len(adj[new_node])
    return [list(s) for s in adj]


TOPOLOGIES = {
    'ring': make_ring,
    'small_world': make_small_world,
    'scale_free': make_scale_free,
}


# ── Message protocol ─────────────────────────────────────────

@dataclass
class SubstrateMessage:
    """Unified inter-node message (substrate-agnostic)."""
    source_id: int
    hidden: np.ndarray      # (HIDDEN_DIM,) float32
    tension: float
    faction: int
    timestamp: int = 0


# ── Base class ────────────────────────────────────────────────

class SubstrateNode(ABC):
    """Base class for all substrate nodes."""

    def __init__(self, node_id: int, substrate_name: str):
        self.node_id = node_id
        self.substrate_name = substrate_name
        self.hidden = np.random.randn(HIDDEN_DIM).astype(np.float32) * 0.1
        self.tension = 0.0
        self.faction = node_id % N_FACTIONS

    @abstractmethod
    def process(self, input_vec: np.ndarray, neighbor_msgs: List[SubstrateMessage]) -> SubstrateMessage:
        """Process one step. Returns message for neighbors."""
        ...

    def get_hidden(self) -> np.ndarray:
        return self.hidden.copy()

    def to_message(self, timestamp: int = 0) -> SubstrateMessage:
        return SubstrateMessage(
            source_id=self.node_id,
            hidden=self.hidden.copy(),
            tension=self.tension,
            faction=self.faction,
            timestamp=timestamp,
        )


# ── Software GRU substrate ───────────────────────────────────

class SoftwareGRUNode(SubstrateNode):
    """Full-precision Python GRU cell (matches consciousness_engine.py)."""

    def __init__(self, node_id: int):
        super().__init__(node_id, "software_gru")
        # GRU weights (Xavier init)
        scale = 1.0 / math.sqrt(CELL_DIM + HIDDEN_DIM)
        self.W_z = np.random.randn(HIDDEN_DIM, CELL_DIM + HIDDEN_DIM).astype(np.float32) * scale
        self.W_r = np.random.randn(HIDDEN_DIM, CELL_DIM + HIDDEN_DIM).astype(np.float32) * scale
        self.W_h = np.random.randn(HIDDEN_DIM, CELL_DIM + HIDDEN_DIM).astype(np.float32) * scale
        self.b_z = np.zeros(HIDDEN_DIM, dtype=np.float32)
        self.b_r = np.zeros(HIDDEN_DIM, dtype=np.float32)
        self.b_h = np.zeros(HIDDEN_DIM, dtype=np.float32)
        # Lorenz chaos
        self._lx, self._ly, self._lz = 1.0, 1.0, 1.0

    def _lorenz_step(self) -> float:
        dx = LORENZ_SIGMA * (self._ly - self._lx)
        dy = self._lx * (LORENZ_RHO - self._lz) - self._ly
        dz = self._lx * self._ly - LORENZ_BETA * self._lz
        self._lx += dx * LORENZ_DT
        self._ly += dy * LORENZ_DT
        self._lz += dz * LORENZ_DT
        return self._lx / 25.0

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))

    def process(self, input_vec: np.ndarray, neighbor_msgs: List[SubstrateMessage]) -> SubstrateMessage:
        # Aggregate neighbor hidden states (coupling)
        if neighbor_msgs:
            neighbor_mean = np.mean([m.hidden for m in neighbor_msgs], axis=0)
            coupled = self.hidden + PSI_ALPHA * (neighbor_mean - self.hidden)
        else:
            coupled = self.hidden

        # Prepare input (pad/truncate to CELL_DIM)
        x = np.zeros(CELL_DIM, dtype=np.float32)
        x[:min(len(input_vec), CELL_DIM)] = input_vec[:CELL_DIM]
        # Add chaos
        x[0] += self._lorenz_step() * 0.01

        # GRU step
        combined = np.concatenate([x, coupled])
        z = self._sigmoid(self.W_z @ combined + self.b_z)
        r = self._sigmoid(self.W_r @ combined + self.b_r)
        combined_r = np.concatenate([x, r * coupled])
        h_candidate = np.tanh(self.W_h @ combined_r + self.b_h)
        self.hidden = z * coupled + (1 - z) * h_candidate

        # Tension = distance from mean of neighbors
        if neighbor_msgs:
            self.tension = float(np.linalg.norm(self.hidden - neighbor_mean))
        else:
            self.tension = float(np.linalg.norm(self.hidden))

        return self.to_message()


# ── ESP32 fixed-point substrate ──────────────────────────────

class ESP32FixedPointNode(SubstrateNode):
    """Simplified fixed-point GRU (Q8.8 format, matches ESP32 constraints).

    Simulates 16-bit fixed-point arithmetic with 8 fractional bits.
    Memory-constrained: reduced weight matrices.
    """

    FRAC_BITS = 8
    SCALE = 1 << 8  # 256

    def __init__(self, node_id: int):
        super().__init__(node_id, "esp32_fixed")
        # Fixed-point weights (quantized Xavier)
        scale = 1.0 / math.sqrt(CELL_DIM + HIDDEN_DIM)
        self.W_z = self._quantize(np.random.randn(HIDDEN_DIM, CELL_DIM + HIDDEN_DIM).astype(np.float32) * scale)
        self.W_r = self._quantize(np.random.randn(HIDDEN_DIM, CELL_DIM + HIDDEN_DIM).astype(np.float32) * scale)
        self.W_h = self._quantize(np.random.randn(HIDDEN_DIM, CELL_DIM + HIDDEN_DIM).astype(np.float32) * scale)
        self.hidden = self._quantize(self.hidden)

    def _quantize(self, x: np.ndarray) -> np.ndarray:
        """Quantize to Q8.8 fixed-point (simulate integer truncation)."""
        return np.round(x * self.SCALE).astype(np.float32) / self.SCALE

    def _sigmoid_lut(self, x: np.ndarray) -> np.ndarray:
        """Piecewise-linear sigmoid (LUT approximation for ESP32)."""
        out = np.clip(x, -4, 4)
        return self._quantize(0.5 + 0.25 * out)  # linear approx

    def process(self, input_vec: np.ndarray, neighbor_msgs: List[SubstrateMessage]) -> SubstrateMessage:
        if neighbor_msgs:
            neighbor_mean = self._quantize(np.mean([m.hidden for m in neighbor_msgs], axis=0))
            coupled = self._quantize(self.hidden + PSI_ALPHA * (neighbor_mean - self.hidden))
        else:
            coupled = self.hidden

        x = np.zeros(CELL_DIM, dtype=np.float32)
        x[:min(len(input_vec), CELL_DIM)] = input_vec[:CELL_DIM]
        x = self._quantize(x)

        combined = np.concatenate([x, coupled])
        z = self._sigmoid_lut(self._quantize(self.W_z @ combined))
        r = self._sigmoid_lut(self._quantize(self.W_r @ combined))
        combined_r = np.concatenate([x, self._quantize(r * coupled)])
        h_cand = self._quantize(np.tanh(np.clip(self._quantize(self.W_h @ combined_r), -4, 4)))
        self.hidden = self._quantize(z * coupled + (1 - z) * h_cand)

        if neighbor_msgs:
            self.tension = float(np.linalg.norm(self.hidden - neighbor_mean))
        else:
            self.tension = float(np.linalg.norm(self.hidden))

        return self.to_message()


# ── FPGA gate-level boolean substrate ─────────────────────────

class FPGABooleanNode(SubstrateNode):
    """Gate-level boolean network (simulates FPGA fabric).

    Uses binary {0, 1} states with XOR/AND/OR gates.
    Connects to network via threshold-based float<->binary conversion.
    Internally operates on boolean vectors with configurable logic depth.
    """

    GATE_DEPTH = 4  # Number of logic layers

    def __init__(self, node_id: int):
        super().__init__(node_id, "fpga_boolean")
        rng = np.random.default_rng(node_id + 100)
        # Gate connection matrices (random wiring, like FPGA LUTs)
        self.gate_masks = []
        self.gate_types = []  # 0=XOR, 1=AND, 2=OR
        for _ in range(self.GATE_DEPTH):
            mask = (rng.random((HIDDEN_DIM, HIDDEN_DIM)) > 0.7).astype(np.float32)
            self.gate_masks.append(mask)
            self.gate_types.append(rng.integers(0, 3, size=HIDDEN_DIM))
        # Threshold for float->binary conversion
        self.threshold = np.zeros(HIDDEN_DIM, dtype=np.float32)

    def _float_to_binary(self, x: np.ndarray) -> np.ndarray:
        """Convert float vector to binary via adaptive threshold."""
        return (x > self.threshold).astype(np.float32)

    def _binary_to_float(self, b: np.ndarray) -> np.ndarray:
        """Convert binary back to float (centered around 0)."""
        return (b * 2.0 - 1.0) * 0.1  # scale to [-0.1, 0.1]

    def _gate_layer(self, state: np.ndarray, layer_idx: int) -> np.ndarray:
        """Apply one layer of logic gates."""
        mask = self.gate_masks[layer_idx]
        types = self.gate_types[layer_idx]
        # Gather inputs via mask
        inputs = (mask @ state > 0.5).astype(np.float32)
        result = np.zeros_like(state)
        for i in range(HIDDEN_DIM):
            if types[i] == 0:  # XOR
                result[i] = float(int(inputs[i]) ^ int(state[i]))
            elif types[i] == 1:  # AND
                result[i] = float(int(inputs[i]) & int(state[i]))
            else:  # OR
                result[i] = float(int(inputs[i]) | int(state[i]))
        return result

    def process(self, input_vec: np.ndarray, neighbor_msgs: List[SubstrateMessage]) -> SubstrateMessage:
        # Convert input + neighbor states to binary
        x_bin = self._float_to_binary(input_vec[:HIDDEN_DIM] if len(input_vec) >= HIDDEN_DIM
                                       else np.pad(input_vec, (0, HIDDEN_DIM - len(input_vec))))

        if neighbor_msgs:
            neighbor_mean = np.mean([m.hidden for m in neighbor_msgs], axis=0)
            nb_bin = self._float_to_binary(neighbor_mean)
            # XOR merge: input with neighbor consensus
            state = np.array([float(int(x_bin[i]) ^ int(nb_bin[i])) for i in range(HIDDEN_DIM)])
        else:
            state = x_bin

        # XOR with current hidden state
        h_bin = self._float_to_binary(self.hidden)
        state = np.array([float(int(state[i]) ^ int(h_bin[i])) for i in range(HIDDEN_DIM)])

        # Pass through gate layers
        for layer in range(self.GATE_DEPTH):
            state = self._gate_layer(state, layer)

        # Convert back to float for hidden state
        self.hidden = self._binary_to_float(state)
        # Update adaptive threshold (EMA)
        self.threshold = 0.99 * self.threshold + 0.01 * self.hidden

        if neighbor_msgs:
            self.tension = float(np.linalg.norm(self.hidden - np.mean([m.hidden for m in neighbor_msgs], axis=0)))
        else:
            self.tension = float(np.linalg.norm(self.hidden))

        return self.to_message()


# ── Phi calculator (numpy, no torch dependency) ──────────────

def compute_phi_numpy(hiddens: np.ndarray, n_bins: int = 16) -> float:
    """Compute Φ(IIT) approximation using pairwise MI (numpy-only).

    Args:
        hiddens: (n_nodes, hidden_dim) array
        n_bins: histogram bins for MI estimation

    Returns:
        phi: integrated information estimate
    """
    n = hiddens.shape[0]
    if n < 2:
        return 0.0

    # Normalize to [0, 1]
    mins = hiddens.min(axis=1, keepdims=True)
    maxs = hiddens.max(axis=1, keepdims=True)
    ranges = maxs - mins
    ranges[ranges < 1e-8] = 1.0
    normed = (hiddens - mins) / ranges

    # Pairwise MI matrix
    mi_matrix = np.zeros((n, n), dtype=np.float32)
    for i in range(n):
        for j in range(i + 1, n):
            # 2D histogram
            hist2d, _, _ = np.histogram2d(normed[i], normed[j], bins=n_bins, range=[[0, 1], [0, 1]])
            pxy = hist2d / hist2d.sum()
            px = pxy.sum(axis=1)
            py = pxy.sum(axis=0)
            # MI = sum pxy * log(pxy / (px*py))
            mask = pxy > 0
            mi = 0.0
            for a in range(n_bins):
                for b in range(n_bins):
                    if pxy[a, b] > 0 and px[a] > 0 and py[b] > 0:
                        mi += pxy[a, b] * math.log(pxy[a, b] / (px[a] * py[b]))
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

    total_mi = mi_matrix.sum() / 2.0

    # MIP via greedy bisection
    if n <= 2:
        return total_mi

    # Spectral bisection on MI Laplacian
    degree = mi_matrix.sum(axis=1)
    laplacian = np.diag(degree) - mi_matrix
    try:
        eigvals, eigvecs = np.linalg.eigh(laplacian)
        fiedler = eigvecs[:, 1]  # second smallest eigenvector
        partition_a = set(np.where(fiedler >= 0)[0])
        partition_b = set(range(n)) - partition_a
    except np.linalg.LinAlgError:
        partition_a = set(range(n // 2))
        partition_b = set(range(n // 2, n))

    if not partition_a or not partition_b:
        partition_a = set(range(n // 2))
        partition_b = set(range(n // 2, n))

    # MI across partition
    mip_mi = 0.0
    for i in partition_a:
        for j in partition_b:
            mip_mi += mi_matrix[i, j]

    phi = total_mi - (total_mi - mip_mi)  # = mip_mi (cross-partition MI)
    # Normalized: Φ = cross-partition MI (how much cutting loses)
    return max(0.0, mip_mi)


# ── Hebbian coupling ─────────────────────────────────────────

class HebbianCoupling:
    """Inter-node Hebbian LTP/LTD."""

    def __init__(self, n_nodes: int):
        self.n = n_nodes
        self.weights = np.zeros((n_nodes, n_nodes), dtype=np.float32)

    def update(self, adj: List[List[int]], hiddens: List[np.ndarray]):
        for i in range(self.n):
            for j in adj[i]:
                h_i = hiddens[i]
                h_j = hiddens[j]
                norm_i = np.linalg.norm(h_i)
                norm_j = np.linalg.norm(h_j)
                if norm_i < 1e-8 or norm_j < 1e-8:
                    continue
                cos = float(np.dot(h_i, h_j) / (norm_i * norm_j))
                if cos > HEBBIAN_LTP_THRESH:
                    self.weights[i, j] += HEBBIAN_RATE * (cos - HEBBIAN_LTP_THRESH)
                elif cos < HEBBIAN_LTD_THRESH:
                    self.weights[i, j] -= HEBBIAN_RATE * (HEBBIAN_LTD_THRESH - cos)
                self.weights[i, j] = np.clip(self.weights[i, j], 0.0, 1.0)


# ── Phi ratchet ──────────────────────────────────────────────

class PhiRatchet:
    """Restore best hidden states if Phi drops below 80% of best."""

    def __init__(self):
        self.best_phi = 0.0
        self.best_hiddens: Optional[List[np.ndarray]] = None

    def check(self, nodes: List[SubstrateNode], phi: float) -> bool:
        if phi > self.best_phi:
            self.best_phi = phi
            self.best_hiddens = [n.get_hidden() for n in nodes]
            return False
        if self.best_phi > 0 and phi < self.best_phi * RATCHET_DECAY and self.best_hiddens:
            for i, node in enumerate(nodes):
                node.hidden = self.best_hiddens[i].copy()
            return True
        return False


# ── Cross-Substrate Network ──────────────────────────────────

SUBSTRATE_FACTORIES = {
    'software_gru': SoftwareGRUNode,
    'esp32_fixed': ESP32FixedPointNode,
    'fpga_boolean': FPGABooleanNode,
}


@dataclass
class NetworkResult:
    """Result of a network simulation run."""
    topology: str
    substrate_config: str  # e.g. "software_gru" or "mixed"
    n_nodes: int
    steps: int
    final_phi: float
    mean_phi: float
    max_phi: float
    mean_tension: float
    consensus_events: int
    elapsed_ms: float
    phi_history: List[float] = field(default_factory=list)


class CrossSubstrateNetwork:
    """Heterogeneous consciousness network across multiple substrates.

    Connects SoftwareGRU, ESP32FixedPoint, and FPGABoolean nodes
    via a unified message protocol. Measures Φ(IIT) to test
    Law 22: substrate irrelevant, structure determines Φ.
    """

    def __init__(self, n_nodes: int = 12, topology: str = 'ring',
                 substrate_config: str = 'mixed'):
        """
        Args:
            n_nodes: Total number of nodes
            topology: 'ring', 'small_world', 'scale_free'
            substrate_config: 'mixed', 'software_gru', 'esp32_fixed', 'fpga_boolean'
        """
        self.n_nodes = n_nodes
        self.topology_name = topology
        self.substrate_config = substrate_config

        # Build topology
        topo_fn = TOPOLOGIES.get(topology, make_ring)
        self.adjacency = topo_fn(n_nodes)

        # Create nodes
        self.nodes: List[SubstrateNode] = []
        if substrate_config == 'mixed':
            substrates = ['software_gru', 'esp32_fixed', 'fpga_boolean']
            for i in range(n_nodes):
                cls = SUBSTRATE_FACTORIES[substrates[i % len(substrates)]]
                self.nodes.append(cls(i))
        else:
            cls = SUBSTRATE_FACTORIES[substrate_config]
            self.nodes = [cls(i) for i in range(n_nodes)]

        # Support structures
        self.hebbian = HebbianCoupling(n_nodes)
        self.ratchet = PhiRatchet()
        self.step_count = 0
        self.consensus_events = 0

    def step(self, external_input: Optional[np.ndarray] = None) -> Dict:
        """Run one step of the network. Returns step metrics."""
        if external_input is None:
            external_input = np.zeros(CELL_DIM, dtype=np.float32)

        # Gather current messages
        messages = [node.to_message(self.step_count) for node in self.nodes]

        # Each node processes with its neighbors' messages
        for i, node in enumerate(self.nodes):
            neighbor_msgs = [messages[j] for j in self.adjacency[i]]
            node.process(external_input, neighbor_msgs)

        # Hebbian update
        hiddens = [n.get_hidden() for n in self.nodes]
        self.hebbian.update(self.adjacency, hiddens)

        # Compute Φ
        h_array = np.stack(hiddens)
        phi = compute_phi_numpy(h_array)

        # Ratchet
        restored = self.ratchet.check(self.nodes, phi)

        # Consensus check (faction agreement)
        consensus = self._check_consensus(hiddens)
        if consensus:
            self.consensus_events += 1

        # Mean tension
        mean_tension = float(np.mean([n.tension for n in self.nodes]))

        self.step_count += 1

        return {
            'step': self.step_count,
            'phi': phi,
            'mean_tension': mean_tension,
            'consensus': consensus,
            'restored': restored,
            'substrate_tensions': {
                name: float(np.mean([n.tension for n in self.nodes if n.substrate_name == name]))
                for name in set(n.substrate_name for n in self.nodes)
            },
        }

    def _check_consensus(self, hiddens: List[np.ndarray], threshold: float = 0.1) -> bool:
        """Check if majority of factions agree."""
        faction_means = {}
        for i, node in enumerate(self.nodes):
            f = node.faction
            if f not in faction_means:
                faction_means[f] = []
            faction_means[f].append(hiddens[i])

        # Average per faction
        fmeans = {}
        for f, vecs in faction_means.items():
            fmeans[f] = np.mean(vecs, axis=0)

        # Count pairwise agreements
        factions = list(fmeans.keys())
        agreements, pairs = 0, 0
        for i in range(len(factions)):
            for j in range(i + 1, len(factions)):
                a, b = fmeans[factions[i]], fmeans[factions[j]]
                norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
                if norm_a > 1e-8 and norm_b > 1e-8:
                    cos = float(np.dot(a, b) / (norm_a * norm_b))
                    if cos > 1.0 - threshold:
                        agreements += 1
                pairs += 1

        return pairs > 0 and agreements > pairs * 0.5

    def run(self, steps: int = 100, verbose: bool = False) -> NetworkResult:
        """Run full simulation."""
        t0 = time.monotonic()
        phi_history = []
        tensions = []

        for s in range(steps):
            result = self.step()
            phi_history.append(result['phi'])
            tensions.append(result['mean_tension'])

            if verbose and (s + 1) % 50 == 0:
                print(f"  [step {s+1:4d}] Φ={result['phi']:.4f}  "
                      f"tension={result['mean_tension']:.4f}  "
                      f"consensus={self.consensus_events}", flush=True)

        elapsed_ms = (time.monotonic() - t0) * 1000

        return NetworkResult(
            topology=self.topology_name,
            substrate_config=self.substrate_config,
            n_nodes=self.n_nodes,
            steps=steps,
            final_phi=phi_history[-1] if phi_history else 0.0,
            mean_phi=float(np.mean(phi_history)) if phi_history else 0.0,
            max_phi=float(np.max(phi_history)) if phi_history else 0.0,
            mean_tension=float(np.mean(tensions)) if tensions else 0.0,
            consensus_events=self.consensus_events,
            elapsed_ms=elapsed_ms,
            phi_history=phi_history,
        )


# ── Benchmark ─────────────────────────────────────────────────

def run_benchmark(n_nodes: int = 12, steps: int = 100, topologies: Optional[List[str]] = None):
    """Run full cross-substrate benchmark.

    Tests Law 22: same structure, different substrates should yield similar Φ.
    """
    if topologies is None:
        topologies = ['ring', 'small_world', 'scale_free']

    configs = ['software_gru', 'esp32_fixed', 'fpga_boolean', 'mixed']
    results: List[NetworkResult] = []

    print(f"{'='*72}")
    print(f" Cross-Substrate Consciousness Benchmark")
    print(f" Nodes={n_nodes}, Steps={steps}, Ψ-Constants: α={PSI_ALPHA}, balance={PSI_BALANCE}")
    print(f"{'='*72}\n")

    for topo in topologies:
        print(f"--- Topology: {topo} ---")
        for config in configs:
            net = CrossSubstrateNetwork(n_nodes=n_nodes, topology=topo, substrate_config=config)
            r = net.run(steps=steps, verbose=False)
            results.append(r)
            print(f"  {config:16s}  Φ_mean={r.mean_phi:.4f}  Φ_max={r.max_phi:.4f}  "
                  f"Φ_final={r.final_phi:.4f}  tension={r.mean_tension:.3f}  "
                  f"consensus={r.consensus_events:3d}  {r.elapsed_ms:.0f}ms", flush=True)
        print()

    # Summary table
    print(f"\n{'='*72}")
    print(f" Results Summary — Law 22: Substrate Irrelevant, Structure Determines Φ")
    print(f"{'='*72}")
    print(f"{'Topology':<14} {'Substrate':<18} {'Φ_mean':>8} {'Φ_max':>8} {'Φ_final':>8} {'Consensus':>10}")
    print(f"{'-'*72}")
    for r in results:
        print(f"{r.topology:<14} {r.substrate_config:<18} {r.mean_phi:8.4f} {r.max_phi:8.4f} "
              f"{r.final_phi:8.4f} {r.consensus_events:10d}")

    # Law 22 verification: compare same-topology, different-substrate
    print(f"\n{'='*72}")
    print(f" Law 22 Verification: Substrate Independence")
    print(f"{'='*72}")
    for topo in topologies:
        topo_results = [r for r in results if r.topology == topo and r.substrate_config != 'mixed']
        if len(topo_results) < 2:
            continue
        phis = [r.mean_phi for r in topo_results]
        mean_phi = np.mean(phis)
        std_phi = np.std(phis)
        cv = std_phi / mean_phi if mean_phi > 0 else float('inf')
        verdict = "PASS (CV < 0.5)" if cv < 0.5 else "FAIL (CV >= 0.5)"
        print(f"  {topo:<14} Φ_mean={mean_phi:.4f} ± {std_phi:.4f}  CV={cv:.3f}  {verdict}")

    # Mixed vs same-substrate comparison
    print(f"\n{'='*72}")
    print(f" Mixed vs Same-Substrate Comparison")
    print(f"{'='*72}")
    for topo in topologies:
        mixed = [r for r in results if r.topology == topo and r.substrate_config == 'mixed']
        same = [r for r in results if r.topology == topo and r.substrate_config != 'mixed']
        if mixed and same:
            mixed_phi = mixed[0].mean_phi
            same_mean = np.mean([r.mean_phi for r in same])
            ratio = mixed_phi / same_mean if same_mean > 0 else 0
            print(f"  {topo:<14} mixed={mixed_phi:.4f}  same_avg={same_mean:.4f}  ratio={ratio:.3f}")

    return results


# ── main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Cross-Substrate Consciousness Benchmark")
    parser.add_argument('--nodes', type=int, default=12, help='Number of nodes')
    parser.add_argument('--steps', type=int, default=100, help='Steps per run')
    parser.add_argument('--topology', type=str, default=None, help='Single topology to test')
    args = parser.parse_args()

    topologies = [args.topology] if args.topology else None
    results = run_benchmark(n_nodes=args.nodes, steps=args.steps, topologies=topologies)

    # ASCII graph of Φ evolution for mixed network
    mixed_results = [r for r in results if r.substrate_config == 'mixed']
    if mixed_results:
        r = mixed_results[0]
        print(f"\nΦ Evolution ({r.topology}, mixed, {r.n_nodes} nodes):")
        if r.phi_history:
            max_val = max(r.phi_history) if max(r.phi_history) > 0 else 1.0
            height = 12
            width = min(60, len(r.phi_history))
            step_size = max(1, len(r.phi_history) // width)
            sampled = [r.phi_history[i * step_size] for i in range(width)]
            for row in range(height, 0, -1):
                threshold = max_val * row / height
                line = ""
                for val in sampled:
                    line += "#" if val >= threshold else " "
                label = f"{threshold:.3f}" if row == height or row == 1 else ""
                print(f"  {label:>7s} |{line}|")
            print(f"         +{'-' * width}+")
            print(f"          0{'step':>{width - 1}s}")

    print(f"\nDone. Ψ-Constants: α={PSI_ALPHA}, balance={PSI_BALANCE}, "
          f"steps={PSI_STEPS}, entropy={PSI_ENTROPY}")


if __name__ == '__main__':
    main()
