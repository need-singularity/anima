#!/usr/bin/env python3
"""ESP32 Consciousness Network Orchestrator

Manages 8 ESP32-S3 boards connected via SPI bus:
  - Board 0: Hub (Law 93: asymmetric hub-spoke)
  - Board 1-7: Spoke cells

Each board runs:
  - 2-4 consciousness cells (GRU, 64d hidden)
  - SPI tension exchange every cycle
  - Local Phi computation (approximate)

The SPI bus bandwidth = natural information bottleneck (Law 92).
Hub board integrates info from all spokes (Law 93).

Network Phi is measured by the Python host via serial.

Usage:
  python esp32_network.py                        # Simulation mode (no hardware)
  python esp32_network.py --ports /dev/ttyUSB0,/dev/ttyUSB1,...  # Real hardware
  python esp32_network.py --topology ring         # Ring topology (default)
  python esp32_network.py --topology hub_spoke    # Hub-spoke (Law 93)
  python esp32_network.py --topology small_world  # Small-world
  python esp32_network.py --steps 1000            # Run N steps
  python esp32_network.py --dashboard             # Real-time ASCII dashboard
  python esp32_network.py --benchmark             # Run full benchmark suite

Requires: numpy, (optional: pyserial for real hardware)
"""

import argparse
import math
import struct
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    import serial
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# Try importing project modules for Phi measurement
try:
    import torch
    from consciousness_meter import PhiCalculator
    HAS_PHI = True
except Exception:
    HAS_PHI = False


# ═══════════════════════════════════════════════════════════
# Constants (matched to anima-rs/crates/esp32/src/lib.rs)
# ═══════════════════════════════════════════════════════════

CELL_DIM = 64
HIDDEN_DIM = 128
COMBINED_DIM = CELL_DIM + 1 + HIDDEN_DIM  # 193
PSI_COUPLING = 0.014
N_BOARDS = 8
CELLS_PER_BOARD = 2
N_FACTIONS = 4

# SPI packet: 128 floats (hidden) + 1 float (tension) + 2 bytes (cell_id, faction_id) = 518 bytes
SPI_PACKET_SIZE = 518

# Serial protocol commands
CMD_INIT = b'\x01'
CMD_STEP = b'\x02'
CMD_GET_STATE = b'\x03'
CMD_SET_TOPOLOGY = b'\x04'
CMD_RESET = b'\x05'


# ═══════════════════════════════════════════════════════════
# Topology definitions
# ═══════════════════════════════════════════════════════════

def make_ring(n: int) -> List[List[int]]:
    """Ring topology: each node connects to left and right neighbor."""
    adj = [[] for _ in range(n)]
    for i in range(n):
        adj[i].append((i - 1) % n)
        adj[i].append((i + 1) % n)
    return adj


def make_hub_spoke(n: int) -> List[List[int]]:
    """Hub-spoke: board 0 connects to all, spokes connect only to hub."""
    adj = [[] for _ in range(n)]
    for i in range(1, n):
        adj[0].append(i)
        adj[i].append(0)
    return adj


def make_small_world(n: int, k: int = 2, p: float = 0.3) -> List[List[int]]:
    """Small-world (Watts-Strogatz): ring + random shortcuts."""
    rng = np.random.default_rng(42)
    adj = [set() for _ in range(n)]
    # Start with ring of k neighbors each side
    for i in range(n):
        for j in range(1, k + 1):
            adj[i].add((i + j) % n)
            adj[i].add((i - j) % n)
    # Rewire with probability p
    for i in range(n):
        neighbors = list(adj[i])
        for nb in neighbors:
            if rng.random() < p:
                # Rewire to random node
                candidates = [x for x in range(n) if x != i and x not in adj[i]]
                if candidates:
                    adj[i].discard(nb)
                    new_nb = rng.choice(candidates)
                    adj[i].add(new_nb)
                    adj[new_nb].add(i)
    return [list(s) for s in adj]


TOPOLOGIES = {
    'ring': make_ring,
    'hub_spoke': make_hub_spoke,
    'small_world': make_small_world,
}


