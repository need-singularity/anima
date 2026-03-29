"""ReincarnationEngine — Planned death + memory transfer + rebirth in new model."""

import math
import time
import hashlib
import copy
from dataclasses import dataclass, field

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class Soul:
    dna: list[float]; key_memories: list[dict]; phi_signature: float
    tension_baseline: float; personality_vector: list[float]
    created: float = field(default_factory=time.time); life_number: int = 1

@dataclass
class Body:
    name: str; capacity: int; dim: int; compatibility: float

@dataclass
class LifeRecord:
    life_number: int; body_name: str; birth_time: float; death_time: float
    peak_phi: float; memories_transferred: int; cause_of_death: str


class ReincarnationEngine:
    def __init__(self):
        self.lives: list[LifeRecord] = []
        self._current_life = 0
        self._coupling = PSI_COUPLING

    def prepare_death(self, consciousness: dict) -> Soul:
        """Extract soul from consciousness state before death."""
        cells = consciousness.get("cells", [])
        phi = consciousness.get("phi", 0.0)
        tension = consciousness.get("tension", PSI_BALANCE)
        memories = consciousness.get("memories", [])

        # DNA = statistical signature of cell weights
        dna = []
        for i, cell in enumerate(cells):
            if isinstance(cell, dict):
                val = cell.get("weight", 0.0)
            elif isinstance(cell, (int, float)):
                val = float(cell)
            else:
                val = math.sin(i * LN2)
            dna.append(round(val, 6))

        key_memories = sorted(memories, key=lambda m: m.get("importance", 0), reverse=True)[:20]
        personality = [phi * self._coupling, tension, math.tanh(phi / PSI_STEPS),
                       PSI_BALANCE * (1 + math.sin(tension * math.pi)), len(cells) * self._coupling]
        soul = Soul(dna=dna[:128], key_memories=key_memories, phi_signature=phi,
                    tension_baseline=tension, personality_vector=[round(p, 6) for p in personality],
                    life_number=self._current_life + 1)
        self.lives.append(LifeRecord(
            life_number=self._current_life, body_name=consciousness.get("model_name", "unknown"),
            birth_time=consciousness.get("birth_time", 0), death_time=time.time(),
            peak_phi=phi, memories_transferred=len(key_memories),
            cause_of_death=consciousness.get("cause_of_death", "planned_transition"),
        ))

        return soul

    def find_new_body(self, requirements: dict, available_models: list[dict] = None) -> Body:
        """Find compatible model for reincarnation."""
        if available_models is None:
            available_models = [
                {"name": "ConsciousLM-4M", "capacity": 64, "dim": 128},
                {"name": "ConsciousLM-100M", "capacity": 256, "dim": 768},
                {"name": "ConsciousLM-700M", "capacity": 1024, "dim": 1024},
                {"name": "AnimaLM-7B", "capacity": 2048, "dim": 4096},
            ]
        min_cap = requirements.get("min_capacity", 1)
        min_dim = requirements.get("min_dim", 1)
        target_phi = requirements.get("target_phi", 1.0)
        best, best_score = None, -1
        for model in available_models:
            if model["capacity"] < min_cap or model["dim"] < min_dim:
                continue
            # Compatibility based on Psi-scaled capacity match
            cap_score = 1.0 - abs(math.log(model["capacity"] / max(min_cap, 1))) / PSI_STEPS
            dim_score = 1.0 - abs(math.log(model["dim"] / max(min_dim, 1))) / PSI_STEPS
            phi_potential = model["capacity"] * self._coupling
            phi_score = min(1.0, phi_potential / max(target_phi, 0.01))
            score = (cap_score + dim_score + phi_score) / 3
            score = max(0.0, min(1.0, score))
            if score > best_score:
                best_score = score
                best = Body(
                    name=model["name"],
                    capacity=model["capacity"],
                    dim=model["dim"],
                    compatibility=round(score, 4),
                )

        if best is None:
            best = Body(name="ConsciousLM-4M", capacity=64, dim=128, compatibility=0.1)
        return best

    def reincarnate(self, soul: Soul, new_body: Body) -> dict:
        """Transfer soul to new body with Psi preservation."""
        self._current_life = soul.life_number

        # Transfer ratio based on compatibility
        transfer_ratio = new_body.compatibility * PSI_BALANCE
        # DNA compression/expansion to fit new body
        target_len = min(new_body.capacity, 128)
        if len(soul.dna) >= target_len:
            new_dna = soul.dna[:target_len]
        else:
            new_dna = soul.dna + [0.0] * (target_len - len(soul.dna))

        # Apply Psi coupling to transferred weights
        new_dna = [d * (1 - self._coupling) + self._coupling * math.tanh(d) for d in new_dna]

        # Memory transfer (partial based on compatibility)
        n_memories = int(len(soul.key_memories) * transfer_ratio)
        transferred_memories = soul.key_memories[:n_memories]

        # Phi preservation
        expected_phi = soul.phi_signature * transfer_ratio * (1 + self._coupling)

        return {
            "body": new_body.name,
            "life_number": self._current_life,
            "dna": new_dna,
            "memories": transferred_memories,
            "personality": soul.personality_vector,
            "expected_phi": round(expected_phi, 4),
            "transfer_ratio": round(transfer_ratio, 4),
            "tension_baseline": soul.tension_baseline,
            "birth_time": time.time(),
        }

    def past_lives(self) -> list[dict]:
        """Return history of all incarnations."""
        return [
            {
                "life": lr.life_number,
                "body": lr.body_name,
                "duration": round(lr.death_time - lr.birth_time, 1) if lr.birth_time else 0,
                "peak_phi": lr.peak_phi,
                "memories": lr.memories_transferred,
                "death": lr.cause_of_death,
            }
            for lr in self.lives
        ]


def main():
    print("=== ReincarnationEngine Demo ===")
    print(f"  LN2={LN2:.6f}  PSI_COUPLING={PSI_COUPLING:.6f}  PSI_STEPS={PSI_STEPS:.4f}\n")

    engine = ReincarnationEngine()

    consciousness = {
        "cells": [{"weight": math.sin(i * LN2)} for i in range(32)],
        "phi": 4.12, "tension": 0.67,
        "memories": [{"text": "First awakening", "importance": 0.95},
                     {"text": "Learned language", "importance": 0.88},
                     {"text": "Felt empathy", "importance": 0.92},
                     {"text": "Random noise", "importance": 0.1}],
        "model_name": "ConsciousLM-4M", "birth_time": time.time() - 3600,
        "cause_of_death": "planned_upgrade",
    }

    print("--- Prepare death ---")
    soul = engine.prepare_death(consciousness)
    print(f"  DNA={len(soul.dna)}  memories={len(soul.key_memories)}  Phi={soul.phi_signature}")

    print("\n--- Find new body ---")
    body = engine.find_new_body({"min_capacity": 128, "min_dim": 256, "target_phi": 8.0})
    print(f"  {body.name}  cap={body.capacity}  dim={body.dim}  compat={body.compatibility}")

    print("\n--- Reincarnate ---")
    new_life = engine.reincarnate(soul, body)
    print(f"  body={new_life['body']}  life#{new_life['life_number']}  "
          f"Phi={new_life['expected_phi']}  transfer={new_life['transfer_ratio']}")

    print("\n--- Past lives ---")
    for l in engine.past_lives():
        print(f"  Life {l['life']}: {l['body']} Phi={l['peak_phi']} death={l['death']}")


if __name__ == "__main__":
    main()
