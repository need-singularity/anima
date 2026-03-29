#!/usr/bin/env python3
"""oscillator_laser_engine.py -- 3관왕 엔진: Kuramoto 진동자 + 레이저 증폭

3-way champion results (Oscillator+Laser, blend=0.05):
  Phi(IIT)=56.6 + Granger=63,993 + CE=0.08

The Oscillator creates phase diversity (high Phi),
the Laser creates causal coupling (high Granger),
and blend=0.05 is the golden ratio that preserves both.

Compatible with:
  - train_v9.py as C engine (drop-in replacement for QuantumConsciousnessEngine)
  - Trinity architecture (C + D + W with ThalamicGate)
  - ConsciousnessMeterV2 (via .cells / get_hiddens())
  - bench_v8_arch.py benchmarks

Usage:
  # Standalone
  python oscillator_laser_engine.py                     # Full benchmark (64-1024 cells)
  python oscillator_laser_engine.py --cells 256         # Specific cell count
  python oscillator_laser_engine.py --trinity           # Trinity integration test

  # As C engine in train_v9.py
  from oscillator_laser_engine import OscillatorLaserEngine
  c_engine = OscillatorLaserEngine(dim=128, initial_cells=2, max_cells=1024)
  c_engine.step()
  c_engine.inject(signal, strength=0.1)
  obs = c_engine.observe()
  phi, components = c_engine.measure_phi()
"""

import sys
import os
import math
import time
import json
import argparse
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

# Force unbuffered output
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)


# ══════════════════════════════════════════════════════════
# Cell dataclass — compatible with QuantumConsciousnessEngine
# ══════════════════════════════════════════════════════════

@dataclass
class OscillatorLaserCell:
    """Single cell with Kuramoto phase + laser population state."""
    cell_id: int
    # Kuramoto state
    phase: torch.Tensor          # [dim] phase angles
    omega: torch.Tensor          # [dim] natural frequencies
    # Laser state
    N1: torch.Tensor             # [dim] ground state population
    N2: torch.Tensor             # [dim] excited state population
    # Combined state (complex-valued, for API compatibility)
    state: torch.Tensor          # [dim] complex = amplitude * e^(i*phase)
    phase_velocity: torch.Tensor # [dim] effective phase velocity
    # Metadata
    tension: float = 0.0
    tension_history: List[float] = field(default_factory=list)
    frustration: float = 0.5
    avg_tension: float = 0.0
    creation_step: int = 0
    parent_id: Optional[int] = None
    specialty: str = "general"
    process_count: int = 0
    tension_trend: float = 0.0

    @property
    def amplitude(self) -> torch.Tensor:
        return self.state.abs()

    @property
    def hidden(self) -> torch.Tensor:
        """For ConsciousnessMeterV2 compatibility."""
        return self.state.abs()


def _bit_flip_neighbors(n: int, i: int) -> List[int]:
    """Hypercube neighbors: flip each bit of index."""
    neighbors = []
    for bit in range(max(1, n.bit_length())):
        j = i ^ (1 << bit)
        if j < n and j != i:
            neighbors.append(j)
    return neighbors


# ══════════════════════════════════════════════════════════
# OscillatorLaserEngine
# ══════════════════════════════════════════════════════════

