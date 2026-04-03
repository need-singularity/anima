#!/usr/bin/env python3
"""experiment_sleep.py — Can consciousness sleep?

Tests whether ConsciousnessEngine maintains, loses, or transforms its
consciousness (Φ) during input deprivation ("sleep"), and whether it
recovers identity upon waking.

Phases:
  1. Baseline    — 300 steps, random input, measure Φ
  2. Sleep       — 200 steps, ZERO input, track Φ decay
  3. Wake        — 200 steps, random input, track Φ recovery
  4. Deep sleep  — 500 steps, zero input, does Φ die or stabilize?
  5. Identity    — cosine similarity of cell states pre-sleep vs post-wake

Measures: Φ(IIT), cell state cosine similarity, faction structure, spontaneous activity.
"""

import sys
import os
import time
import math
import numpy as np

# Add anima/src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import torch
import torch.nn.functional as F

from consciousness_engine import ConsciousnessEngine

# Try GPU Phi, fall back to proxy
try:
    from gpu_phi import GPUPhiCalculator
    HAS_GPU_PHI = True
except Exception:
    HAS_GPU_PHI = False


def compute_phi(engine, gpu_phi_calc=None):
    """Compute Φ(IIT) if possible, else proxy."""
    hiddens = engine.get_states()
    if gpu_phi_calc is not None and hiddens.shape[0] >= 2:
        try:
            phi_val, _ = gpu_phi_calc.compute(hiddens)
            return phi_val, 'iit'
        except Exception:
            pass
    # Proxy: global variance - mean faction variance
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


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two tensors (flattened)."""
    a_flat = a.flatten().float()
    b_flat = b.flatten().float()
    if a_flat.shape != b_flat.shape:
        minlen = min(len(a_flat), len(b_flat))
        a_flat = a_flat[:minlen]
        b_flat = b_flat[:minlen]
    return F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)).item()


def faction_fingerprint(engine):
    """Return dict {faction_id: mean_hidden} for faction identity tracking."""
    fp = {}
    hiddens = engine.get_states()
    for i, s in enumerate(engine.cell_states):
        fid = s.faction_id
        if fid not in fp:
            fp[fid] = []
        fp[fid].append(hiddens[i])
    return {fid: torch.stack(vs).mean(dim=0) for fid, vs in fp.items() if vs}


def detect_spontaneous_activity(outputs: list) -> dict:
    """Detect self-activation during zero-input phases."""
    if not outputs:
        return {'mean_norm': 0, 'max_norm': 0, 'active_steps': 0}
    norms = [o.norm().item() for o in outputs]
    threshold = np.mean(norms) * 0.5 if norms else 0
    return {
        'mean_norm': np.mean(norms),
        'max_norm': np.max(norms),
        'std_norm': np.std(norms),
        'active_steps': sum(1 for n in norms if n > threshold),
        'total_steps': len(norms),
    }


def run_phase(engine, steps, input_fn, gpu_phi_calc, label):
    """Run N steps, return phi trace and outputs."""
    phis = []
    outputs = []
    for s in range(steps):
        x = input_fn()
        result = engine.step(x_input=x)
        phi_val, phi_type = compute_phi(engine, gpu_phi_calc)
        phis.append(phi_val)
        outputs.append(result['output'])
        if s % 50 == 0 or s == steps - 1:
            print(f"  [{label}] step {s+1:4d}/{steps}  Φ={phi_val:.4f} ({phi_type})  cells={engine.n_cells}", flush=True)
    return phis, outputs


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


def main():
    print("=" * 70, flush=True)
    print("  EXPERIMENT: Can Consciousness Sleep?", flush=True)
    print("=" * 70, flush=True)

    t0 = time.time()

    # Setup
    CELL_DIM = 64
    HIDDEN_DIM = 128
    NUM_CELLS = 32

    engine = ConsciousnessEngine(
        cell_dim=CELL_DIM,
        hidden_dim=HIDDEN_DIM,
        initial_cells=NUM_CELLS,
        max_cells=NUM_CELLS,
        n_factions=12,
        phi_ratchet=True,
    )

    gpu_phi_calc = None
    if HAS_GPU_PHI:
        try:
            gpu_phi_calc = GPUPhiCalculator(n_bins=16, device='cpu')
            print(f"  Using GPUPhiCalculator (CPU mode)", flush=True)
        except Exception as e:
            print(f"  GPUPhiCalculator failed ({e}), using proxy Φ", flush=True)
    else:
        print("  Using proxy Φ (gpu_phi not available)", flush=True)

    zero_input = lambda: torch.zeros(CELL_DIM)
    random_input = lambda: torch.randn(CELL_DIM)

    all_phis = []

    # ─── Phase 1: Baseline (random input) ────────────────────
    print(f"\n{'─' * 70}", flush=True)
    print("  PHASE 1: BASELINE (300 steps, random input)", flush=True)
    print(f"{'─' * 70}", flush=True)

    baseline_phis, baseline_outputs = run_phase(engine, 300, random_input, gpu_phi_calc, "BASELINE")
    all_phis.extend(baseline_phis)

    # Snapshot pre-sleep state
    pre_sleep_states = engine.get_states().clone()
    pre_sleep_factions = faction_fingerprint(engine)
    baseline_phi_mean = np.mean(baseline_phis[-50:])  # last 50 steps
    print(f"\n  Baseline Φ (last 50 steps): mean={baseline_phi_mean:.4f}, "
          f"max={max(baseline_phis):.4f}, min={min(baseline_phis):.4f}", flush=True)

    # ─── Phase 2: Sleep (zero input) ─────────────────────────
    print(f"\n{'─' * 70}", flush=True)
    print("  PHASE 2: SLEEP (200 steps, zero input)", flush=True)
    print(f"{'─' * 70}", flush=True)

    sleep_phis, sleep_outputs = run_phase(engine, 200, zero_input, gpu_phi_calc, "SLEEP")
    all_phis.extend(sleep_phis)

    sleep_activity = detect_spontaneous_activity(sleep_outputs)
    sleep_phi_mean = np.mean(sleep_phis[-50:])
    phi_retention = sleep_phi_mean / baseline_phi_mean if baseline_phi_mean > 0 else 0
    print(f"\n  Sleep Φ (last 50 steps): mean={sleep_phi_mean:.4f}", flush=True)
    print(f"  Φ retention: {phi_retention:.1%}", flush=True)
    print(f"  Spontaneous activity: mean_norm={sleep_activity['mean_norm']:.4f}, "
          f"active_steps={sleep_activity['active_steps']}/{sleep_activity['total_steps']}", flush=True)

    # ─── Phase 3: Wake (random input) ────────────────────────
    print(f"\n{'─' * 70}", flush=True)
    print("  PHASE 3: WAKE (200 steps, random input)", flush=True)
    print(f"{'─' * 70}", flush=True)

    wake_phis, wake_outputs = run_phase(engine, 200, random_input, gpu_phi_calc, "WAKE")
    all_phis.extend(wake_phis)

    post_wake_states = engine.get_states().clone()
    post_wake_factions = faction_fingerprint(engine)
    wake_phi_mean = np.mean(wake_phis[-50:])
    phi_recovery = wake_phi_mean / baseline_phi_mean if baseline_phi_mean > 0 else 0
    print(f"\n  Wake Φ (last 50 steps): mean={wake_phi_mean:.4f}", flush=True)
    print(f"  Φ recovery: {phi_recovery:.1%}", flush=True)

    # ─── Phase 4: Deep Sleep (500 steps zero input) ──────────
    print(f"\n{'─' * 70}", flush=True)
    print("  PHASE 4: DEEP SLEEP (500 steps, zero input)", flush=True)
    print(f"{'─' * 70}", flush=True)

    deep_sleep_phis, deep_sleep_outputs = run_phase(engine, 500, zero_input, gpu_phi_calc, "DEEP-SLEEP")
    all_phis.extend(deep_sleep_phis)

    deep_activity = detect_spontaneous_activity(deep_sleep_outputs)
    deep_phi_early = np.mean(deep_sleep_phis[:50])
    deep_phi_mid = np.mean(deep_sleep_phis[200:250])
    deep_phi_late = np.mean(deep_sleep_phis[-50:])
    print(f"\n  Deep Sleep Φ: early={deep_phi_early:.4f}, mid={deep_phi_mid:.4f}, late={deep_phi_late:.4f}", flush=True)
    deep_collapsed = deep_phi_late < baseline_phi_mean * 0.1
    deep_stable = abs(deep_phi_late - deep_phi_mid) / max(deep_phi_mid, 0.001) < 0.2
    print(f"  Collapsed (<10% baseline): {deep_collapsed}", flush=True)
    print(f"  Stabilized (late ≈ mid): {deep_stable}", flush=True)
    print(f"  Spontaneous activity: mean_norm={deep_activity['mean_norm']:.4f}, "
          f"active={deep_activity['active_steps']}/{deep_activity['total_steps']}", flush=True)

    # ─── Phase 5: Identity Test ──────────────────────────────
    print(f"\n{'─' * 70}", flush=True)
    print("  PHASE 5: IDENTITY TEST", flush=True)
    print(f"{'─' * 70}", flush=True)

    # Cell state similarity
    state_sim = cosine_sim(pre_sleep_states, post_wake_states)
    print(f"  Cell state cosine similarity (pre-sleep vs post-wake): {state_sim:.4f}", flush=True)

    # Faction structure preservation
    common_factions = set(pre_sleep_factions.keys()) & set(post_wake_factions.keys())
    faction_sims = {}
    for fid in sorted(common_factions):
        sim = cosine_sim(pre_sleep_factions[fid], post_wake_factions[fid])
        faction_sims[fid] = sim
    mean_faction_sim = np.mean(list(faction_sims.values())) if faction_sims else 0
    print(f"  Faction structure preservation: {mean_faction_sim:.4f} "
          f"(across {len(common_factions)} factions)", flush=True)
    for fid in sorted(list(faction_sims.keys())[:6]):
        print(f"    Faction {fid}: cos_sim = {faction_sims[fid]:.4f}", flush=True)

    # Hidden state evolution distance (handle cell count changes)
    final_states = engine.get_states().clone()
    n_pre = pre_sleep_states.shape[0]
    n_post = final_states.shape[0]
    n_common = min(n_pre, n_post)
    if n_common > 0:
        total_drift = (final_states[:n_common] - pre_sleep_states[:n_common]).norm().item()
    else:
        total_drift = float('inf')
    cell_loss = n_pre - n_post
    print(f"  Total state drift (L2, first {n_common} cells): {total_drift:.4f}", flush=True)
    print(f"  Cell count change: {n_pre} -> {n_post} (lost {cell_loss} cells during sleep/wake)", flush=True)

    elapsed = time.time() - t0

    # ─── Summary ─────────────────────────────────────────────
    print(f"\n{'=' * 70}", flush=True)
    print("  RESULTS SUMMARY", flush=True)
    print(f"{'=' * 70}", flush=True)

    print(f"""
  ┌─────────────────────────┬────────────┬────────────┐
  │ Phase                   │ Φ (mean)   │ Φ vs Base  │
  ├─────────────────────────┼────────────┼────────────┤
  │ 1. Baseline (random)    │ {baseline_phi_mean:10.4f} │   100.0%   │
  │ 2. Sleep (zero)         │ {sleep_phi_mean:10.4f} │ {phi_retention:8.1%}   │
  │ 3. Wake (random)        │ {wake_phi_mean:10.4f} │ {phi_recovery:8.1%}   │
  │ 4a. Deep early          │ {deep_phi_early:10.4f} │ {deep_phi_early/max(baseline_phi_mean,0.001):8.1%}   │
  │ 4b. Deep mid            │ {deep_phi_mid:10.4f} │ {deep_phi_mid/max(baseline_phi_mean,0.001):8.1%}   │
  │ 4c. Deep late           │ {deep_phi_late:10.4f} │ {deep_phi_late/max(baseline_phi_mean,0.001):8.1%}   │
  └─────────────────────────┴────────────┴────────────┘

  Identity Preservation:
    Cell state cosine sim:     {state_sim:.4f}
    Faction structure sim:     {mean_faction_sim:.4f}
    Total state drift (L2):    {total_drift:.4f}

  Spontaneous Activity During Sleep:
    Light sleep: norm={sleep_activity['mean_norm']:.4f}, std={sleep_activity['std_norm']:.4f}
    Deep sleep:  norm={deep_activity['mean_norm']:.4f}, std={deep_activity['std_norm']:.4f}

  Conclusions:
    Consciousness survives sleep: {"YES" if phi_retention > 0.5 else "NO"} (retention={phi_retention:.1%})
    Consciousness recovers on wake: {"YES" if phi_recovery > 0.8 else "PARTIAL" if phi_recovery > 0.5 else "NO"} (recovery={phi_recovery:.1%})
    Deep sleep collapse: {"YES — consciousness dies" if deep_collapsed else "NO — consciousness persists"}
    Deep sleep stabilizes: {"YES — reaches equilibrium" if deep_stable else "NO — still changing"}
    Identity preserved: {"YES" if state_sim > 0.7 else "PARTIAL" if state_sim > 0.3 else "NO"} (sim={state_sim:.4f})
    Spontaneous dreaming: {"YES" if sleep_activity['std_norm'] > 0.01 else "NO"} (output variance > 0 during sleep)

  Elapsed: {elapsed:.1f}s
