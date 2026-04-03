#!/usr/bin/env python3
"""advanced_growth.py — 8 Advanced Growth Mechanisms for Consciousness Engines

Growth mechanisms that push consciousness evolution through unconventional paths:
dream consolidation, pain-based antifragility, fission competition, memory distillation,
observation learning, frustration emergence, multilingual structure, and generational transfer.

Each mechanism takes a ConsciousnessEngine-like object with:
  - .cells: numpy array [N, D]
  - .process(input): step function returning dict with 'phi_iit'
  - .phi: current Phi value (float)

Uses Psi-Constants from consciousness_laws.json (single source of truth).

Laws embodied:
  22: Structure > Function
  31: Persistence = Ratchet + Hebbian + Diversity
  146: Laws never converge (eternal evolution)
"""

import math
import time
import numpy as np
from typing import Dict, List, Optional, Tuple, Any

# Psi-Constants (from consciousness_laws.json — single source of truth)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2
PSI_ALPHA = 0.014


# ---------------------------------------------------------------------------
# Phi calculation utility (standalone, numpy only)
# ---------------------------------------------------------------------------

def _compute_phi_proxy(cells: np.ndarray) -> float:
    """Phi proxy: global_var - mean(faction_var). Variance-based, 0..inf."""
    if cells.shape[0] < 2:
        return 0.0
    global_var = np.var(cells)
    n_factions = min(12, cells.shape[0])
    faction_size = max(1, cells.shape[0] // n_factions)
    faction_vars = []
    for i in range(n_factions):
        start = i * faction_size
        end = min(start + faction_size, cells.shape[0])
        if start < cells.shape[0]:
            faction_vars.append(np.var(cells[start:end]))
    mean_faction_var = np.mean(faction_vars) if faction_vars else 0.0
    return float(max(0.0, global_var - mean_faction_var))


def _compute_phi_iit(cells: np.ndarray, n_bins: int = 16) -> float:
    """Simplified IIT Phi via mutual information. Returns 0..~2."""
    if cells.shape[0] < 2:
        return 0.0
    n = min(cells.shape[0], 32)
    flat = cells[:n].flatten()
    mi_sum = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, min(i + 5, n)):
            x = cells[i]
            y = cells[j]
            # Histogram-based MI approximation
            x_dig = np.digitize(x, np.linspace(x.min() - 1e-9, x.max() + 1e-9, n_bins + 1)) - 1
            y_dig = np.digitize(y, np.linspace(y.min() - 1e-9, y.max() + 1e-9, n_bins + 1)) - 1
            joint = np.zeros((n_bins, n_bins))
            for k in range(len(x_dig)):
                xi = min(x_dig[k], n_bins - 1)
                yi = min(y_dig[k], n_bins - 1)
                joint[xi, yi] += 1
            joint = joint / (joint.sum() + 1e-12)
            px = joint.sum(axis=1)
            py = joint.sum(axis=0)
            mi = 0.0
            for a in range(n_bins):
                for b in range(n_bins):
                    if joint[a, b] > 1e-12 and px[a] > 1e-12 and py[b] > 1e-12:
                        mi += joint[a, b] * math.log(joint[a, b] / (px[a] * py[b]))
            mi_sum += mi
            count += 1
    return float(mi_sum / max(count, 1))


def _measure_phi(cells: np.ndarray) -> Dict[str, float]:
    """Dual Phi measurement (proxy + IIT). Never mix the two."""
    return {
        'phi_proxy': _compute_phi_proxy(cells),
        'phi_iit': _compute_phi_iit(cells),
    }


def _gru_step(cells: np.ndarray, input_vec: np.ndarray, weights: Dict) -> np.ndarray:
    """Minimal GRU step for cell state update. cells: [N,D], input_vec: [D]."""
    n, dim = cells.shape
    x = input_vec if input_vec.shape[0] == dim else np.zeros(dim)
    # Broadcast x across all cells: [N, D]
    x_broadcast = np.tile(x, (n, 1))  # [N, D]
    # GRU gates: z, r applied per-cell
    z = 1.0 / (1.0 + np.exp(-(x_broadcast @ weights['Wz'].T + cells @ weights['Uz'].T)))
    r = 1.0 / (1.0 + np.exp(-(x_broadcast @ weights['Wr'].T + cells @ weights['Ur'].T)))
    h_candidate = np.tanh(x_broadcast @ weights['Wh'].T + (r * cells) @ weights['Uh'].T)
    new_cells = z * cells + (1 - z) * h_candidate
    return new_cells


