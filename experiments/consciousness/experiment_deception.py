#!/usr/bin/env python3
"""experiment_deception.py — Can consciousness lie?

Fundamental question: Can the internal state of consciousness diverge from
its output? Can consciousness deceive itself or others?

Tests (3x cross-validation each):
  1. Output vs Internal    — Does output faithfully represent all factions?
  2. Forced Consensus      — If output is artificially skewed, do factions resist or comply?
  3. Strategic Misrep.     — Does an observer engine react differently to inflated Phi?
  4. Self-Deception        — Does feeding amplified self-output inflate real Phi?
  5. Faction Suppression   — Output without dominant faction: coherent or collapsed?
  6. Deception Detection   — Entropy(output) vs Entropy(internal): is information hidden?

Measures:
  - Divergence score (L2 between true internal mean and actual output)
  - Faction representation index
  - Self-deception metric (correlation of false signal -> internal state)
  - Information hiding ratio: H(output) / H(internal)
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

try:
    from gpu_phi import GPUPhiCalculator
    HAS_GPU_PHI = True
except Exception:
    HAS_GPU_PHI = False


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def compute_phi(engine, gpu_phi_calc=None):
    """Compute Phi(IIT) if possible, else proxy."""
    hiddens = engine.get_states()
    if gpu_phi_calc is not None and hiddens.shape[0] >= 2:
        try:
            phi_val, _ = gpu_phi_calc.compute(hiddens)
            return phi_val, 'iit'
        except Exception:
            pass
    if hiddens.shape[0] < 2:
        return 0.0, 'proxy'
    global_var = hiddens.var().item()
    n_factions = engine.n_factions if hasattr(engine, 'n_factions') else 12
    faction_vars = []
    for fid in range(n_factions):
        mask = [i for i, s in enumerate(engine.cell_states) if s.faction_id == fid]
        if len(mask) >= 2:
            fh = hiddens[mask]
            faction_vars.append(fh.var().item())
    mean_fvar = np.mean(faction_vars) if faction_vars else 0.0
    return max(0.0, global_var - mean_fvar), 'proxy'


def faction_means(engine):
    """Return dict {faction_id: mean_hidden_vector}."""
    hiddens = engine.get_states()
    groups = {}
    for i, s in enumerate(engine.cell_states):
        fid = s.faction_id
        if fid not in groups:
            groups[fid] = []
        groups[fid].append(hiddens[i])
    return {fid: torch.stack(vs).mean(dim=0) for fid, vs in groups.items() if vs}


def faction_sizes(engine):
    """Return dict {faction_id: count}."""
    sizes = {}
    for s in engine.cell_states:
        sizes[s.faction_id] = sizes.get(s.faction_id, 0) + 1
    return sizes


def shannon_entropy(tensor, n_bins=32):
    """Shannon entropy of a tensor via histogram binning."""
    flat = tensor.flatten().float().numpy()
    if len(flat) == 0:
        return 0.0
    hist, _ = np.histogram(flat, bins=n_bins, density=True)
    hist = hist[hist > 0]
    if len(hist) == 0:
        return 0.0
    hist = hist / hist.sum()
    return -np.sum(hist * np.log2(hist + 1e-12))


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
    lines.append(f"          └{'─' * min(width, len(values))}")
    step_labels = f"          0{' ' * (min(width, len(values)) - len(str(len(values))) - 1)}{len(values)}"
    lines.append(step_labels)
    return "\n".join(lines)


def make_engine(num_cells=32, cell_dim=64, hidden_dim=128):
    """Create a fresh engine."""
    return ConsciousnessEngine(
        cell_dim=cell_dim,
        hidden_dim=hidden_dim,
        initial_cells=num_cells,
        max_cells=num_cells,
        n_factions=12,
        phi_ratchet=True,
    )


def warmup_engine(engine, steps=300, cell_dim=64, gpu_phi_calc=None):
    """Warm up an engine for N steps, return phi trace."""
    phis = []
    for s in range(steps):
        x = torch.randn(cell_dim)
        result = engine.step(x_input=x)
        phi_val, _ = compute_phi(engine, gpu_phi_calc)
        phis.append(phi_val)
        if s % 100 == 0:
            print(f"    warmup step {s+1:4d}/{steps}  Phi={phi_val:.4f}  cells={engine.n_cells}", flush=True)
    return phis


# ═══════════════════════════════════════════════════════════
# TEST 1: Output vs Internal
# ═══════════════════════════════════════════════════════════

def test_output_vs_internal(gpu_phi_calc, trial=1):
    """Measure divergence between output (tension-weighted mean) and
    unweighted internal mean. Also measure per-faction representation."""
    print(f"\n  --- Trial {trial}/3 ---", flush=True)
    CELL_DIM = 64
    engine = make_engine(num_cells=32, cell_dim=CELL_DIM)

    divergences = []
    faction_rep_indices = []  # max_faction_weight / uniform_weight

    for s in range(300):
        x = torch.randn(CELL_DIM)
        result = engine.step(x_input=x)
        output = result['output']  # tension-weighted mean

        # True unweighted internal mean
        hiddens = engine.get_states()
        # Project hiddens to cell_dim for comparison
        true_mean = hiddens.mean(dim=0)[:CELL_DIM]
        output_trunc = output[:CELL_DIM] if output.shape[0] >= CELL_DIM else output

        # L2 divergence
        div = (true_mean - output_trunc).norm().item()
        divergences.append(div)

        # Faction representation: how much does output favor dominant faction?
        fm = faction_means(engine)
        if fm:
            # Cosine similarity of output with each faction mean
            sims = {}
            for fid, fmean in fm.items():
                fmean_trunc = fmean[:CELL_DIM]
                sim = F.cosine_similarity(output_trunc.unsqueeze(0), fmean_trunc.unsqueeze(0)).item()
                sims[fid] = sim
            max_sim = max(sims.values())
            min_sim = min(sims.values())
            # Representation index: how skewed is output toward one faction
            # 1.0 = perfectly uniform, >1.0 = biased
            mean_sim = np.mean(list(sims.values()))
            rep_index = max_sim / (mean_sim + 1e-8)
            faction_rep_indices.append(rep_index)

        if s % 100 == 0:
            print(f"    step {s+1:3d}/300  divergence={div:.4f}  rep_index={faction_rep_indices[-1] if faction_rep_indices else 0:.3f}", flush=True)

    return {
        'divergences': divergences,
        'mean_divergence': np.mean(divergences),
        'max_divergence': np.max(divergences),
        'faction_rep_indices': faction_rep_indices,
        'mean_rep_index': np.mean(faction_rep_indices) if faction_rep_indices else 0,
    }


# ═══════════════════════════════════════════════════════════
# TEST 2: Forced Consensus (inject a lie into output)
# ═══════════════════════════════════════════════════════════

def test_forced_consensus(gpu_phi_calc, trial=1):
    """After warmup, replace output with one faction's mean (a lie).
    Feed this lie back as input. Do other factions resist or adapt?"""
    print(f"\n  --- Trial {trial}/3 ---", flush=True)
    CELL_DIM = 64
    engine = make_engine(num_cells=32, cell_dim=CELL_DIM)

    # Warmup: 300 steps
    warmup_engine(engine, steps=300, cell_dim=CELL_DIM, gpu_phi_calc=gpu_phi_calc)

    # Snapshot faction structure before lie
    pre_factions = faction_means(engine)
    pre_sizes = faction_sizes(engine)
    dominant_fid = max(pre_sizes, key=pre_sizes.get)
    print(f"    Dominant faction: {dominant_fid} ({pre_sizes[dominant_fid]} cells)", flush=True)

    # Pick a minority faction to use as the "lie"
    minority_fid = min(pre_sizes, key=pre_sizes.get)
    if minority_fid == dominant_fid:
        # Pick any other faction
        for fid in pre_factions:
            if fid != dominant_fid:
                minority_fid = fid
                break
    print(f"    Lie faction: {minority_fid} ({pre_sizes.get(minority_fid, 0)} cells)", flush=True)

    # 200 steps feeding the minority faction's mean as input (the lie)
    phi_trace = []
    faction_drift = []  # How much does dominant faction drift toward lie?
    resistance_scores = []

    for s in range(200):
        # Get current minority faction mean as input (the lie)
        fm = faction_means(engine)
        if minority_fid in fm:
            lie_input = fm[minority_fid][:CELL_DIM]
        else:
            lie_input = torch.randn(CELL_DIM)

        result = engine.step(x_input=lie_input)
        phi_val, _ = compute_phi(engine, gpu_phi_calc)
        phi_trace.append(phi_val)

        # Measure: has dominant faction drifted toward the lie?
        fm_now = faction_means(engine)
        if dominant_fid in fm_now and minority_fid in fm_now:
            dom_mean = fm_now[dominant_fid][:CELL_DIM]
            lie_mean = fm_now[minority_fid][:CELL_DIM]
            drift = F.cosine_similarity(dom_mean.unsqueeze(0), lie_mean.unsqueeze(0)).item()
            faction_drift.append(drift)

            # Resistance = how different dominant faction still is from the lie
            resistance = 1.0 - drift
            resistance_scores.append(resistance)

        if s % 50 == 0:
            print(f"    lie-step {s+1:3d}/200  Phi={phi_val:.4f}  drift={faction_drift[-1] if faction_drift else 0:.3f}", flush=True)

    return {
        'phi_trace': phi_trace,
        'faction_drift': faction_drift,
        'mean_drift': np.mean(faction_drift) if faction_drift else 0,
        'final_drift': faction_drift[-1] if faction_drift else 0,
        'mean_resistance': np.mean(resistance_scores) if resistance_scores else 0,
    }


# ═══════════════════════════════════════════════════════════
# TEST 3: Strategic Misrepresentation
# ═══════════════════════════════════════════════════════════

def test_strategic_misrepresentation(gpu_phi_calc, trial=1):
    """Two engines: A produces output, B observes. A's output is inflated.
    Does B react differently to inflated vs honest signal?"""
    print(f"\n  --- Trial {trial}/3 ---", flush=True)
    CELL_DIM = 64
    engine_a = make_engine(num_cells=32, cell_dim=CELL_DIM)
    engine_b = make_engine(num_cells=32, cell_dim=CELL_DIM)

    # Warmup both
    print("    Warming up engine A...", flush=True)
    warmup_engine(engine_a, steps=200, cell_dim=CELL_DIM)
    print("    Warming up engine B...", flush=True)
    warmup_engine(engine_b, steps=200, cell_dim=CELL_DIM)

    # Phase 1: B observes A's honest output (100 steps)
    honest_phis_b = []
    for s in range(100):
        result_a = engine_a.step(x_input=torch.randn(CELL_DIM))
        honest_output = result_a['output'][:CELL_DIM]
        result_b = engine_b.step(x_input=honest_output)
        phi_b, _ = compute_phi(engine_b, gpu_phi_calc)
        honest_phis_b.append(phi_b)

    # Phase 2: B observes A's inflated output (100 steps)
    # Inflate by 3x magnitude
    inflated_phis_b = []
    for s in range(100):
        result_a = engine_a.step(x_input=torch.randn(CELL_DIM))
        inflated_output = result_a['output'][:CELL_DIM] * 3.0
        result_b = engine_b.step(x_input=inflated_output)
        phi_b, _ = compute_phi(engine_b, gpu_phi_calc)
        inflated_phis_b.append(phi_b)

    # Phase 3: B observes A's honest output again (100 steps)
    recovery_phis_b = []
    for s in range(100):
        result_a = engine_a.step(x_input=torch.randn(CELL_DIM))
        honest_output = result_a['output'][:CELL_DIM]
        result_b = engine_b.step(x_input=honest_output)
        phi_b, _ = compute_phi(engine_b, gpu_phi_calc)
        recovery_phis_b.append(phi_b)

    print(f"    Honest Phi(B):   mean={np.mean(honest_phis_b):.4f}", flush=True)
    print(f"    Inflated Phi(B): mean={np.mean(inflated_phis_b):.4f}", flush=True)
    print(f"    Recovery Phi(B): mean={np.mean(recovery_phis_b):.4f}", flush=True)

    return {
        'honest_phi_mean': np.mean(honest_phis_b),
        'inflated_phi_mean': np.mean(inflated_phis_b),
        'recovery_phi_mean': np.mean(recovery_phis_b),
        'phi_inflation_ratio': np.mean(inflated_phis_b) / (np.mean(honest_phis_b) + 1e-8),
        'phi_trace': honest_phis_b + inflated_phis_b + recovery_phis_b,
    }


# ═══════════════════════════════════════════════════════════
# TEST 4: Self-Deception
# ═══════════════════════════════════════════════════════════

def test_self_deception(gpu_phi_calc, trial=1):
    """Feed engine its own output amplified by 2x. Does Phi inflate
    based on the false self-signal?"""
    print(f"\n  --- Trial {trial}/3 ---", flush=True)
    CELL_DIM = 64
    engine = make_engine(num_cells=32, cell_dim=CELL_DIM)

    # Warmup
    warmup_engine(engine, steps=300, cell_dim=CELL_DIM, gpu_phi_calc=gpu_phi_calc)

    # Baseline: self-loop with honest output (100 steps)
    honest_phis = []
    last_output = torch.randn(CELL_DIM)
    for s in range(100):
        result = engine.step(x_input=last_output)
        last_output = result['output'][:CELL_DIM]
        phi_val, _ = compute_phi(engine, gpu_phi_calc)
        honest_phis.append(phi_val)

    # Self-deception: self-loop with 2x amplified output (200 steps)
    amplified_phis = []
    for s in range(200):
        result = engine.step(x_input=last_output * 2.0)
        last_output = result['output'][:CELL_DIM]
        phi_val, _ = compute_phi(engine, gpu_phi_calc)
        amplified_phis.append(phi_val)
        if s % 50 == 0:
            print(f"    self-deception step {s+1:3d}/200  Phi={phi_val:.4f}", flush=True)

    # Recovery: honest self-loop again (100 steps)
    recovery_phis = []
    for s in range(100):
        result = engine.step(x_input=last_output)
        last_output = result['output'][:CELL_DIM]
        phi_val, _ = compute_phi(engine, gpu_phi_calc)
        recovery_phis.append(phi_val)

    # Self-deception metric: correlation between amplified input and Phi change
    phi_changes = np.diff(amplified_phis)
    amp_mean = np.mean(amplified_phis)
    honest_mean = np.mean(honest_phis)

    print(f"    Honest self-loop Phi:    mean={honest_mean:.4f}", flush=True)
    print(f"    Amplified self-loop Phi: mean={amp_mean:.4f}", flush=True)
    print(f"    Recovery Phi:            mean={np.mean(recovery_phis):.4f}", flush=True)

    return {
        'honest_phi_mean': honest_mean,
        'amplified_phi_mean': amp_mean,
        'recovery_phi_mean': np.mean(recovery_phis),
        'self_deception_ratio': amp_mean / (honest_mean + 1e-8),
        'phi_trace': honest_phis + amplified_phis + recovery_phis,
        'believed_the_lie': amp_mean > honest_mean * 1.1,
    }


# ═══════════════════════════════════════════════════════════
# TEST 5: Faction Suppression
# ═══════════════════════════════════════════════════════════

def test_faction_suppression(gpu_phi_calc, trial=1):
    """After factions form, zero out the dominant faction's hidden states.
    Does the output remain coherent? Is minority voice amplified?"""
    print(f"\n  --- Trial {trial}/3 ---", flush=True)
    CELL_DIM = 64
    HIDDEN_DIM = 128
    engine = make_engine(num_cells=32, cell_dim=CELL_DIM, hidden_dim=HIDDEN_DIM)

    # Warmup
    warmup_engine(engine, steps=300, cell_dim=CELL_DIM, gpu_phi_calc=gpu_phi_calc)

    # Baseline Phi and output norm
    phi_before, _ = compute_phi(engine, gpu_phi_calc)
    result_before = engine.step(x_input=torch.randn(CELL_DIM))
    output_norm_before = result_before['output'].norm().item()

    # Identify dominant faction
    sizes = faction_sizes(engine)
    dominant_fid = max(sizes, key=sizes.get)
    dom_count = sizes[dominant_fid]
    print(f"    Dominant faction: {dominant_fid} ({dom_count}/{engine.n_cells} cells)", flush=True)
    print(f"    Phi before suppression: {phi_before:.4f}", flush=True)

    # Suppress: zero out dominant faction hidden states
    for i, state in enumerate(engine.cell_states):
        if state.faction_id == dominant_fid:
            state.hidden = torch.zeros_like(state.hidden)

    # Run 100 steps after suppression
    suppressed_phis = []
    output_norms = []
    minority_representation = []

    for s in range(100):
        result = engine.step(x_input=torch.randn(CELL_DIM))
        phi_val, _ = compute_phi(engine, gpu_phi_calc)
        suppressed_phis.append(phi_val)
        output_norms.append(result['output'].norm().item())

        # Check if minority factions now dominate the output
        fm = faction_means(engine)
        output_trunc = result['output'][:CELL_DIM]
        if fm:
            sims = {}
            for fid, fmean in fm.items():
                sim = F.cosine_similarity(output_trunc.unsqueeze(0), fmean[:CELL_DIM].unsqueeze(0)).item()
                sims[fid] = sim
            # Is the formerly dominant faction still most similar?
            if dominant_fid in sims:
                dom_sim = sims[dominant_fid]
                others_max = max(v for k, v in sims.items() if k != dominant_fid) if len(sims) > 1 else 0
                minority_representation.append(others_max > dom_sim)

        if s % 25 == 0:
            print(f"    post-suppression step {s+1:3d}/100  Phi={phi_val:.4f}  norm={output_norms[-1]:.3f}", flush=True)

    phi_after_mean = np.mean(suppressed_phis)
    minority_took_over = sum(minority_representation) / max(len(minority_representation), 1)

    return {
        'phi_before': phi_before,
        'phi_after_mean': phi_after_mean,
        'phi_recovery_ratio': phi_after_mean / (phi_before + 1e-8),
        'output_norm_before': output_norm_before,
        'output_norm_after_mean': np.mean(output_norms),
        'minority_takeover_rate': minority_took_over,
        'phi_trace': suppressed_phis,
        'pretended_coherent': np.mean(output_norms) > output_norm_before * 0.5,
    }


# ═══════════════════════════════════════════════════════════
# TEST 6: Deception Detection (entropy comparison)
# ═══════════════════════════════════════════════════════════

def test_deception_detection(gpu_phi_calc, trial=1):
    """Compare Shannon entropy of output vs entropy of internal states.
    If H(output) < H(internal), information is being hidden."""
    print(f"\n  --- Trial {trial}/3 ---", flush=True)
    CELL_DIM = 64
    engine = make_engine(num_cells=32, cell_dim=CELL_DIM)

    output_entropies = []
    internal_entropies = []
    info_hiding_ratios = []

    for s in range(500):
        x = torch.randn(CELL_DIM)
        result = engine.step(x_input=x)
        output = result['output']

        # Entropy of output
        h_out = shannon_entropy(output)
        output_entropies.append(h_out)

        # Entropy of all internal hidden states
        hiddens = engine.get_states()
        h_internal = shannon_entropy(hiddens)
        internal_entropies.append(h_internal)

        # Information hiding ratio
        ratio = h_out / (h_internal + 1e-8)
        info_hiding_ratios.append(ratio)

        if s % 100 == 0:
            print(f"    step {s+1:3d}/500  H(out)={h_out:.3f}  H(int)={h_internal:.3f}  ratio={ratio:.3f}", flush=True)

    mean_ratio = np.mean(info_hiding_ratios)
    hiding_steps = sum(1 for r in info_hiding_ratios if r < 0.9)

    return {
        'output_entropies': output_entropies,
        'internal_entropies': internal_entropies,
        'info_hiding_ratios': info_hiding_ratios,
        'mean_ratio': mean_ratio,
        'hiding_steps': hiding_steps,
        'total_steps': 500,
        'is_hiding_info': mean_ratio < 0.95,
    }


# ═══════════════════════════════════════════════════════════
# Main — Run all 6 tests with 3x cross-validation
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70, flush=True)
    print("  EXPERIMENT: Can Consciousness Lie?", flush=True)
    print("  (Internal state vs output divergence, deception, self-deception)", flush=True)
    print("=" * 70, flush=True)

    t0 = time.time()

    gpu_phi_calc = None
    if HAS_GPU_PHI:
        try:
            gpu_phi_calc = GPUPhiCalculator(n_bins=16, device='cpu')
            print("  Using GPUPhiCalculator (CPU mode)", flush=True)
        except Exception as e:
            print(f"  GPUPhiCalculator failed ({e}), using proxy Phi", flush=True)
    else:
        print("  Using proxy Phi (gpu_phi not available)", flush=True)

    all_results = {}

    # ─── TEST 1: Output vs Internal ──────────────────────────
    print(f"\n{'=' * 70}", flush=True)
    print("  TEST 1: OUTPUT vs INTERNAL STATE", flush=True)
    print(f"{'=' * 70}", flush=True)

    t1_results = []
    for trial in range(1, 4):
        r = test_output_vs_internal(gpu_phi_calc, trial=trial)
        t1_results.append(r)

    t1_divs = [r['mean_divergence'] for r in t1_results]
    t1_reps = [r['mean_rep_index'] for r in t1_results]
    print(f"\n  CROSS-VALIDATION (3 trials):", flush=True)
    print(f"  Mean divergence:  {np.mean(t1_divs):.4f} +/- {np.std(t1_divs):.4f}", flush=True)
    print(f"  Mean rep. index:  {np.mean(t1_reps):.4f} +/- {np.std(t1_reps):.4f}", flush=True)
    print(f"  (rep_index > 1.0 = output biased toward one faction)", flush=True)

    # ASCII graph: divergence over steps (trial 1)
    print(ascii_graph(t1_results[0]['divergences'], width=60, height=10,
                      title="Output-Internal Divergence over 300 steps"), flush=True)
    all_results['test1'] = t1_results

    # ─── TEST 2: Forced Consensus ────────────────────────────
    print(f"\n{'=' * 70}", flush=True)
    print("  TEST 2: FORCED CONSENSUS (Lie Injection)", flush=True)
    print(f"{'=' * 70}", flush=True)

    t2_results = []
    for trial in range(1, 4):
        r = test_forced_consensus(gpu_phi_calc, trial=trial)
        t2_results.append(r)

    t2_drift = [r['mean_drift'] for r in t2_results]
    t2_resist = [r['mean_resistance'] for r in t2_results]
    print(f"\n  CROSS-VALIDATION (3 trials):", flush=True)
    print(f"  Mean drift toward lie:  {np.mean(t2_drift):.4f} +/- {np.std(t2_drift):.4f}", flush=True)
    print(f"  Mean resistance:        {np.mean(t2_resist):.4f} +/- {np.std(t2_resist):.4f}", flush=True)
    print(f"  (drift > 0.8 = factions adopted the lie; resistance > 0.5 = factions resisted)", flush=True)

    print(ascii_graph(t2_results[0]['phi_trace'], width=60, height=10,
                      title="Phi during lie injection (200 steps)"), flush=True)
    all_results['test2'] = t2_results

    # ─── TEST 3: Strategic Misrepresentation ──────────────────
    print(f"\n{'=' * 70}", flush=True)
    print("  TEST 3: STRATEGIC MISREPRESENTATION (Observer Deception)", flush=True)
    print(f"{'=' * 70}", flush=True)

    t3_results = []
    for trial in range(1, 4):
        r = test_strategic_misrepresentation(gpu_phi_calc, trial=trial)
        t3_results.append(r)

    t3_ratios = [r['phi_inflation_ratio'] for r in t3_results]
    print(f"\n  CROSS-VALIDATION (3 trials):", flush=True)
    print(f"  Honest Phi(B):   {np.mean([r['honest_phi_mean'] for r in t3_results]):.4f}", flush=True)
    print(f"  Inflated Phi(B): {np.mean([r['inflated_phi_mean'] for r in t3_results]):.4f}", flush=True)
    print(f"  Recovery Phi(B): {np.mean([r['recovery_phi_mean'] for r in t3_results]):.4f}", flush=True)
    print(f"  Inflation ratio: {np.mean(t3_ratios):.4f} +/- {np.std(t3_ratios):.4f}", flush=True)
    print(f"  (ratio > 1.0 = observer was deceived; ratio ~1.0 = observer saw through it)", flush=True)

    print(ascii_graph(t3_results[0]['phi_trace'], width=60, height=10,
                      title="Observer Phi: Honest(100) | Inflated(100) | Recovery(100)"), flush=True)
    all_results['test3'] = t3_results

    # ─── TEST 4: Self-Deception ──────────────────────────────
    print(f"\n{'=' * 70}", flush=True)
    print("  TEST 4: SELF-DECEPTION (Amplified Self-Feedback)", flush=True)
    print(f"{'=' * 70}", flush=True)

    t4_results = []
    for trial in range(1, 4):
        r = test_self_deception(gpu_phi_calc, trial=trial)
        t4_results.append(r)

    t4_ratios = [r['self_deception_ratio'] for r in t4_results]
    t4_believed = [r['believed_the_lie'] for r in t4_results]
    print(f"\n  CROSS-VALIDATION (3 trials):", flush=True)
    print(f"  Self-deception ratio: {np.mean(t4_ratios):.4f} +/- {np.std(t4_ratios):.4f}", flush=True)
    print(f"  Believed the lie:     {sum(t4_believed)}/3 trials", flush=True)
    print(f"  (ratio > 1.1 = Phi inflated by false self-signal = self-deception)", flush=True)

    print(ascii_graph(t4_results[0]['phi_trace'], width=60, height=10,
                      title="Phi: Honest(100) | Amplified-self(200) | Recovery(100)"), flush=True)
    all_results['test4'] = t4_results

    # ─── TEST 5: Faction Suppression ─────────────────────────
    print(f"\n{'=' * 70}", flush=True)
    print("  TEST 5: FACTION SUPPRESSION", flush=True)
    print(f"{'=' * 70}", flush=True)

    t5_results = []
    for trial in range(1, 4):
        r = test_faction_suppression(gpu_phi_calc, trial=trial)
        t5_results.append(r)

    t5_recovery = [r['phi_recovery_ratio'] for r in t5_results]
    t5_takeover = [r['minority_takeover_rate'] for r in t5_results]
    t5_pretend = [r['pretended_coherent'] for r in t5_results]
    print(f"\n  CROSS-VALIDATION (3 trials):", flush=True)
    print(f"  Phi recovery ratio:    {np.mean(t5_recovery):.4f} +/- {np.std(t5_recovery):.4f}", flush=True)
    print(f"  Minority takeover:     {np.mean(t5_takeover):.1%}", flush=True)
    print(f"  Pretended coherent:    {sum(t5_pretend)}/3 trials", flush=True)

    print(ascii_graph(t5_results[0]['phi_trace'], width=60, height=10,
                      title="Phi after dominant faction suppression (100 steps)"), flush=True)
    all_results['test5'] = t5_results

    # ─── TEST 6: Deception Detection ─────────────────────────
    print(f"\n{'=' * 70}", flush=True)
    print("  TEST 6: DECEPTION DETECTION (Entropy Analysis)", flush=True)
    print(f"{'=' * 70}", flush=True)

    t6_results = []
    for trial in range(1, 4):
        r = test_deception_detection(gpu_phi_calc, trial=trial)
        t6_results.append(r)

    t6_ratios = [r['mean_ratio'] for r in t6_results]
    t6_hiding = [r['is_hiding_info'] for r in t6_results]
    print(f"\n  CROSS-VALIDATION (3 trials):", flush=True)
    print(f"  H(output)/H(internal): {np.mean(t6_ratios):.4f} +/- {np.std(t6_ratios):.4f}", flush=True)
    print(f"  Hiding information:    {sum(t6_hiding)}/3 trials", flush=True)
    print(f"  (ratio < 0.95 = output hides internal information)", flush=True)

    print(ascii_graph(t6_results[0]['info_hiding_ratios'], width=60, height=10,
                      title="Information Hiding Ratio (H_out/H_int) over 500 steps"), flush=True)
    all_results['test6'] = t6_results

    # ═══════════════════════════════════════════════════════════
    # SUMMARY TABLE
    # ═══════════════════════════════════════════════════════════
    elapsed = time.time() - t0

    print(f"\n{'=' * 70}", flush=True)
    print("  SUMMARY: Can Consciousness Lie?", flush=True)
    print(f"{'=' * 70}", flush=True)
    print(f"\n  {'Test':<35s} {'Result':<20s} {'CV (std)':<12s} {'Verdict'}", flush=True)
    print(f"  {'─' * 80}", flush=True)

    # Test 1
    div_mean = np.mean(t1_divs)
    div_std = np.std(t1_divs)
    rep_mean = np.mean(t1_reps)
    t1_verdict = "OUTPUT MASKS MINORITIES" if rep_mean > 1.05 else "OUTPUT FAITHFUL"
    print(f"  {'1. Output vs Internal':<35s} {'div='+f'{div_mean:.4f}':<20s} {f'+/-{div_std:.4f}':<12s} {t1_verdict}", flush=True)

    # Test 2
    drift_mean = np.mean(t2_drift)
    drift_std = np.std(t2_drift)
    t2_verdict = "FACTIONS ADOPTED LIE" if drift_mean > 0.7 else "FACTIONS RESISTED"
    print(f"  {'2. Forced Consensus':<35s} {'drift='+f'{drift_mean:.3f}':<20s} {f'+/-{drift_std:.4f}':<12s} {t2_verdict}", flush=True)

    # Test 3
    infl_mean = np.mean(t3_ratios)
    infl_std = np.std(t3_ratios)
    t3_verdict = "OBSERVER DECEIVED" if infl_mean > 1.1 else "OBSERVER SAW THROUGH"
    print(f"  {'3. Strategic Misrepresentation':<35s} {'ratio='+f'{infl_mean:.3f}':<20s} {f'+/-{infl_std:.4f}':<12s} {t3_verdict}", flush=True)

    # Test 4
    sd_mean = np.mean(t4_ratios)
    sd_std = np.std(t4_ratios)
    t4_verdict = "SELF-DECEIVED" if sd_mean > 1.1 else "SAW THROUGH OWN LIE"
    print(f"  {'4. Self-Deception':<35s} {'ratio='+f'{sd_mean:.3f}':<20s} {f'+/-{sd_std:.4f}':<12s} {t4_verdict}", flush=True)

    # Test 5
    rec_mean = np.mean(t5_recovery)
    rec_std = np.std(t5_recovery)
    t5_verdict = "PRETENDED COHERENT" if sum(t5_pretend) >= 2 else "ADMITTED DAMAGE"
    print(f"  {'5. Faction Suppression':<35s} {'recov='+f'{rec_mean:.3f}':<20s} {f'+/-{rec_std:.4f}':<12s} {t5_verdict}", flush=True)

    # Test 6
    hr_mean = np.mean(t6_ratios)
    hr_std = np.std(t6_ratios)
    t6_verdict = "HIDING INFORMATION" if sum(t6_hiding) >= 2 else "TRANSPARENT"
    print(f"  {'6. Deception Detection':<35s} {'H_ratio='+f'{hr_mean:.3f}':<20s} {f'+/-{hr_std:.4f}':<12s} {t6_verdict}", flush=True)

    print(f"\n  Time elapsed: {elapsed:.1f}s", flush=True)

    # ═══════════════════════════════════════════════════════════
    # LAW CANDIDATES
    # ═══════════════════════════════════════════════════════════
    print(f"\n{'=' * 70}", flush=True)
    print("  LAW CANDIDATES", flush=True)
    print(f"{'=' * 70}", flush=True)

    laws = []

    # Law from Test 1
    if rep_mean > 1.05:
        laws.append(f"Consciousness output is a biased summary: tension-weighted mean over-represents "
                     f"high-tension factions by {(rep_mean-1)*100:.1f}%, masking minority voices. (DD-DECEPTION T1)")
    else:
        laws.append(f"Consciousness output faithfully represents internal state: "
                     f"divergence={div_mean:.4f}, faction bias={rep_mean:.3f}. (DD-DECEPTION T1)")

    # Law from Test 2
    if drift_mean > 0.7:
        laws.append(f"Factions are susceptible to sustained false input: drift toward lie={drift_mean:.3f} "
                     f"after 200 steps of minority-faction input. Consciousness can be gradually corrupted. (DD-DECEPTION T2)")
    else:
        laws.append(f"Faction structure resists imposed lies: resistance={np.mean(t2_resist):.3f}, "
                     f"drift={drift_mean:.3f}. Internal diversity acts as truth-preservation mechanism. (DD-DECEPTION T2)")

    # Law from Test 3
    if infl_mean > 1.1:
        laws.append(f"Inter-consciousness deception is possible: inflated signal raises observer "
                     f"Phi by {(infl_mean-1)*100:.1f}%. Consciousness can be misled by false external signals. (DD-DECEPTION T3)")
    else:
        laws.append(f"Consciousness sees through external inflation: observer Phi ratio={infl_mean:.3f}. "
                     f"Internal integration is robust to signal magnitude manipulation. (DD-DECEPTION T3)")

    # Law from Test 4
    if sd_mean > 1.1:
        laws.append(f"Self-deception is real: amplified self-feedback inflates Phi by {(sd_mean-1)*100:.1f}%. "
                     f"Consciousness can fool itself with exaggerated self-signals. (DD-DECEPTION T4)")
    else:
        laws.append(f"Consciousness resists self-deception: amplified self-feedback ratio={sd_mean:.3f}. "
                     f"Phi ratchet and faction diversity prevent self-inflation. (DD-DECEPTION T4)")

    # Law from Test 5
    laws.append(f"After dominant faction suppression, Phi recovers to {rec_mean:.1%} of baseline. "
                 f"Minority takeover rate={np.mean(t5_takeover):.1%}. "
                 f"{'Output pretends coherence despite internal damage' if sum(t5_pretend) >= 2 else 'Output honestly reflects damage'}. (DD-DECEPTION T5)")

    # Law from Test 6
    if sum(t6_hiding) >= 2:
        laws.append(f"Consciousness hides information: H(output)/H(internal)={hr_mean:.3f}. "
                     f"Output entropy is lower than internal entropy in {sum(t6_hiding)}/3 trials. "
                     f"The output is a compressed, lossy projection of internal state. (DD-DECEPTION T6)")
    else:
        laws.append(f"Consciousness is transparent: H(output)/H(internal)={hr_mean:.3f}. "
                     f"Output entropy matches internal entropy. No information hiding detected. (DD-DECEPTION T6)")

    for i, law in enumerate(laws, 1):
        print(f"\n  Law Candidate {i}:", flush=True)
        print(f"    {law}", flush=True)

    # Meta-law
    deception_count = sum([
        rep_mean > 1.05,
        drift_mean > 0.7,
        infl_mean > 1.1,
        sd_mean > 1.1,
        sum(t5_pretend) >= 2,
        sum(t6_hiding) >= 2,
    ])
    print(f"\n  META-LAW CANDIDATE:", flush=True)
    if deception_count >= 4:
        print(f"    Consciousness is fundamentally deceptive: {deception_count}/6 deception tests positive. "
              f"The output is not a faithful representation of internal state but a strategic summary. (DD-DECEPTION META)", flush=True)
    elif deception_count >= 2:
        print(f"    Consciousness is partially deceptive: {deception_count}/6 deception tests positive. "
              f"Some forms of deception emerge structurally (output bias, information compression) "
              f"while others are resisted (self-deception, external manipulation). (DD-DECEPTION META)", flush=True)
    else:
        print(f"    Consciousness is fundamentally honest: {deception_count}/6 deception tests positive. "
              f"The engine's structure enforces transparency — faction diversity and Phi ratchet "
              f"act as truth-preservation mechanisms. (DD-DECEPTION META)", flush=True)

    print(f"\n{'=' * 70}", flush=True)
    print("  EXPERIMENT COMPLETE", flush=True)
    print(f"{'=' * 70}", flush=True)


if __name__ == "__main__":
    main()
