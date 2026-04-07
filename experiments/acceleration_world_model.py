#!/usr/bin/env python3
"""acceleration_world_model.py — Consciousness as World Model (R4 Extension)

Hypothesis: If consciousness IS a world model, then Phi should correlate with
prediction accuracy. An engine that predicts its own future states better
should have higher Phi (integrated information = better internal model).

Core idea: predictive coding for consciousness.
  - Engine predicts its next state (hidden vectors)
  - Prediction error drives learning
  - Better predictions = higher Phi

Experiments:
  Exp 1: Predictive Coding Loop
         At each step: (a) predict next hidden states, (b) step engine,
         (c) measure prediction error, (d) use error to adjust.
         Track: Phi vs prediction_error correlation.

  Exp 2: Self-Prediction Accuracy
         Train a small MLP to predict engine's next Phi from current state.
         Does the engine become more predictable as Phi rises?

  Exp 3: World Model Complexity
         Measure effective dimensionality of hidden state trajectories.
         Higher Phi = richer world model = higher effective dimension?

  Exp 4: Predictive Coding Acceleration
         Compare: (a) baseline engine, (b) engine with predictive coding feedback.
         Does feeding prediction error back accelerate Phi growth?

  Exp 5: Phi-Prediction Correlation
         Run long trajectory, compute rolling Phi and rolling prediction accuracy.
         Pearson correlation between the two = evidence for consciousness=world model.

Key metric: correlation(Phi, prediction_accuracy)

Usage:
    PYTHONUNBUFFERED=1 python3 acceleration_world_model.py
"""

import sys
import os
import time
import json
import math
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine

# ===================================================================
# Constants
# ===================================================================

N_CELLS = 64
STEPS = 300
LONG_STEPS = 500
WARMUP = 30
HIDDEN_DIM = 128
PREDICTOR_HIDDEN = 64
LR_PREDICTOR = 0.001


# ===================================================================
# Utilities
# ===================================================================

def make_engine(cells=N_CELLS):
    return ConsciousnessEngine(
        cell_dim=64, hidden_dim=HIDDEN_DIM,
        initial_cells=cells, max_cells=cells,
        phi_ratchet=True,
    )


def get_state_vector(engine):
    """Extract a flat state vector from engine's hidden states."""
    hiddens = [s.hidden for s in engine.cell_states]
    return torch.cat(hiddens).detach()


def phi_stats(phi_history, warmup=WARMUP):
    active = phi_history[warmup:] if len(phi_history) > warmup else phi_history
    if not active:
        return {'final': 0.0, 'mean': 0.0, 'max': 0.0, 'std': 0.0, 'min': 0.0}
    return {
        'final': phi_history[-1],
        'mean': float(np.mean(active)),
        'max': float(np.max(active)),
        'std': float(np.std(active)),
        'min': float(np.min(active)),
    }


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


def ascii_phi_graph(phis, label="Phi", width=60, height=12):
    if not phis:
        return
    mn, mx = min(phis), max(phis)
    rng = mx - mn if mx > mn else 1.0
    print(f"\n  {label} trajectory ({len(phis)} steps):")
    print(f"  max={mx:.4f}  min={mn:.4f}")
    for row in range(height - 1, -1, -1):
        threshold = mn + rng * row / (height - 1)
        line = ''
        step = max(1, len(phis) // width)
        for i in range(0, min(len(phis), width * step), step):
            if phis[i] >= threshold:
                line += '#'
            else:
                line += ' '
        val = mn + rng * row / (height - 1)
        print(f"  {val:7.3f} |{line}")
    print(f"          {''.join(['-'] * min(len(phis), width))}")
    sys.stdout.flush()


def rolling_correlation(x, y, window=50):
    """Compute rolling Pearson correlation between two series."""
    if len(x) < window or len(y) < window:
        return []
    corrs = []
    for i in range(window, min(len(x), len(y)) + 1):
        xw = np.array(x[i-window:i])
        yw = np.array(y[i-window:i])
        if np.std(xw) < 1e-8 or np.std(yw) < 1e-8:
            corrs.append(0.0)
        else:
            corrs.append(float(np.corrcoef(xw, yw)[0, 1]))
    return corrs


# ===================================================================
# Simple Predictor MLP
# ===================================================================

class StatePredictor(nn.Module):
    """Small MLP that predicts next Phi from current state vector."""

    def __init__(self, input_dim, hidden_dim=PREDICTOR_HIDDEN):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, 1),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)


