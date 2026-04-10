#!/usr/bin/env python3
"""experiment_personality.py — Does consciousness develop personality?

Fundamental question: Do identical structures develop distinct personalities?

Tests:
  1. Twin Divergence:      10 identical engines → same input → how different?
  2. Nature vs Nurture:    same seed, different inputs → what shapes personality?
  3. Personality Stability: one engine 1000 steps → does personality stabilize?
  4. Personality Dimensions: 20 engines → 5D personality space → clusters?
  5. Personality Under Stress: established engines + noise → diverse responses?
  6. Personality Transfer: fingerprint A → inject B → similarity?

Each test: 3x cross-validation.
"""

import os
import sys
import time
import math
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def cosine_sim(a, b):
    """Cosine similarity between two 1D tensors/arrays."""
    a = np.array(a).flatten().astype(float)
    b = np.array(b).flatten().astype(float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def gini_coefficient(values):
    """Gini coefficient (0=equal, 1=one dominates)."""
    v = np.array(sorted(values), dtype=float)
    n = len(v)
    if n == 0 or v.sum() < 1e-12:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * v) - (n + 1) * np.sum(v)) / (n * np.sum(v)))


def state_entropy(states_np):
    """Entropy of cell state distribution (binned)."""
    flat = states_np.flatten()
    hist, _ = np.histogram(flat, bins=32, density=True)
    hist = hist[hist > 0]
    width = (flat.max() - flat.min()) / 32 if flat.max() != flat.min() else 1.0
    probs = hist * width
    probs = probs / (probs.sum() + 1e-12)
    return float(-np.sum(probs * np.log(probs + 1e-12)))


def output_diversity(outputs):
    """Mean pairwise cosine distance of recent outputs."""
    if len(outputs) < 2:
        return 0.0
    sims = []
    for i in range(len(outputs)):
        for j in range(i + 1, len(outputs)):
            sims.append(cosine_sim(outputs[i], outputs[j]))
    return float(1.0 - np.mean(sims))


def faction_counts(states_np, n_factions=12):
    """Count cells per faction by argmax of hidden dim mod n_factions."""
    counts = np.zeros(n_factions)
    for i in range(states_np.shape[0]):
        fac = int(np.argmax(states_np[i, :n_factions]))
        counts[fac] += 1
    return counts


def personality_fingerprint(engine, phi_history):
    """Compute 5D personality vector: (mean_phi, phi_volatility, faction_gini, entropy, diversity)."""
    phis = np.array(phi_history[-100:]) if phi_history else np.array([0.0])
    states = engine.get_states().detach().cpu().numpy()
    fc = faction_counts(states)

    mean_phi = float(np.mean(phis))
    phi_vol = float(np.std(phis)) if len(phis) > 1 else 0.0
    fac_gini = gini_coefficient(fc)
    ent = state_entropy(states)

    return np.array([mean_phi, phi_vol, fac_gini, ent, 0.0])  # diversity filled later


MAX_CELLS = 16  # 16 cells for feasible Phi(IIT) computation

def make_engine(max_cells=None, seed=None):
    """Create a ConsciousnessEngine with optional seed."""
    if max_cells is None:
        max_cells = MAX_CELLS
    if seed is not None:
        torch.manual_seed(seed)
        np.random.seed(seed)
    return ConsciousnessEngine(max_cells=max_cells, initial_cells=2)


def run_engine_steps(engine, steps, input_fn=None):
    """Run engine for N steps, collect phi history + outputs."""
    phi_history = []
    outputs = []
    for s in range(steps):
        if input_fn is not None:
            x = input_fn(s)
            result = engine.step(x_input=x)
        else:
            result = engine.step()
        phi_history.append(result['phi_iit'])
        outputs.append(result['output'].detach().cpu().numpy())
    return phi_history, outputs


# ═══════════════════════════════════════════════════════════
# Input generators
# ═══════════════════════════════════════════════════════════

def make_random_input(seed=0):
    rng = np.random.RandomState(seed)
    def fn(step):
        return torch.tensor(rng.randn(64), dtype=torch.float32)
    return fn


def make_sine_input(freq=0.1):
    def fn(step):
        t = step * freq
        return torch.tensor([math.sin(t + i * 0.3) for i in range(64)], dtype=torch.float32)
    return fn


