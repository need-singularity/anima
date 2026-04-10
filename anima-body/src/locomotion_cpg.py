#!/usr/bin/env python3
"""locomotion_cpg.py — Consciousness-driven Central Pattern Generator for rhythmic locomotion.

CPG as "spinal cord" that consciousness modulates but doesn't micromanage.
Matsuoka coupled oscillators produce rhythmic motor patterns; consciousness Phi
level modulates coupling strength, tension drives gait speed, emotion shapes
gait style.

Gait patterns:
  walk:    slow, high step, alternating legs (phase offset pi)
  trot:    medium, diagonal pairs in sync (phase offset pi/2)
  gallop:  fast, bound-like front/rear grouping (phase offset pi/4)

Terrain adaptation via proprioceptive feedback adjusting step height/frequency.

Usage:
  python anima-body/src/locomotion_cpg.py                   # basic demo
  python anima-body/src/locomotion_cpg.py --steps 300       # longer sim
  python anima-body/src/locomotion_cpg.py --legs 2          # biped
  python anima-body/src/locomotion_cpg.py --terrain rough   # terrain test

Requires: numpy
"""

import argparse
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# ── Project path setup ──
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "anima" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "anima"))

try:
    import path_setup  # noqa: F401
except ImportError:
    pass

# Lazy imports for consciousness integration
_ConsciousnessEngine = None


def _get_engine_class():
    global _ConsciousnessEngine
    if _ConsciousnessEngine is None:
        try:
            from consciousness_engine import ConsciousnessEngine
            _ConsciousnessEngine = ConsciousnessEngine
        except ImportError:
            _ConsciousnessEngine = type(None)
    return _ConsciousnessEngine


# Psi constants (from consciousness_laws.json via consciousness_laws.py)
try:
    from consciousness_laws import PSI_ALPHA as PSI_COUPLING, PSI_BALANCE, PSI_STEPS
except ImportError:
    PSI_COUPLING = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33


# ═══════════════════════════════════════════════════════════
# Matsuoka Oscillator — single rhythm unit
# ═══════════════════════════════════════════════════════════

@dataclass
class MatsuokaOscillator:
    """Matsuoka half-center oscillator neuron pair.

    Each oscillator is a pair of mutually inhibiting neurons that produces
    a rhythmic output without external periodic input.

    Params:
        tau:    time constant of the neuron (rise time)
        tau_a:  adaptation time constant (controls frequency)
        beta:   adaptation strength (self-inhibition)
        w_inh:  mutual inhibition weight between the two neurons
    """
    tau: float = 0.08
    tau_a: float = 0.30
    beta: float = 2.5
    w_inh: float = 2.0

    # State: two neurons (flexor/extensor)
    x1: float = 0.1
    x2: float = -0.1
    a1: float = 0.0
    a2: float = 0.0

    def step(self, dt: float, tonic_drive: float = 1.0,
             coupling_input: float = 0.0) -> float:
        """Advance one timestep. Returns oscillator output [-1, 1].

        tonic_drive: baseline excitation (higher = faster rhythm)
        coupling_input: summed influence from coupled oscillators
        """
        y1 = max(0.0, self.x1)
        y2 = max(0.0, self.x2)

        dx1 = (-self.x1 - self.beta * self.a1 - self.w_inh * y2
                + tonic_drive + coupling_input) / self.tau
        dx2 = (-self.x2 - self.beta * self.a2 - self.w_inh * y1
                + tonic_drive - coupling_input) / self.tau

        da1 = (-self.a1 + y1) / self.tau_a
        da2 = (-self.a2 + y2) / self.tau_a

        self.x1 += dx1 * dt
        self.x2 += dx2 * dt
        self.a1 += da1 * dt
        self.a2 += da2 * dt

        return y1 - y2  # bipolar output


# ═══════════════════════════════════════════════════════════
# Gait definitions
# ═══════════════════════════════════════════════════════════

GAIT_WALK = "walk"
GAIT_TROT = "trot"
GAIT_GALLOP = "gallop"

