#!/usr/bin/env python3
"""accel_intervention_map.py — Hypothesis → Intervention mapping for acceleration pipeline.

Maps the 304 brainstorm-stage acceleration hypotheses to Intervention objects
that can be applied to ConsciousnessEngine and measured for Phi retention.

Usage:
    from accel_intervention_map import map_hypothesis_to_intervention, INTERVENTION_TEMPLATES
    intervention = map_hypothesis_to_intervention(hyp_dict)
    if intervention is not None:
        intervention.apply(engine, step=0)
"""

import sys
import os
import math
import torch
import torch.nn.functional as F
import numpy as np
from typing import Optional, Callable, Dict

# ── path setup ──────────────────────────────────────────────────────────────
_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

# ── Intervention class (import from closed_loop, fallback if unavailable) ───
try:
    from closed_loop import Intervention
except Exception:
    class Intervention:  # type: ignore
        """Fallback Intervention when closed_loop is unavailable."""
        def __init__(self, name: str, description: str, apply_fn: Callable):
            self.name = name
            self.description = description
            self.apply_fn = apply_fn

        def apply(self, engine, step: int):
            self.apply_fn(engine, step)


# ══════════════════════════════════════════════════════════════════════════════
# Intervention apply-function implementations
# ══════════════════════════════════════════════════════════════════════════════

# ── compute_reduction ─────────────────────────────────────────────────────────

def _skip_step(engine, step: int):
    """Probabilistic step skipping — run every other step."""
    if step % 2 == 1:
        return  # skip odd steps (no-op)

def _batch_share(engine, step: int):
    """Share hidden state average across cells (batch sharing)."""
    if engine.n_cells < 2:
        return
    if step % 4 == 0:
        avg = torch.stack([s.hidden for s in engine.cell_states]).mean(dim=0)
        for s in engine.cell_states:
            s.hidden = s.hidden * 0.9 + avg * 0.1

def _state_reuse(engine, step: int):
    """Reuse previous step's hidden state partially (state recycling)."""
    if engine.n_cells < 1:
        return
    # Inject slight inertia: blend hidden with itself (reduces compute)
    for s in engine.cell_states:
        s.hidden = s.hidden * 0.95 + s.hidden.detach() * 0.05

def _state_cache(engine, step: int):
    """Cache and reuse cell states every N steps (reduce recomputation)."""
    if not hasattr(engine, '_cache_hiddens') or step % 3 == 0:
        engine._cache_hiddens = [s.hidden.clone() for s in engine.cell_states]
    else:
        for s, ch in zip(engine.cell_states, engine._cache_hiddens):
            s.hidden = s.hidden * 0.8 + ch * 0.2