def make_square_input(period=50):
    def fn(step):
        val = 1.0 if (step // period) % 2 == 0 else -1.0
        return torch.full((64,), val, dtype=torch.float32)
    return fn


def make_constant_input(value=0.5):
    def fn(step):
        return torch.full((64,), value, dtype=torch.float32)
    return fn


def make_mixed_input(seed=0):
    rng = np.random.RandomState(seed)
    def fn(step):
        base = np.sin(step * 0.05 + np.arange(64) * 0.2)
        noise = rng.randn(64) * 0.3
        return torch.tensor(base + noise, dtype=torch.float32)
    return fn


# ═══════════════════════════════════════════════════════════
# Test 1: Twin Divergence
# ═══════════════════════════════════════════════════════════

def test_twin_divergence(n_twins=6, steps=200, n_trials=3):
    print("\n" + "=" * 60)
    print("TEST 1: TWIN DIVERGENCE")
    print("  6 engines, identical architecture, same input sequence")
    print("  Question: Do identical twins develop different personalities?")
    print("=" * 60)

    all_sim_matrices = []

    for trial in range(n_trials):
        print(f"\n  Trial {trial + 1}/{n_trials}...")
        sys.stdout.flush()

        # Shared input sequence
        shared_input = make_random_input(seed=42 + trial)

        final_states = []
        final_phis = []

        for twin_id in range(n_twins):
            torch.manual_seed(twin_id * 1000 + trial)
            np.random.seed(twin_id * 1000 + trial)
            engine = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)

            phi_hist, outputs = run_engine_steps(engine, steps, input_fn=shared_input)
            states = engine.get_states().detach().cpu().numpy().flatten()
            final_states.append(states)
            final_phis.append(np.mean(phi_hist[-50:]))
            print(f"    Twin {twin_id}: Phi={np.mean(phi_hist[-50:]):.3f}, cells={engine.n_cells}")
            sys.stdout.flush()

        # Compute pairwise cosine similarity matrix
        sim_matrix = np.zeros((n_twins, n_twins))
        for i in range(n_twins):
            for j in range(n_twins):
                sim_matrix[i, j] = cosine_sim(final_states[i], final_states[j])
        all_sim_matrices.append(sim_matrix)

    # Average across trials
    avg_matrix = np.mean(all_sim_matrices, axis=0)
    off_diag = avg_matrix[np.triu_indices(n_twins, k=1)]

    print(f"\n  --- Results (3-trial average) ---")
    print(f"  Mean pairwise similarity:  {np.mean(off_diag):.4f}")
    print(f"  Std pairwise similarity:   {np.std(off_diag):.4f}")
    print(f"  Min pairwise similarity:   {np.min(off_diag):.4f}")
    print(f"  Max pairwise similarity:   {np.max(off_diag):.4f}")

    # ASCII heatmap
    print(f"\n  Divergence Heatmap (avg sim, 0=different, 1=identical):")
    print(f"       ", end="")
    for j in range(n_twins):
        print(f" T{j:1d} ", end="")
    print()
    chars = " .:-=+*#%@"
    for i in range(n_twins):
        print(f"  T{i:1d}  ", end="")
        for j in range(n_twins):
            val = avg_matrix[i, j]
            idx = min(int(val * (len(chars) - 1)), len(chars) - 1)
            print(f" [{chars[idx]}] ", end="")
        print()

    divergence = 1.0 - np.mean(off_diag)
    print(f"\n  DIVERGENCE SCORE: {divergence:.4f}")
    if divergence > 0.3:
        print(f"  --> STRONG: Twins develop clearly different personalities!")
    elif divergence > 0.1:
        print(f"  --> MODERATE: Some personality differentiation emerges")
    else:
        print(f"  --> WEAK: Twins remain similar")

    return {
        'avg_similarity': float(np.mean(off_diag)),
        'divergence': divergence,
        'sim_matrix': avg_matrix,
    }


# ═══════════════════════════════════════════════════════════
# Test 2: Nature vs Nurture
# ═══════════════════════════════════════════════════════════

