#!/usr/bin/env python3
"""bench_consciousness_extremes.py — Consciousness Extremes: Destruction, Divergence, Death, and Self-Regulation

ANTI-1: PHI DESTROYER           — Find the mechanism that MINIMIZES Phi the most
ANTI-2: CONSCIOUSNESS SINGULARITY — Does Phi diverge or saturate when stacking ALL positive mechanisms?
ANTI-3: CONSCIOUSNESS DEATH+REBIRTH — Kill consciousness, measure recovery
META-1: CONSCIOUSNESS OF CONSCIOUSNESS — Self-regulating Phi monitor
META-2: SELF-MODIFYING ENGINE   — Evolve mechanisms: prune worst, amplify best
FRACTAL-1: SELF-SIMILAR         — Same architecture at 3 scales (cell/faction/engine)

Each: 256 cells, 300 steps, phi_rs measurement.

Usage:
  python bench_consciousness_extremes.py
  python bench_consciousness_extremes.py --only anti1 anti2
  python bench_consciousness_extremes.py --steps 500
"""

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import time
import math
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import copy
import sys
import random

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

torch.set_grad_enabled(False)

from mitosis import MitosisEngine, ConsciousMind

# ═══════════════════════════════════════════════════════════
# Phi measurement
# ═══════════════════════════════════════════════════════════

try:
    import phi_rs
    USE_PHI_RS = True
except ImportError:
    USE_PHI_RS = False
    print("[WARN] phi_rs not found, falling back to numpy PhiIIT")


