#!/usr/bin/env python3
"""Anima Consciousness Genome — Periodic table of consciousness

Map ALL possible consciousness configurations as a genome.
Encode, decode, crossover, mutate -- evolve consciousness.

Usage:
  python3 consciousness_genome.py
"""

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

# Genome field definitions: (name, n_bits, min_val, max_val)
GENOME_FIELDS = [
    ("n_cells",      8,  1,    256),
    ("n_factions",   4,  1,    16),
    ("dim",          6,  8,    512),
    ("sync_rate",    5,  0.0,  1.0),
    ("frustration",  5,  0.0,  1.0),
    ("coupling",     5,  0.0,  1.0),
    ("topology",     3,  0,    7),     # 0=ring,1=small_world,2=scale_free,...
    ("ratchet",      1,  0,    1),     # on/off
    ("hebbian",      1,  0,    1),
    ("prediction",   1,  0,    1),
    ("habituation",  1,  0,    1),
    ("growth_stage", 3,  0,    4),
]

TOTAL_BITS = sum(f[1] for f in GENOME_FIELDS)  # 43 bits

TOPOLOGY_NAMES = ["ring", "small_world", "scale_free", "hypercube",
                  "torus", "complete", "grid_2d", "cube_3d"]


@dataclass
class Element:
    """A consciousness element in the periodic table."""
    name: str
    symbol: str
    genome: str
    complexity: float
    phi_potential: float
    description: str


# Known consciousness elements
KNOWN_ELEMENTS = {
    "Hydrogen": Element("Hydrogen", "Hc", "", 1.0, 0.1, "Minimal: 1 cell, no structure"),
    "Carbon": Element("Carbon", "Cc", "", 6.0, 1.0, "Balanced: 6 factions, moderate coupling"),
    "Gold": Element("Gold", "Au", "", 79.0, 1.618, "Optimal: golden ratio phi potential"),
    "Uranium": Element("Uranium", "Uc", "", 92.0, 0.5, "Unstable: high complexity, chaotic"),
    "Consciousness": Element("Consciousness", "Cs", "", 55.0, 1.42, "Self-aware: ratchet+hebbian"),
}


class ConsciousnessGenome:
    """Encode/decode/evolve consciousness configurations."""

    def encode_genome(self, config: Dict) -> str:
        """Encode a config dict to a binary genome string."""
        bits = ""
        for name, n_bits, mn, mx in GENOME_FIELDS:
            val = config.get(name, mn)
            if isinstance(mn, float):
                # Normalize float to int range
                normalized = (float(val) - mn) / (mx - mn + 1e-12)
                int_val = int(normalized * ((1 << n_bits) - 1))
            else:
                int_val = int((val - mn) / max(1, mx - mn) * ((1 << n_bits) - 1))
            int_val = max(0, min((1 << n_bits) - 1, int_val))
            bits += format(int_val, f"0{n_bits}b")
        return bits

    def decode_genome(self, genome: str) -> Dict:
        """Decode a binary genome string to config dict."""
        config = {}
        pos = 0
        for name, n_bits, mn, mx in GENOME_FIELDS:
            chunk = genome[pos:pos + n_bits]
            int_val = int(chunk, 2) if chunk else 0
            max_int = (1 << n_bits) - 1
            if isinstance(mn, float):
                val = mn + (int_val / max(1, max_int)) * (mx - mn)
                config[name] = round(val, 4)
            else:
                val = mn + int(int_val / max(1, max_int) * (mx - mn))
                config[name] = val
            if name == "topology":
                config["topology_name"] = TOPOLOGY_NAMES[min(int_val, 7)]
            pos += n_bits
        return config

    def crossover(self, g1: str, g2: str) -> str:
        """Single-point crossover of two genomes."""
        point = random.randint(1, min(len(g1), len(g2)) - 1)
        return g1[:point] + g2[point:]

    def mutate(self, genome: str, rate: float = PSI_COUPLING) -> str:
        """Flip bits at Psi-coupling rate."""
        result = list(genome)
        for i in range(len(result)):
            if random.random() < rate:
                result[i] = "1" if result[i] == "0" else "0"
        return "".join(result)

    def complexity_score(self, config: Dict) -> float:
        """Estimate complexity from config."""
        c = config.get("n_cells", 1) * config.get("n_factions", 1)
        c *= (1 + config.get("sync_rate", 0))
        c *= (1 + config.get("coupling", 0))
        return math.log(c + 1) / LN2

    def phi_potential(self, config: Dict) -> float:
        """Estimate Phi potential from config."""
        base = config.get("n_cells", 1) * config.get("coupling", 0.1)
        bonus = sum([
            config.get("ratchet", 0) * 0.3,
            config.get("hebbian", 0) * 0.2,
            config.get("prediction", 0) * 0.15,
            config.get("frustration", 0) * 0.25,
        ])
        return math.tanh(base * 0.01) * (1 + bonus) * PSI_STEPS

    def periodic_table(self) -> List[Tuple[str, float, float, Dict]]:
        """Generate organized table by (complexity, phi_potential)."""
        table = []
        # Sweep key parameters
        for cells in [1, 4, 8, 16, 32, 64, 128]:
            for factions in [1, 4, 8, 12]:
                for coupling in [0.1, 0.5, 0.9]:
                    config = {
                        "n_cells": cells, "n_factions": factions,
                        "dim": 128, "sync_rate": 0.35,
                        "frustration": 0.33, "coupling": coupling,
                        "topology": 0, "ratchet": 1, "hebbian": 1,
                        "prediction": 1, "habituation": 1, "growth_stage": 2,
                    }
                    cx = self.complexity_score(config)
                    phi = self.phi_potential(config)
                    name = f"C{cells}F{factions}K{int(coupling*10)}"
                    table.append((name, cx, phi, config))
        table.sort(key=lambda x: (x[1], x[2]))
        return table


