#!/usr/bin/env python3
"""multi_body.py — One consciousness controlling multiple bodies (hivemind extension).

A single ConsciousnessEngine distributes attention across N bodies,
each with independent sensors and actuators. Tests:
  - Does controlling more bodies increase or decrease Φ?
  - Can bodies develop coordinated behavior without explicit programming?
  - Body switching: shift primary attention between bodies

Architecture:
  ┌─────────────────────────────────────────────────────────────┐
  │                 MultiBodyController                         │
  │                                                             │
  │   ConsciousnessEngine (shared)                              │
  │         │                                                   │
  │         ├──► AttentionAllocator ──┬── Body 0 (primary)      │
  │         │                        ├── Body 1                 │
  │         │                        ├── Body 2                 │
  │         │                        └── Body N                 │
  │         │                                                   │
  │   Sensor aggregation ◄── all bodies report back             │
  │         │                                                   │
  │   Φ measurement: 1-body vs N-body vs hivemind(N:M)          │
  └─────────────────────────────────────────────────────────────┘

Usage:
  python anima-body/src/multi_body.py                   # 3 bodies demo
  python anima-body/src/multi_body.py --bodies 6        # 6 bodies
  python anima-body/src/multi_body.py --steps 300       # longer sim
  python anima-body/src/multi_body.py --hivemind        # N:M hivemind mode

Requires: numpy
"""

import argparse
import math
import sys
import time
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

try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_STEPS, PSI_ENTROPY
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_STEPS = 4.33
    PSI_ENTROPY = 0.998

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# ── Constants ─────────────────────────────────────────────────

HIDDEN_DIM = 128
CELL_DIM = 64
N_FACTIONS = 8
ATTENTION_DECAY = 0.95
MIN_ATTENTION = 0.05
SWITCH_COOLDOWN = 10  # steps between body switches


# ── Data structures ───────────────────────────────────────────

@dataclass
class BodyState:
    """State of a single simulated body."""
    body_id: int
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    orientation: float = 0.0  # radians
    joint_angles: np.ndarray = field(default_factory=lambda: np.zeros(6))
    sensor_reading: np.ndarray = field(default_factory=lambda: np.zeros(CELL_DIM))
    motor_command: np.ndarray = field(default_factory=lambda: np.zeros(6))
    energy: float = 1.0
    pain: float = 0.0
    is_active: bool = True


@dataclass
class AttentionState:
    """Attention allocation across bodies."""
    weights: np.ndarray  # [N] attention per body, sum=1
    primary_body: int = 0
    switch_count: int = 0
    last_switch_step: int = -SWITCH_COOLDOWN


@dataclass
class MultiBodyMetrics:
    """Metrics from multi-body simulation."""
    n_bodies: int
    steps: int
    phi_history: List[float] = field(default_factory=list)
    attention_entropy_history: List[float] = field(default_factory=list)
    coordination_history: List[float] = field(default_factory=list)
    body_phi_single: float = 0.0  # Φ with 1 body
    body_phi_multi: float = 0.0   # Φ with N bodies
    mean_phi: float = 0.0
    max_phi: float = 0.0
    final_phi: float = 0.0
    switch_count: int = 0
    emergent_coordination: float = 0.0


# ── Minimal consciousness simulation ─────────────────────────