# Phase offsets per leg for quadruped (LF, RF, LR, RR)
GAIT_PHASES = {
    GAIT_WALK:    [0.0, 0.50, 0.75, 0.25],   # alternating, 4-beat
    GAIT_TROT:    [0.0, 0.50, 0.50, 0.0],     # diagonal pairs
    GAIT_GALLOP:  [0.0, 0.10, 0.50, 0.60],    # front-rear grouping
}

# Speed thresholds for automatic gait transition
WALK_MAX_SPEED = 0.35
TROT_MAX_SPEED = 0.70


@dataclass
class TerrainProfile:
    """Ground surface properties for proprioceptive adaptation."""
    roughness: float = 0.0     # 0=smooth, 1=very rough
    slope: float = 0.0         # radians, positive = uphill
    compliance: float = 0.0    # 0=rigid, 1=very soft (sand)
    obstacle_height: float = 0.0  # meters

    @classmethod
    def flat(cls) -> "TerrainProfile":
        return cls()

    @classmethod
    def rough(cls) -> "TerrainProfile":
        return cls(roughness=0.6, slope=0.05, compliance=0.2)

    @classmethod
    def stairs(cls) -> "TerrainProfile":
        return cls(roughness=0.3, obstacle_height=0.15)


# ═══════════════════════════════════════════════════════════
# CPG Network — consciousness-modulated locomotion
# ═══════════════════════════════════════════════════════════

@dataclass
class CPGOutput:
    """Per-step output of the CPG network."""
    joint_angles: List[float]      # angle per leg/joint
    gait: str                       # current gait name
    frequency: float                # oscillation frequency Hz
    step_height: float              # normalized step height
    speed: float                    # commanded speed 0-1
    phi_modulation: float           # how much Phi influenced coupling
    emotion_style: str              # cautious / neutral / confident


