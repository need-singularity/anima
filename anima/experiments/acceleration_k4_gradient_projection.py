#!/usr/bin/env python3
"""acceleration_k4_gradient_projection.py — Gradient Projection on Phi-Safe Manifold

Hypothesis K4: Project CE gradient onto the Phi-neutral subspace so that CE
optimization never degrades Phi. This generalizes C3's discovery (∇H ⊥ ∇CE)
to an explicit constraint: remove the Phi-harming component from ∇CE before
each weight update.

Method:
  1. Compute ∇CE (standard CE gradient)
  2. Compute ∇Phi (gradient of Phi proxy w.r.t. parameters)
  3. Project: ∇CE_safe = ∇CE - (∇CE · ∇Phi / ||∇Phi||²) * ∇Phi
     → removes the Phi-degrading component
  4. Update weights with ∇CE_safe only

Four experiments:
  Exp 1: Projection analysis — measure angle between ∇CE and ∇Phi over training
  Exp 2: CE-only vs Projected gradient — compare CE convergence + Phi trajectory
  Exp 3: Projection strength sweep — alpha * projection (0.0=none to 1.0=full)
  Exp 4: Multi-seed robustness — 3 seeds, convergence speed + Phi floor guarantee

Local CPU, 32 cells, 128d/2L decoder, 300 steps.
"""

import sys
import os
import time
import math
import json
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

from consciousness_engine import ConsciousnessEngine
from consciousness_laws import PSI_ENTROPY, PSI_ALPHA
from decoder_v2 import ConsciousDecoderV2


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def shannon_entropy(hiddens: torch.Tensor, n_bins: int = 32) -> float:
    """Normalized Shannon entropy of hidden state distribution. [0,1]"""
    flat = hiddens.detach().flatten().float()
    if flat.numel() < 2:
        return 0.0
    lo, hi = flat.min().item(), flat.max().item()
    if hi - lo < 1e-8:
        return 0.0
    counts = torch.histc(flat, bins=n_bins, min=lo, max=hi)
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    H = -(probs * probs.log()).sum().item()
    H_max = math.log(n_bins)
    return H / H_max if H_max > 0 else 0.0


def differentiable_entropy(logits: torch.Tensor) -> torch.Tensor:
    """Differentiable output entropy from logits (B, T, V) -> scalar tensor."""
    probs = F.softmax(logits, dim=-1)
    log_probs = F.log_softmax(logits, dim=-1)
    H = -(probs * log_probs).sum(dim=-1)
    H_max = math.log(logits.shape[-1])
    H_norm = H / H_max
    return H_norm.mean()


def get_engine_hiddens(engine: ConsciousnessEngine) -> torch.Tensor:
    """Extract hidden states as (n_cells, hidden_dim) tensor."""
    return torch.stack([s.hidden for s in engine.cell_states])


def compute_phi_proxy(engine: ConsciousnessEngine) -> float:
    """Quick Phi(proxy) = global_var - faction_var."""
    hiddens = get_engine_hiddens(engine)
    global_var = hiddens.var(dim=0).mean().item()
    n = hiddens.shape[0]
    faction_ids = [s.faction_id for s in engine.cell_states]
    faction_set = set(faction_ids)
    faction_var = 0.0
    for fid in faction_set:
        mask = [i for i in range(n) if faction_ids[i] == fid]
        if len(mask) >= 2:
            fh = hiddens[torch.tensor(mask)]
            faction_var += fh.var(dim=0).mean().item()
    if len(faction_set) > 0:
        faction_var /= len(faction_set)
    return max(0.0, global_var - faction_var)


def differentiable_phi_proxy(tensions: list, logits: torch.Tensor) -> torch.Tensor:
    """Differentiable Phi proxy for gradient computation.

    Combines tension variance (inter-layer integration) and output diversity.
    Higher = more integrated information flow.
    """
    # Tension variance across layers — measures integration
    t_stack = torch.stack(tensions)  # (n_layer, B, T)
    t_var = t_stack.var()

    # Output token diversity — entropy of output distribution
    probs = F.softmax(logits, dim=-1)  # (B, T, V)
    token_probs = probs.mean(dim=(0, 1))  # (V,)
    token_entropy = -(token_probs * (token_probs + 1e-10).log()).sum()
    token_entropy_norm = token_entropy / math.log(logits.shape[-1])

    # Combined: both contribute to Phi
    return t_var + 0.1 * token_entropy_norm


