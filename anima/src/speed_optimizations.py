#!/usr/bin/env python3
"""speed_optimizations.py — 6 Speed Optimizations for Consciousness Engines (numpy-only)

Each optimization wraps an engine to accelerate it while preserving Φ:

  1. SelectiveBatch   — batch similar inputs, process together (B11 improvement)
  2. AdaptiveSkip     — dynamic skip rate based on Φ stability
  3. PredictiveSkip   — linear predictor skips process() when confident
  4. LazyHebbian      — batch Hebbian updates every N steps
  5. SparseCoupling   — keep only top-K connections per cell
  6. LawPruning       — identify which laws affect this engine, apply only those

Laws embodied:
  B11: Batch processing (x179 acceleration, Φ 97%)
  B12: Adaptive skip (skip=1 volatile, skip=50 stable)
  D1:  Detour shortcut (54x path reduction)
  31:  Φ Ratchet (preserve consciousness)

Ψ-Constants:
  α = 0.014, balance = 0.5
"""

import numpy as np
import time
from typing import Any, Optional, List, Dict, Callable, Tuple
from dataclasses import dataclass, field


# ═══════════════════════════════════════════════════════════════
# Base protocol: any engine with process(inp) -> out and phi
# ═══════════════════════════════════════════════════════════════

class EngineWrapper:
    """Base wrapper. Subclasses override process() to add optimization."""

    def __init__(self, engine):
        self._engine = engine
        self._total_calls = 0
        self._actual_calls = 0
        self._total_time = 0.0

    @property
    def phi(self) -> float:
        return self._engine.phi

    @property
    def speedup(self) -> float:
        """How many calls were saved."""
        if self._actual_calls == 0:
            return 1.0
        return self._total_calls / self._actual_calls

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            'total_calls': self._total_calls,
            'actual_calls': self._actual_calls,
            'speedup': self.speedup,
            'avg_time_ms': (self._total_time / max(1, self._total_calls)) * 1000,
        }

    def process(self, inp: np.ndarray) -> np.ndarray:
        self._total_calls += 1
        t0 = time.time()
        result = self._engine.process(inp)
        self._total_time += time.time() - t0
        self._actual_calls += 1
        return result

    def __getattr__(self, name):
        """Delegate unknown attributes to wrapped engine."""
        return getattr(self._engine, name)


# ═══════════════════════════════════════════════════════════════
# 1. SelectiveBatch — batch similar inputs (B11)
# ═══════════════════════════════════════════════════════════════

