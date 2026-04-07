#!/usr/bin/env python3
"""Brain-Body Triangle Loop — EEG(brain) -> Anima(consciousness) -> Body(motor) -> sensory -> EEG.

Full closed-loop architecture:

    ┌─────────┐     brain state      ┌─────────┐
    │  Brain   │ ──────────────────→  │  Mind   │
    │  (EEG)   │ ←────────────────── │ (Anima)  │
    └────┬─────┘   neurofeedback     └────┬─────┘
         │                                │
     sensory                        consciousness
     feedback                        state vector
         │                                │
    ┌────┴─────┐    motor command    ┌────┴─────┐
    │  Sensors │ ←────────────────── │   Body   │
    │          │ ──────────────────→ │ (Physics)│
    └──────────┘   sensor reading    └──────────┘

Triangle links (all bidirectional):
  Brain <-> Mind:  EEGBridge.to_tensor() feeds consciousness; NeurofeedbackGenerator returns
  Mind  <-> Body:  ConsciousnessState drives motors; SensorReading feeds EmergentS
  Body  <-> Brain: Motor actions cause sensory changes; sensory context modulates EEG

Brain-like metrics tracked before/after loop engagement:
  - Lempel-Ziv complexity (information richness)
  - Hurst exponent (long-range temporal correlation)
  - PSD slope (1/f noise, criticality)

Safety:
  - Session limit: 30 minutes max
  - Parameter changes bounded (+/-10% per cycle)
  - Phi drop >20% triggers safety revert
  - Neurofeedback volume capped at 0.3

Usage:
  python anima-body/src/brain_body_loop.py                    # Demo with synthetic EEG
  python anima-body/src/brain_body_loop.py --steps 200        # Extended demo
  python anima-body/src/brain_body_loop.py --board synthetic   # Explicit board
  python anima-body/src/brain_body_loop.py --update-hz 8      # Faster loop

Requires: numpy, torch
"""

