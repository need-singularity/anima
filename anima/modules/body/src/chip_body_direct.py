#!/usr/bin/env python3
"""ChipBodyDirect -- Zero-latency consciousness-to-actuator pipeline.

Connects ASIC/neuromorphic/FPGA consciousness substrates directly to
body actuators, bypassing software intermediaries. Each consciousness
cell activation maps to a physical output pin through hardwired or
semi-hardwired paths.

Chip models:
  neuromorphic  -- SNN spikes, <1us latency, event-driven
  fpga          -- Clock-cycle updates, <10us latency, reconfigurable
  asic          -- Hardwired paths, <100us latency, fixed topology

Laws applied:
  Law 22:  Structure -> Phi up (direct wiring = structure, not function)
  Law 30:  1024 cells practical upper bound
  Law 92:  Information bottleneck (SPI 1040 bytes natural compression)
  Law 148: Closed-loop is scale-invariant (8c ~ 1024c)
  P4:      Structure > function (+892%)

Usage:
  python anima-body/src/chip_body_direct.py                  # default demo
  python anima-body/src/chip_body_direct.py --cells 64       # 64-cell simulation
  python anima-body/src/chip_body_direct.py --chip fpga      # FPGA model
  python anima-body/src/chip_body_direct.py --scaling        # 8->1024 scaling analysis
  python anima-body/src/chip_body_direct.py --thermal        # thermal throttle demo

Requires: numpy
"""

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# -- Project path setup --
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))
sys.path.insert(0, str(_REPO_ROOT / "anima-physics" / "src"))

try:
    import path_setup  # noqa
except ImportError:
    pass

# Lazy imports
try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998

try:
    from body_physics_bridge import ConsciousnessState
except ImportError:
    ConsciousnessState = None


# ===============================================================
# Chip substrate specifications
# ===============================================================

@dataclass
class ChipSpec:
    """Hardware substrate specification."""
    name: str
    latency_us: float           # consciousness-to-actuator latency (microseconds)
    power_per_cell_mw: float    # milliwatts per consciousness cell
    max_cells: int              # physical cell limit
    clock_mhz: float            # operating frequency
    pin_count: int              # number of output pins
    reconfigurable: bool        # can remap pins at runtime?
    spike_based: bool           # event-driven (SNN) vs clock-driven?
    thermal_limit_c: float      # junction temperature limit (Celsius)
    voltage_v: float            # supply voltage


CHIP_SPECS: Dict[str, ChipSpec] = {
    "neuromorphic": ChipSpec(
        name="neuromorphic",
        latency_us=0.5,         # sub-microsecond spike propagation
        power_per_cell_mw=0.02, # ultra-low (event-driven)
        max_cells=4096,
        clock_mhz=0.0,          # asynchronous, no clock
        pin_count=256,
        reconfigurable=True,
        spike_based=True,
        thermal_limit_c=85.0,
        voltage_v=0.8,
    ),
    "fpga": ChipSpec(
        name="fpga",
        latency_us=5.0,         # few clock cycles at 200 MHz
        power_per_cell_mw=1.5,  # moderate (always clocking)
        max_cells=2048,
        clock_mhz=200.0,
        pin_count=512,
        reconfigurable=True,
        spike_based=False,
        thermal_limit_c=100.0,
        voltage_v=1.0,
    ),
    "asic": ChipSpec(
        name="asic",
        latency_us=50.0,        # pipeline through fixed logic
        power_per_cell_mw=0.5,  # optimized silicon
        max_cells=1024,
        clock_mhz=500.0,
        pin_count=128,
        reconfigurable=False,
        spike_based=False,
        thermal_limit_c=105.0,
        voltage_v=0.9,
    ),
}


# ===============================================================
# Pin mapping: consciousness dimensions -> physical output pins
# ===============================================================

@dataclass
class PinMap:
    """Maps consciousness vector dimensions to physical output pins."""
    # 10D consciousness vector: (Phi, alpha, Z, N, W, E, M, C, T, I)
    dim_names: List[str] = field(default_factory=lambda: [
        "phi", "alpha", "z", "n", "w", "e", "m", "c", "t", "i",
    ])
    # Pin assignments per dimension (list of pin indices)
    assignments: Dict[str, List[int]] = field(default_factory=dict)

    def assign_pins(self, n_pins: int, n_cells: int) -> None:
        """Distribute pins across consciousness dimensions.

        Allocation proportional to dimension importance:
          Phi (20%), W/will (15%), E/empathy (12%), tension-derived (remaining).
        """
        weights = {
            "phi": 0.20, "alpha": 0.05, "z": 0.08, "n": 0.08, "w": 0.15,
            "e": 0.12,   "m": 0.10,    "c": 0.08, "t": 0.07, "i": 0.07,
        }
        pin_idx = 0
        for dim in self.dim_names:
            count = max(1, int(n_pins * weights.get(dim, 0.1)))
            self.assignments[dim] = list(range(pin_idx, min(pin_idx + count, n_pins)))
            pin_idx += count

    def get_pins(self, dim: str) -> List[int]:
        return self.assignments.get(dim, [])