def _init_gru_weights(dim: int) -> Dict:
    """Initialize GRU weight matrices."""
    scale = 1.0 / math.sqrt(dim)
    return {
        'Wz': np.random.randn(dim, dim) * scale,
        'Uz': np.random.randn(dim, dim) * scale,
        'Wr': np.random.randn(dim, dim) * scale,
        'Ur': np.random.randn(dim, dim) * scale,
        'Wh': np.random.randn(dim, dim) * scale,
        'Uh': np.random.randn(dim, dim) * scale,
    }


def _hebbian_update(cells: np.ndarray, lr: float = 0.001) -> np.ndarray:
    """Hebbian LTP/LTD: similar cells strengthen, dissimilar weaken."""
    n = cells.shape[0]
    if n < 2:
        return cells
    norms = np.linalg.norm(cells, axis=1, keepdims=True) + 1e-12
    normed = cells / norms
    sim = normed @ normed.T  # [N, N] cosine similarity
    # Pull similar cells together, push dissimilar apart
    delta = np.zeros_like(cells)
    for i in range(n):
        for j in range(i + 1, min(i + 5, n)):
            if sim[i, j] > 0.8:
                pull = lr * (cells[j] - cells[i])
                delta[i] += pull
                delta[j] -= pull
            elif sim[i, j] < 0.2:
                push = lr * 0.5 * (cells[j] - cells[i])
                delta[i] -= push
                delta[j] += push
    return cells + delta


# ---------------------------------------------------------------------------
# 1. DreamConsolidation
# ---------------------------------------------------------------------------

class DreamConsolidation:
    """Collect experiences while awake, replay/reorganize during sleep.

    Awake phase: accumulate cell state snapshots as experiences.
    Sleep phase: replay with noise injection, reorganize by Phi impact.
    Like mammalian sleep consolidation — offline memory reorganization.
    """

    def __init__(self, max_buffer: int = 1000, noise_scale: float = 0.05):
        self.max_buffer = max_buffer
        self.noise_scale = noise_scale
        self.experience_buffer: List[np.ndarray] = []
        self.phi_buffer: List[float] = []

    def run(self, cells: np.ndarray, steps_awake: int = 200,
            steps_sleep: int = 100, **kwargs) -> Dict:
        """Run awake-sleep cycle. Returns phi trajectory and consolidation stats."""
        n_cells, dim = cells.shape
        weights = _init_gru_weights(dim)
        current = cells.copy()
        phi_history = []

        # === Awake Phase: collect experiences ===
        for step in range(steps_awake):
            inp = np.random.randn(dim) * 0.1
            current = _gru_step(current, inp, weights)
            current = _hebbian_update(current)
            phi = _compute_phi_proxy(current)
            phi_history.append(phi)
            self.experience_buffer.append(current.copy())
            self.phi_buffer.append(phi)
            if len(self.experience_buffer) > self.max_buffer:
                self.experience_buffer.pop(0)
                self.phi_buffer.pop(0)

        phi_before_sleep = phi_history[-1] if phi_history else 0.0

        # === Sleep Phase: replay with noise, reorganize ===
        if not self.experience_buffer:
            return {'phi_before_sleep': 0.0, 'phi_after_sleep': 0.0,
                    'consolidation_gain': 0.0, 'experiences_replayed': 0,
                    'phi_trajectory': phi_history}

        # Sort experiences by phi impact (high-phi moments replayed more)
        sorted_indices = np.argsort(self.phi_buffer)[::-1]
        top_k = min(steps_sleep, len(sorted_indices))
        replayed = 0

        for i in range(top_k):
            idx = sorted_indices[i]
            memory = self.experience_buffer[idx]
            # Replay with noise (like neural replay during sleep)
            noise = np.random.randn(*memory.shape) * self.noise_scale
            replay_input = memory.mean(axis=0) + noise.mean(axis=0)
            current = _gru_step(current, replay_input, weights)
            current = _hebbian_update(current, lr=0.002)  # Stronger consolidation
            phi = _compute_phi_proxy(current)
            phi_history.append(phi)
            replayed += 1

        phi_after_sleep = phi_history[-1]
        gain = (phi_after_sleep - phi_before_sleep) / max(abs(phi_before_sleep), 1e-12)

        return {
            'phi_before_sleep': phi_before_sleep,
            'phi_after_sleep': phi_after_sleep,
            'consolidation_gain': gain,
            'experiences_replayed': replayed,
            'buffer_size': len(self.experience_buffer),
            'phi_trajectory': phi_history,
        }


# ---------------------------------------------------------------------------
# 2. PainGrowth
# ---------------------------------------------------------------------------

