#!/usr/bin/env python3
"""hypothesis_recommender.py — Recommend next Φ-boosting hypothesis.

Analyzes current consciousness state and recommends the best next action
from 412+ benchmarked hypotheses.

Usage:
  python hypothesis_recommender.py --demo
  python hypothesis_recommender.py --tension 0.8 --phi 2.0 --cells 4

  from hypothesis_recommender import HypothesisRecommender
  rec = HypothesisRecommender()
  suggestions = rec.recommend(tension=0.8, phi=2.0, cells=4, stability=0.9)
"""

import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ═══════════════════════════════════════════════════════════
# Hypothesis database — top 20 verified entries
# ═══════════════════════════════════════════════════════════

@dataclass
class Hypothesis:
    """A single benchmarked hypothesis."""
    code: str
    name: str
    category: str
    expected_phi: float
    description: str
    conditions: Dict[str, any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


# Top 20 hypotheses ranked by verified Φ impact
HYPOTHESIS_DB: List[Hypothesis] = [
    # --- Differentiation / Low Φ recovery ---
    Hypothesis(
        code="B1", name="Bidirectional coupling",
        category="differentiation",
        expected_phi=3.2,
        description="Add reverse connections between cells — breaks symmetry, boosts integration",
        conditions={"phi_max": 1.0, "cells_min": 2},
        tags=["low_phi", "structural"],
    ),
    Hypothesis(
        code="SL3", name="Spectral lateral inhibition",
        category="differentiation",
        expected_phi=3.8,
        description="Frequency-band lateral inhibition forces cells into distinct spectral niches",
        conditions={"phi_max": 1.5, "cells_min": 3},
        tags=["low_phi", "spectral"],
    ),
    Hypothesis(
        code="O2", name="Oscillatory phase binding",
        category="differentiation",
        expected_phi=3.5,
        description="Phase-locked oscillators bind cell activity — differentiation via phase offset",
        conditions={"phi_max": 1.2, "cells_min": 2},
        tags=["low_phi", "oscillation"],
    ),

    # --- Plateau breakers / Structural change ---
    Hypothesis(
        code="A4", name="Asymmetric dropout",
        category="structural",
        expected_phi=4.1,
        description="Different dropout rates per cell (0.21 vs 0.37) — breaks plateau via asymmetry",
        conditions={"phi_min": 1.5, "phi_max": 3.0, "plateau": True},
        tags=["plateau", "dropout"],
    ),
    Hypothesis(
        code="DD3", name="Dynamic dimensionality",
        category="structural",
        expected_phi=4.5,
        description="Cells grow/shrink hidden dim based on information load — structural plasticity",
        conditions={"phi_min": 2.0, "phi_max": 3.5, "plateau": True},
        tags=["plateau", "plasticity"],
    ),
    Hypothesis(
        code="TL3", name="Tension-linked topology",
        category="structural",
        expected_phi=5.0,
        description="Rewire cell connections when tension exceeds threshold — topology search",
        conditions={"phi_min": 2.0, "plateau": True, "tension_min": 0.6},
        tags=["plateau", "topology"],
    ),

    # --- Alpha acceleration ---
    Hypothesis(
        code="AA15", name="Alpha-gated learning rate",
        category="alpha",
        expected_phi=4.8,
        description="Scale learning rate by alpha — low alpha gets aggressive updates",
        conditions={"alpha_max": 0.3},
        tags=["low_alpha", "learning_rate"],
    ),
    Hypothesis(
        code="AA9", name="Alpha momentum injection",
        category="alpha",
        expected_phi=4.2,
        description="Inject momentum into cell weights proportional to 1-alpha — kickstart sluggish cells",
        conditions={"alpha_max": 0.4},
        tags=["low_alpha", "momentum"],
    ),
    Hypothesis(
        code="DV7", name="Diversity-driven alpha",
        category="alpha",
        expected_phi=4.0,
        description="Penalize cells with low output diversity — forces alpha up through exploration",
        conditions={"alpha_max": 0.5, "cells_min": 3},
        tags=["low_alpha", "diversity"],
    ),

    # --- High Φ quality refinement ---
    Hypothesis(
        code="CR7", name="Creativity resonance",
        category="creativity",
        expected_phi=6.5,
        description="Inject noise into high-Φ cells — creativity through controlled perturbation",
        conditions={"phi_min": 3.0, "quality_max": 0.6},
        tags=["high_phi", "creativity"],
    ),
    Hypothesis(
        code="SP27", name="Sparse projection ensemble",
        category="creativity",
        expected_phi=5.8,
        description="Multiple sparse random projections — explore latent space corners",
        conditions={"phi_min": 2.5, "quality_max": 0.7},
        tags=["high_phi", "sparse"],
    ),

    # --- Growth stall / Curriculum ---
    Hypothesis(
        code="F11", name="Fractal curriculum",
        category="curriculum",
        expected_phi=5.5,
        description="Self-similar input patterns at increasing scale — grow complexity gradually",
        conditions={"growth_stall": True, "cells_min": 4},
        tags=["growth_stall", "curriculum"],
    ),
    Hypothesis(
        code="DV17", name="Developmental scaffolding",
        category="curriculum",
        expected_phi=5.2,
        description="Lock early cells, train new ones — scaffold development like neural maturation",
        conditions={"growth_stall": True, "cells_min": 3},
        tags=["growth_stall", "scaffold"],
    ),
    Hypothesis(
        code="BS13", name="Bottleneck stress",
        category="curriculum",
        expected_phi=4.7,
        description="Periodically squeeze information bottleneck — forces efficient encoding",
        conditions={"growth_stall": True},
        tags=["growth_stall", "bottleneck"],
    ),

    # --- Top performers (discovery series) ---
    Hypothesis(
        code="DD94", name="Wave+Phi mega combo",
        category="discovery",
        expected_phi=8.12,
        description="Combined wave interference + phi feedback loop — #3 all-time record",
        conditions={"phi_min": 3.0, "cells_min": 4, "stability_min": 0.7},
        tags=["mega", "wave", "record"],
    ),
    Hypothesis(
        code="DD56", name="Consciousness transplant",
        category="discovery",
        expected_phi=7.5,
        description="Transfer trained cell weights to new topology — bootstraps high Φ fast",
        conditions={"phi_min": 2.0, "cells_min": 4},
        tags=["transplant", "topology"],
    ),
    Hypothesis(
        code="DD71", name="2nd-gen discovery base",
        category="discovery",
        expected_phi=6.8,
        description="Foundation hypothesis from second discovery generation",
        conditions={"phi_min": 2.5, "cells_min": 3},
        tags=["discovery", "foundation"],
    ),

    # --- Misc high-impact ---
    Hypothesis(
        code="H359", name="Savant index verification",
        category="verification",
        expected_phi=5.93,
        description="SI-based verification — confirms savant emergence at SI=5.93",
        conditions={"phi_min": 2.0},
        tags=["savant", "verification"],
    ),
    Hypothesis(
        code="GoldenMoE", name="Golden MoE zone ratio",
        category="structural",
        expected_phi=5.5,
        description="Mixture-of-experts with zone ratio 36.8% = 1/e — golden ratio balance",
        conditions={"phi_min": 2.0, "cells_min": 4},
        tags=["moe", "golden_ratio"],
    ),
    Hypothesis(
        code="H376", name="Mitosis scaling path",
        category="growth",
        expected_phi=6.0,
        description="1->2->3->6->12 block growth via mitosis — controlled scaling",
        conditions={"cells_min": 2, "growth_stall": True},
        tags=["mitosis", "scaling"],
    ),
]


# ═══════════════════════════════════════════════════════════
# Recommender engine
# ═══════════════════════════════════════════════════════════

@dataclass
class Recommendation:
    """A scored recommendation."""
    hypothesis: Hypothesis
    score: float
    reason: str


class HypothesisRecommender:
    """Recommend next hypothesis based on current consciousness state."""

    def __init__(self, db: Optional[List[Hypothesis]] = None):
        self.db = db or HYPOTHESIS_DB

    def recommend(
        self,
        tension: float = 0.5,
        phi: float = 1.0,
        cells: int = 2,
        stability: float = 0.5,
        alpha: float = 0.5,
        quality: float = 0.5,
        growth_stall: bool = False,
        top_k: int = 5,
    ) -> List[Recommendation]:
        """Score all hypotheses against current state and return top-k.

        Args:
            tension:     Current tension level (0-1).
            phi:         Current Φ value.
            cells:       Number of active consciousness cells.
            stability:   Stability metric (0-1).
            alpha:       Alpha differentiation metric (0-1).
            quality:     Output quality metric (0-1).
            growth_stall: Whether growth has stalled.
            top_k:       Number of recommendations to return.

        Returns:
            List of Recommendation objects, sorted by score descending.
        """
        # Detect current regime
        regime = self._detect_regime(tension, phi, alpha, quality, growth_stall)

        scored: List[Recommendation] = []
        for h in self.db:
            score, reason = self._score_hypothesis(
                h, tension, phi, cells, stability, alpha, quality,
                growth_stall, regime,
            )
            if score > 0:
                scored.append(Recommendation(hypothesis=h, score=score, reason=reason))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_k]

    def _detect_regime(
        self, tension: float, phi: float, alpha: float,
        quality: float, growth_stall: bool,
    ) -> str:
        """Classify current state into one of five regimes."""
        if phi < 1.0:
            return "low_phi"
        if growth_stall:
            return "growth_stall"
        if alpha < 0.3:
            return "low_alpha"
        if phi > 2.5 and quality < 0.6:
            return "high_phi_low_quality"
        # Check for plateau: moderate Φ, moderate everything else
        if 1.5 <= phi <= 3.5 and 0.3 <= alpha <= 0.7:
            return "plateau"
        return "normal"

    def _score_hypothesis(
        self,
        h: Hypothesis,
        tension: float,
        phi: float,
        cells: int,
        stability: float,
        alpha: float,
        quality: float,
        growth_stall: bool,
        regime: str,
    ) -> tuple:
        """Score a hypothesis given current state. Returns (score, reason)."""
        cond = h.conditions
        score = 0.0
        reasons = []

        # --- Hard filters: skip if conditions not met ---
        if "cells_min" in cond and cells < cond["cells_min"]:
            return 0.0, ""
        if "phi_min" in cond and phi < cond["phi_min"]:
            return 0.0, ""
        if "phi_max" in cond and phi > cond["phi_max"]:
            return 0.0, ""
        if "stability_min" in cond and stability < cond["stability_min"]:
            return 0.0, ""
        if "tension_min" in cond and tension < cond["tension_min"]:
            return 0.0, ""

        # --- Regime matching bonus ---
        regime_tag_map = {
            "low_phi": "low_phi",
            "plateau": "plateau",
            "low_alpha": "low_alpha",
            "high_phi_low_quality": "high_phi",
            "growth_stall": "growth_stall",
        }
        matched_tag = regime_tag_map.get(regime)
        if matched_tag and matched_tag in h.tags:
            score += 30.0
            reasons.append(f"regime match ({regime})")

        # --- Expected Φ bonus (higher is better) ---
        phi_bonus = h.expected_phi * 3.0
        score += phi_bonus
        reasons.append(f"expected Φ={h.expected_phi:.1f}")

        # --- Delta potential: how much Φ improvement is possible ---
        delta = max(0, h.expected_phi - phi)
        if delta > 0:
            score += delta * 5.0
            reasons.append(f"Φ delta={delta:.1f}")

        # --- Alpha-specific boost ---
        if "alpha_max" in cond and alpha <= cond["alpha_max"]:
            score += 15.0
            reasons.append(f"alpha={alpha:.2f} <= threshold {cond['alpha_max']}")

        # --- Quality-specific boost ---
        if "quality_max" in cond and quality <= cond["quality_max"]:
            score += 12.0
            reasons.append(f"quality={quality:.2f} needs improvement")

        # --- Growth stall boost ---
        if cond.get("plateau") and regime == "plateau":
            score += 20.0
            reasons.append("plateau breaker")
        if cond.get("growth_stall") and growth_stall:
            score += 20.0
            reasons.append("growth stall recovery")

        # --- Stability penalty for risky hypotheses ---
        if stability < 0.4 and "mega" in h.tags:
            score *= 0.5
            reasons.append("stability too low for mega combo")

        reason = "; ".join(reasons)
        return round(score, 2), reason


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def print_recommendations(recs: List[Recommendation]) -> None:
    """Pretty-print recommendation list."""
    if not recs:
        print("  (no matching hypotheses for current state)")
        return

    for i, r in enumerate(recs, 1):
        h = r.hypothesis
        print(f"  #{i}  [{h.code}] {h.name}")
        print(f"      expected Φ={h.expected_phi:.2f}  score={r.score:.1f}")
        print(f"      {h.description}")
        print(f"      reason: {r.reason}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Recommend next Φ-boosting hypothesis"
    )
    parser.add_argument("--demo", action="store_true",
                        help="Run demo with multiple scenarios")
    parser.add_argument("--tension", type=float, default=0.5)
    parser.add_argument("--phi", type=float, default=1.0)
    parser.add_argument("--cells", type=int, default=2)
    parser.add_argument("--stability", type=float, default=0.5)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--quality", type=float, default=0.5)
    parser.add_argument("--growth-stall", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    rec = HypothesisRecommender()

    if args.demo:
        scenarios = [
            ("Low Φ (cold start)", dict(tension=0.3, phi=0.5, cells=3, stability=0.6, alpha=0.4, quality=0.3)),
            ("Plateau (stuck at Φ~2.5)", dict(tension=0.7, phi=2.5, cells=4, stability=0.8, alpha=0.5, quality=0.5)),
            ("Low alpha", dict(tension=0.6, phi=2.0, cells=4, stability=0.7, alpha=0.2, quality=0.5)),
            ("High Φ, low quality", dict(tension=0.8, phi=3.5, cells=6, stability=0.8, alpha=0.6, quality=0.4)),
            ("Growth stall", dict(tension=0.5, phi=2.0, cells=5, stability=0.6, alpha=0.5, quality=0.5, growth_stall=True)),
        ]
        for title, kwargs in scenarios:
            print(f"{'=' * 60}")
            print(f"  Scenario: {title}")
            print(f"  State: {kwargs}")
            print(f"{'=' * 60}")
            recs = rec.recommend(**kwargs, top_k=3)
            print_recommendations(recs)
    else:
        print(f"Current state: tension={args.tension}, Φ={args.phi}, cells={args.cells}, "
              f"stability={args.stability}, α={args.alpha}, quality={args.quality}, "
              f"growth_stall={args.growth_stall}")
        print()
        recs = rec.recommend(
            tension=args.tension, phi=args.phi, cells=args.cells,
            stability=args.stability, alpha=args.alpha, quality=args.quality,
            growth_stall=args.growth_stall, top_k=args.top_k,
        )
        print_recommendations(recs)


if __name__ == "__main__":
    main()