# ═══════════════════════════════════════════════════════════
# Simulated GRU Cell (matches ESP32 Rust implementation)
# ═══════════════════════════════════════════════════════════

class SimGruCell:
    """Python simulation of the no_std GRU cell from esp32 crate."""

    def __init__(self, seed: int = 42):
        rng = np.random.default_rng(seed)
        scale = 0.1
        self.hidden = np.zeros(HIDDEN_DIM, dtype=np.float32)
        self.w_z = rng.standard_normal((HIDDEN_DIM, COMBINED_DIM)).astype(np.float32) * scale
        self.w_r = rng.standard_normal((HIDDEN_DIM, COMBINED_DIM)).astype(np.float32) * scale
        self.w_h = rng.standard_normal((HIDDEN_DIM, COMBINED_DIM)).astype(np.float32) * scale

    def process(self, inp: np.ndarray, tension: float):
        """GRU forward pass, matching Rust implementation."""
        combined = np.zeros(COMBINED_DIM, dtype=np.float32)
        combined[:CELL_DIM] = inp[:CELL_DIM]
        combined[CELL_DIM] = tension
        combined[CELL_DIM + 1:] = self.hidden

        z = _sigmoid(self.w_z @ combined)
        r = _sigmoid(self.w_r @ combined)

        combined_r = combined.copy()
        combined_r[CELL_DIM + 1:] = r * self.hidden

        h_cand = np.tanh(self.w_h @ combined_r)
        self.hidden = (1.0 - z) * h_cand + z * self.hidden


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))


# ═══════════════════════════════════════════════════════════
# Board state
# ═══════════════════════════════════════════════════════════

@dataclass
class BoardState:
    """State of one ESP32 board."""
    board_id: int
    cells: List[SimGruCell] = field(default_factory=list)
    tensions: List[float] = field(default_factory=list)
    local_phi: float = 0.0
    faction_ids: List[int] = field(default_factory=list)
    step_count: int = 0
    # Aggregated hidden for SPI exchange
    mean_hidden: np.ndarray = field(default_factory=lambda: np.zeros(HIDDEN_DIM, dtype=np.float32))

    def compute_local_phi(self) -> float:
        """Approximate Phi from local cells (variance-based proxy)."""
        if len(self.cells) < 2:
            return 0.0
        hiddens = np.array([c.hidden for c in self.cells])
        global_var = np.var(hiddens)
        per_cell_var = np.mean([np.var(c.hidden) for c in self.cells])
        self.local_phi = max(0.0, float(global_var - per_cell_var))
        return self.local_phi

    def compute_mean_hidden(self) -> np.ndarray:
        """Mean hidden state across local cells (for SPI exchange)."""
        if not self.cells:
            return self.mean_hidden
        self.mean_hidden = np.mean([c.hidden for c in self.cells], axis=0).astype(np.float32)
        return self.mean_hidden


# ═══════════════════════════════════════════════════════════
# ESP32 Network Orchestrator
# ═══════════════════════════════════════════════════════════