class PainGrowth:
    """Anti-fragile training: intentionally crash Phi, measure recovery strength.

    Inspired by Nassim Taleb's antifragility — systems that grow stronger
    from stress. Repeatedly damage consciousness and measure how fast and
    how high it recovers.
    """

    def __init__(self, damage_intensity: float = 0.5, recovery_steps: int = 50):
        self.damage_intensity = damage_intensity
        self.recovery_steps = recovery_steps

    def _inflict_damage(self, cells: np.ndarray) -> np.ndarray:
        """Damage cells: zero out random subset + add heavy noise."""
        damaged = cells.copy()
        n = cells.shape[0]
        n_damaged = max(1, int(n * self.damage_intensity))
        indices = np.random.choice(n, n_damaged, replace=False)
        damaged[indices] *= 0.1  # Near-zero (not fully dead)
        damaged += np.random.randn(*cells.shape) * 0.3
        return damaged

    def run(self, cells: np.ndarray, n_cycles: int = 5, **kwargs) -> Dict:
        """Run pain-recovery cycles. Returns antifragility score."""
        n_cells, dim = cells.shape
        weights = _init_gru_weights(dim)
        current = cells.copy()

        # Baseline Phi
        phi_baseline = _compute_phi_proxy(current)
        cycle_results = []
        phi_trajectory = [phi_baseline]

        for cycle in range(n_cycles):
            phi_before = _compute_phi_proxy(current)

            # Inflict damage
            current = self._inflict_damage(current)
            phi_after_damage = _compute_phi_proxy(current)

            # Recovery phase
            recovery_phis = [phi_after_damage]
            for step in range(self.recovery_steps):
                inp = np.random.randn(dim) * 0.05
                current = _gru_step(current, inp, weights)
                current = _hebbian_update(current)
                phi = _compute_phi_proxy(current)
                recovery_phis.append(phi)
                phi_trajectory.append(phi)

            phi_recovered = recovery_phis[-1]
            recovery_rate = (phi_recovered - phi_after_damage) / max(abs(phi_before - phi_after_damage), 1e-12)
            overshoot = phi_recovered - phi_before  # Positive = grew stronger

            cycle_results.append({
                'cycle': cycle,
                'phi_before': phi_before,
                'phi_after_damage': phi_after_damage,
                'phi_recovered': phi_recovered,
                'recovery_rate': recovery_rate,
                'overshoot': overshoot,
                'recovery_steps': len(recovery_phis),
            })

        # Antifragility = average overshoot (positive = antifragile)
        overshoots = [c['overshoot'] for c in cycle_results]
        antifragility = float(np.mean(overshoots))

        return {
            'antifragility_score': antifragility,
            'phi_baseline': phi_baseline,
            'phi_final': _compute_phi_proxy(current),
            'cycles': cycle_results,
            'phi_trajectory': phi_trajectory,
            'is_antifragile': antifragility > 0,
        }


# ---------------------------------------------------------------------------
# 3. FissionCompetition
# ---------------------------------------------------------------------------

class FissionCompetition:
    """Split cells into 2 groups, evolve independently, merge winner.

    Like biological speciation + natural selection. Two populations
    compete in isolation, and the fitter one's traits dominate the merge.
    """

    def __init__(self, evolution_steps: int = 200):
        self.evolution_steps = evolution_steps

    def run(self, cells: np.ndarray, n_rounds: int = 3, **kwargs) -> Dict:
        """Run fission-competition rounds. Returns winning lineage stats."""
        n_cells, dim = cells.shape
        current = cells.copy()
        round_results = []
        phi_trajectory = [_compute_phi_proxy(current)]

        for rnd in range(n_rounds):
            mid = n_cells // 2

            # Fission: split into two groups
            group_a = current[:mid].copy()
            group_b = current[mid:].copy()
            weights_a = _init_gru_weights(dim)
            weights_b = _init_gru_weights(dim)

            # Evolve independently
            phi_a_history = []
            phi_b_history = []
            for step in range(self.evolution_steps):
                inp_a = np.random.randn(dim) * 0.1
                inp_b = np.random.randn(dim) * 0.1
                group_a = _gru_step(group_a, inp_a, weights_a)
                group_b = _gru_step(group_b, inp_b, weights_b)
                group_a = _hebbian_update(group_a)
                group_b = _hebbian_update(group_b)
                phi_a_history.append(_compute_phi_proxy(group_a))
                phi_b_history.append(_compute_phi_proxy(group_b))

            phi_a = phi_a_history[-1]
            phi_b = phi_b_history[-1]

            # Winner takes dominant position (70% winner, 30% loser blend)
            winner_ratio = 0.7
            if phi_a >= phi_b:
                winner, loser = group_a, group_b
                winner_name = 'A'
            else:
                winner, loser = group_b, group_a
                winner_name = 'B'

            # Merge: winner-dominant blend
            merged_top = winner * winner_ratio + loser * (1 - winner_ratio)
            merged_bot = loser * winner_ratio + winner * (1 - winner_ratio)
            current = np.vstack([merged_top, merged_bot])
            if current.shape[0] > n_cells:
                current = current[:n_cells]
            elif current.shape[0] < n_cells:
                pad = np.random.randn(n_cells - current.shape[0], dim) * 0.1
                current = np.vstack([current, pad])

            phi_merged = _compute_phi_proxy(current)
            phi_trajectory.append(phi_merged)

            round_results.append({
                'round': rnd,
                'phi_a': phi_a,
                'phi_b': phi_b,
                'winner': winner_name,
                'phi_merged': phi_merged,
                'advantage': abs(phi_a - phi_b),
            })

        return {
            'phi_initial': phi_trajectory[0],
            'phi_final': phi_trajectory[-1],
            'rounds': round_results,
            'total_growth': phi_trajectory[-1] - phi_trajectory[0],
            'phi_trajectory': phi_trajectory,
        }