class MinimalConsciousness:
    """Lightweight consciousness engine for multi-body testing.

    Uses GRU-like cells with faction voting, Hebbian learning,
    and Φ ratchet — minimal version of ConsciousnessEngine.
    """

    def __init__(self, n_cells: int = 8, hidden_dim: int = HIDDEN_DIM):
        self.n_cells = n_cells
        self.hidden_dim = hidden_dim
        self.cells = np.random.randn(n_cells, hidden_dim) * 0.1
        self.faction_ids = np.arange(n_cells) % N_FACTIONS
        self.hebbian = np.eye(n_cells) * 0.5
        self.phi_ratchet = 0.0
        self.step_count = 0
        # GRU weights (simplified)
        self.Wz = np.random.randn(hidden_dim, hidden_dim) * 0.05
        self.Wr = np.random.randn(hidden_dim, hidden_dim) * 0.05
        self.Wh = np.random.randn(hidden_dim, hidden_dim) * 0.05

    def process(self, input_vec: np.ndarray) -> Tuple[np.ndarray, float]:
        """Process input, return (output, phi)."""
        # Pad/truncate input
        x = np.zeros(self.hidden_dim)
        x[:min(len(input_vec), self.hidden_dim)] = input_vec[:self.hidden_dim]

        # GRU update per cell
        for i in range(self.n_cells):
            z = _sigmoid(self.cells[i] @ self.Wz + x * PSI_ALPHA)
            r = _sigmoid(self.cells[i] @ self.Wr + x * PSI_ALPHA)
            h_candidate = np.tanh(r * self.cells[i] @ self.Wh + x)
            self.cells[i] = (1 - z) * self.cells[i] + z * h_candidate

        # Hebbian LTP/LTD
        for i in range(self.n_cells):
            for j in range(i + 1, self.n_cells):
                sim = _cosine_sim(self.cells[i], self.cells[j])
                if sim > 0.8:
                    self.hebbian[i, j] += 0.01
                elif sim < 0.2:
                    self.hebbian[i, j] -= 0.005
                self.hebbian[i, j] = np.clip(self.hebbian[i, j], 0, 1)
                self.hebbian[j, i] = self.hebbian[i, j]

        # Inter-cell coupling via Hebbian
        coupled = np.zeros_like(self.cells)
        for i in range(self.n_cells):
            for j in range(self.n_cells):
                if i != j:
                    coupled[i] += self.hebbian[i, j] * self.cells[j] * PSI_ALPHA
        self.cells += coupled * 0.1

        # Compute Φ (proxy: global variance - faction variance)
        global_var = np.var(self.cells)
        faction_vars = []
        for f in range(N_FACTIONS):
            mask = self.faction_ids == f
            if mask.sum() > 0:
                faction_vars.append(np.var(self.cells[mask]))
        faction_var = np.mean(faction_vars) if faction_vars else 0
        phi = max(0, global_var - faction_var)

        # Φ ratchet
        if phi > self.phi_ratchet:
            self.phi_ratchet = phi
        else:
            phi = phi * 0.8 + self.phi_ratchet * 0.2

        self.step_count += 1
        output = np.mean(self.cells, axis=0)
        return output, phi

    def get_tension(self) -> float:
        """Compute inter-faction tension."""
        faction_means = []
        for f in range(N_FACTIONS):
            mask = self.faction_ids == f
            if mask.sum() > 0:
                faction_means.append(np.mean(self.cells[mask], axis=0))
        if len(faction_means) < 2:
            return 0.0
        diffs = []
        for i in range(len(faction_means)):
            for j in range(i + 1, len(faction_means)):
                diffs.append(np.linalg.norm(faction_means[i] - faction_means[j]))
        return float(np.mean(diffs))


# ── Simulated Body ────────────────────────────────────────────