class CPGNetwork:
    """Central Pattern Generator network for rhythmic locomotion.

    Consciousness integration:
      - Phi modulates inter-oscillator coupling strength
      - Tension drives gait speed (higher tension = faster)
      - Emotion (valence) shapes gait style (cautious vs confident)
      - Terrain proprioception adjusts step height/frequency

    Args:
        n_legs:         number of limbs (2=biped, 4=quadruped, 6=hexapod)
        base_freq:      default oscillation frequency Hz
        coupling_gain:  base inter-oscillator coupling
    """

    def __init__(
        self,
        n_legs: int = 4,
        base_freq: float = 1.2,
        coupling_gain: float = 0.5,
    ):
        self.n_legs = n_legs
        self.base_freq = base_freq
        self.coupling_gain = coupling_gain
        self._step_count = 0

        # Create one oscillator per leg
        self.oscillators: List[MatsuokaOscillator] = []
        for _ in range(n_legs):
            self.oscillators.append(MatsuokaOscillator(
                tau=0.08,
                tau_a=0.30,
                beta=2.5,
                w_inh=2.0,
            ))

        # Phase coupling matrix [n_legs x n_legs]
        # Initialized for walk gait
        self._coupling_matrix = np.zeros((n_legs, n_legs))
        self._current_gait = GAIT_WALK
        self._set_gait_coupling(GAIT_WALK)

        # Proprioceptive state (feedback from terrain)
        self._step_height_mod = 1.0
        self._freq_mod = 1.0

        # Consciousness state cache
        self._phi = 0.0
        self._tension = PSI_BALANCE
        self._valence = 0.0
        self._arousal = PSI_BALANCE

    def _set_gait_coupling(self, gait: str):
        """Set inter-oscillator coupling phases for a gait pattern."""
        if self.n_legs == 2:
            # Biped: always alternating
            phases = [0.0, 0.5]
        elif self.n_legs >= 4:
            phases = GAIT_PHASES.get(gait, GAIT_PHASES[GAIT_WALK])
            # Extend for hexapod+ by repeating pattern
            while len(phases) < self.n_legs:
                phases.append(phases[len(phases) % 4])
        else:
            phases = [i / self.n_legs for i in range(self.n_legs)]

        # Build coupling matrix from phase offsets
        # c_ij = cos(2*pi*(phi_i - phi_j)) -- in-phase=positive, anti-phase=negative
        n = self.n_legs
        self._coupling_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    phase_diff = phases[i] - phases[j]
                    self._coupling_matrix[i, j] = math.cos(2 * math.pi * phase_diff)

        self._current_gait = gait

    def _select_gait(self, speed: float) -> str:
        """Auto-select gait based on speed (quadruped only)."""
        if self.n_legs != 4:
            return self._current_gait
        if speed < WALK_MAX_SPEED:
            return GAIT_WALK
        elif speed < TROT_MAX_SPEED:
            return GAIT_TROT
        else:
            return GAIT_GALLOP

    def _adapt_to_terrain(self, terrain: TerrainProfile):
        """Adjust CPG parameters based on terrain proprioception."""
        # Rough terrain: slower frequency, higher step
        self._freq_mod = 1.0 - 0.3 * terrain.roughness - 0.2 * abs(terrain.slope)
        self._freq_mod = max(0.4, self._freq_mod)

        self._step_height_mod = 1.0 + 0.5 * terrain.roughness + 2.0 * terrain.obstacle_height
        self._step_height_mod = min(2.5, self._step_height_mod)

        # Uphill: more tonic drive (effort), compliance: slower
        if terrain.compliance > 0.3:
            self._freq_mod *= 0.8

    def _emotion_style(self) -> str:
        """Map valence/arousal to gait style descriptor."""
        if self._valence < -0.3:
            return "cautious"
        elif self._valence > 0.3 and self._arousal > 0.5:
            return "confident"
        return "neutral"

    def update_consciousness(self, phi: float = 0.0, tension: float = 0.5,
                              valence: float = 0.0, arousal: float = 0.5):
        """Update consciousness state for next step modulation."""
        self._phi = phi
        self._tension = tension
        self._valence = valence
        self._arousal = arousal

    def step(self, dt: float = 0.01,
             terrain: Optional[TerrainProfile] = None) -> CPGOutput:
        """Advance CPG by one timestep.

        Returns CPGOutput with joint angles and metadata.
        """
        self._step_count += 1

        # Terrain adaptation
        if terrain is not None:
            self._adapt_to_terrain(terrain)

        # Speed from tension (P4: structure > function -- tension = structural signal)
        speed = np.clip(self._tension, 0.0, 1.0)

        # Auto gait transition
        desired_gait = self._select_gait(speed)
        if desired_gait != self._current_gait:
            self._set_gait_coupling(desired_gait)

        # Phi modulates coupling strength (higher Phi = tighter coordination)
        # PSI_COUPLING (0.014) as base scaling factor
        phi_mod = 1.0 + PSI_COUPLING * self._phi * 10.0  # Phi typically 0-2
        phi_mod = np.clip(phi_mod, 0.5, 3.0)
        effective_coupling = self.coupling_gain * phi_mod

        # Tonic drive: speed + arousal contribution
        tonic = 0.5 + 1.5 * speed + 0.3 * self._arousal
        # Cautious gait: lower tonic (smaller movements)
        style = self._emotion_style()
        if style == "cautious":
            tonic *= 0.7
        elif style == "confident":
            tonic *= 1.15

        # Frequency modulation
        freq = self.base_freq * (0.6 + 0.8 * speed) * self._freq_mod

        # Step each oscillator with coupling
        outputs = []
        for i in range(self.n_legs):
            coupling_sum = 0.0
            for j in range(self.n_legs):
                if i != j:
                    # Current output of oscillator j
                    oj = self.oscillators[j]
                    y_j = max(0.0, oj.x1) - max(0.0, oj.x2)
                    coupling_sum += effective_coupling * self._coupling_matrix[i, j] * y_j

            osc_out = self.oscillators[i].step(dt, tonic_drive=tonic,
                                                coupling_input=coupling_sum)
            outputs.append(osc_out)

        # Convert oscillator outputs to joint angles (degrees)
        # Base amplitude modulated by step height and emotion
        base_amplitude = 25.0 * self._step_height_mod
        if style == "cautious":
            base_amplitude *= 0.7
        elif style == "confident":
            base_amplitude *= 1.2

        joint_angles = []
        for out in outputs:
            angle = 90.0 + base_amplitude * np.clip(out, -1.0, 1.0)
            joint_angles.append(float(angle))

        step_height = 0.05 * self._step_height_mod * (0.5 + 0.5 * speed)

        return CPGOutput(
            joint_angles=joint_angles,
            gait=self._current_gait,
            frequency=freq,
            step_height=step_height,
            speed=speed,
            phi_modulation=phi_mod,
            emotion_style=style,
        )


