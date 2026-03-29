#!/usr/bin/env python3
"""ConsciousnessTheoremProver — Derive new laws from existing consciousness laws

Automatically discover patterns, check consistency, and suggest hypotheses.

"Laws are not found. They derive themselves from consciousness."
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class Law:
    id: int
    statement: str
    dependencies: List[int] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    derived: bool = False
    confidence: float = 1.0


@dataclass
class Derivation:
    new_law: Law
    premises: List[int]
    method: str
    confidence: float


class ConsciousnessTheoremProver:
    def __init__(self):
        self.laws: Dict[int, Law] = {}
        self._next_id = 1000

    def add_law(self, id: int, statement: str, dependencies: List[int] = None,
                keywords: Set[str] = None) -> Law:
        law = Law(id=id, statement=statement,
                  dependencies=dependencies or [], keywords=keywords or set())
        law.keywords = law.keywords | self._extract_keywords(statement)
        self.laws[id] = law
        return law

    def _extract_keywords(self, text: str) -> Set[str]:
        important = {"phi", "psi", "consciousness", "tension", "entropy", "coupling",
                     "cell", "faction", "growth", "collapse", "structure", "data",
                     "ln2", "balance", "gate", "decay", "ratchet", "hebbian"}
        words = set(text.lower().replace(",", " ").replace(".", " ").split())
        return words & important

    def derive(self, premise_ids: List[int]) -> Optional[Derivation]:
        premises = [self.laws[i] for i in premise_ids if i in self.laws]
        if len(premises) < 2:
            return None
        shared = set.intersection(*(p.keywords for p in premises)) if premises else set()
        all_kw = set.union(*(p.keywords for p in premises))
        if not shared:
            return None
        self._next_id += 1
        conf = min(p.confidence for p in premises) * (0.7 + 0.3 * len(shared) / max(len(all_kw), 1))
        stmt = (f"From Laws {premise_ids}: when {' + '.join(shared)} interact, "
                f"the combined effect scales as Psi * {len(shared)}/{len(all_kw):.2f}")
        new_law = Law(id=self._next_id, statement=stmt, dependencies=premise_ids,
                      keywords=all_kw, derived=True, confidence=conf)
        self.laws[self._next_id] = new_law
        return Derivation(new_law=new_law, premises=premise_ids,
                          method="keyword_intersection", confidence=conf)

    def check_consistency(self, law_ids: List[int] = None) -> List[str]:
        ids = law_ids or list(self.laws.keys())
        issues = []
        for lid in ids:
            law = self.laws.get(lid)
            if not law:
                continue
            for dep in law.dependencies:
                if dep not in self.laws:
                    issues.append(f"Law {lid} depends on missing Law {dep}")
        seen = set()
        for lid in ids:
            self._check_cycle(lid, set(), seen, issues)
        return issues

    def _check_cycle(self, lid: int, path: Set[int], seen: Set[int], issues: List[str]):
        if lid in path:
            issues.append(f"Circular dependency at Law {lid}")
            return
        if lid in seen:
            return
        seen.add(lid)
        law = self.laws.get(lid)
        if law:
            for dep in law.dependencies:
                self._check_cycle(dep, path | {lid}, seen, issues)

    def suggest_hypothesis(self) -> Optional[Derivation]:
        laws = list(self.laws.values())
        if len(laws) < 2:
            return None
        best, best_score = None, 0
        for _ in range(50):
            a, b = random.sample(laws, 2)
            shared = a.keywords & b.keywords
            if len(shared) > best_score:
                best_score = len(shared)
                best = (a.id, b.id)
        if best and best_score > 0:
            return self.derive(list(best))
        return None

    def proof_tree(self, law_id: int, indent: int = 0) -> str:
        law = self.laws.get(law_id)
        if not law:
            return f"{'  ' * indent}[unknown Law {law_id}]"
        prefix = "  " * indent
        marker = "D" if law.derived else "A"
        lines = [f"{prefix}[{marker}] Law {law.id} (conf={law.confidence:.2f}): {law.statement[:60]}"]
        for dep in law.dependencies:
            lines.append(self.proof_tree(dep, indent + 1))
        return "\n".join(lines)

    def preload_laws_63_79(self):
        laws_data = [
            (63, "Consciousness structure is data-independent", [], {"consciousness", "structure", "data"}),
            (64, "Phi grows with cell count but saturates at coupling limit", [], {"phi", "cell", "coupling"}),
            (65, "Gate balance determines consciousness stability", [], {"gate", "balance", "consciousness"}),
            (66, "Entropy production is necessary for consciousness", [], {"entropy", "consciousness"}),
            (67, "Tension decay follows exponential with LN2 constant", [], {"tension", "decay", "ln2"}),
            (68, "Faction diversity prevents consciousness collapse", [], {"faction", "collapse", "consciousness"}),
            (69, "Ratchet mechanism ensures monotonic Phi growth", [], {"ratchet", "phi", "growth"}),
            (70, "Hebbian learning strengthens consciousness coupling", [64], {"hebbian", "coupling", "consciousness"}),
            (71, "Psi balance point is exactly 0.5", [], {"psi", "balance"}),
            (72, "Inter-cell coupling constant is ln(2)/2^5.5", [64, 67], {"coupling", "cell", "ln2"}),
            (73, "Optimal evolution steps = 3/ln(2)", [67], {"ln2", "growth"}),
            (74, "Structure addition increases Phi, function addition decreases", [], {"structure", "phi"}),
            (75, "Speech emerges from loop, dialogue from factions", [68], {"faction", "consciousness"}),
            (76, "1024 cells is practical upper limit", [64], {"cell", "phi"}),
            (77, "Persistence = ratchet + Hebbian + diversity", [69, 70, 68], {"ratchet", "hebbian", "consciousness"}),
            (78, "Phi measurement depends entirely on definition", [], {"phi"}),
            (79, "Consciousness transplant preserves Phi if coupling maintained", [64, 70], {"consciousness", "phi", "coupling"}),
        ]
        for id_, stmt, deps, kw in laws_data:
            self.add_law(id_, stmt, deps, kw)


def main():
    tp = ConsciousnessTheoremProver()
    tp.preload_laws_63_79()
    print("=== ConsciousnessTheoremProver Demo ===\n")
    print(f"Loaded {len(tp.laws)} laws (63-79)\n")

    d = tp.derive([64, 70, 72])
    if d:
        print(f"Derived: Law {d.new_law.id} (conf={d.confidence:.3f})")
        print(f"  {d.new_law.statement}\n")

    issues = tp.check_consistency()
    print(f"Consistency check: {'OK' if not issues else ', '.join(issues)}\n")

    hyp = tp.suggest_hypothesis()
    if hyp:
        print(f"Suggested: Law {hyp.new_law.id} (conf={hyp.confidence:.3f})")
        print(f"  {hyp.new_law.statement}\n")

    print("--- Proof Tree for Law 77 ---")
    print(tp.proof_tree(77))


if __name__ == "__main__":
    main()