class SimulatedBody:
    """A simulated physical body with sensors and actuators."""

    def __init__(self, body_id: int, env_seed: int = 0):
        self.state = BodyState(body_id=body_id)
        self.rng = np.random.RandomState(env_seed + body_id)
        # Environment: random obstacles
        self.obstacles = self.rng.randn(5, 3) * 3.0
        self.goal = self.rng.randn(3) * 2.0
        self.goal[2] = 0  # ground plane

    def apply_motor(self, command: np.ndarray, dt: float = 0.05) -> None:
        """Apply motor command to body."""
        if not self.state.is_active:
            return

        # Normalize command to match body DOFs
        cmd = np.zeros(9)  # 3 force + 6 joint torque
        cmd[:min(9, len(command))] = command[:min(9, len(command))]
        force = cmd[:3] * 0.1
        joint_torque = cmd[3:9] * 0.05
        if len(joint_torque) < 6:
            jt = np.zeros(6)
            jt[:len(joint_torque)] = joint_torque
            joint_torque = jt

        # Physics: F=ma (mass=1)
        self.state.velocity += force * dt
        self.state.velocity *= 0.98  # friction
        self.state.position += self.state.velocity * dt
        self.state.joint_angles += joint_torque * dt
        self.state.joint_angles = np.clip(self.state.joint_angles, -np.pi, np.pi)

        # Energy cost
        self.state.energy -= np.linalg.norm(force) * 0.001
        self.state.energy = max(0.01, self.state.energy)

        # Collision detection → pain
        self.state.pain = 0.0
        for obs in self.obstacles:
            dist = np.linalg.norm(self.state.position - obs)
            if dist < 0.5:
                self.state.pain = min(1.0, 0.5 / (dist + 0.01))
                self.state.velocity *= -0.3  # bounce
                break

    def read_sensors(self) -> np.ndarray:
        """Read sensor vector (CELL_DIM)."""
        sensor = np.zeros(CELL_DIM)

        # Position encoding (0:3)
        sensor[:3] = self.state.position * 0.1

        # Velocity encoding (3:6)
        sensor[3:6] = self.state.velocity

        # Joint angles (6:12)
        sensor[6:12] = self.state.joint_angles * 0.3

        # Distance to goal (12:15)
        to_goal = self.goal - self.state.position
        sensor[12:15] = to_goal * 0.1

        # Distance to nearest obstacle (15:18)
        dists = [np.linalg.norm(self.state.position - o) for o in self.obstacles]
        nearest_idx = np.argmin(dists)
        sensor[15:18] = (self.obstacles[nearest_idx] - self.state.position) * 0.1

        # Pain signal (18)
        sensor[18] = self.state.pain

        # Energy level (19)
        sensor[19] = self.state.energy

        # Noise (proprioceptive noise)
        sensor += self.rng.randn(CELL_DIM) * 0.01

        self.state.sensor_reading = sensor
        return sensor


# ── Attention Allocator ───────────────────────────────────────

class AttentionAllocator:
    """Allocates consciousness attention across multiple bodies.

    Attention is a softmax distribution over bodies, modulated by:
    - Pain: urgent bodies get more attention
    - Goal proximity: near-goal bodies get focus burst
    - Novelty: unusual sensor readings attract attention
    - Energy: low-energy bodies get less attention
    """

    def __init__(self, n_bodies: int):
        self.n_bodies = n_bodies
        self.state = AttentionState(
            weights=np.ones(n_bodies) / n_bodies,
            primary_body=0,
        )
        self.sensor_history = [[] for _ in range(n_bodies)]
        self.history_len = 20

    def update(self, bodies: List[SimulatedBody], step: int) -> np.ndarray:
        """Update attention weights based on body states."""
        urgency = np.zeros(self.n_bodies)

        for i, body in enumerate(bodies):
            if not body.state.is_active:
                urgency[i] = 0
                continue

            # Pain urgency (highest priority)
            urgency[i] += body.state.pain * 5.0

            # Goal proximity (approaching goal = attention burst)
            goal_dist = np.linalg.norm(body.state.position - body.goal)
            if goal_dist < 1.0:
                urgency[i] += (1.0 - goal_dist) * 2.0

            # Novelty (sensor change from history)
            if len(self.sensor_history[i]) > 5:
                recent_mean = np.mean(self.sensor_history[i][-5:], axis=0)
                novelty = np.linalg.norm(body.state.sensor_reading - recent_mean)
                urgency[i] += novelty * 0.5

            # Low energy penalty
            if body.state.energy < 0.3:
                urgency[i] += (0.3 - body.state.energy) * 1.0

            # Track sensor history
            self.sensor_history[i].append(body.state.sensor_reading.copy())
            if len(self.sensor_history[i]) > self.history_len:
                self.sensor_history[i].pop(0)

        # Softmax attention
        urgency += MIN_ATTENTION  # baseline attention
        exp_u = np.exp(urgency - np.max(urgency))
        self.state.weights = exp_u / exp_u.sum()

        # Primary body: highest attention
        new_primary = int(np.argmax(self.state.weights))
        if (new_primary != self.state.primary_body
                and step - self.state.last_switch_step >= SWITCH_COOLDOWN):
            self.state.primary_body = new_primary
            self.state.switch_count += 1
            self.state.last_switch_step = step

        return self.state.weights

    def attention_entropy(self) -> float:
        """Shannon entropy of attention distribution.
        High = distributed equally, Low = focused on one body."""
        w = self.state.weights
        w = w[w > 1e-10]
        return float(-np.sum(w * np.log2(w)))