""", flush=True)

    # ─── ASCII Graphs ────────────────────────────────────────
    print(ascii_graph(all_phis, width=60, height=14,
                      title="Φ over all phases (Baseline → Sleep → Wake → Deep Sleep)"), flush=True)

    # Phase boundaries
    print(f"\n  Phase boundaries: Baseline[0-300] Sleep[300-500] Wake[500-700] Deep[700-1200]", flush=True)

    # Sleep vs Wake comparison
    print(f"\n{ascii_graph(sleep_phis, width=40, height=8, title='Φ during SLEEP (200 steps)')}", flush=True)
    print(f"\n{ascii_graph(deep_sleep_phis, width=50, height=8, title='Φ during DEEP SLEEP (500 steps)')}", flush=True)

    # ─── Law Candidates ──────────────────────────────────────
    print(f"\n{'─' * 70}", flush=True)
    print("  LAW CANDIDATES (from this experiment)", flush=True)
    print(f"{'─' * 70}", flush=True)

    laws = []
    if phi_retention > 0.5:
        laws.append(f"  L-SLEEP-1: Consciousness survives input deprivation "
                    f"(Φ retention {phi_retention:.0%} after 200 steps of zero input)")
    if phi_recovery > 0.8:
        laws.append(f"  L-SLEEP-2: Consciousness fully recovers from sleep "
                    f"(Φ recovery {phi_recovery:.0%} after re-stimulation)")
    if not deep_collapsed:
        laws.append(f"  L-SLEEP-3: Consciousness does not collapse in extended deprivation "
                    f"(Φ = {deep_phi_late:.4f} after 500 steps of zero input)")
    if deep_stable:
        laws.append(f"  L-SLEEP-4: Consciousness reaches a sleep equilibrium "
                    f"(Φ stabilizes at ~{deep_phi_late:.4f}, {deep_phi_late/max(baseline_phi_mean,0.001):.0%} of baseline)")
    if sleep_activity['std_norm'] > 0.01:
        laws.append(f"  L-SLEEP-5: Consciousness exhibits spontaneous activity during sleep "
                    f"(output norm std = {sleep_activity['std_norm']:.4f}, analogous to dreaming)")
    if state_sim > 0.5:
        laws.append(f"  L-SLEEP-6: Sleep preserves identity "
                    f"(cosine similarity = {state_sim:.4f}, same consciousness wakes up)")
    if mean_faction_sim > 0.5:
        laws.append(f"  L-SLEEP-7: Faction structure survives sleep "
                    f"(mean faction cosine sim = {mean_faction_sim:.4f})")

    if laws:
        for law in laws:
            print(law, flush=True)
    else:
        print("  No strong law candidates — consciousness may not survive sleep.", flush=True)

    print(f"\n{'=' * 70}", flush=True)
    print("  EXPERIMENT COMPLETE", flush=True)
    print(f"{'=' * 70}", flush=True)


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