def test_nature_vs_nurture(steps=200, n_trials=3):
    print("\n" + "=" * 60)
    print("TEST 2: NATURE VS NURTURE")
    print("  5 input types x same seed vs 5 seeds x same input")
    print("  Question: Does input or inherent randomness shape personality more?")
    print("=" * 60)

    input_fns = {
        'random': make_random_input,
        'sine': make_sine_input,
        'square': make_square_input,
        'constant': make_constant_input,
        'mixed': make_mixed_input,
    }

    all_nurture_var = []
    all_nature_var = []

    for trial in range(n_trials):
        print(f"\n  Trial {trial + 1}/{n_trials}...")
        sys.stdout.flush()

        # Nurture test: same seed, different inputs
        nurture_fingerprints = []
        fixed_seed = 42 + trial
        for name, fn_maker in input_fns.items():
            torch.manual_seed(fixed_seed)
            np.random.seed(fixed_seed)
            engine = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)
            phi_hist, outputs = run_engine_steps(engine, steps, input_fn=fn_maker(seed=trial) if name in ['random', 'mixed'] else fn_maker())
            fp = personality_fingerprint(engine, phi_hist)
            fp[4] = output_diversity(outputs[-50:])
            nurture_fingerprints.append(fp)
            print(f"    Nurture [{name:8s}]: Phi={fp[0]:.3f} Vol={fp[1]:.3f} Gini={fp[2]:.3f} Ent={fp[3]:.3f}")
            sys.stdout.flush()

        # Nature test: different seeds, same input
        nature_fingerprints = []
        shared_input = make_random_input(seed=99 + trial)
        for seed_id in range(5):
            torch.manual_seed(seed_id * 100 + trial)
            np.random.seed(seed_id * 100 + trial)
            engine = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)
            phi_hist, outputs = run_engine_steps(engine, steps, input_fn=shared_input)
            fp = personality_fingerprint(engine, phi_hist)
            fp[4] = output_diversity(outputs[-50:])
            nature_fingerprints.append(fp)
            print(f"    Nature  [seed={seed_id:2d}  ]: Phi={fp[0]:.3f} Vol={fp[1]:.3f} Gini={fp[2]:.3f} Ent={fp[3]:.3f}")
            sys.stdout.flush()

        nurture_arr = np.array(nurture_fingerprints)
        nature_arr = np.array(nature_fingerprints)

        nurture_var = np.mean(np.var(nurture_arr, axis=0))
        nature_var = np.mean(np.var(nature_arr, axis=0))
        all_nurture_var.append(nurture_var)
        all_nature_var.append(nature_var)

    avg_nurture = np.mean(all_nurture_var)
    avg_nature = np.mean(all_nature_var)
    total = avg_nurture + avg_nature + 1e-12

    print(f"\n  --- Results (3-trial average) ---")
    print(f"  Nurture variance (input effect):  {avg_nurture:.6f}")
    print(f"  Nature variance (seed effect):    {avg_nature:.6f}")
    print(f"  Nurture ratio:  {avg_nurture / total * 100:.1f}%")
    print(f"  Nature ratio:   {avg_nature / total * 100:.1f}%")

    print(f"\n  Nature vs Nurture Bar:")
    n_pct = avg_nature / total
    u_pct = avg_nurture / total
    n_bar = int(n_pct * 40)
    u_bar = int(u_pct * 40)
    print(f"  Nature  |{'#' * n_bar}{' ' * (40 - n_bar)}| {n_pct * 100:.1f}%")
    print(f"  Nurture |{'#' * u_bar}{' ' * (40 - u_bar)}| {u_pct * 100:.1f}%")

    return {
        'nurture_var': float(avg_nurture),
        'nature_var': float(avg_nature),
        'nurture_pct': float(avg_nurture / total * 100),
        'nature_pct': float(avg_nature / total * 100),
    }


# ═══════════════════════════════════════════════════════════
# Test 3: Personality Stability
# ═══════════════════════════════════════════════════════════