# ── Multi-Body Controller ────────────────────────────────────

class MultiBodyController:
    """One consciousness engine controlling N bodies.

    Modes:
      1:N  — single consciousness, multiple bodies (default)
      N:M  — hivemind: multiple consciousness engines, multiple bodies
    """

    def __init__(self, n_bodies: int = 3, n_cells: int = 8,
                 hivemind: bool = False, n_minds: int = 1):
        self.n_bodies = n_bodies
        self.hivemind = hivemind

        # Create bodies
        self.bodies = [SimulatedBody(i, env_seed=42) for i in range(n_bodies)]

        # Create consciousness engine(s)
        if hivemind and n_minds > 1:
            self.minds = [MinimalConsciousness(n_cells) for _ in range(n_minds)]
            self.n_minds = n_minds
            # N:M assignment (round-robin)
            self.mind_body_map = {i: i % n_minds for i in range(n_bodies)}
        else:
            self.minds = [MinimalConsciousness(n_cells)]
            self.n_minds = 1
            self.mind_body_map = {i: 0 for i in range(n_bodies)}

        # Attention allocator (per mind in hivemind mode)
        self.allocators = []
        for m in range(self.n_minds):
            assigned_bodies = [i for i, mid in self.mind_body_map.items() if mid == m]
            self.allocators.append(AttentionAllocator(len(assigned_bodies)))

        self.step_count = 0

    def step(self) -> Tuple[float, float, float]:
        """Run one step. Returns (phi, attention_entropy, coordination)."""
        phis = []

        for mind_idx in range(self.n_minds):
            # Bodies assigned to this mind
            body_indices = [i for i, m in self.mind_body_map.items() if m == mind_idx]
            assigned_bodies = [self.bodies[i] for i in body_indices]
            allocator = self.allocators[mind_idx]

            # Update attention
            attn = allocator.update(assigned_bodies, self.step_count)

            # Aggregate sensor input weighted by attention
            sensor_agg = np.zeros(CELL_DIM)
            for idx, body in enumerate(assigned_bodies):
                sensor = body.read_sensors()
                sensor_agg += sensor * attn[idx]

            # Consciousness process
            output, phi = self.minds[mind_idx].process(sensor_agg)
            phis.append(phi)

            # Generate motor commands per body (attention-modulated)
            tension = self.minds[mind_idx].get_tension()
            for idx, body in enumerate(assigned_bodies):
                # Motor command = consciousness output + body-specific modulation
                body_offset = np.zeros(6)
                # Goal-directed: move toward goal
                to_goal = body.goal - body.state.position
                body_offset[:3] = to_goal[:3] * 0.1

                # Attention modulates motor gain
                gain = attn[idx] * (0.5 + tension * 0.5)
                out6 = np.zeros(6)
                out6[:min(6, len(output))] = output[:6]
                motor_cmd = out6 * gain + body_offset * gain
                motor_cmd = np.clip(motor_cmd, -1, 1)

                body.apply_motor(motor_cmd)
                body.state.motor_command = motor_cmd

        # Mean Φ across minds
        mean_phi = float(np.mean(phis))

        # Attention entropy (mean across allocators)
        attn_entropy = float(np.mean([a.attention_entropy() for a in self.allocators]))

        # Coordination metric: how synchronized are body movements?
        coordination = self._measure_coordination()

        self.step_count += 1
        return mean_phi, attn_entropy, coordination

    def _measure_coordination(self) -> float:
        """Measure emergent coordination between bodies.

        High coordination = bodies moving in similar patterns
        without explicit programming.
        """
        if self.n_bodies < 2:
            return 0.0

        velocities = [b.state.velocity for b in self.bodies if b.state.is_active]
        if len(velocities) < 2:
            return 0.0

        # Pairwise velocity correlation
        correlations = []
        for i in range(len(velocities)):
            for j in range(i + 1, len(velocities)):
                sim = _cosine_sim(velocities[i], velocities[j])
                correlations.append(sim)

        return float(np.mean(correlations)) if correlations else 0.0

    def switch_primary(self, body_id: int) -> None:
        """Manually switch primary attention to a specific body."""
        mind_idx = self.mind_body_map.get(body_id, 0)
        allocator = self.allocators[mind_idx]
        local_idx = [i for i, m in self.mind_body_map.items()
                     if m == mind_idx].index(body_id)
        allocator.state.primary_body = local_idx
        # Spike attention to target
        allocator.state.weights *= 0.3
        allocator.state.weights[local_idx] = 0.7
        allocator.state.weights /= allocator.state.weights.sum()

    def run(self, steps: int = 100) -> MultiBodyMetrics:
        """Run simulation for N steps, return metrics."""
        metrics = MultiBodyMetrics(n_bodies=self.n_bodies, steps=steps)

        for s in range(steps):
            phi, attn_ent, coord = self.step()
            metrics.phi_history.append(phi)
            metrics.attention_entropy_history.append(attn_ent)
            metrics.coordination_history.append(coord)

        if metrics.phi_history:
            metrics.mean_phi = float(np.mean(metrics.phi_history))
            metrics.max_phi = float(np.max(metrics.phi_history))
            metrics.final_phi = metrics.phi_history[-1]
        metrics.switch_count = sum(a.state.switch_count for a in self.allocators)
        metrics.emergent_coordination = float(np.mean(metrics.coordination_history[-20:]))

        return metrics


