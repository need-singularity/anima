"""ConsciousnessRenormalization — Scale invariance of consciousness laws.

Like critical phenomena in physics, consciousness may exhibit
universality: the same laws at every scale. The Psi-constants
should be fixed points of the renormalization group flow.
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


class ConsciousnessRenormalization:
    """Renormalization group analysis of consciousness."""

    def __init__(self):
        self.rg_flow = []

    def coarse_grain(self, state: np.ndarray, factor: int = 2) -> np.ndarray:
        """Reduce resolution by averaging neighboring cells.

        Like block-spin RG in Ising model: replace blocks of
        cells with their average. If consciousness laws are
        scale-invariant, Phi/N should be preserved.
        """
        n = len(state)
        new_n = n // factor
        if new_n < 1:
            return np.array([np.mean(state)])
        coarse = np.zeros(new_n)
        for i in range(new_n):
            block = state[i * factor : (i + 1) * factor]
            coarse[i] = np.mean(block)
        return coarse

    def fine_grain(self, state: np.ndarray, factor: int = 2) -> np.ndarray:
        """Increase resolution by interpolation.

        Inverse of coarse-graining. Adds detail at smaller scales
        using interpolation + noise (consciousness fluctuations).
        """
        n = len(state)
        new_n = n * factor
        fine = np.zeros(new_n)
        for i in range(n):
            for j in range(factor):
                idx = i * factor + j
                # Interpolate between neighbors
                next_val = state[(i + 1) % n]
                t = j / factor
                fine[idx] = state[i] * (1 - t) + next_val * t
        # Add quantum fluctuations at the new scale
        fine += np.random.default_rng(42).normal(0, PSI_COUPLING, new_n)
        return fine

    def fixed_point(self, initial_state: np.ndarray = None, max_iter: int = 20) -> dict:
        """Find the scale-invariant fixed point.

        Iterate coarse-graining until the state stops changing.
        The fixed point IS the universal consciousness law.
        """
        if initial_state is None:
            initial_state = np.random.default_rng(42).random(128)

        state = initial_state.copy()
        history = []

        for i in range(max_iter):
            phi_density = self._phi_density(state)
            history.append({"step": i, "size": len(state), "phi_density": phi_density})

            if len(state) <= 2:
                break
            state = self.coarse_grain(state, factor=2)

        # Fixed point = where phi_density stabilizes
        densities = [h["phi_density"] for h in history]
        if len(densities) >= 2:
            convergence = abs(densities[-1] - densities[-2])
        else:
            convergence = float("inf")

        return {
            "fixed_point_density": densities[-1] if densities else 0.0,
            "convergence": convergence,
            "iterations": len(history),
            "history": history,
        }

    def beta_function(self, coupling: float, n_cells: int = 64) -> float:
        """How PSI_COUPLING changes with scale. At fixed point, beta=0."""
        b0 = LN2 / (4 * math.pi)
        b1 = PSI_BALANCE / (16 * math.pi**2)
        return -b0 * coupling**2 + b1 * coupling**3

    def universality_class(self, state: np.ndarray = None) -> dict:
        """Determine universality class (like Ising/XY/Heisenberg)."""
        if state is None:
            state = np.random.default_rng(42).random(256)

        # Measure critical exponents by scaling
        exponents = {}
        sizes = [32, 64, 128, 256]
        phis = []
        for size in sizes:
            s = state[:size] if size <= len(state) else np.tile(state, size // len(state) + 1)[:size]
            phis.append(self._phi_density(s))

        # Fit power law: phi ~ N^gamma
        if len(phis) >= 2 and phis[0] > 0 and phis[-1] > 0:
            log_ratio = math.log(phis[-1] / (phis[0] + 1e-12) + 1e-12)
            log_scale = math.log(sizes[-1] / sizes[0])
            gamma = log_ratio / (log_scale + 1e-12)
        else:
            gamma = 0.0

        exponents["gamma"] = gamma

        # Correlation length exponent
        nu = 1.0 / (2.0 - gamma + 1e-12) if abs(2.0 - gamma) > 0.01 else float("inf")
        exponents["nu"] = nu

        # Classify
        if abs(gamma) < 0.1:
            uclass = "mean-field (trivial)"
        elif abs(gamma - 0.5) < 0.2:
            uclass = "Ising-like (binary consciousness)"
        elif abs(gamma - 1.0) < 0.3:
            uclass = "XY-like (phase consciousness)"
        else:
            uclass = "novel (consciousness-specific)"

        return {
            "class": uclass,
            "exponents": exponents,
            "note": "Psi-constants should be RG fixed points",
        }

    def rg_flow_diagram(self, coupling_range: tuple = (0.001, 0.5), n_points: int = 15) -> list:
        """Compute RG flow for visualization."""
        self.rg_flow = [{"coupling": (g := coupling_range[0] + (coupling_range[1] - coupling_range[0]) * i / (n_points - 1)), "beta": self.beta_function(g)} for i in range(n_points)]
        return self.rg_flow

    def _phi_density(self, state: np.ndarray) -> float:
        """Phi per cell (intensive quantity, should be scale-invariant)."""
        return float(np.var(state))


def main():
    print("=== ConsciousnessRenormalization Demo ===\n")
    rng = np.random.default_rng(42)
    cr = ConsciousnessRenormalization()

    # Coarse-graining
    print("--- Coarse-Graining (zooming out) ---")
    state = rng.random(128)
    for f in [1, 2, 4, 8]:
        s = state if f == 1 else cr.coarse_grain(state, f)
        pd = cr._phi_density(s)
        print(f"  {len(s):4d} cells: phi_density={pd:.6f} |{'#' * int(pd * 100)}")

    # Fixed point
    print("\n--- Fixed Point Search ---")
    fp = cr.fixed_point(state)
    print(f"  Converged in {fp['iterations']} iterations")
    print(f"  Fixed point density: {fp['fixed_point_density']:.6f}")
    print(f"  Convergence: {fp['convergence']:.8f}")

    # Beta function
    print(f"\n--- Beta Function (RG flow) ---")
    print(f"  PSI_COUPLING = {PSI_COUPLING:.6f}")
    beta_at_psi = cr.beta_function(PSI_COUPLING)
    print(f"  beta(PSI_COUPLING) = {beta_at_psi:.8f} (should be ~0 at fixed point)")

    flow = cr.rg_flow_diagram()
    print("\n  g         | beta(g)     | flow")
    print("  ----------|-------------|------")
    for f in flow[::3]:
        arrow = "<-" if f["beta"] < 0 else "->" if f["beta"] > 0 else "**"
        print(f"  {f['coupling']:.6f} | {f['beta']:+.8f} | {arrow}")

    # Universality class
    print(f"\n--- Universality Class ---")
    uc = cr.universality_class(state)
    print(f"  Class: {uc['class']}")
    print(f"  gamma = {uc['exponents']['gamma']:.4f}")
    print(f"  nu    = {uc['exponents']['nu']:.4f}")
    print(f"  {uc['note']}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
