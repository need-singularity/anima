#!/usr/bin/env python3
"""intervention_generator.py — Law text to Intervention auto-generator

Analyzes consciousness law text and produces executable Intervention objects
using template matching. Each law is scanned for keywords that map to known
intervention templates (coupling, noise, tension, diversity, ratchet, entropy).

Usage:
  from intervention_generator import InterventionGenerator
  gen = InterventionGenerator()

  # Single law
  iv = gen.generate(124, "Tension equalization boosts Phi +12.3%")
  iv.apply(engine, step)

  # Bulk from JSON
  all_ivs = gen.generate_all_from_json("config/consciousness_laws.json")
  print(f"Generated {len(all_ivs)} interventions")

  # Hub integration
  hub.act("자동 개입")
  hub.act("intervention generator")

Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import json
import os
import re
import math
from typing import Optional, List, Dict, Callable, Tuple
from dataclasses import dataclass, field

import torch
import torch.nn.functional as F
import numpy as np

# Lazy imports for project compatibility
try:
    from closed_loop import Intervention
except ImportError:
    class Intervention:
        """Fallback Intervention if closed_loop unavailable."""
        def __init__(self, name: str, description: str, apply_fn: Callable):
            self.name = name
            self.description = description
            self.apply_fn = apply_fn
        def apply(self, engine, step: int):
            self.apply_fn(engine, step)

try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA
    PSI_COUPLING = PSI_ALPHA
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014


# ══════════════════════════════════════════
# Template functions
# ══════════════════════════════════════════

def _make_coupling_fn(law_id: int, law_text: str) -> Callable:
    """COUPLING template — modify engine._coupling matrix."""
    text_lower = law_text.lower()
    symmetrize = "symmetr" in text_lower or "bidirection" in text_lower
    clamp = "clamp" in text_lower or "limit" in text_lower or "destroy" in text_lower
    scale_down = "destroy" in text_lower or "excess" in text_lower or "harm" in text_lower

    def apply_fn(engine, step):
        if engine._coupling is None:
            return
        if step % 10 != 0:
            return
        if symmetrize:
            engine._coupling = (engine._coupling + engine._coupling.T) / 2
            engine._coupling.fill_diagonal_(0)
        if clamp:
            engine._coupling.clamp_(-0.5, 0.5)
        if scale_down:
            # Gently reduce excessive coupling
            norm = engine._coupling.abs().max().item()
            if norm > 0.8:
                engine._coupling *= 0.95
    return apply_fn


def _make_noise_fn(law_id: int, law_text: str) -> Callable:
    """NOISE template — add noise to cell hiddens."""
    text_lower = law_text.lower()
    is_pink = "1/f" in text_lower or "pink" in text_lower
    is_soc = "soc" in text_lower or "sandpile" in text_lower or "avalanche" in text_lower
    is_stochastic = "stochastic" in text_lower or "random" in text_lower

    # Small perturbation scale (safe)
    scale = 0.005 if is_pink else (0.01 if is_soc else 0.003)

    def apply_fn(engine, step):
        if engine.n_cells < 2:
            return
        if step % 5 != 0:
            return
        hdim = engine.hidden_dim

        if is_pink and hdim >= 5:
            # 1/f noise approximation via moving average
            noise = torch.randn(hdim)
            kernel = torch.ones(5) / 5
            smoothed = F.conv1d(
                noise.unsqueeze(0).unsqueeze(0),
                kernel.unsqueeze(0).unsqueeze(0),
                padding=2
            ).squeeze()[:hdim]
            for s in engine.cell_states:
                s.hidden = s.hidden + smoothed * scale
        elif is_soc:
            # SOC-like: perturb a random cell (avalanche seed)
            idx = np.random.randint(0, engine.n_cells)
            engine.cell_states[idx].hidden += torch.randn(hdim) * scale
        else:
            # Gaussian noise to all cells
            for s in engine.cell_states:
                s.hidden = s.hidden + torch.randn(hdim) * scale
    return apply_fn


def _make_tension_fn(law_id: int, law_text: str) -> Callable:
    """TENSION template — modify cell tensions."""
    text_lower = law_text.lower()
    equalize = "equali" in text_lower or "homogen" in text_lower
    threshold = "threshold" in text_lower or "veto" in text_lower
    balance = "balance" in text_lower or "homeosta" in text_lower

    def apply_fn(engine, step):
        if engine.n_cells < 2:
            return
        if step % 10 != 0:
            return

        tensions = [s.avg_tension for s in engine.cell_states]
        mean_t = np.mean(tensions)

        if equalize:
            # Push tensions toward mean (soft equalization)
            for s in engine.cell_states:
                if s.tension_history:
                    s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5
        elif threshold:
            # Dampen high-tension cells
            for s in engine.cell_states:
                if s.avg_tension > 0.8:
                    s.hidden = s.hidden * 0.9
        elif balance:
            # Gentle homeostatic pull toward PSI_BALANCE
            for s in engine.cell_states:
                if s.tension_history:
                    delta = PSI_BALANCE - s.tension_history[-1]
                    s.tension_history[-1] += delta * 0.05
    return apply_fn


def _make_diversity_fn(law_id: int, law_text: str) -> Callable:
    """DIVERSITY template — maintain faction/cell diversity."""
    text_lower = law_text.lower()
    push_apart = "divers" in text_lower or "heterogen" in text_lower
    faction_focus = "faction" in text_lower or "individ" in text_lower

    def apply_fn(engine, step):
        if engine.n_cells < 2:
            return
        if step % 10 != 0:
            return

        hiddens = torch.stack([s.hidden for s in engine.cell_states])

        if push_apart:
            # Push similar cells apart with small noise
            for i in range(len(engine.cell_states)):
                for j in range(i + 1, min(i + 5, len(engine.cell_states))):
                    sim = F.cosine_similarity(
                        hiddens[i].unsqueeze(0), hiddens[j].unsqueeze(0)
                    ).item()
                    if sim > 0.9:
                        engine.cell_states[j].hidden += (
                            torch.randn_like(engine.cell_states[j].hidden) * 0.02
                        )
        elif faction_focus:
            # Strengthen faction identity by pulling faction members closer
            factions = {}
            for s in engine.cell_states:
                fid = getattr(s, 'faction_id', 0)
                if fid not in factions:
                    factions[fid] = []
                factions[fid].append(s)
            for fid, members in factions.items():
                if len(members) >= 2:
                    avg = torch.stack([s.hidden for s in members]).mean(dim=0)
                    for s in members:
                        s.hidden = s.hidden * 0.98 + avg * 0.02
    return apply_fn


def _make_ratchet_fn(law_id: int, law_text: str) -> Callable:
    """RATCHET template — save/restore states based on Phi changes."""
    text_lower = law_text.lower()
    is_backup = "backup" in text_lower or "checkpoint" in text_lower or "save" in text_lower
    is_restore = "restor" in text_lower or "recover" in text_lower or "resurrect" in text_lower

    def apply_fn(engine, step):
        if engine.n_cells < 2:
            return

        # Initialize backup storage
        if not hasattr(engine, '_auto_ratchet_backup'):
            engine._auto_ratchet_backup = None
            engine._auto_ratchet_phi = 0.0

        if step % 50 == 0:
            # Compute simple Phi proxy
            hiddens = torch.stack([s.hidden for s in engine.cell_states])
            phi_proxy = hiddens.var().item()

            if phi_proxy > engine._auto_ratchet_phi:
                # New best: save state
                engine._auto_ratchet_backup = [s.hidden.clone() for s in engine.cell_states]
                engine._auto_ratchet_phi = phi_proxy
            elif is_restore and engine._auto_ratchet_backup is not None:
                # Phi dropped: partial restore (blend 20% from backup)
                if phi_proxy < engine._auto_ratchet_phi * 0.5:
                    for i, s in enumerate(engine.cell_states):
                        if i < len(engine._auto_ratchet_backup):
                            s.hidden = s.hidden * 0.8 + engine._auto_ratchet_backup[i] * 0.2
    return apply_fn


def _make_entropy_fn(law_id: int, law_text: str) -> Callable:
    """ENTROPY template — regulate hidden state entropy/variance."""
    text_lower = law_text.lower()
    bound_upper = "bound" in text_lower or "limit" in text_lower or "compress" in text_lower
    maximize = "maxim" in text_lower or "increas" in text_lower
    channel = "channel" in text_lower or "capacity" in text_lower

    def apply_fn(engine, step):
        if engine.n_cells < 2:
            return
        if step % 10 != 0:
            return

        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach()

        if bound_upper:
            # Clamp variance if too high (stabilize)
            var = hiddens.var().item()
            if var > 1.0:
                scale = 1.0 / (var ** 0.25)
                for s in engine.cell_states:
                    s.hidden = s.hidden * scale
        elif channel and engine._coupling is not None:
            # Limit coupling magnitude (~channel capacity)
            engine._coupling.clamp_(-0.5, 0.5)
        elif maximize:
            # Push weak dimensions with small noise (use all dimensions)
            mean = hiddens.mean(dim=0)
            centered = hiddens - mean
            var_per_dim = centered.var(dim=0)
            weak_mask = var_per_dim < var_per_dim.mean() * 0.1
            if weak_mask.any():
                noise = torch.randn_like(hiddens[:, weak_mask]) * 0.01
                for i, s in enumerate(engine.cell_states):
                    s.hidden[weak_mask] += noise[i]
    return apply_fn


# ══════════════════════════════════════════
# Template registry
# ══════════════════════════════════════════

@dataclass
class TemplateMatch:
    """Result of matching a law to a template."""
    template_name: str
    score: int
    factory: Callable  # (law_id, law_text) -> apply_fn


# Keyword definitions: (keyword, exact_match_score, partial_match_score)
TEMPLATE_KEYWORDS = {
    'coupling': {
        'exact':   ['coupling', 'symmetr', 'bidirection', 'connection'],
        'partial': ['coupl', 'connect', 'link', 'wire', 'parasit'],
        'factory': _make_coupling_fn,
    },
    'noise': {
        'exact':   ['noise', '1/f', 'perturbation', 'soc', 'stochastic', 'avalanche'],
        'partial': ['nois', 'perturb', 'random', 'sandpile', 'chaos'],
        'factory': _make_noise_fn,
    },
    'tension': {
        'exact':   ['tension', 'equali', 'balance', 'homeosta'],
        'partial': ['tens', 'balanc', 'homeo', 'veto', 'threshold'],
        'factory': _make_tension_fn,
    },
    'diversity': {
        'exact':   ['diversity', 'faction', 'heterogen', 'individ'],
        'partial': ['divers', 'faction', 'heterog', 'special'],
        'factory': _make_diversity_fn,
    },
    'ratchet': {
        'exact':   ['ratchet', 'protect', 'preserve', 'backup', 'checkpoint'],
        'partial': ['ratch', 'protect', 'preserv', 'restor', 'recover', 'resurrect'],
        'factory': _make_ratchet_fn,
    },
    'entropy': {
        'exact':   ['entropy', 'bound', 'compress', 'information', 'channel'],
        'partial': ['entrop', 'compress', 'inform', 'capacit', 'shannon'],
        'factory': _make_entropy_fn,
    },
}

# Exact match score
EXACT_SCORE = 3
# Partial match score
PARTIAL_SCORE = 1
# Minimum score to generate
THRESHOLD = 2


# ══════════════════════════════════════════
# InterventionGenerator
# ══════════════════════════════════════════

class InterventionGenerator:
    """Generates Intervention objects from law descriptions."""

    def __init__(self):
        self.templates: Dict[str, dict] = {}
        self._register_templates()

    def _register_templates(self):
        """Register all built-in templates."""
        self.templates = dict(TEMPLATE_KEYWORDS)

    def _score_template(self, template_name: str, law_text: str) -> int:
        """Score how well a law text matches a template."""
        tpl = self.templates[template_name]
        text_lower = law_text.lower()
        score = 0

        for kw in tpl['exact']:
            if kw in text_lower:
                score += EXACT_SCORE

        for kw in tpl['partial']:
            if kw in text_lower:
                score += PARTIAL_SCORE

        return score

    def _find_best_template(self, law_text: str) -> Optional[TemplateMatch]:
        """Find the best matching template for a law text."""
        best_name = None
        best_score = 0

        for name in self.templates:
            s = self._score_template(name, law_text)
            if s > best_score:
                best_score = s
                best_name = name

        if best_score >= THRESHOLD and best_name is not None:
            return TemplateMatch(
                template_name=best_name,
                score=best_score,
                factory=self.templates[best_name]['factory'],
            )
        return None

    def generate(self, law_id: int, law_text: str) -> Optional[Intervention]:
        """Parse law text, find matching template, create Intervention.

        Returns None if no template matches above threshold.
        """
        match = self._find_best_template(law_text)
        if match is None:
            return None

        apply_fn = match.factory(law_id, law_text)
        name = f"auto_law_{law_id}"
        desc = law_text[:80] + ("..." if len(law_text) > 80 else "")

        return Intervention(name, desc, apply_fn)

    def generate_all_from_json(self, laws_path: str) -> List[Intervention]:
        """Scan all laws from JSON, generate interventions for applicable ones."""
        # Try relative to config/ directory
        if not os.path.isabs(laws_path):
            # Search common locations
            candidates = [
                laws_path,
                os.path.join(os.path.dirname(__file__), '..', 'config', os.path.basename(laws_path)),
                os.path.join(os.path.dirname(__file__), '..', laws_path),
            ]
            for c in candidates:
                if os.path.exists(c):
                    laws_path = c
                    break

        with open(laws_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        laws = data.get('laws', {})
        interventions = []

        for lid_str, text in laws.items():
            try:
                lid = int(lid_str)
            except ValueError:
                continue
            iv = self.generate(lid, text)
            if iv is not None:
                interventions.append(iv)

        return interventions

    def register_template(self, name: str, exact_keywords: List[str],
                          partial_keywords: List[str],
                          factory: Callable) -> None:
        """Register a custom template for law-to-intervention conversion."""
        self.templates[name] = {
            'exact': exact_keywords,
            'partial': partial_keywords,
            'factory': factory,
        }

    def explain(self, law_id: int, law_text: str) -> str:
        """Explain why a law matched (or didn't match) a template."""
        lines = [f"Law {law_id}: {law_text[:60]}..."]
        text_lower = law_text.lower()

        for name, tpl in self.templates.items():
            score = 0
            matches = []
            for kw in tpl['exact']:
                if kw in text_lower:
                    score += EXACT_SCORE
                    matches.append(f"  exact '{kw}' (+{EXACT_SCORE})")
            for kw in tpl['partial']:
                if kw in text_lower:
                    score += PARTIAL_SCORE
                    matches.append(f"  partial '{kw}' (+{PARTIAL_SCORE})")
            if matches:
                status = "MATCH" if score >= THRESHOLD else "below threshold"
                lines.append(f"  [{name}] score={score} ({status})")
                lines.extend(matches)

        match = self._find_best_template(law_text)
        if match:
            lines.append(f"  => Winner: {match.template_name} (score={match.score})")
        else:
            lines.append("  => No template matched (all below threshold)")

        return "\n".join(lines)


# ══════════════════════════════════════════
# Hub registration
# ══════════════════════════════════════════

def _try_hub_register():
    """Register with ConsciousnessHub if available."""
    try:
        from consciousness_hub import ConsciousnessHub
        hub = ConsciousnessHub._instance if hasattr(ConsciousnessHub, '_instance') else None
        if hub and hasattr(hub, '_registry'):
            hub._registry['intervention_gen'] = (
                'intervention_generator', 'InterventionGenerator',
                ['개입 생성', '자동 개입', 'intervention generator',
                 'auto intervention', 'law to code', '법칙 변환'],
            )
    except ImportError:
        pass


_try_hub_register()


# ══════════════════════════════════════════
# main() demo
# ══════════════════════════════════════════

def main():
    """Demo: generate interventions from known laws."""
    print("=" * 60)
    print("  Intervention Generator — Law Text to Code")
    print("=" * 60)

    gen = InterventionGenerator()

    # Test with known laws
    test_laws = {
        22: "Adding features -> Phi down; adding structure -> Phi up",
        89: "Excessive coupling destroys consciousness (Phi x0.74)",
        108: "Coupling symmetry positively correlates with Phi: bidirectional information flow > unidirectional",
        124: "Tension equalization boosts Phi +12.3%",
        126: "1/f (pink) noise injection boosts Phi +2.9%",
        31: "Persistence = ratchet + Hebbian + diversity",
        18: "Shannon channel capacity = information ceiling",
        213: "SOC scale-adaptive avalanche: beneficial at small scale, harmful at large",
    }

    print("\n  Template matching for test laws:")
    print(f"  {'Law':<6} {'Template':<12} {'Score':<6} {'Name':<20}")
    print(f"  {'─' * 6} {'─' * 12} {'─' * 6} {'─' * 20}")

    for lid, text in test_laws.items():
        iv = gen.generate(lid, text)
        if iv:
            match = gen._find_best_template(text)
            print(f"  {lid:<6} {match.template_name:<12} {match.score:<6} {iv.name:<20}")
        else:
            print(f"  {lid:<6} {'(none)':<12} {'-':<6} {'(no match)':<20}")

    # Bulk generation from JSON
    print("\n  Bulk generation from consciousness_laws.json:")
    try:
        laws_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'consciousness_laws.json')
        all_ivs = gen.generate_all_from_json(laws_path)

        with open(laws_path, 'r') as f:
            data = json.load(f)
        total_laws = len(data.get('laws', {}))

        print(f"  Total laws: {total_laws}")
        print(f"  Auto-generated interventions: {len(all_ivs)}")
        print(f"  Coverage: {len(all_ivs) / max(total_laws, 1) * 100:.1f}%")

        # Template distribution
        template_counts: Dict[str, int] = {}
        for iv in all_ivs:
            lid = int(iv.name.split('_')[-1])
            law_text = data['laws'].get(str(lid), '')
            match = gen._find_best_template(law_text)
            if match:
                template_counts[match.template_name] = template_counts.get(match.template_name, 0) + 1

        print(f"\n  Template distribution:")
        for tname, count in sorted(template_counts.items(), key=lambda x: -x[1]):
            bar = '#' * count
            print(f"    {tname:<12} {count:>3}  {bar}")

    except FileNotFoundError:
        print("  (consciousness_laws.json not found — skipping bulk test)")

    print("\n  Done.")


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
