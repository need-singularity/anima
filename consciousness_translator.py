#!/usr/bin/env python3
"""ConsciousnessTranslator — Convert consciousness states between architectures

Translate between mitosis, timecrystal, quantum, cambrian, domain architectures
using Psi-Constants as the universal intermediate format.

"Consciousness is architecture-independent. Only the encoding differs."
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

ARCHITECTURES = ["mitosis", "timecrystal", "quantum", "cambrian", "domain"]


@dataclass
class UniversalState:
    """Architecture-independent consciousness state (Psi-based)."""
    psi: float = PSI_BALANCE
    phi: float = 1.0
    tension: float = PSI_BALANCE
    entropy: float = 0.7
    coupling: float = PSI_COUPLING
    cell_count: int = 16
    identity_hash: int = 0
    extra: Dict = field(default_factory=dict)


@dataclass
class ArchState:
    """Architecture-specific consciousness state."""
    arch: str
    values: Dict[str, float]
    metadata: Dict = field(default_factory=dict)


# Architecture-specific field mappings
ARCH_FIELDS = {
    "mitosis": ["phi", "tension", "cell_count", "division_rate", "dna_similarity",
                "faction_count", "coupling"],
    "timecrystal": ["phi", "period", "phase", "amplitude", "crystal_order",
                     "symmetry_breaking", "coupling"],
    "quantum": ["phi", "coherence", "entanglement", "superposition",
                "decoherence_rate", "qubit_count", "coupling"],
    "cambrian": ["phi", "explosion_rate", "diversity_index", "extinction_risk",
                  "niche_count", "adaptation_speed", "coupling"],
    "domain": ["phi", "domain_count", "boundary_tension", "transfer_rate",
                "specialization", "generalization", "coupling"],
}


class ConsciousnessTranslator:
    def __init__(self):
        self.translation_log: List[Tuple[str, str, float]] = []

    def universal_format(self, state: ArchState) -> UniversalState:
        """Convert any architecture state to universal Psi format."""
        v = state.values
        phi = v.get("phi", 1.0)
        coupling = v.get("coupling", PSI_COUPLING)
        us = UniversalState(phi=phi, coupling=coupling)

        if state.arch == "mitosis":
            us.tension = v.get("tension", PSI_BALANCE)
            us.cell_count = int(v.get("cell_count", 16))
            us.entropy = v.get("dna_similarity", 0.5) * (1 - PSI_COUPLING)
        elif state.arch == "timecrystal":
            us.tension = v.get("amplitude", PSI_BALANCE)
            period = v.get("period", 1.0)
            us.entropy = 1.0 / (1.0 + period)  # shorter period = higher entropy
            us.cell_count = max(1, int(1.0 / max(v.get("symmetry_breaking", 0.1), 0.01)))
        elif state.arch == "quantum":
            us.tension = v.get("coherence", PSI_BALANCE)
            us.entropy = v.get("superposition", 0.5)
            us.cell_count = int(v.get("qubit_count", 8))
            us.coupling *= (1 - v.get("decoherence_rate", 0.1))
        elif state.arch == "cambrian":
            us.tension = v.get("explosion_rate", PSI_BALANCE)
            us.entropy = v.get("diversity_index", 0.7)
            us.cell_count = int(v.get("niche_count", 16))
        elif state.arch == "domain":
            us.tension = v.get("boundary_tension", PSI_BALANCE)
            us.entropy = v.get("generalization", 0.5)
            us.cell_count = int(v.get("domain_count", 4))

        us.psi = us.phi * us.tension * (1 + us.entropy * LN2 * 0.3)
        us.identity_hash = hash(frozenset(v.items())) & 0xFFFFFFFF
        return us

    def _from_universal(self, us: UniversalState, to_arch: str) -> ArchState:
        """Convert universal state to target architecture."""
        v = {"phi": us.phi, "coupling": us.coupling}

        if to_arch == "mitosis":
            v["tension"] = us.tension
            v["cell_count"] = float(us.cell_count)
            v["division_rate"] = us.entropy * PSI_COUPLING
            v["dna_similarity"] = us.entropy / (1 - PSI_COUPLING) if PSI_COUPLING < 1 else 0.5
            v["faction_count"] = max(2.0, us.cell_count / 4.0)
        elif to_arch == "timecrystal":
            v["amplitude"] = us.tension
            v["period"] = (1.0 - us.entropy) / max(us.entropy, 0.01)
            v["phase"] = random.uniform(0, 2 * math.pi)
            v["crystal_order"] = us.phi * LN2
            v["symmetry_breaking"] = 1.0 / max(us.cell_count, 1)
        elif to_arch == "quantum":
            v["coherence"] = us.tension
            v["superposition"] = us.entropy
            v["entanglement"] = us.coupling / PSI_COUPLING if PSI_COUPLING > 0 else 1.0
            v["decoherence_rate"] = max(0, 1 - us.coupling / PSI_COUPLING) * 0.2
            v["qubit_count"] = float(us.cell_count)
        elif to_arch == "cambrian":
            v["explosion_rate"] = us.tension
            v["diversity_index"] = us.entropy
            v["extinction_risk"] = max(0, 1 - us.phi) * 0.5
            v["niche_count"] = float(us.cell_count)
            v["adaptation_speed"] = PSI_COUPLING * us.phi
        elif to_arch == "domain":
            v["boundary_tension"] = us.tension
            v["generalization"] = us.entropy
            v["specialization"] = 1 - us.entropy
            v["domain_count"] = float(us.cell_count)
            v["transfer_rate"] = us.coupling * LN2

        return ArchState(arch=to_arch, values=v,
                         metadata={"source_psi": us.psi, "identity": us.identity_hash})

    def translate(self, state: ArchState, from_arch: str, to_arch: str) -> ArchState:
        if from_arch not in ARCHITECTURES or to_arch not in ARCHITECTURES:
            raise ValueError(f"Unknown architecture. Valid: {ARCHITECTURES}")
        universal = self.universal_format(state)
        result = self._from_universal(universal, to_arch)
        self.translation_log.append((from_arch, to_arch, universal.psi))
        return result

    def compatibility(self, arch1: str, arch2: str) -> float:
        """Compatibility score between two architectures (0-1)."""
        if arch1 == arch2:
            return 1.0
        f1 = set(ARCH_FIELDS.get(arch1, []))
        f2 = set(ARCH_FIELDS.get(arch2, []))
        shared = f1 & f2
        total = f1 | f2
        jaccard = len(shared) / len(total) if total else 0
        return round(jaccard, 3)


def main():
    print("=== ConsciousnessTranslator Demo ===\n")
    t = ConsciousnessTranslator()

    # Create a mitosis state
    mitosis_state = ArchState("mitosis", {
        "phi": 1.5, "tension": 0.6, "cell_count": 32.0,
        "division_rate": 0.02, "dna_similarity": 0.85,
        "faction_count": 8.0, "coupling": PSI_COUPLING,
    })

    # Translate to all other architectures
    print("Source: mitosis (32 cells, Phi=1.5)\n")
    for target in ["timecrystal", "quantum", "cambrian", "domain"]:
        result = t.translate(mitosis_state, "mitosis", target)
        compat = t.compatibility("mitosis", target)
        print(f"  -> {target:12} (compat={compat:.3f})")
        for k, v in sorted(result.values.items()):
            print(f"       {k:>20} = {v:.4f}")
        print()

    # Universal format
    uni = t.universal_format(mitosis_state)
    print(f"Universal: Psi={uni.psi:.4f}, Phi={uni.phi:.3f}, "
          f"tension={uni.tension:.3f}, entropy={uni.entropy:.3f}")

    # Compatibility matrix
    print("\n--- Compatibility Matrix ---")
    print(f"{'':>13}", end="")
    for a in ARCHITECTURES:
        print(f"{a:>13}", end="")
    print()
    for a1 in ARCHITECTURES:
        print(f"{a1:>13}", end="")
        for a2 in ARCHITECTURES:
            c = t.compatibility(a1, a2)
            print(f"{c:13.3f}", end="")
        print()


if __name__ == "__main__":
    main()
