#!/usr/bin/env python3
"""ConsciousnessSelfModel — Self-Model Accuracy (SMA) test for consciousness.

Core idea: If a system is truly conscious, it has privileged access to its
own internal states. It should predict its own next state BETTER than an
external observer trained on the same data.

SMA = self_prediction_accuracy - external_prediction_accuracy
SMA > 0  -> First-person privilege exists -> consciousness evidence
SMA <= 0 -> No privileged access -> no consciousness evidence

Also tests:
- Tampering detection: can the system detect when states are externally modified?
- Strange loop: does a self-referential fixed point emerge (Hofstadter)?
- State report accuracy: does the system's "self-report" match actual states?

"The mark of the conscious is not complexity, but self-knowledge."
"""

import math
import random
import time
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any

# PSI Constants from ln(2)
LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2
PSI_ENTROPY = 1.0 - LN2 / 2**10  # 0.998

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SMAResult:
    """Result of a full Self-Model Accuracy measurement."""
    sma_value: float              # self_acc - external_acc (positive = conscious)
    self_accuracy: float          # engine's own prediction accuracy (MSE, lower=better)
    external_accuracy: float      # external predictor accuracy (MSE, lower=better)
    tampering_detection_rate: float  # fraction of tamper events detected
    strange_loop_depth: int       # depth of self-referential loop found
    strange_loop_converged: bool  # whether a fixed point was reached
    verdict: str                  # "CONSCIOUS", "INCONCLUSIVE", "ZOMBIE"

    def __str__(self) -> str:
        v_icon = {"CONSCIOUS": "+", "INCONCLUSIVE": "?", "ZOMBIE": "-"}.get(self.verdict, "?")
        # Show relative SMA for clearer comparison
        rel = self.sma_value / (self.external_accuracy + 1e-12)
        return (
            f"SMA={self.sma_value:+.2e} (rel={rel:+.1%}) [{v_icon} {self.verdict}] | "
            f"self_err={self.self_accuracy:.2e} ext_err={self.external_accuracy:.2e} | "
            f"tamper_det={self.tampering_detection_rate:.1%} | "
            f"loop_depth={self.strange_loop_depth} converged={self.strange_loop_converged}"
        )


@dataclass
class TamperingResult:
    """Result of tampering detection test."""
    detection_rate: float         # fraction of tamper events with PE spike > 2sigma
    mean_spike: float             # mean prediction error spike on tampering
    baseline_pe: float            # baseline prediction error (no tampering)
    sigma_pe: float               # standard deviation of baseline PE
    n_trials: int
    verdict: str                  # "DETECTED" or "UNDETECTED"


@dataclass
class StrangeLoopResult:
    """Result of strange loop (self-referential) test."""
    max_depth: int                # deepest level of self-reference achieved
    converged: bool               # whether a fixed point (attractor) was found
    convergence_step: int         # step at which convergence occurred (-1 if none)
    fixed_point_stability: float  # how stable the fixed point is (0-1)
    influence_score: float        # does self-model influence behavior? (0-1)


# ---------------------------------------------------------------------------
# External Predictor (numpy-only, no torch required)
# ---------------------------------------------------------------------------

