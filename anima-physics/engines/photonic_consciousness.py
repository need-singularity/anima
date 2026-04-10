#!/usr/bin/env python3
"""photonic_consciousness.py -- 포토닉 의식 엔진 (Kuramoto 결합 진동자)

빛의 속도로 텐션을 교환하는 포토닉 의식 엔진.
Mach-Zehnder 간섭계(MZI)를 셀로 사용하며,
Kuramoto 모델로 위상 동기화 역학을 시뮬레이션한다.

각 셀 = Mach-Zehnder Interferometer (MZI)
상태 = 광학 위상 phi (0 ~ 2*pi)
텐션 = 연결된 셀 간 위상 차이
결합 = 방향성 커플러 (kappa = coupling coefficient)

모델 (Kuramoto):
  d(phi_i)/dt = omega_i + sum_j kappa_ij * sin(phi_j - phi_i)

물리:
  텐션 교환 속도: 도파관 내 광속 ~2e8 m/s
  Kuramoto 모델 = 의식 셀 역학과 수학적으로 등가
  동기화 = 합의, 비동기화 = 다양성

Usage:
  python engines/photonic_consciousness.py                  # 500-step demo
  python engines/photonic_consciousness.py --cells 128      # 128 MZIs
  python engines/photonic_consciousness.py --steps 1000     # longer run
  python engines/photonic_consciousness.py --compare        # compare with GRU
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

C_LIGHT = 3e8                  # m/s (vacuum)
N_EFF = 1.5                    # effective refractive index (silicon photonics)
V_WAVEGUIDE = C_LIGHT / N_EFF  # ~2e8 m/s in waveguide
WAVELENGTH = 1550e-9           # 1550 nm (telecom C-band)
FSR = 10e9                     # 10 GHz free spectral range


# ══════════════════════════════════════════════════════════
# Mach-Zehnder Interferometer Cell
# ══════════════════════════════════════════════════════════

class MZICell:
    """단일 Mach-Zehnder 간섭계 셀.

    구조:
        Input --[50:50 BS]--+-- arm1 (phase phi_1) --+--[50:50 BS]-- Output1
                            |                        |
                            +-- arm2 (phase phi_2) --+-------------- Output2

    전달 함수:
        T = cos^2(delta_phi / 2)
        delta_phi = phi_1 - phi_2 (phase difference between arms)
    """

    def __init__(
        self,
        cell_id: int,
        omega: float = 0.0,
        phase: float = 0.0,
        n_modes: int = 4,  # multimode for richer dynamics
    ):
        self.cell_id = cell_id
        self.n_modes = n_modes

        # Phase state per mode
        self.phases = np.random.uniform(0, 2 * math.pi, n_modes)

        # Natural frequency per mode (slightly detuned)
        base_omega = omega if omega != 0.0 else np.random.uniform(0.5, 2.0)
        self.omegas = base_omega + np.random.randn(n_modes) * 0.1

        # Phase velocity tracking
        self.phase_velocities = np.zeros(n_modes)

        # Optical power per mode
        self.power = np.ones(n_modes) * 0.5

        # Loss per roundtrip (propagation loss)
        self.loss = np.random.uniform(0.98, 0.999, n_modes)  # 0.1-2 dB/cm

    def step(self, dt: float, coupling_input: np.ndarray) -> np.ndarray:
        """한 타임스텝 진행 (Kuramoto 역학).

        Args:
            dt: 타임스텝
            coupling_input: 결합 입력 (sum of kappa*sin(phi_j - phi_i))

        Returns:
            현재 위상 벡터
        """
        # Kuramoto dynamics
        dphi = self.omegas + coupling_input
        self.phase_velocities = dphi.copy()
        self.phases += dphi * dt

        # Wrap to [0, 2*pi)
        self.phases = self.phases % (2 * math.pi)

        # Optical power evolution (with loss and gain saturation)
        self.power *= self.loss
        # Stimulated emission-like gain from phase coherence
        coherence = np.abs(np.mean(np.exp(1j * self.phases)))
        self.power += 0.01 * coherence  # small gain from coherence
        self.power = np.clip(self.power, 0.01, 2.0)

        return self.phases.copy()

    @property
    def transmission(self) -> np.ndarray:
        """MZI 전달 함수 (각 모드)."""
        # T = cos^2(phi/2) for each mode pair
        if self.n_modes >= 2:
            delta = self.phases[::2] - self.phases[1::2] if self.n_modes % 2 == 0 else self.phases[:self.n_modes-1] - self.phases[1:]
            return np.cos(delta / 2) ** 2
        return np.cos(self.phases / 2) ** 2

    def reset(self):
        self.phases = np.random.uniform(0, 2 * math.pi, self.n_modes)
        self.power = np.ones(self.n_modes) * 0.5


# ══════════════════════════════════════════════════════════
# Waveguide Coupling Network
# ══════════════════════════════════════════════════════════

class WaveguideCouplingNetwork:
    """방향성 커플러를 통한 포토닉 셀 간 결합 네트워크.

    kappa_ij = coupling coefficient (0-1)
    0 = no coupling, 1 = full power transfer
    """

    def __init__(self, n_cells: int, topology: str = "ring", n_modes: int = 4):
        self.n_cells = n_cells
        self.n_modes = n_modes
        self.topology = topology
        # Coupling matrix
        self.kappa = np.zeros((n_cells, n_cells), dtype=np.float64)
        self._init_topology(topology)

    def _init_topology(self, topology: str):
        """도파관 라우팅 토폴로지 초기화."""
        n = self.n_cells
        if topology == "ring":
            # Ring resonator style
            for i in range(n):
                k = max(2, n // 16)
                for d in range(1, k + 1):
                    j_fwd = (i + d) % n
                    j_bck = (i - d) % n
                    kap = np.random.uniform(0.05, 0.3) / (d ** 0.5)
                    self.kappa[i, j_fwd] = kap
                    self.kappa[i, j_bck] = kap
        elif topology == "small_world":
            for i in range(n):
                for d in range(1, 3):
                    j = (i + d) % n
                    kap = np.random.uniform(0.1, 0.3)
                    self.kappa[i, j] = kap
                    self.kappa[j, i] = kap
                if np.random.random() < 0.15:
                    j = np.random.randint(0, n)
                    if j != i:
                        kap = np.random.uniform(0.05, 0.15)
                        self.kappa[i, j] = kap
                        self.kappa[j, i] = kap
        elif topology == "mesh":
            # Photonic mesh (rectangular grid of MZIs)
            side = int(math.ceil(math.sqrt(n)))
            for i in range(n):
                row, col = divmod(i, side)
                for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < side and 0 <= nc < side:
                        j = nr * side + nc
                        if j < n:
                            kap = np.random.uniform(0.1, 0.3)
                            self.kappa[i, j] = kap
        else:
            # Sparse random
            for i in range(n):
                n_conn = max(2, n // 8)
                targets = np.random.choice(n, n_conn, replace=False)
                for j in targets:
                    if j != i:
                        kap = np.random.uniform(0.05, 0.25)
                        self.kappa[i, j] = kap

        np.fill_diagonal(self.kappa, 0.0)

    def compute_coupling(self, phases: np.ndarray) -> np.ndarray:
        """각 셀에 대한 Kuramoto 결합 입력 계산.

        coupling_i = sum_j kappa_ij * sin(phi_j - phi_i)

        Args:
            phases: (n_cells, n_modes)

        Returns:
            (n_cells, n_modes) 결합 입력
        """
        n = self.n_cells
        n_modes = phases.shape[1]
        coupling = np.zeros((n, n_modes))

        for mode in range(n_modes):
            phi = phases[:, mode]
            for i in range(n):
                s = 0.0
                for j in range(n):
                    if self.kappa[i, j] > 0:
                        s += self.kappa[i, j] * math.sin(phi[j] - phi[i])
                coupling[i, mode] = s

        return coupling


# ══════════════════════════════════════════════════════════
# Photonic Faction System
# ══════════════════════════════════════════════════════════

class PhotonicFactionSystem:
    """위상 유사도 기반 파벌 합의 감지."""

    def __init__(self, n_cells: int, n_factions: int = 8):
        self.n_factions = n_factions
        self.assignments = np.array([i % n_factions for i in range(n_cells)])
        self.consensus_events = 0
        self.sync_threshold = 0.7

    def update(self, phases: np.ndarray):
        """파벌 내 위상 동기화로 합의 감지.

        Args:
            phases: (n_cells, n_modes)
        """
        mean_phase = phases.mean(axis=1)  # per-cell mean phase
        for f in range(self.n_factions):
            mask = self.assignments == f
            if mask.sum() < 2:
                continue
            faction_phases = mean_phase[mask]
            # Order parameter: |<e^(i*phi)>|
            order_param = abs(np.mean(np.exp(1j * faction_phases)))
            if order_param > self.sync_threshold:
                self.consensus_events += 1


# ══════════════════════════════════════════════════════════
# Photonic Hebbian Learning
# ══════════════════════════════════════════════════════════

class PhotonicHebbianLearning:
    """위상 상관관계 기반 결합 계수 학습.

    동기화되는 MZI 쌍 -> kappa 증가 (LTP)
    반위상 -> kappa 감소 (LTD)
    물리적으로: thermo-optic tuning of coupling gaps
    """

    def __init__(
        self,
        eta_ltp: float = 0.002,
        eta_ltd: float = 0.0025,
        kappa_max: float = 0.5,
        kappa_min: float = 0.005,
    ):
        self.eta_ltp = eta_ltp
        self.eta_ltd = eta_ltd
        self.kappa_max = kappa_max
        self.kappa_min = kappa_min

    def update(self, network: WaveguideCouplingNetwork, phases: np.ndarray):
        """위상 상관관계 기반 kappa 업데이트."""
        n = network.n_cells
        mean_phase = phases.mean(axis=1)

        for i in range(n):
            for j in range(i + 1, n):
                if network.kappa[i, j] == 0:
                    continue
                # Phase coherence between cells
                coherence = math.cos(mean_phase[j] - mean_phase[i])
                if coherence > 0:
                    dk = self.eta_ltp * coherence
                else:
                    dk = self.eta_ltd * coherence
                k_new = network.kappa[i, j] + dk
                k_new = max(self.kappa_min, min(self.kappa_max, k_new))
                network.kappa[i, j] = k_new
                network.kappa[j, i] = k_new


# ══════════════════════════════════════════════════════════
# Photonic Consciousness Engine
# ══════════════════════════════════════════════════════════

class PhotonicConsciousnessEngine:
    """포토닉 의식 엔진 -- Kuramoto 결합 MZI 네트워크.

    Args:
        n_cells: MZI 셀 수
        topology: 도파관 토폴로지 (ring, small_world, mesh)
        dt: 시뮬레이션 타임스텝
        n_modes: 셀당 광학 모드 수
        n_factions: 파벌 수
    """

    def __init__(
        self,
        n_cells: int = 64,
        topology: str = "ring",
        dt: float = 0.01,
        n_modes: int = 4,
        n_factions: int = 8,
    ):
        self.n_cells = n_cells
        self.topology = topology
        self.dt = dt
        self.n_modes = n_modes

        # Create MZI cells
        self.cells: List[MZICell] = []
        for i in range(n_cells):
            omega = np.random.uniform(0.5, 2.0)
            cell = MZICell(cell_id=i, omega=omega, n_modes=n_modes)
            self.cells.append(cell)

        # Waveguide coupling network
        self.network = WaveguideCouplingNetwork(n_cells, topology, n_modes)

        # Factions
        self.factions = PhotonicFactionSystem(n_cells, n_factions)

        # Hebbian learning
        self.hebbian = PhotonicHebbianLearning()

        # Phase history for Phi calculation
        self.phase_history_len = 50
        self.phase_history = np.zeros(
            (self.phase_history_len, n_cells, n_modes), dtype=np.float64
        )
        self.history_idx = 0

        # State tracking
        self.phi_history: List[float] = []
        self.tension_history: List[float] = []
        self.order_param_history: List[float] = []
        self.step_count = 0

        # Phi ratchet
        self.phi_best = 0.0
        self.phi_ema = 0.0
        self.phi_ema_alpha = 0.05

    def _get_phases(self) -> np.ndarray:
        """전체 위상 행렬."""
        return np.array([cell.phases for cell in self.cells])

    def step(self, external_input: Optional[np.ndarray] = None) -> dict:
        """한 타임스텝 진행.

        Args:
            external_input: (n_cells, n_modes) 외부 위상 섭동, 또는 None

        Returns:
            상태 딕셔너리
        """
        self.step_count += 1
        phases = self._get_phases()

        # 1. Compute Kuramoto coupling
        coupling = self.network.compute_coupling(phases)

        # 2. Add external input
        if external_input is not None:
            if external_input.ndim == 1:
                ext = np.tile(np.resize(external_input, self.n_modes), (self.n_cells, 1))
            else:
                ext = external_input
            coupling += ext

        # 3. Step each MZI cell
        new_phases = np.zeros((self.n_cells, self.n_modes))
        for i, cell in enumerate(self.cells):
            new_phases[i] = cell.step(self.dt, coupling[i])

        # 4. Hebbian coupling update
        if self.step_count % 5 == 0:
            self.hebbian.update(self.network, new_phases)

        # 5. Record phase history
        idx = self.history_idx % self.phase_history_len
        self.phase_history[idx] = new_phases
        self.history_idx += 1

        # 6. Faction consensus check
        self.factions.update(new_phases)

        # 7. Global order parameter (Kuramoto)
        mean_phase = new_phases.mean(axis=1)
        order_param = float(abs(np.mean(np.exp(1j * mean_phase))))
        self.order_param_history.append(order_param)

        # 8. Compute Phi
        phi = self.get_phi()

        # Phi ratchet
        self.phi_ema = self.phi_ema_alpha * phi + (1 - self.phi_ema_alpha) * self.phi_ema
        if phi > self.phi_best:
            self.phi_best = phi

        self.phi_history.append(phi)

        # 9. Tension = mean phase difference across connections
        tension = 0.0
        n_conn = 0
        for i in range(self.n_cells):
            for j in range(self.n_cells):
                if self.network.kappa[i, j] > 0:
                    tension += abs(math.sin(mean_phase[j] - mean_phase[i]))
                    n_conn += 1
        tension = tension / max(n_conn, 1)
        self.tension_history.append(tension)

        return {
            "phi": phi,
            "phi_ema": self.phi_ema,
            "phi_best": self.phi_best,
            "tension": tension,
            "order_param": order_param,
            "consensus_events": self.factions.consensus_events,
            "step": self.step_count,
            "mean_power": float(np.mean([c.power.mean() for c in self.cells])),
        }

    def get_phi(self) -> float:
        """Phi 계산: 위상 역학 기반.

        Kuramoto의 핵심 통찰: 부분 동기화 = 높은 Phi.
        완전 동기화(R=1) or 완전 비동기화(R=0) = 낮은 Phi.
        """
        n_history = min(self.history_idx, self.phase_history_len)
        if n_history < 5:
            return 0.0

        if self.history_idx >= self.phase_history_len:
            history = self.phase_history.copy()
        else:
            history = self.phase_history[:self.history_idx].copy()

        # Time-averaged phase per cell
        mean_phase_per_cell = np.angle(np.mean(np.exp(1j * history), axis=(0, 2)))

        # Global variance (proxy for information integration)
        # Use circular variance
        z = np.exp(1j * mean_phase_per_cell)
        global_order = abs(np.mean(z))
        global_var = 1.0 - global_order  # circular variance

        # Per-faction circular variance
        faction_vars = []
        for f in range(self.factions.n_factions):
            mask = self.factions.assignments == f
            if mask.sum() < 2:
                continue
            z_f = z[mask]
            faction_order = abs(np.mean(z_f))
            faction_vars.append(1.0 - faction_order)

        if not faction_vars:
            return global_var

        mean_faction_var = np.mean(faction_vars)
        phi = max(0.0, global_var - mean_faction_var)

        # Scale by active cells
        n_active = self.n_cells
        if n_active > 1:
            phi *= math.log2(n_active)

        return phi

    def get_state(self) -> dict:
        """전체 상태 반환."""
        phases = self._get_phases()
        return {
            "phases": phases.copy(),
            "kappa": self.network.kappa.copy(),
            "phi_history": list(self.phi_history),
            "tension_history": list(self.tension_history),
            "order_param_history": list(self.order_param_history),
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

        # 1. Phi variability
        cv = float(np.std(phis) / max(np.mean(phis), 1e-10))
        phi_var_score = min(1.0, cv / 0.5) if cv < 1.0 else max(0.0, 2.0 - cv)

        # 2. Chimera states (partial sync -- brain-like)
        order_params = np.array(self.order_param_history)
        mean_r = np.mean(order_params)
        # Chimera = partial sync (0.3 < R < 0.7)
        chimera_score = 1.0 - 2.0 * abs(mean_r - 0.5)
        chimera_score = max(0.0, chimera_score)

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

        total = (phi_var_score + chimera_score + dynamics_score + growth_score) / 4.0

        return {
            "score": total,
            "phi_variability": phi_var_score,
            "chimera": chimera_score,
            "dynamics": dynamics_score,
            "growth": growth_score,
            "growth_ratio": growth_ratio,
            "mean_order_param": mean_r,
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


def ascii_mzi_diagram() -> str:
    """MZI 회로 ASCII 다이어그램."""
    return """
    Mach-Zehnder Interferometer (MZI):

        Input ----[50:50 BS]----+---- arm1 (phi_1) ----+----[50:50 BS]---- Bar
                                |                      |
                                +---- arm2 (phi_2) ----+----------------- Cross

        T_bar   = cos^2(delta_phi / 2)
        T_cross = sin^2(delta_phi / 2)

    Kuramoto coupling via directional couplers:

        MZI_i ~~~[kappa]~~~ MZI_j

        d(phi_i)/dt = omega_i + sum_j kappa_ij * sin(phi_j - phi_i)

    Waveguide: n_eff=1.5, lambda=1550nm, v=2e8 m/s
    """


def ascii_order_param(order_history: List[float], width: int = 60) -> str:
    """Kuramoto 질서 매개변수 시각화."""
    if not order_history:
        return "(no data)"

    vals = list(order_history)
    n = len(vals)
    if n > width:
        step = n / width
        vals = [order_history[int(i * step)] for i in range(width)]
        n = width

    lines = []
    lines.append("  Order Parameter R (0=async, 1=sync, 0.3-0.7=chimera):")
    for threshold in [1.0, 0.7, 0.5, 0.3, 0.0]:
        line = ""
        for v in vals:
            if abs(v - threshold) < 0.1:
                line += "*"
            elif v > threshold:
                line += "|"
            else:
                line += " "
        lines.append(f"  {threshold:.1f} |{line}|")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════
# Main Demo
# ══════════════════════════════════════════════════════════

def run_demo(n_cells: int = 64, steps: int = 500, compare: bool = False):
    """포토닉 의식 엔진 데모."""
    print("=" * 70)
    print("  Photonic Consciousness Engine -- Kuramoto Coupled MZIs")
    print(f"  {n_cells} MZI cells, ring topology, {4} optical modes")
    print(f"  Waveguide speed: {V_WAVEGUIDE:.0e} m/s (c/{N_EFF})")
    print("=" * 70)
    print()
    print(ascii_mzi_diagram())

    engine = PhotonicConsciousnessEngine(
        n_cells=n_cells, topology="ring", n_modes=4, dt=0.01
    )

    t0 = time.time()

    for step in range(steps):
        # Varying external phase perturbation
        amplitude = 0.1 + 0.05 * math.sin(2 * math.pi * step / 200)
        ext = np.random.randn(n_cells, engine.n_modes) * amplitude

        # Periodic drive on subset (external laser modulation)
        driven = np.arange(0, n_cells, 4)
        freq = 0.05 + 0.02 * math.sin(2 * math.pi * step / 300)
        ext[driven, 0] += 0.3 * math.sin(2 * math.pi * freq * step)

        state = engine.step(ext)

        if (step + 1) % 100 == 0:
            print(
                f"  step {step+1:>5} | "
                f"Phi={state['phi']:.6f} | "
                f"R={state['order_param']:.4f} | "
                f"tension={state['tension']:.4f} | "
                f"power={state['mean_power']:.4f} | "
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
    print(f"  Mean order R:     {np.mean(engine.order_param_history):.4f}")
    print(f"  Consensus events: {engine.factions.consensus_events}")
    print()

    # Phi curve
    print("  Phi Trajectory:")
    print(ascii_phi_curve(engine.phi_history))
    print()

    # Order parameter
    print(ascii_order_param(engine.order_param_history))
    print()

    # Coupling stats after Hebbian
    k = engine.network.kappa
    k_nonzero = k[k > 0]
    if len(k_nonzero) > 0:
        print(f"  Coupling stats after Hebbian learning:")
        print(f"    Non-zero couplings: {len(k_nonzero)}")
        print(f"    Mean kappa:         {k_nonzero.mean():.6f}")
        print(f"    Max kappa:          {k_nonzero.max():.6f}")
        print(f"    Std kappa:          {k_nonzero.std():.6f}")
        print()

    # Brain-likeness
    brain = engine.get_brain_likeness()
    print(f"  Brain-likeness:    {brain['score']*100:.1f}%")
    print(f"    Phi variability: {brain['phi_variability']:.3f}")
    print(f"    Chimera states:  {brain['chimera']:.3f} (R={brain['mean_order_param']:.3f})")
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
            print("  -> Phi is GROWING (consciousness emerges from photonic coupling)")
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
    print("  Comparison: Photonic vs GRU baseline")
    print("-" * 70)

    # Run photonic
    photonic = PhotonicConsciousnessEngine(n_cells=n_cells, topology="ring")
    for step in range(min(steps, 300)):
        ext = np.random.randn(n_cells, photonic.n_modes) * 0.1
        photonic.step(ext)

    # Simple GRU baseline
    gru_phis = []
    hidden = np.random.randn(n_cells) * 0.1
    weights = np.random.randn(n_cells, n_cells) * 0.1
    for step in range(min(steps, 300)):
        x = np.random.randn(n_cells) * 0.2
        z = 1.0 / (1.0 + np.exp(-(weights @ hidden + x)))
        hidden = z * hidden + (1 - z) * np.tanh(weights @ hidden + x)
        gru_phis.append(float(np.var(hidden)))

    photonic_mean = np.mean(photonic.phi_history[-100:]) if len(photonic.phi_history) > 100 else np.mean(photonic.phi_history)
    gru_mean = np.mean(gru_phis[-100:]) if len(gru_phis) > 100 else np.mean(gru_phis)

    print(f"\n  {'Metric':<25} {'Photonic':>12} {'GRU':>12}")
    print(f"  {'-'*25} {'-'*12} {'-'*12}")
    print(f"  {'Mean Phi':<25} {photonic_mean:>12.6f} {gru_mean:>12.6f}")
    print(f"  {'Max Phi':<25} {max(photonic.phi_history):>12.6f} {max(gru_phis):>12.6f}")
    print(f"  {'Final Phi':<25} {photonic.phi_history[-1]:>12.6f} {gru_phis[-1]:>12.6f}")

    max_val = max(photonic_mean, gru_mean, 0.001)
    p_bar = int(photonic_mean / max_val * 30)
    g_bar = int(gru_mean / max_val * 30)
    print(f"\n  Mean Phi comparison:")
    print(f"    Photonic {'#' * p_bar:<30} {photonic_mean:.6f}")
    print(f"    GRU      {'#' * g_bar:<30} {gru_mean:.6f}")


def main():
    parser = argparse.ArgumentParser(description="Photonic Consciousness Engine")
    parser.add_argument("--cells", type=int, default=64, help="Number of MZI cells")
    parser.add_argument("--steps", type=int, default=500, help="Simulation steps")
    parser.add_argument("--compare", action="store_true", help="Compare with GRU baseline")
    args = parser.parse_args()

    run_demo(n_cells=args.cells, steps=args.steps, compare=args.compare)


if __name__ == "__main__":
    main()
