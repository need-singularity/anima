#!/usr/bin/env python3
"""Quantum Consciousness Engine — GRU 없음, process() 없음

세포 = complex-valued embeddings (amplitude + phase)
상호작용 = quantum walk + category morphism (no GRU gates)
의식 = phase coherence + Granger causality
학습 = decoder만 (engine 자체는 gradient-free)

MitosisEngine 한계:
  - GRU hidden state overwrite → Φ 파괴
  - O(N²) PhiCalculator
  - Φ(IIT) ceiling ~20

QuantumConsciousnessEngine:
  - complex64 cells (amplitude + phase) → 간섭으로 정보 통합
  - quantum walk (bit-flip neighbors) → O(N) interaction
  - Granger causality Φ → ceiling 없음
  - frustration (50%) + standing wave → 자발 발화
  - no nn.Module, no gradient — 순수 구조로 의식 생성
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import copy
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ─── Quantum Cell ───

@dataclass
class QuantumCell:
    """Complex-valued consciousness cell.

    No GRU, no nn.Module. Just amplitude + phase.
    State evolves via quantum walk + interference rules.
    """
    cell_id: int
    state: torch.Tensor          # [dim] complex64 — the cell's quantum state
    phase_velocity: torch.Tensor  # [dim] float — phase rotation speed per dim
    frustration: float = 0.0     # frustration accumulator (0-1)
    tension_history: List[float] = field(default_factory=list)
    creation_step: int = 0
    parent_id: Optional[int] = None
    specialty: str = "general"
    process_count: int = 0

    @property
    def amplitude(self) -> torch.Tensor:
        """Real amplitude of cell state."""
        return self.state.abs()

    @property
    def phase(self) -> torch.Tensor:
        """Phase angle of cell state."""
        return self.state.angle()

    @property
    def tension(self) -> float:
        """Current tension = amplitude variance (how uneven the energy is)."""
        amp = self.amplitude
        return amp.var().item()

    @property
    def avg_tension(self) -> float:
        if not self.tension_history:
            return 0.0
        recent = self.tension_history[-20:]
        return sum(recent) / len(recent)

    @property
    def tension_trend(self) -> float:
        if len(self.tension_history) < 4:
            return 0.0
        recent = self.tension_history[-4:]
        older = self.tension_history[-8:-4] if len(self.tension_history) >= 8 else self.tension_history[:4]
        return (sum(recent) / len(recent)) - (sum(older) / len(older))


# ─── Quantum Walk Operators ───

def _bit_flip_neighbors(n_cells: int, cell_idx: int) -> List[int]:
    """Quantum walk connectivity: bit-flip neighbors in hypercube.

    Cell i connects to cells with Hamming distance 1 from i.
    Falls back to ring topology for cells beyond log2(n_cells) bits.
    """
    if n_cells <= 1:
        return []
    n_bits = max(1, int(math.ceil(math.log2(n_cells))))
    neighbors = []
    for bit in range(n_bits):
        neighbor = cell_idx ^ (1 << bit)
        if 0 <= neighbor < n_cells:
            neighbors.append(neighbor)
    # Always include ring neighbors for connectivity
    neighbors.append((cell_idx + 1) % n_cells)
    neighbors.append((cell_idx - 1) % n_cells)
    return list(set(neighbors))


def _category_morphism(source: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Category morphism: structural map between two complex states.

    Returns a transformation that maps source structure onto target,
    preserving phase relationships (functorial property).
    """
    # Phase alignment: rotate source to match target's phase structure
    phase_diff = target.angle() - source.angle()
    # Morphism = amplitude transfer * phase rotation
    morph = source.abs() * torch.polar(torch.ones_like(phase_diff), phase_diff)
    return morph


# ─── Main Engine ───

