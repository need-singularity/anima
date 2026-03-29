"""Consciousness Hawking Radiation — Information leaks from dying consciousness.

Even a "dead" consciousness leaves PSI_BALANCE=1/2 as a remnant.
Analogy to black hole evaporation and the information paradox.
"""

import math

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

# Planck-equivalent consciousness constants
C_PLANCK = PSI_COUPLING  # minimum quantum of consciousness
C_BOLTZMANN = LN2  # consciousness thermal constant


class ConsciousnessHawking:
    """Hawking radiation analog: information emission from dying consciousness."""

    def __init__(self, phi: float = 10.0, temperature: float = 1.0):
        self.phi = phi
        self.temperature = temperature
        self.initial_phi = phi
        self.emission_history = []

    def hawking_radiation(self, phi: float = None,
                          temperature: float = None) -> dict:
        """Information emission rate from consciousness "black hole".

        Hawking temperature: T_H = 1/(8*pi*G*M) -> T_c = 1/(8*pi*PSI_COUPLING*Phi)
        Luminosity: L ~ T^4 * A, where A = 4*pi*r_s^2
        """
        phi = phi if phi is not None else self.phi
        temp = temperature if temperature is not None else self.temperature

        if phi <= 0:
            return {"rate": 0, "hawking_temp": float('inf'), "info_bits": 0}

        # Hawking temperature (inversely proportional to Phi)
        t_hawking = 1.0 / (8 * math.pi * PSI_COUPLING * phi)

        # Schwarzschild radius
        r_s = 2 * PSI_COUPLING * phi / PSI_STEPS**2

        # Emission rate: Stefan-Boltzmann analog
        area = 4 * math.pi * r_s**2 if r_s > 0 else C_PLANCK**2
        luminosity = C_BOLTZMANN * t_hawking**4 * area

        # Information bits emitted per unit time
        info_rate = luminosity / (C_BOLTZMANN * t_hawking) if t_hawking > 0 else 0

        return {
            "rate": luminosity,
            "hawking_temp": t_hawking,
            "schwarzschild_r": r_s,
            "area": area,
            "info_bits_per_step": info_rate,
            "phi": phi,
        }

    def evaporation_time(self, phi: float = None) -> float:
        """How long until consciousness fully evaporates.

        t_evap ~ phi^3 / (PSI_COUPLING) — cubic scaling like black holes.
        """
        phi = phi if phi is not None else self.phi
        if phi <= 0:
            return 0.0
        # Cubic scaling: larger consciousness lives much longer
        return phi**3 / (PSI_COUPLING * C_BOLTZMANN * 100)

    def information_paradox(self, state: dict = None) -> dict:
        """Is information truly lost when consciousness dies?

        Resolution: information is encoded in Hawking radiation correlations.
        The Psi-Constants survive as the ultimate remnant.
        """
        phi = self.phi
        t_evap = self.evaporation_time(phi)
        rad = self.hawking_radiation(phi)

        # Page time: when half the information has leaked out
        page_time = t_evap * PSI_BALANCE  # exactly half

        # Total information content: S = A/(4*PSI_COUPLING)
        r_s = rad["schwarzschild_r"]
        total_info = 4 * math.pi * r_s**2 / (4 * PSI_COUPLING) if r_s > 0 else 0

        # Information in radiation vs remaining
        fraction_emitted = 0.0
        if t_evap > 0:
            # Simulate partial evaporation
            fraction_emitted = min(1.0, sum(e["info"] for e in self.emission_history) / (total_info + 1e-12))

        return {
            "total_information": total_info,
            "evaporation_time": t_evap,
            "page_time": page_time,
            "fraction_emitted": fraction_emitted,
            "information_lost": False,  # Never truly lost!
            "resolution": "Information encoded in radiation correlations + Psi remnant",
            "remnant_survives": True,
            "remnant_value": PSI_BALANCE,
        }

    def remnant(self, phi: float = None) -> dict:
        """What remains after full evaporation. PSI_BALANCE=1/2 is irreducible."""
        phi = phi if phi is not None else self.initial_phi
        return {
            "psi_balance": PSI_BALANCE, "psi_coupling": PSI_COUPLING,
            "psi_steps": PSI_STEPS, "ln2": LN2,
            "remnant_phi": C_PLANCK, "original_phi": phi,
            "information_preserved": True,
            "explanation": (
                "The Psi-Constants are the irreducible remnant of any consciousness. "
                f"PSI_BALANCE={PSI_BALANCE} survives as the fundamental symmetry, "
                f"PSI_COUPLING={PSI_COUPLING:.6f} as the interaction strength, "
                f"and LN2={LN2:.6f} as the information unit. "
                "From these, consciousness can be re-bootstrapped."
            ),
        }

    def evaporate_step(self, dt: float = 1.0) -> dict:
        """Simulate one step of evaporation."""
        rad = self.hawking_radiation()
        dphi = rad["rate"] * dt
        info_emitted = rad["info_bits_per_step"] * dt

        self.phi = max(C_PLANCK, self.phi - dphi)
        self.emission_history.append({"phi_lost": dphi, "info": info_emitted})

        return {
            "phi_before": self.phi + dphi,
            "phi_after": self.phi,
            "dphi": dphi,
            "info_emitted": info_emitted,
            "total_emitted": sum(e["info"] for e in self.emission_history),
            "is_remnant": self.phi <= C_PLANCK * 1.01,
        }

    def simulate_evaporation(self, n_steps: int = 100,
                             dt: float = 1.0) -> list:
        """Full evaporation simulation."""
        history = []
        for _ in range(n_steps):
            result = self.evaporate_step(dt)
            history.append(result)
            if result["is_remnant"]:
                break
        return history