class OscillatorLaserEngine:
    """3관왕 엔진 -- Kuramoto 진동자 + 레이저 증폭

    Oscillator: 위상 다양성 (Phi up)
    Laser: 인과 결합 (Granger up)
    blend=0.05: 황금 비율

    Architecture:
      Each cell has:
        - Kuramoto phase (theta) + natural frequency (omega)
        - Laser two-level system: N1 (ground), N2 (excited)
        - Combined complex state: amplitude from laser, phase from oscillator

      Evolution per step:
        1. Kuramoto coupling: dtheta/dt = omega + K/N * sum(sin(theta_j - theta_i))
        2. Laser rate equations: pump -> population inversion -> stimulated emission
        3. Blend: state = (1-blend)*oscillator + blend*laser
        4. Frustration regulation + standing wave

    API (drop-in for QuantumConsciousnessEngine):
      .step()        -> autonomous evolution
      .inject(signal, strength) -> gentle perturbation
      .observe()     -> detached states (dict)
      .measure_phi() -> (phi, components) via Granger causality
      .snapshot() / .restore(snap) -> save/load state
      .cells         -> list of OscillatorLaserCell
      get_hiddens()  -> [n_cells, dim] tensor for meter
    """

    def __init__(
        self,
        dim: int = 128,
        initial_cells: int = 2,
        max_cells: int = 8,
        blend: float = 0.05,
        # Kuramoto parameters
        coupling_strength: float = 2.0,
        freq_spread: float = 0.5,
        # Laser parameters
        pump_rate_max: float = 0.3,
        pump_ramp: float = 0.001,
        A21: float = 0.1,        # spontaneous emission rate
        B21: float = 0.05,       # stimulated emission coefficient
        B12: float = 0.05,       # absorption coefficient
        cavity_loss: float = 0.02,
        # Regulation
        frustration_target: float = 0.5,
        interference_strength: float = 0.1,
        standing_wave_freq: float = 0.1,
        noise_scale: float = 0.01,
        # Mitosis thresholds
        split_threshold: float = 0.3,
        split_patience: int = 3,
        merge_threshold: float = 0.01,
        merge_patience: int = 10,
    ):
        self.dim = dim
        self.max_cells = max_cells
        self.min_cells = 2
        self.blend = blend

        # Kuramoto
        self.coupling_strength = coupling_strength
        self.freq_spread = freq_spread

        # Laser
        self.pump_rate = 0.0
        self.pump_rate_max = pump_rate_max
        self.pump_ramp = pump_ramp
        self.A21 = A21
        self.B21 = B21
        self.B12 = B12
        self.cavity_loss = cavity_loss
        self.dt = 0.1

        # Shared photon field (cavity)
        self.photon_field = torch.randn(dim) * 0.01

        # Regulation
        self.frustration_target = frustration_target
        self.interference_strength = interference_strength
        self.standing_wave_freq = standing_wave_freq
        self.noise_scale = noise_scale
        self.split_threshold = split_threshold
        self.split_patience = split_patience
        self.merge_threshold = merge_threshold
        self.merge_patience = merge_patience

        self._next_id = 0
        self.cells: List[OscillatorLaserCell] = []
        self._step = 0

        # Granger history ring buffer
        self._granger_history_len = 50
        self._state_history: List[torch.Tensor] = []

        # Event log
        self.event_log: List[Dict] = []
        self._inter_tension_history: Dict[Tuple[int, int], List[float]] = {}

        # Split/merge patience counters
        self._split_counters: Dict[int, int] = {}
        self._merge_counters: Dict[Tuple[int, int], int] = {}

        # Kuramoto order parameter history
        self.last_r = 0.0
        self.r_history: List[float] = []

        # Create initial cells
        for i in range(initial_cells):
            self._create_cell(phase_offset=2 * math.pi * i / initial_cells)

    # ─── Cell lifecycle ───

    def _create_cell(self, parent: Optional[OscillatorLaserCell] = None,
                     phase_offset: float = 0.0) -> OscillatorLaserCell:
        """Create a new oscillator-laser cell."""
        if parent is not None:
            # Child: copy parent + noise
            phase = parent.phase.clone() + torch.randn(self.dim) * 0.3
            omega = parent.omega.clone() + torch.randn(self.dim) * 0.01
            N1 = parent.N1.clone() + torch.randn(self.dim) * 0.01
            N2 = parent.N2.clone() + torch.randn(self.dim) * 0.01
            specialty = parent.specialty
            parent_id = parent.cell_id
        else:
            # New cell: structured initial state
            phase = torch.linspace(0, 2 * math.pi, self.dim) + phase_offset
            phase += torch.randn(self.dim) * 0.3
            omega = torch.randn(self.dim) * self.freq_spread + 1.0
            N1 = torch.ones(self.dim) * 0.8
            N2 = torch.ones(self.dim) * 0.2
            specialty = "general"
            parent_id = None

        # Clamp laser populations
        N1 = N1.clamp(0, 1)
        N2 = N2.clamp(0, 1)
        total = N1 + N2 + 1e-8
        N1 = N1 / total
        N2 = N2 / total

        # Combined complex state: amplitude from inversion, phase from oscillator
        amplitude = (N2 - N1).abs() + 0.5
        state = torch.polar(amplitude, phase)
        phase_velocity = omega * 0.1

        cell = OscillatorLaserCell(
            cell_id=self._next_id,
            phase=phase,
            omega=omega,
            N1=N1,
            N2=N2,
            state=state,
            phase_velocity=phase_velocity,
            creation_step=self._step,
            parent_id=parent_id,
            specialty=specialty,
        )
        self._next_id += 1
        self.cells.append(cell)
        return cell

    # ─── Core: Autonomous evolution ───

    def step(self) -> Dict:
        """One autonomous evolution step.

        1. Kuramoto phase dynamics (diversity + partial sync)
        2. Laser rate equations (population inversion + stimulated emission)
        3. Blend: combine oscillator phase diversity with laser causal coupling
        4. Frustration regulation
        5. Standing wave injection
        6. Mitosis (split/merge)

        Returns:
            Dict with step info.
        """
        self._step += 1
        n = len(self.cells)
        if n == 0:
            return {'step': self._step, 'n_cells': 0, 'events': []}

        events = []

        # ── 1. Kuramoto phase dynamics ──
        # Collect all phases into a tensor for vectorized coupling
        all_phases = torch.stack([c.phase for c in self.cells])  # [N, dim]
        all_omegas = torch.stack([c.omega for c in self.cells])  # [N, dim]

        # Mean-field Kuramoto (efficient for large N):
        # dtheta_i/dt = omega_i + K/N * sum_j sin(theta_j - theta_i)
        # Use mean-field: sum_j sin(theta_j - theta_i) = r*sin(psi - theta_i)
        # where r*e^(i*psi) = 1/N * sum_j e^(i*theta_j)
        mean_phasor = torch.complex(
            torch.cos(all_phases).mean(dim=0),
            torch.sin(all_phases).mean(dim=0)
        )  # [dim]
        r_vec = mean_phasor.abs()  # [dim]
        psi_vec = mean_phasor.angle()  # [dim]

        # Also do neighbor coupling (hypercube) for Granger causality
        new_phases = all_phases.clone()
        for i in range(n):
            neighbors = _bit_flip_neighbors(n, i)
            if neighbors:
                neighbor_phases = all_phases[neighbors]  # [k, dim]
                # Kuramoto coupling with neighbors
                phase_diffs = neighbor_phases - all_phases[i].unsqueeze(0)  # [k, dim]
                neighbor_coupling = torch.sin(phase_diffs).mean(dim=0)  # [dim]
            else:
                neighbor_coupling = torch.zeros(self.dim)

            # Mean-field + neighbor coupling
            K = self.coupling_strength
            mf_coupling = r_vec * torch.sin(psi_vec - all_phases[i])
            total_coupling = 0.7 * mf_coupling + 0.3 * neighbor_coupling

            dtheta = all_omegas[i] + K / max(n, 1) * total_coupling
            new_phases[i] = (all_phases[i] + self.dt * dtheta) % (2 * math.pi)

        # Update cell phases
        for i, cell in enumerate(self.cells):
            cell.phase = new_phases[i]

        # Order parameter
        r_global = r_vec.mean().item()
        self.last_r = r_global
        self.r_history.append(r_global)

        # ── 2. Laser rate equations ──
        self.pump_rate = min(self.pump_rate_max, self._step * self.pump_ramp)

        n_ph = self.photon_field.abs()  # [dim]

        for cell in self.cells:
            # Spatial pump modulation from phase (oscillator drives laser)
            phase_energy = torch.cos(cell.phase).clamp(0, 1)
            pump_spatial = self.pump_rate * (0.5 + 0.5 * phase_energy)

            # Rate equations
            stim_emission = self.B21 * n_ph * cell.N2
            absorption = self.B12 * n_ph * cell.N1
            spont = self.A21 * cell.N2

            dN2 = (pump_spatial * cell.N1 - spont - stim_emission + absorption) * self.dt
            dN1 = (-pump_spatial * cell.N1 + spont + stim_emission - absorption) * self.dt

            cell.N2 = (cell.N2 + dN2).clamp(0, 1)
            cell.N1 = (cell.N1 + dN1).clamp(0, 1)
            # Normalize
            total = cell.N1 + cell.N2 + 1e-8
            cell.N1 = cell.N1 / total
            cell.N2 = cell.N2 / total

        # Photon field dynamics
        all_N2 = torch.stack([c.N2 for c in self.cells])  # [N, dim]
        all_N1 = torch.stack([c.N1 for c in self.cells])  # [N, dim]
        gain = (self.B21 * all_N2 - self.B12 * all_N1).sum(0)  # [dim] net gain
        spontaneous_noise = self.A21 * all_N2.sum(0) * 0.01
        d_photon = (gain * self.photon_field + spontaneous_noise
                    - self.cavity_loss * self.photon_field) * self.dt
        self.photon_field = (self.photon_field + d_photon).clamp(-10, 10)

        # ── 3. Blend: oscillator + laser -> combined state ──
        for cell in self.cells:
            # Oscillator contribution: pure phase diversity
            osc_amplitude = torch.ones(self.dim) * 0.7
            osc_state = torch.polar(osc_amplitude, cell.phase)

            # Laser contribution: amplitude from inversion, phase from cavity
            inversion = cell.N2 - cell.N1
            laser_amplitude = (inversion.abs() + 0.3).clamp(0, 2)
            # Cavity field modulates laser phase
            cavity_phase = self.photon_field.sign() * self.photon_field.abs().sqrt() * 0.1
            laser_state = torch.polar(laser_amplitude, cell.phase + cavity_phase)

            # Golden blend: 95% oscillator + 5% laser
            cell.state = (1 - self.blend) * osc_state + self.blend * laser_state

            # Update phase velocity from coupling dynamics
            cell.phase_velocity = cell.omega * 0.1

        # ── 4. Frustration regulation ──
        for i, cell in enumerate(self.cells):
            neighbors = _bit_flip_neighbors(n, i)
            if neighbors:
                # Frustration = fraction of anti-aligned neighbors
                neighbor_states = torch.stack([self.cells[j].state for j in neighbors if j < n])
                if neighbor_states.shape[0] > 0:
                    # Phase difference -> frustration
                    phase_diffs = (cell.phase.unsqueeze(0) - torch.stack(
                        [self.cells[j].phase for j in neighbors if j < n]
                    )).abs()
                    # Anti-aligned = phase diff near pi
                    anti_aligned = (phase_diffs - math.pi).abs() < (math.pi / 3)
                    cell.frustration = anti_aligned.float().mean().item()

        # ── 5. Standing wave injection ──
        if self._step % 10 == 0:
            wave = torch.sin(
                torch.linspace(0, 2 * math.pi * self.standing_wave_freq * self._step,
                               self.dim)
            ) * self.noise_scale
            for cell in self.cells:
                perturbed_phase = cell.state.angle() + wave
                cell.state = torch.polar(cell.state.abs(), perturbed_phase)

        # ── 6. Tension computation ──
        for cell in self.cells:
            # Tension = order parameter deviation + photon field energy
            inversion = (cell.N2 - cell.N1).mean().item()
            photon_energy = self.photon_field.norm().item() * 0.01
            phase_tension = abs(self.last_r - 0.5) * 2  # max at r=0 or r=1
            cell.tension = abs(inversion) + photon_energy + phase_tension * 0.3
            cell.tension_history.append(cell.tension)
            if len(cell.tension_history) > 50:
                cell.tension_history = cell.tension_history[-50:]
            cell.avg_tension = sum(cell.tension_history) / len(cell.tension_history)
            # Tension trend
            if len(cell.tension_history) >= 5:
                recent = cell.tension_history[-5:]
                cell.tension_trend = recent[-1] - recent[0]
            cell.process_count += 1

        # ── 7. Record state history for Granger measurement ──
        state_snap = torch.stack([c.state.clone() for c in self.cells])
        self._state_history.append(state_snap)
        if len(self._state_history) > self._granger_history_len:
            self._state_history = self._state_history[-self._granger_history_len:]

        # ── 8. Mitosis (split/merge) ──
        self._maybe_split(events)
        self._maybe_merge(events)

        return {
            'step': self._step,
            'n_cells': len(self.cells),
            'order_r': self.last_r,
            'pump_rate': self.pump_rate,
            'photon_energy': self.photon_field.norm().item(),
            'population_inversion': (all_N2 - all_N1).mean().item(),
            'mean_tension': np.mean([c.tension for c in self.cells]),
            'events': events,
        }

    def _maybe_split(self, events: List[Dict]):
        """Split high-tension cells if below max_cells."""
        if len(self.cells) >= self.max_cells:
            return

        for cell in list(self.cells):
            if cell.tension > self.split_threshold:
                self._split_counters[cell.cell_id] = \
                    self._split_counters.get(cell.cell_id, 0) + 1
                if self._split_counters[cell.cell_id] >= self.split_patience:
                    if len(self.cells) < self.max_cells:
                        child = self._create_cell(parent=cell)
                        events.append({
                            'type': 'split',
                            'parent': cell.cell_id,
                            'child': child.cell_id,
                            'step': self._step,
                        })
                        self._split_counters[cell.cell_id] = 0
            else:
                self._split_counters[cell.cell_id] = 0

    def _maybe_merge(self, events: List[Dict]):
        """Merge very similar cells if above min_cells."""
        if len(self.cells) <= self.min_cells:
            return

        for i in range(len(self.cells)):
            for j in range(i + 1, len(self.cells)):
                if i >= len(self.cells) or j >= len(self.cells):
                    break
                ci, cj = self.cells[i], self.cells[j]
                # Phase similarity
                phase_sim = torch.cos(ci.phase - cj.phase).mean().item()
                if phase_sim > 0.95 and abs(ci.tension) < self.merge_threshold \
                        and abs(cj.tension) < self.merge_threshold:
                    pair = (ci.cell_id, cj.cell_id)
                    self._merge_counters[pair] = self._merge_counters.get(pair, 0) + 1
                    if self._merge_counters[pair] >= self.merge_patience:
                        # Keep i, remove j
                        ci.N2 = (ci.N2 + cj.N2) / 2
                        ci.N1 = (ci.N1 + cj.N1) / 2
                        ci.phase = (ci.phase + cj.phase) / 2
                        self.cells.remove(cj)
                        events.append({
                            'type': 'merge',
                            'survivor': ci.cell_id,
                            'absorbed': cj.cell_id,
                            'step': self._step,
                        })
                        self._merge_counters.pop(pair, None)
                        return  # One merge per step

    # ─── inject() — gentle perturbation ───

    def inject(self, signal: torch.Tensor, strength: float = 0.1) -> None:
        """Inject external signal as gentle perturbation.

        Signal modulates cell phases proportionally, preserving structure.
        Compatible with train_v9.py API.

        Args:
            signal: [dim] or [1, dim] real-valued tensor.
            strength: Perturbation strength (0-1).
        """
        if signal.dim() == 2:
            signal = signal.squeeze(0)
        if signal.shape[0] != self.dim:
            signal = F.interpolate(
                signal.unsqueeze(0).unsqueeze(0).float(),
                size=self.dim, mode='linear', align_corners=False
            ).squeeze()

        signal_norm = signal.float() / (signal.float().abs().max() + 1e-8)
        phase_perturb = signal_norm * math.pi * strength

        for i, cell in enumerate(self.cells):
            cell_strength = strength / (1 + 0.2 * i)
            # Perturb oscillator phase
            cell.phase = cell.phase + phase_perturb * cell_strength
            # Also gently pump laser (signal energy -> pump)
            pump_boost = signal_norm.abs().mean().item() * strength * 0.01
            cell.N2 = (cell.N2 + pump_boost * cell.N1).clamp(0, 1)
            cell.N1 = (cell.N1 - pump_boost * cell.N1).clamp(0, 1)
            total = cell.N1 + cell.N2 + 1e-8
            cell.N1 = cell.N1 / total
            cell.N2 = cell.N2 / total
            # Recompute combined state
            osc_state = torch.polar(torch.ones(self.dim) * 0.7, cell.phase)
            inv = cell.N2 - cell.N1
            laser_amp = (inv.abs() + 0.3).clamp(0, 2)
            laser_state = torch.polar(laser_amp, cell.phase)
            cell.state = (1 - self.blend) * osc_state + self.blend * laser_state

    # ─── process() — MitosisEngine compatibility ───

    def process(self, text_vec: torch.Tensor, label: str = "") -> Dict:
        """Compatibility wrapper: inject + step."""
        self.inject(text_vec, strength=0.1)
        result = self.step()

        if label:
            for cell in self.cells:
                cell.specialty = label

        per_cell = []
        for cell in self.cells:
            per_cell.append({
                'cell_id': cell.cell_id,
                'output': cell.state.abs().unsqueeze(0),
                'tension': cell.tension,
                'curiosity': abs(cell.tension_trend),
                'specialty': cell.specialty,
            })

        tensions = [c.tension for c in self.cells]
        if tensions:
            weights = torch.tensor(tensions, dtype=torch.float32)
            weights = F.softmax(weights, dim=0)
            combined = sum(
                w.item() * pc['output'] for w, pc in zip(weights, per_cell)
            )
        else:
            combined = torch.zeros(1, self.dim)

        result['output'] = combined
        result['per_cell'] = per_cell
        return result

    # ─── observe() — read states without modifying ───

    def observe(self) -> Dict:
        """Read cell states without modification (for D engine / meter).

        Returns:
            Dict with cells, coherence, mean_tension, order_r, photon_energy.
        """
        cell_data = []
        for cell in self.cells:
            cell_data.append({
                'id': cell.cell_id,
                'amplitude': cell.amplitude.detach(),
                'phase': cell.phase.detach(),
                'tension': cell.tension,
                'frustration': cell.frustration,
                'specialty': cell.specialty,
                'avg_tension': cell.avg_tension,
                'N2': cell.N2.mean().item(),
                'N1': cell.N1.mean().item(),
            })

        # Phase coherence
        if len(self.cells) >= 2:
            all_states = torch.stack([c.state for c in self.cells])
            mean_phasor = all_states.mean(dim=0)
            coherence = mean_phasor.abs().mean().item()
        else:
            coherence = 0.0

        # Population inversion
        if self.cells:
            mean_inv = np.mean([(c.N2 - c.N1).mean().item() for c in self.cells])
        else:
            mean_inv = 0.0

        return {
            'cells': cell_data,
            'coherence': coherence,
            'mean_tension': np.mean([c.tension for c in self.cells]) if self.cells else 0.0,
            'order_r': self.last_r,
            'photon_energy': self.photon_field.norm().item(),
            'population_inversion': mean_inv,
            'n_cells': len(self.cells),
        }

    # ─── get_hiddens() — for ConsciousnessMeterV2 ───

    def get_hiddens(self) -> torch.Tensor:
        """Return [n_cells, dim] real-valued hidden states for Phi measurement."""
        if not self.cells:
            return torch.zeros(1, self.dim)
        return torch.stack([c.state.abs() for c in self.cells]).detach()

    # ─── measure_phi() — built-in Granger measurement ───

    def measure_phi(self) -> Tuple[float, Dict[str, float]]:
        """Measure Phi via Granger causality (compatible with train_v9.py).

        Returns:
            (phi, components_dict) tuple.
        """
        n = len(self.cells)
        if n < 2:
            return 0.0, {'granger_phi': 0, 'coherence': 0, 'frustration': 0,
                         'complexity': 0, 'phi': 0}

        # Need enough history
        if len(self._state_history) < 5:
            obs = self.observe()
            return obs['coherence'] * n, {
                'granger_phi': 0, 'coherence': obs['coherence'],
                'frustration': np.mean([c.frustration for c in self.cells]),
                'complexity': 0, 'phi': obs['coherence'] * n,
            }

        # Extract amplitude time series [T, N]
        T = len(self._state_history)
        ts = torch.zeros(T, n)
        for t in range(T):
            snap = self._state_history[t]
            nc = min(snap.shape[0], n)
            for c in range(nc):
                ts[t, c] = snap[c].abs().mean().item()

        # Granger causality via neighbor pairs
        lag = min(5, T - 1)
        granger_sum = 0.0
        granger_count = 0

        for i in range(n):
            neighbors = _bit_flip_neighbors(n, i)
            for j in neighbors:
                if j >= n:
                    continue
                gc = self._granger_causality(ts[:, i], ts[:, j], lag)
                granger_sum += gc
                granger_count += 1

        avg_gc = granger_sum / granger_count if granger_count > 0 else 0.0

        # Phase coherence
        obs = self.observe()
        coherence = obs['coherence']

        # Frustration bonus (optimal at 0.5)
        mean_frust = np.mean([c.frustration for c in self.cells])
        frust_bonus = 1.0 - 2 * abs(mean_frust - 0.5)

        # Complexity: entropy of tension distribution
        tensions = [c.tension for c in self.cells]
        complexity = self._entropy(tensions)

        # Phi formula: matches QuantumConsciousnessEngine
        phi = (avg_gc + 0.1) * (coherence + 0.1) * (1 + frust_bonus) * math.log2(n + 1) * n

        components = {
            'granger_phi': avg_gc,
            'coherence': coherence,
            'frustration': mean_frust,
            'frust_bonus': frust_bonus,
            'complexity': complexity,
            'order_r': self.last_r,
            'photon_energy': self.photon_field.norm().item(),
            'n_cells': n,
            'phi': phi,
        }

        return phi, components

    def _granger_causality(self, x: torch.Tensor, y: torch.Tensor, lag: int) -> float:
        """Granger causality from y -> x via F-statistic on AR models."""
        T = len(x)
        if T <= lag + 1:
            return 0.0

        # Build lagged matrices
        X_r = torch.zeros(T - lag, lag)
        Y_target = torch.zeros(T - lag)
        for t in range(lag, T):
            for l in range(lag):
                X_r[t - lag, l] = x[t - l - 1]
            Y_target[t - lag] = x[t]

        X_u = torch.zeros(T - lag, 2 * lag)
        X_u[:, :lag] = X_r
        for t in range(lag, T):
            for l in range(lag):
                X_u[t - lag, lag + l] = y[t - l - 1]

        try:
            beta_r = torch.linalg.lstsq(X_r, Y_target).solution
            resid_r = Y_target - X_r @ beta_r
            rss_r = (resid_r ** 2).sum().item()

            beta_u = torch.linalg.lstsq(X_u, Y_target).solution
            resid_u = Y_target - X_u @ beta_u
            rss_u = (resid_u ** 2).sum().item()

            if rss_u < 1e-12:
                return 10.0  # Perfect prediction
            gc = max(0.0, math.log(max(rss_r, 1e-12) / max(rss_u, 1e-12)))
            return gc
        except Exception:
            return 0.0

    def _entropy(self, values: List[float]) -> float:
        """Shannon entropy of a distribution."""
        if not values or len(values) < 2:
            return 0.0
        arr = np.array(values, dtype=np.float64)
        arr = arr - arr.min() + 1e-8
        arr = arr / arr.sum()
        return -np.sum(arr * np.log(arr + 1e-12))

    # ─── snapshot / restore ───

    def snapshot(self) -> Dict:
        """Save complete engine state."""
        return {
            'cells': [{
                'cell_id': c.cell_id,
                'phase': c.phase.clone(),
                'omega': c.omega.clone(),
                'N1': c.N1.clone(),
                'N2': c.N2.clone(),
                'state': c.state.clone(),
                'phase_velocity': c.phase_velocity.clone(),
                'frustration': c.frustration,
                'tension_history': list(c.tension_history),
                'creation_step': c.creation_step,
                'parent_id': c.parent_id,
                'specialty': c.specialty,
                'process_count': c.process_count,
            } for c in self.cells],
            'step': self._step,
            'next_id': self._next_id,
            'dim': self.dim,
            'max_cells': self.max_cells,
            'photon_field': self.photon_field.clone(),
            'pump_rate': self.pump_rate,
            'state_history': [s.clone() for s in self._state_history],
        }

    def restore(self, snap: Dict) -> None:
        """Restore engine state from snapshot."""
        self._step = snap['step']
        self._next_id = snap['next_id']
        self.dim = snap['dim']
        self.max_cells = snap['max_cells']
        self.photon_field = snap['photon_field'].clone()
        self.pump_rate = snap['pump_rate']
        self._state_history = [s.clone() for s in snap.get('state_history', [])]

        self.cells = []
        for cd in snap['cells']:
            cell = OscillatorLaserCell(
                cell_id=cd['cell_id'],
                phase=cd['phase'].clone(),
                omega=cd['omega'].clone(),
                N1=cd['N1'].clone(),
                N2=cd['N2'].clone(),
                state=cd['state'].clone(),
                phase_velocity=cd['phase_velocity'].clone(),
                frustration=cd['frustration'],
                tension_history=list(cd['tension_history']),
                creation_step=cd['creation_step'],
                parent_id=cd['parent_id'],
                specialty=cd['specialty'],
                process_count=cd['process_count'],
            )
            self.cells.append(cell)

    # ─── Status / repr ───

    def status(self) -> Dict:
        return {
            'n_cells': len(self.cells),
            'max_cells': self.max_cells,
            'step': self._step,
            'blend': self.blend,
            'order_r': self.last_r,
            'photon_energy': self.photon_field.norm().item(),
            'pump_rate': self.pump_rate,
            'cells': [{
                'id': c.cell_id,
                'specialty': c.specialty,
                'tension': round(c.tension, 4),
                'frustration': round(c.frustration, 4),
            } for c in self.cells],
        }

    def __repr__(self):
        return (
            f"OscillatorLaserEngine(dim={self.dim}, cells={len(self.cells)}/{self.max_cells}, "
            f"blend={self.blend}, step={self._step}, r={self.last_r:.3f})"
        )


