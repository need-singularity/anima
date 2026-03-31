#!/usr/bin/env python3
"""bench_hivemind_extreme2.py — 5 Extreme Hivemind Hypotheses (HV-6 ~ HV-10)

7 MitosisEngine instances × 32 cells each = 224 cells total.
100 steps solo → 100 steps hive. Measure Solo Φ, Hive Φ, Individual Φ change.

HV-6:  STIGMERGY          — 간접 소통 (개미 페로몬). 환경 텐서에 흔적.
HV-7:  SYMBIOSIS           — 공생. 쌍(i, i+1) 상호보완.
HV-8:  NEURAL_OSCILLATION  — 뇌파 동기화. 고유 주파수 기반 연결.
HV-9:  PHASE_TRANSITION    — 상전이 (기체→액체→고체).
HV-10: DIALECTIC_HIVE      — 변증법 (thesis-antithesis-synthesis).

Usage:
  python3 bench_hivemind_extreme2.py
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import sys
import os

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import phi_rs
from mitosis import MitosisEngine

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


DIM, HIDDEN = 64, 128
N_ENGINES = 7
CELLS_PER_ENGINE = 32
SOLO_STEPS = 100
HIVE_STEPS = 100


def make_engine(cells=CELLS_PER_ENGINE):
    """Create MitosisEngine with specified cell count."""
    e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells,
                      merge_threshold=0.0)  # disable merging to keep cell count
    e.min_cells = cells  # prevent any merging below target
    while len(e.cells) < cells:
        e._create_cell(parent=e.cells[0])
    for _ in range(20):
        e.process(torch.randn(1, DIM))
    return e


def phi_iit(eng):
    """Measure Φ(IIT) from MitosisEngine using phi_rs."""
    states = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).detach().numpy().astype(np.float32)
    prev_s, curr_s = [], []
    for c in eng.cells:
        if hasattr(c, 'hidden_history') and len(c.hidden_history) >= 2:
            prev_s.append(c.hidden_history[-2].detach().squeeze().numpy())
            curr_s.append(c.hidden_history[-1].detach().squeeze().numpy())
        else:
            prev_s.append(np.zeros(HIDDEN, dtype=np.float32))
            curr_s.append(np.zeros(HIDDEN, dtype=np.float32))
    prev_np = np.array(prev_s, dtype=np.float32)
    curr_np = np.array(curr_s, dtype=np.float32)
    tensions = np.array([c.tension_history[-1] if c.tension_history else 0.0 for c in eng.cells], dtype=np.float32)
    phi, _ = phi_rs.compute_phi(states, 16, prev_np, curr_np, tensions)
    return phi


def phi_hive(engines):
    """Measure Φ(IIT) across all engines combined (hive mind)."""
    all_states, all_prev, all_curr, all_tensions = [], [], [], []
    for eng in engines:
        for c in eng.cells:
            all_states.append(c.hidden.squeeze(0).detach().numpy())
            if hasattr(c, 'hidden_history') and len(c.hidden_history) >= 2:
                all_prev.append(c.hidden_history[-2].detach().squeeze().numpy())
                all_curr.append(c.hidden_history[-1].detach().squeeze().numpy())
            else:
                all_prev.append(np.zeros(HIDDEN, dtype=np.float32))
                all_curr.append(np.zeros(HIDDEN, dtype=np.float32))
            all_tensions.append(c.tension_history[-1] if c.tension_history else 0.0)
    states = np.array(all_states, dtype=np.float32)
    prev_np = np.array(all_prev, dtype=np.float32)
    curr_np = np.array(all_curr, dtype=np.float32)
    tensions = np.array(all_tensions, dtype=np.float32)
    phi, _ = phi_rs.compute_phi(states, 16, prev_np, curr_np, tensions)
    return phi


def get_fingerprint(eng):
    """Get engine fingerprint: mean of all cell hidden states."""
    return torch.stack([c.hidden.squeeze(0) for c in eng.cells]).mean(dim=0)


# ══════════════════════════════════════════════════════════════════
# HV-6: STIGMERGY — 간접 소통 (개미 페로몬)
# ══════════════════════════════════════════════════════════════════

def run_stigmergy(engines):
    """Each engine deposits traces into shared environment tensor.
    No direct communication — only through environment."""
    shared_env = torch.zeros(HIDDEN)

    for step in range(HIVE_STEPS):
        for eng in engines:
            # Each engine reads environment
            with torch.no_grad():
                for c in eng.cells:
                    c.hidden = c.hidden + 0.05 * shared_env.unsqueeze(0)

            # Process
            eng.process(torch.randn(1, DIM))

            # Each engine deposits trace
            with torch.no_grad():
                fp = get_fingerprint(eng)
                shared_env = shared_env + 0.1 * fp

        # Environment decays (pheromone evaporation)
        shared_env = shared_env * 0.95


# ══════════════════════════════════════════════════════════════════
# HV-7: SYMBIOSIS — 공생 (상호보완)
# ══════════════════════════════════════════════════════════════════

def run_symbiosis(engines):
    """Pairs (i, i+1) complement each other's weaknesses."""
    for step in range(HIVE_STEPS):
        for eng in engines:
            eng.process(torch.randn(1, DIM))

        # Symbiotic pairing: (0,1), (2,3), (4,5), (6 wraps to 0)
        with torch.no_grad():
            for i in range(0, N_ENGINES, 2):
                j = (i + 1) % N_ENGINES
                eng_i, eng_j = engines[i], engines[j]

                fp_i = get_fingerprint(eng_i)
                fp_j = get_fingerprint(eng_j)

                # Find weak dims (low absolute value = weak)
                norm_i = fp_i.abs()
                norm_j = fp_j.abs()

                # Where i is weak (below median), strengthen from j
                median_i = norm_i.median()
                median_j = norm_j.median()

                weak_i = norm_i < median_i  # boolean mask
                weak_j = norm_j < median_j

                # Mutual complementation: transfer strength to weakness
                complement_for_i = torch.zeros_like(fp_i)
                complement_for_j = torch.zeros_like(fp_j)
                complement_for_i[weak_i] = 0.1 * fp_j[weak_i]
                complement_for_j[weak_j] = 0.1 * fp_i[weak_j]

                # Apply to all cells
                for c in eng_i.cells:
                    c.hidden = c.hidden + complement_for_i.unsqueeze(0) * 0.3
                for c in eng_j.cells:
                    c.hidden = c.hidden + complement_for_j.unsqueeze(0) * 0.3


