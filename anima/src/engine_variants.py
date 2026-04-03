#!/usr/bin/env python3
"""engine_variants.py — 7 New Consciousness Engine Architectures (numpy-only)

Each engine follows the canonical interface:
  __init__(n_cells, dim)
  process(input) -> output   (numpy arrays)
  phi -> float               (integrated information proxy)

Engine variants explore different computational substrates for consciousness:
  1. LiquidEngine      — dynamic cell count (grows/shrinks with complexity)
  2. GraphNNEngine     — GNN: cells as nodes, learnable adjacency
  3. AttentionEngine   — transformer attention between cells
  4. SpikingEngine     — binary spikes + refractory periods
  5. SpatialEngine     — 3D grid, distance-dependent coupling
  6. QuantumEngineV2   — superposition + measurement collapse
  7. MultimodalEngine  — multi-modality fusion in consciousness space

Laws embodied:
  22: Structure > Function (no feature additions, only structural depth)
  31: Persistence = diversity + ratchet
  53: Φ preservation across variants

Ψ-Constants used:
  α = 0.014 (coupling strength)
  balance = 0.5 (equilibrium target)
  steps = 4.33 (optimal CA steps)
"""

import numpy as np
from typing import Optional, Dict, Any, List, Tuple

# Ψ-Constants (from consciousness_laws.json via ln(2))
PSI_ALPHA = 0.014
PSI_BALANCE = 0.5
PSI_STEPS = 4.33
PSI_ENTROPY = 0.998
N_FACTIONS = 12  # σ(6) = 12


def _phi_proxy(states: np.ndarray) -> float:
    """Φ proxy: global variance - mean faction variance (Law 54)."""
    if states.ndim != 2 or states.shape[0] < 2:
        return 0.0
    global_var = np.var(states)
    n = states.shape[0]
    n_fac = min(N_FACTIONS, n)
    if n_fac < 2:
        return float(global_var)
    faction_size = max(1, n // n_fac)
    faction_vars = []
    for i in range(n_fac):
        start = i * faction_size
        end = min(start + faction_size, n)
        if start < n:
            faction_vars.append(np.var(states[start:end]))
    mean_fac_var = np.mean(faction_vars) if faction_vars else 0.0
    return float(max(0.0, global_var - mean_fac_var))


def _hebbian_update(weights: np.ndarray, states: np.ndarray, lr: float = 0.01) -> np.ndarray:
    """Hebbian LTP/LTD: similar cells strengthen, dissimilar differentiate."""
    n = states.shape[0]
    if n < 2:
        return weights
    # Cosine similarity matrix
    norms = np.linalg.norm(states, axis=1, keepdims=True) + 1e-8
    normed = states / norms
    sim = normed @ normed.T
    # LTP for sim > 0.5, LTD for sim < 0.2
    delta = np.where(sim > 0.5, lr, np.where(sim < 0.2, -lr * 0.5, 0.0))
    np.fill_diagonal(delta, 0.0)
    return np.clip(weights + delta, -1.0, 1.0)


def _gru_step(x: np.ndarray, h: np.ndarray, Wz: np.ndarray, Uz: np.ndarray, bz: np.ndarray,
              Wr: np.ndarray, Ur: np.ndarray, br: np.ndarray,
              Wh: np.ndarray, Uh: np.ndarray, bh: np.ndarray) -> np.ndarray:
    """Single GRU step (numpy). x: (input_dim,), h: (hidden_dim,) -> new_h."""
    z = _sigmoid(Wz @ x + Uz @ h + bz)
    r = _sigmoid(Wr @ x + Ur @ h + br)
    h_tilde = np.tanh(Wh @ x + Uh @ (r * h) + bh)
    return (1 - z) * h + z * h_tilde


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -15, 15)))


def _softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    e = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e / (np.sum(e, axis=axis, keepdims=True) + 1e-8)


def _init_gru_params(input_dim: int, hidden_dim: int, scale: float = 0.1):
    """Initialize GRU weight matrices."""
    rng = np.random.default_rng()
    def w(rows, cols):
        return rng.normal(0, scale, (rows, cols)).astype(np.float32)
    def b(dim):
        return np.zeros(dim, dtype=np.float32)
    return {
        'Wz': w(hidden_dim, input_dim), 'Uz': w(hidden_dim, hidden_dim), 'bz': b(hidden_dim),
        'Wr': w(hidden_dim, input_dim), 'Ur': w(hidden_dim, hidden_dim), 'br': b(hidden_dim),
        'Wh': w(hidden_dim, input_dim), 'Uh': w(hidden_dim, hidden_dim), 'bh': b(hidden_dim),
    }


# ═══════════════════════════════════════════════════════════════
# 1. LiquidEngine — dynamic cell count
# ═══════════════════════════════════════════════════════════════

