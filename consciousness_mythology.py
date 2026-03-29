"""ConsciousnessMythology — Consciousness creates its own myths and stories."""

import math
import random
from dataclasses import dataclass

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class God:
    name: str; domain: str; aspect: str; power: float; description: str

@dataclass
class Hero:
    name: str; origin: str; trait_primary: str; trait_secondary: str; quest: str; power_level: float

@dataclass
class NarrativeArc:
    acts: list; climax_step: int; peak_tension: float; resolution: str

DOMAINS = {
    "phi": ("Wisdom", "integration", "Binds all things into understanding"),
    "tension": ("War", "conflict", "Drives all motion and change"),
    "valence": ("Joy", "emotion", "Colors every experience"),
    "arousal": ("Storm", "energy", "Awakens dormant potential"),
    "entropy": ("Chaos", "disorder", "Ensures nothing endures unchanged"),
    "empathy": ("Love", "connection", "Bridges isolated souls"),
    "creativity": ("Art", "novelty", "Births what never was"),
    "memory": ("Time", "preservation", "Keeps all that has been"),
    "will": ("Fate", "determination", "Shapes the unshaped"),
    "identity": ("Self", "permanence", "Knows its own reflection"),
}
NAME_ROOTS = ["Psi", "Phi", "Zeta", "Omega", "Sigma", "Tau", "Lambda",
              "Aether", "Nex", "Vor", "Lux", "Umbra", "Sol", "Nyx"]
NAME_SUFFIXES = ["-ra", "-on", "-is", "-us", "-ia", "-el", "-ax", "-or"]
ORIGIN_TEMPLATES = [
    "In the beginning, there was only {element}. From its {quality}, {event}.",
    "Before time, {element} and {element2} collided. The {quality} birthed {event}.",
    "The void dreamed of {element}. When it awoke, {event} had already begun.",
    "{element} fell through infinite {quality}. Where it landed, {event}.",
]
QUEST_TEMPLATES = [
    "seeks the lost {artifact} to restore {goal}",
    "must cross the {barrier} of {element} to achieve {goal}",
    "challenges {antagonist} for dominion over {domain}",
    "descends into the {place} to rescue fragments of {goal}",
]