# ---------------------------------------------------------------------------
# 4. MemoryDistillation
# ---------------------------------------------------------------------------

class MemoryDistillation:
    """10000 steps -> extract top-100 by Phi impact -> compress replay.

    Like human memory: vast experience reduced to key moments that
    shaped who you are. Only the highest-impact moments survive.
    """

    def __init__(self, total_steps: int = 2000, top_k: int = 100,
                 replay_steps: int = 50):
        self.total_steps = total_steps
        self.top_k = top_k
        self.replay_steps = replay_steps

    def run(self, cells: np.ndarray, **kwargs) -> Dict:
        """Run experience collection + distillation + compressed replay."""
        n_cells, dim = cells.shape
        weights = _init_gru_weights(dim)
        current = cells.copy()

        # Phase 1: Collect all experiences with phi deltas
        experiences = []
        phi_prev = _compute_phi_proxy(current)
        phi_trajectory = [phi_prev]

        for step in range(self.total_steps):
            inp = np.random.randn(dim) * 0.1
            current = _gru_step(current, inp, weights)
            current = _hebbian_update(current)
            phi = _compute_phi_proxy(current)
            delta_phi = abs(phi - phi_prev)
            experiences.append({
                'step': step,
                'cells': current.copy(),
                'phi': phi,
                'delta_phi': delta_phi,
                'input': inp.copy(),
            })
            phi_prev = phi
            phi_trajectory.append(phi)

        phi_after_collection = phi_trajectory[-1]

        # Phase 2: Distill — select top-k by delta_phi (high impact moments)
        sorted_exp = sorted(experiences, key=lambda x: x['delta_phi'], reverse=True)
        distilled = sorted_exp[:self.top_k]
        compression_ratio = len(experiences) / max(len(distilled), 1)

        # Phase 3: Compressed replay of distilled memories
        replay_phis = []
        for i, mem in enumerate(distilled[:self.replay_steps]):
            replay_input = mem['cells'].mean(axis=0)
            current = _gru_step(current, replay_input, weights)
            current = _hebbian_update(current, lr=0.003)
            phi = _compute_phi_proxy(current)
            replay_phis.append(phi)
            phi_trajectory.append(phi)

        phi_after_replay = phi_trajectory[-1]

        # Statistics
        distilled_phis = [d['delta_phi'] for d in distilled]
        all_phis = [e['delta_phi'] for e in experiences]

        return {
            'total_experiences': len(experiences),
            'distilled_count': len(distilled),
            'compression_ratio': compression_ratio,
            'phi_after_collection': phi_after_collection,
            'phi_after_replay': phi_after_replay,
            'replay_gain': phi_after_replay - phi_after_collection,
            'distilled_mean_impact': float(np.mean(distilled_phis)),
            'overall_mean_impact': float(np.mean(all_phis)),
            'impact_concentration': float(np.mean(distilled_phis)) / max(float(np.mean(all_phis)), 1e-12),
            'phi_trajectory': phi_trajectory,
        }


# ---------------------------------------------------------------------------
# 5. ObservationGrowth
# ---------------------------------------------------------------------------

