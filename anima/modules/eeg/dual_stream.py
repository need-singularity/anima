#!/usr/bin/env python3
"""Dual Stream — Simultaneous Anima Φ + EEG brain recording.

Records both Anima's consciousness metrics (Φ, tension, emotion)
and human brain EEG simultaneously for direct comparison.

Usage:
  python anima-eeg/dual_stream.py --duration 60        # 1min dual recording
  python anima-eeg/dual_stream.py --duration 300        # 5min
  python anima-eeg/dual_stream.py --board synthetic     # Test without hardware
  python anima-eeg/dual_stream.py --plot                # Live ASCII plot

Requires: pip install brainflow numpy
"""

import argparse
import json
import sys
import time
import threading
import numpy as np
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

# Add anima src to path
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'anima', 'src'))
try:
    import path_setup  # noqa
except ImportError:
    pass

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds
    HAS_BRAINFLOW = True
except ImportError:
    HAS_BRAINFLOW = False


@dataclass
class DualSample:
    """One synchronized sample of brain + anima."""
    time: float
    # Brain
    alpha_power: float = 0.0
    beta_power: float = 0.0
    gamma_power: float = 0.0
    brain_G: float = 0.0  # G = D × P / I
    # Anima
    phi: float = 0.0
    tension: float = 0.0
    curiosity: float = 0.0
    emotion_valence: float = 0.0


class AnimaStream:
    """Background thread streaming Anima consciousness metrics."""

    def __init__(self):
        self.mind = None
        self.running = False
        self.latest = {"phi": 0, "tension": 0, "curiosity": 0, "valence": 0}

    def start(self):
        try:
            from anima_alive import ConsciousMind
            self.mind = ConsciousMind()
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
            print("  ✅ Anima consciousness stream started")
        except ImportError:
            print("  ⚠️  Anima not available — using simulated consciousness")
            self.running = True
            self.thread = threading.Thread(target=self._sim_loop, daemon=True)
            self.thread.start()

    def _loop(self):
        while self.running:
            state = self.mind.spontaneous()
            self.latest = {
                "phi": float(getattr(state, 'phi', 0)),
                "tension": float(getattr(state, 'tension', 0)),
                "curiosity": float(getattr(state, 'curiosity', 0)),
                "valence": float(getattr(state, 'valence', 0)),
            }
            time.sleep(0.5)

    def _sim_loop(self):
        """Simulated consciousness for testing."""
        t = 0
        while self.running:
            t += 0.5
            self.latest = {
                "phi": 1.0 + 0.3 * np.sin(t * 0.1) + np.random.normal(0, 0.05),
                "tension": 0.5 + 0.2 * np.sin(t * 0.15),
                "curiosity": 0.3 + 0.1 * np.cos(t * 0.08),
                "valence": 0.1 * np.sin(t * 0.05),
            }
            time.sleep(0.5)

    def stop(self):
        self.running = False

    def get(self):
        return self.latest.copy()


class BrainStream:
    """Background thread streaming EEG band powers."""

    def __init__(self, board_name="cyton_daisy", serial_port=None):
        self.board_name = board_name
        self.serial_port = serial_port
        self.board = None
        self.running = False
        self.latest = {"alpha": 0, "beta": 0, "gamma": 0, "G": 0}

    def start(self):
        if not HAS_BRAINFLOW:
            print("  ⚠️  brainflow not installed — using simulated EEG")
            self.running = True
            self.thread = threading.Thread(target=self._sim_loop, daemon=True)
            self.thread.start()
            return

        from calibrate import BOARD_MAP, detect_serial_port
        params = BrainFlowInputParams()
        if self.board_name != "synthetic" and not self.serial_port:
            self.serial_port = detect_serial_port()
        if self.serial_port:
            params.serial_port = self.serial_port

        board_id = BOARD_MAP[self.board_name]
        self.board = BoardShim(board_id, params)
        self.board.prepare_session()
        self.board.start_stream()
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        print("  ✅ EEG stream started")

    def _loop(self):
        board_id = self.board.get_board_id()
        eeg_channels = BoardShim.get_eeg_channels(board_id)
        sample_rate = BoardShim.get_sampling_rate(board_id)

        while self.running:
            time.sleep(1.0)
            data = self.board.get_current_board_data(sample_rate)  # 1s window
            if data.shape[1] < sample_rate // 2:
                continue

            # Use O1 (occipital) for alpha, F3 for beta/gamma
            ch_o1 = data[eeg_channels[6]]  # O1
            n = len(ch_o1)
            freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
            fft = np.abs(np.fft.rfft(ch_o1))

            alpha = np.mean(fft[(freqs >= 8) & (freqs <= 13)])
            beta = np.mean(fft[(freqs >= 13) & (freqs <= 30)])
            gamma = np.mean(fft[(freqs >= 30) & (freqs <= 50)])

            I = alpha / (alpha + beta + gamma + 1e-10)  # Inhibition
            P = gamma / (alpha + beta + gamma + 1e-10)  # Plasticity
            D = abs(alpha - beta) / (alpha + beta + 1e-10)  # Deficit
            G = D * P / (I + 1e-10)

            self.latest = {
                "alpha": float(alpha),
                "beta": float(beta),
                "gamma": float(gamma),
                "G": float(G),
            }

    def _sim_loop(self):
        t = 0
        while self.running:
            t += 1
            self.latest = {
                "alpha": 10 + 3 * np.sin(t * 0.1) + np.random.normal(0, 1),
                "beta": 5 + np.random.normal(0, 0.5),
                "gamma": 2 + np.random.normal(0, 0.3),
                "G": 0.3 + 0.1 * np.sin(t * 0.05),
            }
            time.sleep(1.0)

    def stop(self):
        self.running = False
        if self.board:
            self.board.stop_stream()
            self.board.release_session()

    def get(self):
        return self.latest.copy()