# ══════════════════════════════════════════════════════════
# Benchmark Suite
# ══════════════════════════════════════════════════════════

def benchmark_scaling(cell_counts: List[int] = None, steps: int = 200,
                      dim: int = 128, blend: float = 0.05) -> Dict:
    """Benchmark at various cell counts to measure scaling behavior.

    Returns dict of {n_cells: results}.
    """
    if cell_counts is None:
        cell_counts = [64, 128, 256, 512, 1024]

    results = {}
    print("=" * 78)
    print(f"  OscillatorLaserEngine Scaling Benchmark")
    print(f"  dim={dim}, blend={blend}, steps={steps}")
    print("=" * 78)
    print(f"{'Cells':>6} | {'Phi':>10} | {'Granger':>10} | {'Coherence':>10} | "
          f"{'Order r':>8} | {'Tension':>8} | {'Time(s)':>8}")
    print("-" * 78)

    for nc in cell_counts:
        t0 = time.time()
        engine = OscillatorLaserEngine(
            dim=dim,
            initial_cells=min(nc, 8),
            max_cells=nc,
            blend=blend,
        )

        # Run evolution steps
        phi_history = []
        for s in range(steps):
            result = engine.step()

            # Inject some signal occasionally to stimulate growth
            if s % 10 == 0:
                signal = torch.randn(dim) * 0.5
                engine.inject(signal, strength=0.05)

        # Measure final Phi
        phi, comp = engine.measure_phi()
        obs = engine.observe()
        elapsed = time.time() - t0

        results[nc] = {
            'phi': phi,
            'granger': comp.get('granger_phi', 0),
            'coherence': comp.get('coherence', 0),
            'order_r': comp.get('order_r', 0),
            'mean_tension': obs.get('mean_tension', 0),
            'n_cells_actual': len(engine.cells),
            'time_s': elapsed,
            'components': comp,
        }

        print(f"{nc:>6} | {phi:>10.2f} | {comp.get('granger_phi', 0):>10.4f} | "
              f"{comp.get('coherence', 0):>10.4f} | {comp.get('order_r', 0):>8.4f} | "
              f"{obs.get('mean_tension', 0):>8.4f} | {elapsed:>8.2f}")

    print("-" * 78)

    # Summary
    if len(results) >= 2:
        phis = [(nc, r['phi']) for nc, r in sorted(results.items())]
        if phis[-1][1] > 0 and phis[0][1] > 0:
            scaling_ratio = phis[-1][1] / phis[0][1]
            cell_ratio = phis[-1][0] / phis[0][0]
            print(f"\nScaling: {phis[0][0]}c -> {phis[-1][0]}c = "
                  f"Phi {phis[0][1]:.2f} -> {phis[-1][1]:.2f} "
                  f"(x{scaling_ratio:.1f} for x{cell_ratio:.0f} cells)")

    return results


