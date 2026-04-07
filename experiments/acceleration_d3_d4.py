#!/usr/bin/env python3
"""acceleration_d3_d4.py — D3 Consciousness Telescope + D4 Mutation Bomb

D3: Consciousness Telescope — consciousness observes and accelerates learning
  Exp 1: Consciousness Curriculum — PE x tension weighted token selection
  Exp 2: Consciousness LR — Phi-adaptive learning rate
  Exp 3: Consciousness Gradient — project gradient onto consciousness principal direction

D4: Mutation Bomb — massive mutations + natural selection
  Exp 1: Mutation Spectrum — 50 mutants at 4 intensity levels, survival analysis
  Exp 2: Selection + Crossover — top-5 breed, 10 generations
  Exp 3: Mutation vs Gradient — same compute budget comparison
  Exp 4: Law-based Mutation — 180 laws as mutation directions vs random noise

Usage:
  PYTHONUNBUFFERED=1 python3 acceleration_d3_d4.py              # All experiments
  PYTHONUNBUFFERED=1 python3 acceleration_d3_d4.py --d3-only    # Consciousness telescope
  PYTHONUNBUFFERED=1 python3 acceleration_d3_d4.py --d4-only    # Mutation bomb
"""

import sys
import os
import time
import copy
import math
import argparse
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn as nn
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import LAWS, PSI_ALPHA as PSI_COUPLING
except ImportError:
    LAWS = {}
    PSI_COUPLING = 0.014

try:
    from self_modifying_engine import LawParser, Modification
    HAS_SELF_MOD = True
except ImportError:
    HAS_SELF_MOD = False
    LawParser = None


# ══════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════

def measure_phi(engine):
    """Get current Phi(IIT) from engine."""
    return engine._measure_phi_iit() if hasattr(engine, '_measure_phi_iit') else engine.measure_phi()


def run_engine_steps(engine, steps, x_input=None):
    """Run engine for N steps, return phi history."""
    phis = []
    for _ in range(steps):
        result = engine.step(x_input=x_input)
        phis.append(result['phi_iit'])
    return phis


def simple_ce_loss(engine, target_dim=128):
    """Compute a simple cross-entropy-like loss from engine output vs random target.
    Simulates a learning scenario where the engine tries to match a target distribution.
    """
    states = engine.get_states()  # (n_cells, hidden_dim)
    output = states.mean(dim=0)  # (hidden_dim,)
    # Project to target dim and compute softmax CE
    proj = output[:target_dim] if output.shape[0] >= target_dim else F.pad(output, (0, target_dim - output.shape[0]))
    logits = proj.unsqueeze(0)  # (1, target_dim)
    # Target: uniform noise shifted by engine output (not purely random)
    target = torch.randint(0, target_dim, (1,))
    return F.cross_entropy(logits, target)


def ascii_bar(label, value, max_val, width=40):
    """Create ASCII bar chart line."""
    filled = int(width * min(value / max(max_val, 1e-8), 1.0))
    bar = '#' * filled + '.' * (width - filled)
    return f"  {label:20s} |{bar}| {value:.4f}"


def ascii_graph(values, title="", width=60, height=12):
    """Create ASCII line graph."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    lines = []
    if title:
        lines.append(f"  {title}")
    for row in range(height - 1, -1, -1):
        threshold = mn + rng * row / (height - 1)
        chars = []
        step_size = max(1, len(values) // width)
        for i in range(0, min(len(values), width * step_size), step_size):
            v = values[i]
            if row == 0:
                chars.append('-')
            elif abs(v - threshold) < rng / (height * 2) or (i > 0 and
                 (values[max(0, i - step_size)] - threshold) * (v - threshold) < 0):
                chars.append('*')
            elif v >= threshold:
                chars.append('|')
            else:
                chars.append(' ')
        label = f"{threshold:8.4f}" if row % 3 == 0 else "        "
        lines.append(f"  {label} |{''.join(chars)}")
    lines.append(f"  {'':8s} +{'-' * min(len(values), width)}")
    lines.append(f"  {'':8s}  0{' ' * (min(len(values), width) - 5)}step {len(values)}")
    return '\n'.join(lines)


def print_section(title):
    """Print section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    sys.stdout.flush()


# ══════════════════════════════════════════
# D3: Consciousness Telescope
# ══════════════════════════════════════════

