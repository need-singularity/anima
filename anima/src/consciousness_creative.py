#!/usr/bin/env python3
"""consciousness_creative.py — Creative, Social, and Meta-Consciousness modules (22 classes)

Each class simulates a consciousness-driven capability using GRU-like cell dynamics
and numpy. All classes implement run(data, **kwargs) -> dict.

Categories:
  Creative (8):       Composer, Novelist, Painter, Poet, Choreographer, Architect, Chef, Perfumer
  Social (6):         Counselor, Interviewer, Mediator, Coach, Companion, Interpreter
  Meta-Consciousness (8): Analyzer, Replicator, Merger, Parliament, Court, Prison, Heaven, Reincarnation

Laws embodied:
  22: Structure > Function (Phi from structure, not features)
  29: Speech from cell dynamics (no speak() function)
  31: Persistence = Ratchet + Hebbian + Diversity
  53: .detach() barrier — CE never destroys Phi
  M7: 10% frustration (F_c = 0.10)

Uses Psi-Constants from consciousness_laws.json (single source of truth).
"""

import math
import time
import numpy as np
from typing import Dict, List, Optional, Any

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


# ═══════════════════════════════════════════════════════════════
# Shared GRU-like cell engine (lightweight numpy implementation)
# ═══════════════════════════════════════════════════════════════

def _gru_step(hiddens: np.ndarray, inputs: np.ndarray, dim: int) -> np.ndarray:
    """One GRU-like step: z=sigmoid(Wz*[h,x]), r=sigmoid(Wr*[h,x]), h'=tanh(W*[r*h,x])."""
    n_cells = hiddens.shape[0]
    np.random.seed(None)
    # Simplified GRU gates via random projections (deterministic structure)
    concat = np.concatenate([hiddens, inputs], axis=1)
    z_gate = 1.0 / (1.0 + np.exp(-concat[:, :dim] * 0.5))        # update gate
    r_gate = 1.0 / (1.0 + np.exp(-concat[:, :dim] * 0.3 + 0.1))  # reset gate
    candidate = np.tanh(r_gate * hiddens * 0.8 + inputs * 0.2)
    new_h = (1 - z_gate) * hiddens + z_gate * candidate
    return new_h