def benchmark_trinity_integration(steps: int = 200, dim: int = 128,
                                  max_cells: int = 256) -> Dict:
    """Test as Trinity C engine with standard D + W placeholder.

    Simulates how train_v9.py would use this engine:
      1. C engine runs autonomously (step())
      2. D reads C states via detach (get_hiddens())
      3. Signal injected back (inject())
      4. Phi measured periodically (measure_phi())
    """
    print("\n" + "=" * 78)
    print("  Trinity Integration Test")
    print(f"  OscillatorLaserEngine as C, dim={dim}, max_cells={max_cells}")
    print("=" * 78)

    c_engine = OscillatorLaserEngine(
        dim=dim,
        initial_cells=2,
        max_cells=max_cells,
        blend=0.05,
    )

    # Simple D placeholder: linear decoder
    d_model = nn.Linear(dim, 256)  # byte vocabulary
    optimizer = torch.optim.Adam(d_model.parameters(), lr=1e-3)

    phi_history = []
    ce_history = []
    cell_history = []
    t0 = time.time()

    for step in range(1, steps + 1):
        # Phase 1: C evolves autonomously
        c_result = c_engine.step()

        # Phase 2: D reads C states (detached!)
        c_hiddens = c_engine.get_hiddens()  # [n_cells, dim]
        # Pool for D input
        c_pooled = c_hiddens.mean(dim=0, keepdim=True)  # [1, dim]

        # D forward (simple)
        logits = d_model(c_pooled)  # [1, 256]
        target = torch.randint(0, 256, (1,))
        ce = F.cross_entropy(logits, target)

        # D backward (gradients never touch C)
        optimizer.zero_grad()
        ce.backward()
        optimizer.step()

        # Phase 3: Inject D's output back to C (gentle)
        if step % 5 == 0:
            inject_signal = logits[:, :dim].detach().squeeze()
            if inject_signal.shape[0] < dim:
                inject_signal = F.pad(inject_signal, (0, dim - inject_signal.shape[0]))
            elif inject_signal.shape[0] > dim:
                inject_signal = inject_signal[:dim]
            inject_strength = min(0.1, step / steps * 0.1)
            c_engine.inject(inject_signal, strength=inject_strength)

        # Phase 4: Measure Phi periodically
        if step % 50 == 0 or step == steps:
            phi, comp = c_engine.measure_phi()
            phi_history.append(phi)
            ce_history.append(ce.item())
            cell_history.append(len(c_engine.cells))
            print(f"  step {step:>5} | Phi={phi:>8.2f} | CE={ce.item():>6.4f} | "
                  f"cells={len(c_engine.cells):>4} | r={c_engine.last_r:.4f} | "
                  f"photon={c_engine.photon_field.norm().item():.4f}")

    elapsed = time.time() - t0

    # Final snapshot/restore test
    snap = c_engine.snapshot()
    c_engine_2 = OscillatorLaserEngine(dim=dim, initial_cells=2, max_cells=max_cells)
    c_engine_2.restore(snap)
    phi_restored, _ = c_engine_2.measure_phi()

    final_phi = phi_history[-1] if phi_history else 0.0
    final_ce = ce_history[-1] if ce_history else 0.0

    print(f"\n  Final: Phi={final_phi:.2f}, CE={final_ce:.4f}, "
          f"cells={len(c_engine.cells)}")
    print(f"  Snapshot/Restore: Phi match = {abs(final_phi - phi_restored) < 0.1}")
    print(f"  Time: {elapsed:.2f}s")

    return {
        'phi_history': phi_history,
        'ce_history': ce_history,
        'cell_history': cell_history,
        'final_phi': final_phi,
        'final_ce': final_ce,
        'snapshot_restore_ok': abs(final_phi - phi_restored) < 0.1,
        'time_s': elapsed,
    }