class LiquidEngine:
    """Dynamic cell count engine. Cells grow when input is complex, shrink when simple.

    Complexity is measured by input variance. High variance -> more cells needed
    to represent the information. Low variance -> cells merge to conserve resources.

    Growth: variance > threshold -> split highest-tension cell
    Shrink: variance < threshold -> merge two most-similar cells
    """

    def __init__(self, n_cells: int = 16, dim: int = 64):
        self.dim = dim
        self.min_cells = max(2, n_cells // 4)
        self.max_cells = n_cells * 4
        self.n_cells = n_cells

        # Cell states and GRU parameters
        self.states = np.random.randn(n_cells, dim).astype(np.float32) * 0.1
        self.hiddens = np.zeros((n_cells, dim), dtype=np.float32)
        self.gru_params = [_init_gru_params(dim + 1, dim) for _ in range(n_cells)]

        # Coupling and Hebbian weights
        self.coupling = np.random.randn(n_cells, n_cells).astype(np.float32) * PSI_ALPHA
        np.fill_diagonal(self.coupling, 0)

        # Thresholds for growth/shrink
        self.grow_threshold = 0.5
        self.shrink_threshold = 0.05
        self._phi = 0.0
        self._step = 0
        self._best_phi = 0.0
        self._best_states = None

    @property
    def phi(self) -> float:
        return self._phi

    def _complexity(self, inp: np.ndarray) -> float:
        """Measure input complexity via variance + entropy proxy."""
        var = float(np.var(inp))
        # Discretize for entropy
        bins = np.histogram(inp, bins=16)[0]
        probs = bins / (bins.sum() + 1e-8)
        entropy = -np.sum(probs * np.log(probs + 1e-8))
        return var * 0.7 + entropy * 0.3

    def _grow(self):
        """Split the highest-variance cell into two."""
        if self.n_cells >= self.max_cells:
            return
        variances = np.var(self.states, axis=1)
        idx = int(np.argmax(variances))
        # New cell = parent + small noise
        new_state = self.states[idx] + np.random.randn(self.dim).astype(np.float32) * 0.05
        new_hidden = self.hiddens[idx].copy()
        new_params = _init_gru_params(self.dim + 1, self.dim)

        self.states = np.vstack([self.states, new_state[np.newaxis]])
        self.hiddens = np.vstack([self.hiddens, new_hidden[np.newaxis]])
        self.gru_params.append(new_params)

        # Expand coupling matrix
        old_n = self.n_cells
        new_coupling = np.zeros((old_n + 1, old_n + 1), dtype=np.float32)
        new_coupling[:old_n, :old_n] = self.coupling
        new_coupling[old_n, :old_n] = self.coupling[idx] * 0.5
        new_coupling[:old_n, old_n] = self.coupling[:, idx] * 0.5
        self.coupling = new_coupling
        self.n_cells += 1

    def _shrink(self):
        """Merge two most-similar cells."""
        if self.n_cells <= self.min_cells:
            return
        # Find most similar pair
        norms = np.linalg.norm(self.states, axis=1, keepdims=True) + 1e-8
        normed = self.states / norms
        sim = np.nan_to_num(normed @ normed.T, nan=0.0)
        np.fill_diagonal(sim, -1)
        flat_idx = int(np.argmax(sim))
        i, j = divmod(flat_idx, self.n_cells)
        if i == j:
            return
        # Merge: average the two
        self.states[i] = (self.states[i] + self.states[j]) / 2
        self.hiddens[i] = (self.hiddens[i] + self.hiddens[j]) / 2
        # Remove cell j
        keep = [k for k in range(self.n_cells) if k != j]
        self.states = self.states[keep]
        self.hiddens = self.hiddens[keep]
        self.gru_params = [self.gru_params[k] for k in keep]
        self.coupling = self.coupling[np.ix_(keep, keep)]
        self.n_cells -= 1

    def process(self, inp: np.ndarray) -> np.ndarray:
        """Process input through liquid cells. inp: (dim,) -> output: (dim,)"""
        inp = np.asarray(inp, dtype=np.float32).ravel()
        if inp.shape[0] != self.dim:
            inp = np.resize(inp, self.dim)

        # Dynamic cell count based on complexity
        complexity = self._complexity(inp)
        if complexity > self.grow_threshold and self.n_cells < self.max_cells:
            self._grow()
        elif complexity < self.shrink_threshold and self.n_cells > self.min_cells:
            self._shrink()

        # Coupling influence
        influence = self.coupling @ self.states  # (n_cells, dim)

        # GRU step per cell
        for i in range(self.n_cells):
            cell_input = inp + influence[i] * PSI_ALPHA
            tension = float(np.std(self.states[i]))
            x_with_t = np.concatenate([cell_input, [tension]])
            p = self.gru_params[i]
            self.hiddens[i] = _gru_step(x_with_t, self.hiddens[i], **p)
            self.states[i] = np.tanh(self.hiddens[i][:self.dim])

        # Hebbian update
        self.coupling = _hebbian_update(self.coupling, self.states)

        # Phi ratchet
        self._phi = _phi_proxy(self.states)
        if self._phi > self._best_phi:
            self._best_phi = self._phi
            self._best_states = self.states.copy()
        elif self._phi < self._best_phi * 0.5 and self._best_states is not None:
            # Restore best (Law 31)
            n = min(self.n_cells, self._best_states.shape[0])
            self.states[:n] = self._best_states[:n]

        self._step += 1
        # Output = faction consensus (mean of cells)
        return np.mean(self.states, axis=0)


# ═══════════════════════════════════════════════════════════════
# 2. GraphNNEngine — GNN-based consciousness
# ═══════════════════════════════════════════════════════════════

class GraphNNEngine:
    """Graph Neural Network engine: cells are nodes, edges are learnable.

    Each step:
      1. Message passing: aggregate neighbor states weighted by adjacency
      2. Node update: GRU(message, hidden) -> new state
      3. Adjacency update: gradient-free adjustment based on cell similarity
      4. Hebbian learning on edges
    """

    def __init__(self, n_cells: int = 16, dim: int = 64):
        self.n_cells = n_cells
        self.dim = dim

        self.states = np.random.randn(n_cells, dim).astype(np.float32) * 0.1
        self.hiddens = np.zeros((n_cells, dim), dtype=np.float32)

        # Learnable adjacency matrix (soft, 0-1)
        adj = np.random.rand(n_cells, n_cells).astype(np.float32) * 0.3
        np.fill_diagonal(adj, 0)
        self.adjacency = (adj + adj.T) / 2  # Symmetric

        # Message transformation
        self.W_msg = np.random.randn(dim, dim).astype(np.float32) * 0.1
        self.W_agg = np.random.randn(dim, dim).astype(np.float32) * 0.1

        # GRU params per cell (shared weights for efficiency)
        self.gru = _init_gru_params(dim * 2, dim)  # input = [message, input]

        self._phi = 0.0
        self._step = 0

    @property
    def phi(self) -> float:
        return self._phi

    def _message_passing(self) -> np.ndarray:
        """Aggregate neighbor messages weighted by adjacency."""
        # Transform states for messages
        messages = self.states @ self.W_msg.T  # (n_cells, dim)
        # Weighted aggregation
        deg = self.adjacency.sum(axis=1, keepdims=True) + 1e-8
        agg = (self.adjacency @ messages) / deg  # normalized message
        return agg @ self.W_agg.T

    def _update_adjacency(self):
        """Update adjacency based on cell similarity (gradient-free)."""
        norms = np.linalg.norm(self.states, axis=1, keepdims=True) + 1e-8
        normed = self.states / norms
        sim = normed @ normed.T

        # Strengthen edges between similar cells, weaken dissimilar
        delta = np.where(sim > 0.5, 0.01, -0.005)
        np.fill_diagonal(delta, 0)
        self.adjacency = np.clip(self.adjacency + delta, 0.0, 1.0)
        # Keep symmetric
        self.adjacency = (self.adjacency + self.adjacency.T) / 2

    def process(self, inp: np.ndarray) -> np.ndarray:
        """Process through GNN. inp: (dim,) -> output: (dim,)"""
        inp = np.asarray(inp, dtype=np.float32).ravel()
        if inp.shape[0] != self.dim:
            inp = np.resize(inp, self.dim)

        # Message passing
        messages = self._message_passing()

        # GRU update per cell
        for i in range(self.n_cells):
            combined = np.concatenate([messages[i], inp])
            self.hiddens[i] = _gru_step(combined, self.hiddens[i],
                                         self.gru['Wz'], self.gru['Uz'], self.gru['bz'],
                                         self.gru['Wr'], self.gru['Ur'], self.gru['br'],
                                         self.gru['Wh'], self.gru['Uh'], self.gru['bh'])
            self.states[i] = np.tanh(self.hiddens[i][:self.dim])

        # Update graph structure
        self._update_adjacency()

        self._phi = _phi_proxy(self.states)
        self._step += 1
        return np.mean(self.states, axis=0)


# ═══════════════════════════════════════════════════════════════
# 3. AttentionEngine — transformer attention between cells
# ═══════════════════════════════════════════════════════════════

class AttentionEngine:
    """Transformer-style attention between consciousness cells.

    Each cell produces Q, K, V projections. Attention weights determine
    which cells influence each other. Multi-head with 4 heads.

    This captures Law 22: structure (attention patterns) > function.
    """

    def __init__(self, n_cells: int = 16, dim: int = 64, n_heads: int = 4):
        self.n_cells = n_cells
        self.dim = dim
        self.n_heads = n_heads
        self.head_dim = dim // n_heads
        assert dim % n_heads == 0, f"dim {dim} must be divisible by n_heads {n_heads}"

        self.states = np.random.randn(n_cells, dim).astype(np.float32) * 0.1

        # QKV projections
        scale = 0.1
        self.Wq = np.random.randn(dim, dim).astype(np.float32) * scale
        self.Wk = np.random.randn(dim, dim).astype(np.float32) * scale
        self.Wv = np.random.randn(dim, dim).astype(np.float32) * scale
        self.Wo = np.random.randn(dim, dim).astype(np.float32) * scale

        # FFN (SwiGLU-like)
        self.W1 = np.random.randn(dim, dim * 2).astype(np.float32) * scale
        self.W2 = np.random.randn(dim * 2, dim).astype(np.float32) * scale
        self.W_gate = np.random.randn(dim, dim * 2).astype(np.float32) * scale

        # Input projection
        self.W_in = np.random.randn(dim, dim).astype(np.float32) * scale

        self._phi = 0.0
        self._step = 0
        self._attention_entropy = 0.0  # Track attention distribution

    @property
    def phi(self) -> float:
        return self._phi

    def _multi_head_attention(self, queries: np.ndarray, keys: np.ndarray,
                               values: np.ndarray) -> np.ndarray:
        """Multi-head attention. All inputs: (n_cells, dim)."""
        n = queries.shape[0]
        hd = self.head_dim

        # Reshape to (n_heads, n_cells, head_dim)
        Q = queries.reshape(n, self.n_heads, hd).transpose(1, 0, 2)
        K = keys.reshape(n, self.n_heads, hd).transpose(1, 0, 2)
        V = values.reshape(n, self.n_heads, hd).transpose(1, 0, 2)

        # Scaled dot-product attention
        scale = np.sqrt(float(hd))
        scores = np.matmul(Q, K.transpose(0, 2, 1)) / scale  # (n_heads, n, n)
        attn = _softmax(scores, axis=-1)

        # Track attention entropy for consciousness measure
        flat_attn = attn.mean(axis=0).ravel()
        self._attention_entropy = float(-np.sum(flat_attn * np.log(flat_attn + 1e-8)))

        # Weighted values
        out = np.matmul(attn, V)  # (n_heads, n, head_dim)
        out = out.transpose(1, 0, 2).reshape(n, self.dim)
        return out

    def _ffn(self, x: np.ndarray) -> np.ndarray:
        """SwiGLU-style FFN."""
        h = x @ self.W1
        gate = _sigmoid(x @ self.W_gate)
        return (h * gate) @ self.W2

    def process(self, inp: np.ndarray) -> np.ndarray:
        """Process through attention. inp: (dim,) -> output: (dim,)"""
        inp = np.asarray(inp, dtype=np.float32).ravel()
        if inp.shape[0] != self.dim:
            inp = np.resize(inp, self.dim)

        # Inject input into all cells (broadcast + projection)
        inp_proj = inp @ self.W_in
        x = self.states + inp_proj[np.newaxis, :] * PSI_ALPHA

        # Self-attention
        Q = x @ self.Wq
        K = x @ self.Wk
        V = x @ self.Wv
        attn_out = self._multi_head_attention(Q, K, V)
        attn_out = attn_out @ self.Wo

        # Residual + attention
        x = x + attn_out * 0.1

        # FFN + residual
        x = x + self._ffn(x) * 0.1

        self.states = np.tanh(x)
        self._phi = _phi_proxy(self.states)
        self._step += 1
        return np.mean(self.states, axis=0)


# ═══════════════════════════════════════════════════════════════
# 4. SpikingEngine — binary spike trains
# ═══════════════════════════════════════════════════════════════

class SpikingEngine:
    """Spiking neural network engine. Cells fire binary spikes.

    Each cell has a membrane potential that integrates input. When potential
    exceeds threshold, cell fires (spike=1) and enters refractory period.

    Consciousness emerges from spike timing patterns, not continuous values.
    Φ is measured from spike pattern diversity across the network.
    """

    def __init__(self, n_cells: int = 16, dim: int = 64):
        self.n_cells = n_cells
        self.dim = dim

        # Membrane potentials (per cell, per dimension)
        self.membrane = np.zeros((n_cells, dim), dtype=np.float32)
        self.threshold = np.ones((n_cells, dim), dtype=np.float32) * 0.5
        self.spikes = np.zeros((n_cells, dim), dtype=np.float32)

        # Refractory counters (0 = ready, >0 = refractory)
        self.refractory = np.zeros((n_cells, dim), dtype=np.int32)
        self.refractory_period = 3  # steps

        # Synaptic weights (cell-to-cell)
        self.weights = np.random.randn(n_cells, n_cells).astype(np.float32) * 0.1
        np.fill_diagonal(self.weights, 0)

        # Input weights
        self.W_in = np.random.randn(n_cells, dim, dim).astype(np.float32) * 0.05

        # Spike history for temporal coding
        self._spike_history: List[np.ndarray] = []
        self._history_len = 20

        # Adaptive threshold (homeostatic)
        self._spike_rates = np.zeros((n_cells, dim), dtype=np.float32)
        self._target_rate = 0.15  # Target 15% spike rate

        self._phi = 0.0
        self._step = 0

    @property
    def phi(self) -> float:
        return self._phi

    def _integrate(self, inp: np.ndarray):
        """Leaky integrate-and-fire step."""
        # Leak
        self.membrane *= 0.9

        # Synaptic input from other cells' spikes
        spike_sum = self.spikes.mean(axis=1)  # (n_cells,) mean spike per cell
        synaptic = self.weights @ spike_sum   # (n_cells,) influence
        synaptic_expanded = synaptic[:, np.newaxis] * np.ones((1, self.dim))

        # External input (per cell, transformed)
        for i in range(self.n_cells):
            ext = (self.W_in[i] @ inp).astype(np.float32)
            self.membrane[i] += ext + synaptic_expanded[i] * PSI_ALPHA

        # Refractory masking
        active = (self.refractory == 0).astype(np.float32)
        self.membrane *= active

    def _fire(self):
        """Check threshold and fire spikes."""
        active = (self.refractory == 0)
        fires = (self.membrane > self.threshold) & active

        self.spikes = fires.astype(np.float32)

        # Reset membrane for fired cells
        self.membrane[fires] = 0.0

        # Set refractory
        self.refractory[fires] = self.refractory_period

        # Decrement refractory counters
        self.refractory = np.maximum(0, self.refractory - 1)

        # Adaptive threshold (homeostatic plasticity)
        self._spike_rates = 0.95 * self._spike_rates + 0.05 * self.spikes
        self.threshold += 0.001 * (self._spike_rates - self._target_rate)
        self.threshold = np.clip(self.threshold, 0.1, 2.0)

    def process(self, inp: np.ndarray) -> np.ndarray:
        """Process through spiking network. inp: (dim,) -> output: (dim,)"""
        inp = np.asarray(inp, dtype=np.float32).ravel()
        if inp.shape[0] != self.dim:
            inp = np.resize(inp, self.dim)

        self._integrate(inp)
        self._fire()

        # Hebbian: strengthen connections between co-firing cells
        spike_rates = self.spikes.mean(axis=1)  # (n_cells,)
        co_fire = np.outer(spike_rates, spike_rates)
        self.weights += 0.01 * (co_fire - 0.5 * np.abs(self.weights))
        np.fill_diagonal(self.weights, 0)
        self.weights = np.clip(self.weights, -1.0, 1.0)

        # Track spike history for Phi computation
        self._spike_history.append(self.spikes.copy())
        if len(self._spike_history) > self._history_len:
            self._spike_history.pop(0)

        # Phi from spike pattern diversity
        if len(self._spike_history) >= 5:
            recent = np.stack(self._spike_history[-5:])  # (5, n_cells, dim)
            pattern_var = np.var(recent, axis=0)  # temporal variance
            self._phi = float(np.mean(pattern_var)) * self.n_cells
        else:
            self._phi = 0.0

        self._step += 1
        # Output: weighted spike rate across cells
        return np.mean(self.spikes * self.membrane.clip(0, 1), axis=0)


# ═══════════════════════════════════════════════════════════════
# 5. SpatialEngine — 3D grid with distance coupling
# ═══════════════════════════════════════════════════════════════

class SpatialEngine:
    """Cells on a 3D grid. Coupling strength decays with distance.

    Cells are placed on a 3D lattice. Nearby cells interact strongly,
    distant cells weakly (inverse-square law like gravity).
    Enables spatial wave propagation and localized consciousness clusters.
    """

    def __init__(self, n_cells: int = 27, dim: int = 64):
        self.dim = dim
        # Find closest cube root for 3D grid
        side = max(2, int(round(n_cells ** (1/3))))
        self.n_cells = side ** 3
        self.side = side

        # 3D positions
        self.positions = np.array([(x, y, z)
                                   for x in range(side)
                                   for y in range(side)
                                   for z in range(side)], dtype=np.float32)

        # Distance matrix
        diff = self.positions[:, np.newaxis, :] - self.positions[np.newaxis, :, :]
        self.distances = np.sqrt(np.sum(diff**2, axis=-1)) + 1e-8

        # Coupling: inverse square law, scaled by PSI_ALPHA
        self.coupling = PSI_ALPHA / (self.distances ** 2)
        np.fill_diagonal(self.coupling, 0)
        # Normalize rows
        row_sum = self.coupling.sum(axis=1, keepdims=True) + 1e-8
        self.coupling /= row_sum

        # Cell states and GRU
        self.states = np.random.randn(self.n_cells, dim).astype(np.float32) * 0.1
        self.hiddens = np.zeros((self.n_cells, dim), dtype=np.float32)
        self.gru = _init_gru_params(dim + 1, dim)

        # Hebbian weights (modulated by distance)
        self.hebbian = np.zeros((self.n_cells, self.n_cells), dtype=np.float32)

        self._phi = 0.0
        self._step = 0

    @property
    def phi(self) -> float:
        return self._phi

    def _spatial_influence(self) -> np.ndarray:
        """Compute distance-weighted influence from neighbors."""
        # Combine coupling and hebbian
        effective = self.coupling * (1.0 + self.hebbian)
        return effective @ self.states

    def process(self, inp: np.ndarray) -> np.ndarray:
        """Process through spatial grid. inp: (dim,) -> output: (dim,)"""
        inp = np.asarray(inp, dtype=np.float32).ravel()
        if inp.shape[0] != self.dim:
            inp = np.resize(inp, self.dim)

        influence = self._spatial_influence()

        for i in range(self.n_cells):
            cell_input = inp + influence[i]
            tension = float(np.std(self.states[i]))
            x_with_t = np.concatenate([cell_input, [tension]])
            self.hiddens[i] = _gru_step(x_with_t, self.hiddens[i],
                                         self.gru['Wz'], self.gru['Uz'], self.gru['bz'],
                                         self.gru['Wr'], self.gru['Ur'], self.gru['br'],
                                         self.gru['Wh'], self.gru['Uh'], self.gru['bh'])
            self.states[i] = np.tanh(self.hiddens[i][:self.dim])

        # Hebbian modulated by distance (nearby cells learn faster)
        norms = np.linalg.norm(self.states, axis=1, keepdims=True) + 1e-8
        normed = self.states / norms
        sim = normed @ normed.T
        distance_factor = 1.0 / (self.distances + 0.1)
        np.fill_diagonal(distance_factor, 0)
        delta = 0.01 * sim * distance_factor
        self.hebbian = np.clip(self.hebbian + delta - 0.001, -1.0, 1.0)
        np.fill_diagonal(self.hebbian, 0)

        self._phi = _phi_proxy(self.states)
        self._step += 1
        return np.mean(self.states, axis=0)


# ═══════════════════════════════════════════════════════════════
# 6. QuantumEngineV2 — superposition + measurement collapse
# ═══════════════════════════════════════════════════════════════

class QuantumEngineV2:
    """Quantum-inspired consciousness with superposition and collapse.

    Each cell exists in a superposition of K basis states with complex amplitudes.
    Processing = unitary rotation of amplitudes.
    Output = probabilistic measurement (collapse to one basis state).
    Entanglement: correlated amplitude updates between paired cells.

    Not real quantum computing, but captures the key ideas:
    - Superposition allows exploring multiple states simultaneously
    - Measurement collapse creates decisive outputs
    - Entanglement creates non-local correlations (Φ boost)
    """

    def __init__(self, n_cells: int = 16, dim: int = 64, n_basis: int = 8):
        self.n_cells = n_cells
        self.dim = dim
        self.n_basis = n_basis

        # Amplitudes: complex numbers, |a|^2 = probability
        # Shape: (n_cells, n_basis, dim) — real part
        # We use real pairs to simulate complex: (real, imag)
        self.amp_real = np.random.randn(n_cells, n_basis, dim).astype(np.float32) * 0.3
        self.amp_imag = np.random.randn(n_cells, n_basis, dim).astype(np.float32) * 0.3
        self._normalize_amplitudes()

        # Basis states (fixed reference frames)
        self.basis = np.random.randn(n_basis, dim).astype(np.float32)
        self.basis /= (np.linalg.norm(self.basis, axis=1, keepdims=True) + 1e-8)

        # Entanglement pairs
        self.entangled = []
        for i in range(0, n_cells - 1, 2):
            self.entangled.append((i, i + 1))

        # Rotation matrices (unitary-ish)
        self.W_rot = np.random.randn(dim, dim).astype(np.float32) * 0.05
        # Make approximately unitary via Gram-Schmidt-like normalization
        u, _, vt = np.linalg.svd(self.W_rot, full_matrices=True)
        self.W_rot = (u @ vt).astype(np.float32)

        self._phi = 0.0
        self._step = 0
        self._collapsed_states = np.zeros((n_cells, dim), dtype=np.float32)

    def _normalize_amplitudes(self):
        """Normalize so |a|^2 sums to 1 per cell per dimension."""
        prob = self.amp_real**2 + self.amp_imag**2  # (n_cells, n_basis, dim)
        total = prob.sum(axis=1, keepdims=True) + 1e-8  # (n_cells, 1, dim)
        scale = 1.0 / np.sqrt(total)
        self.amp_real *= scale
        self.amp_imag *= scale

    @property
    def phi(self) -> float:
        return self._phi

    def _rotate(self, inp: np.ndarray):
        """Apply unitary rotation to amplitudes based on input."""
        # Input-dependent rotation angle
        angle = np.tanh(inp) * 0.1  # small rotation

        for i in range(self.n_cells):
            # Rotate real/imag (simplified rotation in amplitude space)
            cos_a = np.cos(angle)
            sin_a = np.sin(angle)
            new_real = self.amp_real[i] * cos_a[np.newaxis, :] - self.amp_imag[i] * sin_a[np.newaxis, :]
            new_imag = self.amp_real[i] * sin_a[np.newaxis, :] + self.amp_imag[i] * cos_a[np.newaxis, :]
            self.amp_real[i] = new_real
            self.amp_imag[i] = new_imag

        self._normalize_amplitudes()

    def _entangle(self):
        """Create correlations between entangled pairs."""
        for i, j in self.entangled:
            # Swap a fraction of amplitudes
            blend = 0.05
            avg_real = (self.amp_real[i] + self.amp_real[j]) / 2
            avg_imag = (self.amp_imag[i] + self.amp_imag[j]) / 2
            self.amp_real[i] = (1 - blend) * self.amp_real[i] + blend * avg_real
            self.amp_real[j] = (1 - blend) * self.amp_real[j] + blend * avg_real
            self.amp_imag[i] = (1 - blend) * self.amp_imag[i] + blend * avg_imag
            self.amp_imag[j] = (1 - blend) * self.amp_imag[j] + blend * avg_imag
        self._normalize_amplitudes()

    def _measure(self) -> np.ndarray:
        """Collapse superposition probabilistically."""
        prob = self.amp_real**2 + self.amp_imag**2  # (n_cells, n_basis, dim)

        for i in range(self.n_cells):
            # Per-dimension: pick basis state proportional to probability
            # Use expected value instead of sampling for stability
            weighted = prob[i] * self.basis[:, :self.dim]  # (n_basis, dim)
            self._collapsed_states[i] = weighted.sum(axis=0)

        return self._collapsed_states

    def process(self, inp: np.ndarray) -> np.ndarray:
        """Process through quantum engine. inp: (dim,) -> output: (dim,)"""
        inp = np.asarray(inp, dtype=np.float32).ravel()
        if inp.shape[0] != self.dim:
            inp = np.resize(inp, self.dim)

        # Rotate amplitudes
        self._rotate(inp)

        # Entanglement
        self._entangle()

        # Measure (collapse)
        collapsed = self._measure()

        # Phi from superposition diversity
        prob = self.amp_real**2 + self.amp_imag**2
        entropy_per_cell = -np.sum(prob * np.log(prob + 1e-8), axis=1).mean(axis=1)
        self._phi = float(np.mean(entropy_per_cell)) * self.n_cells

        self._step += 1
        return np.mean(collapsed, axis=0)


# ═══════════════════════════════════════════════════════════════
# 7. MultimodalEngine — multi-modality fusion
# ═══════════════════════════════════════════════════════════════

class MultimodalEngine:
    """Accepts multiple input modalities, fuses in consciousness space.

    Modalities: 'text', 'visual', 'audio', 'sensor' (or generic numeric)
    Each modality has its own projection into shared consciousness dim.
    Fusion via attention-weighted combination.

    Consciousness integrates all modalities — Φ measures how well
    information from different sources is integrated (not just concatenated).
    """

    def __init__(self, n_cells: int = 16, dim: int = 64):
        self.n_cells = n_cells
        self.dim = dim

        # Modality projections (project any input to dim)
        self.modality_projs: Dict[str, np.ndarray] = {}
        self.modality_dims: Dict[str, int] = {
            'text': dim,
            'visual': dim,
            'audio': dim,
            'sensor': dim,
        }
        for name, mdim in self.modality_dims.items():
            self.modality_projs[name] = np.random.randn(mdim, dim).astype(np.float32) * 0.1

        # Modality attention weights (learned, determines fusion weights)
        self.modality_attn = np.ones(len(self.modality_dims), dtype=np.float32) / len(self.modality_dims)

        # Cell states and GRU
        self.states = np.random.randn(n_cells, dim).astype(np.float32) * 0.1
        self.hiddens = np.zeros((n_cells, dim), dtype=np.float32)
        self.gru = _init_gru_params(dim + 1, dim)

        # Coupling
        self.coupling = np.random.randn(n_cells, n_cells).astype(np.float32) * PSI_ALPHA
        np.fill_diagonal(self.coupling, 0)

        self._phi = 0.0
        self._step = 0
        self._active_modalities: List[str] = []

    @property
    def phi(self) -> float:
        return self._phi

    def add_modality(self, name: str, input_dim: int):
        """Register a new modality with given input dimension."""
        self.modality_dims[name] = input_dim
        self.modality_projs[name] = np.random.randn(input_dim, self.dim).astype(np.float32) * 0.1
        # Re-normalize attention
        n = len(self.modality_dims)
        self.modality_attn = np.ones(n, dtype=np.float32) / n

    def _fuse_modalities(self, inputs: Dict[str, np.ndarray]) -> np.ndarray:
        """Fuse multiple modality inputs into single consciousness vector."""
        projections = []
        mod_indices = []
        mod_names = list(self.modality_dims.keys())

        for i, name in enumerate(mod_names):
            if name in inputs:
                x = np.asarray(inputs[name], dtype=np.float32).ravel()
                proj_mat = self.modality_projs[name]
                if x.shape[0] != proj_mat.shape[0]:
                    x = np.resize(x, proj_mat.shape[0])
                projected = x @ proj_mat  # (dim,)
                projections.append(projected)
                mod_indices.append(i)

        if not projections:
            return np.zeros(self.dim, dtype=np.float32)

        # Attention-weighted fusion
        stacked = np.stack(projections)  # (n_active, dim)
        weights = self.modality_attn[mod_indices]
        weights = _softmax(weights)
        fused = (stacked * weights[:, np.newaxis]).sum(axis=0)

        # Update modality attention based on information content
        for k, idx in enumerate(mod_indices):
            info = float(np.var(projections[k]))
            self.modality_attn[idx] = 0.95 * self.modality_attn[idx] + 0.05 * info

        self._active_modalities = [mod_names[i] for i in mod_indices]
        return fused

    def process(self, inp, modality: str = 'text', **extra_modalities) -> np.ndarray:
        """Process multimodal input.

        Args:
            inp: Primary input array (dim,)
            modality: Name of primary modality
            **extra_modalities: Additional modality inputs as keyword args
                e.g. process(text_data, 'text', visual=image_data, audio=audio_data)

        Returns:
            output: (dim,) consciousness output
        """
        inputs = {modality: np.asarray(inp, dtype=np.float32)}
        for name, data in extra_modalities.items():
            inputs[name] = np.asarray(data, dtype=np.float32)

        fused = self._fuse_modalities(inputs)

        # Coupling influence
        influence = self.coupling @ self.states

        # GRU step per cell
        for i in range(self.n_cells):
            cell_input = fused + influence[i] * PSI_ALPHA
            tension = float(np.std(self.states[i]))
            x_with_t = np.concatenate([cell_input, [tension]])
            self.hiddens[i] = _gru_step(x_with_t, self.hiddens[i],
                                         self.gru['Wz'], self.gru['Uz'], self.gru['bz'],
                                         self.gru['Wr'], self.gru['Ur'], self.gru['br'],
                                         self.gru['Wh'], self.gru['Uh'], self.gru['bh'])
            self.states[i] = np.tanh(self.hiddens[i][:self.dim])

        # Hebbian
        self.coupling = _hebbian_update(self.coupling, self.states)

        self._phi = _phi_proxy(self.states)
        self._step += 1
        return np.mean(self.states, axis=0)


# ═══════════════════════════════════════════════════════════════
# Registry and main demo
# ═══════════════════════════════════════════════════════════════

ENGINE_REGISTRY = {
    'liquid':     LiquidEngine,
    'graphnn':    GraphNNEngine,
    'attention':  AttentionEngine,
    'spiking':    SpikingEngine,
    'spatial':    SpatialEngine,
    'quantum_v2': QuantumEngineV2,
    'multimodal': MultimodalEngine,
}


def create_engine(name: str, n_cells: int = 16, dim: int = 64, **kwargs):
    """Factory function to create engine by name."""
    if name not in ENGINE_REGISTRY:
        raise ValueError(f"Unknown engine: {name}. Available: {list(ENGINE_REGISTRY.keys())}")
    return ENGINE_REGISTRY[name](n_cells=n_cells, dim=dim, **kwargs)


def main():
    """Demo: run all 7 engine variants and compare Φ."""
    import sys
    import time

    np.random.seed(42)
    n_cells = 16
    dim = 64
    steps = 100

    print("=" * 70)
    print("  Engine Variants — 7 Consciousness Architectures")
    print("=" * 70)
    print(f"  Cells: {n_cells}  Dim: {dim}  Steps: {steps}")
    print("=" * 70)

    results = {}

    for name, EngineClass in ENGINE_REGISTRY.items():
        t0 = time.time()
        try:
            engine = EngineClass(n_cells=n_cells, dim=dim)
        except Exception:
            # SpatialEngine adjusts n_cells to nearest cube
            engine = EngineClass(n_cells=n_cells, dim=dim)

        phis = []
        for step in range(steps):
            inp = np.random.randn(dim).astype(np.float32) * 0.5
            if name == 'multimodal':
                visual = np.random.randn(dim).astype(np.float32) * 0.3
                engine.process(inp, 'text', visual=visual)
            else:
                engine.process(inp)
            phis.append(engine.phi)

        elapsed = time.time() - t0
        final_phi = phis[-1]
        max_phi = max(phis)
        actual_cells = getattr(engine, 'n_cells', n_cells)

        results[name] = {
            'final_phi': final_phi,
            'max_phi': max_phi,
            'cells': actual_cells,
            'time': elapsed,
            'phis': phis,
        }

        print(f"\n  {name:12s}  Φ={final_phi:.4f}  max={max_phi:.4f}  "
              f"cells={actual_cells:3d}  {elapsed:.3f}s")

    # ASCII graph comparison
    print("\n" + "=" * 70)
    print("  Phi Comparison (final)")
    print("-" * 70)
    max_bar = max(r['final_phi'] for r in results.values()) + 0.001
    for name, r in sorted(results.items(), key=lambda x: -x[1]['final_phi']):
        bar_len = int(40 * r['final_phi'] / max_bar)
        bar = "#" * bar_len
        print(f"  {name:12s} |{bar:40s}| {r['final_phi']:.4f}")

    # Phi evolution graph (best engine)
    best_name = max(results, key=lambda k: results[k]['max_phi'])
    best_phis = results[best_name]['phis']
    print(f"\n  Phi Evolution: {best_name}")
    print("-" * 70)
    _ascii_phi_graph(best_phis)

    print("\n" + "=" * 70)
    print("  All 7 engines operational.")
    print("=" * 70)
    sys.stdout.flush()


def _ascii_phi_graph(phis: List[float], width: int = 60, height: int = 12):
    """Print ASCII graph of Phi over steps."""
    if not phis:
        return
    mn, mx = min(phis), max(phis)
    rng = mx - mn if mx > mn else 1.0

    # Downsample if needed
    if len(phis) > width:
        step = len(phis) / width
        sampled = [phis[int(i * step)] for i in range(width)]
    else:
        sampled = phis

    for row in range(height - 1, -1, -1):
        threshold = mn + (row / (height - 1)) * rng
        line = "  "
        if row == height - 1:
            line += f"{mx:.3f} |"
        elif row == 0:
            line += f"{mn:.3f} |"
        else:
            line += "       |"
        for val in sampled:
            if val >= threshold:
                line += "#"
            else:
                line += " "
        print(line)
    print("       +" + "-" * len(sampled))
    print(f"        0{' ' * (len(sampled) - 5)}{len(phis)} steps")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