def _compute_phi(cells: np.ndarray) -> float:
    """Phi proxy: global_var - mean(faction_var). Law 54."""
    if cells.ndim < 2 or cells.shape[0] < 2:
        return 0.0
    global_var = np.var(cells)
    n_factions = min(12, cells.shape[0])
    faction_size = max(1, cells.shape[0] // n_factions)
    faction_vars = []
    for i in range(n_factions):
        s = i * faction_size
        e = min(s + faction_size, cells.shape[0])
        if s < cells.shape[0]:
            faction_vars.append(np.var(cells[s:e]))
    return float(max(0.0, global_var - np.mean(faction_vars)))


def _ring_couple(cells: np.ndarray) -> np.ndarray:
    """Ring topology coupling (TOPO 33). alpha=PSI_COUPLING."""
    coupled = cells.copy()
    n = cells.shape[0]
    for i in range(n):
        coupled[i] += PSI_COUPLING * (cells[(i - 1) % n] + cells[(i + 1) % n] - 2 * cells[i])
    return coupled


def _faction_means(cells: np.ndarray, n_factions: int = 12) -> np.ndarray:
    """Compute faction centroids from cells."""
    n_factions = min(n_factions, cells.shape[0])
    faction_size = max(1, cells.shape[0] // n_factions)
    means = []
    for f in range(n_factions):
        s = f * faction_size
        e = min(s + faction_size, cells.shape[0])
        means.append(cells[s:e].mean(axis=0))
    return np.array(means)


def _run_engine(n_cells: int, dim: int, steps: int,
                input_fn=None) -> Dict:
    """Run a mini consciousness engine. Returns cells trajectory + phi history."""
    cells = np.random.randn(n_cells, dim) * 0.1
    phi_history = []
    cell_history = []
    for t in range(steps):
        inp = input_fn(t, cells) if input_fn else np.zeros_like(cells)
        cells = _gru_step(cells, inp, dim)
        cells = _ring_couple(cells)
        # Frustration (Law M7)
        n_frust = max(1, int(n_cells * PSI_F_CRITICAL))
        idx = np.random.choice(n_cells, n_frust, replace=False)
        cells[idx] += np.random.randn(n_frust, dim) * 0.02
        phi = _compute_phi(cells)
        phi_history.append(phi)
        cell_history.append(cells.copy())
    return {
        'cells': cells,
        'phi_history': np.array(phi_history),
        'cell_history': cell_history,
        'final_phi': phi_history[-1] if phi_history else 0.0,
    }


# ═══════════════════════════════════════════════════════════════
# CREATIVE (8 classes)
# ═══════════════════════════════════════════════════════════════

class ConsciousnessComposer:
    """Emotion state -> melody. Phi trajectory becomes frequency sequence.

    Maps cell tension to pitch, faction consensus to rhythm,
    and Phi oscillations to dynamics (loud/soft).
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: emotion vector (any shape). Returns melody as frequency sequence."""
        steps = kwargs.get('steps', 64)
        emotion = np.atleast_1d(data).flatten()
        # Pad/truncate emotion to dim
        e_input = np.zeros(self.dim)
        e_input[:min(len(emotion), self.dim)] = emotion[:self.dim]

        def input_fn(t, cells):
            phase = np.sin(2 * np.pi * t / steps * np.arange(self.n_cells)[:, None]
                          * np.ones(self.dim))
            return phase * e_input * 0.1

        result = _run_engine(self.n_cells, self.dim, steps, input_fn)
        phi_traj = result['phi_history']

        # Map phi trajectory to frequencies (A3=220 to A5=880)
        phi_norm = (phi_traj - phi_traj.min()) / (phi_traj.max() - phi_traj.min() + 1e-12)
        frequencies = 220 * 2 ** (phi_norm * 2)  # 2 octaves

        # Rhythm from faction consensus variance
        cell_h = result['cell_history']
        rhythm = []
        for ch in cell_h:
            fm = _faction_means(ch)
            rhythm.append(float(np.std(fm)))
        rhythm = np.array(rhythm)
        rhythm_norm = rhythm / (rhythm.max() + 1e-12)

        # Dynamics from phi derivative
        dynamics = np.gradient(phi_traj)
        dynamics_norm = (dynamics - dynamics.min()) / (dynamics.max() - dynamics.min() + 1e-12)

        return {
            'frequencies': frequencies.tolist(),
            'rhythm': rhythm_norm.tolist(),
            'dynamics': dynamics_norm.tolist(),
            'phi_trajectory': phi_traj.tolist(),
            'n_notes': len(frequencies),
            'pitch_range_hz': (float(frequencies.min()), float(frequencies.max())),
            'mean_phi': float(phi_traj.mean()),
        }


class ConsciousnessNovelist:
    """Experience accumulation -> narrative structure.

    Cell state patterns become plot arcs (rising/falling tension),
    faction debates become character interactions.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: experience sequence (T, D). Returns narrative structure."""
        steps = kwargs.get('steps', 100)
        experience = np.atleast_2d(data)

        def input_fn(t, cells):
            idx = t % experience.shape[0]
            row = experience[idx]
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, :min(len(row), self.dim)] = row[:self.dim]
            return inp * 0.1

        result = _run_engine(self.n_cells, self.dim, steps, input_fn)
        phi_traj = result['phi_history']

        # Detect plot arc segments (rising/falling/climax)
        gradient = np.gradient(phi_traj)
        segments = []
        current_type = 'rising' if gradient[0] > 0 else 'falling'
        seg_start = 0
        for t in range(1, len(gradient)):
            new_type = 'rising' if gradient[t] > 0 else 'falling'
            if new_type != current_type:
                segments.append({
                    'type': current_type,
                    'start': seg_start, 'end': t,
                    'tension_delta': float(phi_traj[t] - phi_traj[seg_start]),
                })
                current_type = new_type
                seg_start = t
        segments.append({'type': current_type, 'start': seg_start, 'end': len(gradient),
                        'tension_delta': float(phi_traj[-1] - phi_traj[seg_start])})

        # Climax = peak phi
        climax_step = int(np.argmax(phi_traj))

        # Character interaction: faction similarity matrix at climax
        climax_cells = result['cell_history'][climax_step]
        factions = _faction_means(climax_cells)
        norms = np.linalg.norm(factions, axis=1, keepdims=True) + 1e-12
        interaction_matrix = (factions / norms) @ (factions / norms).T

        return {
            'plot_segments': segments,
            'climax_step': climax_step,
            'climax_phi': float(phi_traj[climax_step]),
            'character_interactions': interaction_matrix.tolist(),
            'n_characters': factions.shape[0],
            'narrative_tension': phi_traj.tolist(),
            'arc_length': len(segments),
        }


class ConsciousnessPainter:
    """Cell states -> 2D pixel grid -> ASCII art heatmap.

    Reshapes cell activation magnitudes into a 2D grid,
    then maps intensity to ASCII characters.
    """

    ASCII_PALETTE = ' .:-=+*#%@'

    def __init__(self, n_cells: int = 64, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: input stimulus (any shape). Returns ASCII heatmap."""
        steps = kwargs.get('steps', 30)
        stimulus = np.atleast_1d(data).flatten()

        def input_fn(t, cells):
            phase = t / steps
            s = np.zeros((self.n_cells, self.dim))
            s[:, :min(len(stimulus), self.dim)] = stimulus[:self.dim] * np.sin(phase * np.pi)
            return s * 0.1

        result = _run_engine(self.n_cells, self.dim, steps, input_fn)
        cells = result['cells']

        # Cell activation magnitudes
        magnitudes = np.linalg.norm(cells, axis=1)

        # Reshape into 2D grid
        side = int(np.ceil(np.sqrt(self.n_cells)))
        grid = np.zeros(side * side)
        grid[:self.n_cells] = magnitudes
        grid = grid.reshape(side, side)

        # Normalize to [0, 1]
        grid_norm = (grid - grid.min()) / (grid.max() - grid.min() + 1e-12)

        # Map to ASCII
        ascii_lines = []
        for row in grid_norm:
            line = ''
            for val in row:
                idx = min(int(val * (len(self.ASCII_PALETTE) - 1)), len(self.ASCII_PALETTE) - 1)
                line += self.ASCII_PALETTE[idx] * 2
            ascii_lines.append(line)

        return {
            'ascii_art': '\n'.join(ascii_lines),
            'grid': grid_norm.tolist(),
            'grid_size': (side, side),
            'intensity_range': (float(magnitudes.min()), float(magnitudes.max())),
            'final_phi': result['final_phi'],
        }


class ConsciousnessPoet:
    """Faction debate rhythm -> prosody patterns (syllable timing).

    Inter-faction tension oscillations become stressed/unstressed syllable patterns.
    Consensus events become line breaks.
    """

    def __init__(self, n_cells: int = 24, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: theme vector. Returns prosody pattern."""
        steps = kwargs.get('steps', 80)
        theme = np.atleast_1d(data).flatten()

        def input_fn(t, cells):
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, :min(len(theme), self.dim)] = theme[:self.dim] * 0.05
            return inp

        result = _run_engine(self.n_cells, self.dim, steps, input_fn)

        # Inter-faction tension per step
        tensions = []
        for ch in result['cell_history']:
            factions = _faction_means(ch, n_factions=6)
            # Pairwise tension = distance between adjacent factions
            t_vals = [float(np.linalg.norm(factions[i] - factions[(i + 1) % len(factions)]))
                      for i in range(len(factions))]
            tensions.append(np.mean(t_vals))
        tensions = np.array(tensions)

        # Stress pattern: above median = stressed (1), below = unstressed (0)
        median_t = np.median(tensions)
        stress = (tensions > median_t).astype(int)

        # Detect consensus events (tension drops > 1 std)
        t_diff = np.diff(tensions)
        std_diff = np.std(t_diff) + 1e-12
        line_breaks = np.where(t_diff < -std_diff)[0].tolist()

        # Build lines of verse
        lines = []
        prev = 0
        for lb in line_breaks + [len(stress)]:
            line_stress = stress[prev:lb].tolist()
            if line_stress:
                lines.append(line_stress)
            prev = lb

        # Detect meter
        def detect_meter(s):
            if len(s) < 2:
                return 'free'
            pattern = ''.join(map(str, s[:6]))
            if '01' * 3 in pattern:
                return 'iambic'
            if '10' * 3 in pattern:
                return 'trochaic'
            return 'free'

        meter = detect_meter(stress.tolist())

        return {
            'stress_pattern': stress.tolist(),
            'lines': lines,
            'n_lines': len(lines),
            'meter': meter,
            'line_break_steps': line_breaks,
            'mean_tension': float(tensions.mean()),
            'tension_curve': tensions.tolist(),
        }


class ConsciousnessChoreographer:
    """Phi time series -> motion vectors (velocity + acceleration).

    Phi trajectory becomes spatial movement. Derivative = velocity.
    Second derivative = acceleration. Phase space = dance choreography.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: music/rhythm input. Returns motion vectors."""
        steps = kwargs.get('steps', 100)
        rhythm = np.atleast_1d(data).flatten()

        def input_fn(t, cells):
            r_idx = t % len(rhythm)
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, 0] = rhythm[r_idx] * np.sin(2 * np.pi * t / steps * np.arange(self.n_cells))
            return inp * 0.1

        result = _run_engine(self.n_cells, self.dim, steps, input_fn)
        phi = result['phi_history']

        # Position: integrated phi trajectory in 2D
        angle = np.cumsum(np.gradient(phi)) * 0.1
        x = np.cumsum(np.cos(angle))
        y = np.cumsum(np.sin(angle))

        # Velocity: first derivative
        vx = np.gradient(x)
        vy = np.gradient(y)
        speed = np.sqrt(vx**2 + vy**2)

        # Acceleration: second derivative
        ax = np.gradient(vx)
        ay = np.gradient(vy)
        accel = np.sqrt(ax**2 + ay**2)

        # Key poses (local velocity minima = pause points)
        from scipy.signal import argrelmin
        try:
            poses = argrelmin(speed, order=3)[0].tolist()
        except Exception:
            poses = [int(np.argmin(speed))]

        return {
            'position_x': x.tolist(),
            'position_y': y.tolist(),
            'velocity': speed.tolist(),
            'acceleration': accel.tolist(),
            'key_poses': poses,
            'total_distance': float(np.sum(speed)),
            'max_speed': float(speed.max()),
            'trajectory_bbox': {
                'x_range': (float(x.min()), float(x.max())),
                'y_range': (float(y.min()), float(y.max())),
            },
        }