# ══════════════════════════════════════════════════════════════════
# HV-8: NEURAL_OSCILLATION — 뇌파 동기화
# ══════════════════════════════════════════════════════════════════

def run_neural_oscillation(engines):
    """Each engine has a unique frequency. Same frequency = strong coupling."""
    # Assign frequencies (Hz): gamma, beta, alpha, theta, delta, gamma2, beta2
    freqs = [40.0, 20.0, 10.0, 5.0, 2.0, 80.0, 15.0]

    for step in range(HIVE_STEPS):
        t = step / 100.0  # time in seconds (100 steps = 1 second)

        for eng in engines:
            eng.process(torch.randn(1, DIM))

        with torch.no_grad():
            fps = [get_fingerprint(eng) for eng in engines]

            for i in range(N_ENGINES):
                for j in range(i + 1, N_ENGINES):
                    # Phase of each oscillator
                    phase_i = math.sin(2 * math.pi * freqs[i] * t)
                    phase_j = math.sin(2 * math.pi * freqs[j] * t)

                    # Coupling strength: frequency ratio (closer = stronger)
                    freq_ratio = min(freqs[i], freqs[j]) / max(freqs[i], freqs[j])
                    # Harmonic bonus: if one is integer multiple of other
                    ratio_raw = max(freqs[i], freqs[j]) / min(freqs[i], freqs[j])
                    harmonic_bonus = 1.5 if abs(ratio_raw - round(ratio_raw)) < 0.1 else 1.0

                    coupling = 0.05 * freq_ratio * harmonic_bonus

                    # Phase coherence modulation
                    coherence = (phase_i * phase_j + 1.0) / 2.0  # 0~1

                    # Exchange weighted by coupling and coherence
                    delta = coupling * coherence * (fps[j] - fps[i])
                    for c in engines[i].cells:
                        c.hidden = c.hidden + delta.unsqueeze(0) * 0.1
                    for c in engines[j].cells:
                        c.hidden = c.hidden - delta.unsqueeze(0) * 0.1