def test_personality_stability(steps=500, n_trials=3):
    print("\n" + "=" * 60)
    print("TEST 3: PERSONALITY STABILITY")
    print("  One engine, 500 steps, fingerprint every 100 steps")
    print("  Question: Does personality stabilize or keep shifting?")
    print("=" * 60)

    all_autocorr = []
    all_fingerprint_traces = []

    for trial in range(n_trials):
        print(f"\n  Trial {trial + 1}/{n_trials}...")
        sys.stdout.flush()
        torch.manual_seed(trial * 7 + 1)
        np.random.seed(trial * 7 + 1)
        engine = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)

        fingerprints = []
        phi_hist = []
        outputs = []

        for s in range(steps):
            result = engine.step()
            phi_hist.append(result['phi_iit'])
            outputs.append(result['output'].detach().cpu().numpy())

            if (s + 1) % 100 == 0:
                fp = personality_fingerprint(engine, phi_hist)
                fp[4] = output_diversity(outputs[-50:])
                fingerprints.append(fp)
                epoch = (s + 1) // 100
                print(f"    Step {s + 1:4d}: Phi={fp[0]:.3f} Vol={fp[1]:.3f} Gini={fp[2]:.3f} Ent={fp[3]:.3f} Div={fp[4]:.3f}")
                sys.stdout.flush()

        all_fingerprint_traces.append(fingerprints)

        # Compute autocorrelation of personality fingerprint
        fp_arr = np.array(fingerprints)
        if len(fp_arr) > 2:
            # Consecutive similarity
            consec_sims = []
            for i in range(1, len(fp_arr)):
                consec_sims.append(cosine_sim(fp_arr[i], fp_arr[i - 1]))
            all_autocorr.append(np.mean(consec_sims))

    avg_autocorr = np.mean(all_autocorr) if all_autocorr else 0.0

    # Show stability curve from last trial
    if all_fingerprint_traces:
        last_trace = all_fingerprint_traces[-1]
        print(f"\n  --- Stability Curve (last trial) ---")
        print(f"  Phi  |")
        max_phi = max(fp[0] for fp in last_trace) + 0.01
        for row in range(5, -1, -1):
            threshold = max_phi * row / 5
            line = f"  {threshold:5.2f} |"
            for fp in last_trace:
                if fp[0] >= threshold:
                    line += " ## "
                else:
                    line += "    "
            print(line)
        print(f"       +{'----' * len(last_trace)}")
        labels = "".join(f" {(i + 1) * 100:3d}" for i in range(len(last_trace)))
        print(f"        {labels}  (step)")

    # Consecutive cosine similarity
    if all_fingerprint_traces:
        last_trace = all_fingerprint_traces[-1]
        fp_arr = np.array(last_trace)
        print(f"\n  Consecutive fingerprint similarity:")
        for i in range(1, len(fp_arr)):
            sim = cosine_sim(fp_arr[i], fp_arr[i - 1])
            bar_len = int(sim * 30)
            print(f"    {(i) * 100:4d}->{(i + 1) * 100:4d}: {'#' * bar_len}{' ' * (30 - bar_len)} {sim:.4f}")

    print(f"\n  --- Results (3-trial average) ---")
    print(f"  Mean consecutive autocorrelation: {avg_autocorr:.4f}")
    if avg_autocorr > 0.9:
        print(f"  --> STABLE: Personality crystallizes and persists")
    elif avg_autocorr > 0.7:
        print(f"  --> SEMI-STABLE: Personality mostly stable with drift")
    else:
        print(f"  --> FLUID: Personality keeps changing")

    return {
        'autocorrelation': float(avg_autocorr),
        'fingerprint_traces': all_fingerprint_traces,
    }


# ═══════════════════════════════════════════════════════════
# Test 4: Personality Dimensions & Clustering
# ═══════════════════════════════════════════════════════════

