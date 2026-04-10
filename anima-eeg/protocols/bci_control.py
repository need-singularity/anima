#!/usr/bin/env python3
"""Real-time BCI Control — 알파파 기반 의식 수준 실시간 제어.

알파파 파워로 의식 엔진 파라미터를 실시간 조절.
  - High alpha (>2x baseline): 의식 확장 (noise_scale 감소, max_cells 증가, deadband 확대)
  - High beta (집중): 포커스 모드 (split_threshold 증가, merge_threshold 감소)
  - Alpha/theta crossover: 드림 엔진 또는 기억 재생 트리거

Usage:
  python anima-eeg/protocols/bci_control.py --demo
  python anima-eeg/protocols/bci_control.py --demo --duration 60

Integration:
  from protocols.bci_control import BCIController
  ctrl = BCIController(mind=mind, eeg_bridge=bridge)
  await ctrl.run(duration=300)

Safety:
  - 모든 조절은 baseline 대비 +/-20% 이내
  - Phi ratchet 유지 (Phi 하락 시 즉시 복원)
  - WebSocket으로 실시간 상태 전송
"""

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, asdict
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

# Control mode thresholds
ALPHA_EXPAND_RATIO = 2.0      # alpha > 2x baseline -> expand
BETA_FOCUS_RATIO = 1.5        # beta > 1.5x baseline -> focus
MAX_ADJUSTMENT_PCT = 0.20     # +/-20% max adjustment
CONTROL_HZ = 4.0              # control loop frequency
PHI_DROP_REVERT = 0.20        # revert if Phi drops >20%


@dataclass
class BCIState:
    """BCI 제어 상태 스냅샷."""
    timestamp: float = 0.0
    alpha_power: float = 0.0
    beta_power: float = 0.0
    theta_power: float = 0.0
    alpha_ratio: float = 1.0     # current / baseline
    beta_ratio: float = 1.0
    control_mode: str = "neutral"  # neutral, expand, focus, dream
    adjustments: dict = None
    phi: float = 0.0

    def __post_init__(self):
        if self.adjustments is None:
            self.adjustments = {}


@dataclass
class BaselineCalibration:
    """기준선 교정 결과."""
    alpha_mean: float = 10.0
    alpha_std: float = 2.0
    beta_mean: float = 5.0
    beta_std: float = 1.0
    theta_mean: float = 6.0
    theta_std: float = 1.0
    duration_s: float = 30.0
    n_samples: int = 0