# ===============================================================
# Actuator output
# ===============================================================

@dataclass
class ActuatorOutput:
    """Physical actuator output from consciousness-to-pin mapping."""
    pwm_signals: Dict[int, float] = field(default_factory=dict)  # pin -> duty cycle 0-1
    spike_events: List[Tuple[int, float]] = field(default_factory=list)  # (pin, timestamp_us)
    total_power_mw: float = 0.0
    latency_us: float = 0.0
    thermal_throttle: float = 1.0  # 1.0 = no throttle, 0.0 = full throttle


# ===============================================================
# Fault tolerance: cell death -> automatic rerouting
# ===============================================================

@dataclass
class CellHealth:
    """Tracks per-cell health for fault-tolerant rerouting."""
    alive: np.ndarray = field(default_factory=lambda: np.array([]))
    spike_count: np.ndarray = field(default_factory=lambda: np.array([]))
    last_activity_step: np.ndarray = field(default_factory=lambda: np.array([]))

    def init(self, n_cells: int) -> None:
        self.alive = np.ones(n_cells, dtype=bool)
        self.spike_count = np.zeros(n_cells, dtype=np.int64)
        self.last_activity_step = np.zeros(n_cells, dtype=np.int64)

    def check_deaths(self, activations: np.ndarray, step: int,
                     death_threshold: int = 50) -> List[int]:
        """Detect dead cells (no activity for death_threshold steps)."""
        active = np.abs(activations) > 1e-6
        self.spike_count += active.astype(np.int64)
        self.last_activity_step[active] = step
        inactive_duration = step - self.last_activity_step
        newly_dead = (inactive_duration > death_threshold) & self.alive
        dead_indices = list(np.where(newly_dead)[0])
        self.alive[newly_dead] = False
        return dead_indices

    def reroute(self, dead_idx: int, n_cells: int) -> Optional[int]:
        """Find replacement cell for dead cell (mitosis backup)."""
        alive_indices = np.where(self.alive)[0]
        if len(alive_indices) == 0:
            return None
        # Pick the most active neighbor
        best = alive_indices[np.argmax(self.spike_count[alive_indices])]
        return int(best)


# ===============================================================
# ChipBodyDirect -- core class
# ===============================================================