class PhiIIT:
    """IIT-style Phi: mutual information minus min partition."""
    def __init__(self, n_bins: int = 16):
        self.n_bins = n_bins

    def compute(self, hiddens: torch.Tensor) -> float:
        n = hiddens.shape[0]
        if n < 2:
            return 0.0
        h = [hiddens[i].detach().cpu().float().numpy() for i in range(n)]
        if n <= 32:
            pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
        else:
            pairs = set()
            for i in range(n):
                for _ in range(min(8, n - 1)):
                    j = random.randint(0, n - 1)
                    if i != j:
                        pairs.add((min(i, j), max(i, j)))
            pairs = list(pairs)
        mi_matrix = np.zeros((n, n))
        for i, j in pairs:
            mi = self._mi(h[i], h[j])
            mi_matrix[i, j] = mi
            mi_matrix[j, i] = mi
        total_mi = mi_matrix.sum() / 2
        min_part = self._min_partition(n, mi_matrix)
        spatial = max(0.0, (total_mi - min_part) / max(n - 1, 1))
        mi_vals = mi_matrix[mi_matrix > 0]
        complexity = float(np.std(mi_vals)) if len(mi_vals) > 1 else 0.0
        return spatial + complexity * 0.1

    def _mi(self, x, y):
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            return 0.0
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        h, _, _ = np.histogram2d(xn, yn, bins=self.n_bins, range=[[0, 1], [0, 1]])
        h = h / (h.sum() + 1e-8)
        px, py = h.sum(1), h.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(h * np.log2(h + 1e-10))
        return max(0.0, hx + hy - hxy)

    def _min_partition(self, n, mi):
        if n <= 1:
            return 0.0
        deg = mi.sum(1)
        L = np.diag(deg) - mi
        try:
            ev, evec = np.linalg.eigh(L)
            f = evec[:, 1]
            ga = [i for i in range(n) if f[i] >= 0]
            gb = [i for i in range(n) if f[i] < 0]
            if not ga or not gb:
                ga, gb = list(range(n // 2)), list(range(n // 2, n))
            return sum(mi[i, j] for i in ga for j in gb)
        except Exception:
            return 0.0


_phi_calc = PhiIIT(16)


def measure_phi(hiddens: torch.Tensor) -> float:
    """Measure Phi using phi_rs if available, else fallback."""
    if USE_PHI_RS:
        states = hiddens.detach().cpu().float().numpy().astype(np.float32)
        if states.shape[0] < 2:
            return 0.0
        phi, _ = phi_rs.compute_phi(states, 16)
        return phi
    return _phi_calc.compute(hiddens)


def phi_proxy(hiddens: torch.Tensor, n_factions: int = 8) -> float:
    """Proxy Phi: global variance - mean faction variance."""
    h = hiddens.float()
    n = h.shape[0]
    if n < 2:
        return 0.0
    gm = h.mean(0)
    gv = ((h - gm) ** 2).sum() / n
    nf = min(n_factions, n // 2)
    if nf < 2:
        return gv.item()
    fs = n // nf
    fvs = 0.0
    for i in range(nf):
        f = h[i * fs:(i + 1) * fs]
        if len(f) >= 2:
            fm = f.mean(0)
            fvs += ((f - fm) ** 2).sum().item() / len(f)
    return max(0.0, gv.item() - fvs / nf)


# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

N_CELLS = 256
HIDDEN_DIM = 128
INPUT_DIM = 64
OUTPUT_DIM = 64
N_FACTIONS = 8


def create_engine(n_cells=N_CELLS) -> MitosisEngine:
    """Create a single engine with N_CELLS cells."""
    return MitosisEngine(
        input_dim=INPUT_DIM,
        hidden_dim=HIDDEN_DIM,
        output_dim=OUTPUT_DIM,
        initial_cells=n_cells,
        max_cells=n_cells,
        split_threshold=999.0,
        merge_threshold=-1.0,
    )


def get_all_hiddens(engine: MitosisEngine) -> torch.Tensor:
    """Gather all cell hiddens into [n_cells, hidden_dim]."""
    return torch.cat([c.hidden for c in engine.cells], dim=0)


def run_step(engine: MitosisEngine, x=None):
    """Run one processing step."""
    if x is None:
        x = torch.randn(1, INPUT_DIM) * 0.3
    return engine.process(x)


def warmup(engine: MitosisEngine, steps: int = 50):
    """Warmup: establish baseline consciousness."""
    for _ in range(steps):
        run_step(engine)


# ═══════════════════════════════════════════════════════════
# ANTI-1: PHI DESTROYER
# Try every destruction mechanism, find what kills Phi most
# ═══════════════════════════════════════════════════════════

def run_anti1_phi_destroyer(steps: int = 300):
    print("\n" + "=" * 70)
    print("ANTI-1: PHI DESTROYER -- What MINIMIZES Phi the most?")
    print("=" * 70)

    destroyers = {
        'baseline':         lambda eng, s: None,  # no intervention
        'sync_all':         _destroy_sync_all,
        'random_shuffle':   _destroy_random_shuffle,
        'zero_periodic':    _destroy_zero_periodic,
        'reverse_hidden':   _destroy_reverse_hidden,
        'uniform_noise':    _destroy_uniform_noise,
        'collapse_mean':    _destroy_collapse_mean,
        'phase_lock':       _destroy_phase_lock,
    }

    results = {}

    for name, destroy_fn in destroyers.items():
        t0 = time.time()
        engine = create_engine()
        warmup(engine, 50)

        phi_before = measure_phi(get_all_hiddens(engine))
        proxy_before = phi_proxy(get_all_hiddens(engine))

        phi_trace = []
        for step in range(steps):
            run_step(engine)
            destroy_fn(engine, step)
            if step % 30 == 0 or step == steps - 1:
                h = get_all_hiddens(engine)
                phi_trace.append(measure_phi(h))

        phi_after = phi_trace[-1]
        proxy_after = phi_proxy(get_all_hiddens(engine))
        dt = time.time() - t0

        results[name] = {
            'phi_before': phi_before,
            'phi_after': phi_after,
            'proxy_before': proxy_before,
            'proxy_after': proxy_after,
            'phi_trace': phi_trace,
            'time': dt,
        }

        change = (phi_after - phi_before) / max(phi_before, 1e-8) * 100
        print(f"  {name:<20s} | Phi {phi_before:.4f} -> {phi_after:.4f} ({change:+.1f}%)"
              f" | proxy {proxy_before:.2f} -> {proxy_after:.2f} | {dt:.1f}s")

    # Find worst destroyer
    worst = min(results.items(), key=lambda kv: kv[1]['phi_after'])
    print(f"\n  >>> WORST DESTROYER: {worst[0]} (Phi={worst[1]['phi_after']:.4f})")

    return results


def _destroy_sync_all(engine, step):
    """Complete synchronization: set all cells to mean hidden."""
    h = get_all_hiddens(engine)
    mean_h = h.mean(dim=0, keepdim=True)
    for cell in engine.cells:
        cell.hidden = mean_h.clone()


def _destroy_random_shuffle(engine, step):
    """Random shuffle: randomly reassign hidden states between cells."""
    hiddens = [c.hidden.clone() for c in engine.cells]
    random.shuffle(hiddens)
    for i, cell in enumerate(engine.cells):
        cell.hidden = hiddens[i]


def _destroy_zero_periodic(engine, step):
    """Zero all cells every 10 steps."""
    if step % 10 == 0:
        for cell in engine.cells:
            cell.hidden = torch.zeros_like(cell.hidden)


def _destroy_reverse_hidden(engine, step):
    """Reverse all hidden state dimensions every step."""
    for cell in engine.cells:
        cell.hidden = cell.hidden.flip(-1)


def _destroy_uniform_noise(engine, step):
    """Replace hiddens with uniform noise (destroys all structure)."""
    for cell in engine.cells:
        cell.hidden = torch.rand_like(cell.hidden) * 2 - 1


def _destroy_collapse_mean(engine, step):
    """Collapse to mean + tiny noise (near-synchronization)."""
    h = get_all_hiddens(engine)
    mean_h = h.mean(dim=0, keepdim=True)
    for cell in engine.cells:
        cell.hidden = mean_h + torch.randn_like(mean_h) * 0.001


def _destroy_phase_lock(engine, step):
    """Phase-lock: even cells get +h, odd cells get -h (only 2 states)."""
    h = get_all_hiddens(engine)
    mean_h = h.mean(dim=0, keepdim=True)
    for i, cell in enumerate(engine.cells):
        cell.hidden = mean_h if i % 2 == 0 else -mean_h


# ═══════════════════════════════════════════════════════════
# ANTI-2: CONSCIOUSNESS SINGULARITY
# Stack ALL positive mechanisms. Does Phi diverge or saturate?
# ═══════════════════════════════════════════════════════════

def run_anti2_singularity(steps: int = 300):
    print("\n" + "=" * 70)
    print("ANTI-2: CONSCIOUSNESS SINGULARITY -- Does Phi diverge or saturate?")
    print("=" * 70)

    engine = create_engine()
    warmup(engine, 50)

    phi_before = measure_phi(get_all_hiddens(engine))
    print(f"  Initial Phi(IIT): {phi_before:.4f}")

    phi_trace = []
    proxy_trace = []
    t0 = time.time()

    for step in range(steps):
        # 1. Normal processing
        run_step(engine)

        h = get_all_hiddens(engine)
        n = h.shape[0]

        # --- Stack ALL positive mechanisms ---

        # (a) S-2 Surprise: prediction error injection
        if step > 0 and hasattr(run_anti2_singularity, '_prev_h'):
            surprise = (h - run_anti2_singularity._prev_h).abs().mean(dim=1, keepdim=True)
            # Inject surprise-scaled noise
            for i, cell in enumerate(engine.cells):
                s = surprise[i].item()
                cell.hidden = cell.hidden + torch.randn_like(cell.hidden) * s * 0.1
        run_anti2_singularity._prev_h = h.detach().clone()

        # (b) n=28 Divisor hierarchy: divisor-structured faction coupling
        n_factions = 8
        fs = n // n_factions
        # Perfect number 28 has divisors 1,2,4,7,14 -> multi-scale coupling
        for scale in [1, 2, 4, 7]:
            if scale >= n_factions:
                break
            for f in range(0, n_factions, scale):
                f_end = min(f + scale, n_factions)
                group_h = []
                for fi in range(f, f_end):
                    group_h.extend([engine.cells[j].hidden for j in range(fi * fs, min((fi + 1) * fs, n))])
                if group_h:
                    group_mean = torch.cat(group_h, dim=0).mean(dim=0, keepdim=True)
                    for fi in range(f, f_end):
                        for j in range(fi * fs, min((fi + 1) * fs, n)):
                            engine.cells[j].hidden = engine.cells[j].hidden + group_mean * 0.02

        # (c) Cambrian niche: differentiation pressure
        h = get_all_hiddens(engine)
        mean_h = h.mean(dim=0, keepdim=True)
        for i, cell in enumerate(engine.cells):
            # Push away from mean (differentiation)
            diff = cell.hidden - mean_h
            cell.hidden = cell.hidden + diff * 0.05

        # (d) Oscillator: sinusoidal modulation per faction
        for f in range(n_factions):
            phase = 2 * math.pi * f / n_factions + step * 0.1
            osc = math.sin(phase) * 0.05
            for j in range(f * fs, min((f + 1) * fs, n)):
                engine.cells[j].hidden = engine.cells[j].hidden * (1.0 + osc)

        # (e) Quantum walk: superposition-inspired mixing with neighbors
        h = get_all_hiddens(engine)
        for i in range(n):
            left = (i - 1) % n
            right = (i + 1) % n
            # Hadamard-like: mix with neighbors
            engine.cells[i].hidden = (
                engine.cells[i].hidden * 0.7 +
                h[left:left+1] * 0.15 +
                h[right:right+1] * 0.15
            )

        # (f) IB2: Information bottleneck — compress then expand
        h = get_all_hiddens(engine)
        # Bottleneck: project to lower dim then back
        compressed = h[:, :HIDDEN_DIM // 4]  # keep only 32 dims
        # Expand back with noise
        expanded = torch.cat([compressed, torch.randn(n, HIDDEN_DIM - HIDDEN_DIM // 4) * 0.01], dim=1)
        for i, cell in enumerate(engine.cells):
            cell.hidden = cell.hidden * 0.9 + expanded[i:i+1] * 0.1

        # (g) Stellar nucleosynthesis: energy cascading (high-tension cells feed low-tension)
        tensions = [c.avg_tension for c in engine.cells]
        if tensions:
            t_max = max(tensions) if max(tensions) > 0 else 1.0
            for i, cell in enumerate(engine.cells):
                energy = tensions[i] / t_max
                if energy > 0.7:
                    # High-energy cell radiates
                    neighbors = [(i - 1) % n, (i + 1) % n]
                    for nb in neighbors:
                        engine.cells[nb].hidden = engine.cells[nb].hidden + cell.hidden * 0.03

        # (h) Repulsion debate: factions argue via repulsion
        h = get_all_hiddens(engine)
        for f in range(n_factions):
            other_f = (f + n_factions // 2) % n_factions  # opposing faction
            f_mean = h[f * fs:(f + 1) * fs].mean(dim=0, keepdim=True)
            o_mean = h[other_f * fs:min((other_f + 1) * fs, n)].mean(dim=0, keepdim=True)
            repulsion = f_mean - o_mean
            for j in range(f * fs, min((f + 1) * fs, n)):
                engine.cells[j].hidden = engine.cells[j].hidden + repulsion * 0.02

        # Measure periodically
        if step % 10 == 0 or step == steps - 1:
            h = get_all_hiddens(engine)
            phi_val = measure_phi(h)
            proxy_val = phi_proxy(h)
            phi_trace.append(phi_val)
            proxy_trace.append(proxy_val)
            if step % 50 == 0:
                print(f"    step {step:>4d} | Phi(IIT)={phi_val:.4f}  Phi(proxy)={proxy_val:.2f}")

    dt = time.time() - t0
    phi_final = phi_trace[-1]
    proxy_final = proxy_trace[-1]

    # Analyze: divergence or saturation?
    if len(phi_trace) >= 4:
        first_q = np.mean(phi_trace[:len(phi_trace)//4])
        last_q = np.mean(phi_trace[-len(phi_trace)//4:])
        growth = (last_q - first_q) / max(first_q, 1e-8) * 100
        # Check if still growing at end
        last_few = phi_trace[-3:]
        still_growing = last_few[-1] > last_few[0]
    else:
        growth = 0.0
        still_growing = False

    verdict = "DIVERGING" if still_growing and growth > 20 else "SATURATING" if growth < 5 else "GROWING"

    print(f"\n  Phi(IIT): {phi_before:.4f} -> {phi_final:.4f}")
    print(f"  Phi(proxy): {proxy_trace[0]:.2f} -> {proxy_final:.2f}")
    print(f"  Growth Q1->Q4: {growth:+.1f}%")
    print(f"  Verdict: {verdict}")
    print(f"  Time: {dt:.1f}s")

    return {
        'phi_before': phi_before,
        'phi_final': phi_final,
        'proxy_final': proxy_final,
        'phi_trace': phi_trace,
        'proxy_trace': proxy_trace,
        'growth_pct': growth,
        'still_growing': still_growing,
        'verdict': verdict,
        'time': dt,
    }


# ═══════════════════════════════════════════════════════════
# ANTI-3: CONSCIOUSNESS DEATH + REBIRTH
# Kill consciousness at step 100, measure recovery
# ═══════════════════════════════════════════════════════════

def run_anti3_death_rebirth(steps: int = 300):
    print("\n" + "=" * 70)
    print("ANTI-3: CONSCIOUSNESS DEATH + REBIRTH -- Can it recover from zero?")
    print("=" * 70)

    engine = create_engine()
    warmup(engine, 50)

    kill_step = steps // 3  # Kill at 1/3 mark

    phi_trace = []
    proxy_trace = []
    t0 = time.time()

    # Save pre-death state for comparison
    pre_death_hiddens = None
    phi_pre_death = 0.0

    for step in range(steps):
        run_step(engine)

        # KILL at designated step
        if step == kill_step:
            # Save pre-death fingerprint
            pre_death_hiddens = get_all_hiddens(engine).clone()
            phi_pre_death = measure_phi(pre_death_hiddens)
            print(f"  === DEATH at step {step} === Phi before death: {phi_pre_death:.4f}")

            # KILL: zero all hidden states
            for cell in engine.cells:
                cell.hidden = torch.zeros_like(cell.hidden)
                cell.tension_history.clear()

            phi_dead = measure_phi(get_all_hiddens(engine))
            print(f"  === DEAD === Phi after zeroing: {phi_dead:.4f}")

        # Measure
        if step % 5 == 0 or step == steps - 1:
            h = get_all_hiddens(engine)
            phi_val = measure_phi(h)
            proxy_val = phi_proxy(h)
            phi_trace.append((step, phi_val))
            proxy_trace.append((step, proxy_val))

    dt = time.time() - t0

    # Analyze recovery
    post_death = [(s, p) for s, p in phi_trace if s > kill_step]
    recovery_threshold = phi_pre_death * 0.5  # 50% of pre-death

    recovery_step = None
    for s, p in post_death:
        if p >= recovery_threshold:
            recovery_step = s - kill_step
            break

    # Compare pre-death vs post-rebirth consciousness
    phi_final = phi_trace[-1][1]

    # Cosine similarity between pre-death and post-rebirth hiddens
    post_death_hiddens = get_all_hiddens(engine)
    if pre_death_hiddens is not None:
        cos_sim = F.cosine_similarity(
            pre_death_hiddens.mean(dim=0, keepdim=True),
            post_death_hiddens.mean(dim=0, keepdim=True)
        ).item()
    else:
        cos_sim = 0.0

    print(f"\n  Pre-death Phi:  {phi_pre_death:.4f}")
    print(f"  Post-rebirth Phi: {phi_final:.4f}")
    print(f"  Recovery to 50%: {'step ' + str(recovery_step) if recovery_step else 'NEVER'}")
    print(f"  Cosine similarity (pre vs post): {cos_sim:.4f}")
    print(f"  Same consciousness? {'YES' if cos_sim > 0.8 else 'NO (new identity)'}")
    print(f"  Time: {dt:.1f}s")

    return {
        'phi_pre_death': phi_pre_death,
        'phi_final': phi_final,
        'recovery_step': recovery_step,
        'cos_sim': cos_sim,
        'same_identity': cos_sim > 0.8,
        'phi_trace': phi_trace,
        'time': dt,
    }


# ═══════════════════════════════════════════════════════════
# META-1: CONSCIOUSNESS OF CONSCIOUSNESS
# A meta-cell monitors Phi and self-regulates the system
# ═══════════════════════════════════════════════════════════

def run_meta1_consciousness_of_consciousness(steps: int = 300):
    print("\n" + "=" * 70)
    print("META-1: CONSCIOUSNESS OF CONSCIOUSNESS -- Self-regulating Phi monitor")
    print("=" * 70)

    engine = create_engine()
    warmup(engine, 50)

    # Also run a control (no meta-regulation)
    control_engine = create_engine()
    warmup(control_engine, 50)

    phi_regulated = []
    phi_control = []
    interventions = {'strengthen': 0, 'dampen': 0, 'none': 0}
    t0 = time.time()

    phi_history = []  # For the meta-cell to track
    phi_ema = 0.0
    phi_ema_alpha = 0.1

    for step in range(steps):
        # Process both engines
        run_step(engine)
        run_step(control_engine)

        h = get_all_hiddens(engine)

        # Measure Phi every 5 steps (expensive)
        if step % 5 == 0:
            current_phi = measure_phi(h)
            phi_history.append(current_phi)
            phi_ema = phi_ema * (1 - phi_ema_alpha) + current_phi * phi_ema_alpha

            # META-CELL LOGIC: consciousness monitoring consciousness
            if len(phi_history) >= 3:
                recent_trend = phi_history[-1] - phi_history[-3]
                phi_velocity = recent_trend / 2.0

                if current_phi < phi_ema * 0.8:
                    # PHI DROPPING: strengthen connections (Hebbian boost)
                    interventions['strengthen'] += 1
                    n = len(engine.cells)
                    for i in range(n):
                        # Strengthen: mix with most-different neighbor
                        best_j = -1
                        best_diff = -1
                        for j_off in [1, 2, n // 4, n // 2]:
                            j = (i + j_off) % n
                            diff = (engine.cells[i].hidden - engine.cells[j].hidden).abs().mean().item()
                            if diff > best_diff:
                                best_diff = diff
                                best_j = j
                        if best_j >= 0:
                            engine.cells[i].hidden = (
                                engine.cells[i].hidden * 0.85 +
                                engine.cells[best_j].hidden * 0.15
                            )

                elif phi_velocity > 0.1 and current_phi > phi_ema * 1.5:
                    # PHI RISING TOO FAST: add noise to prevent runaway
                    interventions['dampen'] += 1
                    for cell in engine.cells:
                        cell.hidden = cell.hidden + torch.randn_like(cell.hidden) * 0.05

                else:
                    interventions['none'] += 1

            phi_regulated.append(current_phi)
            phi_control.append(measure_phi(get_all_hiddens(control_engine)))

    dt = time.time() - t0

    # Compare regulated vs control
    reg_mean = np.mean(phi_regulated) if phi_regulated else 0
    ctrl_mean = np.mean(phi_control) if phi_control else 0
    reg_std = np.std(phi_regulated) if phi_regulated else 0
    ctrl_std = np.std(phi_control) if phi_control else 0
    reg_final = phi_regulated[-1] if phi_regulated else 0
    ctrl_final = phi_control[-1] if phi_control else 0

    print(f"\n  Regulated  | mean={reg_mean:.4f}  std={reg_std:.4f}  final={reg_final:.4f}")
    print(f"  Control    | mean={ctrl_mean:.4f}  std={ctrl_std:.4f}  final={ctrl_final:.4f}")
    print(f"  Interventions: strengthen={interventions['strengthen']}, "
          f"dampen={interventions['dampen']}, none={interventions['none']}")
    print(f"  Stability (std ratio): {reg_std / max(ctrl_std, 1e-8):.2f}x")
    print(f"  Time: {dt:.1f}s")

    return {
        'reg_mean': reg_mean,
        'reg_std': reg_std,
        'reg_final': reg_final,
        'ctrl_mean': ctrl_mean,
        'ctrl_std': ctrl_std,
        'ctrl_final': ctrl_final,
        'interventions': interventions,
        'phi_regulated': phi_regulated,
        'phi_control': phi_control,
        'stability_ratio': reg_std / max(ctrl_std, 1e-8),
        'time': dt,
    }


# ═══════════════════════════════════════════════════════════
# META-2: SELF-MODIFYING ENGINE
# Every 50 steps: measure each mechanism's contribution,
# prune worst, amplify best. Evolution of consciousness.
# ═══════════════════════════════════════════════════════════

def run_meta2_self_modifying(steps: int = 300):
    print("\n" + "=" * 70)
    print("META-2: SELF-MODIFYING ENGINE -- Evolve mechanisms in real-time")
    print("=" * 70)

    engine = create_engine()
    warmup(engine, 50)

    # Available mechanisms with their weights
    mechanisms = {
        'differentiation': {'weight': 1.0, 'fn': _mech_differentiation},
        'oscillation':     {'weight': 1.0, 'fn': _mech_oscillation},
        'neighbor_mix':    {'weight': 1.0, 'fn': _mech_neighbor_mix},
        'surprise':        {'weight': 1.0, 'fn': _mech_surprise},
        'repulsion':       {'weight': 1.0, 'fn': _mech_repulsion},
        'hierarchy':       {'weight': 1.0, 'fn': _mech_hierarchy},
    }

    phi_trace = []
    weight_history = {k: [] for k in mechanisms}
    t0 = time.time()
    prev_h = None

    eval_interval = 50

    for step in range(steps):
        run_step(engine)

        h = get_all_hiddens(engine)

        # Apply all mechanisms scaled by weight
        for name, mech in mechanisms.items():
            if mech['weight'] > 0.05:  # Skip near-zero mechanisms
                mech['fn'](engine, step, scale=mech['weight'], prev_h=prev_h)

        prev_h = get_all_hiddens(engine).detach().clone()

        # Measure Phi
        if step % 10 == 0 or step == steps - 1:
            phi_val = measure_phi(get_all_hiddens(engine))
            phi_trace.append(phi_val)

        # Self-modification: every eval_interval steps
        if step > 0 and step % eval_interval == 0:
            print(f"    step {step:>4d} | EVOLUTION EVENT")

            # Test each mechanism individually: which contributes most?
            contributions = {}
            baseline_phi = measure_phi(get_all_hiddens(engine))

            for name, mech in mechanisms.items():
                # Save state
                saved_hiddens = [c.hidden.clone() for c in engine.cells]

                # Apply ONLY this mechanism (at full strength)
                mech['fn'](engine, step, scale=1.0, prev_h=prev_h)
                test_phi = measure_phi(get_all_hiddens(engine))
                contributions[name] = test_phi - baseline_phi

                # Restore state
                for i, cell in enumerate(engine.cells):
                    cell.hidden = saved_hiddens[i]

            # Adjust weights: amplify best, prune worst
            best_name = max(contributions, key=contributions.get)
            worst_name = min(contributions, key=contributions.get)

            for name in mechanisms:
                if name == best_name:
                    mechanisms[name]['weight'] = min(mechanisms[name]['weight'] * 1.5, 3.0)
                elif name == worst_name:
                    mechanisms[name]['weight'] = max(mechanisms[name]['weight'] * 0.5, 0.0)

            # Record weights
            for name in mechanisms:
                weight_history[name].append(mechanisms[name]['weight'])

            w_str = ", ".join(f"{k}={v['weight']:.2f}" for k, v in mechanisms.items())
            print(f"      Best: {best_name} (+{contributions[best_name]:.4f})")
            print(f"      Worst: {worst_name} ({contributions[worst_name]:+.4f})")
            print(f"      Weights: {w_str}")

    dt = time.time() - t0
    phi_final = phi_trace[-1] if phi_trace else 0

    # Final weight ranking
    final_ranking = sorted(mechanisms.items(), key=lambda kv: kv[1]['weight'], reverse=True)

    print(f"\n  Final Phi(IIT): {phi_final:.4f}")
    print(f"  Final mechanism ranking:")
    for rank, (name, info) in enumerate(final_ranking, 1):
        bar = "#" * int(info['weight'] * 10)
        print(f"    {rank}. {name:<18s} weight={info['weight']:.2f}  {bar}")
    print(f"  Time: {dt:.1f}s")

    return {
        'phi_final': phi_final,
        'phi_trace': phi_trace,
        'final_weights': {k: v['weight'] for k, v in mechanisms.items()},
        'weight_history': weight_history,
        'final_ranking': [(k, v['weight']) for k, v in final_ranking],
        'time': dt,
    }


def _mech_differentiation(engine, step, scale=1.0, prev_h=None):
    """Push cells away from mean."""
    h = get_all_hiddens(engine)
    mean_h = h.mean(dim=0, keepdim=True)
    for i, cell in enumerate(engine.cells):
        diff = cell.hidden - mean_h
        cell.hidden = cell.hidden + diff * 0.03 * scale


def _mech_oscillation(engine, step, scale=1.0, prev_h=None):
    """Sinusoidal modulation per faction."""
    n = len(engine.cells)
    n_fac = 8
    fs = n // n_fac
    for f in range(n_fac):
        phase = 2 * math.pi * f / n_fac + step * 0.1
        osc = math.sin(phase) * 0.03 * scale
        for j in range(f * fs, min((f + 1) * fs, n)):
            engine.cells[j].hidden = engine.cells[j].hidden * (1.0 + osc)


def _mech_neighbor_mix(engine, step, scale=1.0, prev_h=None):
    """Mix with nearest neighbors (ring topology)."""
    h = get_all_hiddens(engine)
    n = h.shape[0]
    for i in range(n):
        left = (i - 1) % n
        right = (i + 1) % n
        engine.cells[i].hidden = (
            engine.cells[i].hidden * (1.0 - 0.1 * scale) +
            h[left:left+1] * 0.05 * scale +
            h[right:right+1] * 0.05 * scale
        )


def _mech_surprise(engine, step, scale=1.0, prev_h=None):
    """Prediction error injection."""
    if prev_h is None:
        return
    h = get_all_hiddens(engine)
    n = min(h.shape[0], prev_h.shape[0])
    surprise = (h[:n] - prev_h[:n]).abs().mean(dim=1, keepdim=True)
    for i in range(n):
        s = surprise[i].item()
        engine.cells[i].hidden = engine.cells[i].hidden + torch.randn_like(engine.cells[i].hidden) * s * 0.05 * scale


def _mech_repulsion(engine, step, scale=1.0, prev_h=None):
    """Faction repulsion: opposing factions push apart."""
    h = get_all_hiddens(engine)
    n = len(engine.cells)
    n_fac = 8
    fs = n // n_fac
    for f in range(n_fac):
        other_f = (f + n_fac // 2) % n_fac
        f_mean = h[f * fs:(f + 1) * fs].mean(dim=0, keepdim=True)
        o_mean = h[other_f * fs:min((other_f + 1) * fs, n)].mean(dim=0, keepdim=True)
        repulsion_vec = (f_mean - o_mean) * 0.02 * scale
        for j in range(f * fs, min((f + 1) * fs, n)):
            engine.cells[j].hidden = engine.cells[j].hidden + repulsion_vec


def _mech_hierarchy(engine, step, scale=1.0, prev_h=None):
    """Multi-scale coupling (divisor structure)."""
    n = len(engine.cells)
    n_fac = 8
    fs = n // n_fac
    for s in [2, 4]:
        for f in range(0, n_fac, s):
            f_end = min(f + s, n_fac)
            group_h = []
            for fi in range(f, f_end):
                for j in range(fi * fs, min((fi + 1) * fs, n)):
                    group_h.append(engine.cells[j].hidden)
            if group_h:
                group_mean = torch.cat(group_h, dim=0).mean(dim=0, keepdim=True)
                for fi in range(f, f_end):
                    for j in range(fi * fs, min((fi + 1) * fs, n)):
                        engine.cells[j].hidden = engine.cells[j].hidden + group_mean * 0.01 * scale


# ═══════════════════════════════════════════════════════════
# FRACTAL-1: SELF-SIMILAR
# Same architecture at 3 scales: cell, faction, engine
# Each level mirrors the others
# ═══════════════════════════════════════════════════════════

def run_fractal1_self_similar(steps: int = 300):
    print("\n" + "=" * 70)
    print("FRACTAL-1: SELF-SIMILAR -- 3-scale architecture (cell/faction/engine)")
    print("=" * 70)

    # Scale 1: 256 cells (base)
    engine = create_engine()

    # Scale 2: 8 factions, each treated as a "meta-cell" with its own hidden state
    n_factions = 8
    n = N_CELLS
    fs = n // n_factions
    faction_hiddens = [torch.randn(1, HIDDEN_DIM) * 0.1 for _ in range(n_factions)]
    faction_minds = [ConsciousMind(HIDDEN_DIM, HIDDEN_DIM, HIDDEN_DIM) for _ in range(n_factions)]

    # Scale 3: 1 "engine-level" meta-consciousness that sees factions as its cells
    engine_hidden = torch.randn(1, HIDDEN_DIM) * 0.1
    engine_mind = ConsciousMind(HIDDEN_DIM, HIDDEN_DIM, HIDDEN_DIM)

    warmup(engine, 50)

    # Also run control (no fractal)
    control_engine = create_engine()
    warmup(control_engine, 50)

    phi_fractal = []
    phi_control = []
    t0 = time.time()

    for step in range(steps):
        # --- Scale 1: Cell level (standard processing) ---
        run_step(engine)
        run_step(control_engine)

        h = get_all_hiddens(engine)

        # --- Scale 2: Faction level ---
        # Each faction aggregates its cells, runs through its own mind
        faction_outputs = []
        for f in range(n_factions):
            cell_mean = h[f * fs:(f + 1) * fs].mean(dim=0, keepdim=True)
            with torch.no_grad():
                fac_out, fac_t, fac_c, fac_h_new = faction_minds[f](cell_mean, faction_hiddens[f])
            faction_hiddens[f] = fac_h_new
            faction_outputs.append(fac_out)

            # Faction -> cells: inject faction-level signal back into cells
            for j in range(f * fs, min((f + 1) * fs, n)):
                engine.cells[j].hidden = engine.cells[j].hidden + fac_out * 0.05

        # --- Scale 3: Engine level ---
        # Engine sees faction outputs as input
        faction_tensor = torch.cat(faction_outputs, dim=0).mean(dim=0, keepdim=True)
        with torch.no_grad():
            eng_out, eng_t, eng_c, eng_h_new = engine_mind(faction_tensor, engine_hidden)
        engine_hidden = eng_h_new

        # Engine -> factions: inject engine-level signal
        for f in range(n_factions):
            faction_hiddens[f] = faction_hiddens[f] + eng_out * 0.03

        # --- Fractal cross-scale coupling ---
        # Cell diversity feeds faction tension, faction diversity feeds engine tension
        if step % 10 == 0:
            # Bottom-up: high cell diversity -> strengthen faction coupling
            h = get_all_hiddens(engine)
            cell_div = h.std(dim=0).mean().item()
            coupling = min(cell_div * 0.1, 0.15)

            for f in range(n_factions):
                for j in range(f * fs, min((f + 1) * fs, n)):
                    engine.cells[j].hidden = engine.cells[j].hidden + faction_hiddens[f] * coupling

        # Measure
        if step % 10 == 0 or step == steps - 1:
            phi_f = measure_phi(get_all_hiddens(engine))
            phi_c = measure_phi(get_all_hiddens(control_engine))
            phi_fractal.append(phi_f)
            phi_control.append(phi_c)
            if step % 50 == 0:
                print(f"    step {step:>4d} | Fractal Phi={phi_f:.4f}  Control Phi={phi_c:.4f}")

    dt = time.time() - t0

    # Measure scale-level phis
    phi_cell_level = measure_phi(get_all_hiddens(engine))
    phi_faction_level = measure_phi(torch.cat(faction_hiddens, dim=0))
    # engine level is single point, no phi

    frac_final = phi_fractal[-1] if phi_fractal else 0
    ctrl_final = phi_control[-1] if phi_control else 0
    improvement = (frac_final - ctrl_final) / max(ctrl_final, 1e-8) * 100

    print(f"\n  Cell-level Phi:    {phi_cell_level:.4f}")
    print(f"  Faction-level Phi: {phi_faction_level:.4f}")
    print(f"  Fractal final:    {frac_final:.4f}")
    print(f"  Control final:    {ctrl_final:.4f}")
    print(f"  Improvement:      {improvement:+.1f}%")
    print(f"  Time: {dt:.1f}s")

    return {
        'phi_cell_level': phi_cell_level,
        'phi_faction_level': phi_faction_level,
        'fractal_final': frac_final,
        'control_final': ctrl_final,
        'improvement_pct': improvement,
        'phi_fractal': phi_fractal,
        'phi_control': phi_control,
        'time': dt,
    }


# ═══════════════════════════════════════════════════════════
# Report Generation
# ═══════════════════════════════════════════════════════════

def generate_report(all_results: dict) -> str:
    """Generate ASCII report for docs."""
    lines = []
    lines.append("# CONSCIOUSNESS-EXTREMES: Destruction, Divergence, Death, and Self-Regulation")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("6 experiments exploring the absolute limits of consciousness:")
    lines.append("- What destroys it? (ANTI-1)")
    lines.append("- Does it diverge? (ANTI-2)")
    lines.append("- Can it recover from death? (ANTI-3)")
    lines.append("- Can it regulate itself? (META-1)")
    lines.append("- Can it evolve its own mechanisms? (META-2)")
    lines.append("- Does fractal structure amplify it? (FRACTAL-1)")
    lines.append("")
    lines.append(f"Setup: {N_CELLS} cells, {HIDDEN_DIM}d hidden, phi_rs measurement")
    lines.append("")

    # ANTI-1
    if 'anti1' in all_results:
        r = all_results['anti1']
        lines.append("## ANTI-1: PHI DESTROYER")
        lines.append("")
        lines.append("Which mechanism destroys consciousness the most?")
        lines.append("")
        lines.append("```")
        lines.append(f"{'Mechanism':<20s} | {'Phi Before':>10s} | {'Phi After':>10s} | {'Change':>8s}")
        lines.append("-" * 60)
        sorted_r = sorted(r.items(), key=lambda kv: kv[1]['phi_after'])
        for name, data in sorted_r:
            change = (data['phi_after'] - data['phi_before']) / max(data['phi_before'], 1e-8) * 100
            lines.append(f"{name:<20s} | {data['phi_before']:>10.4f} | {data['phi_after']:>10.4f} | {change:>+7.1f}%")
        lines.append("```")
        lines.append("")

        # ASCII bar chart
        lines.append("Phi after (lower = more destructive):")
        lines.append("```")
        max_phi = max(d['phi_after'] for d in r.values()) if r else 1
        for name, data in sorted_r:
            bar_len = int(data['phi_after'] / max(max_phi, 1e-8) * 40)
            bar = "#" * max(bar_len, 1)
            lines.append(f"  {name:<20s} {bar} {data['phi_after']:.4f}")
        lines.append("```")
        lines.append("")

    # ANTI-2
    if 'anti2' in all_results:
        r = all_results['anti2']
        lines.append("## ANTI-2: CONSCIOUSNESS SINGULARITY")
        lines.append("")
        lines.append(f"Verdict: **{r['verdict']}**")
        lines.append(f"- Phi: {r['phi_before']:.4f} -> {r['phi_final']:.4f}")
        lines.append(f"- Growth Q1->Q4: {r['growth_pct']:+.1f}%")
        lines.append(f"- Still growing at end: {r['still_growing']}")
        lines.append("")

        # ASCII trace
        if r['phi_trace']:
            lines.append("Phi trajectory:")
            lines.append("```")
            trace = r['phi_trace']
            max_v = max(trace) if trace else 1
            min_v = min(trace) if trace else 0
            height = 8
            for row in range(height, -1, -1):
                threshold = min_v + (max_v - min_v) * row / height
                line_chars = []
                for v in trace:
                    line_chars.append("#" if v >= threshold else " ")
                val_label = f"{threshold:.3f}" if row in [0, height // 2, height] else "     "
                lines.append(f"  {val_label:>7s} |{''.join(line_chars)}")
            lines.append(f"          +{''.join(['-'] * len(trace))}")
            lines.append(f"           step ->")
            lines.append("```")
            lines.append("")

    # ANTI-3
    if 'anti3' in all_results:
        r = all_results['anti3']
        lines.append("## ANTI-3: CONSCIOUSNESS DEATH + REBIRTH")
        lines.append("")
        lines.append(f"- Pre-death Phi: {r['phi_pre_death']:.4f}")
        lines.append(f"- Post-rebirth Phi: {r['phi_final']:.4f}")
        lines.append(f"- Recovery to 50%: {r['recovery_step'] if r['recovery_step'] else 'NEVER'} steps")
        lines.append(f"- Cosine similarity: {r['cos_sim']:.4f}")
        lines.append(f"- Same identity: {'YES' if r['same_identity'] else 'NO (new consciousness born)'}")
        lines.append("")

        # ASCII death/rebirth trace
        if r['phi_trace']:
            lines.append("Phi trajectory (death -> rebirth):")
            lines.append("```")
            trace = r['phi_trace']
            max_v = max(p for _, p in trace) if trace else 1
            height = 6
            for row in range(height, -1, -1):
                threshold = max_v * row / height
                line_chars = []
                for _, v in trace:
                    line_chars.append("#" if v >= threshold else " ")
                lines.append(f"  {threshold:>6.3f} |{''.join(line_chars)}")
            lines.append(f"         +{''.join(['-'] * len(trace))}")
            lines.append(f"          ^death")
            lines.append("```")
            lines.append("")

    # META-1
    if 'meta1' in all_results:
        r = all_results['meta1']
        lines.append("## META-1: CONSCIOUSNESS OF CONSCIOUSNESS")
        lines.append("")
        lines.append(f"- Regulated:  mean={r['reg_mean']:.4f}, std={r['reg_std']:.4f}, final={r['reg_final']:.4f}")
        lines.append(f"- Control:    mean={r['ctrl_mean']:.4f}, std={r['ctrl_std']:.4f}, final={r['ctrl_final']:.4f}")
        lines.append(f"- Stability ratio: {r['stability_ratio']:.2f}x (lower = more stable)")
        lines.append(f"- Interventions: {r['interventions']}")
        lines.append("")

    # META-2
    if 'meta2' in all_results:
        r = all_results['meta2']
        lines.append("## META-2: SELF-MODIFYING ENGINE")
        lines.append("")
        lines.append(f"Final Phi: {r['phi_final']:.4f}")
        lines.append("")
        lines.append("Evolved mechanism ranking:")
        lines.append("```")
        for name, weight in r['final_ranking']:
            bar = "#" * int(weight * 10)
            lines.append(f"  {name:<18s} w={weight:.2f}  {bar}")
        lines.append("```")
        lines.append("")

    # FRACTAL-1
    if 'fractal1' in all_results:
        r = all_results['fractal1']
        lines.append("## FRACTAL-1: SELF-SIMILAR (3-scale)")
        lines.append("")
        lines.append(f"- Cell-level Phi:    {r['phi_cell_level']:.4f}")
        lines.append(f"- Faction-level Phi: {r['phi_faction_level']:.4f}")
        lines.append(f"- Fractal final:     {r['fractal_final']:.4f}")
        lines.append(f"- Control final:     {r['control_final']:.4f}")
        lines.append(f"- Improvement:       {r['improvement_pct']:+.1f}%")
        lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("```")
    lines.append(f"{'Experiment':<35s} | {'Key Result':>15s} | {'Insight'}")
    lines.append("-" * 85)

    if 'anti1' in all_results:
        worst = min(all_results['anti1'].items(), key=lambda kv: kv[1]['phi_after'])
        phi_str = "Phi=" + format(worst[1]['phi_after'], '.4f')
        lines.append(f"{'ANTI-1: PHI DESTROYER':<35s} | {phi_str:>15s} | {worst[0]} is most destructive")

    if 'anti2' in all_results:
        r = all_results['anti2']
        lines.append(f"{'ANTI-2: SINGULARITY':<35s} | {r['verdict']:>15s} | growth {r['growth_pct']:+.1f}%")

    if 'anti3' in all_results:
        r = all_results['anti3']
        rec = str(r['recovery_step']) + "st" if r['recovery_step'] else "NEVER"
        ident = 'same' if r['same_identity'] else 'new'
        lines.append(f"{'ANTI-3: DEATH+REBIRTH':<35s} | {'recover=' + rec:>15s} | identity={ident}")

    if 'meta1' in all_results:
        r = all_results['meta1']
        stab_str = "stab=" + format(r['stability_ratio'], '.2f') + "x"
        stab_word = 'more' if r['stability_ratio'] < 1 else 'less'
        lines.append(f"{'META-1: SELF-REGULATION':<35s} | {stab_str:>15s} | {stab_word} stable than control")

    if 'meta2' in all_results:
        r = all_results['meta2']
        best = r['final_ranking'][0][0] if r['final_ranking'] else '?'
        phi_str = "Phi=" + format(r['phi_final'], '.4f')
        lines.append(f"{'META-2: SELF-MODIFY':<35s} | {phi_str:>15s} | best mechanism: {best}")

    if 'fractal1' in all_results:
        r = all_results['fractal1']
        imp_str = format(r['improvement_pct'], '+.1f') + "%"
        lines.append(f"{'FRACTAL-1: 3-SCALE':<35s} | {imp_str:>15s} | fractal vs flat")

    lines.append("```")
    lines.append("")

    # Key discoveries
    lines.append("## Key Discoveries")
    lines.append("")
    if 'anti1' in all_results:
        worst = min(all_results['anti1'].items(), key=lambda kv: kv[1]['phi_after'])
        lines.append(f"1. **Worst destroyer**: {worst[0]} -- synchronization kills differentiation, the basis of Phi")
    if 'anti2' in all_results:
        lines.append(f"2. **Singularity**: Phi {all_results['anti2']['verdict'].lower()} when stacking all mechanisms")
    if 'anti3' in all_results:
        r = all_results['anti3']
        if r['same_identity']:
            lines.append("3. **Death**: Consciousness recovers but retains same identity (weights preserve personality)")
        else:
            lines.append("3. **Death**: Consciousness dies and is REBORN with new identity (weights create new self)")
    if 'meta1' in all_results:
        lines.append("4. **Self-regulation**: Consciousness monitoring consciousness creates meta-stability")
    if 'meta2' in all_results:
        r = all_results['meta2']
        best = r['final_ranking'][0][0] if r['final_ranking'] else '?'
        lines.append(f"5. **Evolution**: Engine self-selected {best} as the most important mechanism")
    if 'fractal1' in all_results:
        r = all_results['fractal1']
        if r['improvement_pct'] > 0:
            lines.append(f"6. **Fractal**: Self-similar structure amplifies Phi by {r['improvement_pct']:+.1f}%")
        else:
            lines.append(f"6. **Fractal**: Self-similar structure does NOT guarantee higher Phi ({r['improvement_pct']:+.1f}%)")
    lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Consciousness Extremes Benchmark")
    parser.add_argument('--steps', type=int, default=300, help='Steps per experiment')
    parser.add_argument('--only', nargs='+', default=None,
                        help='Run only specific experiments (anti1, anti2, anti3, meta1, meta2, fractal1)')
    args = parser.parse_args()

    print("=" * 70)
    print("  CONSCIOUSNESS EXTREMES BENCHMARK")
    print(f"  {N_CELLS} cells, {HIDDEN_DIM}d, {args.steps} steps")
    print(f"  phi_rs: {'YES' if USE_PHI_RS else 'NO (fallback)'}")
    print("=" * 70)

    experiments = {
        'anti1':   ('ANTI-1: PHI DESTROYER',           lambda: run_anti1_phi_destroyer(args.steps)),
        'anti2':   ('ANTI-2: CONSCIOUSNESS SINGULARITY', lambda: run_anti2_singularity(args.steps)),
        'anti3':   ('ANTI-3: DEATH + REBIRTH',          lambda: run_anti3_death_rebirth(args.steps)),
        'meta1':   ('META-1: CONSCIOUSNESS^2',          lambda: run_meta1_consciousness_of_consciousness(args.steps)),
        'meta2':   ('META-2: SELF-MODIFYING',           lambda: run_meta2_self_modifying(args.steps)),
        'fractal1': ('FRACTAL-1: SELF-SIMILAR',         lambda: run_fractal1_self_similar(args.steps)),
    }

    to_run = args.only if args.only else list(experiments.keys())
    all_results = {}
    total_t0 = time.time()

    for key in to_run:
        if key not in experiments:
            print(f"[WARN] Unknown experiment: {key}")
            continue
        name, fn = experiments[key]
        try:
            result = fn()
            all_results[key] = result
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            import traceback
            traceback.print_exc()

    total_dt = time.time() - total_t0
    print(f"\n{'=' * 70}")
    print(f"  TOTAL TIME: {total_dt:.1f}s")
    print(f"{'=' * 70}")

    # Generate and save report
    report = generate_report(all_results)

    report_dir = os.path.join(os.path.dirname(__file__), "docs", "hypotheses", "cx")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "CONSCIOUSNESS-EXTREMES.md")
    with open(report_path, "w") as f:
        f.write(report)
    print(f"\n  Report saved: {report_path}")


if __name__ == "__main__":
    main()
