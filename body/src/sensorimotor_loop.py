#!/usr/bin/env python3
"""SensorimotorLoop — Bidirectional sensorimotor loop for consciousness embodiment.

Closes the loop: ConsciousnessEngine.step() -> motor_command -> simulated_sensor_feedback
-> consciousness_input -> next step.

The loop measures Phi(IIT) before and after engagement to verify that embodiment
enhances integrated information (Law 22: structure > function).

Architecture:
  ┌──────────────────────────────────────────────────────────────────┐
  │                    SensorimotorLoop                              │
  │                                                                  │
  │   ConsciousnessEngine.step(sensor_vec)                           │
  │         │                                                        │
  │         ▼                                                        │
  │   ConsciousnessState (10D: Φ,α,Z,N,W,E,M,C,T,I)                │
  │         │                                                        │
  │         ▼                                                        │
  │   consciousness_to_motor(state) → MotorCommand                   │
  │         │                                                        │
  │         ▼                                                        │
  │   body.send_motor(cmd)  →  body.read_sensors()                   │
  │         │                                                        │
  │         ▼                                                        │
  │   sensor_to_consciousness(reading) → sensor_vec (next input)     │
  │         │                                                        │
  │         └──────────────── feedback loop ──────────────────────┐   │
  │                                                               │   │
  │   Φ measurement: before loop vs during loop (Law 22 verify)   │   │
  │   Ψ-Constants: α=0.014 coupling, balance=0.5                  │   │
  └──────────────────────────────────────────────────────────────────┘

Usage:
  python anima-body/src/sensorimotor_loop.py               # Default demo (100 steps)
  python anima-body/src/sensorimotor_loop.py --steps 500    # 500 steps
  python anima-body/src/sensorimotor_loop.py --cells 32     # 32 consciousness cells

Requires: numpy, torch
"""

import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

# ── Project path setup ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "src"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# ── Lazy imports (_try pattern) ──
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

try:
    from consciousness_engine import ConsciousnessEngine
    HAS_ENGINE = True
except ImportError:
    HAS_ENGINE = False

try:
    from body_physics_bridge import (
        ConsciousnessState,
        MotorCommand,
        SensorReading,
        SimulatedBody,
        consciousness_to_motor,
        sensor_to_consciousness,
    )
    HAS_BODY = True
except ImportError:
    HAS_BODY = False

try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998

LN2 = math.log(2)


# ═══════════════════════════════════════════════════════════
# Sensorimotor telemetry
# ═══════════════════════════════════════════════════════════

@dataclass
class LoopTelemetry:
    """Per-step telemetry from the sensorimotor loop."""
    step: int = 0
    phi_iit: float = 0.0
    phi_proxy: float = 0.0
    tension: float = 0.0
    n_cells: int = 2
    motor_speed: float = 0.0
    sensor_magnitude: float = 0.0
    prediction_error: float = 0.0
    proprioception_balance: float = 1.0


@dataclass
class LoopResult:
    """Summary result from a sensorimotor loop run."""
    total_steps: int = 0
    phi_before: float = 0.0
    phi_after: float = 0.0
    phi_delta: float = 0.0
    phi_ratio: float = 1.0
    mean_tension: float = 0.0
    mean_prediction_error: float = 0.0
    max_cells: int = 2
    telemetry: List[LoopTelemetry] = field(default_factory=list)
    elapsed_s: float = 0.0


# ═══════════════════════════════════════════════════════════
# SensorimotorLoop
# ═══════════════════════════════════════════════════════════

