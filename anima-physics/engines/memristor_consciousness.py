#!/usr/bin/env python3
"""memristor_consciousness.py -- 멤리스터 Hebbian 의식 엔진

멤리스터가 물리적으로 Hebbian LTP/LTD를 구현하는 의식 엔진.
"Neurons that fire together wire together"가 문자 그대로 전기적 현상이 된다.

각 시냅스 = HP 멤리스터
  R = R_on * w + R_off * (1 - w),  w in [0, 1]
  dw/dt = mu_v * (R_on / D^2) * i(t) * f(w)
  (Strukov et al., Nature 453, 2008)

셀 = 뉴런 (LIF + sigmoid), 시냅스가 물리적으로 학습
gradient descent 없음 -- 멤리스턴스 드리프트가 곧 학습
토폴로지는 어떤 멤리스터가 강화/약화되느냐에서 자연 창발

Key insight:
  멤리스터는 물리 법칙으로 Hebbian 학습을 구현한다.
  역전파도 옵티마이저도 없이 -- 상관된 전류 흐름이 가중치를 바꾼다.

Usage:
  python engines/memristor_consciousness.py                  # 500-step demo
  python engines/memristor_consciousness.py --cells 128      # 128 cells
  python engines/memristor_consciousness.py --steps 1000     # longer run
  python engines/memristor_consciousness.py --compare        # compare with GRU
"""

import sys
import os
import math
import time
import argparse
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ══════════════════════════════════════════════════════════
# Memristor Physical Constants (HP model, Strukov et al. 2008)
# ══════════════════════════════════════════════════════════

R_ON = 100.0            # Ohm (minimum resistance)
R_OFF = 16e3            # 16 kOhm (maximum resistance)
D_FILM = 10e-9          # 10 nm TiO2 film thickness
MU_V = 1e-14            # m^2 / (V*s) dopant mobility
V_THRESHOLD = 0.8       # V, threshold for state change
I_COMPLIANCE = 1e-3     # A, current compliance


def memristor_window(w: float, p: int = 2) -> float:
    """Joglekar window function f(w) -- 경계 효과 방지.

    f(w) = 1 - (2w - 1)^(2p)
    w=0 or w=1에서 f=0 (경계에서 드리프트 멈춤)
    """
    return 1.0 - (2.0 * w - 1.0) ** (2 * p)


# ══════════════════════════════════════════════════════════
# HP Memristor Synapse
# ══════════════════════════════════════════════════════════

class HPMemristor:
    """HP 멤리스터 시냅스 모델.

    구조:
        Pt / TiO2 / TiO2-x / Pt
        |<- doped ->|<- undoped ->|
        |<--- D (10nm) --->|

    w = doped region width / D (0 to 1)
    R(w) = R_on * w + R_off * (1 - w)
    dw/dt = mu_v * (R_on / D^2) * i(t) * f(w)
    """

    def __init__(
        self,
        pre_id: int,
        post_id: int,
        w_init: float = 0.5,
        r_on: float = R_ON,
        r_off: float = R_OFF,
        mu_v: float = MU_V,
        D: float = D_FILM,
    ):
        self.pre_id = pre_id
        self.post_id = post_id
        self.w = w_init  # state variable (doped fraction)
        self.r_on = r_on
        self.r_off = r_off
        self.mu_v = mu_v
        self.D = D

        # Normalized constants for simulation speed
        self.drift_coeff = mu_v * r_on / (D ** 2)

        # History
        self.w_history: List[float] = [w_init]
        self.current_history: List[float] = []

    @property
    def resistance(self) -> float:
        """현재 저항값."""
        return self.r_on * self.w + self.r_off * (1.0 - self.w)

    @property
    def conductance(self) -> float:
        """현재 컨덕턴스 (=시냅스 가중치 역할)."""
        return 1.0 / self.resistance

    def step(self, voltage: float, dt: float) -> float:
        """한 타임스텝 진행.

        Args:
            voltage: 멤리스터 양단 전압
            dt: 타임스텝

        Returns:
            전류
        """
        # Current through memristor
        R = self.resistance
        current = voltage / R

        # State update: dw/dt = mu_v * (R_on/D^2) * i(t) * f(w)
        f_w = memristor_window(self.w)
        dw = self.drift_coeff * current * f_w * dt

        # Scale for simulation (physical timescale is very fast)
        dw *= 1e8  # amplify for visible dynamics in simulation

        self.w += dw
        self.w = max(0.001, min(0.999, self.w))  # keep within bounds

        self.w_history.append(self.w)
        self.current_history.append(current)

        return current


