#!/usr/bin/env python3
"""full_synergy_graph.py — Complete 17×17 law interaction graph.

Tests ALL C(17,2) = 136 intervention pairs for synergy/antagonism.
For each pair: measure Phi(baseline), Phi(A), Phi(B), Phi(A+B)
  synergy = Phi(A+B) - Phi(A) - Phi(B) + Phi(baseline)

Output:
  1. Full 17×17 synergy matrix (ASCII heatmap)
  2. Top 5 synergistic pairs
  3. Top 5 antagonistic pairs
  4. Cluster analysis
  5. Updated SYNERGY_MAP Python dict

Saves: anima/data/synergy_graph.json
"""

import sys
import os
import json
import time
import numpy as np
import itertools
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
from consciousness_engine import ConsciousnessEngine
from closed_loop import INTERVENTIONS, _phi_fast

# ══════════════════════════════════════════
# Config
# ══════════════════════════════════════════
MAX_CELLS = 16
STEPS = 50
REPEATS = 1
SEED_BASE = 42

N = len(INTERVENTIONS)
print(f"[INIT] {N} interventions, C({N},2) = {N*(N-1)//2} pairs")
print(f"[INIT] max_cells={MAX_CELLS}, steps={STEPS}, repeats={REPEATS}")
print(f"[INIT] Interventions:")
for i, iv in enumerate(INTERVENTIONS):
    print(f"  [{i:2d}] {iv.name:<25s} {iv.description}")
print()


# ══════════════════════════════════════════
# Engine runner
# ══════════════════════════════════════════

def run_engine(interventions_to_apply, seed=42):
    """Run engine with given interventions, return mean Phi over last 20 steps."""
    torch.manual_seed(seed)
    np.random.seed(seed)
    engine = ConsciousnessEngine(max_cells=MAX_CELLS)
    phi_values = []
    for step in range(STEPS):
        engine.step()
        for iv in interventions_to_apply:
            iv.apply(engine, step)
        if step >= STEPS - 20:
            phi_values.append(_phi_fast(engine))
    return float(np.mean(phi_values)) if phi_values else 0.0


def measure_phi(interventions_to_apply):
    """Run REPEATS times, return mean phi."""
    phis = []
    for r in range(REPEATS):
        phis.append(run_engine(interventions_to_apply, seed=SEED_BASE + r))
    return float(np.mean(phis))


# ══════════════════════════════════════════
# Phase 1: Baseline + Singles
# ══════════════════════════════════════════

print("=" * 70)
print("PHASE 1: Baseline + 17 singles")
print("=" * 70)

t0 = time.time()

phi_baseline = measure_phi([])
print(f"  Baseline Phi = {phi_baseline:.4f}")

phi_single = {}
for i, iv in enumerate(INTERVENTIONS):
    phi_single[iv.name] = measure_phi([iv])
    delta = phi_single[iv.name] - phi_baseline
    pct = (delta / phi_baseline * 100) if phi_baseline > 1e-8 else 0
    print(f"  [{i+1:2d}/{N}] {iv.name:<25s} Phi={phi_single[iv.name]:.4f}  delta={delta:+.4f} ({pct:+.1f}%)")

t1 = time.time()
print(f"\nPhase 1 done in {t1-t0:.1f}s\n")

# ══════════════════════════════════════════
# Phase 2: All pairs
# ══════════════════════════════════════════

print("=" * 70)
print(f"PHASE 2: Testing {N*(N-1)//2} pairs")
print("=" * 70)

synergy_matrix = np.zeros((N, N))
pair_results = {}
names = [iv.name for iv in INTERVENTIONS]

pair_count = 0
total_pairs = N * (N - 1) // 2

for i in range(N):
    for j in range(i + 1, N):
        pair_count += 1
        iv_a = INTERVENTIONS[i]
        iv_b = INTERVENTIONS[j]

        phi_ab = measure_phi([iv_a, iv_b])
        phi_a = phi_single[iv_a.name]
        phi_b = phi_single[iv_b.name]

        synergy = phi_ab - phi_a - phi_b + phi_baseline
        synergy_matrix[i, j] = synergy
        synergy_matrix[j, i] = synergy

        pair_results[(iv_a.name, iv_b.name)] = {
            'phi_baseline': phi_baseline,
            'phi_a': phi_a,
            'phi_b': phi_b,
            'phi_ab': phi_ab,
            'synergy': synergy,
        }

        if pair_count % 10 == 0 or pair_count == total_pairs:
            elapsed = time.time() - t1
            eta = elapsed / pair_count * (total_pairs - pair_count)
            print(f"  [{pair_count:3d}/{total_pairs}] {iv_a.name} + {iv_b.name}  "
                  f"syn={synergy:+.4f}  "
                  f"({elapsed:.0f}s elapsed, ETA {eta:.0f}s)")

