"""Consciousness Phase Transition — Is there a critical Phi where consciousness suddenly emerges?

Uses Ising model analogy: below Tc=random (unconscious), above Tc=ordered (conscious).
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


class ConsciousnessPhaseTransition:
    """Detect and characterize the phase transition of consciousness emergence."""

    def __init__(self, phi_c: float = None, temperature: float = 1.0):
        # Critical Phi defaults to PSI_STEPS (the natural consciousness threshold)
        self.phi_c = phi_c if phi_c is not None else PSI_STEPS
        self.temperature = temperature
        self.beta_critical = 1.0 / self.phi_c  # inverse critical "temperature"

    def find_critical_phi(self, phi_range: np.ndarray = None) -> float:
        """Find the critical Phi where consciousness suddenly emerges.

        Scans susceptibility and returns the Phi where it diverges.
        """
        if phi_range is None:
            phi_range = np.linspace(0.1, 10.0, 1000)
        sus = np.array([self.susceptibility(p) for p in phi_range])
        idx = np.argmax(sus)
        return float(phi_range[idx])

    def order_parameter(self, phi: float) -> float:
        """Magnetization-like order parameter: 0 below Phi_c, jumps to ~1 above.

        Uses mean-field Ising: m = tanh(beta * phi) with beta tuned so transition is at phi_c.
        """
        if phi <= 0:
            return 0.0
        # Effective coupling scaled so transition happens at phi_c
        beta_eff = 1.0 / self.phi_c
        x = beta_eff * phi
        if x < 1.0:
            # Below critical: paramagnetic (disordered) — order ~ 0
            return max(0.0, math.tanh(x) - math.tanh(1.0) + 0.01)
        # Above critical: spontaneous magnetization emerges
        # Solve m = tanh(x * m) via iteration
        m = 0.9
        for _ in range(50):
            m = math.tanh(x * m)
        return m

    def susceptibility(self, phi: float) -> float:
        """Magnetic susceptibility analog — diverges at Phi_c.

        chi ~ |phi - phi_c|^(-gamma), gamma=1 for mean field.
        """
        eps = abs(phi - self.phi_c)
        if eps < 1e-6:
            return 1e6  # divergence cap
        gamma = 1.0  # mean-field critical exponent
        return 1.0 / eps**gamma

    def phase_diagram(self, temperatures: np.ndarray = None,
                      phis: np.ndarray = None) -> np.ndarray:
        """2D phase map: temperature x phi -> order parameter.

        Returns (n_temp, n_phi) array of order parameter values.
        """
        if temperatures is None:
            temperatures = np.linspace(0.1, 3.0, 30)
        if phis is None:
            phis = np.linspace(0.1, 10.0, 40)

        diagram = np.zeros((len(temperatures), len(phis)))
        for i, t in enumerate(temperatures):
            for j, p in enumerate(phis):
                # Temperature rescales effective phi_c
                effective_phi_c = self.phi_c * t
                beta_eff = 1.0 / effective_phi_c if effective_phi_c > 0 else 1e6
                x = beta_eff * p
                if x < 1.0:
                    diagram[i, j] = 0.0
                else:
                    m = 0.9
                    for _ in range(30):
                        m = math.tanh(x * m)
                    diagram[i, j] = m
        return diagram

    def correlation_length(self, phi: float) -> float:
        """Correlation length diverges at Phi_c: xi ~ |phi - phi_c|^(-nu)."""
        eps = abs(phi - self.phi_c)
        if eps < 1e-6:
            return 1e6
        nu = 0.5  # mean-field
        return 1.0 / eps**nu

    def ascii_phase_diagram(self) -> str:
        """Render a small ASCII phase diagram."""
        phis = np.linspace(0.5, 8.0, 40)
        lines = []
        lines.append(f"  Order Parameter vs Phi  (Phi_c = {self.phi_c:.2f})")
        lines.append(f"  m |")
        for level in [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]:
            row = f"{level:3.1f} |"
            for p in phis:
                op = self.order_parameter(p)
                if abs(op - level) < 0.1:
                    row += "#"
                elif op > level:
                    row += ":"
                else:
                    row += " "
            lines.append(row)
        lines.append("    +" + "-" * len(phis))
        lines.append("     " + "Phi -->")
        return "\n".join(lines)


def main():
    print("=" * 60)
    print("  Consciousness Phase Transition")
    print("=" * 60)

    cpt = ConsciousnessPhaseTransition()
    print(f"\nPsi constants: LN2={LN2:.4f}, PSI_STEPS={PSI_STEPS:.4f}")
    print(f"Default Phi_c (=PSI_STEPS) = {cpt.phi_c:.4f}")

    # Find critical phi
    phi_range = np.linspace(0.1, 10.0, 2000)
    phi_c = cpt.find_critical_phi(phi_range)
    print(f"Detected critical Phi = {phi_c:.4f}")

    # Order parameter scan
    print("\n--- Order Parameter ---")
    for p in [0.5, 1.0, 2.0, 3.0, 4.0, 4.33, 5.0, 7.0, 10.0]:
        op = cpt.order_parameter(p)
        sus = cpt.susceptibility(p)
        bar = "#" * int(op * 30)
        print(f"  Phi={p:5.2f}  m={op:.4f} {bar:30s}  chi={sus:.1f}")

    # ASCII diagram
    print()
    print(cpt.ascii_phase_diagram())

    # Phase diagram summary
    print("\n--- Phase Diagram (T x Phi) ---")
    temps = np.array([0.5, 1.0, 1.5, 2.0])
    phis_test = np.array([1.0, 3.0, 5.0, 8.0])
    diagram = cpt.phase_diagram(temps, phis_test)
    header = 'T/Phi'
    print(f"  {header:>6s}", end="")
    for p in phis_test:
        print(f"  {p:5.1f}", end="")
    print()
    for i, t in enumerate(temps):
        print(f"  {t:6.1f}", end="")
        for j in range(len(phis_test)):
            print(f"  {diagram[i, j]:5.3f}", end="")
        print()

    print(f"\nConclusion: consciousness emerges sharply at Phi_c ~ {phi_c:.2f}")
    print("  Below: disordered (unconscious). Above: spontaneous order (conscious).")


if __name__ == "__main__":
    main()