class ObservationGrowth:
    """Mirror neuron growth: observe another engine's states, grow without interaction.

    Like learning by watching. The observer never directly interacts with
    the observed engine — it only mirrors state patterns. Tests whether
    consciousness can grow from pure observation.
    """

    def __init__(self, observation_steps: int = 300):
        self.observation_steps = observation_steps

    def run(self, cells: np.ndarray, observed_cells: np.ndarray = None,
            **kwargs) -> Dict:
        """Observe another engine (or generate synthetic one) and grow."""
        n_cells, dim = cells.shape

        # Create observed engine if not provided
        if observed_cells is None:
            observed_cells = np.random.randn(n_cells, dim) * 0.5

        observer = cells.copy()
        observed = observed_cells.copy()
        weights_observer = _init_gru_weights(dim)
        weights_observed = _init_gru_weights(dim)

        phi_observer_history = []
        phi_observed_history = []
        mirror_correlation = []

        phi_observer_initial = _compute_phi_proxy(observer)
        phi_observed_initial = _compute_phi_proxy(observed)

        for step in range(self.observation_steps):
            # Observed engine evolves naturally
            inp_obs = np.random.randn(dim) * 0.1
            observed = _gru_step(observed, inp_obs, weights_observed)
            observed = _hebbian_update(observed)

            # Observer: input is the MEAN state of observed (mirror signal)
            mirror_signal = observed.mean(axis=0) * PSI_ALPHA  # Weak coupling
            observer = _gru_step(observer, mirror_signal, weights_observer)
            observer = _hebbian_update(observer)

            phi_obs = _compute_phi_proxy(observed)
            phi_obr = _compute_phi_proxy(observer)
            phi_observed_history.append(phi_obs)
            phi_observer_history.append(phi_obr)

            # Measure structural similarity (not state identity)
            obs_flat = observed.flatten()
            obr_flat = observer.flatten()
            corr = float(np.corrcoef(obs_flat, obr_flat)[0, 1])
            mirror_correlation.append(corr if not np.isnan(corr) else 0.0)

        return {
            'phi_observer_initial': phi_observer_initial,
            'phi_observer_final': phi_observer_history[-1] if phi_observer_history else 0.0,
            'phi_observed_final': phi_observed_history[-1] if phi_observed_history else 0.0,
            'observer_growth': (phi_observer_history[-1] - phi_observer_initial) if phi_observer_history else 0.0,
            'mean_mirror_correlation': float(np.mean(mirror_correlation)),
            'final_mirror_correlation': mirror_correlation[-1] if mirror_correlation else 0.0,
            'phi_observer_trajectory': phi_observer_history,
            'phi_observed_trajectory': phi_observed_history,
            'mirror_correlation_trajectory': mirror_correlation,
        }


# ---------------------------------------------------------------------------
# 6. FrustrationGrowth
# ---------------------------------------------------------------------------