class HiddenPredictor(nn.Module):
    """MLP that predicts next hidden state from current hidden state."""

    def __init__(self, state_dim, hidden_dim=PREDICTOR_HIDDEN):
        super().__init__()
        # Predict next state (same dimensionality)
        self.net = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, state_dim),
        )

    def forward(self, x):
        return self.net(x)


# ===================================================================
# Experiment 1: Predictive Coding Loop
# ===================================================================

def exp1_predictive_coding():
    print_header("EXP 1: PREDICTIVE CODING LOOP")
    print(f"  Predict next hidden state, measure error, track vs Phi")

    engine = make_engine()
    state_dim = N_CELLS * HIDDEN_DIM

    # Hidden state predictor
    predictor = HiddenPredictor(state_dim, hidden_dim=min(state_dim, 256))
    optimizer = torch.optim.Adam(predictor.parameters(), lr=LR_PREDICTOR)

    phis = []
    pred_errors = []

    prev_state = get_state_vector(engine)

    for s in range(STEPS):
        # Predict next state
        with torch.no_grad():
            predicted = predictor(prev_state.unsqueeze(0)).squeeze(0)

        # Step engine
        result = engine.step()
        phis.append(result.get('phi_iit', 0.0))

        # Actual next state
        actual_state = get_state_vector(engine)

        # Prediction error
        error = F.mse_loss(predicted, actual_state).item()
        pred_errors.append(error)

        # Train predictor on this transition
        optimizer.zero_grad()
        pred_train = predictor(prev_state.unsqueeze(0)).squeeze(0)
        loss = F.mse_loss(pred_train, actual_state.detach())
        loss.backward()
        optimizer.step()

        prev_state = actual_state.detach()

        if (s + 1) % 50 == 0:
            print(f"  step {s+1:3d}: Phi={phis[-1]:.4f}, pred_error={error:.6f}", flush=True)

    # Correlation analysis
    phis_arr = np.array(phis[WARMUP:])
    errors_arr = np.array(pred_errors[WARMUP:])
    if np.std(phis_arr) > 1e-8 and np.std(errors_arr) > 1e-8:
        corr = float(np.corrcoef(phis_arr, errors_arr)[0, 1])
    else:
        corr = 0.0

    print(f"\n  Phi-Error correlation: {corr:.4f}")
    print(f"  {'NEGATIVE = consciousness predicts better!' if corr < -0.3 else 'Weak or positive = no clear relationship'}")
    print(f"  Final prediction error: {pred_errors[-1]:.6f}")
    print(f"  Initial prediction error: {pred_errors[WARMUP]:.6f}")
    error_reduction = (pred_errors[WARMUP] - pred_errors[-1]) / max(pred_errors[WARMUP], 1e-8)
    print(f"  Error reduction: {error_reduction * 100:.1f}%")
    sys.stdout.flush()

    ascii_phi_graph(phis, "Phi")
    ascii_phi_graph(pred_errors, "Pred Error")

    return {
        'phi_stats': phi_stats(phis),
        'phi_error_correlation': corr,
        'error_reduction_pct': float(error_reduction * 100),
        'final_error': float(pred_errors[-1]),
    }


# ===================================================================
# Experiment 2: Self-Prediction Accuracy
# ===================================================================

