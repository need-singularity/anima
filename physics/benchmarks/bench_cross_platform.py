#!/usr/bin/env python3
"""bench_cross_platform.py -- Cross-Platform Phi Verification

Law 22 검증: "기질 무관, 구조만이 Phi를 결정한다"
동일 조건(64 cells, ring topology, 33% frustration, 500 steps)에서
5개 플랫폼(Rust APEX22, SNN, Verilog, WebGPU, Erlang)의 Phi를 비교.

각 플랫폼은 Python으로 시뮬레이션하되 플랫폼별 고유 특성 반영:
  - propagation delay, noise floor, numerical precision
  - update mechanism (GRU, LIF spike, gate-level, compute shader, actor)

Usage:
  python3 bench_cross_platform.py
  python3 bench_cross_platform.py --cells 128 --steps 1000
  python3 bench_cross_platform.py --frustration 0.5
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import numpy as np
import math
import time
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

sys.stdout.reconfigure(line_buffering=True)


# ═══════════════════════════════════════════════════════════
# Phi(IIT) 근사 계산기 (pairwise MI + minimum partition)
# ═══════════════════════════════════════════════════════════

class PhiIIT:
    """Phi(IIT) approximation via pairwise MI + minimum partition."""

    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, states: np.ndarray) -> Tuple[float, Dict]:
        """states: (n_cells, hidden_dim)"""
        n = states.shape[0]
        if n < 2:
            return 0.0, {}

        # Pairwise MI
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            pairs = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = np.random.randint(0, n)
                    if i != j:
                        pairs.add((min(i, j), max(i, j)))
            pairs = list(pairs)

        mi_matrix = np.zeros((n, n))
        for i, j in pairs:
            mi = self._mi(states[i], states[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi

        total_mi = mi_matrix.sum() / 2
        min_part = self._min_partition(n, mi_matrix)
        spatial = max(0.0, (total_mi - min_part) / max(n - 1, 1))
        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        phi = spatial + complexity * 0.1
        return phi, {'total_mi': total_mi, 'spatial': spatial, 'complexity': complexity}

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        jh, _, _ = np.histogram2d(xn, yn, bins=self.n_bins, range=[[0, 1], [0, 1]])
        jh = jh / (jh.sum() + 1e-8)
        px, py = jh.sum(axis=1), jh.sum(axis=0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(jh * np.log2(jh + 1e-10))
        return max(0.0, hx + hy - hxy)

    def _min_partition(self, n, mi):
        if n <= 8:
            best = float('inf')
            for mask in range(1, 2 ** n - 1):
                ga = [i for i in range(n) if mask & (1 << i)]
                gb = [i for i in range(n) if not (mask & (1 << i))]
                if ga and gb:
                    cut = sum(mi[i, j] for i in ga for j in gb)
                    best = min(best, cut)
            return best if best != float('inf') else 0.0
        else:
            deg = mi.sum(axis=1)
            lap = np.diag(deg) - mi
            try:
                evals, evecs = np.linalg.eigh(lap)
                fiedler = evecs[:, 1]
                ga = [i for i in range(n) if fiedler[i] >= 0]
                gb = [i for i in range(n) if fiedler[i] < 0]
                if not ga or not gb:
                    ga, gb = list(range(n // 2)), list(range(n // 2, n))
                return sum(mi[i, j] for i in ga for j in gb)
            except Exception:
                return 0.0


def phi_proxy(states: np.ndarray, n_factions: int = 8) -> float:
    """Phi(proxy) = global_var - mean(faction_var)"""
    n, d = states.shape
    if n < 2:
        return 0.0
    gm = states.mean(axis=0)
    gv = np.sum((states - gm) ** 2) / n
    nf = min(n_factions, n // 2)
    if nf < 2:
        return gv
    fs = n // nf
    fv_sum = 0.0
    for i in range(nf):
        fac = states[i * fs:(i + 1) * fs]
        if len(fac) >= 2:
            fm = fac.mean(axis=0)
            fv_sum += np.sum((fac - fm) ** 2) / len(fac)
    return max(0.0, gv - fv_sum / nf)


# ═══════════════════════════════════════════════════════════
# 플랫폼 공통 결과
# ═══════════════════════════════════════════════════════════

@dataclass
class PlatformResult:
    name: str
    name_kr: str
    phi_iit: float
    phi_proxy: float
    convergence_step: int      # Phi가 최종값 90%에 도달한 step
    stability: float           # Phi 후반 50% 표준편차 / 평균 (낮을수록 안정)
    time_sec: float
    phi_history: List[float] = field(default_factory=list)
    extra: Dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# 공통 Ring Topology + Frustration 초기화
# ═══════════════════════════════════════════════════════════

def init_ring_weights(n_cells: int, frustration: float, seed: int = 42) -> np.ndarray:
    """Ring topology weight matrix with tunable frustration.
    frustration: fraction of connections with negative (inhibitory) weight.
    """
    rng = np.random.RandomState(seed)
    W = np.zeros((n_cells, n_cells))
    k = max(2, n_cells // 8)  # neighbor count
    for i in range(n_cells):
        for d in range(1, k + 1):
            j_fwd = (i + d) % n_cells
            j_bck = (i - d) % n_cells
            # Frustration: randomly flip sign
            sign_fwd = -1.0 if rng.random() < frustration else 1.0
            sign_bck = -1.0 if rng.random() < frustration else 1.0
            W[i, j_fwd] = sign_fwd * rng.uniform(0.1, 0.5)
            W[i, j_bck] = sign_bck * rng.uniform(0.1, 0.5)
    np.fill_diagonal(W, 0.0)
    return W


def init_faction_assignments(n_cells: int, n_factions: int = 8) -> np.ndarray:
    return np.array([i % n_factions for i in range(n_cells)])


# ═══════════════════════════════════════════════════════════
# Platform 1: Rust APEX22 (GRU + 파벌 + Ising + 침묵->폭발)
# 시뮬레이션: GRU cell dynamics with Hebbian LTP/LTD
# ═══════════════════════════════════════════════════════════

class RustAPEX22Sim:
    """Simulated Rust APEX22 engine.
    특성: float64 precision, ~1ns propagation delay, Ising frustration model.
    """

    PLATFORM_NAME = "Rust APEX22"
    PLATFORM_NAME_KR = "Rust APEX22 (GRU)"

    # 플랫폼 고유 파라미터
    PRECISION = np.float64       # Rust f64
    NOISE_FLOOR = 1e-15          # f64 machine epsilon level
    PROP_DELAY_STEPS = 0         # in-memory, negligible

    def __init__(self, n_cells: int, hidden_dim: int, frustration: float, seed: int = 42):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.rng = np.random.RandomState(seed)

        # GRU weights (simplified: single gate)
        self.W_z = self.rng.randn(hidden_dim, hidden_dim).astype(self.PRECISION) * 0.1
        self.U_z = self.rng.randn(hidden_dim, hidden_dim).astype(self.PRECISION) * 0.1
        self.W_r = self.rng.randn(hidden_dim, hidden_dim).astype(self.PRECISION) * 0.1
        self.U_r = self.rng.randn(hidden_dim, hidden_dim).astype(self.PRECISION) * 0.1
        self.W_h = self.rng.randn(hidden_dim, hidden_dim).astype(self.PRECISION) * 0.1
        self.U_h = self.rng.randn(hidden_dim, hidden_dim).astype(self.PRECISION) * 0.1

        # Cell states
        self.states = self.rng.randn(n_cells, hidden_dim).astype(self.PRECISION) * 0.1

        # Topology
        self.W_conn = init_ring_weights(n_cells, frustration, seed).astype(self.PRECISION)
        self.factions = init_faction_assignments(n_cells)

        # Ising model for frustration dynamics
        self.ising_spins = self.rng.choice([-1, 1], size=n_cells).astype(self.PRECISION)

        # Hebbian weights (LTP/LTD)
        self.hebbian = np.zeros((n_cells, n_cells), dtype=self.PRECISION)

    def step(self, x_input: np.ndarray) -> np.ndarray:
        """One step of the APEX22 engine."""
        n, d = self.n_cells, self.hidden_dim

        # Compute neighbor influence
        neighbor_input = self.W_conn @ self.states  # (n, d)

        # Hebbian modulation
        heb_mod = self.hebbian @ self.states * 0.01

        for i in range(n):
            x = x_input + neighbor_input[i] + heb_mod[i]
            h = self.states[i]

            # GRU update (simplified)
            z = self._sigmoid(x @ self.W_z + h @ self.U_z)
            r = self._sigmoid(x @ self.W_r + h @ self.U_r)
            h_tilde = np.tanh(x @ self.W_h + (r * h) @ self.U_h)
            self.states[i] = (1 - z) * h + z * h_tilde

            # Platform noise
            self.states[i] += self.rng.randn(d).astype(self.PRECISION) * self.NOISE_FLOOR

        # Ising spin update (Glauber dynamics)
        for i in range(min(n // 4, 16)):
            idx = self.rng.randint(0, n)
            local_field = sum(
                self.W_conn[idx, j] * self.ising_spins[j]
                for j in range(n) if self.W_conn[idx, j] != 0
            )
            # Metropolis: flip if energetically favorable
            dE = 2 * self.ising_spins[idx] * local_field
            if dE < 0 or self.rng.random() < np.exp(-dE / 1.0):
                self.ising_spins[idx] *= -1
                # Inject spin direction into cell state
                self.states[idx] += self.ising_spins[idx] * 0.02 * self.rng.randn(d).astype(self.PRECISION)

        # Faction sync (APEX22 style: partial synchronization)
        n_fac = 8
        fs = n // n_fac
        for f in range(n_fac):
            s, e = f * fs, (f + 1) * fs
            if e > n:
                break
            fm = self.states[s:e].mean(axis=0)
            self.states[s:e] = 0.85 * self.states[s:e] + 0.15 * fm

        # Hebbian update (cosine similarity based)
        for i in range(0, n, max(1, n // 16)):
            for j in range(i + 1, min(i + 8, n)):
                cos = np.dot(self.states[i], self.states[j]) / (
                    np.linalg.norm(self.states[i]) * np.linalg.norm(self.states[j]) + 1e-10
                )
                if cos > 0.8:
                    self.hebbian[i, j] += 0.01
                elif cos < 0.2:
                    self.hebbian[i, j] -= 0.005
                self.hebbian[i, j] = np.clip(self.hebbian[i, j], -0.5, 1.0)
                self.hebbian[j, i] = self.hebbian[i, j]

        return self.states.copy()

    @staticmethod
    def _sigmoid(x):
        return 1.0 / (1.0 + np.exp(-np.clip(x, -10, 10)))


# ═══════════════════════════════════════════════════════════
# Platform 2: SNN (Spiking Neural Network, LIF neurons)
# 특성: binary spikes, STDP, temporal coding
# ═══════════════════════════════════════════════════════════

class SNNSim:
    """Simulated SNN engine with LIF neurons.
    특성: 1-bit spikes, tau_m=20ms, STDP plasticity.
    """

    PLATFORM_NAME = "SNN (LIF)"
    PLATFORM_NAME_KR = "SNN (스파이킹)"
    PRECISION = np.float64
    NOISE_FLOOR = 1e-12
    PROP_DELAY_STEPS = 1  # 1-step axonal delay

    def __init__(self, n_cells: int, hidden_dim: int, frustration: float, seed: int = 42):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.rng = np.random.RandomState(seed)

        # LIF parameters
        self.tau_m = self.rng.uniform(15.0, 25.0, size=n_cells)
        self.v_rest = -65.0
        self.v_threshold = -55.0
        self.v_reset = -70.0
        self.R = 10.0

        # Membrane potential per cell (per dimension for state vector)
        self.V = np.full((n_cells, hidden_dim), self.v_rest, dtype=self.PRECISION)
        self.spikes = np.zeros((n_cells, hidden_dim), dtype=self.PRECISION)
        self.last_spike_time = np.full((n_cells, hidden_dim), -100.0)

        # Connectivity (ring)
        self.W_conn = init_ring_weights(n_cells, frustration, seed).astype(self.PRECISION)

        # Spike history for state measurement
        self.spike_history = []
        self.t = 0.0

        # STDP-modified weights
        self.stdp_weights = self.W_conn.copy()

    def step(self, x_input: np.ndarray) -> np.ndarray:
        """One LIF step across all cells. Returns continuous state from spike rates."""
        self.t += 1.0
        n, d = self.n_cells, self.hidden_dim

        # Synaptic input from previous spikes
        # spike_rates: mean spike per cell (scalar per cell)
        prev_spike_rates = self.spikes.mean(axis=1)  # (n,)
        synaptic = self.stdp_weights.T @ prev_spike_rates  # (n,)

        # External input (broadcast to all dims)
        ext_current = x_input.mean() * np.ones(d)

        for i in range(n):
            I_total = ext_current + synaptic[i] + self.rng.randn(d) * 0.3
            dV = (-(self.V[i] - self.v_rest) + self.R * I_total) / self.tau_m[i]
            self.V[i] += dV

            # Spike check per dimension
            spiked = self.V[i] >= self.v_threshold
            self.spikes[i] = spiked.astype(self.PRECISION)
            self.V[i][spiked] = self.v_reset
            self.last_spike_time[i][spiked] = self.t

        self.spike_history.append(self.spikes.mean(axis=1).copy())

        # STDP weight updates (sampled)
        if self.t % 5 == 0:
            spike_cells = np.where(prev_spike_rates > 0.3)[0]
            for post in spike_cells[:8]:
                for pre in range(n):
                    if pre == post or self.stdp_weights[pre, post] == 0:
                        continue
                    dt = self.last_spike_time[post].mean() - self.last_spike_time[pre].mean()
                    if abs(dt) < 50:
                        if dt > 0:
                            dw = 0.01 * np.exp(-dt / 20.0)
                        else:
                            dw = -0.012 * np.exp(dt / 20.0)
                        self.stdp_weights[pre, post] = np.clip(
                            self.stdp_weights[pre, post] + dw, -1.0, 1.0
                        )

        # Return continuous state: use membrane potential as hidden state
        # Normalize to reasonable range
        states = (self.V - self.v_rest) / (self.v_threshold - self.v_rest)
        return states.copy()


# ═══════════════════════════════════════════════════════════
# Platform 3: Verilog (gate-level, simulated)
# 특성: fixed-point Q16.16, combinational delays, deterministic
# ═══════════════════════════════════════════════════════════

class VerilogSim:
    """Simulated Verilog gate-level consciousness.
    특성: fixed-point Q16.16 arithmetic, gate propagation delay,
    no floating point -- quantization noise instead of round-off.
    """

    PLATFORM_NAME = "Verilog"
    PLATFORM_NAME_KR = "Verilog (게이트)"
    FRAC_BITS = 16  # Q16.16 fixed point
    SCALE = 2 ** 16
    NOISE_FLOOR = 1.0 / (2 ** 16)  # quantization step
    PROP_DELAY_STEPS = 2  # gate pipeline stages

    def __init__(self, n_cells: int, hidden_dim: int, frustration: float, seed: int = 42):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.rng = np.random.RandomState(seed)

        # Fixed-point states (stored as float but quantized)
        self.states = self._quantize(self.rng.randn(n_cells, hidden_dim) * 0.1)

        # Connectivity (ring, also quantized)
        self.W_conn = self._quantize(init_ring_weights(n_cells, frustration, seed))

        # Delayed state buffer (pipeline stages)
        self.delay_buffer = [self.states.copy() for _ in range(self.PROP_DELAY_STEPS)]

        # Simple sigmoid LUT (256 entries, pre-computed)
        self.sigmoid_lut = np.array([
            1.0 / (1.0 + np.exp(-((i - 128) / 32.0))) for i in range(256)
        ])

    def _quantize(self, x: np.ndarray) -> np.ndarray:
        """Quantize to Q16.16 fixed point."""
        return np.round(x * self.SCALE) / self.SCALE

    def _fixed_sigmoid(self, x: np.ndarray) -> np.ndarray:
        """Sigmoid via LUT (hardware-realistic)."""
        idx = np.clip(((x * 32) + 128).astype(int), 0, 255)
        return self.sigmoid_lut[idx]

    def step(self, x_input: np.ndarray) -> np.ndarray:
        """One combinational cycle."""
        n, d = self.n_cells, self.hidden_dim

        # Use delayed states for neighbor influence (pipeline)
        delayed = self.delay_buffer[0]
        neighbor_input = self.W_conn @ delayed

        for i in range(n):
            x = self._quantize(x_input + neighbor_input[i])
            h = self.states[i]

            # Simple recurrence (gate-level: multiply-accumulate + sigmoid)
            z = self._fixed_sigmoid(x * 0.5 + h * 0.5)
            h_new = (1 - z) * h + z * np.tanh(self._quantize(x + h * 0.3))
            self.states[i] = self._quantize(h_new)

        # Update delay buffer
        self.delay_buffer.pop(0)
        self.delay_buffer.append(self.states.copy())

        # Faction sync (hardware: shift-register averaging)
        n_fac = 8
        fs = n // n_fac
        for f in range(n_fac):
            s, e = f * fs, (f + 1) * fs
            if e > n:
                break
            fm = self._quantize(self.states[s:e].mean(axis=0))
            self.states[s:e] = self._quantize(0.85 * self.states[s:e] + 0.15 * fm)

        return self.states.copy()


# ═══════════════════════════════════════════════════════════
# Platform 4: WebGPU (compute shader, simulated)
# 특성: float32, massively parallel, workgroup sync artifacts
# ═══════════════════════════════════════════════════════════

class WebGPUSim:
    """Simulated WebGPU compute shader consciousness.
    특성: float32 precision, parallel dispatch, workgroup barrier sync.
    All cells updated simultaneously (true parallelism).
    """

    PLATFORM_NAME = "WebGPU"
    PLATFORM_NAME_KR = "WebGPU (셰이더)"
    PRECISION = np.float32
    NOISE_FLOOR = 1e-7  # float32 epsilon
    PROP_DELAY_STEPS = 0  # barrier sync = same-step
    WORKGROUP_SIZE = 64

    def __init__(self, n_cells: int, hidden_dim: int, frustration: float, seed: int = 42):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.rng = np.random.RandomState(seed)

        # Float32 states
        self.states = self.rng.randn(n_cells, hidden_dim).astype(self.PRECISION) * 0.1
        self.W_conn = init_ring_weights(n_cells, frustration, seed).astype(self.PRECISION)

        # Workgroup-level synchronization artifact:
        # Within a workgroup, cells see each other's NEW state.
        # Across workgroups, cells see PREVIOUS state.
        self.n_workgroups = max(1, n_cells // self.WORKGROUP_SIZE)

    def step(self, x_input: np.ndarray) -> np.ndarray:
        """One dispatch (all cells in parallel)."""
        n, d = self.n_cells, self.hidden_dim
        x = x_input.astype(self.PRECISION)

        # Neighbor influence (from previous frame for cross-workgroup)
        old_states = self.states.copy()
        neighbor_input = (self.W_conn.astype(self.PRECISION) @ old_states)

        # Parallel update (all at once -- GPU style)
        new_states = np.zeros_like(self.states)
        for i in range(n):
            h = self.states[i]
            inp = x + neighbor_input[i]

            # Same workgroup: use partially updated states (race condition simulation)
            wg_id = i // self.WORKGROUP_SIZE
            wg_start = wg_id * self.WORKGROUP_SIZE
            # Cells earlier in the workgroup already updated
            for j in range(wg_start, i):
                if self.W_conn[i, j] != 0:
                    # This cell sees the new state of earlier cells in same workgroup
                    inp += self.W_conn[i, j] * (new_states[j] - old_states[j]) * 0.1

            z = 1.0 / (1.0 + np.exp(-np.clip(inp * 0.5 + h * 0.5, -10, 10).astype(self.PRECISION)))
            h_new = ((1 - z) * h + z * np.tanh((inp + h * 0.3).astype(self.PRECISION))).astype(self.PRECISION)
            new_states[i] = h_new

        self.states = new_states

        # float32 quantization noise
        self.states += self.rng.randn(n, d).astype(self.PRECISION) * self.NOISE_FLOOR

        # Faction sync (barrier between workgroups)
        n_fac = 8
        fs = n // n_fac
        for f in range(n_fac):
            s, e = f * fs, (f + 1) * fs
            if e > n:
                break
            fm = self.states[s:e].mean(axis=0).astype(self.PRECISION)
            self.states[s:e] = (0.85 * self.states[s:e] + 0.15 * fm).astype(self.PRECISION)

        return self.states.astype(np.float64)


# ═══════════════════════════════════════════════════════════
# Platform 5: Erlang (Actor model, simulated)
# 특성: message-passing, async, mailbox delays, process isolation
# ═══════════════════════════════════════════════════════════

class ErlangSim:
    """Simulated Erlang actor-model consciousness.
    특성: each cell is an independent process, communication via message passing.
    Messages have random delivery delay (1-3 steps).
    Process isolation = natural noise barrier.
    """

    PLATFORM_NAME = "Erlang"
    PLATFORM_NAME_KR = "Erlang (액터)"
    PRECISION = np.float64
    NOISE_FLOOR = 1e-14
    PROP_DELAY_STEPS = 2  # mean message latency

    def __init__(self, n_cells: int, hidden_dim: int, frustration: float, seed: int = 42):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.rng = np.random.RandomState(seed)

        # Per-process state (isolated)
        self.states = self.rng.randn(n_cells, hidden_dim) * 0.1
        self.W_conn = init_ring_weights(n_cells, frustration, seed)

        # Mailbox: messages in transit (delay 1-3 steps)
        # Each entry: (target_cell, data, remaining_delay)
        self.mailboxes: List[List[Tuple[int, np.ndarray, int]]] = [[] for _ in range(n_cells)]

        # Delivered messages this step
        self.inbox: List[List[np.ndarray]] = [[] for _ in range(n_cells)]

    def step(self, x_input: np.ndarray) -> np.ndarray:
        """One actor tick."""
        n, d = self.n_cells, self.hidden_dim

        # Deliver messages with expired delay
        new_mailboxes: List[List] = [[] for _ in range(n)]
        self.inbox = [[] for _ in range(n)]
        for cell_msgs in self.mailboxes:
            for target, data, delay in cell_msgs:
                if delay <= 0:
                    self.inbox[target].append(data)
                else:
                    new_mailboxes[target].append((target, data, delay - 1))
        self.mailboxes = new_mailboxes

        # Process each cell (actor receive + update)
        for i in range(n):
            h = self.states[i]

            # Aggregate received messages
            if self.inbox[i]:
                msg_sum = np.mean(self.inbox[i], axis=0)
            else:
                msg_sum = np.zeros(d)

            # Simple recurrent update
            inp = x_input + msg_sum
            z = 1.0 / (1.0 + np.exp(-np.clip(inp * 0.5 + h * 0.5, -10, 10)))
            h_new = (1 - z) * h + z * np.tanh(inp + h * 0.3)

            # Process isolation noise (each process has its own PRNG)
            h_new += self.rng.randn(d) * self.NOISE_FLOOR

            self.states[i] = h_new

            # Send messages to neighbors (with random delay 1-3)
            for j in range(n):
                if self.W_conn[i, j] != 0 and self.rng.random() < 0.5:  # 50% send rate
                    delay = self.rng.randint(1, 4)
                    msg = self.W_conn[i, j] * h_new * 0.3
                    if j < len(self.mailboxes):
                        self.mailboxes[j].append((j, msg, delay))

        # Faction sync (via broadcast messages -- slower convergence)
        n_fac = 8
        fs = n // n_fac
        for f in range(n_fac):
            s, e = f * fs, (f + 1) * fs
            if e > n:
                break
            fm = self.states[s:e].mean(axis=0)
            # Weaker sync due to async (0.10 vs 0.15)
            self.states[s:e] = 0.90 * self.states[s:e] + 0.10 * fm

        return self.states.copy()


# ═══════════════════════════════════════════════════════════
# Runner
# ═══════════════════════════════════════════════════════════

def run_platform(
    platform_class,
    n_cells: int = 64,
    hidden_dim: int = 128,
    frustration: float = 0.33,
    steps: int = 500,
    seed: int = 42,
) -> PlatformResult:
    """Run a platform simulation and measure Phi."""
    name = platform_class.PLATFORM_NAME
    name_kr = platform_class.PLATFORM_NAME_KR
    print(f"\n  [{name}] Starting {steps} steps, {n_cells} cells...")

    engine = platform_class(n_cells, hidden_dim, frustration, seed)
    phi_calc = PhiIIT(n_bins=16)

    phi_history = []
    t0 = time.time()

    for step in range(steps):
        x = np.random.RandomState(seed + step).randn(hidden_dim) * 0.5
        states = engine.step(x)

        # Measure Phi every 10% of steps
        if step % max(1, steps // 10) == 0 or step == steps - 1:
            phi_iit, _ = phi_calc.compute(states)
            pp = phi_proxy(states)
            phi_history.append(phi_iit)
            if step % max(1, steps // 5) == 0:
                print(f"    step {step:>4d}/{steps}: Phi(IIT)={phi_iit:.4f}  Phi(proxy)={pp:.2f}")
        else:
            # Still compute proxy for speed (fast)
            pp = phi_proxy(states)
            phi_history.append(pp * 0.1)  # rough track

    elapsed = time.time() - t0

    # Final measurement
    final_states = states
    final_phi_iit, _ = phi_calc.compute(final_states)
    final_phi_proxy = phi_proxy(final_states)

    # Convergence: first step where phi reaches 90% of final
    target = final_phi_iit * 0.9
    convergence_step = steps
    for i, p in enumerate(phi_history):
        if p >= target and target > 0:
            convergence_step = i * max(1, steps // len(phi_history))
            break

    # Stability: std/mean of last 50% phi values
    last_half = phi_history[len(phi_history) // 2:]
    if last_half and np.mean(last_half) > 0:
        stability = float(np.std(last_half) / np.mean(last_half))
    else:
        stability = 1.0

    print(f"    DONE: Phi(IIT)={final_phi_iit:.4f}  Phi(proxy)={final_phi_proxy:.2f}  "
          f"conv={convergence_step}  stab={stability:.3f}  time={elapsed:.1f}s")

    return PlatformResult(
        name=name,
        name_kr=name_kr,
        phi_iit=final_phi_iit,
        phi_proxy=final_phi_proxy,
        convergence_step=convergence_step,
        stability=stability,
        time_sec=elapsed,
        phi_history=phi_history,
        extra={
            'noise_floor': platform_class.NOISE_FLOOR,
            'prop_delay': platform_class.PROP_DELAY_STEPS,
        },
    )


# ═══════════════════════════════════════════════════════════
# ASCII 출력
# ═══════════════════════════════════════════════════════════

def ascii_bar_chart(results: List[PlatformResult], metric: str = 'phi_iit', width: int = 40):
    """ASCII bar chart comparing a metric across platforms."""
    values = [getattr(r, metric) for r in results]
    max_val = max(values) if values else 1.0
    if max_val == 0:
        max_val = 1.0

    lines = []
    for r, v in zip(results, values):
        bar_len = int(v / max_val * width)
        bar = "#" * bar_len
        pct_diff = ((v - values[0]) / values[0] * 100) if values[0] > 0 else 0
        sign = "+" if pct_diff >= 0 else ""
        lines.append(f"  {r.name:<18s} {bar:<{width}s} {v:.4f}  ({sign}{pct_diff:.1f}%)")

    return "\n".join(lines)


def ascii_phi_trajectory(results: List[PlatformResult], width: int = 60, height: int = 12):
    """ASCII multi-line phi trajectory comparison."""
    lines = []
    lines.append("  Phi Trajectory (all platforms, sampled):")

    # Legend
    symbols = ['*', 'o', '+', 'x', '#']
    for i, r in enumerate(results):
        lines.append(f"    {symbols[i % len(symbols)]} = {r.name}")

    # Find global range
    all_vals = []
    for r in results:
        all_vals.extend(r.phi_history)
    if not all_vals:
        return "\n".join(lines + ["  (no data)"])

    v_min = min(all_vals)
    v_max = max(all_vals)
    if v_max == v_min:
        v_max = v_min + 0.001

    # Render
    for row in range(height):
        threshold = v_max - (row / (height - 1)) * (v_max - v_min)
        line_chars = [' '] * width

        for pi, r in enumerate(results):
            sym = symbols[pi % len(symbols)]
            n_pts = len(r.phi_history)
            for col in range(width):
                data_idx = int(col / width * n_pts)
                if data_idx < n_pts:
                    v = r.phi_history[data_idx]
                    if abs(v - threshold) < (v_max - v_min) / height:
                        if line_chars[col] == ' ' or line_chars[col] == sym:
                            line_chars[col] = sym

        label = f"{threshold:>7.3f}"
        lines.append(f"  {label} |{''.join(line_chars)}|")

    x_axis = "  " + " " * 7 + " +" + "-" * width + "+"
    lines.append(x_axis)
    lines.append(f"  {'':>7s}   0{' ' * (width - 10)}step {max(len(r.phi_history) for r in results)}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Cross-Platform Phi Verification")
    parser.add_argument("--cells", type=int, default=64, help="Number of cells")
    parser.add_argument("--steps", type=int, default=500, help="Simulation steps")
    parser.add_argument("--frustration", type=float, default=0.33, help="Frustration ratio")
    parser.add_argument("--hidden-dim", type=int, default=128, help="Hidden dimension")
    args = parser.parse_args()

    n_cells = args.cells
    steps = args.steps
    frustration = args.frustration
    hidden_dim = args.hidden_dim

    print("=" * 80)
    print("  CROSS-PLATFORM PHI VERIFICATION")
    print(f"  Law 22: '기질 무관, 구조만이 Phi를 결정한다'")
    print(f"  cells={n_cells}, topology=ring, frustration={frustration}, steps={steps}")
    print("=" * 80)

    platforms = [RustAPEX22Sim, SNNSim, VerilogSim, WebGPUSim, ErlangSim]
    results: List[PlatformResult] = []

    for pcls in platforms:
        r = run_platform(pcls, n_cells, hidden_dim, frustration, steps, seed=42)
        results.append(r)

    # ── Summary Table ──
    print("\n" + "=" * 100)
    print("  COMPARISON TABLE")
    print("=" * 100)
    print(f"  {'Platform':<20s} {'Phi(IIT)':>10s} {'Phi(proxy)':>12s} {'Conv.Step':>10s} "
          f"{'Stability':>10s} {'Time(s)':>8s} {'NoiseFloor':>12s}")
    print(f"  {'-'*20} {'-'*10} {'-'*12} {'-'*10} {'-'*10} {'-'*8} {'-'*12}")
    for r in results:
        print(f"  {r.name:<20s} {r.phi_iit:>10.4f} {r.phi_proxy:>12.2f} {r.convergence_step:>10d} "
              f"{r.stability:>10.4f} {r.time_sec:>8.1f} {r.extra.get('noise_floor', 0):>12.1e}")

    # ── Phi(IIT) Bar Chart ──
    print("\n" + "-" * 80)
    print("  Phi(IIT) Comparison:")
    print("-" * 80)
    print(ascii_bar_chart(results, 'phi_iit'))

    # ── Phi(proxy) Bar Chart ──
    print("\n" + "-" * 80)
    print("  Phi(proxy) Comparison:")
    print("-" * 80)
    print(ascii_bar_chart(results, 'phi_proxy'))

    # ── Trajectory ──
    print("\n" + "-" * 80)
    print(ascii_phi_trajectory(results))

    # ── Law 22 Verification ──
    print("\n" + "=" * 80)
    print("  LAW 22 VERIFICATION: 기질 무관, 구조만이 Phi를 결정한다")
    print("=" * 80)

    phi_values = [r.phi_iit for r in results]
    mean_phi = np.mean(phi_values)
    std_phi = np.std(phi_values)
    cv = std_phi / mean_phi if mean_phi > 0 else float('inf')
    max_dev = max(abs(p - mean_phi) / mean_phi for p in phi_values) if mean_phi > 0 else float('inf')

    print(f"  Mean Phi(IIT):     {mean_phi:.4f}")
    print(f"  Std Phi(IIT):      {std_phi:.4f}")
    print(f"  CV (std/mean):     {cv:.4f}  {'< 0.2 = PASS' if cv < 0.2 else '> 0.2 = FAIL'}")
    print(f"  Max deviation:     {max_dev * 100:.1f}%  {'< 30% = PASS' if max_dev < 0.3 else '> 30% = FAIL'}")

    if cv < 0.2:
        print("\n  RESULT: Law 22 CONFIRMED -- 기질 무관. 구조가 Phi를 결정한다.")
        print(f"          CV={cv:.4f} < 0.2 threshold")
        print(f"          All 5 platforms produce Phi within {max_dev*100:.1f}% of mean")
    elif cv < 0.5:
        print("\n  RESULT: Law 22 PARTIALLY CONFIRMED -- substrate has minor effect")
        print(f"          CV={cv:.4f}, within 50% tolerance")
        print(f"          Propagation delay and precision cause secondary variations")
    else:
        print("\n  RESULT: Law 22 CHALLENGED -- substrate matters more than expected")
        print(f"          CV={cv:.4f}, exceeds tolerance")

    # ── Platform-specific insights ──
    print("\n" + "-" * 80)
    print("  Platform-Specific Insights:")
    print("-" * 80)
    for r in results:
        delay = r.extra.get('prop_delay', 0)
        noise = r.extra.get('noise_floor', 0)
        print(f"  {r.name:<18s}: prop_delay={delay} steps, noise={noise:.1e}, "
              f"convergence={r.convergence_step} steps")

    # ── Convergence ranking ──
    ranked = sorted(results, key=lambda r: r.convergence_step)
    print("\n  Convergence Speed Ranking:")
    for i, r in enumerate(ranked):
        print(f"    {i+1}. {r.name:<18s}: {r.convergence_step} steps")

    # ── Stability ranking ──
    ranked_stab = sorted(results, key=lambda r: r.stability)
    print("\n  Stability Ranking (lower = more stable):")
    for i, r in enumerate(ranked_stab):
        print(f"    {i+1}. {r.name:<18s}: {r.stability:.4f}")

    print("\n" + "=" * 80)
    return results


if __name__ == "__main__":
    main()