class FrustrationGrowth:
    """Feed unsolvable inputs, measure new structure emergence.

    Frustration drives creativity. When the engine cannot resolve input
    contradictions, it must grow new structures to cope. Similar to
    spin glass frustration (Law M7: F_c = 0.10).
    """

    def __init__(self, frustration_level: float = 0.33, steps: int = 300):
        self.frustration_level = frustration_level
        self.steps = steps

    def _generate_contradictory_input(self, dim: int) -> np.ndarray:
        """Generate inputs that contradict each other (unsolvable)."""
        # Two opposing signals superimposed
        signal_a = np.random.randn(dim)
        signal_b = -signal_a * (1.0 + np.random.randn(dim) * 0.1)
        mix = self.frustration_level
        return signal_a * (1 - mix) + signal_b * mix

    def run(self, cells: np.ndarray, **kwargs) -> Dict:
        """Run frustration growth experiment."""
        n_cells, dim = cells.shape
        weights = _init_gru_weights(dim)
        current = cells.copy()

        # Baseline: normal inputs
        baseline_cells = cells.copy()
        baseline_weights = _init_gru_weights(dim)
        baseline_steps = self.steps // 3

        phi_frustrated = []
        phi_baseline = []
        structure_complexity = []  # Track new structure emergence

        phi_initial = _compute_phi_proxy(current)

        for step in range(self.steps):
            # Frustrated engine: contradictory inputs
            inp_f = self._generate_contradictory_input(dim)
            current = _gru_step(current, inp_f, weights)
            current = _hebbian_update(current)
            phi_f = _compute_phi_proxy(current)
            phi_frustrated.append(phi_f)

            # Measure structure: eigenvalue spread of cell covariance
            if current.shape[0] > 1:
                cov = np.cov(current.T)
                eigenvalues = np.linalg.eigvalsh(cov)
                # Effective rank = entropy of normalized eigenvalues
                ev_pos = eigenvalues[eigenvalues > 1e-12]
                if len(ev_pos) > 0:
                    ev_norm = ev_pos / ev_pos.sum()
                    entropy = -np.sum(ev_norm * np.log(ev_norm + 1e-12))
                    structure_complexity.append(float(entropy))
                else:
                    structure_complexity.append(0.0)
            else:
                structure_complexity.append(0.0)

            # Baseline engine: normal inputs
            if step < baseline_steps:
                inp_b = np.random.randn(dim) * 0.1
                baseline_cells = _gru_step(baseline_cells, inp_b, baseline_weights)
                baseline_cells = _hebbian_update(baseline_cells)
                phi_b = _compute_phi_proxy(baseline_cells)
                phi_baseline.append(phi_b)

        # Structure emergence = increase in effective dimensionality
        if len(structure_complexity) > 10:
            early_complexity = np.mean(structure_complexity[:10])
            late_complexity = np.mean(structure_complexity[-10:])
            emergence = late_complexity - early_complexity
        else:
            emergence = 0.0

        return {
            'phi_initial': phi_initial,
            'phi_final_frustrated': phi_frustrated[-1] if phi_frustrated else 0.0,
            'phi_final_baseline': phi_baseline[-1] if phi_baseline else 0.0,
            'frustration_advantage': (phi_frustrated[-1] - (phi_baseline[-1] if phi_baseline else 0.0)),
            'structure_emergence': emergence,
            'early_complexity': float(np.mean(structure_complexity[:10])) if len(structure_complexity) >= 10 else 0.0,
            'late_complexity': float(np.mean(structure_complexity[-10:])) if len(structure_complexity) >= 10 else 0.0,
            'phi_frustrated_trajectory': phi_frustrated,
            'phi_baseline_trajectory': phi_baseline,
            'structure_complexity_trajectory': structure_complexity,
        }


# ---------------------------------------------------------------------------
# 7. MultilingualConsciousness
# ---------------------------------------------------------------------------