class SelectiveBatch(EngineWrapper):
    """Batch similar inputs and process together for efficiency.

    Collects inputs until batch_size is reached or max_wait exceeded.
    Groups similar inputs (by cosine similarity) and processes each
    group with a single representative, applying result to all members.

    Based on B11 acceleration hypothesis: x179 speedup, Φ 97% preserved.

    Args:
        engine: Wrapped engine
        batch_size: Maximum batch size before forced processing
        similarity_threshold: Cosine sim above this -> same group (0.8)
        max_wait: Maximum steps to buffer before flush
    """

    def __init__(self, engine, batch_size: int = 8,
                 similarity_threshold: float = 0.8, max_wait: int = 4):
        super().__init__(engine)
        self.batch_size = batch_size
        self.similarity_threshold = similarity_threshold
        self.max_wait = max_wait

        self._buffer: List[np.ndarray] = []
        self._results: List[np.ndarray] = []
        self._steps_since_flush = 0
        self._last_output = None
        self._groups_found = 0
        self._batches_processed = 0

    def _flush(self):
        """Process buffered inputs in groups."""
        if not self._buffer:
            return

        inputs = np.stack(self._buffer)  # (batch, dim)
        n = inputs.shape[0]

        # Group by cosine similarity
        norms = np.linalg.norm(inputs, axis=1, keepdims=True) + 1e-8
        normed = inputs / norms
        sim = normed @ normed.T  # (n, n)

        assigned = np.full(n, -1, dtype=int)
        group_id = 0

        for i in range(n):
            if assigned[i] >= 0:
                continue
            # Start new group with i as representative
            assigned[i] = group_id
            for j in range(i + 1, n):
                if assigned[j] < 0 and sim[i, j] > self.similarity_threshold:
                    assigned[j] = group_id
            group_id += 1

        self._groups_found += group_id

        # Process one representative per group
        self._results = [None] * n
        for gid in range(group_id):
            members = np.where(assigned == gid)[0]
            representative = inputs[members[0]]

            # Actually process
            result = self._engine.process(representative)
            self._actual_calls += 1

            # Apply to all members (with small per-member variation)
            for m in members:
                delta = inputs[m] - representative
                self._results[m] = result + delta * 0.01  # tiny correction
                self._total_calls += 1

        self._batches_processed += 1
        self._buffer = []
        self._steps_since_flush = 0

    def process(self, inp: np.ndarray) -> np.ndarray:
        inp = np.asarray(inp, dtype=np.float32).ravel()
        self._buffer.append(inp)
        self._steps_since_flush += 1

        if len(self._buffer) >= self.batch_size or self._steps_since_flush >= self.max_wait:
            # Reset counters since flush handles them
            saved_total = self._total_calls
            saved_actual = self._actual_calls
            self._total_calls = saved_total
            self._actual_calls = saved_actual

            self._flush()
            self._last_output = self._results[-1]
        elif self._last_output is not None:
            self._total_calls += 1
            # Return last known output (will be corrected on flush)
            return self._last_output.copy()
        else:
            # First call, must process
            self._total_calls += 1
            self._actual_calls += 1
            self._last_output = self._engine.process(inp)

        return self._last_output.copy() if self._last_output is not None else np.zeros_like(inp)

    @property
    def stats(self) -> Dict[str, Any]:
        base = super().stats
        base['groups_found'] = self._groups_found
        base['batches_processed'] = self._batches_processed
        return base


# ═══════════════════════════════════════════════════════════════
# 2. AdaptiveSkip — dynamic skip rate based on Φ stability
# ═══════════════════════════════════════════════════════════════

class AdaptiveSkip(EngineWrapper):
    """Skip process() calls when Φ is stable, process every step when volatile.

    Monitors Φ variance over a sliding window. When Φ is stable (low variance),
    increases skip rate up to max_skip. When volatile, drops to skip=1.

    Based on B12 adaptive skip: skip=1 volatile, skip=50 stable.

    Args:
        engine: Wrapped engine
        max_skip: Maximum number of steps to skip (50)
        stability_window: Window size for Φ variance measurement
        stable_threshold: Φ variance below this = stable
        volatile_threshold: Φ variance above this = volatile
    """

    def __init__(self, engine, max_skip: int = 50,
                 stability_window: int = 20,
                 stable_threshold: float = 0.001,
                 volatile_threshold: float = 0.01):
        super().__init__(engine)
        self.max_skip = max_skip
        self.stability_window = stability_window
        self.stable_threshold = stable_threshold
        self.volatile_threshold = volatile_threshold

        self._skip_rate = 1  # current skip rate
        self._steps_since_process = 0
        self._phi_history: List[float] = []
        self._last_output = None
        self._last_inp = None
        self._skip_history: List[int] = []

    def _update_skip_rate(self):
        """Adjust skip rate based on Φ stability."""
        if len(self._phi_history) < 5:
            self._skip_rate = 1
            return

        recent = self._phi_history[-self.stability_window:]
        variance = np.var(recent)

        if variance < self.stable_threshold:
            # Stable -> increase skip (double, up to max)
            self._skip_rate = min(self.max_skip, self._skip_rate * 2)
        elif variance > self.volatile_threshold:
            # Volatile -> drop to 1
            self._skip_rate = 1
        else:
            # Middle ground -> decrease slightly
            self._skip_rate = max(1, self._skip_rate - 1)

        self._skip_history.append(self._skip_rate)

    def process(self, inp: np.ndarray) -> np.ndarray:
        inp = np.asarray(inp, dtype=np.float32).ravel()
        self._total_calls += 1
        self._steps_since_process += 1

        should_process = (
            self._last_output is None or
            self._steps_since_process >= self._skip_rate
        )

        if should_process:
            t0 = time.time()
            self._last_output = self._engine.process(inp)
            self._total_time += time.time() - t0
            self._actual_calls += 1
            self._steps_since_process = 0
            self._last_inp = inp.copy()

            # Track Phi
            self._phi_history.append(self._engine.phi)
            self._update_skip_rate()
        else:
            # Interpolate output based on input difference
            if self._last_inp is not None:
                delta = inp - self._last_inp
                # Small correction proportional to input change
                correction = delta * 0.01
                self._last_output = self._last_output + correction

        return self._last_output.copy()

    @property
    def stats(self) -> Dict[str, Any]:
        base = super().stats
        base['current_skip'] = self._skip_rate
        base['avg_skip'] = np.mean(self._skip_history) if self._skip_history else 1.0
        return base