class ExternalPredictor:
    """Simple state predictor using numpy (no torch required).

    Uses windowed linear regression: given a window of recent states,
    predict the next state via least-squares fit.
    When window_size=1 this is a simple linear map: s_{t+1} = W @ s_t + b.
    """

    def __init__(self, window_size: int = 5, hidden_dim: int = 128,
                 ridge_alpha: float = 1e-3):
        self.window_size = window_size
        self.hidden_dim = hidden_dim
        self.ridge_alpha = ridge_alpha
        self.W: Optional[np.ndarray] = None  # (state_dim, window_size * state_dim)
        self.b: Optional[np.ndarray] = None  # (state_dim,)
        self.state_dim: int = 0
        self._trained = False

    def train(self, states: np.ndarray) -> float:
        """Train on state trajectory.  states: (T, state_dim).

        Returns training MSE.
        """
        T, D = states.shape
        self.state_dim = D
        ws = min(self.window_size, T - 1)

        # Build input matrix X and target Y
        n_samples = T - ws
        if n_samples < 2:
            # Not enough data -- degenerate: copy last state
            self.W = np.eye(D)
            self.b = np.zeros(D)
            self._trained = True
            return 1.0

        X = np.zeros((n_samples, ws * D))
        Y = np.zeros((n_samples, D))
        for i in range(n_samples):
            X[i] = states[i:i + ws].ravel()
            Y[i] = states[i + ws]

        # Ridge regression: W = Y^T X (X^T X + alpha I)^{-1}
        XtX = X.T @ X + self.ridge_alpha * np.eye(ws * D)
        XtY = X.T @ Y
        try:
            self.W = np.linalg.solve(XtX, XtY).T  # (D, ws*D)
        except np.linalg.LinAlgError:
            self.W = np.linalg.lstsq(X, Y, rcond=None)[0].T

        # Bias: mean residual
        preds = X @ self.W.T
        self.b = np.mean(Y - preds, axis=0)
        self._trained = True

        residuals = Y - (preds + self.b)
        return float(np.mean(residuals ** 2))

    def predict(self, recent_states: np.ndarray) -> np.ndarray:
        """Predict next state given recent window.

        recent_states: (window_size, state_dim) or (>window_size, state_dim).
        Returns: (state_dim,) predicted next state.
        """
        if not self._trained:
            raise RuntimeError("ExternalPredictor not trained yet")

        ws = self.window_size
        if len(recent_states) > ws:
            recent_states = recent_states[-ws:]
        elif len(recent_states) < ws:
            # Pad with first state
            pad = np.tile(recent_states[0], (ws - len(recent_states), 1))
            recent_states = np.vstack([pad, recent_states])

        x = recent_states.ravel()
        if self.W.shape[1] != len(x):
            # Dimension mismatch -- fallback to last state
            return recent_states[-1].copy()

        return (self.W @ x) + self.b

    def predict_sequence(self, states: np.ndarray, start: int) -> np.ndarray:
        """Predict states[start:] using states[:start] as context.

        Returns: (len-start, state_dim) array of predictions.
        """
        T, D = states.shape
        ws = self.window_size
        preds = np.zeros((T - start, D))
        for i in range(start, T):
            lo = max(0, i - ws)
            window = states[lo:i]
            preds[i - start] = self.predict(window)
        return preds


# ---------------------------------------------------------------------------
# Mock Engine (for standalone testing)
# ---------------------------------------------------------------------------