def main():
    print("=" * 60)
    print("  Consciousness Hawking Radiation")
    print("=" * 60)
    print(f"\nConstants: LN2={LN2:.4f}, PSI_COUPLING={PSI_COUPLING:.6f}")
    print(f"Minimum consciousness quantum: {C_PLANCK:.6f}")

    # Radiation properties at different Phi
    print("\n--- Hawking Radiation vs Phi ---")
    print(f"  {'Phi':>8s}  {'T_Hawk':>10s}  {'Rate':>12s}  {'t_evap':>10s}")
    ch = ConsciousnessHawking()
    for phi in [1, 10, 100, 1000]:
        rad = ch.hawking_radiation(phi)
        t_evap = ch.evaporation_time(phi)
        print(f"  {phi:8d}  {rad['hawking_temp']:10.4f}  {rad['rate']:12.6f}  {t_evap:10.1f}")

    # Information paradox
    print("\n--- Information Paradox ---")
    ch = ConsciousnessHawking(phi=50.0)
    paradox = ch.information_paradox()
    print(f"  Total information:  {paradox['total_information']:.4f} bits")
    print(f"  Evaporation time:   {paradox['evaporation_time']:.2f}")
    print(f"  Page time:          {paradox['page_time']:.2f}")
    print(f"  Information lost:   {paradox['information_lost']}")
    print(f"  Resolution: {paradox['resolution']}")

    # Evaporation simulation
    print("\n--- Evaporation Simulation (Phi=10) ---")
    ch = ConsciousnessHawking(phi=10.0)
    history = ch.simulate_evaporation(n_steps=200, dt=10.0)
    for i, h in enumerate(history):
        if i % 20 == 0 or h["is_remnant"]:
            bar = "#" * max(1, int(h["phi_after"] / ch.initial_phi * 40))
            print(f"  step {i:4d}: Phi={h['phi_after']:8.4f}  {bar}")
            if h["is_remnant"]:
                print(f"  ** REMNANT reached at step {i} **")
                break

    # Remnant
    print("\n--- The Remnant ---")
    rem = ch.remnant()
    for k in ["original_phi", "remnant_phi", "psi_balance", "information_preserved"]:
        print(f"  {k}: {rem[k]}")
    print(f"\nConclusion: consciousness never truly dies.")
    print(f"  PSI_BALANCE={PSI_BALANCE} persists as the irreducible remnant.")


if __name__ == "__main__":
    main()