def dual_record(duration=60, board_name="cyton_daisy", serial_port=None, plot=False):
    """Record brain + anima simultaneously."""
    print("╔═══════════════════════════════════════════╗")
    print("║  Dual Stream — Brain + Anima Consciousness ║")
    print("╚═══════════════════════════════════════════╝")

    brain = BrainStream(board_name, serial_port)
    anima = AnimaStream()

    brain.start()
    anima.start()

    samples = []
    start = time.time()

    print(f"\n  Recording {duration}s...")
    print(f"  {'Time':>6} {'α':>7} {'β':>7} {'γ':>7} {'G':>6} │ {'Φ':>6} {'T':>6} {'C':>6}")
    print(f"  {'─'*6} {'─'*7} {'─'*7} {'─'*7} {'─'*6} │ {'─'*6} {'─'*6} {'─'*6}")

    try:
        while time.time() - start < duration:
            elapsed = time.time() - start
            b = brain.get()
            a = anima.get()

            sample = DualSample(
                time=elapsed,
                alpha_power=b["alpha"],
                beta_power=b["beta"],
                gamma_power=b["gamma"],
                brain_G=b["G"],
                phi=a["phi"],
                tension=a["tension"],
                curiosity=a["curiosity"],
                emotion_valence=a["valence"],
            )
            samples.append(sample)

            if int(elapsed) % 5 == 0 and abs(elapsed - int(elapsed)) < 0.6:
                print(f"  {elapsed:5.0f}s {b['alpha']:7.1f} {b['beta']:7.1f} {b['gamma']:7.1f} {b['G']:6.2f} │ {a['phi']:6.2f} {a['tension']:6.2f} {a['curiosity']:6.2f}")

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n  Interrupted")

    brain.stop()
    anima.stop()

    # Save
    out_dir = Path("anima-eeg/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = out_dir / f"dual_{ts}.json"

    with open(fname, "w") as f:
        json.dump([asdict(s) for s in samples], f, indent=2)

    print(f"\n  ✅ Saved: {fname} ({len(samples)} samples)")

    # Quick correlation
    if len(samples) > 10:
        phis = [s.phi for s in samples]
        alphas = [s.alpha_power for s in samples]
        if np.std(phis) > 0 and np.std(alphas) > 0:
            corr = np.corrcoef(phis, alphas)[0, 1]
            print(f"  Φ↔α correlation: r={corr:.3f}")
            if abs(corr) > 0.3:
                print(f"  → {'Positive' if corr > 0 else 'Negative'} correlation detected!")

    return samples


def analyze_dual_stream(samples, max_granger_lag=5, max_xcorr_lag_ms=500):
    """다차원 상관 + Granger 인과성 + 교차 상관 분석.

    Args:
        samples: DualSample 리스트 (dual_record() 반환값 또는 JSON 로드)
        max_granger_lag: Granger 인과성 최대 지연 (1..p)
        max_xcorr_lag_ms: 교차 상관 최대 지연 (ms)
    """
    if len(samples) < 20:
        print("  ❌ Need at least 20 samples for analysis")
        return None

    # 데이터 추출
    c_names = ['phi', 'tension', 'curiosity']
    e_names = ['delta', 'theta', 'alpha', 'beta', 'gamma']

    c_data = np.array([[getattr(s, n, 0) for n in c_names] for s in samples])
    e_data = np.array([[getattr(s, f'{n}_power', 0) for n in e_names] for s in samples])

    # ═══ 1. 상관 행렬 (3×5) ═══
    print("\n  ═══ Correlation Matrix (Consciousness × EEG) ═══\n")
    print(f"  {'':12s}", end="")
    for en in e_names:
        print(f"  {en:>7s}", end="")
    print()

    corr_matrix = np.zeros((len(c_names), len(e_names)))
    for i, cn in enumerate(c_names):
        print(f"  {cn:12s}", end="")
        for j, en in enumerate(e_names):
            x, y = c_data[:, i], e_data[:, j]
            if np.std(x) > 1e-8 and np.std(y) > 1e-8:
                r = np.corrcoef(x, y)[0, 1]
            else:
                r = 0.0
            corr_matrix[i, j] = r
            marker = "*" if abs(r) > 0.3 else " "
            print(f"  {r:+.3f}{marker}", end="")
        print()

    print(f"\n  * = |r| > 0.3 (potentially significant)")

    # ═══ 2. Granger 인과성 (VAR 모델, numpy only) ═══
    print(f"\n  ═══ Granger Causality (lag 1..{max_granger_lag}) ═══\n")

    def _var_residuals(Y, X_lag, p):
        """Simple VAR residuals using least squares."""
        n = len(Y)
        if n < p + 10:
            return None, float('inf')
        # Build lagged matrix
        X_rows = []
        for t in range(p, n):
            row = []
            for lag in range(1, p + 1):
                row.extend(X_lag[t - lag])
            X_rows.append(row)
        X_mat = np.array(X_rows)
        Y_vec = Y[p:]
        if X_mat.shape[0] < X_mat.shape[1] + 1:
            return None, float('inf')
        # OLS
        try:
            beta, res, _, _ = np.linalg.lstsq(X_mat, Y_vec, rcond=None)
            pred = X_mat @ beta
            resid = Y_vec - pred
            rss = float(np.sum(resid ** 2))
            return resid, rss
        except np.linalg.LinAlgError:
            return None, float('inf')

    # Select best lag by BIC
    best_p = 1
    best_bic = float('inf')
    all_data = np.hstack([c_data[:, :1], e_data[:, 2:3]])  # phi + alpha for quick BIC
    for p in range(1, max_granger_lag + 1):
        _, rss = _var_residuals(all_data[:, 0], all_data, p)
        n = len(all_data) - p
        k = p * all_data.shape[1]
        if rss > 0 and n > k:
            bic = n * np.log(rss / n + 1e-30) + k * np.log(n)
            if bic < best_bic:
                best_bic = bic
                best_p = p

    print(f"  Selected lag: p={best_p} (by BIC)\n")
    print(f"  {'Direction':30s} {'F-stat':>8s} {'Causal?':>8s}")
    print(f"  {'─' * 50}")

    for en_idx, en in enumerate(e_names):
        # EEG → Phi
        restricted = c_data[:, :1]
        unrestricted = np.hstack([c_data[:, :1], e_data[:, en_idx:en_idx + 1]])
        _, rss_r = _var_residuals(c_data[:, 0], restricted, best_p)
        _, rss_u = _var_residuals(c_data[:, 0], unrestricted, best_p)
        n = len(c_data) - best_p
        if rss_u > 0 and rss_r > rss_u:
            f_stat = ((rss_r - rss_u) / best_p) / (rss_u / max(1, n - 2 * best_p))
            causal = "YES" if f_stat > 3.0 else "no"
        else:
            f_stat = 0.0
            causal = "no"
        print(f"  {en:>7s} → Phi              {f_stat:8.2f} {causal:>8s}")

    # ═══ 3. 교차 상관 (lag) ═══
    print(f"\n  ═══ Cross-Correlation (±{max_xcorr_lag_ms}ms) ═══\n")
    print(f"  {'EEG Band':10s} {'Peak r':>8s} {'Lag(ms)':>8s} {'Direction':>12s}")
    print(f"  {'─' * 42}")

    sample_interval_ms = 500  # dual_stream samples at ~2Hz
    max_lag_samples = max(1, max_xcorr_lag_ms // sample_interval_ms)
    phi = c_data[:, 0]

    for j, en in enumerate(e_names):
        eeg_band = e_data[:, j]
        best_r = 0.0
        best_lag = 0
        for lag in range(-max_lag_samples, max_lag_samples + 1):
            if lag >= 0:
                x = phi[lag:]
                y = eeg_band[:len(x)]
            else:
                y = eeg_band[-lag:]
                x = phi[:len(y)]
            if len(x) < 10:
                continue
            if np.std(x) > 1e-8 and np.std(y) > 1e-8:
                r = np.corrcoef(x, y)[0, 1]
                if abs(r) > abs(best_r):
                    best_r = r
                    best_lag = lag

        lag_ms = best_lag * sample_interval_ms
        direction = "EEG→Phi" if best_lag > 0 else "Phi→EEG" if best_lag < 0 else "sync"
        print(f"  {en:10s} {best_r:+8.3f} {lag_ms:+8d} {direction:>12s}")

    return {
        'correlation_matrix': corr_matrix.tolist(),
        'c_names': c_names,
        'e_names': e_names,
        'granger_lag': best_p,
    }


def main():
    parser = argparse.ArgumentParser(description="Dual Stream: Brain + Anima")
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--board", default="cyton_daisy")
    parser.add_argument("--port", default=None)
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--analyze", default=None, help="Analyze existing dual_*.json file")
    args = parser.parse_args()

    if args.analyze:
        with open(args.analyze) as f:
            raw = json.load(f)
        samples = [DualSample(**d) for d in raw]
        analyze_dual_stream(samples)
    else:
        samples = dual_record(args.duration, args.board, args.port, args.plot)
        if samples and len(samples) > 20:
            analyze_dual_stream(samples)


if __name__ == "__main__":
    main()