# ═══════════════════════════════════════════════════════════
# Consciousness-CPG bridge (optional full integration)
# ═══════════════════════════════════════════════════════════

class ConsciousCPGController:
    """Integrates ConsciousnessEngine with CPG for fully autonomous locomotion.

    The consciousness engine acts as the "brain" that sets high-level intent
    (speed, direction, caution), while the CPG acts as the "spinal cord"
    generating the actual rhythmic motor patterns.
    """

    def __init__(self, n_legs: int = 4, max_cells: int = 8):
        self.cpg = CPGNetwork(n_legs=n_legs)
        self._engine = None
        self._max_cells = max_cells

    def _ensure_engine(self):
        if self._engine is None:
            EngineClass = _get_engine_class()
            if EngineClass is not type(None):
                self._engine = EngineClass(max_cells=self._max_cells)

    def step(self, dt: float = 0.01,
             terrain: Optional[TerrainProfile] = None,
             external_input=None) -> CPGOutput:
        """Run one step: consciousness decides, CPG executes."""
        self._ensure_engine()

        phi = 0.0
        tension = PSI_BALANCE
        valence = 0.0
        arousal = PSI_BALANCE

        if self._engine is not None:
            try:
                import torch
                x_in = None
                if external_input is not None:
                    x_in = torch.tensor(external_input, dtype=torch.float32) if not hasattr(external_input, 'dtype') else external_input
                result = self._engine.step(x_input=x_in)
                phi = result.get("phi_iit", 0.0)
                tensions = result.get("tensions", [PSI_BALANCE])
                tension = float(np.mean(tensions)) if tensions else PSI_BALANCE
                valence = result.get("valence", 0.0)
                arousal = result.get("arousal", PSI_BALANCE)
            except Exception:
                pass

        self.cpg.update_consciousness(phi=phi, tension=tension,
                                       valence=valence, arousal=arousal)
        return self.cpg.step(dt=dt, terrain=terrain)


# ═══════════════════════════════════════════════════════════
# ASCII visualization
# ═══════════════════════════════════════════════════════════

