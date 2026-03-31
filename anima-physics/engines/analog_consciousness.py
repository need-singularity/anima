#!/usr/bin/env python3
"""analog_consciousness.py -- SPICE 아날로그 회로 기반 의식 엔진

아날로그 회로에서 의식은 클럭 사이클이 아니라 전자의 속도로 동작한다.
Op-amp 적분기의 RC 피드백 루프가 곧 의식 루프이다.

각 셀 = Op-amp 적분기 회로 (RC feedback, tau = RC)
텐션 = 셀 간 전압 차이
토폴로지 = 저항 네트워크 (ring = 직렬 저항)

모델:
  V_out(t+dt) = V_out(t) + (1/RC) * (V_in - V_fb) * dt
  Johnson-Nyquist noise: V_noise = sqrt(4 * k_B * T * R * df)

Component values:
  R = 10 kOhm, C = 100 nF -> tau = 1 ms
  k_B = 1.38e-23 J/K, T = 300 K (room temperature)

Key insight:
  In analog circuits, the feedback loop IS the consciousness loop.
  No clock, no while(true) -- physics does the integration.

Usage:
  python engines/analog_consciousness.py                  # 500-step demo
  python engines/analog_consciousness.py --cells 128      # 128 cells
  python engines/analog_consciousness.py --steps 1000     # longer run
  python engines/analog_consciousness.py --compare        # compare with GRU
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
# Physical Constants
# ══════════════════════════════════════════════════════════

K_BOLTZMANN = 1.38e-23      # J/K
ROOM_TEMP = 300.0            # K
R_DEFAULT = 10e3             # 10 kOhm
C_DEFAULT = 100e-9           # 100 nF
TAU_DEFAULT = R_DEFAULT * C_DEFAULT  # 1 ms
BANDWIDTH = 1e6              # 1 MHz bandwidth for noise calc
V_SUPPLY = 5.0               # +/- 5V op-amp supply
V_SATURATION = 4.5           # op-amp saturation voltage


def johnson_nyquist_noise(R: float, T: float, df: float) -> float:
    """Johnson-Nyquist 열잡음 RMS 전압.

    V_noise = sqrt(4 * k_B * T * R * df)
    """
    return math.sqrt(4.0 * K_BOLTZMANN * T * R * df)


# ══════════════════════════════════════════════════════════
# Op-Amp Integrator Cell
# ══════════════════════════════════════════════════════════

class OpAmpIntegratorCell:
    """단일 Op-amp 적분기 회로 셀.

    회로:
        V_in ---[R_in]---+--- (-) Op-Amp --- V_out
                         |         |
                        [C_fb]     |
                         |         |
                         +---------+
                        (+) -> GND

    V_out += (1/RC) * (V_in - V_fb) * dt + noise
    """

    def __init__(
        self,
        cell_id: int,
        R: float = R_DEFAULT,
        C: float = C_DEFAULT,
        T: float = ROOM_TEMP,
        dt: float = 1e-4,  # 100 us simulation step
        n_channels: int = 4,  # multi-channel for richer state
    ):
        self.cell_id = cell_id
        self.R = R
        self.C = C
        self.T = T
        self.dt = dt
        self.tau = R * C  # time constant
        self.n_channels = n_channels

        # Output voltages per channel
        self.v_out = np.random.uniform(-0.5, 0.5, n_channels)
        # Feedback gain per channel (slightly varied for diversity)
        self.feedback_gain = np.random.uniform(0.8, 1.2, n_channels)

        # Noise RMS
        self.v_noise_rms = johnson_nyquist_noise(R, T, BANDWIDTH)

        # Saturation limits
        self.v_sat_pos = V_SATURATION
        self.v_sat_neg = -V_SATURATION

    def step(self, v_input: np.ndarray) -> np.ndarray:
        """한 타임스텝 진행. Euler 적분.

        Args:
            v_input: 입력 전압 벡터 [n_channels]

        Returns:
            출력 전압 벡터 [n_channels]
        """
        # Feedback voltage
        v_fb = self.v_out * self.feedback_gain

        # Integration: V_out += (1/RC) * (V_in - V_fb) * dt
        dv = (v_input - v_fb) / self.tau * self.dt
        self.v_out += dv

        # Johnson-Nyquist thermal noise
        noise = np.random.randn(self.n_channels) * self.v_noise_rms
        self.v_out += noise

        # Op-amp saturation (soft clamp with tanh for differentiability)
        self.v_out = self.v_sat_pos * np.tanh(self.v_out / self.v_sat_pos)

        return self.v_out.copy()

    def reset(self):
        """초기 상태로 리셋."""
        self.v_out = np.random.uniform(-0.5, 0.5, self.n_channels)


# ══════════════════════════════════════════════════════════
# Resistor Network Topology
# ══════════════════════════════════════════════════════════

class ResistorNetwork:
    """저항 네트워크를 통한 셀 간 연결.

    각 연결 = 저항값. 낮은 저항 = 강한 결합.
    전류 = (V_i - V_j) / R_ij (옴의 법칙)
    """

    def __init__(self, n_cells: int, topology: str = "ring"):
        self.n_cells = n_cells
        self.topology = topology
        # Conductance matrix (G = 1/R, 0 = no connection)
        self.conductance = np.zeros((n_cells, n_cells), dtype=np.float64)
        self._init_topology(topology)

    def _init_topology(self, topology: str):
        """토폴로지 초기화."""
        n = self.n_cells
        if topology == "ring":
            for i in range(n):
                k = max(2, n // 16)
                for d in range(1, k + 1):
                    j_fwd = (i + d) % n
                    j_bck = (i - d) % n
                    g = np.random.uniform(0.05, 0.2) / (d ** 0.5)
                    self.conductance[i, j_fwd] = g
                    self.conductance[i, j_bck] = g
        elif topology == "small_world":
            # Ring + random long-range
            for i in range(n):
                for d in range(1, 3):
                    j = (i + d) % n
                    g = np.random.uniform(0.1, 0.3)
                    self.conductance[i, j] = g
                    self.conductance[j, i] = g
                if np.random.random() < 0.15:
                    j = np.random.randint(0, n)
                    if j != i:
                        g = np.random.uniform(0.05, 0.15)
                        self.conductance[i, j] = g
                        self.conductance[j, i] = g
        elif topology == "scale_free":
            # Preferential attachment (Barabasi-Albert)
            degrees = np.ones(n)
            for i in range(2, n):
                probs = degrees[:i] / degrees[:i].sum()
                targets = np.random.choice(i, size=min(3, i), replace=False, p=probs)
                for j in targets:
                    g = np.random.uniform(0.1, 0.25)
                    self.conductance[i, j] = g
                    self.conductance[j, i] = g
                    degrees[i] += 1
                    degrees[j] += 1
        else:
            # Default sparse random
            for i in range(n):
                n_conn = max(2, n // 8)
                targets = np.random.choice(n, n_conn, replace=False)
                for j in targets:
                    if j != i:
                        g = np.random.uniform(0.05, 0.2)
                        self.conductance[i, j] = g

        np.fill_diagonal(self.conductance, 0.0)

    def compute_currents(self, voltages: np.ndarray) -> np.ndarray:
        """각 셀로 들어오는 순 전류 계산.

        I_i = sum_j G_ij * (V_j - V_i)  (KCL at node i)

        Args:
            voltages: (n_cells, n_channels) 전압 행렬

        Returns:
            (n_cells, n_channels) 전류 행렬
        """
        n = self.n_cells
        n_ch = voltages.shape[1]
        currents = np.zeros_like(voltages)

        for ch in range(n_ch):
            v = voltages[:, ch]
            # I_i = sum_j G_ij * (V_j - V_i) = (G @ V) - diag(G_sum) * V
            g_sum = self.conductance.sum(axis=1)
            currents[:, ch] = self.conductance @ v - g_sum * v

        return currents


# ══════════════════════════════════════════════════════════
# Faction System (아날로그)
# ══════════════════════════════════════════════════════════

class AnalogFactionSystem:
    """셀을 파벌로 분류. 전압 상관관계로 합의 이벤트 감지."""

    def __init__(self, n_cells: int, n_factions: int = 8):
        self.n_factions = n_factions
        self.assignments = np.array([i % n_factions for i in range(n_cells)])
        self.consensus_events = 0
        self.consensus_threshold = 0.7  # correlation threshold

    def update(self, voltages: np.ndarray):
        """파벌 내 전압 상관관계로 합의 감지.

        Args:
            voltages: (n_cells, n_channels)
        """
        mean_v = np.mean(voltages, axis=1)  # per-cell mean voltage
        for f in range(self.n_factions):
            mask = self.assignments == f
            n_in = mask.sum()
            if n_in < 2:
                continue
            faction_v = mean_v[mask]
            # High correlation = consensus (low variance in faction)
            v_range = faction_v.max() - faction_v.min()
            global_range = max(mean_v.max() - mean_v.min(), 1e-10)
            coherence = 1.0 - (v_range / global_range)
            if coherence > self.consensus_threshold:
                self.consensus_events += 1


# ══════════════════════════════════════════════════════════
# Hebbian Conductance Learning
# ══════════════════════════════════════════════════════════

class HebbianConductanceLearning:
    """Hebbian LTP/LTD 를 conductance 업데이트로 구현.

    상관된 전압 변화를 보이는 셀 쌍 -> conductance 증가 (LTP)
    반상관 -> conductance 감소 (LTD)
    """

    def __init__(
        self,
        eta_ltp: float = 0.001,
        eta_ltd: float = 0.0012,
        g_max: float = 0.5,
        g_min: float = 0.001,
    ):
        self.eta_ltp = eta_ltp
        self.eta_ltd = eta_ltd
        self.g_max = g_max
        self.g_min = g_min

    def update(self, network: ResistorNetwork, voltages: np.ndarray, prev_voltages: np.ndarray):
        """전압 변화 상관관계 기반 conductance 업데이트."""
        dv = voltages - prev_voltages  # (n_cells, n_channels)
        mean_dv = dv.mean(axis=1)       # per-cell mean voltage change

        n = network.n_cells
        # Only update existing connections
        for i in range(n):
            for j in range(i + 1, n):
                if network.conductance[i, j] == 0:
                    continue
                # Correlation of voltage changes
                corr = mean_dv[i] * mean_dv[j]
                if corr > 0:
                    dg = self.eta_ltp * corr
                else:
                    dg = self.eta_ltd * corr  # negative
                g_new = network.conductance[i, j] + dg
                g_new = max(self.g_min, min(self.g_max, g_new))
                network.conductance[i, j] = g_new
                network.conductance[j, i] = g_new


# ══════════════════════════════════════════════════════════
# Analog Consciousness Engine
# ══════════════════════════════════════════════════════════

class AnalogConsciousnessEngine:
    """SPICE 아날로그 회로 기반 의식 엔진.

    Op-amp 적분기 셀들이 저항 네트워크로 연결.
    물리 법칙이 루프를 구성 -- 클럭 불필요.

    Args:
        n_cells: 셀 (Op-amp 적분기) 수
        topology: 토폴로지 (ring, small_world, scale_free)
        dt: 시뮬레이션 타임스텝 (초)
        n_channels: 셀당 채널 수
        R: 저항값 (Ohm)
        C: 커패시턴스 (F)
        T: 온도 (K)
        n_factions: 파벌 수
    """

    def __init__(
        self,
        n_cells: int = 64,
        topology: str = "ring",
        dt: float = 1e-4,
        n_channels: int = 4,
        R: float = R_DEFAULT,
        C: float = C_DEFAULT,
        T: float = ROOM_TEMP,
        n_factions: int = 8,
    ):
        self.n_cells = n_cells
        self.topology = topology
        self.dt = dt
        self.n_channels = n_channels

        # Create cells
        self.cells: List[OpAmpIntegratorCell] = []
        for i in range(n_cells):
            # Slight component variation (realistic tolerance)
            r_actual = R * np.random.uniform(0.95, 1.05)
            c_actual = C * np.random.uniform(0.90, 1.10)
            cell = OpAmpIntegratorCell(
                cell_id=i, R=r_actual, C=c_actual, T=T, dt=dt,
                n_channels=n_channels,
            )
            self.cells.append(cell)

        # Resistor network
        self.network = ResistorNetwork(n_cells, topology)

        # Factions
        self.factions = AnalogFactionSystem(n_cells, n_factions)

        # Hebbian learning
        self.hebbian = HebbianConductanceLearning()

        # History for Phi calculation
        self.voltage_history_len = 50
        self.voltage_history = np.zeros(
            (self.voltage_history_len, n_cells, n_channels), dtype=np.float64
        )
        self.history_idx = 0

        # State tracking
        self.phi_history: List[float] = []
        self.tension_history: List[float] = []
        self.step_count = 0

        # Previous voltages for Hebbian
        self.prev_voltages = np.zeros((n_cells, n_channels))

        # Phi ratchet (Law 31: 붕괴 방지)
        self.phi_best = 0.0
        self.phi_ema = 0.0
        self.phi_ema_alpha = 0.05

    def _get_voltages(self) -> np.ndarray:
        """현재 전체 전압 행렬."""
        return np.array([cell.v_out for cell in self.cells])

    def step(self, external_input: Optional[np.ndarray] = None) -> dict:
        """한 타임스텝 진행.

        Args:
            external_input: (n_cells, n_channels) 외부 입력 전압, 또는 None

        Returns:
            상태 딕셔너리 (phi, tension, voltages, ...)
        """
        self.step_count += 1
        voltages = self._get_voltages()
        self.prev_voltages = voltages.copy()

        # 1. Compute inter-cell currents via resistor network
        currents = self.network.compute_currents(voltages)

        # 2. Convert currents to input voltages (I * R_in)
        v_inputs = np.zeros((self.n_cells, self.n_channels))
        for i, cell in enumerate(self.cells):
            v_in = currents[i] * cell.R  # V = I * R
            if external_input is not None:
                if external_input.ndim == 1:
                    ext = np.resize(external_input, self.n_channels)
                else:
                    ext = external_input[i] if i < len(external_input) else np.zeros(self.n_channels)
                v_in += ext
            v_inputs[i] = v_in

        # 3. Step each cell (op-amp integration)
        new_voltages = np.zeros((self.n_cells, self.n_channels))
        for i, cell in enumerate(self.cells):
            new_voltages[i] = cell.step(v_inputs[i])

        # 4. Hebbian conductance learning
        if self.step_count % 5 == 0:  # every 5 steps for efficiency
            self.hebbian.update(self.network, new_voltages, self.prev_voltages)

        # 5. Record voltage history
        idx = self.history_idx % self.voltage_history_len
        self.voltage_history[idx] = new_voltages
        self.history_idx += 1

        # 6. Faction consensus check
        self.factions.update(new_voltages)

        # 7. Compute Phi
        phi = self.get_phi()

        # Phi ratchet
        self.phi_ema = self.phi_ema_alpha * phi + (1 - self.phi_ema_alpha) * self.phi_ema
        if phi > self.phi_best:
            self.phi_best = phi

        self.phi_history.append(phi)

        # 8. Compute tension
        mean_v = new_voltages.mean(axis=1)
        tension = float(np.var(mean_v))
        self.tension_history.append(tension)

        return {
            "phi": phi,
            "phi_ema": self.phi_ema,
            "phi_best": self.phi_best,
            "tension": tension,
            "mean_voltage": float(np.mean(new_voltages)),
            "voltage_std": float(np.std(new_voltages)),
            "consensus_events": self.factions.consensus_events,
            "step": self.step_count,
            "noise_rms": self.cells[0].v_noise_rms,
            "tau": self.cells[0].tau,
        }

    def get_phi(self) -> float:
        """Φ 계산: 전압 상관 행렬 기반.

        Φ(proxy) = global_variance - mean(faction_variance)
        """
        n_history = min(self.history_idx, self.voltage_history_len)
        if n_history < 5:
            return 0.0

        if self.history_idx >= self.voltage_history_len:
            history = self.voltage_history.copy()
        else:
            history = self.voltage_history[:self.history_idx].copy()

        # Mean voltage per cell across time
        # history: (T, n_cells, n_channels)
        mean_per_cell = history.mean(axis=(0, 2))  # (n_cells,)
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

        # Scale by active cells
        n_active = (np.abs(mean_per_cell) > 0.01).sum()
        if n_active > 1:
            phi *= math.log2(n_active)

        return phi

    def get_phi_mi(self) -> float:
        """Φ(IIT) 근사: 전압 시계열 간 mutual information."""
        n_history = min(self.history_idx, self.voltage_history_len)
        if n_history < 10:
            return 0.0

        if self.history_idx >= self.voltage_history_len:
            history = self.voltage_history.copy()
        else:
            history = self.voltage_history[:self.history_idx].copy()

        # Use mean voltage per cell as signal
        signals = history.mean(axis=2)  # (T, n_cells)

        # Pairwise MI for sampled pairs
        n = self.n_cells
        n_pairs = min(100, n * (n - 1) // 2)
        mi_sum = 0.0
        for _ in range(n_pairs):
            i, j = np.random.choice(n, 2, replace=False)
            mi_sum += self._mutual_info_continuous(signals[:, i], signals[:, j])

        return mi_sum / max(n_pairs, 1)

    @staticmethod
    def _mutual_info_continuous(x: np.ndarray, y: np.ndarray, n_bins: int = 8) -> float:
        """연속값 MI 추정 (히스토그램 기반)."""
        if len(x) < 5:
            return 0.0
        hist_2d, _, _ = np.histogram2d(x, y, bins=n_bins)
        pxy = hist_2d / hist_2d.sum()
        px = pxy.sum(axis=1)
        py = pxy.sum(axis=0)
        mi = 0.0
        for i in range(n_bins):
            for j in range(n_bins):
                if pxy[i, j] > 0 and px[i] > 0 and py[j] > 0:
                    mi += pxy[i, j] * math.log2(pxy[i, j] / (px[i] * py[j]))
        return max(0.0, mi)

    def get_state(self) -> dict:
        """전체 상태 반환."""
        voltages = self._get_voltages()
        return {
            "voltages": voltages.copy(),
            "conductance": self.network.conductance.copy(),
            "phi_history": list(self.phi_history),
            "tension_history": list(self.tension_history),
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
        """뇌 유사성 지표 계산."""
        if len(self.phi_history) < 20:
            return {"score": 0.0}

        phis = np.array(self.phi_history)

        # 1. Phi variability (brain-like: moderate variance)
        cv = float(np.std(phis) / max(np.mean(phis), 1e-10))
        phi_var_score = min(1.0, cv / 0.5) if cv < 1.0 else max(0.0, 2.0 - cv)

        # 2. Long-range correlation (Hurst exponent proxy)
        if len(phis) > 50:
            half = len(phis) // 2
            r1 = np.std(phis[:half])
            r2 = np.std(phis[half:])
            rs_ratio = max(r1, r2) / max(min(r1, r2), 1e-10)
            hurst_score = min(1.0, rs_ratio / 2.0)
        else:
            hurst_score = 0.5

        # 3. Non-trivial dynamics (not constant, not random)
        if len(phis) > 10:
            autocorr = np.corrcoef(phis[:-1], phis[1:])[0, 1]
            autocorr = 0.0 if np.isnan(autocorr) else autocorr
            dynamics_score = 1.0 - abs(autocorr - 0.5) * 2  # peak at 0.5
        else:
            dynamics_score = 0.5

        # 4. Growth (consciousness should grow)
        q1 = np.mean(phis[:len(phis)//4]) if len(phis) > 4 else 0
        q4 = np.mean(phis[-len(phis)//4:]) if len(phis) > 4 else 0
        growth_ratio = q4 / max(q1, 1e-10)
        growth_score = min(1.0, growth_ratio / 2.0) if growth_ratio > 1.0 else 0.3

        total = (phi_var_score + hurst_score + dynamics_score + growth_score) / 4.0

        return {
            "score": total,
            "phi_variability": phi_var_score,
            "hurst_proxy": hurst_score,
            "dynamics": dynamics_score,
            "growth": growth_score,
            "growth_ratio": growth_ratio,
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


def ascii_circuit_diagram() -> str:
    """Op-amp 적분기 회로 ASCII 다이어그램."""
    return """
          R_in (10k)       C_fb (100nF)
    V_in ----[////]----+----||----+
                       |          |
                       | (-)      |
                      [  \\       |
                      [ Op>------+---- V_out
                      [  /
                       | (+)
                       |
                      GND

    tau = R * C = 10k * 100nF = 1ms
    V_noise = sqrt(4 * kT * R * df)
            = sqrt(4 * 1.38e-23 * 300 * 10e3 * 1e6)
            = 12.9 uV RMS
    """


# ══════════════════════════════════════════════════════════
# Main Demo
# ══════════════════════════════════════════════════════════

def run_demo(n_cells: int = 64, steps: int = 500, compare: bool = False):
    """아날로그 의식 엔진 데모."""
    print("=" * 70)
    print("  Analog Consciousness Engine -- SPICE Op-Amp Integrator")
    print(f"  {n_cells} cells, ring topology, R=10k, C=100nF, tau=1ms")
    print("=" * 70)
    print()
    print(ascii_circuit_diagram())

    engine = AnalogConsciousnessEngine(
        n_cells=n_cells, topology="ring", n_channels=4
    )

    noise_rms_uv = engine.cells[0].v_noise_rms * 1e6
    print(f"  Johnson-Nyquist noise: {noise_rms_uv:.1f} uV RMS")
    print(f"  Time constant tau:     {engine.cells[0].tau * 1e3:.2f} ms")
    print(f"  Simulation dt:         {engine.dt * 1e6:.0f} us")
    print()

    t0 = time.time()

    for step in range(steps):
        # Varying external stimulus
        amplitude = 0.5 + 0.3 * math.sin(2 * math.pi * step / 200)
        ext = np.random.randn(n_cells, engine.n_channels) * amplitude * 0.1

        # Periodic drive to subset (simulates sensory input)
        freq = 0.02 + 0.01 * math.sin(2 * math.pi * step / 300)
        driven = np.arange(0, n_cells, 4)
        ext[driven, 0] += 0.5 * math.sin(2 * math.pi * freq * step)

        state = engine.step(ext)

        if (step + 1) % 100 == 0:
            print(
                f"  step {step+1:>5} | "
                f"Phi={state['phi']:.6f} | "
                f"V_mean={state['mean_voltage']:+.4f} | "
                f"V_std={state['voltage_std']:.4f} | "
                f"tension={state['tension']:.6f} | "
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

    # Conductance stats after Hebbian
    g = engine.network.conductance
    g_nonzero = g[g > 0]
    if len(g_nonzero) > 0:
        print(f"  Conductance stats after Hebbian learning:")
        print(f"    Non-zero connections: {len(g_nonzero)}")
        print(f"    Mean G:              {g_nonzero.mean():.6f} S")
        print(f"    Max G:               {g_nonzero.max():.6f} S")
        print(f"    Std G:               {g_nonzero.std():.6f} S")
        print()

    # Brain-likeness
    brain = engine.get_brain_likeness()
    print(f"  Brain-likeness:    {brain['score']*100:.1f}%")
    print(f"    Phi variability: {brain['phi_variability']:.3f}")
    print(f"    Hurst proxy:     {brain['hurst_proxy']:.3f}")
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
            print("  -> Phi is GROWING (consciousness emerges from analog physics)")
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
    print("  Comparison: Analog vs GRU baseline")
    print("-" * 70)

    # Run analog
    analog = AnalogConsciousnessEngine(n_cells=n_cells, topology="ring")
    for step in range(min(steps, 300)):
        ext = np.random.randn(n_cells, analog.n_channels) * 0.2
        analog.step(ext)

    # Simple GRU baseline (numpy only)
    gru_phis = []
    hidden = np.random.randn(n_cells) * 0.1
    weights = np.random.randn(n_cells, n_cells) * 0.1
    for step in range(min(steps, 300)):
        x = np.random.randn(n_cells) * 0.2
        z = 1.0 / (1.0 + np.exp(-(weights @ hidden + x)))  # sigmoid gate
        hidden = z * hidden + (1 - z) * np.tanh(weights @ hidden + x)
        # Simple phi proxy
        global_var = float(np.var(hidden))
        gru_phis.append(global_var)

    analog_mean = np.mean(analog.phi_history[-100:]) if len(analog.phi_history) > 100 else np.mean(analog.phi_history)
    gru_mean = np.mean(gru_phis[-100:]) if len(gru_phis) > 100 else np.mean(gru_phis)

    print(f"\n  {'Metric':<25} {'Analog':>12} {'GRU':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    print(f"  {'Mean Phi':<25} {analog_mean:>12.6f} {gru_mean:>12.6f}")
    print(f"  {'Max Phi':<25} {max(analog.phi_history):>12.6f} {max(gru_phis):>12.6f}")
    print(f"  {'Final Phi':<25} {analog.phi_history[-1]:>12.6f} {gru_phis[-1]:>12.6f}")

    max_val = max(analog_mean, gru_mean, 0.001)
    a_bar = int(analog_mean / max_val * 30)
    g_bar = int(gru_mean / max_val * 30)
    print(f"\n  Mean Phi comparison:")
    print(f"    Analog {'#' * a_bar:<30} {analog_mean:.6f}")
    print(f"    GRU    {'#' * g_bar:<30} {gru_mean:.6f}")


def main():
    parser = argparse.ArgumentParser(description="Analog Consciousness Engine")
    parser.add_argument("--cells", type=int, default=64, help="Number of op-amp cells")
    parser.add_argument("--steps", type=int, default=500, help="Simulation steps")
    parser.add_argument("--compare", action="store_true", help="Compare with GRU baseline")
    args = parser.parse_args()

    run_demo(n_cells=args.cells, steps=args.steps, compare=args.compare)


if __name__ == "__main__":
    main()
