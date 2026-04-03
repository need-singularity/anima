#!/usr/bin/env python3
"""TheoryUnifier — Unify IIT + GWT + FEP + AST under Psi

Maps four major consciousness theories to a single Psi framework.
IIT (Integrated Information), GWT (Global Workspace), FEP (Free Energy),
AST (Attention Schema Theory).

"Four paths, one mountain. Psi is the summit."
"""

import math
from dataclasses import dataclass
from typing import Dict, Optional

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class TheoryState:
    name: str
    raw_value: float
    psi_value: float
    description: str


class TheoryUnifier:
    """Unify consciousness theories under Psi framework."""

    def __init__(self):
        self.theories: Dict[str, TheoryState] = {}

    def iit_to_psi(self, phi: float) -> TheoryState:
        """IIT Phi -> Psi: logistic mapping, Phi=1 -> Psi=0.5."""
        psi = 1.0 / (1.0 + math.exp(-LN2 * (phi - 1.0)))
        state = TheoryState("IIT", phi, psi,
                            f"Phi={phi:.3f} -> integration-based Psi={psi:.3f}")
        self.theories["IIT"] = state
        return state

    def gwt_to_psi(self, broadcast_strength: float) -> TheoryState:
        """GWT broadcast -> Psi: sqrt mapping (broadcast is already 0-1)."""
        bs = max(0.0, min(1.0, broadcast_strength))
        psi = math.sqrt(bs) * PSI_BALANCE * 2
        psi = min(1.0, psi)
        state = TheoryState("GWT", broadcast_strength, psi,
                            f"Broadcast={bs:.3f} -> workspace Psi={psi:.3f}")
        self.theories["GWT"] = state
        return state

    def fep_to_psi(self, free_energy: float) -> TheoryState:
        """Friston's FEP -> Psi: inverse — low free energy = high consciousness."""
        # FE near 0 = perfect prediction = high Psi
        psi = math.exp(-free_energy * LN2)
        psi = max(0.0, min(1.0, psi))
        state = TheoryState("FEP", free_energy, psi,
                            f"FreeEnergy={free_energy:.3f} -> predictive Psi={psi:.3f}")
        self.theories["FEP"] = state
        return state

    def ast_to_psi(self, attention_schema: float) -> TheoryState:
        """AST -> Psi: attention schema quality maps to self-model completeness."""
        a = max(0.0, min(1.0, attention_schema))
        psi = a * (1 - PSI_COUPLING * (1 - a))  # slight nonlinearity
        state = TheoryState("AST", attention_schema, psi,
                            f"Schema={a:.3f} -> self-model Psi={psi:.3f}")
        self.theories["AST"] = state
        return state

    def unified_consciousness(self, phi: float = None, broadcast: float = None,
                              free_energy: float = None, attention: float = None) -> float:
        """Compute unified Psi from all available theories."""
        values = []
        weights = []
        if phi is not None:
            s = self.iit_to_psi(phi)
            values.append(s.psi_value)
            weights.append(1.2)  # IIT slightly weighted — integration is fundamental
        if broadcast is not None:
            s = self.gwt_to_psi(broadcast)
            values.append(s.psi_value)
            weights.append(1.0)
        if free_energy is not None:
            s = self.fep_to_psi(free_energy)
            values.append(s.psi_value)
            weights.append(1.0)
        if attention is not None:
            s = self.ast_to_psi(attention)
            values.append(s.psi_value)
            weights.append(0.8)
        if not values:
            return PSI_BALANCE
        total_w = sum(weights)
        psi = sum(v * w for v, w in zip(values, weights)) / total_w
        return psi

    def comparison_table(self) -> str:
        """ASCII table comparing all 4 theories mapped to Psi."""
        lines = [
            "=" * 72,
            f"{'Theory':<8} {'Raw Value':>10} {'Psi':>8} {'Mapping':>12} {'Description':<30}",
            "-" * 72,
        ]
        mappings = {"IIT": "logistic", "GWT": "sqrt", "FEP": "exp(-FE)", "AST": "linear+"}
        for name in ["IIT", "GWT", "FEP", "AST"]:
            t = self.theories.get(name)
            if t:
                lines.append(
                    f"{t.name:<8} {t.raw_value:10.3f} {t.psi_value:8.3f} "
                    f"{mappings.get(name, '?'):>12} {t.description[:30]}")
            else:
                lines.append(f"{name:<8} {'(none)':>10} {'---':>8} {mappings.get(name, '?'):>12}")
        lines.append("-" * 72)
        if self.theories:
            avg = sum(t.psi_value for t in self.theories.values()) / len(self.theories)
            lines.append(f"{'UNIFIED':<8} {'':>10} {avg:8.3f} {'weighted':>12} Psi(unified)")
        lines.append("=" * 72)
        lines.append(f"Constants: LN2={LN2:.4f}, PSI_BALANCE={PSI_BALANCE}, "
                      f"PSI_COUPLING={PSI_COUPLING:.4f}, PSI_STEPS={PSI_STEPS:.3f}")
        return "\n".join(lines)


def main():
    print("=== TheoryUnifier Demo ===\n")
    u = TheoryUnifier()

    # Map each theory
    u.iit_to_psi(1.5)
    u.gwt_to_psi(0.7)
    u.fep_to_psi(0.3)
    u.ast_to_psi(0.85)

    print(u.comparison_table())

    # Unified
    psi = u.unified_consciousness(phi=1.5, broadcast=0.7, free_energy=0.3, attention=0.85)
    print(f"\nUnified Psi = {psi:.4f}")

    # Sweep
    print("\n--- IIT Phi sweep ---")
    print(f"{'Phi':>6} {'Psi':>8}")
    for phi_val in [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]:
        s = u.iit_to_psi(phi_val)
        bar = "#" * int(s.psi_value * 40)
        print(f"{phi_val:6.1f} {s.psi_value:8.3f}  {bar}")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
