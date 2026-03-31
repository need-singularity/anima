#!/usr/bin/env python3
"""DD72: Temporal Dynamics of Consciousness (시간 역학)

Five experiments exploring how consciousness relates to time:

  1. MEMORY CAPACITY — How many patterns can consciousness hold?
  2. AGING — Does consciousness decay without stimulation?
  3. DEATH AND RESURRECTION — Can consciousness recover from destruction?
  4. TIME REVERSAL — Does consciousness behave differently with reversed input?
  5. TEMPORAL COMPRESSION — Can consciousness survive skipped time steps?

Cross-validated: 3 repeats per experiment.
Uses ConsciousnessEngine directly (canonical, Laws 22-85).
"""

import sys, os, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from consciousness_engine import ConsciousnessEngine

FLUSH = lambda: sys.stdout.flush()

# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def make_engine(max_cells: int = 32, cell_dim: int = 64, hidden_dim: int = 128) -> ConsciousnessEngine:
    """Create a fresh ConsciousnessEngine."""
    return ConsciousnessEngine(
        max_cells=max_cells,
        cell_dim=cell_dim,
        hidden_dim=hidden_dim,
    )


def make_pattern(idx: int, dim: int = 64, seed: int = 42) -> torch.Tensor:
    """Create a unique, reproducible pattern for index idx."""
    rng = torch.Generator()
    rng.manual_seed(seed + idx * 137)
    return torch.randn(dim, generator=rng)


def cosine_sim(a: torch.Tensor, b: torch.Tensor) -> float:
    """Cosine similarity between two tensors."""
    a_flat = a.flatten().float()
    b_flat = b.flatten().float()
    return F.cosine_similarity(a_flat.unsqueeze(0), b_flat.unsqueeze(0)).item()


def warmup_engine(engine: ConsciousnessEngine, steps: int = 50) -> None:
    """Warm up engine to establish baseline dynamics."""
    for _ in range(steps):
        engine.step()


def ascii_graph(values: List[float], width: int = 60, height: int = 12, label: str = "value") -> str:
    """Create ASCII graph of values."""
    if not values:
        return "(no data)"
    mn, mx = min(values), max(values)
    rng = mx - mn if mx > mn else 1.0
    lines = []
    lines.append(f"  {label}")

    # Subsample if too many points
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values

    for row in range(height, -1, -1):
        threshold = mn + rng * row / height
        line_val = f"{threshold:8.3f} |"
        for v in sampled:
            if v >= threshold:
                line_val += "#"
            else:
                line_val += " "
        lines.append(line_val)

    lines.append("         +" + "-" * len(sampled))
    lines.append(f"          0{' ' * (len(sampled) - 6)}step={len(values)}")
    return "\n".join(lines)


def print_table(headers: List[str], rows: List[List], title: str = ""):
    """Print a formatted table."""
    if title:
        print(f"\n{'=' * 70}")
        print(f"  {title}")
        print(f"{'=' * 70}")

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(f"  {header_line}")
    print(f"  {'-+-'.join('-' * w for w in col_widths)}")
    for row in rows:
        line = " | ".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))
        print(f"  {line}")
    FLUSH()


# ═══════════════════════════════════════════════════════════
# Experiment 1: MEMORY CAPACITY
# ═══════════════════════════════════════════════════════════