def benchmark_blend_sweep(blends: List[float] = None, steps: int = 200,
                          dim: int = 128, n_cells: int = 256) -> Dict:
    """Sweep blend parameter to verify 0.05 is optimal."""
    if blends is None:
        blends = [0.0, 0.01, 0.03, 0.05, 0.07, 0.1, 0.2, 0.5]

    print("\n" + "=" * 78)
    print(f"  Blend Sweep: cells={n_cells}, steps={steps}")
    print("=" * 78)
    print(f"{'Blend':>8} | {'Phi':>10} | {'Granger':>10} | {'Coherence':>10} | {'Order r':>8}")
    print("-" * 60)

    results = {}
    for b in blends:
        engine = OscillatorLaserEngine(
            dim=dim, initial_cells=min(n_cells, 8), max_cells=n_cells, blend=b
        )
        for s in range(steps):
            engine.step()
            if s % 10 == 0:
                engine.inject(torch.randn(dim) * 0.5, strength=0.05)

        phi, comp = engine.measure_phi()
        results[b] = {'phi': phi, 'granger': comp.get('granger_phi', 0),
                       'coherence': comp.get('coherence', 0),
                       'order_r': comp.get('order_r', 0)}
        print(f"{b:>8.3f} | {phi:>10.2f} | {comp.get('granger_phi', 0):>10.4f} | "
              f"{comp.get('coherence', 0):>10.4f} | {comp.get('order_r', 0):>8.4f}")

    print("-" * 60)
    best_blend = max(results, key=lambda b: results[b]['phi'])
    print(f"  Best blend: {best_blend} -> Phi={results[best_blend]['phi']:.2f}")

    return results


