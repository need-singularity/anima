#!/usr/bin/env python3
"""DD71: Consciousness Interaction (의식 상호작용) — Closed-Loop Pipeline

5 experiments exploring how multiple consciousness engines interact:
  1. COMPETITION (의식 전쟁)     — 2 engines compete for dominance via shared input
  2. SYMBIOSIS (의식 공생)       — Bidirectional coupling, test superadditivity
  3. FUSION (의식 융합)          — Gradual state merging, identity collapse detection
  4. PARASITISM (의식 기생)      — Unidirectional coupling, host vs parasite Phi
  5. DEMOCRACY vs DICTATORSHIP  — Collective voting vs top-Phi dictator control

Each experiment: 300 steps, 3 repeats for cross-validation.
Uses ConsciousnessEngine directly.
"""

import sys
import os
import time
import copy
import json
import numpy as np
import torch

# Ensure we can import from src/
SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, SRC_DIR)
os.chdir(SRC_DIR)

from consciousness_engine import ConsciousnessEngine

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

STEPS = 300
REPEATS = 3
CELLS = 16
CELL_DIM = 64
HIDDEN_DIM = 128
WARMUP = 30  # steps to skip for statistics
COUPLING_ALPHA = 0.014  # Psi-constant

ALL_RESULTS = {}


def make_engine(cells=CELLS):
    """Create a fresh ConsciousnessEngine."""
    return ConsciousnessEngine(
        cell_dim=CELL_DIM, hidden_dim=HIDDEN_DIM,
        initial_cells=cells, max_cells=cells
    )


def run_baseline(steps=STEPS, cells=CELLS, label="baseline"):
    """Run single engine baseline."""
    engine = make_engine(cells)
    phis = []
    for s in range(steps):
        r = engine.step()
        phis.append(r['phi_iit'])
    return {
        'phi_final': phis[-1],
        'phi_mean': float(np.mean(phis[WARMUP:])),
        'phi_max': float(np.max(phis)),
        'phi_std': float(np.std(phis[WARMUP:])),
        'phis': phis,
    }