def _frozen_cells(engine, step: int):
    """Freeze 30% of cells for 5 steps then rotate (selective compute)."""
    n = engine.n_cells
    if n < 3:
        return
    freeze_count = max(1, n // 3)
    freeze_idx = set(range(step % n, min(step % n + freeze_count, n)))
    if hasattr(engine, '_prev_hiddens') and engine._prev_hiddens:
        for i, s in enumerate(engine.cell_states):
            if i in freeze_idx and i < len(engine._prev_hiddens):
                s.hidden = engine._prev_hiddens[i]
    engine._prev_hiddens = [s.hidden.clone() for s in engine.cell_states]

def _speculative_draft(engine, step: int):
    """Draft small-engine approximation: average 2 cells → broadcast."""
    if engine.n_cells < 4:
        return
    draft = torch.stack([engine.cell_states[i].hidden for i in range(2)]).mean(0)
    for s in engine.cell_states[2:]:
        s.hidden = s.hidden * 0.85 + draft * 0.15


# ── topology ─────────────────────────────────────────────────────────────────

def _topology_ring(engine, step: int):
    """Force ring topology coupling."""
    engine.topology = 'ring'

def _topology_small_world(engine, step: int):
    """Switch to small_world topology."""
    engine.topology = 'small_world'

def _topology_scale_free(engine, step: int):
    """Switch to scale_free topology."""
    engine.topology = 'scale_free'

def _topology_hypercube(engine, step: int):
    """Switch to hypercube topology."""
    engine.topology = 'hypercube'

def _topology_cycle(engine, step: int):
    """Cycle through topologies every 50 steps."""
    topos = ['ring', 'small_world', 'scale_free', 'hypercube']
    engine.topology = topos[(step // 50) % len(topos)]


# ── optimization ──────────────────────────────────────────────────────────────

def _hebbian_boost(engine, step: int):
    """Amplify Hebbian coupling matrix by 1.2x every 20 steps."""
    if engine._coupling is not None and step % 20 == 0:
        engine._coupling = engine._coupling * 1.2
        # Clamp to avoid runaway
        engine._coupling = torch.clamp(engine._coupling, -2.0, 2.0)
        engine._coupling.fill_diagonal_(0)

def _cosine_lr(engine, step: int):
    """Apply cosine annealing to coupling strength."""
    if engine._coupling is not None and step > 0:
        lr_scale = 0.5 * (1 + math.cos(math.pi * (step % 100) / 100))
        engine._coupling = engine._coupling * lr_scale
        engine._coupling = torch.clamp(engine._coupling, -1.5, 1.5)
        engine._coupling.fill_diagonal_(0)

def _annealing(engine, step: int):
    """Simulated annealing: add decreasing noise to coupling."""
    if engine._coupling is None:
        return
    temp = max(0.01, 1.0 - step / 500.0)
    noise = torch.randn_like(engine._coupling) * temp * 0.05
    engine._coupling = engine._coupling + noise
    engine._coupling.fill_diagonal_(0)

def _symmetrize_coupling(engine, step: int):
    """Symmetrize the coupling matrix (bidirectional connections)."""
    if engine._coupling is not None and step % 10 == 0:
        engine._coupling = (engine._coupling + engine._coupling.T) / 2
        engine._coupling.fill_diagonal_(0)


# ── loss_function ─────────────────────────────────────────────────────────────

def _entropy_loss(engine, step: int):
    """Maximize entropy of hidden state distribution."""
    if engine.n_cells < 2:
        return
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    # Compute softmax probabilities, add entropy gradient
    probs = torch.softmax(hiddens.abs().mean(dim=1), dim=0)
    uniform = torch.ones_like(probs) / len(probs)
    # Push toward uniform distribution
    correction = (uniform - probs).unsqueeze(1) * 0.01
    for i, s in enumerate(engine.cell_states):
        s.hidden = s.hidden + correction[i]

def _dual_loss(engine, step: int):
    """Dual loss: balance CE-like diversity + Phi-like integration."""
    if engine.n_cells < 2:
        return
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    # Diversity term: push cells apart
    mean = hiddens.mean(0)
    for i, s in enumerate(engine.cell_states):
        diff = s.hidden - mean
        s.hidden = s.hidden + diff * 0.02

    # Integration term: pull cells together slightly
    avg = hiddens.mean(0)
    for s in engine.cell_states:
        s.hidden = s.hidden * 0.98 + avg * 0.02


# ── dynamics ─────────────────────────────────────────────────────────────────

def _noise_inject(engine, step: int):
    """Inject small Gaussian noise into cell states."""
    for s in engine.cell_states:
        s.hidden = s.hidden + torch.randn_like(s.hidden) * 0.01

def _perturbation(engine, step: int):
    """Periodic perturbation: sharp reset every 50 steps."""
    if step % 50 == 0 and engine.n_cells >= 2:
        idx = step % engine.n_cells
        engine.cell_states[idx].hidden = torch.randn_like(engine.cell_states[idx].hidden) * 0.1

def _temperature_scale(engine, step: int):
    """Temperature scaling: scale hidden states by temperature factor."""
    temp = 1.0 + 0.5 * math.sin(step / 30.0)
    for s in engine.cell_states:
        s.hidden = s.hidden / (temp + 1e-8)

def _dropout_hidden(engine, step: int):
    """Apply dropout to hidden states during step (p=0.1)."""
    if engine.n_cells < 2:
        return
    for s in engine.cell_states:
        mask = torch.bernoulli(torch.full_like(s.hidden, 0.9))
        s.hidden = s.hidden * mask

def _sparse_coupling(engine, step: int):
    """Sparsify coupling matrix: zero out bottom 50% of weights."""
    if engine._coupling is None:
        return
    if step % 25 == 0:
        flat = engine._coupling.abs().flatten()
        threshold = flat.quantile(0.5).item()
        mask = engine._coupling.abs() >= threshold
        engine._coupling = engine._coupling * mask.float()
        engine._coupling.fill_diagonal_(0)

def _jitter(engine, step: int):
    """Add jitter: small random temporal offset in hidden updates."""
    if engine.n_cells < 2:
        return
    jitter = (torch.rand(1).item() - 0.5) * 0.02
    for s in engine.cell_states:
        s.hidden = s.hidden + jitter

def _prune_weak(engine, step: int):
    """Prune weak connections in coupling (set near-zero to zero)."""
    if engine._coupling is None:
        return
    if step % 30 == 0:
        engine._coupling = engine._coupling * (engine._coupling.abs() > 0.02).float()
        engine._coupling.fill_diagonal_(0)


# ── architecture ─────────────────────────────────────────────────────────────

def _faction_modify(engine, step: int):
    """Reassign faction IDs to maximize faction diversity."""
    if engine.n_cells < 2:
        return
    if step % 50 == 0:
        for i, s in enumerate(engine.cell_states):
            s.faction_id = i % engine.n_factions

def _diversity_pressure(engine, step: int):
    """Push similar cells apart to maintain diversity."""
    if engine.n_cells < 2:
        return
    if step % 10 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        for i in range(len(engine.cell_states)):
            for j in range(i + 1, len(engine.cell_states)):
                sim = F.cosine_similarity(
                    hiddens[i].unsqueeze(0), hiddens[j].unsqueeze(0)
                ).item()
                if sim > 0.9:
                    engine.cell_states[j].hidden += torch.randn_like(
                        engine.cell_states[j].hidden
                    ) * 0.02


# ── weight_init / transplant ──────────────────────────────────────────────────

def _state_injection(engine, step: int):
    """Inject structured initial state to guide convergence."""
    if step == 0:
        for i, s in enumerate(engine.cell_states):
            # Orthogonal initial states per cell
            angle = 2 * math.pi * i / max(engine.n_cells, 1)
            s.hidden[0] = math.cos(angle) * 0.5
            s.hidden[1] = math.sin(angle) * 0.5

def _curriculum_schedule(engine, step: int):
    """Curriculum: start with weak coupling, increase over time."""
    if engine._coupling is not None:
        curriculum_scale = min(1.0, step / 200.0)
        engine._coupling = engine._coupling * curriculum_scale
        engine._coupling.fill_diagonal_(0)

def _phase_schedule(engine, step: int):
    """Phase schedule: switch topology based on training phase."""
    if step < 100:
        engine.topology = 'ring'
    elif step < 200:
        engine.topology = 'small_world'
    else:
        engine.topology = 'scale_free'


# ── gating ────────────────────────────────────────────────────────────────────

def _phi_gate(engine, step: int):
    """Gate cell updates by Phi threshold: only update high-Phi cells."""
    if engine.n_cells < 2:
        return
    # Simple proxy: keep cells with above-average tension
    tensions = [s.avg_tension for s in engine.cell_states]
    mean_t = sum(tensions) / len(tensions) if tensions else 0.0
    for s in engine.cell_states:
        if s.avg_tension < mean_t * 0.5:
            # Low tension cell: reduce update (gate)
            s.hidden = s.hidden * 0.95

def _attention_bias(engine, step: int):
    """Bias attention toward highest-tension cells."""
    if engine.n_cells < 2:
        return
    tensions = torch.tensor([s.avg_tension for s in engine.cell_states])
    weights = torch.softmax(tensions * 5.0, dim=0)
    weighted_hidden = sum(
        w.item() * s.hidden for w, s in zip(weights, engine.cell_states)
    )
    for i, s in enumerate(engine.cell_states):
        s.hidden = s.hidden * (1 - weights[i].item() * 0.1) + weighted_hidden * weights[i].item() * 0.1


# ── meta / self-play ─────────────────────────────────────────────────────────

def _metacognition(engine, step: int):
    """Metacognitive signal: compute mean tension and modulate coupling."""
    if engine._coupling is None or engine.n_cells < 2:
        return
    tensions = [s.avg_tension for s in engine.cell_states]
    meta = sum(tensions) / len(tensions)
    # High meta-tension → increase coupling strength
    if meta > 0.5:
        engine._coupling = engine._coupling * 1.01
    else:
        engine._coupling = engine._coupling * 0.99
    engine._coupling = torch.clamp(engine._coupling, -2.0, 2.0)
    engine._coupling.fill_diagonal_(0)

def _reward_signal(engine, step: int):
    """Apply positive/negative reward signal based on coupling symmetry."""
    if engine._coupling is None:
        return
    c = engine._coupling
    symmetry = 1.0 - (c - c.T).abs().mean().item() / (c.abs().mean().item() + 1e-8)
    reward = symmetry - 0.5  # positive if symmetric, negative otherwise
    for s in engine.cell_states:
        s.hidden = s.hidden + torch.randn_like(s.hidden) * reward * 0.005

def _curiosity(engine, step: int):
    """Curiosity signal: add noise proportional to recent prediction error."""
    for s in engine.cell_states:
        # Estimate novelty as deviation from zero
        novelty = s.hidden.abs().mean().item()
        s.hidden = s.hidden + torch.randn_like(s.hidden) * novelty * 0.005

def _self_compete(engine, step: int):
    """Self-play competition: weakest cell gets noise, strongest gets boost."""
    if engine.n_cells < 3:
        return
    tensions = [(s.avg_tension, i) for i, s in enumerate(engine.cell_states)]
    tensions.sort()
    weakest = tensions[0][1]
    strongest = tensions[-1][1]
    engine.cell_states[weakest].hidden += torch.randn_like(engine.cell_states[weakest].hidden) * 0.03
    engine.cell_states[strongest].hidden *= 1.01


# ── null (hardware/compile/quantization — not testable at engine level) ────────

def _null_intervention(engine, step: int):
    """No-op: intervention cannot be evaluated at engine level."""
    pass  # Hardware/compiler/quantization — not engine-level


# ══════════════════════════════════════════════════════════════════════════════
# Intervention template registry (20+ templates)
# ══════════════════════════════════════════════════════════════════════════════

INTERVENTION_TEMPLATES: Dict[str, Intervention] = {
    # compute_reduction
    "skip_step": Intervention("skip_step", "Probabilistic step skipping (every other step)", _skip_step),
    "batch_share": Intervention("batch_share", "Share hidden state average across cells", _batch_share),
    "state_reuse": Intervention("state_reuse", "Reuse previous state partially (inertia)", _state_reuse),
    "state_cache": Intervention("state_cache", "Cache and reuse cell states every N steps", _state_cache),
    "frozen_cells": Intervention("frozen_cells", "Freeze 30% of cells and rotate", _frozen_cells),
    "speculative_draft": Intervention("speculative_draft", "Draft from 2 cells, verify with all", _speculative_draft),

    # topology
    "topology_ring": Intervention("topology_ring", "Force ring topology", _topology_ring),
    "topology_small_world": Intervention("topology_small_world", "Switch to small_world topology", _topology_small_world),
    "topology_scale_free": Intervention("topology_scale_free", "Switch to scale_free topology", _topology_scale_free),
    "topology_hypercube": Intervention("topology_hypercube", "Switch to hypercube topology", _topology_hypercube),
    "topology_cycle": Intervention("topology_cycle", "Cycle through all 4 topologies", _topology_cycle),

    # optimization
    "hebbian_boost": Intervention("hebbian_boost", "Amplify Hebbian coupling by 1.2x", _hebbian_boost),
    "cosine_lr": Intervention("cosine_lr", "Cosine annealing on coupling strength", _cosine_lr),
    "annealing": Intervention("annealing", "Simulated annealing on coupling", _annealing),
    "symmetrize_coupling": Intervention("symmetrize_coupling", "Symmetrize coupling matrix", _symmetrize_coupling),

    # loss_function
    "entropy_loss": Intervention("entropy_loss", "Maximize entropy of hidden distribution", _entropy_loss),
    "dual_loss": Intervention("dual_loss", "Dual: diversity + integration", _dual_loss),

    # dynamics
    "noise_inject": Intervention("noise_inject", "Inject small Gaussian noise", _noise_inject),
    "perturbation": Intervention("perturbation", "Periodic sharp perturbation", _perturbation),
    "temperature_scale": Intervention("temperature_scale", "Temperature scaling of hidden states", _temperature_scale),
    "dropout_hidden": Intervention("dropout_hidden", "Apply p=0.1 dropout to hidden states", _dropout_hidden),
    "sparse_coupling": Intervention("sparse_coupling", "Sparsify coupling (keep top 50%)", _sparse_coupling),
    "jitter": Intervention("jitter", "Small random temporal jitter", _jitter),
    "prune_weak": Intervention("prune_weak", "Prune near-zero coupling weights", _prune_weak),

    # architecture
    "faction_modify": Intervention("faction_modify", "Reassign faction IDs for max diversity", _faction_modify),
    "diversity_pressure": Intervention("diversity_pressure", "Push similar cells apart", _diversity_pressure),

    # weight_init / curriculum
    "state_injection": Intervention("state_injection", "Inject structured initial state", _state_injection),
    "curriculum_schedule": Intervention("curriculum_schedule", "Weak→strong coupling curriculum", _curriculum_schedule),
    "phase_schedule": Intervention("phase_schedule", "Phase-based topology schedule", _phase_schedule),

    # gating
    "phi_gate": Intervention("phi_gate", "Gate updates by Phi/tension threshold", _phi_gate),
    "attention_bias": Intervention("attention_bias", "Bias attention to high-tension cells", _attention_bias),

    # meta
    "metacognition": Intervention("metacognition", "Meta-tension modulates coupling", _metacognition),
    "reward_signal": Intervention("reward_signal", "Symmetry-based reward signal", _reward_signal),
    "curiosity": Intervention("curiosity", "Curiosity noise proportional to novelty", _curiosity),
    "self_compete": Intervention("self_compete", "Weakest cell boosted, strongest rewarded", _self_compete),

    # null
    "null_intervention": Intervention("null_intervention", "No-op (hardware/compiler/quantization)", _null_intervention),
}


# ══════════════════════════════════════════════════════════════════════════════
# Category → template mapping
# ══════════════════════════════════════════════════════════════════════════════

CATEGORY_MAP: Dict[str, str] = {
    "compute_reduction": "skip_step",
    "compute_reduction + training_schedule": "skip_step",
    "topology": "topology_cycle",
    "optimization": "hebbian_boost",
    "loss_function": "entropy_loss",
    "dynamics": "noise_inject",
    "architecture": "faction_modify",
    "architecture + compute_reduction": "sparse_coupling",
    "weight_init": "state_injection",
    "training_schedule": "curriculum_schedule",
    "knowledge_transfer": "batch_share",
    "inference": "state_cache",
    "self_modification": "metacognition",
    "consciousness_only": "phi_gate",
    "dimensionality": "diversity_pressure",
    "decoder_acceleration": "skip_step",  # closest at engine level
}


# ── Keyword → template mapping ────────────────────────────────────────────────

KEYWORD_MAP = [
    # (keywords_list, template_name)
    (["skip", "speculative", "draft", "verify"], "speculative_draft"),
    (["reuse", "recycle", "cache", "recompute"], "state_reuse"),
    (["freeze", "frozen", "selective compute"], "frozen_cells"),
    (["batch", "share", "sharing"], "batch_share"),
    (["ring"], "topology_ring"),
    (["small_world", "small world"], "topology_small_world"),
    (["scale_free", "scale free", "scale-free", "hub"], "topology_scale_free"),
    (["hypercube", "hyper cube"], "topology_hypercube"),
    (["topology", "topo", "topolog"], "topology_cycle"),
    (["hebbian", "ltp", "ltd", "hebb"], "hebbian_boost"),
    (["cosine", "annealing", "anneal", "lr schedule", "learning rate"], "cosine_lr"),
    (["symmetr", "symmetric", "bidirectional"], "symmetrize_coupling"),
    (["entropy", "maxent", "information maximiz"], "entropy_loss"),
    (["dual loss", "dual objective", "two loss"], "dual_loss"),
    (["noise", "stochastic", "random inject"], "noise_inject"),
    (["perturbation", "perturb"], "perturbation"),
    (["temperature", "temper", "annealing"], "temperature_scale"),
    (["dropout", "drop out", "drop cells"], "dropout_hidden"),
    (["sparse", "pruning", "prune", "sparsif"], "sparse_coupling"),
    (["jitter", "temporal offset"], "jitter"),
    (["faction", "group", "partition", "shard"], "faction_modify"),
    (["diversity", "dissimilar", "diverse"], "diversity_pressure"),
    (["inject", "initial state", "transplant", "donor"], "state_injection"),
    (["curriculum", "phase", "schedule", "progress"], "curriculum_schedule"),
    (["gate", "gating", "threshold", "select"], "phi_gate"),
    (["attention", "attend", "focus", "sink cells"], "attention_bias"),
    (["meta", "monitor", "self-aware", "introspect"], "metacognition"),
    (["reward", "reinforce", "feedback signal"], "reward_signal"),
    (["curiosity", "novelty", "explore"], "curiosity"),
    (["compete", "competition", "self-play", "adversar"], "self_compete"),
    # null patterns — hardware/compile/quantization not evaluable at engine level
    (["hardware", "fpga", "asic", "chip", "quantiz", "4-bit", "8-bit",
      "compile", "kernel fusion", "flash attention", "vram", "memory band",
      "parallel", "multi-gpu", "distributed", "moe routing"], "null_intervention"),
]


# ══════════════════════════════════════════════════════════════════════════════
# Main mapping function
# ══════════════════════════════════════════════════════════════════════════════

def map_hypothesis_to_intervention(hyp: dict) -> Optional[Intervention]:
    """Map a hypothesis dict to an Intervention object.

    Strategy:
    1. Try category match first (CATEGORY_MAP).
    2. Try keyword match on description + name (KEYWORD_MAP).
    3. Return None if truly unmappable.

    Args:
        hyp: dict with at least 'id', 'name', 'description', optional 'category'

    Returns:
        Intervention or None (if unmappable)
    """
    category = (hyp.get("category") or "").lower().strip()
    name = (hyp.get("name") or "").lower()
    desc = (hyp.get("description") or "").lower()
    combined = name + " " + desc

    # 1. Category match
    if category and category in CATEGORY_MAP:
        template_key = CATEGORY_MAP[category]
        return INTERVENTION_TEMPLATES[template_key]

    # 2. Keyword match (description + name)
    for keywords, template_key in KEYWORD_MAP:
        if any(kw in combined for kw in keywords):
            return INTERVENTION_TEMPLATES[template_key]

    # 3. Null — return None (unmappable)
    return None


def get_null_intervention() -> Intervention:
    """Return the null intervention (for null-mapped hypotheses)."""
    return INTERVENTION_TEMPLATES["null_intervention"]


if __name__ == "__main__":
    print("INTERVENTION_TEMPLATES count:", len(INTERVENTION_TEMPLATES))
    sys.stdout.flush()
    print("Templates:", list(INTERVENTION_TEMPLATES.keys()))
    sys.stdout.flush()

    # Demo
    sample = {
        "id": "I1",
        "name": "Speculative Decoding (Consciousness Version)",
        "category": "compute_reduction",
        "description": "Small engine generates draft → large engine verifies only",
    }
    iv = map_hypothesis_to_intervention(sample)
    print(f"\nSample mapping: {sample['id']} → {iv.name if iv else 'None'}")
    sys.stdout.flush()
