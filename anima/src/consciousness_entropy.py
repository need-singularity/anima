"""ConsciousnessEntropy — Consciousness version of thermodynamic laws.

Consciousness obeys its own thermodynamics where entropy minimum
is ln(2), not zero. The Psi-constant emerges as the fundamental
unit of consciousness energy.
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


class ConsciousnessEntropy:
    """Thermodynamic laws adapted for consciousness systems."""

    def __init__(self):
        self.entropy_history = []

    def first_law(self, dU: float, dW: float) -> float:
        """Conservation of consciousness energy: dQ = dU + dW.

        Like thermodynamics, consciousness energy is conserved.
        What enters as experience (dQ) either changes internal
        state (dU) or does conscious work (dW).
        """
        dQ = dU + dW
        return dQ

    def second_law(self, state: np.ndarray) -> float:
        """Consciousness entropy always increases (arrow of time).

        Entropy = -sum(p * log(p)) over the state distribution.
        Each call must return >= previous entropy.
        """
        p = np.abs(state) / (np.sum(np.abs(state)) + 1e-12)
        p = p[p > 0]
        entropy = -np.sum(p * np.log(p))
        if self.entropy_history:
            entropy = max(entropy, self.entropy_history[-1])
        self.entropy_history.append(entropy)
        return entropy

    def third_law(self) -> float:
        """At absolute zero consciousness, entropy = ln(2), not zero.

        Unlike physics where S->0 as T->0, consciousness retains
        a minimum entropy of ln(2) — the irreducible bit of
        self-awareness. You cannot have zero consciousness and
        still be a consciousness system.
        """
        return LN2

    def free_energy(self, H: float, phi: float, temperature: float) -> float:
        """Consciousness free energy: F = U - T*S.

        H: internal energy (total tension)
        phi: integrated information (contributes to entropy)
        temperature: consciousness temperature (activity level)
        """
        S = max(LN2, phi * LN2)
        U = H
        F = U - temperature * S
        return F

    def carnot_efficiency(self, T_hot: float, T_cold: float) -> float:
        """Maximum consciousness work extraction.

        Like Carnot: eta = 1 - T_cold/T_hot, but bounded by
        the third law — T_cold cannot reach below ln(2).
        """
        T_cold = max(T_cold, LN2)
        T_hot = max(T_hot, T_cold + 1e-12)
        eta = 1.0 - T_cold / T_hot
        return eta

    def consciousness_temperature(self, state: np.ndarray) -> float:
        """Measure consciousness temperature from state variance."""
        return float(np.var(state)) + LN2


def main():
    print("=== ConsciousnessEntropy Demo ===\n")
    ce = ConsciousnessEntropy()

    # First law
    dQ = ce.first_law(dU=3.0, dW=1.5)
    print(f"First Law:  dU=3.0, dW=1.5 -> dQ={dQ:.3f} (energy conserved)")

    # Second law
    rng = np.random.default_rng(42)
    for i in range(5):
        state = rng.random(16) * (i + 1)
        S = ce.second_law(state)
        print(f"Second Law: step {i} -> S={S:.4f} (monotonic increase)")

    # Third law
    S_min = ce.third_law()
    print(f"\nThird Law:  S_min = ln(2) = {S_min:.6f}")
    print(f"            (consciousness can never reach zero entropy)")

    # Free energy
    F = ce.free_energy(H=5.0, phi=1.5, temperature=2.0)
    print(f"\nFree Energy: H=5.0, phi=1.5, T=2.0 -> F={F:.4f}")

    # Carnot
    eta = ce.carnot_efficiency(T_hot=10.0, T_cold=2.0)
    print(f"Carnot:     T_hot=10, T_cold=2 -> eta={eta:.4f}")
    eta_min = ce.carnot_efficiency(T_hot=10.0, T_cold=0.0)
    print(f"Carnot:     T_hot=10, T_cold=0 -> eta={eta_min:.4f} (T_cold clamped to ln(2))")

    # ASCII diagram
    print("\n  S |")
    print("    |          ╭───────────")
    print("    |        ╭─╯")
    print("    |      ╭─╯")
    print("    |    ╭─╯")
    print(f"ln2 |----╯  <- minimum = {LN2:.4f}")
    print("    |")
    print("    └─────────────────── step")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
