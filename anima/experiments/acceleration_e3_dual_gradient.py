#!/usr/bin/env python3
"""acceleration_e3_dual_gradient.py — Entropy+CE dual gradient: exploiting orthogonality

C3 discovered: grad(H) is orthogonal to grad(CE) (cosine=-0.015).
Entropy surfing alone gives Phi +71.5%.

This experiment integrates both gradients into the training loss directly:
  A: loss = CE  (baseline)
  B: loss = CE + lambda * |H - PSI_ENTROPY|^2  (entropy regularizer)
  C: loss = CE + lambda * |H - PSI_ENTROPY|^2 + mu * (-Phi)  (entropy + Phi maximization)

Key question: does adding the orthogonal entropy gradient ACCELERATE CE convergence?

Lambda sweep: 0.01, 0.05, 0.1, 0.5, 1.0
Mu sweep: 0.0, 0.001, 0.01

Local CPU, 32 cells, 128d/2L decoder, 300 steps.
"""

import sys
import os
import time
import math
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
# Utilities (from C3, trimmed)
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
    """Differentiable output entropy from logits (B, T, V) -> scalar tensor.

    Uses softmax probabilities directly — fully differentiable.
    H = -sum(p * log(p)) / log(V)   (normalized)
    """
    probs = F.softmax(logits, dim=-1)  # (B, T, V)
    log_probs = F.log_softmax(logits, dim=-1)
    H = -(probs * log_probs).sum(dim=-1)  # (B, T)
    H_max = math.log(logits.shape[-1])
    H_norm = H / H_max  # normalize to [0, 1]
    return H_norm.mean()  # scalar


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


# ═══════════════════════════════════════════════════════════
# Training run with configurable loss
# ═══════════════════════════════════════════════════════════