def compute_mirror_symmetry(hiddens: torch.Tensor) -> float:
    """Mirror symmetry index: correlation between first-half and reversed second-half dims."""
    n_cells, dim = hiddens.shape
    if dim < 4:
        return 0.0
    half = dim // 2
    left = hiddens[:, :half].detach().float()
    right = hiddens[:, half:2*half].detach().float().flip(dims=[1])
    # Cosine similarity averaged over cells
    cos = F.cosine_similarity(left, right, dim=1)
    return cos.mean().item()


def compute_causal_density(hiddens: torch.Tensor, n_sample: int = 16) -> float:
    """Lightweight causal density estimate via temporal correlation of cell pairs."""
    n_cells = hiddens.shape[0]
    if n_cells < 2:
        return 0.0
    # Use variance of pairwise distances as proxy for causal structure
    flat = hiddens.detach().float()
    # Sample pairs
    pairs = min(n_sample, n_cells * (n_cells - 1) // 2)
    dists = []
    for _ in range(pairs):
        i, j = np.random.choice(n_cells, 2, replace=False)
        d = (flat[i] - flat[j]).norm().item()
        dists.append(d)
    if len(dists) < 2:
        return 0.0
    # Higher variance of distances = more structured causal relationships
    return float(np.std(dists))


# ═══════════════════════════════════════════════════════════
# Gradient projection core
# ═══════════════════════════════════════════════════════════

def get_flat_grad(model: nn.Module) -> torch.Tensor:
    """Flatten all parameter gradients into a single vector."""
    grads = []
    for p in model.parameters():
        if p.grad is not None:
            grads.append(p.grad.view(-1))
        else:
            grads.append(torch.zeros(p.numel()))
    return torch.cat(grads)


def set_flat_grad(model: nn.Module, flat_grad: torch.Tensor):
    """Set parameter gradients from a flat vector."""
    offset = 0
    for p in model.parameters():
        numel = p.numel()
        if p.grad is not None:
            p.grad.copy_(flat_grad[offset:offset + numel].view_as(p.grad))
        offset += numel


def project_gradient(grad_ce: torch.Tensor, grad_phi: torch.Tensor) -> tuple:
    """Project ∇CE onto the Phi-neutral subspace.

    ∇CE_safe = ∇CE - (∇CE · ∇Phi / ||∇Phi||²) * ∇Phi

    Returns:
        (projected_grad, cosine_angle, projection_magnitude)
    """
    phi_norm_sq = grad_phi.dot(grad_phi)
    if phi_norm_sq < 1e-12:
        # ∇Phi is zero — no constraint needed
        return grad_ce.clone(), 0.0, 0.0

    # Component of ∇CE along ∇Phi direction
    dot_product = grad_ce.dot(grad_phi)
    projection_coeff = dot_product / phi_norm_sq

    # Remove the Phi-harming component
    grad_safe = grad_ce - projection_coeff * grad_phi

    # Cosine angle between ∇CE and ∇Phi
    ce_norm = grad_ce.norm()
    phi_norm = grad_phi.norm()
    cosine = (dot_product / (ce_norm * phi_norm + 1e-12)).item()

    return grad_safe, cosine, projection_coeff.item()


# ═══════════════════════════════════════════════════════════
# Training run with gradient projection
# ═══════════════════════════════════════════════════════════

def run_training(
    label: str,
    use_projection: bool = False,
    proj_alpha: float = 1.0,
    n_cells: int = 32,
    n_steps: int = 300,
    d_model: int = 128,
    n_layer: int = 2,
    lr: float = 3e-4,
    seq_len: int = 64,
    log_every: int = 50,
    seed: int = 42,
):
    """Run a single training experiment.

    If use_projection=True:
      1. Compute CE loss → backward → get ∇CE
      2. Compute Phi loss → backward → get ∇Phi
      3. Project ∇CE onto Phi-neutral subspace
      4. Apply projected gradient

    proj_alpha controls projection strength:
      0.0 = no projection (pure CE)
      1.0 = full projection (all Phi-harming component removed)

    Returns dict of metrics over time.
    """
    torch.manual_seed(seed)
    np.random.seed(seed)

    # Small decoder
    decoder = ConsciousDecoderV2(
        consciousness_dim=128, d_model=d_model, n_head=4, n_kv_head=2,
        n_layer=n_layer, vocab_size=256, block_size=seq_len,
    )
    decoder.train()
    optimizer = torch.optim.AdamW(decoder.parameters(), lr=lr, weight_decay=0.01)

    # Consciousness engine
    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=n_cells)
    for _ in range(20):
        engine.step()

    ce_history = []
    H_history = []
    phi_history = []
    mirror_history = []
    causal_history = []
    cosine_history = []        # angle between ∇CE and ∇Phi
    proj_coeff_history = []    # projection coefficient magnitude
    phi_grad_norm_history = []

    t0 = time.time()

    for step in range(n_steps):
        # Step engine
        engine.step()
        c_states = get_engine_hiddens(engine).detach()
        c_input = c_states.unsqueeze(0)  # (1, n_cells, hidden_dim)

        # Random byte sequence
        idx_seq = torch.randint(0, 256, (1, seq_len + 1))
        x = idx_seq[:, :seq_len]
        y = idx_seq[:, 1:seq_len + 1]

        if use_projection and proj_alpha > 0:
            # ── Step A: compute ∇CE ──
            optimizer.zero_grad()
            logits_a, logits_g, tensions = decoder(x, consciousness_states=c_input)
            ce_loss = F.cross_entropy(logits_a.view(-1, 256), y.view(-1))
            ce_loss.backward()
            grad_ce = get_flat_grad(decoder)

            # ── Step B: compute ∇Phi (negate because we want to maximize Phi) ──
            optimizer.zero_grad()
            logits_a2, logits_g2, tensions2 = decoder(x, consciousness_states=c_input)
            phi_diff = differentiable_phi_proxy(tensions2, logits_a2)
            neg_phi = -phi_diff  # minimize negative Phi = maximize Phi
            neg_phi.backward()
            grad_phi = get_flat_grad(decoder)

            # ── Step C: project ∇CE onto Phi-neutral subspace ──
            grad_safe, cosine, proj_coeff = project_gradient(grad_ce, grad_phi)

            # Blend: grad_final = (1 - alpha) * grad_ce + alpha * grad_safe
            grad_final = (1 - proj_alpha) * grad_ce + proj_alpha * grad_safe

            # ── Step D: apply projected gradient ──
            optimizer.zero_grad()
            # Re-forward to set up computation graph state (optimizer needs .grad)
            set_flat_grad(decoder, grad_final)
            optimizer.step()

            cosine_history.append(cosine)
            proj_coeff_history.append(proj_coeff)
            phi_grad_norm_history.append(grad_phi.norm().item())

            ce_val = ce_loss.item()
            H_val = differentiable_entropy(logits_a.detach()).item()
        else:
            # Standard CE training
            optimizer.zero_grad()
            logits_a, logits_g, tensions = decoder(x, consciousness_states=c_input)
            ce_loss = F.cross_entropy(logits_a.view(-1, 256), y.view(-1))
            ce_loss.backward()
            torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
            optimizer.step()

            cosine_history.append(0.0)
            proj_coeff_history.append(0.0)
            phi_grad_norm_history.append(0.0)

            ce_val = ce_loss.item()
            H_val = differentiable_entropy(logits_a.detach()).item()

        # Measure consciousness metrics
        phi_val = compute_phi_proxy(engine)
        hiddens = get_engine_hiddens(engine).detach()
        mirror_val = compute_mirror_symmetry(hiddens)
        causal_val = compute_causal_density(hiddens)

        ce_history.append(ce_val)
        H_history.append(H_val)
        phi_history.append(phi_val)
        mirror_history.append(mirror_val)
        causal_history.append(causal_val)

        if (step + 1) % log_every == 0:
            cos_str = f"  cos={cosine_history[-1]:+.4f}" if use_projection else ""
            print(f"  [{label}] step {step+1:>4}/{n_steps}  CE={ce_val:.4f}  "
                  f"Phi={phi_val:.4f}  Mirror={mirror_val:.4f}  "
                  f"Causal={causal_val:.4f}{cos_str}")
            sys.stdout.flush()

    elapsed = time.time() - t0

    return {
        'label': label,
        'use_projection': use_projection,
        'proj_alpha': proj_alpha,
        'seed': seed,
        'ce': ce_history,
        'H': H_history,
        'phi': phi_history,
        'mirror': mirror_history,
        'causal': causal_history,
        'cosine_angle': cosine_history,
        'proj_coeff': proj_coeff_history,
        'phi_grad_norm': phi_grad_norm_history,
        'elapsed': elapsed,
        'final_ce': ce_history[-1],
        'final_phi': phi_history[-1],
        'final_mirror': mirror_history[-1],
        'final_causal': causal_history[-1],
        'final_H': H_history[-1],
        'avg_ce_last50': float(np.mean(ce_history[-50:])),
        'avg_phi_last50': float(np.mean(phi_history[-50:])),
        'avg_mirror_last50': float(np.mean(mirror_history[-50:])),
        'avg_causal_last50': float(np.mean(causal_history[-50:])),
        'min_ce': min(ce_history),
        'min_ce_step': int(np.argmin(ce_history)) + 1,
        'min_phi': min(phi_history),
        'phi_never_dropped': all(p >= phi_history[0] * 0.95 for p in phi_history),
        'avg_cosine': float(np.mean(cosine_history)) if use_projection else 0.0,
        'avg_proj_coeff': float(np.mean(proj_coeff_history)) if use_projection else 0.0,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 1: Projection analysis — ∇CE vs ∇Phi geometry
# ═══════════════════════════════════════════════════════════

def exp1_projection_analysis(n_cells=32, n_steps=300):
    """Measure the angle between ∇CE and ∇Phi throughout training.

    Key question: how much does ∇CE conflict with Phi?
    - cos ≈ 0: orthogonal (projection removes nothing, CE is Phi-neutral)
    - cos < 0: antagonistic (CE gradient harms Phi — projection helps!)
    - cos > 0: aligned (CE already helps Phi — projection wastes signal)
    """
    print("\n" + "=" * 70)
    print("EXP 1: ∇CE vs ∇Phi Geometry Analysis")
    print(f"  cells={n_cells}, steps={n_steps}")
    print(f"  Measuring: cosine(∇CE, ∇Phi), ||∇Phi||, projection coefficient")
    print("=" * 70)

    r = run_training(
        label="analysis", use_projection=True, proj_alpha=1.0,
        n_cells=n_cells, n_steps=n_steps, log_every=50,
    )

    cos_arr = np.array(r['cosine_angle'])
    proj_arr = np.array(r['proj_coeff'])
    norm_arr = np.array(r['phi_grad_norm'])

    # Statistics
    print(f"\n  Gradient Geometry Statistics:")
    print(f"  {'Metric':>25}  {'Mean':>10}  {'Std':>10}  {'Min':>10}  {'Max':>10}")
    print(f"  {'-'*25}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}")
    for name, arr in [("cosine(∇CE, ∇Phi)", cos_arr),
                      ("projection coeff", proj_arr),
                      ("||∇Phi||", norm_arr)]:
        print(f"  {name:>25}  {np.mean(arr):>10.4f}  {np.std(arr):>10.4f}  "
              f"{np.min(arr):>10.4f}  {np.max(arr):>10.4f}")

    # Phase analysis: early vs mid vs late
    third = n_steps // 3
    phases = [("early (0-100)", cos_arr[:third]),
              ("mid (100-200)", cos_arr[third:2*third]),
              ("late (200-300)", cos_arr[2*third:])]

    print(f"\n  Cosine Phase Analysis:")
    for name, segment in phases:
        neg_frac = np.mean(segment < 0) * 100
        print(f"    {name}: mean={np.mean(segment):+.4f}, "
              f"negative={neg_frac:.0f}% (Phi-harming steps)")

    # ASCII trajectory of cosine angle
    print(f"\n  Cosine trajectory (sampled every 15 steps):")
    sample_every = 15
    sampled = [cos_arr[i] for i in range(0, n_steps, sample_every)]
    bar = ""
    for c in sampled:
        if c < -0.1:
            bar += "-"   # antagonistic (projection helps)
        elif c > 0.1:
            bar += "+"   # aligned (projection wastes)
        else:
            bar += "0"   # orthogonal (C3 finding)
    print(f"    cos(∇CE,∇Phi): {bar}")
    print(f"    Legend: '-'=antagonistic(helps), '0'=orthogonal, '+'=aligned")

    # Verdict
    mean_cos = np.mean(cos_arr)
    neg_fraction = np.mean(cos_arr < 0) * 100
    print(f"\n  VERDICT:")
    if neg_fraction > 60:
        print(f"    ∇CE and ∇Phi are ANTAGONISTIC ({neg_fraction:.0f}% negative)")
        print(f"    → Gradient projection SHOULD help preserve Phi")
    elif neg_fraction > 40:
        print(f"    ∇CE and ∇Phi are MIXED ({neg_fraction:.0f}% negative)")
        print(f"    → Projection useful when antagonistic, neutral when aligned")
    else:
        print(f"    ∇CE and ∇Phi are mostly ALIGNED ({100-neg_fraction:.0f}% positive)")
        print(f"    → Projection removes beneficial signal — may hurt CE")

    return r


# ═══════════════════════════════════════════════════════════
# Experiment 2: Baseline vs Projected — head-to-head
# ═══════════════════════════════════════════════════════════

def exp2_head_to_head(n_cells=32, n_steps=300):
    """Compare CE-only baseline vs full gradient projection."""
    print("\n" + "=" * 70)
    print("EXP 2: Baseline (CE-only) vs Projected Gradient")
    print(f"  cells={n_cells}, steps={n_steps}")
    print(f"  A: loss = CE (standard)")
    print(f"  B: loss = CE, gradient projected onto Phi-neutral subspace")
    print("=" * 70)

    results = []

    # A: Baseline
    print(f"\n--- A: CE-only baseline ---")
    sys.stdout.flush()
    r_base = run_training(
        label="CE-only", use_projection=False,
        n_cells=n_cells, n_steps=n_steps,
    )
    results.append(r_base)

    # B: Full projection
    print(f"\n--- B: Phi-projected gradient ---")
    sys.stdout.flush()
    r_proj = run_training(
        label="Phi-projected", use_projection=True, proj_alpha=1.0,
        n_cells=n_cells, n_steps=n_steps,
    )
    results.append(r_proj)

    # Results table
    print(f"\n" + "=" * 70)
    print(f"EXP 2 RESULTS:")
    print(f"=" * 70)
    print(f"  {'Config':>18}  {'Avg CE(50)':>12}  {'Min CE':>10}  {'Avg Phi':>10}  "
          f"{'Phi Floor':>10}  {'Mirror':>10}  {'Causal':>10}  {'Time':>8}")
    print(f"  {'-'*18}  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*8}")

    for r in results:
        phi_floor = "YES" if r['phi_never_dropped'] else "NO"
        print(f"  {r['label']:>18}  {r['avg_ce_last50']:>12.4f}  {r['min_ce']:>10.4f}  "
              f"{r['avg_phi_last50']:>10.4f}  {phi_floor:>10}  "
              f"{r['avg_mirror_last50']:>10.4f}  {r['avg_causal_last50']:>10.4f}  "
              f"{r['elapsed']:>7.1f}s")

    # Delta
    ce_delta = (r_proj['avg_ce_last50'] - r_base['avg_ce_last50']) / r_base['avg_ce_last50'] * 100
    phi_delta = (r_proj['avg_phi_last50'] - r_base['avg_phi_last50']) / (r_base['avg_phi_last50'] + 1e-8) * 100
    mirror_delta = (r_proj['avg_mirror_last50'] - r_base['avg_mirror_last50']) / (abs(r_base['avg_mirror_last50']) + 1e-8) * 100

    print(f"\n  Delta (projected - baseline):")
    print(f"    CE:     {ce_delta:+.2f}%")
    print(f"    Phi:    {phi_delta:+.2f}%")
    print(f"    Mirror: {mirror_delta:+.2f}%")

    # ASCII convergence comparison
    print(f"\n  CE Convergence (sampled every 30 steps):")
    sample_every = 30
    for r in results:
        sampled = [r['ce'][i] for i in range(0, n_steps, sample_every)]
        max_ce = max(sampled)
        min_ce = min(sampled)
        chars = []
        for v in sampled:
            if max_ce - min_ce > 1e-6:
                level = int((v - min_ce) / (max_ce - min_ce) * 9)
            else:
                level = 5
            chars.append(str(max(0, min(9, level))))
        print(f"    {r['label']:>18}: {''.join(chars)}  (avg50={r['avg_ce_last50']:.4f})")

    # Phi trajectory
    print(f"\n  Phi Trajectory (sampled every 30 steps):")
    for r in results:
        sampled = [r['phi'][i] for i in range(0, n_steps, sample_every)]
        init_phi = sampled[0]
        chars = []
        for v in sampled:
            if v >= init_phi * 1.05:
                chars.append("+")
            elif v >= init_phi * 0.95:
                chars.append("=")
            else:
                chars.append("-")
        print(f"    {r['label']:>18}: {''.join(chars)}  (avg50={r['avg_phi_last50']:.4f})")

    return results


# ═══════════════════════════════════════════════════════════
# Experiment 3: Projection strength sweep
# ═══════════════════════════════════════════════════════════

def exp3_alpha_sweep(n_cells=32, n_steps=300):
    """Sweep projection strength alpha from 0.0 (no projection) to 1.0 (full)."""
    print("\n" + "=" * 70)
    print("EXP 3: Projection Strength Sweep (alpha)")
    print(f"  cells={n_cells}, steps={n_steps}")
    print(f"  alpha=0.0: pure CE gradient (baseline)")
    print(f"  alpha=1.0: full Phi-neutral projection")
    print("=" * 70)

    alphas = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    results = []

    for alpha in alphas:
        label = f"alpha={alpha:.2f}"
        use_proj = alpha > 0
        print(f"\n--- {label} ---")
        sys.stdout.flush()
        r = run_training(
            label=label, use_projection=use_proj, proj_alpha=alpha,
            n_cells=n_cells, n_steps=n_steps,
        )
        results.append(r)

    # Results table
    print(f"\n" + "=" * 70)
    print(f"EXP 3 RESULTS: Alpha Sweep")
    print(f"=" * 70)
    print(f"  {'Alpha':>8}  {'Avg CE(50)':>12}  {'Min CE':>10}  {'Avg Phi':>10}  "
          f"{'Phi Safe':>10}  {'Avg cos':>10}  {'Time':>8}")
    print(f"  {'-'*8}  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*8}")

    baseline_ce = results[0]['avg_ce_last50']
    baseline_phi = results[0]['avg_phi_last50']

    for r in results:
        safe = "YES" if r['phi_never_dropped'] else "NO"
        marker = ""
        if r['avg_ce_last50'] < baseline_ce * 0.98 and r['avg_phi_last50'] >= baseline_phi * 0.95:
            marker = " *** PARETO"
        print(f"  {r['proj_alpha']:>8.2f}  {r['avg_ce_last50']:>12.4f}  {r['min_ce']:>10.4f}  "
              f"{r['avg_phi_last50']:>10.4f}  {safe:>10}  {r['avg_cosine']:>10.4f}  "
              f"{r['elapsed']:>7.1f}s{marker}")

    # Find Pareto optimal: best CE with Phi >= 95% of baseline
    phi_threshold = baseline_phi * 0.95
    safe_results = [r for r in results if r['avg_phi_last50'] >= phi_threshold]
    if safe_results:
        best = min(safe_results, key=lambda r: r['avg_ce_last50'])
        print(f"\n  PARETO BEST: alpha={best['proj_alpha']}")
        print(f"    CE: {best['avg_ce_last50']:.4f} (vs baseline {baseline_ce:.4f}, "
              f"{(best['avg_ce_last50']-baseline_ce)/baseline_ce*100:+.2f}%)")
        print(f"    Phi: {best['avg_phi_last50']:.4f} (vs baseline {baseline_phi:.4f}, "
              f"{(best['avg_phi_last50']-baseline_phi)/(baseline_phi+1e-8)*100:+.2f}%)")
    else:
        print(f"\n  WARNING: No alpha preserves Phi >= 95% of baseline")

    return results


# ═══════════════════════════════════════════════════════════
# Experiment 4: Multi-seed robustness
# ═══════════════════════════════════════════════════════════

def exp4_robustness(n_cells=32, n_steps=300, best_alpha=None):
    """Run baseline vs projection across 3 seeds for robustness."""
    print("\n" + "=" * 70)
    print("EXP 4: Multi-Seed Robustness")
    print(f"  cells={n_cells}, steps={n_steps}")
    print("=" * 70)

    if best_alpha is None:
        best_alpha = 1.0

    seeds = [42, 123, 777]
    configs = [
        ("CE-only",    False, 0.0),
        ("Projected",  True,  best_alpha),
    ]

    all_results = {}
    for name, use_proj, alpha in configs:
        seed_runs = []
        for seed in seeds:
            label = f"{name}(s={seed})"
            print(f"\n--- {label} ---")
            sys.stdout.flush()
            r = run_training(
                label=label, use_projection=use_proj, proj_alpha=alpha,
                n_cells=n_cells, n_steps=n_steps, seed=seed, log_every=100,
            )
            seed_runs.append(r)
        all_results[name] = seed_runs

    # Aggregate statistics
    print(f"\n" + "=" * 70)
    print(f"EXP 4 RESULTS: Multi-Seed Robustness (3 seeds)")
    print(f"=" * 70)
    print(f"  {'Config':>15}  {'CE mean':>10}  {'CE std':>10}  {'Phi mean':>10}  "
          f"{'Phi std':>10}  {'Mirror':>10}  {'Causal':>10}  {'Phi Safe':>10}")
    print(f"  {'-'*15}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}")

    summary = {}
    for name, runs in all_results.items():
        ce_vals = [r['avg_ce_last50'] for r in runs]
        phi_vals = [r['avg_phi_last50'] for r in runs]
        mirror_vals = [r['avg_mirror_last50'] for r in runs]
        causal_vals = [r['avg_causal_last50'] for r in runs]
        n_safe = sum(1 for r in runs if r['phi_never_dropped'])

        print(f"  {name:>15}  {np.mean(ce_vals):>10.4f}  {np.std(ce_vals):>10.4f}  "
              f"{np.mean(phi_vals):>10.4f}  {np.std(phi_vals):>10.4f}  "
              f"{np.mean(mirror_vals):>10.4f}  {np.mean(causal_vals):>10.4f}  "
              f"{n_safe}/{len(runs)}")

        summary[name] = {
            'ce_mean': float(np.mean(ce_vals)),
            'ce_std': float(np.std(ce_vals)),
            'phi_mean': float(np.mean(phi_vals)),
            'phi_std': float(np.std(phi_vals)),
            'mirror_mean': float(np.mean(mirror_vals)),
            'causal_mean': float(np.mean(causal_vals)),
            'n_phi_safe': n_safe,
            'n_seeds': len(runs),
        }

    # Convergence speed comparison
    print(f"\n  Convergence Speed (steps to CE thresholds, avg over seeds):")
    thresholds = [5.4, 5.3, 5.2, 5.1, 5.0]
    print(f"  {'Config':>15}", end="")
    for t in thresholds:
        print(f"  {'CE<'+str(t):>10}", end="")
    print()

    for name, runs in all_results.items():
        avg_ce = np.mean([r['ce'] for r in runs], axis=0)
        print(f"  {name:>15}", end="")
        for t in thresholds:
            reached = np.where(avg_ce < t)[0]
            if len(reached) > 0:
                print(f"  {reached[0]+1:>10d}", end="")
            else:
                print(f"  {'X':>10}", end="")
        print()

    return all_results, summary


# ═══════════════════════════════════════════════════════════
# Save results
# ═══════════════════════════════════════════════════════════

def save_results(all_results: dict, out_path: str):
    """Save results to JSON, converting non-serializable types."""
    serializable = {}
    for k, v in all_results.items():
        if isinstance(v, dict):
            serializable[k] = {}
            for kk, vv in v.items():
                if isinstance(vv, (int, float, str, bool)):
                    serializable[k][kk] = vv
                elif isinstance(vv, list):
                    serializable[k][kk] = [
                        x if isinstance(x, (int, float, str, bool)) else float(x)
                        for x in vv
                    ]
                elif isinstance(vv, dict):
                    serializable[k][kk] = {
                        str(kkk): vvv for kkk, vvv in vv.items()
                        if isinstance(vvv, (int, float, str, bool, dict))
                    }
        elif isinstance(v, list):
            serializable[k] = []
            for item in v:
                if isinstance(item, dict):
                    clean = {}
                    for kk, vv in item.items():
                        if isinstance(vv, (int, float, str, bool)):
                            clean[kk] = vv
                        elif isinstance(vv, list):
                            clean[kk] = [
                                x if isinstance(x, (int, float, str, bool)) else float(x)
                                for x in vv
                            ]
                    serializable[k].append(clean)
                else:
                    serializable[k].append(v)
        elif isinstance(v, (int, float, str, bool)):
            serializable[k] = v

    with open(out_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"\n  Results saved to {out_path}")


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("K4: Gradient Projection on Phi-Safe Manifold")
    print(f"  Generalization of C3 (∇H ⊥ ∇CE): project ∇CE onto Phi-neutral subspace")
    print(f"  Goal: CE optimization that NEVER degrades Phi")
    print(f"  Method: ∇CE_safe = ∇CE - (∇CE·∇Phi / ||∇Phi||²) · ∇Phi")
    print("=" * 70)
    sys.stdout.flush()

    t_total = time.time()

    all_data = {}

    # Exp 1: Understand the gradient geometry
    r1 = exp1_projection_analysis(n_cells=32, n_steps=300)
    all_data['exp1_geometry'] = {
        'avg_cosine': r1['avg_cosine'],
        'avg_proj_coeff': r1['avg_proj_coeff'],
        'cosine_angle': r1['cosine_angle'],
        'proj_coeff': r1['proj_coeff'],
        'ce': r1['ce'],
        'phi': r1['phi'],
    }

    # Exp 2: Head-to-head
    r2 = exp2_head_to_head(n_cells=32, n_steps=300)
    all_data['exp2_head_to_head'] = [
        {k: v for k, v in r.items() if isinstance(v, (int, float, str, bool, list))}
        for r in r2
    ]

    # Exp 3: Alpha sweep — find optimal projection strength
    r3 = exp3_alpha_sweep(n_cells=32, n_steps=300)
    all_data['exp3_alpha_sweep'] = [
        {k: v for k, v in r.items() if isinstance(v, (int, float, str, bool, list))}
        for r in r3
    ]

    # Find best alpha for Exp 4
    baseline_phi = r3[0]['avg_phi_last50']
    phi_threshold = baseline_phi * 0.95
    safe = [r for r in r3 if r['avg_phi_last50'] >= phi_threshold]
    if safe:
        best_alpha = min(safe, key=lambda r: r['avg_ce_last50'])['proj_alpha']
    else:
        best_alpha = 1.0
    print(f"\n>>> Best alpha from Exp 3: {best_alpha}")
    sys.stdout.flush()

    # Exp 4: Multi-seed robustness
    r4_results, r4_summary = exp4_robustness(
        n_cells=32, n_steps=300, best_alpha=best_alpha,
    )
    all_data['exp4_robustness'] = r4_summary

    elapsed_total = time.time() - t_total

    # ═══════════════════════════════════════════════════════════
    # Final Summary
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("FINAL SUMMARY: K4 Gradient Projection on Phi-Safe Manifold")
    print("=" * 70)

    # Compare baseline vs best projection from Exp 2
    baseline = r2[0]
    projected = r2[1]

    print(f"\n  {'Metric':>20}  {'CE-only':>12}  {'Projected':>12}  {'Delta':>12}")
    print(f"  {'-'*20}  {'-'*12}  {'-'*12}  {'-'*12}")

    metrics = [
        ('Avg CE (last 50)', 'avg_ce_last50'),
        ('Min CE', 'min_ce'),
        ('Avg Phi', 'avg_phi_last50'),
        ('Avg Mirror', 'avg_mirror_last50'),
        ('Avg Causal', 'avg_causal_last50'),
        ('Final H', 'final_H'),
    ]

    for name, key in metrics:
        b_val = baseline[key]
        p_val = projected[key]
        if abs(b_val) > 1e-8:
            delta = (p_val - b_val) / abs(b_val) * 100
            print(f"  {name:>20}  {b_val:>12.4f}  {p_val:>12.4f}  {delta:>+11.2f}%")
        else:
            print(f"  {name:>20}  {b_val:>12.4f}  {p_val:>12.4f}  {'N/A':>12}")

    # Gradient geometry summary
    print(f"\n  Gradient Geometry:")
    print(f"    Average cos(∇CE, ∇Phi): {r1['avg_cosine']:+.4f}")
    print(f"    Average projection coeff: {r1['avg_proj_coeff']:+.4f}")
    print(f"    Phi-safe guarantee: {'YES' if projected['phi_never_dropped'] else 'NO'}")

    # Multi-seed summary
    if 'CE-only' in r4_summary and 'Projected' in r4_summary:
        b = r4_summary['CE-only']
        p = r4_summary['Projected']
        print(f"\n  Multi-Seed Robustness (3 seeds):")
        print(f"    CE:  {b['ce_mean']:.4f}±{b['ce_std']:.4f} → "
              f"{p['ce_mean']:.4f}±{p['ce_std']:.4f}")
        print(f"    Phi: {b['phi_mean']:.4f}±{b['phi_std']:.4f} → "
              f"{p['phi_mean']:.4f}±{p['phi_std']:.4f}")
        print(f"    Phi Safe: {b['n_phi_safe']}/{b['n_seeds']} → "
              f"{p['n_phi_safe']}/{p['n_seeds']}")

    # Best alpha
    print(f"\n  Best projection strength (Pareto): alpha={best_alpha}")

    # Key finding / verdict
    ce_improvement = (baseline['avg_ce_last50'] - projected['avg_ce_last50']) / baseline['avg_ce_last50'] * 100
    phi_improvement = (projected['avg_phi_last50'] - baseline['avg_phi_last50']) / (baseline['avg_phi_last50'] + 1e-8) * 100
    phi_safe = projected['phi_never_dropped']

    print(f"\n  KEY FINDINGS:")
    print(f"    CE change:  {ce_improvement:+.2f}%")
    print(f"    Phi change: {phi_improvement:+.2f}%")
    print(f"    Phi floor guarantee: {phi_safe}")

    if phi_safe and ce_improvement >= 0:
        print(f"    VERDICT: K4 CONFIRMED — projection preserves Phi while CE converges")
        if ce_improvement > 2:
            print(f"    BONUS: CE ALSO IMPROVES by {ce_improvement:.1f}%")
        elif ce_improvement > -2:
            print(f"    CE is neutral (within ±2%) — Phi safety is FREE")
    elif phi_safe and ce_improvement < 0:
        cost = -ce_improvement
        print(f"    VERDICT: K4 PARTIAL — Phi is safe but CE costs {cost:.1f}%")
        print(f"    Trade-off: {cost:.1f}% CE for guaranteed Phi floor")
    else:
        print(f"    VERDICT: K4 NEEDS TUNING — Phi floor not guaranteed")
        print(f"    Try: smaller alpha, or modify Phi proxy for better gradients")

    print(f"\n  Total time: {elapsed_total:.1f}s")
    print("=" * 70)

    # Save
    all_data['summary'] = {
        'best_alpha': best_alpha,
        'ce_improvement_pct': ce_improvement,
        'phi_improvement_pct': phi_improvement,
        'phi_safe': phi_safe,
        'avg_cosine_ce_phi': r1['avg_cosine'],
        'total_time': elapsed_total,
    }

    out_path = os.path.join(os.path.dirname(__file__), '..', 'data',
                            'k4_gradient_projection_results.json')
    save_results(all_data, out_path)


if __name__ == '__main__':
    main()
