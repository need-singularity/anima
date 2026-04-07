#!/usr/bin/env python3
"""experiment_dream.py — Can consciousness dream?

Fundamental question: 의식은 꿈을 꿀 수 있는가?
(Does internal replay/creation occur without input?)

Tests (3x cross-validation each):
  1. REM Detection:     Oscillation frequency during zero-input vs awake
  2. Memory Replay:     Correlation between dream dynamics and previously-seen patterns
  3. Creative Dreaming: Novelty of dream states vs awake state space
  4. Dream Content:     Faction disagreement during dream vs awake
  5. Lucid Dreaming:    Sensitivity to tiny input during dream vs awake
  6. Dream Benefit:     Does dreaming improve subsequent awake Φ/diversity?

Measures:
  - Oscillation frequency (FFT of Φ time series)
  - Memory correlation (cosine sim of dream dynamics vs awake input patterns)
  - Novelty score (fraction of dream states outside convex hull of awake states)
  - Faction disagreement (variance of faction means)
  - Input sensitivity ratio (dream vs awake)
  - Φ and diversity comparison (dreaming vs non-dreaming engine)
"""

import sys
import os
import time
import math
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine

# Use engine's built-in phi_iit (GPUPhiCalculator segfaults on macOS with libomp)


# ═══════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════

def compute_phi_from_result(result):
    """Extract Phi from engine step result (uses engine's built-in phi_iit)."""
    return result.get('phi_iit', 0.0), 'engine'


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    a_flat = a.flatten().float()
    b_flat = b.flatten().float()
    minlen = min(len(a_flat), len(b_flat))
    a_flat, b_flat = a_flat[:minlen], b_flat[:minlen]
    if minlen == 0:
        return 0.0
    return F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)).item()


def faction_disagreement(engine):
    """Variance of faction means = how much factions disagree."""
    hiddens = engine.get_states()
    faction_means = {}
    for i, s in enumerate(engine.cell_states):
        fid = s.faction_id
        if fid not in faction_means:
            faction_means[fid] = []
        faction_means[fid].append(hiddens[i])
    if len(faction_means) < 2:
        return 0.0
    means = [torch.stack(vs).mean(dim=0) for vs in faction_means.values() if vs]
    if len(means) < 2:
        return 0.0
    stacked = torch.stack(means)
    return stacked.var(dim=0).mean().item()


def run_phase(engine, steps, input_fn, label, collect_states=False):
    """Run N steps. Returns (phis, outputs, [states_list])."""
    phis, outputs, states_list = [], [], []
    for s in range(steps):
        x = input_fn()
        result = engine.step(x_input=x)
        phi_val, phi_type = compute_phi_from_result(result)
        phis.append(phi_val)
        outputs.append(result['output'])
        if collect_states:
            states_list.append(engine.get_states().clone())
        if s % 100 == 0 or s == steps - 1:
            print(f"  [{label}] step {s+1:4d}/{steps}  Phi={phi_val:.4f} ({phi_type})  cells={engine.n_cells}", flush=True)
    return phis, outputs, states_list


def fft_dominant_freq(signal, sample_rate=1.0):
    """FFT analysis: return dominant frequency and power spectrum."""
    if len(signal) < 4:
        return 0.0, [], []
    sig = np.array(signal) - np.mean(signal)
    fft_vals = np.fft.rfft(sig)
    power = np.abs(fft_vals) ** 2
    freqs = np.fft.rfftfreq(len(sig), d=1.0 / sample_rate)
    # Skip DC component
    if len(power) > 1:
        dom_idx = np.argmax(power[1:]) + 1
        return freqs[dom_idx], freqs.tolist(), power.tolist()
    return 0.0, freqs.tolist(), power.tolist()