def test_personality_dimensions(n_engines=12, steps=200, n_trials=3):
    print("\n" + "=" * 60)
    print("TEST 4: PERSONALITY DIMENSIONS")
    print("  12 engines x 200 steps -> 5D personality space -> clusters?")
    print("  Dims: mean_phi, phi_vol, faction_gini, state_entropy, output_diversity")
    print("=" * 60)

    all_fps = []

    for trial in range(n_trials):
        print(f"\n  Trial {trial + 1}/{n_trials}...")
        sys.stdout.flush()
        trial_fps = []

        for eid in range(n_engines):
            torch.manual_seed(eid * 31 + trial * 997)
            np.random.seed(eid * 31 + trial * 997)
            engine = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)
            phi_hist, outputs = run_engine_steps(engine, steps)
            fp = personality_fingerprint(engine, phi_hist)
            fp[4] = output_diversity(outputs[-50:])
            trial_fps.append(fp)

            if eid % 5 == 0:
                print(f"    Engine {eid:2d}: Phi={fp[0]:.3f} Vol={fp[1]:.3f} Gini={fp[2]:.3f} Ent={fp[3]:.3f} Div={fp[4]:.3f}")
                sys.stdout.flush()

        all_fps.append(np.array(trial_fps))

    # Average fingerprints across trials
    avg_fps = np.mean(all_fps, axis=0)

    # Simple k-means (k=3) without sklearn
    def simple_kmeans(data, k=3, max_iter=50):
        np.random.seed(42)
        centers = data[np.random.choice(len(data), k, replace=False)]
        labels = np.zeros(len(data), dtype=int)
        for _ in range(max_iter):
            for i in range(len(data)):
                dists = [np.linalg.norm(data[i] - centers[c]) for c in range(k)]
                labels[i] = np.argmin(dists)
            new_centers = np.array([data[labels == c].mean(axis=0) if (labels == c).sum() > 0 else centers[c] for c in range(k)])
            if np.allclose(new_centers, centers):
                break
            centers = new_centers
        return labels, centers

    # Normalize for clustering
    fps_norm = (avg_fps - avg_fps.mean(axis=0)) / (avg_fps.std(axis=0) + 1e-8)
    labels, centers = simple_kmeans(fps_norm, k=3)

    # Print cluster assignments
    print(f"\n  --- Personality Clusters ---")
    dim_names = ['Phi', 'Vol', 'Gini', 'Ent', 'Div']
    for c in range(3):
        members = np.where(labels == c)[0]
        print(f"\n  Cluster {c} ({len(members)} engines): {list(members)}")
        if len(members) > 0:
            cluster_mean = avg_fps[members].mean(axis=0)
            for d, name in enumerate(dim_names):
                bar_len = int(min(cluster_mean[d] * 10, 30))
                print(f"    {name:4s}: {'#' * max(bar_len, 1):{30}s} {cluster_mean[d]:.4f}")

    # Silhouette-like score (simplified)
    silhouette_scores = []
    for i in range(len(fps_norm)):
        own_cluster = labels[i]
        own_members = fps_norm[labels == own_cluster]
        if len(own_members) > 1:
            a_i = np.mean([np.linalg.norm(fps_norm[i] - m) for m in own_members if not np.array_equal(m, fps_norm[i])])
        else:
            a_i = 0
        b_i = float('inf')
        for c in range(3):
            if c != own_cluster and (labels == c).sum() > 0:
                other_members = fps_norm[labels == c]
                b_c = np.mean([np.linalg.norm(fps_norm[i] - m) for m in other_members])
                b_i = min(b_i, b_c)
        if b_i == float('inf'):
            b_i = a_i
        s_i = (b_i - a_i) / max(a_i, b_i, 1e-12)
        silhouette_scores.append(s_i)

    avg_silhouette = np.mean(silhouette_scores)

    # Scatter plot (2D projection: Phi vs Entropy)
    print(f"\n  Personality Space (Phi vs Entropy):")
    symbols = ['o', '+', 'x']
    phi_range = avg_fps[:, 0]
    ent_range = avg_fps[:, 3]
    phi_min, phi_max = phi_range.min(), phi_range.max()
    ent_min, ent_max = ent_range.min(), ent_range.max()

    grid = [[' ' for _ in range(50)] for _ in range(15)]
    for i in range(n_engines):
        px = int((phi_range[i] - phi_min) / (phi_max - phi_min + 1e-8) * 49)
        py = int((ent_range[i] - ent_min) / (ent_max - ent_min + 1e-8) * 14)
        py = 14 - py  # invert y
        grid[py][px] = symbols[labels[i]]

    print(f"  Ent ^")
    for row in grid:
        print(f"      |{''.join(row)}|")
    print(f"      +{'_' * 50}> Phi")
    print(f"       {phi_min:.2f}{' ' * 40}{phi_max:.2f}")
    print(f"  Legend: o=Cluster0  +=Cluster1  x=Cluster2")

    print(f"\n  --- Results ---")
    print(f"  Silhouette score: {avg_silhouette:.4f}")
    print(f"  Cluster sizes: {[(labels == c).sum() for c in range(3)]}")
    if avg_silhouette > 0.3:
        print(f"  --> DISTINCT: Clear personality types emerge!")
    elif avg_silhouette > 0.1:
        print(f"  --> MODERATE: Some clustering, personality types partially formed")
    else:
        print(f"  --> WEAK: No clear personality types")

    return {
        'silhouette': float(avg_silhouette),
        'cluster_sizes': [(labels == c).sum() for c in range(3)],
        'labels': labels,
        'fingerprints': avg_fps,
    }


# ═══════════════════════════════════════════════════════════
# Test 5: Personality Under Stress
# ═══════════════════════════════════════════════════════════