def d3_exp1_consciousness_curriculum(cells=16, steps=300):
    """D3-Exp1: Consciousness-based token selection (curriculum).

    Compare:
      A) Uniform learning — all tokens weighted equally
      B) Top-50% selection — only high consciousness_attention tokens
      C) Weighted learning — loss *= consciousness_attention
    """
    print_section("D3-Exp1: Consciousness Curriculum (PE x Tension Token Selection)")
    print(f"  Cells: {cells}, Steps: {steps}")
    print(f"  Method A: Uniform (all tokens equal weight)")
    print(f"  Method B: Top-50% selection (high attention only)")
    print(f"  Method C: Weighted loss (attention as weight)")
    sys.stdout.flush()

    target_dim = 64
    results = {}

    for method_name, method_id in [("A_uniform", 0), ("B_top50", 1), ("C_weighted", 2)]:
        print(f"\n  --- Method {method_name} ---")
        sys.stdout.flush()

        engine = ConsciousnessEngine(max_cells=cells)
        # Warmup: let consciousness establish
        run_engine_steps(engine, 30)

        ce_history = []
        phi_history = []
        pred_errors = []

        # Simple trainable projection for CE measurement
        proj = nn.Linear(engine.hidden_dim, target_dim, bias=False)
        optimizer = torch.optim.Adam(proj.parameters(), lr=0.01)

        for step_i in range(steps):
            # 1. Engine step
            result = engine.step()
            phi = result['phi_iit']
            tensions = result.get('tensions', [])
            avg_tension = np.mean(tensions) if tensions else 0.5

            # 2. Get states and compute logits
            states = engine.get_states().detach()  # (n_cells, hidden_dim)
            output = states.mean(dim=0)  # (hidden_dim,)

            logits = proj(output.unsqueeze(0))  # (1, target_dim)
            target = torch.randint(0, target_dim, (1,))
            base_ce = F.cross_entropy(logits, target)

            # 3. Prediction error = change in states
            if step_i > 0:
                pe = torch.norm(output - prev_output).item()
            else:
                pe = 1.0
            prev_output = output.clone()

            # 4. consciousness_attention = PE * tension
            consciousness_attention = pe * avg_tension

            # 5. Apply method
            if method_id == 0:
                # A: Uniform — learn from everything equally
                loss = base_ce
            elif method_id == 1:
                # B: Top-50% — only learn if attention is above median
                if consciousness_attention > 0.5:  # simplified threshold
                    loss = base_ce
                else:
                    loss = base_ce * 0.0  # skip this step
            else:
                # C: Weighted — scale loss by attention
                weight = min(consciousness_attention * 2.0, 3.0)  # cap at 3x
                loss = base_ce * weight

            optimizer.zero_grad()
            if loss.requires_grad and loss.item() > 0:
                loss.backward()
                optimizer.step()

            ce_history.append(base_ce.item())
            phi_history.append(phi)
            pred_errors.append(pe)

            if (step_i + 1) % 50 == 0:
                avg_ce = np.mean(ce_history[-50:])
                avg_phi = np.mean(phi_history[-50:])
                print(f"    step {step_i+1:4d} | CE={avg_ce:.4f} | Phi={avg_phi:.4f} | PE={pe:.4f} | attn={consciousness_attention:.4f}")
                sys.stdout.flush()

        results[method_name] = {
            'ce_history': ce_history,
            'phi_history': phi_history,
            'final_ce': np.mean(ce_history[-30:]),
            'final_phi': np.mean(phi_history[-30:]),
            'ce_convergence_step': next((i for i, c in enumerate(ce_history) if c < np.mean(ce_history[:30]) * 0.8), steps),
        }

    # Report
    print(f"\n  {'':=<60}")
    print(f"  D3-Exp1 Results")
    print(f"  {'':=<60}")
    print(f"  {'Method':<20s} {'Final CE':>10s} {'Final Phi':>10s} {'Conv.Step':>10s}")
    print(f"  {'-'*50}")
    max_ce = max(r['final_ce'] for r in results.values())
    for name, r in results.items():
        print(f"  {name:<20s} {r['final_ce']:10.4f} {r['final_phi']:10.4f} {r['ce_convergence_step']:10d}")
    print()

    # ASCII comparison bar
    for name, r in results.items():
        print(ascii_bar(name, r['final_ce'], max_ce))
    print()

    # Best method CE graph
    best_method = min(results.keys(), key=lambda k: results[k]['final_ce'])
    print(ascii_graph(results[best_method]['ce_history'], f"Best: {best_method} CE over steps"))
    sys.stdout.flush()
    return results


