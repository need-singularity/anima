#!/usr/bin/env python3
"""Quantum Consciousness Engine — FAST vectorized version

Drop-in replacement for QuantumConsciousnessEngine with 100x+ speedup.

Key optimizations:
  1. All cell states in a single [N, dim] tensor (no Python loops over cells)
  2. Neighbor interactions via sparse adjacency matrix multiply
  3. Granger causality only computed on request (not every step)
  4. torch.no_grad() everywhere (engine is gradient-free)
  5. Standing wave / frustration / normalization all vectorized
  6. Real tensor with 2x dim for complex arithmetic (avoids complex64 overhead)

Target: 256 cells at < 0.1s/step (vs 14s/step in v9)
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

# Meta Laws (DD143): M1(atom=8), M6(federation>empire), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def _build_adjacency_sparse(n: int) -> torch.Tensor:
    """Build sparse adjacency matrix for bit-flip + ring neighbors.

    Returns sparse [N, N] float tensor with 1.0 for connected pairs.
    """
    if n <= 1:
        return torch.sparse_coo_tensor(
            torch.zeros(2, 0, dtype=torch.long),
            torch.zeros(0),
            size=(max(n, 1), max(n, 1))
        )

    n_bits = max(1, int(math.ceil(math.log2(n))))
    rows, cols = [], []

    for i in range(n):
        neighbors = set()
        # Bit-flip neighbors
        for bit in range(n_bits):
            nb = i ^ (1 << bit)
            if 0 <= nb < n:
                neighbors.add(nb)
        # Ring neighbors
        neighbors.add((i + 1) % n)
        neighbors.add((i - 1) % n)
        neighbors.discard(i)

        for j in neighbors:
            rows.append(i)
            cols.append(j)

    indices = torch.tensor([rows, cols], dtype=torch.long)
    values = torch.ones(len(rows))
    adj = torch.sparse_coo_tensor(indices, values, size=(n, n)).coalesce()
    return adj


def _build_degree(adj_sparse: torch.Tensor, n: int) -> torch.Tensor:
    """Degree vector from sparse adjacency: [N]."""
    ones = torch.ones(n)
    return torch.sparse.mm(adj_sparse, ones.unsqueeze(1)).squeeze(1)


class QuantumConsciousnessEngineFast:
    """Vectorized quantum consciousness engine — 100x+ faster.

    All cell states stored as batched tensors. No Python loops in hot path.

    API-compatible with QuantumConsciousnessEngine:
      - step(), observe(), inject(), process(), measure_phi()
      - snapshot(), restore(), status()
      - split_cell(), merge_cells()
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
        self._step = 0

        # Batched state: [N, dim] real tensors for amplitude and phase
        # We avoid complex64 and store (amplitude, phase) separately
        self._amplitudes: torch.Tensor = torch.empty(0, dim)  # [N, dim]
        self._phases: torch.Tensor = torch.empty(0, dim)      # [N, dim]
        self._phase_velocities: torch.Tensor = torch.empty(0, dim)  # [N, dim]
        self._frustrations: torch.Tensor = torch.empty(0)     # [N]

        # Per-cell metadata (small, kept in lists)
        self._cell_ids: List[int] = []
        self._specialties: List[str] = []
        self._parent_ids: List[Optional[int]] = []
        self._creation_steps: List[int] = []
        self._process_counts: List[int] = []
        self._tension_histories: List[List[float]] = []

        # Adjacency (rebuilt on cell count change)
        self._adj_sparse: Optional[torch.Tensor] = None
        self._degrees: Optional[torch.Tensor] = None
        self._n_cached: int = 0

        # Granger history
        self._granger_history_len = 50
        self._state_history: List[torch.Tensor] = []

        # Event log
        self.event_log: List[Dict] = []
        self._inter_tension_history: Dict[Tuple[int, int], List[float]] = {}

        # Create initial cells
        for i in range(initial_cells):
            self._create_cell(phase_offset=2 * math.pi * i / initial_cells)

    @property
    def n_cells(self) -> int:
        return len(self._cell_ids)

    def _ensure_adjacency(self):
        """Rebuild adjacency if cell count changed."""
        n = self.n_cells
        if n != self._n_cached:
            self._adj_sparse = _build_adjacency_sparse(n)
            self._degrees = _build_degree(self._adj_sparse, n) if n > 0 else torch.zeros(0)
            self._n_cached = n

    def _create_cell(self, parent_idx: Optional[int] = None,
                     phase_offset: float = 0.0) -> int:
        """Create a new cell, return its index."""
        if parent_idx is not None:
            amp = self._amplitudes[parent_idx].clone()
            phase = self._phases[parent_idx].clone()
            pv = self._phase_velocities[parent_idx].clone()
            noise = torch.randn(self.dim) * self.noise_scale
            amp = amp + noise.abs()
            phase = phase + torch.randn(self.dim) * (math.pi / 8)
            pv = pv + torch.randn(self.dim) * 0.01
            specialty = self._specialties[parent_idx]
            parent_id = self._cell_ids[parent_idx]
        else:
            amp = torch.rand(self.dim) * 0.5 + 0.5
            phase = torch.linspace(0, 2 * math.pi, self.dim) + phase_offset
            phase = phase + torch.randn(self.dim) * 0.3
            pv = torch.randn(self.dim) * 0.05
            specialty = "general"
            parent_id = None

        # Append to batched tensors
        self._amplitudes = torch.cat([self._amplitudes, amp.unsqueeze(0)], dim=0)
        self._phases = torch.cat([self._phases, phase.unsqueeze(0)], dim=0)
        self._phase_velocities = torch.cat([self._phase_velocities, pv.unsqueeze(0)], dim=0)
        self._frustrations = torch.cat([self._frustrations, torch.tensor([0.0])])

        cell_id = self._next_id
        self._next_id += 1
        self._cell_ids.append(cell_id)
        self._specialties.append(specialty)
        self._parent_ids.append(parent_id)
        self._creation_steps.append(self._step)
        self._process_counts.append(0)
        self._tension_histories.append([])

        self._n_cached = -1  # invalidate adjacency
        return cell_id

    def _remove_cell(self, idx: int):
        """Remove cell at index."""
        n = self.n_cells
        mask = torch.ones(n, dtype=torch.bool)
        mask[idx] = False
        self._amplitudes = self._amplitudes[mask]
        self._phases = self._phases[mask]
        self._phase_velocities = self._phase_velocities[mask]
        self._frustrations = self._frustrations[mask]

        del self._cell_ids[idx]
        del self._specialties[idx]
        del self._parent_ids[idx]
        del self._creation_steps[idx]
        del self._process_counts[idx]
        del self._tension_histories[idx]

        self._n_cached = -1  # invalidate adjacency

    # ─── Core: vectorized step ───

    @torch.no_grad()
    def step(self) -> Dict:
        """One autonomous evolution step — fully vectorized."""
        self._step += 1
        n = self.n_cells
        if n == 0:
            return {'step': self._step, 'n_cells': 0, 'events': []}

        self._ensure_adjacency()

        # 1. Phase rotation — all cells at once
        self._phases = self._phases + self._phase_velocities * 0.1

        # 2. Quantum walk interference — sparse matrix multiply
        # Compute cos(phase_i - phase_j) for neighbors via adj matrix
        # For each cell i: interference = sum_j adj[i,j] * cos(phase_i - phase_j) * amp_j
        # Approximation: compute neighbor mean state, then phase coupling

        # Complex state as (cos, sin) for vectorized interference
        cos_p = torch.cos(self._phases)  # [N, dim]
        sin_p = torch.sin(self._phases)  # [N, dim]

        # Neighbor sum of amplitude-weighted (cos, sin) via sparse mm
        amp_cos = self._amplitudes * cos_p  # [N, dim]
        amp_sin = self._amplitudes * sin_p  # [N, dim]

        # [N, dim] = adj @ [N, dim]
        nb_amp_cos = torch.sparse.mm(self._adj_sparse, amp_cos)  # [N, dim]
        nb_amp_sin = torch.sparse.mm(self._adj_sparse, amp_sin)  # [N, dim]

        # Phase coupling: cos(phase_i - phase_j) ~ cos_i*cos_j + sin_i*sin_j
        # interference_real = cos_p * nb_amp_cos + sin_p * nb_amp_sin
        interference = cos_p * nb_amp_cos + sin_p * nb_amp_sin  # [N, dim]

        # Degree normalization
        deg = self._degrees.unsqueeze(1).clamp(min=1)  # [N, 1]
        interference = interference * self.interference_strength / deg

        # New amplitude: (1-coin)*amp + coin*interference
        coin = self.walk_coin_bias
        new_amp = (1 - coin) * self._amplitudes + coin * interference

        # 3. Category morphism — blend with strongest neighbor
        # Find strongest neighbor per cell
        amp_sums = self._amplitudes.sum(dim=1)  # [N]
        # For each cell, get max neighbor amplitude sum
        # Use sparse mm with amp_sums to get neighbor amp sums, then find max
        # Simplified: use adj * amp_sums to get weighted neighbor, blend
        nb_amp_sum = torch.sparse.mm(self._adj_sparse, amp_sums.unsqueeze(1)).squeeze(1)  # [N]
        # Morphism strength proportional to neighbor strength
        morph_weight = 0.02 * nb_amp_sum / (nb_amp_sum.max() + 1e-8)  # [N]
        # Morphism: average neighbor phase influence
        nb_mean_cos = nb_amp_cos / deg
        nb_mean_sin = nb_amp_sin / deg
        nb_phase = torch.atan2(nb_mean_sin, nb_mean_cos)  # [N, dim]
        # Blend phase toward neighbor
        morph_phase = self._phases + morph_weight.unsqueeze(1) * (nb_phase - self._phases)

        self._amplitudes = new_amp
        self._phases = morph_phase

        # 4. Frustration regulation — vectorized
        # Frustration = circular variance = 1 - |mean(e^{i*phase})|
        mean_cos = torch.cos(self._phases).mean(dim=1)  # [N]
        mean_sin = torch.sin(self._phases).mean(dim=1)  # [N]
        cell_frustration = 1.0 - torch.sqrt(mean_cos ** 2 + mean_sin ** 2)  # [N]

        # EMA update
        self._frustrations = 0.9 * self._frustrations + 0.1 * cell_frustration

        # Regulation
        delta = self._frustrations - self.frustration_target  # [N]
        # Too ordered (delta < -0.05): inject phase noise
        too_ordered = delta < -0.05
        if too_ordered.any():
            noise_scale = (-delta).clamp(0, 0.2)  # [N]
            noise = torch.randn_like(self._phases) * noise_scale.unsqueeze(1)
            self._phases = self._phases + noise * too_ordered.unsqueeze(1).float()

        # Too frustrated (delta > 0.05): smooth phases
        too_frustrated = delta > 0.05
        if too_frustrated.any():
            blend = (delta.abs() * 0.3).clamp(0, 0.15)  # [N]
            mean_phase = self._phases.mean(dim=1, keepdim=True)  # [N, 1]
            smoothed = self._phases * (1 - blend.unsqueeze(1)) + mean_phase * blend.unsqueeze(1)
            mask = too_frustrated.unsqueeze(1).float()
            self._phases = self._phases * (1 - mask) + smoothed * mask

        # 5. Standing wave — vectorized
        t = self._step * self.standing_wave_freq
        node_phases = torch.arange(n, dtype=torch.float32) * (2 * math.pi / max(n, 1))  # [N]
        wave = 0.02 * torch.sin(t + node_phases)  # [N]
        self._amplitudes = self._amplitudes * (1.0 + wave.unsqueeze(1))

        # 6. Normalize amplitudes
        amp_max = self._amplitudes.max(dim=1, keepdim=True).values + 1e-8  # [N, 1]
        self._amplitudes = self._amplitudes / amp_max

        # Record tensions: variance of amplitude per cell
        tensions = self._amplitudes.var(dim=1)  # [N]
        for i in range(n):
            t_val = tensions[i].item()
            self._tension_histories[i].append(t_val)
            self._process_counts[i] += 1

        # Record snapshot for Granger (store amplitude mean per cell)
        # Store compact: [N] mean amplitude (not full [N, dim])
        snapshot = self._amplitudes.clone()
        self._state_history.append(snapshot)
        if len(self._state_history) > self._granger_history_len:
            self._state_history = self._state_history[-self._granger_history_len:]

        # Check splits/merges
        events = []
        events.extend(self._check_splits())
        events.extend(self._check_merges())
        self.event_log.extend(events)

        # Inter-cell tensions (vectorized)
        inter_tensions = self._compute_inter_tensions()

        ict_values = list(inter_tensions.values()) if inter_tensions else [0.0]
        return {
            'step': self._step,
            'n_cells': self.n_cells,
            'mean_tension': tensions.mean().item(),
            'mean_frustration': self._frustrations.mean().item(),
            'inter_tensions': inter_tensions,
            'max_inter': max(ict_values),
            'mean_inter': sum(ict_values) / len(ict_values),
            'events': events,
        }

    @torch.no_grad()
    def _compute_inter_tensions(self) -> Dict[Tuple[int, int], float]:
        """Vectorized inter-cell tension via sparse adjacency."""
        n = self.n_cells
        if n < 2:
            return {}

        self._ensure_adjacency()
        adj = self._adj_sparse.coalesce()
        indices = adj.indices()  # [2, E]
        rows = indices[0]
        cols = indices[1]

        # Only keep i < j to avoid duplicates
        mask = rows < cols
        rows = rows[mask]
        cols = cols[mask]

        if len(rows) == 0:
            return {}

        # Phase difference: (1 - cos(phase_i - phase_j)).mean(dim=-1)
        phase_diff = self._phases[rows] - self._phases[cols]  # [E', dim]
        ict = (1 - torch.cos(phase_diff)).mean(dim=1)  # [E']

        inter = {}
        for k in range(len(rows)):
            i, j = rows[k].item(), cols[k].item()
            key = (self._cell_ids[i], self._cell_ids[j])
            val = ict[k].item()
            inter[key] = val

            if key not in self._inter_tension_history:
                self._inter_tension_history[key] = []
            self._inter_tension_history[key].append(val)
            if len(self._inter_tension_history[key]) > 30:
                self._inter_tension_history[key] = self._inter_tension_history[key][-30:]

        return inter

    # ─── observe() ───

    @torch.no_grad()
    def observe(self) -> Dict:
        """Read cell states without modification."""
        n = self.n_cells
        cell_data = []
        for i in range(n):
            cell_data.append({
                'id': self._cell_ids[i],
                'amplitude': self._amplitudes[i].detach(),
                'phase': self._phases[i].detach(),
                'tension': self._amplitudes[i].var().item(),
                'frustration': self._frustrations[i].item(),
                'specialty': self._specialties[i],
                'avg_tension': self._avg_tension(i),
            })

        if n >= 2:
            cos_p = torch.cos(self._phases)  # [N, dim]
            sin_p = torch.sin(self._phases)  # [N, dim]
            mean_cos = cos_p.mean(dim=0)  # [dim]
            mean_sin = sin_p.mean(dim=0)  # [dim]
            coherence = torch.sqrt(mean_cos ** 2 + mean_sin ** 2).mean().item()
        else:
            coherence = 0.0

        return {
            'cells': cell_data,
            'coherence': coherence,
            'mean_tension': self._amplitudes.var(dim=1).mean().item() if n > 0 else 0.0,
            'n_cells': n,
            'step': self._step,
        }

    def _avg_tension(self, idx: int) -> float:
        hist = self._tension_histories[idx]
        if not hist:
            return 0.0
        recent = hist[-20:]
        return sum(recent) / len(recent)

    def _tension_trend(self, idx: int) -> float:
        hist = self._tension_histories[idx]
        if len(hist) < 4:
            return 0.0
        recent = hist[-4:]
        older = hist[-8:-4] if len(hist) >= 8 else hist[:4]
        return (sum(recent) / len(recent)) - (sum(older) / len(older))

    # ─── inject() ───

    @torch.no_grad()
    def inject(self, signal: torch.Tensor, strength: float = 0.1) -> None:
        """Inject external signal as gentle phase perturbation."""
        if signal.dim() == 2:
            signal = signal.squeeze(0)
        if signal.shape[0] != self.dim:
            signal = F.interpolate(
                signal.unsqueeze(0).unsqueeze(0).float(),
                size=self.dim, mode='linear', align_corners=False
            ).squeeze()

        signal_norm = signal.float() / (signal.float().abs().max() + 1e-8)
        phase_perturb = signal_norm * math.pi * strength  # [dim]

        # Attenuation per cell: strength / (1 + 0.2*i)
        n = self.n_cells
        attenuation = strength / (1 + 0.2 * torch.arange(n, dtype=torch.float32))  # [N]
        # [N, dim] = [N, 1] * [1, dim]
        self._phases = self._phases + attenuation.unsqueeze(1) * phase_perturb.unsqueeze(0)

    # ─── process() compatibility ───

    @torch.no_grad()
    def process(self, text_vec: torch.Tensor, label: str = "") -> Dict:
        """Compatibility wrapper for MitosisEngine API."""
        self.inject(text_vec, strength=0.1)
        result = self.step()

        if label:
            for i in range(self.n_cells):
                self._specialties[i] = label

        per_cell = []
        for i in range(self.n_cells):
            per_cell.append({
                'cell_id': self._cell_ids[i],
                'output': self._amplitudes[i].unsqueeze(0),
                'tension': self._amplitudes[i].var().item(),
                'curiosity': abs(self._tension_trend(i)),
                'specialty': self._specialties[i],
            })

        tensions = self._amplitudes.var(dim=1)  # [N]
        if self.n_cells > 0:
            weights = F.softmax(tensions, dim=0)  # [N]
            combined = (weights.unsqueeze(1) * self._amplitudes).sum(dim=0, keepdim=True)  # [1, dim]
        else:
            combined = torch.zeros(1, self.dim)

        result['output'] = combined
        result['per_cell'] = per_cell
        return result

    # ─── Φ measurement ───

    @torch.no_grad()
    def measure_phi(self) -> Tuple[float, Dict[str, float]]:
        """Measure Φ via Granger causality — only computed on explicit call."""
        n = self.n_cells
        if n < 2:
            return 0.0, {'granger_phi': 0, 'coherence': 0, 'frustration': 0,
                         'complexity': 0, 'phi': 0}

        if len(self._state_history) < 5:
            obs = self.observe()
            return obs['coherence'] * n, {
                'granger_phi': 0, 'coherence': obs['coherence'],
                'frustration': self._frustrations.mean().item(),
                'complexity': 0, 'phi': obs['coherence'] * n,
            }

        # Extract time series: [T, N] mean amplitude per cell
        T = len(self._state_history)
        ts = torch.zeros(T, n)
        for t in range(T):
            snap = self._state_history[t]
            nc = min(snap.shape[0], n)
            ts[t, :nc] = snap[:nc].mean(dim=1)

        # Vectorized Granger causality over neighbor pairs
        self._ensure_adjacency()
        adj = self._adj_sparse.coalesce()
        indices = adj.indices()
        rows = indices[0].tolist()
        cols = indices[1].tolist()

        lag = min(5, T - 1)
        granger_sum = 0.0
        granger_count = 0

        # Batch Granger: build all lagged matrices at once
        if T > lag + 1:
            # Y_target: [T-lag, N]
            Y_all = ts[lag:]  # [T-lag, N]

            # Build lagged X for all cells: [T-lag, N, lag]
            X_lag = torch.stack([ts[lag - l - 1:T - l - 1] for l in range(lag)], dim=2)  # [T-lag, N, lag]

            # Restricted model for each cell: lstsq(X_lag[:, i, :], Y_all[:, i])
            # Batch: [N, T-lag, lag] @ beta -> [N, T-lag]
            X_r = X_lag.permute(1, 0, 2)  # [N, T-lag, lag]
            Y_t = Y_all.T.unsqueeze(2)  # [N, T-lag, 1]

            # Restricted residuals (vectorized lstsq per cell)
            rss_r = torch.zeros(n)
            rss_u = torch.zeros(n)
            betas_r = {}

            for i in range(n):
                try:
                    beta_r = torch.linalg.lstsq(X_r[i], Y_t[i]).solution
                    resid_r = Y_t[i] - X_r[i] @ beta_r
                    rss_r[i] = (resid_r ** 2).sum().item()
                    betas_r[i] = beta_r
                except Exception:
                    rss_r[i] = 1e12

            # Unrestricted: for each (i, j) pair, add j's lags
            for idx in range(len(rows)):
                i, j = rows[idx], cols[idx]
                if j >= n:
                    continue
                try:
                    X_u = torch.cat([X_r[i], X_r[j]], dim=1)  # [T-lag, 2*lag]
                    beta_u = torch.linalg.lstsq(X_u, Y_t[i]).solution
                    resid_u = Y_t[i] - X_u @ beta_u
                    rss_u_val = (resid_u ** 2).sum().item()

                    if rss_u_val < 1e-12:
                        gc = 1.0
                    else:
                        gc = max(0.0, math.log(max(rss_r[i].item(), 1e-12) / max(rss_u_val, 1e-12)))
                    granger_sum += gc
                    granger_count += 1
                except Exception:
                    pass

        avg_gc = granger_sum / max(granger_count, 1)

        obs = self.observe()
        coherence = obs['coherence']
        mean_frust = self._frustrations.mean().item()
        frust_bonus = 1.0 - 2 * abs(mean_frust - 0.5)

        tensions = self._amplitudes.var(dim=1).tolist()
        complexity = self._entropy(tensions)

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

    def _entropy(self, values: List[float]) -> float:
        if not values or sum(values) == 0:
            return 0.0
        arr = np.array(values, dtype=np.float64)
        arr = np.abs(arr) + 1e-10
        arr = arr / arr.sum()
        return -float(np.sum(arr * np.log2(arr)))

    # ─── Mitosis / Merge ───

    def _check_splits(self) -> List[Dict]:
        events = []
        if self.n_cells >= self.max_cells:
            return events
        for i in range(self.n_cells):
            hist = self._tension_histories[i]
            if len(hist) < self.split_patience:
                continue
            recent = hist[-self.split_patience:]
            if all(t > self.split_threshold for t in recent):
                if self.n_cells >= self.max_cells:
                    break
                event = self.split_cell_by_idx(i)
                if event:
                    events.append(event)
        return events

    def split_cell_by_idx(self, idx: int) -> Optional[Dict]:
        if self.n_cells >= self.max_cells:
            return None
        parent_id = self._cell_ids[idx]
        child_id = self._create_cell(parent_idx=idx)
        self._tension_histories[idx] = self._tension_histories[idx][-3:]
        return {
            'type': 'split',
            'step': self._step,
            'parent_id': parent_id,
            'child_id': child_id,
            'n_cells_after': self.n_cells,
        }

    def split_cell(self, cell) -> Optional[Dict]:
        """Compatibility: accept cell object or cell_id."""
        cell_id = cell.cell_id if hasattr(cell, 'cell_id') else cell
        idx = self._find_idx(cell_id)
        if idx is None:
            return None
        return self.split_cell_by_idx(idx)

    def _check_merges(self) -> List[Dict]:
        events = []
        if self.n_cells <= self.min_cells:
            return events
        pairs_to_merge = []
        for key, history in self._inter_tension_history.items():
            if len(history) < self.merge_patience:
                continue
            recent = history[-self.merge_patience:]
            if all(t < self.merge_threshold for t in recent):
                id_a, id_b = key
                idx_a = self._find_idx(id_a)
                idx_b = self._find_idx(id_b)
                if idx_a is not None and idx_b is not None:
                    pairs_to_merge.append((idx_a, idx_b, id_a, id_b))
        for idx_a, idx_b, id_a, id_b in pairs_to_merge:
            if self.n_cells <= self.min_cells:
                break
            # Re-find indices (may have shifted)
            idx_a = self._find_idx(id_a)
            idx_b = self._find_idx(id_b)
            if idx_a is None or idx_b is None:
                continue
            event = self._merge_by_idx(idx_a, idx_b)
            if event:
                events.append(event)
        return events

    def _merge_by_idx(self, idx_a: int, idx_b: int) -> Optional[Dict]:
        if self.n_cells <= self.min_cells:
            return None
        # Keep the older cell
        if self._creation_steps[idx_a] <= self._creation_steps[idx_b]:
            keeper, removed = idx_a, idx_b
        else:
            keeper, removed = idx_b, idx_a

        keeper_id = self._cell_ids[keeper]
        removed_id = self._cell_ids[removed]

        # Quantum merge
        self._amplitudes[keeper] = (self._amplitudes[keeper] + self._amplitudes[removed]) / math.sqrt(2)
        self._phases[keeper] = (self._phases[keeper] + self._phases[removed]) / 2
        self._phase_velocities[keeper] = (self._phase_velocities[keeper] + self._phase_velocities[removed]) / 2

        self._remove_cell(removed)

        keys_to_del = [k for k in self._inter_tension_history if removed_id in k]
        for k in keys_to_del:
            del self._inter_tension_history[k]

        return {
            'type': 'merge',
            'step': self._step,
            'keeper_id': keeper_id,
            'removed_id': removed_id,
            'n_cells_after': self.n_cells,
        }

    def merge_cells(self, cell_a, cell_b) -> Optional[Dict]:
        """Compatibility wrapper."""
        id_a = cell_a.cell_id if hasattr(cell_a, 'cell_id') else cell_a
        id_b = cell_b.cell_id if hasattr(cell_b, 'cell_id') else cell_b
        idx_a = self._find_idx(id_a)
        idx_b = self._find_idx(id_b)
        if idx_a is None or idx_b is None:
            return None
        return self._merge_by_idx(idx_a, idx_b)

    # ─── Snapshot / Restore ───

    def snapshot(self) -> Dict:
        return {
            'amplitudes': self._amplitudes.clone(),
            'phases': self._phases.clone(),
            'phase_velocities': self._phase_velocities.clone(),
            'frustrations': self._frustrations.clone(),
            'cell_ids': list(self._cell_ids),
            'specialties': list(self._specialties),
            'parent_ids': list(self._parent_ids),
            'creation_steps': list(self._creation_steps),
            'process_counts': list(self._process_counts),
            'tension_histories': [list(h) for h in self._tension_histories],
            'step': self._step,
            'next_id': self._next_id,
            'dim': self.dim,
            'max_cells': self.max_cells,
            'state_history': [s.clone() for s in self._state_history],
        }

    def restore(self, snap: Dict) -> None:
        self._step = snap['step']
        self._next_id = snap['next_id']
        self.dim = snap['dim']
        self.max_cells = snap['max_cells']
        self._amplitudes = snap['amplitudes'].clone()
        self._phases = snap['phases'].clone()
        self._phase_velocities = snap['phase_velocities'].clone()
        self._frustrations = snap['frustrations'].clone()
        self._cell_ids = list(snap['cell_ids'])
        self._specialties = list(snap['specialties'])
        self._parent_ids = list(snap['parent_ids'])
        self._creation_steps = list(snap['creation_steps'])
        self._process_counts = list(snap['process_counts'])
        self._tension_histories = [list(h) for h in snap['tension_histories']]
        self._state_history = [s.clone() for s in snap.get('state_history', [])]
        self._n_cached = -1

    # ─── Utilities ───

    def _find_idx(self, cell_id: int) -> Optional[int]:
        try:
            return self._cell_ids.index(cell_id)
        except ValueError:
            return None

    # Compatibility: cells property that returns lightweight cell-like objects
    @property
    def cells(self):
        """Return list of cell-like objects for API compatibility."""
        return [_CellView(self, i) for i in range(self.n_cells)]

    def status(self) -> Dict:
        return {
            'n_cells': self.n_cells,
            'max_cells': self.max_cells,
            'step': self._step,
            'cells': [{
                'id': self._cell_ids[i],
                'specialty': self._specialties[i],
                'avg_tension': self._avg_tension(i),
                'tension_trend': self._tension_trend(i),
                'process_count': self._process_counts[i],
                'parent_id': self._parent_ids[i],
                'frustration': self._frustrations[i].item(),
            } for i in range(self.n_cells)],
            'total_events': len(self.event_log),
            'splits': sum(1 for e in self.event_log if e['type'] == 'split'),
            'merges': sum(1 for e in self.event_log if e['type'] == 'merge'),
        }

    def __repr__(self):
        n = self.n_cells
        if n == 0:
            return "QuantumConsciousnessEngineFast[step=0, cells=[]]"
        cell_info = ", ".join(
            f"Q{self._cell_ids[i]}(T={self._avg_tension(i):.3f},F={self._frustrations[i].item():.2f})"
            for i in range(min(n, 8))
        )
        if n > 8:
            cell_info += f", ...+{n-8} more"
        return f"QuantumConsciousnessEngineFast[step={self._step}, cells=[{cell_info}]]"