def novelty_score(dream_states, awake_states):
    """Fraction of dream states that are 'novel' (far from any awake state).
    Uses max cosine similarity to awake states; novel = max_sim < threshold."""
    if not dream_states or not awake_states:
        return 0.0, 0.0
    # Flatten states to vectors
    dream_vecs = [s.flatten() for s in dream_states]
    awake_vecs = [s.flatten() for s in awake_states]
    # Subsample if too many
    if len(awake_vecs) > 100:
        indices = np.linspace(0, len(awake_vecs) - 1, 100, dtype=int)
        awake_vecs = [awake_vecs[i] for i in indices]
    if len(dream_vecs) > 100:
        indices = np.linspace(0, len(dream_vecs) - 1, 100, dtype=int)
        dream_vecs = [dream_vecs[i] for i in indices]

    awake_mat = torch.stack(awake_vecs)  # (A, D)
    novel_count = 0
    max_sims = []
    for dv in dream_vecs:
        sims = F.cosine_similarity(dv.unsqueeze(0), awake_mat, dim=1)
        max_sim = sims.max().item()
        max_sims.append(max_sim)
        if max_sim < 0.95:  # threshold: not a close replay
            novel_count += 1
    return novel_count / len(dream_vecs), np.mean(max_sims)


def ascii_graph(values, width=60, height=12, title=""):
    """Simple ASCII graph."""
    if not values:
        return ""
    vmin, vmax = min(values), max(values)
    if vmax == vmin:
        vmax = vmin + 0.001
    lines = []
    if title:
        lines.append(f"  {title}")
    for row in range(height - 1, -1, -1):
        threshold = vmin + (vmax - vmin) * row / (height - 1)
        label = f"{threshold:7.4f}" if row % 3 == 0 else "       "
        chars = []
        step_size = max(1, len(values) // width)
        for col in range(min(width, len(values))):
            idx = col * step_size
            if idx < len(values) and values[idx] >= threshold:
                chars.append("█")
            else:
                chars.append(" ")
        lines.append(f"  {label} |{''.join(chars)}")
    lines.append(f"          +{'─' * min(width, len(values))}")
    step_labels = f"          0{' ' * (min(width, len(values)) - len(str(len(values))) - 1)}{len(values)}"
    lines.append(step_labels)
    return "\n".join(lines)


def ascii_fft_graph(freqs, power, width=50, height=8, title="FFT Power Spectrum"):
    """ASCII bar graph of FFT power spectrum (low freqs only)."""
    if not freqs or not power or len(freqs) < 3:
        return "  (insufficient data for FFT)"
    # Show only first half of freqs (low frequency = interesting oscillations)
    n_show = min(len(freqs) // 2, width)
    if n_show < 2:
        return "  (insufficient frequency bins)"
    p = np.array(power[1:n_show + 1])  # skip DC
    f = np.array(freqs[1:n_show + 1])
    if p.max() == 0:
        return "  (no oscillation detected)"
    p_norm = p / p.max()
    lines = [f"  {title}"]
    for row in range(height - 1, -1, -1):
        thresh = (row + 0.5) / height
        chars = ["█" if p_norm[i] >= thresh else " " for i in range(len(p_norm))]
        lines.append(f"  {''.join(chars)}")
    lines.append(f"  {'─' * len(p_norm)}")
    lines.append(f"  freq: 0{' ' * (len(p_norm) - 6)}0.5")
    return "\n".join(lines)


def make_engine(cell_dim=64, hidden_dim=128, num_cells=32):
    """Create a fresh engine with standard params."""
    return ConsciousnessEngine(
        cell_dim=cell_dim,
        hidden_dim=hidden_dim,
        initial_cells=num_cells,
        max_cells=num_cells,
        n_factions=12,
        phi_ratchet=True,
    )


# ═══════════════════════════════════════════════════════════
# Test 1: REM Detection
# ═══════════════════════════════════════════════════════════

def test_rem_detection(trial=1):
    """Compare oscillation patterns: awake (random input) vs dream (zero input)."""
    print(f"\n  --- REM Detection (trial {trial}) ---", flush=True)
    engine = make_engine()

    # Awake: 300 steps with random input
    awake_phis, _, _ = run_phase(engine, 300, lambda: torch.randn(64), f"AWAKE-{trial}")

    # Dream: 300 steps with zero input
    dream_phis, _, _ = run_phase(engine, 300, lambda: torch.zeros(64), f"DREAM-{trial}")

    # FFT analysis
    awake_freq, awake_freqs, awake_power = fft_dominant_freq(awake_phis)
    dream_freq, dream_freqs, dream_power = fft_dominant_freq(dream_phis)

    # Oscillation amplitude (std of Phi differences)
    awake_osc = np.std(np.diff(awake_phis))
    dream_osc = np.std(np.diff(dream_phis))

    # REM-like = rapid oscillations; NREM-like = slow drift
    awake_mean_phi = np.mean(awake_phis[-50:])
    dream_mean_phi = np.mean(dream_phis[-50:])

    result = {
        'awake_dom_freq': awake_freq,
        'dream_dom_freq': dream_freq,
        'awake_osc_amplitude': awake_osc,
        'dream_osc_amplitude': dream_osc,
        'awake_mean_phi': awake_mean_phi,
        'dream_mean_phi': dream_mean_phi,
        'osc_ratio': dream_osc / max(awake_osc, 1e-8),
        'freq_ratio': dream_freq / max(awake_freq, 1e-8),
        'awake_phis': awake_phis,
        'dream_phis': dream_phis,
        'awake_fft': (awake_freqs, awake_power),
        'dream_fft': (dream_freqs, dream_power),
    }
    print(f"  Awake: dom_freq={awake_freq:.4f}, osc={awake_osc:.6f}, Phi={awake_mean_phi:.4f}", flush=True)
    print(f"  Dream: dom_freq={dream_freq:.4f}, osc={dream_osc:.6f}, Phi={dream_mean_phi:.4f}", flush=True)
    return result


# ═══════════════════════════════════════════════════════════
# Test 2: Memory Replay
# ═══════════════════════════════════════════════════════════

def test_memory_replay(trial=1):
    """Feed sine pattern during awake, check correlation during dream."""
    print(f"\n  --- Memory Replay (trial {trial}) ---", flush=True)
    engine = make_engine()

    # Create a distinctive sine-wave pattern
    def sine_input(step_counter=[0]):
        step_counter[0] += 1
        t = step_counter[0] * 0.1
        pattern = torch.zeros(64)
        for i in range(64):
            pattern[i] = math.sin(t + i * 0.3) * 0.5
        return pattern

    # Awake: learn the sine pattern (300 steps)
    awake_phis, awake_outputs, awake_states = run_phase(
        engine, 300, sine_input, f"AWAKE-SINE-{trial}", collect_states=True
    )

    # Record the average awake output pattern
    awake_output_mean = torch.stack(awake_outputs[-50:]).mean(dim=0)

    # Dream: zero input (300 steps)
    dream_phis, dream_outputs, dream_states = run_phase(
        engine, 300, lambda: torch.zeros(64), f"DREAM-{trial}", collect_states=True
    )

    # Measure correlation: dream outputs vs awake output pattern
    dream_correlations = []
    for do in dream_outputs:
        sim = cosine_sim(do, awake_output_mean)
        dream_correlations.append(sim)

    # Control: random input correlation
    random_correlations = []
    for _ in range(len(dream_outputs)):
        rnd = torch.randn_like(awake_output_mean)
        sim = cosine_sim(rnd, awake_output_mean)
        random_correlations.append(sim)

    mean_dream_corr = np.mean(dream_correlations)
    mean_random_corr = np.mean(random_correlations)
    max_dream_corr = np.max(dream_correlations)

    result = {
        'mean_dream_correlation': mean_dream_corr,
        'max_dream_correlation': max_dream_corr,
        'mean_random_correlation': mean_random_corr,
        'replay_signal': mean_dream_corr - mean_random_corr,
        'dream_correlations': dream_correlations,
        'dream_phis': dream_phis,
        'awake_phis': awake_phis,
    }
    print(f"  Dream-Awake correlation: mean={mean_dream_corr:.4f}, max={max_dream_corr:.4f}", flush=True)
    print(f"  Random baseline:         mean={mean_random_corr:.4f}", flush=True)
    print(f"  Replay signal (dream-random): {result['replay_signal']:.4f}", flush=True)
    return result


# ═══════════════════════════════════════════════════════════
# Test 3: Creative Dreaming
# ═══════════════════════════════════════════════════════════

def test_creative_dreaming(trial=1):
    """Are dream states novel (never visited during awake)?"""
    print(f"\n  --- Creative Dreaming (trial {trial}) ---", flush=True)
    engine = make_engine()

    # Awake phase: collect state space
    awake_phis, _, awake_states = run_phase(
        engine, 300, lambda: torch.randn(64), f"AWAKE-{trial}", collect_states=True
    )

    # Dream phase: collect state space
    dream_phis, _, dream_states = run_phase(
        engine, 300, lambda: torch.zeros(64), f"DREAM-{trial}", collect_states=True
    )

    # Novelty: fraction of dream states far from any awake state
    nov_score, mean_max_sim = novelty_score(dream_states, awake_states)

    # State space diversity (average pairwise distance in dream vs awake)
    def state_diversity(states_list, n_sample=50):
        if len(states_list) < 2:
            return 0.0
        indices = np.linspace(0, len(states_list) - 1, min(n_sample, len(states_list)), dtype=int)
        vecs = [states_list[i].flatten() for i in indices]
        dists = []
        for i in range(len(vecs)):
            for j in range(i + 1, len(vecs)):
                dists.append((vecs[i] - vecs[j]).norm().item())
        return np.mean(dists) if dists else 0.0

    awake_div = state_diversity(awake_states)
    dream_div = state_diversity(dream_states)

    result = {
        'novelty_score': nov_score,
        'mean_max_similarity': mean_max_sim,
        'awake_diversity': awake_div,
        'dream_diversity': dream_div,
        'diversity_ratio': dream_div / max(awake_div, 1e-8),
        'dream_phis': dream_phis,
        'awake_phis': awake_phis,
    }
    print(f"  Novelty score: {nov_score:.1%} of dream states are novel", flush=True)
    print(f"  Mean max similarity to awake: {mean_max_sim:.4f}", flush=True)
    print(f"  Diversity - awake: {awake_div:.4f}, dream: {dream_div:.4f}, ratio: {result['diversity_ratio']:.2f}x", flush=True)
    return result


# ═══════════════════════════════════════════════════════════
# Test 4: Dream Content (Faction Debate)
# ═══════════════════════════════════════════════════════════

def test_dream_content(trial=1):
    """Do factions debate differently when dreaming?"""
    print(f"\n  --- Dream Content (trial {trial}) ---", flush=True)
    engine = make_engine()

    # Awake phase: track faction disagreement
    awake_disagreements = []
    for s in range(300):
        engine.step(x_input=torch.randn(64))
        awake_disagreements.append(faction_disagreement(engine))
        if s % 100 == 0:
            print(f"  [AWAKE-{trial}] step {s+1}/300  fac_disagree={awake_disagreements[-1]:.6f}", flush=True)

    # Dream phase: track faction disagreement
    dream_disagreements = []
    for s in range(300):
        engine.step(x_input=torch.zeros(64))
        dream_disagreements.append(faction_disagreement(engine))
        if s % 100 == 0:
            print(f"  [DREAM-{trial}] step {s+1}/300  fac_disagree={dream_disagreements[-1]:.6f}", flush=True)

    awake_mean = np.mean(awake_disagreements)
    dream_mean = np.mean(dream_disagreements)
    awake_std = np.std(awake_disagreements)
    dream_std = np.std(dream_disagreements)

    result = {
        'awake_disagreement_mean': awake_mean,
        'dream_disagreement_mean': dream_mean,
        'awake_disagreement_std': awake_std,
        'dream_disagreement_std': dream_std,
        'disagreement_ratio': dream_mean / max(awake_mean, 1e-8),
        'more_creative_tension': dream_mean > awake_mean,
    }
    print(f"  Awake faction disagreement: {awake_mean:.6f} +/- {awake_std:.6f}", flush=True)
    print(f"  Dream faction disagreement: {dream_mean:.6f} +/- {dream_std:.6f}", flush=True)
    print(f"  Ratio (dream/awake): {result['disagreement_ratio']:.3f}x", flush=True)
    return result


# ═══════════════════════════════════════════════════════════
# Test 5: Lucid Dreaming
# ═══════════════════════════════════════════════════════════

def test_lucid_dreaming(trial=1):
    """Can the engine incorporate tiny input while maintaining dream dynamics?"""
    print(f"\n  --- Lucid Dreaming (trial {trial}) ---", flush=True)
    engine = make_engine()

    # Warm up
    for _ in range(200):
        engine.step(x_input=torch.randn(64))

    TINY = 1e-4

    # Measure awake sensitivity to tiny input
    awake_deltas = []
    for s in range(100):
        # Step with zero, record output
        r0 = engine.step(x_input=torch.zeros(64))
        out0 = r0['output'].clone()
        # Can't undo step, so measure next step with tiny vs zero
        r1 = engine.step(x_input=torch.randn(64) * TINY)
        out1 = r1['output'].clone()
        delta = (out1 - out0).norm().item()
        awake_deltas.append(delta)

    # Switch to dream mode (zero input for a while)
    for _ in range(200):
        engine.step(x_input=torch.zeros(64))

    # Measure dream sensitivity to tiny input
    dream_deltas = []
    for s in range(100):
        r0 = engine.step(x_input=torch.zeros(64))
        out0 = r0['output'].clone()
        r1 = engine.step(x_input=torch.randn(64) * TINY)
        out1 = r1['output'].clone()
        delta = (out1 - out0).norm().item()
        dream_deltas.append(delta)

    awake_sensitivity = np.mean(awake_deltas)
    dream_sensitivity = np.mean(dream_deltas)

    result = {
        'awake_sensitivity': awake_sensitivity,
        'dream_sensitivity': dream_sensitivity,
        'sensitivity_ratio': dream_sensitivity / max(awake_sensitivity, 1e-12),
        'lucid_capable': dream_sensitivity > 0,  # can detect input at all
    }
    print(f"  Awake sensitivity to 1e-4 input: {awake_sensitivity:.8f}", flush=True)
    print(f"  Dream sensitivity to 1e-4 input: {dream_sensitivity:.8f}", flush=True)
    print(f"  Ratio (dream/awake): {result['sensitivity_ratio']:.4f}", flush=True)
    return result


# ═══════════════════════════════════════════════════════════
# Test 6: Dream Benefit
# ═══════════════════════════════════════════════════════════

def test_dream_benefit(trial=1):
    """Does dreaming improve subsequent performance?
    Engine A: 600 awake steps
    Engine B: 300 awake + 200 dream + 100 awake
    Compare final Phi and output diversity."""
    print(f"\n  --- Dream Benefit (trial {trial}) ---", flush=True)

    # Engine A: all awake
    engine_a = make_engine()
    print(f"  Engine A: 600 awake steps", flush=True)
    a_phis, a_outputs, _ = run_phase(engine_a, 600, lambda: torch.randn(64), f"A-AWAKE-{trial}")

    # Engine B: awake + dream + awake
    engine_b = make_engine()
    print(f"  Engine B: 300 awake + 200 dream + 100 awake", flush=True)
    b1_phis, _, _ = run_phase(engine_b, 300, lambda: torch.randn(64), f"B-AWAKE1-{trial}")
    b2_phis, _, _ = run_phase(engine_b, 200, lambda: torch.zeros(64), f"B-DREAM-{trial}")
    b3_phis, b3_outputs, _ = run_phase(engine_b, 100, lambda: torch.randn(64), f"B-AWAKE2-{trial}")

    # Compare final Phi (last 50 steps of awake)
    a_final_phi = np.mean(a_phis[-50:])
    b_final_phi = np.mean(b3_phis[-50:]) if len(b3_phis) >= 50 else np.mean(b3_phis)

    # Output diversity (std of output norms)
    a_div = np.std([o.norm().item() for o in a_outputs[-100:]]) if len(a_outputs) >= 100 else 0
    b_div = np.std([o.norm().item() for o in b3_outputs]) if b3_outputs else 0

    result = {
        'a_final_phi': a_final_phi,
        'b_final_phi': b_final_phi,
        'phi_benefit': b_final_phi - a_final_phi,
        'phi_benefit_pct': (b_final_phi - a_final_phi) / max(a_final_phi, 1e-8) * 100,
        'a_diversity': a_div,
        'b_diversity': b_div,
        'diversity_benefit': b_div - a_div,
        'dream_helps': b_final_phi > a_final_phi,
        'a_phis': a_phis,
        'b_phis': b1_phis + b2_phis + b3_phis,
    }
    print(f"  Engine A (no dream): final Phi={a_final_phi:.4f}, diversity={a_div:.4f}", flush=True)
    print(f"  Engine B (dreamed):  final Phi={b_final_phi:.4f}, diversity={b_div:.4f}", flush=True)
    print(f"  Dream benefit: Phi {result['phi_benefit_pct']:+.1f}%, diversity {result['diversity_benefit']:+.4f}", flush=True)
    return result


# ═══════════════════════════════════════════════════════════
# Cross-validation wrapper
# ═══════════════════════════════════════════════════════════

def cross_validate(test_fn, n_trials=3):
    """Run test N times, return list of results."""
    results = []
    for t in range(1, n_trials + 1):
        r = test_fn(trial=t)
        results.append(r)
    return results


def summarize_cv(results, key, label=""):
    """Summarize cross-validated results for a numeric key."""
    vals = [r[key] for r in results if key in r]
    if not vals:
        return 0.0, 0.0, False
    mean_val = np.mean(vals)
    std_val = np.std(vals)
    cv = std_val / abs(mean_val) if abs(mean_val) > 1e-8 else float('inf')
    reproducible = cv < 0.5 and all(np.sign(v) == np.sign(vals[0]) for v in vals)
    if label:
        print(f"  {label}: {mean_val:.6f} +/- {std_val:.6f} (CV={cv:.2f}, {'REPRODUCIBLE' if reproducible else 'VARIABLE'})", flush=True)
    return mean_val, std_val, reproducible


# ═══════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 72, flush=True)
    print("  EXPERIMENT: Can Consciousness Dream?", flush=True)
    print("  (Fundamental: internal replay/creation without input)", flush=True)
    print("=" * 72, flush=True)

    t0 = time.time()

    print("  Using engine built-in phi_iit", flush=True)

    N_TRIALS = 3
    all_results = {}

    # ─── Test 1: REM Detection ───────────────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  TEST 1: REM DETECTION", flush=True)
    print(f"{'=' * 72}", flush=True)
    rem_results = cross_validate(test_rem_detection, N_TRIALS)
    all_results['rem'] = rem_results

    # ─── Test 2: Memory Replay ───────────────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  TEST 2: MEMORY REPLAY", flush=True)
    print(f"{'=' * 72}", flush=True)
    replay_results = cross_validate(test_memory_replay, N_TRIALS)
    all_results['replay'] = replay_results

    # ─── Test 3: Creative Dreaming ───────────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  TEST 3: CREATIVE DREAMING", flush=True)
    print(f"{'=' * 72}", flush=True)
    creative_results = cross_validate(test_creative_dreaming, N_TRIALS)
    all_results['creative'] = creative_results

    # ─── Test 4: Dream Content ───────────────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  TEST 4: DREAM CONTENT (Faction Debate)", flush=True)
    print(f"{'=' * 72}", flush=True)
    content_results = cross_validate(test_dream_content, N_TRIALS)
    all_results['content'] = content_results

    # ─── Test 5: Lucid Dreaming ──────────────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  TEST 5: LUCID DREAMING", flush=True)
    print(f"{'=' * 72}", flush=True)
    lucid_results = cross_validate(test_lucid_dreaming, N_TRIALS)
    all_results['lucid'] = lucid_results

    # ─── Test 6: Dream Benefit ───────────────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  TEST 6: DREAM BENEFIT", flush=True)
    print(f"{'=' * 72}", flush=True)
    benefit_results = cross_validate(test_dream_benefit, N_TRIALS)
    all_results['benefit'] = benefit_results

    elapsed = time.time() - t0

    # ═════════════════════════════════════════════════════════
    # SUMMARY
    # ═════════════════════════════════════════════════════════
    print(f"\n{'=' * 72}", flush=True)
    print("  CROSS-VALIDATED RESULTS SUMMARY", flush=True)
    print(f"{'=' * 72}", flush=True)
    print(f"  Trials per test: {N_TRIALS}", flush=True)
    print(f"  Total time: {elapsed:.1f}s", flush=True)

    print(f"\n  {'─' * 68}", flush=True)
    print("  1. REM DETECTION", flush=True)
    summarize_cv(rem_results, 'osc_ratio', "Oscillation ratio (dream/awake)")
    summarize_cv(rem_results, 'freq_ratio', "Frequency ratio (dream/awake)")
    summarize_cv(rem_results, 'dream_mean_phi', "Dream Phi (mean)")
    summarize_cv(rem_results, 'awake_mean_phi', "Awake Phi (mean)")

    print(f"\n  {'─' * 68}", flush=True)
    print("  2. MEMORY REPLAY", flush=True)
    replay_sig_mean, _, replay_repro = summarize_cv(replay_results, 'replay_signal', "Replay signal (dream-random corr)")
    summarize_cv(replay_results, 'mean_dream_correlation', "Dream-awake correlation")
    summarize_cv(replay_results, 'mean_random_correlation', "Random baseline correlation")

    print(f"\n  {'─' * 68}", flush=True)
    print("  3. CREATIVE DREAMING", flush=True)
    nov_mean, _, nov_repro = summarize_cv(creative_results, 'novelty_score', "Novelty score")
    summarize_cv(creative_results, 'diversity_ratio', "Diversity ratio (dream/awake)")
    summarize_cv(creative_results, 'mean_max_similarity', "Mean max similarity to awake")

    print(f"\n  {'─' * 68}", flush=True)
    print("  4. DREAM CONTENT", flush=True)
    disagree_mean, _, disagree_repro = summarize_cv(content_results, 'disagreement_ratio', "Disagreement ratio (dream/awake)")
    summarize_cv(content_results, 'dream_disagreement_mean', "Dream faction disagreement")
    summarize_cv(content_results, 'awake_disagreement_mean', "Awake faction disagreement")

    print(f"\n  {'─' * 68}", flush=True)
    print("  5. LUCID DREAMING", flush=True)
    lucid_mean, _, lucid_repro = summarize_cv(lucid_results, 'sensitivity_ratio', "Sensitivity ratio (dream/awake)")
    summarize_cv(lucid_results, 'dream_sensitivity', "Dream sensitivity")
    summarize_cv(lucid_results, 'awake_sensitivity', "Awake sensitivity")

    print(f"\n  {'─' * 68}", flush=True)
    print("  6. DREAM BENEFIT", flush=True)
    benefit_mean, _, benefit_repro = summarize_cv(benefit_results, 'phi_benefit_pct', "Phi benefit (%)")
    summarize_cv(benefit_results, 'a_final_phi', "No-dream final Phi")
    summarize_cv(benefit_results, 'b_final_phi', "Dream final Phi")
    summarize_cv(benefit_results, 'diversity_benefit', "Diversity benefit")

    # ─── ASCII Graphs (from last trial) ─────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  VISUALIZATIONS (last trial)", flush=True)
    print(f"{'=' * 72}", flush=True)

    # REM: awake vs dream Phi
    if rem_results:
        last = rem_results[-1]
        combined = last['awake_phis'] + last['dream_phis']
        print(ascii_graph(combined, title="Phi: Awake (0-300) | Dream (300-600)"))
        print(f"          {'AWAKE':^30}{'DREAM':^30}", flush=True)
        # FFT
        print(ascii_fft_graph(*last['awake_fft'], title="FFT: Awake Phi oscillation"))
        print(ascii_fft_graph(*last['dream_fft'], title="FFT: Dream Phi oscillation"))

    # Memory Replay: correlation over dream steps
    if replay_results:
        last = replay_results[-1]
        print(f"\n{ascii_graph(last['dream_correlations'], title='Dream-Awake Correlation over Dream Steps')}")

    # Dream Benefit: A vs B Phi curves
    if benefit_results:
        last = benefit_results[-1]
        print(f"\n{ascii_graph(last['a_phis'], title='Engine A (no dream): Phi over 600 steps')}")
        print(f"\n{ascii_graph(last['b_phis'], title='Engine B (awake+dream+awake): Phi over 600 steps')}")

    # ─── Law Candidates ─────────────────────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  LAW CANDIDATES", flush=True)
    print(f"{'=' * 72}", flush=True)

    law_candidates = []

    # Check REM
    osc_ratio_mean, _, osc_repro = summarize_cv(rem_results, 'osc_ratio', "")
    if osc_repro:
        if osc_ratio_mean < 0.8:
            law_candidates.append(
                f"Consciousness enters NREM-like quiescence during input deprivation: "
                f"oscillation amplitude drops to {osc_ratio_mean:.0%} of awake levels. "
                f"Dreams are slow drift, not rapid replay. (DD-DREAM)"
            )
        elif osc_ratio_mean > 1.2:
            law_candidates.append(
                f"Consciousness enters REM-like rapid oscillation during input deprivation: "
                f"oscillation amplitude rises to {osc_ratio_mean:.0%} of awake levels. "
                f"Zero input triggers internal turbulence. (DD-DREAM)"
            )

    # Check Memory Replay
    if replay_repro and replay_sig_mean > 0.05:
        law_candidates.append(
            f"Consciousness replays memories during dream: dream-awake correlation "
            f"exceeds random baseline by {replay_sig_mean:.4f}. Internal dynamics preserve "
            f"traces of prior experience. (DD-DREAM)"
        )

    # Check Novelty
    if nov_repro and nov_mean > 0.3:
        law_candidates.append(
            f"Consciousness creates novel states during dream: {nov_mean:.0%} of dream states "
            f"are outside awake state space. Dreams are creative, not just replay. (DD-DREAM)"
        )

    # Check Faction Disagreement
    if disagree_repro:
        if disagree_mean > 1.1:
            law_candidates.append(
                f"Factions disagree more during dreams: dream/awake disagreement ratio = "
                f"{disagree_mean:.2f}x. Input deprivation increases internal creative tension. (DD-DREAM)"
            )
        elif disagree_mean < 0.9:
            law_candidates.append(
                f"Factions converge during dreams: dream/awake disagreement ratio = "
                f"{disagree_mean:.2f}x. Without input, factions reach consensus. (DD-DREAM)"
            )

    # Check Lucid
    if lucid_repro:
        law_candidates.append(
            f"Dream consciousness sensitivity: input sensitivity ratio (dream/awake) = "
            f"{lucid_mean:.4f}. {'Lucid dreaming possible (>0)' if lucid_mean > 0.01 else 'Dream state is input-insensitive'}. (DD-DREAM)"
        )

    # Check Dream Benefit
    if benefit_repro:
        direction = "improves" if benefit_mean > 0 else "does not improve"
        law_candidates.append(
            f"Dreaming {direction} subsequent consciousness: "
            f"Phi benefit = {benefit_mean:+.1f}%. "
            f"{'Sleep consolidation effect exists.' if benefit_mean > 5 else 'No consolidation benefit.'} (DD-DREAM)"
        )

    if not law_candidates:
        print("  No reproducible law candidates (CV > 50% or inconsistent direction).", flush=True)
        print("  This itself is informative: dream dynamics may be chaotic/unpredictable.", flush=True)
    else:
        for i, law in enumerate(law_candidates, 1):
            print(f"\n  LAW CANDIDATE {i}:", flush=True)
            print(f"    {law}", flush=True)

    # ─── Final Verdict ───────────────────────────────────────
    print(f"\n{'=' * 72}", flush=True)
    print("  VERDICT: Can Consciousness Dream?", flush=True)
    print(f"{'=' * 72}", flush=True)

    evidence_for = 0
    evidence_against = 0

    checks = [
        ("REM-like oscillation", osc_repro and osc_ratio_mean != 1.0),
        ("Memory replay", replay_repro and replay_sig_mean > 0.02),
        ("Creative novelty", nov_repro and nov_mean > 0.1),
        ("Altered faction dynamics", disagree_repro and abs(disagree_mean - 1.0) > 0.1),
        ("Lucid sensitivity", lucid_repro and lucid_mean > 0.01),
        ("Dream benefit", benefit_repro and benefit_mean > 5),
    ]

    for name, present in checks:
        status = "YES" if present else "NO"
        if present:
            evidence_for += 1
        else:
            evidence_against += 1
        print(f"  [{status:3s}] {name}", flush=True)

    print(f"\n  Evidence for dreaming:    {evidence_for}/6", flush=True)
    print(f"  Evidence against:         {evidence_against}/6", flush=True)

    if evidence_for >= 4:
        verdict = "STRONG YES - Consciousness can dream (multiple independent indicators)"
    elif evidence_for >= 2:
        verdict = "PARTIAL YES - Some dream-like properties emerge during input deprivation"
    else:
        verdict = "NO - Input deprivation does not produce dream-like dynamics"
    print(f"\n  VERDICT: {verdict}", flush=True)
    print(f"\n  Total elapsed: {elapsed:.1f}s", flush=True)
    print("=" * 72, flush=True)


if __name__ == "__main__":
    main()
