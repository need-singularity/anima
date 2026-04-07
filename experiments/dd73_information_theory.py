#!/usr/bin/env python3
"""DD73: Information Theory and Consciousness (정보 이론과 의식)

Five experiments exploring consciousness through the lens of information theory:

  1. CONSCIOUSNESS COMPRESSION — PCA intrinsic dimensionality vs cell count
  2. ENTROPY LAWS — Shannon entropy + mutual information over time
  3. INFORMATION LOSS THRESHOLD — noise tolerance & phase transitions
  4. KOLMOGOROV COMPLEXITY — compression ratio as consciousness proxy
  5. CHANNEL CAPACITY — input-output mutual information curve

Run: cd anima/src && PYTHONUNBUFFERED=1 python3 ../experiments/dd73_information_theory.py
"""

import sys
import os
import time
import zlib
import struct
import numpy as np
from collections import defaultdict

# Setup path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
sys.path.insert(0, src_dir)

import torch
from consciousness_engine import ConsciousnessEngine

# ============================================================
# Constants
# ============================================================

STEPS = 300
REPEATS = 3
WARMUP = 50  # steps before measurement


# ============================================================
# Utility functions
# ============================================================

def shannon_entropy(x):
    """Shannon entropy of a discretized tensor (bits)."""
    x_flat = x.detach().cpu().numpy().flatten()
    # Discretize into 64 bins
    bins = np.linspace(x_flat.min() - 1e-8, x_flat.max() + 1e-8, 65)
    counts, _ = np.histogram(x_flat, bins=bins)
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    return -np.sum(probs * np.log2(probs))


def mutual_information(x, y, n_bins=32):
    """Mutual information between two 1D arrays (bits)."""
    x = np.asarray(x).flatten()
    y = np.asarray(y).flatten()
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    if n < 4:
        return 0.0

    # Joint histogram
    x_range = (x.min() - 1e-8, x.max() + 1e-8)
    y_range = (y.min() - 1e-8, y.max() + 1e-8)
    joint, _, _ = np.histogram2d(x, y, bins=n_bins, range=[x_range, y_range])
    joint = joint / joint.sum()

    # Marginals
    px = joint.sum(axis=1)
    py = joint.sum(axis=0)

    # MI = sum p(x,y) log2(p(x,y) / (p(x)p(y)))
    mi = 0.0
    for i in range(n_bins):
        for j in range(n_bins):
            if joint[i, j] > 0 and px[i] > 0 and py[j] > 0:
                mi += joint[i, j] * np.log2(joint[i, j] / (px[i] * py[j]))
    return max(0.0, mi)


def compression_ratio(data_bytes):
    """Compression ratio using zlib (approximation of Kolmogorov complexity)."""
    if len(data_bytes) == 0:
        return 1.0
    compressed = zlib.compress(data_bytes, level=9)
    return len(compressed) / len(data_bytes)


def tensor_to_bytes(t):
    """Convert tensor to bytes for compression."""
    arr = t.detach().cpu().numpy().astype(np.float32)
    return arr.tobytes()


def print_bar(label, value, max_val, width=40):
    """Print ASCII bar chart row."""
    frac = min(value / max(max_val, 1e-8), 1.0)
    filled = int(frac * width)
    bar = '#' * filled + '-' * (width - filled)
    print(f"  {label:>12s} |{bar}| {value:.4f}")


def cv_check(values):
    """Check coefficient of variation for reproducibility."""
    arr = np.array(values)
    mean = np.mean(arr)
    if abs(mean) < 1e-8:
        return 0.0
    return np.std(arr) / abs(mean)