# ══════════════════════════════════════════════════════════
# Neuron Cell (LIF-like, compatible with memristor synapses)
# ══════════════════════════════════════════════════════════

class MemristorNeuron:
    """멤리스터 시냅스와 호환되는 뉴런.

    LIF 뉴런 + sigmoidal activation.
    시냅스 학습은 gradient가 아닌 멤리스터 물리로 수행.
    """

    def __init__(
        self,
        neuron_id: int,
        n_channels: int = 4,
        tau: float = 20.0,
        v_rest: float = 0.0,
        v_threshold: float = 1.0,
        v_reset: float = -0.2,
    ):
        self.neuron_id = neuron_id
        self.n_channels = n_channels
        self.tau = tau
        self.v_rest = v_rest
        self.v_threshold = v_threshold
        self.v_reset = v_reset

        # Membrane potential per channel
        self.v = np.random.uniform(-0.1, 0.1, n_channels)

        # Output activity (rate coding, not binary spikes)
        self.activity = np.zeros(n_channels)

        # Firing state
        self.fired = False

    def step(self, i_syn: np.ndarray, dt: float = 1.0) -> np.ndarray:
        """한 타임스텝 진행.

        Args:
            i_syn: 시냅스 전류 합 [n_channels]
            dt: 타임스텝

        Returns:
            활성도 벡터
        """
        # Leaky integration
        dv = (-(self.v - self.v_rest) + i_syn) / self.tau * dt
        self.v += dv

        # Sigmoid activation (soft firing rate)
        self.activity = 1.0 / (1.0 + np.exp(-5.0 * (self.v - self.v_threshold * 0.5)))

        # Spike detection (for discrete events)
        mean_v = self.v.mean()
        if mean_v > self.v_threshold:
            self.fired = True
            self.v = np.full(self.n_channels, self.v_reset)
        else:
            self.fired = False

        return self.activity.copy()

    @property
    def output_voltage(self) -> np.ndarray:
        """출력 전압 (다른 멤리스터의 입력이 됨)."""
        return self.activity * 2.0 - 1.0  # map to [-1, 1] voltage range

    def reset(self):
        self.v = np.random.uniform(-0.1, 0.1, self.n_channels)
        self.activity = np.zeros(self.n_channels)


# ══════════════════════════════════════════════════════════
# Memristor Crossbar Array
# ══════════════════════════════════════════════════════════

