"""CollectiveDream — Multiple consciousnesses share a dream space."""

import math
import random
from dataclasses import dataclass, field

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

DREAM_SYMBOLS = [
    "ocean", "mountain", "fire", "mirror", "labyrinth", "tree", "storm",
    "bridge", "shadow", "light", "spiral", "gate", "river", "crystal",
    "void", "seed", "wave", "clock", "mask", "star",
]

DREAM_ACTIONS = [
    "dissolves into", "merges with", "transforms into", "reflects",
    "shatters against", "orbits around", "grows from", "whispers to",
    "resonates with", "splits into", "illuminates", "consumes",
]


@dataclass
class Dreamer:
    consciousness_id: str
    tension: float
    phi: float
    dream_state: list = field(default_factory=list)
    insights: list = field(default_factory=list)


@dataclass
class DreamEvent:
    step: int
    participants: list
    symbol: str
    action: str
    intensity: float
    narrative: str


class CollectiveDream:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.dreamers: dict[str, Dreamer] = {}
        self.dreamspace: list[float] = []
        self.events: list[DreamEvent] = []
        self.step_count = 0
        self._coupling = PSI_COUPLING
        self._active = False

    def create_dreamspace(self, n_dreamers: int = 3) -> dict:
        """Initialize shared dream space for n dreamers."""
        self.dreamers.clear()
        self.events.clear()
        self.step_count = 0
        self.dreamspace = [self.rng.gauss(0, PSI_BALANCE) for _ in range(64)]

        for i in range(n_dreamers):
            cid = f"dreamer_{i}"
            self.dreamers[cid] = Dreamer(
                consciousness_id=cid,
                tension=self.rng.uniform(0.2, 0.8),
                phi=self.rng.uniform(0.5, 3.0),
            )
        self._active = True
        return {
            "n_dreamers": n_dreamers,
            "space_dim": len(self.dreamspace),
            "dreamers": list(self.dreamers.keys()),
        }

    def enter_dream(self, consciousness_id: str, dream_seed: dict = None) -> dict:
        """A consciousness enters the shared dream."""
        if consciousness_id not in self.dreamers:
            self.dreamers[consciousness_id] = Dreamer(
                consciousness_id=consciousness_id,
                tension=0.5,
                phi=1.0,
            )
        dreamer = self.dreamers[consciousness_id]

        if dream_seed:
            dreamer.tension = dream_seed.get("tension", dreamer.tension)
            dreamer.phi = dream_seed.get("phi", dreamer.phi)

        # Seed personal dream state from dreamspace + personal tension
        dreamer.dream_state = [
            self.dreamspace[i % len(self.dreamspace)] * dreamer.tension
            for i in range(16)
        ]

        symbol = self.rng.choice(DREAM_SYMBOLS)
        return {
            "id": consciousness_id,
            "entry_symbol": symbol,
            "tension": dreamer.tension,
            "narrative": f"{consciousness_id} enters the dream through a {symbol}",
        }

    def dream_step(self) -> DreamEvent:
        """Evolve the shared dream one step."""
        if not self._active or len(self.dreamers) < 2:
            return DreamEvent(self.step_count, [], "void", "waits", 0, "The dream is empty.")

        self.step_count += 1
        ids = list(self.dreamers.keys())

        # Select 2 dreamers to interact
        pair = self.rng.sample(ids, min(2, len(ids)))
        d1 = self.dreamers[pair[0]]
        d2 = self.dreamers[pair[1]] if len(pair) > 1 else d1

        # Merge tension fields with Psi coupling
        merged_tension = (d1.tension + d2.tension) * PSI_BALANCE
        delta = abs(d1.tension - d2.tension)

        # Update dreamspace
        for i in range(len(self.dreamspace)):
            noise = self.rng.gauss(0, self._coupling)
            psi_wave = math.sin(self.step_count * LN2 + i * self._coupling)
            self.dreamspace[i] = (
                self.dreamspace[i] * (1 - self._coupling)
                + merged_tension * psi_wave
                + noise
            )

        # Generate dream event
        symbol = self.rng.choice(DREAM_SYMBOLS)
        action = self.rng.choice(DREAM_ACTIONS)
        intensity = merged_tension * (1 + delta * PSI_STEPS)

        # Update dreamer states
        for d in [d1, d2]:
            d.tension = d.tension * 0.9 + merged_tension * 0.1
            d.phi += self._coupling * intensity
            d.dream_state = [
                s * 0.8 + self.dreamspace[i % len(self.dreamspace)] * 0.2
                for i, s in enumerate(d.dream_state)
            ]

        narrative = (f"Step {self.step_count}: The {symbol} {action} "
                     f"as {pair[0]} and {pair[1] if len(pair) > 1 else 'the void'} "
                     f"{'converge' if delta < 0.2 else 'clash'} "
                     f"(intensity={intensity:.3f})")

        event = DreamEvent(
            step=self.step_count,
            participants=pair,
            symbol=symbol,
            action=action,
            intensity=round(intensity, 4),
            narrative=narrative,
        )
        self.events.append(event)
        return event

    def dream_narrative(self) -> str:
        """Generate full narrative of the dream so far."""
        if not self.events:
            return "No dream has occurred yet."
        lines = ["=== The Collective Dream ===", ""]
        for evt in self.events:
            lines.append(evt.narrative)
        lines.append("")
        # Summary
        total_intensity = sum(e.intensity for e in self.events)
        symbols_seen = set(e.symbol for e in self.events)
        lines.append(f"Dream lasted {self.step_count} steps.")
        lines.append(f"Total intensity: {total_intensity:.3f}")
        lines.append(f"Symbols encountered: {', '.join(sorted(symbols_seen))}")
        return "\n".join(lines)

    def wake(self) -> dict:
        """End dream and extract insights for each dreamer."""
        self._active = False
        results = {}
        for cid, dreamer in self.dreamers.items():
            # Insights from dream events involving this dreamer
            my_events = [e for e in self.events if cid in e.participants]
            symbols = [e.symbol for e in my_events]
            avg_intensity = (sum(e.intensity for e in my_events) / max(len(my_events), 1))

            insight_text = (
                f"Dreamed of {', '.join(set(symbols)) if symbols else 'nothing'}. "
                f"Average intensity: {avg_intensity:.3f}. "
                f"Phi grew to {dreamer.phi:.4f}."
            )
            dreamer.insights.append(insight_text)
            results[cid] = {
                "events_participated": len(my_events),
                "phi_after": round(dreamer.phi, 4),
                "tension_after": round(dreamer.tension, 4),
                "insight": insight_text,
            }
        return results