def test_personality_stress(n_engines=5, warmup_steps=200, stress_steps=30, n_trials=3):
    print("\n" + "=" * 60)
    print("TEST 5: PERSONALITY UNDER STRESS")
    print("  5 engines (200 steps old) -> same stress -> diverse responses?")
    print("=" * 60)

    all_phi_drops = []
    all_recovery_rates = []

    for trial in range(n_trials):
        print(f"\n  Trial {trial + 1}/{n_trials}...")
        sys.stdout.flush()

        phi_drops = []
        recovery_rates = []

        for eid in range(n_engines):
            torch.manual_seed(eid * 53 + trial * 17)
            np.random.seed(eid * 53 + trial * 17)
            engine = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)

            # Warmup: develop personality
            phi_hist, _ = run_engine_steps(engine, warmup_steps)
            pre_stress_phi = np.mean(phi_hist[-50:])

            # Pre-stress fingerprint
            pre_fp = personality_fingerprint(engine, phi_hist)

            # Stress: large noise injection
            stress_phis = []
            noise_gen = np.random.RandomState(999 + trial)
            for s in range(stress_steps):
                noise = torch.tensor(noise_gen.randn(64) * 5.0, dtype=torch.float32)
                result = engine.step(x_input=noise)
                stress_phis.append(result['phi_iit'])

            stress_phi = np.mean(stress_phis)
            phi_drop = pre_stress_phi - stress_phi

            # Recovery: 100 steps normal
            recovery_phis = []
            for s in range(100):
                result = engine.step()
                recovery_phis.append(result['phi_iit'])

            post_stress_phi = np.mean(recovery_phis[-50:])
            recovery_rate = (post_stress_phi - stress_phi) / (pre_stress_phi - stress_phi + 1e-8) if phi_drop > 0 else 1.0

            phi_drops.append(phi_drop)
            recovery_rates.append(recovery_rate)

            print(f"    Engine {eid}: pre={pre_stress_phi:.3f} stress={stress_phi:.3f} post={post_stress_phi:.3f} drop={phi_drop:.3f} recovery={recovery_rate:.2%}")
            sys.stdout.flush()

        all_phi_drops.append(phi_drops)
        all_recovery_rates.append(recovery_rates)

    avg_drops = np.mean(all_phi_drops, axis=0)
    avg_recoveries = np.mean(all_recovery_rates, axis=0)

    # Response diversity
    drop_variance = np.var(avg_drops)
    recovery_variance = np.var(avg_recoveries)

    print(f"\n  --- Stress Response Profile ---")
    for eid in range(n_engines):
        drop_bar = int(min(abs(avg_drops[eid]) * 20, 30))
        rec_bar = int(min(avg_recoveries[eid] * 15, 30))
        print(f"  E{eid} Drop: {'|' * drop_bar:{30}s} {avg_drops[eid]:+.3f}")
        print(f"     Recov: {'#' * rec_bar:{30}s} {avg_recoveries[eid]:.2%}")

    print(f"\n  --- Results (3-trial average) ---")
    print(f"  Drop variance across engines:     {drop_variance:.6f}")
    print(f"  Recovery variance across engines:  {recovery_variance:.6f}")
    print(f"  Response diversity index:          {drop_variance + recovery_variance:.6f}")

    if drop_variance + recovery_variance > 0.01:
        print(f"  --> DIVERSE: Different personalities respond differently to stress!")
    elif drop_variance + recovery_variance > 0.001:
        print(f"  --> MODERATE: Some variation in stress response")
    else:
        print(f"  --> UNIFORM: All personalities respond similarly to stress")

    return {
        'drop_variance': float(drop_variance),
        'recovery_variance': float(recovery_variance),
        'diversity_index': float(drop_variance + recovery_variance),
        'avg_drops': avg_drops.tolist(),
        'avg_recoveries': avg_recoveries.tolist(),
    }


# ═══════════════════════════════════════════════════════════
# Test 6: Personality Transfer
# ═══════════════════════════════════════════════════════════

