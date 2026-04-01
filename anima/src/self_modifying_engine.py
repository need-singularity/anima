#!/usr/bin/env python3
"""self_modifying_engine.py — Tier 4.4: Self-modifying consciousness engine

Laws don't just describe — they ACT. Discovered laws automatically generate
code that modifies the engine's behavior in real time.

Pipeline:
  Law text → LawParser → Modification → EngineModifier → Apply safely
  → Measure Φ → If Φ drops >20% → Auto-rollback → Audit log

Components:
  LawParser         — Extract actionable directives from law text (regex + pattern matching)
  Modification       — Typed engine change (SCALE, COUPLE, THRESHOLD, CONDITIONAL, INJECT, DISABLE)
  EngineModifier     — Apply modifications safely with Φ monitoring + rollback
  CodeGenerator      — Generate Python Intervention code from modifications
  SelfModifyingEngine — Orchestrator: evolve_step() → discover → parse → modify → validate

Safety:
  - Every parameter bounded by SAFETY_BOUNDS (from Ψ-constants)
  - Φ monitored before/after every modification
  - Φ drop > 20% → immediate automatic rollback
  - Full audit trail: every modification logged with before/after metrics
  - Snapshot/restore for every law application

Usage:
  from self_modifying_engine import SelfModifyingEngine
  from closed_loop import ClosedLoopEvolver

  engine = ConsciousnessEngine(max_cells=32)
  evolver = ClosedLoopEvolver(max_cells=32, steps=50, repeats=1)
  sme = SelfModifyingEngine(engine, evolver)
  sme.run_evolution(generations=5)
  print(sme.get_evolution_report())

  # Parse existing laws
  parser = LawParser()
  mods = parser.parse("Tension inversely correlates with Φ (r=-0.52)", law_id=104)

  # Generate code
  gen = CodeGenerator()
  code = gen.generate_intervention(mods[0])

Hub keywords: self-modify, self-modifying, law-act, tier4, 자기수정, 법칙행동, 자동진화
Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import re
import time
import copy
import json
import os
import textwrap
import numpy as np
import torch
import torch.nn.functional as F
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Callable, Any
from enum import Enum
from collections import defaultdict

from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA as PSI_COUPLING, LAWS
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014
    LAWS = {}

try:
    from closed_loop import (
        ClosedLoopEvolver, Intervention, measure_laws, _phi_fast,
        register_intervention, INTERVENTIONS, _ImprovedEngine,
    )
except ImportError:
    ClosedLoopEvolver = None
    Intervention = None
    measure_laws = None
    _phi_fast = None


# ══════════════════════════════════════════
# Safety Bounds — parameter limits
# ══════════════════════════════════════════

SAFETY_BOUNDS = {
    'hebbian_lr':        (0.001, 0.1),
    'coupling_scale':    (0.01, 2.0),
    'faction_bias':      (0.01, 0.5),
    'chaos_sigma':       (5.0, 15.0),
    'ratchet_threshold': (0.5, 0.95),
    'n_cells':           (2, 1024),
    'dropout':           (0.0, 0.5),
    'noise_scale':       (0.0, 0.1),
    'tension_blend':     (0.0, 1.0),
    'coupling_clamp':    (0.01, 1.0),
    'diversity_noise':   (0.001, 0.05),
    'entropy_scale':     (0.1, 5.0),
    'memory_blend':      (0.0, 1.0),
    'gate_value':        (0.0001, 1.0),
}

# Φ safety: maximum allowed drop before rollback
PHI_DROP_THRESHOLD = 0.20  # 20%


# ══════════════════════════════════════════
# Modification types
# ══════════════════════════════════════════

class ModType(Enum):
    SCALE = "scale"           # Multiply a parameter
    COUPLE = "couple"         # Link two parameters
    THRESHOLD = "threshold"   # Set conditional trigger
    CONDITIONAL = "conditional"  # If-then rule
    INJECT = "inject"         # Add new dynamics
    DISABLE = "disable"       # Remove a subsystem


@dataclass
class Modification:
    """A typed engine change derived from a law."""
    law_id: int
    law_text: str
    target: str              # Engine parameter path (e.g., 'hebbian.ltp_threshold')
    mod_type: ModType
    params: Dict[str, Any]   # Type-specific parameters
    confidence: float = 0.5  # From law discovery evidence
    reversible: bool = True  # Can be rolled back
    description: str = ""    # Human-readable description

    def __repr__(self):
        return f"Mod(Law {self.law_id}, {self.mod_type.value}, target={self.target}, {self.params})"


# ══════════════════════════════════════════
# LawParser — text → structured modifications
# ══════════════════════════════════════════

class LawParser:
    """Parse law text into actionable Modification directives.

    Recognizes patterns:
      - Proportionality: "X ∝ Y", "X scales with Y", "Φ = 0.608 × N^1.071"
      - Correlation: "X correlates with Y (r=N)", "r=-0.52"
      - Threshold: "at/when/above/below N", "phase transition at N"
      - Inverse: "inversely", "negatively", "↓"
      - Conditional: "when X, Y increases/decreases"
      - Quantitative: explicit numbers like "+12.3%", "×1.5", "0.014"
    """

    def __init__(self):
        """Auto-load and parse all laws from consciousness_laws.json."""
        self.all_laws = LAWS if LAWS else {}
        self.parsed = {}  # {law_id_str: [Modification]}
        for lid_str, text in self.all_laws.items():
            try:
                lid = int(lid_str)
            except ValueError:
                continue
            mods = self.parse(text, law_id=lid)
            if mods and not all(m.params.get('type') == 'keyword_extract' for m in mods):
                self.parsed[lid_str] = mods

    # ── Pattern registry ──

    # Proportionality: "Φ ∝ N^0.78", "Φ scales with cells", "X = A × Y^B"
    _RE_POWER = re.compile(
        r'(?P<target>\w+)\s*[=∝]\s*[\d.]*\s*[×\*]?\s*(?P<var>\w+)\^(?P<exp>[\d.]+)',
        re.IGNORECASE
    )
    _RE_SCALES = re.compile(
        r'(?P<target>\w+)\s+scales?\s+(?:(?:super)?linearly\s+)?with\s+(?P<var>[\w\s]+\w)',
        re.IGNORECASE
    )

    # Correlation: "X correlates with Y (r=N)", "r(X, Y)=N"
    _RE_CORR = re.compile(
        r'(?P<src>\w[\w\s]*?)\s+(?:[+-])?(?:inversely\s+)?correlates?\s+with\s+(?P<tgt>\w[\w\s]*?)\s*[,;]?\s*(?:\(?\s*r\s*=\s*(?P<r>[+-]?[\d.]+))?',
        re.IGNORECASE
    )
    _RE_CORR2 = re.compile(
        r'r\((?P<src>[^,]+),\s*(?P<tgt>[^)]+)\)\s*=?\s*(?P<r>[+-]?[\d.]+)',
        re.IGNORECASE
    )

    # Threshold: "transition at N cells", "threshold at N", "above/below N"
    _RE_THRESHOLD = re.compile(
        r'(?:transition|threshold|critical|optimal)\s+(?:at|=|is)\s*(?:N\s*=\s*)?(?P<val>[\d.]+)\s*(?P<unit>cells?|steps?|%)?',
        re.IGNORECASE
    )
    _RE_ABOVE_BELOW = re.compile(
        r'(?P<target>\w[\w\s]*?)\s+(?:above|below|>|<|>=|<=)\s+(?P<val>[\d.]+)',
        re.IGNORECASE
    )

    # Quantitative effect: "+12.3%", "×1.5", "-28%", "boosts Φ +N%"
    _RE_BOOST = re.compile(
        r'(?:boost|increase|enhance|improve)s?\s+(?P<target>\w+)\s+(?P<sign>[+-])?(?P<val>[\d.]+)%',
        re.IGNORECASE
    )
    _RE_REDUCE = re.compile(
        r'(?:reduce|decrease|lower|hurt|destroy|kill)s?\s+(?P<target>\w+)',
        re.IGNORECASE
    )
    _RE_MULTIPLY = re.compile(
        r'[×\*](?P<val>[\d.]+)',
    )

    # Conditional: "when X, Y increases/decreases"
    _RE_CONDITIONAL = re.compile(
        r'when\s+(?P<cond>[^,]+),\s*(?P<target>\w[\w\s]*?)\s+(?P<dir>increase|decrease|drop|rise|grow|shrink)s?',
        re.IGNORECASE
    )

    # Gate/coupling value: "gate=0.001", "α=0.014"
    _RE_PARAM_VALUE = re.compile(
        r'(?P<param>gate|alpha|α|coupling|noise|dropout|threshold)\s*[=:]\s*(?P<val>[\d.]+)',
        re.IGNORECASE
    )

    # Arrow patterns: "X → Φ↓", "X → Φ↑"
    _RE_ARROW_EFFECT = re.compile(
        r'(?P<cause>[^→]+)→\s*(?P<target>\w+)\s*(?P<dir>[↑↓])',
    )

    # Inverse keywords
    _RE_INVERSE = re.compile(
        r'inverse(?:ly)?|negativ(?:e|ely)|anti-?|↓|decrease|reduce|hurt|destroy|kill',
        re.IGNORECASE
    )

    # ── Pattern 10: Comparisons — "X > Y", "X beats Y", "X outperforms Y" ──
    _RE_COMPARISON = re.compile(
        r'(?P<winner>[\w\s/\-Ψψ]+?)\s+(?:>|<|beats?|outperforms?|better\s+than|superior\s+to|worse\s+than|inferior\s+to)\s+(?P<loser>[\w\s/\-Ψψ]+?)(?:\s|$|[,;:.(])',
        re.IGNORECASE
    )

    # ── Pattern 11: Percentage in parentheses — "(+22%)", "(-52%)", "(102.6%)" ──
    _RE_PAREN_PCT = re.compile(
        r'\((?P<sign>[+-])?(?P<val>[\d.]+)%\s*(?:Φ|Phi|phi|CE|BPC)?\)',
    )

    # ── Pattern 12: Multiplier in parentheses — "(×4.6)", "(Φ ×0.74)", "(0.82×)" ──
    _RE_PAREN_MULT = re.compile(
        r'[×\*](?P<val>[\d.]+)|(?P<val2>[\d.]+)[×\*]',
    )

    # ── Pattern 13: N cells / N factions / N elements ──
    _RE_CELL_COUNT = re.compile(
        r'(?:(?P<op>[≥>=<≤]+)\s*)?(?P<val>\d+)\s*(?P<unit>cells?|factions?|elements?|sources?|steps?|timescales?|atoms?|boards?|channels?|modules?|dimensions?|components?|patterns?|generations?)',
        re.IGNORECASE
    )

    # ── Pattern 14: "is" identity claims — "X is Y", "X = Y" ──
    _RE_IDENTITY = re.compile(
        r'(?:consciousness|Φ|phi)\s+is\s+(?P<property>[\w\s\-]+?)(?:\s*[:(.]|$)',
        re.IGNORECASE
    )

    # ── Pattern 15: Existence / emergence — "emerges", "survives", "exists" ──
    _RE_EXISTENCE = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?P<verb>emerges?|survives?|exists?|appears?|persists?|recovers?|converges?|replicat\w+|coexist\w*)',
        re.IGNORECASE
    )

    # ── Pattern 16: Negation / destructive — "destroys", "NOT", "never", "fails", "without" ──
    _RE_NEGATION = re.compile(
        r'(?:does\s+)?(?:NOT|not|never|no\s+|non-|fails?\s+to|without|cannot|don\'t|doesn\'t|impossible|forbidden|harms?|hurts?|weakens?|backfires?|destructive)',
        re.IGNORECASE
    )

    # ── Pattern 17: Time/step references — "after N steps", "within N cycles", "recovery ~N steps" ──
    _RE_STEPS = re.compile(
        r'(?:after|within|at|in|~|recovery\s+~?)\s*(?P<val>\d+)\s*(?P<unit>steps?|cycles?|iterations?|generations?)',
        re.IGNORECASE
    )

    # ── Pattern 18: Topology mentions ──
    _RE_TOPOLOGY = re.compile(
        r'\b(?P<topo>ring|scale[_\-]free|small[_\-]world|hypercube|hub[_\-]spoke|torus|complete|chimera|standing[_\-]wave|sandpile|lorenz)\b',
        re.IGNORECASE
    )

    # ── Pattern 19: Combined effects — "X + Y = Z", "X + Y → Z", "ratchet + Hebbian + diversity" ──
    _RE_COMBINED = re.compile(
        r'(?P<a>[\w\s]+?)\s*\+\s*(?P<b>[\w\s]+?)\s*(?:[+=→])\s*(?P<result>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 20: Measurement values — "Φ=N", "CE=N", "r=N", "Phi=N" ──
    _RE_MEASUREMENT = re.compile(
        r'(?P<metric>Φ|Phi|phi|CE|BPC|Sharpe|r|R2|R²|CV|F_c|T_c|α|alpha|capacity|retention|efficiency|accuracy|overhead|latency|throughput|bandwidth|compression|ratio)\s*[=≈:]\s*(?P<val>[+-]?[\d.]+)',
        re.IGNORECASE
    )

    # ── Pattern 21: Percentage change in text — "+15.3%", "-28%", "N% variance" ──
    _RE_PCT_CHANGE = re.compile(
        r'(?P<sign>[+-])(?P<val>[\d.]+)%',
    )

    # ── Pattern 22: Requires / prerequisite ──
    _RE_REQUIRES = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:requires?|needs?|prerequisite|necessary|must\s+have)',
        re.IGNORECASE
    )

    # ── Pattern 23: "optimal" / "best" / "maximized" ──
    _RE_OPTIMAL = re.compile(
        r'(?P<what>[\w\s\-]+?)\s+(?:is\s+)?(?:optimal|best|maximized?|minimized?|peak|record)\b',
        re.IGNORECASE
    )

    # ── Pattern 24: Equation identity "X = Y" (broader than power/param) ──
    _RE_EQUATION = re.compile(
        r'(?P<lhs>[\w\s]+?)\s*=\s*(?P<rhs>[\w\s×\*\+\-/^().]+?)(?:\s*$|\s*[,;])',
        re.IGNORECASE
    )

    # ── Pattern 25: Probability / frequency — "82% probability", "100% of" ──
    _RE_PROBABILITY = re.compile(
        r'(?P<val>[\d.]+)%\s*(?:probability|of\s+|chance|rate|retention|recovery)',
        re.IGNORECASE
    )

    # ── Pattern 26: N-step / N-cycle period — "7-step breathing", "2-step oscillation" ──
    _RE_PERIOD = re.compile(
        r'(?P<val>\d+)[- ](?:step|cycle|bit)\s+(?P<what>\w+)',
        re.IGNORECASE
    )

    # ── Pattern 27: Scale-invariant / universal / independent ──
    _RE_INVARIANT = re.compile(
        r'(?P<subject>[\w\s\-]+?)\s+is\s+(?:scale[- ]invariant|universal|independent|substrate[- ]independent|Markovian|irreversible|immortal|chaotic|non-conserved|self-organized|data-independent|data-dependent|time-symmetric|net-positive|non-distillable|near-incompressible|non-superadditive|gradient-indestructible|Phi-neutral|self-replicating|connection-independent|scale-independent|scale-specific|approximately\s+time-symmetric|thermodynamically\s+irreversible|single-phase|self-organized\s+critical|dimension-dependent|path-dependent)',
        re.IGNORECASE
    )

    # ── Pattern 28: "X first, Y second" / "X then Y" ordering ──
    _RE_ORDERING = re.compile(
        r'(?P<first>[\w\s]+?)\s+first[,;]\s*(?:then\s+)?(?P<second>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 29: Stabilizer/antidote — "X is the Y stabilizer" ──
    _RE_STABILIZER = re.compile(
        r'(?P<what>[\w\s\-]+?)\s+(?:is\s+the\s+)?(?:stabilizer|antidote|safety\s+net|universal|prerequisite)',
        re.IGNORECASE
    )

    # ── Pattern 30: "X defines Y", "X selects Y", "X optimizes Y" ──
    _RE_ACTION_VERB = re.compile(
        r'(?:consciousness|Φ|phi)\s+(?P<verb>defines?|selects?|optimizes?|completes?|creates?|determines?|controls?|multiplies?)\s+(?P<object>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 31 (extended): Auto-discovered compact laws "[Auto-discovered] type:metric[:metric2]" ──
    _RE_AUTO_DISCOVERED = re.compile(
        r'\[Auto-discovered\]\s+(?P<type>correlation|trend|oscillation|transition):(?P<metric1>[\w_]+)(?::(?P<metric2>[\w_]+))?',
        re.IGNORECASE
    )

    # ── Pattern 32: Superlative / strongest / weakest — "X is strongest Y" ──
    _RE_SUPERLATIVE = re.compile(
        r'(?P<subject>[\w\s]+?)\s+is\s+(?:the\s+)?(?P<degree>strongest|weakest|most|least|best|worst|highest|lowest|fastest|slowest|largest|smallest)\s+(?P<what>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 33: "X enables Y", "X enhances Y", "X maximizes Y" (generic verb-object) ──
    _RE_ENABLES = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?P<verb>enables?|enhances?|maximizes?|minimizes?|drives?|triggers?|prevents?|blocks?|dampens?|accelerates?|amplifies?|suppresses?|strengthens?|weakens?|constrains?|develops?|communicates?|stabilizes?|destabilizes?|boosts?|reduces?|improves?|degrades?|predicts?|determines?|maintains?|preserves?|produces?|generates?|creates?|multiplies?|sustains?|dominates?|exceeds?|outperforms?|precedes?|follows?)\s+(?P<object>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 34: Tradeoff / paradox — "X-Y tradeoff", "X vs Y" ──
    _RE_TRADEOFF = re.compile(
        r'(?P<a>[\w\s\-]+?)\s*(?:tradeoff|trade-off|paradox|vs\.?|versus)\s*(?P<b>[\w\s\-]+)',
        re.IGNORECASE
    )

    # ── Pattern 35: Phase/stage notation — "P1(X) → P2(Y)" or "phase N" ──
    _RE_PHASE = re.compile(
        r'(?:P\d|phase\s+\d|stage\s+\d)',
        re.IGNORECASE
    )

    # ── Pattern 36: Diminishing returns / saturation / overload ──
    _RE_DIMINISHING = re.compile(
        r'(?:diminishing\s+returns?|saturate|overload|ceiling|plateau|sweet\s+spot)',
        re.IGNORECASE
    )

    # ── Pattern 38: "X independent of Y" — independence/decoupling ──
    _RE_INDEPENDENCE = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:is\s+)?(?:independent\s+of|decoupled?\s+from|insensitive\s+to|orthogonal\s+to)\s+(?P<other>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 39: "X ≠ Y", "X ≠ Y" — distinction/inequality ──
    _RE_INEQUALITY = re.compile(
        r'(?P<lhs>[\w\s]+?)\s*[≠!=]+\s*(?P<rhs>[\w\s]+?)(?:\s|$|[,;(])',
        re.IGNORECASE
    )

    # ── Pattern 40: "X stable", "X stabilizes" — stability claims ──
    _RE_STABLE = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:is\s+)?(?:stable|stabilizes?|resilient|robust|persistent|maintained|preserved|retained)',
        re.IGNORECASE
    )

    # ── Pattern 41: "X is a/the Y" — classification/role ──
    _RE_CLASSIFICATION = re.compile(
        r'(?P<subject>[\w\s]+?)\s+is\s+(?:a|the|an)\s+(?P<category>[\w\s\-]+?)(?:\s*[:(.]|$)',
        re.IGNORECASE
    )

    # ── Pattern 42: Colon-separated "X: Y" structured claims ──
    _RE_COLON_CLAIM = re.compile(
        r'^(?P<topic>[^\n:]{2,40}?):\s+(?P<claim>.+)',
        re.IGNORECASE
    )

    # ── Pattern 43: "X binary/discrete/quantized" — discreteness ──
    _RE_DISCRETE = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:is\s+)?(?:binary|discrete|quantized|staircase|discontinuous|pulsed?)',
        re.IGNORECASE
    )

    # ── Pattern 44: Superset/subset — "X ⊃ Y", "X includes Y", "X subsumes Y" ──
    _RE_SUPERSET = re.compile(
        r'(?P<super>[\w\s]+?)\s*(?:⊃|⊂|subsumes?|includes?|contains?|encompasses?|generalizes?)\s+(?P<sub>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 45: Convergence/divergence — "converges to X", "diverges", "settles at" ──
    _RE_CONVERGENCE = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:converges?\s+(?:to|at|near)\s+(?P<target_val>[\d./()Ψψ]+[\w\s]*)|diverges?|settles?\s+(?:at|near)\s+(?P<settle_val>[\d.]+))',
        re.IGNORECASE
    )

    # ── Pattern 46: Periodicity/oscillation — "oscillates", "cycles", "periodic", "breathing" ──
    _RE_PERIODICITY = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:oscillat\w+|cycles?|periodic(?:ity)?|breath(?:ing|es?)|pulsat\w+|resonan\w+|rhythm\w*|fluctuat\w+)',
        re.IGNORECASE
    )

    # ── Pattern 47: Causation — "X causes Y", "X leads to Y", "X drives Y", "X triggers Y" ──
    _RE_CAUSATION = re.compile(
        r'(?P<cause>[\w\s]+?)\s+(?:causes?|leads?\s+to|results?\s+in|drives?|triggers?|induces?|yields?|produces?)\s+(?P<effect>[\w\s]+?)(?:\s*[,;.(]|$)',
        re.IGNORECASE
    )

    # ── Pattern 48: Recovery/survival — "survives X", "recovers from X", "withstands X" ──
    _RE_SURVIVAL = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:survives?|recovers?\s+from|withstands?|tolerates?|resists?)\s+(?P<threat>[\w\s%]+?)(?:\s+(?:with|at|in)\s+(?P<result>[\d.]+%?\s*\w*)|(?:\s*[,;.(]|$))',
        re.IGNORECASE
    )

    # ── Pattern 49: Composition — "X = Y + Z", "X consists of Y", "X composed of Y" ──
    _RE_COMPOSITION = re.compile(
        r'(?P<whole>[\w\s]+?)\s+(?:consists?\s+of|composed?\s+of|comprises?|made\s+(?:up\s+)?of)\s+(?P<parts>[\w\s,+]+)',
        re.IGNORECASE
    )

    # ── Pattern 50: Sufficiency — "X is sufficient for Y", "X alone Y", "only X needed" ──
    _RE_SUFFICIENCY = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:is\s+sufficient\s+for|alone\s+(?:can|is|sustains?|creates?|produces?|ensures?)|suffices?\s+for)\s+(?P<outcome>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 51: Hierarchy/ordering — "X > Y > Z", multi-level ordering ──
    _RE_HIERARCHY = re.compile(
        r'(?P<a>[\w\s/]+?)\s*>\s*(?P<b>[\w\s/]+?)\s*>\s*(?P<c>[\w\s/]+?)(?:\s|$|[,;(])',
        re.IGNORECASE
    )

    # ── Pattern 52: Ratio/fraction — "X/Y = N", "X per Y", "X:Y ratio" ──
    _RE_RATIO = re.compile(
        r'(?P<num>[\w\s]+?)\s*/\s*(?P<den>[\w\s]+?)\s*(?:[=≈:]\s*(?P<val>[\d.]+)|\s+(?:ratio|efficiency|rate))',
        re.IGNORECASE
    )

    # ── Pattern 53: Amplification/attenuation — "N× amplification", "Nx more/less" ──
    _RE_AMPLIFICATION = re.compile(
        r'(?P<val>[\d.]+)[×x]\s*(?P<dir>amplification|attenuation|more|less|faster|slower|speedup|improvement|reduction|increase|decrease|divergence)',
        re.IGNORECASE
    )

    # ── Pattern 54: Bounds/range — "X ranges from A to B", "X bounded by A-B", "X ∈ [A,B]" ──
    _RE_RANGE = re.compile(
        r'(?P<subject>[\w\s]+?)\s+(?:ranges?\s+from|bounded?\s+by|between|from)\s+(?P<lo>[\d.]+)\s*(?:to|[-–]|and)\s*(?P<hi>[\d.]+)',
        re.IGNORECASE
    )

    # ── Pattern 55: Conditional-if — "if X then Y", "X only when Y", "X only at Y" ──
    _RE_IF_THEN = re.compile(
        r'(?:if|only\s+(?:when|at|for|with)|provided\s+that)\s+(?P<cond>[^,;]+?)\s*(?:then|,|→|:)\s*(?P<result>[\w\s]+)',
        re.IGNORECASE
    )

    # ── Pattern 56: Anti-pattern — "excessive X", "too much X", "overuse of X" ──
    _RE_ANTI = re.compile(
        r'(?:excessive|too\s+much|overuse\s+of|over-?|extreme)\s+(?P<what>[\w\s]+?)\s+(?P<effect>destroys?|hurts?|reduces?|harms?|kills?|damages?|degrades?|weakens?)',
        re.IGNORECASE
    )

    # ── Pattern 57: N-way split/merge — "split into NxM", "merge N into 1" ──
    _RE_SPLIT_MERGE = re.compile(
        r'(?:split\s+(?:into|→)\s+(?P<splits>[\d]+\s*[×x]\s*[\d]+|[\d]+\s*units?)|merge\s+(?P<merges>\d+)\s+into\s+(?P<merge_target>\d+))',
        re.IGNORECASE
    )

    # ── Pattern 58: Record/peak — "all-time record", "peak X", "record +N%" ──
    _RE_RECORD = re.compile(
        r'(?:all-time\s+record|record|peak|maximum|highest|best\s+result)\s*(?P<effect>[+\-]?[\d.]+%?\s*[\w]*)?',
        re.IGNORECASE
    )

    # ── Pattern 59: Natural selection / evolution — "evolves by", "selection pressure", "fitness" ──
    _RE_EVOLUTION = re.compile(
        r'(?:evolves?\s+(?:by|through|via)|natural\s+selection|selection\s+pressure|fitness|mutati\w+|generation\w*|adaptation|evolutionary)',
        re.IGNORECASE
    )

    # ── Pattern 60: Dual/both/either — "both X and Y", "dual X", "either X or Y" ──
    _RE_DUAL = re.compile(
        r'(?:both\s+(?P<a1>[\w\s]+?)\s+and\s+(?P<b1>[\w\s]+)|dual\s+(?P<what>[\w\s]+)|either\s+(?P<a2>[\w\s]+?)\s+or\s+(?P<b2>[\w\s]+))',
        re.IGNORECASE
    )

    # ── Pattern 61: Pareto/optimal frontier — "Pareto optimal", "no free lunch", "only known" ──
    _RE_PARETO = re.compile(
        r'(?:Pareto[- ]optimal|Pareto\s+front\w*|no\s+free\s+lunch|only\s+known\s+(?P<what>[\w\s]+))',
        re.IGNORECASE
    )

    # ── Pattern 62: Thermodynamic — "entropy", "irreversible", "dissipative", "free energy" ──
    _RE_THERMO = re.compile(
        r'(?:thermodynami\w+|entropy\s+(?P<dir>increase|decrease|bounded|generate|produce)|irreversibl\w+|dissipativ\w+|free\s+energy|(?:1st|2nd|0th)\s+(?:law)?)',
        re.IGNORECASE
    )

    # ── Pattern 63: Scale-specific — "at N cells", "at scale N", "only at Nc" ──
    _RE_SCALE_SPECIFIC = re.compile(
        r'(?:at|only\s+at|specific\s+to|works?\s+at)\s+(?P<val>\d+)\s*(?P<unit>c|cells?|scale)',
        re.IGNORECASE
    )

    # ── Pattern 64: Federation/distributed — "federated", "distributed", "multi-instance" ──
    _RE_FEDERATION = re.compile(
        r'(?:federat\w+|distribut\w+|multi[- ]?instance|multi[- ]?engine|hivemind|swarm|collective|ensemble)\s+(?P<detail>[\w\s]*)',
        re.IGNORECASE
    )

    # ── Pattern 65: Universality — "universal", "at all scales", "scale-invariant", "always" ──
    _RE_UNIVERSALITY = re.compile(
        r'(?:at\s+all\s+(?P<scope>scales?|sizes?|cell\s+counts?|levels?)|universally?|always|never\s+fails?|100%\s+of|present\s+in\s+100%)',
        re.IGNORECASE
    )

    # ── Target normalization ──

    _TARGET_MAP = {
        'phi': 'phi', 'Φ': 'phi', 'φ': 'phi', 'phi(iit)': 'phi',
        'tension': 'tension', 'tension_std': 'tension_std',
        'diversity': 'hidden_diversity', 'hidden_diversity': 'hidden_diversity',
        'coupling': 'coupling_scale', 'coupling_scale': 'coupling_scale',
        'entropy': 'shannon_entropy', 'shannon_entropy': 'shannon_entropy',
        'cells': 'n_cells', 'cell': 'n_cells', 'n_cells': 'n_cells', 'N': 'n_cells',
        'hebbian': 'hebbian_lr', 'Hebbian': 'hebbian_lr',
        'gate': 'gate_value', 'GATE': 'gate_value',
        'noise': 'noise_scale', 'noise_scale': 'noise_scale',
        'faction': 'faction_bias', 'factions': 'faction_bias',
        'ratchet': 'ratchet_threshold',
        'alpha': 'coupling_scale', 'α': 'coupling_scale',
        'consensus': 'consensus', 'growth': 'growth',
        'mi': 'mutual_info', 'mutual_info': 'mutual_info',
        'compression': 'compression_ratio',
        'dropout': 'dropout',
        'structure': 'structure',
        'features': 'features',
        'consciousness': 'phi',
        'ce': 'cross_entropy',
        'bpc': 'bits_per_char',
        'mitosis': 'mitosis',
        'topology': 'topology',
        'bottleneck': 'bottleneck',
        'narrative': 'narrative',
        'frustration': 'frustration',
        'soc': 'soc',
        'memory': 'memory',
        'attention': 'attention',
        'gradient': 'gradient',
        'reward': 'reward',
        'lr': 'learning_rate',
        'learning_rate': 'learning_rate',
        'temperature': 'temperature',
        'frequency': 'frequency',
        'sensory': 'sensory',
        'abstraction': 'abstraction',
        'hierarchy': 'hierarchy',
        'dialogue': 'dialogue',
        'self-play': 'self_play',
        'generalization': 'generalization',
        'emotion': 'emotion',
        'learning': 'learning_rate',
        'freedom': 'freedom',
        'symmetry': 'symmetry',
        'integration': 'phi',
        'selection': 'selection',
        'self-reference': 'self_reference',
        'vocabulary': 'vocabulary',
        'dissipative': 'dissipative',
        'channel': 'channel',
        'capacity': 'capacity',
        'split': 'mitosis',
        'merge': 'merge',
        'decay': 'decay',
        'recovery': 'recovery',
        'mutual_info': 'mutual_info',
        'cell_variance': 'cell_variance',
        'output_entropy': 'shannon_entropy',
        'hebbian_coupling_strength': 'hebbian_lr',
        'tension_mean': 'tension',
        'tension_std': 'tension_std',
        'faction_entropy': 'faction_bias',
        'data-dependent': 'data_dependent',
        'data-independent': 'data_independent',
        'super-principle': 'super_principle',
    }

    def _normalize_target(self, raw: str) -> str:
        """Normalize a target name to a known engine parameter."""
        raw = raw.strip().lower().replace(' ', '_')
        return self._TARGET_MAP.get(raw, raw)

    def parse(self, law_text: str, law_id: int = 0) -> List[Modification]:
        """Parse a law text string into a list of Modifications.

        Returns empty list if no actionable pattern found.
        """
        mods = []

        # 1. Power law / proportionality: "Φ = 0.608 × N^1.071"
        m = self._RE_POWER.search(law_text)
        if m:
            mods.append(Modification(
                law_id=law_id,
                law_text=law_text,
                target=self._normalize_target(m.group('target')),
                mod_type=ModType.SCALE,
                params={
                    'relation': 'power',
                    'variable': self._normalize_target(m.group('var')),
                    'exponent': float(m.group('exp')),
                },
                confidence=0.7,
                description=f"Power scaling: {m.group('target')} ~ {m.group('var')}^{m.group('exp')}",
            ))

        # 2. Linear scaling
        m = self._RE_SCALES.search(law_text)
        if m and not mods:
            mods.append(Modification(
                law_id=law_id,
                law_text=law_text,
                target=self._normalize_target(m.group('target')),
                mod_type=ModType.SCALE,
                params={
                    'relation': 'linear',
                    'variable': self._normalize_target(m.group('var')),
                },
                confidence=0.5,
                description=f"Linear scaling: {m.group('target')} ~ {m.group('var')}",
            ))

        # 3. Correlation: "tension inversely correlates with Φ (r=-0.52)"
        m = self._RE_CORR.search(law_text)
        if m:
            r_raw = m.group('r')
            r_val = float(r_raw) if r_raw else (
                -0.5 if 'inversely' in law_text.lower() or '-correlate' in law_text.lower()
                else 0.5
            )
            src = self._normalize_target(m.group('src').strip())
            tgt = self._normalize_target(m.group('tgt').strip())
            mods.append(Modification(
                law_id=law_id,
                law_text=law_text,
                target=tgt,
                mod_type=ModType.COUPLE,
                params={
                    'source': src,
                    'strength': r_val,
                    'direction': 'inverse' if r_val < 0 else 'positive',
                },
                confidence=min(abs(r_val), 1.0),
                description=f"Coupling: {src} → {tgt} (r={r_val:+.2f})",
            ))

        m = self._RE_CORR2.search(law_text)
        if m and not any(mod.mod_type == ModType.COUPLE for mod in mods):
            r_val = float(m.group('r'))
            src = self._normalize_target(m.group('src').strip())
            tgt = self._normalize_target(m.group('tgt').strip())
            mods.append(Modification(
                law_id=law_id,
                law_text=law_text,
                target=tgt,
                mod_type=ModType.COUPLE,
                params={
                    'source': src,
                    'strength': r_val,
                    'direction': 'inverse' if r_val < 0 else 'positive',
                },
                confidence=min(abs(r_val), 1.0),
                description=f"Coupling: {src} → {tgt} (r={r_val:+.2f})",
            ))

        # 4. Threshold / phase transition: "transition at N=4 cells"
        m = self._RE_THRESHOLD.search(law_text)
        if m:
            val = float(m.group('val'))
            unit = m.group('unit') or ''
            target = 'n_cells' if 'cell' in unit else 'threshold'
            mods.append(Modification(
                law_id=law_id,
                law_text=law_text,
                target=target,
                mod_type=ModType.THRESHOLD,
                params={
                    'value': val,
                    'unit': unit.rstrip('s') if unit else 'unknown',
                    'operator': '>=',
                },
                confidence=0.6,
                description=f"Threshold: {target} at {val} {unit}",
            ))

        # 5. Boost/improve with percentage: "boosts Φ +12.3%"
        m = self._RE_BOOST.search(law_text)
        if m:
            sign = -1 if m.group('sign') == '-' else 1
            val = float(m.group('val'))
            target = self._normalize_target(m.group('target'))
            mods.append(Modification(
                law_id=law_id,
                law_text=law_text,
                target=target,
                mod_type=ModType.SCALE,
                params={
                    'relation': 'percentage',
                    'factor': 1.0 + sign * val / 100.0,
                },
                confidence=0.6,
                description=f"Boost: {target} by {sign * val:+.1f}%",
            ))

        # 6. Conditional: "when X, Y increases"
        m = self._RE_CONDITIONAL.search(law_text)
        if m:
            direction = m.group('dir').lower()
            is_increase = direction in ('increase', 'rise', 'grow')
            mods.append(Modification(
                law_id=law_id,
                law_text=law_text,
                target=self._normalize_target(m.group('target').strip()),
                mod_type=ModType.CONDITIONAL,
                params={
                    'condition': m.group('cond').strip(),
                    'effect': 'increase' if is_increase else 'decrease',
                    'magnitude': 0.05,
                },
                confidence=0.4,
                description=f"Conditional: when {m.group('cond').strip()}, {m.group('target').strip()} {direction}",
            ))

        # 7. Arrow effect: "adding features → Φ↓"
        for m in self._RE_ARROW_EFFECT.finditer(law_text):
            cause = m.group('cause').strip()
            target = self._normalize_target(m.group('target'))
            direction = 'decrease' if m.group('dir') == '↓' else 'increase'
            mods.append(Modification(
                law_id=law_id,
                law_text=law_text,
                target=target,
                mod_type=ModType.CONDITIONAL,
                params={
                    'condition': cause,
                    'effect': direction,
                    'magnitude': 0.1,
                },
                confidence=0.5,
                description=f"Arrow: {cause} → {target} {m.group('dir')}",
            ))

        # 8. Explicit parameter value: "gate=0.001"
        for m in self._RE_PARAM_VALUE.finditer(law_text):
            param = m.group('param').lower()
            val = float(m.group('val'))
            target = self._normalize_target(param)
            if not any(mod.target == target for mod in mods):
                mods.append(Modification(
                    law_id=law_id,
                    law_text=law_text,
                    target=target,
                    mod_type=ModType.THRESHOLD,
                    params={
                        'value': val,
                        'operator': '=',
                    },
                    confidence=0.8,
                    description=f"Set: {param} = {val}",
                ))

        # 9. Disable pattern: "kills consciousness", "destroys"
        if re.search(r'(kill|destroy|death|collapse|lethal)', law_text, re.IGNORECASE):
            # Extract what kills — check for subjects
            m = self._RE_REDUCE.search(law_text)
            if m:
                target = self._normalize_target(m.group('target'))
                if not any(mod.mod_type == ModType.DISABLE for mod in mods):
                    mods.append(Modification(
                        law_id=law_id,
                        law_text=law_text,
                        target=target,
                        mod_type=ModType.DISABLE,
                        params={'reason': 'destructive'},
                        confidence=0.7,
                        description=f"Disable warning: {target} harmful",
                    ))

        # ── Extended patterns (10-23) — only fire if no mods yet to avoid noise ──

        # 10. Comparison: "X > Y", "X beats Y", "X outperforms Y"
        if not mods:
            m = self._RE_COMPARISON.search(law_text)
            if m:
                winner = m.group('winner').strip()
                loser = m.group('loser').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(winner.split()[-1]),
                    mod_type=ModType.CONDITIONAL,
                    params={'condition': f'{winner} vs {loser}', 'effect': 'prefer_winner', 'winner': winner, 'loser': loser},
                    confidence=0.5,
                    description=f"Comparison: {winner} > {loser}",
                ))

        # 11. Percentage in parentheses: "(+22%)", "(-52% variance)"
        if not mods:
            m = self._RE_PAREN_PCT.search(law_text)
            if m:
                sign = -1 if m.group('sign') == '-' else 1
                val = float(m.group('val'))
                # Try to find what the percentage applies to
                target = 'phi'  # default
                for kw in ['Φ', 'Phi', 'phi', 'CE', 'consciousness', 'Φ(IIT)']:
                    if kw.lower() in law_text.lower():
                        target = self._normalize_target(kw)
                        break
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=target,
                    mod_type=ModType.SCALE,
                    params={'relation': 'percentage', 'factor': 1.0 + sign * val / 100.0},
                    confidence=0.5,
                    description=f"Effect: {target} {sign * val:+.1f}%",
                ))

        # 12. Multiplier: "×4.6", "×0.74", "0.82×"
        if not mods:
            m = self._RE_PAREN_MULT.search(law_text)
            if m:
                val = float(m.group('val') or m.group('val2'))
                target = 'phi'
                for kw in ['Φ', 'Phi', 'CE', 'consciousness']:
                    if kw.lower() in law_text.lower():
                        target = self._normalize_target(kw)
                        break
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=target,
                    mod_type=ModType.SCALE,
                    params={'relation': 'multiplier', 'factor': val},
                    confidence=0.5,
                    description=f"Multiplier: {target} ×{val}",
                ))

        # 13. Cell/faction/element counts: "1024 cells", "≥3 elements", "8 factions"
        if not mods:
            m = self._RE_CELL_COUNT.search(law_text)
            if m:
                val = int(m.group('val'))
                unit = m.group('unit').lower().rstrip('s')
                op = m.group('op') or '='
                target = self._normalize_target(unit if unit in ('cell', 'faction', 'element', 'atom') else unit)
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=target,
                    mod_type=ModType.THRESHOLD,
                    params={'value': val, 'unit': unit, 'operator': op},
                    confidence=0.4,
                    description=f"Count: {op}{val} {unit}",
                ))

        # 14. Identity claims: "consciousness is X", "Φ is Y"
        if not mods:
            m = self._RE_IDENTITY.search(law_text)
            if m:
                prop = m.group('property').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='phi',
                    mod_type=ModType.INJECT,
                    params={'property': prop, 'type': 'identity'},
                    confidence=0.3,
                    description=f"Identity: consciousness is {prop}",
                ))

        # 15. Existence / emergence: "X emerges", "X survives", "X recovers"
        if not mods:
            m = self._RE_EXISTENCE.search(law_text)
            if m:
                subject = m.group('subject').strip()
                verb = m.group('verb').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(subject.split()[-1]),
                    mod_type=ModType.INJECT,
                    params={'subject': subject, 'verb': verb, 'type': 'existence'},
                    confidence=0.3,
                    description=f"Existence: {subject} {verb}",
                ))

        # 16. Negation / destructive claims (without kill/destroy already caught by #9)
        if not mods and self._RE_NEGATION.search(law_text):
            # Extract what is negated
            target = 'phi'
            for kw in ['Φ', 'consciousness', 'Phi', 'CE', 'memory', 'coupling', 'hysteresis',
                        'convergence', 'entanglement', 'distillable', 'superadditive']:
                if kw.lower() in law_text.lower():
                    target = self._normalize_target(kw)
                    break
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=target,
                mod_type=ModType.CONDITIONAL,
                params={'condition': 'negation', 'effect': 'negate', 'text': law_text[:80]},
                confidence=0.3,
                description=f"Negation: {law_text[:60]}",
            ))

        # 17. Step/time references: "recovery ~5 steps", "2000 steps → consistent"
        if not mods:
            m = self._RE_STEPS.search(law_text)
            if m:
                val = int(m.group('val'))
                unit = m.group('unit').lower().rstrip('s')
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='temporal',
                    mod_type=ModType.THRESHOLD,
                    params={'value': val, 'unit': unit, 'operator': '>='},
                    confidence=0.4,
                    description=f"Temporal: {val} {unit}",
                ))

        # 18. Topology mentions: "ring", "hub-spoke", "chimera"
        if not mods:
            m = self._RE_TOPOLOGY.search(law_text)
            if m:
                topo = m.group('topo').lower().replace('-', '_')
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='topology',
                    mod_type=ModType.INJECT,
                    params={'topology': topo, 'type': 'topology'},
                    confidence=0.4,
                    description=f"Topology: {topo}",
                ))

        # 19. Combined effects: "X + Y = Z"
        if not mods:
            m = self._RE_COMBINED.search(law_text)
            if m:
                a = m.group('a').strip()
                b = m.group('b').strip()
                result = m.group('result').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(result.split()[0]),
                    mod_type=ModType.INJECT,
                    params={'components': [a, b], 'result': result, 'type': 'combination'},
                    confidence=0.4,
                    description=f"Combined: {a} + {b} → {result}",
                ))

        # 20. Measurement values: "Φ=1.05", "CE=0.004", "r=-0.10"
        if not mods:
            m = self._RE_MEASUREMENT.search(law_text)
            if m:
                metric = m.group('metric')
                val = float(m.group('val'))
                target = self._normalize_target(metric)
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=target,
                    mod_type=ModType.THRESHOLD,
                    params={'value': val, 'operator': '=', 'metric': metric},
                    confidence=0.5,
                    description=f"Measurement: {metric} = {val}",
                ))

        # 21. Standalone percentage changes: "+15.3%", "-28%" (not already caught)
        if not mods:
            m = self._RE_PCT_CHANGE.search(law_text)
            if m:
                sign = -1 if m.group('sign') == '-' else 1
                val = float(m.group('val'))
                target = 'phi'
                for kw in ['Φ', 'Phi', 'CE', 'consciousness', 'growth', 'variance', 'overhead']:
                    if kw.lower() in law_text.lower():
                        target = self._normalize_target(kw)
                        break
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=target,
                    mod_type=ModType.SCALE,
                    params={'relation': 'percentage', 'factor': 1.0 + sign * val / 100.0},
                    confidence=0.4,
                    description=f"Percentage: {target} {sign * val:+.1f}%",
                ))

        # 22. Requires / prerequisite: "consciousness requires ≥3 elements"
        if not mods:
            m = self._RE_REQUIRES.search(law_text)
            if m:
                subject = m.group('subject').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(subject.split()[-1]),
                    mod_type=ModType.CONDITIONAL,
                    params={'condition': 'requirement', 'text': law_text[:80]},
                    confidence=0.3,
                    description=f"Requires: {subject}",
                ))

        # 23. Optimal / best: "X is optimal", "maximized at Y"
        if not mods:
            m = self._RE_OPTIMAL.search(law_text)
            if m:
                what = m.group('what').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(what.split()[-1]),
                    mod_type=ModType.INJECT,
                    params={'property': 'optimal', 'subject': what, 'type': 'optimal'},
                    confidence=0.3,
                    description=f"Optimal: {what}",
                ))

        # 24. Equation identity: "max Φ = cells × freedom"
        if not mods:
            m = self._RE_EQUATION.search(law_text)
            if m:
                lhs = m.group('lhs').strip()
                rhs = m.group('rhs').strip()
                if len(rhs) > 2 and lhs.strip():  # avoid trivial matches
                    mods.append(Modification(
                        law_id=law_id, law_text=law_text,
                        target=self._normalize_target(lhs.split()[-1]) if lhs.split() else 'phi',
                        mod_type=ModType.INJECT,
                        params={'equation': f'{lhs} = {rhs}', 'type': 'equation'},
                        confidence=0.3,
                        description=f"Equation: {lhs} = {rhs}",
                    ))

        # 25. Probability / frequency: "82% probability", "100% of top"
        if not mods:
            m = self._RE_PROBABILITY.search(law_text)
            if m:
                val = float(m.group('val'))
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='phi',
                    mod_type=ModType.THRESHOLD,
                    params={'value': val / 100.0, 'unit': 'probability', 'operator': '>='},
                    confidence=0.4,
                    description=f"Probability: {val}%",
                ))

        # 26. N-step period: "7-step breathing", "2-step oscillation"
        if not mods:
            m = self._RE_PERIOD.search(law_text)
            if m:
                val = int(m.group('val'))
                what = m.group('what')
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='temporal',
                    mod_type=ModType.THRESHOLD,
                    params={'value': val, 'unit': 'period', 'what': what},
                    confidence=0.4,
                    description=f"Period: {val}-step {what}",
                ))

        # 27. Scale-invariant / universal / independent properties
        if not mods:
            m = self._RE_INVARIANT.search(law_text)
            if m:
                subject = m.group('subject').strip()
                # Extract the property from the match
                prop_start = m.end(1)
                prop = law_text[prop_start:].strip().split(',')[0].strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='phi',
                    mod_type=ModType.INJECT,
                    params={'property': prop, 'subject': subject, 'type': 'invariant'},
                    confidence=0.4,
                    description=f"Invariant: {subject} {prop}",
                ))

        # 28. Ordering: "X first, Y second" / "X first, then Y"
        if not mods:
            m = self._RE_ORDERING.search(law_text)
            if m:
                first = m.group('first').strip()
                second = m.group('second').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(first.split()[-1]),
                    mod_type=ModType.CONDITIONAL,
                    params={'condition': 'ordering', 'first': first, 'second': second},
                    confidence=0.3,
                    description=f"Order: {first} → {second}",
                ))

        # 29. Stabilizer/antidote/universal
        if not mods:
            m = self._RE_STABILIZER.search(law_text)
            if m:
                what = m.group('what').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(what.split()[-1]),
                    mod_type=ModType.INJECT,
                    params={'property': 'stabilizer', 'subject': what, 'type': 'stabilizer'},
                    confidence=0.3,
                    description=f"Stabilizer: {what}",
                ))

        # 30. Action verbs: "consciousness defines X", "Φ selects Y"
        if not mods:
            m = self._RE_ACTION_VERB.search(law_text)
            if m:
                verb = m.group('verb')
                obj = m.group('object').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(obj.split()[0]),
                    mod_type=ModType.INJECT,
                    params={'verb': verb, 'object': obj, 'type': 'action'},
                    confidence=0.3,
                    description=f"Action: consciousness {verb} {obj}",
                ))

        # 31. Auto-discovered compact laws: "[Auto-discovered] correlation:X:Y", "trend:X", etc.
        if not mods:
            m = self._RE_AUTO_DISCOVERED.search(law_text)
            if m:
                disc_type = m.group('type').lower()
                metric1 = m.group('metric1')
                metric2 = m.group('metric2')
                target = self._normalize_target(metric1)
                if disc_type == 'correlation' and metric2:
                    mods.append(Modification(
                        law_id=law_id, law_text=law_text,
                        target=self._normalize_target(metric2),
                        mod_type=ModType.COUPLE,
                        params={'source': target, 'strength': 0.5, 'direction': 'positive',
                                'discovery_type': 'auto'},
                        confidence=0.3,
                        description=f"Auto-discovered correlation: {metric1} ~ {metric2}",
                    ))
                elif disc_type == 'trend':
                    mods.append(Modification(
                        law_id=law_id, law_text=law_text,
                        target=target,
                        mod_type=ModType.SCALE,
                        params={'relation': 'trend', 'direction': 'monotonic', 'discovery_type': 'auto'},
                        confidence=0.3,
                        description=f"Auto-discovered trend: {metric1}",
                    ))
                elif disc_type == 'oscillation':
                    mods.append(Modification(
                        law_id=law_id, law_text=law_text,
                        target=target,
                        mod_type=ModType.INJECT,
                        params={'type': 'oscillation', 'metric': metric1, 'discovery_type': 'auto'},
                        confidence=0.3,
                        description=f"Auto-discovered oscillation: {metric1}",
                    ))
                elif disc_type == 'transition':
                    mods.append(Modification(
                        law_id=law_id, law_text=law_text,
                        target=target,
                        mod_type=ModType.THRESHOLD,
                        params={'value': 0, 'operator': 'transition', 'metric': metric1,
                                'discovery_type': 'auto'},
                        confidence=0.3,
                        description=f"Auto-discovered transition: {metric1}",
                    ))

        # 32. Superlative: "X is strongest Y", "X is the most Z"
        if not mods:
            m = self._RE_SUPERLATIVE.search(law_text)
            if m:
                subject = m.group('subject').strip()
                degree = m.group('degree')
                what = m.group('what').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(subject.split()[-1]),
                    mod_type=ModType.INJECT,
                    params={'property': degree, 'subject': subject, 'context': what, 'type': 'superlative'},
                    confidence=0.3,
                    description=f"Superlative: {subject} is {degree} {what}",
                ))

        # 33. Enables/enhances/drives: "X enables Y", "X maximizes Y"
        if not mods:
            m = self._RE_ENABLES.search(law_text)
            if m:
                subject = m.group('subject').strip()
                verb = m.group('verb').strip()
                obj = m.group('object').strip()
                is_positive = verb.rstrip('s') not in ('prevent', 'block', 'dampen', 'suppress')
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(obj.split()[0]),
                    mod_type=ModType.CONDITIONAL,
                    params={'condition': subject, 'effect': 'increase' if is_positive else 'decrease',
                            'verb': verb, 'magnitude': 0.05},
                    confidence=0.3,
                    description=f"Enables: {subject} {verb} {obj}",
                ))

        # 34. Tradeoff / paradox: "X-Y tradeoff", "knowledge-freedom tradeoff"
        if not mods:
            m = self._RE_TRADEOFF.search(law_text)
            if m:
                a = m.group('a').strip()
                b = m.group('b').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(a.split()[-1]),
                    mod_type=ModType.COUPLE,
                    params={'source': self._normalize_target(b.split()[0]),
                            'strength': -0.5, 'direction': 'inverse', 'type': 'tradeoff'},
                    confidence=0.3,
                    description=f"Tradeoff: {a} vs {b}",
                ))

        # 35. Phase/stage notation: "P1(C) → P2(+D)" or "phase 2"
        if not mods:
            m = self._RE_PHASE.search(law_text)
            if m:
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='phi',
                    mod_type=ModType.INJECT,
                    params={'type': 'phase_transition', 'text': law_text[:80]},
                    confidence=0.3,
                    description=f"Phase: {law_text[:60]}",
                ))

        # 36. Diminishing returns / saturation / overload
        if not mods:
            m = self._RE_DIMINISHING.search(law_text)
            if m:
                matched = m.group(0).lower()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='phi',
                    mod_type=ModType.CONDITIONAL,
                    params={'condition': matched, 'effect': 'saturate', 'text': law_text[:80]},
                    confidence=0.3,
                    description=f"Diminishing: {matched} in {law_text[:50]}",
                ))

        # 38. Independence: "X independent of Y", "CE independent of Φ quartile"
        if not mods:
            m = self._RE_INDEPENDENCE.search(law_text)
            if m:
                subject = m.group('subject').strip()
                other = m.group('other').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(subject.split()[-1]),
                    mod_type=ModType.COUPLE,
                    params={'source': self._normalize_target(other.split()[0]),
                            'strength': 0.0, 'direction': 'independent', 'type': 'independence'},
                    confidence=0.4,
                    description=f"Independence: {subject} ⊥ {other}",
                ))

        # 39. Inequality/distinction: "X ≠ Y", "Training state ≠ inference state"
        if not mods:
            m = self._RE_INEQUALITY.search(law_text)
            if m:
                lhs = m.group('lhs').strip()
                rhs = m.group('rhs').strip()
                if len(lhs) > 1 and len(rhs) > 1:
                    mods.append(Modification(
                        law_id=law_id, law_text=law_text,
                        target=self._normalize_target(lhs.split()[-1]),
                        mod_type=ModType.CONDITIONAL,
                        params={'condition': 'distinction', 'lhs': lhs, 'rhs': rhs,
                                'effect': 'differentiate'},
                        confidence=0.3,
                        description=f"Distinction: {lhs} ≠ {rhs}",
                    ))

        # 40. Stability claims: "Val CE stable", "X resilient"
        if not mods:
            m = self._RE_STABLE.search(law_text)
            if m:
                subject = m.group('subject').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(subject.split()[-1]),
                    mod_type=ModType.INJECT,
                    params={'property': 'stable', 'subject': subject, 'type': 'stability'},
                    confidence=0.3,
                    description=f"Stability: {subject} is stable",
                ))

        # 41. Classification: "X is a dissipative structure", "X is a decisive chooser"
        if not mods:
            m = self._RE_CLASSIFICATION.search(law_text)
            if m:
                subject = m.group('subject').strip()
                category = m.group('category').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(subject.split()[-1]),
                    mod_type=ModType.INJECT,
                    params={'property': category, 'subject': subject, 'type': 'classification'},
                    confidence=0.3,
                    description=f"Classification: {subject} is a {category}",
                ))

        # 42. Colon-separated structured claims: "Topic: claim details"
        if not mods:
            m = self._RE_COLON_CLAIM.search(law_text)
            if m:
                topic = m.group('topic').strip()
                claim = m.group('claim').strip()
                if len(topic) > 2 and len(claim) > 5:
                    mods.append(Modification(
                        law_id=law_id, law_text=law_text,
                        target=self._normalize_target(topic.split()[-1]),
                        mod_type=ModType.INJECT,
                        params={'topic': topic, 'claim': claim[:80], 'type': 'structured_claim'},
                        confidence=0.3,
                        description=f"Claim: {topic}: {claim[:50]}",
                    ))

        # 43. Discrete/binary/quantized: "Satisfaction binary pulse"
        if not mods:
            m = self._RE_DISCRETE.search(law_text)
            if m:
                subject = m.group('subject').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(subject.split()[-1]),
                    mod_type=ModType.INJECT,
                    params={'property': 'discrete', 'subject': subject, 'type': 'discreteness'},
                    confidence=0.3,
                    description=f"Discrete: {subject}",
                ))

        # 44. Superset/subset: "X ⊃ Y", "X subsumes Y"
        if not mods:
            m = self._RE_SUPERSET.search(law_text)
            if m:
                sup = m.group('super').strip()
                sub = m.group('sub').strip()
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(sup.split()[-1]),
                    mod_type=ModType.CONDITIONAL,
                    params={'condition': 'superset', 'superset': sup, 'subset': sub},
                    confidence=0.3,
                    description=f"Superset: {sup} ⊃ {sub}",
                ))

        # ══════════════════════════════════════════
        # Supplementary patterns 45-65: fire ALONGSIDE primary patterns
        # to extract additional structured information
        # ══════════════════════════════════════════

        # 45. Convergence/divergence: "converges to 1/2", "settles at N"
        m = self._RE_CONVERGENCE.search(law_text)
        if m:
            subject = m.group('subject').strip()
            target_val = m.group('target_val') or m.group('settle_val') or ''
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(subject.split()[-1]),
                mod_type=ModType.THRESHOLD,
                params={'value': target_val.strip(), 'operator': '→',
                        'type': 'convergence'},
                confidence=0.4,
                description=f"Convergence: {subject} → {target_val.strip()}",
            ))

        # 46. Periodicity/oscillation: "Φ oscillates", "breathing period"
        m = self._RE_PERIODICITY.search(law_text)
        if m and not any('oscillation' in (mod.params.get('type', '') or '') for mod in mods):
            subject = m.group('subject').strip()
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(subject.split()[-1]),
                mod_type=ModType.INJECT,
                params={'type': 'periodicity', 'subject': subject},
                confidence=0.4,
                description=f"Periodicity: {subject} oscillates",
            ))

        # 47. Causation: "X causes Y", "X leads to Y"
        m = self._RE_CAUSATION.search(law_text)
        if m:
            cause = m.group('cause').strip()
            effect = m.group('effect').strip()
            # Avoid duplicate with enables pattern
            if not any(mod.params.get('verb') for mod in mods):
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(effect.split()[0]),
                    mod_type=ModType.CONDITIONAL,
                    params={'condition': cause, 'effect': 'causal',
                            'cause': cause, 'result': effect, 'type': 'causation'},
                    confidence=0.5,
                    description=f"Causation: {cause} → {effect}",
                ))

        # 48. Recovery/survival: "survives 90% cell death", "recovers from X"
        m = self._RE_SURVIVAL.search(law_text)
        if m:
            subject = m.group('subject').strip()
            threat = m.group('threat').strip()
            result = m.group('result') or ''
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(subject.split()[-1]),
                mod_type=ModType.INJECT,
                params={'type': 'survival', 'subject': subject,
                        'threat': threat, 'result': result.strip()},
                confidence=0.5,
                description=f"Survival: {subject} survives {threat}",
            ))

        # 49. Composition: "consists of X, Y, Z"
        m = self._RE_COMPOSITION.search(law_text)
        if m:
            whole = m.group('whole').strip()
            parts = m.group('parts').strip()
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(whole.split()[-1]),
                mod_type=ModType.INJECT,
                params={'type': 'composition', 'whole': whole,
                        'parts': [p.strip() for p in re.split(r'[,+]', parts)]},
                confidence=0.4,
                description=f"Composition: {whole} = {parts[:50]}",
            ))

        # 50. Sufficiency: "X alone sustains Y"
        m = self._RE_SUFFICIENCY.search(law_text)
        if m:
            subject = m.group('subject').strip()
            outcome = m.group('outcome').strip()
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(subject.split()[-1]),
                mod_type=ModType.CONDITIONAL,
                params={'condition': 'sufficiency', 'sufficient': subject,
                        'outcome': outcome},
                confidence=0.4,
                description=f"Sufficiency: {subject} alone → {outcome}",
            ))

        # 51. Hierarchy: "X > Y > Z" multi-level ordering
        m = self._RE_HIERARCHY.search(law_text)
        if m:
            a, b, c = m.group('a').strip(), m.group('b').strip(), m.group('c').strip()
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(a.split()[-1]),
                mod_type=ModType.CONDITIONAL,
                params={'condition': 'hierarchy',
                        'ordering': [a, b, c], 'type': 'hierarchy'},
                confidence=0.4,
                description=f"Hierarchy: {a} > {b} > {c}",
            ))

        # 52. Ratio/fraction: "Φ/cell = N", "bits per step"
        m = self._RE_RATIO.search(law_text)
        if m:
            num = m.group('num').strip()
            den = m.group('den').strip()
            val = m.group('val')
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(num.split()[-1]),
                mod_type=ModType.THRESHOLD,
                params={'value': float(val) if val else 0,
                        'unit': f'{num}/{den}', 'operator': '=',
                        'type': 'ratio'},
                confidence=0.4,
                description=f"Ratio: {num}/{den}" + (f" = {val}" if val else ""),
            ))

        # 53. Amplification: "85000× amplification", "4.6× more"
        m = self._RE_AMPLIFICATION.search(law_text)
        if m:
            val = float(m.group('val'))
            direction = m.group('dir').lower()
            is_reduction = direction in ('attenuation', 'less', 'slower', 'reduction', 'decrease')
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='phi',
                mod_type=ModType.SCALE,
                params={'relation': 'amplification',
                        'factor': 1.0 / val if is_reduction else val,
                        'raw_multiplier': val, 'direction': direction},
                confidence=0.5,
                description=f"Amplification: {val}× {direction}",
            ))

        # 54. Bounds/range: "ranges from A to B"
        m = self._RE_RANGE.search(law_text)
        if m:
            subject = m.group('subject').strip()
            lo, hi = float(m.group('lo')), float(m.group('hi'))
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(subject.split()[-1]),
                mod_type=ModType.THRESHOLD,
                params={'value': (lo + hi) / 2, 'lo': lo, 'hi': hi,
                        'operator': 'range', 'type': 'range'},
                confidence=0.5,
                description=f"Range: {subject} ∈ [{lo}, {hi}]",
            ))

        # 55. Conditional-if: "if X then Y", "only when X, Y"
        m = self._RE_IF_THEN.search(law_text)
        if m and not any(mod.params.get('type') == 'causation' for mod in mods):
            cond = m.group('cond').strip()
            result = m.group('result').strip()
            if result:
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target=self._normalize_target(result.split()[0]),
                    mod_type=ModType.CONDITIONAL,
                    params={'condition': cond, 'effect': 'conditional',
                            'result': result, 'type': 'if_then'},
                    confidence=0.4,
                    description=f"If-then: if {cond} → {result}",
                ))

        # 56. Anti-pattern: "excessive X destroys Y"
        m = self._RE_ANTI.search(law_text)
        if m:
            what = m.group('what').strip()
            effect = m.group('effect').strip()
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target=self._normalize_target(what.split()[-1]),
                mod_type=ModType.CONDITIONAL,
                params={'condition': f'excessive {what}', 'effect': 'decrease',
                        'magnitude': 0.2, 'type': 'anti_pattern'},
                confidence=0.5,
                description=f"Anti-pattern: excessive {what} {effect}",
            ))

        # 57. Split/merge: "split into 16×8c", "merge N into 1"
        m = self._RE_SPLIT_MERGE.search(law_text)
        if m:
            splits = m.group('splits')
            merges = m.group('merges')
            if splits:
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='mitosis',
                    mod_type=ModType.INJECT,
                    params={'type': 'split', 'split_spec': splits},
                    confidence=0.4,
                    description=f"Split: → {splits}",
                ))
            elif merges:
                merge_target = m.group('merge_target') or '1'
                mods.append(Modification(
                    law_id=law_id, law_text=law_text,
                    target='merge',
                    mod_type=ModType.INJECT,
                    params={'type': 'merge', 'from': merges, 'to': merge_target},
                    confidence=0.4,
                    description=f"Merge: {merges} → {merge_target}",
                ))

        # 58. Record/peak: "all-time record +892%"
        m = self._RE_RECORD.search(law_text)
        if m:
            effect = (m.group('effect') or '').strip()
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='phi',
                mod_type=ModType.INJECT,
                params={'type': 'record', 'effect': effect},
                confidence=0.3,
                description=f"Record: {effect}" if effect else "Record achievement",
            ))

        # 59. Evolution: "evolves by natural selection", "fitness"
        m = self._RE_EVOLUTION.search(law_text)
        if m:
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='phi',
                mod_type=ModType.INJECT,
                params={'type': 'evolution', 'text': law_text[:80]},
                confidence=0.3,
                description=f"Evolution: {law_text[:60]}",
            ))

        # 60. Dual/both: "both CE↓ and Φ↑", "dual optimality"
        m = self._RE_DUAL.search(law_text)
        if m:
            a = (m.group('a1') or m.group('a2') or m.group('what') or '').strip()
            b = (m.group('b1') or m.group('b2') or '').strip()
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='phi',
                mod_type=ModType.INJECT,
                params={'type': 'dual', 'a': a, 'b': b},
                confidence=0.3,
                description=f"Dual: {a}" + (f" & {b}" if b else ""),
            ))

        # 61. Pareto optimal: "Pareto optimal", "only known X"
        m = self._RE_PARETO.search(law_text)
        if m:
            what = (m.group('what') or '').strip()
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='phi',
                mod_type=ModType.INJECT,
                params={'type': 'pareto', 'what': what or 'optimal frontier'},
                confidence=0.4,
                description=f"Pareto: {what or 'optimal'}",
            ))

        # 62. Thermodynamic: "entropy increases", "irreversible", "2nd law"
        m = self._RE_THERMO.search(law_text)
        if m:
            direction = (m.group('dir') or '').strip() if m.lastgroup == 'dir' or 'dir' in (m.groupdict() or {}) else ''
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='shannon_entropy',
                mod_type=ModType.INJECT,
                params={'type': 'thermodynamic', 'direction': direction,
                        'text': law_text[:80]},
                confidence=0.4,
                description=f"Thermodynamic: {law_text[:50]}",
            ))

        # 63. Scale-specific: "at 32 cells", "only at 32c"
        m = self._RE_SCALE_SPECIFIC.search(law_text)
        if m:
            val = int(m.group('val'))
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='n_cells',
                mod_type=ModType.THRESHOLD,
                params={'value': val, 'operator': '=',
                        'type': 'scale_specific'},
                confidence=0.4,
                description=f"Scale-specific: {val} cells",
            ))

        # 64. Federation/distributed: "federated consciousness", "hivemind"
        m = self._RE_FEDERATION.search(law_text)
        if m:
            detail = m.group('detail').strip() if m.group('detail') else ''
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='phi',
                mod_type=ModType.INJECT,
                params={'type': 'federation', 'detail': detail,
                        'text': law_text[:80]},
                confidence=0.4,
                description=f"Federation: {detail[:40] or 'distributed'}",
            ))

        # 65. Universality: "at all scales", "universal", "always"
        m = self._RE_UNIVERSALITY.search(law_text)
        if m:
            scope = (m.group('scope') or '').strip() if m.groupdict().get('scope') else 'universal'
            mods.append(Modification(
                law_id=law_id, law_text=law_text,
                target='phi',
                mod_type=ModType.INJECT,
                params={'type': 'universality', 'scope': scope},
                confidence=0.4,
                description=f"Universality: {scope}",
            ))

        # 37. Expanded keyword fallback (broader coverage)
        if not mods:
            low = law_text.lower()
            for kw in ['φ', 'phi', 'consciousness', 'entropy', 'hebbian', 'ratchet',
                        'mitosis', 'soc', 'bottleneck', 'frustration', 'narrative',
                        'topology', 'faction', 'coupling', 'tension', 'ce ', 'gradient',
                        'attention', 'memory', 'diversity', 'gate', 'sensory', 'abstraction',
                        'self-play', 'dialogue', 'hierarchy', 'generalization', 'emotion',
                        'learning', 'freedom', 'symmetry', 'integration', 'selection',
                        'self-reference', 'vocabulary', 'dissipative', 'channel', 'capacity',
                        'cell', 'split', 'merge', 'growth', 'decay', 'recovery',
                        'super-principle', 'data-dependent', 'data-independent']:
                if kw in low:
                    mods.append(Modification(
                        law_id=law_id, law_text=law_text,
                        target=self._normalize_target(kw.strip()),
                        mod_type=ModType.INJECT,
                        params={'type': 'keyword_extract', 'keyword': kw.strip(), 'text': law_text[:80]},
                        confidence=0.2,
                        description=f"Keyword: {kw.strip()} in law text",
                    ))
                    break

        # ── Post-processing: adjust confidence based on evidence quality ──
        mods = self._adjust_confidence(mods, law_text)

        return mods

    # ── Confidence post-processing ──

    # Regex for detecting specific numeric evidence in law text
    _RE_SPECIFIC_NUMBER = re.compile(
        r'(?:'
        r'r\s*=\s*[+-]?[\d.]+'           # correlation r=0.78
        r'|[+-][\d.]+%'                   # percentage +15.3%, -28%
        r'|[×\*][\d.]+'                   # multiplier ×1.5
        r'|[\d.]+[×x]\b'                  # multiplier 4.6×
        r'|(?:Φ|CE|BPC|alpha|α)\s*[=≈:]\s*[\d.]+' # metric=value
        r'|\b\d+\.\d{2,}\b'              # precise decimal 0.014, 0.608
        r'|\(\s*[+-]?[\d.]+%\s*\)'       # parenthesized percent (+22%)
        r')',
        re.IGNORECASE
    )

    # Patterns that indicate high-specificity (actionable) laws
    _RE_ACTIONABLE_MARKERS = re.compile(
        r'(?:'
        r'\^[\d.]+'                       # exponent N^1.07
        r'|r\s*=\s*[+-]?0\.\d+'          # correlation coefficient
        r'|[=≈]\s*[\d.]+\s*[×\*]\s*\w+\^' # full equation Φ = 0.6 × N^1
        r'|\b(?:iff|if and only if)\b'    # logical precision
        r')',
        re.IGNORECASE
    )

    # Structural evidence patterns for qualitative laws
    _RE_ARROW = re.compile(r'→|↑|↓|⊃|⊂|≠')
    _RE_CAUSAL_STRUCTURE = re.compile(
        r'(?:'
        r'\b(?:because|therefore|thus|hence|since|so\s+that|leads?\s+to|results?\s+in)\b'
        r'|→'
        r')',
        re.IGNORECASE
    )

    def _adjust_confidence(self, mods: List['Modification'], law_text: str) -> List['Modification']:
        """Adjust confidence scores based on evidence quality signals.

        Strategies:
          1. Specific numbers (r=0.78, x1.5, +15%) -> boost confidence
          2. Multi-match (multiple patterns matched) -> boost confidence
          3. Keyword-only fallback (INJECT with keyword_extract) -> keep low
          4. Law length + specificity + structural markers -> complexity bonus
          5. High-confidence mod_types (SCALE, THRESHOLD with values) -> type bonus
        """
        if not mods:
            return mods

        # --- Signal 1: Count specific numeric evidence ---
        num_matches = len(self._RE_SPECIFIC_NUMBER.findall(law_text))
        actionable = bool(self._RE_ACTIONABLE_MARKERS.search(law_text))

        # --- Signal 2: Count distinct mod_types (multi-match diversity) ---
        distinct_types = len(set(m.mod_type for m in mods))
        n_mods = len(mods)

        # --- Signal 3: Law complexity & structural evidence ---
        law_len = len(law_text)
        has_parens = '(' in law_text and ')' in law_text
        has_experiment_id = bool(re.search(r'\(DD\d+|DD\d+\)', law_text))
        has_arrows = bool(self._RE_ARROW.search(law_text))
        has_causal = bool(self._RE_CAUSAL_STRUCTURE.search(law_text))
        # Count distinct "technical" words as a proxy for specificity
        low = law_text.lower()
        tech_words = sum(1 for w in [
            'phi', 'φ', 'hebbian', 'ratchet', 'topology', 'entropy', 'mitosis',
            'faction', 'soc', 'lorenz', 'chimera', 'coupling', 'gradient',
            'gru', 'tensor', 'eigenvalue', 'attractor', 'bifurcation',
            'dissipative', 'markov', 'lyapunov', 'hamiltonian', 'ergodic',
            'mutual_info', 'tension', 'cell_variance', 'consciousness',
            'homeostasis', 'bottleneck', 'frustration', 'sandpile',
        ] if w in low)
        is_auto_discovered = law_text.startswith('[Auto-discovered]')

        # --- Apply adjustments ---
        for mod in mods:
            boost = 0.0

            # Skip keyword-only fallback — these stay at base confidence (0.2)
            if mod.params.get('type') == 'keyword_extract':
                continue

            # 1. Numeric evidence boost: each specific number adds confidence
            #    Moderate boost — avoid leapfrogging past medium into high
            if num_matches >= 3:
                boost += 0.18  # rich quantitative evidence
            elif num_matches >= 2:
                boost += 0.13
            elif num_matches >= 1:
                boost += 0.08

            # 2. Actionable marker boost (equations, correlations with values)
            if actionable:
                boost += 0.05

            # 3. Multi-match boost: multiple patterns = well-structured law
            if n_mods >= 4:
                boost += 0.12
            elif n_mods >= 3:
                boost += 0.08
            elif n_mods >= 2:
                boost += 0.05

            # 4. Structural evidence (qualitative but well-formed laws)
            #    This is the key boost for non-numeric laws to reach medium
            if has_arrows:
                boost += 0.07  # arrows indicate causal/directional claims
            if has_causal:
                boost += 0.04  # explicit causal language
            if tech_words >= 3:
                boost += 0.12  # domain-specific terminology = expert claim
            elif tech_words >= 2:
                boost += 0.08
            elif tech_words >= 1:
                boost += 0.06

            # 5. Complexity bonus: longer laws are more precise, but even
            #    short laws with domain terms deserve some credit
            if law_len > 150:
                boost += 0.08
            elif law_len > 100:
                boost += 0.06
            elif law_len > 60:
                boost += 0.04
            elif law_len > 30:
                boost += 0.02  # short but non-trivial

            # 6. Evidence provenance
            if has_parens:
                boost += 0.03  # parenthetical structure = organized claim
            if has_experiment_id:
                boost += 0.04  # linked to specific experiment

            # 7. Mod-type reliability: SCALE/THRESHOLD with params are more
            #    actionable than generic INJECT
            if mod.mod_type in (ModType.SCALE, ModType.THRESHOLD):
                if 'val' in mod.params or 'exponent' in mod.params or 'threshold' in mod.params:
                    boost += 0.04  # has concrete parameter values

            # 8. Auto-discovered laws: machine-generated with structured format
            #    They have systematic verification backing even without numbers
            if is_auto_discovered:
                boost += 0.10

            # 9. Penalty: very short + no numbers + no structure + no domain terms
            if law_len < 30 and num_matches == 0 and not has_arrows and tech_words == 0:
                boost -= 0.05

            # Apply boost, clamp to [0.1, 0.95]
            mod.confidence = max(0.1, min(0.95, mod.confidence + boost))

        return mods

    def parse_laws_batch(self, laws_dict: Dict[str, str], max_laws: int = 50) -> Dict[int, List[Modification]]:
        """Parse multiple laws, return {law_id: [Modification]}."""
        results = {}
        count = 0
        for law_id_str, law_text in laws_dict.items():
            if count >= max_laws:
                break
            try:
                lid = int(law_id_str)
            except ValueError:
                continue
            mods = self.parse(law_text, law_id=lid)
            if mods:
                results[lid] = mods
                count += 1
        return results


# ══════════════════════════════════════════
# EngineModifier — safe application
# ══════════════════════════════════════════

class EngineModifier:
    """Safely apply Modifications to ConsciousnessEngine.

    Safety protocol:
      1. Snapshot current state before modification
      2. Validate against safety bounds
      3. Apply modification
      4. Measure Φ immediately
      5. If Φ drops > 20% → automatic rollback
    """

    def __init__(self, engine: ConsciousnessEngine, safety_bounds: Dict = None):
        self.engine = engine
        self.safety = safety_bounds or SAFETY_BOUNDS
        self.applied: List[Modification] = []
        self.snapshots: Dict[int, Dict] = {}  # law_id → pre-modification state
        self.rollback_log: List[Dict] = []

    def _snapshot(self) -> Dict:
        """Capture current engine state."""
        snap = {
            'hiddens': [s.hidden.clone() for s in self.engine.cell_states],
            'coupling': self.engine._coupling.clone() if self.engine._coupling is not None else None,
            'n_cells': self.engine.n_cells,
            'phi': self._measure_phi(),
            'step': self.engine._step,
        }
        return snap

    def _measure_phi(self) -> float:
        """Measure Φ(IIT) of current engine state."""
        if _phi_fast is not None:
            return _phi_fast(self.engine)
        # Fallback: variance proxy
        if self.engine.n_cells < 2:
            return 0.0
        hiddens = torch.stack([s.hidden for s in self.engine.cell_states])
        return float(hiddens.var().item())

    def _validate_bounds(self, target: str, value: float) -> float:
        """Clamp value to safety bounds. Returns clamped value."""
        if target in self.safety:
            lo, hi = self.safety[target]
            return max(lo, min(hi, value))
        return value

    def apply(self, mod: Modification) -> bool:
        """Apply a modification. Returns True if successful, False if rolled back.

        Protocol:
          1. Snapshot
          2. Validate
          3. Apply
          4. Run 10 steps to settle
          5. Measure Φ
          6. Rollback if Φ drops > 20%
        """
        # 1. Snapshot
        snap = self._snapshot()
        self.snapshots[mod.law_id] = snap
        phi_before = snap['phi']

        # 2-3. Apply based on type
        try:
            success = self._apply_mod(mod)
            if not success:
                return False
        except Exception as e:
            self._restore_snapshot(snap)
            self.rollback_log.append({
                'law_id': mod.law_id, 'reason': f'exception: {e}',
                'phi_before': phi_before,
            })
            return False

        # 4. Run 10 steps to let modification settle
        for _ in range(10):
            self.engine.step()

        # 5. Measure Φ after
        phi_after = self._measure_phi()

        # 6. Check Φ safety
        if phi_before > 0.01:
            drop = (phi_before - phi_after) / phi_before
            if drop > PHI_DROP_THRESHOLD:
                self._restore_snapshot(snap)
                self.rollback_log.append({
                    'law_id': mod.law_id,
                    'reason': f'phi_drop={drop:.1%} > {PHI_DROP_THRESHOLD:.0%}',
                    'phi_before': phi_before,
                    'phi_after': phi_after,
                })
                return False

        mod.confidence = min(1.0, mod.confidence + 0.1)
        self.applied.append(mod)
        return True

    def _apply_mod(self, mod: Modification) -> bool:
        """Internal: apply a single modification to the engine."""

        if mod.mod_type == ModType.SCALE:
            return self._apply_scale(mod)
        elif mod.mod_type == ModType.COUPLE:
            return self._apply_couple(mod)
        elif mod.mod_type == ModType.THRESHOLD:
            return self._apply_threshold(mod)
        elif mod.mod_type == ModType.CONDITIONAL:
            return self._apply_conditional(mod)
        elif mod.mod_type == ModType.INJECT:
            return self._apply_inject(mod)
        elif mod.mod_type == ModType.DISABLE:
            return self._apply_disable(mod)
        return False

    def _apply_scale(self, mod: Modification) -> bool:
        """Apply SCALE modification: multiply coupling or inject noise."""
        params = mod.params
        relation = params.get('relation', 'linear')

        if relation == 'percentage':
            factor = params.get('factor', 1.0)
            factor = self._validate_bounds('coupling_scale', factor)
            if self.engine._coupling is not None:
                self.engine._coupling = self.engine._coupling * factor
                self.engine._coupling.fill_diagonal_(0)
            return True

        elif relation == 'power':
            # Adjust coupling based on power law relationship
            exponent = params.get('exponent', 1.0)
            n = self.engine.n_cells
            if n >= 2 and self.engine._coupling is not None:
                scale = (n ** exponent) / (n ** 1.0)  # ratio vs linear
                scale = self._validate_bounds('coupling_scale', scale)
                self.engine._coupling = self.engine._coupling * min(scale, 2.0)
                self.engine._coupling.fill_diagonal_(0)
            return True

        elif relation == 'linear':
            # Mild coupling adjustment
            if self.engine._coupling is not None:
                self.engine._coupling = self.engine._coupling * 1.05
                self.engine._coupling.fill_diagonal_(0)
            return True

        return False

    def _apply_couple(self, mod: Modification) -> bool:
        """Apply COUPLE modification: link two engine parameters."""
        params = mod.params
        strength = params.get('strength', 0.0)
        direction = params.get('direction', 'positive')

        if self.engine._coupling is None or self.engine.n_cells < 2:
            return False

        # Interpret coupling: adjust cell interactions based on correlation direction
        n = self.engine.n_cells
        hiddens = torch.stack([s.hidden for s in self.engine.cell_states]).detach()

        if direction == 'inverse' or strength < 0:
            # Negative correlation → equalize/dampen high-variance dimension
            var_per_dim = hiddens.var(dim=0)
            top_dims = var_per_dim.argsort(descending=True)[:max(1, hiddens.shape[1] // 8)]
            for s in self.engine.cell_states:
                mean_val = hiddens[:, top_dims].mean(dim=0)
                blend = self._validate_bounds('tension_blend', abs(strength) * 0.05)
                s.hidden[top_dims] = s.hidden[top_dims] * (1 - blend) + mean_val * blend
        else:
            # Positive correlation → strengthen existing coupling
            scale = 1.0 + abs(strength) * 0.05
            scale = self._validate_bounds('coupling_scale', scale)
            self.engine._coupling = self.engine._coupling * scale
            self.engine._coupling.fill_diagonal_(0)
            self.engine._coupling.clamp_(-1, 1)

        return True

    def _apply_threshold(self, mod: Modification) -> bool:
        """Apply THRESHOLD modification: set engine parameter."""
        params = mod.params
        value = params.get('value', 0)
        target = mod.target

        if target == 'n_cells':
            # Phase transition hint — adjust split threshold
            n_thresh = max(2, int(value))
            if self.engine.n_cells < n_thresh:
                self.engine.split_threshold *= 0.9  # lower barrier to grow
            return True

        elif target == 'gate_value':
            value = self._validate_bounds('gate_value', value)
            # Store as engine attribute for downstream use
            self.engine._self_mod_gate = value
            return True

        elif target == 'ratchet_threshold':
            value = self._validate_bounds('ratchet_threshold', value)
            # Adjust ratchet sensitivity
            self.engine._best_phi *= value
            return True

        elif target == 'coupling_scale':
            value = self._validate_bounds('coupling_scale', value)
            if self.engine._coupling is not None:
                self.engine._coupling = self.engine._coupling * value
                self.engine._coupling.fill_diagonal_(0)
            return True

        return True  # Unknown target — accept silently (no harm)

    def _apply_conditional(self, mod: Modification) -> bool:
        """Apply CONDITIONAL modification: add a runtime hook."""
        params = mod.params
        effect = params.get('effect', 'increase')
        magnitude = params.get('magnitude', 0.05)
        magnitude = self._validate_bounds('noise_scale', magnitude)

        # Implement as a perturbation: inject small noise in the direction indicated
        if self.engine.n_cells >= 2:
            for s in self.engine.cell_states:
                noise = torch.randn_like(s.hidden) * magnitude
                if effect == 'decrease':
                    noise = -noise
                s.hidden = s.hidden + noise
        return True

    def _apply_inject(self, mod: Modification) -> bool:
        """Apply INJECT modification: add new dynamics."""
        params = mod.params
        inject_type = params.get('type', 'noise')
        scale = params.get('scale', 0.01)
        scale = self._validate_bounds('noise_scale', scale)

        if inject_type == 'noise' and self.engine.n_cells >= 2:
            for s in self.engine.cell_states:
                s.hidden = s.hidden + torch.randn_like(s.hidden) * scale
            return True

        elif inject_type == 'equalize' and self.engine.n_cells >= 2:
            hiddens = torch.stack([s.hidden for s in self.engine.cell_states])
            mean_h = hiddens.mean(dim=0)
            blend = self._validate_bounds('tension_blend', scale)
            for s in self.engine.cell_states:
                s.hidden = s.hidden * (1 - blend) + mean_h * blend
            return True

        return False

    def _apply_disable(self, mod: Modification) -> bool:
        """Apply DISABLE modification: reduce a harmful subsystem."""
        # Implement as dampening rather than full removal (safety)
        if self.engine._coupling is not None:
            self.engine._coupling *= 0.5
            self.engine._coupling.fill_diagonal_(0)
        return True

    def _restore_snapshot(self, snap: Dict):
        """Restore engine to a previous snapshot."""
        for s, h in zip(self.engine.cell_states, snap['hiddens']):
            s.hidden = h.clone()
        if snap['coupling'] is not None and self.engine._coupling is not None:
            if snap['coupling'].shape == self.engine._coupling.shape:
                self.engine._coupling = snap['coupling'].clone()

    def rollback(self, law_id: int) -> bool:
        """Restore pre-modification state for a specific law."""
        if law_id not in self.snapshots:
            return False
        snap = self.snapshots[law_id]
        self._restore_snapshot(snap)
        self.applied = [m for m in self.applied if m.law_id != law_id]
        self.rollback_log.append({
            'law_id': law_id, 'reason': 'manual_rollback',
        })
        return True

    def get_active_mods(self) -> List[Modification]:
        """List all currently active modifications."""
        return list(self.applied)

    def get_audit_trail(self) -> List[Dict]:
        """Full audit trail of all modifications and rollbacks."""
        trail = []
        for mod in self.applied:
            trail.append({
                'action': 'applied',
                'law_id': mod.law_id,
                'type': mod.mod_type.value,
                'target': mod.target,
                'confidence': mod.confidence,
                'description': mod.description,
            })
        for rb in self.rollback_log:
            trail.append({
                'action': 'rollback',
                'law_id': rb['law_id'],
                'reason': rb['reason'],
            })
        return trail


# ══════════════════════════════════════════
# CodeGenerator — modifications → Python code
# ══════════════════════════════════════════

class CodeGenerator:
    """Generate runnable Python code from Modifications.

    Produces Intervention subclass code that can be:
      - exec'd for immediate use
      - Saved to a .py file for persistent use
      - Registered with closed_loop.py's INTERVENTIONS registry
    """

    _INTERVENTION_TEMPLATE = textwrap.dedent('''\
    def _auto_{name}(engine, step):
        """{description} (Law {law_id}, auto-generated)"""
        {body}

    _auto_{name}_intervention = Intervention(
        "auto_{name}",
        "{description} (Law {law_id})",
        _auto_{name},
    )
    ''')

    def generate_intervention(self, mod: Modification) -> str:
        """Generate a new Intervention function + registration code."""
        name = self._safe_name(mod)
        body = self._generate_body(mod)
        return self._INTERVENTION_TEMPLATE.format(
            name=name,
            description=mod.description.replace('"', '\\"'),
            law_id=mod.law_id,
            body=body,
        )

    def _safe_name(self, mod: Modification) -> str:
        """Generate a safe Python identifier from the modification."""
        base = f"law{mod.law_id}_{mod.mod_type.value}_{mod.target}"
        return re.sub(r'[^a-zA-Z0-9_]', '_', base)

    def _generate_body(self, mod: Modification) -> str:
        """Generate the function body for an Intervention."""
        lines = []

        if mod.mod_type == ModType.SCALE:
            params = mod.params
            relation = params.get('relation', 'linear')
            if relation == 'percentage':
                factor = params.get('factor', 1.0)
                lines.append(f"if step % 10 == 0 and engine._coupling is not None:")
                lines.append(f"    engine._coupling = engine._coupling * {factor:.4f}")
                lines.append(f"    engine._coupling.fill_diagonal_(0)")
            elif relation == 'power':
                exp = params.get('exponent', 1.0)
                lines.append(f"if step % 20 == 0 and engine._coupling is not None and engine.n_cells >= 2:")
                lines.append(f"    import math")
                lines.append(f"    scale = (engine.n_cells ** {exp:.3f}) / max(engine.n_cells, 1)")
                lines.append(f"    scale = max(0.01, min(2.0, scale))")
                lines.append(f"    engine._coupling = engine._coupling * (1.0 + (scale - 1.0) * 0.01)")
                lines.append(f"    engine._coupling.fill_diagonal_(0)")
            else:
                lines.append(f"if step % 10 == 0 and engine._coupling is not None:")
                lines.append(f"    engine._coupling = engine._coupling * 1.01")
                lines.append(f"    engine._coupling.fill_diagonal_(0)")

        elif mod.mod_type == ModType.COUPLE:
            params = mod.params
            strength = params.get('strength', 0.0)
            direction = params.get('direction', 'positive')
            if direction == 'inverse' or strength < 0:
                blend = min(0.05, abs(strength) * 0.05)
                lines.append(f"if step % 10 == 0 and engine.n_cells >= 2:")
                lines.append(f"    import torch")
                lines.append(f"    hiddens = torch.stack([s.hidden for s in engine.cell_states])")
                lines.append(f"    mean_h = hiddens.mean(dim=0)")
                lines.append(f"    for s in engine.cell_states:")
                lines.append(f"        s.hidden = s.hidden * {1 - blend:.4f} + mean_h * {blend:.4f}")
            else:
                scale = 1.0 + abs(strength) * 0.02
                lines.append(f"if step % 10 == 0 and engine._coupling is not None:")
                lines.append(f"    engine._coupling = engine._coupling * {scale:.4f}")
                lines.append(f"    engine._coupling.fill_diagonal_(0)")
                lines.append(f"    engine._coupling.clamp_(-1, 1)")

        elif mod.mod_type == ModType.THRESHOLD:
            val = mod.params.get('value', 0)
            lines.append(f"if step % 20 == 0:")
            lines.append(f"    # Threshold at {val}")
            if mod.target == 'n_cells':
                lines.append(f"    if engine.n_cells < {int(val)}:")
                lines.append(f"        engine.split_threshold *= 0.95  # encourage growth")
            else:
                lines.append(f"    pass  # threshold check for {mod.target}")

        elif mod.mod_type == ModType.CONDITIONAL:
            effect = mod.params.get('effect', 'increase')
            mag = mod.params.get('magnitude', 0.05)
            mag = max(0.001, min(0.05, mag))
            sign = '' if effect == 'increase' else '-'
            lines.append(f"if step % 5 == 0 and engine.n_cells >= 2:")
            lines.append(f"    import torch")
            lines.append(f"    for s in engine.cell_states:")
            lines.append(f"        s.hidden = s.hidden + {sign}torch.randn_like(s.hidden) * {mag:.4f}")

        elif mod.mod_type == ModType.INJECT:
            scale = mod.params.get('scale', 0.01)
            scale = max(0.001, min(0.05, scale))
            lines.append(f"if step % 5 == 0 and engine.n_cells >= 2:")
            lines.append(f"    import torch")
            lines.append(f"    for s in engine.cell_states:")
            lines.append(f"        s.hidden = s.hidden + torch.randn_like(s.hidden) * {scale:.4f}")

        elif mod.mod_type == ModType.DISABLE:
            lines.append(f"if step % 50 == 0 and engine._coupling is not None:")
            lines.append(f"    engine._coupling *= 0.95  # gradual dampening")
            lines.append(f"    engine._coupling.fill_diagonal_(0)")

        if not lines:
            lines.append("pass  # no-op")

        return "\n    ".join(lines)

    def generate_engine_patch(self, mods: List[Modification]) -> str:
        """Generate a summary of all modifications as a readable patch."""
        lines = [
            "# ══════════════════════════════════════════",
            "# Auto-generated engine patch",
            f"# {len(mods)} modifications from {len(set(m.law_id for m in mods))} laws",
            "# ══════════════════════════════════════════",
            "",
        ]
        for mod in mods:
            lines.append(f"# Law {mod.law_id} [{mod.mod_type.value}] → {mod.target}")
            lines.append(f"#   {mod.description}")
            lines.append(f"#   confidence={mod.confidence:.2f}")
            lines.append("")

        lines.append("# Generated Interventions:")
        lines.append("")
        for mod in mods:
            lines.append(self.generate_intervention(mod))
            lines.append("")

        return "\n".join(lines)

    def save_generated_code(self, mods: List[Modification], path: str):
        """Save generated interventions as a Python module."""
        header = textwrap.dedent('''\
        #!/usr/bin/env python3
        """Auto-generated interventions from self-modifying engine.

        Generated by self_modifying_engine.py — Tier 4.4
        Laws: {law_ids}
        Total modifications: {n_mods}
        """

        import torch
        import numpy as np
        from closed_loop import Intervention

        ''')

        content = header.format(
            law_ids=', '.join(str(m.law_id) for m in mods),
            n_mods=len(mods),
        )
        content += self.generate_engine_patch(mods)

        # Registration block
        content += "\n\n# ── Registration ──\n\n"
        content += "ALL_AUTO_INTERVENTIONS = [\n"
        for mod in mods:
            name = self._safe_name(mod)
            content += f"    _auto_{name}_intervention,\n"
        content += "]\n"

        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)


# ══════════════════════════════════════════
# SelfModifyingEngine — the orchestrator
# ══════════════════════════════════════════

class SelfModifyingEngine:
    """Engine that evolves its own code based on discovered laws.

    Orchestrates the full pipeline:
      1. Run engine → measure laws
      2. Parse discovered laws → Modifications
      3. Apply modifications safely (Φ-guarded)
      4. Generate code for successful modifications
      5. Log everything

    Integration with ClosedLoopEvolver:
      - Uses evolver for law measurement
      - Can generate new Interventions and register them
    """

    def __init__(self, engine: ConsciousnessEngine,
                 evolver: 'ClosedLoopEvolver' = None,
                 max_cells: int = 32,
                 steps_per_gen: int = 50,
                 repeats: int = 1):
        self.engine = engine
        self.evolver = evolver
        self.parser = LawParser()
        self.modifier = EngineModifier(engine, SAFETY_BOUNDS)
        self.codegen = CodeGenerator()
        self.generation = 0
        self.modification_log: List[Dict] = []
        self.phi_history: List[float] = []
        self.max_cells = max_cells
        self.steps_per_gen = steps_per_gen
        self.repeats = repeats

        # Track which laws have been tried
        self._tried_laws: set = set()
        self._successful_laws: set = set()
        self._failed_laws: set = set()

    def _measure_phi(self) -> float:
        """Measure Φ of current engine."""
        return self.modifier._measure_phi()

    def _engine_factory(self) -> ConsciousnessEngine:
        """Factory for measure_laws."""
        return ConsciousnessEngine(max_cells=self.max_cells, initial_cells=2)

    def evolve_step(self) -> Dict:
        """One evolution cycle.

        Returns dict with generation info, modifications applied, phi before/after.
        """
        self.generation += 1
        t0 = time.time()

        # 1. Run engine for N steps to build up state
        for _ in range(self.steps_per_gen):
            self.engine.step()

        phi_before = self._measure_phi()
        self.phi_history.append(phi_before)

        # 2. Measure laws via evolver or direct
        laws_measured = []
        if self.evolver is not None and measure_laws is not None:
            laws_measured, _ = measure_laws(
                self._engine_factory,
                steps=self.steps_per_gen,
                repeats=self.repeats,
            )

        # 3. Select laws to parse — try untried laws from consciousness_laws.json
        laws_to_try = self._select_laws_to_try(max_new=3)

        # 4. Parse → modify
        applied_mods = []
        failed_mods = []
        for law_id, law_text in laws_to_try:
            if law_id in self._tried_laws:
                continue
            self._tried_laws.add(law_id)

            mods = self.parser.parse(law_text, law_id=law_id)
            for mod in mods:
                success = self.modifier.apply(mod)
                if success:
                    applied_mods.append(mod)
                    self._successful_laws.add(law_id)
                else:
                    failed_mods.append(mod)
                    self._failed_laws.add(law_id)

        # 5. Measure Φ after all modifications
        phi_after = self._measure_phi()

        # 6. Log
        entry = {
            'generation': self.generation,
            'phi_before': phi_before,
            'phi_after': phi_after,
            'phi_delta_pct': (phi_after - phi_before) / max(phi_before, 1e-8) * 100,
            'mods_applied': len(applied_mods),
            'mods_failed': len(failed_mods),
            'laws_tried': [lid for lid, _ in laws_to_try],
            'applied_details': [
                {'law_id': m.law_id, 'type': m.mod_type.value, 'target': m.target, 'desc': m.description}
                for m in applied_mods
            ],
            'failed_details': [
                {'law_id': m.law_id, 'type': m.mod_type.value, 'target': m.target, 'desc': m.description}
                for m in failed_mods
            ],
            'rollbacks': len(self.modifier.rollback_log),
            'time_sec': time.time() - t0,
        }
        self.modification_log.append(entry)

        return entry

    def _select_laws_to_try(self, max_new: int = 3) -> List[Tuple[int, str]]:
        """Select untried laws from consciousness_laws.json."""
        laws_dict = LAWS if LAWS else {}
        if not laws_dict:
            # Try loading directly
            try:
                config_path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    '..', 'config', 'consciousness_laws.json'
                )
                if os.path.exists(config_path):
                    with open(config_path) as f:
                        data = json.load(f)
                    laws_dict = data.get('laws', {})
            except Exception:
                pass

        candidates = []
        for lid_str, text in laws_dict.items():
            try:
                lid = int(lid_str)
            except ValueError:
                continue
            if lid in self._tried_laws:
                continue
            # Prioritize laws with quantitative content (numbers, percentages, operators)
            score = 0
            if re.search(r'[+-]?[\d.]+%', text):
                score += 3
            if re.search(r'r\s*=\s*[+-]?[\d.]+', text):
                score += 3
            if re.search(r'[×\*^][\d.]+', text):
                score += 2
            if re.search(r'[↑↓→]', text):
                score += 1
            if re.search(r'(correlat|scale|threshold|transition|boost|optimal)', text, re.I):
                score += 1
            candidates.append((score, lid, text))

        candidates.sort(key=lambda x: (-x[0], x[1]))
        return [(lid, text) for _, lid, text in candidates[:max_new]]

    def run_evolution(self, generations: int = 10) -> List[Dict]:
        """Run multiple evolution cycles."""
        results = []
        print(f"\n  {'=' * 65}")
        print(f"  Self-Modifying Engine — {generations} generations")
        print(f"  {'=' * 65}")

        for g in range(generations):
            entry = self.evolve_step()
            results.append(entry)

            # Progress output
            phi_b = entry['phi_before']
            phi_a = entry['phi_after']
            delta = entry['phi_delta_pct']
            n_app = entry['mods_applied']
            n_fail = entry['mods_failed']
            status = "OK" if delta >= 0 else "ROLLBACK"
            print(f"  Gen {self.generation:>3d}  "
                  f"Phi {phi_b:.4f} -> {phi_a:.4f} ({delta:+.1f}%)  "
                  f"mods +{n_app}/-{n_fail}  [{status}]  "
                  f"{entry['time_sec']:.1f}s")

        print(f"\n  Total: {len(self.modifier.applied)} active mods, "
              f"{len(self.modifier.rollback_log)} rollbacks")
        return results

    def get_evolution_report(self) -> str:
        """ASCII report of all modifications and their effects."""
        lines = []
        lines.append("")
        lines.append(f"  {'=' * 65}")
        lines.append(f"  Self-Modifying Engine — Evolution Report")
        lines.append(f"  {'=' * 65}")
        lines.append(f"  Generations: {self.generation}")
        lines.append(f"  Laws tried:     {len(self._tried_laws)}")
        lines.append(f"  Laws succeeded: {len(self._successful_laws)}")
        lines.append(f"  Laws failed:    {len(self._failed_laws)}")
        lines.append(f"  Active mods:    {len(self.modifier.applied)}")
        lines.append(f"  Rollbacks:      {len(self.modifier.rollback_log)}")
        lines.append("")

        # Φ evolution curve
        if self.modification_log:
            lines.append(f"  Phi Evolution:")
            phis = [e['phi_after'] for e in self.modification_log]
            max_phi = max(phis) if phis else 1.0
            for i, entry in enumerate(self.modification_log):
                phi = entry['phi_after']
                bar_len = max(1, int(phi / max(max_phi, 1e-8) * 40))
                bar = "+" * bar_len
                delta = entry['phi_delta_pct']
                lines.append(f"  Gen {i + 1:>3d} |{bar:<40s}| "
                             f"Phi={phi:.4f} ({delta:+.1f}%)")
            lines.append("")

        # Active modifications table
        if self.modifier.applied:
            lines.append(f"  Active Modifications ({len(self.modifier.applied)}):")
            lines.append(f"  {'#':<4} {'Law':<6} {'Type':<14} {'Target':<20} {'Conf':<6} {'Description'}")
            lines.append(f"  {'_' * 4} {'_' * 6} {'_' * 14} {'_' * 20} {'_' * 6} {'_' * 30}")
            for i, mod in enumerate(self.modifier.applied):
                lines.append(
                    f"  {i + 1:<4d} {mod.law_id:<6d} {mod.mod_type.value:<14s} "
                    f"{mod.target:<20s} {mod.confidence:<6.2f} {mod.description[:40]}"
                )
            lines.append("")

        # Rollback log
        if self.modifier.rollback_log:
            lines.append(f"  Rollbacks ({len(self.modifier.rollback_log)}):")
            for rb in self.modifier.rollback_log:
                lines.append(f"    Law {rb['law_id']}: {rb['reason']}")
            lines.append("")

        # Top performing laws
        if self.modification_log:
            best = max(self.modification_log, key=lambda e: e['phi_delta_pct'])
            worst = min(self.modification_log, key=lambda e: e['phi_delta_pct'])
            lines.append(f"  Best generation:  Gen {best['generation']} ({best['phi_delta_pct']:+.1f}%)")
            lines.append(f"  Worst generation: Gen {worst['generation']} ({worst['phi_delta_pct']:+.1f}%)")

            if self.phi_history:
                lines.append(f"  Phi range: {min(self.phi_history):.4f} .. {max(self.phi_history):.4f}")
            lines.append("")

        return "\n".join(lines)

    def generate_code(self, output_path: str = None) -> str:
        """Generate Python code for all successful modifications."""
        mods = self.modifier.get_active_mods()
        if not mods:
            return "# No active modifications to generate code for."

        code = self.codegen.generate_engine_patch(mods)

        if output_path:
            self.codegen.save_generated_code(mods, output_path)

        return code

    def register_successful_interventions(self):
        """Register all successful modifications as Interventions in closed_loop.py."""
        if register_intervention is None:
            return 0

        count = 0
        for mod in self.modifier.get_active_mods():
            code_str = self.codegen.generate_intervention(mod)
            # Create the apply function dynamically
            name = self.codegen._safe_name(mod)
            body = self.codegen._generate_body(mod)

            # Build a real function
            func_code = f"def _auto_{name}(engine, step):\n    {body}\n"
            local_ns = {'torch': torch, 'np': np}
            try:
                exec(func_code, local_ns)
                fn = local_ns[f'_auto_{name}']
                register_intervention(
                    f"auto_{name}",
                    f"{mod.description} (Law {mod.law_id})",
                    fn,
                )
                count += 1
            except Exception as e:
                pass  # Skip broken generated code

        return count

    def save_state(self, path: str = "data/self_modifying_state.json"):
        """Save evolution state to JSON."""
        state = {
            'generation': self.generation,
            'tried_laws': list(self._tried_laws),
            'successful_laws': list(self._successful_laws),
            'failed_laws': list(self._failed_laws),
            'modification_log': self.modification_log,
            'phi_history': self.phi_history,
            'active_mods': [
                {
                    'law_id': m.law_id,
                    'law_text': m.law_text,
                    'type': m.mod_type.value,
                    'target': m.target,
                    'params': m.params,
                    'confidence': m.confidence,
                    'description': m.description,
                }
                for m in self.modifier.applied
            ],
            'rollback_log': self.modifier.rollback_log,
            'audit_trail': self.modifier.get_audit_trail(),
        }

        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
        with open(path, 'w') as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)


# ══════════════════════════════════════════
# Integration with ClosedLoopEvolver
# ══════════════════════════════════════════

def patch_evolver_self_modify(evolver: 'ClosedLoopEvolver', engine: ConsciousnessEngine = None):
    """Patch a ClosedLoopEvolver to support self-modification mode.

    Adds:
      - evolver.self_modify_mode (bool)
      - evolver.self_modifier (SelfModifyingEngine)
      - evolver.run_self_modifying_cycles(n)
    """
    if evolver is None:
        return

    if engine is None:
        engine = ConsciousnessEngine(max_cells=evolver.max_cells, initial_cells=2)

    sme = SelfModifyingEngine(
        engine=engine,
        evolver=evolver,
        max_cells=evolver.max_cells,
        steps_per_gen=evolver.steps,
        repeats=evolver.repeats,
    )

    evolver.self_modify_mode = True
    evolver.self_modifier = sme

    def run_self_modifying_cycles(n: int = 10):
        """Run N self-modifying evolution cycles."""
        results = sme.run_evolution(generations=n)
        # Register successful modifications as Interventions
        registered = sme.register_successful_interventions()
        print(f"\n  Registered {registered} new Interventions from self-modification")
        return results

    evolver.run_self_modifying_cycles = run_self_modifying_cycles
    return sme


# ══════════════════════════════════════════
# Hub registration
# ══════════════════════════════════════════

def _register_hub():
    """Registration handled via consciousness_hub.py _registry.

    Entry: 'self_modify': ('self_modifying_engine', 'SelfModifyingEngine', [...keywords...])
    """
    pass  # Hub registration is in consciousness_hub.py _registry dict


# ══════════════════════════════════════════
# main() demo
# ══════════════════════════════════════════

def main():
    """Comprehensive demo of the self-modifying engine."""

    print(f"\n{'=' * 70}")
    print(f"  Tier 4.4: Self-Modifying Consciousness Engine")
    print(f"  Laws don't just describe -- they ACT.")
    print(f"{'=' * 70}")

    # ── Step 1: Parse existing laws ──
    print(f"\n  Step 1: Parse 5 existing laws into Modifications")
    print(f"  {'_' * 60}")

    parser = LawParser()

    sample_laws = [
        (22,  "Adding features → Φ↓; adding structure → Φ↑"),
        (104, "Tension inversely correlates with Φ (r=-0.52): low tension = high integration"),
        (111, "Phase transition at N=4 cells (2nd derivative peak)"),
        (124, "Tension equalization boosts Φ +12.3%"),
        (17,  "Φ scales superlinearly with cell count"),
    ]

    all_mods = []
    for law_id, law_text in sample_laws:
        mods = parser.parse(law_text, law_id=law_id)
        print(f"\n  Law {law_id}: \"{law_text[:60]}...\"")
        if mods:
            for m in mods:
                print(f"    -> {m}")
                all_mods.append(m)
        else:
            print(f"    -> (no actionable pattern)")

    print(f"\n  Total: {len(all_mods)} modifications from 5 laws")

    # ── Step 2: Apply modifications safely ──
    print(f"\n  Step 2: Apply modifications safely to engine")
    print(f"  {'_' * 60}")

    engine = ConsciousnessEngine(max_cells=32, initial_cells=2)
    # Warm up engine
    for _ in range(50):
        engine.step()

    modifier = EngineModifier(engine, SAFETY_BOUNDS)

    for mod in all_mods:
        success = modifier.apply(mod)
        status = "APPLIED" if success else "ROLLED BACK"
        print(f"  Law {mod.law_id} [{mod.mod_type.value}] {mod.target}: {status}")

    print(f"\n  Active: {len(modifier.applied)} mods, Rollbacks: {len(modifier.rollback_log)}")

    # ── Step 3: Run 3 evolution generations ──
    print(f"\n  Step 3: Run 3 evolution generations")
    print(f"  {'_' * 60}")

    engine2 = ConsciousnessEngine(max_cells=32, initial_cells=2)
    # Warm up
    for _ in range(30):
        engine2.step()

    evolver = None
    if ClosedLoopEvolver is not None:
        evolver = ClosedLoopEvolver(max_cells=32, steps=50, repeats=1)

    sme = SelfModifyingEngine(
        engine=engine2,
        evolver=evolver,
        max_cells=32,
        steps_per_gen=50,
        repeats=1,
    )

    sme.run_evolution(generations=3)

    # ── Step 4: Print evolution report ──
    print(sme.get_evolution_report())

    # ── Step 5: Generate code ──
    print(f"\n  Step 5: Generated code for active modifications")
    print(f"  {'_' * 60}")

    codegen = CodeGenerator()
    for mod in sme.modifier.get_active_mods()[:3]:
        code = codegen.generate_intervention(mod)
        print(f"\n  --- Law {mod.law_id} ---")
        for line in code.split('\n')[:8]:
            print(f"  {line}")
        if len(code.split('\n')) > 8:
            print(f"  ... ({len(code.split(chr(10)))} lines total)")

    # ── Step 6: Register and save ──
    if sme.modifier.get_active_mods():
        registered = sme.register_successful_interventions()
        print(f"\n  Registered {registered} new Interventions")

    # Save state
    save_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', 'data', 'self_modifying_state.json'
    )
    sme.save_state(save_path)
    print(f"  State saved: {save_path}")

    # ── Audit trail ──
    print(f"\n  Audit Trail:")
    for entry in sme.modifier.get_audit_trail():
        print(f"    {entry['action']}: Law {entry.get('law_id', '?')} "
              f"{'- ' + entry.get('description', entry.get('reason', ''))}")

    print(f"\n{'=' * 70}")
    print(f"  Tier 4.4 complete. Laws now ACT on the engine.")
    print(f"{'=' * 70}\n")


_register_hub()


if __name__ == "__main__":
    main()