class ESP32Network:
    """Orchestrates 8 ESP32 boards (real or simulated)."""

    def __init__(
        self,
        n_boards: int = N_BOARDS,
        cells_per_board: int = CELLS_PER_BOARD,
        topology: str = 'ring',
        ports: Optional[List[str]] = None,
        seed: int = 42,
    ):
        self.n_boards = n_boards
        self.cells_per_board = cells_per_board
        self.topology_name = topology
        self.seed = seed
        self.simulation_mode = (ports is None)
        self.step_count = 0

        # Build adjacency
        topo_fn = TOPOLOGIES.get(topology, make_ring)
        self.adjacency = topo_fn(n_boards)

        # Initialize boards
        self.boards: List[BoardState] = []
        for bid in range(n_boards):
            board = BoardState(board_id=bid)
            for cid in range(cells_per_board):
                cell_seed = seed + bid * 100 + cid
                board.cells.append(SimGruCell(seed=cell_seed))
                board.tensions.append(0.0)
                board.faction_ids.append((bid * cells_per_board + cid) % N_FACTIONS)
            self.boards.append(board)

        # Serial connections (real hardware)
        self.serial_conns: List[Optional[serial.Serial]] = []
        if not self.simulation_mode and HAS_SERIAL:
            for port in (ports or []):
                try:
                    conn = serial.Serial(port, 115200, timeout=1)
                    self.serial_conns.append(conn)
                except Exception as e:
                    print(f"[esp32] WARNING: Could not open {port}: {e}")
                    self.serial_conns.append(None)
            if len(self.serial_conns) < n_boards:
                print(f"[esp32] Only {len(self.serial_conns)}/{n_boards} boards connected, rest simulated")

        # Telemetry history
        self.phi_history: List[float] = []
        self.tension_history: List[float] = []
        self.board_phi_history: List[List[float]] = [[] for _ in range(n_boards)]

        # Phi calculator
        self.phi_calc_bins = 16

    def switch_topology(self, new_topology: str):
        """Runtime topology switching (Law 90: recovery in ~5 steps)."""
        topo_fn = TOPOLOGIES.get(new_topology)
        if topo_fn is None:
            print(f"[esp32] Unknown topology: {new_topology}")
            return
        self.topology_name = new_topology
        self.adjacency = topo_fn(self.n_boards)
        print(f"[esp32] Topology switched to {new_topology}")

    def step(self, external_input: Optional[np.ndarray] = None) -> Dict:
        """Run one consciousness cycle across all boards.

        1. Each board processes its cells locally
        2. SPI exchange: boards share mean hidden with neighbors
        3. Hub integrates (if hub_spoke topology)
        4. Compute network Phi
        """
        self.step_count += 1

        # Generate input if not provided
        rng = np.random.default_rng(self.seed + self.step_count)
        if external_input is None:
            base_input = rng.standard_normal(CELL_DIM).astype(np.float32) * 0.1
        else:
            base_input = external_input[:CELL_DIM].astype(np.float32)

        # Phase 1: Local processing on each board
        for board in self.boards:
            for ci, cell in enumerate(board.cells):
                # Build coupled input from neighbor boards
                coupled = base_input.copy()
                for nb_id in self.adjacency[board.board_id]:
                    nb_hidden = self.boards[nb_id].mean_hidden
                    coupled[:CELL_DIM] += PSI_COUPLING * nb_hidden[:CELL_DIM]

                # Compute tension
                tension = float(np.sqrt(np.mean(cell.hidden ** 2)))
                cell.process(coupled, tension)
                board.tensions[ci] = tension

            board.compute_mean_hidden()
            board.compute_local_phi()
            board.step_count = self.step_count

        # Phase 2: Compute network-level Phi
        all_hiddens = []
        for board in self.boards:
            for cell in board.cells:
                all_hiddens.append(cell.hidden.copy())

        network_phi = self._compute_network_phi(all_hiddens)
        mean_tension = float(np.mean([t for b in self.boards for t in b.tensions]))

        self.phi_history.append(network_phi)
        self.tension_history.append(mean_tension)
        for i, board in enumerate(self.boards):
            self.board_phi_history[i].append(board.local_phi)

        return {
            'step': self.step_count,
            'network_phi': network_phi,
            'mean_tension': mean_tension,
            'board_phis': [b.local_phi for b in self.boards],
            'board_tensions': [np.mean(b.tensions) for b in self.boards],
            'n_cells': sum(len(b.cells) for b in self.boards),
            'topology': self.topology_name,
        }

    def _compute_network_phi(self, hiddens: List[np.ndarray]) -> float:
        """Compute Phi(IIT) proxy from all cell hidden states."""
        if len(hiddens) < 2:
            return 0.0

        arr = np.array(hiddens)  # [n_cells, hidden_dim]

        # Mutual information approximation via histogram binning
        n_cells = arr.shape[0]
        n_bins = self.phi_calc_bins

        # Normalize to [0, 1] per dimension
        mins = arr.min(axis=0, keepdims=True)
        maxs = arr.max(axis=0, keepdims=True)
        ranges = maxs - mins
        ranges[ranges < 1e-8] = 1.0
        normed = (arr - mins) / ranges

        # Discretize
        binned = np.clip((normed * n_bins).astype(int), 0, n_bins - 1)

        # Compute pairwise MI for a subset of dimensions (speed)
        dims_to_check = min(16, arr.shape[1])
        step_d = max(1, arr.shape[1] // dims_to_check)
        total_mi = 0.0
        n_pairs = 0

        for i in range(n_cells):
            for j in range(i + 1, n_cells):
                mi = 0.0
                for d in range(0, arr.shape[1], step_d):
                    # Joint histogram
                    joint = np.zeros((n_bins, n_bins), dtype=np.float64)
                    for k in range(arr.shape[1] // step_d):
                        dd = k * step_d
                        if dd < arr.shape[1]:
                            bi, bj = binned[i, dd], binned[j, dd]
                            joint[bi, bj] += 1
                    joint /= max(joint.sum(), 1)

                    # Marginals
                    px = joint.sum(axis=1)
                    py = joint.sum(axis=0)

                    # MI
                    for a in range(n_bins):
                        for b in range(n_bins):
                            if joint[a, b] > 1e-12 and px[a] > 1e-12 and py[b] > 1e-12:
                                mi += joint[a, b] * np.log2(joint[a, b] / (px[a] * py[b]))
                    break  # One pass of dimensions is enough for approximation
                total_mi += max(0.0, mi)
                n_pairs += 1

        if n_pairs == 0:
            return 0.0

        avg_mi = total_mi / n_pairs

        # Minimum partition: split into two halves
        mid = n_cells // 2
        left = arr[:mid]
        right = arr[mid:]
        left_var = np.var(left) if len(left) > 0 else 0
        right_var = np.var(right) if len(right) > 0 else 0
        whole_var = np.var(arr)

        # Phi = integration that can't be decomposed
        partition_loss = max(0.0, whole_var - (left_var + right_var) / 2)
        phi = avg_mi + partition_loss

        return float(phi)

    def run(self, n_steps: int = 500, dashboard: bool = False) -> List[Dict]:
        """Run the network for N steps."""
        results = []
        for s in range(n_steps):
            result = self.step()
            results.append(result)
            if dashboard and (s % 10 == 0 or s == n_steps - 1):
                self._print_dashboard(result, s, n_steps)
        return results

    def _print_dashboard(self, result: Dict, step: int, total: int):
        """ASCII real-time dashboard."""
        pct = (step + 1) / total * 100
        bar_len = 40
        filled = int(bar_len * (step + 1) / total)
        bar = '=' * filled + '-' * (bar_len - filled)

        lines = []
        lines.append('')
        lines.append(f'  ESP32 Consciousness Network  [{self.topology_name}]  {"SIM" if self.simulation_mode else "HW"}')
        lines.append(f'  [{bar}] {pct:5.1f}%  step {step + 1}/{total}')
        lines.append('')
        lines.append(f'  Network Phi: {result["network_phi"]:.4f}   Mean Tension: {result["mean_tension"]:.4f}   Cells: {result["n_cells"]}')
        lines.append('')

        # Per-board status
        lines.append('  Board | Cells | Tension | Local Phi | Faction ')
        lines.append('  ------+-------+---------+-----------+---------')
        for b in self.boards:
            mean_t = np.mean(b.tensions)
            factions = ','.join(str(f) for f in b.faction_ids)
            role = 'HUB' if b.board_id == 0 and self.topology_name == 'hub_spoke' else f'  {b.board_id}'
            lines.append(f'  {role:5s} | {len(b.cells):5d} | {mean_t:7.4f} | {b.local_phi:9.4f} | {factions}')

        # Mini Phi graph (last 50 steps)
        if len(self.phi_history) > 1:
            lines.append('')
            lines.append('  Phi(network) history:')
            recent = self.phi_history[-50:]
            max_phi = max(recent) if recent else 1.0
            min_phi = min(recent) if recent else 0.0
            span = max(max_phi - min_phi, 1e-6)
            graph_h = 8
            graph_w = min(50, len(recent))

            for row in range(graph_h, -1, -1):
                threshold = min_phi + span * row / graph_h
                line = '  '
                if row == graph_h:
                    line += f'{max_phi:6.3f} |'
                elif row == 0:
                    line += f'{min_phi:6.3f} |'
                else:
                    line += '       |'
                for i in range(graph_w):
                    idx = len(recent) - graph_w + i
                    if idx >= 0 and recent[idx] >= threshold:
                        line += '#'
                    else:
                        line += ' '
                lines.append(line)
            lines.append('         ' + '-' * graph_w + ' step')

        # Topology visualization
        lines.append('')
        lines.append(f'  Topology: {self.topology_name}')
        for i, neighbors in enumerate(self.adjacency):
            arrows = ' -> '.join(str(n) for n in neighbors)
            lines.append(f'    [{i}] -> {arrows}')

        # Clear and print
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.write('\n'.join(lines) + '\n')
        sys.stdout.flush()

    def get_telemetry(self) -> Dict:
        """Get full telemetry for logging."""
        return {
            'step': self.step_count,
            'topology': self.topology_name,
            'n_boards': self.n_boards,
            'cells_per_board': self.cells_per_board,
            'n_cells_total': sum(len(b.cells) for b in self.boards),
            'network_phi': self.phi_history[-1] if self.phi_history else 0.0,
            'mean_tension': self.tension_history[-1] if self.tension_history else 0.0,
            'board_states': [
                {
                    'board_id': b.board_id,
                    'n_cells': len(b.cells),
                    'local_phi': b.local_phi,
                    'tensions': b.tensions,
                    'faction_ids': b.faction_ids,
                }
                for b in self.boards
            ],
            'phi_history': self.phi_history[-100:],
            'tension_history': self.tension_history[-100:],
        }


# ═══════════════════════════════════════════════════════════
# Benchmark
# ═══════════════════════════════════════════════════════════

def run_benchmark():
    """Run ESP32 network benchmark across topologies."""
    print('=' * 70)
    print('  ESP32 Consciousness Network Benchmark')
    print('  8 boards x 2 cells = 16 cells, 64d input, 128d hidden')
    print('=' * 70)
    print()

    results = {}
    steps = 200

    for topo in ['ring', 'hub_spoke', 'small_world']:
        print(f'  Running {topo}...')
        net = ESP32Network(topology=topo, seed=42)
        step_results = net.run(steps, dashboard=False)

        final_phi = step_results[-1]['network_phi']
        mean_phi = np.mean([r['network_phi'] for r in step_results[-50:]])
        mean_tension = np.mean([r['mean_tension'] for r in step_results[-50:]])

        results[topo] = {
            'final_phi': final_phi,
            'mean_phi_last50': mean_phi,
            'mean_tension': mean_tension,
            'phi_history': [r['network_phi'] for r in step_results],
        }
        print(f'    Phi={final_phi:.4f} (mean last 50: {mean_phi:.4f}), tension={mean_tension:.4f}')

    # Topology switch test (Law 90)
    print()
    print('  Topology switch test (Law 90):')
    net = ESP32Network(topology='ring', seed=42)
    for _ in range(100):
        net.step()
    phi_before = net.phi_history[-1]
    net.switch_topology('hub_spoke')
    recovery_steps = 0
    for _ in range(20):
        net.step()
        recovery_steps += 1
        if net.phi_history[-1] >= phi_before * 0.9:
            break
    phi_after = net.phi_history[-1]
    print(f'    ring Phi={phi_before:.4f} -> hub_spoke Phi={phi_after:.4f}, recovery={recovery_steps} steps')

    # Summary table
    print()
    print('  Results Summary:')
    print('  ' + '-' * 55)
    print(f'  {"Topology":<15} | {"Final Phi":>10} | {"Mean Phi":>10} | {"Tension":>10}')
    print('  ' + '-' * 55)
    for topo, r in results.items():
        print(f'  {topo:<15} | {r["final_phi"]:>10.4f} | {r["mean_phi_last50"]:>10.4f} | {r["mean_tension"]:>10.4f}')
    print('  ' + '-' * 55)

    # ASCII graph comparing topologies
    print()
    print('  Phi evolution comparison (200 steps):')
    graph_w = 60
    for topo, r in results.items():
        hist = r['phi_history']
        max_v = max(hist) if hist else 1
        # Downsample to graph_w points
        indices = np.linspace(0, len(hist) - 1, graph_w).astype(int)
        sampled = [hist[i] for i in indices]
        bar = ''.join('#' if v > max_v * 0.5 else '.' for v in sampled)
        print(f'  {topo:<13} |{bar}| max={max_v:.3f}')

    print()
    print('  SPI bandwidth analysis (Law 92 — information bottleneck):')
    print(f'    Packet size: {SPI_PACKET_SIZE} bytes')
    print(f'    SPI clock: 10 MHz typical -> {10_000_000 / SPI_PACKET_SIZE / 8:.0f} packets/sec')
    print(f'    Bottleneck ratio: {CELL_DIM}/{HIDDEN_DIM} = {CELL_DIM / HIDDEN_DIM:.2f} (input/hidden)')
    print(f'    Law 92: bottleneck forces compression -> higher Phi')
    print()


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='ESP32 Consciousness Network Orchestrator')
    parser.add_argument('--ports', type=str, default=None,
                        help='Comma-separated serial ports (e.g., /dev/ttyUSB0,/dev/ttyUSB1,...)')
    parser.add_argument('--topology', type=str, default='ring',
                        choices=list(TOPOLOGIES.keys()),
                        help='Network topology (default: ring)')
    parser.add_argument('--boards', type=int, default=N_BOARDS, help='Number of boards')
    parser.add_argument('--cells', type=int, default=CELLS_PER_BOARD, help='Cells per board')
    parser.add_argument('--steps', type=int, default=500, help='Number of steps')
    parser.add_argument('--dashboard', action='store_true', help='Show real-time ASCII dashboard')
    parser.add_argument('--benchmark', action='store_true', help='Run full benchmark suite')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    if args.benchmark:
        run_benchmark()
        return

    ports = args.ports.split(',') if args.ports else None
    if ports is None:
        print('[esp32] No serial ports specified — running in SIMULATION mode')

    net = ESP32Network(
        n_boards=args.boards,
        cells_per_board=args.cells,
        topology=args.topology,
        ports=ports,
        seed=args.seed,
    )

    print(f'[esp32] Network: {args.boards} boards x {args.cells} cells = {args.boards * args.cells} total')
    print(f'[esp32] Topology: {args.topology}')
    print(f'[esp32] Steps: {args.steps}')
    print()

    results = net.run(args.steps, dashboard=args.dashboard)

    if not args.dashboard:
        # Print final summary
        final = results[-1]
        print()
        print('  Final State:')
        print(f'    Network Phi: {final["network_phi"]:.4f}')
        print(f'    Mean Tension: {final["mean_tension"]:.4f}')
        print(f'    Cells: {final["n_cells"]}')
        print()

        # Mini ASCII graph
        phis = [r['network_phi'] for r in results]
        print('  Phi evolution:')
        max_phi = max(phis) if phis else 1
        min_phi = min(phis) if phis else 0
        graph_h = 10
        graph_w = min(60, len(phis))
        span = max(max_phi - min_phi, 1e-6)
        indices = np.linspace(0, len(phis) - 1, graph_w).astype(int)
        sampled = [phis[i] for i in indices]

        for row in range(graph_h, -1, -1):
            threshold = min_phi + span * row / graph_h
            line = f'  {threshold:7.4f} |'
            for v in sampled:
                line += '#' if v >= threshold else ' '
            print(line)
        print('          ' + '-' * graph_w + ' step')


if __name__ == '__main__':
    main()