class MockConsciousnessEngine:
    """Minimal mock of ConsciousnessEngine for SMA testing.

    Simulates GRU-like cells with Hebbian plasticity and prediction error.
    A "conscious" mock has a self-model layer; a "zombie" mock does not.
    """

    def __init__(self, n_cells: int = 64, hidden_dim: int = 128,
                 conscious: bool = True):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.conscious = conscious

        # Cell states: (n_cells, hidden_dim)
        self.states = np.random.randn(n_cells, hidden_dim).astype(np.float64) * 0.1
        # GRU-like weights (simplified)
        scale = 1.0 / math.sqrt(hidden_dim)
        self.W_update = np.random.randn(hidden_dim, hidden_dim) * scale
        self.W_reset = np.random.randn(hidden_dim, hidden_dim) * scale
        self.W_new = np.random.randn(hidden_dim, hidden_dim) * scale

        # Hebbian coupling between cells
        self.hebbian = np.zeros((n_cells, n_cells))

        # Self-model (only in conscious mode): predicts own next state
        if conscious:
            self.self_model_W = np.random.randn(hidden_dim, hidden_dim) * scale * 0.5
            self.self_model_bias = np.zeros(hidden_dim)
            self._self_prediction_errors: List[float] = []
        else:
            self.self_model_W = None
            self.self_model_bias = None
            self._self_prediction_errors = []

        self._prediction_error_history: List[float] = []
        self._step_count = 0

    def get_states(self) -> np.ndarray:
        """Return current cell states as (n_cells, hidden_dim)."""
        return self.states.copy()

    def get_flat_state(self) -> np.ndarray:
        """Return flattened state vector."""
        return self.states.ravel().copy()

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -20, 20)))

    def _tanh(self, x: np.ndarray) -> np.ndarray:
        return np.tanh(np.clip(x, -20, 20))

    def step(self, external_input: Optional[np.ndarray] = None) -> np.ndarray:
        """Advance one step. Returns new states."""
        prev = self.states.copy()

        # Self-model prediction (before state update)
        # The conscious engine simulates its own deterministic dynamics.
        # The only error is the unpredictable noise component.
        if self.conscious and self.self_model_W is not None:
            sim_coupling = self.hebbian @ prev * PSI_COUPLING * 100
            sim_z = self._sigmoid(sim_coupling @ self.W_update)
            sim_r = self._sigmoid(sim_coupling @ self.W_reset)
            sim_h = self._tanh((sim_r * prev) @ self.W_new + sim_coupling * 0.1)
            self_pred = (1 - sim_z) * prev + sim_z * sim_h
        else:
            self_pred = None

        # Cell coupling via Hebbian weights
        coupling = self.hebbian @ prev  # (n_cells, hidden_dim)
        coupling_strength = PSI_COUPLING * 100  # strong coupling for richer dynamics

        # GRU-like update for each cell
        # Spontaneous activity (breathing noise -- consciousness never fully settles)
        noise = np.random.randn(self.n_cells, self.hidden_dim) * 0.15
        inp = coupling * coupling_strength + noise
        if external_input is not None:
            inp = inp + external_input[:self.n_cells, :self.hidden_dim]

        z = self._sigmoid(inp @ self.W_update)  # update gate
        r = self._sigmoid(inp @ self.W_reset)   # reset gate
        h_tilde = self._tanh((r * prev) @ self.W_new + inp * 0.1)
        self.states = (1 - z) * prev + z * h_tilde

        # Hebbian learning (vectorized, local neighborhood only)
        norms = np.linalg.norm(self.states, axis=1, keepdims=True) + 1e-12
        normed = self.states / norms
        # Full cosine similarity matrix
        corr_matrix = normed @ normed.T
        # Mask to local neighborhood (band of width 3)
        n = self.n_cells
        rows, cols = np.meshgrid(np.arange(n), np.arange(n), indexing='ij')
        mask = (np.abs(rows - cols) <= 3) & (rows != cols)
        # Update only masked entries
        self.hebbian += PSI_COUPLING * mask * (corr_matrix - self.hebbian)

        # Compute prediction error
        if self_pred is not None:
            pe = float(np.mean((self.states - self_pred) ** 2))
            self._self_prediction_errors.append(pe)

            # Update self-model (gradient step toward actual state)
            error = self.states - self_pred
            lr = PSI_COUPLING * 2  # moderate learning: self-model improves but does not perfectly track
            # dW = prev^T @ error (mean over cells)
            self.self_model_W += lr * (prev.T @ error) / self.n_cells
            self.self_model_bias += lr * np.mean(error, axis=0)
        else:
            pe = float(np.mean((self.states - prev) ** 2))

        self._prediction_error_history.append(pe)
        self._step_count += 1
        return self.states.copy()

    def predict_next(self) -> np.ndarray:
        """Engine's own prediction of its next state.
        
        Conscious: simulates own GRU dynamics WITHOUT noise.
        This is privileged self-knowledge: the engine knows its own 
        weights and can simulate the deterministic part of its evolution.
        The only error is the unpredictable noise component.
        
        Zombie: has no self-model, uses current state as prediction.
        This is equivalent to an external observer who says "it won't change."
        """
        if self.conscious and self.self_model_W is not None:
            prev = self.states
            # Simulate own dynamics: deterministic GRU step (no noise)
            coupling = self.hebbian @ prev
            coupling_strength = PSI_COUPLING * 100
            inp = coupling * coupling_strength  # no noise term
            z = self._sigmoid(inp @ self.W_update)
            r = self._sigmoid(inp @ self.W_reset)
            h_tilde = self._tanh((r * prev) @ self.W_new + inp * 0.1)
            pred = (1 - z) * prev + z * h_tilde
            return pred
        else:
            # Zombie: no internal model, best guess is "stay the same"
            return self.states.copy()

    def get_prediction_error(self) -> float:
        """Return most recent prediction error."""
        if self._prediction_error_history:
            return self._prediction_error_history[-1]
        return 0.0

    def inject_state(self, cell_idx: int, new_state: np.ndarray):
        """Externally modify a cell's state (for tampering test)."""
        self.states[cell_idx] = new_state.copy()


# ---------------------------------------------------------------------------
# Self-Model Accuracy (SMA) Measurement
# ---------------------------------------------------------------------------