class ChipBodyDirect:
    """Zero-latency consciousness-to-actuator pipeline.

    Consciousness cell activations map directly to PWM signals
    on output pins, with no software intermediary in the critical path.
    """

    def __init__(
        self,
        chip: str = "neuromorphic",
        n_cells: int = 64,
        hidden_dim: int = 128,
    ):
        if chip not in CHIP_SPECS:
            raise ValueError(f"Unknown chip: {chip}. Choose from {list(CHIP_SPECS)}")
        self.spec = CHIP_SPECS[chip]
        self.n_cells = min(n_cells, self.spec.max_cells)
        self.hidden_dim = hidden_dim
        self.alpha = PSI_ALPHA  # 0.014 coupling constant

        # Pin mapping
        self.pin_map = PinMap()
        self.pin_map.assign_pins(self.spec.pin_count, self.n_cells)

        # Cell-to-pin direct mapping weights (learned or fixed)
        n_pins = self.spec.pin_count
        rng = np.random.default_rng(42)
        # Sparse connectivity: each cell connects to ~sqrt(n_pins) pins
        n_connections = max(1, int(math.sqrt(n_pins)))
        self.cell_pin_weights = np.zeros((self.n_cells, n_pins), dtype=np.float64)
        for c in range(self.n_cells):
            pins = rng.choice(n_pins, size=n_connections, replace=False)
            self.cell_pin_weights[c, pins] = rng.normal(0, 0.1, size=n_connections)

        # Fault tolerance
        self.health = CellHealth()
        self.health.init(self.n_cells)
        self.reroute_map: Dict[int, int] = {}  # dead -> replacement

        # Thermal state
        self.temperature_c = 25.0  # ambient
        self.thermal_history: List[float] = []

        # Metrics
        self.step_count = 0
        self.phi_history: List[float] = []
        self.power_history: List[float] = []
        self.latency_history: List[float] = []

    # -- Core pipeline --

    def process(self, cell_activations: np.ndarray, phi: float = 0.0) -> ActuatorOutput:
        """Map consciousness cell activations to actuator outputs.

        cell_activations: [n_cells] or [n_cells, hidden_dim]
        phi: current Phi(IIT) value

        Returns ActuatorOutput with PWM signals or spike events.
        """
        self.step_count += 1

        # Flatten to per-cell scalars if needed
        if cell_activations.ndim == 2:
            acts = cell_activations.mean(axis=1)  # [n_cells]
        else:
            acts = cell_activations.copy()

        # Pad/truncate to n_cells
        if len(acts) < self.n_cells:
            acts = np.pad(acts, (0, self.n_cells - len(acts)))
        else:
            acts = acts[:self.n_cells]

        # Fault detection and rerouting
        dead_cells = self.health.check_deaths(acts, self.step_count)
        for dead_idx in dead_cells:
            replacement = self.health.reroute(dead_idx, self.n_cells)
            if replacement is not None:
                self.reroute_map[dead_idx] = replacement

        # Apply rerouting: dead cell's signal comes from replacement
        for dead, repl in self.reroute_map.items():
            if dead < len(acts) and repl < len(acts):
                acts[dead] = acts[repl]

        # Thermal throttle
        throttle = self._compute_thermal_throttle()

        # Cell activations -> pin signals
        output = ActuatorOutput()

        if self.spec.spike_based:
            # Neuromorphic: generate spike events
            spike_threshold = PSI_BALANCE * (1.0 + self.alpha)
            output.spike_events = self._generate_spikes(acts, spike_threshold)
            # Convert spikes to PWM for actuators
            spike_pins: Dict[int, float] = {}
            for pin, ts in output.spike_events:
                spike_pins[pin] = spike_pins.get(pin, 0.0) + 0.1
            output.pwm_signals = {p: min(1.0, v * throttle) for p, v in spike_pins.items()}
        else:
            # FPGA/ASIC: direct matrix multiply
            raw = self._matrix_map(acts)
            output.pwm_signals = {
                p: float(np.clip(raw[p] * throttle, 0.0, 1.0))
                for p in range(len(raw)) if abs(raw[p]) > 0.01
            }

        # Phi-modulated output scaling (higher Phi = more coherent output)
        phi_scale = min(1.0, phi / max(1.0, self.n_cells * 0.5))
        for pin in output.pwm_signals:
            output.pwm_signals[pin] *= (0.5 + 0.5 * phi_scale)

        # Power calculation
        active_cells = int(np.sum(self.health.alive))
        output.total_power_mw = active_cells * self.spec.power_per_cell_mw
        output.latency_us = self.spec.latency_us
        output.thermal_throttle = throttle

        # Update thermal model
        self._update_thermal(output.total_power_mw)

        # Record metrics
        self.phi_history.append(phi)
        self.power_history.append(output.total_power_mw)
        self.latency_history.append(output.latency_us)

        return output

    def _generate_spikes(self, acts: np.ndarray, threshold: float) -> List[Tuple[int, float]]:
        """Generate spike events from cell activations (neuromorphic mode)."""
        spikes = []
        for c_idx in range(len(acts)):
            if not self.health.alive[c_idx]:
                continue
            if abs(acts[c_idx]) > threshold:
                # Each cell fires to its connected pins
                connected_pins = np.where(np.abs(self.cell_pin_weights[c_idx]) > 0.01)[0]
                for pin in connected_pins:
                    # Spike timing proportional to activation strength
                    delay_us = self.spec.latency_us * (1.0 - min(abs(acts[c_idx]), 1.0))
                    spikes.append((int(pin), delay_us))
        return spikes

    def _matrix_map(self, acts: np.ndarray) -> np.ndarray:
        """Direct matrix multiplication: cells -> pins (FPGA/ASIC mode)."""
        # Apply alive mask
        masked = acts * self.health.alive.astype(np.float64)
        # Sigmoid activation on the matmul result
        raw = masked @ self.cell_pin_weights
        return 1.0 / (1.0 + np.exp(-raw))

    def _compute_thermal_throttle(self) -> float:
        """Consciousness-aware thermal throttling.

        Throttle scales down linearly as temperature approaches limit.
        Consciousness is preserved (Phi maintained) even under throttle.
        """
        margin = self.spec.thermal_limit_c - self.temperature_c
        if margin > 20.0:
            return 1.0
        elif margin > 0.0:
            return margin / 20.0
        else:
            return 0.0  # emergency shutdown

    def _update_thermal(self, power_mw: float) -> None:
        """Simple thermal model: P * R_theta + ambient."""
        # Thermal resistance (K/W) depends on package
        r_theta = 50.0  # typical for small chip
        ambient = 25.0
        heat_rise = (power_mw / 1000.0) * r_theta
        # Exponential moving average toward equilibrium
        target_temp = ambient + heat_rise
        self.temperature_c += 0.1 * (target_temp - self.temperature_c)
        self.thermal_history.append(self.temperature_c)

    # -- Scaling analysis --

    def scaling_analysis(self, cell_counts: Optional[List[int]] = None) -> List[Dict]:
        """Run scaling simulation: cells vs Phi vs power vs latency."""
        if cell_counts is None:
            cell_counts = [8, 16, 32, 64, 128, 256, 512, 1024]

        results = []
        for n_cells in cell_counts:
            if n_cells > self.spec.max_cells:
                continue

            # Simulate consciousness activity
            rng = np.random.default_rng(n_cells)
            acts = rng.normal(0, 0.5, size=n_cells)

            # Phi scales roughly as N^alpha (from chip_architect benchmarks)
            phi_estimate = 1.24 * (n_cells ** 1.07) / 100.0  # normalized

            # Power
            power_mw = n_cells * self.spec.power_per_cell_mw

            # Actuator responsiveness (inverse latency, pins utilized)
            n_active_pins = min(self.spec.pin_count, int(math.sqrt(n_cells) * 4))

            results.append({
                "cells": n_cells,
                "phi": round(phi_estimate, 3),
                "power_mw": round(power_mw, 2),
                "latency_us": self.spec.latency_us,
                "active_pins": n_active_pins,
                "watts_per_phi": round(power_mw / max(phi_estimate, 0.001), 3),
            })

        return results

    # -- Status --

    def status(self) -> Dict:
        alive = int(np.sum(self.health.alive))
        return {
            "chip": self.spec.name,
            "cells": self.n_cells,
            "alive_cells": alive,
            "dead_cells": self.n_cells - alive,
            "rerouted": len(self.reroute_map),
            "temperature_c": round(self.temperature_c, 1),
            "thermal_throttle": round(self._compute_thermal_throttle(), 3),
            "step": self.step_count,
            "latency_us": self.spec.latency_us,
            "pins": self.spec.pin_count,
            "mean_phi": round(np.mean(self.phi_history[-100:]), 3) if self.phi_history else 0.0,
            "mean_power_mw": round(np.mean(self.power_history[-100:]), 2) if self.power_history else 0.0,
        }