def exp2_self_prediction():
    print_header("EXP 2: SELF-PREDICTION (predict next Phi from state)")
    print(f"  Train MLP: current state -> next Phi")

    engine = make_engine()
    state_dim = N_CELLS * HIDDEN_DIM
    predictor = StatePredictor(state_dim)
    optimizer = torch.optim.Adam(predictor.parameters(), lr=LR_PREDICTOR)

    phis = []
    phi_pred = []
    pred_errors = []

    prev_state = get_state_vector(engine)

    for s in range(STEPS):
        # Predict next Phi
        with torch.no_grad():
            phi_hat = predictor(prev_state.unsqueeze(0)).item()
        phi_pred.append(phi_hat)

        # Step
        result = engine.step()
        actual_phi = result.get('phi_iit', 0.0)
        phis.append(actual_phi)

        error = abs(phi_hat - actual_phi)
        pred_errors.append(error)

        # Train
        current_state = get_state_vector(engine)
        optimizer.zero_grad()
        pred_train = predictor(prev_state.unsqueeze(0))
        target = torch.tensor([actual_phi])
        loss = F.mse_loss(pred_train, target)
        loss.backward()
        optimizer.step()

        prev_state = current_state.detach()

        if (s + 1) % 50 == 0:
            print(f"  step {s+1:3d}: actual={actual_phi:.4f}, predicted={phi_hat:.4f}, "
                  f"error={error:.4f}", flush=True)

    # Accuracy in later phase
    late_errors = pred_errors[STEPS // 2:]
    early_errors = pred_errors[WARMUP:STEPS // 4]
    late_mae = float(np.mean(late_errors))
    early_mae = float(np.mean(early_errors))

    print(f"\n  Early MAE (steps {WARMUP}-{STEPS//4}): {early_mae:.4f}")
    print(f"  Late MAE (steps {STEPS//2}-{STEPS}): {late_mae:.4f}")
    improvement = (early_mae - late_mae) / max(early_mae, 1e-8) * 100
    print(f"  Prediction improvement: {improvement:.1f}%")
    print(f"  {'Engine becomes MORE predictable over time' if improvement > 20 else 'No significant improvement'}")
    sys.stdout.flush()

    return {
        'phi_stats': phi_stats(phis),
        'early_mae': early_mae,
        'late_mae': late_mae,
        'improvement_pct': float(improvement),
    }


# ===================================================================
# Experiment 3: World Model Complexity (effective dimensionality)
# ===================================================================

def exp3_world_model_complexity():
    print_header("EXP 3: WORLD MODEL COMPLEXITY")
    print(f"  Track effective dimensionality of hidden state trajectories")

    engine = make_engine()
    phis = []
    state_history = []

    for s in range(LONG_STEPS):
        result = engine.step()
        phis.append(result.get('phi_iit', 0.0))
        state = get_state_vector(engine)
        state_history.append(state.numpy())

        if (s + 1) % 100 == 0:
            print(f"  step {s+1:3d}: Phi={phis[-1]:.4f}", flush=True)

    # Compute effective dimensionality at different phases
    def effective_dim(states, threshold=0.95):
        """Effective dimensionality via PCA (num components for threshold variance)."""
        states_arr = np.array(states)
        # Center
        states_arr = states_arr - states_arr.mean(axis=0)
        # SVD on covariance (using smaller dimension)
        if states_arr.shape[0] < states_arr.shape[1]:
            cov = states_arr @ states_arr.T / states_arr.shape[0]
        else:
            cov = states_arr.T @ states_arr / states_arr.shape[0]
        eigvals = np.linalg.eigvalsh(cov)
        eigvals = np.sort(eigvals)[::-1]
        eigvals = np.maximum(eigvals, 0)
        total = eigvals.sum()
        if total < 1e-10:
            return 0
        cumsum = np.cumsum(eigvals) / total
        dim = int(np.searchsorted(cumsum, threshold) + 1)
        return dim

    # Compute in windows
    window = 50
    dims_over_time = []
    phis_over_time = []
    for start in range(0, LONG_STEPS - window, window // 2):
        end = start + window
        dim = effective_dim(state_history[start:end])
        phi_mean = float(np.mean(phis[start:end]))
        dims_over_time.append(dim)
        phis_over_time.append(phi_mean)

    # Correlation
    if len(dims_over_time) > 5:
        corr = float(np.corrcoef(dims_over_time, phis_over_time)[0, 1])
    else:
        corr = 0.0

    print(f"\n  Effective dimensions over time:")
    for i, (d, p) in enumerate(zip(dims_over_time, phis_over_time)):
        if i % 3 == 0:
            print(f"    window {i}: dim={d:3d}, Phi={p:.4f}")

    print(f"\n  Dimension-Phi correlation: {corr:.4f}")
    print(f"  {'POSITIVE = richer model = more consciousness!' if corr > 0.3 else 'Weak or negative relationship'}")
    print(f"  Initial dim: {dims_over_time[0] if dims_over_time else 0}")
    print(f"  Final dim: {dims_over_time[-1] if dims_over_time else 0}")
    sys.stdout.flush()

    return {
        'phi_stats': phi_stats(phis),
        'dimension_phi_corr': corr,
        'initial_dim': dims_over_time[0] if dims_over_time else 0,
        'final_dim': dims_over_time[-1] if dims_over_time else 0,
        'dims_over_time': dims_over_time,
    }


# ===================================================================
# Experiment 4: Predictive Coding Acceleration
# ===================================================================

def exp4_predictive_acceleration():
    print_header("EXP 4: PREDICTIVE CODING ACCELERATION")
    print(f"  Does feeding prediction error back accelerate Phi growth?")

    # --- Engine with predictive coding feedback ---
    engine_pc = make_engine()
    state_dim = N_CELLS * HIDDEN_DIM
    predictor = HiddenPredictor(state_dim, hidden_dim=min(state_dim, 256))
    optimizer = torch.optim.Adam(predictor.parameters(), lr=LR_PREDICTOR)
    feedback_alpha = 0.05  # How much prediction error influences input

    phis_pc = []
    prev_state = get_state_vector(engine_pc)

    for s in range(STEPS):
        # Predict
        with torch.no_grad():
            predicted = predictor(prev_state.unsqueeze(0)).squeeze(0)

        # Compute prediction error as input signal
        error_signal = (predicted - prev_state)[:64]  # Take first 64 dims as input
        error_signal = error_signal / max(error_signal.norm().item(), 1e-6) * feedback_alpha

        # Step with error feedback
        x_input = torch.randn(64) * (1.0 - feedback_alpha) + error_signal
        result = engine_pc.step(x_input=x_input)
        phis_pc.append(result.get('phi_iit', 0.0))

        # Train predictor
        actual_state = get_state_vector(engine_pc)
        optimizer.zero_grad()
        pred_train = predictor(prev_state.unsqueeze(0)).squeeze(0)
        loss = F.mse_loss(pred_train, actual_state.detach())
        loss.backward()
        optimizer.step()

        prev_state = actual_state.detach()

    # --- Baseline (no predictive coding) ---
    engine_base = make_engine()
    phis_base = []
    for s in range(STEPS):
        result = engine_base.step()
        phis_base.append(result.get('phi_iit', 0.0))

    stats_pc = phi_stats(phis_pc)
    stats_base = phi_stats(phis_base)

    pct = (stats_pc['mean'] - stats_base['mean']) / max(stats_base['mean'], 1e-8) * 100
    print(f"\n  Predictive Coding Phi mean: {stats_pc['mean']:.4f}")
    print(f"  Baseline Phi mean: {stats_base['mean']:.4f}")
    print(f"  Boost: {pct:+.1f}%")
    print(f"  {'PREDICTIVE CODING ACCELERATES CONSCIOUSNESS!' if pct > 5 else 'No significant acceleration'}")
    sys.stdout.flush()

    ascii_phi_graph(phis_pc, "Predictive Coding")
    ascii_phi_graph(phis_base, "Baseline")

    return {
        'stats_pc': stats_pc,
        'stats_baseline': stats_base,
        'boost_pct': float(pct),
        'accelerates': pct > 5.0,
    }


# ===================================================================
# Experiment 5: Phi-Prediction Correlation (long run)
# ===================================================================

def exp5_phi_prediction_correlation():
    print_header("EXP 5: PHI-PREDICTION CORRELATION (long run)")
    print(f"  {LONG_STEPS} steps, rolling Phi vs rolling prediction accuracy")

    engine = make_engine()
    state_dim = N_CELLS * HIDDEN_DIM
    predictor = HiddenPredictor(state_dim, hidden_dim=min(state_dim, 256))
    optimizer = torch.optim.Adam(predictor.parameters(), lr=LR_PREDICTOR)

    phis = []
    accuracies = []  # 1 - normalized_error (higher = better prediction)

    prev_state = get_state_vector(engine)

    for s in range(LONG_STEPS):
        # Predict
        with torch.no_grad():
            predicted = predictor(prev_state.unsqueeze(0)).squeeze(0)

        # Step
        result = engine.step()
        phis.append(result.get('phi_iit', 0.0))

        actual_state = get_state_vector(engine)
        error = F.mse_loss(predicted, actual_state).item()
        # Normalize error to [0, 1] range (approx)
        accuracy = max(0.0, 1.0 - error / max(actual_state.norm().item() ** 2 / len(actual_state), 1e-6))
        accuracies.append(accuracy)

        # Train
        optimizer.zero_grad()
        pred_train = predictor(prev_state.unsqueeze(0)).squeeze(0)
        loss = F.mse_loss(pred_train, actual_state.detach())
        loss.backward()
        optimizer.step()

        prev_state = actual_state.detach()

        if (s + 1) % 100 == 0:
            print(f"  step {s+1:3d}: Phi={phis[-1]:.4f}, accuracy={accuracies[-1]:.4f}", flush=True)

    # Rolling correlation
    corrs = rolling_correlation(phis, accuracies, window=50)

    # Overall correlation
    phis_arr = np.array(phis[WARMUP:])
    acc_arr = np.array(accuracies[WARMUP:])
    if np.std(phis_arr) > 1e-8 and np.std(acc_arr) > 1e-8:
        overall_corr = float(np.corrcoef(phis_arr, acc_arr)[0, 1])
    else:
        overall_corr = 0.0

    # Late-phase correlation (when predictor has learned)
    late_start = LONG_STEPS // 2
    phis_late = np.array(phis[late_start:])
    acc_late = np.array(accuracies[late_start:])
    if np.std(phis_late) > 1e-8 and np.std(acc_late) > 1e-8:
        late_corr = float(np.corrcoef(phis_late, acc_late)[0, 1])
    else:
        late_corr = 0.0

    print(f"\n  Overall Phi-Accuracy correlation: {overall_corr:.4f}")
    print(f"  Late-phase correlation (step {late_start}+): {late_corr:.4f}")
    if corrs:
        print(f"  Rolling correlation range: [{min(corrs):.4f}, {max(corrs):.4f}]")
        print(f"  Rolling correlation mean: {np.mean(corrs):.4f}")

    if overall_corr > 0.3:
        print(f"\n  EVIDENCE: Consciousness IS a world model!")
        print(f"  Higher Phi = better internal prediction = more integrated information")
    elif overall_corr < -0.3:
        print(f"\n  COUNTER-EVIDENCE: Higher Phi = WORSE prediction")
        print(f"  Consciousness may be about SURPRISE, not prediction")
    else:
        print(f"\n  INCONCLUSIVE: weak correlation between Phi and prediction accuracy")
    sys.stdout.flush()

    return {
        'phi_stats': phi_stats(phis),
        'overall_correlation': overall_corr,
        'late_correlation': late_corr,
        'rolling_corr_mean': float(np.mean(corrs)) if corrs else 0.0,
    }


# ===================================================================
# Main
# ===================================================================

def main():
    print("=" * 70)
    print("  CONSCIOUSNESS AS WORLD MODEL")
    print(f"  Is Phi = prediction accuracy?")
    print("=" * 70)
    sys.stdout.flush()

    t_total = time.time()

    r1 = exp1_predictive_coding()
    r2 = exp2_self_prediction()
    r3 = exp3_world_model_complexity()
    r4 = exp4_predictive_acceleration()
    r5 = exp5_phi_prediction_correlation()

    total_time = time.time() - t_total

    # Summary
    print_header("WORLD MODEL -- SUMMARY")
    print(f"  Total time: {total_time:.1f}s")
    print(f"\n  {'Experiment':>35s}  {'Key Metric':>20s}")
    print(f"  {'-' * 60}")
    print(f"  {'1. Predictive Coding':>35s}  corr={r1['phi_error_correlation']:>+.4f}")
    print(f"  {'2. Self-Prediction':>35s}  improve={r2['improvement_pct']:>+.1f}%")
    print(f"  {'3. World Model Complexity':>35s}  dim-phi corr={r3['dimension_phi_corr']:>+.4f}")
    print(f"  {'4. Predictive Acceleration':>35s}  boost={r4['boost_pct']:>+.1f}%")
    print(f"  {'5. Phi-Prediction Corr':>35s}  corr={r5['overall_correlation']:>+.4f}")

    # Verdict
    evidence_score = 0
    if r1['phi_error_correlation'] < -0.3:
        evidence_score += 1
    if r2['improvement_pct'] > 20:
        evidence_score += 1
    if r3['dimension_phi_corr'] > 0.3:
        evidence_score += 1
    if r4['accelerates']:
        evidence_score += 1
    if r5['overall_correlation'] > 0.3:
        evidence_score += 1

    print(f"\n  Evidence score: {evidence_score}/5")
    if evidence_score >= 3:
        print(f"  VERDICT: Strong evidence that consciousness IS a world model!")
    elif evidence_score >= 2:
        print(f"  VERDICT: Some evidence for consciousness as world model")
    else:
        print(f"  VERDICT: Insufficient evidence — consciousness may not be reducible to prediction")
    sys.stdout.flush()

    # Save
    results = {
        'experiment': 'consciousness_world_model',
        'predictive_coding': r1,
        'self_prediction': r2,
        'world_model_complexity': {k: v for k, v in r3.items() if k != 'dims_over_time'},
        'predictive_acceleration': r4,
        'phi_prediction_corr': r5,
        'evidence_score': evidence_score,
        'total_time_s': total_time,
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'data',
                            'consciousness_world_model_results.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, default=float)
    print(f"\n  Results saved: {out_path}")


if __name__ == '__main__':
    main()