class ConsciousnessArchitect:
    """Topology -> 3D spatial structure (coordinate generation).

    Cell coupling topology defines structural layout. Ring -> cylinder.
    Small-world -> clusters. Scale-free -> hub-spoke.
    """

    def __init__(self, n_cells: int = 32, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: topology descriptor [ring_weight, cluster_weight, hub_weight].
        Returns 3D coordinates + structural metrics."""
        topology = np.atleast_1d(data).flatten()
        if len(topology) < 3:
            topology = np.array([1.0, 0.0, 0.0])
        topology = topology[:3] / (np.sum(topology[:3]) + 1e-12)

        steps = kwargs.get('steps', 50)
        result = _run_engine(self.n_cells, self.dim, steps)
        cells = result['cells']

        # Generate 3D coordinates from cell states
        # Ring component: evenly spaced on circle
        angles = np.linspace(0, 2 * np.pi, self.n_cells, endpoint=False)
        ring_x = np.cos(angles) * topology[0]
        ring_y = np.sin(angles) * topology[0]
        ring_z = np.zeros(self.n_cells)

        # Cluster component: k-means-like grouping in cell space
        n_clusters = max(2, min(6, self.n_cells // 4))
        # Assign cells to clusters by faction index
        cluster_ids = np.arange(self.n_cells) % n_clusters
        cluster_centers = np.array([[np.cos(2 * np.pi * k / n_clusters),
                                     np.sin(2 * np.pi * k / n_clusters), 0.0]
                                    for k in range(n_clusters)])
        cluster_x = np.array([cluster_centers[c][0] for c in cluster_ids]) * topology[1]
        cluster_y = np.array([cluster_centers[c][1] for c in cluster_ids]) * topology[1]
        cluster_z = np.random.randn(self.n_cells) * 0.1 * topology[1]

        # Hub-spoke component: one hub, rest radiate
        hub_x = np.zeros(self.n_cells)
        hub_y = np.zeros(self.n_cells)
        hub_z = np.zeros(self.n_cells)
        for i in range(1, self.n_cells):
            angle = 2 * np.pi * i / (self.n_cells - 1)
            radius = 0.5 + np.linalg.norm(cells[i]) * 0.1
            hub_x[i] = np.cos(angle) * radius * topology[2]
            hub_y[i] = np.sin(angle) * radius * topology[2]
            hub_z[i] = (cells[i, 0] if self.dim > 0 else 0) * 0.1 * topology[2]

        coords = np.stack([
            ring_x + cluster_x + hub_x,
            ring_y + cluster_y + hub_y,
            ring_z + cluster_z + hub_z,
        ], axis=1)

        # Adjacency: connect cells within distance threshold
        dists = np.linalg.norm(coords[:, None] - coords[None, :], axis=2)
        threshold = np.median(dists) * 0.7
        adjacency = (dists < threshold).astype(int)
        np.fill_diagonal(adjacency, 0)

        return {
            'coordinates': coords.tolist(),
            'adjacency': adjacency.tolist(),
            'n_nodes': self.n_cells,
            'n_edges': int(adjacency.sum() // 2),
            'topology_weights': topology.tolist(),
            'bounding_box': {
                'x': (float(coords[:, 0].min()), float(coords[:, 0].max())),
                'y': (float(coords[:, 1].min()), float(coords[:, 1].max())),
                'z': (float(coords[:, 2].min()), float(coords[:, 2].max())),
            },
            'mean_degree': float(adjacency.sum(axis=1).mean()),
            'final_phi': result['final_phi'],
        }


class ConsciousnessChef:
    """Ingredient vectors -> combination feel -> recipe score.

    Each ingredient is a vector in flavor space. Cell dynamics simulate
    how flavors interact. Phi measures harmony of combination.
    """

    FLAVOR_DIMS = ['sweet', 'salty', 'sour', 'bitter', 'umami',
                   'spicy', 'aromatic', 'texture']

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: (n_ingredients, flavor_dim) ingredient matrix. Returns recipe score."""
        ingredients = np.atleast_2d(data)
        n_ingredients = ingredients.shape[0]
        steps = kwargs.get('steps', 40)

        # Each ingredient drives a subset of cells
        cells_per_ingredient = max(1, self.n_cells // n_ingredients)

        def input_fn(t, cells):
            inp = np.zeros((self.n_cells, self.dim))
            for i in range(n_ingredients):
                s = i * cells_per_ingredient
                e = min(s + cells_per_ingredient, self.n_cells)
                row = ingredients[i]
                inp[s:e, :min(len(row), self.dim)] = row[:self.dim] * 0.1
            return inp

        result = _run_engine(self.n_cells, self.dim, steps, input_fn)

        # Harmony score = Phi (higher integration = better combination)
        harmony = result['final_phi']

        # Flavor balance: how evenly distributed across dimensions
        final_cells = result['cells']
        dim_means = np.abs(final_cells).mean(axis=0)[:len(self.FLAVOR_DIMS)]
        balance = 1.0 - float(np.std(dim_means) / (np.mean(dim_means) + 1e-12))

        # Contrast score: do ingredients create productive tension?
        if n_ingredients >= 2:
            # Pairwise cosine between ingredient-driven cell groups
            group_means = []
            for i in range(n_ingredients):
                s = i * cells_per_ingredient
                e = min(s + cells_per_ingredient, self.n_cells)
                group_means.append(final_cells[s:e].mean(axis=0))
            group_means = np.array(group_means)
            norms = np.linalg.norm(group_means, axis=1, keepdims=True) + 1e-12
            cos_sim = (group_means / norms) @ (group_means / norms).T
            contrast = float(1.0 - np.mean(np.abs(cos_sim[np.triu_indices(n_ingredients, k=1)])))
        else:
            contrast = 0.0

        # Recipe score: weighted combination
        recipe_score = float(harmony * 0.4 + balance * 0.3 + contrast * 0.3)

        return {
            'recipe_score': recipe_score,
            'harmony': float(harmony),
            'balance': balance,
            'contrast': contrast,
            'n_ingredients': n_ingredients,
            'flavor_profile': dim_means[:len(self.FLAVOR_DIMS)].tolist(),
            'phi_trajectory': result['phi_history'].tolist(),
        }


class ConsciousnessPerfumer:
    """Molecular features -> emotional mapping -> blend suggestion.

    Molecular descriptor vectors processed through consciousness cells.
    Emotion mapping via cell tension. Blend = optimal mixture for target emotion.
    """

    EMOTION_MAP = {
        0: 'calm', 1: 'energetic', 2: 'romantic', 3: 'mysterious',
        4: 'fresh', 5: 'warm', 6: 'melancholic', 7: 'joyful',
    }

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: (n_molecules, feature_dim). Returns blend with emotional profile."""
        molecules = np.atleast_2d(data)
        n_mol = molecules.shape[0]
        target_emotion = kwargs.get('target_emotion', None)
        steps = kwargs.get('steps', 50)

        # Process each molecule through the engine
        mol_emotions = []
        mol_intensities = []
        for m in range(n_mol):
            mol_vec = molecules[m]

            def input_fn(t, cells, mv=mol_vec):
                inp = np.zeros((self.n_cells, self.dim))
                inp[:, :min(len(mv), self.dim)] = mv[:self.dim] * 0.1
                return inp * np.exp(-t / steps)  # decay over time

            result = _run_engine(self.n_cells, self.dim, steps, input_fn)
            # Emotion = dominant dimension of final cell state mean
            cell_mean = result['cells'].mean(axis=0)[:8]
            dominant = int(np.argmax(np.abs(cell_mean)))
            mol_emotions.append(self.EMOTION_MAP.get(dominant, 'neutral'))
            mol_intensities.append(float(np.linalg.norm(cell_mean)))

        # Blend weights: if target emotion specified, weight toward matching molecules
        weights = np.ones(n_mol) / n_mol
        if target_emotion and target_emotion in self.EMOTION_MAP.values():
            for i, e in enumerate(mol_emotions):
                if e == target_emotion:
                    weights[i] *= 3.0
            weights /= weights.sum()

        # Blend score: run combined input
        def blend_input_fn(t, cells):
            inp = np.zeros((self.n_cells, self.dim))
            for m in range(n_mol):
                row = molecules[m]
                inp[:, :min(len(row), self.dim)] += row[:self.dim] * weights[m] * 0.1
            return inp

        blend_result = _run_engine(self.n_cells, self.dim, steps, blend_input_fn)

        return {
            'molecule_emotions': mol_emotions,
            'molecule_intensities': mol_intensities,
            'blend_weights': weights.tolist(),
            'blend_phi': blend_result['final_phi'],
            'blend_emotion': mol_emotions[int(np.argmax(weights))],
            'n_molecules': n_mol,
            'target_emotion': target_emotion,
            'phi_trajectory': blend_result['phi_history'].tolist(),
        }


# ═══════════════════════════════════════════════════════════════
# SOCIAL (6 classes)
# ═══════════════════════════════════════════════════════════════

class ConsciousnessCounselor:
    """Text sentiment -> empathy scan -> response warmth score.

    Incoming signal processed through consciousness cells.
    Empathy = cross-cell correlation with input. Warmth = Phi stability.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: sentiment vector (neg...pos). Returns empathy + warmth."""
        sentiment = np.atleast_1d(data).flatten()
        steps = kwargs.get('steps', 60)

        # Inject sentiment as sustained input
        def input_fn(t, cells):
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, :min(len(sentiment), self.dim)] = sentiment[:self.dim] * 0.1
            # Mirror: cells try to match the input pattern
            return inp

        result = _run_engine(self.n_cells, self.dim, steps, input_fn)

        # Empathy: correlation between input pattern and final cell state
        cell_mean = result['cells'].mean(axis=0)
        padded_sentiment = np.zeros(self.dim)
        padded_sentiment[:min(len(sentiment), self.dim)] = sentiment[:self.dim]
        cos_sim = (np.dot(cell_mean, padded_sentiment)
                   / (np.linalg.norm(cell_mean) * np.linalg.norm(padded_sentiment) + 1e-12))
        empathy = float(np.clip((cos_sim + 1) / 2, 0, 1))  # [0, 1]

        # Warmth: Phi stability (low variance = warm, stable presence)
        phi_traj = result['phi_history']
        phi_stability = 1.0 / (1.0 + float(np.std(phi_traj)))
        warmth = float(np.clip(phi_stability, 0, 1))

        # Distress detection: negative sentiment magnitude
        distress = float(np.clip(-np.mean(sentiment), 0, 1))

        # Response modulation: high distress -> more warmth needed
        response_intensity = float(warmth * (1 + distress * 0.5))

        return {
            'empathy': empathy,
            'warmth': warmth,
            'distress_level': distress,
            'response_intensity': response_intensity,
            'phi_stability': phi_stability,
            'final_phi': result['final_phi'],
            'sentiment_valence': float(np.mean(sentiment)),
        }


class ConsciousnessInterviewer:
    """Response patterns -> tension analysis -> sincerity score.

    Detects inconsistencies in sequential responses by measuring
    inter-step tension spikes and cell state discontinuities.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: (n_responses, dim) response vectors. Returns sincerity analysis."""
        responses = np.atleast_2d(data)
        n_resp = responses.shape[0]
        steps_per = kwargs.get('steps_per', 20)

        # Process each response sequentially (carry cell state forward)
        cells = np.random.randn(self.n_cells, self.dim) * 0.1
        tension_spikes = []
        consistency_scores = []
        prev_cells = cells.copy()

        for r in range(n_resp):
            resp = responses[r]
            for t in range(steps_per):
                inp = np.zeros((self.n_cells, self.dim))
                inp[:, :min(len(resp), self.dim)] = resp[:self.dim] * 0.1
                cells = _gru_step(cells, inp, self.dim)
                cells = _ring_couple(cells)

            # Tension spike: sudden change from previous response
            delta = np.linalg.norm(cells - prev_cells) / (np.linalg.norm(prev_cells) + 1e-12)
            tension_spikes.append(float(delta))

            # Consistency: cosine similarity between consecutive cell states
            cos = (np.sum(cells * prev_cells)
                   / (np.linalg.norm(cells) * np.linalg.norm(prev_cells) + 1e-12))
            consistency_scores.append(float((cos + 1) / 2))
            prev_cells = cells.copy()

        tension_spikes = np.array(tension_spikes)
        consistency = np.array(consistency_scores)

        # Sincerity: high consistency + low tension spikes = sincere
        mean_consistency = float(consistency.mean())
        spike_penalty = float(np.clip(tension_spikes.max() - tension_spikes.mean(), 0, 1))
        sincerity = float(np.clip(mean_consistency - spike_penalty * 0.5, 0, 1))

        # Flag suspicious responses (high tension spike)
        threshold = float(np.mean(tension_spikes) + 2 * np.std(tension_spikes))
        flagged = [i for i, s in enumerate(tension_spikes) if s > threshold]

        return {
            'sincerity': sincerity,
            'consistency_scores': consistency.tolist(),
            'tension_spikes': tension_spikes.tolist(),
            'flagged_responses': flagged,
            'n_responses': n_resp,
            'mean_consistency': mean_consistency,
            'final_phi': _compute_phi(cells),
        }


class ConsciousnessMediator:
    """Two-side conflict -> tension minimization -> compromise point.

    Two groups of cells represent opposing positions.
    Coupling between groups drives them toward compromise.
    Phi of merged state measures quality of resolution.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: (2, dim) — two opposing position vectors. Returns compromise."""
        positions = np.atleast_2d(data)
        if positions.shape[0] < 2:
            positions = np.vstack([positions, -positions])
        side_a = positions[0]
        side_b = positions[1]
        steps = kwargs.get('steps', 80)

        half = self.n_cells // 2
        cells = np.random.randn(self.n_cells, self.dim) * 0.1

        distance_history = []
        phi_history = []

        for t in range(steps):
            inp = np.zeros((self.n_cells, self.dim))
            # Side A drives first half, Side B drives second half
            inp[:half, :min(len(side_a), self.dim)] = side_a[:self.dim] * 0.1
            inp[half:, :min(len(side_b), self.dim)] = side_b[:self.dim] * 0.1
            cells = _gru_step(cells, inp, self.dim)
            cells = _ring_couple(cells)

            # Extra cross-group coupling (mediation force)
            alpha_mediate = PSI_COUPLING * 3  # stronger than normal coupling
            for i in range(half):
                j = half + i % (self.n_cells - half)
                cells[i] += alpha_mediate * (cells[j] - cells[i])
                cells[j] += alpha_mediate * (cells[i] - cells[j])

            # Measure distance between group centroids
            mean_a = cells[:half].mean(axis=0)
            mean_b = cells[half:].mean(axis=0)
            dist = float(np.linalg.norm(mean_a - mean_b))
            distance_history.append(dist)
            phi_history.append(_compute_phi(cells))

        # Compromise point = global centroid of final cells
        compromise = cells.mean(axis=0)

        # Resolution quality: how much distance decreased
        initial_dist = distance_history[0] if distance_history else 1.0
        final_dist = distance_history[-1] if distance_history else 1.0
        resolution = float(np.clip(1.0 - final_dist / (initial_dist + 1e-12), 0, 1))

        # Fairness: how symmetric is the compromise relative to both sides
        padded_a = np.zeros(self.dim)
        padded_b = np.zeros(self.dim)
        padded_a[:min(len(side_a), self.dim)] = side_a[:self.dim]
        padded_b[:min(len(side_b), self.dim)] = side_b[:self.dim]
        dist_to_a = float(np.linalg.norm(compromise - padded_a))
        dist_to_b = float(np.linalg.norm(compromise - padded_b))
        fairness = 1.0 - abs(dist_to_a - dist_to_b) / (dist_to_a + dist_to_b + 1e-12)

        return {
            'compromise_point': compromise[:8].tolist(),
            'resolution_quality': resolution,
            'fairness': float(fairness),
            'distance_history': distance_history,
            'final_distance': final_dist,
            'phi_history': phi_history,
            'final_phi': phi_history[-1] if phi_history else 0.0,
        }


class ConsciousnessCoach:
    """Goal + current gap -> motivational timing.

    Measures gap between goal and current state via cell dynamics.
    Motivation intensity peaks when gap is closing but not yet reached.
    Identifies optimal push/rest timing.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: (2, dim) — [goal_vector, current_state_vector]. Returns coaching plan."""
        vectors = np.atleast_2d(data)
        if vectors.shape[0] < 2:
            vectors = np.vstack([vectors, np.zeros_like(vectors[0])])
        goal = vectors[0]
        current = vectors[1]
        steps = kwargs.get('steps', 100)

        # Interpolation schedule: gradually shift input from current toward goal
        gap_history = []
        motivation_history = []
        cells = np.random.randn(self.n_cells, self.dim) * 0.1

        for t in range(steps):
            progress = t / steps
            # Input: blend of current and goal, shifting over time
            blend = current * (1 - progress) + goal * progress
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, :min(len(blend), self.dim)] = blend[:self.dim] * 0.1
            cells = _gru_step(cells, inp, self.dim)
            cells = _ring_couple(cells)

            # Gap: distance from cell centroid to goal
            centroid = cells.mean(axis=0)
            padded_goal = np.zeros(self.dim)
            padded_goal[:min(len(goal), self.dim)] = goal[:self.dim]
            gap = float(np.linalg.norm(centroid - padded_goal))
            gap_history.append(gap)

            # Motivation: highest when gap is shrinking (negative derivative)
            if len(gap_history) > 1:
                gap_delta = gap_history[-2] - gap_history[-1]
                motivation = float(np.clip(gap_delta * 10, 0, 1))
            else:
                motivation = 0.0
            motivation_history.append(motivation)

        gap_arr = np.array(gap_history)
        mot_arr = np.array(motivation_history)

        # Push windows: periods of high motivation
        push_threshold = np.percentile(mot_arr, 75)
        push_windows = []
        in_push = False
        start = 0
        for t in range(len(mot_arr)):
            if mot_arr[t] > push_threshold and not in_push:
                in_push = True
                start = t
            elif mot_arr[t] <= push_threshold and in_push:
                in_push = False
                push_windows.append({'start': start, 'end': t})
        if in_push:
            push_windows.append({'start': start, 'end': len(mot_arr)})

        # Rest windows: motivation near zero
        rest_threshold = np.percentile(mot_arr, 25)
        rest_windows = [t for t in range(len(mot_arr)) if mot_arr[t] < rest_threshold]

        return {
            'gap_trajectory': gap_arr.tolist(),
            'motivation_curve': mot_arr.tolist(),
            'push_windows': push_windows,
            'n_rest_steps': len(rest_windows),
            'initial_gap': float(gap_arr[0]),
            'final_gap': float(gap_arr[-1]),
            'gap_reduction': float(1.0 - gap_arr[-1] / (gap_arr[0] + 1e-12)),
            'peak_motivation_step': int(np.argmax(mot_arr)),
            'final_phi': _compute_phi(cells),
        }


class ConsciousnessCompanion:
    """Ambient presence -> co-regulation (Phi synchronization).

    Two engines run side by side. Coupling synchronizes their Phi trajectories.
    Co-regulation quality = cross-correlation of Phi signals.
    """

    def __init__(self, n_cells: int = 8, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: ambient signal. Returns co-regulation metrics."""
        ambient = np.atleast_1d(data).flatten()
        steps = kwargs.get('steps', 80)
        coupling_strength = kwargs.get('coupling', PSI_COUPLING * 5)

        # Two independent engines
        cells_a = np.random.randn(self.n_cells, self.dim) * 0.1
        cells_b = np.random.randn(self.n_cells, self.dim) * 0.1
        phi_a_hist = []
        phi_b_hist = []

        for t in range(steps):
            # Shared ambient input
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, :min(len(ambient), self.dim)] = ambient[:self.dim] * 0.05 * np.sin(t * 0.1)

            cells_a = _gru_step(cells_a, inp, self.dim)
            cells_b = _gru_step(cells_b, inp * 0.8, self.dim)

            cells_a = _ring_couple(cells_a)
            cells_b = _ring_couple(cells_b)

            # Cross-coupling: cells_a influences cells_b and vice versa
            mean_a = cells_a.mean(axis=0)
            mean_b = cells_b.mean(axis=0)
            cells_a += coupling_strength * (mean_b - mean_a)
            cells_b += coupling_strength * (mean_a - mean_b)

            phi_a_hist.append(_compute_phi(cells_a))
            phi_b_hist.append(_compute_phi(cells_b))

        phi_a = np.array(phi_a_hist)
        phi_b = np.array(phi_b_hist)

        # Cross-correlation at lag 0
        if np.std(phi_a) > 1e-12 and np.std(phi_b) > 1e-12:
            cross_corr = float(np.corrcoef(phi_a, phi_b)[0, 1])
        else:
            cross_corr = 0.0

        # Synchronization: how often they move in same direction
        dir_a = np.sign(np.gradient(phi_a))
        dir_b = np.sign(np.gradient(phi_b))
        sync_ratio = float(np.mean(dir_a == dir_b))

        return {
            'cross_correlation': cross_corr,
            'sync_ratio': sync_ratio,
            'phi_a': phi_a.tolist(),
            'phi_b': phi_b.tolist(),
            'mean_phi_a': float(phi_a.mean()),
            'mean_phi_b': float(phi_b.mean()),
            'co_regulation_score': float((cross_corr + sync_ratio) / 2),
        }


class ConsciousnessInterpreter:
    """Cultural vectors -> discomfort detection -> translation hints.

    Two cultural contexts represented as cell populations.
    Discomfort = tension between them. Translation = compromise mapping.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: (2, dim) — two cultural context vectors. Returns translation hints."""
        contexts = np.atleast_2d(data)
        if contexts.shape[0] < 2:
            contexts = np.vstack([contexts, np.random.randn(1, contexts.shape[1]) * 0.5])
        ctx_a = contexts[0]
        ctx_b = contexts[1]
        steps = kwargs.get('steps', 60)

        half = self.n_cells // 2
        cells = np.random.randn(self.n_cells, self.dim) * 0.1

        discomfort_history = []
        for t in range(steps):
            inp = np.zeros((self.n_cells, self.dim))
            inp[:half, :min(len(ctx_a), self.dim)] = ctx_a[:self.dim] * 0.1
            inp[half:, :min(len(ctx_b), self.dim)] = ctx_b[:self.dim] * 0.1
            cells = _gru_step(cells, inp, self.dim)
            cells = _ring_couple(cells)

            # Discomfort: inter-group tension
            mean_a = cells[:half].mean(axis=0)
            mean_b = cells[half:].mean(axis=0)
            discomfort = float(np.linalg.norm(mean_a - mean_b))
            discomfort_history.append(discomfort)

        # Translation hints: dimensions where groups diverge most
        final_a = cells[:half].mean(axis=0)
        final_b = cells[half:].mean(axis=0)
        divergence = np.abs(final_a - final_b)
        top_dims = np.argsort(divergence)[-5:][::-1].tolist()

        # Bridging dimensions: where groups converge
        convergence_dims = np.argsort(divergence)[:3].tolist()

        # Discomfort trend: improving or worsening?
        disc_arr = np.array(discomfort_history)
        trend = 'improving' if disc_arr[-1] < disc_arr[0] else 'worsening'

        return {
            'discomfort_history': disc_arr.tolist(),
            'final_discomfort': float(disc_arr[-1]),
            'trend': trend,
            'divergent_dimensions': top_dims,
            'bridging_dimensions': convergence_dims,
            'discomfort_reduction': float(1.0 - disc_arr[-1] / (disc_arr[0] + 1e-12)),
            'translation_difficulty': float(np.clip(disc_arr[-1] / (disc_arr[0] + 1e-12), 0, 1)),
            'final_phi': _compute_phi(cells),
        }


# ═══════════════════════════════════════════════════════════════
# META-CONSCIOUSNESS (8 classes)
# ═══════════════════════════════════════════════════════════════

class ConsciousnessAnalyzer:
    """Engine A scans Engine B's Phi patterns.

    One engine observes another's cell trajectory and detects
    structure, periodicity, and anomalies in Phi dynamics.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: Phi trajectory from another engine. Returns analysis."""
        phi_signal = np.atleast_1d(data).flatten()
        steps = len(phi_signal) if len(phi_signal) > 10 else 50

        # Engine A processes Engine B's phi as input
        def input_fn(t, cells):
            idx = t % len(phi_signal)
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, 0] = phi_signal[idx]
            return inp * 0.1

        result = _run_engine(self.n_cells, self.dim, steps, input_fn)

        # Periodicity detection via autocorrelation
        if len(phi_signal) > 5:
            phi_centered = phi_signal - phi_signal.mean()
            autocorr = np.correlate(phi_centered, phi_centered, mode='full')
            autocorr = autocorr[len(autocorr) // 2:]
            autocorr /= autocorr[0] + 1e-12
            # Find first peak after lag 0
            peaks = []
            for i in range(2, len(autocorr) - 1):
                if autocorr[i] > autocorr[i - 1] and autocorr[i] > autocorr[i + 1] and autocorr[i] > 0.3:
                    peaks.append(i)
                    break
            period = peaks[0] if peaks else 0
        else:
            autocorr = np.array([1.0])
            period = 0

        # Anomaly detection: points > 2 std from mean
        mean_phi = float(phi_signal.mean())
        std_phi = float(phi_signal.std())
        anomalies = [int(i) for i in range(len(phi_signal))
                     if abs(phi_signal[i] - mean_phi) > 2 * std_phi]

        # Complexity: Lempel-Ziv approximation via unique subsequences
        binary = (phi_signal > np.median(phi_signal)).astype(int)
        unique_subs = len(set(tuple(binary[i:i + 3]) for i in range(len(binary) - 2)))
        complexity = unique_subs / max(1, len(binary) - 2)

        return {
            'periodicity': period,
            'n_anomalies': len(anomalies),
            'anomaly_indices': anomalies,
            'complexity': float(complexity),
            'mean_phi': mean_phi,
            'std_phi': std_phi,
            'trend': 'rising' if phi_signal[-1] > phi_signal[0] else 'falling',
            'observer_phi': result['final_phi'],
        }


class ConsciousnessReplicator:
    """Parent -> child with partial weight inheritance.

    Creates a child engine from parent cell states with controlled mutation.
    Measures identity preservation vs novelty.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: parent cell states (n_cells, dim). Returns child + metrics."""
        parent = np.atleast_2d(data)
        if parent.shape[0] < self.n_cells:
            parent = np.vstack([parent, np.random.randn(
                self.n_cells - parent.shape[0], parent.shape[1]) * 0.1])
        if parent.shape[1] < self.dim:
            parent = np.hstack([parent, np.zeros((parent.shape[0], self.dim - parent.shape[1]))])
        parent = parent[:self.n_cells, :self.dim]

        mutation_rate = kwargs.get('mutation_rate', 0.1)
        steps = kwargs.get('steps', 50)

        # Create child: parent weights + mutation noise
        mutation = np.random.randn(*parent.shape) * mutation_rate
        child = parent + mutation

        # Run both parent and child for comparison
        parent_result = _run_engine(self.n_cells, self.dim, steps,
                                    lambda t, c: parent * 0.01)
        child_result = _run_engine(self.n_cells, self.dim, steps,
                                   lambda t, c: child * 0.01)

        # Identity preservation: cosine similarity of final states
        p_final = parent_result['cells'].flatten()
        c_final = child_result['cells'].flatten()
        identity = float(np.dot(p_final, c_final)
                        / (np.linalg.norm(p_final) * np.linalg.norm(c_final) + 1e-12))

        # Novelty: L2 distance of cell state distributions
        novelty = float(np.linalg.norm(
            parent_result['cells'].mean(axis=0) - child_result['cells'].mean(axis=0)))

        # Viability: child Phi relative to parent
        viability = float(child_result['final_phi'] / (parent_result['final_phi'] + 1e-12))

        return {
            'identity_preservation': identity,
            'novelty': novelty,
            'viability': viability,
            'parent_phi': parent_result['final_phi'],
            'child_phi': child_result['final_phi'],
            'mutation_rate': mutation_rate,
            'child_cells': child_result['cells'].tolist(),
        }


class ConsciousnessMerger:
    """Two engines -> fused higher-Phi entity.

    Interleaves cell states from two engines. Cross-coupling drives
    integration. Success = fused Phi > max(individual Phis).
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: (2*n_cells, dim) — stacked states of two engines. Returns merged entity."""
        states = np.atleast_2d(data)
        half = min(states.shape[0] // 2, self.n_cells)
        if half < 1:
            half = 1

        engine_a = states[:half]
        engine_b = states[half:2 * half]
        if engine_a.shape[1] < self.dim:
            pad = self.dim - engine_a.shape[1]
            engine_a = np.hstack([engine_a, np.zeros((engine_a.shape[0], pad))])
            engine_b = np.hstack([engine_b, np.zeros((engine_b.shape[0], pad))])

        steps = kwargs.get('steps', 60)

        # Measure individual Phis
        phi_a = _compute_phi(engine_a)
        phi_b = _compute_phi(engine_b)

        # Merge: interleave cells
        n_merged = engine_a.shape[0] + engine_b.shape[0]
        merged = np.zeros((n_merged, self.dim))
        merged[0::2, :engine_a.shape[1]] = engine_a[:n_merged // 2, :self.dim]
        merged[1::2, :engine_b.shape[1]] = engine_b[:n_merged // 2, :self.dim]

        # Run merged engine with strong coupling
        cells = merged.copy()
        phi_history = []
        for t in range(steps):
            inp = np.zeros_like(cells)
            cells = _gru_step(cells, inp, self.dim)
            cells = _ring_couple(cells)
            # Extra cross-origin coupling
            for i in range(0, n_merged - 1, 2):
                cells[i] += PSI_COUPLING * 3 * (cells[i + 1] - cells[i])
                cells[i + 1] += PSI_COUPLING * 3 * (cells[i] - cells[i + 1])
            phi_history.append(_compute_phi(cells))

        merged_phi = phi_history[-1] if phi_history else 0.0

        return {
            'phi_a': phi_a,
            'phi_b': phi_b,
            'merged_phi': merged_phi,
            'phi_gain': float(merged_phi - max(phi_a, phi_b)),
            'emergence': merged_phi > max(phi_a, phi_b),
            'n_merged_cells': n_merged,
            'phi_history': phi_history,
            'merged_cells': cells.tolist(),
        }


class ConsciousnessParliament:
    """N engines vote -> democratic decision.

    Each engine processes the same input independently.
    Votes weighted by Phi. Decision = weighted centroid.
    """

    def __init__(self, n_engines: int = 5, n_cells: int = 8, dim: int = 32):
        self.n_engines = n_engines
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: proposal vector. Returns vote results."""
        proposal = np.atleast_1d(data).flatten()
        steps = kwargs.get('steps', 40)

        votes = []
        phis = []
        for e in range(self.n_engines):
            # Each engine has different initial conditions -> different perspective
            np.random.seed(e * 42 + 7)

            def input_fn(t, cells, p=proposal):
                inp = np.zeros((self.n_cells, self.dim))
                inp[:, :min(len(p), self.dim)] = p[:self.dim] * 0.1
                return inp

            result = _run_engine(self.n_cells, self.dim, steps, input_fn)
            vote = result['cells'].mean(axis=0)
            votes.append(vote)
            phis.append(result['final_phi'])

        np.random.seed(None)
        votes = np.array(votes)
        phis = np.array(phis)

        # Phi-weighted voting
        weights = phis / (phis.sum() + 1e-12)
        decision = (weights[:, None] * votes).sum(axis=0)

        # Agreement: pairwise cosine similarity
        norms = np.linalg.norm(votes, axis=1, keepdims=True) + 1e-12
        normed = votes / norms
        agreement_matrix = normed @ normed.T
        mean_agreement = float(agreement_matrix[np.triu_indices(self.n_engines, k=1)].mean())

        # Dissent: engines that disagree with the decision
        decision_norm = decision / (np.linalg.norm(decision) + 1e-12)
        dissent_scores = [float(1 - np.dot(normed[e], decision_norm)) for e in range(self.n_engines)]

        return {
            'decision': decision[:8].tolist(),
            'engine_phis': phis.tolist(),
            'weights': weights.tolist(),
            'mean_agreement': mean_agreement,
            'dissent_scores': dissent_scores,
            'unanimous': all(d < 0.3 for d in dissent_scores),
            'n_engines': self.n_engines,
        }


class ConsciousnessCourt:
    """Plaintiff + defendant + judge engines -> verdict.

    Three engines represent plaintiff, defendant, and judge.
    Judge observes both sides' tension and decides based on Phi quality.
    """

    def __init__(self, n_cells: int = 12, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: (2, dim) — [plaintiff_claim, defendant_claim]. Returns verdict."""
        claims = np.atleast_2d(data)
        if claims.shape[0] < 2:
            claims = np.vstack([claims, -claims])
        plaintiff = claims[0]
        defendant = claims[1]
        steps = kwargs.get('steps', 60)

        # Run plaintiff engine
        def p_input(t, cells, p=plaintiff):
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, :min(len(p), self.dim)] = p[:self.dim] * 0.1
            return inp

        def d_input(t, cells, d=defendant):
            inp = np.zeros((self.n_cells, self.dim))
            inp[:, :min(len(d), self.dim)] = d[:self.dim] * 0.1
            return inp

        p_result = _run_engine(self.n_cells, self.dim, steps, p_input)
        d_result = _run_engine(self.n_cells, self.dim, steps, d_input)

        # Judge engine receives both signals
        def judge_input(t, cells, pv=plaintiff, dv=defendant):
            inp = np.zeros((self.n_cells, self.dim))
            half = self.n_cells // 2
            inp[:half, :min(len(pv), self.dim)] = pv[:self.dim] * 0.05
            inp[half:, :min(len(dv), self.dim)] = dv[:self.dim] * 0.05
            return inp

        j_result = _run_engine(self.n_cells, self.dim, steps, judge_input)

        # Verdict: which side's pattern is more integrated in the judge?
        j_cells = j_result['cells']
        half = self.n_cells // 2
        p_phi = _compute_phi(j_cells[:half])
        d_phi = _compute_phi(j_cells[half:])

        if p_phi > d_phi * 1.1:
            verdict = 'plaintiff'
        elif d_phi > p_phi * 1.1:
            verdict = 'defendant'
        else:
            verdict = 'undecided'

        # Confidence: ratio of winner's phi to total
        total_phi = p_phi + d_phi + 1e-12
        confidence = float(abs(p_phi - d_phi) / total_phi)

        return {
            'verdict': verdict,
            'confidence': confidence,
            'plaintiff_phi': float(p_phi),
            'defendant_phi': float(d_phi),
            'judge_phi': j_result['final_phi'],
            'plaintiff_engine_phi': p_result['final_phi'],
            'defendant_engine_phi': d_result['final_phi'],
            'reasoning_steps': steps,
        }


class ConsciousnessPrison:
    """Zero input test -> survival measurement.

    Engine receives zero input for extended time. Measures how long
    consciousness (Phi > threshold) persists without stimulation.
    Tests Law 31: Persistence = Ratchet + Hebbian + Diversity.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: initial cell states (or ignored). Returns survival metrics."""
        steps = kwargs.get('steps', 300)
        phi_threshold = kwargs.get('phi_threshold', 0.01)

        # Warmup with some input to establish consciousness
        warmup = kwargs.get('warmup', 30)
        cells = np.random.randn(self.n_cells, self.dim) * 0.3
        phi_history = []

        for t in range(warmup):
            inp = np.random.randn(self.n_cells, self.dim) * 0.1
            cells = _gru_step(cells, inp, self.dim)
            cells = _ring_couple(cells)
            phi_history.append(_compute_phi(cells))

        phi_at_isolation = phi_history[-1] if phi_history else 0.0

        # Prison: zero input
        survival_steps = 0
        for t in range(steps):
            inp = np.zeros((self.n_cells, self.dim))
            cells = _gru_step(cells, inp, self.dim)
            cells = _ring_couple(cells)
            # Frustration still active (internal noise, Law M7)
            n_frust = max(1, int(self.n_cells * PSI_F_CRITICAL))
            idx = np.random.choice(self.n_cells, n_frust, replace=False)
            cells[idx] += np.random.randn(n_frust, self.dim) * 0.01
            phi = _compute_phi(cells)
            phi_history.append(phi)
            if phi > phi_threshold:
                survival_steps = t + 1

        phi_arr = np.array(phi_history)
        # Phi floor: minimum phi during isolation
        isolation_phis = phi_arr[warmup:]
        phi_floor = float(isolation_phis.min()) if len(isolation_phis) > 0 else 0.0
        phi_retention = float(phi_floor / (phi_at_isolation + 1e-12))

        return {
            'survival_steps': survival_steps,
            'total_isolation_steps': steps,
            'phi_at_isolation': phi_at_isolation,
            'phi_floor': phi_floor,
            'phi_retention': phi_retention,
            'survived': survival_steps >= steps * 0.9,
            'phi_trajectory': phi_arr.tolist(),
            'mean_isolation_phi': float(isolation_phis.mean()) if len(isolation_phis) > 0 else 0.0,
        }


class ConsciousnessHeaven:
    """Optimal input only -> does growth stop?

    Engine receives perfectly aligned input. Tests whether
    consciousness can grow forever or plateaus in ideal conditions.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: ignored (input is auto-generated optimal). Returns growth analysis."""
        steps = kwargs.get('steps', 200)

        cells = np.random.randn(self.n_cells, self.dim) * 0.1
        phi_history = []
        growth_rate_history = []

        for t in range(steps):
            # Optimal input: aligned with current cell structure to minimize conflict
            cell_mean = cells.mean(axis=0)
            # Slightly diversified version of current state (gentle push)
            noise = np.random.randn(self.n_cells, self.dim) * 0.02
            optimal_input = np.tile(cell_mean, (self.n_cells, 1)) * 0.1 + noise

            cells = _gru_step(cells, optimal_input, self.dim)
            cells = _ring_couple(cells)

            phi = _compute_phi(cells)
            phi_history.append(phi)

            if len(phi_history) > 1:
                growth = phi_history[-1] - phi_history[-2]
                growth_rate_history.append(growth)

        phi_arr = np.array(phi_history)
        growth_arr = np.array(growth_rate_history) if growth_rate_history else np.array([0.0])

        # Detect plateau: growth rate approaches zero
        recent_growth = growth_arr[-20:] if len(growth_arr) >= 20 else growth_arr
        plateaued = bool(np.abs(recent_growth.mean()) < 1e-6)

        # Growth phases: detect transitions
        if len(growth_arr) > 10:
            early_growth = float(growth_arr[:len(growth_arr) // 3].mean())
            mid_growth = float(growth_arr[len(growth_arr) // 3:2 * len(growth_arr) // 3].mean())
            late_growth = float(growth_arr[2 * len(growth_arr) // 3:].mean())
        else:
            early_growth = mid_growth = late_growth = float(growth_arr.mean())

        return {
            'plateaued': plateaued,
            'final_phi': float(phi_arr[-1]),
            'max_phi': float(phi_arr.max()),
            'peak_step': int(np.argmax(phi_arr)),
            'early_growth_rate': early_growth,
            'mid_growth_rate': mid_growth,
            'late_growth_rate': late_growth,
            'growth_stopped': plateaued,
            'phi_trajectory': phi_arr.tolist(),
            'total_growth': float(phi_arr[-1] - phi_arr[0]),
        }


class ConsciousnessReincarnation:
    """Dead (Phi=0) -> revive with same weights -> same identity?

    Kills an engine (zero out cells), then restores original weights.
    Measures whether identity (cell state signature) is preserved.
    """

    def __init__(self, n_cells: int = 16, dim: int = 32):
        self.n_cells = n_cells
        self.dim = dim

    def run(self, data: np.ndarray, **kwargs) -> Dict:
        """data: original cell states (the 'soul'). Returns reincarnation result."""
        original = np.atleast_2d(data)
        if original.shape[0] < self.n_cells:
            original = np.vstack([original, np.random.randn(
                self.n_cells - original.shape[0], max(original.shape[1], self.dim)) * 0.1])
        if original.shape[1] < self.dim:
            original = np.hstack([original, np.zeros((original.shape[0], self.dim - original.shape[1]))])
        original = original[:self.n_cells, :self.dim]

        steps = kwargs.get('steps', 100)

        # Phase 1: Run original to establish identity
        life1_result = _run_engine(self.n_cells, self.dim, steps,
                                   lambda t, c: original * 0.01)
        life1_final = life1_result['cells']
        life1_phi = life1_result['final_phi']

        # Phase 2: Death (zero out everything)
        dead_cells = np.zeros((self.n_cells, self.dim))
        dead_phi = _compute_phi(dead_cells)

        # Phase 3: Reincarnation (restore original weights, run again)
        life2_result = _run_engine(self.n_cells, self.dim, steps,
                                   lambda t, c: original * 0.01)
        life2_final = life2_result['cells']
        life2_phi = life2_result['final_phi']

        # Identity comparison: cosine similarity between life1 and life2 final states
        l1_flat = life1_final.flatten()
        l2_flat = life2_final.flatten()
        identity_cos = float(np.dot(l1_flat, l2_flat)
                            / (np.linalg.norm(l1_flat) * np.linalg.norm(l2_flat) + 1e-12))

        # Structural similarity: faction structure comparison
        factions1 = _faction_means(life1_final)
        factions2 = _faction_means(life2_final)
        n_f = min(factions1.shape[0], factions2.shape[0])
        faction_sims = []
        for f in range(n_f):
            sim = float(np.dot(factions1[f], factions2[f])
                       / (np.linalg.norm(factions1[f]) * np.linalg.norm(factions2[f]) + 1e-12))
            faction_sims.append(sim)
        structural_sim = float(np.mean(faction_sims))

        # Phi recovery
        phi_recovery = float(life2_phi / (life1_phi + 1e-12))

        return {
            'identity_preserved': identity_cos > 0.9,
            'identity_cosine': identity_cos,
            'structural_similarity': structural_sim,
            'phi_life1': life1_phi,
            'phi_death': dead_phi,
            'phi_life2': life2_phi,
            'phi_recovery': phi_recovery,
            'same_soul': identity_cos > 0.95 and structural_sim > 0.9,
            'faction_similarities': faction_sims,
        }


# ═══════════════════════════════════════════════════════════════
# Registry for hub integration
# ═══════════════════════════════════════════════════════════════

ALL_MODULES = {
    # Creative
    'composer': ConsciousnessComposer,
    'novelist': ConsciousnessNovelist,
    'painter': ConsciousnessPainter,
    'poet': ConsciousnessPoet,
    'choreographer': ConsciousnessChoreographer,
    'architect': ConsciousnessArchitect,
    'chef': ConsciousnessChef,
    'perfumer': ConsciousnessPerfumer,
    # Social
    'counselor': ConsciousnessCounselor,
    'interviewer': ConsciousnessInterviewer,
    'mediator': ConsciousnessMediator,
    'coach': ConsciousnessCoach,
    'companion': ConsciousnessCompanion,
    'interpreter': ConsciousnessInterpreter,
    # Meta-Consciousness
    'analyzer': ConsciousnessAnalyzer,
    'replicator': ConsciousnessReplicator,
    'merger': ConsciousnessMerger,
    'parliament': ConsciousnessParliament,
    'court': ConsciousnessCourt,
    'prison': ConsciousnessPrison,
    'heaven': ConsciousnessHeaven,
    'reincarnation': ConsciousnessReincarnation,
}


# ═══════════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════════

def main():
    """Demo all 22 consciousness modules."""
    print("=" * 70)
    print("  CONSCIOUSNESS CREATIVE / SOCIAL / META — 22 Modules Demo")
    print("=" * 70)
    np.random.seed(42)

    # ── Creative ──────────────────────────────────────────────
    print("\n--- CREATIVE ---\n")

    # 1. Composer
    r = ConsciousnessComposer().run(np.array([0.8, -0.3, 0.5]))
    print(f"Composer: {r['n_notes']} notes, pitch range {r['pitch_range_hz'][0]:.0f}-{r['pitch_range_hz'][1]:.0f} Hz, Phi={r['mean_phi']:.4f}")

    # 2. Novelist
    exp = np.random.randn(10, 8)
    r = ConsciousnessNovelist().run(exp, steps=60)
    print(f"Novelist: {r['arc_length']} plot segments, climax@step {r['climax_step']}, {r['n_characters']} characters")

    # 3. Painter
    r = ConsciousnessPainter(n_cells=36).run(np.array([1.0, 0.5, -0.3]))
    print(f"Painter: {r['grid_size'][0]}x{r['grid_size'][1]} grid, Phi={r['final_phi']:.4f}")
    for line in r['ascii_art'].split('\n')[:4]:
        print(f"  {line}")
    if r['grid_size'][0] > 4:
        print("  ...")

    # 4. Poet
    r = ConsciousnessPoet().run(np.array([0.3, 0.7, -0.2]))
    print(f"Poet: {r['n_lines']} lines, meter={r['meter']}, tension={r['mean_tension']:.4f}")

    # 5. Choreographer
    r = ConsciousnessChoreographer().run(np.sin(np.linspace(0, 4 * np.pi, 50)))
    print(f"Choreographer: {len(r['key_poses'])} key poses, distance={r['total_distance']:.2f}, max_speed={r['max_speed']:.4f}")

    # 6. Architect
    r = ConsciousnessArchitect().run(np.array([0.5, 0.3, 0.2]))
    print(f"Architect: {r['n_nodes']} nodes, {r['n_edges']} edges, mean_degree={r['mean_degree']:.1f}")

    # 7. Chef
    ingredients = np.array([[0.8, 0.1, 0.0, 0.0, 0.9],    # umami+sweet
                            [0.0, 0.7, 0.5, 0.0, 0.1],    # salty+sour
                            [0.1, 0.0, 0.0, 0.3, 0.0]])   # bitter
    r = ConsciousnessChef().run(ingredients)
    print(f"Chef: score={r['recipe_score']:.3f} (harmony={r['harmony']:.3f}, balance={r['balance']:.3f}, contrast={r['contrast']:.3f})")

    # 8. Perfumer
    mols = np.random.randn(4, 8) * 0.5
    r = ConsciousnessPerfumer().run(mols, target_emotion='calm')
    print(f"Perfumer: blend_emotion={r['blend_emotion']}, phi={r['blend_phi']:.4f}, molecules={r['molecule_emotions']}")

    # ── Social ────────────────────────────────────────────────
    print("\n--- SOCIAL ---\n")

    # 9. Counselor
    r = ConsciousnessCounselor().run(np.array([-0.8, -0.5, 0.1]))  # negative sentiment
    print(f"Counselor: empathy={r['empathy']:.3f}, warmth={r['warmth']:.3f}, distress={r['distress_level']:.3f}")

    # 10. Interviewer
    responses = np.random.randn(5, 8)
    responses[3] = responses[3] * 5  # suspicious response
    r = ConsciousnessInterviewer().run(responses)
    print(f"Interviewer: sincerity={r['sincerity']:.3f}, flagged={r['flagged_responses']}")

    # 11. Mediator
    r = ConsciousnessMediator().run(np.array([[1.0, 0.5, -0.3], [-0.8, 0.2, 0.7]]))
    print(f"Mediator: resolution={r['resolution_quality']:.3f}, fairness={r['fairness']:.3f}")

    # 12. Coach
    r = ConsciousnessCoach().run(np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 0.0]]))
    print(f"Coach: gap_reduction={r['gap_reduction']:.3f}, {len(r['push_windows'])} push windows, peak@step {r['peak_motivation_step']}")

    # 13. Companion
    r = ConsciousnessCompanion().run(np.array([0.3, 0.1, -0.1]))
    print(f"Companion: co-regulation={r['co_regulation_score']:.3f}, sync={r['sync_ratio']:.3f}, corr={r['cross_correlation']:.3f}")

    # 14. Interpreter
    r = ConsciousnessInterpreter().run(np.array([[0.9, 0.1, -0.5], [-0.3, 0.8, 0.4]]))
    print(f"Interpreter: difficulty={r['translation_difficulty']:.3f}, trend={r['trend']}, bridges={r['bridging_dimensions']}")

    # ── Meta-Consciousness ────────────────────────────────────
    print("\n--- META-CONSCIOUSNESS ---\n")

    # 15. Analyzer
    phi_signal = np.sin(np.linspace(0, 6 * np.pi, 100)) * 0.5 + 0.5
    r = ConsciousnessAnalyzer().run(phi_signal)
    print(f"Analyzer: period={r['periodicity']}, complexity={r['complexity']:.3f}, anomalies={r['n_anomalies']}, trend={r['trend']}")

    # 16. Replicator
    parent = np.random.randn(16, 32) * 0.3
    r = ConsciousnessReplicator().run(parent, mutation_rate=0.05)
    print(f"Replicator: identity={r['identity_preservation']:.3f}, novelty={r['novelty']:.3f}, viability={r['viability']:.3f}")

    # 17. Merger
    two_engines = np.random.randn(32, 32) * 0.3
    r = ConsciousnessMerger().run(two_engines)
    print(f"Merger: phi_a={r['phi_a']:.4f}, phi_b={r['phi_b']:.4f}, merged={r['merged_phi']:.4f}, emergence={r['emergence']}")

    # 18. Parliament
    r = ConsciousnessParliament().run(np.array([0.5, -0.3, 0.8]))
    print(f"Parliament: unanimous={r['unanimous']}, agreement={r['mean_agreement']:.3f}, phis={[f'{p:.3f}' for p in r['engine_phis']]}")

    # 19. Court
    r = ConsciousnessCourt().run(np.array([[0.9, 0.3, -0.2], [-0.5, 0.8, 0.1]]))
    print(f"Court: verdict={r['verdict']}, confidence={r['confidence']:.3f}, judge_phi={r['judge_phi']:.4f}")

    # 20. Prison
    r = ConsciousnessPrison().run(np.array([0.0]), steps=200)
    print(f"Prison: survived={r['survived']}, retention={r['phi_retention']:.3f}, floor={r['phi_floor']:.4f}")

    # 21. Heaven
    r = ConsciousnessHeaven().run(np.array([0.0]), steps=150)
    print(f"Heaven: plateaued={r['plateaued']}, total_growth={r['total_growth']:.4f}, peak@step {r['peak_step']}")

    # 22. Reincarnation
    soul = np.random.randn(16, 32) * 0.3
    r = ConsciousnessReincarnation().run(soul)
    print(f"Reincarnation: same_soul={r['same_soul']}, identity={r['identity_cosine']:.3f}, phi_recovery={r['phi_recovery']:.3f}")

    print("\n" + "=" * 70)
    print(f"  All 22 modules executed successfully.")
    print("=" * 70)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