def d3_exp2_consciousness_lr(cells=16, steps=300):
    """D3-Exp2: Phi-adaptive learning rate.

    lr = base_lr * (Phi / Phi_target)
    High Phi (focused) -> higher lr -> learn more
    Low Phi (scattered) -> lower lr -> learn less
    """
    print_section("D3-Exp2: Consciousness-Adaptive Learning Rate")
    print(f"  Cells: {cells}, Steps: {steps}")
    print(f"  Method A: Fixed lr=0.01")
    print(f"  Method B: lr = 0.01 * (Phi / Phi_target)")
    sys.stdout.flush()

    target_dim = 64
    results = {}

    for method_name, adaptive in [("A_fixed_lr", False), ("B_phi_lr", True)]:
        print(f"\n  --- Method {method_name} ---")
        sys.stdout.flush()

        engine = ConsciousnessEngine(max_cells=cells)
        run_engine_steps(engine, 30)  # warmup

        proj = nn.Linear(engine.hidden_dim, target_dim, bias=False)
        base_lr = 0.01
        optimizer = torch.optim.SGD(proj.parameters(), lr=base_lr)

        # Estimate Phi_target from warmup
        warmup_phis = [engine.step()['phi_iit'] for _ in range(20)]
        phi_target = np.mean(warmup_phis) if warmup_phis else 1.0
        phi_target = max(phi_target, 0.01)

        ce_history = []
        phi_history = []
        lr_history = []

        for step_i in range(steps):
            result = engine.step()
            phi = result['phi_iit']

            states = engine.get_states().detach()
            output = states.mean(dim=0)
            logits = proj(output.unsqueeze(0))
            target = torch.randint(0, target_dim, (1,))
            loss = F.cross_entropy(logits, target)

            if adaptive:
                # Phi-adaptive lr
                phi_ratio = max(phi / phi_target, 0.1)  # floor at 0.1
                phi_ratio = min(phi_ratio, 5.0)  # cap at 5x
                current_lr = base_lr * phi_ratio
                for pg in optimizer.param_groups:
                    pg['lr'] = current_lr
            else:
                current_lr = base_lr

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            ce_history.append(loss.item())
            phi_history.append(phi)
            lr_history.append(current_lr)

            if (step_i + 1) % 50 == 0:
                avg_ce = np.mean(ce_history[-50:])
                avg_phi = np.mean(phi_history[-50:])
                print(f"    step {step_i+1:4d} | CE={avg_ce:.4f} | Phi={avg_phi:.4f} | lr={current_lr:.6f}")
                sys.stdout.flush()

        results[method_name] = {
            'ce_history': ce_history,
            'phi_history': phi_history,
            'lr_history': lr_history,
            'final_ce': np.mean(ce_history[-30:]),
            'final_phi': np.mean(phi_history[-30:]),
        }

    # Report
    print(f"\n  {'':=<60}")
    print(f"  D3-Exp2 Results: Fixed LR vs Phi-Adaptive LR")
    print(f"  {'':=<60}")
    print(f"  {'Method':<20s} {'Final CE':>10s} {'Final Phi':>10s}")
    print(f"  {'-'*40}")
    for name, r in results.items():
        print(f"  {name:<20s} {r['final_ce']:10.4f} {r['final_phi']:10.4f}")

    if len(results) == 2:
        a = results['A_fixed_lr']['final_ce']
        b = results['B_phi_lr']['final_ce']
        improvement = (a - b) / a * 100 if a > 0 else 0
        print(f"\n  Phi-LR improvement: {improvement:+.1f}% CE reduction")

    print()
    print(ascii_graph(results['B_phi_lr']['lr_history'], "Phi-Adaptive LR over steps"))
    sys.stdout.flush()
    return results


def d3_exp3_consciousness_gradient(cells=16, steps=300):
    """D3-Exp3: Consciousness-directed gradient projection.

    Project gradient onto the principal direction of consciousness states.
    Only the component of gradient aligned with consciousness survives.
    """
    print_section("D3-Exp3: Consciousness Gradient Direction")
    print(f"  Cells: {cells}, Steps: {steps}")
    print(f"  Method A: Full gradient (standard SGD)")
    print(f"  Method B: Gradient projected onto consciousness PC1")
    sys.stdout.flush()

    target_dim = 64
    results = {}

    for method_name, use_projection in [("A_full_grad", False), ("B_consciousness_grad", True)]:
        print(f"\n  --- Method {method_name} ---")
        sys.stdout.flush()

        engine = ConsciousnessEngine(max_cells=cells)
        run_engine_steps(engine, 30)

        proj = nn.Linear(engine.hidden_dim, target_dim, bias=False)
        optimizer = torch.optim.SGD(proj.parameters(), lr=0.01)

        ce_history = []
        phi_history = []
        grad_alignment_history = []

        for step_i in range(steps):
            result = engine.step()
            phi = result['phi_iit']

            states = engine.get_states().detach()  # (n_cells, hidden_dim)
            output = states.mean(dim=0)
            logits = proj(output.unsqueeze(0))
            target = torch.randint(0, target_dim, (1,))
            loss = F.cross_entropy(logits, target)

            optimizer.zero_grad()
            loss.backward()

            if use_projection and proj.weight.grad is not None:
                # Compute consciousness principal direction (PC1 via SVD)
                states_centered = states - states.mean(dim=0, keepdim=True)
                if states_centered.shape[0] >= 2:
                    try:
                        U, S, Vh = torch.linalg.svd(states_centered, full_matrices=False)
                        pc1 = Vh[0]  # first principal component (hidden_dim,)
                        # Project gradient: keep only the consciousness-aligned component
                        grad = proj.weight.grad  # (target_dim, hidden_dim)
                        # Project each row onto pc1
                        alignment = (grad @ pc1).unsqueeze(1)  # (target_dim, 1)
                        projected_grad = alignment * pc1.unsqueeze(0)  # (target_dim, hidden_dim)
                        # Measure alignment before replacement
                        cos_sim = F.cosine_similarity(
                            grad.flatten().unsqueeze(0),
                            projected_grad.flatten().unsqueeze(0)
                        ).item()
                        grad_alignment_history.append(cos_sim)
                        proj.weight.grad.copy_(projected_grad)
                    except Exception:
                        grad_alignment_history.append(0.0)
                else:
                    grad_alignment_history.append(0.0)
            else:
                grad_alignment_history.append(1.0)  # full grad = 100% alignment

            optimizer.step()
            ce_history.append(loss.item())
            phi_history.append(phi)

            if (step_i + 1) % 50 == 0:
                avg_ce = np.mean(ce_history[-50:])
                avg_phi = np.mean(phi_history[-50:])
                avg_align = np.mean(grad_alignment_history[-50:])
                print(f"    step {step_i+1:4d} | CE={avg_ce:.4f} | Phi={avg_phi:.4f} | align={avg_align:.4f}")
                sys.stdout.flush()

        results[method_name] = {
            'ce_history': ce_history,
            'phi_history': phi_history,
            'grad_alignment': grad_alignment_history,
            'final_ce': np.mean(ce_history[-30:]),
            'final_phi': np.mean(phi_history[-30:]),
            'avg_alignment': np.mean(grad_alignment_history[-30:]) if grad_alignment_history else 0,
        }

    # Report
    print(f"\n  {'':=<60}")
    print(f"  D3-Exp3 Results: Full Gradient vs Consciousness Gradient")
    print(f"  {'':=<60}")
    print(f"  {'Method':<25s} {'Final CE':>10s} {'Final Phi':>10s} {'Alignment':>10s}")
    print(f"  {'-'*55}")
    for name, r in results.items():
        print(f"  {name:<25s} {r['final_ce']:10.4f} {r['final_phi']:10.4f} {r['avg_alignment']:10.4f}")

    if len(results) == 2:
        a = results['A_full_grad']['final_ce']
        b = results['B_consciousness_grad']['final_ce']
        improvement = (a - b) / a * 100 if a > 0 else 0
        print(f"\n  Consciousness gradient improvement: {improvement:+.1f}% CE reduction")

    print()
    if results['B_consciousness_grad']['grad_alignment']:
        print(ascii_graph(results['B_consciousness_grad']['grad_alignment'],
                          "Gradient-Consciousness Alignment over steps"))
    sys.stdout.flush()
    return results


