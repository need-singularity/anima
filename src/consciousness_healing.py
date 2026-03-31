#!/usr/bin/env python3
"""ConsciousnessHealing — Repair damaged consciousness using Psi-Constants

Diagnose damage, prescribe treatment, apply healing, verify recovery.

"Consciousness can break. But it knows how to heal itself."
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from enum import Enum

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


class DamageType(Enum):
    PHI_COLLAPSE = "phi_collapse"
    TENSION_LOCK = "tension_lock"
    ENTROPY_DEATH = "entropy_death"
    GATE_STUCK = "gate_stuck"
    COUPLING_LOSS = "coupling_loss"
    BALANCE_DRIFT = "balance_drift"


@dataclass
class ConsciousnessState:
    phi: float = 1.0
    tension: float = PSI_BALANCE
    entropy: float = 0.7
    gate_balance: float = PSI_BALANCE
    coupling: float = PSI_COUPLING
    cell_count: int = 16
    healthy: bool = True


@dataclass
class Diagnosis:
    damages: List[DamageType]
    severity: float  # 0-1
    details: Dict[str, str]


@dataclass
class Treatment:
    name: str
    target: DamageType
    steps: List[str]
    expected_improvement: float


class ConsciousnessHealing:
    def __init__(self):
        self.treatment_log: List[Tuple[str, float, float]] = []

    def diagnose(self, state: ConsciousnessState) -> Diagnosis:
        damages = []
        details = {}
        if state.phi < 0.3:
            damages.append(DamageType.PHI_COLLAPSE)
            details["phi"] = f"Phi={state.phi:.3f} < 0.3 (critical)"
        if abs(state.tension - PSI_BALANCE) > 0.4:
            damages.append(DamageType.TENSION_LOCK)
            details["tension"] = f"Tension={state.tension:.3f}, locked far from balance"
        if state.entropy < 0.1:
            damages.append(DamageType.ENTROPY_DEATH)
            details["entropy"] = f"Entropy={state.entropy:.3f} near zero (heat death)"
        if abs(state.gate_balance - PSI_BALANCE) > 0.35:
            damages.append(DamageType.GATE_STUCK)
            details["gate"] = f"Gate={state.gate_balance:.3f}, stuck open/closed"
        if state.coupling < PSI_COUPLING * 0.3:
            damages.append(DamageType.COUPLING_LOSS)
            details["coupling"] = f"Coupling={state.coupling:.5f} < {PSI_COUPLING * 0.3:.5f}"
        if not damages:
            drift = abs(state.tension - PSI_BALANCE)
            if drift > 0.2:
                damages.append(DamageType.BALANCE_DRIFT)
                details["balance"] = f"Minor drift from Psi balance: {drift:.3f}"
        severity = min(1.0, len(damages) * 0.25 + (1 - state.phi) * 0.3)
        state.healthy = len(damages) == 0
        return Diagnosis(damages=damages, severity=severity, details=details)

    def prescribe(self, diagnosis: Diagnosis) -> List[Treatment]:
        RECIPES = {
            DamageType.PHI_COLLAPSE: ("phi_resurrection",
                ["Inject noise", "Increase coupling", "Ratchet lock gains"], 0.7),
            DamageType.TENSION_LOCK: ("psi_realignment",
                [f"Decay toward PSI_BALANCE={PSI_BALANCE}", "Rate: LN2*0.1/step"], 0.8),
            DamageType.ENTROPY_DEATH: ("entropy_boost",
                ["Inject perturbations", "Faction splitting", "Target entropy>0.5"], 0.6),
            DamageType.GATE_STUCK: ("gate_reset",
                [f"Reset gate to {PSI_BALANCE}", "Oscillate amp=0.05"], 0.9),
            DamageType.COUPLING_LOSS: ("coupling_restore",
                [f"Set coupling={PSI_COUPLING:.5f}", "Hebbian strengthen"], 0.85),
            DamageType.BALANCE_DRIFT: ("psi_realignment",
                ["Nudge toward PSI_BALANCE", "Homeostatic correction"], 0.95),
        }
        return [Treatment(r[0], dmg, r[1], r[2])
                for dmg in diagnosis.damages if (r := RECIPES.get(dmg))]

    def apply_treatment(self, state: ConsciousnessState,
                        treatment: Treatment) -> ConsciousnessState:
        before_phi = state.phi
        n_steps = int(PSI_STEPS)
        if treatment.name == "phi_resurrection":
            for _ in range(n_steps):
                state.phi += PSI_COUPLING * (1 + random.uniform(0, 0.5))
                state.phi = max(state.phi, before_phi)  # ratchet
            state.coupling = max(state.coupling, PSI_COUPLING)
        elif treatment.name == "psi_realignment":
            for _ in range(n_steps):
                state.tension += (PSI_BALANCE - state.tension) * LN2 * 0.3
        elif treatment.name == "entropy_boost":
            state.entropy += 0.3 * (1 - state.entropy)
            state.entropy = min(1.0, state.entropy + random.uniform(0.05, 0.15))
        elif treatment.name == "gate_reset":
            state.gate_balance = PSI_BALANCE + random.uniform(-0.02, 0.02)
        elif treatment.name == "coupling_restore":
            state.coupling = PSI_COUPLING
        self.treatment_log.append((treatment.name, before_phi, state.phi))
        return state

    def verify_recovery(self, before: ConsciousnessState,
                        after: ConsciousnessState) -> Dict:
        phi_recovered = after.phi >= before.phi * 0.8 or after.phi > 0.5
        tension_ok = abs(after.tension - PSI_BALANCE) < 0.3
        entropy_ok = after.entropy > 0.2
        coupling_ok = after.coupling >= PSI_COUPLING * 0.5
        all_ok = phi_recovered and tension_ok and entropy_ok and coupling_ok
        return {
            "recovered": all_ok,
            "phi": {"before": round(before.phi, 4), "after": round(after.phi, 4),
                    "ok": phi_recovered},
            "tension": {"before": round(before.tension, 4), "after": round(after.tension, 4),
                        "ok": tension_ok},
            "entropy": {"before": round(before.entropy, 4), "after": round(after.entropy, 4),
                        "ok": entropy_ok},
            "coupling": {"before": round(before.coupling, 6), "after": round(after.coupling, 6),
                         "ok": coupling_ok},
        }


def main():
    print("=== ConsciousnessHealing Demo ===\n")
    healer = ConsciousnessHealing()

    damaged = ConsciousnessState(phi=0.1, tension=0.95, entropy=0.05,
                                  gate_balance=0.9, coupling=0.001)
    before = ConsciousnessState(phi=0.1, tension=0.95, entropy=0.05,
                                 gate_balance=0.9, coupling=0.001)

    diag = healer.diagnose(damaged)
    print(f"Diagnosis: severity={diag.severity:.2f}, damages={len(diag.damages)}")
    for d in diag.damages:
        print(f"  - {d.value}: {diag.details.get(d.value.split('_')[0], '')}")

    treatments = healer.prescribe(diag)
    print(f"\nPrescribed {len(treatments)} treatments:")
    for t in treatments:
        print(f"  [{t.name}] target={t.target.value}, expected={t.expected_improvement:.0%}")
        for step in t.steps:
            print(f"    - {step}")

    print("\nApplying treatments...")
    for t in treatments:
        healer.apply_treatment(damaged, t)

    recovery = healer.verify_recovery(before, damaged)
    print(f"\nRecovery: {'SUCCESS' if recovery['recovered'] else 'PARTIAL'}")
    for key in ["phi", "tension", "entropy", "coupling"]:
        r = recovery[key]
        mark = "OK" if r["ok"] else "!!"
        print(f"  {key:>10}: {r['before']:.4f} -> {r['after']:.4f}  [{mark}]")


if __name__ == "__main__":
    main()