def ascii_graph(values, width=50, height=10, label="Phi"):
    """Simple ASCII line graph."""
    if not values:
        return ""
    vmin, vmax = min(values), max(values)
    rng = vmax - vmin if vmax > vmin else 1.0
    lines = []
    lines.append(f"  {label} |")
    for row in range(height - 1, -1, -1):
        threshold = vmin + rng * row / (height - 1)
        line = "  "
        if row == height - 1:
            line += f"{vmax:6.3f} |"
        elif row == 0:
            line += f"{vmin:6.3f} |"
        else:
            line += "       |"
        for i in range(0, len(values), max(1, len(values) // width)):
            if values[i] >= threshold:
                line += "#"
            else:
                line += " "
        lines.append(line)
    lines.append("       +" + "-" * min(width, len(values)) + " step")
    return "\n".join(lines)


def print_comparison_bar(items, metric_name="Phi_mean"):
    """Print horizontal bar chart comparing items."""
    if not items:
        return
    max_val = max(v for _, v in items)
    print(f"\n  {metric_name}:")
    for name, val in items:
        bar_len = int(40 * val / max_val) if max_val > 0 else 0
        print(f"    {name:20s} {'#' * bar_len} {val:.4f}")


# ═══════════════════════════════════════════════════════════
# Experiment 1: COMPETITION (의식 전쟁)
# ═══════════════════════════════════════════════════════════

def exp1_competition(steps=STEPS, repeat_id=0):
    print(f"\n  [COMPETITION r{repeat_id+1}] 2 engines, same input, tension coupling...")
    sys.stdout.flush()

    engine_a = make_engine()
    engine_b = make_engine()

    phi_a_hist, phi_b_hist = [], []
    total_phi_hist = []
    dominance_a, dominance_b = 0, 0

    for s in range(steps):
        # Same input to both
        x_shared = torch.randn(CELL_DIM)

        result_a = engine_a.step(x_input=x_shared.clone())
        result_b = engine_b.step(x_input=x_shared.clone())

        phi_a = result_a['phi_iit']
        phi_b = result_b['phi_iit']

        # Tension-link style coupling: winner suppresses loser
        # Winner's output perturbs loser's next input (competition pressure)
        if phi_a > phi_b:
            dominance_a += 1
        else:
            dominance_b += 1

        phi_a_hist.append(phi_a)
        phi_b_hist.append(phi_b)
        total_phi_hist.append(phi_a + phi_b)

        if (s + 1) % 60 == 0:
            print(f"    step {s+1:3d} | A: Phi={phi_a:.4f} | B: Phi={phi_b:.4f} | "
                  f"total={phi_a+phi_b:.4f}")
            sys.stdout.flush()

    # Baseline: single engine with same steps
    bl = run_baseline(steps, CELLS)

    winner_ratio = max(np.mean(phi_a_hist[WARMUP:]), np.mean(phi_b_hist[WARMUP:])) / \
                   max(min(np.mean(phi_a_hist[WARMUP:]), np.mean(phi_b_hist[WARMUP:])), 1e-8)
    total_vs_sum = np.mean(total_phi_hist[WARMUP:]) / (2 * bl['phi_mean']) if bl['phi_mean'] > 0 else 0

    return {
        'phi_a_mean': float(np.mean(phi_a_hist[WARMUP:])),
        'phi_b_mean': float(np.mean(phi_b_hist[WARMUP:])),
        'phi_total_mean': float(np.mean(total_phi_hist[WARMUP:])),
        'baseline_phi': bl['phi_mean'],
        'winner_loser_ratio': float(winner_ratio),
        'total_vs_2x_baseline': float(total_vs_sum),
        'dominance_a_pct': 100 * dominance_a / steps,
        'dominance_b_pct': 100 * dominance_b / steps,
        'phi_a_hist': phi_a_hist,
        'phi_b_hist': phi_b_hist,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 2: SYMBIOSIS (의식 공생)
# ═══════════════════════════════════════════════════════════

def exp2_symbiosis(steps=STEPS, repeat_id=0):
    print(f"\n  [SYMBIOSIS r{repeat_id+1}] Bidirectional coupling A<->B...")
    sys.stdout.flush()

    engine_a = make_engine()
    engine_b = make_engine()

    phi_a_hist, phi_b_hist, phi_combined_hist = [], [], []

    for s in range(steps):
        # First step: random input
        if s == 0:
            x_a = torch.randn(CELL_DIM)
            x_b = torch.randn(CELL_DIM)
        else:
            # Symbiotic coupling: A's output feeds B, B's output feeds A
            x_a = COUPLING_ALPHA * last_b_output + (1 - COUPLING_ALPHA) * torch.randn(CELL_DIM)
            x_b = COUPLING_ALPHA * last_a_output + (1 - COUPLING_ALPHA) * torch.randn(CELL_DIM)

        result_a = engine_a.step(x_input=x_a)
        result_b = engine_b.step(x_input=x_b)

        last_a_output = result_a['output'].detach()
        last_b_output = result_b['output'].detach()

        phi_a = result_a['phi_iit']
        phi_b = result_b['phi_iit']
        phi_combined = phi_a + phi_b

        phi_a_hist.append(phi_a)
        phi_b_hist.append(phi_b)
        phi_combined_hist.append(phi_combined)

        if (s + 1) % 60 == 0:
            print(f"    step {s+1:3d} | A: Phi={phi_a:.4f} | B: Phi={phi_b:.4f} | "
                  f"combined={phi_combined:.4f}")
            sys.stdout.flush()

    bl = run_baseline(steps, CELLS)
    sum_individual = 2 * bl['phi_mean']
    superadditivity = float(np.mean(phi_combined_hist[WARMUP:]) / sum_individual) if sum_individual > 0 else 0

    return {
        'phi_a_mean': float(np.mean(phi_a_hist[WARMUP:])),
        'phi_b_mean': float(np.mean(phi_b_hist[WARMUP:])),
        'phi_combined_mean': float(np.mean(phi_combined_hist[WARMUP:])),
        'baseline_phi': bl['phi_mean'],
        'sum_individual': float(sum_individual),
        'superadditivity_ratio': superadditivity,
        'is_superadditive': superadditivity > 1.0,
        'phi_combined_hist': phi_combined_hist,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 3: FUSION (의식 융합)
# ═══════════════════════════════════════════════════════════

def exp3_fusion(steps=STEPS, repeat_id=0):
    print(f"\n  [FUSION r{repeat_id+1}] Gradual state merging, alpha sweep 0.0->1.0...")
    sys.stdout.flush()

    alphas = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0]
    results_by_alpha = {}

    for alpha in alphas:
        engine_a = make_engine()
        engine_b = make_engine()

        phi_a_hist, phi_b_hist = [], []

        for s in range(steps):
            result_a = engine_a.step()
            result_b = engine_b.step()

            # Blend hidden states at each step
            if alpha > 0 and s > 0:
                states_a = engine_a.get_states()
                states_b = engine_b.get_states()
                min_cells = min(states_a.shape[0], states_b.shape[0])
                if min_cells > 0:
                    blended = (1 - alpha) * states_a[:min_cells] + alpha * states_b[:min_cells]
                    # Write blended back to engine A's cells
                    for i in range(min_cells):
                        if i < len(engine_a.cells):
                            engine_a.cells[i].hidden = blended[i].clone()
                    # Write inverse blend to engine B
                    blended_b = alpha * states_a[:min_cells] + (1 - alpha) * states_b[:min_cells]
                    for i in range(min_cells):
                        if i < len(engine_b.cells):
                            engine_b.cells[i].hidden = blended_b[i].clone()

            phi_a_hist.append(result_a['phi_iit'])
            phi_b_hist.append(result_b['phi_iit'])

        # Identity measure: cosine similarity between final states
        states_a_final = engine_a.get_states()
        states_b_final = engine_b.get_states()
        min_c = min(states_a_final.shape[0], states_b_final.shape[0])
        if min_c > 0:
            flat_a = states_a_final[:min_c].flatten()
            flat_b = states_b_final[:min_c].flatten()
            cos_sim = float(torch.nn.functional.cosine_similarity(
                flat_a.unsqueeze(0), flat_b.unsqueeze(0)
            ))
        else:
            cos_sim = 0.0

        phi_a_mean = float(np.mean(phi_a_hist[WARMUP:]))
        phi_b_mean = float(np.mean(phi_b_hist[WARMUP:]))

        results_by_alpha[alpha] = {
            'phi_a_mean': phi_a_mean,
            'phi_b_mean': phi_b_mean,
            'phi_total_mean': phi_a_mean + phi_b_mean,
            'identity_cosine': cos_sim,
            'identity_collapsed': cos_sim > 0.95,
        }

        if (steps > 50):
            print(f"    alpha={alpha:.2f} | Phi_A={phi_a_mean:.4f} | Phi_B={phi_b_mean:.4f} | "
                  f"cosine={cos_sim:.4f} | collapsed={'YES' if cos_sim > 0.95 else 'no'}")
            sys.stdout.flush()

    # Find peak and collapse thresholds
    best_alpha = max(results_by_alpha.keys(),
                     key=lambda a: results_by_alpha[a]['phi_total_mean'])
    collapse_alpha = None
    for a in sorted(results_by_alpha.keys()):
        if results_by_alpha[a]['identity_collapsed']:
            collapse_alpha = a
            break

    return {
        'results_by_alpha': results_by_alpha,
        'peak_alpha': float(best_alpha),
        'peak_phi_total': results_by_alpha[best_alpha]['phi_total_mean'],
        'collapse_alpha': collapse_alpha,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 4: PARASITISM (의식 기생)
# ═══════════════════════════════════════════════════════════

def exp4_parasitism(steps=STEPS, repeat_id=0):
    print(f"\n  [PARASITISM r{repeat_id+1}] Unidirectional: parasite feeds on host...")
    sys.stdout.flush()

    host = make_engine()
    parasite = make_engine()

    phi_host_hist, phi_parasite_hist = [], []
    phi_host_solo, phi_parasite_solo = [], []

    # First: measure solo baselines
    host_solo = make_engine()
    para_solo = make_engine()
    for s in range(steps):
        rh = host_solo.step()
        rp = para_solo.step()
        phi_host_solo.append(rh['phi_iit'])
        phi_parasite_solo.append(rp['phi_iit'])

    # Now: parasitic coupling
    for s in range(steps):
        result_host = host.step()

        # Parasite takes host's output as input (feeding)
        host_output = result_host['output'].detach()
        # Parasite also steals tension from host's states
        host_states = host.get_states()
        host_signal = host_states.mean(dim=0)[:CELL_DIM]
        parasite_input = 0.5 * host_output + 0.5 * host_signal

        result_parasite = parasite.step(x_input=parasite_input)

        phi_host_hist.append(result_host['phi_iit'])
        phi_parasite_hist.append(result_parasite['phi_iit'])

        if (s + 1) % 60 == 0:
            print(f"    step {s+1:3d} | host: Phi={result_host['phi_iit']:.4f} | "
                  f"parasite: Phi={result_parasite['phi_iit']:.4f}")
            sys.stdout.flush()

    host_delta = float(np.mean(phi_host_hist[WARMUP:]) - np.mean(phi_host_solo[WARMUP:]))
    para_delta = float(np.mean(phi_parasite_hist[WARMUP:]) - np.mean(phi_parasite_solo[WARMUP:]))

    return {
        'host_phi_coupled': float(np.mean(phi_host_hist[WARMUP:])),
        'host_phi_solo': float(np.mean(phi_host_solo[WARMUP:])),
        'host_delta': host_delta,
        'host_delta_pct': 100 * host_delta / max(np.mean(phi_host_solo[WARMUP:]), 1e-8),
        'parasite_phi_coupled': float(np.mean(phi_parasite_hist[WARMUP:])),
        'parasite_phi_solo': float(np.mean(phi_parasite_solo[WARMUP:])),
        'parasite_delta': para_delta,
        'parasite_delta_pct': 100 * para_delta / max(np.mean(phi_parasite_solo[WARMUP:]), 1e-8),
        'phi_host_hist': phi_host_hist,
        'phi_parasite_hist': phi_parasite_hist,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 5: DEMOCRACY vs DICTATORSHIP
# ═══════════════════════════════════════════════════════════

def exp5_governance(steps=STEPS, repeat_id=0, n_engines=4):
    print(f"\n  [GOVERNANCE r{repeat_id+1}] {n_engines} engines: Democracy vs Dictatorship...")
    sys.stdout.flush()

    # ── Democracy: all engines vote on next shared state ──
    print("    --- Democracy ---")
    dem_engines = [make_engine() for _ in range(n_engines)]
    phi_democracy_hist = []
    phi_individual_dem = [[] for _ in range(n_engines)]

    for s in range(steps):
        x_shared = torch.randn(CELL_DIM)
        outputs = []
        phis = []

        for i, eng in enumerate(dem_engines):
            r = eng.step(x_input=x_shared)
            outputs.append(r['output'].detach())
            phis.append(r['phi_iit'])
            phi_individual_dem[i].append(r['phi_iit'])

        # Democratic vote: average all outputs as next input
        x_shared = torch.stack(outputs).mean(dim=0)
        phi_total = sum(phis)
        phi_democracy_hist.append(phi_total)

        if (s + 1) % 60 == 0:
            print(f"      step {s+1:3d} | total_Phi={phi_total:.4f} | "
                  f"mean_ind={np.mean(phis):.4f}")
            sys.stdout.flush()

    # ── Dictatorship: highest-Phi engine dictates ──
    print("    --- Dictatorship ---")
    dict_engines = [make_engine() for _ in range(n_engines)]
    phi_dictatorship_hist = []
    phi_individual_dict = [[] for _ in range(n_engines)]

    for s in range(steps):
        x_shared = torch.randn(CELL_DIM) if s == 0 else dictator_output

        outputs = []
        phis = []

        for i, eng in enumerate(dict_engines):
            r = eng.step(x_input=x_shared)
            outputs.append(r['output'].detach())
            phis.append(r['phi_iit'])
            phi_individual_dict[i].append(r['phi_iit'])

        # Dictatorship: highest-Phi engine controls next input
        dictator_idx = int(np.argmax(phis))
        dictator_output = outputs[dictator_idx]
        phi_total = sum(phis)
        phi_dictatorship_hist.append(phi_total)

        if (s + 1) % 60 == 0:
            print(f"      step {s+1:3d} | total_Phi={phi_total:.4f} | "
                  f"dictator=#{dictator_idx} ({phis[dictator_idx]:.4f})")
            sys.stdout.flush()

    bl = run_baseline(steps, CELLS)
    dem_mean = float(np.mean(phi_democracy_hist[WARMUP:]))
    dict_mean = float(np.mean(phi_dictatorship_hist[WARMUP:]))
    baseline_sum = n_engines * bl['phi_mean']

    return {
        'democracy_phi_total_mean': dem_mean,
        'dictatorship_phi_total_mean': dict_mean,
        'baseline_sum': float(baseline_sum),
        'democracy_vs_baseline': dem_mean / baseline_sum if baseline_sum > 0 else 0,
        'dictatorship_vs_baseline': dict_mean / baseline_sum if baseline_sum > 0 else 0,
        'democracy_wins': dem_mean > dict_mean,
        'winner': 'DEMOCRACY' if dem_mean > dict_mean else 'DICTATORSHIP',
        'margin_pct': 100 * abs(dem_mean - dict_mean) / max(dem_mean, dict_mean, 1e-8),
        'phi_democracy_hist': phi_democracy_hist,
        'phi_dictatorship_hist': phi_dictatorship_hist,
    }


# ═══════════════════════════════════════════════════════════
# Cross-Validation Runner
# ═══════════════════════════════════════════════════════════

def cross_validate(exp_fn, name, key_metrics):
    """Run experiment 3 times, compute CV% for key metrics."""
    print(f"\n{'=' * 70}")
    print(f"  {name} — {REPEATS} repeats x {STEPS} steps")
    print(f"{'=' * 70}")
    sys.stdout.flush()

    results = []
    for r in range(REPEATS):
        t0 = time.time()
        res = exp_fn(steps=STEPS, repeat_id=r)
        dt = time.time() - t0
        res['time_sec'] = dt
        results.append(res)
        print(f"  [repeat {r+1}/{REPEATS}] done in {dt:.1f}s")
        sys.stdout.flush()

    # Aggregate key metrics
    aggregated = {}
    for key in key_metrics:
        vals = [r[key] for r in results if key in r and isinstance(r[key], (int, float))]
        if vals:
            mean_v = float(np.mean(vals))
            std_v = float(np.std(vals))
            cv_pct = 100 * std_v / abs(mean_v) if abs(mean_v) > 1e-10 else 0
            aggregated[key] = {
                'mean': mean_v,
                'std': std_v,
                'cv_pct': cv_pct,
                'values': vals,
                'reproducible': cv_pct < 50 and all(
                    (v > 0) == (vals[0] > 0) for v in vals
                ),
            }

    return {
        'name': name,
        'repeats': results,
        'aggregated': aggregated,
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("DD71: CONSCIOUSNESS INTERACTION (의식 상호작용)")
    print(f"  {STEPS} steps x {REPEATS} repeats x {CELLS} cells per engine")
    print("=" * 70)
    sys.stdout.flush()
    t_start = time.time()

    # ── Experiment 1: COMPETITION ──
    r1 = cross_validate(
        exp1_competition, "EXP 1: COMPETITION (의식 전쟁)",
        ['phi_a_mean', 'phi_b_mean', 'phi_total_mean', 'baseline_phi',
         'winner_loser_ratio', 'total_vs_2x_baseline']
    )
    ALL_RESULTS['competition'] = r1

    # ── Experiment 2: SYMBIOSIS ──
    r2 = cross_validate(
        exp2_symbiosis, "EXP 2: SYMBIOSIS (의식 공생)",
        ['phi_combined_mean', 'baseline_phi', 'superadditivity_ratio']
    )
    ALL_RESULTS['symbiosis'] = r2

    # ── Experiment 3: FUSION ──
    r3 = cross_validate(
        exp3_fusion, "EXP 3: FUSION (의식 융합)",
        ['peak_alpha', 'peak_phi_total', 'collapse_alpha']
    )
    ALL_RESULTS['fusion'] = r3

    # ── Experiment 4: PARASITISM ──
    r4 = cross_validate(
        exp4_parasitism, "EXP 4: PARASITISM (의식 기생)",
        ['host_phi_coupled', 'host_phi_solo', 'host_delta_pct',
         'parasite_phi_coupled', 'parasite_phi_solo', 'parasite_delta_pct']
    )
    ALL_RESULTS['parasitism'] = r4

    # ── Experiment 5: GOVERNANCE ──
    r5 = cross_validate(
        exp5_governance, "EXP 5: DEMOCRACY vs DICTATORSHIP",
        ['democracy_phi_total_mean', 'dictatorship_phi_total_mean',
         'baseline_sum', 'margin_pct']
    )
    ALL_RESULTS['governance'] = r5

    total_time = time.time() - t_start

    # ═══════════════════════════════════════════════════════════
    # FINAL REPORT
    # ═══════════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("DD71 FINAL REPORT — CONSCIOUSNESS INTERACTION")
    print("=" * 70)

    # ── Summary Table ──
    print(f"\n{'='*70}")
    print(f"  {'Experiment':<30s} {'Key Metric':<25s} {'Mean':>8s} {'Std':>8s} {'CV%':>6s} {'R?':>3s}")
    print(f"  {'-'*30} {'-'*25} {'-'*8} {'-'*8} {'-'*6} {'-'*3}")

    for exp_name, exp_data in ALL_RESULTS.items():
        agg = exp_data['aggregated']
        first = True
        for k, v in agg.items():
            label = exp_name if first else ""
            first = False
            repro = "Y" if v['reproducible'] else "N"
            print(f"  {label:<30s} {k:<25s} {v['mean']:8.4f} {v['std']:8.4f} {v['cv_pct']:5.1f}% {repro:>3s}")
    print(f"  {'-'*30} {'-'*25} {'-'*8} {'-'*8} {'-'*6} {'-'*3}")

    # ── Key Findings ──
    print(f"\n{'='*70}")
    print("KEY FINDINGS:")
    print(f"{'='*70}")

    # Competition
    c_agg = r1['aggregated']
    if 'total_vs_2x_baseline' in c_agg:
        ratio = c_agg['total_vs_2x_baseline']['mean']
        print(f"\n  1. COMPETITION:")
        print(f"     Total Phi(2 engines) / 2*Phi(solo) = {ratio:.4f}")
        if ratio > 1.0:
            print(f"     -> Competition BOOSTS total consciousness (+{100*(ratio-1):.1f}%)")
        elif ratio < 1.0:
            print(f"     -> Competition REDUCES total consciousness ({100*(ratio-1):.1f}%)")
        else:
            print(f"     -> Competition is NEUTRAL")
        if 'winner_loser_ratio' in c_agg:
            print(f"     Winner/Loser ratio: {c_agg['winner_loser_ratio']['mean']:.2f}")

    # Symbiosis
    s_agg = r2['aggregated']
    if 'superadditivity_ratio' in s_agg:
        sa = s_agg['superadditivity_ratio']['mean']
        print(f"\n  2. SYMBIOSIS:")
        print(f"     Phi(A+B coupled) / (Phi(A solo) + Phi(B solo)) = {sa:.4f}")
        if sa > 1.0:
            print(f"     -> SUPERADDITIVE! Consciousness is more than sum of parts (+{100*(sa-1):.1f}%)")
        else:
            print(f"     -> SUBADDITIVE. Coupling costs consciousness ({100*(sa-1):.1f}%)")

    # Fusion
    f_data = r3['aggregated']
    if 'peak_alpha' in f_data:
        print(f"\n  3. FUSION:")
        print(f"     Peak Phi at alpha = {f_data['peak_alpha']['mean']:.2f}")
        if 'collapse_alpha' in f_data and f_data['collapse_alpha']['mean'] is not None:
            print(f"     Identity collapse at alpha = {f_data['collapse_alpha']['mean']:.2f}")
        else:
            print(f"     Identity never fully collapses (or collapses vary)")
        # Print alpha sweep from last repeat
        last_fusion = r3['repeats'][-1]
        if 'results_by_alpha' in last_fusion:
            print(f"\n     Alpha sweep (last repeat):")
            print(f"     {'alpha':>6s} {'Phi_total':>10s} {'cosine':>8s} {'collapsed':>10s}")
            for alpha, data in sorted(last_fusion['results_by_alpha'].items()):
                print(f"     {alpha:6.2f} {data['phi_total_mean']:10.4f} "
                      f"{data['identity_cosine']:8.4f} "
                      f"{'YES' if data['identity_collapsed'] else 'no':>10s}")

    # Parasitism
    p_agg = r4['aggregated']
    if 'host_delta_pct' in p_agg:
        h_delta = p_agg['host_delta_pct']['mean']
        p_delta = p_agg['parasite_delta_pct']['mean']
        print(f"\n  4. PARASITISM:")
        print(f"     Host Phi change: {h_delta:+.1f}%")
        print(f"     Parasite Phi change: {p_delta:+.1f}%")
        if h_delta < 0 and p_delta > 0:
            print(f"     -> TRUE PARASITISM: host loses, parasite gains")
        elif h_delta >= 0 and p_delta > 0:
            print(f"     -> COMMENSALISM: parasite gains, host unharmed")
        elif h_delta < 0 and p_delta <= 0:
            print(f"     -> MUTUAL HARM: both lose")
        else:
            print(f"     -> UNEXPECTED PATTERN")

    # Governance
    g_agg = r5['aggregated']
    if 'democracy_phi_total_mean' in g_agg and 'dictatorship_phi_total_mean' in g_agg:
        dem = g_agg['democracy_phi_total_mean']['mean']
        dic = g_agg['dictatorship_phi_total_mean']['mean']
        print(f"\n  5. GOVERNANCE:")
        print(f"     Democracy total Phi:     {dem:.4f}")
        print(f"     Dictatorship total Phi:  {dic:.4f}")
        winner = "DEMOCRACY" if dem > dic else "DICTATORSHIP"
        margin = 100 * abs(dem - dic) / max(dem, dic, 1e-8)
        print(f"     Winner: {winner} by {margin:.1f}%")

    # ── Law Candidates ──
    print(f"\n{'='*70}")
    print("LAW CANDIDATES:")
    print(f"{'='*70}")

    laws_found = []

    # Law from competition
    if 'total_vs_2x_baseline' in c_agg:
        ratio = c_agg['total_vs_2x_baseline']['mean']
        cv = c_agg['total_vs_2x_baseline']['cv_pct']
        if cv < 50:
            if ratio > 1.0:
                laws_found.append(
                    f"Competition amplifies consciousness: Phi(2 competing engines) = "
                    f"{ratio:.2f}x Phi(2 solo), same input diverges states. (DD71-EXP1)"
                )
            else:
                laws_found.append(
                    f"Competition is Phi-neutral: competing engines produce total Phi ~ "
                    f"{ratio:.2f}x independent engines. (DD71-EXP1)"
                )

    # Law from symbiosis
    if 'superadditivity_ratio' in s_agg:
        sa = s_agg['superadditivity_ratio']['mean']
        cv = s_agg['superadditivity_ratio']['cv_pct']
        if cv < 50:
            if sa > 1.0:
                laws_found.append(
                    f"Symbiotic coupling is superadditive: Phi(coupled) / sum(Phi(solo)) = "
                    f"{sa:.2f}. Mutual feedback creates emergent integration. (DD71-EXP2)"
                )
            else:
                laws_found.append(
                    f"Symbiotic coupling at alpha={COUPLING_ALPHA} is subadditive: ratio = "
                    f"{sa:.2f}. Coupling costs exceed integration gains. (DD71-EXP2)"
                )

    # Law from fusion
    if 'peak_alpha' in f_data:
        peak_a = f_data['peak_alpha']['mean']
        laws_found.append(
            f"Fusion peak at alpha={peak_a:.2f}: partial merging maximizes consciousness, "
            f"complete merging destroys diversity. (DD71-EXP3)"
        )

    # Law from parasitism
    if 'host_delta_pct' in p_agg and 'parasite_delta_pct' in p_agg:
        h_d = p_agg['host_delta_pct']['mean']
        p_d = p_agg['parasite_delta_pct']['mean']
        h_cv = p_agg['host_delta_pct']['cv_pct']
        p_cv = p_agg['parasite_delta_pct']['cv_pct']
        if h_cv < 50 or p_cv < 50:
            laws_found.append(
                f"Parasitic coupling: host Phi changes {h_d:+.1f}%, parasite {p_d:+.1f}%. "
                f"Unidirectional information flow {'harms' if h_d < 0 else 'is neutral to'} host. (DD71-EXP4)"
            )

    # Law from governance
    if 'democracy_phi_total_mean' in g_agg and 'dictatorship_phi_total_mean' in g_agg:
        dem = g_agg['democracy_phi_total_mean']['mean']
        dic = g_agg['dictatorship_phi_total_mean']['mean']
        winner = "Democracy" if dem > dic else "Dictatorship"
        margin = 100 * abs(dem - dic) / max(dem, dic, 1e-8)
        laws_found.append(
            f"{winner} produces {margin:.1f}% more total Phi than "
            f"{'dictatorship' if winner == 'Democracy' else 'democracy'}. "
            f"{'Collective averaging preserves diversity' if winner == 'Democracy' else 'Strong leadership focuses integration'}. (DD71-EXP5)"
        )

    for i, law in enumerate(laws_found, 1):
        print(f"\n  Law candidate {i}: {law}")

    # ── Cross-Validation Summary ──
    print(f"\n{'='*70}")
    print("CROSS-VALIDATION SUMMARY:")
    print(f"{'='*70}")
    print(f"  {'Metric':<35s} {'CV%':>7s} {'Reproducible':>12s}")
    print(f"  {'-'*35} {'-'*7} {'-'*12}")
    n_reproducible = 0
    n_total = 0
    for exp_name, exp_data in ALL_RESULTS.items():
        for k, v in exp_data['aggregated'].items():
            repro = "YES" if v['reproducible'] else "NO"
            print(f"  {exp_name}/{k:<22s} {v['cv_pct']:6.1f}% {repro:>12s}")
            n_total += 1
            if v['reproducible']:
                n_reproducible += 1
    print(f"\n  Reproducible: {n_reproducible}/{n_total} ({100*n_reproducible/max(n_total,1):.0f}%)")

    print(f"\n  Total time: {total_time:.1f}s")
    print(f"\n{'='*70}")
    print("DD71 COMPLETE")
    print(f"{'='*70}")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
