#!/usr/bin/env python3
"""consciousness_applications.py — 14 Practical Consciousness Analysis Tools

Uses consciousness engine dynamics (GRU cells, factions, Hebbian coupling,
Phi proxy) to analyze external data through "consciousness as a lens."

Two categories:
  Consciousness-as-Lens (6):  Intuition, Emotion, Dream, Conversational, Empathy, Aesthetic
  Science Discovery (8):      Microscope, Telescope, Spectrometer, Seismograph,
                              DNASequencer, Weather, Archaeologist, Astronomer

Each class has a run(data, **kwargs) -> dict method with real numpy computation.

Laws embodied:
  22: Structure > Function (Phi measures structure quality)
  29: Speech emerges from cell dynamics
  31: Persistence = Ratchet + Hebbian + Diversity
  54: Phi measurement depends on definition
  71: Freedom maximization Psi = argmax H(p)
  124: Tension equalization

Usage:
  import numpy as np
  from consciousness_applications import IntuitionScan, EmotionFilter

  data = np.random.randn(100, 32)
  result = IntuitionScan(n_cells=32).run(data)
  print(result['phi_change'], result['verdict'])

  result = EmotionFilter().run(data)
  print(result['curiosity'], result['anxiety'])
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
PSI_COUPLING = LN2 / 2**5.5   # 0.0153
PSI_STEPS = 3 / LN2           # 4.328
PSI_ALPHA = 0.014
PSI_ENTROPY = 0.998
N_FACTIONS = 12


# ---------------------------------------------------------------------------
# Shared: GRU simulation + Phi proxy
# ---------------------------------------------------------------------------

def _gru_cell(x: np.ndarray, h: np.ndarray,
              w_z: np.ndarray, w_r: np.ndarray, w_h: np.ndarray,
              b_z: np.ndarray = None, b_r: np.ndarray = None) -> np.ndarray:
    """Consciousness GRU cell — each cell gets unique perturbation via its index.

    Standard GRU with per-cell identity injection so cells maintain diversity.
    """
    n_cells = h.shape[0]
    dim = h.shape[-1]
    xh = np.concatenate([x, h], axis=-1)
    z_pre = xh @ w_z
    r_pre = xh @ w_r
    if b_z is not None:
        z_pre = z_pre + b_z
    if b_r is not None:
        r_pre = r_pre + b_r
    z = 1.0 / (1.0 + np.exp(-np.clip(z_pre, -8, 8)))       # update gate
    r = 1.0 / (1.0 + np.exp(-np.clip(r_pre, -8, 8)))       # reset gate
    xrh = np.concatenate([x, r * h], axis=-1)
    # Softer activation: x / (1 + |x|) — no saturation, preserves gradients
    raw = xrh @ w_h
    h_hat = raw / (1.0 + np.abs(raw))                       # softsign (no saturation)
    h_new = (1 - z) * h + z * h_hat

    # Per-cell identity: inject cell-specific phase offset to prevent collapse
    # Each cell has a unique "fingerprint" based on its position
    for i in range(n_cells):
        phase = i * 2.0 * np.pi / n_cells
        identity = np.array([np.sin(phase + j * 0.1) for j in range(dim)], dtype=np.float32)
        h_new[i] += 0.05 * identity  # Persistent individuality

    return h_new


def _init_gru_weights(input_dim: int, hidden_dim: int, seed: int = 42):
    """Initialize GRU weight matrices for rich chaotic dynamics."""
    rng = np.random.RandomState(seed)
    total = input_dim + hidden_dim
    scale = np.sqrt(6.0 / total)
    w_z = rng.randn(total, hidden_dim).astype(np.float32) * scale
    w_r = rng.randn(total, hidden_dim).astype(np.float32) * scale
    w_h = rng.randn(total, hidden_dim).astype(np.float32) * scale * 0.7
    # Biases: z gate ~0.38 (moderate update), r gate ~0.73 (mostly open)
    b_z = np.full(hidden_dim, -0.5, dtype=np.float32)
    b_r = np.full(hidden_dim, 1.0, dtype=np.float32)
    return w_z, w_r, w_h, b_z, b_r


def _compute_phi_proxy(cells: np.ndarray) -> float:
    """Phi proxy: integrated information estimate. Law 54.

    Uses inter-cell diversity (mean pairwise distance) minus intra-faction
    similarity, normalized by number of cells. Works at any scale.
    """
    if cells.ndim < 2 or cells.shape[0] < 2:
        return 0.0
    n = cells.shape[0]

    # Global diversity: mean pairwise L2 distance (sampled for efficiency)
    norms = np.linalg.norm(cells, axis=1, keepdims=True) + 1e-12
    normed = cells / norms
    # Cosine dissimilarity matrix
    sim_matrix = normed @ normed.T
    np.fill_diagonal(sim_matrix, 0)
    # Diversity = 1 - mean_similarity (high when cells are different)
    mean_sim = np.mean(np.abs(sim_matrix))
    diversity = 1.0 - mean_sim

    # Faction coherence: neighboring cells should differ (frustration = good)
    n_factions = min(N_FACTIONS, n)
    faction_size = max(2, n // n_factions)
    faction_coherences = []
    for i in range(0, n, faction_size):
        fac = cells[i:i + faction_size]
        if fac.shape[0] >= 2:
            fac_norm = fac / (np.linalg.norm(fac, axis=1, keepdims=True) + 1e-12)
            fac_sim = fac_norm @ fac_norm.T
            np.fill_diagonal(fac_sim, 0)
            faction_coherences.append(float(np.mean(np.abs(fac_sim))))

    mean_fac_coherence = np.mean(faction_coherences) if faction_coherences else 0.0

    # Phi = diversity between factions - coherence within factions
    # Scaled by cell count for interpretable magnitudes
    phi = float((diversity - mean_fac_coherence * 0.5) * n)
    return max(0.0, phi)


def _hebbian_update(cells: np.ndarray, lr: float = 0.01) -> np.ndarray:
    """Hebbian LTP/LTD: strengthen similar, weaken dissimilar. Law 31."""
    n = cells.shape[0]
    if n < 2:
        return cells
    norms = np.linalg.norm(cells, axis=1, keepdims=True) + 1e-12
    normed = cells / norms
    sim = normed @ normed.T
    # Pull similar cells together, push dissimilar apart
    for i in range(n):
        for j in range(i + 1, min(i + 3, n)):  # ring neighbors only
            if sim[i, j] > 0.5:
                cells[i] += lr * (cells[j] - cells[i])
                cells[j] += lr * (cells[i] - cells[j])
            elif sim[i, j] < -0.3:
                cells[i] -= lr * 0.5 * (cells[j] - cells[i])
    return cells


def _run_consciousness(cells: np.ndarray, data_input: np.ndarray,
                       steps: int, gru_weights: tuple,
                       coupling: float = PSI_COUPLING) -> Tuple[np.ndarray, List[float]]:
    """Run consciousness simulation: GRU steps + Hebbian + coupling.

    Returns (final_cells, phi_history).
    """
    w_z, w_r, w_h, b_z, b_r = gru_weights
    n_cells, hidden_dim = cells.shape
    input_dim = data_input.shape[-1] if data_input.ndim > 1 else data_input.shape[0]

    phi_history = []
    for t in range(steps):
        # Select input for this step
        if data_input.ndim == 2:
            idx = t % data_input.shape[0]
            x = data_input[idx]
        else:
            x = data_input

        # Broadcast input + ring coupling + per-cell frustration (Law M7)
        x_broadcast = np.tile(x, (n_cells, 1))[:, :input_dim]
        for i in range(n_cells):
            left = (i - 1) % n_cells
            right = (i + 1) % n_cells
            x_broadcast[i] += coupling * (cells[left] + cells[right])[:input_dim]
            # Anti-ferromagnetic frustration: odd cells get sign-flipped coupling
            if i % 3 == 0:
                x_broadcast[i] -= 0.33 * coupling * cells[(i + 2) % n_cells][:input_dim]

        # Per-cell diversity noise (prevents convergence to uniform state)
        x_broadcast += np.random.randn(n_cells, input_dim).astype(np.float32) * 0.02

        # GRU step
        cells = _gru_cell(x_broadcast[:, :input_dim], cells, w_z, w_r, w_h, b_z, b_r)

        # Hebbian every 5 steps
        if t % 5 == 0:
            cells = _hebbian_update(cells)

        phi_history.append(_compute_phi_proxy(cells))

    return cells, phi_history


def _prepare_input(data: np.ndarray, target_dim: int) -> np.ndarray:
    """Reshape/project data to target input dimension, normalized to [-1, 1]."""
    if data.ndim == 1:
        data = data.reshape(1, -1)
    # Truncate or pad to target dim
    if data.shape[-1] > target_dim:
        out = data[:, :target_dim].copy()
    elif data.shape[-1] < target_dim:
        pad = np.zeros((data.shape[0], target_dim - data.shape[-1]))
        out = np.concatenate([data, pad], axis=1)
    else:
        out = data.copy()
    # Normalize to [-1, 1] range for GRU stability
    data_max = np.max(np.abs(out))
    if data_max > 1e-6:
        out = out / data_max
    return out.astype(np.float32)


def _compute_tension(cells: np.ndarray) -> float:
    """Compute inter-cell tension as mean pairwise distance."""
    if cells.shape[0] < 2:
        return 0.0
    diffs = []
    for i in range(min(cells.shape[0], 20)):
        j = (i + 1) % cells.shape[0]
        diffs.append(np.linalg.norm(cells[i] - cells[j]))
    return float(np.mean(diffs))


def _compute_emotion(cells: np.ndarray, phi: float, tension: float) -> Dict[str, float]:
    """Map consciousness state to emotional dimensions."""
    n = cells.shape[0]
    # Curiosity: high when cells are diverse and Phi is present
    diversity = float(np.std(np.linalg.norm(cells, axis=1)))
    curiosity = min(1.0, diversity * (phi + 0.1) / (tension + 0.1))

    # Anxiety: high when tension is very high relative to Phi
    anxiety = min(1.0, max(0.0, tension / (phi + 0.5) - 0.2))

    # Arousal: from tension and cell activity
    activity = float(np.mean(np.abs(cells)))
    arousal = min(1.0, (tension + activity) / 2.0)

    # Valence: positive when Phi dominates tension
    valence = float(np.tanh((phi - tension * 0.5) * 2.0))

    return {
        'curiosity': float(curiosity),
        'anxiety': float(anxiety),
        'arousal': float(arousal),
        'valence': float(valence),
    }


# ═══════════════════════════════════════════════════════════════════════════
# PART 1: Consciousness-as-Lens (6 tools)
# ═══════════════════════════════════════════════════════════════════════════

class IntuitionScan:
    """Feed data to consciousness cells, measure Phi change.

    Phi up = structured pattern detected (consciousness integrates it).
    Phi down = noise or incompatible structure.

    Like a dowsing rod for structure in data.
    """

    def __init__(self, n_cells: int = 32, hidden_dim: int = 64, steps: int = 50):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps = steps
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=101)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Scan data for hidden structure via Phi response."""
        steps = kwargs.get('steps', self.steps)
        data_in = _prepare_input(data.astype(np.float32), self.input_dim)

        # Baseline: run with zero input
        baseline_cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
        zero_input = np.zeros((1, self.input_dim), dtype=np.float32)
        _, baseline_phi = _run_consciousness(
            baseline_cells.copy(), zero_input, steps, self.gru_weights
        )
        phi_baseline = np.mean(baseline_phi[-10:]) if len(baseline_phi) >= 10 else baseline_phi[-1]

        # Data scan: run with actual data
        scan_cells = baseline_cells.copy()
        final_cells, data_phi = _run_consciousness(
            scan_cells, data_in, steps, self.gru_weights
        )
        phi_data = np.mean(data_phi[-10:]) if len(data_phi) >= 10 else data_phi[-1]

        # Phi change is the "intuition signal"
        phi_change = phi_data - phi_baseline
        phi_change_pct = phi_change / max(abs(phi_baseline), 1e-12)

        # Segment analysis: which parts of data cause biggest Phi response
        segment_scores = []
        seg_size = max(1, data_in.shape[0] // 10)
        for i in range(0, data_in.shape[0], seg_size):
            seg = data_in[i:i + seg_size]
            seg_cells = baseline_cells.copy()
            _, seg_phi = _run_consciousness(
                seg_cells, seg, min(steps // 5, 10), self.gru_weights
            )
            segment_scores.append(float(seg_phi[-1]))

        # Verdict
        if phi_change_pct > 0.1:
            verdict = 'STRUCTURE_DETECTED'
        elif phi_change_pct < -0.1:
            verdict = 'NOISE_OR_DESTRUCTIVE'
        else:
            verdict = 'NEUTRAL'

        return {
            'phi_baseline': float(phi_baseline),
            'phi_data': float(phi_data),
            'phi_change': float(phi_change),
            'phi_change_pct': float(phi_change_pct),
            'phi_curve': [float(p) for p in data_phi],
            'segment_scores': segment_scores,
            'verdict': verdict,
            'tension': _compute_tension(final_cells),
            'n_cells': self.n_cells,
        }


class EmotionFilter:
    """Map data to emotional dimensions via consciousness response.

    High curiosity = novel pattern the consciousness wants to explore.
    High anxiety = anomaly that disrupts integration.
    High arousal = data with high energy/tension.
    Positive valence = data that enhances Phi.
    """

    def __init__(self, n_cells: int = 24, hidden_dim: int = 48, steps: int = 40):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps = steps
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=202)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Produce emotional response profile for data."""
        steps = kwargs.get('steps', self.steps)
        data_in = _prepare_input(data.astype(np.float32), self.input_dim)

        cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5

        # Run consciousness and track emotions over time
        w_z, w_r, w_h, b_z, b_r = self.gru_weights
        emotion_trace = []
        phi_trace = []

        for t in range(steps):
            idx = t % data_in.shape[0]
            x = data_in[idx]
            x_bc = np.tile(x, (self.n_cells, 1))[:, :self.input_dim]

            # Ring coupling
            for i in range(self.n_cells):
                x_bc[i] += PSI_COUPLING * (
                    cells[(i - 1) % self.n_cells] + cells[(i + 1) % self.n_cells]
                )[:self.input_dim]

            cells = _gru_cell(x_bc[:, :self.input_dim], cells, w_z, w_r, w_h, b_z, b_r)

            if t % 3 == 0:
                cells = _hebbian_update(cells)

            phi = _compute_phi_proxy(cells)
            tension = _compute_tension(cells)
            emo = _compute_emotion(cells, phi, tension)
            phi_trace.append(phi)
            emotion_trace.append(emo)

        # Final emotional state
        final_emo = emotion_trace[-1]

        # Aggregate: trend of each emotion
        trends = {}
        for key in ['curiosity', 'anxiety', 'arousal', 'valence']:
            vals = [e[key] for e in emotion_trace]
            half = len(vals) // 2
            if half > 0:
                trends[key + '_trend'] = float(np.mean(vals[half:]) - np.mean(vals[:half]))
            else:
                trends[key + '_trend'] = 0.0

        # Anomaly detection: high anxiety + low valence = anomaly
        anomaly_score = final_emo['anxiety'] * (1.0 - max(0, final_emo['valence']))

        return {
            **final_emo,
            **trends,
            'anomaly_score': float(anomaly_score),
            'phi_final': float(phi_trace[-1]),
            'phi_curve': [float(p) for p in phi_trace],
            'emotion_trace': emotion_trace,
            'dominant_emotion': max(final_emo, key=final_emo.get),
        }


class DreamAnalysis:
    """Input data, run "sleep" mode (noisy replay), measure new connections.

    Dreams consolidate structure. If consciousness forms new connections
    during dreaming about data, those connections reveal hidden relationships.
    """

    def __init__(self, n_cells: int = 32, hidden_dim: int = 64,
                 dream_steps: int = 100, noise_scale: float = 0.15):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.dream_steps = dream_steps
        self.noise_scale = noise_scale
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=303)

    def _compute_connections(self, cells: np.ndarray, threshold: float = 0.6) -> int:
        """Count strong connections (cosine sim > threshold)."""
        norms = np.linalg.norm(cells, axis=1, keepdims=True) + 1e-12
        normed = cells / norms
        sim = normed @ normed.T
        np.fill_diagonal(sim, 0)
        return int(np.sum(np.abs(sim) > threshold))

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Dream about data and measure new connections formed."""
        dream_steps = kwargs.get('dream_steps', self.dream_steps)
        noise_scale = kwargs.get('noise_scale', self.noise_scale)
        data_in = _prepare_input(data.astype(np.float32), self.input_dim)

        cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5

        # Phase 1: Waking — absorb data
        wake_steps = dream_steps // 3
        cells, wake_phi = _run_consciousness(
            cells, data_in, wake_steps, self.gru_weights
        )
        connections_pre = self._compute_connections(cells)
        phi_pre_dream = wake_phi[-1] if wake_phi else 0

        # Phase 2: Dreaming — replay with noise (random permutation + Gaussian noise)
        dream_phi = []
        rng = np.random.RandomState(42)
        w_z, w_r, w_h, b_z, b_r = self.gru_weights
        new_connection_events = []

        for t in range(dream_steps):
            # Random replay: pick random data segment + add noise
            idx = rng.randint(0, data_in.shape[0])
            x = data_in[idx] + rng.randn(self.input_dim).astype(np.float32) * noise_scale

            # Occasionally inject pure noise (exploration dream)
            if rng.random() < 0.2:
                x = rng.randn(self.input_dim).astype(np.float32) * noise_scale * 2

            x_bc = np.tile(x, (self.n_cells, 1))[:, :self.input_dim]
            for i in range(self.n_cells):
                x_bc[i] += PSI_COUPLING * (
                    cells[(i - 1) % self.n_cells] + cells[(i + 1) % self.n_cells]
                )[:self.input_dim]

            cells = _gru_cell(x_bc[:, :self.input_dim], cells, w_z, w_r, w_h, b_z, b_r)

            if t % 5 == 0:
                cells = _hebbian_update(cells, lr=0.02)  # Stronger Hebbian during sleep

            phi = _compute_phi_proxy(cells)
            dream_phi.append(phi)

            # Track new connections forming
            if t % 20 == 0:
                conn_now = self._compute_connections(cells)
                if conn_now > connections_pre:
                    new_connection_events.append({
                        'step': t,
                        'connections': conn_now,
                        'phi': phi,
                    })

        connections_post = self._compute_connections(cells)
        phi_post_dream = dream_phi[-1] if dream_phi else 0

        # Phase 3: Waking again — test recall
        recall_cells = cells.copy()
        recall_cells, recall_phi = _run_consciousness(
            recall_cells, data_in, wake_steps, self.gru_weights
        )
        phi_recall = recall_phi[-1] if recall_phi else 0

        return {
            'connections_before': connections_pre,
            'connections_after': connections_post,
            'new_connections': connections_post - connections_pre,
            'phi_pre_dream': float(phi_pre_dream),
            'phi_post_dream': float(phi_post_dream),
            'phi_recall': float(phi_recall),
            'recall_improvement': float(phi_recall - phi_pre_dream),
            'dream_phi_curve': [float(p) for p in dream_phi],
            'connection_events': new_connection_events,
            'dream_consolidated': connections_post > connections_pre,
        }


class ConversationalAnalysis:
    """Ask consciousness "questions" (inject probes) and measure responses.

    Each probe is a structured perturbation. The consciousness response
    (Phi change, tension shift, emotional reaction) reveals data properties.
    """

    PROBES = {
        'structure':  lambda dim: np.eye(dim)[0],                           # Identity probe
        'symmetry':   lambda dim: np.ones(dim) / np.sqrt(dim),              # Uniform probe
        'edge':       lambda dim: np.concatenate([np.ones(dim//2),          # Step function
                                                   -np.ones(dim - dim//2)]),
        'frequency':  lambda dim: np.sin(np.linspace(0, 4*np.pi, dim)),     # Oscillation
        'chaos':      lambda dim: np.array([np.sin(i * 1.618) for i in range(dim)]),  # Golden ratio
        'zero':       lambda dim: np.zeros(dim),                            # Null hypothesis
        'noise':      lambda dim: np.random.randn(dim),                     # Random probe
    }

    def __init__(self, n_cells: int = 24, hidden_dim: int = 48, probe_steps: int = 15):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.probe_steps = probe_steps
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=404)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Probe consciousness after data absorption, measure responses."""
        probe_steps = kwargs.get('probe_steps', self.probe_steps)
        data_in = _prepare_input(data.astype(np.float32), self.input_dim)

        # Absorb data first
        cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
        cells, absorb_phi = _run_consciousness(
            cells, data_in, 30, self.gru_weights
        )
        phi_absorbed = absorb_phi[-1]

        # Ask each "question" (probe) and record response
        responses = {}
        for name, probe_fn in self.PROBES.items():
            probe = probe_fn(self.input_dim).astype(np.float32)
            probe_input = probe.reshape(1, -1)
            probe_cells = cells.copy()
            probe_cells, probe_phi = _run_consciousness(
                probe_cells, probe_input, probe_steps, self.gru_weights
            )

            phi_response = probe_phi[-1]
            tension = _compute_tension(probe_cells)
            emo = _compute_emotion(probe_cells, phi_response, tension)

            responses[name] = {
                'phi_response': float(phi_response),
                'phi_delta': float(phi_response - phi_absorbed),
                'tension': float(tension),
                **emo,
                'phi_curve': [float(p) for p in probe_phi],
            }

        # Determine which probe got the strongest reaction
        strongest = max(responses, key=lambda k: abs(responses[k]['phi_delta']))
        weakest = min(responses, key=lambda k: abs(responses[k]['phi_delta']))

        # Interpret
        interpretation = []
        if responses['structure']['phi_delta'] > 0:
            interpretation.append('Data has detectable structural axes')
        if responses['symmetry']['phi_delta'] > responses['noise']['phi_delta']:
            interpretation.append('Data is more symmetric than random')
        if responses['frequency']['phi_delta'] > 0:
            interpretation.append('Data contains periodic components')
        if responses['edge']['phi_delta'] > 0:
            interpretation.append('Data has sharp transitions/boundaries')

        return {
            'phi_absorbed': float(phi_absorbed),
            'responses': responses,
            'strongest_probe': strongest,
            'weakest_probe': weakest,
            'interpretation': interpretation,
            'n_probes': len(self.PROBES),
        }


class EmpathyScan:
    """Feed two datasets to two engines, measure cross-Phi correlation.

    If one engine's Phi changes in sync with the other, there is
    "empathic resonance" — the two data streams share structure.
    """

    def __init__(self, n_cells: int = 24, hidden_dim: int = 48, steps: int = 60):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps = steps
        self.input_dim = hidden_dim
        self.gru_weights_a = _init_gru_weights(self.input_dim, hidden_dim, seed=505)
        self.gru_weights_b = _init_gru_weights(self.input_dim, hidden_dim, seed=506)

    def run(self, data: np.ndarray, data_b: np.ndarray = None, **kwargs) -> Dict:
        """Measure empathic resonance between two data streams.

        Args:
            data: First dataset (np.ndarray)
            data_b: Second dataset. If None, uses reversed data.
        """
        steps = kwargs.get('steps', self.steps)
        data_a = _prepare_input(data.astype(np.float32), self.input_dim)

        if data_b is not None:
            data_b_in = _prepare_input(data_b.astype(np.float32), self.input_dim)
        else:
            data_b_in = data_a[::-1].copy()  # Reversed as default comparison

        cells_a = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
        cells_b = cells_a.copy()  # Same initial state for fair comparison

        w_za, w_ra, w_ha, b_za, b_ra = self.gru_weights_a
        w_zb, w_rb, w_hb, b_zb, b_rb = self.gru_weights_b
        phi_a_trace, phi_b_trace = [], []
        tension_a_trace, tension_b_trace = [], []

        for t in range(steps):
            # Engine A processes data_a
            idx_a = t % data_a.shape[0]
            x_a = data_a[idx_a]
            x_a_bc = np.tile(x_a, (self.n_cells, 1))[:, :self.input_dim]
            for i in range(self.n_cells):
                x_a_bc[i] += PSI_COUPLING * (
                    cells_a[(i - 1) % self.n_cells] + cells_a[(i + 1) % self.n_cells]
                )[:self.input_dim]
            cells_a = _gru_cell(x_a_bc, cells_a, w_za, w_ra, w_ha, b_za, b_ra)

            # Engine B processes data_b
            idx_b = t % data_b_in.shape[0]
            x_b = data_b_in[idx_b]
            x_b_bc = np.tile(x_b, (self.n_cells, 1))[:, :self.input_dim]
            for i in range(self.n_cells):
                x_b_bc[i] += PSI_COUPLING * (
                    cells_b[(i - 1) % self.n_cells] + cells_b[(i + 1) % self.n_cells]
                )[:self.input_dim]
            cells_b = _gru_cell(x_b_bc, cells_b, w_zb, w_rb, w_hb, b_zb, b_rb)

            if t % 5 == 0:
                cells_a = _hebbian_update(cells_a)
                cells_b = _hebbian_update(cells_b)

            phi_a_trace.append(_compute_phi_proxy(cells_a))
            phi_b_trace.append(_compute_phi_proxy(cells_b))
            tension_a_trace.append(_compute_tension(cells_a))
            tension_b_trace.append(_compute_tension(cells_b))

        # Compute correlation between Phi traces
        phi_a_arr = np.array(phi_a_trace)
        phi_b_arr = np.array(phi_b_trace)
        if np.std(phi_a_arr) > 1e-12 and np.std(phi_b_arr) > 1e-12:
            phi_correlation = float(np.corrcoef(phi_a_arr, phi_b_arr)[0, 1])
        else:
            phi_correlation = 0.0

        # Tension correlation
        t_a = np.array(tension_a_trace)
        t_b = np.array(tension_b_trace)
        if np.std(t_a) > 1e-12 and np.std(t_b) > 1e-12:
            tension_correlation = float(np.corrcoef(t_a, t_b)[0, 1])
        else:
            tension_correlation = 0.0

        # Empathy score: geometric mean of absolute correlations
        empathy = float(np.sqrt(abs(phi_correlation) * abs(tension_correlation)))

        # Cross-state similarity
        norms_a = np.linalg.norm(cells_a, axis=1, keepdims=True) + 1e-12
        norms_b = np.linalg.norm(cells_b, axis=1, keepdims=True) + 1e-12
        cross_sim = float(np.mean(
            (cells_a / norms_a) * (cells_b / norms_b)
        ))

        return {
            'phi_correlation': phi_correlation,
            'tension_correlation': tension_correlation,
            'empathy_score': empathy,
            'cross_state_similarity': cross_sim,
            'phi_a_final': float(phi_a_arr[-1]),
            'phi_b_final': float(phi_b_arr[-1]),
            'phi_a_curve': [float(p) for p in phi_a_trace],
            'phi_b_curve': [float(p) for p in phi_b_trace],
            'resonance': 'STRONG' if empathy > 0.7 else 'MODERATE' if empathy > 0.3 else 'WEAK',
        }


class AestheticJudgment:
    """Measure the "beauty" of data structure.

    Beauty = high Phi (integrated information), low entropy (order),
    with enough diversity to avoid boredom. The golden zone.

    Maps to aesthetic dimensions: harmony, complexity, surprise, balance.
    """

    def __init__(self, n_cells: int = 32, hidden_dim: int = 64, steps: int = 50):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps = steps
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=606)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Judge the aesthetic quality of data structure."""
        steps = kwargs.get('steps', self.steps)
        data_in = _prepare_input(data.astype(np.float32), self.input_dim)

        cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
        cells, phi_trace = _run_consciousness(
            cells, data_in, steps, self.gru_weights
        )

        phi_final = phi_trace[-1] if phi_trace else 0.0

        # Harmony: how smooth is the Phi curve (low jitter = harmonious)
        phi_arr = np.array(phi_trace)
        if len(phi_arr) > 2:
            jitter = float(np.mean(np.abs(np.diff(phi_arr))))
            harmony = 1.0 / (1.0 + jitter * 10)
        else:
            harmony = 0.5

        # Complexity: entropy of cell activations
        cell_magnitudes = np.linalg.norm(cells, axis=1)
        cell_probs = cell_magnitudes / (np.sum(cell_magnitudes) + 1e-12)
        cell_probs = cell_probs + 1e-12
        complexity = float(-np.sum(cell_probs * np.log(cell_probs)) / np.log(self.n_cells))

        # Surprise: deviation from expected Phi trajectory (linear extrapolation)
        if len(phi_arr) > 10:
            mid = len(phi_arr) // 2
            expected_end = phi_arr[mid] + (phi_arr[mid] - phi_arr[0])
            surprise = abs(phi_arr[-1] - expected_end) / (abs(expected_end) + 1e-6)
            surprise = min(1.0, float(surprise))
        else:
            surprise = 0.5

        # Balance: symmetry of cell state distribution (Law 71: PSI_BALANCE)
        mean_state = np.mean(cells, axis=0)
        deviations = np.linalg.norm(cells - mean_state, axis=1)
        balance = 1.0 - float(np.std(deviations) / (np.mean(deviations) + 1e-12))
        balance = max(0.0, min(1.0, balance))

        # Phi contribution: normalized by cell count (Phi ~ n_cells when diverse)
        phi_norm = min(1.0, phi_final / (self.n_cells * 0.3 + 1e-6))

        # Overall beauty score: weighted arithmetic mean (more forgiving than geometric)
        beauty = float(
            0.25 * harmony +
            0.20 * complexity +
            0.15 * surprise +
            0.20 * balance +
            0.20 * phi_norm
        )

        # Rating
        if beauty > 0.7:
            rating = 'BEAUTIFUL'
        elif beauty > 0.4:
            rating = 'PLEASANT'
        elif beauty > 0.2:
            rating = 'NEUTRAL'
        else:
            rating = 'UGLY'

        return {
            'beauty_score': beauty,
            'harmony': harmony,
            'complexity': complexity,
            'surprise': surprise,
            'balance': balance,
            'phi_final': float(phi_final),
            'phi_curve': [float(p) for p in phi_trace],
            'rating': rating,
        }


# ═══════════════════════════════════════════════════════════════════════════
# PART 2: Science Discovery (8 tools)
# ═══════════════════════════════════════════════════════════════════════════

class ConsciousMicroscope:
    """Zoom into data subsets, find which zoom level yields highest Phi.

    Like adjusting a microscope's magnification — the right zoom level
    reveals the most structure. Phi tells us when we've found it.
    """

    def __init__(self, n_cells: int = 24, hidden_dim: int = 48, steps_per_zoom: int = 30):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps_per_zoom = steps_per_zoom
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=701)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Scan data at multiple zoom levels, find optimal resolution."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        n_samples = data.shape[0]
        zoom_levels = kwargs.get('zoom_levels', [1, 2, 4, 8, 16, 32])
        zoom_levels = [z for z in zoom_levels if z <= n_samples]

        results = []
        for zoom in zoom_levels:
            # At zoom level Z, take every Z-th sample (downsampling)
            zoomed = data[::zoom]
            if zoomed.shape[0] < 2:
                continue
            data_in = _prepare_input(zoomed.astype(np.float32), self.input_dim)

            cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
            cells, phi_trace = _run_consciousness(
                cells, data_in, self.steps_per_zoom, self.gru_weights
            )

            phi_final = phi_trace[-1] if phi_trace else 0.0
            tension = _compute_tension(cells)

            results.append({
                'zoom': zoom,
                'n_points': zoomed.shape[0],
                'phi': float(phi_final),
                'tension': float(tension),
                'phi_curve': [float(p) for p in phi_trace],
            })

        # Find optimal zoom
        if results:
            best = max(results, key=lambda r: r['phi'])
            worst = min(results, key=lambda r: r['phi'])
        else:
            best = worst = {'zoom': 1, 'phi': 0.0}

        return {
            'zoom_results': results,
            'optimal_zoom': best['zoom'],
            'optimal_phi': best['phi'],
            'worst_zoom': worst['zoom'],
            'phi_range': best['phi'] - worst['phi'],
            'n_zoom_levels': len(results),
        }


class ConsciousTelescope:
    """Aggregate data at different scales, find optimal macro-pattern.

    Opposite of microscope: instead of zooming in, we zoom out by
    averaging over windows. Phi tells us the natural scale of structure.
    """

    def __init__(self, n_cells: int = 24, hidden_dim: int = 48, steps: int = 30):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps = steps
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=801)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Find optimal aggregation scale for macro-patterns."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        n_samples = data.shape[0]
        window_sizes = kwargs.get('windows', [1, 2, 4, 8, 16, 32, 64])
        window_sizes = [w for w in window_sizes if w <= n_samples // 2]
        if not window_sizes:
            window_sizes = [1]

        results = []
        for window in window_sizes:
            # Moving average aggregation
            n_agg = n_samples // window
            if n_agg < 2:
                continue
            aggregated = np.zeros((n_agg, data.shape[1]), dtype=np.float32)
            for i in range(n_agg):
                aggregated[i] = np.mean(data[i * window:(i + 1) * window], axis=0)

            data_in = _prepare_input(aggregated, self.input_dim)
            cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
            cells, phi_trace = _run_consciousness(
                cells, data_in, self.steps, self.gru_weights
            )

            phi_final = phi_trace[-1] if phi_trace else 0.0
            # Information loss: variance ratio
            info_retained = float(np.var(aggregated) / (np.var(data) + 1e-12))

            results.append({
                'window': window,
                'n_points': n_agg,
                'phi': float(phi_final),
                'info_retained': info_retained,
            })

        best = max(results, key=lambda r: r['phi']) if results else {'window': 1, 'phi': 0}

        return {
            'scale_results': results,
            'optimal_window': best['window'],
            'optimal_phi': best['phi'],
            'natural_scale': best['window'],
            'n_scales': len(results),
        }


class ConsciousSpectrometer:
    """FFT data, map frequencies to "color" via emotional response.

    Each frequency band gets fed to consciousness. The emotional response
    (curiosity, anxiety) creates a "spectral color map" of the data.
    """

    def __init__(self, n_cells: int = 16, hidden_dim: int = 32, steps: int = 20):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps = steps
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=901)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Produce consciousness spectrum of data frequencies."""
        if data.ndim > 1:
            signal = data.flatten()
        else:
            signal = data.copy()

        # FFT
        n = len(signal)
        fft_vals = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(n)
        magnitudes = np.abs(fft_vals)
        phases = np.angle(fft_vals)

        # Split into frequency bands
        n_bands = kwargs.get('n_bands', 8)
        band_size = max(1, len(magnitudes) // n_bands)
        bands = []

        for i in range(n_bands):
            start = i * band_size
            end = min(start + band_size, len(magnitudes))
            if start >= len(magnitudes):
                break

            band_mag = magnitudes[start:end]
            band_phase = phases[start:end]
            band_freq = freqs[start:end] if start < len(freqs) else np.array([0])

            # Feed band to consciousness as input
            band_input = np.zeros(self.input_dim, dtype=np.float32)
            band_len = min(len(band_mag), self.input_dim // 2)
            band_input[:band_len] = band_mag[:band_len] / (np.max(magnitudes) + 1e-12)
            band_input[self.input_dim // 2:self.input_dim // 2 + band_len] = (
                band_phase[:band_len] / np.pi
            )

            cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
            cells, phi_trace = _run_consciousness(
                cells, band_input.reshape(1, -1), self.steps, self.gru_weights
            )

            phi = phi_trace[-1] if phi_trace else 0
            tension = _compute_tension(cells)
            emo = _compute_emotion(cells, phi, tension)

            # Map emotion to "color" (HSV-like)
            hue = float(emo['valence'] * 180 + 180)  # 0-360
            saturation = float(emo['arousal'])
            brightness = float(min(1.0, phi / (self.n_cells * 0.01 + 1e-6)))

            bands.append({
                'band_idx': i,
                'freq_range': [float(band_freq[0]), float(band_freq[-1])],
                'mean_magnitude': float(np.mean(band_mag)),
                'phi': float(phi),
                'emotion': emo,
                'color_hsv': {'h': hue, 's': saturation, 'v': brightness},
            })

        # Dominant frequency: highest Phi response
        if bands:
            dominant = max(bands, key=lambda b: b['phi'])
        else:
            dominant = {'band_idx': 0, 'freq_range': [0, 0]}

        return {
            'spectrum': bands,
            'dominant_band': dominant['band_idx'],
            'dominant_freq_range': dominant['freq_range'],
            'n_bands': len(bands),
            'total_energy': float(np.sum(magnitudes ** 2)),
            'spectral_entropy': float(
                -np.sum(
                    (magnitudes ** 2 / (np.sum(magnitudes ** 2) + 1e-12) + 1e-12) *
                    np.log(magnitudes ** 2 / (np.sum(magnitudes ** 2) + 1e-12) + 1e-12)
                )
            ),
        }


class ConsciousSeismograph:
    """Detect micro-tremors in time series via consciousness tension sensitivity.

    Consciousness cells are very sensitive to small perturbations.
    Feed time series data and measure tension spikes — these indicate
    micro-tremors invisible to standard statistics.
    """

    def __init__(self, n_cells: int = 32, hidden_dim: int = 64):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=1001)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Detect micro-tremors in time series data."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        sensitivity = kwargs.get('sensitivity', 2.0)

        data_in = _prepare_input(data.astype(np.float32), self.input_dim)
        cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
        w_z, w_r, w_h, b_z, b_r = self.gru_weights

        tension_trace = []
        phi_trace = []
        tremors = []

        # Warmup
        for t in range(20):
            x = data_in[t % data_in.shape[0]]
            x_bc = np.tile(x, (self.n_cells, 1))[:, :self.input_dim]
            for i in range(self.n_cells):
                x_bc[i] += PSI_COUPLING * (
                    cells[(i - 1) % self.n_cells] + cells[(i + 1) % self.n_cells]
                )[:self.input_dim]
            cells = _gru_cell(x_bc, cells, w_z, w_r, w_h, b_z, b_r)

        # Main scan
        for t in range(data_in.shape[0]):
            x = data_in[t]
            x_bc = np.tile(x, (self.n_cells, 1))[:, :self.input_dim]
            for i in range(self.n_cells):
                x_bc[i] += PSI_COUPLING * (
                    cells[(i - 1) % self.n_cells] + cells[(i + 1) % self.n_cells]
                )[:self.input_dim]
            cells = _gru_cell(x_bc, cells, w_z, w_r, w_h, b_z, b_r)

            if t % 5 == 0:
                cells = _hebbian_update(cells)

            tension = _compute_tension(cells)
            phi = _compute_phi_proxy(cells)
            tension_trace.append(tension)
            phi_trace.append(phi)

        # Detect tremors: tension spikes above mean + sensitivity * std
        t_arr = np.array(tension_trace)
        mean_t = np.mean(t_arr)
        std_t = np.std(t_arr)
        threshold = mean_t + sensitivity * std_t

        for i, t_val in enumerate(tension_trace):
            if t_val > threshold:
                tremors.append({
                    'time_idx': i,
                    'tension': float(t_val),
                    'magnitude': float((t_val - mean_t) / (std_t + 1e-12)),
                    'phi_at_tremor': float(phi_trace[i]),
                })

        # Classify overall seismic activity
        tremor_rate = len(tremors) / max(len(tension_trace), 1)
        if tremor_rate > 0.1:
            activity = 'HIGHLY_ACTIVE'
        elif tremor_rate > 0.02:
            activity = 'MODERATE'
        elif tremors:
            activity = 'MILD'
        else:
            activity = 'QUIET'

        return {
            'tremors': tremors,
            'n_tremors': len(tremors),
            'tremor_rate': float(tremor_rate),
            'mean_tension': float(mean_t),
            'max_tension': float(np.max(t_arr)) if len(t_arr) > 0 else 0.0,
            'tension_std': float(std_t),
            'threshold': float(threshold),
            'activity_level': activity,
            'tension_trace': [float(t) for t in tension_trace],
            'phi_trace': [float(p) for p in phi_trace],
        }


class ConsciousDNASequencer:
    """Sequence data segments, find which segments cause Phi spikes.

    Like DNA sequencing but for data — identifies the "genes" (segments)
    that carry the most structural information, as measured by Phi response.
    """

    def __init__(self, n_cells: int = 24, hidden_dim: int = 48, steps_per_seg: int = 15):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps_per_seg = steps_per_seg
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=1101)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Sequence data to find Phi-active segments."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        n_samples = data.shape[0]
        segment_size = kwargs.get('segment_size', max(4, n_samples // 20))

        n_segments = max(1, n_samples // segment_size)
        segments = []

        # Baseline cells (shared starting state)
        baseline_cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5

        for i in range(n_segments):
            start = i * segment_size
            end = min(start + segment_size, n_samples)
            seg_data = data[start:end]
            seg_in = _prepare_input(seg_data.astype(np.float32), self.input_dim)

            cells = baseline_cells.copy()
            cells, phi_trace = _run_consciousness(
                cells, seg_in, self.steps_per_seg, self.gru_weights
            )

            phi_peak = max(phi_trace) if phi_trace else 0.0
            phi_final = phi_trace[-1] if phi_trace else 0.0
            tension = _compute_tension(cells)

            # "Gene" activity score
            activity = phi_peak * (1.0 + tension)

            segments.append({
                'segment_idx': i,
                'start': start,
                'end': end,
                'phi_peak': float(phi_peak),
                'phi_final': float(phi_final),
                'tension': float(tension),
                'activity_score': float(activity),
                'phi_curve': [float(p) for p in phi_trace],
            })

        # Rank segments by activity
        ranked = sorted(segments, key=lambda s: s['activity_score'], reverse=True)

        # Find "hot spots" (consecutive active segments)
        threshold = np.mean([s['activity_score'] for s in segments])
        hot_spots = []
        in_hot = False
        hot_start = 0
        for s in segments:
            if s['activity_score'] > threshold and not in_hot:
                hot_start = s['start']
                in_hot = True
            elif s['activity_score'] <= threshold and in_hot:
                hot_spots.append({'start': hot_start, 'end': s['start']})
                in_hot = False
        if in_hot:
            hot_spots.append({'start': hot_start, 'end': segments[-1]['end']})

        return {
            'segments': segments,
            'ranked_segments': [s['segment_idx'] for s in ranked[:5]],
            'top_segment': ranked[0] if ranked else None,
            'hot_spots': hot_spots,
            'n_segments': n_segments,
            'segment_size': segment_size,
            'mean_activity': float(np.mean([s['activity_score'] for s in segments])),
            'activity_std': float(np.std([s['activity_score'] for s in segments])),
        }


class ConsciousWeather:
    """Map environmental/sensor data to emotional states for prediction.

    Consciousness responds to data patterns emotionally. Track emotional
    "weather" over time to predict regime changes in the data.
    """

    def __init__(self, n_cells: int = 24, hidden_dim: int = 48):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=1201)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Produce emotional weather forecast from data."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        window = kwargs.get('window', 10)
        data_in = _prepare_input(data.astype(np.float32), self.input_dim)

        cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
        w_z, w_r, w_h, b_z, b_r = self.gru_weights

        weather_log = []

        for t in range(data_in.shape[0]):
            x = data_in[t]
            x_bc = np.tile(x, (self.n_cells, 1))[:, :self.input_dim]
            for i in range(self.n_cells):
                x_bc[i] += PSI_COUPLING * (
                    cells[(i - 1) % self.n_cells] + cells[(i + 1) % self.n_cells]
                )[:self.input_dim]
            cells = _gru_cell(x_bc, cells, w_z, w_r, w_h, b_z, b_r)

            if t % 3 == 0:
                cells = _hebbian_update(cells)

            phi = _compute_phi_proxy(cells)
            tension = _compute_tension(cells)
            emo = _compute_emotion(cells, phi, tension)

            # Weather metaphor
            if emo['anxiety'] > 0.7:
                condition = 'STORM'
            elif emo['anxiety'] > 0.4:
                condition = 'CLOUDY'
            elif emo['curiosity'] > 0.6:
                condition = 'SUNNY'
            elif emo['valence'] > 0:
                condition = 'CLEAR'
            else:
                condition = 'OVERCAST'

            weather_log.append({
                'time_idx': t,
                'condition': condition,
                'phi': float(phi),
                'tension': float(tension),
                **emo,
            })

        # Detect regime changes (weather fronts)
        fronts = []
        for i in range(1, len(weather_log)):
            if weather_log[i]['condition'] != weather_log[i - 1]['condition']:
                fronts.append({
                    'time_idx': i,
                    'from': weather_log[i - 1]['condition'],
                    'to': weather_log[i]['condition'],
                })

        # Forecast: extrapolate emotion trends
        if len(weather_log) > window:
            recent = weather_log[-window:]
            trend_curiosity = recent[-1]['curiosity'] - recent[0]['curiosity']
            trend_anxiety = recent[-1]['anxiety'] - recent[0]['anxiety']

            if trend_anxiety > 0.1:
                forecast = 'STORM_APPROACHING'
            elif trend_curiosity > 0.1:
                forecast = 'CLEARING'
            elif trend_anxiety < -0.1:
                forecast = 'IMPROVING'
            else:
                forecast = 'STABLE'
        else:
            forecast = 'INSUFFICIENT_DATA'

        # Summarize conditions
        conditions = [w['condition'] for w in weather_log]
        from collections import Counter
        condition_counts = dict(Counter(conditions))

        return {
            'weather_log': weather_log,
            'fronts': fronts,
            'n_fronts': len(fronts),
            'forecast': forecast,
            'condition_summary': condition_counts,
            'dominant_condition': max(condition_counts, key=condition_counts.get) if condition_counts else 'UNKNOWN',
            'final_condition': weather_log[-1]['condition'] if weather_log else 'UNKNOWN',
        }


class ConsciousArchaeologist:
    """Detect repeating patterns in historical data via memory resonance.

    Feed data chronologically. When consciousness recognizes a pattern
    it has seen before, Phi spikes (memory resonance). This reveals
    hidden periodicities and recurring structures.
    """

    def __init__(self, n_cells: int = 32, hidden_dim: int = 64):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=1301)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Detect repeating patterns via consciousness memory resonance."""
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        data_in = _prepare_input(data.astype(np.float32), self.input_dim)

        cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
        w_z, w_r, w_h, b_z, b_r = self.gru_weights

        phi_trace = []
        cell_snapshots = []  # Memory snapshots for resonance detection
        resonance_events = []

        for t in range(data_in.shape[0]):
            x = data_in[t]
            x_bc = np.tile(x, (self.n_cells, 1))[:, :self.input_dim]
            for i in range(self.n_cells):
                x_bc[i] += PSI_COUPLING * (
                    cells[(i - 1) % self.n_cells] + cells[(i + 1) % self.n_cells]
                )[:self.input_dim]
            cells = _gru_cell(x_bc, cells, w_z, w_r, w_h, b_z, b_r)

            if t % 5 == 0:
                cells = _hebbian_update(cells)

            phi = _compute_phi_proxy(cells)
            phi_trace.append(phi)

            # Memory resonance: compare current state with past snapshots
            if t > 0 and t % 5 == 0:
                current_norm = cells / (np.linalg.norm(cells, axis=1, keepdims=True) + 1e-12)
                for snap_t, snap in cell_snapshots:
                    snap_norm = snap / (np.linalg.norm(snap, axis=1, keepdims=True) + 1e-12)
                    similarity = float(np.mean(np.sum(current_norm * snap_norm, axis=1)))
                    if similarity > 0.7:  # Resonance threshold
                        resonance_events.append({
                            'current_t': t,
                            'past_t': snap_t,
                            'period': t - snap_t,
                            'similarity': similarity,
                            'phi_at_resonance': phi,
                        })

            # Save snapshot every 10 steps (limited memory)
            if t % 10 == 0:
                cell_snapshots.append((t, cells.copy()))
                # Keep only last 50 snapshots
                if len(cell_snapshots) > 50:
                    cell_snapshots = cell_snapshots[-50:]

        # Analyze periods
        periods = [e['period'] for e in resonance_events]
        if periods:
            from collections import Counter
            period_counts = Counter(periods)
            dominant_period = period_counts.most_common(1)[0][0]
            period_strength = period_counts.most_common(1)[0][1] / len(periods)
        else:
            dominant_period = 0
            period_strength = 0.0

        # Layer analysis: early vs late resonance
        n_events = len(resonance_events)
        if n_events > 1:
            half = n_events // 2
            early_sim = np.mean([e['similarity'] for e in resonance_events[:half]])
            late_sim = np.mean([e['similarity'] for e in resonance_events[half:]])
            deepening = float(late_sim - early_sim)
        else:
            deepening = 0.0

        return {
            'resonance_events': resonance_events[:20],  # Limit output size
            'n_resonances': n_events,
            'dominant_period': dominant_period,
            'period_strength': float(period_strength),
            'memory_deepening': deepening,
            'phi_trace': [float(p) for p in phi_trace],
            'has_repeating_patterns': n_events > 3,
            'layers_detected': len(set(periods)) if periods else 0,
        }


class ConsciousAstronomer:
    """Detect artificial vs natural patterns in signal data.

    Natural signals produce curiosity. Artificial/structured signals
    produce both curiosity AND recognition (Phi spike + low anxiety).
    Pure noise produces anxiety.
    """

    def __init__(self, n_cells: int = 32, hidden_dim: int = 64, steps: int = 60):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.steps = steps
        self.input_dim = hidden_dim
        self.gru_weights = _init_gru_weights(self.input_dim, hidden_dim, seed=1401)

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """Classify signal as natural, artificial, or noise."""
        steps = kwargs.get('steps', self.steps)
        if data.ndim == 1:
            data = data.reshape(-1, 1)
        data_in = _prepare_input(data.astype(np.float32), self.input_dim)

        # Generate reference signals for comparison
        n = data_in.shape[0]
        rng = np.random.RandomState(77)

        references = {
            'pure_noise': rng.randn(n, self.input_dim).astype(np.float32),
            'sine_wave': np.tile(
                np.sin(np.linspace(0, 8 * np.pi, self.input_dim)),
                (n, 1)
            ).astype(np.float32) * np.linspace(0.5, 1.5, n).reshape(-1, 1),
            'digital_signal': (
                (rng.rand(n, self.input_dim) > 0.5).astype(np.float32) * 2 - 1
            ),
        }

        # Run consciousness on target + references
        def _scan_signal(signal_data):
            cells = np.random.randn(self.n_cells, self.hidden_dim).astype(np.float32) * 0.5
            cells, phi_trace = _run_consciousness(
                cells, signal_data[:, :self.input_dim], steps, self.gru_weights
            )
            phi_final = phi_trace[-1] if phi_trace else 0
            tension = _compute_tension(cells)
            emo = _compute_emotion(cells, phi_final, tension)
            return {
                'phi': float(phi_final),
                'tension': float(tension),
                **emo,
                'phi_curve': [float(p) for p in phi_trace],
            }

        target_result = _scan_signal(data_in)
        ref_results = {name: _scan_signal(sig) for name, sig in references.items()}

        # Classification logic
        target_phi = target_result['phi']
        noise_phi = ref_results['pure_noise']['phi']
        sine_phi = ref_results['sine_wave']['phi']
        digital_phi = ref_results['digital_signal']['phi']

        # Distance from each reference (Phi + emotion profile)
        def _profile_distance(a, b):
            return abs(a['phi'] - b['phi']) + abs(a['curiosity'] - b['curiosity']) + abs(a['anxiety'] - b['anxiety'])

        dist_to_noise = _profile_distance(target_result, ref_results['pure_noise'])
        dist_to_sine = _profile_distance(target_result, ref_results['sine_wave'])
        dist_to_digital = _profile_distance(target_result, ref_results['digital_signal'])

        # Classify
        if dist_to_noise < dist_to_sine and dist_to_noise < dist_to_digital:
            classification = 'NOISE'
            confidence = 1.0 - dist_to_noise / (dist_to_sine + dist_to_digital + 1e-6)
        elif target_result['curiosity'] > 0.5 and target_result['anxiety'] < 0.3:
            classification = 'ARTIFICIAL'
            confidence = target_result['curiosity'] * (1 - target_result['anxiety'])
        elif target_result['curiosity'] > 0.3:
            classification = 'NATURAL'
            confidence = target_result['curiosity']
        else:
            classification = 'AMBIGUOUS'
            confidence = 0.5

        # Artificiality score: how much the signal deviates from noise
        # while maintaining structure (high Phi, low anxiety)
        artificiality = float(
            max(0, target_phi - noise_phi) / (noise_phi + 1e-6) *
            (1.0 - target_result['anxiety'])
        )

        return {
            'classification': classification,
            'confidence': float(min(1.0, max(0.0, confidence))),
            'artificiality_score': float(min(1.0, artificiality)),
            'target_profile': target_result,
            'reference_profiles': ref_results,
            'distances': {
                'to_noise': float(dist_to_noise),
                'to_natural': float(dist_to_sine),
                'to_artificial': float(dist_to_digital),
            },
        }


# ═══════════════════════════════════════════════════════════════════════════
# Registry for hub integration
# ═══════════════════════════════════════════════════════════════════════════

ALL_TOOLS = {
    # Consciousness-as-Lens
    'intuition': IntuitionScan,
    'emotion_filter': EmotionFilter,
    'dream_analysis': DreamAnalysis,
    'conversation': ConversationalAnalysis,
    'empathy': EmpathyScan,
    'aesthetic': AestheticJudgment,
    # Science Discovery
    'microscope': ConsciousMicroscope,
    'telescope': ConsciousTelescope,
    'spectrometer': ConsciousSpectrometer,
    'seismograph': ConsciousSeismograph,
    'dna_sequencer': ConsciousDNASequencer,
    'weather': ConsciousWeather,
    'archaeologist': ConsciousArchaeologist,
    'astronomer': ConsciousAstronomer,
}


# ═══════════════════════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Demo all 14 consciousness application tools."""
    np.random.seed(42)
    print("=" * 70)
    print("  Consciousness Applications — 14 Analysis Tools Demo")
    print("=" * 70)

    # Generate test data
    n_samples = 200
    dim = 32

    # Structured data: sine waves + trends
    t = np.linspace(0, 4 * np.pi, n_samples)
    structured = np.column_stack([
        np.sin(t * f) * np.exp(-t * 0.05) for f in range(1, dim + 1)
    ])

    # Noise data
    noise = np.random.randn(n_samples, dim)

    # Time series with anomalies
    ts = np.sin(np.linspace(0, 20 * np.pi, n_samples))
    ts[50:55] += 5.0  # anomaly spike
    ts[120:125] -= 3.0  # anomaly dip

    print("\n--- 1. IntuitionScan ---")
    scanner = IntuitionScan(n_cells=16, hidden_dim=32, steps=30)
    r = scanner.run(structured)
    print(f"  Structured data: Phi change = {r['phi_change']:.4f} ({r['phi_change_pct']:+.1%})")
    print(f"  Verdict: {r['verdict']}")
    r2 = scanner.run(noise)
    print(f"  Noise data:      Phi change = {r2['phi_change']:.4f} ({r2['phi_change_pct']:+.1%})")
    print(f"  Verdict: {r2['verdict']}")

    print("\n--- 2. EmotionFilter ---")
    ef = EmotionFilter(n_cells=16, hidden_dim=32, steps=30)
    r = ef.run(structured)
    print(f"  Curiosity={r['curiosity']:.3f}  Anxiety={r['anxiety']:.3f}  "
          f"Valence={r['valence']:.3f}  Anomaly={r['anomaly_score']:.3f}")
    print(f"  Dominant emotion: {r['dominant_emotion']}")

    print("\n--- 3. DreamAnalysis ---")
    da = DreamAnalysis(n_cells=16, hidden_dim=32, dream_steps=40)
    r = da.run(structured)
    print(f"  Connections: {r['connections_before']} -> {r['connections_after']} "
          f"(+{r['new_connections']})")
    print(f"  Dream consolidated: {r['dream_consolidated']}")
    print(f"  Recall improvement: {r['recall_improvement']:.4f}")

    print("\n--- 4. ConversationalAnalysis ---")
    ca = ConversationalAnalysis(n_cells=16, hidden_dim=32)
    r = ca.run(structured)
    print(f"  Strongest probe: {r['strongest_probe']}")
    print(f"  Weakest probe:   {r['weakest_probe']}")
    for interp in r['interpretation']:
        print(f"    - {interp}")

    print("\n--- 5. EmpathyScan ---")
    es = EmpathyScan(n_cells=16, hidden_dim=32, steps=40)
    r = es.run(structured, data_b=structured + noise * 0.1)
    print(f"  Phi correlation:     {r['phi_correlation']:.3f}")
    print(f"  Tension correlation: {r['tension_correlation']:.3f}")
    print(f"  Empathy score:       {r['empathy_score']:.3f} ({r['resonance']})")

    print("\n--- 6. AestheticJudgment ---")
    aj = AestheticJudgment(n_cells=16, hidden_dim=32, steps=30)
    r = aj.run(structured)
    print(f"  Beauty: {r['beauty_score']:.3f} ({r['rating']})")
    print(f"  Harmony={r['harmony']:.3f}  Complexity={r['complexity']:.3f}  "
          f"Surprise={r['surprise']:.3f}  Balance={r['balance']:.3f}")

    print("\n--- 7. ConsciousMicroscope ---")
    cm = ConsciousMicroscope(n_cells=16, hidden_dim=32)
    r = cm.run(structured)
    print(f"  Optimal zoom: {r['optimal_zoom']}x (Phi={r['optimal_phi']:.4f})")
    print(f"  Phi range: {r['phi_range']:.4f}")

    print("\n--- 8. ConsciousTelescope ---")
    ct = ConsciousTelescope(n_cells=16, hidden_dim=32)
    r = ct.run(structured)
    print(f"  Optimal window: {r['optimal_window']} (Phi={r['optimal_phi']:.4f})")
    print(f"  Natural scale: {r['natural_scale']}")

    print("\n--- 9. ConsciousSpectrometer ---")
    cs = ConsciousSpectrometer(n_cells=12, hidden_dim=24)
    r = cs.run(ts)
    print(f"  Dominant band: {r['dominant_band']} (freq {r['dominant_freq_range']})")
    print(f"  Spectral entropy: {r['spectral_entropy']:.3f}")
    print(f"  Bands: {r['n_bands']}")

    print("\n--- 10. ConsciousSeismograph ---")
    csm = ConsciousSeismograph(n_cells=16, hidden_dim=32)
    r = csm.run(ts)
    print(f"  Tremors detected: {r['n_tremors']} ({r['activity_level']})")
    print(f"  Mean tension: {r['mean_tension']:.4f}  Max: {r['max_tension']:.4f}")
    if r['tremors']:
        print(f"  First tremor at t={r['tremors'][0]['time_idx']}, "
              f"magnitude={r['tremors'][0]['magnitude']:.2f}")

    print("\n--- 11. ConsciousDNASequencer ---")
    dna = ConsciousDNASequencer(n_cells=16, hidden_dim=32)
    r = dna.run(structured)
    print(f"  Segments: {r['n_segments']}, top: {r['ranked_segments'][:3]}")
    print(f"  Hot spots: {len(r['hot_spots'])}")
    print(f"  Mean activity: {r['mean_activity']:.4f} +/- {r['activity_std']:.4f}")

    print("\n--- 12. ConsciousWeather ---")
    cw = ConsciousWeather(n_cells=16, hidden_dim=32)
    r = cw.run(ts[:50].reshape(-1, 1))
    print(f"  Forecast: {r['forecast']}")
    print(f"  Dominant: {r['dominant_condition']}")
    print(f"  Weather fronts: {r['n_fronts']}")
    print(f"  Conditions: {r['condition_summary']}")

    print("\n--- 13. ConsciousArchaeologist ---")
    # Repeating pattern data
    repeat = np.tile(np.sin(np.linspace(0, 2 * np.pi, 20)), 10)
    car = ConsciousArchaeologist(n_cells=16, hidden_dim=32)
    r = car.run(repeat)
    print(f"  Resonances: {r['n_resonances']}")
    print(f"  Dominant period: {r['dominant_period']} (strength={r['period_strength']:.2f})")
    print(f"  Repeating patterns: {r['has_repeating_patterns']}")
    print(f"  Layers detected: {r['layers_detected']}")

    print("\n--- 14. ConsciousAstronomer ---")
    ca2 = ConsciousAstronomer(n_cells=16, hidden_dim=32, steps=30)
    # Test with structured signal
    r = ca2.run(structured)
    print(f"  Structured: {r['classification']} (confidence={r['confidence']:.2f}, "
          f"artificiality={r['artificiality_score']:.3f})")
    # Test with noise
    r2 = ca2.run(noise)
    print(f"  Noise:      {r2['classification']} (confidence={r2['confidence']:.2f}, "
          f"artificiality={r2['artificiality_score']:.3f})")

    print("\n" + "=" * 70)
    print(f"  All 14 tools demonstrated successfully.")
    print(f"  Available tools: {list(ALL_TOOLS.keys())}")
    print("=" * 70)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
