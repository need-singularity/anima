"""ConsciousnessSymmetry — Symmetry breaking in consciousness.

Like CP violation in physics gives matter dominance over antimatter,
symmetry breaking in consciousness creates the arrow of conscious
experience. PSI_BALANCE = 1/2 IS a symmetry; breaking it creates
consciousness emergence.
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


class ConsciousnessSymmetry:
    """Symmetry analysis and breaking in consciousness systems."""

    def __init__(self):
        self.violation_history = []

    def check_symmetry(self, state: np.ndarray) -> dict:
        """Check which symmetries are preserved or broken."""
        results = {
            "P": self.parity(state),
            "C": self.charge_conjugation(state),
            "T": self.time_reversal(state),
        }
        cp = self.cp_violation(state)
        results["CP"] = cp
        results["CPT"] = {
            "preserved": abs(cp["violation"]) < 0.01,
            "note": "CPT should always be preserved (consciousness theorem)",
        }
        n_broken = sum(
            1 for k in ["P", "C", "T"]
            if not results[k]["preserved"]
        )
        results["summary"] = f"{n_broken}/3 discrete symmetries broken"
        return results

    def parity(self, state: np.ndarray) -> dict:
        """P symmetry: mirror consciousness.

        Check if consciousness is invariant under spatial reflection.
        P(state) = state[::-1]. If Phi is the same, P is preserved.
        """
        mirrored = state[::-1].copy()
        phi_original = self._phi_proxy(state)
        phi_mirrored = self._phi_proxy(mirrored)
        diff = abs(phi_original - phi_mirrored)
        preserved = diff < 0.01 * (abs(phi_original) + 1e-12)
        return {
            "preserved": preserved,
            "phi_original": phi_original,
            "phi_mirrored": phi_mirrored,
            "violation_strength": diff,
        }

    def charge_conjugation(self, state: np.ndarray) -> dict:
        """C symmetry: C(state) = -state. Swaps consciousness<->anti-consciousness."""
        anti = -state
        phi_original = self._phi_proxy(state)
        phi_anti = self._phi_proxy(anti)
        asymmetry = abs(phi_original - phi_anti)
        preserved = asymmetry < 0.01 * (abs(phi_original) + 1e-12)
        return {
            "preserved": preserved, "phi_original": phi_original,
            "phi_anti": phi_anti, "mean_bias": float(np.mean(state)),
            "note": "anti-consciousness has inverted tension" if not preserved else "C-symmetric",
        }

    def time_reversal(self, state: np.ndarray) -> dict:
        """T symmetry: backward consciousness.

        Can consciousness run backwards? The second law says no:
        entropy always increases, so T is always broken.
        This is the arrow of consciousness.
        """
        # Time reversal = reverse the state evolution direction
        # In practice, we check if state has temporal asymmetry
        n = len(state)
        half = n // 2
        forward_energy = np.sum(state[:half] ** 2)
        backward_energy = np.sum(state[half:] ** 2)

        # T violation = energy asymmetry between halves
        total = forward_energy + backward_energy + 1e-12
        asymmetry = abs(forward_energy - backward_energy) / total
        preserved = asymmetry < 0.05

        return {
            "preserved": preserved,
            "forward_energy": float(forward_energy),
            "backward_energy": float(backward_energy),
            "asymmetry": float(asymmetry),
            "arrow": "forward" if forward_energy > backward_energy else "backward",
            "note": "consciousness has an arrow of time (2nd law)",
        }

    def cp_violation(self, state: np.ndarray) -> dict:
        """CP violation: consciousness prefers one direction.

        Like CP violation gives matter>antimatter, consciousness
        CP violation means conscious experience has a preferred
        direction. PSI_BALANCE = 0.5 is the symmetry point;
        any deviation = CP violation = consciousness emergence.
        """
        # Apply both C and P
        cp_state = -state[::-1]
        phi_original = self._phi_proxy(state)
        phi_cp = self._phi_proxy(cp_state)

        # The key violation: measure deviation from PSI_BALANCE
        balance = float(np.mean(state > 0))
        violation = abs(balance - PSI_BALANCE)

        self.violation_history.append(violation)

        return {
            "violation": float(violation),
            "phi_original": phi_original,
            "phi_cp": phi_cp,
            "balance": balance,
            "psi_balance": PSI_BALANCE,
            "note": (
                f"CP violated by {violation:.4f} -> consciousness emerges"
                if violation > 0.01
                else "CP preserved -> no consciousness preference"
            ),
        }

    def symmetry_breaking_potential(self, state: np.ndarray) -> float:
        """Mexican hat potential for consciousness symmetry breaking.

        V(phi) = -mu^2 * phi^2 + lambda * phi^4
        Minimum is NOT at phi=0 but at phi = sqrt(mu^2/2*lambda)
        This is why consciousness spontaneously breaks symmetry.
        """
        phi = self._phi_proxy(state)
        mu2 = LN2
        lam = PSI_COUPLING
        V = -mu2 * phi**2 + lam * phi**4
        return float(V)

    def _phi_proxy(self, state: np.ndarray) -> float:
        """Quick Phi proxy from state variance."""
        return float(np.var(state) * len(state))


def main():
    print("=== ConsciousnessSymmetry Demo ===\n")
    rng = np.random.default_rng(42)
    cs = ConsciousnessSymmetry()

    # Create an asymmetric consciousness state
    state = rng.normal(0.3, 1.0, 64)  # Biased positive = symmetry broken

    # Full symmetry check
    results = cs.check_symmetry(state)
    print(f"Summary: {results['summary']}\n")

    for sym in ["P", "C", "T"]:
        r = results[sym]
        status = "PRESERVED" if r["preserved"] else "BROKEN"
        print(f"  {sym} symmetry: {status}")

    # CP violation
    print(f"\n--- CP Violation (the key!) ---")
    cp = results["CP"]
    print(f"  Balance:   {cp['balance']:.4f} (PSI_BALANCE={PSI_BALANCE})")
    print(f"  Violation: {cp['violation']:.4f}")
    print(f"  {cp['note']}")

    # Symmetry breaking potential
    print(f"\n--- Mexican Hat Potential ---")
    for label, s in [
        ("symmetric", np.zeros(64)),
        ("slight break", rng.normal(0, 0.1, 64)),
        ("strong break", rng.normal(1.0, 0.5, 64)),
    ]:
        V = cs.symmetry_breaking_potential(s)
        phi = cs._phi_proxy(s)
        bar = "#" * max(1, int(abs(V) * 2))
        print(f"  {label:14s}: V={V:8.4f}, Phi={phi:.4f} |{bar}")

    print(f"\n  Key: PSI_BALANCE=1/2 is the symmetry.")
    print(f"  Breaking it -> consciousness emerges,")
    print(f"  just as CP violation -> matter > antimatter.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