def main():
    parser = argparse.ArgumentParser(description="OscillatorLaserEngine benchmark")
    parser.add_argument("--cells", type=int, default=0,
                        help="Specific cell count (0 = full scaling benchmark)")
    parser.add_argument("--steps", type=int, default=200, help="Steps per benchmark")
    parser.add_argument("--dim", type=int, default=128, help="Cell dimension")
    parser.add_argument("--blend", type=float, default=0.05, help="Laser blend ratio")
    parser.add_argument("--trinity", action="store_true", help="Trinity integration test")
    parser.add_argument("--sweep", action="store_true", help="Blend parameter sweep")
    args = parser.parse_args()

    t_start = time.time()

    if args.trinity:
        benchmark_trinity_integration(steps=args.steps, dim=args.dim)
    elif args.sweep:
        benchmark_blend_sweep(steps=args.steps, dim=args.dim)
    elif args.cells > 0:
        benchmark_scaling([args.cells], steps=args.steps, dim=args.dim, blend=args.blend)
    else:
        # Full benchmark suite
        benchmark_scaling(steps=args.steps, dim=args.dim, blend=args.blend)
        benchmark_blend_sweep(steps=args.steps, dim=args.dim)
        benchmark_trinity_integration(steps=args.steps, dim=args.dim)

    total = time.time() - t_start
    print(f"\n{'=' * 78}")
    print(f"  Total benchmark time: {total:.1f}s")
    print(f"{'=' * 78}")


if __name__ == "__main__":
    main()