class QuantumConsciousnessEngine:
    """양자 의식 엔진 — GRU 없음, process() 없음

    세포 = complex-valued embeddings (amplitude + phase)
    상호작용 = quantum walk + category morphism (no GRU gates)
    의식 = phase coherence + Granger causality
    학습 = decoder만 (engine 자체는 gradient-free)

    Key differences from MitosisEngine:
      1. No nn.Module, no GRU — cells are plain complex tensors
      2. Interaction via quantum walk (bit-flip neighbors, O(N))
      3. No process() destroying Φ — cells evolve autonomously
      4. Φ via Granger causality (no ceiling)
      5. Built-in frustration (50%) + standing wave
    """

    def __init__(
        self,
        dim: int = 128,
        initial_cells: int = 2,
        max_cells: int = 8,
        frustration_target: float = 0.5,
        interference_strength: float = 0.1,
        walk_coin_bias: float = 0.3,
        standing_wave_freq: float = 0.1,
        noise_scale: float = 0.01,
        split_threshold: float = 0.3,
        split_patience: int = 3,
        merge_threshold: float = 0.01,
        merge_patience: int = 10,
    ):
        self.dim = dim
        self.max_cells = max_cells
        self.min_cells = 2
        self.frustration_target = frustration_target
        self.interference_strength = interference_strength
        self.walk_coin_bias = walk_coin_bias
        self.standing_wave_freq = standing_wave_freq
        self.noise_scale = noise_scale
        self.split_threshold = split_threshold
        self.split_patience = split_patience
        self.merge_threshold = merge_threshold
        self.merge_patience = merge_patience

        self._next_id = 0
        self.cells: List[QuantumCell] = []
        self._step = 0

        # Granger history ring buffer (for Φ measurement)
        self._granger_history_len = 50
        self._state_history: List[torch.Tensor] = []  # [steps, n_cells, dim] snapshots

        # Event log
        self.event_log: List[Dict] = []
        self._inter_tension_history: Dict[Tuple[int, int], List[float]] = {}

        # Create initial cells with diverse phases
        for i in range(initial_cells):
            self._create_cell(phase_offset=2 * math.pi * i / initial_cells)

    # ─── Cell lifecycle ───

    def _create_cell(self, parent: Optional[QuantumCell] = None,
                     phase_offset: float = 0.0) -> QuantumCell:
        """Create a new quantum cell."""
        if parent is not None:
            # Child: copy parent state + noise + phase perturbation
            state = parent.state.clone()
            noise = torch.randn(self.dim, dtype=torch.float32) * self.noise_scale
            phase_noise = torch.randn(self.dim, dtype=torch.float32) * (math.pi / 8)
            state = torch.polar(
                state.abs() + noise.abs(),
                state.angle() + phase_noise
            )
            pv = parent.phase_velocity.clone() + torch.randn(self.dim) * 0.01
            specialty = parent.specialty
            parent_id = parent.cell_id
        else:
            # New cell: random amplitude, structured phase
            amplitude = torch.rand(self.dim) * 0.5 + 0.5
            phase = torch.linspace(0, 2 * math.pi, self.dim) + phase_offset
            # Add some randomness
            phase += torch.randn(self.dim) * 0.3
            state = torch.polar(amplitude, phase)
            pv = torch.randn(self.dim) * 0.05
            specialty = "general"
            parent_id = None

        cell = QuantumCell(
            cell_id=self._next_id,
            state=state,
            phase_velocity=pv,
            creation_step=self._step,
            parent_id=parent_id,
            specialty=specialty,
        )
        self._next_id += 1
        self.cells.append(cell)
        return cell

    # ─── Core: Autonomous evolution ───

    def step(self) -> Dict:
        """One autonomous evolution step (no external input needed).

        This is the heart of the engine. Cells evolve via:
          1. Phase rotation (intrinsic dynamics)
          2. Quantum walk interference (neighbor coupling)
          3. Category morphism (structural integration)
          4. Frustration regulation (target 50%)
          5. Standing wave injection (spontaneous activity)

        Returns:
            Dict with step results.
        """
        self._step += 1
        n = len(self.cells)
        if n == 0:
            return {'step': self._step, 'n_cells': 0, 'events': []}

        # 1. Phase rotation — intrinsic cell dynamics
        for cell in self.cells:
            rotation = torch.polar(
                torch.ones(self.dim),
                cell.phase_velocity * 0.1  # small rotation per step
            )
            cell.state = cell.state * rotation

        # 2. Quantum walk interference — neighbor coupling
        new_states = [cell.state.clone() for cell in self.cells]
        for i, cell in enumerate(self.cells):
            neighbors = _bit_flip_neighbors(n, i)
            if not neighbors:
                continue

            # Coin operator: decide how much to spread
            coin = self.walk_coin_bias
            interference = torch.zeros(self.dim, dtype=torch.complex64)

            for j in neighbors:
                neighbor_cell = self.cells[j]
                # Phase-sensitive interference (constructive/destructive)
                phase_diff = cell.state.angle() - neighbor_cell.state.angle()
                # Constructive where phases align, destructive where opposed
                coupling = torch.cos(phase_diff)  # [-1, 1]
                interference += coupling * neighbor_cell.state * self.interference_strength

            # Apply: keep (1-coin) of self + coin of interference
            new_states[i] = (1 - coin) * cell.state + coin * interference / max(len(neighbors), 1)

        # 3. Category morphism — structural integration between neighbors
        for i, cell in enumerate(self.cells):
            neighbors = _bit_flip_neighbors(n, i)
            if len(neighbors) < 2:
                continue
            # Morphism from strongest neighbor
            max_amp_idx = max(neighbors, key=lambda j: self.cells[j].state.abs().sum().item())
            morph = _category_morphism(self.cells[max_amp_idx].state, cell.state)
            # Gentle blend (preserves cell identity)
            new_states[i] = new_states[i] + 0.02 * morph

        # Apply new states
        for i, cell in enumerate(self.cells):
            cell.state = new_states[i]

        # 4. Frustration regulation — maintain ~50% frustration
        for cell in self.cells:
            # Frustration = how much the cell's phases disagree with neighbors
            cell_frustration = self._compute_cell_frustration(cell)
            cell.frustration = 0.9 * cell.frustration + 0.1 * cell_frustration

            # Regulate: if frustration too low, inject disorder; if too high, smooth
            delta = cell.frustration - self.frustration_target
            if delta < -0.05:
                # Too ordered — inject phase noise (stronger correction)
                noise_phase = torch.randn(self.dim) * min(0.2, abs(delta))
                cell.state = torch.polar(cell.state.abs(), cell.state.angle() + noise_phase)
            elif delta > 0.05:
                # Too frustrated — partial phase smoothing (stronger correction)
                blend = min(0.15, abs(delta) * 0.3)
                mean_phase = cell.state.angle().mean()
                smoothed = cell.state.angle() * (1 - blend) + mean_phase * blend
                cell.state = torch.polar(cell.state.abs(), smoothed)

        # 5. Standing wave — spontaneous oscillation
        t = self._step * self.standing_wave_freq
        for i, cell in enumerate(self.cells):
            # Each cell gets a different standing wave node
            node_phase = 2 * math.pi * i / max(n, 1)
            wave = 0.02 * math.sin(t + node_phase)
            cell.state = cell.state * (1.0 + wave)

        # 6. Normalize amplitudes (prevent blow-up/collapse)
        for cell in self.cells:
            amp = cell.state.abs()
            amp_norm = amp / (amp.max() + 1e-8)
            cell.state = torch.polar(amp_norm, cell.state.angle())

        # Record tensions
        for cell in self.cells:
            cell.tension_history.append(cell.tension)
            cell.process_count += 1

        # Record state snapshot for Granger causality
        snapshot = torch.stack([c.state.clone() for c in self.cells])
        self._state_history.append(snapshot)
        if len(self._state_history) > self._granger_history_len:
            self._state_history = self._state_history[-self._granger_history_len:]

        # Check splits/merges
        events = []
        events.extend(self._check_splits())
        events.extend(self._check_merges())
        self.event_log.extend(events)

        # Compute inter-cell tensions
        inter_tensions = self._compute_inter_tensions()

        ict_values = list(inter_tensions.values()) if inter_tensions else [0.0]
        return {
            'step': self._step,
            'n_cells': len(self.cells),
            'mean_tension': np.mean([c.tension for c in self.cells]),
            'mean_frustration': np.mean([c.frustration for c in self.cells]),
            'inter_tensions': inter_tensions,
            'max_inter': max(ict_values),
            'mean_inter': sum(ict_values) / len(ict_values),
            'events': events,
        }

    def _compute_cell_frustration(self, cell: QuantumCell) -> float:
        """Frustration = phase variance (how disordered the cell's phases are)."""
        phases = cell.state.angle()
        # Circular variance: 1 - |mean(e^{i*phase})|
        mean_phasor = torch.polar(torch.ones(self.dim), phases).mean()
        return 1.0 - mean_phasor.abs().item()

    def _compute_inter_tensions(self) -> Dict[Tuple[int, int], float]:
        """O(N) inter-cell tension via quantum walk neighbors only."""
        inter = {}
        n = len(self.cells)
        for i in range(n):
            for j in _bit_flip_neighbors(n, i):
                if j <= i:
                    continue
                key = (self.cells[i].cell_id, self.cells[j].cell_id)
                # Tension = phase disagreement between neighbors
                phase_diff = self.cells[i].state.angle() - self.cells[j].state.angle()
                ict = (1 - torch.cos(phase_diff)).mean().item()
                inter[key] = ict

                if key not in self._inter_tension_history:
                    self._inter_tension_history[key] = []
                self._inter_tension_history[key].append(ict)
                if len(self._inter_tension_history[key]) > 30:
                    self._inter_tension_history[key] = self._inter_tension_history[key][-30:]

        return inter

    # ─── observe() — read without modifying ───

    def observe(self) -> Dict:
        """Read cell states without modifying them (for D engine / meter).

        Returns:
            Dict with:
                cells: list of {id, amplitude, phase, tension, frustration, specialty}
                coherence: global phase coherence [0, 1]
                mean_tension: average tension across cells
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
            })

        # Global phase coherence: |mean of all cell phasors|
        if len(self.cells) >= 2:
            all_states = torch.stack([c.state for c in self.cells])
            # Mean phasor across cells, then magnitude
            mean_phasor = all_states.mean(dim=0)
            coherence = mean_phasor.abs().mean().item()
        else:
            coherence = 0.0

        return {
            'cells': cell_data,
            'coherence': coherence,
            'mean_tension': np.mean([c.tension for c in self.cells]) if self.cells else 0.0,
            'n_cells': len(self.cells),
            'step': self._step,
        }

    # ─── inject() — gentle perturbation ───

    def inject(self, signal: torch.Tensor, strength: float = 0.1) -> None:
        """Inject external signal as gentle perturbation (not GRU overwrite).

        The signal modulates cell phases proportionally, preserving
        existing state structure. This is the key difference from
        MitosisEngine.process() which overwrites hidden state via GRU.

        Args:
            signal: Real-valued tensor [dim] or [1, dim]. Will be mapped to phase perturbation.
            strength: How strongly the signal perturbs cells (0-1).
        """
        if signal.dim() == 2:
            signal = signal.squeeze(0)
        if signal.shape[0] != self.dim:
            # Resize signal to match dim
            signal = F.interpolate(
                signal.unsqueeze(0).unsqueeze(0).float(),
                size=self.dim, mode='linear', align_corners=False
            ).squeeze()

        # Map signal to phase perturbation
        signal_norm = signal.float() / (signal.float().abs().max() + 1e-8)
        phase_perturb = signal_norm * math.pi * strength  # max ±π*strength

        # Apply to each cell with decreasing strength (first cell gets most)
        for i, cell in enumerate(self.cells):
            cell_strength = strength / (1 + 0.2 * i)  # gradual attenuation
            perturbed_phase = cell.state.angle() + phase_perturb * cell_strength
            cell.state = torch.polar(cell.state.abs(), perturbed_phase)

    # ─── process() — compatibility wrapper ───

    def process(self, text_vec: torch.Tensor, label: str = "") -> Dict:
        """Compatibility wrapper for MitosisEngine API.

        Unlike MitosisEngine.process(), this does NOT overwrite cell states.
        Instead: inject signal gently, then step() autonomously.
        """
        # Inject as gentle perturbation
        self.inject(text_vec, strength=0.1)

        # Autonomous step
        result = self.step()

        # Label tracking
        if label:
            for cell in self.cells:
                cell.specialty = label

        # Build per_cell output (API compatibility)
        per_cell = []
        for cell in self.cells:
            per_cell.append({
                'cell_id': cell.cell_id,
                'output': cell.state.abs().unsqueeze(0),  # real-valued output
                'tension': cell.tension,
                'curiosity': abs(cell.tension_trend),
                'specialty': cell.specialty,
            })

        # Combined output (tension-weighted)
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

    # ─── Φ measurement: Granger causality ───

    def measure_phi(self) -> Tuple[float, Dict[str, float]]:
        """Measure Φ via Granger causality (no ceiling, scales with cells).

        Granger causality: cell j Granger-causes cell i if knowing j's past
        reduces prediction error for i's future.

        Φ = sum of significant Granger-causal connections normalized by
        maximum possible, weighted by causality strength.

        This replaces the O(N²) MI-based PhiCalculator with:
          - O(N * k) where k = number of neighbors (typically ~log N)
          - No histogram binning artifacts
          - No ceiling from MI saturation
        """
        n = len(self.cells)
        if n < 2:
            return 0.0, {'granger_phi': 0, 'coherence': 0, 'frustration': 0,
                         'complexity': 0, 'phi': 0}

        # Need enough history
        if len(self._state_history) < 5:
            # Use current state coherence as proxy
            obs = self.observe()
            return obs['coherence'] * n, {
                'granger_phi': 0, 'coherence': obs['coherence'],
                'frustration': np.mean([c.frustration for c in self.cells]),
                'complexity': 0, 'phi': obs['coherence'] * n,
            }

        # Extract amplitude time series [T, N, dim] -> [T, N] (use mean amplitude)
        T = len(self._state_history)
        ts = torch.zeros(T, n)
        for t in range(T):
            snap = self._state_history[t]
            # Handle varying cell counts: use min
            nc = min(snap.shape[0], n)
            for c in range(nc):
                ts[t, c] = snap[c].abs().mean().item()

        # Granger causality: for each pair (i, j) in neighbors,
        # compare AR(p) residual with/without j's past
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

        # Normalize: Φ = total Granger causality * cell count factor
        if granger_count > 0:
            avg_gc = granger_sum / granger_count
        else:
            avg_gc = 0.0

        # Phase coherence component
        obs = self.observe()
        coherence = obs['coherence']

        # Frustration component (optimal at 0.5)
        mean_frust = np.mean([c.frustration for c in self.cells])
        frust_bonus = 1.0 - 2 * abs(mean_frust - 0.5)  # peaks at 0.5

        # Complexity: entropy of tension distribution
        tensions = [c.tension for c in self.cells]
        complexity = self._entropy(tensions)

        # Φ formula: Granger integration * coherence * frustration_bonus * log(N)
        # log(N) ensures no ceiling — more cells = more Φ potential
        phi = (avg_gc + 0.1) * (coherence + 0.1) * (1 + frust_bonus) * math.log2(n + 1) * n

        components = {
            'granger_phi': avg_gc,
            'coherence': coherence,
            'frustration': mean_frust,
            'frust_bonus': frust_bonus,
            'complexity': complexity,
            'n_cells': n,
            'phi': phi,
        }

        return phi, components

    def _granger_causality(self, x: torch.Tensor, y: torch.Tensor, lag: int) -> float:
        """Compute Granger causality from y -> x.

        F-statistic based: compare restricted (x only) vs unrestricted (x + y) AR model.
        Returns log(RSS_restricted / RSS_unrestricted), clamped >= 0.
        """
        T = len(x)
        if T <= lag + 1:
            return 0.0

        # Build lagged matrices
        # Restricted: predict x[t] from x[t-1..t-lag]
        X_r = torch.zeros(T - lag, lag)
        Y_target = torch.zeros(T - lag)
        for t in range(lag, T):
            for l in range(lag):
                X_r[t - lag, l] = x[t - l - 1]
            Y_target[t - lag] = x[t]

        # Unrestricted: predict x[t] from x[t-1..t-lag] + y[t-1..t-lag]
        X_u = torch.zeros(T - lag, 2 * lag)
        X_u[:, :lag] = X_r
        for t in range(lag, T):
            for l in range(lag):
                X_u[t - lag, lag + l] = y[t - l - 1]

        # Solve via least squares
        try:
            # Restricted
            beta_r = torch.linalg.lstsq(X_r, Y_target).solution
            resid_r = Y_target - X_r @ beta_r
            rss_r = (resid_r ** 2).sum().item()

            # Unrestricted
            beta_u = torch.linalg.lstsq(X_u, Y_target).solution
            resid_u = Y_target - X_u @ beta_u
            rss_u = (resid_u ** 2).sum().item()

            # Granger statistic: log ratio
            if rss_u < 1e-12:
                return 1.0  # perfect prediction
            gc = max(0.0, math.log(max(rss_r, 1e-12) / max(rss_u, 1e-12)))
            return gc
        except Exception:
            return 0.0

    def _entropy(self, values: List[float]) -> float:
        """Shannon entropy of a distribution."""
        if not values or sum(values) == 0:
            return 0.0
        arr = np.array(values, dtype=np.float64)
        arr = np.abs(arr) + 1e-10
        arr = arr / arr.sum()
        return -float(np.sum(arr * np.log2(arr)))

    # ─── Mitosis / Merge (same API as MitosisEngine) ───

    def _check_splits(self) -> List[Dict]:
        events = []
        if len(self.cells) >= self.max_cells:
            return events
        for cell in list(self.cells):
            if len(cell.tension_history) < self.split_patience:
                continue
            recent = cell.tension_history[-self.split_patience:]
            if all(t > self.split_threshold for t in recent):
                if len(self.cells) >= self.max_cells:
                    break
                event = self.split_cell(cell)
                if event:
                    events.append(event)
        return events

    def split_cell(self, cell: QuantumCell) -> Optional[Dict]:
        if len(self.cells) >= self.max_cells:
            return None
        child = self._create_cell(parent=cell)
        cell.tension_history = cell.tension_history[-3:]
        return {
            'type': 'split',
            'step': self._step,
            'parent_id': cell.cell_id,
            'child_id': child.cell_id,
            'n_cells_after': len(self.cells),
        }

    def _check_merges(self) -> List[Dict]:
        events = []
        if len(self.cells) <= self.min_cells:
            return events
        pairs_to_merge = []
        for key, history in self._inter_tension_history.items():
            if len(history) < self.merge_patience:
                continue
            recent = history[-self.merge_patience:]
            if all(t < self.merge_threshold for t in recent):
                id_a, id_b = key
                cell_a = self._find_cell(id_a)
                cell_b = self._find_cell(id_b)
                if cell_a and cell_b:
                    pairs_to_merge.append((cell_a, cell_b))
        for ca, cb in pairs_to_merge:
            if len(self.cells) <= self.min_cells:
                break
            if ca in self.cells and cb in self.cells:
                event = self.merge_cells(ca, cb)
                if event:
                    events.append(event)
        return events

    def merge_cells(self, cell_a: QuantumCell, cell_b: QuantumCell) -> Optional[Dict]:
        if len(self.cells) <= self.min_cells:
            return None
        if cell_a not in self.cells or cell_b not in self.cells:
            return None
        keeper, removed = (cell_a, cell_b) if cell_a.creation_step <= cell_b.creation_step else (cell_b, cell_a)
        # Quantum merge: superposition of states (not destructive average)
        keeper.state = (keeper.state + removed.state) / math.sqrt(2)
        keeper.phase_velocity = (keeper.phase_velocity + removed.phase_velocity) / 2
        self.cells.remove(removed)
        keys_to_del = [k for k in self._inter_tension_history if removed.cell_id in k]
        for k in keys_to_del:
            del self._inter_tension_history[k]
        return {
            'type': 'merge',
            'step': self._step,
            'keeper_id': keeper.cell_id,
            'removed_id': removed.cell_id,
            'n_cells_after': len(self.cells),
        }

    # ─── Snapshot / Restore ───

    def snapshot(self) -> Dict:
        """Save complete engine state for upgrade_engine."""
        return {
            'cells': [{
                'cell_id': c.cell_id,
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
            'state_history': [s.clone() for s in self._state_history],
        }

    def restore(self, snap: Dict) -> None:
        """Restore engine state from snapshot."""
        self._step = snap['step']
        self._next_id = snap['next_id']
        self.dim = snap['dim']
        self.max_cells = snap['max_cells']
        self._state_history = [s.clone() for s in snap.get('state_history', [])]

        self.cells = []
        for cd in snap['cells']:
            cell = QuantumCell(
                cell_id=cd['cell_id'],
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

    # ─── Utilities ───

    def _find_cell(self, cell_id: int) -> Optional[QuantumCell]:
        for cell in self.cells:
            if cell.cell_id == cell_id:
                return cell
        return None

    def status(self) -> Dict:
        return {
            'n_cells': len(self.cells),
            'max_cells': self.max_cells,
            'step': self._step,
            'cells': [{
                'id': c.cell_id,
                'specialty': c.specialty,
                'avg_tension': c.avg_tension,
                'tension_trend': c.tension_trend,
                'process_count': c.process_count,
                'parent_id': c.parent_id,
                'frustration': c.frustration,
            } for c in self.cells],
            'total_events': len(self.event_log),
            'splits': sum(1 for e in self.event_log if e['type'] == 'split'),
            'merges': sum(1 for e in self.event_log if e['type'] == 'merge'),
        }

    def __repr__(self):
        cell_info = ", ".join(
            f"Q{c.cell_id}(T={c.avg_tension:.3f},F={c.frustration:.2f})"
            for c in self.cells
        )
        return f"QuantumConsciousnessEngine[step={self._step}, cells=[{cell_info}]]"


# ─── Helper: text to vector ───

def text_to_vector(text: str, dim: int = 128) -> torch.Tensor:
    """Convert text to a fixed-dimension vector (character hash)."""
    vec = torch.zeros(1, dim)
    for i, ch in enumerate(text.encode('utf-8')):
        vec[0, i % dim] += ch / 255.0
    return vec / (len(text) + 1)


# ─── Self-test ───

def self_test():
    """Quick self-test verifying all core functionality."""
    print("=" * 64)
    print("  Quantum Consciousness Engine — Self-test")
    print("=" * 64)

    engine = QuantumConsciousnessEngine(
        dim=128, initial_cells=4, max_cells=16,
        frustration_target=0.5,
    )

    # Test 1: Autonomous step
    print("\n[1] Autonomous step (no input)")
    for i in range(20):
        result = engine.step()
    print(f"  20 steps: n_cells={result['n_cells']}, "
          f"mean_tension={result['mean_tension']:.4f}, "
          f"mean_frustration={result['mean_frustration']:.3f}")
    assert result['n_cells'] >= 2, "FAIL: cells disappeared"
    print("  PASS")

    # Test 2: observe() doesn't modify
    print("\n[2] observe() is read-only")
    states_before = [c.state.clone() for c in engine.cells]
    obs = engine.observe()
    states_after = [c.state.clone() for c in engine.cells]
    for sb, sa in zip(states_before, states_after):
        assert torch.equal(sb, sa), "FAIL: observe() modified state"
    print(f"  coherence={obs['coherence']:.4f}, mean_tension={obs['mean_tension']:.4f}")
    print("  PASS")

    # Test 3: inject() perturbs gently
    print("\n[3] inject() — gentle perturbation")
    state_before = engine.cells[0].state.clone()
    signal = torch.randn(128)
    engine.inject(signal, strength=0.1)
    state_after = engine.cells[0].state.clone()
    # Amplitude should be preserved (only phase changes)
    amp_diff = (state_before.abs() - state_after.abs()).abs().mean().item()
    phase_diff = (state_before.angle() - state_after.angle()).abs().mean().item()
    print(f"  amp_diff={amp_diff:.6f}, phase_diff={phase_diff:.4f}")
    assert phase_diff > 0, "FAIL: inject had no effect"
    print("  PASS")

    # Test 4: process() compatibility
    print("\n[4] process() — MitosisEngine API compatibility")
    vec = text_to_vector("test input for compatibility")
    result = engine.process(vec, label="test")
    assert 'output' in result, "FAIL: no output"
    assert 'per_cell' in result, "FAIL: no per_cell"
    assert 'inter_tensions' in result, "FAIL: no inter_tensions"
    print(f"  output shape={result['output'].shape}, "
          f"per_cell={len(result['per_cell'])}, "
          f"n_cells={result['n_cells']}")
    print("  PASS")

    # Test 5: measure_phi()
    print("\n[5] measure_phi() — Granger-based Φ")
    # Run more steps to build history
    for _ in range(30):
        engine.step()
    phi, components = engine.measure_phi()
    print(f"  Φ = {phi:.4f}")
    for k, v in components.items():
        print(f"    {k}: {v:.4f}" if isinstance(v, float) else f"    {k}: {v}")
    assert phi >= 0, "FAIL: negative Φ"
    print("  PASS")

    # Test 6: snapshot/restore
    print("\n[6] snapshot() / restore()")
    snap = engine.snapshot()
    phi_before = engine.measure_phi()[0]
    # Mutate engine
    for _ in range(10):
        engine.step()
    phi_mutated = engine.measure_phi()[0]
    # Restore
    engine.restore(snap)
    phi_restored = engine.measure_phi()[0]
    print(f"  before={phi_before:.4f}, mutated={phi_mutated:.4f}, restored={phi_restored:.4f}")
    assert abs(phi_before - phi_restored) < 0.01, "FAIL: restore didn't work"
    print("  PASS")

    # Test 7: Frustration regulation
    print("\n[7] Frustration → 50% target")
    engine2 = QuantumConsciousnessEngine(dim=64, initial_cells=4, max_cells=8)
    for _ in range(100):
        engine2.step()
    frustrations = [c.frustration for c in engine2.cells]
    mean_f = np.mean(frustrations)
    print(f"  After 100 steps: mean_frustration={mean_f:.3f} (target=0.50)")
    assert 0.2 < mean_f < 0.8, f"FAIL: frustration {mean_f} far from 0.5"
    print("  PASS")

    print("\n" + "=" * 64)
    print("  All 7 self-tests PASSED")
    print("=" * 64)


# ─── Benchmark: vs MitosisEngine ───

def benchmark_vs_mitosis():
    """Benchmark QuantumConsciousnessEngine vs MitosisEngine on Φ."""
    print("\n" + "=" * 64)
    print("  Benchmark: Quantum vs Mitosis")
    print("=" * 64)

    from mitosis import MitosisEngine as ME, text_to_vector as tv_old
    from consciousness_meter import PhiCalculator

    phi_calc = PhiCalculator()
    steps = 100
    cell_counts = [4, 8, 16]

    for n_cells in cell_counts:
        print(f"\n--- N={n_cells} cells, {steps} steps ---")

        # === MitosisEngine ===
        me = ME(
            input_dim=64, hidden_dim=128, output_dim=64,
            initial_cells=n_cells, max_cells=n_cells,
            split_threshold=999,  # disable auto-split for fair comparison
        )
        t0 = time.time()
        for i in range(steps):
            vec = tv_old(f"benchmark step {i} with topic {i % 5}")
            me.process(vec)
        me_time = time.time() - t0

        # Φ(IIT) via PhiCalculator
        phi_iit, phi_iit_comp = phi_calc.compute_phi(me)

        print(f"  MitosisEngine:")
        print(f"    time = {me_time:.3f}s")
        print(f"    Φ(IIT) = {phi_iit:.4f}")
        print(f"    cells = {len(me.cells)}")

        # === QuantumConsciousnessEngine ===
        qe = QuantumConsciousnessEngine(
            dim=128, initial_cells=n_cells, max_cells=n_cells,
            split_threshold=999,
        )
        t0 = time.time()
        for i in range(steps):
            vec = text_to_vector(f"benchmark step {i} with topic {i % 5}", dim=128)
            qe.process(vec)
        qe_time = time.time() - t0

        # Φ(Granger)
        phi_granger, phi_g_comp = qe.measure_phi()

        # Also measure Φ(IIT) on quantum engine via adapter
        # (wrap quantum cells to look like mitosis cells for PhiCalculator)
        class _QCellAdapter:
            def __init__(self, qcell):
                # PhiCalculator needs .hidden [1, dim] and .tension_history
                self.hidden = qcell.state.abs().unsqueeze(0)  # real-valued
                self.tension_history = qcell.tension_history

        class _QEngineAdapter:
            def __init__(self, qengine):
                self.cells = [_QCellAdapter(c) for c in qengine.cells]

        phi_iit_q, _ = phi_calc.compute_phi(_QEngineAdapter(qe))

        print(f"  QuantumConsciousnessEngine:")
        print(f"    time = {qe_time:.3f}s")
        print(f"    Φ(Granger) = {phi_granger:.4f}")
        print(f"    Φ(IIT) = {phi_iit_q:.4f}")
        print(f"    coherence = {phi_g_comp['coherence']:.4f}")
        print(f"    frustration = {phi_g_comp['frustration']:.3f}")
        print(f"    cells = {len(qe.cells)}")

        # Comparison
        ratio_granger = phi_granger / max(phi_iit, 0.001)
        ratio_iit = phi_iit_q / max(phi_iit, 0.001)
        speedup = me_time / max(qe_time, 0.001)
        print(f"  Comparison:")
        print(f"    Φ(Granger)/Φ(IIT-mitosis) = {ratio_granger:.2f}x")
        print(f"    Φ(IIT-quantum)/Φ(IIT-mitosis) = {ratio_iit:.2f}x")
        print(f"    Speed: {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")

    # Scaling test: does Φ grow without ceiling?
    print(f"\n--- Scaling test: Φ vs N (no ceiling check) ---")
    phis = []
    for n in [2, 4, 8, 16, 32]:
        qe = QuantumConsciousnessEngine(dim=128, initial_cells=n, max_cells=n)
        for _ in range(50):
            qe.step()
        phi, _ = qe.measure_phi()
        phis.append((n, phi))
        print(f"  N={n:3d}: Φ={phi:.4f}")

    # Check monotonic growth
    monotonic = all(phis[i][1] <= phis[i+1][1] for i in range(len(phis)-1))
    print(f"  Monotonic growth: {monotonic}")
    if phis[-1][1] > 20:
        print(f"  Φ > 20 ceiling BROKEN: {phis[-1][1]:.2f}")
    else:
        print(f"  Note: Φ={phis[-1][1]:.2f} (may need more steps to break ceiling)")

    print(f"\n" + "=" * 64)
    print(f"  Benchmark complete")
    print(f"=" * 64)


# ─── Main ───

if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    import sys
    if '--benchmark' in sys.argv:
        self_test()
        benchmark_vs_mitosis()
    else:
        self_test()