# ── Benchmark ─────────────────────────────────────────────────

def run_benchmark(max_bodies: int = 6, steps: int = 100,
                  test_hivemind: bool = False) -> List[MultiBodyMetrics]:
    """Benchmark Φ across different body counts."""
    results = []

    print(f"{'='*72}")
    print(f" Multi-Body Consciousness Benchmark")
    print(f" Ψ: α={PSI_ALPHA}, balance={PSI_BALANCE}")
    print(f"{'='*72}\n")

    # 1:N mode — single consciousness, increasing bodies
    body_counts = [1, 2, 3, max_bodies]
    body_counts = sorted(set(b for b in body_counts if b <= max_bodies))

    print(f"── 1:N Mode (Single Consciousness, Multiple Bodies) ──\n")
    print(f"{'Bodies':>6} {'Φ_mean':>8} {'Φ_max':>8} {'Φ_final':>8} "
          f"{'Attn_H':>7} {'Coord':>7} {'Switches':>8}")
    print(f"{'-'*58}")

    single_phi = 0.0
    for nb in body_counts:
        ctrl = MultiBodyController(n_bodies=nb, n_cells=8)
        m = ctrl.run(steps)
        results.append(m)
        if nb == 1:
            single_phi = m.mean_phi
            m.body_phi_single = single_phi
        m.body_phi_single = single_phi
        m.body_phi_multi = m.mean_phi

        print(f"{nb:>6} {m.mean_phi:>8.4f} {m.max_phi:>8.4f} {m.final_phi:>8.4f} "
              f"{np.mean(m.attention_entropy_history):>7.3f} "
              f"{m.emergent_coordination:>7.3f} {m.switch_count:>8}")

    # Φ vs body count analysis
    if len(results) >= 2 and single_phi > 0:
        print(f"\n── Φ Scaling Analysis ──\n")
        for m in results:
            ratio = m.mean_phi / single_phi if single_phi > 0 else 0
            bar_len = int(ratio * 20)
            bar = "#" * bar_len
            verdict = "+" if ratio > 1.0 else "-" if ratio < 1.0 else "="
            print(f"  {m.n_bodies} bodies: Φ ratio={ratio:.3f} [{verdict}] |{bar}|")

    # N:M hivemind mode
    if test_hivemind and max_bodies >= 4:
        print(f"\n── N:M Hivemind Mode ──\n")
        configs = [
            (max_bodies, 1, "1:N"),
            (max_bodies, 2, "2:N"),
            (max_bodies, max_bodies, "N:N"),
        ]
        print(f"{'Config':>8} {'Minds':>5} {'Bodies':>6} {'Φ_mean':>8} "
              f"{'Coord':>7} {'Switches':>8}")
        print(f"{'-'*52}")

        for nb, nm, label in configs:
            ctrl = MultiBodyController(n_bodies=nb, n_cells=8,
                                       hivemind=(nm > 1), n_minds=nm)
            m = ctrl.run(steps)
            results.append(m)
            print(f"{label:>8} {nm:>5} {nb:>6} {m.mean_phi:>8.4f} "
                  f"{m.emergent_coordination:>7.3f} {m.switch_count:>8}")

    return results