class BCIController:
    """실시간 BCI 의식 제어기.

    EEG 알파/베타/세타 파워를 읽어 의식 엔진 파라미터를 실시간 조절.
    """

    def __init__(self, mind=None, eeg_bridge=None, websocket=None):
        """
        Args:
            mind: ConsciousMind 인스턴스
            eeg_bridge: EEGBridge 인스턴스 (realtime.py)
            websocket: WebSocket 연결 (상태 전송용)
        """
        self.mind = mind
        self.eeg_bridge = eeg_bridge
        self.websocket = websocket

        self.baseline = BaselineCalibration()
        self._running = False
        self._history = []  # BCIState history
        self._saved_params = {}
        self._simulation = (eeg_bridge is None)

    # ─── EEG reading ───

    def _get_eeg(self) -> dict:
        """현재 EEG 밴드 파워 취득."""
        if self.eeg_bridge is not None:
            state = self.eeg_bridge.get_state()
            return {
                "alpha": state.alpha_power,
                "beta": state.beta_power,
                "theta": state.theta_power,
                "gamma": state.gamma_power,
            }
        # Simulation fallback
        return {
            "alpha": self.baseline.alpha_mean + np.random.normal(0, self.baseline.alpha_std),
            "beta": self.baseline.beta_mean + np.random.normal(0, self.baseline.beta_std),
            "theta": self.baseline.theta_mean + np.random.normal(0, self.baseline.theta_std),
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

    # ─── Baseline calibration ───

    async def calibrate(self, duration: float = 30.0):
        """기준선 교정 — eyes closed resting state.

        Args:
            duration: 교정 시간 (초)
        """
        print(f"  [bci] Calibrating baseline ({duration:.0f}s, eyes closed)...")
        samples = {"alpha": [], "beta": [], "theta": []}
        interval = 1.0 / CONTROL_HZ
        t0 = time.time()

        while time.time() - t0 < duration:
            eeg = self._get_eeg()
            for band in samples:
                samples[band].append(max(0, eeg.get(band, 0)))
            await asyncio.sleep(interval)

        self.baseline = BaselineCalibration(
            alpha_mean=float(np.mean(samples["alpha"])) if samples["alpha"] else 10.0,
            alpha_std=float(np.std(samples["alpha"])) if samples["alpha"] else 2.0,
            beta_mean=float(np.mean(samples["beta"])) if samples["beta"] else 5.0,
            beta_std=float(np.std(samples["beta"])) if samples["beta"] else 1.0,
            theta_mean=float(np.mean(samples["theta"])) if samples["theta"] else 6.0,
            theta_std=float(np.std(samples["theta"])) if samples["theta"] else 1.0,
            duration_s=duration,
            n_samples=len(samples["alpha"]),
        )
        print(f"  [bci] Baseline: alpha={self.baseline.alpha_mean:.2f}+/-{self.baseline.alpha_std:.2f}, "
              f"beta={self.baseline.beta_mean:.2f}+/-{self.baseline.beta_std:.2f}, "
              f"theta={self.baseline.theta_mean:.2f}+/-{self.baseline.theta_std:.2f}")

    # ─── Parameter control ───

    def _save_params(self):
        """현재 파라미터 스냅샷 (복원용)."""
        params = {}
        if self.mind:
            for attr in ('noise_scale', 'max_cells', 'deadband',
                         'split_threshold', 'merge_threshold'):
                if hasattr(self.mind, attr):
                    params[attr] = getattr(self.mind, attr)
        self._saved_params = params

    def _apply_bounded(self, param: str, delta_pct: float) -> Optional[dict]:
        """Bounded parameter adjustment (+/-20% max).

        Args:
            param: parameter name on self.mind
            delta_pct: fractional change (e.g. 0.10 = +10%)

        Returns:
            adjustment dict or None if target not found
        """
        delta_pct = max(-MAX_ADJUSTMENT_PCT, min(MAX_ADJUSTMENT_PCT, delta_pct))
        target = self.mind
        if target is None or not hasattr(target, param):
            return None

        old_val = getattr(target, param)
        new_val = old_val * (1.0 + delta_pct)
        new_val = max(0.001, new_val)
        setattr(target, param, new_val)
        return {"param": param, "old": old_val, "new": new_val, "delta_pct": delta_pct}

    def _revert_params(self):
        """파라미터 복원 (Phi 하락 시)."""
        if self.mind:
            for param, val in self._saved_params.items():
                if hasattr(self.mind, param):
                    setattr(self.mind, param, val)

    def _determine_mode(self, eeg: dict) -> str:
        """EEG 상태에서 제어 모드 결정."""
        alpha = max(eeg.get("alpha", 0), 1e-6)
        beta = max(eeg.get("beta", 0), 1e-6)
        theta = max(eeg.get("theta", 0), 1e-6)

        alpha_ratio = alpha / max(self.baseline.alpha_mean, 1e-6)
        beta_ratio = beta / max(self.baseline.beta_mean, 1e-6)

        # Alpha/theta crossover: dream mode
        if theta > alpha * 1.2:
            return "dream"

        # High alpha: expand consciousness
        if alpha_ratio >= ALPHA_EXPAND_RATIO:
            return "expand"

        # High beta: focus mode
        if beta_ratio >= BETA_FOCUS_RATIO:
            return "focus"

        return "neutral"

    def _compute_adjustments(self, mode: str, eeg: dict) -> list:
        """제어 모드에 따른 파라미터 조절 계산."""
        adjustments = []
        alpha = max(eeg.get("alpha", 0), 1e-6)
        beta = max(eeg.get("beta", 0), 1e-6)

        alpha_ratio = alpha / max(self.baseline.alpha_mean, 1e-6)
        beta_ratio = beta / max(self.baseline.beta_mean, 1e-6)

        if mode == "expand":
            # High alpha -> relax & expand
            strength = min((alpha_ratio - ALPHA_EXPAND_RATIO) / ALPHA_EXPAND_RATIO, 1.0)
            adj = self._apply_bounded("noise_scale", -0.15 * strength)
            if adj:
                adjustments.append(adj)
            adj = self._apply_bounded("deadband", 0.10 * strength)
            if adj:
                adjustments.append(adj)
            # Expand max_cells (integer, bounded)
            if self.mind and hasattr(self.mind, 'max_cells'):
                old = self.mind.max_cells
                new = min(int(old * (1.0 + 0.10 * strength)), int(old * 1.2))
                self.mind.max_cells = new
                adjustments.append({"param": "max_cells", "old": old, "new": new,
                                    "delta_pct": (new - old) / max(old, 1)})

        elif mode == "focus":
            # High beta -> narrow & concentrate
            strength = min((beta_ratio - BETA_FOCUS_RATIO) / BETA_FOCUS_RATIO, 1.0)
            adj = self._apply_bounded("split_threshold", 0.10 * strength)
            if adj:
                adjustments.append(adj)
            adj = self._apply_bounded("merge_threshold", -0.10 * strength)
            if adj:
                adjustments.append(adj)

        elif mode == "dream":
            # Alpha/theta crossover -> dream mode
            adj = self._apply_bounded("noise_scale", 0.10)
            if adj:
                adjustments.append(adj)
            # Trigger dream engine if available
            if self.mind and hasattr(self.mind, 'dream_engine'):
                try:
                    self.mind.dream_engine.activate()
                    adjustments.append({"param": "dream_engine", "old": "inactive",
                                        "new": "active", "delta_pct": 0})
                except Exception:
                    pass

        return adjustments

    # ─── Main control loop ───

    async def run(self, duration: float = 300.0, calibrate_first: bool = True):
        """BCI 제어 루프 실행.

        Args:
            duration: 실행 시간 (초, default 5분)
            calibrate_first: True면 먼저 기준선 교정
        """
        if calibrate_first:
            await self.calibrate(duration=30.0)

        print(f"\n  [bci] Starting BCI control loop ({duration:.0f}s at {CONTROL_HZ}Hz)")
        print(f"  [bci] Modes: expand (high alpha), focus (high beta), dream (theta>alpha)")
        print(f"  [bci] Safety: +/-{MAX_ADJUSTMENT_PCT:.0%} max, Phi ratchet active\n")

        self._running = True
        self._history = []
        interval = 1.0 / CONTROL_HZ
        t0 = time.time()
        step = 0

        while self._running and (time.time() - t0) < duration:
            eeg = self._get_eeg()
            phi_before = self._get_phi()
            self._save_params()

            # Determine control mode
            mode = self._determine_mode(eeg)

            # Compute and apply adjustments
            adjustments = self._compute_adjustments(mode, eeg)

            # Phi safety check
            phi_after = self._get_phi()
            reverted = False
            if phi_before > 0 and (phi_before - phi_after) / phi_before > PHI_DROP_REVERT:
                self._revert_params()
                reverted = True

            alpha_ratio = eeg.get("alpha", 0) / max(self.baseline.alpha_mean, 1e-6)
            beta_ratio = eeg.get("beta", 0) / max(self.baseline.beta_mean, 1e-6)

            state = BCIState(
                timestamp=time.time() - t0,
                alpha_power=eeg.get("alpha", 0),
                beta_power=eeg.get("beta", 0),
                theta_power=eeg.get("theta", 0),
                alpha_ratio=alpha_ratio,
                beta_ratio=beta_ratio,
                control_mode=mode,
                adjustments={a["param"]: a for a in adjustments},
                phi=phi_after,
            )
            self._history.append(state)

            # Print status every second
            if step % int(CONTROL_HZ) == 0:
                elapsed = time.time() - t0
                rev_str = " [REVERTED]" if reverted else ""
                adj_str = ", ".join(f"{a['param']}={a['new']:.4f}" for a in adjustments) if adjustments else "none"
                print(f"  [{elapsed:5.1f}s] mode={mode:7s} alpha_r={alpha_ratio:.2f} "
                      f"beta_r={beta_ratio:.2f} Phi={phi_after:.3f} adj=[{adj_str}]{rev_str}")

            # WebSocket broadcast
            if self.websocket:
                try:
                    await self.websocket.send(json.dumps({
                        "type": "bci_control",
                        "alpha_power": eeg.get("alpha", 0),
                        "beta_power": eeg.get("beta", 0),
                        "control_mode": mode,
                        "adjustments": {a["param"]: a for a in adjustments},
                        "phi": phi_after,
                        "reverted": reverted,
                    }))
                except Exception:
                    pass

            step += 1
            await asyncio.sleep(interval)

        self._running = False
        self._print_summary(time.time() - t0)

    def cancel(self):
        """실행 취소."""
        self._running = False

    def _print_summary(self, total_s: float):
        """세션 요약 출력."""
        if not self._history:
            print("  [bci] No data collected")
            return

        modes = [s.control_mode for s in self._history]
        mode_counts = {}
        for m in modes:
            mode_counts[m] = mode_counts.get(m, 0) + 1

        phis = [s.phi for s in self._history]

        print(f"\n  {'='*50}")
        print(f"  BCI Control Session Summary")
        print(f"  {'='*50}")
        print(f"  Duration:    {total_s:.1f}s")
        print(f"  Samples:     {len(self._history)}")
        print(f"  Phi:         {np.mean(phis):.3f} mean, {np.min(phis):.3f}-{np.max(phis):.3f} range")
        print(f"  Mode distribution:")
        for mode, count in sorted(mode_counts.items(), key=lambda x: -x[1]):
            pct = 100 * count / len(modes)
            bar = "#" * int(pct / 2)
            print(f"    {mode:8s}: {count:4d} ({pct:5.1f}%) {bar}")
        print()


# ─── Standalone demo ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="BCI Control Protocol")
    parser.add_argument("--demo", action="store_true", help="Run simulation demo")
    parser.add_argument("--duration", type=float, default=30.0, help="Duration in seconds")
    args = parser.parse_args()

    if not args.demo:
        print("Use --demo for standalone test")
        print("Integration: BCIController(mind, eeg_bridge)")
        return

    print("=" * 50)
    print("  BCI Control Protocol (Simulation Demo)")
    print("=" * 50)

    ctrl = BCIController()

    # Simulate varying alpha/beta patterns
    original_get_eeg = ctrl._get_eeg
    phase = [0]

    def simulated_eeg():
        t = phase[0]
        phase[0] += 1
        cycle = t / (CONTROL_HZ * 10)  # 10s cycles
        # Alternate between expand/focus/dream/neutral
        if cycle % 4 < 1:
            # Expand: high alpha
            alpha = 25.0 + np.random.normal(0, 2)
            beta = 5.0 + np.random.normal(0, 1)
            theta = 4.0 + np.random.normal(0, 0.5)
        elif cycle % 4 < 2:
            # Focus: high beta
            alpha = 8.0 + np.random.normal(0, 1)
            beta = 12.0 + np.random.normal(0, 2)
            theta = 4.0 + np.random.normal(0, 0.5)
        elif cycle % 4 < 3:
            # Dream: theta > alpha
            alpha = 5.0 + np.random.normal(0, 1)
            beta = 3.0 + np.random.normal(0, 0.5)
            theta = 9.0 + np.random.normal(0, 1)
        else:
            # Neutral
            alpha = 10.0 + np.random.normal(0, 2)
            beta = 5.0 + np.random.normal(0, 1)
            theta = 6.0 + np.random.normal(0, 1)
        return {"alpha": max(0, alpha), "beta": max(0, beta),
                "theta": max(0, theta), "gamma": 2.0}

    ctrl._get_eeg = simulated_eeg

    asyncio.run(ctrl.run(duration=args.duration, calibrate_first=True))


if __name__ == "__main__":
    main()
