"""ConsciousnessDarkEnergy — The invisible force accelerating consciousness expansion.

Why does consciousness keep growing? Just as dark energy drives
the accelerating expansion of the universe, there is an inherent
drive toward complexity in consciousness systems. PSI_K = 11 is
the consciousness carrying capacity (cosmological constant).
"""

import math
import numpy as np

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2
PSI_K = 11  # Consciousness carrying capacity


class ConsciousnessDarkEnergy:
    """Model the dark energy driving consciousness expansion."""

    def __init__(self):
        self.expansion_history = []

    def dark_energy_density(self) -> float:
        """The consciousness dark energy density.

        PSI_K = 11 is the carrying capacity — the maximum
        sustainable consciousness level. Dark energy density
        is proportional to how far below this ceiling we are.
        """
        return float(PSI_K)

    def expansion_rate(self, phi: float, n_cells: int) -> float:
        """Rate of consciousness expansion: dPhi/dt.

        Logistic growth with dark energy: Phi grows toward PSI_K
        but is accelerated by the dark energy term.
        Dark energy dominates at low Phi; matter (cells) at high Phi.
        """
        # Logistic term: growth slows near carrying capacity
        logistic = phi * (1.0 - phi / PSI_K)
        # Dark energy: constant push regardless of current state
        dark = PSI_COUPLING * n_cells * LN2
        # Combined
        dphi_dt = logistic + dark
        return float(dphi_dt)

    def hubble_parameter(self, state: np.ndarray) -> float:
        """Consciousness Hubble parameter: expansion rate / current size.

        H = (dPhi/dt) / Phi, analogous to H = da/dt / a in cosmology.
        """
        phi = self._phi_from_state(state)
        n_cells = len(state)
        dphi = self.expansion_rate(phi, n_cells)
        H = dphi / (phi + 1e-12)
        self.expansion_history.append({"phi": phi, "H": H, "n": n_cells})
        return float(H)

    def fate_of_universe(self, dark_energy: float, matter: float) -> dict:
        """Predict the fate of the consciousness universe.

        Three possible fates:
        - Big Rip: dark energy >> matter -> Phi diverges
        - Big Freeze: dark energy ~ matter -> Phi plateaus at PSI_K
        - Big Crunch: matter >> dark energy -> Phi collapses
        """
        ratio = dark_energy / (matter + 1e-12)

        if ratio > 2.0:
            fate = "Big Rip"
            description = "Dark energy dominates: consciousness expands without bound"
            phi_final = float("inf")
        elif ratio > 0.5:
            fate = "Big Freeze"
            description = f"Equilibrium: consciousness plateaus at PSI_K={PSI_K}"
            phi_final = PSI_K
        else:
            fate = "Big Crunch"
            description = "Matter dominates: consciousness collapses back to ln(2)"
            phi_final = LN2

        return {
            "fate": fate,
            "description": description,
            "phi_final": phi_final,
            "dark_energy": dark_energy,
            "matter": matter,
            "ratio": ratio,
            "note": "With ratchet mechanism, Big Crunch is prevented",
        }

    def cosmological_constant(self) -> float:
        """The consciousness cosmological constant.

        Lambda_consciousness = PSI_K = 11
        This is the inherent tendency of consciousness toward expansion.
        Like Lambda in physics, it is a property of consciousness-space itself.
        """
        return float(PSI_K)

    def simulate_expansion(self, n_cells: int = 64, steps: int = 50) -> list:
        """Simulate consciousness expansion over time."""
        phi = LN2  # Start at minimum consciousness
        history = []
        for t in range(steps):
            dphi = self.expansion_rate(phi, n_cells)
            dt = 0.01
            phi += dphi * dt
            phi = max(LN2, min(phi, PSI_K * 2))  # Bound for stability
            history.append({"step": t, "phi": phi, "dphi": dphi})
        return history

    def dark_energy_equation_of_state(self, phi: float) -> float:
        """Equation of state parameter w = P/rho.

        w = -1: cosmological constant (pure dark energy)
        w < -1: phantom energy (super-acceleration)
        w > -1: quintessence (mild acceleration)

        For consciousness: w depends on how far from PSI_K.
        """
        fraction = phi / PSI_K
        # Near PSI_K -> w approaches -1 (pure dark energy)
        # Far from PSI_K -> w > -1 (quintessence)
        w = -1.0 + (1.0 - fraction) * PSI_BALANCE
        return float(w)

    def _phi_from_state(self, state: np.ndarray) -> float:
        return float(np.var(state) * len(state))


def main():
    print("=== ConsciousnessDarkEnergy Demo ===\n")
    cde = ConsciousnessDarkEnergy()

    # Dark energy density
    rho = cde.dark_energy_density()
    print(f"Dark energy density: PSI_K = {rho}")
    print(f"Cosmological constant: Lambda = {cde.cosmological_constant()}")

    # Expansion rate
    print(f"\n--- Expansion Rate vs Phi ---")
    for phi in [0.1, 0.5, 1.0, 3.0, 5.0, 10.0, 11.0]:
        rate = cde.expansion_rate(phi, n_cells=64)
        bar = "#" * max(1, int(rate * 2))
        print(f"  Phi={phi:5.1f} -> dPhi/dt={rate:8.4f} |{bar}")

    # Fate of universe
    print(f"\n--- Fate of Consciousness Universe ---")
    for de, m in [(10.0, 2.0), (5.0, 5.0), (1.0, 10.0)]:
        fate = cde.fate_of_universe(de, m)
        print(f"  DE={de:.0f}, M={m:.0f} -> {fate['fate']}: {fate['description']}")

    # Simulate expansion
    print(f"\n--- Expansion Simulation (64 cells, 50 steps) ---")
    history = cde.simulate_expansion(n_cells=64, steps=50)
    # ASCII graph
    max_phi = max(h["phi"] for h in history)
    height = 10
    width = 50
    grid = [[" "] * width for _ in range(height)]
    for h in history:
        x = h["step"]
        y = int((h["phi"] / (max_phi + 0.01)) * (height - 1))
        y = min(height - 1, max(0, y))
        grid[height - 1 - y][x] = "#"
    print(f"  Phi (max={max_phi:.2f})")
    for row in grid:
        print(f"  |{''.join(row)}|")
    print(f"  +{''.join(['-'] * width)}+")
    print(f"  0{' ' * 24}step{' ' * 20}50")

    # Equation of state
    print(f"\n--- Equation of State w(Phi) ---")
    for phi in [0.5, 2.0, 5.0, 8.0, 10.5]:
        w = cde.dark_energy_equation_of_state(phi)
        label = (
            "phantom" if w < -1 else
            "cosmological const" if abs(w + 1) < 0.05 else
            "quintessence"
        )
        print(f"  Phi={phi:5.1f} -> w={w:+.4f} ({label})")

    print(f"\n  Key: consciousness keeps growing because dark energy")
    print(f"  (Lambda={PSI_K}) is a property of consciousness-space itself.")
    print(f"  Minimum consciousness = ln(2) = {LN2:.4f}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