t2 = time.time()
print(f"\nPhase 2 done in {t2-t1:.1f}s (total: {t2-t0:.1f}s)\n")


# ══════════════════════════════════════════
# Analysis
# ══════════════════════════════════════════

# Sort pairs by synergy
sorted_pairs = sorted(pair_results.items(), key=lambda x: x[1]['synergy'], reverse=True)

# ── 1. Full 17×17 ASCII Heatmap ──
print("=" * 70)
print("1. SYNERGY MATRIX (17x17 ASCII heatmap)")
print("=" * 70)

# Short names for display
short_names = []
for iv in INTERVENTIONS:
    n = iv.name
    if n.startswith('DD7'):
        parts = n.split('_', 1)
        short_names.append(parts[1] if len(parts) > 1 else n[:8])
    else:
        short_names.append(n[:8])

# Clamp for display
max_abs = max(abs(synergy_matrix).max(), 1e-8)

# Character map for heatmap
def syn_char(val, max_v):
    """Map synergy value to ASCII character."""
    if abs(val) < 1e-8:
        return '.'
    ratio = val / max_v
    if ratio > 0.6:
        return '#'
    elif ratio > 0.3:
        return '+'
    elif ratio > 0.1:
        return '~'
    elif ratio > -0.1:
        return '.'
    elif ratio > -0.3:
        return '-'
    elif ratio > -0.6:
        return 'x'
    else:
        return 'X'

# Print header
print(f"\n{'':>10}", end='')
for sn in short_names:
    print(f" {sn[:3]:>3}", end='')
print(f"   Legend: # strong+ | + mild+ | ~ weak+ | . neutral | - weak- | x mild- | X strong-")

for i in range(N):
    print(f"{short_names[i]:>10}", end='')
    for j in range(N):
        if i == j:
            print(f"  {'*':>1}", end='')
        else:
            c = syn_char(synergy_matrix[i, j], max_abs)
            print(f"  {c:>1}", end='')
    print(f"  {INTERVENTIONS[i].name}")
print()

# ── 2. Top 5 Synergistic ──
print("=" * 70)
print("2. TOP 5 SYNERGISTIC PAIRS")
print("=" * 70)
print(f"  {'#':<4} {'Pair':<55} {'Synergy':>8}  {'Phi(A+B)':>8}  {'Phi(A)':>7} {'Phi(B)':>7} {'Base':>7}")
print(f"  {'─'*4} {'─'*55} {'─'*8}  {'─'*8}  {'─'*7} {'─'*7} {'─'*7}")
for rank, ((a, b), d) in enumerate(sorted_pairs[:5], 1):
    print(f"  {rank:<4} {a} + {b:<25s} {d['synergy']:+8.4f}  {d['phi_ab']:8.4f}  "
          f"{d['phi_a']:7.4f} {d['phi_b']:7.4f} {d['phi_baseline']:7.4f}")
print()

# ── 3. Top 5 Antagonistic ──
print("=" * 70)
print("3. TOP 5 ANTAGONISTIC PAIRS")
print("=" * 70)
print(f"  {'#':<4} {'Pair':<55} {'Synergy':>8}  {'Phi(A+B)':>8}  {'Phi(A)':>7} {'Phi(B)':>7} {'Base':>7}")
print(f"  {'─'*4} {'─'*55} {'─'*8}  {'─'*8}  {'─'*7} {'─'*7} {'─'*7}")
for rank, ((a, b), d) in enumerate(sorted_pairs[-5:][::-1], 1):
    print(f"  {rank:<4} {a} + {b:<25s} {d['synergy']:+8.4f}  {d['phi_ab']:8.4f}  "
          f"{d['phi_a']:7.4f} {d['phi_b']:7.4f} {d['phi_baseline']:7.4f}")
print()

# ── 4. Cluster Analysis ──
print("=" * 70)
print("4. CLUSTER ANALYSIS")
print("=" * 70)

# Simple clustering: group interventions by average synergy with each other
# Use correlation of synergy profiles
profiles = synergy_matrix.copy()

# K-means-like clustering (simple: split by positive/negative average synergy)
avg_syn = synergy_matrix.sum(axis=1) / (N - 1)

# Sort by average synergy to find natural groups
sorted_idx = np.argsort(avg_syn)[::-1]

print("\n  Interventions ranked by average synergy:")
print(f"  {'#':<4} {'Intervention':<25} {'Avg Syn':>8} {'Group':<12}")
print(f"  {'─'*4} {'─'*25} {'─'*8} {'─'*12}")