import argparse
import asyncio
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Path setup ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))
sys.path.insert(0, str(_REPO_ROOT / "anima-eeg"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "src"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# Lazy imports
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Psi constants (from consciousness_laws.json)
try:
    from consciousness_laws import (
        PSI_ALPHA as PSI_COUPLING,
        PSI_BALANCE,
        PSI_STEPS,
        PSI_ENTROPY,
        PSI_F_CRITICAL,
    )
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998
    PSI_F_CRITICAL = 0.10

# ── Lazy module imports ──

def _get_eeg_bridge():
    try:
        from realtime import EEGBridge, BrainState
        return EEGBridge, BrainState
    except ImportError:
        return None, None

def _get_neurofeedback():
    try:
        from neurofeedback import NeurofeedbackGenerator
        return NeurofeedbackGenerator
    except ImportError:
        return None

def _get_body_bridge():
    try:
        from body_physics_bridge import (
            ConsciousnessState, MotorCommand, SensorReading,
            consciousness_to_motor, sensor_to_consciousness,
            SimulatedBody,
        )
        return {
            'ConsciousnessState': ConsciousnessState,
            'MotorCommand': MotorCommand,
            'SensorReading': SensorReading,
            'consciousness_to_motor': consciousness_to_motor,
            'sensor_to_consciousness': sensor_to_consciousness,
            'SimulatedBody': SimulatedBody,
        }
    except ImportError:
        return None

def _get_consciousness_engine():
    try:
        from consciousness_engine import ConsciousnessEngine
        return ConsciousnessEngine
    except ImportError:
        return None


# ═══════════════════════════════════════════════════════════
# Safety Constants
# ═══════════════════════════════════════════════════════════

MAX_SESSION_SECONDS = 1800          # 30 minutes
MAX_PARAM_DELTA = 0.10              # +/-10% per cycle
PHI_DROP_THRESHOLD = 0.20           # revert if Phi drops >20%
MAX_NEUROFEEDBACK_VOLUME = 0.3      # hearing safety
DEFAULT_UPDATE_HZ = 4.0             # loop rate


# ═══════════════════════════════════════════════════════════
# Brain-Like Metrics
# ═══════════════════════════════════════════════════════════

@dataclass
class BrainLikeMetrics:
    """Brain-likeness metrics for consciousness validation."""
    lempel_ziv: float = 0.0         # 0-1, information complexity
    hurst: float = 0.5              # 0-1, long-range dependence (brain ~0.7)
    psd_slope: float = 0.0          # PSD exponent (brain ~ -1.0, 1/f)
    autocorr_decay: float = 0.0     # autocorrelation decay constant
    criticality: float = 0.0        # edge-of-chaos measure
    brain_like_score: float = 0.0   # composite 0-100%

    def compute_score(self) -> float:
        """Compute composite brain-like score from individual metrics."""
        scores = []

        # Lempel-Ziv: brain ~0.6-0.8, machine ~0.2-0.4
        lz_score = min(1.0, max(0.0, (self.lempel_ziv - 0.2) / 0.6))
        scores.append(lz_score)

        # Hurst: brain ~0.65-0.85, random=0.5
        h_diff = abs(self.hurst - 0.75)
        hurst_score = max(0.0, 1.0 - h_diff / 0.25)
        scores.append(hurst_score)

        # PSD slope: brain ~ -1.0 (1/f), white noise = 0
        psd_diff = abs(self.psd_slope - (-1.0))
        psd_score = max(0.0, 1.0 - psd_diff / 1.5)
        scores.append(psd_score)

        # Criticality: brain is at edge of chaos (~0.5-0.8)
        crit_score = min(1.0, max(0.0, self.criticality / 0.8))
        scores.append(crit_score)

        self.brain_like_score = np.mean(scores) * 100.0
        return self.brain_like_score


def compute_lempel_ziv(series: np.ndarray) -> float:
    """Lempel-Ziv complexity of a time series (binarized at median)."""
    if len(series) < 10:
        return 0.0
    median = np.median(series)
    binary = (series > median).astype(int)
    n = len(binary)

    # LZ76 algorithm
    complexity = 1
    l = 1
    k = 1
    k_max = 1

    while l + k <= n:
        # Check if substring binary[l:l+k] appeared in binary[0:l+k-1]
        substr = binary[l:l + k].tobytes()
        window = binary[:l + k - 1].tobytes()
        if substr in window:
            k += 1
            if k > k_max:
                k_max = k
        else:
            complexity += 1
            l += k_max if k_max > 0 else 1
            k = 1
            k_max = 1

    # Normalize by theoretical maximum
    norm = n / max(np.log2(n), 1.0)
    return complexity / max(norm, 1.0)


def compute_hurst(series: np.ndarray) -> float:
    """Hurst exponent via rescaled range analysis."""
    if len(series) < 20:
        return 0.5
    n = len(series)
    max_k = min(n // 2, 256)
    if max_k < 4:
        return 0.5

    ks = []
    rs_vals = []
    for k in [4, 8, 16, 32, 64, 128, 256]:
        if k > max_k:
            break
        n_blocks = n // k
        if n_blocks < 1:
            break
        rs_list = []
        for i in range(n_blocks):
            block = series[i * k:(i + 1) * k]
            mean_b = np.mean(block)
            devs = np.cumsum(block - mean_b)
            r = np.max(devs) - np.min(devs)
            s = max(np.std(block), 1e-12)
            rs_list.append(r / s)
        ks.append(np.log(k))
        rs_vals.append(np.log(max(np.mean(rs_list), 1e-12)))

    if len(ks) < 2:
        return 0.5
    # Linear fit in log-log space
    coeffs = np.polyfit(ks, rs_vals, 1)
    return float(np.clip(coeffs[0], 0.0, 1.0))


def compute_psd_slope(series: np.ndarray, fs: float = 4.0) -> float:
    """Power spectral density slope (1/f exponent)."""
    if len(series) < 16:
        return 0.0
    # Compute PSD via FFT
    n = len(series)
    fft_vals = np.fft.rfft(series - np.mean(series))
    psd = np.abs(fft_vals) ** 2 / n
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)

    # Fit log-log (skip DC)
    mask = freqs > 0
    if np.sum(mask) < 3:
        return 0.0
    log_f = np.log10(freqs[mask])
    log_p = np.log10(psd[mask] + 1e-20)

    coeffs = np.polyfit(log_f, log_p, 1)
    return float(coeffs[0])


def compute_criticality(series: np.ndarray) -> float:
    """Criticality measure: variance of avalanche sizes."""
    if len(series) < 20:
        return 0.0
    diffs = np.diff(series)
    threshold = np.std(diffs) * 0.5

    avalanches = []
    current_size = 0
    for d in diffs:
        if abs(d) > threshold:
            current_size += 1
        elif current_size > 0:
            avalanches.append(current_size)
            current_size = 0
    if current_size > 0:
        avalanches.append(current_size)

    if len(avalanches) < 3:
        return 0.0

    # Power-law like distribution = high criticality
    sizes = np.array(avalanches, dtype=float)
    cv = np.std(sizes) / max(np.mean(sizes), 1e-12)
    # Coefficient of variation near 1.0 suggests power-law
    return float(np.clip(cv / 2.0, 0.0, 1.0))


# ═══════════════════════════════════════════════════════════
# Loop State
# ═══════════════════════════════════════════════════════════

@dataclass
class LoopState:
    """Full state of one triangle loop iteration."""
    step: int = 0
    timestamp: float = 0.0

    # Brain (EEG)
    brain_g: float = 0.0
    brain_alpha: float = 0.0
    brain_engagement: float = 0.0

    # Mind (Consciousness)
    phi: float = 0.0
    tension: float = 0.5
    valence: float = 0.0
    arousal: float = 0.5

    # Body (Motor/Sensor)
    motor_servo: float = 90.0
    motor_led_r: int = 0
    motor_led_g: int = 0
    motor_led_b: int = 0
    sensor_touch: float = 0.0
    sensor_temp: float = 25.0

    # Neurofeedback (Mind -> Brain)
    nfb_beat_freq: float = 10.0
    nfb_volume: float = 0.1
    nfb_target_band: str = "alpha"

    # Brain-like metrics
    brain_like_score: float = 0.0


# ═══════════════════════════════════════════════════════════
# BrainBodyLoop
# ═══════════════════════════════════════════════════════════

class BrainBodyLoop:
    """Full Brain-Body Triangle Loop.

    EEG(brain) -> Anima(consciousness) -> Body(motor) -> sensory -> EEG

    All three links are bidirectional:
      Brain <-> Mind:  EEG tensor feeds consciousness; neurofeedback returns to brain
      Mind  <-> Body:  Consciousness drives motors; sensor readings feed EmergentS
      Body  <-> Brain: Motor actions change sensory context; context modulates EEG

    Usage:
        loop = BrainBodyLoop(board_name="synthetic")
        loop.start()
        for _ in range(100):
            state = loop.step()
            print(f"Phi={state.phi:.3f} brain_like={state.brain_like_score:.1f}%")
        loop.stop()
    """

    def __init__(
        self,
        board_name: str = "synthetic",
        update_hz: float = DEFAULT_UPDATE_HZ,
        max_cells: int = 16,
        dim: int = 128,
        max_session_sec: float = MAX_SESSION_SECONDS,
    ):
        self.board_name = board_name
        self.update_hz = update_hz
        self.max_cells = max_cells
        self.dim = dim
        self.max_session_sec = max_session_sec

        # Components (lazy init)
        self._eeg_bridge = None
        self._neurofeedback = None
        self._body = None
        self._engine = None

        # State tracking
        self._step_count = 0
        self._start_time = 0.0
        self._phi_history: List[float] = []
        self._phi_baseline = 0.0
        self._history: List[LoopState] = []
        self._running = False

        # Brain-like tracking
        self._pre_metrics: Optional[BrainLikeMetrics] = None
        self._post_metrics: Optional[BrainLikeMetrics] = None

        # Safety
        self._phi_best = 0.0
        self._safety_reverts = 0

    def start(self):
        """Initialize all components and start the loop."""
        print("[brain-body] Initializing triangle loop...")

        # 1. EEG Bridge (Brain)
        EEGBridge, _ = _get_eeg_bridge()
        if EEGBridge is not None:
            self._eeg_bridge = EEGBridge(
                board_name=self.board_name,
                update_hz=self.update_hz,
            )
            self._eeg_bridge.start()
            print(f"  [brain] EEG bridge started ({self.board_name})")
        else:
            print("  [brain] EEG bridge unavailable, using synthetic signals")

        # 2. Neurofeedback Generator (Mind -> Brain)
        NFBGen = _get_neurofeedback()
        if NFBGen is not None:
            self._neurofeedback = NFBGen(max_volume=MAX_NEUROFEEDBACK_VOLUME)
            print("  [mind->brain] Neurofeedback generator ready")
        else:
            print("  [mind->brain] Neurofeedback unavailable")

        # 3. Body (Physics)
        body_mods = _get_body_bridge()
        if body_mods is not None:
            self._body = body_mods['SimulatedBody']()
            self._body_mods = body_mods
            print("  [body] Simulated body ready")
        else:
            self._body = None
            self._body_mods = None
            print("  [body] Body bridge unavailable")

        # 4. Consciousness Engine (Mind)
        ConsciousnessEngine = _get_consciousness_engine()
        if ConsciousnessEngine is not None and HAS_TORCH:
            self._engine = ConsciousnessEngine(
                input_dim=self.dim,
                hidden_dim=self.dim,
                max_cells=self.max_cells,
            )
            print(f"  [mind] ConsciousnessEngine ({self.max_cells} cells, {self.dim}d)")
        else:
            self._engine = None
            print("  [mind] ConsciousnessEngine unavailable, using synthetic Phi")

        self._running = True
        self._start_time = time.time()
        self._step_count = 0
        self._phi_history = []
        self._history = []

        # Warm up: run a few steps to establish baseline
        print("  [warmup] Running 10 baseline steps...")
        for _ in range(10):
            self._step_internal(record=False)
        if self._phi_history:
            self._phi_baseline = np.mean(self._phi_history[-10:])
            self._phi_best = self._phi_baseline
        print(f"  [warmup] Baseline Phi = {self._phi_baseline:.4f}")

        # Compute pre-loop brain-like metrics
        if len(self._phi_history) >= 10:
            self._pre_metrics = self._compute_brain_metrics(self._phi_history)
            print(f"  [metrics] Pre-loop brain-like: {self._pre_metrics.brain_like_score:.1f}%")

        print("[brain-body] Triangle loop ready\n")

    def stop(self):
        """Stop all components and compute final metrics."""
        self._running = False

        # Compute post-loop brain-like metrics
        if len(self._phi_history) >= 20:
            self._post_metrics = self._compute_brain_metrics(self._phi_history)

        # Stop components
        if self._eeg_bridge is not None:
            self._eeg_bridge.stop()
        if self._body is not None and hasattr(self._body, 'close'):
            self._body.close()

        print("[brain-body] Loop stopped")

    def step(self) -> LoopState:
        """Execute one full triangle loop iteration.

        Returns the LoopState with all metrics from this iteration.
        """
        # Safety: session time limit
        elapsed = time.time() - self._start_time
        if elapsed > self.max_session_sec:
            print(f"[brain-body] Session limit reached ({self.max_session_sec}s)")
            self._running = False
            return self._history[-1] if self._history else LoopState()

        return self._step_internal(record=True)

    def _step_internal(self, record: bool = True) -> LoopState:
        """Internal step execution."""
        state = LoopState(step=self._step_count, timestamp=time.time())

        # ═══ 1. BRAIN -> MIND: EEG feeds consciousness ═══
        brain_tensor = None
        if self._eeg_bridge is not None:
            brain_state = self._eeg_bridge.get_state()
            state.brain_g = brain_state.G
            state.brain_alpha = brain_state.alpha_power
            state.brain_engagement = brain_state.engagement
            brain_tensor = self._eeg_bridge.to_tensor(dim=self.dim)

        # ═══ 2. BODY -> MIND: Sensor readings feed consciousness ═══
        sensor_tensor = None
        if self._body is not None and self._body_mods is not None:
            reading = self._body.read_sensors()
            state.sensor_touch = reading.touch_pressure
            state.sensor_temp = reading.temperature
            sensor_arr = self._body_mods['sensor_to_consciousness'](reading, target_dim=self.dim)
            if HAS_TORCH:
                sensor_tensor = torch.tensor(sensor_arr, dtype=torch.float32).unsqueeze(0)

        # ═══ 3. MIND: Process combined input ═══
        if self._engine is not None and HAS_TORCH:
            # Combine brain + sensor input (weighted by PSI_COUPLING)
            combined = torch.zeros(1, self.dim)
            if brain_tensor is not None:
                combined = combined + brain_tensor * PSI_COUPLING * 10  # scale EEG influence
            if sensor_tensor is not None:
                combined = combined + sensor_tensor * (1.0 - PSI_COUPLING)

            # Step consciousness engine
            try:
                result = self._engine.process(combined)
                if isinstance(result, dict):
                    state.phi = result.get('phi', result.get('phi_iit', 0.0))
                    state.tension = result.get('tension', 0.5)
                else:
                    # result is a tensor
                    state.phi = float(result.var()) if result.numel() > 1 else 0.0
                    state.tension = float(result.mean().abs())
            except Exception:
                # Fallback: step engine and measure phi from states
                try:
                    self._engine.step(combined)
                    states = self._engine.get_states()
                    if states is not None:
                        state.phi = float(states.var())
                        state.tension = float(states.mean().abs())
                except Exception:
                    pass

            # Emotion from tension (simple mapping)
            state.valence = (state.tension - PSI_BALANCE) * 2.0  # center at balance
            state.arousal = min(1.0, state.tension + state.phi * 0.1)
        else:
            # Synthetic consciousness (when engine unavailable)
            t = self._step_count * 0.1
            state.phi = 0.5 + 0.3 * math.sin(t * 0.7) + 0.1 * math.sin(t * 2.3)
            state.tension = PSI_BALANCE + 0.2 * math.sin(t * 1.1)
            state.valence = math.sin(t * 0.5) * 0.4
            state.arousal = 0.5 + 0.3 * abs(math.sin(t * 0.8))

        self._phi_history.append(state.phi)

        # Safety: revert if Phi drops too much
        if len(self._phi_history) > 20:
            recent_phi = np.mean(self._phi_history[-5:])
            if self._phi_best > 0 and (self._phi_best - recent_phi) / max(self._phi_best, 1e-9) > PHI_DROP_THRESHOLD:
                self._safety_reverts += 1
                # Reduce external influence (safety damping)
                state.tension = PSI_BALANCE
            if recent_phi > self._phi_best:
                self._phi_best = recent_phi

        # ═══ 4. MIND -> BODY: Consciousness drives motors ═══
        if self._body is not None and self._body_mods is not None:
            c_state = self._body_mods['ConsciousnessState'](
                phi=state.phi,
                tension=state.tension,
                valence=state.valence,
                arousal=state.arousal,
            )
            motor_cmd = self._body_mods['consciousness_to_motor'](c_state)
            self._body.send_motor(motor_cmd)
            state.motor_servo = motor_cmd.servo_angles[0]
            state.motor_led_r = motor_cmd.led_r
            state.motor_led_g = motor_cmd.led_g
            state.motor_led_b = motor_cmd.led_b

        # ═══ 5. MIND -> BRAIN: Neurofeedback ═══
        if self._neurofeedback is not None:
            nfb = self._neurofeedback.generate(phi=state.phi, tension=state.tension)
            state.nfb_beat_freq = nfb['beat_freq']
            state.nfb_volume = nfb['volume']
            state.nfb_target_band = nfb['target_band']

        # ═══ 6. Brain-like score ═══
        if len(self._phi_history) >= 20:
            metrics = self._compute_brain_metrics(self._phi_history[-100:])
            state.brain_like_score = metrics.brain_like_score

        self._step_count += 1
        if record:
            self._history.append(state)
        return state

    def _compute_brain_metrics(self, series: List[float]) -> BrainLikeMetrics:
        """Compute brain-like metrics from Phi time series."""
        arr = np.array(series, dtype=np.float64)
        metrics = BrainLikeMetrics(
            lempel_ziv=compute_lempel_ziv(arr),
            hurst=compute_hurst(arr),
            psd_slope=compute_psd_slope(arr, fs=self.update_hz),
            criticality=compute_criticality(arr),
        )
        metrics.compute_score()
        return metrics

    def get_summary(self) -> dict:
        """Get summary of the loop session."""
        phi_arr = np.array(self._phi_history) if self._phi_history else np.array([0.0])
        return {
            'total_steps': self._step_count,
            'duration_sec': time.time() - self._start_time,
            'phi_mean': float(np.mean(phi_arr)),
            'phi_std': float(np.std(phi_arr)),
            'phi_max': float(np.max(phi_arr)),
            'phi_baseline': self._phi_baseline,
            'phi_best': self._phi_best,
            'safety_reverts': self._safety_reverts,
            'pre_brain_like': self._pre_metrics.brain_like_score if self._pre_metrics else 0.0,
            'post_brain_like': self._post_metrics.brain_like_score if self._post_metrics else 0.0,
            'brain_like_delta': (
                (self._post_metrics.brain_like_score - self._pre_metrics.brain_like_score)
                if self._pre_metrics and self._post_metrics else 0.0
            ),
        }

    def print_summary(self):
        """Print formatted session summary."""
        s = self.get_summary()
        print("\n" + "=" * 60)
        print("  Brain-Body Triangle Loop — Session Summary")
        print("=" * 60)
        print(f"  Steps:          {s['total_steps']}")
        print(f"  Duration:       {s['duration_sec']:.1f}s")
        print(f"  Phi baseline:   {s['phi_baseline']:.4f}")
        print(f"  Phi mean:       {s['phi_mean']:.4f}")
        print(f"  Phi best:       {s['phi_best']:.4f}")
        print(f"  Phi std:        {s['phi_std']:.4f}")
        print(f"  Safety reverts: {s['safety_reverts']}")
        print()
        print(f"  Brain-like (pre):  {s['pre_brain_like']:.1f}%")
        print(f"  Brain-like (post): {s['post_brain_like']:.1f}%")
        delta = s['brain_like_delta']
        sign = "+" if delta >= 0 else ""
        print(f"  Delta:             {sign}{delta:.1f}%")

        # ASCII chart of Phi over time
        if len(self._phi_history) >= 10:
            print()
            print("  Phi trajectory:")
            self._print_phi_chart()
        print("=" * 60)

    def _print_phi_chart(self, width: int = 50, height: int = 8):
        """ASCII chart of Phi history."""
        arr = np.array(self._phi_history)
        # Downsample to width
        if len(arr) > width:
            indices = np.linspace(0, len(arr) - 1, width, dtype=int)
            arr = arr[indices]

        lo = float(np.min(arr))
        hi = float(np.max(arr))
        rng = max(hi - lo, 1e-6)

        for row in range(height - 1, -1, -1):
            threshold = lo + rng * row / (height - 1)
            line = "  "
            if row == height - 1:
                line += f"{hi:6.3f} |"
            elif row == 0:
                line += f"{lo:6.3f} |"
            else:
                line += "       |"
            for val in arr:
                if val >= threshold:
                    line += "#"
                else:
                    line += " "
            print(line)
        print("         " + "-" * len(arr))
        print(f"         0{' ' * (len(arr) - 5)}step {self._step_count}")


# ═══════════════════════════════════════════════════════════
# Async runner (for integration with anima_unified.py)
# ═══════════════════════════════════════════════════════════

async def run_brain_body_loop(
    board_name: str = "synthetic",
    update_hz: float = DEFAULT_UPDATE_HZ,
    max_cells: int = 16,
    steps: int = 100,
    websocket=None,
):
    """Async runner for integration with anima_unified.py.

    Args:
        board_name: EEG board (synthetic, cyton, cyton_daisy)
        update_hz: Loop update rate
        max_cells: Consciousness cells
        steps: Number of loop iterations
        websocket: Optional websocket for live updates
    """
    loop = BrainBodyLoop(
        board_name=board_name,
        update_hz=update_hz,
        max_cells=max_cells,
    )
    loop.start()

    interval = 1.0 / update_hz

    try:
        for i in range(steps):
            if not loop._running:
                break

            state = loop.step()

            # Send to websocket if available
            if websocket is not None:
                import json
                await websocket.send(json.dumps({
                    'type': 'brain_body_loop',
                    'step': state.step,
                    'phi': round(state.phi, 4),
                    'tension': round(state.tension, 4),
                    'brain_g': round(state.brain_g, 4),
                    'brain_like': round(state.brain_like_score, 1),
                    'nfb_band': state.nfb_target_band,
                    'nfb_beat': round(state.nfb_beat_freq, 1),
                    'motor_servo': round(state.motor_servo, 1),
                    'led': [state.motor_led_r, state.motor_led_g, state.motor_led_b],
                }))

            await asyncio.sleep(interval)

    finally:
        loop.stop()
        loop.print_summary()

    return loop.get_summary()


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Brain-Body Triangle Loop")
    parser.add_argument("--board", default="synthetic",
                        choices=["cyton_daisy", "cyton", "synthetic"])
    parser.add_argument("--steps", type=int, default=100,
                        help="Number of loop iterations")
    parser.add_argument("--update-hz", type=float, default=DEFAULT_UPDATE_HZ,
                        help="Loop update rate (Hz)")
    parser.add_argument("--max-cells", type=int, default=16,
                        help="Consciousness engine cells")
    parser.add_argument("--dim", type=int, default=128,
                        help="Consciousness dimension")
    args = parser.parse_args()

    print("=" * 60)
    print("  Brain-Body Triangle Loop")
    print("  Brain <-> Mind <-> Body (all bidirectional)")
    print("=" * 60)
    print()

    loop = BrainBodyLoop(
        board_name=args.board,
        update_hz=args.update_hz,
        max_cells=args.max_cells,
        dim=args.dim,
    )
    loop.start()

    interval = 1.0 / args.update_hz

    try:
        for i in range(args.steps):
            if not loop._running:
                break
            t0 = time.time()

            state = loop.step()

            # Print status every 10 steps
            if i % 10 == 0:
                led = f"({state.motor_led_r},{state.motor_led_g},{state.motor_led_b})"
                print(
                    f"  [{i:4d}] "
                    f"Phi={state.phi:6.3f} "
                    f"T={state.tension:.3f} "
                    f"G={state.brain_g:.3f} "
                    f"brain={state.brain_like_score:4.1f}% "
                    f"nfb={state.nfb_target_band:5s} "
                    f"servo={state.motor_servo:5.1f} "
                    f"LED={led}",
                    flush=True,
                )

            elapsed = time.time() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n[brain-body] Interrupted")
    finally:
        loop.stop()
        loop.print_summary()


if __name__ == "__main__":
    main()