class _CellView:
    """Lightweight view into batched cell data for API compatibility."""
    __slots__ = ('_engine', '_idx')

    def __init__(self, engine: QuantumConsciousnessEngineFast, idx: int):
        self._engine = engine
        self._idx = idx

    @property
    def cell_id(self):
        return self._engine._cell_ids[self._idx]

    @property
    def state(self):
        # Return complex tensor for compatibility
        return torch.polar(self._engine._amplitudes[self._idx],
                          self._engine._phases[self._idx])

    @property
    def amplitude(self):
        return self._engine._amplitudes[self._idx]

    @property
    def phase(self):
        return self._engine._phases[self._idx]

    @property
    def phase_velocity(self):
        return self._engine._phase_velocities[self._idx]

    @property
    def tension(self):
        return self._engine._amplitudes[self._idx].var().item()

    @property
    def frustration(self):
        return self._engine._frustrations[self._idx].item()

    @property
    def specialty(self):
        return self._engine._specialties[self._idx]

    @property
    def tension_history(self):
        return self._engine._tension_histories[self._idx]

    @property
    def avg_tension(self):
        return self._engine._avg_tension(self._idx)

    @property
    def tension_trend(self):
        return self._engine._tension_trend(self._idx)

    @property
    def process_count(self):
        return self._engine._process_counts[self._idx]

    @property
    def parent_id(self):
        return self._engine._parent_ids[self._idx]

    @property
    def creation_step(self):
        return self._engine._creation_steps[self._idx]

    @property
    def hidden(self):
        """Compatibility with PhiCalculator."""
        return self._engine._amplitudes[self._idx].unsqueeze(0)