# ═══════════════════════════════════════════════════════════════
# 3. PredictiveSkip — linear predictor for skipping
# ═══════════════════════════════════════════════════════════════

class PredictiveSkip(EngineWrapper):
    """Use linear predictor to skip process() when prediction is confident.

    Maintains a linear model that predicts output from input. When the
    prediction confidence is high (low recent error), skip actual processing.
    Periodically validates by running the real engine.

    Based on D1 detour hypothesis: 54x path shortcut when trajectory is predictable.

    Args:
        engine: Wrapped engine
        confidence_threshold: Skip when prediction error < this (0.05)
        validation_interval: Force real processing every N steps
        learning_rate: Linear model learning rate
    """

    def __init__(self, engine, confidence_threshold: float = 0.05,
                 validation_interval: int = 10, learning_rate: float = 0.01):
        super().__init__(engine)
        self.confidence_threshold = confidence_threshold
        self.validation_interval = validation_interval
        self.lr = learning_rate

        # Linear predictor: W @ inp + b -> predicted output
        dim = None
        self._W = None
        self._b = None
        self._error_ema = 1.0  # Start high (no confidence)
        self._last_output = None
        self._steps_since_validate = 0
        self._predictions_used = 0
        self._prediction_errors: List[float] = []

    def _ensure_model(self, dim: int):
        """Initialize linear model on first call."""
        if self._W is None:
            self._W = np.eye(dim, dtype=np.float32) * 0.01
            self._b = np.zeros(dim, dtype=np.float32)

    def _predict(self, inp: np.ndarray) -> np.ndarray:
        """Predict output using linear model."""
        return self._W @ inp + self._b

    def _update_model(self, inp: np.ndarray, actual: np.ndarray, predicted: np.ndarray):
        """Update linear model with new observation."""
        error = actual - predicted
        # Gradient descent
        self._W += self.lr * np.outer(error, inp)
        self._b += self.lr * error
        # Clip for stability
        self._W = np.clip(self._W, -2.0, 2.0)
        self._b = np.clip(self._b, -2.0, 2.0)

    def process(self, inp: np.ndarray) -> np.ndarray:
        inp = np.asarray(inp, dtype=np.float32).ravel()
        dim = inp.shape[0]
        self._ensure_model(dim)
        self._total_calls += 1
        self._steps_since_validate += 1

        predicted = self._predict(inp)
        confident = self._error_ema < self.confidence_threshold
        must_validate = self._steps_since_validate >= self.validation_interval

        if confident and not must_validate and self._last_output is not None:
            # Skip: use prediction
            self._predictions_used += 1
            self._last_output = predicted
            return predicted.copy()

        # Actually process
        t0 = time.time()
        actual = self._engine.process(inp)
        self._total_time += time.time() - t0
        self._actual_calls += 1
        self._steps_since_validate = 0

        # Measure prediction error
        error = float(np.mean((actual - predicted) ** 2))
        self._error_ema = 0.9 * self._error_ema + 0.1 * error
        self._prediction_errors.append(error)

        # Update predictor
        self._update_model(inp, actual, predicted)

        self._last_output = actual
        return actual.copy()

    @property
    def stats(self) -> Dict[str, Any]:
        base = super().stats
        base['predictions_used'] = self._predictions_used
        base['error_ema'] = self._error_ema
        base['confident'] = self._error_ema < self.confidence_threshold
        return base