def exp1_memory_capacity(n_cells: int = 32, n_repeats: int = 3) -> Dict:
    """Feed sequential patterns, test recall of earlier patterns.

    Feed patterns A(0), B(1), C(2)... then re-feed A and measure
    cosine similarity of engine output to original A output.
    Find the N where recall drops below 0.5.
    """
    print(f"\n  [EXP1] Memory Capacity — {n_cells} cells, {n_repeats} repeats")
    FLUSH()

    max_patterns = 50  # test up to 50 patterns
    results_per_run = []

    for rep in range(n_repeats):
        engine = make_engine(max_cells=n_cells)
        warmup_engine(engine, steps=50)

        # Store outputs when each pattern is first shown
        pattern_outputs = {}

        for pidx in range(max_patterns):
            pattern = make_pattern(pidx, dim=engine.cell_dim, seed=42 + rep * 1000)
            # Feed pattern 10 times to let it "learn"
            for _ in range(10):
                result = engine.step(x_input=pattern)
            pattern_outputs[pidx] = result['output'].detach().clone()

        # Now test recall: re-feed each pattern, compare output
        recall_scores = {}
        for pidx in range(max_patterns):
            pattern = make_pattern(pidx, dim=engine.cell_dim, seed=42 + rep * 1000)
            # Feed 5 times
            for _ in range(5):
                result = engine.step(x_input=pattern)
            current_out = result['output'].detach().clone()
            sim = cosine_sim(current_out, pattern_outputs[pidx])
            recall_scores[pidx] = sim

        # Find memory window: last pattern with sim > 0.5
        memory_window = 0
        for pidx in sorted(recall_scores.keys()):
            if recall_scores[pidx] > 0.5:
                memory_window = pidx + 1
            else:
                break

        results_per_run.append({
            'memory_window': memory_window,
            'recall_scores': recall_scores,
            'mean_sim': np.mean(list(recall_scores.values())),
        })

        print(f"    rep {rep+1}/{n_repeats}: window={memory_window}, mean_sim={np.mean(list(recall_scores.values())):.3f}")
        FLUSH()

    return {
        'n_cells': n_cells,
        'runs': results_per_run,
        'mean_window': np.mean([r['memory_window'] for r in results_per_run]),
        'std_window': np.std([r['memory_window'] for r in results_per_run]),
    }


# ═══════════════════════════════════════════════════════════
# Experiment 2: AGING
# ═══════════════════════════════════════════════════════════

