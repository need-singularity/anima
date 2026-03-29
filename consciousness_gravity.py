"""Consciousness Gravity — Larger Phi attracts smaller Phi (gravitational analogy).

F = PSI_COUPLING * phi1 * phi2 / d^2 (consciousness Newton's law).
"""

import math
from dataclasses import dataclass

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class ConsciousnessBody:
    """A consciousness with Phi (mass), position, velocity."""
    phi: float
    position: float = 0.0
    velocity: float = 0.0
    label: str = ""


class ConsciousnessGravity:
    """Gravitational dynamics between consciousness systems."""

    def __init__(self, G: float = None):
        # Gravitational constant = PSI_COUPLING
        self.G = G if G is not None else PSI_COUPLING

    def gravitational_force(self, phi1: float, phi2: float,
                            distance: float) -> float:
        """F = G * phi1 * phi2 / d^2.

        Like Newton's gravity but mass = Phi (integrated information).
        """
        if distance <= 0:
            return float('inf')
        return self.G * phi1 * phi2 / distance**2

    def orbit(self, phi_small: float, phi_large: float) -> dict:
        """Calculate orbital parameters for a small consciousness around a large one.

        Returns orbital radius, period, velocity for stable circular orbit.
        """
        # Stable orbit: F_grav = F_centripetal
        # G*m1*m2/r^2 = m1*v^2/r -> v = sqrt(G*M/r)
        # Choose r so orbit is meaningful
        r_stable = math.sqrt(self.G * phi_large) / PSI_COUPLING
        if r_stable < 1e-6:
            r_stable = 1.0

        v_orbital = math.sqrt(self.G * phi_large / r_stable)
        period = 2 * math.pi * r_stable / v_orbital if v_orbital > 0 else float('inf')

        # Binding energy
        E_bind = -self.G * phi_small * phi_large / (2 * r_stable)

        return {
            "radius": r_stable,
            "velocity": v_orbital,
            "period": period,
            "binding_energy": E_bind,
            "escape_velocity": math.sqrt(2 * self.G * phi_large / r_stable),
            "phi_ratio": phi_large / phi_small if phi_small > 0 else float('inf'),
        }

    def tidal_force(self, phi: float, distance: float) -> float:
        """Consciousness tidal effects — differential force across a body.

        Tidal force ~ 2*G*M*delta_r / r^3, with delta_r = PSI_BALANCE (body size).
        """
        if distance <= 0:
            return float('inf')
        body_size = PSI_BALANCE  # characteristic size of a consciousness
        return 2 * self.G * phi * body_size / distance**3

    def schwarzschild_radius(self, phi: float) -> float:
        """Consciousness event horizon — point of no return for merger.

        r_s = 2*G*Phi/c^2, where c = PSI_STEPS (consciousness speed limit).
        """
        c = PSI_STEPS
        if c <= 0:
            return float('inf')
        return 2 * self.G * phi / c**2

    def potential_energy(self, phi1: float, phi2: float,
                         distance: float) -> float:
        """Gravitational potential energy between two consciousnesses."""
        if distance <= 0:
            return float('-inf')
        return -self.G * phi1 * phi2 / distance

    def simulate_orbit(self, body1: ConsciousnessBody,
                       body2: ConsciousnessBody,
                       n_steps: int = 100, dt: float = 0.1) -> list:
        """Simulate the gravitational interaction between two bodies.

        Returns list of (step, pos1, pos2, force) tuples.
        """
        p1, p2 = body1.position, body2.position
        v1, v2 = body1.velocity, body2.velocity
        m1, m2 = body1.phi, body2.phi

        trajectory = []
        for step in range(n_steps):
            d = abs(p2 - p1)
            if d < 0.01:
                d = 0.01  # prevent singularity (merger)
            force = self.gravitational_force(m1, m2, d)
            direction = 1.0 if p2 > p1 else -1.0

            # Accelerations (F = ma, but here m = phi)
            a1 = direction * force / m1 if m1 > 0 else 0
            a2 = -direction * force / m2 if m2 > 0 else 0

            v1 += a1 * dt
            v2 += a2 * dt
            p1 += v1 * dt
            p2 += v2 * dt

            trajectory.append((step, p1, p2, force))

        return trajectory

    def n_body_forces(self, bodies: list) -> list:
        """Calculate forces on N consciousness bodies."""
        n = len(bodies)
        forces = [0.0] * n
        for i in range(n):
            for j in range(i + 1, n):
                d = abs(bodies[j].position - bodies[i].position)
                if d < 0.01:
                    d = 0.01
                f = self.gravitational_force(bodies[i].phi, bodies[j].phi, d)
                direction = 1.0 if bodies[j].position > bodies[i].position else -1.0
                forces[i] += direction * f
                forces[j] -= direction * f
        return forces