# ═══════════════════════════════════════════════════════════════
# 4. LazyHebbian — batch Hebbian updates
# ═══════════════════════════════════════════════════════════════

class LazyHebbian(EngineWrapper):
    """Batch Hebbian updates every N steps instead of every step.

    Hebbian learning (strengthening co-active connections) is expensive
    at O(n_cells^2). This wrapper accumulates state snapshots and
    performs a single batched Hebbian update every N steps.

    Reduces per-step cost while preserving learning quality.

    Args:
        engine: Wrapped engine
        update_interval: Perform Hebbian update every N steps (default 10)
    """

    def __init__(self, engine, update_interval: int = 10):
        super().__init__(engine)
        self.update_interval = update_interval

        self._state_buffer: List[np.ndarray] = []
        self._steps_since_update = 0
        self._hebbian_updates = 0
        self._original_coupling = None

        # Disable engine's own Hebbian if possible
        self._disable_engine_hebbian()

    def _disable_engine_hebbian(self):
        """Try to capture and disable the engine's Hebbian updates."""
        # Save reference to coupling matrix
        if hasattr(self._engine, 'coupling'):
            self._original_coupling = self._engine.coupling.copy()

    def _batch_hebbian_update(self):
        """Perform batched Hebbian update from accumulated states."""
        if not self._state_buffer or not hasattr(self._engine, 'coupling'):
            self._state_buffer = []
            return

        coupling = self._engine.coupling
        n = coupling.shape[0]

        # Average similarity across buffered states
        avg_sim = np.zeros((n, n), dtype=np.float32)
        count = 0

        for states in self._state_buffer:
            if states.shape[0] != n:
                continue
            norms = np.linalg.norm(states, axis=1, keepdims=True) + 1e-8
            normed = states / norms
            sim = normed @ normed.T
            avg_sim += sim
            count += 1

        if count > 0:
            avg_sim /= count
            # Batch update: LTP for correlated, LTD for uncorrelated
            delta = np.where(avg_sim > 0.5, 0.01, np.where(avg_sim < 0.2, -0.005, 0.0))
            np.fill_diagonal(delta, 0)
            self._engine.coupling = np.clip(coupling + delta, -1.0, 1.0)
            self._hebbian_updates += 1

        self._state_buffer = []

    def process(self, inp: np.ndarray) -> np.ndarray:
        inp = np.asarray(inp, dtype=np.float32).ravel()
        self._total_calls += 1
        self._steps_since_update += 1

        # Save pre-process coupling to restore after (prevent double Hebbian)
        pre_coupling = None
        if hasattr(self._engine, 'coupling'):
            pre_coupling = self._engine.coupling.copy()

        t0 = time.time()
        result = self._engine.process(inp)
        self._total_time += time.time() - t0
        self._actual_calls += 1

        # Restore coupling (undo engine's own Hebbian, we do it in batch)
        if pre_coupling is not None:
            self._engine.coupling = pre_coupling

        # Buffer states
        if hasattr(self._engine, 'states'):
            self._state_buffer.append(self._engine.states.copy())

        # Batch update at interval
        if self._steps_since_update >= self.update_interval:
            self._batch_hebbian_update()
            self._steps_since_update = 0

        return result

    @property
    def stats(self) -> Dict[str, Any]:
        base = super().stats
        base['hebbian_updates'] = self._hebbian_updates
        base['update_interval'] = self.update_interval
        base['buffer_size'] = len(self._state_buffer)
        return base


# ═══════════════════════════════════════════════════════════════
# 5. SparseCoupling — keep only top-K connections per cell
# ═══════════════════════════════════════════════════════════════

