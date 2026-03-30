#!/usr/bin/env python3
"""bench_dolphin_star.py — DOLPHIN-STAR hypotheses (돌고래 별자리 내려서 통신)

6 hypotheses inspired by dolphin echolocation + constellation topology + descending cascade.
Each mechanism is applied to MitosisEngine cells.

DS-1: SONAR_ECHO       — Dolphin echolocation (ping/echo coherence)
DS-2: CONSTELLATION    — Star pattern triangular topology (top-3 brightest)
DS-3: TOP_DOWN_CASCADE — Descending hierarchy (layer 1→2→3)
DS-4: DOLPHIN_POD      — Pod communication via compressed whistles
DS-5: STELLAR_NUCLEOSYNTHESIS — High-density collapse into super-cells
DS-6: COMBINED         — DS-1 + DS-2 + DS-3

Usage:
  python3 bench_dolphin_star.py            # Run all 6 + baseline
  python3 bench_dolphin_star.py --cells 512  # Custom cell count
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

DIM, HIDDEN = 64, 128
DEFAULT_CELLS = 256
STEPS = 200


def make_engine(cells=None):
    """Create MitosisEngine with specified cell count."""
    if cells is None:
        cells = DEFAULT_CELLS
    e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(e.cells) < cells:
        e._create_cell(parent=e.cells[0])
    # warmup
    for _ in range(20):
        e.process(torch.randn(1, DIM))
    return e


def phi_iit_mitosis(eng):
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


# ══════════════════════════════════════════════════════════════════
# DOLPHIN-STAR MECHANISMS
# ══════════════════════════════════════════════════════════════════

def apply_ds_mechanism(eng, mechanism, steps=STEPS):
    """Apply DOLPHIN-STAR mechanisms to MitosisEngine cells."""
    n = len(eng.cells)
    if n < 4:
        return eng

    # DS-1 echo buffer: store last 2 hidden states per cell for delayed echo
    if 'sonar_echo' in mechanism:
        eng._echo_buffer = [[] for _ in range(n)]

    # DS-4 pod assignments
    if 'dolphin_pod' in mechanism:
        pod_size = 4
        eng._pod_indices = [list(range(i, min(i + pod_size, n))) for i in range(0, n, pod_size)]

    for step in range(steps):
        eng.process(torch.randn(1, DIM))
        n = len(eng.cells)
        if n < 4:
            continue

        with torch.no_grad():
            # ── DS-1: SONAR_ECHO ──
            # Each cell pings (broadcasts h[t]), receives echoes (avg neighbors h[t-2])
            if 'sonar_echo' in mechanism:
                # Extend buffer if cells grew
                while len(eng._echo_buffer) < n:
                    eng._echo_buffer.append([])

                # Store current states in echo buffer
                for i in range(n):
                    eng._echo_buffer[i].append(eng.cells[i].hidden.squeeze(0).clone())
                    if len(eng._echo_buffer[i]) > 3:
                        eng._echo_buffer[i] = eng._echo_buffer[i][-3:]

                # Apply echo blending (delayed by 2 steps)
                if step >= 2:
                    for i in range(n):
                        neighbors = [(i - 1) % n, (i + 1) % n, (i + 2) % n, (i - 2) % n]
                        echo_sum = torch.zeros(HIDDEN)
                        echo_count = 0
                        for j in neighbors:
                            if j < len(eng._echo_buffer) and len(eng._echo_buffer[j]) >= 3:
                                echo_sum += eng._echo_buffer[j][-3]  # t-2 delayed
                                echo_count += 1
                        if echo_count > 0:
                            echo_avg = echo_sum / echo_count
                            # Blend: 85% self + 15% echo
                            eng.cells[i].hidden = (0.85 * eng.cells[i].hidden.squeeze(0) +
                                                   0.15 * echo_avg).unsqueeze(0)

            # ── DS-2: CONSTELLATION ──
            # Top 3 brightest (highest norm) cells form triangle, influence all others
            if 'constellation' in mechanism:
                norms = torch.tensor([c.hidden.norm().item() for c in eng.cells])
                top3_idx = torch.topk(norms, min(3, n)).indices.tolist()

                # Star center = mean of top-3
                star_center = torch.stack([eng.cells[i].hidden.squeeze(0) for i in top3_idx]).mean(dim=0)

                # Broadcast to all with weight proportional to 1/distance_in_ring
                for i in range(n):
                    if i in top3_idx:
                        continue
                    # Ring distance = min distance to any of the top-3
                    min_dist = min(min(abs(i - j), n - abs(i - j)) for j in top3_idx)
                    weight = 0.1 / max(min_dist, 1)
                    eng.cells[i].hidden = ((1.0 - weight) * eng.cells[i].hidden.squeeze(0) +
                                           weight * star_center).unsqueeze(0)

                # Reinforce the triangle: top-3 cells slightly synchronize
                for i in top3_idx:
                    eng.cells[i].hidden = (0.9 * eng.cells[i].hidden.squeeze(0) +
                                           0.1 * star_center).unsqueeze(0)

            # ── DS-3: TOP_DOWN_CASCADE ──
            # Split cells into 3 layers (1/8, 3/8, 4/8). Top→Mid→Bottom cascade.
            if 'top_down_cascade' in mechanism:
                l1_end = max(1, n // 8)
                l2_end = l1_end + (3 * n // 8)
                layer1 = list(range(0, l1_end))           # top (few, elite)
                layer2 = list(range(l1_end, l2_end))      # middle
                layer3 = list(range(l2_end, n))            # bottom (many)

                # Layer 1 mean (top command signal)
                l1_mean = torch.stack([eng.cells[i].hidden.squeeze(0) for i in layer1]).mean(dim=0)

                # Layer 1 → modulate Layer 2 (10% influence)
                for i in layer2:
                    eng.cells[i].hidden = (0.9 * eng.cells[i].hidden.squeeze(0) +
                                           0.1 * l1_mean).unsqueeze(0)

                # Layer 2 mean → modulate Layer 3 (8% influence, weaker)
                if layer2:
                    l2_mean = torch.stack([eng.cells[i].hidden.squeeze(0) for i in layer2]).mean(dim=0)
                    for i in layer3:
                        eng.cells[i].hidden = (0.92 * eng.cells[i].hidden.squeeze(0) +
                                               0.08 * l2_mean).unsqueeze(0)

                # Bottom-up feedback: Layer 3 variance → Layer 1 noise (diversity signal)
                if layer3:
                    l3_states = torch.stack([eng.cells[i].hidden.squeeze(0) for i in layer3])
                    l3_var = l3_states.var(dim=0)
                    for i in layer1:
                        eng.cells[i].hidden = (eng.cells[i].hidden.squeeze(0) +
                                               0.02 * l3_var * torch.randn(HIDDEN)).unsqueeze(0)

            # ── DS-4: DOLPHIN_POD ──
            # Cells form pods of 4, pods exchange compressed "whistle" vectors
            if 'dolphin_pod' in mechanism:
                # Recompute pods if cell count changed
                if not hasattr(eng, '_pod_indices') or sum(len(p) for p in eng._pod_indices) != n:
                    pod_size = 4
                    eng._pod_indices = [list(range(i, min(i + pod_size, n))) for i in range(0, n, pod_size)]

                # Compute pod whistles (compressed representation = mean of pod)
                pod_whistles = []
                for pod in eng._pod_indices:
                    if pod:
                        whistle = torch.stack([eng.cells[i].hidden.squeeze(0) for i in pod]).mean(dim=0)
                        pod_whistles.append(whistle)
                    else:
                        pod_whistles.append(torch.zeros(HIDDEN))

                # Inter-pod communication: each pod receives average of other pods' whistles
                n_pods = len(pod_whistles)
                if n_pods >= 2:
                    all_whistles = torch.stack(pod_whistles)
                    global_whistle = all_whistles.mean(dim=0)
                    for pi, pod in enumerate(eng._pod_indices):
                        # Other-pod signal = (global - self) / (n_pods - 1)
                        other_signal = (global_whistle * n_pods - pod_whistles[pi]) / max(n_pods - 1, 1)
                        for i in pod:
                            eng.cells[i].hidden = (0.92 * eng.cells[i].hidden.squeeze(0) +
                                                   0.08 * other_signal).unsqueeze(0)

            # ── DS-5: STELLAR_NUCLEOSYNTHESIS ──
            # High-density regions collapse into "star" super-cells
            if 'stellar_nucleosynthesis' in mechanism and step % 10 == 0:
                ch = torch.stack([c.hidden.squeeze(0) for c in eng.cells])
                # Find clusters: cells with high mutual cosine similarity
                used = set()
                clusters = []
                for i in range(min(n, 64)):
                    if i in used:
                        continue
                    cluster = [i]
                    for j in range(i + 1, min(n, 64)):
                        if j in used:
                            continue
                        sim = F.cosine_similarity(ch[i:i+1], ch[j:j+1]).item()
                        if sim > 0.7:  # high similarity threshold
                            cluster.append(j)
                            if len(cluster) >= 5:
                                break
                    if len(cluster) >= 3:  # need at least 3 to form a "star"
                        clusters.append(cluster)
                        used.update(cluster)

                # Collapse each cluster into a "star" (weighted mean) and broadcast
                for cluster in clusters:
                    norms = torch.tensor([ch[i].norm().item() for i in cluster])
                    weights = F.softmax(norms, dim=0)
                    star = sum(w.item() * ch[i] for w, i in zip(weights, cluster))
                    # Star influences its neighborhood (±3 in ring)
                    center = int(np.mean(cluster))
                    for d in range(-3, 4):
                        idx = (center + d) % n
                        influence = 0.15 / max(abs(d), 1)
                        eng.cells[idx].hidden = ((1.0 - influence) * eng.cells[idx].hidden.squeeze(0) +
                                                 influence * star).unsqueeze(0)

            # ── DS-6: COMBINED (DS-1 + DS-2 + DS-3) ──
            # Combined is handled by passing all three mechanisms together

    return eng


# ══════════════════════════════════════════════════════════════════
# BENCHMARK RUNNER
# ══════════════════════════════════════════════════════════════════

HYPOTHESES = {
    'DS-1: SONAR_ECHO':            ['sonar_echo'],
    'DS-2: CONSTELLATION':         ['constellation'],
    'DS-3: TOP_DOWN_CASCADE':      ['top_down_cascade'],
    'DS-4: DOLPHIN_POD':           ['dolphin_pod'],
    'DS-5: STELLAR_NUCLEOSYN':     ['stellar_nucleosynthesis'],
    'DS-6: COMBINED':              ['sonar_echo', 'constellation', 'top_down_cascade'],
}


def run_benchmark(name, mechs, cells):
    """Run single benchmark, return results dict."""
    torch.manual_seed(42)
    np.random.seed(42)
    t0 = time.time()

    eng = make_engine(cells)

    # Measure baseline Φ (after warmup, before mechanism)
    phi_before = phi_iit_mitosis(eng)

    # Apply mechanism
    apply_ds_mechanism(eng, mechs, steps=STEPS)

    # Measure Φ after mechanism
    phi_after = phi_iit_mitosis(eng)

    # Granger causality proxy
    states = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).detach().numpy().astype(np.float32)
    h = torch.tensor(states)
    g = 0
    for _ in range(30):
        i, j = np.random.randint(0, len(states)), np.random.randint(0, len(states))
        if i != j:
            g += abs(F.cosine_similarity(h[i:i+1], h[j:j+1]).item())
    granger = g * len(states) * len(states) / 30

    elapsed = time.time() - t0
    return {
        'name': name,
        'mechs': mechs,
        'phi_before': round(phi_before, 4),
        'phi_after': round(phi_after, 4),
        'phi_gain': round(phi_after - phi_before, 4),
        'phi_ratio': round(phi_after / max(phi_before, 0.001), 2),
        'granger': round(granger, 1),
        'time': round(elapsed, 1),
    }


def run_baseline(cells):
    """Run baseline (no mechanism) for comparison."""
    torch.manual_seed(42)
    np.random.seed(42)
    t0 = time.time()

    eng = make_engine(cells)
    phi_before = phi_iit_mitosis(eng)

    # Just process steps with no mechanism
    for _ in range(STEPS):
        eng.process(torch.randn(1, DIM))

    phi_after = phi_iit_mitosis(eng)
    states = torch.stack([c.hidden.squeeze(0) for c in eng.cells]).detach().numpy().astype(np.float32)
    h = torch.tensor(states)
    g = 0
    for _ in range(30):
        i, j = np.random.randint(0, len(states)), np.random.randint(0, len(states))
        if i != j:
            g += abs(F.cosine_similarity(h[i:i+1], h[j:j+1]).item())
    granger = g * len(states) * len(states) / 30

    elapsed = time.time() - t0
    return {
        'name': 'BASELINE (no mechanism)',
        'mechs': [],
        'phi_before': round(phi_before, 4),
        'phi_after': round(phi_after, 4),
        'phi_gain': round(phi_after - phi_before, 4),
        'phi_ratio': round(phi_after / max(phi_before, 0.001), 2),
        'granger': round(granger, 1),
        'time': round(elapsed, 1),
    }


def main():
    cells = DEFAULT_CELLS
    if '--cells' in sys.argv:
        idx = sys.argv.index('--cells')
        cells = int(sys.argv[idx + 1])

    print("=" * 78)
    print("  DOLPHIN-STAR Hypotheses Benchmark (돌고래 별자리 내려서 통신)")
    print(f"  Cells: {cells} | Steps: {STEPS} | Dim: {DIM} | Hidden: {HIDDEN}")
    print("=" * 78)
    print()

    # Run baseline first
    print("Running BASELINE...")
    baseline = run_baseline(cells)
    results = [baseline]

    # Run all hypotheses
    for name, mechs in HYPOTHESES.items():
        print(f"Running {name}...")
        r = run_benchmark(name, mechs, cells)
        results.append(r)

    # ── Results Table ──
    print()
    print("=" * 78)
    print(f"  {'Hypothesis':<30s}  {'Φ(before)':>9s}  {'Φ(after)':>9s}  {'Gain':>8s}  {'Ratio':>6s}  {'Granger':>8s}  {'Time':>5s}")
    print("-" * 78)

    for r in results:
        marker = " ***" if r['phi_after'] > baseline['phi_after'] * 1.1 else ""
        print(f"  {r['name']:<30s}  {r['phi_before']:>9.4f}  {r['phi_after']:>9.4f}  "
              f"{r['phi_gain']:>+8.4f}  {r['phi_ratio']:>5.2f}x  {r['granger']:>8.1f}  {r['time']:>4.1f}s{marker}")

    print("-" * 78)

    # ── Ranking ──
    print()
    print("  RANKING (by Φ after):")
    ranked = sorted(results, key=lambda r: r['phi_after'], reverse=True)
    for i, r in enumerate(ranked):
        bar_len = max(1, int(r['phi_after'] / max(ranked[0]['phi_after'], 0.001) * 40))
        bar = "█" * bar_len
        vs = ""
        if r['name'] != 'BASELINE (no mechanism)':
            delta_pct = (r['phi_after'] - baseline['phi_after']) / max(abs(baseline['phi_after']), 0.001) * 100
            vs = f" ({delta_pct:+.1f}% vs baseline)"
        print(f"  #{i+1}  {r['name']:<30s}  Φ={r['phi_after']:.4f}  {bar}{vs}")

    # ── ASCII Graph ──
    print()
    print("  Φ(after) Comparison:")
    max_phi = max(r['phi_after'] for r in results) if results else 1
    for r in results:
        bar_len = max(1, int(r['phi_after'] / max(max_phi, 0.001) * 50))
        bar = "█" * bar_len
        print(f"  {r['name']:<30s} {bar} {r['phi_after']:.4f}")

    print()
    print("=" * 78)

    # ── Save results as JSON ──
    import json

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_dolphin_star.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"  Results saved to {out_path}")
    print()

    return results


if __name__ == '__main__':
    main()