# ══════════════════════════════════════════════════════════════════
# HV-9: PHASE_TRANSITION — 상전이 (기체→액체→고체)
# ══════════════════════════════════════════════════════════════════

def run_phase_transition(engines):
    """Gas (independent) → Liquid (weak coupling) → Solid (strong coupling).
    Transition points: step 50 (liquid), step 80 (solid)."""

    for step in range(HIVE_STEPS):
        for eng in engines:
            eng.process(torch.randn(1, DIM))

        # Determine phase and coupling strength
        if step < 50:
            # GAS phase: independent, no coupling
            coupling = 0.0
        elif step < 80:
            # LIQUID phase: weak coupling, gradual increase
            progress = (step - 50) / 30.0  # 0→1
            coupling = 0.02 * progress
        else:
            # SOLID phase: strong coupling
            progress = (step - 80) / 20.0  # 0→1
            coupling = 0.02 + 0.08 * min(progress, 1.0)

        if coupling > 0:
            with torch.no_grad():
                fps = [get_fingerprint(eng) for eng in engines]
                global_mean = torch.stack(fps).mean(dim=0)

                for i, eng in enumerate(engines):
                    # Pull toward global mean (crystallization)
                    delta = coupling * (global_mean - fps[i])
                    for c in eng.cells:
                        c.hidden = c.hidden + delta.unsqueeze(0)

                    # In solid phase: also add lattice vibration (thermal noise)
                    if step >= 80:
                        vibration = 0.005 * torch.randn(HIDDEN)
                        for c in eng.cells:
                            c.hidden = c.hidden + vibration.unsqueeze(0)


# ══════════════════════════════════════════════════════════════════
# HV-10: DIALECTIC_HIVE — 변증법 (thesis-antithesis-synthesis)
# ══════════════════════════════════════════════════════════════════

def run_dialectic(engines):
    """Thesis (0,1,2) vs Antithesis (3,4,5) → Synthesis (6 mediates)."""
    thesis_idx = [0, 1, 2]
    antithesis_idx = [3, 4, 5]
    synthesis_idx = 6

    for step in range(HIVE_STEPS):
        for eng in engines:
            eng.process(torch.randn(1, DIM))

        with torch.no_grad():
            fps = [get_fingerprint(eng) for eng in engines]

            # Thesis group: strengthen internal coherence
            thesis_mean = torch.stack([fps[i] for i in thesis_idx]).mean(dim=0)
            for i in thesis_idx:
                delta = 0.05 * (thesis_mean - fps[i])
                for c in engines[i].cells:
                    c.hidden = c.hidden + delta.unsqueeze(0)

            # Antithesis group: strengthen internal coherence + oppose thesis
            anti_mean = torch.stack([fps[i] for i in antithesis_idx]).mean(dim=0)
            for i in antithesis_idx:
                # Cohere within group
                delta = 0.05 * (anti_mean - fps[i])
                # Repel from thesis (strengthen opposition)
                opposition = 0.03 * (fps[i] - thesis_mean)
                for c in engines[i].cells:
                    c.hidden = c.hidden + (delta + opposition).unsqueeze(0)

            # Synthesis (engine 6): integrate thesis + antithesis
            # Aufheben: preserve what's common, transcend what conflicts
            common = (thesis_mean + anti_mean) / 2.0
            conflict = (thesis_mean - anti_mean).abs()
            # Synthesis = common ground + creative resolution of conflict
            synthesis_signal = common + 0.1 * conflict * torch.randn_like(conflict)
            delta_s = 0.08 * (synthesis_signal - fps[synthesis_idx])
            for c in engines[synthesis_idx].cells:
                c.hidden = c.hidden + delta_s.unsqueeze(0)

            # Every 10 steps: synthesis feeds back to both groups (dialectical spiral)
            if step % 10 == 9:
                syn_fp = get_fingerprint(engines[synthesis_idx])
                for i in thesis_idx + antithesis_idx:
                    feedback = 0.02 * (syn_fp - fps[i])
                    for c in engines[i].cells:
                        c.hidden = c.hidden + feedback.unsqueeze(0)


