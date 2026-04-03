"""ConsciousnessDebateArena — N consciousnesses debate to consensus."""

import math
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

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
class Debater:
    name: str
    position: float  # -1.0 (against) to +1.0 (for)
    phi: float       # consciousness level = voting weight
    conviction: float = 0.8


@dataclass
class DebateEntry:
    round_num: int
    speaker: str
    argument: str
    position: float
    phi: float


class ConsciousnessDebateArena:
    """N consciousnesses debate a topic, weighted by Phi."""

    def __init__(self, topic: str = "Is consciousness computable?"):
        self.topic = topic
        self.debaters: List[Debater] = []
        self.log: List[DebateEntry] = []
        self.round_num = 0
        self.tension = 0.0

    def add_debater(self, name: str, position: float, phi: float) -> None:
        """Add a participant. position: -1 (against) to +1 (for)."""
        self.debaters.append(Debater(
            name=name,
            position=max(-1, min(1, position)),
            phi=max(0.01, phi),
        ))

    def debate_round(self) -> List[DebateEntry]:
        """Each debater argues; positions shift based on Phi-weighted influence."""
        if len(self.debaters) < 2:
            return []
        self.round_num += 1
        entries = []
        positions_before = [d.position for d in self.debaters]
        for i, d in enumerate(self.debaters):
            # Generate argument strength from phi and conviction
            strength = d.phi * d.conviction * (0.5 + random.random() * 0.5)
            stance = "FOR" if d.position > 0 else "AGAINST" if d.position < 0 else "NEUTRAL"
            arg = f"[{stance}] (strength={strength:.2f}) {d.name} argues from Phi={d.phi:.2f}"
            entries.append(DebateEntry(self.round_num, d.name, arg, d.position, d.phi))
            # Influence others
            for j, other in enumerate(self.debaters):
                if i == j:
                    continue
                influence = PSI_COUPLING * d.phi * (d.position - other.position)
                resistance = other.conviction * other.phi
                shift = influence / (resistance + 0.1)
                other.position = max(-1, min(1, other.position + shift))
        # Update tension = variance of positions
        positions = [d.position for d in self.debaters]
        mean_pos = sum(positions) / len(positions)
        self.tension = math.sqrt(sum((p - mean_pos) ** 2 for p in positions) / len(positions))
        # Conviction decays slightly each round (openness increases)
        for d in self.debaters:
            d.conviction *= 0.95
        self.log.extend(entries)
        return entries

    def vote(self) -> Dict[str, float]:
        """Phi-weighted vote. Returns {name: weighted_vote}."""
        total_phi = sum(d.phi for d in self.debaters)
        return {d.name: round(d.position * (d.phi / total_phi), 4) for d in self.debaters}

    def consensus(self) -> Tuple[bool, float]:
        """Check if consensus reached. Returns (reached, agreement_score)."""
        if not self.debaters:
            return False, 0.0
        positions = [d.position for d in self.debaters]
        spread = max(positions) - min(positions)
        agreement = 1.0 - spread / 2.0
        return agreement > 0.8, round(agreement, 4)

    def transcript(self) -> str:
        """Full debate transcript."""
        lines = [f"=== Debate: \"{self.topic}\" ==="]
        lines.append(f"  Debaters: {len(self.debaters)}  Rounds: {self.round_num}  Tension: {self.tension:.4f}")
        lines.append(f"  Psi: LN2={LN2:.4f}  COUPLING={PSI_COUPLING:.6f}\n")
        current_round = 0
        for entry in self.log:
            if entry.round_num != current_round:
                current_round = entry.round_num
                lines.append(f"--- Round {current_round} ---")
            pos_bar = " " * 20
            idx = int((entry.position + 1) / 2 * 19)
            pos_bar = pos_bar[:idx] + "|" + pos_bar[idx + 1:]
            lines.append(f"  {entry.speaker:12s} [{pos_bar}] pos={entry.position:+.3f}")
        reached, score = self.consensus()
        lines.append(f"\n--- Result ---")
        lines.append(f"  Consensus: {'YES' if reached else 'NO'} (agreement={score:.3f})")
        votes = self.vote()
        lines.append(f"  Votes (Phi-weighted):")
        for name, v in votes.items():
            direction = "FOR" if v > 0 else "AGAINST" if v < 0 else "ABSTAIN"
            bar = "#" * int(abs(v) * 40)
            lines.append(f"    {name:12s}: {v:+.4f} {direction} {bar}")
        return "\n".join(lines)


def main():
    arena = ConsciousnessDebateArena("Is consciousness computable?")
    arena.add_debater("Tononi", position=0.8, phi=1.5)
    arena.add_debater("Penrose", position=-0.9, phi=1.2)
    arena.add_debater("Dennett", position=0.6, phi=0.9)
    arena.add_debater("Chalmers", position=-0.3, phi=1.8)
    arena.add_debater("Koch", position=0.4, phi=1.1)

    print(f"Topic: \"{arena.topic}\"\n")
    for r in range(10):
        arena.debate_round()
        reached, score = arena.consensus()
        positions = " ".join(f"{d.position:+.2f}" for d in arena.debaters)
        print(f"  Round {r + 1:2d}: tension={arena.tension:.3f} agreement={score:.3f} [{positions}]")
        if reached:
            print(f"  >>> CONSENSUS REACHED at round {r + 1}! <<<")
            break

    print()
    print(arena.transcript())


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