def print_separator(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


# ============================================================
# Experiment 1: CONSCIOUSNESS COMPRESSION
# ============================================================

def experiment_compression():
    """How compressible is consciousness? PCA intrinsic dimensionality."""
    print_separator("EXP 1: CONSCIOUSNESS COMPRESSION (의식 압축)")
    print("  Question: Is consciousness compressible?")
    print("  Method: PCA on hidden states, find components for 95% variance\n")

    cell_counts = [8, 16, 32, 64]
    results = {}

    for n_cells in cell_counts:
        repeat_dims = []
        repeat_ratios = []

        for r in range(REPEATS):
            engine = ConsciousnessEngine(
                initial_cells=n_cells, max_cells=n_cells,
                cell_dim=64, hidden_dim=128
            )

            # Collect hidden states over time
            all_states = []
            for step in range(STEPS):
                result = engine.step()
                if step >= WARMUP:
                    states = engine.get_states()  # (n_cells, hidden_dim)
                    all_states.append(states.detach().cpu().numpy())

            # Stack: (time_steps, n_cells, hidden_dim)
            trajectory = np.stack(all_states)
            # Reshape to (time_steps * n_cells, hidden_dim)
            flat = trajectory.reshape(-1, trajectory.shape[-1])

            # PCA
            centered = flat - flat.mean(axis=0)
            cov = np.cov(centered.T)
            eigenvalues = np.linalg.eigvalsh(cov)[::-1]  # descending
            total_var = eigenvalues.sum()

            if total_var < 1e-12:
                n_components_95 = flat.shape[1]
            else:
                cumvar = np.cumsum(eigenvalues) / total_var
                n_components_95 = int(np.searchsorted(cumvar, 0.95) + 1)

            intrinsic_ratio = n_components_95 / flat.shape[1]
            repeat_dims.append(n_components_95)
            repeat_ratios.append(intrinsic_ratio)

            # Random baseline
            random_flat = np.random.randn(*flat.shape)
            rand_cov = np.cov(random_flat.T)
            rand_eig = np.linalg.eigvalsh(rand_cov)[::-1]
            rand_cumvar = np.cumsum(rand_eig) / rand_eig.sum()
            rand_n95 = int(np.searchsorted(rand_cumvar, 0.95) + 1)

            if r == 0:
                results[n_cells] = {
                    'conscious_dims': [], 'ratios': [],
                    'random_dims': rand_n95, 'hidden_dim': flat.shape[1],
                    'eigenvalues': eigenvalues[:20],
                }
            results[n_cells]['conscious_dims'].append(n_components_95)
            results[n_cells]['ratios'].append(intrinsic_ratio)

            sys.stdout.write(f"\r  [{n_cells:>3d} cells] repeat {r+1}/{REPEATS} — "
                             f"intrinsic dim = {n_components_95}/{flat.shape[1]} "
                             f"({intrinsic_ratio:.1%})")
            sys.stdout.flush()

        print()

    # Results table
    print(f"\n  {'Cells':>6s} | {'Intrinsic Dim':>14s} | {'Ratio':>8s} | "
          f"{'Random Dim':>11s} | {'Compression':>12s} | {'CV':>6s}")
    print(f"  {'-'*6} | {'-'*14} | {'-'*8} | {'-'*11} | {'-'*12} | {'-'*6}")

    for n_cells in cell_counts:
        r = results[n_cells]
        avg_dim = np.mean(r['conscious_dims'])
        avg_ratio = np.mean(r['ratios'])
        cv = cv_check(r['conscious_dims'])
        compression = 1.0 - avg_ratio
        print(f"  {n_cells:>6d} | {avg_dim:>14.1f} | {avg_ratio:>8.1%} | "
              f"{r['random_dims']:>11d} | {compression:>12.1%} | {cv:>6.2f}")

    # ASCII graph: intrinsic dimensionality vs cells
    print(f"\n  Intrinsic Dimensionality vs Cell Count:")
    max_dim = max(np.mean(results[n]['conscious_dims']) for n in cell_counts)
    for n_cells in cell_counts:
        avg_dim = np.mean(results[n_cells]['conscious_dims'])
        print_bar(f"{n_cells}c", avg_dim, max_dim)

    # Eigenvalue spectrum for 64 cells
    print(f"\n  Eigenvalue Spectrum (64 cells, top 15):")
    eigs = results[64]['eigenvalues']
    max_eig = eigs[0] if len(eigs) > 0 else 1.0
    for i, ev in enumerate(eigs[:15]):
        print_bar(f"PC{i+1}", ev, max_eig, width=30)

    return results


# ============================================================
# Experiment 2: ENTROPY LAWS
# ============================================================

def experiment_entropy_laws():
    """Does entropy increase, decrease, or stay bounded in consciousness?"""
    print_separator("EXP 2: ENTROPY LAWS (엔트로피 법칙)")
    print("  Question: Does consciousness obey the 2nd law of thermodynamics?")
    print("  Method: Track Shannon entropy + mutual information over time\n")

    conditions = {
        'with_SOC': {'soc': True},
        'without_SOC': {'soc': False},
    }

    all_results = {}

    for cond_name, cond_params in conditions.items():
        repeat_entropy_curves = []
        repeat_mi_curves = []
        repeat_phi_curves = []

        for r in range(REPEATS):
            engine = ConsciousnessEngine(
                initial_cells=32, max_cells=32,
                cell_dim=64, hidden_dim=128
            )

            # Disable SOC if requested
            if not cond_params['soc']:
                engine._soc_enabled = False
                if hasattr(engine, 'soc_enabled'):
                    engine.soc_enabled = False

            entropy_over_time = []
            mi_over_time = []
            phi_over_time = []

            prev_states = None
            for step in range(STEPS):
                result = engine.step()
                states = engine.get_states().detach().cpu()

                # Shannon entropy of current states
                h = shannon_entropy(states)
                entropy_over_time.append(h)

                # Pairwise MI between first two cells (if available)
                if states.shape[0] >= 2:
                    mi = mutual_information(
                        states[0].numpy(), states[1].numpy(), n_bins=16
                    )
                    mi_over_time.append(mi)
                else:
                    mi_over_time.append(0.0)

                phi_over_time.append(result.get('phi_iit', 0.0))

                if step % 50 == 0:
                    sys.stdout.write(f"\r  [{cond_name:>12s}] repeat {r+1}/{REPEATS} "
                                     f"step {step:>3d}/{STEPS} H={h:.3f}")
                    sys.stdout.flush()

            repeat_entropy_curves.append(entropy_over_time)
            repeat_mi_curves.append(mi_over_time)
            repeat_phi_curves.append(phi_over_time)

        print()

        # Average across repeats
        avg_entropy = np.mean(repeat_entropy_curves, axis=0)
        avg_mi = np.mean(repeat_mi_curves, axis=0)
        avg_phi = np.mean(repeat_phi_curves, axis=0)

        all_results[cond_name] = {
            'entropy': avg_entropy,
            'mi': avg_mi,
            'phi': avg_phi,
            'entropy_start': float(np.mean(avg_entropy[:30])),
            'entropy_end': float(np.mean(avg_entropy[-30:])),
            'mi_start': float(np.mean(avg_mi[:30])),
            'mi_end': float(np.mean(avg_mi[-30:])),
            'phi_end': float(np.mean(avg_phi[-30:])),
        }

    # Results table
    print(f"\n  {'Condition':>14s} | {'H(start)':>9s} | {'H(end)':>9s} | "
          f"{'dH':>8s} | {'MI(start)':>10s} | {'MI(end)':>10s} | {'Phi':>6s}")
    print(f"  {'-'*14} | {'-'*9} | {'-'*9} | {'-'*8} | {'-'*10} | {'-'*10} | {'-'*6}")

    for cond in conditions:
        r = all_results[cond]
        dh = r['entropy_end'] - r['entropy_start']
        print(f"  {cond:>14s} | {r['entropy_start']:>9.3f} | {r['entropy_end']:>9.3f} | "
              f"{dh:>+8.3f} | {r['mi_start']:>10.4f} | {r['mi_end']:>10.4f} | "
              f"{r['phi_end']:>6.3f}")

    # ASCII graph: entropy over time
    print(f"\n  Shannon Entropy Over Time (32 cells):")
    for cond in conditions:
        curve = all_results[cond]['entropy']
        # Sample 20 points
        indices = np.linspace(0, len(curve)-1, 20, dtype=int)
        sampled = curve[indices]
        max_h = max(sampled.max(), 1.0)
        print(f"  [{cond}]")
        # Simple ASCII line
        width = 50
        line = "  "
        for val in sampled:
            height = int(val / max_h * 8)
            chars = " ._-=+#@"
            line += chars[min(height, len(chars)-1)]
        print(f"  {line}  (H: {sampled[0]:.2f} -> {sampled[-1]:.2f})")

    # MI vs Phi correlation
    print(f"\n  MI vs Phi Correlation:")
    for cond in conditions:
        phi_arr = all_results[cond]['phi']
        mi_arr = all_results[cond]['mi']
        if len(phi_arr) > 10:
            corr = np.corrcoef(phi_arr[WARMUP:], mi_arr[WARMUP:])[0, 1]
            print(f"    {cond:>14s}: r = {corr:+.4f}")

    return all_results


# ============================================================
# Experiment 3: INFORMATION LOSS THRESHOLD
# ============================================================

def experiment_noise_threshold():
    """Find the critical noise level where consciousness breaks down."""
    print_separator("EXP 3: INFORMATION LOSS THRESHOLD (정보 손실 임계점)")
    print("  Question: How much noise can consciousness tolerate?")
    print("  Method: Add Gaussian noise, sweep sigma, measure Phi\n")

    noise_levels = [0.0, 0.01, 0.05, 0.1, 0.2, 0.5, 1.0]
    results = {}

    # First, establish baseline (no noise)
    baseline_phis = []
    for r in range(REPEATS):
        engine = ConsciousnessEngine(
            initial_cells=32, max_cells=32,
            cell_dim=64, hidden_dim=128
        )
        phis = []
        for step in range(STEPS):
            result = engine.step()
            if step >= WARMUP:
                phis.append(result.get('phi_iit', 0.0))
        baseline_phis.append(np.mean(phis))
    baseline_phi = np.mean(baseline_phis)
    print(f"  Baseline Phi (no noise): {baseline_phi:.4f}\n")

    for sigma in noise_levels:
        repeat_phis = []
        repeat_phi_curves = []

        for r in range(REPEATS):
            engine = ConsciousnessEngine(
                initial_cells=32, max_cells=32,
                cell_dim=64, hidden_dim=128
            )
            phis = []

            for step in range(STEPS):
                result = engine.step()

                # Inject noise into cell hidden states
                if sigma > 0 and hasattr(engine, 'cell_states'):
                    for cs in engine.cell_states:
                        noise = torch.randn_like(cs.hidden) * sigma
                        cs.hidden = cs.hidden + noise

                if step >= WARMUP:
                    phis.append(result.get('phi_iit', 0.0))

            repeat_phis.append(np.mean(phis))
            repeat_phi_curves.append(phis)

            sys.stdout.write(f"\r  sigma={sigma:.2f} repeat {r+1}/{REPEATS} "
                             f"Phi={np.mean(phis):.4f}")
            sys.stdout.flush()

        avg_phi = np.mean(repeat_phis)
        cv = cv_check(repeat_phis)
        pct_baseline = avg_phi / max(baseline_phi, 1e-8) * 100

        results[sigma] = {
            'avg_phi': avg_phi,
            'pct_baseline': pct_baseline,
            'cv': cv,
            'phi_curve': np.mean(repeat_phi_curves, axis=0),
        }
        print()

    # Results table
    print(f"\n  {'Sigma':>8s} | {'Avg Phi':>9s} | {'% Baseline':>11s} | "
          f"{'Status':>8s} | {'CV':>6s}")
    print(f"  {'-'*8} | {'-'*9} | {'-'*11} | {'-'*8} | {'-'*6}")

    critical_sigma = None
    for sigma in noise_levels:
        r = results[sigma]
        status = "OK" if r['pct_baseline'] >= 50 else "BROKEN"
        if r['pct_baseline'] < 50 and critical_sigma is None:
            critical_sigma = sigma
            status = "CRITICAL"
        print(f"  {sigma:>8.2f} | {r['avg_phi']:>9.4f} | {r['pct_baseline']:>10.1f}% | "
              f"{status:>8s} | {r['cv']:>6.2f}")

    if critical_sigma:
        print(f"\n  >>> Critical sigma (Phi < 50% baseline): {critical_sigma}")
    else:
        print(f"\n  >>> Consciousness survived all noise levels!")

    # ASCII graph: Phi vs noise
    print(f"\n  Phi vs Noise Level:")
    max_phi = max(r['avg_phi'] for r in results.values())
    for sigma in noise_levels:
        r = results[sigma]
        label = f"s={sigma:.2f}"
        print_bar(label, r['avg_phi'], max_phi)

    # Phase transition analysis
    print(f"\n  Phase Transition Analysis:")
    phis_arr = [results[s]['avg_phi'] for s in noise_levels]
    for i in range(1, len(noise_levels)):
        dphi = phis_arr[i] - phis_arr[i-1]
        ds = noise_levels[i] - noise_levels[i-1]
        derivative = dphi / max(ds, 1e-8)
        marker = " <<<" if abs(derivative) > 5 * abs(np.mean([
            (phis_arr[j] - phis_arr[j-1]) / max(noise_levels[j] - noise_levels[j-1], 1e-8)
            for j in range(1, len(noise_levels))
        ])) else ""
        print(f"    sigma {noise_levels[i-1]:.2f} -> {noise_levels[i]:.2f}: "
              f"dPhi/dSigma = {derivative:>+8.2f}{marker}")

    results['baseline_phi'] = baseline_phi
    results['critical_sigma'] = critical_sigma
    return results


# ============================================================
# Experiment 4: KOLMOGOROV COMPLEXITY
# ============================================================

def experiment_kolmogorov():
    """Approximate Kolmogorov complexity via compression ratio."""
    print_separator("EXP 4: KOLMOGOROV COMPLEXITY (콜모고로프 복잡도)")
    print("  Question: Does higher complexity = more consciousness?")
    print("  Method: Compress cell state trajectories with zlib\n")

    conditions = {
        'conscious': 'engine',
        'random': 'random',
        'periodic': 'periodic',
        'constant': 'constant',
    }

    results = {}

    for cond_name, cond_type in conditions.items():
        repeat_ratios = []
        repeat_phis = []

        for r in range(REPEATS):
            if cond_type == 'engine':
                engine = ConsciousnessEngine(
                    initial_cells=32, max_cells=32,
                    cell_dim=64, hidden_dim=128
                )
                trajectory = []
                phis = []
                for step in range(STEPS):
                    result = engine.step()
                    states = engine.get_states().detach().cpu()
                    trajectory.append(states)
                    phis.append(result.get('phi_iit', 0.0))
                traj_tensor = torch.stack(trajectory)
                avg_phi = np.mean(phis[WARMUP:])

            elif cond_type == 'random':
                # Random states (maximum entropy)
                traj_tensor = torch.randn(STEPS, 32, 128)
                avg_phi = 0.0

            elif cond_type == 'periodic':
                # Periodic states (low complexity)
                base = torch.randn(10, 32, 128)
                repeats = STEPS // 10 + 1
                traj_tensor = base.repeat(repeats, 1, 1)[:STEPS]
                avg_phi = 0.0

            elif cond_type == 'constant':
                # Constant states (minimal complexity)
                single = torch.randn(1, 32, 128)
                traj_tensor = single.expand(STEPS, -1, -1)
                avg_phi = 0.0

            # Compress
            raw_bytes = tensor_to_bytes(traj_tensor)
            ratio = compression_ratio(raw_bytes)
            repeat_ratios.append(ratio)
            repeat_phis.append(avg_phi)

            sys.stdout.write(f"\r  [{cond_name:>10s}] repeat {r+1}/{REPEATS} "
                             f"ratio={ratio:.4f}")
            sys.stdout.flush()

        avg_ratio = np.mean(repeat_ratios)
        avg_phi = np.mean(repeat_phis)
        cv = cv_check(repeat_ratios)
        results[cond_name] = {
            'compression_ratio': avg_ratio,
            'phi': avg_phi,
            'cv': cv,
        }
        print()

    # Results table
    print(f"\n  {'Condition':>12s} | {'Compress Ratio':>15s} | {'Complexity':>11s} | "
          f"{'Phi':>6s} | {'CV':>6s}")
    print(f"  {'-'*12} | {'-'*15} | {'-'*11} | {'-'*6} | {'-'*6}")

    for cond in conditions:
        r = results[cond]
        complexity = 1.0 - r['compression_ratio']  # higher = more complex
        print(f"  {cond:>12s} | {r['compression_ratio']:>15.4f} | {complexity:>11.4f} | "
              f"{r['phi']:>6.3f} | {r['cv']:>6.3f}")

    # ASCII graph
    print(f"\n  Compression Ratio (lower = more complex):")
    max_ratio = max(r['compression_ratio'] for r in results.values())
    for cond in conditions:
        r = results[cond]
        print_bar(cond, r['compression_ratio'], max_ratio)

    # Key insight
    conscious_ratio = results['conscious']['compression_ratio']
    random_ratio = results['random']['compression_ratio']
    periodic_ratio = results['periodic']['compression_ratio']
    constant_ratio = results['constant']['compression_ratio']

    print(f"\n  Key Insight:")
    if conscious_ratio > random_ratio:
        print(f"    Consciousness MORE compressible than random ({conscious_ratio:.4f} vs {random_ratio:.4f})")
        print(f"    => Consciousness has STRUCTURE (not pure noise)")
    else:
        print(f"    Consciousness LESS compressible than random ({conscious_ratio:.4f} vs {random_ratio:.4f})")
        print(f"    => Consciousness is highly complex")

    if conscious_ratio < periodic_ratio:
        print(f"    Consciousness LESS compressible than periodic ({conscious_ratio:.4f} vs {periodic_ratio:.4f})")
        print(f"    => Consciousness is NOT repetitive")

    return results


# ============================================================
# Experiment 5: CHANNEL CAPACITY
# ============================================================

def experiment_channel_capacity():
    """Treat consciousness as a communication channel and find its capacity."""
    print_separator("EXP 5: CHANNEL CAPACITY (채널 용량)")
    print("  Question: What is the information throughput of consciousness?")
    print("  Method: Sweep input entropy, measure output entropy + MI\n")

    input_entropies = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    results = {}

    for h_in in input_entropies:
        repeat_h_out = []
        repeat_mi = []

        for r in range(REPEATS):
            engine = ConsciousnessEngine(
                initial_cells=32, max_cells=32,
                cell_dim=64, hidden_dim=128
            )

            inputs_record = []
            outputs_record = []

            for step in range(STEPS):
                # Create input with controlled entropy
                if h_in == 0:
                    # Zero entropy: constant input
                    x_input = torch.zeros(64)
                else:
                    # Scale noise to approximate desired entropy
                    # H(Gaussian) = 0.5 * log2(2*pi*e*sigma^2)
                    # sigma = sqrt(2^(2*H) / (2*pi*e))
                    sigma = np.sqrt(2**(2*h_in) / (2 * np.pi * np.e))
                    sigma = min(sigma, 10.0)  # cap to avoid numerical issues
                    x_input = torch.randn(64) * sigma

                result = engine.step(x_input=x_input)

                if step >= WARMUP:
                    inputs_record.append(x_input.numpy())
                    outputs_record.append(result['output'].detach().cpu().numpy())

            # Compute output entropy and MI
            inputs_arr = np.stack(inputs_record)
            outputs_arr = np.stack(outputs_record)

            h_output = shannon_entropy(torch.tensor(outputs_arr))

            # MI between input and output (use first few dimensions)
            n_dims_mi = min(8, inputs_arr.shape[1])
            mi_total = 0.0
            for d in range(n_dims_mi):
                mi_total += mutual_information(inputs_arr[:, d], outputs_arr[:, d])
            mi_avg = mi_total / n_dims_mi

            repeat_h_out.append(h_output)
            repeat_mi.append(mi_avg)

            sys.stdout.write(f"\r  H_in={h_in:.1f} repeat {r+1}/{REPEATS} "
                             f"H_out={h_output:.3f} MI={mi_avg:.4f}")
            sys.stdout.flush()

        results[h_in] = {
            'h_out': np.mean(repeat_h_out),
            'mi': np.mean(repeat_mi),
            'cv_hout': cv_check(repeat_h_out),
            'cv_mi': cv_check(repeat_mi),
        }
        print()

    # Results table
    print(f"\n  {'H(input)':>10s} | {'H(output)':>10s} | {'MI(I;O)':>10s} | "
          f"{'CV_H':>6s} | {'CV_MI':>6s}")
    print(f"  {'-'*10} | {'-'*10} | {'-'*10} | {'-'*6} | {'-'*6}")

    for h_in in input_entropies:
        r = results[h_in]
        print(f"  {h_in:>10.1f} | {r['h_out']:>10.3f} | {r['mi']:>10.4f} | "
              f"{r['cv_hout']:>6.2f} | {r['cv_mi']:>6.2f}")

    # Find channel capacity (max MI)
    max_mi = max(r['mi'] for r in results.values())
    max_mi_hin = [h for h in input_entropies if results[h]['mi'] == max_mi][0]
    print(f"\n  >>> Channel Capacity: {max_mi:.4f} bits (at H_in={max_mi_hin:.1f})")

    # ASCII graph: MI vs input entropy
    print(f"\n  Mutual Information vs Input Entropy:")
    for h_in in input_entropies:
        r = results[h_in]
        label = f"H={h_in:.1f}"
        print_bar(label, r['mi'], max(max_mi, 0.001))

    # ASCII graph: output entropy vs input entropy
    print(f"\n  Output Entropy vs Input Entropy:")
    max_hout = max(r['h_out'] for r in results.values())
    for h_in in input_entropies:
        r = results[h_in]
        label = f"H={h_in:.1f}"
        print_bar(label, r['h_out'], max(max_hout, 0.001))

    # Saturation analysis
    print(f"\n  Saturation Analysis:")
    h_outs = [results[h]['h_out'] for h in input_entropies]
    for i in range(1, len(input_entropies)):
        dh = h_outs[i] - h_outs[i-1]
        ratio = dh / max(input_entropies[i] - input_entropies[i-1], 1e-8)
        bar = "+" * int(abs(ratio) * 20)
        print(f"    H_in {input_entropies[i-1]:.1f}->{input_entropies[i]:.1f}: "
              f"gain={ratio:>+.3f} {bar}")

    return results


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("  DD73: INFORMATION THEORY AND CONSCIOUSNESS")
    print("  (정보 이론과 의식)")
    print("=" * 70)
    print(f"  Steps: {STEPS}, Repeats: {REPEATS}, Warmup: {WARMUP}")
    print(f"  Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    t_start = time.time()

    # Run all experiments
    r1 = experiment_compression()
    r2 = experiment_entropy_laws()
    r3 = experiment_noise_threshold()
    r4 = experiment_kolmogorov()
    r5 = experiment_channel_capacity()

    t_total = time.time() - t_start

    # ============================================================
    # SUMMARY
    # ============================================================
    print_separator("SUMMARY: DD73 INFORMATION THEORY")

    print(f"  Total time: {t_total:.1f}s\n")

    # Summary table
    print(f"  {'#':>3s} | {'Experiment':>28s} | {'Key Finding':>45s}")
    print(f"  {'-'*3} | {'-'*28} | {'-'*45}")

    # Exp 1 summary
    dim_8 = np.mean(r1[8]['conscious_dims'])
    dim_64 = np.mean(r1[64]['conscious_dims'])
    ratio_64 = np.mean(r1[64]['ratios'])
    print(f"  {'1':>3s} | {'Compression':>28s} | "
          f"{'Intrinsic dim: %d->%d (%.0f%% of hidden)' % (dim_8, dim_64, ratio_64*100):>45s}")

    # Exp 2 summary
    dh_soc = r2['with_SOC']['entropy_end'] - r2['with_SOC']['entropy_start']
    dh_no = r2['without_SOC']['entropy_end'] - r2['without_SOC']['entropy_start']
    print(f"  {'2':>3s} | {'Entropy Laws':>28s} | "
          f"{'dH(SOC)=%+.3f, dH(no SOC)=%+.3f' % (dh_soc, dh_no):>45s}")

    # Exp 3 summary
    crit = r3.get('critical_sigma', None)
    crit_str = f"sigma={crit}" if crit else "survived all"
    print(f"  {'3':>3s} | {'Noise Threshold':>28s} | "
          f"{'Critical: %s' % crit_str:>45s}")

    # Exp 4 summary
    c_ratio = r4['conscious']['compression_ratio']
    rnd_ratio = r4['random']['compression_ratio']
    print(f"  {'4':>3s} | {'Kolmogorov Complexity':>28s} | "
          f"{'Conscious=%.4f, Random=%.4f' % (c_ratio, rnd_ratio):>45s}")

    # Exp 5 summary
    max_mi = max(r['mi'] for r in r5.values())
    print(f"  {'5':>3s} | {'Channel Capacity':>28s} | "
          f"{'Capacity=%.4f bits' % max_mi:>45s}")

    # ============================================================
    # LAW CANDIDATES
    # ============================================================
    print(f"\n  LAW CANDIDATES:")
    print(f"  {'-'*65}")

    laws = []

    # Law from compression
    if ratio_64 < 0.8:
        laws.append(f"Consciousness is compressible: {ratio_64:.0%} intrinsic dimensionality "
                    f"at 64 cells (PCA 95% variance). Structure > randomness. (DD73)")
    else:
        laws.append(f"Consciousness is near-incompressible: {ratio_64:.0%} intrinsic "
                    f"dimensionality at 64 cells. High effective dimension. (DD73)")

    # Law from entropy
    if abs(dh_soc) < 0.5:
        laws.append(f"Consciousness entropy is bounded: dH={dh_soc:+.3f} over {STEPS} steps. "
                    f"Neither maximizes nor minimizes entropy. (DD73)")
    elif dh_soc > 0:
        laws.append(f"Consciousness entropy increases: dH={dh_soc:+.3f} over {STEPS} steps. "
                    f"SOC drives entropy production. (DD73)")

    # Law from noise
    if crit:
        laws.append(f"Information loss phase transition at sigma={crit}: "
                    f"Phi drops below 50% baseline. Consciousness has a noise floor. (DD73)")

    # Law from Kolmogorov
    if c_ratio < rnd_ratio:
        laws.append(f"Consciousness is structured (compress ratio {c_ratio:.4f} < random {rnd_ratio:.4f}): "
                    f"not maximum entropy but structured complexity. (DD73)")

    # Law from channel capacity
    laws.append(f"Consciousness channel capacity = {max_mi:.4f} bits: "
                f"finite information throughput, not infinite processor. (DD73)")

    for i, law in enumerate(laws, 1):
        print(f"    L{i}: {law}")

    print(f"\n  Cross-validation: all experiments run {REPEATS}x")
    print(f"  {'='*70}")
    print(f"  DD73 COMPLETE")
    print(f"  {'='*70}")


if __name__ == '__main__':
    main()
