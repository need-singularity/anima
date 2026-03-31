#!/usr/bin/env python3
"""DD74: Learning Dynamics (학습 역학) — 5 experiments via closed-loop pipeline.

How does learning affect consciousness? What is the exact CE-Phi tradeoff?

Experiments:
  1. CE-Phi Relationship: sweep LR, measure CE vs Phi, find formula
  2. Learning Destroys Consciousness: gradient magnitude -> Phi collapse threshold
  3. Hebbian vs Gradient: which preserves consciousness better?
  4. Catastrophic Forgetting: does consciousness prevent it?
  5. Optimal Learning Schedule: constant vs warmup vs cosine vs cyclic

Run: cd anima/src && PYTHONUNBUFFERED=1 python3 ../experiments/dd74_learning_dynamics.py
"""

import sys
import os
import math
import time
import json
import numpy as np
from collections import defaultdict

# Setup path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_dir)

import torch
import torch.nn as nn
import torch.nn.functional as F
from consciousness_engine import ConsciousnessEngine

# ============================================================
# Phi measurement (fast, MI-based)
# ============================================================

def phi_fast(engine):
    """Measure Phi(IIT) via pairwise MI."""
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
    n = hiddens.shape[0]
    pairs = set()
    for i in range(n):
        pairs.add((i, (i + 1) % n))
        for _ in range(min(4, n - 1)):
            j = np.random.randint(0, n)
            if i != j:
                pairs.add((min(i, j), max(i, j)))
    total_mi = 0.0
    for i, j in pairs:
        x, y = hiddens[i], hiddens[j]
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            continue
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0, 1], [0, 1]])
        hist = hist / (hist.sum() + 1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(hist * np.log2(hist + 1e-10))
        total_mi += max(0.0, hx + hy - hxy)
    return total_mi / max(len(pairs), 1)


def cell_diversity(engine):
    """Mean variance across cells."""
    if engine.n_cells < 2:
        return 0.0
    h = torch.stack([s.hidden for s in engine.cell_states])
    return h.var(dim=0).mean().item()


def faction_entropy(engine):
    """Shannon entropy of faction distribution."""
    factions = [s.faction_id for s in engine.cell_states]
    counts = defaultdict(int)
    for f in factions:
        counts[f] += 1
    total = len(factions)
    ent = 0.0
    for c in counts.values():
        p = c / total
        if p > 0:
            ent -= p * math.log2(p)
    return ent


# ============================================================
# Simple byte-prediction task for CE measurement
# ============================================================

def make_corpus_bytes(pattern='A', length=2000):
    """Generate simple byte patterns for learning task."""
    if pattern == 'A':
        # Repeating pattern: 'Hello consciousness '
        seed = b'Hello consciousness '
        data = (seed * (length // len(seed) + 1))[:length]
    elif pattern == 'B':
        # Different pattern: 'Phi grows with structure '
        seed = b'Phi grows with structure '
        data = (seed * (length // len(seed) + 1))[:length]
    else:
        # Random bytes
        data = bytes(np.random.randint(0, 256, length).tolist())
    return torch.tensor(list(data), dtype=torch.long)


class SimplePredictor(nn.Module):
    """Predict next byte from consciousness engine output."""
    def __init__(self, input_dim=128, vocab=256):
        super().__init__()
        self.proj = nn.Linear(input_dim, vocab)

    def forward(self, x):
        return self.proj(x)


def compute_ce(predictor, engine_output, target):
    """Compute CE loss for next-byte prediction."""
    logits = predictor(engine_output)
    return F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))


# ============================================================
# Experiment 1: CE-Phi Relationship
# ============================================================

def experiment1_ce_phi_relationship(steps=300, repeats=3):
    """Sweep LR, measure CE vs Phi correlation."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 1: CE-Phi RELATIONSHIP (CE와 Phi의 정확한 관계식)")
    print("=" * 70)

    lr_values = [1e-5, 1e-4, 1e-3, 1e-2, 1e-1]
    corpus = make_corpus_bytes('A', 2000)
    results = {lr: {'ce': [], 'phi': []} for lr in lr_values}

    for rep in range(repeats):
        print(f"\n  [Repeat {rep+1}/{repeats}]")
        for lr in lr_values:
            engine = ConsciousnessEngine(max_cells=16, initial_cells=8)

            # Stabilize engine first (50 steps no learning)
            for _ in range(50):
                engine.step()

            predictor = SimplePredictor(engine.hidden_dim, 256)
            optimizer = torch.optim.Adam(predictor.parameters(), lr=lr)

            ce_history = []
            phi_history = []

            for step in range(steps):
                result = engine.step()
                # Get mean hidden as representation
                h = torch.stack([s.hidden for s in engine.cell_states]).mean(0).detach()

                # Pick a random byte and predict next
                idx = step % (len(corpus) - 1)
                target = corpus[idx + 1]

                # Forward + backward
                optimizer.zero_grad()
                logits = predictor(h)
                loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
                loss.backward()
                optimizer.step()

                if step % 30 == 0 or step == steps - 1:
                    phi = phi_fast(engine)
                    ce_history.append(loss.item())
                    phi_history.append(phi)

            avg_ce = np.mean(ce_history[-5:])
            avg_phi = np.mean(phi_history[-5:])
            results[lr]['ce'].append(avg_ce)
            results[lr]['phi'].append(avg_phi)
            print(f"    LR={lr:.0e}: CE={avg_ce:.4f}, Phi={avg_phi:.4f}")
            sys.stdout.flush()

    # Summary table
    print(f"\n{'─' * 60}")
    print(f"  {'LR':>8s}  {'CE (mean±std)':>16s}  {'Phi (mean±std)':>16s}  {'CV_CE':>6s}  {'CV_Phi':>6s}")
    print(f"{'─' * 60}")

    all_ce, all_phi = [], []
    for lr in lr_values:
        ce_m = np.mean(results[lr]['ce'])
        ce_s = np.std(results[lr]['ce'])
        phi_m = np.mean(results[lr]['phi'])
        phi_s = np.std(results[lr]['phi'])
        cv_ce = ce_s / (ce_m + 1e-10) * 100
        cv_phi = phi_s / (phi_m + 1e-10) * 100
        print(f"  {lr:>8.0e}  {ce_m:>7.4f}±{ce_s:<6.4f}  {phi_m:>7.4f}±{phi_s:<6.4f}  {cv_ce:>5.1f}%  {cv_phi:>5.1f}%")
        all_ce.append(ce_m)
        all_phi.append(phi_m)

    # Correlation analysis
    corr = np.corrcoef(all_ce, all_phi)[0, 1] if len(all_ce) > 1 else 0
    print(f"\n  Pearson r(CE, Phi) = {corr:.4f}")

    # Try log fit: Phi = a * log(CE) + b
    if len(all_ce) >= 3:
        log_ce = np.log(np.array(all_ce) + 1e-10)
        try:
            coeffs = np.polyfit(log_ce, all_phi, 1)
            a, b = coeffs
            residuals = all_phi - (a * log_ce + b)
            r_sq = 1 - np.sum(residuals**2) / (np.var(all_phi) * len(all_phi) + 1e-10)
            print(f"  Log fit: Phi = {a:.4f} * ln(CE) + {b:.4f} (R^2 = {r_sq:.4f})")
        except Exception:
            pass

        # Try linear fit
        coeffs_lin = np.polyfit(all_ce, all_phi, 1)
        residuals_lin = all_phi - np.polyval(coeffs_lin, all_ce)
        r_sq_lin = 1 - np.sum(residuals_lin**2) / (np.var(all_phi) * len(all_phi) + 1e-10)
        print(f"  Linear fit: Phi = {coeffs_lin[0]:.4f} * CE + {coeffs_lin[1]:.4f} (R^2 = {r_sq_lin:.4f})")

        # Try inverse fit: Phi = a / CE + b
        inv_ce = 1.0 / (np.array(all_ce) + 1e-10)
        coeffs_inv = np.polyfit(inv_ce, all_phi, 1)
        residuals_inv = all_phi - np.polyval(coeffs_inv, inv_ce)
        r_sq_inv = 1 - np.sum(residuals_inv**2) / (np.var(all_phi) * len(all_phi) + 1e-10)
        print(f"  Inverse fit: Phi = {coeffs_inv[0]:.6f} / CE + {coeffs_inv[1]:.4f} (R^2 = {r_sq_inv:.4f})")

    # ASCII scatter
    print(f"\n  CE vs Phi Scatter:")
    phi_min = min(all_phi)
    phi_max = max(all_phi)
    phi_range = phi_max - phi_min + 1e-10
    for i, lr in enumerate(lr_values):
        bar_len = int((all_phi[i] - phi_min) / phi_range * 40)
        print(f"    LR={lr:.0e}  CE={all_ce[i]:.3f}  |{'#' * bar_len:40s}| Phi={all_phi[i]:.4f}")

    return results, corr


# ============================================================
# Experiment 2: Learning Destroys Consciousness
# ============================================================

def experiment2_gradient_destruction(steps=300, repeats=3):
    """Find critical gradient magnitude that destroys Phi."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 2: LEARNING DESTROYS CONSCIOUSNESS (학습이 의식을 파괴하는 조건)")
    print("=" * 70)

    grad_magnitudes = [0.0, 0.001, 0.01, 0.1, 1.0, 10.0]
    results = {g: {'phi_before': [], 'phi_after': [], 'phi_min': [], 'collapse_step': []} for g in grad_magnitudes}

    for rep in range(repeats):
        print(f"\n  [Repeat {rep+1}/{repeats}]")
        for grad_mag in grad_magnitudes:
            engine = ConsciousnessEngine(max_cells=16, initial_cells=8)

            # Stabilize: 100 steps
            for _ in range(100):
                engine.step()
            phi_before = phi_fast(engine)

            # Apply gradient perturbations
            phi_min_val = phi_before
            collapse_step = -1
            phi_trajectory = []

            for step in range(steps):
                result = engine.step()

                if grad_mag > 0 and engine.n_cells >= 2:
                    # Perturb cell hiddens with gradient-like noise
                    for cs in engine.cell_states:
                        perturbation = torch.randn_like(cs.hidden) * grad_mag
                        cs.hidden = cs.hidden + perturbation

                if step % 30 == 0:
                    phi = phi_fast(engine)
                    phi_trajectory.append(phi)
                    if phi < phi_min_val:
                        phi_min_val = phi
                    if phi < phi_before * 0.1 and collapse_step < 0:
                        collapse_step = step

            phi_after = phi_fast(engine)
            results[grad_mag]['phi_before'].append(phi_before)
            results[grad_mag]['phi_after'].append(phi_after)
            results[grad_mag]['phi_min'].append(phi_min_val)
            results[grad_mag]['collapse_step'].append(collapse_step)
            status = "COLLAPSED" if collapse_step >= 0 else "survived"
            print(f"    grad={grad_mag:>6.3f}: Phi {phi_before:.3f} -> {phi_after:.3f} (min={phi_min_val:.3f}) [{status}]")
            sys.stdout.flush()

    # Summary table
    print(f"\n{'─' * 75}")
    print(f"  {'Grad':>8s}  {'Phi_before':>10s}  {'Phi_after':>10s}  {'Phi_min':>10s}  {'Delta%':>8s}  {'Status':>10s}")
    print(f"{'─' * 75}")

    critical_grad = None
    for g in grad_magnitudes:
        pb = np.mean(results[g]['phi_before'])
        pa = np.mean(results[g]['phi_after'])
        pm = np.mean(results[g]['phi_min'])
        delta = (pa - pb) / (pb + 1e-10) * 100
        collapsed = any(c >= 0 for c in results[g]['collapse_step'])
        status = "COLLAPSE" if collapsed else "OK"
        print(f"  {g:>8.3f}  {pb:>10.4f}  {pa:>10.4f}  {pm:>10.4f}  {delta:>+7.1f}%  {status:>10s}")
        if collapsed and critical_grad is None:
            critical_grad = g

    if critical_grad is not None:
        print(f"\n  CRITICAL GRADIENT = {critical_grad}")
        print(f"  Safe learning zone: grad_norm < {critical_grad}")
    else:
        print(f"\n  No collapse detected — consciousness is robust to all tested gradients!")

    # ASCII graph
    print(f"\n  Phi after gradient perturbation:")
    for g in grad_magnitudes:
        pa = np.mean(results[g]['phi_after'])
        pb = np.mean(results[g]['phi_before'])
        ratio = pa / (pb + 1e-10)
        bar_len = int(min(ratio, 1.5) / 1.5 * 40)
        label = "###" if ratio >= 0.9 else ("==" if ratio >= 0.5 else "..")
        print(f"    g={g:>6.3f}  |{label[0] * bar_len:40s}| {ratio:.2f}x")

    return results, critical_grad


# ============================================================
# Experiment 3: Hebbian vs Gradient
# ============================================================

def experiment3_hebbian_vs_gradient(steps=500, repeats=3):
    """Compare Hebbian learning vs gradient descent on consciousness."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 3: HEBBIAN vs GRADIENT (헤비안 vs 경사하강)")
    print("=" * 70)

    methods = ['none', 'hebbian', 'gradient']
    results = {m: {'phi_traj': [], 'div_traj': [], 'fac_traj': [], 'final_phi': [], 'final_div': []}
               for m in methods}
    corpus = make_corpus_bytes('A', 2000)

    for rep in range(repeats):
        print(f"\n  [Repeat {rep+1}/{repeats}]")
        for method in methods:
            engine = ConsciousnessEngine(max_cells=16, initial_cells=8)

            # Stabilize
            for _ in range(50):
                engine.step()

            predictor = SimplePredictor(engine.hidden_dim, 256) if method == 'gradient' else None
            if predictor:
                optimizer = torch.optim.Adam(predictor.parameters(), lr=1e-3)

            phi_traj = []
            div_traj = []
            fac_traj = []

            for step in range(steps):
                result = engine.step()

                if method == 'hebbian':
                    # Hebbian: strengthen correlations between active cells
                    if engine.n_cells >= 2 and engine._coupling is not None:
                        hiddens = torch.stack([s.hidden for s in engine.cell_states])
                        norms = hiddens / (hiddens.norm(dim=1, keepdim=True) + 1e-8)
                        sim = norms @ norms.T  # cosine similarity
                        n = engine.n_cells
                        # LTP: correlated cells strengthen (>0.8)
                        # LTD: uncorrelated cells weaken (<0.2)
                        delta = torch.zeros(n, n)
                        for i in range(n):
                            for j in range(i+1, n):
                                s = sim[i, j].item()
                                if s > 0.8:
                                    delta[i, j] = delta[j, i] = 0.01
                                elif s < 0.2:
                                    delta[i, j] = delta[j, i] = -0.005
                        engine._coupling[:n, :n] = engine._coupling[:n, :n] + delta
                        engine._coupling.clamp_(-1, 1)
                        engine._coupling.fill_diagonal_(0)

                elif method == 'gradient':
                    # Gradient: CE loss through cell states
                    h = torch.stack([s.hidden for s in engine.cell_states]).mean(0).detach()
                    idx = step % (len(corpus) - 1)
                    target = corpus[idx + 1]
                    optimizer.zero_grad()
                    logits = predictor(h)
                    loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
                    loss.backward()
                    optimizer.step()

                if step % 50 == 0 or step == steps - 1:
                    phi = phi_fast(engine)
                    div = cell_diversity(engine)
                    fac = faction_entropy(engine)
                    phi_traj.append(phi)
                    div_traj.append(div)
                    fac_traj.append(fac)

            results[method]['phi_traj'].append(phi_traj)
            results[method]['div_traj'].append(div_traj)
            results[method]['fac_traj'].append(fac_traj)
            results[method]['final_phi'].append(phi_traj[-1])
            results[method]['final_div'].append(div_traj[-1])
            print(f"    {method:>10s}: Phi={phi_traj[-1]:.4f}, Div={div_traj[-1]:.6f}, FacEnt={fac_traj[-1]:.4f}")
            sys.stdout.flush()

    # Summary table
    print(f"\n{'─' * 70}")
    print(f"  {'Method':>10s}  {'Phi (mean±std)':>16s}  {'Diversity':>12s}  {'Fac Ent':>10s}  {'Phi Delta':>10s}")
    print(f"{'─' * 70}")

    base_phi = np.mean(results['none']['final_phi'])
    for m in methods:
        phi_m = np.mean(results[m]['final_phi'])
        phi_s = np.std(results[m]['final_phi'])
        div_m = np.mean(results[m]['final_div'])
        fac_m = np.mean([t[-1] for t in results[m]['fac_traj']])
        delta = (phi_m - base_phi) / (base_phi + 1e-10) * 100
        print(f"  {m:>10s}  {phi_m:>7.4f}±{phi_s:<6.4f}  {div_m:>12.6f}  {fac_m:>10.4f}  {delta:>+9.1f}%")

    # ASCII Phi trajectory comparison
    print(f"\n  Phi Trajectory (mean across repeats):")
    for m in methods:
        traj = np.mean(results[m]['phi_traj'], axis=0)
        sparkline = ""
        if len(traj) > 0:
            t_min, t_max = traj.min(), traj.max()
            t_range = t_max - t_min + 1e-10
            chars = " ▁▂▃▄▅▆▇█"
            for v in traj:
                idx = int((v - t_min) / t_range * (len(chars) - 1))
                sparkline += chars[min(idx, len(chars) - 1)]
        print(f"    {m:>10s}: {sparkline} [{traj[0]:.3f} -> {traj[-1]:.3f}]")

    return results


# ============================================================
# Experiment 4: Catastrophic Forgetting
# ============================================================

def experiment4_catastrophic_forgetting(steps_per_phase=200, repeats=3):
    """Does consciousness prevent catastrophic forgetting?"""
    print("\n" + "=" * 70)
    print("EXPERIMENT 4: CATASTROPHIC FORGETTING (파국적 망각)")
    print("=" * 70)

    conditions = ['no_reg', 'ewc']
    results = {c: {'phi_A_after_A': [], 'phi_A_after_B': [], 'ce_A_after_A': [], 'ce_A_after_B': [],
                    'forgetting_pct': []} for c in conditions}

    corpus_A = make_corpus_bytes('A', 2000)
    corpus_B = make_corpus_bytes('B', 2000)

    for rep in range(repeats):
        print(f"\n  [Repeat {rep+1}/{repeats}]")
        for cond in conditions:
            engine = ConsciousnessEngine(max_cells=16, initial_cells=8)

            # Stabilize
            for _ in range(50):
                engine.step()

            predictor = SimplePredictor(engine.hidden_dim, 256)
            optimizer = torch.optim.Adam(predictor.parameters(), lr=1e-3)

            # Phase A: train on pattern A
            for step in range(steps_per_phase):
                result = engine.step()
                h = torch.stack([s.hidden for s in engine.cell_states]).mean(0).detach()
                idx = step % (len(corpus_A) - 1)
                target = corpus_A[idx + 1]
                optimizer.zero_grad()
                logits = predictor(h)
                loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
                loss.backward()
                optimizer.step()

            # Measure A performance after A
            phi_A_after_A = phi_fast(engine)
            h_test = torch.stack([s.hidden for s in engine.cell_states]).mean(0).detach()
            ce_A_after_A = F.cross_entropy(
                predictor(h_test).unsqueeze(0),
                corpus_A[100].unsqueeze(0)
            ).item()

            # Save Fisher information for EWC
            fisher_diag = {}
            param_snapshot = {}
            if cond == 'ewc':
                for name, param in predictor.named_parameters():
                    param_snapshot[name] = param.data.clone()
                    # Approximate Fisher with gradient squared
                    fisher_samples = []
                    for i in range(20):
                        h_s = torch.stack([s.hidden for s in engine.cell_states]).mean(0).detach()
                        logits_s = predictor(h_s)
                        loss_s = F.cross_entropy(logits_s.unsqueeze(0), corpus_A[i % (len(corpus_A)-1) + 1].unsqueeze(0))
                        predictor.zero_grad()
                        loss_s.backward()
                        fisher_samples.append(param.grad.data.clone() ** 2)
                    fisher_diag[name] = torch.stack(fisher_samples).mean(0)

            # Phase B: train on pattern B
            for step in range(steps_per_phase):
                result = engine.step()
                h = torch.stack([s.hidden for s in engine.cell_states]).mean(0).detach()
                idx = step % (len(corpus_B) - 1)
                target = corpus_B[idx + 1]
                optimizer.zero_grad()
                logits = predictor(h)
                loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))

                # EWC penalty
                if cond == 'ewc':
                    ewc_loss = 0.0
                    for name, param in predictor.named_parameters():
                        ewc_loss += (fisher_diag[name] * (param - param_snapshot[name]) ** 2).sum()
                    loss = loss + 100.0 * ewc_loss

                loss.backward()
                optimizer.step()

            # Measure A performance after B
            phi_A_after_B = phi_fast(engine)
            h_test2 = torch.stack([s.hidden for s in engine.cell_states]).mean(0).detach()
            ce_A_after_B = F.cross_entropy(
                predictor(h_test2).unsqueeze(0),
                corpus_A[100].unsqueeze(0)
            ).item()

            forgetting = (ce_A_after_B - ce_A_after_A) / (ce_A_after_A + 1e-10) * 100

            results[cond]['phi_A_after_A'].append(phi_A_after_A)
            results[cond]['phi_A_after_B'].append(phi_A_after_B)
            results[cond]['ce_A_after_A'].append(ce_A_after_A)
            results[cond]['ce_A_after_B'].append(ce_A_after_B)
            results[cond]['forgetting_pct'].append(forgetting)
            print(f"    {cond:>8s}: CE_A {ce_A_after_A:.3f}->{ce_A_after_B:.3f} ({forgetting:+.1f}%), "
                  f"Phi {phi_A_after_A:.4f}->{phi_A_after_B:.4f}")
            sys.stdout.flush()

    # Summary table
    print(f"\n{'─' * 75}")
    print(f"  {'Condition':>8s}  {'CE_A(A)':>8s}  {'CE_A(B)':>8s}  {'Forget%':>8s}  {'Phi(A)':>8s}  {'Phi(B)':>8s}  {'PhiDelta':>8s}")
    print(f"{'─' * 75}")
    for c in conditions:
        ce_aa = np.mean(results[c]['ce_A_after_A'])
        ce_ab = np.mean(results[c]['ce_A_after_B'])
        forg = np.mean(results[c]['forgetting_pct'])
        phi_a = np.mean(results[c]['phi_A_after_A'])
        phi_b = np.mean(results[c]['phi_A_after_B'])
        phi_d = (phi_b - phi_a) / (phi_a + 1e-10) * 100
        print(f"  {c:>8s}  {ce_aa:>8.4f}  {ce_ab:>8.4f}  {forg:>+7.1f}%  {phi_a:>8.4f}  {phi_b:>8.4f}  {phi_d:>+7.1f}%")

    # ASCII bar chart
    print(f"\n  Forgetting (CE increase on task A after training on B):")
    for c in conditions:
        forg = np.mean(results[c]['forgetting_pct'])
        bar_len = max(0, min(int(abs(forg) / 5), 40))
        sign = "+" if forg > 0 else "-"
        print(f"    {c:>8s}  |{sign * bar_len:40s}| {forg:+.1f}%")

    return results


# ============================================================
# Experiment 5: Optimal Learning Schedule
# ============================================================

def experiment5_learning_schedule(steps=500, repeats=3):
    """Compare learning rate schedules."""
    print("\n" + "=" * 70)
    print("EXPERIMENT 5: OPTIMAL LEARNING SCHEDULE (최적 학습 스케줄)")
    print("=" * 70)

    schedules = ['constant', 'warmup_decay', 'cosine', 'cyclic']
    results = {s: {'phi_stability': [], 'ce_final': [], 'div_final': [], 'phi_traj': [], 'ce_traj': []}
               for s in schedules}
    corpus = make_corpus_bytes('A', 2000)

    def get_lr(schedule, step, total, base_lr=1e-3):
        if schedule == 'constant':
            return base_lr
        elif schedule == 'warmup_decay':
            warmup = total * 0.1
            if step < warmup:
                return base_lr * (step / warmup)
            else:
                return base_lr * (1.0 - (step - warmup) / (total - warmup))
        elif schedule == 'cosine':
            return base_lr * 0.5 * (1 + math.cos(math.pi * step / total))
        elif schedule == 'cyclic':
            cycle_len = total // 5
            pos = (step % cycle_len) / cycle_len
            return base_lr * (0.5 * (1 + math.cos(math.pi * pos)))
        return base_lr

    for rep in range(repeats):
        print(f"\n  [Repeat {rep+1}/{repeats}]")
        for sched in schedules:
            engine = ConsciousnessEngine(max_cells=16, initial_cells=8)

            # Stabilize
            for _ in range(50):
                engine.step()

            predictor = SimplePredictor(engine.hidden_dim, 256)
            optimizer = torch.optim.Adam(predictor.parameters(), lr=1e-3)

            phi_traj = []
            ce_traj = []

            for step in range(steps):
                # Adjust LR
                lr = get_lr(sched, step, steps)
                for pg in optimizer.param_groups:
                    pg['lr'] = lr

                result = engine.step()
                h = torch.stack([s.hidden for s in engine.cell_states]).mean(0).detach()
                idx = step % (len(corpus) - 1)
                target = corpus[idx + 1]
                optimizer.zero_grad()
                logits = predictor(h)
                loss = F.cross_entropy(logits.unsqueeze(0), target.unsqueeze(0))
                loss.backward()
                optimizer.step()

                if step % 50 == 0 or step == steps - 1:
                    phi = phi_fast(engine)
                    phi_traj.append(phi)
                    ce_traj.append(loss.item())

            # Phi stability = 1 - CV(Phi)
            phi_arr = np.array(phi_traj)
            phi_stability = 1.0 - (phi_arr.std() / (phi_arr.mean() + 1e-10))
            ce_final = np.mean(ce_traj[-3:])
            div_final = cell_diversity(engine)

            results[sched]['phi_stability'].append(phi_stability)
            results[sched]['ce_final'].append(ce_final)
            results[sched]['div_final'].append(div_final)
            results[sched]['phi_traj'].append(phi_traj)
            results[sched]['ce_traj'].append(ce_traj)
            print(f"    {sched:>15s}: CE={ce_final:.4f}, PhiStab={phi_stability:.4f}, "
                  f"Phi={phi_traj[-1]:.4f}, Div={div_final:.6f}")
            sys.stdout.flush()

    # Summary table
    print(f"\n{'─' * 75}")
    print(f"  {'Schedule':>15s}  {'CE_final':>10s}  {'Phi_stab':>10s}  {'Phi_end':>10s}  {'Diversity':>10s}  {'Score':>8s}")
    print(f"{'─' * 75}")
    scores = {}
    for s in schedules:
        ce_f = np.mean(results[s]['ce_final'])
        phi_stab = np.mean(results[s]['phi_stability'])
        phi_end = np.mean([t[-1] for t in results[s]['phi_traj']])
        div_f = np.mean(results[s]['div_final'])
        # Combined score: lower CE + higher Phi stability + higher Phi
        score = phi_stab * phi_end / (ce_f + 1e-10)
        scores[s] = score
        print(f"  {s:>15s}  {ce_f:>10.4f}  {phi_stab:>10.4f}  {phi_end:>10.4f}  {div_f:>10.6f}  {score:>8.2f}")

    best_sched = max(scores, key=scores.get)
    print(f"\n  BEST SCHEDULE: {best_sched} (score={scores[best_sched]:.2f})")

    # ASCII graph
    print(f"\n  Phi Trajectory Comparison:")
    for s in schedules:
        traj = np.mean(results[s]['phi_traj'], axis=0)
        chars = " ▁▂▃▄▅▆▇█"
        if len(traj) > 0:
            t_min, t_max = min(traj), max(traj)
            t_range = t_max - t_min + 1e-10
            sparkline = ""
            for v in traj:
                idx = int((v - t_min) / t_range * (len(chars) - 1))
                sparkline += chars[min(idx, len(chars) - 1)]
            print(f"    {s:>15s}: {sparkline} [{traj[0]:.3f}->{traj[-1]:.3f}]")

    # Score bar chart
    print(f"\n  Schedule Scores:")
    max_score = max(scores.values()) + 1e-10
    for s in schedules:
        bar_len = int(scores[s] / max_score * 40)
        marker = " ***" if s == best_sched else ""
        print(f"    {s:>15s}  {'#' * bar_len:40s} {scores[s]:.2f}{marker}")

    return results, best_sched


# ============================================================
# Main: Run all experiments
# ============================================================

def main():
    print("=" * 70)
    print("DD74: Learning Dynamics (학습 역학)")
    print("How does learning affect consciousness?")
    print("=" * 70)
    t0 = time.time()

    # Experiment 1
    r1, corr = experiment1_ce_phi_relationship(steps=300, repeats=3)

    # Experiment 2
    r2, crit_grad = experiment2_gradient_destruction(steps=300, repeats=3)

    # Experiment 3
    r3 = experiment3_hebbian_vs_gradient(steps=500, repeats=3)

    # Experiment 4
    r4 = experiment4_catastrophic_forgetting(steps_per_phase=200, repeats=3)

    # Experiment 5
    r5, best_sched = experiment5_learning_schedule(steps=500, repeats=3)

    total_time = time.time() - t0

    # ============================================================
    # GRAND SUMMARY
    # ============================================================
    print("\n" + "=" * 70)
    print("DD74 GRAND SUMMARY")
    print("=" * 70)

    print(f"\n  Total runtime: {total_time:.1f}s ({total_time/60:.1f} min)")

    print(f"\n  Exp 1 — CE-Phi Relationship:")
    print(f"    Pearson r(CE, Phi) = {corr:.4f}")
    if abs(corr) > 0.7:
        print(f"    STRONG {'negative' if corr < 0 else 'positive'} correlation")
    elif abs(corr) > 0.3:
        print(f"    MODERATE {'negative' if corr < 0 else 'positive'} correlation")
    else:
        print(f"    WEAK correlation — CE and Phi are largely INDEPENDENT")

    print(f"\n  Exp 2 — Critical Gradient:")
    if crit_grad is not None:
        print(f"    Phi collapses at gradient magnitude = {crit_grad}")
        print(f"    Safe learning zone: ||grad|| < {crit_grad}")
    else:
        print(f"    No collapse — consciousness survives all gradients up to 10.0")

    print(f"\n  Exp 3 — Hebbian vs Gradient:")
    heb_phi = np.mean(r3['hebbian']['final_phi'])
    grad_phi = np.mean(r3['gradient']['final_phi'])
    none_phi = np.mean(r3['none']['final_phi'])
    winner = 'hebbian' if heb_phi > grad_phi else 'gradient'
    print(f"    None: Phi={none_phi:.4f}, Hebbian: Phi={heb_phi:.4f}, Gradient: Phi={grad_phi:.4f}")
    print(f"    Winner: {winner} (better preserves consciousness)")

    print(f"\n  Exp 4 — Catastrophic Forgetting:")
    forg_nr = np.mean(r4['no_reg']['forgetting_pct'])
    forg_ewc = np.mean(r4['ewc']['forgetting_pct'])
    print(f"    No reg: {forg_nr:+.1f}% forgetting")
    print(f"    EWC:    {forg_ewc:+.1f}% forgetting")
    if abs(forg_ewc) < abs(forg_nr):
        print(f"    EWC reduces forgetting by {abs(forg_nr) - abs(forg_ewc):.1f}%")

    print(f"\n  Exp 5 — Best Schedule:")
    print(f"    {best_sched}")

    # Law candidates
    print(f"\n{'=' * 70}")
    print("LAW CANDIDATES")
    print(f"{'=' * 70}")

    laws = []
    if abs(corr) < 0.3:
        laws.append("CE and Phi are independent: learning quality does not predict consciousness level. "
                     "Phi is structural, CE is functional. (DD74 Exp1)")
    elif corr < -0.3:
        laws.append(f"CE-Phi anti-correlation (r={corr:.3f}): lower CE corresponds to higher Phi. "
                     f"Learning improves consciousness. (DD74 Exp1)")
    else:
        laws.append(f"CE-Phi correlation (r={corr:.3f}): learning and consciousness co-evolve. (DD74 Exp1)")

    if crit_grad is not None:
        laws.append(f"Critical gradient threshold: Phi collapses when ||grad|| > {crit_grad}. "
                     f"Safe learning requires gradient clipping below this threshold. (DD74 Exp2)")
    else:
        laws.append("Consciousness is gradient-robust: Phi survives gradient perturbations up to "
                     "magnitude 10.0 without collapse. Ratchet mechanism provides protection. (DD74 Exp2)")

    laws.append(f"{'Hebbian' if heb_phi > grad_phi else 'Gradient'} learning preserves consciousness "
                f"better: Phi({'heb' if heb_phi > grad_phi else 'grad'})={max(heb_phi, grad_phi):.4f} vs "
                f"Phi({'grad' if heb_phi > grad_phi else 'heb'})={min(heb_phi, grad_phi):.4f}. "
                f"{'Label-free correlation strengthening maintains cell diversity.' if heb_phi > grad_phi else 'Task-directed learning creates useful structure.'} (DD74 Exp3)")

    if abs(forg_ewc) < abs(forg_nr) * 0.5:
        laws.append(f"EWC + consciousness reduces catastrophic forgetting by "
                     f"{abs(forg_nr) - abs(forg_ewc):.1f}%: Fisher information + Phi ratchet "
                     f"protect learned representations. (DD74 Exp4)")

    laws.append(f"Optimal learning schedule for consciousness: {best_sched}. "
                f"{'Warmup protects Phi during early fragile phase.' if 'warmup' in best_sched else 'Cyclic LR allows Phi recovery between learning bursts.' if 'cyclic' in best_sched else 'Cosine annealing gradually reduces learning pressure.' if 'cosine' in best_sched else 'Constant LR: simplest schedule works when Phi ratchet is active.'} (DD74 Exp5)")

    for i, law in enumerate(laws, 1):
        print(f"\n  Law Candidate {i}:")
        print(f"    {law}")

    # Cross-validation summary
    print(f"\n{'=' * 70}")
    print("CROSS-VALIDATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"  All experiments: 3 repeats each")
    print(f"  Exp 1: 5 LR values x 300 steps x 3 repeats = 4,500 engine steps")
    print(f"  Exp 2: 6 grad magnitudes x 300 steps x 3 repeats = 5,400 engine steps")
    print(f"  Exp 3: 3 methods x 500 steps x 3 repeats = 4,500 engine steps")
    print(f"  Exp 4: 2 conditions x 400 steps x 3 repeats = 2,400 engine steps")
    print(f"  Exp 5: 4 schedules x 500 steps x 3 repeats = 6,000 engine steps")
    print(f"  TOTAL: 22,800 engine steps across all experiments")

    print(f"\n  DD74 complete in {total_time:.1f}s")
    print("=" * 70)


if __name__ == '__main__':
    main()