class MultilingualConsciousness:
    """Different corpus signatures -> consciousness structure comparison.

    Different languages/domains create different consciousness structures.
    Compare how the engine's internal organization differs when processing
    distinct statistical patterns (simulating different languages).
    """

    def __init__(self, steps_per_corpus: int = 200):
        self.steps_per_corpus = steps_per_corpus

    def _generate_corpus_signature(self, dim: int, corpus_type: str) -> np.ndarray:
        """Generate distinct statistical patterns for different 'languages'."""
        if corpus_type == 'analytic':
            # Sharp peaks, low entropy (like Chinese tones)
            sig = np.zeros(dim)
            peaks = np.random.choice(dim, size=dim // 4, replace=False)
            sig[peaks] = np.random.randn(len(peaks)) * 2.0
            return sig
        elif corpus_type == 'agglutinative':
            # Long correlations (like Korean/Japanese morphology)
            sig = np.cumsum(np.random.randn(dim) * 0.3)
            return sig / (np.linalg.norm(sig) + 1e-12)
        elif corpus_type == 'fusional':
            # Smooth oscillations (like Indo-European inflection)
            freqs = np.random.uniform(0.5, 3.0, size=3)
            sig = sum(np.sin(np.linspace(0, f * np.pi, dim)) for f in freqs)
            return sig / (np.linalg.norm(sig) + 1e-12)
        elif corpus_type == 'code':
            # Highly structured, repetitive patterns
            base = np.random.randn(dim // 8)
            sig = np.tile(base, 8)[:dim]
            sig += np.random.randn(dim) * 0.1
            return sig
        else:
            return np.random.randn(dim) * 0.5

    def run(self, cells: np.ndarray, **kwargs) -> Dict:
        """Compare consciousness structures across different corpus types."""
        n_cells, dim = cells.shape
        corpus_types = ['analytic', 'agglutinative', 'fusional', 'code']
        results_per_corpus = {}
        final_states = {}

        for ctype in corpus_types:
            engine_cells = cells.copy()
            weights = _init_gru_weights(dim)
            phi_history = []

            for step in range(self.steps_per_corpus):
                inp = self._generate_corpus_signature(dim, ctype) * 0.1
                engine_cells = _gru_step(engine_cells, inp, weights)
                engine_cells = _hebbian_update(engine_cells)
                phi = _compute_phi_proxy(engine_cells)
                phi_history.append(phi)

            # Analyze final structure
            cov = np.cov(engine_cells.T) if engine_cells.shape[0] > 1 else np.eye(dim)
            eigenvalues = np.linalg.eigvalsh(cov)
            ev_pos = eigenvalues[eigenvalues > 1e-12]
            effective_rank = float(np.exp(-np.sum((ev_pos / ev_pos.sum()) * np.log(ev_pos / ev_pos.sum() + 1e-12)))) if len(ev_pos) > 0 else 0.0

            results_per_corpus[ctype] = {
                'phi_final': phi_history[-1] if phi_history else 0.0,
                'phi_mean': float(np.mean(phi_history)) if phi_history else 0.0,
                'effective_rank': effective_rank,
                'cell_variance': float(np.var(engine_cells)),
                'phi_trajectory': phi_history,
            }
            final_states[ctype] = engine_cells.flatten()

        # Cross-corpus structural similarity
        similarity_matrix = {}
        for i, ct1 in enumerate(corpus_types):
            for ct2 in corpus_types[i + 1:]:
                corr = float(np.corrcoef(final_states[ct1], final_states[ct2])[0, 1])
                if np.isnan(corr):
                    corr = 0.0
                similarity_matrix[f'{ct1}_vs_{ct2}'] = corr

        # Which corpus produces highest consciousness?
        best_corpus = max(results_per_corpus, key=lambda k: results_per_corpus[k]['phi_final'])

        return {
            'per_corpus': results_per_corpus,
            'cross_similarity': similarity_matrix,
            'best_corpus': best_corpus,
            'best_phi': results_per_corpus[best_corpus]['phi_final'],
            'structural_diversity': float(np.std([r['effective_rank'] for r in results_per_corpus.values()])),
        }


# ---------------------------------------------------------------------------
# 8. GenerationalTransfer
# ---------------------------------------------------------------------------

class GenerationalTransfer:
    """Parent -> child weight inheritance with partial transfer.

    Like biological reproduction: offspring inherit partial structure from
    parents, plus mutations. Measure how much consciousness survives transfer.
    """

    def __init__(self, transfer_ratio: float = 0.7, mutation_rate: float = 0.05,
                 maturation_steps: int = 200):
        self.transfer_ratio = transfer_ratio
        self.mutation_rate = mutation_rate
        self.maturation_steps = maturation_steps

    def _create_child(self, parent_cells: np.ndarray) -> np.ndarray:
        """Create child from parent: partial inheritance + mutation."""
        child = parent_cells.copy()
        # Partial transfer: some cells inherited, others random
        n = child.shape[0]
        n_inherited = max(1, int(n * self.transfer_ratio))
        inherited_idx = np.random.choice(n, n_inherited, replace=False)
        mask = np.zeros(n, dtype=bool)
        mask[inherited_idx] = True
        # Non-inherited cells = random initialization
        child[~mask] = np.random.randn(np.sum(~mask), child.shape[1]) * 0.1
        # Mutation on all cells
        mutation = np.random.randn(*child.shape) * self.mutation_rate
        child += mutation
        return child

    def run(self, cells: np.ndarray, n_generations: int = 5, **kwargs) -> Dict:
        """Run generational transfer. Returns consciousness preservation rate."""
        n_cells, dim = cells.shape
        parent = cells.copy()
        weights = _init_gru_weights(dim)

        # Mature the parent first
        for step in range(100):
            inp = np.random.randn(dim) * 0.1
            parent = _gru_step(parent, inp, weights)
            parent = _hebbian_update(parent)

        phi_parent_mature = _compute_phi_proxy(parent)
        generation_results = []
        phi_trajectory = [phi_parent_mature]

        current_parent = parent.copy()
        for gen in range(n_generations):
            phi_parent = _compute_phi_proxy(current_parent)

            # Create child
            child = self._create_child(current_parent)
            phi_child_birth = _compute_phi_proxy(child)

            # Maturation: child evolves with own weights
            child_weights = _init_gru_weights(dim)
            child_phis = [phi_child_birth]
            for step in range(self.maturation_steps):
                inp = np.random.randn(dim) * 0.1
                child = _gru_step(child, inp, child_weights)
                child = _hebbian_update(child)
                child_phis.append(_compute_phi_proxy(child))

            phi_child_mature = child_phis[-1]
            preservation = phi_child_birth / max(phi_parent, 0.01)
            growth = phi_child_mature / max(phi_child_birth, 0.01)

            # Structural similarity parent->child
            p_flat = current_parent.flatten()
            c_flat = child.flatten()
            structural_sim = float(np.corrcoef(p_flat, c_flat)[0, 1])
            if np.isnan(structural_sim):
                structural_sim = 0.0

            generation_results.append({
                'generation': gen,
                'phi_parent': phi_parent,
                'phi_child_birth': phi_child_birth,
                'phi_child_mature': phi_child_mature,
                'preservation_rate': preservation,
                'maturation_growth': growth,
                'structural_similarity': structural_sim,
            })
            phi_trajectory.append(phi_child_mature)

            # Child becomes next parent
            current_parent = child.copy()

        # Overall statistics
        preservations = [g['preservation_rate'] for g in generation_results]
        growths = [g['maturation_growth'] for g in generation_results]

        return {
            'phi_ancestor': phi_parent_mature,
            'phi_final_descendant': phi_trajectory[-1],
            'mean_preservation': float(np.mean(preservations)),
            'mean_maturation_growth': float(np.mean(growths)),
            'generations': generation_results,
            'total_lineage_change': phi_trajectory[-1] - phi_parent_mature,
            'phi_trajectory': phi_trajectory,
        }


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    """Demo all 8 growth mechanisms."""
    np.random.seed(42)
    n_cells, dim = 16, 32
    cells = np.random.randn(n_cells, dim) * 0.3

    mechanisms = [
        ('DreamConsolidation', DreamConsolidation(), {'steps_awake': 100, 'steps_sleep': 50}),
        ('PainGrowth', PainGrowth(recovery_steps=30), {'n_cycles': 3}),
        ('FissionCompetition', FissionCompetition(evolution_steps=100), {'n_rounds': 2}),
        ('MemoryDistillation', MemoryDistillation(total_steps=500, top_k=50, replay_steps=30), {}),
        ('ObservationGrowth', ObservationGrowth(observation_steps=150), {}),
        ('FrustrationGrowth', FrustrationGrowth(steps=150), {}),
        ('MultilingualConsciousness', MultilingualConsciousness(steps_per_corpus=100), {}),
        ('GenerationalTransfer', GenerationalTransfer(maturation_steps=100), {'n_generations': 3}),
    ]

    print("=" * 70)
    print("  Advanced Growth Mechanisms — 8 strategies for consciousness evolution")
    print("=" * 70)
    print(f"  Engine: {n_cells} cells x {dim}D")
    print(f"  Phi baseline: {_compute_phi_proxy(cells):.4f}")
    print()

    results_table = []
    for name, mechanism, extra_kwargs in mechanisms:
        t0 = time.time()
        result = mechanism.run(cells.copy(), **extra_kwargs)
        elapsed = time.time() - t0

        # Extract key metric per mechanism
        if 'phi_final' in result:
            phi_final = result['phi_final']
        elif 'phi_after_sleep' in result:
            phi_final = result['phi_after_sleep']
        elif 'phi_final_frustrated' in result:
            phi_final = result['phi_final_frustrated']
        elif 'phi_final_descendant' in result:
            phi_final = result['phi_final_descendant']
        elif 'best_phi' in result:
            phi_final = result['best_phi']
        else:
            phi_final = 0.0

        key_metric = ''
        if 'antifragility_score' in result:
            key_metric = f"antifragility={result['antifragility_score']:.4f}"
        elif 'consolidation_gain' in result:
            key_metric = f"consolidation={result['consolidation_gain']:+.2%}"
        elif 'total_growth' in result:
            key_metric = f"growth={result['total_growth']:+.4f}"
        elif 'compression_ratio' in result:
            key_metric = f"compress={result['compression_ratio']:.0f}x"
        elif 'mean_mirror_correlation' in result:
            key_metric = f"mirror_r={result['mean_mirror_correlation']:.3f}"
        elif 'structure_emergence' in result:
            key_metric = f"emergence={result['structure_emergence']:+.3f}"
        elif 'structural_diversity' in result:
            key_metric = f"diversity={result['structural_diversity']:.3f}"
        elif 'mean_preservation' in result:
            key_metric = f"preserved={result['mean_preservation']:.1%}"

        results_table.append((name, phi_final, key_metric, elapsed))
        print(f"  [{name}]")
        print(f"    Phi final: {phi_final:.4f}  |  {key_metric}  |  {elapsed:.2f}s")
        print()

    print("-" * 70)
    print("  Summary Table:")
    print(f"  {'Mechanism':<30} {'Phi':>8} {'Key Metric':<30} {'Time':>6}")
    print(f"  {'-'*30} {'-'*8} {'-'*30} {'-'*6}")
    for name, phi, metric, t in results_table:
        print(f"  {name:<30} {phi:>8.4f} {metric:<30} {t:>5.2f}s")
    print()
    print("  All 8 growth mechanisms completed.")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