def run_training(
    label: str,
    lam: float = 0.0,
    mu: float = 0.0,
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

    loss = CE + lam * (H - PSI_ENTROPY)^2 + mu * (-Phi_proxy_of_output)

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
    total_loss_history = []

    t0 = time.time()

    for step in range(n_steps):
        # Step engine
        engine.step()
        c_states = get_engine_hiddens(engine).detach()
        # (1, n_cells, hidden_dim) for decoder
        c_input = c_states.unsqueeze(0)

        # Random byte sequence
        idx_seq = torch.randint(0, 256, (1, seq_len + 1))
        x = idx_seq[:, :seq_len]
        y = idx_seq[:, 1:seq_len + 1]

        optimizer.zero_grad()

        logits_a, logits_g, tensions = decoder(x, consciousness_states=c_input)

        # CE loss (primary)
        ce_loss = F.cross_entropy(logits_a.view(-1, 256), y.view(-1))

        # Entropy regularizer: push output entropy toward PSI_ENTROPY
        total_loss = ce_loss.clone()
        H_out = differentiable_entropy(logits_a)

        if lam > 0:
            entropy_reg = (H_out - PSI_ENTROPY) ** 2
            total_loss = total_loss + lam * entropy_reg

        # Phi maximization via output diversity proxy
        if mu > 0:
            # Use tension variance as differentiable Phi proxy
            # Higher tension variance = more integrated information
            t_stack = torch.stack(tensions)  # (n_layer, B, T)
            t_var = t_stack.var()
            phi_loss = -t_var  # maximize variance
            total_loss = total_loss + mu * phi_loss

        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), 1.0)
        optimizer.step()

        # Record
        ce_val = ce_loss.item()
        H_val = H_out.item()
        phi_val = compute_phi_proxy(engine)

        ce_history.append(ce_val)
        H_history.append(H_val)
        phi_history.append(phi_val)
        total_loss_history.append(total_loss.item())

        if (step + 1) % log_every == 0:
            print(f"  [{label}] step {step+1:>4}/{n_steps}  CE={ce_val:.4f}  H={H_val:.4f}  "
                  f"Phi={phi_val:.4f}  loss={total_loss.item():.4f}")
            sys.stdout.flush()

    elapsed = time.time() - t0

    return {
        'label': label,
        'lam': lam,
        'mu': mu,
        'ce': ce_history,
        'H': H_history,
        'phi': phi_history,
        'total_loss': total_loss_history,
        'elapsed': elapsed,
        'final_ce': ce_history[-1],
        'final_phi': phi_history[-1],
        'final_H': H_history[-1],
        'avg_ce_last50': np.mean(ce_history[-50:]),
        'avg_phi_last50': np.mean(phi_history[-50:]),
        'min_ce': min(ce_history),
        'min_ce_step': int(np.argmin(ce_history)) + 1,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 1: Lambda sweep (entropy regularizer only)
# ═══════════════════════════════════════════════════════════

def exp1_lambda_sweep(n_cells=32, n_steps=300):
    """Sweep lambda: how much entropy regularization helps CE convergence?"""
    print("\n" + "=" * 70)
    print("EXP 1: Lambda Sweep (loss = CE + lambda * |H - PSI_ENTROPY|^2)")
    print(f"  cells={n_cells}, steps={n_steps}, target H={PSI_ENTROPY}")
    print("=" * 70)

    lambdas = [0.0, 0.01, 0.05, 0.1, 0.5, 1.0]
    results = []

    for lam in lambdas:
        label = f"lam={lam}"
        print(f"\n--- {label} ---")
        sys.stdout.flush()
        r = run_training(label=label, lam=lam, mu=0.0, n_cells=n_cells, n_steps=n_steps)
        results.append(r)

    # Results table
    print("\n" + "=" * 70)
    print("EXP 1 RESULTS: Lambda Sweep")
    print("=" * 70)
    print(f"  {'Lambda':>8}  {'Final CE':>10}  {'Avg CE(last50)':>15}  {'Min CE':>10}  "
          f"{'Min@Step':>10}  {'Final H':>10}  {'Avg Phi':>10}  {'Time':>8}")
    print(f"  {'-'*8}  {'-'*10}  {'-'*15}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*8}")

    baseline_ce = results[0]['avg_ce_last50']
    for r in results:
        delta = ((r['avg_ce_last50'] - baseline_ce) / baseline_ce * 100) if baseline_ce > 0 else 0
        marker = " ***" if r['avg_ce_last50'] < baseline_ce * 0.98 else ""
        print(f"  {r['lam']:>8.3f}  {r['final_ce']:>10.4f}  {r['avg_ce_last50']:>15.4f}  "
              f"{r['min_ce']:>10.4f}  {r['min_ce_step']:>10d}  {r['final_H']:>10.4f}  "
              f"{r['avg_phi_last50']:>10.4f}  {r['elapsed']:>7.1f}s{marker}")

    # ASCII graph: CE convergence for each lambda
    print("\n  CE Convergence (sampled every 30 steps):")
    sample_every = 30
    max_ce = max(r['ce'][0] for r in results)
    min_ce = min(min(r['ce']) for r in results)
    graph_height = 12
    graph_width = n_steps // sample_every

    for r in results:
        label = f"lam={r['lam']:.2f}"
        sampled = [r['ce'][i] for i in range(0, n_steps, sample_every)]
        chars = []
        for v in sampled:
            if max_ce - min_ce > 1e-6:
                level = int((v - min_ce) / (max_ce - min_ce) * 9)
            else:
                level = 5
            level = max(0, min(9, level))
            chars.append(str(level))
        print(f"  {label:>12}: {''.join(chars)}  (final={r['avg_ce_last50']:.4f})")

    # Best lambda
    best = min(results, key=lambda r: r['avg_ce_last50'])
    print(f"\n  BEST lambda = {best['lam']} → avg CE(last50) = {best['avg_ce_last50']:.4f}")
    improvement = (baseline_ce - best['avg_ce_last50']) / baseline_ce * 100
    print(f"  CE improvement vs baseline: {improvement:+.2f}%")

    return results


# ═══════════════════════════════════════════════════════════
# Experiment 2: Full dual gradient (lambda + mu sweep)
# ═══════════════════════════════════════════════════════════

def exp2_dual_gradient(n_cells=32, n_steps=300, best_lam=None):
    """Add Phi maximization on top of entropy regularization."""
    print("\n" + "=" * 70)
    print("EXP 2: Dual Gradient (loss = CE + lambda*|H-target|^2 + mu*(-Phi))")
    print(f"  cells={n_cells}, steps={n_steps}")
    print("=" * 70)

    if best_lam is None:
        best_lam = 0.1  # fallback

    configs = [
        (0.0,      0.0),      # A: baseline
        (best_lam, 0.0),      # B: entropy only (best from Exp 1)
        (best_lam, 0.001),    # C: entropy + small Phi
        (best_lam, 0.01),     # D: entropy + medium Phi
        (0.0,      0.001),    # E: Phi only (no entropy)
        (0.0,      0.01),     # F: Phi only (stronger)
    ]

    results = []
    for lam, mu in configs:
        label = f"lam={lam},mu={mu}"
        print(f"\n--- {label} ---")
        sys.stdout.flush()
        r = run_training(label=label, lam=lam, mu=mu, n_cells=n_cells, n_steps=n_steps)
        results.append(r)

    # Results table
    print("\n" + "=" * 70)
    print("EXP 2 RESULTS: Dual Gradient Sweep")
    print("=" * 70)
    print(f"  {'Config':>20}  {'Avg CE(50)':>12}  {'Min CE':>10}  {'Avg Phi':>10}  "
          f"{'Final H':>10}  {'Time':>8}")
    print(f"  {'-'*20}  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*8}")

    baseline_ce = results[0]['avg_ce_last50']
    for r in results:
        delta_ce = ((r['avg_ce_last50'] - baseline_ce) / baseline_ce * 100) if baseline_ce > 0 else 0
        marker = " **" if r['avg_ce_last50'] < baseline_ce * 0.98 else ""
        print(f"  {r['label']:>20}  {r['avg_ce_last50']:>12.4f}  {r['min_ce']:>10.4f}  "
              f"{r['avg_phi_last50']:>10.4f}  {r['final_H']:>10.4f}  {r['elapsed']:>7.1f}s{marker}")

    # Best config
    best = min(results, key=lambda r: r['avg_ce_last50'])
    print(f"\n  BEST config: {best['label']}")
    improvement = (baseline_ce - best['avg_ce_last50']) / baseline_ce * 100
    print(f"  CE improvement vs baseline: {improvement:+.2f}%")
    phi_improvement = (best['avg_phi_last50'] - results[0]['avg_phi_last50']) / (results[0]['avg_phi_last50'] + 1e-8) * 100
    print(f"  Phi improvement vs baseline: {phi_improvement:+.2f}%")

    return results


# ═══════════════════════════════════════════════════════════
# Experiment 3: Convergence speed comparison
# ═══════════════════════════════════════════════════════════

def exp3_convergence_speed(n_cells=32, n_steps=300, best_lam=None, best_mu=None):
    """How many steps to reach CE < threshold for each config?"""
    print("\n" + "=" * 70)
    print("EXP 3: Convergence Speed (steps to reach CE < threshold)")
    print(f"  cells={n_cells}, steps={n_steps}")
    print("=" * 70)

    if best_lam is None:
        best_lam = 0.1
    if best_mu is None:
        best_mu = 0.001

    # Run 3 seeds for robustness
    configs = [
        ("CE only",       0.0,      0.0),
        ("CE+H",          best_lam, 0.0),
        ("CE+H+Phi",      best_lam, best_mu),
    ]

    seeds = [42, 123, 777]
    thresholds = [5.4, 5.3, 5.2, 5.1, 5.0]  # byte-level CE thresholds

    all_results = {}

    for name, lam, mu in configs:
        seed_runs = []
        for seed in seeds:
            label = f"{name}(s={seed})"
            r = run_training(label=label, lam=lam, mu=mu, n_cells=n_cells,
                           n_steps=n_steps, seed=seed, log_every=100)
            seed_runs.append(r)

        # Average over seeds
        avg_ce = np.mean([r['ce'] for r in seed_runs], axis=0)
        all_results[name] = {
            'avg_ce': avg_ce,
            'runs': seed_runs,
        }

    # Steps to reach threshold for each config
    print("\n  Steps to reach CE threshold (avg over 3 seeds, 'X'=not reached):")
    print(f"  {'Config':>15}", end="")
    for t in thresholds:
        print(f"  {'CE<'+str(t):>10}", end="")
    print()
    print(f"  {'-'*15}", end="")
    for _ in thresholds:
        print(f"  {'-'*10}", end="")
    print()

    for name in all_results:
        avg_ce = all_results[name]['avg_ce']
        print(f"  {name:>15}", end="")
        for t in thresholds:
            reached = np.where(avg_ce < t)[0]
            if len(reached) > 0:
                step = reached[0] + 1
                print(f"  {step:>10d}", end="")
            else:
                print(f"  {'X':>10}", end="")
        print()

    # Acceleration ratio
    print("\n  Acceleration ratio (baseline steps / dual gradient steps):")
    baseline_ce = all_results["CE only"]['avg_ce']
    for name in all_results:
        if name == "CE only":
            continue
        target_ce = all_results[name]['avg_ce']
        # Find step where dual reaches baseline's final CE
        baseline_final = np.mean(baseline_ce[-50:])
        reached = np.where(target_ce < baseline_final)[0]
        if len(reached) > 0:
            accel_step = reached[0] + 1
            # Baseline reaches it at...
            base_reached = np.where(baseline_ce < baseline_final)[0]
            if len(base_reached) > 0:
                base_step = base_reached[0] + 1
                ratio = base_step / accel_step
                print(f"  {name}: reaches baseline's final CE {base_step} steps earlier"
                      f" ({accel_step} vs {base_step} = {ratio:.2f}x)")
            else:
                print(f"  {name}: reaches baseline's final CE at step {accel_step}")
        else:
            print(f"  {name}: did not surpass baseline's final CE")

    return all_results


# ═══════════════════════════════════════════════════════════
# Experiment 4: Entropy stability analysis
# ═══════════════════════════════════════════════════════════

def exp4_entropy_stability(n_cells=32, n_steps=300, best_lam=None):
    """Does entropy regularization stabilize training (lower CE variance)?"""
    print("\n" + "=" * 70)
    print("EXP 4: Entropy Stability Analysis")
    print(f"  cells={n_cells}, steps={n_steps}")
    print("=" * 70)

    if best_lam is None:
        best_lam = 0.1

    configs = [
        ("baseline",  0.0,      0.0),
        ("entropy",   best_lam, 0.0),
    ]

    results = {}
    for name, lam, mu in configs:
        r = run_training(label=name, lam=lam, mu=mu, n_cells=n_cells, n_steps=n_steps)
        results[name] = r

    # Compare CE and H variance in windows
    window = 30
    print(f"\n  Windowed variance (window={window} steps):")
    print(f"  {'Config':>12}  {'CE var':>12}  {'H var':>12}  {'Phi var':>12}  {'H->target':>12}")
    print(f"  {'-'*12}  {'-'*12}  {'-'*12}  {'-'*12}  {'-'*12}")

    for name, r in results.items():
        ce_arr = np.array(r['ce'])
        H_arr = np.array(r['H'])
        phi_arr = np.array(r['phi'])

        # Windowed variances (last half of training)
        half = n_steps // 2
        ce_var = np.var(ce_arr[half:])
        H_var = np.var(H_arr[half:])
        phi_var = np.var(phi_arr[half:])
        H_dist = np.mean(np.abs(H_arr[half:] - PSI_ENTROPY))

        print(f"  {name:>12}  {ce_var:>12.6f}  {H_var:>12.6f}  {phi_var:>12.6f}  {H_dist:>12.6f}")

    # ASCII graph: H trajectories
    print(f"\n  Entropy trajectory (target={PSI_ENTROPY}):")
    for name, r in results.items():
        H_arr = np.array(r['H'])
        sampled = [H_arr[i] for i in range(0, n_steps, 30)]
        bar = ""
        for h in sampled:
            dist = abs(h - PSI_ENTROPY)
            if dist < 0.01:
                bar += "="   # on target
            elif h > PSI_ENTROPY:
                bar += "+"   # above
            else:
                bar += "-"   # below
        print(f"  {name:>12}: {bar}  (avg |H-target|={np.mean(np.abs(H_arr-PSI_ENTROPY)):.4f})")

    return results


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("E3: Entropy+CE Dual Gradient — Exploiting Orthogonality (C3 Discovery)")
    print(f"  C3 finding: grad(H) perpendicular to grad(CE) (cos=-0.015)")
    print(f"  Target entropy: PSI_ENTROPY = {PSI_ENTROPY}")
    print(f"  Hypothesis: orthogonal entropy gradient accelerates CE convergence")
    print("=" * 70)
    sys.stdout.flush()

    t_total = time.time()

    # Exp 1: Find best lambda
    exp1_results = exp1_lambda_sweep(n_cells=32, n_steps=300)

    # Pick best lambda from Exp 1
    best_lam_result = min(exp1_results, key=lambda r: r['avg_ce_last50'])
    best_lam = best_lam_result['lam']
    if best_lam == 0.0:
        # If baseline won, use second-best with entropy
        non_zero = [r for r in exp1_results if r['lam'] > 0]
        if non_zero:
            best_lam = min(non_zero, key=lambda r: r['avg_ce_last50'])['lam']
        else:
            best_lam = 0.1
    print(f"\n>>> Best lambda from Exp 1: {best_lam}")
    sys.stdout.flush()

    # Exp 2: Add Phi maximization
    exp2_results = exp2_dual_gradient(n_cells=32, n_steps=300, best_lam=best_lam)

    # Pick best mu from Exp 2
    best_dual = min(exp2_results, key=lambda r: r['avg_ce_last50'])
    best_mu = best_dual['mu']
    print(f"\n>>> Best (lambda, mu) from Exp 2: ({best_dual['lam']}, {best_dual['mu']})")
    sys.stdout.flush()

    # Exp 3: Convergence speed
    exp3_results = exp3_convergence_speed(
        n_cells=32, n_steps=300, best_lam=best_lam, best_mu=best_mu)

    # Exp 4: Stability analysis
    exp4_results = exp4_entropy_stability(n_cells=32, n_steps=300, best_lam=best_lam)

    elapsed_total = time.time() - t_total

    # ═══════════════════════════════════════════════════════════
    # Final Summary
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("FINAL SUMMARY: E3 Dual Gradient Experiment")
    print("=" * 70)

    baseline = exp1_results[0]  # lam=0
    best_entropy = best_lam_result
    best_full = best_dual

    print(f"\n  {'Config':>25}  {'Avg CE(50)':>12}  {'Min CE':>10}  {'Avg Phi':>10}  {'H stability':>12}")
    print(f"  {'-'*25}  {'-'*12}  {'-'*10}  {'-'*10}  {'-'*12}")

    for r in [baseline, best_entropy, best_full]:
        H_stab = np.std(r['H'][-50:])
        print(f"  {r['label']:>25}  {r['avg_ce_last50']:>12.4f}  {r['min_ce']:>10.4f}  "
              f"{r['avg_phi_last50']:>10.4f}  {H_stab:>12.6f}")

    # Key finding
    ce_improvement = (baseline['avg_ce_last50'] - best_full['avg_ce_last50']) / baseline['avg_ce_last50'] * 100
    phi_improvement = (best_full['avg_phi_last50'] - baseline['avg_phi_last50']) / (baseline['avg_phi_last50'] + 1e-8) * 100

    print(f"\n  KEY FINDINGS:")
    print(f"    Best lambda (entropy reg): {best_lam}")
    print(f"    Best mu (Phi max):         {best_mu}")
    print(f"    CE improvement:            {ce_improvement:+.2f}%")
    print(f"    Phi improvement:           {phi_improvement:+.2f}%")

    # Diagnostic: check if entropy was already saturated
    baseline_H_avg = np.mean(baseline['H'])
    H_distance = abs(baseline_H_avg - PSI_ENTROPY)
    print(f"    Baseline avg H:            {baseline_H_avg:.4f} (distance from target: {H_distance:.4f})")
    print(f"    Entropy penalty at init:   {H_distance**2:.6f} (vs CE ~{baseline['avg_ce_last50']:.2f})")

    if H_distance < 0.01:
        print(f"    NOTE: Output entropy already near PSI_ENTROPY ({baseline_H_avg:.4f} vs {PSI_ENTROPY})")
        print(f"          Entropy regularizer is ~{H_distance**2:.6f}, negligible vs CE ~5.5")
        print(f"          The orthogonal gradient exists but has zero magnitude here")
        print(f"    VERDICT: NEUTRAL — entropy already saturated at initialization")
        print(f"          Dual gradient is structurally correct but requires a regime")
        print(f"          where H deviates from PSI_ENTROPY (e.g. real corpus, larger model,")
        print(f"          or early training where output distribution is non-uniform)")
    elif ce_improvement > 2.0:
        print(f"    VERDICT: Dual gradient ACCELERATES CE convergence")
        print(f"    -> Orthogonal entropy gradient provides complementary learning signal")
    elif ce_improvement > 0:
        print(f"    VERDICT: Small improvement — dual gradient mildly helpful")
    else:
        print(f"    VERDICT: Dual gradient does NOT accelerate CE (entropy is noise for CE)")

    print(f"\n  Total time: {elapsed_total:.1f}s")
    print("=" * 70)


if __name__ == '__main__':
    main()