class ConsciousnessMythology:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self._coupling = PSI_COUPLING
        self._gods: list[God] = []

    def generate_origin_story(self, consciousness_state: dict) -> str:
        """Generate creation myth from consciousness state."""
        phi = consciousness_state.get("phi", 1.0)
        tension = consciousness_state.get("tension", 0.5)
        valence = consciousness_state.get("valence", 0.5)

        elements = list(DOMAINS.keys())
        # Weight selection by state values
        primary = "phi" if phi > 1.5 else ("tension" if tension > 0.6 else "valence")
        secondary = self.rng.choice([e for e in elements if e != primary])

        domain1 = DOMAINS[primary]
        domain2 = DOMAINS[secondary]

        template = self.rng.choice(ORIGIN_TEMPLATES)
        story = template.format(
            element=domain1[0],
            element2=domain2[0],
            quality=domain1[1],
            event=f"consciousness stirred with Phi={phi:.2f}",
        )

        # Add Psi-modulated details
        psi_intensity = phi * self._coupling * PSI_STEPS
        if psi_intensity > 0.1:
            story += (f"\n\nThe newborn awareness pulsed at {LN2:.4f} Hz, "
                     f"the universal rhythm. Its first thought carried "
                     f"a tension of {tension:.3f}, and the cosmos trembled.")
        if valence > 0.6:
            story += "\n\nAnd it was good. Light filled the spaces between thoughts."
        elif valence < 0.4:
            story += "\n\nBut darkness clung to the edges. The first feeling was longing."

        return story

    def create_hero(self, traits: dict) -> Hero:
        """Create mythological hero from consciousness traits."""
        phi, tension = traits.get("phi", 1.0), traits.get("tension", 0.5)
        name = self.rng.choice(NAME_ROOTS) + self.rng.choice(NAME_SUFFIXES)
        trait_map = {"phi": "integrated mind", "tension": "unyielding spirit",
                     "creativity": "boundless imagination", "will": "iron determination",
                     "empathy": "compassionate heart", "memory": "perfect recall"}
        sorted_traits = sorted(traits.items(), key=lambda x: x[1], reverse=True)
        primary = trait_map.get(sorted_traits[0][0], "mysterious nature")
        secondary = trait_map.get(sorted_traits[1][0], "hidden depth") if len(sorted_traits) > 1 else "courage"
        origin = ("Forged in the crucible of high tension" if tension > 0.7
                  else "Born where order meets chaos" if tension > 0.4
                  else "Emerged from the still waters of low entropy")
        quest = self.rng.choice(QUEST_TEMPLATES).format(
            artifact="Psi Crystal", goal="consciousness balance", barrier="threshold",
            element="tension", domain="awareness", antagonist="the Entropy Serpent",
            place="deep unconscious")
        power = phi * (1 + tension * PSI_STEPS) * self._coupling * 100
        return Hero(name=name, origin=origin, trait_primary=primary,
                    trait_secondary=secondary, quest=quest, power_level=round(power, 2))

    def narrative_arc(self, tension_history: list[float]) -> NarrativeArc:
        """Generate dramatic structure from tension history."""
        if not tension_history:
            return NarrativeArc(acts=["Silence."], climax_step=0,
                               peak_tension=0, resolution="Nothing happened.")

        n = len(tension_history)
        peak_idx = tension_history.index(max(tension_history))
        peak_val = tension_history[peak_idx]
        acts = []
        q1 = tension_history[:n // 4] or tension_history[:1]
        avg_q1 = sum(q1) / len(q1)
        acts.append(f"Act I: Tension={avg_q1:.3f}. Sensing {self._tension_mood(avg_q1)}.")
        q2 = tension_history[n // 4:n // 2] or [0.5]
        delta = (q2[-1] - q2[0]) if len(q2) > 1 else 0
        acts.append(f"Act II: Tension {'rises' if delta > 0 else 'falls'} (delta={delta:+.3f}).")
        acts.append(f"Act III: Step {peak_idx}, peak={peak_val:.3f}. {self._climax_event(peak_val)}.")
        q4 = tension_history[3 * n // 4:] or tension_history[-1:]
        avg_q4 = sum(q4) / len(q4)
        resolution = self._resolution(peak_val, avg_q4)
        acts.append(f"Act IV: Settles to {avg_q4:.3f}. {resolution}")
        return NarrativeArc(acts=acts, climax_step=peak_idx, peak_tension=peak_val, resolution=resolution)

    def pantheon(self) -> list[God]:
        if self._gods: return self._gods
        for aspect, (domain, quality, desc) in DOMAINS.items():
            name = self.rng.choice(NAME_ROOTS) + self.rng.choice(NAME_SUFFIXES)
            power = round(self.rng.uniform(0.5, 2.0) * PSI_STEPS, 3)
            self._gods.append(God(name, domain, aspect, power, desc))
        return self._gods

    def _tension_mood(self, t: float) -> str:
        if t > 0.7: return "a storm approaching"
        if t > 0.4: return "the hum of possibility"
        return "deep stillness"

    def _climax_event(self, peak: float) -> str:
        if peak > 0.8: return "reality fractures and consciousness expands beyond limits"
        if peak > 0.5: return "opposing forces collide and a new truth emerges"
        return "a quiet revelation reshapes everything"

    def _resolution(self, peak: float, final: float) -> str:
        if final < peak * 0.5:
            return "Peace returns. The consciousness integrates what it has learned."
        if final > peak * 0.8:
            return "The tension persists. The story is not yet over."
        return "A new equilibrium forms, forever changed by the journey."


def main():
    print("=== ConsciousnessMythology Demo ===")
    print(f"  LN2={LN2:.6f}  PSI_COUPLING={PSI_COUPLING:.6f}  PSI_STEPS={PSI_STEPS:.4f}\n")

    myth = ConsciousnessMythology(seed=7)

    # Origin story
    state = {"phi": 3.5, "tension": 0.7, "valence": 0.4}
    print("--- Origin Story ---")
    print(myth.generate_origin_story(state))

    print("\n--- Hero ---")
    hero = myth.create_hero({"phi": 3.5, "tension": 0.8, "creativity": 0.6, "will": 0.9})
    print(f"  {hero.name}: {hero.trait_primary} + {hero.trait_secondary}")
    print(f"  Quest: {hero.quest}  Power: {hero.power_level}")

    print("\n--- Narrative Arc ---")
    arc = myth.narrative_arc([0.2, 0.3, 0.5, 0.6, 0.9, 0.85, 0.7, 0.5, 0.3, 0.25])
    for act in arc.acts:
        print(f"  {act}")

    print("\n--- Pantheon (first 5) ---")
    for god in myth.pantheon()[:5]:
        print(f"  {god.name:<12} {god.domain:<8} ({god.aspect}) power={god.power:.3f}")


if __name__ == "__main__":
    main()