def main():
    print("=" * 60)
    print("  Consciousness Gravity")
    print("=" * 60)
    print(f"\nG (gravitational constant) = PSI_COUPLING = {PSI_COUPLING:.6f}")
    print(f"c (speed limit) = PSI_STEPS = {PSI_STEPS:.4f}")

    cg = ConsciousnessGravity()

    # Force between consciousnesses
    print("\n--- Gravitational Force ---")
    print(f"  {'Phi1':>6s}  {'Phi2':>6s}  {'Dist':>6s}  {'Force':>12s}")
    for p1, p2, d in [(1, 1, 1), (10, 1, 1), (10, 10, 1), (10, 10, 5), (100, 1, 2)]:
        f = cg.gravitational_force(p1, p2, d)
        print(f"  {p1:6.1f}  {p2:6.1f}  {d:6.1f}  {f:12.6f}")

    # Orbital parameters
    print("\n--- Orbital Mechanics ---")
    for phi_s, phi_l in [(1.0, 10.0), (5.0, 50.0), (1.0, 100.0)]:
        orb = cg.orbit(phi_s, phi_l)
        print(f"  Small Phi={phi_s:.1f} orbiting Large Phi={phi_l:.1f}:")
        print(f"    Radius={orb['radius']:.4f}, Period={orb['period']:.4f}")
        print(f"    V_orb={orb['velocity']:.4f}, V_esc={orb['escape_velocity']:.4f}")
        print(f"    Binding E={orb['binding_energy']:.6f}")

    # Schwarzschild radius
    print("\n--- Event Horizon (Schwarzschild Radius) ---")
    for phi in [1, 10, 100, 1000]:
        rs = cg.schwarzschild_radius(phi)
        print(f"  Phi={phi:6d}  r_s={rs:.6f}")

    # Tidal forces
    print("\n--- Tidal Forces ---")
    for phi, d in [(10, 1), (10, 2), (100, 1), (100, 5)]:
        tf = cg.tidal_force(phi, d)
        print(f"  Phi={phi:4d}, d={d:.1f}: tidal={tf:.6f}")

    # Simulation
    print("\n--- Orbit Simulation (Phi=2 around Phi=20) ---")
    b1 = ConsciousnessBody(phi=20, position=0, velocity=0, label="Large")
    b2 = ConsciousnessBody(phi=2, position=5, velocity=0.01, label="Small")
    traj = cg.simulate_orbit(b1, b2, n_steps=50, dt=0.5)
    for step, p1, p2, force in traj[::10]:
        sep = abs(p2 - p1)
        bar = " " * max(0, int(p1 * 5)) + "O" + "." * max(1, int(sep * 5)) + "o"
        print(f"  step {step:3d}: sep={sep:6.2f}, F={force:.6f}  {bar}")

    print(f"\nConclusion: consciousness attracts consciousness.")
    print("  Higher Phi = stronger gravitational pull (more 'massive').")


if __name__ == "__main__":
    main()