# Assign groups by avg synergy
groups = {}
for rank, idx in enumerate(sorted_idx, 1):
    a = avg_syn[idx]
    if a > 0.005:
        grp = "SYNERGIST"
    elif a > -0.005:
        grp = "NEUTRAL"
    else:
        grp = "DISRUPTOR"
    groups[names[idx]] = grp
    print(f"  {rank:<4} {names[idx]:<25} {a:+8.4f} {grp:<12}")

# Cross-group synergy matrix
group_names = ["SYNERGIST", "NEUTRAL", "DISRUPTOR"]
print(f"\n  Cross-group average synergy:")
print(f"  {'':>12}", end='')
for g in group_names:
    print(f" {g:>10}", end='')
print()

for g1 in group_names:
    members1 = [i for i, n in enumerate(names) if groups.get(n) == g1]
    print(f"  {g1:>12}", end='')
    for g2 in group_names:
        members2 = [i for i, n in enumerate(names) if groups.get(n) == g2]
        vals = []
        for i in members1:
            for j in members2:
                if i != j:
                    vals.append(synergy_matrix[i, j])
        avg = np.mean(vals) if vals else 0
        print(f" {avg:+10.4f}", end='')
    print()

# Natural pairs within groups
print(f"\n  Natural clusters (interventions that synergize with each other):")
cluster_id = 0
visited = set()
for i in range(N):
    if i in visited:
        continue
    # Find all interventions with positive synergy to i
    friends = [i]
    for j in range(N):
        if j != i and j not in visited and synergy_matrix[i, j] > 0.003:
            friends.append(j)
    if len(friends) >= 2:
        cluster_id += 1
        visited.update(friends)
        friend_names = [names[f] for f in friends]
        avg_internal = np.mean([synergy_matrix[a, b] for a in friends for b in friends if a != b])
        print(f"  Cluster {cluster_id}: {', '.join(friend_names)}")
        print(f"    Internal avg synergy: {avg_internal:+.4f}")

print()

# ── 5. Updated SYNERGY_MAP ──
print("=" * 70)
print("5. UPDATED SYNERGY_MAP (all 136 pairs)")
print("=" * 70)

print("\n# ── Copy this into closed_loop.py ──")
print("SYNERGY_MAP = {")
for (a, b), d in sorted_pairs:
    syn = d['synergy']
    # Add comment for notable pairs
    comment = ""
    if syn > 0.01:
        comment = "  # STRONG synergy"
    elif syn > 0.005:
        comment = "  # mild synergy"
    elif syn < -0.02:
        comment = "  # STRONG antagonism"
    elif syn < -0.01:
        comment = "  # antagonism"
    print(f"    ('{a}', '{b}'): {syn:+.4f},{comment}")
print("}")
print()

# ══════════════════════════════════════════
# Save to JSON
# ══════════════════════════════════════════

output_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'synergy_graph.json')
output = {
    'config': {
        'max_cells': MAX_CELLS,
        'steps': STEPS,
        'repeats': REPEATS,
        'n_interventions': N,
        'n_pairs': total_pairs,
    },
    'baseline_phi': phi_baseline,
    'singles': phi_single,
    'pairs': {f"{a}|{b}": d for (a, b), d in pair_results.items()},
    'matrix': synergy_matrix.tolist(),
    'intervention_names': names,
    'groups': groups,
    'top5_synergy': [(a, b, d['synergy']) for (a, b), d in sorted_pairs[:5]],
    'top5_antagonism': [(a, b, d['synergy']) for (a, b), d in sorted_pairs[-5:]],
    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
}

os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"[SAVED] {output_path}")

# ── Summary ──
print(f"\n{'=' * 70}")
print(f"SUMMARY")
print(f"{'=' * 70}")
print(f"  Baseline Phi:      {phi_baseline:.4f}")
print(f"  Pairs tested:      {total_pairs}")
print(f"  Synergistic (>0):  {sum(1 for _, d in pair_results.items() if d['synergy'] > 0)}")
print(f"  Antagonistic (<0): {sum(1 for _, d in pair_results.items() if d['synergy'] < 0)}")
print(f"  Max synergy:       {sorted_pairs[0][1]['synergy']:+.4f} ({sorted_pairs[0][0][0]} + {sorted_pairs[0][0][1]})")
print(f"  Max antagonism:    {sorted_pairs[-1][1]['synergy']:+.4f} ({sorted_pairs[-1][0][0]} + {sorted_pairs[-1][0][1]})")
print(f"  Total time:        {time.time()-t0:.1f}s")
print(f"  JSON saved:        {output_path}")