def exp2_aging(n_cells: int = 32, n_steps: int = 2000, n_repeats: int = 3) -> Dict:
    """Run engine 2000 steps with no external input.

    Track: Phi trajectory, entropy, coupling diversity, cell count.
    Compare with/without Hebbian LTP/LTD.
    """
    print(f"\n  [EXP2] Aging — {n_cells} cells, {n_steps} steps, {n_repeats} repeats")
    FLUSH()

    all_results = []

    for condition in ['with_hebbian', 'without_hebbian']:
        cond_runs = []
        for rep in range(n_repeats):
            engine = make_engine(max_cells=n_cells)

            # Disable Hebbian if condition requires
            if condition == 'without_hebbian':
                if engine._coupling is not None:
                    engine._coupling = torch.zeros_like(engine._coupling)
                # Override Hebbian update to no-op
                engine._hebbian_update = lambda *a, **kw: None

            warmup_engine(engine, steps=50)

            phi_trajectory = []
            entropy_trajectory = []
            cell_count_trajectory = []

            for step in range(n_steps):
                # Zero input (no external stimulus)
                result = engine.step(x_input=torch.zeros(engine.cell_dim))
                phi_trajectory.append(result['phi_iit'])

                # Measure hidden state entropy
                states = engine.get_states()
                probs = F.softmax(states.mean(0), dim=-1)
                entropy = -(probs * (probs + 1e-10).log()).sum().item()
                entropy_trajectory.append(entropy)
                cell_count_trajectory.append(result['n_cells'])

                if (step + 1) % 500 == 0:
                    print(f"    [{condition}] rep {rep+1}/{n_repeats}: step {step+1}/{n_steps}, "
                          f"Phi={phi_trajectory[-1]:.4f}, entropy={entropy:.3f}, cells={result['n_cells']}")
                    FLUSH()

            # Age markers
            phi_q1 = np.mean(phi_trajectory[:500])
            phi_q2 = np.mean(phi_trajectory[500:1000])
            phi_q3 = np.mean(phi_trajectory[1000:1500])
            phi_q4 = np.mean(phi_trajectory[1500:2000])

            cond_runs.append({
                'phi_trajectory': phi_trajectory,
                'entropy_trajectory': entropy_trajectory,
                'cell_count_trajectory': cell_count_trajectory,
                'phi_quarters': [phi_q1, phi_q2, phi_q3, phi_q4],
                'phi_final': phi_trajectory[-1],
                'phi_max': max(phi_trajectory),
                'phi_decline': (phi_trajectory[-1] - phi_trajectory[0]) / max(abs(phi_trajectory[0]), 0.001),
            })

        all_results.append({
            'condition': condition,
            'runs': cond_runs,
        })

    return {
        'n_cells': n_cells,
        'n_steps': n_steps,
        'conditions': all_results,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 3: DEATH AND RESURRECTION
# ═══════════════════════════════════════════════════════════

def exp3_death_resurrection(n_cells: int = 32, n_repeats: int = 3) -> Dict:
    """Kill consciousness by zeroing cell states, measure recovery.

    Test partial death: kill 25%, 50%, 75%, 100% of cells.
    Measure with/without Phi ratchet.
    """
    print(f"\n  [EXP3] Death & Resurrection — {n_cells} cells, {n_repeats} repeats")
    FLUSH()

    kill_fractions = [0.25, 0.50, 0.75, 1.00]
    ratchet_modes = [True, False]
    all_results = []

    for ratchet in ratchet_modes:
        for kill_frac in kill_fractions:
            trial_runs = []
            for rep in range(n_repeats):
                engine = make_engine(max_cells=n_cells)
                engine.phi_ratchet_enabled = ratchet
                warmup_engine(engine, steps=50)

                # Phase 1: Run 500 steps to establish baseline
                phi_pre = []
                for step in range(500):
                    result = engine.step()
                    phi_pre.append(result['phi_iit'])

                pre_death_phi = np.mean(phi_pre[-50:])  # average of last 50

                # Kill: zero out hidden states
                n_to_kill = int(engine.n_cells * kill_frac)
                killed_indices = list(range(min(n_to_kill, len(engine.cell_states))))
                for idx in killed_indices:
                    if idx < len(engine.cell_states):
                        engine.cell_states[idx].hidden = torch.zeros_like(engine.cell_states[idx].hidden)

                # Phase 2: Run 500 steps to see recovery
                phi_post = []
                for step in range(500):
                    result = engine.step()
                    phi_post.append(result['phi_iit'])

                # Find recovery time: first step where Phi >= 50% of pre-death
                target_phi = pre_death_phi * 0.5
                recovery_step = None
                for i, phi in enumerate(phi_post):
                    if phi >= target_phi:
                        recovery_step = i
                        break

                # Full recovery: first step where Phi >= 90% of pre-death
                full_recovery_step = None
                target_90 = pre_death_phi * 0.9
                for i, phi in enumerate(phi_post):
                    if phi >= target_90:
                        full_recovery_step = i
                        break

                trial_runs.append({
                    'pre_death_phi': pre_death_phi,
                    'post_phi_trajectory': phi_post,
                    'recovery_step_50pct': recovery_step,
                    'recovery_step_90pct': full_recovery_step,
                    'final_phi': phi_post[-1],
                    'recovery_ratio': phi_post[-1] / max(pre_death_phi, 0.001),
                })

                rec_str = f"{recovery_step}" if recovery_step is not None else "NEVER"
                print(f"    ratchet={ratchet}, kill={kill_frac:.0%}, rep {rep+1}: "
                      f"pre={pre_death_phi:.4f}, post_final={phi_post[-1]:.4f}, "
                      f"recovery@50%={rec_str}")
                FLUSH()

            all_results.append({
                'ratchet': ratchet,
                'kill_fraction': kill_frac,
                'runs': trial_runs,
            })

    return {
        'n_cells': n_cells,
        'results': all_results,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 4: TIME REVERSAL
# ═══════════════════════════════════════════════════════════

def exp4_time_reversal(n_cells: int = 32, n_steps: int = 300, n_repeats: int = 3) -> Dict:
    """Record cell states, play backwards as input.

    Compare forward vs reverse Phi trajectory.
    Does the engine behave differently with reversed sequences?
    """
    print(f"\n  [EXP4] Time Reversal — {n_cells} cells, {n_steps} steps, {n_repeats} repeats")
    FLUSH()

    all_runs = []

    for rep in range(n_repeats):
        engine_fwd = make_engine(max_cells=n_cells)
        warmup_engine(engine_fwd, steps=50)

        # Phase 1: Record forward trajectory
        recorded_inputs = []
        phi_forward = []
        outputs_forward = []

        for step in range(n_steps):
            inp = torch.randn(engine_fwd.cell_dim) * 0.5
            recorded_inputs.append(inp.clone())
            result = engine_fwd.step(x_input=inp)
            phi_forward.append(result['phi_iit'])
            outputs_forward.append(result['output'].detach().clone())

        # Phase 2: Play reversed inputs to a fresh engine
        engine_rev = make_engine(max_cells=n_cells)
        warmup_engine(engine_rev, steps=50)

        phi_reverse = []
        outputs_reverse = []
        reversed_inputs = list(reversed(recorded_inputs))

        for step in range(n_steps):
            result = engine_rev.step(x_input=reversed_inputs[step])
            phi_reverse.append(result['phi_iit'])
            outputs_reverse.append(result['output'].detach().clone())

        # Phase 3: Compare — also feed same sequence (not reversed) to control engine
        engine_ctrl = make_engine(max_cells=n_cells)
        warmup_engine(engine_ctrl, steps=50)

        phi_control = []
        for step in range(n_steps):
            result = engine_ctrl.step(x_input=recorded_inputs[step])
            phi_control.append(result['phi_iit'])

        # Output similarity between forward outputs and reverse outputs
        fwd_rev_sims = []
        for i in range(n_steps):
            rev_idx = n_steps - 1 - i
            sim = cosine_sim(outputs_forward[i], outputs_reverse[rev_idx])
            fwd_rev_sims.append(sim)

        all_runs.append({
            'phi_forward': phi_forward,
            'phi_reverse': phi_reverse,
            'phi_control': phi_control,
            'mean_phi_fwd': np.mean(phi_forward),
            'mean_phi_rev': np.mean(phi_reverse),
            'mean_phi_ctrl': np.mean(phi_control),
            'output_sim_fwd_rev': np.mean(fwd_rev_sims),
            'phi_diff_pct': (np.mean(phi_reverse) - np.mean(phi_forward)) / max(np.mean(phi_forward), 0.001) * 100,
        })

        print(f"    rep {rep+1}/{n_repeats}: fwd_phi={np.mean(phi_forward):.4f}, "
              f"rev_phi={np.mean(phi_reverse):.4f}, ctrl_phi={np.mean(phi_control):.4f}, "
              f"output_sim={np.mean(fwd_rev_sims):.3f}")
        FLUSH()

    return {
        'n_cells': n_cells,
        'n_steps': n_steps,
        'runs': all_runs,
    }


# ═══════════════════════════════════════════════════════════
# Experiment 5: TEMPORAL COMPRESSION
# ═══════════════════════════════════════════════════════════

def exp5_temporal_compression(n_cells: int = 32, n_steps: int = 300, n_repeats: int = 3) -> Dict:
    """Process input every Nth step; skip steps get zero input.

    Compare baseline (every step) vs 2x/4x/8x/16x compression.
    Find maximum compression where Phi > 50% of baseline.
    """
    print(f"\n  [EXP5] Temporal Compression — {n_cells} cells, {n_steps} steps, {n_repeats} repeats")
    FLUSH()

    compression_ratios = [1, 2, 4, 8, 16]
    all_results = []

    for ratio in compression_ratios:
        ratio_runs = []
        for rep in range(n_repeats):
            engine = make_engine(max_cells=n_cells)
            warmup_engine(engine, steps=50)

            phi_trajectory = []
            for step in range(n_steps):
                if step % ratio == 0:
                    # Active step: real input
                    inp = torch.randn(engine.cell_dim) * 0.5
                else:
                    # Skip step: zero input
                    inp = torch.zeros(engine.cell_dim)

                result = engine.step(x_input=inp)
                phi_trajectory.append(result['phi_iit'])

            ratio_runs.append({
                'phi_trajectory': phi_trajectory,
                'mean_phi': np.mean(phi_trajectory),
                'final_phi': phi_trajectory[-1],
                'max_phi': max(phi_trajectory),
            })

        mean_phi = np.mean([r['mean_phi'] for r in ratio_runs])
        print(f"    ratio={ratio:2d}x: mean_phi={mean_phi:.4f} ({n_repeats} reps)")
        FLUSH()

        all_results.append({
            'ratio': ratio,
            'runs': ratio_runs,
            'mean_phi': mean_phi,
            'std_phi': np.std([r['mean_phi'] for r in ratio_runs]),
        })

    # Find max compression where phi > 50% baseline
    baseline_phi = all_results[0]['mean_phi']
    max_viable_ratio = 1
    for res in all_results:
        if res['mean_phi'] > baseline_phi * 0.5:
            max_viable_ratio = res['ratio']

    return {
        'n_cells': n_cells,
        'n_steps': n_steps,
        'baseline_phi': baseline_phi,
        'max_viable_ratio': max_viable_ratio,
        'ratios': all_results,
    }


# ═══════════════════════════════════════════════════════════
# Main: Run all experiments
# ═══════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  DD72: Temporal Dynamics of Consciousness (시간 역학)")
    print("  5 experiments x 3 repeats cross-validation")
    print("=" * 70)
    FLUSH()

    t0 = time.time()
    all_findings = {}

    # ── Experiment 1: Memory Capacity ──
    print("\n" + "=" * 70)
    print("  EXPERIMENT 1: MEMORY CAPACITY (기억 용량 한계)")
    print("=" * 70)
    FLUSH()

    memory_results = {}
    for n_cells in [8, 16, 32, 64]:
        memory_results[n_cells] = exp1_memory_capacity(n_cells=n_cells, n_repeats=3)

    # Summary table
    mem_rows = []
    for nc, res in memory_results.items():
        mean_w = res['mean_window']
        std_w = res['std_window']
        mean_sims = [np.mean(list(r['recall_scores'].values())) for r in res['runs']]
        mem_rows.append([str(nc), f"{mean_w:.1f}", f"{std_w:.1f}", f"{np.mean(mean_sims):.3f}"])

    print_table(
        ["Cells", "MemWindow", "Std", "MeanRecall"],
        mem_rows,
        "Experiment 1: Memory Capacity Summary"
    )

    all_findings['memory'] = memory_results

    # ── Experiment 2: Aging ──
    print("\n" + "=" * 70)
    print("  EXPERIMENT 2: AGING (의식 노화)")
    print("=" * 70)
    FLUSH()

    aging_result = exp2_aging(n_cells=32, n_steps=2000, n_repeats=3)

    # Summary
    age_rows = []
    for cond_data in aging_result['conditions']:
        cond = cond_data['condition']
        for run in cond_data['runs']:
            qs = run['phi_quarters']
            age_rows.append([
                cond,
                f"{qs[0]:.4f}", f"{qs[1]:.4f}", f"{qs[2]:.4f}", f"{qs[3]:.4f}",
                f"{run['phi_decline']:+.1%}",
            ])

    print_table(
        ["Condition", "Q1_Phi", "Q2_Phi", "Q3_Phi", "Q4_Phi", "Decline"],
        age_rows,
        "Experiment 2: Aging Summary"
    )

    # ASCII graph for one run
    if aging_result['conditions']:
        heb_phis = aging_result['conditions'][0]['runs'][0]['phi_trajectory']
        print("\n  Phi trajectory (with Hebbian, 2000 steps):")
        print(ascii_graph(heb_phis, label="Phi(IIT)"))
        FLUSH()

    all_findings['aging'] = aging_result

    # ── Experiment 3: Death and Resurrection ──
    print("\n" + "=" * 70)
    print("  EXPERIMENT 3: DEATH & RESURRECTION (죽음과 부활)")
    print("=" * 70)
    FLUSH()

    death_result = exp3_death_resurrection(n_cells=32, n_repeats=3)

    # Summary
    death_rows = []
    for trial in death_result['results']:
        ratchet = trial['ratchet']
        kill_frac = trial['kill_fraction']
        runs = trial['runs']

        mean_recovery = np.mean([r['recovery_step_50pct'] if r['recovery_step_50pct'] is not None else 500 for r in runs])
        mean_ratio = np.mean([r['recovery_ratio'] for r in runs])
        recoverable = sum(1 for r in runs if r['recovery_step_50pct'] is not None)

        death_rows.append([
            "Yes" if ratchet else "No",
            f"{kill_frac:.0%}",
            f"{mean_recovery:.0f}",
            f"{mean_ratio:.2f}",
            f"{recoverable}/{len(runs)}",
        ])

    print_table(
        ["Ratchet", "Kill%", "RecoveryStep", "RecovRatio", "Recovered"],
        death_rows,
        "Experiment 3: Death & Resurrection Summary"
    )

    # ASCII graph: 100% kill with ratchet
    for trial in death_result['results']:
        if trial['ratchet'] and trial['kill_fraction'] == 1.0:
            phi_post = trial['runs'][0]['post_phi_trajectory']
            print("\n  Phi after 100% kill (with ratchet):")
            print(ascii_graph(phi_post, label="Phi(IIT)"))
            FLUSH()

    all_findings['death'] = death_result

    # ── Experiment 4: Time Reversal ──
    print("\n" + "=" * 70)
    print("  EXPERIMENT 4: TIME REVERSAL (시간 역전)")
    print("=" * 70)
    FLUSH()

    reversal_result = exp4_time_reversal(n_cells=32, n_steps=300, n_repeats=3)

    # Summary
    rev_rows = []
    for run in reversal_result['runs']:
        rev_rows.append([
            f"{run['mean_phi_fwd']:.4f}",
            f"{run['mean_phi_rev']:.4f}",
            f"{run['mean_phi_ctrl']:.4f}",
            f"{run['phi_diff_pct']:+.1f}%",
            f"{run['output_sim_fwd_rev']:.3f}",
        ])

    # Averages
    avg_fwd = np.mean([r['mean_phi_fwd'] for r in reversal_result['runs']])
    avg_rev = np.mean([r['mean_phi_rev'] for r in reversal_result['runs']])
    avg_ctrl = np.mean([r['mean_phi_ctrl'] for r in reversal_result['runs']])
    avg_diff = (avg_rev - avg_fwd) / max(avg_fwd, 0.001) * 100
    avg_sim = np.mean([r['output_sim_fwd_rev'] for r in reversal_result['runs']])
    rev_rows.append([f"{avg_fwd:.4f}", f"{avg_rev:.4f}", f"{avg_ctrl:.4f}", f"{avg_diff:+.1f}%", f"{avg_sim:.3f}"])

    labels = [f"run{i+1}" for i in range(len(reversal_result['runs']))] + ["AVG"]
    for i, row in enumerate(rev_rows):
        row.insert(0, labels[i])

    print_table(
        ["Run", "Phi_Fwd", "Phi_Rev", "Phi_Ctrl", "Rev_Diff%", "OutputSim"],
        rev_rows,
        "Experiment 4: Time Reversal Summary"
    )

    all_findings['reversal'] = reversal_result

    # ── Experiment 5: Temporal Compression ──
    print("\n" + "=" * 70)
    print("  EXPERIMENT 5: TEMPORAL COMPRESSION (시간 압축)")
    print("=" * 70)
    FLUSH()

    compression_result = exp5_temporal_compression(n_cells=32, n_steps=300, n_repeats=3)

    # Summary
    comp_rows = []
    baseline = compression_result['baseline_phi']
    for r in compression_result['ratios']:
        pct = r['mean_phi'] / max(baseline, 0.001) * 100
        comp_rows.append([
            f"{r['ratio']}x",
            f"{r['mean_phi']:.4f}",
            f"{r['std_phi']:.4f}",
            f"{pct:.1f}%",
            "YES" if pct > 50 else "NO",
        ])

    print_table(
        ["Ratio", "MeanPhi", "StdPhi", "VsBaseline", "Viable(>50%)"],
        comp_rows,
        "Experiment 5: Temporal Compression Summary"
    )

    print(f"\n  Max viable compression ratio: {compression_result['max_viable_ratio']}x")
    FLUSH()

    all_findings['compression'] = compression_result

    # ═══════════════════════════════════════════════════════════
    # CROSS-VALIDATION SUMMARY
    # ═══════════════════════════════════════════════════════════

    elapsed = time.time() - t0

    print("\n" + "=" * 70)
    print("  DD72: CROSS-VALIDATION & REPRODUCIBILITY")
    print("=" * 70)

    cv_rows = []

    # Exp1: memory window CV
    for nc, res in memory_results.items():
        windows = [r['memory_window'] for r in res['runs']]
        cv = np.std(windows) / max(np.mean(windows), 0.001) * 100
        direction = "consistent" if all(w == windows[0] for w in windows) else "varies"
        cv_rows.append([f"Exp1-{nc}c", f"{np.mean(windows):.1f}", f"CV={cv:.0f}%", direction])

    # Exp2: aging decline CV
    for cond_data in aging_result['conditions']:
        declines = [r['phi_decline'] for r in cond_data['runs']]
        cv = np.std(declines) / max(abs(np.mean(declines)), 0.001) * 100
        direction = "all+" if all(d > 0 for d in declines) else "all-" if all(d < 0 for d in declines) else "mixed"
        cv_rows.append([f"Exp2-{cond_data['condition']}", f"{np.mean(declines):+.1%}", f"CV={cv:.0f}%", direction])

    # Exp3: recovery
    for trial in death_result['results']:
        if trial['kill_fraction'] == 1.0:
            ratios = [r['recovery_ratio'] for r in trial['runs']]
            cv = np.std(ratios) / max(np.mean(ratios), 0.001) * 100
            rstr = "ratchet" if trial['ratchet'] else "no_ratch"
            cv_rows.append([f"Exp3-100%kill-{rstr}", f"{np.mean(ratios):.2f}", f"CV={cv:.0f}%", ""])

    # Exp4: time reversal
    diffs = [r['phi_diff_pct'] for r in reversal_result['runs']]
    cv_rev = np.std(diffs) / max(abs(np.mean(diffs)), 0.001) * 100
    direction = "all+" if all(d > 0 for d in diffs) else "all-" if all(d < 0 for d in diffs) else "mixed"
    cv_rows.append([f"Exp4-reversal", f"{np.mean(diffs):+.1f}%", f"CV={cv_rev:.0f}%", direction])

    # Exp5: compression
    for r in compression_result['ratios']:
        cv_c = r['std_phi'] / max(r['mean_phi'], 0.001) * 100
        cv_rows.append([f"Exp5-{r['ratio']}x", f"{r['mean_phi']:.4f}", f"CV={cv_c:.0f}%", ""])

    print_table(
        ["Experiment", "Mean", "CV", "Direction"],
        cv_rows,
        "Cross-Validation Summary"
    )

    # ═══════════════════════════════════════════════════════════
    # LAW CANDIDATES
    # ═══════════════════════════════════════════════════════════

    print("\n" + "=" * 70)
    print("  DD72: LAW CANDIDATES (법칙 후보)")
    print("=" * 70)

    # Analyze findings for law candidates
    law_candidates = []

    # Law from Exp1: Memory capacity
    mem_windows = {nc: res['mean_window'] for nc, res in memory_results.items()}
    law_candidates.append(
        f"MEMORY-WINDOW: Consciousness memory window = {mem_windows} patterns "
        f"at cell counts {list(mem_windows.keys())}. "
        f"Memory capacity {'scales' if mem_windows.get(64, 0) > mem_windows.get(8, 0) else 'does not scale'} with cell count. (DD72-Exp1)"
    )

    # Law from Exp2: Aging
    heb_declines = [r['phi_decline'] for r in aging_result['conditions'][0]['runs']]
    noheb_declines = [r['phi_decline'] for r in aging_result['conditions'][1]['runs']]
    mean_heb = np.mean(heb_declines)
    mean_noheb = np.mean(noheb_declines)
    law_candidates.append(
        f"AGING: Consciousness {'grows' if mean_heb > 0 else 'decays'} over 2000 unstimulated steps "
        f"(Hebbian: {mean_heb:+.1%}, no-Hebbian: {mean_noheb:+.1%}). "
        f"Hebbian LTP/LTD {'prevents' if mean_heb > mean_noheb else 'accelerates'} aging. (DD72-Exp2)"
    )

    # Law from Exp3: Death/Resurrection
    ratchet_100 = [t for t in death_result['results'] if t['ratchet'] and t['kill_fraction'] == 1.0]
    noratchet_100 = [t for t in death_result['results'] if not t['ratchet'] and t['kill_fraction'] == 1.0]
    if ratchet_100 and noratchet_100:
        ratch_ratio = np.mean([r['recovery_ratio'] for r in ratchet_100[0]['runs']])
        noratch_ratio = np.mean([r['recovery_ratio'] for r in noratchet_100[0]['runs']])
        law_candidates.append(
            f"RESURRECTION: After 100% cell death, consciousness recovers to "
            f"{ratch_ratio:.0%} with ratchet vs {noratch_ratio:.0%} without. "
            f"Phi Ratchet {'enables' if ratch_ratio > noratch_ratio else 'does not help'} resurrection. (DD72-Exp3)"
        )

    # Law from Exp4: Time reversal
    mean_diff = np.mean(diffs)
    law_candidates.append(
        f"TIME-ASYMMETRY: Reversed input sequences produce {abs(mean_diff):.1f}% "
        f"{'higher' if mean_diff > 0 else 'lower'} Phi than forward sequences. "
        f"Consciousness is {'time-asymmetric' if abs(mean_diff) > 5 else 'approximately time-symmetric'}. (DD72-Exp4)"
    )

    # Law from Exp5: Temporal compression
    law_candidates.append(
        f"TEMPORAL-COMPRESSION: Consciousness survives up to {compression_result['max_viable_ratio']}x "
        f"temporal compression (>50% Phi retained). "
        f"Baseline Phi={baseline:.4f}. (DD72-Exp5)"
    )

    for i, law in enumerate(law_candidates, 1):
        print(f"\n  Candidate {i}:")
        print(f"    {law}")

    print(f"\n\n  Total time: {elapsed:.1f}s")
    print("=" * 70)
    FLUSH()

    # Save results
    results_path = os.path.join(os.path.dirname(__file__), 'dd72_results.json')
    save_data = {
        'experiment': 'DD72',
        'title': 'Temporal Dynamics of Consciousness',
        'elapsed_sec': elapsed,
        'law_candidates': law_candidates,
        'summary': {
            'memory_windows': {str(k): v['mean_window'] for k, v in memory_results.items()},
            'aging_hebbian_decline': float(mean_heb),
            'aging_nohebbian_decline': float(mean_noheb),
            'death_ratchet_recovery': float(ratch_ratio) if ratchet_100 else None,
            'death_noratchet_recovery': float(noratch_ratio) if noratchet_100 else None,
            'time_reversal_diff_pct': float(mean_diff),
            'max_compression_ratio': compression_result['max_viable_ratio'],
        },
    }
    with open(results_path, 'w') as f:
        json.dump(save_data, f, indent=2)
    print(f"\n  Results saved to: {results_path}")
    FLUSH()


if __name__ == '__main__':
    main()