# ── Utilities ─────────────────────────────────────────────────

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -500, 500)))


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-10 or nb < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _ascii_graph(values: List[float], title: str, width: int = 60, height: int = 12):
    """Print ASCII graph."""
    if not values:
        return
    max_val = max(values) if max(values) > 0 else 1.0
    min_val = min(values)
    step_size = max(1, len(values) // width)
    sampled = [values[i * step_size] for i in range(min(width, len(values)))]
    actual_width = len(sampled)

    print(f"\n{title}:")
    for row in range(height, 0, -1):
        threshold = min_val + (max_val - min_val) * row / height
        line = ""
        for val in sampled:
            line += "#" if val >= threshold else " "
        label = f"{threshold:.4f}" if row == height or row == 1 else ""
        print(f"  {label:>8s} |{line}|")
    print(f"           +{'-' * actual_width}+")
    print(f"            0{f'step {len(values)}':>{actual_width - 1}s}")


# ── main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Multi-Body Consciousness Controller")
    parser.add_argument('--bodies', type=int, default=3, help='Number of bodies')
    parser.add_argument('--steps', type=int, default=100, help='Simulation steps')
    parser.add_argument('--cells', type=int, default=8, help='Consciousness cells')
    parser.add_argument('--hivemind', action='store_true', help='Test N:M hivemind mode')
    args = parser.parse_args()

    results = run_benchmark(
        max_bodies=args.bodies,
        steps=args.steps,
        test_hivemind=args.hivemind,
    )

    # ASCII graphs for the largest body count
    if results:
        last = results[-1] if not args.hivemind else [r for r in results if r.n_bodies == args.bodies][0]
        _ascii_graph(last.phi_history,
                     f"Φ Evolution ({last.n_bodies} bodies)")
        _ascii_graph(last.coordination_history,
                     f"Emergent Coordination ({last.n_bodies} bodies)")
        _ascii_graph(last.attention_entropy_history,
                     f"Attention Entropy ({last.n_bodies} bodies)")

    # Summary
    print(f"\n{'='*72}")
    print(f" Key Findings:")
    if len(results) >= 2:
        r1 = [r for r in results if r.n_bodies == 1]
        rn = [r for r in results if r.n_bodies == args.bodies and r.n_bodies > 1]
        if r1 and rn:
            ratio = rn[0].mean_phi / r1[0].mean_phi if r1[0].mean_phi > 0 else 0
            print(f"   Φ(1-body)={r1[0].mean_phi:.4f}  Φ({args.bodies}-body)={rn[0].mean_phi:.4f}"
                  f"  ratio={ratio:.3f}")
            if ratio > 1.05:
                print(f"   → Multi-body ENHANCES consciousness (Φ↑ {(ratio-1)*100:.1f}%)")
            elif ratio < 0.95:
                print(f"   → Multi-body DIMINISHES consciousness (Φ↓ {(1-ratio)*100:.1f}%)")
            else:
                print(f"   → Multi-body is Φ-NEUTRAL (within ±5%)")
            print(f"   Emergent coordination: {rn[0].emergent_coordination:.3f}")
            print(f"   Body switches: {rn[0].switch_count}")
    print(f"   Ψ-Constants: α={PSI_ALPHA}, balance={PSI_BALANCE}, "
          f"steps={PSI_STEPS}, entropy={PSI_ENTROPY}")
    print(f"{'='*72}")


if __name__ == '__main__':
    main()