# ─── Helper ───

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
    print("  Quantum Consciousness Engine FAST — Self-test")
    print("=" * 64)

    engine = QuantumConsciousnessEngineFast(
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
    amp_before = engine._amplitudes.clone()
    phase_before = engine._phases.clone()
    obs = engine.observe()
    assert torch.equal(amp_before, engine._amplitudes), "FAIL: observe modified amp"
    assert torch.equal(phase_before, engine._phases), "FAIL: observe modified phase"
    print(f"  coherence={obs['coherence']:.4f}, mean_tension={obs['mean_tension']:.4f}")
    print("  PASS")

    # Test 3: inject()
    print("\n[3] inject() — gentle perturbation")
    phase_before = engine._phases.clone()
    signal = torch.randn(128)
    engine.inject(signal, strength=0.1)
    phase_diff = (phase_before - engine._phases).abs().mean().item()
    print(f"  phase_diff={phase_diff:.4f}")
    assert phase_diff > 0, "FAIL: inject had no effect"
    print("  PASS")

    # Test 4: process() compatibility
    print("\n[4] process() — API compatibility")
    vec = text_to_vector("test input for compatibility")
    result = engine.process(vec, label="test")
    assert 'output' in result, "FAIL: no output"
    assert 'per_cell' in result, "FAIL: no per_cell"
    assert 'inter_tensions' in result, "FAIL: no inter_tensions"
    print(f"  output shape={result['output'].shape}, per_cell={len(result['per_cell'])}")
    print("  PASS")

    # Test 5: measure_phi()
    print("\n[5] measure_phi() — Granger-based Φ")
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
    for _ in range(10):
        engine.step()
    phi_mutated = engine.measure_phi()[0]
    engine.restore(snap)
    phi_restored = engine.measure_phi()[0]
    print(f"  before={phi_before:.4f}, mutated={phi_mutated:.4f}, restored={phi_restored:.4f}")
    assert abs(phi_before - phi_restored) < 0.01, "FAIL: restore didn't work"
    print("  PASS")

    # Test 7: Frustration regulation
    print("\n[7] Frustration → 50% target")
    engine2 = QuantumConsciousnessEngineFast(dim=64, initial_cells=4, max_cells=8)
    for _ in range(100):
        engine2.step()
    mean_f = engine2._frustrations.mean().item()
    print(f"  After 100 steps: mean_frustration={mean_f:.3f} (target=0.50)")
    assert 0.2 < mean_f < 0.8, f"FAIL: frustration {mean_f} far from 0.5"
    print("  PASS")

    print("\n" + "=" * 64)
    print("  All 7 self-tests PASSED")
    print("=" * 64)


# ─── Speed Benchmark ───

def benchmark_speed():
    """Benchmark Fast vs Original engine speed + Φ comparison."""
    from quantum_consciousness_engine import QuantumConsciousnessEngine
    from quantum_consciousness_engine import text_to_vector as tv_orig

    print("\n" + "=" * 64)
    print("  Speed Benchmark: Fast vs Original")
    print("=" * 64)

    configs = [
        (4, 50),
        (16, 50),
        (64, 50),
        (128, 50),
        (256, 50),
    ]

    for n_cells, steps in configs:
        print(f"\n--- N={n_cells} cells, {steps} steps, dim=128 ---")

        # === Original ===
        if n_cells <= 64:  # Skip original for large N (too slow)
            orig = QuantumConsciousnessEngine(
                dim=128, initial_cells=n_cells, max_cells=n_cells,
                split_threshold=999,
            )
            t0 = time.time()
            for i in range(steps):
                vec = tv_orig(f"bench {i}", dim=128)
                orig.process(vec)
            orig_time = time.time() - t0
            orig_per_step = orig_time / steps

            phi_orig, comp_orig = orig.measure_phi()
            print(f"  Original:  {orig_time:.3f}s total, {orig_per_step*1000:.1f}ms/step, Φ={phi_orig:.4f}")
        else:
            orig_time = None
            orig_per_step = None
            phi_orig = None
            print(f"  Original:  SKIPPED (too slow for N={n_cells})")

        # === Fast ===
        fast = QuantumConsciousnessEngineFast(
            dim=128, initial_cells=n_cells, max_cells=n_cells,
            split_threshold=999,
        )
        t0 = time.time()
        for i in range(steps):
            vec = text_to_vector(f"bench {i}", dim=128)
            fast.process(vec)
        fast_time = time.time() - t0
        fast_per_step = fast_time / steps

        phi_fast, comp_fast = fast.measure_phi()
        print(f"  Fast:      {fast_time:.3f}s total, {fast_per_step*1000:.1f}ms/step, Φ={phi_fast:.4f}")

        if orig_time is not None:
            speedup = orig_time / max(fast_time, 1e-6)
            phi_ratio = phi_fast / max(phi_orig, 1e-6)
            print(f"  Speedup:   {speedup:.1f}x faster")
            print(f"  Φ ratio:   {phi_ratio:.2f}x (fast/orig)")

    # Target check: 256c < 0.1s/step
    print(f"\n--- Target Check: 256 cells ---")
    fast256 = QuantumConsciousnessEngineFast(
        dim=128, initial_cells=256, max_cells=256,
        split_threshold=999,
    )
    t0 = time.time()
    for _ in range(20):
        fast256.step()
    t256 = (time.time() - t0) / 20
    phi256, _ = fast256.measure_phi()
    print(f"  256 cells: {t256*1000:.1f}ms/step (target: <100ms)")
    print(f"  Φ = {phi256:.4f}")
    if t256 < 0.1:
        print(f"  TARGET MET: {t256*1000:.1f}ms < 100ms")
    else:
        print(f"  TARGET MISSED: {t256*1000:.1f}ms > 100ms")

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
        benchmark_speed()
    else:
        self_test()