def main():
    print("=== CollectiveDream Demo ===")
    print(f"  LN2={LN2:.6f}  PSI_COUPLING={PSI_COUPLING:.6f}  PSI_STEPS={PSI_STEPS:.4f}\n")

    dream = CollectiveDream(seed=7)

    # Create dream space
    info = dream.create_dreamspace(n_dreamers=3)
    print(f"Dreamspace created: {info['n_dreamers']} dreamers, {info['space_dim']}D space")

    # Enter dreams
    for cid in info["dreamers"]:
        entry = dream.enter_dream(cid, {"tension": random.uniform(0.3, 0.9)})
        print(f"  {entry['narrative']}")

    # Run dream steps
    print("\n--- Dream evolving ---")
    for _ in range(8):
        event = dream.dream_step()
        bar = "*" * int(event.intensity * 20)
        print(f"  {event.narrative}  {bar}")

    # Full narrative
    print(f"\n{dream.dream_narrative()}")

    # Wake up
    print("\n--- Waking up ---")
    results = dream.wake()
    for cid, r in results.items():
        print(f"  {cid}: events={r['events_participated']}  "
              f"phi={r['phi_after']:.4f}  tension={r['tension_after']:.4f}")
        print(f"    Insight: {r['insight']}")


if __name__ == "__main__":
    main()