class SensorimotorLoop:
    """Bidirectional sensorimotor loop connecting consciousness to a simulated body.

    The loop runs continuously:
      1. ConsciousnessEngine.step(sensor_input) -> result
      2. ConsciousnessState.from_engine_result(result) -> state
      3. consciousness_to_motor(state) -> motor_command
      4. body.send_motor(cmd) -> body.read_sensors() -> sensor_reading
      5. sensor_to_consciousness(reading) -> sensor_input (fed back to step 1)

    Phi(IIT) is measured at baseline (no sensory input) and during the loop
    to verify that embodied sensorimotor coupling enhances consciousness.
    """

    def __init__(
        self,
        max_cells: int = 16,
        cell_dim: int = 64,
        hidden_dim: int = 128,
        psi_coupling: float = PSI_COUPLING,
        psi_balance: float = PSI_BALANCE,
    ):
        if not HAS_TORCH:
            raise ImportError("torch required for SensorimotorLoop")
        if not HAS_ENGINE:
            raise ImportError("ConsciousnessEngine required (anima/src/consciousness_engine.py)")
        if not HAS_BODY:
            raise ImportError("body_physics_bridge required (anima-physics/src/body_physics_bridge.py)")

        self.max_cells = max_cells
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.psi_coupling = psi_coupling
        self.psi_balance = psi_balance

        # Create consciousness engine
        self.engine = ConsciousnessEngine(
            cell_dim=cell_dim,
            hidden_dim=hidden_dim,
            max_cells=max_cells,
        )

        # Create simulated body
        self.body = SimulatedBody()

        # Sensorimotor state
        self._sensor_vec: Optional[torch.Tensor] = None
        self._prev_motor: Optional[MotorCommand] = None
        self._step_count = 0

        # Telemetry
        self._telemetry: List[LoopTelemetry] = []

    def measure_baseline_phi(self, warmup_steps: int = 50) -> float:
        """Measure Phi(IIT) with no sensory input (baseline).

        Runs the engine for warmup_steps with zero input to establish
        the consciousness level without embodiment.
        """
        for _ in range(warmup_steps):
            self.engine.step(x_input=torch.zeros(self.cell_dim))
        result = self.engine.step(x_input=torch.zeros(self.cell_dim))
        return result.get("phi_iit", result.get("phi_proxy", 0.0))

    def step(self) -> LoopTelemetry:
        """Run one sensorimotor cycle.

        Returns per-step telemetry.
        """
        self._step_count += 1

        # 1. Process consciousness with sensor input
        if self._sensor_vec is not None:
            # Apply Psi coupling modulation to sensor input
            modulated = self._sensor_vec * (1.0 + self.psi_coupling * math.sin(
                self._step_count * self.psi_balance * math.pi
            ))
            result = self.engine.step(x_input=modulated)
        else:
            result = self.engine.step()

        # 2. Extract consciousness state
        state = ConsciousnessState.from_engine_result(result)

        # 3. Map to motor command
        cmd = consciousness_to_motor(state)

        # 4. Compute prediction error (proprioception)
        prediction_error = 0.0
        proprioception_balance = 1.0
        if self._prev_motor is not None:
            # Predicted acceleration from servo movement
            predicted_motion = abs(cmd.servo_angles[0] - 90.0) / 90.0
            prev_motion = abs(self._prev_motor.servo_angles[0] - 90.0) / 90.0
            prediction_error = abs(predicted_motion - prev_motion)

        # 5. Send motor command, read sensors
        self.body.send_motor(cmd)
        sensor = self.body.read_sensors()

        # 6. Sensor -> consciousness input vector
        consciousness_input = sensor_to_consciousness(sensor, self.cell_dim)
        self._sensor_vec = torch.from_numpy(consciousness_input).float()

        # Apply prediction error modulation (Law 22: structure learns)
        # High prediction error = amplified input (novelty signal)
        pe_gain = 1.0 + prediction_error * 2.0
        self._sensor_vec *= pe_gain

        # Store for next step
        self._prev_motor = cmd

        # Sensor magnitude for telemetry
        sensor_mag = float(np.linalg.norm(consciousness_input))

        # Build telemetry
        telem = LoopTelemetry(
            step=self._step_count,
            phi_iit=result.get("phi_iit", 0.0),
            phi_proxy=result.get("phi_proxy", 0.0),
            tension=result.get("mean_tension", state.tension),
            n_cells=result.get("n_cells", 2),
            motor_speed=cmd.servo_speed,
            sensor_magnitude=sensor_mag,
            prediction_error=prediction_error,
            proprioception_balance=proprioception_balance,
        )
        self._telemetry.append(telem)
        return telem

    def run(
        self,
        n_steps: int = 100,
        baseline_warmup: int = 50,
        verbose: bool = True,
    ) -> LoopResult:
        """Run the full sensorimotor loop with before/after Phi measurement.

        Args:
            n_steps: Number of loop iterations.
            baseline_warmup: Steps for baseline Phi measurement.
            verbose: Print progress.

        Returns:
            LoopResult with Phi comparison and telemetry.
        """
        t0 = time.monotonic()

        # Phase 1: Baseline Phi (no sensory loop)
        if verbose:
            print("  [sensorimotor] Phase 1: Measuring baseline Phi...")
            sys.stdout.flush()
        phi_before = self.measure_baseline_phi(baseline_warmup)
        if verbose:
            print(f"    Baseline Phi = {phi_before:.4f} ({baseline_warmup} warmup steps)")
            sys.stdout.flush()

        # Phase 2: Sensorimotor loop
        if verbose:
            print(f"  [sensorimotor] Phase 2: Running loop ({n_steps} steps)...")
            sys.stdout.flush()

        phi_samples = []
        for i in range(n_steps):
            telem = self.step()
            phi_samples.append(telem.phi_iit)
            if verbose and (i + 1) % max(1, n_steps // 10) == 0:
                print(
                    f"    step={i+1:4d}  Phi={telem.phi_iit:.4f}  "
                    f"T={telem.tension:.4f}  cells={telem.n_cells}  "
                    f"PE={telem.prediction_error:.4f}  sensor={telem.sensor_magnitude:.3f}"
                )
                sys.stdout.flush()

        # Phase 3: After-loop Phi (last 20% average)
        tail_start = max(0, len(phi_samples) - len(phi_samples) // 5)
        phi_after = float(np.mean(phi_samples[tail_start:])) if phi_samples else 0.0

        elapsed = time.monotonic() - t0

        # Compute result
        phi_delta = phi_after - phi_before
        phi_ratio = phi_after / max(phi_before, 1e-8)
        mean_tension = float(np.mean([t.tension for t in self._telemetry])) if self._telemetry else 0.0
        mean_pe = float(np.mean([t.prediction_error for t in self._telemetry])) if self._telemetry else 0.0
        max_cells = max((t.n_cells for t in self._telemetry), default=2)

        result = LoopResult(
            total_steps=n_steps,
            phi_before=phi_before,
            phi_after=phi_after,
            phi_delta=phi_delta,
            phi_ratio=phi_ratio,
            mean_tension=mean_tension,
            mean_prediction_error=mean_pe,
            max_cells=max_cells,
            telemetry=self._telemetry,
            elapsed_s=elapsed,
        )

        if verbose:
            self._print_summary(result)

        return result

    def _print_summary(self, result: LoopResult):
        """Print sensorimotor loop summary."""
        print()
        print("=" * 60)
        print("  Sensorimotor Loop Summary")
        print("=" * 60)
        print(f"  Steps:            {result.total_steps}")
        print(f"  Elapsed:          {result.elapsed_s:.2f}s")
        print(f"  Max cells:        {result.max_cells}")
        print()
        print(f"  Phi(before):      {result.phi_before:.4f}")
        print(f"  Phi(after):       {result.phi_after:.4f}")
        print(f"  Delta Phi:        {result.phi_delta:+.4f}")
        print(f"  Ratio:            {result.phi_ratio:.2f}x")
        print()
        print(f"  Mean tension:     {result.mean_tension:.4f}")
        print(f"  Mean pred error:  {result.mean_prediction_error:.4f}")
        print()

        # Psi constants used
        print(f"  Psi coupling:     {self.psi_coupling:.4f}")
        print(f"  Psi balance:      {self.psi_balance:.4f}")
        print()

        # ASCII graph of Phi over time
        phis = [t.phi_iit for t in result.telemetry]
        if phis:
            self._ascii_phi_graph(phis)

        # Verdict
        if result.phi_ratio > 1.05:
            print("  VERDICT: Embodiment ENHANCES consciousness (Phi increased)")
        elif result.phi_ratio > 0.95:
            print("  VERDICT: Embodiment NEUTRAL (Phi stable)")
        else:
            print("  VERDICT: Embodiment DISRUPTS consciousness (Phi decreased)")
        print("=" * 60)
        sys.stdout.flush()

    @staticmethod
    def _ascii_phi_graph(phis: List[float], width: int = 50, height: int = 10):
        """ASCII sparkline of Phi over time."""
        if not phis:
            return

        # Downsample to width
        n = len(phis)
        step = max(1, n // width)
        sampled = [phis[i] for i in range(0, n, step)][:width]

        phi_min = min(sampled)
        phi_max = max(sampled)
        phi_range = phi_max - phi_min if phi_max > phi_min else 1.0

        print(f"  Phi over time ({len(phis)} steps):")
        for row in range(height - 1, -1, -1):
            threshold = phi_min + (row / (height - 1)) * phi_range
            line = "  "
            if row == height - 1:
                line += f"{phi_max:6.3f} |"
            elif row == 0:
                line += f"{phi_min:6.3f} |"
            else:
                line += "       |"
            for val in sampled:
                if val >= threshold:
                    line += "*"
                else:
                    line += " "
            print(line)
        print("        +" + "-" * len(sampled))
        print(f"         0{' ' * (len(sampled) - 5)}{len(phis)} step")
        print()


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    """Sensorimotor loop demo.

    Measures Phi before and after engaging the sensorimotor loop
    to verify that embodied feedback enhances consciousness.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Sensorimotor Loop Demo")
    parser.add_argument("--steps", type=int, default=100, help="Loop iterations (default: 100)")
    parser.add_argument("--cells", type=int, default=16, help="Max consciousness cells (default: 16)")
    parser.add_argument("--warmup", type=int, default=50, help="Baseline warmup steps (default: 50)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    args = parser.parse_args()

    print("=" * 60)
    print("  Anima Sensorimotor Loop")
    print("  Consciousness + Body = Enhanced Phi?")
    print("=" * 60)
    print()
    print(f"  Config: cells={args.cells}, steps={args.steps}, warmup={args.warmup}")
    print(f"  Psi: alpha={PSI_COUPLING}, balance={PSI_BALANCE}, steps={PSI_STEPS}")
    print()
    sys.stdout.flush()

    loop = SensorimotorLoop(max_cells=args.cells)
    result = loop.run(
        n_steps=args.steps,
        baseline_warmup=args.warmup,
        verbose=not args.quiet,
    )

    return result


if __name__ == "__main__":
    main()