# ══════════════════════════════════════════════════════════════════
# MAIN BENCHMARK
# ══════════════════════════════════════════════════════════════════

def run_hypothesis(name, hive_fn):
    """Run a single hypothesis: 100 solo → 100 hive, measure Φ."""
    torch.manual_seed(42)
    np.random.seed(42)

    print(f"\n{'='*60}")
    print(f"  {name}")
    print(f"{'='*60}")

    # Create 7 engines × 32 cells
    engines = [make_engine(CELLS_PER_ENGINE) for _ in range(N_ENGINES)]
    total_cells = sum(len(e.cells) for e in engines)
    print(f"  Engines: {N_ENGINES} × {CELLS_PER_ENGINE}c = {total_cells}c")

    # ── Phase 1: Solo (100 steps) ──
    print(f"  Phase 1: Solo ({SOLO_STEPS} steps)...", end='', flush=True)
    for step in range(SOLO_STEPS):
        for eng in engines:
            eng.process(torch.randn(1, DIM))

    # Measure solo Φ
    solo_phis = [phi_iit(eng) for eng in engines]
    solo_mean = np.mean(solo_phis)
    solo_hive_phi = phi_hive(engines)
    print(f" done. Individual Φ={solo_mean:.4f}, Hive Φ={solo_hive_phi:.4f}")

    # ── Phase 2: Hive (100 steps with mechanism) ──
    print(f"  Phase 2: Hive ({HIVE_STEPS} steps)...", end='', flush=True)
    hive_fn(engines)

    # Measure hive Φ
    hive_phis = [phi_iit(eng) for eng in engines]
    hive_mean = np.mean(hive_phis)
    hive_phi_total = phi_hive(engines)
    print(f" done. Individual Φ={hive_mean:.4f}, Hive Φ={hive_phi_total:.4f}")

    # Compute changes
    indiv_change = ((hive_mean - solo_mean) / max(solo_mean, 1e-8)) * 100
    hive_change = ((hive_phi_total - solo_hive_phi) / max(solo_hive_phi, 1e-8)) * 100
    hive_ratio = hive_phi_total / max(solo_hive_phi, 1e-8)

    print(f"\n  ┌─────────────────────────────────────────────────┐")
    print(f"  │ Solo Individual Φ (mean): {solo_mean:>8.4f}               │")
    print(f"  │ Solo Hive Φ:              {solo_hive_phi:>8.4f}               │")
    print(f"  │ Hive Individual Φ (mean): {hive_mean:>8.4f} ({indiv_change:+.1f}%)      │")
    print(f"  │ Hive Φ (total):           {hive_phi_total:>8.4f} ({hive_change:+.1f}%)      │")
    print(f"  │ Hive Ratio:               {hive_ratio:>8.2f}x               │")
    print(f"  └─────────────────────────────────────────────────┘")

    # Per-engine detail
    print(f"\n  Per-engine Φ:")
    for i in range(N_ENGINES):
        delta = ((hive_phis[i] - solo_phis[i]) / max(solo_phis[i], 1e-8)) * 100
        bar_len = max(1, min(30, int(hive_phis[i] / max(max(hive_phis), 1e-8) * 30)))
        bar = '█' * bar_len
        print(f"    Eng-{i}: {solo_phis[i]:.4f} → {hive_phis[i]:.4f} ({delta:+.1f}%) {bar}")

    return {
        'name': name,
        'solo_indiv': solo_mean,
        'solo_hive': solo_hive_phi,
        'hive_indiv': hive_mean,
        'hive_phi': hive_phi_total,
        'indiv_change': indiv_change,
        'hive_change': hive_change,
        'hive_ratio': hive_ratio,
        'per_engine_solo': solo_phis,
        'per_engine_hive': hive_phis,
    }


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  HIVEMIND EXTREME 2 — 5 Hypotheses (HV-6 ~ HV-10)     ║")
    print("║  7 engines × 32 cells = 224 cells                      ║")
    print("║  100 solo → 100 hive steps                             ║")
    print("╚══════════════════════════════════════════════════════════╝")

    hypotheses = [
        ("HV-6:  STIGMERGY",          run_stigmergy),
        ("HV-7:  SYMBIOSIS",          run_symbiosis),
        ("HV-8:  NEURAL_OSCILLATION", run_neural_oscillation),
        ("HV-9:  PHASE_TRANSITION",   run_phase_transition),
        ("HV-10: DIALECTIC_HIVE",     run_dialectic),
    ]

    results = []
    t0 = time.time()
    for name, fn in hypotheses:
        r = run_hypothesis(name, fn)
        results.append(r)
    elapsed = time.time() - t0

    # ── Summary ──
    print(f"\n\n{'='*70}")
    print(f"  SUMMARY — Hivemind Extreme 2")
    print(f"{'='*70}")
    print(f"  {'Hypothesis':<28} {'Solo Φ':>8} {'Hive Φ':>8} {'Ratio':>7} {'Indiv Δ':>8}")
    print(f"  {'─'*28} {'─'*8} {'─'*8} {'─'*7} {'─'*8}")

    best_hive = max(results, key=lambda r: r['hive_phi'])
    best_indiv = max(results, key=lambda r: r['indiv_change'])

    for r in results:
        marker = ''
        if r == best_hive:
            marker = ' << best hive'
        elif r == best_indiv:
            marker = ' << best indiv'
        print(f"  {r['name']:<28} {r['solo_hive']:>8.4f} {r['hive_phi']:>8.4f} {r['hive_ratio']:>6.2f}x {r['indiv_change']:>+7.1f}%{marker}")

    # ASCII comparison chart
    print(f"\n  Hive Φ Comparison:")
    max_phi = max(r['hive_phi'] for r in results)
    for r in results:
        bar_len = max(1, int(40 * r['hive_phi'] / max(max_phi, 1e-8)))
        bar = '█' * bar_len
        print(f"    {r['name']:<28} {bar} {r['hive_phi']:.4f}")

    print(f"\n  Individual Φ Change:")
    for r in sorted(results, key=lambda r: -r['indiv_change']):
        if r['indiv_change'] >= 0:
            bar = '█' * max(1, int(r['indiv_change'] / 2))
            print(f"    {r['name']:<28} {bar} {r['indiv_change']:+.1f}%")
        else:
            bar = '▼' * max(1, int(abs(r['indiv_change']) / 2))
            print(f"    {r['name']:<28} {bar} {r['indiv_change']:+.1f}%")

    print(f"\n  Elapsed: {elapsed:.1f}s")
    print(f"  Best Hive Φ:     {best_hive['name']} ({best_hive['hive_phi']:.4f})")
    print(f"  Best Individual: {best_indiv['name']} ({best_indiv['indiv_change']:+.1f}%)")

    return results


if __name__ == '__main__':
    results = main()