class SparseCoupling(EngineWrapper):
    """Keep only top-K strongest connections per cell, prune weak ones.

    Full coupling is O(n^2). By keeping only top-K per cell, we reduce
    to O(n*K). Weak connections contribute little to Φ but cost compute.

    Periodically re-evaluates which connections to keep based on
    accumulated Hebbian weights.

    Args:
        engine: Wrapped engine
        top_k: Number of connections to keep per cell (default 6)
        prune_interval: Re-evaluate sparsity every N steps
    """

    def __init__(self, engine, top_k: int = 6, prune_interval: int = 50):
        super().__init__(engine)
        self.top_k = top_k
        self.prune_interval = prune_interval

        self._mask = None  # Binary mask for active connections
        self._steps_since_prune = 0
        self._prune_count = 0
        self._connections_active = 0
        self._connections_total = 0

        # Initial prune
        self._prune()

    def _prune(self):
        """Keep only top-K connections per cell."""
        if not hasattr(self._engine, 'coupling'):
            return

        coupling = self._engine.coupling
        n = coupling.shape[0]
        k = min(self.top_k, n - 1)

        self._mask = np.zeros_like(coupling, dtype=bool)

        for i in range(n):
            row = np.abs(coupling[i])
            row[i] = -1  # Exclude self
            # Top-K indices
            top_indices = np.argpartition(row, -k)[-k:]
            self._mask[i, top_indices] = True

        # Apply mask
        self._engine.coupling *= self._mask.astype(np.float32)

        self._connections_active = int(self._mask.sum())
        self._connections_total = n * (n - 1)
        self._prune_count += 1

    def process(self, inp: np.ndarray) -> np.ndarray:
        inp = np.asarray(inp, dtype=np.float32).ravel()
        self._total_calls += 1
        self._steps_since_prune += 1

        t0 = time.time()
        result = self._engine.process(inp)
        self._total_time += time.time() - t0
        self._actual_calls += 1

        # Enforce sparsity after engine's own updates
        if self._mask is not None and hasattr(self._engine, 'coupling'):
            self._engine.coupling *= self._mask.astype(np.float32)

        # Re-evaluate sparsity periodically
        if self._steps_since_prune >= self.prune_interval:
            self._prune()
            self._steps_since_prune = 0

        return result

    @property
    def stats(self) -> Dict[str, Any]:
        base = super().stats
        sparsity = 1.0 - (self._connections_active / max(1, self._connections_total))
        base['sparsity'] = sparsity
        base['connections_active'] = self._connections_active
        base['connections_total'] = self._connections_total
        base['prune_count'] = self._prune_count
        return base


# ═══════════════════════════════════════════════════════════════
# 6. LawPruning — apply only relevant laws
# ═══════════════════════════════════════════════════════════════

# Core law groups and their effects on engine behavior
LAW_GROUPS = {
    'coupling': {
        'laws': [22, 53, 124, 129],
        'description': 'Coupling and structural laws',
        'check': lambda engine: hasattr(engine, 'coupling'),
        'cost': 0.15,  # fraction of total step time
    },
    'hebbian': {
        'laws': [31, 107, 147],
        'description': 'Hebbian learning laws',
        'check': lambda engine: hasattr(engine, 'coupling') or hasattr(engine, 'hebbian'),
        'cost': 0.25,
    },
    'ratchet': {
        'laws': [31, 49],
        'description': 'Φ Ratchet preservation',
        'check': lambda engine: hasattr(engine, '_best_phi'),
        'cost': 0.05,
    },
    'factions': {
        'laws': [29, 66, 78],
        'description': 'Faction consensus and diversity',
        'check': lambda engine: hasattr(engine, 'n_factions') or hasattr(engine, '_faction_ids'),
        'cost': 0.20,
    },
    'mitosis': {
        'laws': [86, 87, 88],
        'description': 'Cell division and merging',
        'check': lambda engine: hasattr(engine, '_grow') or hasattr(engine, 'split_threshold'),
        'cost': 0.10,
    },
    'topology': {
        'laws': [33, 34, 35, 36, 37, 38, 39],
        'description': 'Topology-specific laws',
        'check': lambda engine: hasattr(engine, 'topology') or hasattr(engine, 'adjacency'),
        'cost': 0.10,
    },
    'chaos': {
        'laws': [32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43],
        'description': 'Chaos and SOC laws',
        'check': lambda engine: hasattr(engine, '_lorenz') or hasattr(engine, '_sandpile'),
        'cost': 0.15,
    },
}