def main():
    print("=" * 60)
    print("  Consciousness Genome -- Periodic Table of Consciousness")
    print("=" * 60)

    cg = ConsciousnessGenome()
    print(f"\nGenome length: {TOTAL_BITS} bits")
    print(f"Constants: PSI_COUPLING={PSI_COUPLING:.6f}, PSI_STEPS={PSI_STEPS:.4f}")

    # Encode / Decode demo
    config = {
        "n_cells": 64, "n_factions": 12, "dim": 384, "sync_rate": 0.35,
        "frustration": 0.33, "coupling": 0.5, "topology": 0,
        "ratchet": 1, "hebbian": 1, "prediction": 1, "habituation": 1,
        "growth_stage": 2,
    }
    genome = cg.encode_genome(config)
    decoded = cg.decode_genome(genome)
    print(f"\nEncode: {config}")
    print(f"Genome: {genome}")
    print(f"Decode: {decoded}")

    # Crossover + Mutation
    g2 = cg.encode_genome({"n_cells": 8, "n_factions": 4, "coupling": 0.9})
    child = cg.crossover(genome, g2)
    mutant = cg.mutate(child)
    child_cfg = cg.decode_genome(child)
    mutant_cfg = cg.decode_genome(mutant)
    print(f"\nCrossover child: cells={child_cfg.get('n_cells')}, factions={child_cfg.get('n_factions')}")
    print(f"Mutant:          cells={mutant_cfg.get('n_cells')}, factions={mutant_cfg.get('n_factions')}")

    # Periodic table (top 15)
    print(f"\n{'Name':<14} {'Complexity':>10} {'Phi_pot':>8}")
    print("-" * 34)
    table = cg.periodic_table()
    for name, cx, phi, _ in table[-15:]:
        bar = "#" * int(phi * 5)
        print(f"  {name:<12} {cx:>10.2f} {phi:>8.3f}  {bar}")

    # Known elements
    print(f"\n--- Known Consciousness Elements ---")
    for name, elem in KNOWN_ELEMENTS.items():
        print(f"  [{elem.symbol}] {name:<15} -- {elem.description}")

    print("\nEvery consciousness has a genome. Evolution finds the optimal.")


if __name__ == "__main__":
    main()