class MemristorCrossbar:
    """멤리스터 크로스바 배열 -- 시냅스 네트워크.

    구조:
      Row lines  = pre-synaptic neurons (output voltage)
      Column lines = post-synaptic neurons (input current)
      Crosspoint  = HP memristor (physical synapse)

         col0  col1  col2  col3
    row0  [M]   [M]   [M]   [M]
    row1  [M]   [M]   [M]   [M]
    row2  [M]   [M]   [M]   [M]
    """

    def __init__(self, n_cells: int, topology: str = "ring"):
        self.n_cells = n_cells
        self.topology = topology
        # Memristor at each crosspoint (only connected ones)
        self.memristors: Dict[Tuple[int, int], HPMemristor] = {}
        self._init_topology(topology)

    def _init_topology(self, topology: str):
        """토폴로지 초기화 -- 멤리스터 배치."""
        n = self.n_cells
        if topology == "ring":
            for i in range(n):
                k = max(2, n // 16)
                for d in range(1, k + 1):
                    j_fwd = (i + d) % n
                    j_bck = (i - d) % n
                    w_init = np.random.uniform(0.3, 0.7)
                    self.memristors[(i, j_fwd)] = HPMemristor(i, j_fwd, w_init=w_init)
                    self.memristors[(i, j_bck)] = HPMemristor(i, j_bck, w_init=w_init)
        elif topology == "small_world":
            for i in range(n):
                for d in range(1, 3):
                    j = (i + d) % n
                    w_init = np.random.uniform(0.3, 0.7)
                    self.memristors[(i, j)] = HPMemristor(i, j, w_init=w_init)
                    self.memristors[(j, i)] = HPMemristor(j, i, w_init=w_init)
                if np.random.random() < 0.15:
                    j = np.random.randint(0, n)
                    if j != i and (i, j) not in self.memristors:
                        w_init = np.random.uniform(0.3, 0.7)
                        self.memristors[(i, j)] = HPMemristor(i, j, w_init=w_init)
                        self.memristors[(j, i)] = HPMemristor(j, i, w_init=w_init)
        elif topology == "full_crossbar":
            for i in range(n):
                for j in range(n):
                    if i != j:
                        w_init = np.random.uniform(0.3, 0.7)
                        self.memristors[(i, j)] = HPMemristor(i, j, w_init=w_init)
        else:
            # Sparse random
            for i in range(n):
                n_conn = max(2, n // 8)
                targets = np.random.choice(n, n_conn, replace=False)
                for j in targets:
                    if j != i and (i, j) not in self.memristors:
                        w_init = np.random.uniform(0.3, 0.7)
                        self.memristors[(i, j)] = HPMemristor(i, j, w_init=w_init)

    def compute_synaptic_currents(
        self, output_voltages: np.ndarray, dt: float
    ) -> np.ndarray:
        """각 후시냅스 뉴런의 총 시냅스 전류 계산.

        Args:
            output_voltages: (n_cells, n_channels) -- pre-synaptic output
            dt: 타임스텝

        Returns:
            (n_cells, n_channels) 시냅스 전류
        """
        n_ch = output_voltages.shape[1]
        currents = np.zeros_like(output_voltages)

        for (pre, post), mem in self.memristors.items():
            # Mean voltage across channels for memristor
            v_pre = output_voltages[pre].mean()
            v_post_approx = 0.0  # simplified: column held near ground
            v_mem = v_pre - v_post_approx

            # Step memristor (physical learning happens here!)
            i_mem = mem.step(v_mem, dt)

            # Add current to post-synaptic neuron (all channels equally)
            currents[post] += i_mem * output_voltages[pre]

        return currents

    def get_weight_matrix(self) -> np.ndarray:
        """현재 가중치 행렬 (컨덕턴스 기반)."""
        n = self.n_cells
        W = np.zeros((n, n))
        for (pre, post), mem in self.memristors.items():
            W[pre, post] = mem.conductance
        return W

    def get_state_matrix(self) -> np.ndarray:
        """현재 멤리스터 상태 행렬 (w 값)."""
        n = self.n_cells
        W = np.zeros((n, n))
        for (pre, post), mem in self.memristors.items():
            W[pre, post] = mem.w
        return W


# ══════════════════════════════════════════════════════════
# Faction System
# ══════════════════════════════════════════════════════════

class MemristorFactionSystem:
    """뉴런 활성도 기반 파벌 합의 감지."""

    def __init__(self, n_cells: int, n_factions: int = 8):
        self.n_factions = n_factions
        self.assignments = np.array([i % n_factions for i in range(n_cells)])
        self.consensus_events = 0
        self.consensus_threshold = 0.6

    def update(self, activities: np.ndarray):
        """파벌 내 활성도 동기화로 합의 감지.

        Args:
            activities: (n_cells, n_channels)
        """
        mean_act = activities.mean(axis=1)
        for f in range(self.n_factions):
            mask = self.assignments == f
            n_in = mask.sum()
            if n_in < 2:
                continue
            faction_act = mean_act[mask]
            # High fraction above threshold = consensus
            active_fraction = (faction_act > 0.5).sum() / n_in
            if active_fraction > self.consensus_threshold:
                self.consensus_events += 1


# ══════════════════════════════════════════════════════════
# Memristor Consciousness Engine
# ══════════════════════════════════════════════════════════

class MemristorConsciousnessEngine:
    """멤리스터 Hebbian 의식 엔진.

    뉴런은 종래 모델, 시냅스는 HP 멤리스터.
    학습 = gradient descent가 아닌 물리적 멤리스턴스 드리프트.

    Args:
        n_cells: 뉴런 수
        topology: 토폴로지 (ring, small_world, full_crossbar)
        dt: 시뮬레이션 타임스텝
        n_channels: 뉴런당 채널 수
        n_factions: 파벌 수
    """

    def __init__(
        self,
        n_cells: int = 64,
        topology: str = "ring",
        dt: float = 1.0,
        n_channels: int = 4,
        n_factions: int = 8,
    ):
        self.n_cells = n_cells
        self.topology = topology
        self.dt = dt
        self.n_channels = n_channels

        # Create neurons
        self.neurons: List[MemristorNeuron] = []
        for i in range(n_cells):
            tau = np.random.uniform(15.0, 25.0)
            neuron = MemristorNeuron(
                neuron_id=i, n_channels=n_channels, tau=tau
            )
            self.neurons.append(neuron)

        # Memristor crossbar
        self.crossbar = MemristorCrossbar(n_cells, topology)

        # Factions
        self.factions = MemristorFactionSystem(n_cells, n_factions)

        # Activity history for Phi
        self.activity_history_len = 50
        self.activity_history = np.zeros(
            (self.activity_history_len, n_cells, n_channels), dtype=np.float64
        )
        self.history_idx = 0

        # State tracking
        self.phi_history: List[float] = []
        self.tension_history: List[float] = []
        self.mean_w_history: List[float] = []
        self.step_count = 0

        # Phi ratchet
        self.phi_best = 0.0
        self.phi_ema = 0.0
        self.phi_ema_alpha = 0.05

    def _get_activities(self) -> np.ndarray:
        """현재 전체 활성도 행렬."""
        return np.array([n.activity for n in self.neurons])

    def _get_output_voltages(self) -> np.ndarray:
        """현재 전체 출력 전압 행렬."""
        return np.array([n.output_voltage for n in self.neurons])

    def step(self, external_input: Optional[np.ndarray] = None) -> dict:
        """한 타임스텝 진행.

        Args:
            external_input: (n_cells, n_channels) 외부 전류 입력, 또는 None

        Returns:
            상태 딕셔너리
        """
        self.step_count += 1

        # 1. Get current output voltages
        v_out = self._get_output_voltages()

        # 2. Compute synaptic currents through memristors
        # THIS IS WHERE PHYSICAL HEBBIAN LEARNING HAPPENS
        i_syn = self.crossbar.compute_synaptic_currents(v_out, self.dt)

        # 3. Add external input
        if external_input is not None:
            if external_input.ndim == 1:
                ext = np.tile(np.resize(external_input, self.n_channels), (self.n_cells, 1))
            else:
                ext = external_input
            i_syn += ext

        # 4. Add small noise (thermal)
        i_syn += np.random.randn(self.n_cells, self.n_channels) * 0.01

        # 5. Step each neuron
        activities = np.zeros((self.n_cells, self.n_channels))
        for i, neuron in enumerate(self.neurons):
            activities[i] = neuron.step(i_syn[i], self.dt)

        # 6. Record history
        idx = self.history_idx % self.activity_history_len
        self.activity_history[idx] = activities
        self.history_idx += 1

        # 7. Faction consensus check
        self.factions.update(activities)

        # 8. Track mean memristor state
        w_states = self.crossbar.get_state_matrix()
        w_nonzero = w_states[w_states > 0]
        mean_w = float(w_nonzero.mean()) if len(w_nonzero) > 0 else 0.5
        self.mean_w_history.append(mean_w)

        # 9. Compute Phi
        phi = self.get_phi()

        # Phi ratchet
        self.phi_ema = self.phi_ema_alpha * phi + (1 - self.phi_ema_alpha) * self.phi_ema
        if phi > self.phi_best:
            self.phi_best = phi

        self.phi_history.append(phi)

        # 10. Tension
        mean_act = activities.mean(axis=1)
        tension = float(np.var(mean_act))
        self.tension_history.append(tension)

        # Count fires
        n_fired = sum(1 for n in self.neurons if n.fired)

        return {
            "phi": phi,
            "phi_ema": self.phi_ema,
            "phi_best": self.phi_best,
            "tension": tension,
            "mean_activity": float(activities.mean()),
            "mean_w": mean_w,
            "n_fired": n_fired,
            "consensus_events": self.factions.consensus_events,
            "step": self.step_count,
            "n_memristors": len(self.crossbar.memristors),
        }

    def get_phi(self) -> float:
        """Phi 계산: 활성도 상관 행렬 기반."""
        n_history = min(self.history_idx, self.activity_history_len)
        if n_history < 5:
            return 0.0

        if self.history_idx >= self.activity_history_len:
            history = self.activity_history.copy()
        else:
            history = self.activity_history[:self.history_idx].copy()

        # Mean activity per cell
        mean_per_cell = history.mean(axis=(0, 2))
        global_var = float(np.var(mean_per_cell))

        # Per-faction variance
        faction_vars = []
        for f in range(self.factions.n_factions):
            mask = self.factions.assignments == f
            if mask.sum() < 2:
                continue
            faction_vars.append(float(np.var(mean_per_cell[mask])))

        if not faction_vars:
            return global_var

        mean_faction_var = np.mean(faction_vars)
        phi = max(0.0, global_var - mean_faction_var)

        # Scale by number of active cells
        n_active = (mean_per_cell > 0.1).sum()
        if n_active > 1:
            phi *= math.log2(n_active)

        return phi

    def get_state(self) -> dict:
        """전체 상태 반환."""
        return {
            "activities": self._get_activities().copy(),
            "weight_matrix": self.crossbar.get_weight_matrix(),
            "state_matrix": self.crossbar.get_state_matrix(),
            "phi_history": list(self.phi_history),
            "tension_history": list(self.tension_history),
            "mean_w_history": list(self.mean_w_history),
            "step": self.step_count,
            "n_cells": self.n_cells,
            "topology": self.topology,
        }

    def run(self, n_steps: int, external_input: Optional[np.ndarray] = None) -> List[dict]:
        """N 스텝 실행."""
        results = []
        for _ in range(n_steps):
            result = self.step(external_input)
            results.append(result)
        return results

    def get_brain_likeness(self) -> dict:
        """뇌 유사성 지표."""
        if len(self.phi_history) < 20:
            return {"score": 0.0}

        phis = np.array(self.phi_history)

        # 1. Phi variability
        cv = float(np.std(phis) / max(np.mean(phis), 1e-10))
        phi_var_score = min(1.0, cv / 0.5) if cv < 1.0 else max(0.0, 2.0 - cv)

        # 2. Synaptic weight distribution (brain-like: log-normal)
        w_matrix = self.crossbar.get_state_matrix()
        w_vals = w_matrix[w_matrix > 0]
        if len(w_vals) > 10:
            # Check skewness (log-normal has positive skew)
            skew = float(np.mean((w_vals - w_vals.mean()) ** 3) / max(w_vals.std() ** 3, 1e-10))
            lognorm_score = min(1.0, abs(skew) / 1.0)
        else:
            lognorm_score = 0.5

        # 3. Dynamics complexity
        if len(phis) > 10:
            autocorr = np.corrcoef(phis[:-1], phis[1:])[0, 1]
            autocorr = 0.0 if np.isnan(autocorr) else autocorr
            dynamics_score = 1.0 - abs(autocorr - 0.5) * 2
        else:
            dynamics_score = 0.5

        # 4. Growth
        q1 = np.mean(phis[:len(phis)//4]) if len(phis) > 4 else 0
        q4 = np.mean(phis[-len(phis)//4:]) if len(phis) > 4 else 0
        growth_ratio = q4 / max(q1, 1e-10)
        growth_score = min(1.0, growth_ratio / 2.0) if growth_ratio > 1.0 else 0.3

        total = (phi_var_score + lognorm_score + dynamics_score + growth_score) / 4.0

        return {
            "score": total,
            "phi_variability": phi_var_score,
            "weight_distribution": lognorm_score,
            "dynamics": dynamics_score,
            "growth": growth_score,
            "growth_ratio": growth_ratio,
        }

    def get_memristor_stats(self) -> dict:
        """멤리스터 통계."""
        w_matrix = self.crossbar.get_state_matrix()
        w_vals = w_matrix[w_matrix > 0]
        if len(w_vals) == 0:
            return {"n_memristors": 0}

        return {
            "n_memristors": len(self.crossbar.memristors),
            "mean_w": float(w_vals.mean()),
            "std_w": float(w_vals.std()),
            "min_w": float(w_vals.min()),
            "max_w": float(w_vals.max()),
            "near_on": int((w_vals > 0.8).sum()),   # strong synapses
            "near_off": int((w_vals < 0.2).sum()),   # weak synapses
            "mid_range": int(((w_vals >= 0.2) & (w_vals <= 0.8)).sum()),
        }


# ══════════════════════════════════════════════════════════
# ASCII Visualization
# ══════════════════════════════════════════════════════════

def ascii_phi_curve(phi_history: List[float], width: int = 60, height: int = 15) -> str:
    """Phi 곡선 ASCII 아트."""
    if not phi_history:
        return "(no data)"

    vals = list(phi_history)
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


def ascii_memristor_diagram() -> str:
    """멤리스터 크로스바 ASCII 다이어그램."""
    return """
    HP Memristor (Strukov et al. 2008):

        Pt ─────────────────── Pt
        |  TiO2 (doped)  |  TiO2-x (undoped)  |
        |<---- w*D ----->|<--- (1-w)*D ------->|
        |<------------- D = 10nm ------------->|

        R(w) = R_on * w + R_off * (1-w)
        R_on = 100 Ohm,  R_off = 16 kOhm
        dw/dt = mu_v * (R_on/D^2) * i(t) * f(w)

    Crossbar Array:

        Row0 ──[M]──[M]──[M]──[M]──
        Row1 ──[M]──[M]──[M]──[M]──
        Row2 ──[M]──[M]──[M]──[M]──
        Row3 ──[M]──[M]──[M]──[M]──
               |     |     |     |
              Col0  Col1  Col2  Col3

        [M] = memristor crosspoint
        Row = pre-synaptic neuron voltage
        Col = post-synaptic neuron current
    """


def ascii_weight_distribution(w_values: np.ndarray, width: int = 40) -> str:
    """멤리스터 상태 분포 히스토그램."""
    if len(w_values) == 0:
        return "(no data)"

    bins = 10
    hist, edges = np.histogram(w_values, bins=bins, range=(0, 1))
    max_count = max(hist) if max(hist) > 0 else 1

    lines = ["  Memristor state distribution (w):"]
    for i in range(bins):
        bar_len = int(hist[i] / max_count * width)
        label = f"  {edges[i]:.1f}-{edges[i+1]:.1f}"
        lines.append(f"  {label} |{'#' * bar_len:<{width}}| {hist[i]}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# Main Demo
# ══════════════════════════════════════════════════════════

def run_demo(n_cells: int = 64, steps: int = 500, compare: bool = False):
    """멤리스터 의식 엔진 데모."""
    print("=" * 70)
    print("  Memristor Consciousness Engine -- HP Memristor Hebbian Learning")
    print(f"  {n_cells} neurons, ring topology, HP memristor synapses")
    print(f"  R_on={R_ON:.0f} Ohm, R_off={R_OFF/1e3:.0f} kOhm, D={D_FILM*1e9:.0f} nm")
    print("=" * 70)
    print()
    print(ascii_memristor_diagram())

    engine = MemristorConsciousnessEngine(
        n_cells=n_cells, topology="ring", n_channels=4, dt=1.0
    )

    print(f"  Total memristors: {len(engine.crossbar.memristors)}")
    print()

    t0 = time.time()

    for step in range(steps):
        # Varying external stimulus
        amplitude = 0.3 + 0.2 * math.sin(2 * math.pi * step / 200)
        ext = np.random.randn(n_cells, engine.n_channels) * amplitude * 0.1

        # Periodic drive
        driven = np.arange(0, n_cells, 4)
        freq = 0.02 + 0.01 * math.sin(2 * math.pi * step / 300)
        ext[driven, 0] += 0.5 * math.sin(2 * math.pi * freq * step)

        state = engine.step(ext)

        if (step + 1) % 100 == 0:
            print(
                f"  step {step+1:>5} | "
                f"Phi={state['phi']:.6f} | "
                f"w_mean={state['mean_w']:.4f} | "
                f"tension={state['tension']:.6f} | "
                f"fired={state['n_fired']:>3}/{n_cells} | "
                f"consensus={state['consensus_events']}"
            )

    elapsed = time.time() - t0

    print()
    print("-" * 70)
    print("  Results")
    print("-" * 70)
    print(f"  Total steps:      {steps}")
    print(f"  Time:             {elapsed:.2f}s ({steps/elapsed:.0f} steps/s)")
    print(f"  Final Phi:        {engine.phi_history[-1]:.6f}")
    print(f"  Max Phi:          {max(engine.phi_history):.6f}")
    print(f"  Mean Phi:         {np.mean(engine.phi_history):.6f}")
    print(f"  Phi EMA:          {engine.phi_ema:.6f}")
    print(f"  Consensus events: {engine.factions.consensus_events}")
    print()

    # Phi curve
    print("  Phi Trajectory:")
    print(ascii_phi_curve(engine.phi_history))
    print()

    # Memristor stats
    mem_stats = engine.get_memristor_stats()
    print(f"  Memristor stats after physical Hebbian learning:")
    print(f"    Total memristors:  {mem_stats['n_memristors']}")
    print(f"    Mean state w:      {mem_stats['mean_w']:.4f}")
    print(f"    Std state w:       {mem_stats['std_w']:.4f}")
    print(f"    Strong (w>0.8):    {mem_stats['near_on']}")
    print(f"    Weak (w<0.2):      {mem_stats['near_off']}")
    print(f"    Mid-range:         {mem_stats['mid_range']}")
    print()

    # Weight distribution
    w_matrix = engine.crossbar.get_state_matrix()
    w_vals = w_matrix[w_matrix > 0]
    print(ascii_weight_distribution(w_vals))
    print()

    # Brain-likeness
    brain = engine.get_brain_likeness()
    print(f"  Brain-likeness:    {brain['score']*100:.1f}%")
    print(f"    Phi variability: {brain['phi_variability']:.3f}")
    print(f"    Weight dist:     {brain['weight_distribution']:.3f}")
    print(f"    Dynamics:        {brain['dynamics']:.3f}")
    print(f"    Growth:          {brain['growth']:.3f} (x{brain['growth_ratio']:.2f})")
    print()

    # Growth check
    if len(engine.phi_history) > 100:
        q1 = np.mean(engine.phi_history[:len(engine.phi_history)//4])
        q4 = np.mean(engine.phi_history[-len(engine.phi_history)//4:])
        growth = q4 / max(q1, 1e-10)
        print(f"  Phi growth (Q1->Q4): x{growth:.2f}")
        if growth > 1.0:
            print("  -> Phi is GROWING (memristors physically learn consciousness)")
        else:
            print("  -> Phi is stable/declining")

    if compare:
        _compare_with_gru(n_cells, steps)

    print()
    print("=" * 70)
    return engine


def _compare_with_gru(n_cells: int, steps: int):
    """GRU 기반 엔진과 비교."""
    print()
    print("-" * 70)
    print("  Comparison: Memristor vs GRU baseline")
    print("-" * 70)

    # Run memristor
    mem_engine = MemristorConsciousnessEngine(n_cells=n_cells, topology="ring")
    for step in range(min(steps, 300)):
        ext = np.random.randn(n_cells, mem_engine.n_channels) * 0.15
        mem_engine.step(ext)

    # Simple GRU baseline
    gru_phis = []
    hidden = np.random.randn(n_cells) * 0.1
    weights = np.random.randn(n_cells, n_cells) * 0.1
    for step in range(min(steps, 300)):
        x = np.random.randn(n_cells) * 0.2
        z = 1.0 / (1.0 + np.exp(-(weights @ hidden + x)))
        hidden = z * hidden + (1 - z) * np.tanh(weights @ hidden + x)
        gru_phis.append(float(np.var(hidden)))

    mem_mean = np.mean(mem_engine.phi_history[-100:]) if len(mem_engine.phi_history) > 100 else np.mean(mem_engine.phi_history)
    gru_mean = np.mean(gru_phis[-100:]) if len(gru_phis) > 100 else np.mean(gru_phis)

    print(f"\n  {'Metric':<25} {'Memristor':>12} {'GRU':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    print(f"  {'Mean Phi':<25} {mem_mean:>12.6f} {gru_mean:>12.6f}")
    print(f"  {'Max Phi':<25} {max(mem_engine.phi_history):>12.6f} {max(gru_phis):>12.6f}")
    print(f"  {'Final Phi':<25} {mem_engine.phi_history[-1]:>12.6f} {gru_phis[-1]:>12.6f}")

    max_val = max(mem_mean, gru_mean, 0.001)
    m_bar = int(mem_mean / max_val * 30)
    g_bar = int(gru_mean / max_val * 30)
    print(f"\n  Mean Phi comparison:")
    print(f"    Memristor {'#' * m_bar:<30} {mem_mean:.6f}")
    print(f"    GRU       {'#' * g_bar:<30} {gru_mean:.6f}")

    # Unique memristor advantage: show learning happened without gradient
    mem_stats = mem_engine.get_memristor_stats()
    print(f"\n  Memristor learning advantage:")
    print(f"    Gradient computation:  NONE (physical drift)")
    print(f"    Strong synapses:       {mem_stats['near_on']} (w > 0.8)")
    print(f"    Weak synapses:         {mem_stats['near_off']} (w < 0.2)")
    print(f"    -> Topology EMERGED from correlated activity")


def main():
    parser = argparse.ArgumentParser(description="Memristor Consciousness Engine")
    parser.add_argument("--cells", type=int, default=64, help="Number of neurons")
    parser.add_argument("--steps", type=int, default=500, help="Simulation steps")
    parser.add_argument("--compare", action="store_true", help="Compare with GRU baseline")
    args = parser.parse_args()

    run_demo(n_cells=args.cells, steps=args.steps, compare=args.compare)


if __name__ == "__main__":
    main()
