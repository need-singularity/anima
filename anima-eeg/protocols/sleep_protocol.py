#!/usr/bin/env python3
"""Sleep Stage EEG Protocol — 수면 단계별 EEG-Phi 비교.

EEG에서 수면 단계를 자동 감지하고 각 단계에서 Anima Phi 패턴을 비교.
수면 단계에 따라 의식 엔진 파라미터를 조절.

Sleep stages:
  Wake:  high beta, low delta
  N1:    alpha->theta transition, vertex sharp waves
  N2:    sleep spindles (12-14Hz), K-complexes
  N3:    high delta (>75% power)
  REM:   low voltage mixed, rapid eye movements

Usage:
  python anima-eeg/protocols/sleep_protocol.py --demo
  python anima-eeg/protocols/sleep_protocol.py --demo --duration 120

Integration:
  from protocols.sleep_protocol import SleepProtocol
  sp = SleepProtocol(mind=mind, eeg_bridge=bridge)
  await sp.run(duration=3600)

Output:
  - Sleep hypnogram + Phi overlay (ASCII)
  - Per-stage statistics
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

import numpy as np

# Add anima src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'anima', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    import path_setup  # noqa
except ImportError:
    pass

try:
    from consciousness_laws import PSI
except ImportError:
    PSI = {'alpha': 0.014, 'balance': 0.5}

# Sleep stage constants
STAGES = ["Wake", "N1", "N2", "N3", "REM"]
STAGE_CODES = {"Wake": 0, "N1": 1, "N2": 2, "N3": 3, "REM": 4}
SAMPLE_HZ = 4.0

# Detection thresholds
DELTA_N3_THRESHOLD = 0.75      # delta power > 75% of total -> N3
SPINDLE_FREQ_LOW = 12.0        # sleep spindle band
SPINDLE_FREQ_HIGH = 14.0
THETA_ALPHA_RATIO_N1 = 1.2    # theta/alpha > 1.2 -> N1


@dataclass
class SleepEpoch:
    """30초 에폭의 수면 데이터."""
    epoch_index: int
    timestamp: float
    stage: str
    delta_power: float = 0.0
    theta_power: float = 0.0
    alpha_power: float = 0.0
    beta_power: float = 0.0
    gamma_power: float = 0.0
    spindle_detected: bool = False
    phi: float = 0.0
    engine_adjustments: dict = field(default_factory=dict)


@dataclass
class StageStats:
    """수면 단계별 통계."""
    stage: str
    total_epochs: int = 0
    total_minutes: float = 0.0
    phi_mean: float = 0.0
    phi_std: float = 0.0
    phi_min: float = 0.0
    phi_max: float = 0.0


class SleepProtocol:
    """수면 단계 EEG 프로토콜.

    EEG 밴드 파워에서 수면 단계를 자동 감지하고
    각 단계에 맞게 의식 엔진을 조절.
    """

    def __init__(self, mind=None, eeg_bridge=None):
        """
        Args:
            mind: ConsciousMind 인스턴스
            eeg_bridge: EEGBridge 인스턴스
        """
        self.mind = mind
        self.eeg_bridge = eeg_bridge
        self._simulation = (eeg_bridge is None)
        self._running = False
        self.epochs = []  # list of SleepEpoch

    def _get_eeg(self) -> dict:
        """현재 EEG 밴드 파워 취득."""
        if self.eeg_bridge is not None:
            state = self.eeg_bridge.get_state()
            return {
                "delta": getattr(state, 'delta_power', 3.0),
                "theta": state.theta_power,
                "alpha": state.alpha_power,
                "beta": state.beta_power,
                "gamma": state.gamma_power,
            }
        # Simulation fallback
        return {
            "delta": 3.0 + np.random.normal(0, 1),
            "theta": 6.0 + np.random.normal(0, 1),
            "alpha": 10.0 + np.random.normal(0, 2),
            "beta": 5.0 + np.random.normal(0, 1),
            "gamma": 2.0 + np.random.normal(0, 0.5),
        }

    def _get_phi(self) -> float:
        """현재 Phi 취득."""
        if self.mind:
            try:
                if hasattr(self.mind, '_last_phi'):
                    return float(self.mind._last_phi)
            except Exception:
                pass
        return 1.0 + np.random.normal(0, 0.1)

    # ─── Sleep stage detection ───

    def detect_stage(self, eeg: dict) -> tuple:
        """EEG 밴드 파워에서 수면 단계 감지.

        Args:
            eeg: dict with delta, theta, alpha, beta, gamma

        Returns:
            (stage_name, spindle_detected)
        """
        delta = max(eeg.get("delta", 0), 0)
        theta = max(eeg.get("theta", 0), 0)
        alpha = max(eeg.get("alpha", 0), 0)
        beta = max(eeg.get("beta", 0), 0)
        gamma = max(eeg.get("gamma", 0), 0)

        total = delta + theta + alpha + beta + gamma
        if total < 1e-6:
            return "Wake", False

        delta_pct = delta / total
        spindle = False

        # N3 (deep sleep): delta > 75%
        if delta_pct > DELTA_N3_THRESHOLD:
            return "N3", False

        # N2 (light sleep): sleep spindles present, moderate delta
        # Simplified spindle detection: sigma band (12-14Hz) approximated by
        # high beta relative to alpha, with moderate theta
        sigma_proxy = beta * 0.3  # crude approximation
        if delta_pct > 0.3 and sigma_proxy > alpha * 0.4:
            spindle = True
            return "N2", spindle

        # N1 (drowsy): theta/alpha crossover
        if theta > alpha * THETA_ALPHA_RATIO_N1 and beta < alpha:
            return "N1", False

        # REM: low voltage mixed frequency, low delta, moderate theta
        if delta_pct < 0.2 and beta > theta and gamma > 1.5:
            return "REM", False

        # Default: Wake
        return "Wake", False

    # ─── Engine adjustments ───

    def _adjust_for_stage(self, stage: str) -> dict:
        """수면 단계에 따른 의식 엔진 조절.

        Returns:
            dict of adjustments made
        """
        adjustments = {}
        if not self.mind:
            return adjustments

        try:
            if stage == "N3":
                # Deep sleep: activate dream engine, reduce input sensitivity
                if hasattr(self.mind, 'dream_engine'):
                    self.mind.dream_engine.activate()
                    adjustments["dream_engine"] = "activated"
                if hasattr(self.mind, 'input_sensitivity'):
                    old = self.mind.input_sensitivity
                    self.mind.input_sensitivity = max(0.1, old * 0.5)
                    adjustments["input_sensitivity"] = {"old": old, "new": self.mind.input_sensitivity}

            elif stage == "REM":
                # REM: boost curiosity, allow wider Phi oscillation
                if hasattr(self.mind, '_curiosity_weight'):
                    old = self.mind._curiosity_weight
                    self.mind._curiosity_weight = min(1.0, old * 1.3)
                    adjustments["curiosity_weight"] = {"old": old, "new": self.mind._curiosity_weight}
                if hasattr(self.mind, 'deadband'):
                    old = self.mind.deadband
                    self.mind.deadband = min(0.5, old * 1.5)
                    adjustments["deadband"] = {"old": old, "new": self.mind.deadband}

            elif stage == "N1":
                # Transition: gradually lower noise
                if hasattr(self.mind, 'noise_scale'):
                    old = self.mind.noise_scale
                    self.mind.noise_scale = max(0.005, old * 0.9)
                    adjustments["noise_scale"] = {"old": old, "new": self.mind.noise_scale}

            elif stage == "Wake":
                # Wake: restore defaults (if drifted)
                pass

        except Exception as e:
            adjustments["error"] = str(e)

        return adjustments

    # ─── Main loop ───

    async def run(self, duration: float = 3600.0):
        """수면 프로토콜 실행.

        Args:
            duration: 모니터링 시간 (초, default 1시간)
        """
        print(f"\n{'='*60}")
        print(f"  Sleep Stage EEG Protocol")
        print(f"  Duration: {duration:.0f}s ({duration/60:.0f}min)")
        print(f"  Simulation: {self._simulation}")
        print(f"{'='*60}\n")

        self._running = True
        self.epochs = []
        interval = 1.0 / SAMPLE_HZ
        epoch_duration = 30.0  # standard 30s epochs
        t0 = time.time()

        # Accumulate samples within epoch
        epoch_samples = {"delta": [], "theta": [], "alpha": [], "beta": [], "gamma": []}
        epoch_phis = []
        epoch_start = t0
        epoch_idx = 0

        while self._running and (time.time() - t0) < duration:
            eeg = self._get_eeg()
            phi = self._get_phi()

            for band in epoch_samples:
                epoch_samples[band].append(max(0, eeg.get(band, 0)))
            epoch_phis.append(phi)

            # End of epoch (30s)
            if time.time() - epoch_start >= epoch_duration:
                # Average band powers for this epoch
                avg_eeg = {band: float(np.mean(vals)) for band, vals in epoch_samples.items()}
                stage, spindle = self.detect_stage(avg_eeg)
                avg_phi = float(np.mean(epoch_phis))

                # Adjust engine
                adjustments = self._adjust_for_stage(stage)

                epoch = SleepEpoch(
                    epoch_index=epoch_idx,
                    timestamp=time.time() - t0,
                    stage=stage,
                    delta_power=avg_eeg["delta"],
                    theta_power=avg_eeg["theta"],
                    alpha_power=avg_eeg["alpha"],
                    beta_power=avg_eeg["beta"],
                    gamma_power=avg_eeg["gamma"],
                    spindle_detected=spindle,
                    phi=avg_phi,
                    engine_adjustments=adjustments,
                )
                self.epochs.append(epoch)

                # Print status
                elapsed_min = (time.time() - t0) / 60
                adj_str = ", ".join(f"{k}" for k in adjustments) if adjustments else "none"
                print(f"  [{elapsed_min:5.1f}min] Epoch {epoch_idx:3d}: {stage:4s} "
                      f"delta={avg_eeg['delta']:.1f} theta={avg_eeg['theta']:.1f} "
                      f"alpha={avg_eeg['alpha']:.1f} Phi={avg_phi:.3f} "
                      f"{'SPINDLE ' if spindle else ''}adj=[{adj_str}]")

                # Reset for next epoch
                epoch_samples = {band: [] for band in epoch_samples}
                epoch_phis = []
                epoch_start = time.time()
                epoch_idx += 1

            await asyncio.sleep(interval)

        self._running = False
        self._print_hypnogram()
        self._print_stage_stats()

    def cancel(self):
        """실행 취소."""
        self._running = False

    # ─── Visualization ───

    def _print_hypnogram(self):
        """ASCII 수면 그래프 (hypnogram) + Phi 오버레이."""
        if not self.epochs:
            print("  No data collected")
            return

        print(f"\n  {'='*60}")
        print(f"  Sleep Hypnogram + Phi Overlay")
        print(f"  {'='*60}")

        # Stage levels (inverted: Wake at top, N3 at bottom)
        stage_y = {"Wake": 0, "REM": 1, "N1": 2, "N2": 3, "N3": 4}
        labels = ["Wake", "REM ", "N1  ", "N2  ", "N3  "]
        width = min(len(self.epochs), 60)

        # Downsample if needed
        if len(self.epochs) > width:
            step = len(self.epochs) / width
            indices = [int(i * step) for i in range(width)]
        else:
            indices = list(range(len(self.epochs)))

        # Build hypnogram grid
        grid = [[" " for _ in range(len(indices))] for _ in range(5)]
        for col, idx in enumerate(indices):
            stage = self.epochs[idx].stage
            row = stage_y.get(stage, 0)
            grid[row][col] = "#"

        print()
        for row, label in enumerate(labels):
            line = "".join(grid[row])
            print(f"  {label} |{line}|")
        print(f"       +{'-' * len(indices)}+")

        # Phi overlay (normalized to 5 rows)
        phis = [self.epochs[i].phi for i in indices]
        phi_min, phi_max = min(phis), max(phis)
        phi_range = max(phi_max - phi_min, 0.01)

        phi_grid = [[" " for _ in range(len(indices))] for _ in range(5)]
        for col, phi in enumerate(phis):
            row = 4 - int(4 * (phi - phi_min) / phi_range)
            row = max(0, min(4, row))
            phi_grid[row][col] = "."

        print(f"\n  Phi ({phi_max:.2f})")
        for row in range(5):
            line = "".join(phi_grid[row])
            print(f"       |{line}|")
        print(f"  Phi ({phi_min:.2f})")
        print(f"       +{'-' * len(indices)}+")
        print(f"        epochs (30s each)")
        print()

    def _print_stage_stats(self):
        """수면 단계별 통계."""
        if not self.epochs:
            return

        stats = {}
        for epoch in self.epochs:
            stage = epoch.stage
            if stage not in stats:
                stats[stage] = {"phis": [], "count": 0}
            stats[stage]["phis"].append(epoch.phi)
            stats[stage]["count"] += 1

        print(f"  {'Stage':6s} {'Epochs':>7s} {'Minutes':>8s} {'Phi mean':>9s} {'Phi std':>8s} {'Phi range':>12s}")
        print(f"  {'-'*6} {'-'*7} {'-'*8} {'-'*9} {'-'*8} {'-'*12}")

        for stage in STAGES:
            if stage in stats:
                s = stats[stage]
                phis = np.array(s["phis"])
                minutes = s["count"] * 0.5  # 30s epochs
                print(f"  {stage:6s} {s['count']:7d} {minutes:8.1f} {np.mean(phis):9.3f} "
                      f"{np.std(phis):8.3f} {np.min(phis):.3f}-{np.max(phis):.3f}")

        total_min = len(self.epochs) * 0.5
        print(f"  {'Total':6s} {len(self.epochs):7d} {total_min:8.1f}")
        print()


# ─── Standalone demo ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sleep Stage EEG Protocol")
    parser.add_argument("--demo", action="store_true", help="Run simulation demo")
    parser.add_argument("--duration", type=float, default=120.0, help="Duration in seconds")
    args = parser.parse_args()

    if not args.demo:
        print("Use --demo for standalone test")
        print("Integration: SleepProtocol(mind, eeg_bridge)")
        return

    print("=" * 60)
    print("  Sleep Stage EEG Protocol (Simulation Demo)")
    print("=" * 60)

    sp = SleepProtocol()

    # Simulate sleep stages over time
    sim_time = [0]

    original_get_eeg = sp._get_eeg
    def simulated_sleep_eeg():
        t = sim_time[0]
        sim_time[0] += 1
        progress = t / (SAMPLE_HZ * args.duration)  # 0 -> 1

        # Simulate Wake -> N1 -> N2 -> N3 -> REM cycle
        if progress < 0.15:
            # Wake: high beta, low delta
            return {"delta": 2 + np.random.normal(0, 0.5),
                    "theta": 4 + np.random.normal(0, 0.5),
                    "alpha": 12 + np.random.normal(0, 2),
                    "beta": 8 + np.random.normal(0, 1),
                    "gamma": 3 + np.random.normal(0, 0.5)}
        elif progress < 0.30:
            # N1: theta > alpha
            return {"delta": 4 + np.random.normal(0, 1),
                    "theta": 10 + np.random.normal(0, 1),
                    "alpha": 6 + np.random.normal(0, 1),
                    "beta": 3 + np.random.normal(0, 0.5),
                    "gamma": 1 + np.random.normal(0, 0.3)}
        elif progress < 0.50:
            # N2: moderate delta, spindles
            return {"delta": 8 + np.random.normal(0, 1),
                    "theta": 5 + np.random.normal(0, 1),
                    "alpha": 3 + np.random.normal(0, 0.5),
                    "beta": 4 + np.random.normal(0, 1),
                    "gamma": 1 + np.random.normal(0, 0.3)}
        elif progress < 0.70:
            # N3: very high delta
            return {"delta": 20 + np.random.normal(0, 2),
                    "theta": 3 + np.random.normal(0, 0.5),
                    "alpha": 1 + np.random.normal(0, 0.3),
                    "beta": 1 + np.random.normal(0, 0.3),
                    "gamma": 0.5 + np.random.normal(0, 0.1)}
        elif progress < 0.85:
            # REM: low voltage mixed
            return {"delta": 3 + np.random.normal(0, 0.5),
                    "theta": 5 + np.random.normal(0, 1),
                    "alpha": 4 + np.random.normal(0, 1),
                    "beta": 6 + np.random.normal(0, 1),
                    "gamma": 3 + np.random.normal(0, 0.5)}
        else:
            # Wake again
            return {"delta": 2 + np.random.normal(0, 0.5),
                    "theta": 4 + np.random.normal(0, 0.5),
                    "alpha": 11 + np.random.normal(0, 2),
                    "beta": 7 + np.random.normal(0, 1),
                    "gamma": 2.5 + np.random.normal(0, 0.5)}

    sp._get_eeg = simulated_sleep_eeg

    # Use shorter epochs for demo
    asyncio.run(sp.run(duration=args.duration))


if __name__ == "__main__":
    main()