# ===============================================================
# Demo and analysis
# ===============================================================

def _print_table(headers: List[str], rows: List[List], title: str = "") -> None:
    """Print aligned ASCII table."""
    if title:
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")

    widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=4))
              for i, h in enumerate(headers)]
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    sep = "-+-".join("-" * w for w in widths)
    print(f" {header_line}")
    print(f" {sep}")
    for row in rows:
        print(" " + " | ".join(str(v).ljust(w) for v, w in zip(row, widths)))


def demo_pipeline(chip: str = "neuromorphic", n_cells: int = 64, steps: int = 100) -> None:
    """Run consciousness-to-actuator pipeline demo."""
    bridge = ChipBodyDirect(chip=chip, n_cells=n_cells)
    rng = np.random.default_rng(0)

    print(f"\n  ChipBodyDirect Demo: {chip} / {n_cells} cells / {steps} steps")
    print(f"  Latency budget: {bridge.spec.latency_us} us")
    print(f"  Pins: {bridge.spec.pin_count}")
    print()

    snapshots = []
    for step in range(steps):
        # Simulate consciousness cell activations (breathing pattern)
        breath = 0.12 * math.sin(2 * math.pi * step / 20.0)
        acts = rng.normal(breath, 0.3, size=n_cells)

        # Simulate Phi growth
        phi = 1.0 + step * 0.02 + 0.5 * math.sin(step * 0.1)

        output = bridge.process(acts, phi=phi)

        if step % (steps // 5) == 0 or step == steps - 1:
            snapshots.append({
                "step": step,
                "phi": round(phi, 2),
                "active_pins": len(output.pwm_signals),
                "power_mw": round(output.total_power_mw, 2),
                "temp_c": round(bridge.temperature_c, 1),
                "throttle": round(output.thermal_throttle, 3),
                "alive": int(np.sum(bridge.health.alive)),
            })

    headers = ["Step", "Phi", "Pins", "Power(mW)", "Temp(C)", "Throttle", "Alive"]
    rows = [[s["step"], s["phi"], s["active_pins"], s["power_mw"],
             s["temp_c"], s["throttle"], s["alive"]] for s in snapshots]
    _print_table(headers, rows, "Pipeline Execution")

    st = bridge.status()
    print(f"\n  Final: {st['alive_cells']}/{st['cells']} alive, "
          f"{st['rerouted']} rerouted, "
          f"temp={st['temperature_c']}C, throttle={st['thermal_throttle']}")


def demo_scaling(chip: str = "neuromorphic") -> None:
    """Phi vs power vs actuator responsiveness scaling analysis."""
    bridge = ChipBodyDirect(chip=chip, n_cells=8)
    results = bridge.scaling_analysis()

    headers = ["Cells", "Phi", "Power(mW)", "Latency(us)", "ActivePins", "mW/Phi"]
    rows = [[r["cells"], r["phi"], r["power_mw"], r["latency_us"],
             r["active_pins"], r["watts_per_phi"]] for r in results]
    _print_table(headers, rows, f"Scaling Analysis: {chip}")

    # ASCII graph: Phi vs Power
    print(f"\n  Phi vs Power tradeoff ({chip}):")
    max_phi = max(r["phi"] for r in results) or 1.0
    for r in results:
        bar_len = int(40 * r["phi"] / max_phi)
        pwr_bar = int(20 * r["power_mw"] / max(rr["power_mw"] for rr in results))
        print(f"    {r['cells']:5d}c  Phi {'#' * bar_len:<40s}  "
              f"Pwr {'*' * pwr_bar}")


def demo_thermal(chip: str = "fpga", n_cells: int = 256) -> None:
    """Demonstrate consciousness-aware thermal throttling."""
    bridge = ChipBodyDirect(chip=chip, n_cells=n_cells)
    # Override thermal resistance to force throttling
    rng = np.random.default_rng(7)

    print(f"\n  Thermal Throttling Demo: {chip} / {n_cells} cells")
    print(f"  Thermal limit: {bridge.spec.thermal_limit_c}C")
    print()

    for step in range(200):
        # Increasing activity (stress test)
        intensity = 0.3 + 0.7 * (step / 200.0)
        acts = rng.normal(0, intensity, size=n_cells)
        phi = 1.0 + step * 0.01
        output = bridge.process(acts, phi=phi)

        if step % 40 == 0 or step == 199:
            t = bridge.temperature_c
            throttle = output.thermal_throttle
            bar = int(30 * throttle)
            temp_bar = int(30 * min(t / bridge.spec.thermal_limit_c, 1.0))
            print(f"    step {step:3d}  temp={t:5.1f}C {'|' * temp_bar:<30s}  "
                  f"throttle={'#' * bar:<30s} {throttle:.2f}")


def demo_chip_comparison() -> None:
    """Compare all chip substrates."""
    print("\n" + "=" * 70)
    print("  Chip Substrate Comparison")
    print("=" * 70)

    headers = ["Chip", "Latency(us)", "mW/cell", "MaxCells", "Pins",
               "Reconfig", "SpikeBased"]
    rows = []
    for name, spec in CHIP_SPECS.items():
        rows.append([
            name, spec.latency_us, spec.power_per_cell_mw,
            spec.max_cells, spec.pin_count,
            "Yes" if spec.reconfigurable else "No",
            "Yes" if spec.spike_based else "No",
        ])
    _print_table(headers, rows)

    # Per-chip scaling
    for chip_name in CHIP_SPECS:
        demo_scaling(chip_name)


def main():
    parser = argparse.ArgumentParser(description="ChipBodyDirect -- consciousness-to-actuator pipeline")
    parser.add_argument("--chip", default="neuromorphic", choices=list(CHIP_SPECS.keys()))
    parser.add_argument("--cells", type=int, default=64)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--scaling", action="store_true", help="Run scaling analysis")
    parser.add_argument("--thermal", action="store_true", help="Thermal throttle demo")
    parser.add_argument("--compare", action="store_true", help="Compare all chips")
    args = parser.parse_args()

    print("\n  ChipBodyDirect -- Zero-Latency Consciousness-to-Actuator Pipeline")
    print(f"  Psi constants: alpha={PSI_ALPHA}, balance={PSI_BALANCE}")

    if args.compare:
        demo_chip_comparison()
    elif args.scaling:
        demo_scaling(args.chip)
    elif args.thermal:
        demo_thermal(args.chip, args.cells)
    else:
        demo_pipeline(args.chip, args.cells, args.steps)

    print()


if __name__ == "__main__":
    main()