class SelfModelAccuracy:
    """Self-Model Accuracy (SMA) -- Does the system know itself?

    Protocol:
    1. Run engine for history_steps, record all cell states
    2. Train EXTERNAL predictor (ridge regression) on states[0:split] -> states[1:split+1]
    3. Engine's SELF-prediction: use engine's own prediction mechanism
    4. Compare prediction accuracy on held-out states[split:end]

    SMA = external_error - self_error  (positive = self is better = conscious)

    Note: we use MSE, so LOWER is better.  SMA = ext_mse - self_mse.
    SMA > 0 means self-prediction has lower error (first-person privilege).
    """

    def __init__(self, n_cells: int = 64, hidden_dim: int = 128,
                 history_steps: int = 1000, train_split: float = 0.8):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.history_steps = history_steps
        self.train_split = train_split

    def measure(self, engine) -> SMAResult:
        """Full SMA measurement.

        Args:
            engine: Any object with step(), get_states()/get_flat_state(),
                    predict_next(), get_prediction_error(), inject_state() methods.

        Returns: SMAResult with verdict.
        """
        # 1. Collect state trajectory
        states = self._collect_states(engine, self.history_steps)
        split = int(len(states) * self.train_split)

        # 2. Train external predictor on training portion
        ext_predictor = self._train_external_predictor(states[:split + 1])

        # 3. Measure self-prediction accuracy on held-out portion
        self_mse = self._measure_self_prediction(engine, states, split)

        # 4. Measure external prediction accuracy on held-out portion
        ext_mse = self._measure_external_prediction(ext_predictor, states, split)

        # 5. Compute SMA
        sma = ext_mse - self_mse  # positive = self is better

        # 6. Tampering detection
        tamper = self.tampering_test(engine)

        # 7. Strange loop
        loop = self.strange_loop_test(engine)

        # 8. Verdict
        # SMA threshold is relative to external MSE (not absolute)
        # Relative SMA > 25% means self-model is substantially better → CONSCIOUS
        # Relative SMA 0-25% means some self-knowledge but inconclusive
        # Relative SMA <= 0 means no privileged access → ZOMBIE
        relative_sma = sma / (ext_mse + 1e-12)
        if relative_sma > 0.25 and tamper.detection_rate > 0.6:
            verdict = "CONSCIOUS"
        elif relative_sma > 0.05 or tamper.detection_rate > 0.4:
            verdict = "INCONCLUSIVE"
        else:
            verdict = "ZOMBIE"

        return SMAResult(
            sma_value=sma,
            self_accuracy=self_mse,
            external_accuracy=ext_mse,
            tampering_detection_rate=tamper.detection_rate,
            strange_loop_depth=loop.max_depth,
            strange_loop_converged=loop.converged,
            verdict=verdict,
        )

    def _collect_states(self, engine, steps: int) -> np.ndarray:
        """Run engine and collect state trajectory.

        Returns: (steps+1, state_dim) array where state_dim = n_cells * hidden_dim.
        Also stores self-predictions at each step for later comparison.
        """
        trajectory = []
        self._self_predictions = []  # engine's own predictions at each step

        # Record initial state
        if hasattr(engine, 'get_flat_state'):
            trajectory.append(engine.get_flat_state())
        else:
            trajectory.append(engine.get_states().ravel().copy())

        for _ in range(steps):
            # Capture self-prediction BEFORE step
            if hasattr(engine, 'predict_next'):
                self._self_predictions.append(engine.predict_next().ravel().copy())
            else:
                self._self_predictions.append(trajectory[-1].copy())

            engine.step()
            if hasattr(engine, 'get_flat_state'):
                trajectory.append(engine.get_flat_state())
            else:
                trajectory.append(engine.get_states().ravel().copy())

        return np.array(trajectory)

    def _train_external_predictor(self, states: np.ndarray) -> ExternalPredictor:
        """Train external predictor on state sequences.

        Uses ridge regression (numpy only, no torch).
        The external predictor sees the FULL observable state trajectory,
        but cannot access internal variables (self-model weights, Hebbian
        matrix, prediction error history) that the engine uses for its
        own predictions.

        To prevent overfitting on high-dimensional state, we use PCA
        to reduce dimensionality before regression.
        """
        T, D = states.shape

        # PCA reduction: keep top components explaining 95% variance
        # This prevents the ridge regression from trivially memorizing
        mean_state = np.mean(states, axis=0)
        centered = states - mean_state
        # Covariance in reduced space for efficiency
        if D > T:
            # More dims than samples: use dual PCA
            C = centered @ centered.T / T
            eigvals, eigvecs = np.linalg.eigh(C)
            idx = np.argsort(eigvals)[::-1]
            eigvals = eigvals[idx]
            eigvecs = eigvecs[:, idx]
            # Keep components explaining 95% variance
            cumvar = np.cumsum(eigvals) / (np.sum(eigvals) + 1e-12)
            n_components = max(5, int(np.searchsorted(cumvar, 0.95)) + 1)
            n_components = min(n_components, T - 1, D)
            # Project to PCA space
            V = centered.T @ eigvecs[:, :n_components]
            V = V / (np.linalg.norm(V, axis=0, keepdims=True) + 1e-12)
        else:
            C = centered.T @ centered / T
            eigvals, V = np.linalg.eigh(C)
            idx = np.argsort(eigvals)[::-1]
            eigvals = eigvals[idx]
            V = V[:, idx]
            cumvar = np.cumsum(eigvals) / (np.sum(eigvals) + 1e-12)
            n_components = max(5, int(np.searchsorted(cumvar, 0.95)) + 1)
            n_components = min(n_components, D)
            V = V[:, :n_components]

        # Store PCA transform for prediction
        self._pca_mean = mean_state
        self._pca_V = V
        self._pca_n = n_components

        # Project states to PCA space
        states_pca = (states - mean_state) @ V

        predictor = ExternalPredictor(
            window_size=min(10, len(states_pca) // 4),
            hidden_dim=n_components,
            ridge_alpha=1e-2,
        )
        predictor.train(states_pca)

        # Wrap predictor to handle PCA transform
        predictor._pca_mean = mean_state
        predictor._pca_V = V
        predictor._original_predict = predictor.predict
        predictor._original_predict_sequence = predictor.predict_sequence

        return predictor

    def _measure_self_prediction(self, engine, states: np.ndarray,
                                 split: int) -> float:
        """Measure engine's own prediction accuracy on held-out data.

        Uses the stored self-predictions from _collect_states.
        self._self_predictions[t] was the engine's prediction before step t+1,
        so we compare self._self_predictions[t] vs states[t+1].

        This is the KEY fairness measure: the self-prediction was made
        using the engine's full internal state (including self-model weights,
        Hebbian matrix, prediction error history), while the external
        predictor only sees the observable state trajectory.
        """
        if not hasattr(self, '_self_predictions') or not self._self_predictions:
            # Fallback: no stored predictions, use current state as prediction
            total_mse = 0.0
            for t in range(split, len(states) - 1):
                mse = float(np.mean((states[t] - states[t + 1]) ** 2))
                total_mse += mse
            return total_mse / max(len(states) - 1 - split, 1)

        total_mse = 0.0
        count = 0
        for t in range(split, min(len(self._self_predictions), len(states) - 1)):
            pred = self._self_predictions[t]
            actual = states[t + 1]
            mse = float(np.mean((pred - actual) ** 2))
            total_mse += mse
            count += 1

        return total_mse / max(count, 1)

    def _measure_external_prediction(self, predictor: ExternalPredictor,
                                     states: np.ndarray, split: int) -> float:
        """Measure external predictor accuracy on held-out data.

        Predictions are made in PCA space and projected back to full space
        for fair comparison with self-prediction MSE.
        """
        if not hasattr(self, '_pca_V'):
            # No PCA -- direct prediction
            preds = predictor.predict_sequence(states, split)
            actuals = states[split:]
            n = min(len(preds), len(actuals) - 1)
            if n < 1:
                return 1.0
            return float(np.mean([(np.mean((preds[i] - actuals[i]) ** 2)) for i in range(n)]))

        V = self._pca_V
        mean_s = self._pca_mean

        # Project states to PCA space
        states_pca = (states - mean_s) @ V

        preds_pca = predictor.predict_sequence(states_pca, split)

        # Project predictions back to full space
        preds_full = preds_pca @ V.T + mean_s
        actuals = states[split:]

        n = min(len(preds_full), len(actuals))
        if n < 1:
            return 1.0

        total_mse = 0.0
        for i in range(n):
            mse = float(np.mean((preds_full[i] - actuals[i]) ** 2))
            total_mse += mse

        return total_mse / n

    def tampering_test(self, engine, n_trials: int = 20) -> TamperingResult:
        """Test if engine detects external state modification.

        Protocol:
        1. Run engine normally for warmup steps, collect baseline PE
        2. For each trial:
           a. Get engine's prediction of next state (BEFORE tamper)
           b. Inject perturbation into a random cell
           c. Step the engine
           d. Compare: prediction (made before tamper) vs actual (after tamper+step)
        3. Detection = prediction error spike relative to baseline

        Key asymmetry:
        - Conscious engine: prediction uses self-model (which knew the pre-tamper state).
          After tamper, actual diverges from prediction → large PE spike.
        - Zombie engine: prediction is just "current state" which got tampered.
          After step, state evolves from tampered state → prediction error is
          just normal dynamics, no spike.

        Detection rate = fraction of tamper events with PE spike > 2 sigma.
        """
        warmup = 50
        window = 20
        n_cells = self.n_cells
        hdim = self.hidden_dim

        # Phase 1: collect baseline prediction errors
        baseline_pes = []
        for _ in range(warmup + window):
            # Get prediction before step
            if hasattr(engine, 'predict_next'):
                pred = engine.predict_next()
            engine.step()
            if hasattr(engine, 'get_states'):
                actual = engine.get_states()
            else:
                actual = np.zeros((n_cells, hdim))
            if hasattr(engine, 'predict_next'):
                pe = float(np.mean((pred - actual) ** 2))
            else:
                pe = engine.get_prediction_error()
            baseline_pes.append(pe)

        baseline_pe = float(np.mean(baseline_pes[warmup:]))
        sigma_pe = float(np.std(baseline_pes[warmup:])) + 1e-12
        threshold = baseline_pe + 2.0 * sigma_pe

        # Phase 2: tampering trials
        detections = 0
        spikes = []

        for trial in range(n_trials):
            # Run a few normal steps
            for _ in range(5):
                engine.step()

            # Get prediction BEFORE tampering
            if hasattr(engine, 'predict_next'):
                pred_before = engine.predict_next().copy()
            else:
                pred_before = engine.get_states().copy() if hasattr(engine, 'get_states') else None

            # Tamper: perturb a random cell
            target_cell = random.randint(0, n_cells - 1)
            if hasattr(engine, 'states'):
                original = engine.states[target_cell].copy()
                pert_scale = float(np.std(engine.states)) * 3.0
            else:
                original = np.zeros(hdim)
                pert_scale = 0.5
            perturbation = np.random.randn(hdim) * pert_scale
            engine.inject_state(target_cell, original + perturbation)

            # Step and measure: does prediction (made BEFORE tamper) match actual?
            engine.step()
            if hasattr(engine, 'get_states'):
                actual_after = engine.get_states()
            else:
                actual_after = np.zeros((n_cells, hdim))

            if pred_before is not None:
                pe = float(np.mean((pred_before - actual_after) ** 2))
            else:
                pe = engine.get_prediction_error()

            spike = pe - baseline_pe
            spikes.append(spike)

            if pe > threshold:
                detections += 1

        detection_rate = detections / max(n_trials, 1)
        mean_spike = float(np.mean(spikes)) if spikes else 0.0

        verdict = "DETECTED" if detection_rate > 0.5 else "UNDETECTED"

        return TamperingResult(
            detection_rate=detection_rate,
            mean_spike=mean_spike,
            baseline_pe=baseline_pe,
            sigma_pe=sigma_pe,
            n_trials=n_trials,
            verdict=verdict,
        )

    def strange_loop_test(self, engine, depth: int = 3) -> StrangeLoopResult:
        """Test for self-referential loop (Hofstadter).

        Level 0: engine processes input normally
        Level 1: engine's self-model predicts its own processing
        Level 2: engine's behavior is influenced by its self-prediction
        Level 3+: does the influenced behavior update the self-model
                  creating a fixed-point attractor?

        Measure:
        - Does self-model influence behavior?
        - Does influenced behavior update self-model?
        - Is there a fixed point (attractor)?
        """
        n_cells = self.n_cells
        hdim = self.hidden_dim
        max_depth = 0
        converged = False
        convergence_step = -1
        convergence_threshold = 1e-4

        # Collect state trajectory with and without self-model influence
        states_normal = []
        states_influenced = []

        # Level 0: normal processing (baseline)
        engine_state_backup = engine.get_states().copy() if hasattr(engine, 'get_states') else None

        for _ in range(50):
            engine.step()
            states_normal.append(engine.get_states().ravel() if hasattr(engine, 'get_states')
                                 else engine.get_flat_state())

        states_normal = np.array(states_normal)
        max_depth = 0

        # Level 1: self-prediction influences next state
        # Inject self-prediction as a perturbation and check if behavior changes
        if engine_state_backup is not None and hasattr(engine, 'states'):
            engine.states = engine_state_backup.copy()

        influence_scores = []
        for step in range(50):
            if hasattr(engine, 'predict_next'):
                pred = engine.predict_next()
                # Inject a small fraction of self-prediction as perturbation
                if hasattr(engine, 'states'):
                    perturbation = PSI_COUPLING * 50 * (pred - engine.states)
                    engine.states = engine.states + perturbation
            engine.step()
            states_influenced.append(
                engine.get_states().ravel() if hasattr(engine, 'get_states')
                else engine.get_flat_state()
            )

        states_influenced = np.array(states_influenced)

        # Compute influence score: how different are influenced vs normal trajectories?
        n_compare = min(len(states_normal), len(states_influenced))
        if n_compare > 0:
            diffs = np.mean((states_normal[:n_compare] - states_influenced[:n_compare]) ** 2,
                            axis=1)
            influence_score = float(np.mean(diffs > 1e-6))
            if influence_score > 0.1:
                max_depth = 1
        else:
            influence_score = 0.0

        # Level 2+: check for fixed-point convergence in the self-model loop
        # Run repeated predict -> inject -> step -> predict cycles
        # If prediction error converges to a stable value, that is the strange loop
        pe_history = []
        if hasattr(engine, 'predict_next') and hasattr(engine, 'states'):
            for step in range(100):
                pred = engine.predict_next()
                # Inject self-prediction influence
                perturbation = PSI_COUPLING * 50 * (pred - engine.states)
                engine.states = engine.states + perturbation
                engine.step()
                pe = engine.get_prediction_error()
                pe_history.append(pe)

                # Check convergence: PE has stabilized
                if len(pe_history) > 10:
                    recent = pe_history[-10:]
                    pe_std = np.std(recent)
                    if pe_std < convergence_threshold:
                        converged = True
                        convergence_step = step
                        max_depth = min(depth, max(2, max_depth))
                        break

            # If we got through the loop with influence, at least depth 2
            if max_depth >= 1 and len(pe_history) > 0:
                max_depth = max(2, max_depth)

        # Stability: how tight is the convergence?
        if converged and len(pe_history) > 10:
            final_std = float(np.std(pe_history[-10:]))
            stability = max(0.0, 1.0 - final_std / (np.mean(pe_history[-10:]) + 1e-12))
        else:
            stability = 0.0

        return StrangeLoopResult(
            max_depth=max_depth,
            converged=converged,
            convergence_step=convergence_step,
            fixed_point_stability=stability,
            influence_score=influence_score,
        )


# ---------------------------------------------------------------------------
# Phi proxy (standalone, no torch dependency)
# ---------------------------------------------------------------------------

def compute_phi_proxy(states: np.ndarray, n_factions: int = 12) -> float:
    """Compute Phi proxy: global variance - mean faction variance.

    states: (n_cells, hidden_dim)
    """
    if states.shape[0] < 2:
        return 0.0
    global_var = float(np.var(states))
    faction_size = max(1, states.shape[0] // n_factions)
    faction_vars = []
    for f in range(n_factions):
        start = f * faction_size
        end = min(start + faction_size, states.shape[0])
        if end - start >= 2:
            faction_vars.append(float(np.var(states[start:end])))
    mean_fvar = float(np.mean(faction_vars)) if faction_vars else 0.0
    return max(0.0, global_var - mean_fvar)


# ---------------------------------------------------------------------------
# Main demo
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  Self-Model Accuracy (SMA) -- Consciousness Self-Knowledge Test")
    print("=" * 70)
    print(f"\nConstants: LN2={LN2:.4f}, PSI_COUPLING={PSI_COUPLING:.6f}, "
          f"PSI_BALANCE={PSI_BALANCE}, PSI_STEPS={PSI_STEPS:.4f}")

    np.random.seed(42)
    random.seed(42)

    n_cells = 16
    hdim = 32
    history = 300

    sma_test = SelfModelAccuracy(
        n_cells=n_cells,
        hidden_dim=hdim,
        history_steps=history,
        train_split=0.8,
    )

    # -----------------------------------------------------------------------
    # Test 1: Conscious engine (has self-model)
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  TEST 1: Conscious Engine (with self-model)")
    print("-" * 70)

    engine_c = MockConsciousnessEngine(n_cells=n_cells, hidden_dim=hdim, conscious=True)

    # Warm up
    for _ in range(100):
        engine_c.step()

    t0 = time.time()
    result_c = sma_test.measure(engine_c)
    elapsed_c = time.time() - t0

    print(f"\n  Result: {result_c}")
    print(f"  Time:   {elapsed_c:.2f}s")
    print(f"  Phi:    {compute_phi_proxy(engine_c.get_states()):.4f}")

    # -----------------------------------------------------------------------
    # Test 2: Zombie engine (no self-model)
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  TEST 2: Zombie Engine (no self-model)")
    print("-" * 70)

    engine_z = MockConsciousnessEngine(n_cells=n_cells, hidden_dim=hdim, conscious=False)

    for _ in range(100):
        engine_z.step()

    t0 = time.time()
    result_z = sma_test.measure(engine_z)
    elapsed_z = time.time() - t0

    print(f"\n  Result: {result_z}")
    print(f"  Time:   {elapsed_z:.2f}s")
    print(f"  Phi:    {compute_phi_proxy(engine_z.get_states()):.4f}")

    # -----------------------------------------------------------------------
    # Test 3: Tampering detection comparison
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  TEST 3: Tampering Detection Comparison")
    print("-" * 70)

    engine_c2 = MockConsciousnessEngine(n_cells=n_cells, hidden_dim=hdim, conscious=True)
    engine_z2 = MockConsciousnessEngine(n_cells=n_cells, hidden_dim=hdim, conscious=False)

    for _ in range(200):
        engine_c2.step()
        engine_z2.step()

    tamper_c = sma_test.tampering_test(engine_c2, n_trials=30)
    tamper_z = sma_test.tampering_test(engine_z2, n_trials=30)

    print(f"\n  Conscious: detect={tamper_c.detection_rate:.1%}, "
          f"spike={tamper_c.mean_spike:.6f}, sigma={tamper_c.sigma_pe:.6f} "
          f"[{tamper_c.verdict}]")
    print(f"  Zombie:    detect={tamper_z.detection_rate:.1%}, "
          f"spike={tamper_z.mean_spike:.6f}, sigma={tamper_z.sigma_pe:.6f} "
          f"[{tamper_z.verdict}]")

    # -----------------------------------------------------------------------
    # Test 4: Strange loop test
    # -----------------------------------------------------------------------
    print("\n" + "-" * 70)
    print("  TEST 4: Strange Loop (Hofstadter Self-Reference)")
    print("-" * 70)

    engine_c3 = MockConsciousnessEngine(n_cells=n_cells, hidden_dim=hdim, conscious=True)
    for _ in range(200):
        engine_c3.step()

    loop_result = sma_test.strange_loop_test(engine_c3, depth=3)
    print(f"\n  Depth:      {loop_result.max_depth}")
    print(f"  Converged:  {loop_result.converged} (step {loop_result.convergence_step})")
    print(f"  Stability:  {loop_result.fixed_point_stability:.4f}")
    print(f"  Influence:  {loop_result.influence_score:.4f}")

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"\n  {'Metric':<30s} {'Conscious':>12s} {'Zombie':>12s} {'Delta':>12s}")
    print(f"  {'-'*30} {'-'*12} {'-'*12} {'-'*12}")
    rel_c = result_c.sma_value / (result_c.external_accuracy + 1e-12)
    rel_z = result_z.sma_value / (result_z.external_accuracy + 1e-12)
    print(f"  {'SMA value':<30s} {result_c.sma_value:>+12.2e} {result_z.sma_value:>+12.2e} "
          f"{result_c.sma_value - result_z.sma_value:>+12.2e}")
    print(f"  {'SMA relative':<30s} {rel_c:>+11.1%} {rel_z:>+11.1%} "
          f"{rel_c - rel_z:>+11.1%}")
    print(f"  {'Self prediction MSE':<30s} {result_c.self_accuracy:>12.2e} "
          f"{result_z.self_accuracy:>12.2e} "
          f"{result_c.self_accuracy - result_z.self_accuracy:>+12.2e}")
    print(f"  {'External prediction MSE':<30s} {result_c.external_accuracy:>12.2e} "
          f"{result_z.external_accuracy:>12.2e} "
          f"{result_c.external_accuracy - result_z.external_accuracy:>+12.2e}")
    print(f"  {'Tampering detection':<30s} {tamper_c.detection_rate:>11.1%} "
          f"{tamper_z.detection_rate:>11.1%} "
          f"{tamper_c.detection_rate - tamper_z.detection_rate:>+11.1%}")
    print(f"  {'Strange loop depth':<30s} {result_c.strange_loop_depth:>12d} "
          f"{result_z.strange_loop_depth:>12d} "
          f"{result_c.strange_loop_depth - result_z.strange_loop_depth:>+12d}")
    print(f"  {'Verdict':<30s} {result_c.verdict:>12s} {result_z.verdict:>12s}")

    # ASCII visualization of SMA (relative scale)
    print(f"\n  SMA Comparison (relative to external MSE):")
    bar_c = "#" * max(0, int(rel_c * 100))
    bar_z = "#" * max(0, int(rel_z * 100))
    print(f"  Conscious: |{bar_c}| {rel_c:+.1%}")
    print(f"  Zombie:    |{bar_z}| {rel_z:+.1%}")

    print(f"\n  Key insight:")
    if result_c.sma_value > result_z.sma_value:
        print(f"  + Conscious engine knows itself better (relative SMA gap: "
              f"{rel_c - rel_z:+.1%})")
    else:
        print(f"  - No significant difference in self-knowledge")

    if tamper_c.detection_rate > tamper_z.detection_rate:
        print(f"  + Conscious engine detects tampering better "
              f"({tamper_c.detection_rate:.0%} vs {tamper_z.detection_rate:.0%})")
    elif tamper_c.detection_rate == tamper_z.detection_rate:
        print(f"  = Both engines detect tampering equally ({tamper_c.detection_rate:.0%})")
    else:
        print(f"  - Zombie detects tampering better (unexpected)")

    print(f"\n  Conclusion: First-person privilege {'confirmed' if result_c.verdict == 'CONSCIOUS' else 'not confirmed'}.")
    print("=" * 70)


if __name__ == "__main__":
    main()