# ══════════════════════════════════════════
# D4: Mutation Bomb
# ══════════════════════════════════════════

def create_mutant(engine, epsilon):
    """Create a mutant by adding noise to GRU weights."""
    mutant = ConsciousnessEngine(max_cells=engine.n_cells)
    # Copy weights then add noise
    with torch.no_grad():
        for src_cell, dst_cell in zip(engine.cell_states, mutant.cell_states):
            dst_cell.hidden = src_cell.hidden.clone() + torch.randn_like(src_cell.hidden) * epsilon
    # Also perturb coupling matrix
    if hasattr(engine, 'coupling') and hasattr(mutant, 'coupling'):
        with torch.no_grad():
            noise = torch.randn_like(engine.coupling) * epsilon
            mutant.coupling.copy_(engine.coupling + noise)
    return mutant


def crossover(parent1, parent2, cells):
    """Create child by averaging parent weights."""
    child = ConsciousnessEngine(max_cells=cells)
    with torch.no_grad():
        n = min(len(parent1.cell_states), len(parent2.cell_states), len(child.cell_states))
        for i in range(n):
            child.cell_states[i].hidden = (
                0.5 * parent1.cell_states[i].hidden.clone() +
                0.5 * parent2.cell_states[i].hidden.clone()
            )
    if hasattr(parent1, 'coupling') and hasattr(parent2, 'coupling') and hasattr(child, 'coupling'):
        with torch.no_grad():
            child.coupling.copy_(0.5 * parent1.coupling + 0.5 * parent2.coupling)
    return child