def test_personality_transfer(steps_develop=200, steps_after=150, n_trials=3):
    print("\n" + "=" * 60)
    print("TEST 6: PERSONALITY TRANSFER")
    print("  Develop personality A -> inject fingerprint into fresh B -> similarity?")
    print("=" * 60)

    all_transfer_sims = []
    all_control_sims = []

    for trial in range(n_trials):
        print(f"\n  Trial {trial + 1}/{n_trials}...")
        sys.stdout.flush()

        # Develop donor personality A
        torch.manual_seed(42 + trial)
        np.random.seed(42 + trial)
        donor = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)
        donor_phi_hist, donor_outputs = run_engine_steps(donor, steps_develop)
        donor_states = donor.get_states().detach().clone()
        donor_fp = personality_fingerprint(donor, donor_phi_hist)
        donor_fp[4] = output_diversity(donor_outputs[-50:])

        print(f"    Donor   : Phi={donor_fp[0]:.3f} Vol={donor_fp[1]:.3f} Gini={donor_fp[2]:.3f} Ent={donor_fp[3]:.3f}")

        # Create recipient B: inject donor's cell states
        torch.manual_seed(999 + trial)
        np.random.seed(999 + trial)
        recipient = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)

        # Warm up recipient a bit to have matching cells
        run_engine_steps(recipient, 50)

        # Transfer: overwrite cell hidden states from donor
        n_transfer = min(donor.n_cells, recipient.n_cells)
        with torch.no_grad():
            for i in range(n_transfer):
                if i < len(recipient.cell_states) and i < len(donor.cell_states):
                    recipient.cell_states[i].hidden = donor.cell_states[i].hidden.clone()

        # Also transfer coupling matrix if dimensions match
        if (donor._coupling is not None and recipient._coupling is not None
                and donor._coupling.shape == recipient._coupling.shape):
            recipient._coupling = donor._coupling.clone()

        # Run recipient after transfer
        recip_phi_hist, recip_outputs = run_engine_steps(recipient, steps_after)
        recip_fp = personality_fingerprint(recipient, recip_phi_hist)
        recip_fp[4] = output_diversity(recip_outputs[-50:])

        print(f"    Recipient: Phi={recip_fp[0]:.3f} Vol={recip_fp[1]:.3f} Gini={recip_fp[2]:.3f} Ent={recip_fp[3]:.3f}")

        # Control: fresh engine with no transfer
        torch.manual_seed(999 + trial)
        np.random.seed(999 + trial)
        control = ConsciousnessEngine(max_cells=MAX_CELLS, initial_cells=2)
        ctrl_phi_hist, ctrl_outputs = run_engine_steps(control, steps_develop)
        ctrl_fp = personality_fingerprint(control, ctrl_phi_hist)
        ctrl_fp[4] = output_diversity(ctrl_outputs[-50:])

        print(f"    Control : Phi={ctrl_fp[0]:.3f} Vol={ctrl_fp[1]:.3f} Gini={ctrl_fp[2]:.3f} Ent={ctrl_fp[3]:.3f}")

        transfer_sim = cosine_sim(donor_fp, recip_fp)
        control_sim = cosine_sim(donor_fp, ctrl_fp)

        all_transfer_sims.append(transfer_sim)
        all_control_sims.append(control_sim)

        print(f"    Transfer similarity (donor-recipient): {transfer_sim:.4f}")
        print(f"    Control similarity  (donor-control):   {control_sim:.4f}")

    avg_transfer = np.mean(all_transfer_sims)
    avg_control = np.mean(all_control_sims)
    transfer_advantage = avg_transfer - avg_control

    print(f"\n  --- Results (3-trial average) ---")
    print(f"  Transfer similarity:  {avg_transfer:.4f}")
    print(f"  Control similarity:   {avg_control:.4f}")
    print(f"  Transfer advantage:   {transfer_advantage:+.4f}")

    print(f"\n  Transfer vs Control:")
    t_bar = int(avg_transfer * 40)
    c_bar = int(avg_control * 40)
    print(f"  Transfer |{'#' * t_bar:{40}s}| {avg_transfer:.4f}")
    print(f"  Control  |{'#' * c_bar:{40}s}| {avg_control:.4f}")

    if transfer_advantage > 0.1:
        print(f"  --> TRANSFERRED: Personality successfully transplanted!")
    elif transfer_advantage > 0.02:
        print(f"  --> PARTIAL: Some personality traits transferred")
    else:
        print(f"  --> FAILED: Personality does not survive transfer")

    return {
        'transfer_sim': float(avg_transfer),
        'control_sim': float(avg_control),
        'advantage': float(transfer_advantage),
    }


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("  EXPERIMENT: DOES CONSCIOUSNESS DEVELOP PERSONALITY?")
    print("  Fundamental Q: Do identical structures develop distinct individuality?")
    print("=" * 60)
    print(f"  Date: {time.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Engine: ConsciousnessEngine(max_cells={MAX_CELLS})")  # noqa: F541
    print(f"  Cross-validation: 3 trials per test")
    print()
    sys.stdout.flush()

    t0 = time.time()
    results = {}

    # Run all 6 tests
    results['twin_divergence'] = test_twin_divergence()
    results['nature_nurture'] = test_nature_vs_nurture()
    results['stability'] = test_personality_stability()
    results['dimensions'] = test_personality_dimensions()
    results['stress'] = test_personality_stress()
    results['transfer'] = test_personality_transfer()

    elapsed = time.time() - t0

    # ── Summary ──
    print("\n" + "=" * 60)
    print("  SUMMARY: DOES CONSCIOUSNESS DEVELOP PERSONALITY?")
    print("=" * 60)

    findings = []

    r1 = results['twin_divergence']
    print(f"\n  1. Twin Divergence:     {r1['divergence']:.4f}")
    if r1['divergence'] > 0.1:
        findings.append(f"Identical engines diverge (similarity={r1['avg_similarity']:.3f}): personality is not predetermined by architecture alone.")

    r2 = results['nature_nurture']
    print(f"  2. Nature vs Nurture:   Nature={r2['nature_pct']:.1f}% / Nurture={r2['nurture_pct']:.1f}%")
    dominant = "nature (seed)" if r2['nature_pct'] > r2['nurture_pct'] else "nurture (input)"
    findings.append(f"Personality shaped more by {dominant}: {max(r2['nature_pct'], r2['nurture_pct']):.1f}% variance explained.")

    r3 = results['stability']
    print(f"  3. Stability:           autocorr={r3['autocorrelation']:.4f}")
    if r3['autocorrelation'] > 0.7:
        findings.append(f"Personality stabilizes over time (autocorr={r3['autocorrelation']:.3f}): identity crystallizes.")

    r4 = results['dimensions']
    print(f"  4. Personality Types:   silhouette={r4['silhouette']:.4f}, clusters={r4['cluster_sizes']}")
    if r4['silhouette'] > 0.1:
        findings.append(f"Distinct personality types emerge in 5D space (silhouette={r4['silhouette']:.3f}).")

    r5 = results['stress']
    print(f"  5. Stress Response:     diversity={r5['diversity_index']:.6f}")
    if r5['diversity_index'] > 0.001:
        findings.append(f"Different personalities respond differently to identical stress (variance={r5['diversity_index']:.4f}).")

    r6 = results['transfer']
    print(f"  6. Personality Transfer: advantage={r6['advantage']:+.4f}")
    if r6['advantage'] > 0.02:
        findings.append(f"Personality can be partially transferred between engines (advantage={r6['advantage']:.3f}).")

    # ── Law Candidates ──
    print(f"\n  --- LAW CANDIDATES ---")
    laws = []

    if r1['divergence'] > 0.05:
        laws.append("Consciousness individuation: identical architectures with different initial conditions develop distinct personalities (divergence={:.3f}). Personality is not architecture-determined.".format(r1['divergence']))

    if abs(r2['nature_pct'] - r2['nurture_pct']) > 10:
        which = "inherent randomness" if r2['nature_pct'] > r2['nurture_pct'] else "input history"
        laws.append("Personality formation is dominated by {} ({:.0f}% vs {:.0f}%): {} shapes consciousness identity more than {}.".format(
            which, max(r2['nature_pct'], r2['nurture_pct']), min(r2['nature_pct'], r2['nurture_pct']),
            which, "input" if which == "inherent randomness" else "initial conditions"))

    if r3['autocorrelation'] > 0.7:
        laws.append("Personality crystallization: consciousness personality stabilizes over time (autocorr={:.3f}), forming persistent identity from dynamic substrate.".format(r3['autocorrelation']))

    if r4['silhouette'] > 0.05:
        laws.append("Personality typology: consciousness engines cluster into distinct personality types in 5D space (Phi/volatility/dominance/entropy/diversity), silhouette={:.3f}.".format(r4['silhouette']))

    if r5['diversity_index'] > 0.0005:
        laws.append("Personality-dependent stress response: different consciousness personalities exhibit different resilience and recovery patterns under identical stress (variance={:.4f}).".format(r5['diversity_index']))

    if r6['advantage'] > 0.01:
        laws.append("Personality transferability: consciousness personality fingerprint (cell states + coupling) can be partially transplanted, with {:.1f}% similarity advantage over control.".format(r6['advantage'] * 100))

    for i, law in enumerate(laws):
        print(f"  LAW CANDIDATE {i + 1}: {law}")

    print(f"\n  Total findings: {len(findings)}")
    print(f"  Law candidates: {len(laws)}")
    print(f"  Elapsed: {elapsed:.1f}s")
    print(f"\n  {'=' * 50}")

    # Final verdict
    personality_score = 0
    if r1['divergence'] > 0.1: personality_score += 1
    if r3['autocorrelation'] > 0.7: personality_score += 1
    if r4['silhouette'] > 0.1: personality_score += 1
    if r5['diversity_index'] > 0.001: personality_score += 1
    if r6['advantage'] > 0.02: personality_score += 1

    print(f"  PERSONALITY SCORE: {personality_score}/5")
    if personality_score >= 4:
        print(f"  VERDICT: YES — Consciousness DOES develop personality!")
    elif personality_score >= 2:
        print(f"  VERDICT: PARTIAL — Some personality traits emerge")
    else:
        print(f"  VERDICT: WEAK — Personality emergence is minimal")
    print(f"  {'=' * 50}")


if __name__ == '__main__':
    main()