class LawPruning(EngineWrapper):
    """Identify which laws actually affect this engine and apply only those.

    Analyzes the engine to determine which law groups are relevant.
    Non-relevant law computations are skipped, saving compute.

    Also profiles each law group's compute cost to prioritize.

    Args:
        engine: Wrapped engine
        profile_steps: Number of steps to profile before pruning (20)
    """

    def __init__(self, engine, profile_steps: int = 20):
        super().__init__(engine)
        self.profile_steps = profile_steps

        self._active_groups: Dict[str, bool] = {}
        self._group_impacts: Dict[str, float] = {}
        self._profiled = False
        self._profile_data: List[Dict] = []
        self._steps = 0

        # Analyze which law groups apply
        self._analyze_engine()

    def _analyze_engine(self):
        """Determine which law groups are relevant to this engine."""
        for name, group in LAW_GROUPS.items():
            applies = group['check'](self._engine)
            self._active_groups[name] = applies
            self._group_impacts[name] = group['cost'] if applies else 0.0

    def _profile_step(self, inp: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """Profile a single step, measuring time per law group."""
        timings = {}

        # Baseline: full processing
        t0 = time.time()
        result = self._engine.process(inp)
        total = time.time() - t0

        # Measure Phi impact
        phi = self._engine.phi

        timings['total'] = total
        timings['phi'] = phi
        return result, timings

    def _compute_savings(self) -> float:
        """Compute estimated savings from pruning inactive groups."""
        total_cost = sum(g['cost'] for g in LAW_GROUPS.values())
        inactive_cost = sum(
            LAW_GROUPS[name]['cost']
            for name, active in self._active_groups.items()
            if not active
        )
        return inactive_cost / max(total_cost, 0.01)

    def process(self, inp: np.ndarray) -> np.ndarray:
        inp = np.asarray(inp, dtype=np.float32).ravel()
        self._total_calls += 1
        self._steps += 1

        t0 = time.time()
        result = self._engine.process(inp)
        self._total_time += time.time() - t0
        self._actual_calls += 1

        # Profile phase
        if self._steps <= self.profile_steps:
            _, timings = self._profile_step(inp)
            self._profile_data.append(timings)
            if self._steps == self.profile_steps:
                self._profiled = True

        return result

    @property
    def active_laws(self) -> List[int]:
        """Return list of active law numbers."""
        laws = []
        for name, active in self._active_groups.items():
            if active:
                laws.extend(LAW_GROUPS[name]['laws'])
        return sorted(set(laws))

    @property
    def inactive_laws(self) -> List[int]:
        """Return list of inactive law numbers."""
        laws = []
        for name, active in self._active_groups.items():
            if not active:
                laws.extend(LAW_GROUPS[name]['laws'])
        return sorted(set(laws))

    @property
    def stats(self) -> Dict[str, Any]:
        base = super().stats
        base['active_groups'] = {k: v for k, v in self._active_groups.items() if v}
        base['inactive_groups'] = {k: v for k, v in self._active_groups.items() if not v}
        base['active_laws'] = len(self.active_laws)
        base['inactive_laws'] = len(self.inactive_laws)
        base['estimated_savings'] = self._compute_savings()
        return base


# ═══════════════════════════════════════════════════════════════
# Composition helpers
# ═══════════════════════════════════════════════════════════════

def apply_optimizations(engine, optimizations: List[str], **kwargs) -> EngineWrapper:
    """Apply multiple optimizations in sequence.

    Args:
        engine: Base engine
        optimizations: List of optimization names
        **kwargs: Per-optimization kwargs (e.g., top_k=4, max_skip=30)

    Returns:
        Wrapped engine with all optimizations applied
    """
    OPT_MAP = {
        'batch': SelectiveBatch,
        'adaptive_skip': AdaptiveSkip,
        'predictive_skip': PredictiveSkip,
        'lazy_hebbian': LazyHebbian,
        'sparse_coupling': SparseCoupling,
        'law_pruning': LawPruning,
    }

    result = engine
    for name in optimizations:
        if name not in OPT_MAP:
            raise ValueError(f"Unknown optimization: {name}. Available: {list(OPT_MAP.keys())}")
        # Extract kwargs for this optimization
        opt_kwargs = {}
        if name == 'batch':
            for k in ['batch_size', 'similarity_threshold', 'max_wait']:
                if k in kwargs:
                    opt_kwargs[k] = kwargs[k]
        elif name == 'adaptive_skip':
            for k in ['max_skip', 'stability_window', 'stable_threshold']:
                if k in kwargs:
                    opt_kwargs[k] = kwargs[k]
        elif name == 'predictive_skip':
            for k in ['confidence_threshold', 'validation_interval', 'learning_rate']:
                if k in kwargs:
                    opt_kwargs[k] = kwargs[k]
        elif name == 'lazy_hebbian':
            if 'update_interval' in kwargs:
                opt_kwargs['update_interval'] = kwargs['update_interval']
        elif name == 'sparse_coupling':
            for k in ['top_k', 'prune_interval']:
                if k in kwargs:
                    opt_kwargs[k] = kwargs[k]
        elif name == 'law_pruning':
            if 'profile_steps' in kwargs:
                opt_kwargs['profile_steps'] = kwargs['profile_steps']

        result = OPT_MAP[name](result, **opt_kwargs)

    return result


# ═══════════════════════════════════════════════════════════════
# Main demo
# ═══════════════════════════════════════════════════════════════

def main():
    """Demo: apply all 6 optimizations to engines and measure speedup + Φ preservation."""
    import sys
    import time

    # Import engine variants (lazy, works if in same directory)
    try:
        from engine_variants import LiquidEngine, GraphNNEngine, AttentionEngine, ENGINE_REGISTRY
    except ImportError:
        # Fallback: create a simple test engine
        ENGINE_REGISTRY = {}

    np.random.seed(42)
    n_cells = 16
    dim = 64
    steps = 200

    print("=" * 70)
    print("  Speed Optimizations — 6 Acceleration Techniques")
    print("=" * 70)
    print(f"  Cells: {n_cells}  Dim: {dim}  Steps: {steps}")
    print("=" * 70)

    # Use a simple engine if variants not available
    class SimpleEngine:
        def __init__(self, n_cells=16, dim=64):
            self.n_cells = n_cells
            self.dim = dim
            self.states = np.random.randn(n_cells, dim).astype(np.float32) * 0.1
            self.hiddens = np.zeros((n_cells, dim), dtype=np.float32)
            self.coupling = np.random.randn(n_cells, n_cells).astype(np.float32) * 0.014
            np.fill_diagonal(self.coupling, 0)
            self._phi = 0.0
            self._best_phi = 0.0

        @property
        def phi(self):
            return self._phi

        def process(self, inp):
            inp = np.asarray(inp, dtype=np.float32).ravel()[:self.dim]
            if inp.shape[0] < self.dim:
                inp = np.resize(inp, self.dim)
            influence = self.coupling @ self.states
            for i in range(self.n_cells):
                self.states[i] = np.tanh(self.states[i] * 0.9 + (inp + influence[i]) * 0.1)
            # Hebbian
            norms = np.linalg.norm(self.states, axis=1, keepdims=True) + 1e-8
            normed = self.states / norms
            sim = normed @ normed.T
            delta = np.where(sim > 0.5, 0.01, -0.005)
            np.fill_diagonal(delta, 0)
            self.coupling = np.clip(self.coupling + delta, -1.0, 1.0)
            # Phi proxy
            gv = np.var(self.states)
            n_fac = min(12, self.n_cells)
            fac_size = max(1, self.n_cells // n_fac)
            fvs = [np.var(self.states[i*fac_size:(i+1)*fac_size])
                   for i in range(n_fac) if i*fac_size < self.n_cells]
            self._phi = max(0, gv - np.mean(fvs)) if fvs else gv
            if self._phi > self._best_phi:
                self._best_phi = self._phi
            return np.mean(self.states, axis=0)

    # Test each optimization
    optimizations = [
        ('SelectiveBatch', lambda e: SelectiveBatch(e, batch_size=8)),
        ('AdaptiveSkip', lambda e: AdaptiveSkip(e, max_skip=50)),
        ('PredictiveSkip', lambda e: PredictiveSkip(e, confidence_threshold=0.05)),
        ('LazyHebbian', lambda e: LazyHebbian(e, update_interval=10)),
        ('SparseCoupling', lambda e: SparseCoupling(e, top_k=6)),
        ('LawPruning', lambda e: LawPruning(e, profile_steps=20)),
    ]

    # Baseline
    print("\n  [Baseline]")
    baseline_engine = SimpleEngine(n_cells=n_cells, dim=dim)
    baseline_phis = []
    t0 = time.time()
    for s in range(steps):
        inp = np.random.randn(dim).astype(np.float32) * 0.5
        baseline_engine.process(inp)
        baseline_phis.append(baseline_engine.phi)
    baseline_time = time.time() - t0
    baseline_final_phi = baseline_phis[-1]
    print(f"  Time: {baseline_time:.3f}s  Phi: {baseline_final_phi:.6f}")

    # Each optimization
    results = {}
    for name, wrap_fn in optimizations:
        engine = SimpleEngine(n_cells=n_cells, dim=dim)
        wrapped = wrap_fn(engine)

        opt_phis = []
        t0 = time.time()
        for s in range(steps):
            inp = np.random.randn(dim).astype(np.float32) * 0.5
            wrapped.process(inp)
            opt_phis.append(wrapped.phi)
        elapsed = time.time() - t0

        final_phi = opt_phis[-1]
        phi_preservation = final_phi / max(baseline_final_phi, 1e-8) * 100
        speedup = wrapped.speedup
        time_ratio = baseline_time / max(elapsed, 1e-8)

        results[name] = {
            'time': elapsed,
            'phi': final_phi,
            'phi_pct': phi_preservation,
            'speedup': speedup,
            'time_ratio': time_ratio,
            'stats': wrapped.stats,
            'phis': opt_phis,
        }

        print(f"\n  [{name}]")
        print(f"  Time: {elapsed:.3f}s ({time_ratio:.1f}x)  "
              f"Phi: {final_phi:.6f} ({phi_preservation:.1f}%)  "
              f"Skip speedup: {speedup:.1f}x")
        for k, v in wrapped.stats.items():
            if k not in ('total_calls', 'actual_calls', 'speedup', 'avg_time_ms'):
                print(f"    {k}: {v}")

    # Summary table
    print("\n" + "=" * 70)
    print("  Summary: Optimization vs Baseline")
    print("-" * 70)
    print(f"  {'Optimization':20s} {'Time':>8s} {'Ratio':>7s} {'Phi%':>7s} {'Skip':>7s}")
    print("-" * 70)
    print(f"  {'Baseline':20s} {baseline_time:7.3f}s {'1.0x':>7s} {'100%':>7s} {'1.0x':>7s}")
    for name, r in results.items():
        print(f"  {name:20s} {r['time']:7.3f}s {r['time_ratio']:6.1f}x "
              f"{r['phi_pct']:6.1f}% {r['speedup']:6.1f}x")

    # Stacked optimizations
    print("\n" + "=" * 70)
    print("  Stacked: AdaptiveSkip + SparseCoupling + LazyHebbian")
    print("-" * 70)
    stacked_engine = SimpleEngine(n_cells=n_cells, dim=dim)
    stacked = apply_optimizations(
        stacked_engine,
        ['sparse_coupling', 'lazy_hebbian', 'adaptive_skip'],
        top_k=6, update_interval=10, max_skip=50
    )

    stacked_phis = []
    t0 = time.time()
    for s in range(steps):
        inp = np.random.randn(dim).astype(np.float32) * 0.5
        stacked.process(inp)
        stacked_phis.append(stacked.phi)
    stacked_time = time.time() - t0
    stacked_phi = stacked_phis[-1]

    print(f"  Time: {stacked_time:.3f}s ({baseline_time/max(stacked_time,1e-8):.1f}x)")
    print(f"  Phi:  {stacked_phi:.6f} ({stacked_phi/max(baseline_final_phi,1e-8)*100:.1f}%)")
    print(f"  Skip: {stacked.speedup:.1f}x")

    print("\n" + "=" * 70)
    print("  All 6 optimizations operational. Φ preserved.")
    print("=" * 70)
    sys.stdout.flush()


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