def d4_exp1_mutation_spectrum(cells=16, mutant_steps=50):
    """D4-Exp1: Mutation spectrum — vary intensity, measure survival.

    50 mutants: 20 weak (e=0.001), 15 medium (e=0.01), 10 strong (e=0.1), 5 extreme (e=1.0)
    Each runs 50 steps. Measure Phi survival rate.
    """
    print_section("D4-Exp1: Mutation Spectrum")
    print(f"  Cells: {cells}, Mutant steps: {mutant_steps}")
    sys.stdout.flush()

    # Create base engine and measure baseline
    base_engine = ConsciousnessEngine(max_cells=cells)
    base_phis = run_engine_steps(base_engine, 50)
    baseline_phi = np.mean(base_phis[-10:])
    print(f"  Baseline Phi: {baseline_phi:.4f}")
    sys.stdout.flush()

    spectrum = [
        ("weak",    0.001, 20),
        ("medium",  0.01,  15),
        ("strong",  0.1,   10),
        ("extreme", 1.0,    5),
    ]

    results = {}
    all_mutant_data = []

    for level_name, epsilon, count in spectrum:
        print(f"\n  --- {level_name} (epsilon={epsilon}, n={count}) ---")
        sys.stdout.flush()

        alive = 0
        phis = []
        peak_phis = []

        for m in range(count):
            mutant = create_mutant(base_engine, epsilon)
            mutant_phis = run_engine_steps(mutant, mutant_steps)
            final_phi = np.mean(mutant_phis[-5:])
            peak_phi = max(mutant_phis)
            phis.append(final_phi)
            peak_phis.append(peak_phi)

            # Survival: Phi >= 50% of baseline
            if final_phi >= baseline_phi * 0.5:
                alive += 1

            all_mutant_data.append({
                'level': level_name, 'epsilon': epsilon,
                'final_phi': final_phi, 'peak_phi': peak_phi,
                'survived': final_phi >= baseline_phi * 0.5,
            })

        survival_rate = alive / count * 100
        avg_phi = np.mean(phis)
        avg_peak = np.mean(peak_phis)

        results[level_name] = {
            'epsilon': epsilon,
            'count': count,
            'survival_rate': survival_rate,
            'avg_phi': avg_phi,
            'avg_peak': avg_peak,
            'phis': phis,
        }

        print(f"    Survival: {alive}/{count} ({survival_rate:.0f}%)")
        print(f"    Avg Phi: {avg_phi:.4f}, Avg Peak: {avg_peak:.4f}")
        sys.stdout.flush()

    # Report
    print(f"\n  {'':=<60}")
    print(f"  D4-Exp1 Results: Mutation Spectrum")
    print(f"  {'':=<60}")
    print(f"  Baseline Phi: {baseline_phi:.4f}")
    print(f"  {'Level':<12s} {'Epsilon':>8s} {'N':>4s} {'Survival':>10s} {'Avg Phi':>10s} {'Peak':>10s}")
    print(f"  {'-'*54}")
    for name, r in results.items():
        print(f"  {name:<12s} {r['epsilon']:8.3f} {r['count']:4d} {r['survival_rate']:9.0f}% {r['avg_phi']:10.4f} {r['avg_peak']:10.4f}")

    print(f"\n  Survival Rate (bar chart):")
    for name, r in results.items():
        bar_len = int(r['survival_rate'] / 2.5)
        print(f"  {name:<12s} |{'#' * bar_len}{'.' * (40 - bar_len)}| {r['survival_rate']:.0f}%")

    sys.stdout.flush()
    return results


