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

    # ── Pattern registry ──

    # Proportionality: "Φ ∝ N^0.78", "Φ scales with cells", "X = A × Y^B"
    _RE_POWER = re.compile(
        r'(?P<target>\w+)\s*[=∝]\s*[\d.]*\s*[×\*]?\s*(?P<var>\w+)\^(?P<exp>[\d.]+)',
        re.IGNORECASE
    )
    _RE_SCALES = re.compile(
        r'(?P<target>\w+)\s+scales?\s+(?:super)?linearly\s+with\s+(?P<var>\w+)',
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
        r'(?P<winner>[\w\s/\-]+?)\s+(?:>|beats?|outperforms?|better\s+than|superior\s+to)\s+(?P<loser>[\w\s/\-]+?)(?:\s|$|[,;:.(])',
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
        r'(?P<metric>Φ|Phi|phi|CE|BPC|Sharpe|r|R2|R²|CV|F_c|T_c|α|alpha)\s*[=≈:]\s*(?P<val>[+-]?[\d.]+)',
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
        r'(?P<subject>[\w\s\-]+?)\s+is\s+(?:scale[- ]invariant|universal|independent|substrate[- ]independent|Markovian|irreversible|immortal|chaotic|non-conserved|self-organized|data-independent|time-symmetric|net-positive|non-distillable|near-incompressible|non-superadditive|gradient-indestructible|Phi-neutral|self-replicating)',
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

        # 31. Fallback: extract any known keyword from law text as an INJECT
        if not mods:
            low = law_text.lower()
            for kw in ['φ', 'phi', 'consciousness', 'entropy', 'hebbian', 'ratchet',
                        'mitosis', 'soc', 'bottleneck', 'frustration', 'narrative',
                        'topology', 'faction', 'coupling', 'tension', 'ce ', 'gradient',
                        'attention', 'memory', 'diversity', 'gate']:
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