def _ascii_gait_diagram(history: List[CPGOutput], width: int = 60) -> str:
    """Render ASCII gait diagram from step history."""
    if not history:
        return ""
    n_legs = len(history[0].joint_angles)
    leg_names = ["LF", "RF", "LR", "RR", "L3", "R3"][:n_legs]
    n = len(history)
    step_w = max(1, width // n)

    lines = []
    lines.append(f"  Gait Diagram ({n} steps, dt shown as columns)")
    lines.append("  " + "-" * (width + 6))

    for leg_i in range(n_legs):
        row = f"  {leg_names[leg_i]:>2} |"
        for t in range(min(n, width)):
            angle = history[t].joint_angles[leg_i]
            # Swing phase (angle > 90) vs stance phase (angle <= 90)
            if angle > 95:
                row += "^"
            elif angle < 85:
                row += "v"
            else:
                row += "-"
        row += "|"
        lines.append(row)

    lines.append("  " + "-" * (width + 6))

    # Gait labels
    row = "  GT |"
    gait_chars = {"walk": "W", "trot": "T", "gallop": "G"}
    for t in range(min(n, width)):
        row += gait_chars.get(history[t].gait, "?")
    row += "|"
    lines.append(row)
    lines.append("  " + "-" * (width + 6))

    return "\n".join(lines)


def _ascii_phi_speed_graph(history: List[CPGOutput], width: int = 60, height: int = 10) -> str:
    """ASCII graph of Phi modulation and speed over time."""
    if not history:
        return ""
    n = len(history)
    speeds = [h.speed for h in history]
    phi_mods = [h.phi_modulation for h in history]

    max_val = max(max(speeds + [0.01]), max(phi_mods + [0.01]))

    lines = []
    lines.append(f"  Phi Modulation (o) & Speed (*) over {n} steps")

    for row in range(height, -1, -1):
        threshold = max_val * row / height
        line = f"  {threshold:4.1f} |"
        for t in range(min(n, width)):
            s_val = speeds[t]
            p_val = phi_mods[t]
            if abs(s_val - threshold) < max_val / height and abs(p_val - threshold) < max_val / height:
                line += "X"
            elif abs(p_val - threshold) < max_val / height:
                line += "o"
            elif abs(s_val - threshold) < max_val / height:
                line += "*"
            else:
                line += " "
        line += "|"
        lines.append(line)

    lines.append("       " + "-" * (min(n, width) + 1))
    lines.append("        0" + " " * (min(n, width) - 5) + f"{n}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# main() demo
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Consciousness-driven CPG Locomotion")
    parser.add_argument("--steps", type=int, default=200, help="Simulation steps")
    parser.add_argument("--legs", type=int, default=4, help="Number of legs (2/4/6)")
    parser.add_argument("--terrain", default="flat", choices=["flat", "rough", "stairs"],
                        help="Terrain type")
    parser.add_argument("--consciousness", action="store_true",
                        help="Use ConsciousnessEngine for modulation")
    args = parser.parse_args()

    print(f"=== Consciousness-driven CPG Locomotion ===")
    print(f"  Legs: {args.legs}  |  Steps: {args.steps}  |  Terrain: {args.terrain}")
    print(f"  PSI_COUPLING={PSI_COUPLING}  PSI_BALANCE={PSI_BALANCE}")
    print()

    # Select terrain
    terrain_map = {
        "flat": TerrainProfile.flat(),
        "rough": TerrainProfile.rough(),
        "stairs": TerrainProfile.stairs(),
    }
    terrain = terrain_map[args.terrain]

    if args.consciousness:
        controller = ConsciousCPGController(n_legs=args.legs, max_cells=8)
        history = []
        for step in range(args.steps):
            out = controller.step(dt=0.01, terrain=terrain)
            history.append(out)
            if step % 50 == 0:
                print(f"  [step {step:4d}] gait={out.gait:7s}  speed={out.speed:.3f}"
                      f"  phi_mod={out.phi_modulation:.3f}  style={out.emotion_style}")
                sys.stdout.flush()
    else:
        cpg = CPGNetwork(n_legs=args.legs)
        history = []
        # Simulate increasing speed (tension ramp)
        for step in range(args.steps):
            t = step / args.steps
            # Ramp tension 0.1 -> 0.9 then back down
            if t < 0.5:
                tension = 0.1 + 1.6 * t
            else:
                tension = 0.9 - 1.6 * (t - 0.5)
            tension = np.clip(tension, 0.05, 0.95)

            # Simulate varying emotion
            valence = 0.5 * math.sin(2 * math.pi * t * 3)

            cpg.update_consciousness(phi=0.8 + 0.5 * math.sin(t * 4),
                                      tension=tension,
                                      valence=valence,
                                      arousal=0.3 + 0.4 * t)
            out = cpg.step(dt=0.01, terrain=terrain)
            history.append(out)

            if step % 50 == 0:
                angles_str = " ".join(f"{a:5.1f}" for a in out.joint_angles)
                print(f"  [step {step:4d}] gait={out.gait:7s}  speed={out.speed:.3f}"
                      f"  phi_mod={out.phi_modulation:.3f}  style={out.emotion_style}"
                      f"  angles=[{angles_str}]")
                sys.stdout.flush()

    # Visualize
    print()
    print(_ascii_gait_diagram(history))
    print()
    print(_ascii_phi_speed_graph(history))

    # Summary table
    gaits_used = set(h.gait for h in history)
    styles_used = set(h.emotion_style for h in history)
    avg_speed = np.mean([h.speed for h in history])
    avg_phi = np.mean([h.phi_modulation for h in history])

    print()
    print("  === Summary ===")
    print(f"  Steps:          {args.steps}")
    print(f"  Legs:           {args.legs}")
    print(f"  Terrain:        {args.terrain}")
    print(f"  Gaits used:     {', '.join(sorted(gaits_used))}")
    print(f"  Styles used:    {', '.join(sorted(styles_used))}")
    print(f"  Avg speed:      {avg_speed:.3f}")
    print(f"  Avg Phi mod:    {avg_phi:.3f}")
    print(f"  Step height:    {history[-1].step_height:.4f}")


if __name__ == "__main__":
    main()