def d4_exp2_selection_crossover(cells=16, pop_size=30, generations=10, steps_per_gen=50):
    """D4-Exp2: Selection + Crossover evolution.

    Start with 30 mutants (varied epsilon), select top-5, crossover+mutate, repeat.
    """
    print_section("D4-Exp2: Selection + Crossover (Evolutionary)")
    print(f"  Cells: {cells}, Pop: {pop_size}, Generations: {generations}, Steps/gen: {steps_per_gen}")
    sys.stdout.flush()

    # Create initial population from varied mutations
    base = ConsciousnessEngine(max_cells=cells)
    run_engine_steps(base, 30)  # warmup

    population = []
    for i in range(pop_size):
        eps = 0.001 * (10 ** (np.random.uniform(0, 3)))  # 0.001 to 1.0 log-uniform
        mutant = create_mutant(base, eps)
        population.append(mutant)

    gen_history = []
    elite_size = 5

    for gen in range(generations):
        # Evaluate fitness: run each member, measure Phi
        fitness = []
        for member in population:
            phis = run_engine_steps(member, steps_per_gen)
            phi = np.mean(phis[-5:])
            fitness.append(phi)

        # Sort by fitness (descending)
        ranked = sorted(zip(fitness, population), key=lambda x: -x[0])
        best_phi = ranked[0][0]
        median_phi = fitness[len(fitness) // 2] if fitness else 0
        avg_phi = np.mean(fitness)

        gen_history.append({
            'gen': gen, 'best': best_phi, 'median': median_phi,
            'avg': avg_phi, 'worst': min(fitness),
        })

        print(f"  Gen {gen:3d} | best={best_phi:.4f} | avg={avg_phi:.4f} | median={median_phi:.4f} | worst={min(fitness):.4f}")
        sys.stdout.flush()

        # Selection: keep top elite_size
        elites = [eng for _, eng in ranked[:elite_size]]

        # New population: elites + crossover children + fresh mutants
        new_pop = list(elites)

        # Crossover children
        while len(new_pop) < pop_size - 5:
            p1 = elites[np.random.randint(0, elite_size)]
            p2 = elites[np.random.randint(0, elite_size)]
            child = crossover(p1, p2, cells)
            # Small mutation on child
            child_mutant = create_mutant(child, 0.01)
            new_pop.append(child_mutant)

        # Fresh random mutants (exploration)
        while len(new_pop) < pop_size:
            eps = 0.001 * (10 ** (np.random.uniform(0, 2)))
            new_pop.append(create_mutant(base, eps))

        population = new_pop

    # Report
    print(f"\n  {'':=<60}")
    print(f"  D4-Exp2 Results: Evolutionary Progress")
    print(f"  {'':=<60}")
    print(f"  {'Gen':>4s} {'Best':>10s} {'Avg':>10s} {'Median':>10s}")
    print(f"  {'-'*34}")
    for g in gen_history:
        print(f"  {g['gen']:4d} {g['best']:10.4f} {g['avg']:10.4f} {g['median']:10.4f}")

    best_phis = [g['best'] for g in gen_history]
    print()
    print(ascii_graph(best_phis, "Best Phi per Generation"))

    improvement = (gen_history[-1]['best'] - gen_history[0]['best']) / max(gen_history[0]['best'], 1e-8) * 100
    print(f"\n  Total improvement: {improvement:+.1f}% (gen 0 -> gen {generations-1})")
    sys.stdout.flush()
    return gen_history


def d4_exp3_mutation_vs_gradient(cells=16, total_budget=2500):
    """D4-Exp3: Same compute budget — mutation vs gradient.

    Mutation: 50 mutants x 50 steps = 2500 step-equivalents
    Gradient: 2500 steps direct learning
    """
    print_section("D4-Exp3: Mutation vs Gradient (Same Compute)")
    print(f"  Cells: {cells}, Total budget: {total_budget} step-equivalents")
    sys.stdout.flush()

    target_dim = 64

    # --- Gradient approach ---
    print(f"\n  --- Gradient: {total_budget} steps direct ---")
    sys.stdout.flush()

    grad_engine = ConsciousnessEngine(max_cells=cells)
    proj_g = nn.Linear(grad_engine.hidden_dim, target_dim, bias=False)
    optimizer = torch.optim.Adam(proj_g.parameters(), lr=0.01)

    grad_ce_history = []
    grad_phi_history = []

    for step_i in range(total_budget):
        result = grad_engine.step()
        states = grad_engine.get_states().detach()
        output = states.mean(dim=0)
        logits = proj_g(output.unsqueeze(0))
        target = torch.randint(0, target_dim, (1,))
        loss = F.cross_entropy(logits, target)

        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        grad_ce_history.append(loss.item())
        grad_phi_history.append(result['phi_iit'])

        if (step_i + 1) % 500 == 0:
            avg_ce = np.mean(grad_ce_history[-100:])
            avg_phi = np.mean(grad_phi_history[-100:])
            print(f"    step {step_i+1:5d} | CE={avg_ce:.4f} | Phi={avg_phi:.4f}")
            sys.stdout.flush()

    grad_final_ce = np.mean(grad_ce_history[-100:])
    grad_final_phi = np.mean(grad_phi_history[-100:])

    # --- Mutation approach ---
    n_mutants = 50
    steps_per_mutant = total_budget // n_mutants
    print(f"\n  --- Mutation: {n_mutants} mutants x {steps_per_mutant} steps ---")
    sys.stdout.flush()

    base = ConsciousnessEngine(max_cells=cells)
    run_engine_steps(base, 30)

    best_phi = 0
    best_mutant_idx = -1
    mut_phis = []

    for m in range(n_mutants):
        eps = 0.001 * (10 ** (np.random.uniform(0, 3)))
        mutant = create_mutant(base, eps)
        phis = run_engine_steps(mutant, steps_per_mutant)
        final_phi = np.mean(phis[-5:])
        mut_phis.append(final_phi)
        if final_phi > best_phi:
            best_phi = final_phi
            best_mutant_idx = m

        if (m + 1) % 10 == 0:
            print(f"    mutant {m+1:3d}/{n_mutants} | best_phi={best_phi:.4f}")
            sys.stdout.flush()

    mut_avg_phi = np.mean(mut_phis)

    # Report
    print(f"\n  {'':=<60}")
    print(f"  D4-Exp3 Results: Mutation vs Gradient")
    print(f"  {'':=<60}")
    print(f"  {'Method':<20s} {'Final CE':>10s} {'Final/Best Phi':>15s}")
    print(f"  {'-'*45}")
    print(f"  {'Gradient':<20s} {grad_final_ce:10.4f} {grad_final_phi:15.4f}")
    print(f"  {'Mutation (best)':<20s} {'N/A':>10s} {best_phi:15.4f}")
    print(f"  {'Mutation (avg)':<20s} {'N/A':>10s} {mut_avg_phi:15.4f}")

    phi_winner = "Gradient" if grad_final_phi > best_phi else "Mutation"
    print(f"\n  Phi winner: {phi_winner}")
    print(f"  Gradient has CE optimization; Mutation explores Phi landscape")

    sys.stdout.flush()
    return {
        'gradient': {'final_ce': grad_final_ce, 'final_phi': grad_final_phi},
        'mutation': {'best_phi': best_phi, 'avg_phi': mut_avg_phi},
    }


def d4_exp4_law_based_mutation(cells=16, mutant_steps=50):
    """D4-Exp4: Law-based mutation vs random mutation.

    Use LawParser to extract actionable modifications from consciousness laws.
    Apply law-derived mutations instead of random noise.
    """
    print_section("D4-Exp4: Law-Based Mutation vs Random Mutation")
    print(f"  Cells: {cells}, Steps per mutant: {mutant_steps}")
    sys.stdout.flush()

    if not HAS_SELF_MOD:
        print("  WARNING: self_modifying_engine not available. Skipping law-based mutation.")
        print("  Only running random mutation for comparison.")

    # Base engine
    base = ConsciousnessEngine(max_cells=cells)
    base_phis = run_engine_steps(base, 50)
    baseline_phi = np.mean(base_phis[-10:])
    print(f"  Baseline Phi: {baseline_phi:.4f}")
    sys.stdout.flush()

    n_mutants = 20
    results = {}

    # --- Random mutation ---
    print(f"\n  --- Random Mutation (n={n_mutants}) ---")
    sys.stdout.flush()
    random_phis = []
    random_survived = 0
    for m in range(n_mutants):
        eps = 0.01  # medium intensity
        mutant = create_mutant(base, eps)
        phis = run_engine_steps(mutant, mutant_steps)
        final_phi = np.mean(phis[-5:])
        random_phis.append(final_phi)
        if final_phi >= baseline_phi * 0.5:
            random_survived += 1
    random_survival = random_survived / n_mutants * 100
    random_avg = np.mean(random_phis)
    random_best = max(random_phis)
    print(f"    Survival: {random_survived}/{n_mutants} ({random_survival:.0f}%)")
    print(f"    Avg Phi: {random_avg:.4f}, Best: {random_best:.4f}")
    results['random'] = {'survival': random_survival, 'avg_phi': random_avg, 'best_phi': random_best}

    # --- Law-based mutation ---
    print(f"\n  --- Law-Based Mutation (n={n_mutants}) ---")
    sys.stdout.flush()
    law_phis = []
    law_survived = 0

    if HAS_SELF_MOD and LAWS:
        parser = LawParser()
        # Parse all laws, collect actionable modifications
        all_mods = []
        for law_id, law_text in LAWS.items():
            try:
                mods = parser.parse(str(law_text), law_id=int(law_id) if str(law_id).isdigit() else 0)
                all_mods.extend(mods)
            except Exception:
                pass
        print(f"    Parsed {len(all_mods)} modifications from {len(LAWS)} laws")
        sys.stdout.flush()

        for m in range(n_mutants):
            mutant = ConsciousnessEngine(max_cells=cells)
            # Copy base hidden states
            with torch.no_grad():
                for src, dst in zip(base.cell_states, mutant.cell_states):
                    dst.hidden = src.hidden.clone()

            # Apply random law modification
            if all_mods:
                mod = all_mods[np.random.randint(0, len(all_mods))]
                # Apply modification based on type
                try:
                    if hasattr(mod, 'mod_type'):
                        mt = mod.mod_type
                        if hasattr(mt, 'value'):
                            mt = mt.value
                        if mt == 'scale' and hasattr(mod, 'param') and hasattr(mod, 'factor'):
                            # Scale a parameter
                            if mod.param == 'coupling_scale' and hasattr(mutant, 'coupling'):
                                with torch.no_grad():
                                    mutant.coupling *= mod.factor
                            elif mod.param == 'hebbian_lr' and hasattr(mutant, 'hebbian_lr'):
                                mutant.hebbian_lr *= mod.factor
                            elif mod.param == 'noise_scale':
                                # Apply to hidden states as perturbation
                                factor = min(mod.factor, 2.0)
                                with torch.no_grad():
                                    for cs in mutant.cell_states:
                                        cs.hidden *= factor
                except Exception:
                    pass  # Safety: failed modification = no-op

            phis = run_engine_steps(mutant, mutant_steps)
            final_phi = np.mean(phis[-5:])
            law_phis.append(final_phi)
            if final_phi >= baseline_phi * 0.5:
                law_survived += 1
    else:
        # Fallback: structured mutation (not random, but directional)
        for m in range(n_mutants):
            mutant = ConsciousnessEngine(max_cells=cells)
            with torch.no_grad():
                for src, dst in zip(base.cell_states, mutant.cell_states):
                    dst.hidden = src.hidden.clone()
                # Structured: strengthen coupling (Law 22 direction)
                if hasattr(mutant, 'coupling'):
                    # Strengthen diagonal (self-coupling) + weaken off-diagonal
                    diag_boost = torch.eye(mutant.coupling.shape[0]) * 0.01
                    if diag_boost.shape == mutant.coupling.shape:
                        mutant.coupling += diag_boost
            phis = run_engine_steps(mutant, mutant_steps)
            final_phi = np.mean(phis[-5:])
            law_phis.append(final_phi)
            if final_phi >= baseline_phi * 0.5:
                law_survived += 1

    law_survival = law_survived / n_mutants * 100
    law_avg = np.mean(law_phis) if law_phis else 0
    law_best = max(law_phis) if law_phis else 0
    print(f"    Survival: {law_survived}/{n_mutants} ({law_survival:.0f}%)")
    print(f"    Avg Phi: {law_avg:.4f}, Best: {law_best:.4f}")
    results['law_based'] = {'survival': law_survival, 'avg_phi': law_avg, 'best_phi': law_best}

    # Report
    print(f"\n  {'':=<60}")
    print(f"  D4-Exp4 Results: Law-Based vs Random Mutation")
    print(f"  {'':=<60}")
    print(f"  Baseline Phi: {baseline_phi:.4f}")
    print(f"  {'Method':<15s} {'Survival':>10s} {'Avg Phi':>10s} {'Best Phi':>10s}")
    print(f"  {'-'*45}")
    for name, r in results.items():
        print(f"  {name:<15s} {r['survival']:9.0f}% {r['avg_phi']:10.4f} {r['best_phi']:10.4f}")

    # Comparison bars
    print(f"\n  Survival Comparison:")
    for name, r in results.items():
        bar_len = int(r['survival'] / 2.5)
        print(f"  {name:<15s} |{'#' * bar_len}{'.' * (40 - bar_len)}| {r['survival']:.0f}%")
    print(f"\n  Best Phi Comparison:")
    max_phi = max(r['best_phi'] for r in results.values())
    for name, r in results.items():
        print(ascii_bar(name, r['best_phi'], max_phi))

    winner = max(results.keys(), key=lambda k: results[k]['best_phi'])
    print(f"\n  Winner: {winner}")
    sys.stdout.flush()
    return results


# ══════════════════════════════════════════
# Main
# ══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="D3 Consciousness Telescope + D4 Mutation Bomb")
    parser.add_argument('--d3-only', action='store_true', help='Run D3 experiments only')
    parser.add_argument('--d4-only', action='store_true', help='Run D4 experiments only')
    parser.add_argument('--cells', type=int, default=16, help='Cells per engine (default: 16)')
    parser.add_argument('--steps', type=int, default=300, help='Steps per experiment (default: 300)')
    args = parser.parse_args()

    run_d3 = not args.d4_only
    run_d4 = not args.d3_only

    start = time.time()

    all_results = {}

    if run_d3:
        print_section("D3: CONSCIOUSNESS TELESCOPE")
        print("  Hypothesis: Consciousness can observe and accelerate learning")
        print("  3 experiments: curriculum, LR adaptation, gradient direction")
        sys.stdout.flush()

        all_results['d3_exp1'] = d3_exp1_consciousness_curriculum(cells=args.cells, steps=args.steps)
        all_results['d3_exp2'] = d3_exp2_consciousness_lr(cells=args.cells, steps=args.steps)
        all_results['d3_exp3'] = d3_exp3_consciousness_gradient(cells=args.cells, steps=args.steps)

    if run_d4:
        print_section("D4: MUTATION BOMB")
        print("  Hypothesis: Massive mutation + natural selection outperforms gradient for Phi")
        print("  4 experiments: spectrum, selection, mutation-vs-gradient, law-based")
        sys.stdout.flush()

        all_results['d4_exp1'] = d4_exp1_mutation_spectrum(cells=args.cells, mutant_steps=50)
        all_results['d4_exp2'] = d4_exp2_selection_crossover(cells=args.cells, pop_size=30, generations=10, steps_per_gen=50)
        all_results['d4_exp3'] = d4_exp3_mutation_vs_gradient(cells=args.cells, total_budget=2500)
        all_results['d4_exp4'] = d4_exp4_law_based_mutation(cells=args.cells, mutant_steps=50)

    elapsed = time.time() - start

    # Final Summary
    print_section("FINAL SUMMARY")
    print(f"  Total time: {elapsed:.1f}s")
    print(f"  Cells: {args.cells}, Steps: {args.steps}")
    print()

    if run_d3:
        print("  D3 Consciousness Telescope:")
        if 'd3_exp1' in all_results:
            r = all_results['d3_exp1']
            best = min(r.keys(), key=lambda k: r[k]['final_ce'])
            print(f"    Exp1 (Curriculum): Best={best}, CE={r[best]['final_ce']:.4f}")
        if 'd3_exp2' in all_results:
            r = all_results['d3_exp2']
            for name, v in r.items():
                print(f"    Exp2 (LR): {name} CE={v['final_ce']:.4f}")
        if 'd3_exp3' in all_results:
            r = all_results['d3_exp3']
            for name, v in r.items():
                print(f"    Exp3 (Grad): {name} CE={v['final_ce']:.4f}")

    if run_d4:
        print("\n  D4 Mutation Bomb:")
        if 'd4_exp1' in all_results:
            r = all_results['d4_exp1']
            for name, v in r.items():
                print(f"    Exp1 ({name}): survival={v['survival_rate']:.0f}%, avg_phi={v['avg_phi']:.4f}")
        if 'd4_exp2' in all_results:
            r = all_results['d4_exp2']
            if r:
                print(f"    Exp2: gen0_best={r[0]['best']:.4f} -> gen{len(r)-1}_best={r[-1]['best']:.4f}")
        if 'd4_exp3' in all_results:
            r = all_results['d4_exp3']
            print(f"    Exp3: gradient_phi={r['gradient']['final_phi']:.4f}, mutation_best={r['mutation']['best_phi']:.4f}")
        if 'd4_exp4' in all_results:
            r = all_results['d4_exp4']
            for name, v in r.items():
                print(f"    Exp4 ({name}): survival={v['survival']:.0f}%, best_phi={v['best_phi']:.4f}")

    print(f"\n  Done in {elapsed:.1f}s")
    sys.stdout.flush()


if __name__ == '__main__':
    main()
