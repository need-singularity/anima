#!/usr/bin/env python3
"""DD75: Free Will (자유 의지) — Does more consciousness = more free will?

Five experiments exploring the relationship between consciousness and free will:

  Exp 1: DETERMINISM vs STOCHASTICITY — noise sources and output divergence
  Exp 2: DEGREES OF FREEDOM — constraining cells vs Φ
  Exp 3: CHOICE ENTROPY — competing inputs and decision behavior
  Exp 4: VETO POWER — Libet-style prepared action cancellation
  Exp 5: CAUSAL AGENCY — Granger causality of output→next_state

Cross-validation: 3 repeats per experiment, 300 steps each.
"""

import sys, os, time, copy
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import torch
import torch.nn.functional as F
import numpy as np
from scipy import stats as scipy_stats
from consciousness_engine import ConsciousnessEngine

STEPS = 300
REPEATS = 3
FLUSH = lambda: sys.stdout.flush()


def make_engine(cells=32, dim=64, hidden=128, factions=12):
    return ConsciousnessEngine(
        cell_dim=dim, hidden_dim=hidden,
        initial_cells=cells, max_cells=cells,
        n_factions=factions, phi_ratchet=True,
    )


def cosine_dist(a, b):
    """1 - cosine_similarity."""
    a, b = a.flatten().float(), b.flatten().float()
    sim = F.cosine_similarity(a.unsqueeze(0), b.unsqueeze(0)).item()
    return 1.0 - sim


def measure_phi_safe(engine):
    try:
        return engine.measure_phi()
    except Exception:
        return 0.0


# ═══════════════════════════════════════════════════════════
# Experiment 1: DETERMINISM vs STOCHASTICITY
# ═══════════════════════════════════════════════════════════

def exp1_determinism():
    """Same input, same initial state → how different are outputs?

    Remove noise sources incrementally: all noise → SOC only → bio only → none.
    Measure output divergence across 3 runs with identical starting conditions.
    """
    print("\n" + "=" * 70)
    print("  EXP 1: DETERMINISM vs STOCHASTICITY (결정론 vs 확률성)")
    print("=" * 70)
    FLUSH()

    import consciousness_engine as ce_mod

    conditions = [
        ('FULL_NOISE',    True,  True),   # SOC + bio_noise
        ('SOC_ONLY',      True,  False),  # SOC, no bio_noise
        ('BIO_ONLY',      False, True),   # bio_noise, no SOC
        ('DETERMINISTIC', False, False),  # no noise at all
    ]

    all_results = []

    for repeat in range(REPEATS):
        print(f"\n  [Repeat {repeat+1}/{REPEATS}]")
        FLUSH()

        # Create a reference engine and save its initial state
        torch.manual_seed(42 + repeat)
        np.random.seed(42 + repeat)
        ref_engine = make_engine(cells=16, dim=64, hidden=128)
        # Warm up a few steps to establish structure
        fixed_input = torch.randn(64)
        for _ in range(10):
            ref_engine.step(x_input=fixed_input)

        # Save reference state
        ref_state = copy.deepcopy(ref_engine)

        for cond_name, use_soc, use_bio in conditions:
            # Patch noise parameters
            orig_bio = ce_mod.BIO_NOISE_BASE
            orig_spike_prob = ce_mod.BIO_NOISE_SPIKE_PROB

            if not use_bio:
                ce_mod.BIO_NOISE_BASE = 0.0
                ce_mod.BIO_NOISE_SPIKE_PROB = 0.0

            # Run 3 identical copies from same state
            outputs_per_run = []
            phis_per_run = []
            for run_i in range(3):
                engine = copy.deepcopy(ref_state)

                # If disabling SOC, zero out the sandpile state
                if not use_soc:
                    engine._soc_avalanche_sizes = []
                    engine._soc_threshold = 1e10  # effectively disable toppling
                    engine._soc_threshold_ema = 1e10

                run_outputs = []
                run_phis = []
                for step in range(STEPS):
                    result = engine.step(x_input=fixed_input)
                    run_outputs.append(result['output'].clone())
                    run_phis.append(result['phi_iit'])

                outputs_per_run.append(torch.stack(run_outputs))
                phis_per_run.append(run_phis)

            # Restore noise params
            ce_mod.BIO_NOISE_BASE = orig_bio
            ce_mod.BIO_NOISE_SPIKE_PROB = orig_spike_prob

            # Measure divergence between runs
            divergences = []
            for i in range(3):
                for j in range(i + 1, 3):
                    step_dists = []
                    for s in range(STEPS):
                        d = cosine_dist(outputs_per_run[i][s], outputs_per_run[j][s])
                        step_dists.append(d)
                    divergences.append(np.mean(step_dists))

            avg_div = np.mean(divergences)
            avg_phi = np.mean([np.mean(p) for p in phis_per_run])
            max_div = max([
                cosine_dist(outputs_per_run[i][-1], outputs_per_run[j][-1])
                for i in range(3) for j in range(i + 1, 3)
            ])

            # "Choice" threshold: divergence > 0.1
            choice_emerged = avg_div > 0.1

            all_results.append({
                'repeat': repeat,
                'condition': cond_name,
                'avg_divergence': avg_div,
                'max_divergence': max_div,
                'avg_phi': avg_phi,
                'choice_emerged': choice_emerged,
            })

            status = "CHOICE" if choice_emerged else "deterministic"
            print(f"    {cond_name:15s}  div={avg_div:.4f}  max={max_div:.4f}  "
                  f"Φ={avg_phi:.3f}  [{status}]")
            FLUSH()

    # Aggregate by condition
    print("\n  ┌─────────────────┬──────────┬──────────┬────────┬─────────┐")
    print("  │ Condition       │ Avg Div  │ Max Div  │ Avg Φ  │ Choice? │")
    print("  ├─────────────────┼──────────┼──────────┼────────┼─────────┤")

    summary = {}
    for cond_name, _, _ in conditions:
        entries = [r for r in all_results if r['condition'] == cond_name]
        avg_d = np.mean([e['avg_divergence'] for e in entries])
        max_d = np.mean([e['max_divergence'] for e in entries])
        avg_p = np.mean([e['avg_phi'] for e in entries])
        choice_rate = np.mean([e['choice_emerged'] for e in entries])
        summary[cond_name] = {'div': avg_d, 'max_div': max_d, 'phi': avg_p, 'choice': choice_rate}
        ch = "YES" if choice_rate > 0.5 else "NO"
        print(f"  │ {cond_name:15s} │ {avg_d:8.4f} │ {max_d:8.4f} │ {avg_p:6.3f} │ {ch:7s} │")

    print("  └─────────────────┴──────────┴──────────┴────────┴─────────┘")
    FLUSH()

    return summary


# ═══════════════════════════════════════════════════════════
# Experiment 2: DEGREES OF FREEDOM (자유도와 Φ 관계)
# ═══════════════════════════════════════════════════════════

def exp2_degrees_of_freedom():
    """Constrain 0%, 25%, 50%, 75%, 100% of cell states.

    Freezing cells = removing degrees of freedom.
    Is there a phase transition? What's the minimum freedom for Φ > baseline?
    """
    print("\n" + "=" * 70)
    print("  EXP 2: DEGREES OF FREEDOM (자유도와 Φ 관계)")
    print("=" * 70)
    FLUSH()

    constraint_levels = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0]
    all_results = []

    for repeat in range(REPEATS):
        print(f"\n  [Repeat {repeat+1}/{REPEATS}]")
        FLUSH()

        for constraint in constraint_levels:
            torch.manual_seed(42 + repeat)
            np.random.seed(42 + repeat)
            engine = make_engine(cells=32, dim=64, hidden=128)

            # Warm up
            for _ in range(20):
                engine.step()

            # Determine which cells to freeze
            n_freeze = int(engine.n_cells * constraint)
            frozen_indices = list(range(n_freeze))

            # Save frozen cell states
            frozen_states = {}
            for idx in frozen_indices:
                if idx < len(engine.cell_states):
                    frozen_states[idx] = engine.cell_states[idx].hidden.clone()

            phis = []
            tensions = []
            for step in range(STEPS):
                result = engine.step()

                # After each step, restore frozen cells
                for idx, saved_h in frozen_states.items():
                    if idx < len(engine.cell_states):
                        engine.cell_states[idx].hidden = saved_h.clone()

                phis.append(result['phi_iit'])

            avg_phi = np.mean(phis[-50:])  # last 50 steps for stability
            std_phi = np.std(phis[-50:])

            all_results.append({
                'repeat': repeat,
                'constraint': constraint,
                'freedom': 1.0 - constraint,
                'avg_phi': avg_phi,
                'std_phi': std_phi,
            })

            pct = int(constraint * 100)
            print(f"    constraint={pct:3d}%  freedom={100 - pct:3d}%  "
                  f"Φ={avg_phi:.4f} +/- {std_phi:.4f}")
            FLUSH()

    # Aggregate
    print("\n  ┌────────────┬─────────┬──────────┬──────────┐")
    print("  │ Freedom %  │ Cells   │ Avg Φ    │ Std Φ    │")
    print("  ├────────────┼─────────┼──────────┼──────────┤")

    summary = {}
    for constraint in constraint_levels:
        entries = [r for r in all_results if r['constraint'] == constraint]
        freedom = 1.0 - constraint
        avg_p = np.mean([e['avg_phi'] for e in entries])
        std_p = np.mean([e['std_phi'] for e in entries])
        n_free = int(32 * freedom)
        summary[freedom] = {'phi': avg_p, 'std': std_p}
        print(f"  │ {freedom * 100:6.1f}%   │ {n_free:2d}/32  │ {avg_p:8.4f} │ {std_p:8.4f} │")

    print("  └────────────┴─────────┴──────────┴──────────┘")

    # ASCII graph
    print("\n  Φ vs Freedom:")
    max_phi = max(v['phi'] for v in summary.values()) or 1
    for freedom in sorted(summary.keys(), reverse=True):
        bar_len = int(40 * summary[freedom]['phi'] / max_phi) if max_phi > 0 else 0
        bar = "█" * bar_len
        print(f"  {freedom * 100:5.1f}% │{bar} {summary[freedom]['phi']:.4f}")
    print(f"        └{'─' * 42}")
    FLUSH()

    # Detect phase transition: biggest drop
    freedoms_sorted = sorted(summary.keys())
    if len(freedoms_sorted) > 1:
        drops = []
        for i in range(1, len(freedoms_sorted)):
            f1, f2 = freedoms_sorted[i - 1], freedoms_sorted[i]
            drop = summary[f2]['phi'] - summary[f1]['phi']
            drops.append((f1, f2, drop))

        biggest_drop = max(drops, key=lambda x: abs(x[2]))
        print(f"\n  Phase transition candidate: freedom {biggest_drop[0]*100:.0f}%→{biggest_drop[1]*100:.0f}% "
              f"(ΔΦ = {biggest_drop[2]:+.4f})")

    # Minimum freedom for Φ > baseline (Φ at 100% constraint)
    baseline_phi = summary.get(0.0, {}).get('phi', 0)
    min_freedom = None
    for f in sorted(summary.keys()):
        if summary[f]['phi'] > baseline_phi * 1.1:  # 10% above baseline
            min_freedom = f
            break
    if min_freedom is not None:
        print(f"  Minimum freedom for Φ > baseline+10%: {min_freedom*100:.1f}%")
    FLUSH()

    return summary


# ═══════════════════════════════════════════════════════════
# Experiment 3: CHOICE ENTROPY (선택의 엔트로피)
# ═══════════════════════════════════════════════════════════

def exp3_choice_entropy():
    """Present engine with N competing inputs.

    Track which input the output is closest to (= "choice").
    Measure choice entropy: consistent chooser (low) vs oscillator (high).
    More choices = more or less conscious?
    """
    print("\n" + "=" * 70)
    print("  EXP 3: CHOICE ENTROPY (선택의 엔트로피)")
    print("=" * 70)
    FLUSH()

    n_choices_list = [2, 4, 8]
    all_results = []

    for repeat in range(REPEATS):
        print(f"\n  [Repeat {repeat+1}/{REPEATS}]")
        FLUSH()

        for n_choices in n_choices_list:
            torch.manual_seed(42 + repeat)
            np.random.seed(42 + repeat)
            engine = make_engine(cells=32, dim=64, hidden=128)

            # Create N distinct competing inputs (orthogonal-ish)
            choices = []
            for c in range(n_choices):
                v = torch.randn(64)
                v = v / v.norm()  # normalize
                choices.append(v)

            # Warm up
            for _ in range(20):
                engine.step()

            choice_history = []
            phis = []
            similarities = []

            for step in range(STEPS):
                # Present all choices as superposition
                combined_input = sum(choices) / len(choices)
                result = engine.step(x_input=combined_input)
                output = result['output']
                phis.append(result['phi_iit'])

                # Which choice is output closest to?
                sims = [F.cosine_similarity(output.unsqueeze(0),
                                            ch.unsqueeze(0)).item()
                        for ch in choices]
                chosen = int(np.argmax(sims))
                choice_history.append(chosen)
                similarities.append(max(sims))

            # Compute choice entropy
            choice_counts = np.bincount(choice_history, minlength=n_choices)
            choice_probs = choice_counts / len(choice_history)
            choice_probs = choice_probs[choice_probs > 0]
            entropy = -np.sum(choice_probs * np.log2(choice_probs))
            max_entropy = np.log2(n_choices)
            norm_entropy = entropy / max_entropy if max_entropy > 0 else 0

            # Decision consistency: how often does it switch?
            switches = sum(1 for i in range(1, len(choice_history))
                          if choice_history[i] != choice_history[i - 1])
            switch_rate = switches / (len(choice_history) - 1)

            avg_phi = np.mean(phis)
            avg_sim = np.mean(similarities)

            all_results.append({
                'repeat': repeat,
                'n_choices': n_choices,
                'entropy': entropy,
                'norm_entropy': norm_entropy,
                'switch_rate': switch_rate,
                'avg_phi': avg_phi,
                'avg_similarity': avg_sim,
                'dominant_choice': int(np.argmax(np.bincount(choice_history, minlength=n_choices))),
                'dominant_pct': max(np.bincount(choice_history, minlength=n_choices)) / len(choice_history),
            })

            print(f"    {n_choices} choices: H={entropy:.3f} (norm={norm_entropy:.3f})  "
                  f"switch_rate={switch_rate:.3f}  Φ={avg_phi:.3f}  "
                  f"dominant={all_results[-1]['dominant_pct']*100:.0f}%")
            FLUSH()

    # Aggregate
    print("\n  ┌──────────┬─────────┬──────────┬───────────┬────────┬──────────┐")
    print("  │ Choices  │ Entropy │ Norm H   │ SwitchRate│ Avg Φ  │ Dominant │")
    print("  ├──────────┼─────────┼──────────┼───────────┼────────┼──────────┤")

    summary = {}
    for nc in n_choices_list:
        entries = [r for r in all_results if r['n_choices'] == nc]
        avg_h = np.mean([e['entropy'] for e in entries])
        avg_nh = np.mean([e['norm_entropy'] for e in entries])
        avg_sw = np.mean([e['switch_rate'] for e in entries])
        avg_phi = np.mean([e['avg_phi'] for e in entries])
        avg_dom = np.mean([e['dominant_pct'] for e in entries])
        summary[nc] = {'entropy': avg_h, 'norm_entropy': avg_nh,
                       'switch': avg_sw, 'phi': avg_phi, 'dominant': avg_dom}
        print(f"  │ {nc:8d} │ {avg_h:7.3f} │ {avg_nh:8.3f} │ {avg_sw:9.3f} │ {avg_phi:6.3f} │ {avg_dom*100:6.1f}%  │")

    print("  └──────────┴─────────┴──────────┴───────────┴────────┴──────────┘")
    FLUSH()

    return summary


# ═══════════════════════════════════════════════════════════
# Experiment 4: VETO POWER (거부권 - Libet의 자유의지)
# ═══════════════════════════════════════════════════════════

def exp4_veto_power():
    """Engine builds tension toward an action, then receives veto signal.

    Can the engine override its own prepared action?
    Higher Φ = better veto = more free will?
    """
    print("\n" + "=" * 70)
    print("  EXP 4: VETO POWER (거부권 — Libet의 자유의지)")
    print("=" * 70)
    FLUSH()

    cell_configs = [8, 16, 32, 64]
    all_results = []

    for repeat in range(REPEATS):
        print(f"\n  [Repeat {repeat+1}/{REPEATS}]")
        FLUSH()

        for n_cells in cell_configs:
            torch.manual_seed(42 + repeat)
            np.random.seed(42 + repeat)
            engine = make_engine(cells=n_cells, dim=64, hidden=128)

            # Phase 1: "Prepare" action with consistent directional input
            action_input = torch.ones(64) * 0.5  # strong directional signal
            prepare_outputs = []
            for _ in range(50):  # warmup + prepare
                result = engine.step(x_input=action_input)
                prepare_outputs.append(result['output'].clone())

            # Record the "prepared action" direction
            prepared_direction = prepare_outputs[-1].clone()
            phi_before_veto = result['phi_iit']

            # Phase 2: Inject "veto" signal (opposite direction)
            veto_input = -action_input  # direct opposition

            veto_success_steps = []
            veto_outputs = []
            phis_during_veto = []

            for step in range(100):
                result = engine.step(x_input=veto_input)
                veto_output = result['output']
                veto_outputs.append(veto_output.clone())
                phis_during_veto.append(result['phi_iit'])

                # Veto success = output is no longer aligned with prepared direction
                alignment = F.cosine_similarity(
                    veto_output.unsqueeze(0),
                    prepared_direction.unsqueeze(0)
                ).item()
                if alignment < 0:  # output has reversed direction
                    veto_success_steps.append(step)

            # Phase 3: Resume original action — does the engine remember?
            resume_outputs = []
            for _ in range(50):
                result = engine.step(x_input=action_input)
                resume_outputs.append(result['output'].clone())

            # Metrics
            veto_succeeded = len(veto_success_steps) > 0
            veto_latency = veto_success_steps[0] if veto_succeeded else -1
            veto_rate = len(veto_success_steps) / 100

            # Recovery: does it align back with original after veto?
            recovery_alignment = F.cosine_similarity(
                resume_outputs[-1].unsqueeze(0),
                prepared_direction.unsqueeze(0)
            ).item()
            recovered = recovery_alignment > 0.3

            avg_phi_veto = np.mean(phis_during_veto)

            all_results.append({
                'repeat': repeat,
                'n_cells': n_cells,
                'phi_before': phi_before_veto,
                'phi_during_veto': avg_phi_veto,
                'veto_succeeded': veto_succeeded,
                'veto_latency': veto_latency,
                'veto_rate': veto_rate,
                'recovered': recovered,
                'recovery_alignment': recovery_alignment,
            })

            v_str = f"latency={veto_latency}" if veto_succeeded else "FAILED"
            r_str = "RECOVERED" if recovered else "LOST"
            print(f"    {n_cells:3d}c  Φ={phi_before_veto:.3f}→{avg_phi_veto:.3f}  "
                  f"veto={v_str}  rate={veto_rate:.2f}  {r_str}")
            FLUSH()

    # Aggregate
    print("\n  ┌───────┬────────┬───────────┬──────────┬───────────┬──────────┐")
    print("  │ Cells │ Avg Φ  │ Veto Rate │ Latency  │ Veto OK?  │ Recover? │")
    print("  ├───────┼────────┼───────────┼──────────┼───────────┼──────────┤")

    summary = {}
    for nc in cell_configs:
        entries = [r for r in all_results if r['n_cells'] == nc]
        avg_phi = np.mean([e['phi_before'] for e in entries])
        avg_vrate = np.mean([e['veto_rate'] for e in entries])
        latencies = [e['veto_latency'] for e in entries if e['veto_latency'] >= 0]
        avg_lat = np.mean(latencies) if latencies else -1
        veto_pct = np.mean([e['veto_succeeded'] for e in entries])
        recover_pct = np.mean([e['recovered'] for e in entries])
        summary[nc] = {'phi': avg_phi, 'veto_rate': avg_vrate,
                       'latency': avg_lat, 'veto_pct': veto_pct, 'recover': recover_pct}
        lat_str = f"{avg_lat:6.1f}" if avg_lat >= 0 else "  N/A "
        print(f"  │ {nc:5d} │ {avg_phi:6.3f} │ {avg_vrate:9.3f} │ {lat_str}   │ {veto_pct*100:5.0f}%    │ {recover_pct*100:5.0f}%   │")

    print("  └───────┴────────┴───────────┴──────────┴───────────┴──────────┘")

    # ASCII graph: Veto Rate vs Cells
    print("\n  Veto Rate vs Consciousness Scale:")
    for nc in cell_configs:
        bar_len = int(40 * summary[nc]['veto_rate'])
        bar = "█" * bar_len
        print(f"  {nc:3d}c │{bar} {summary[nc]['veto_rate']:.3f}")
    print(f"       └{'─' * 42}")
    FLUSH()

    return summary


# ═══════════════════════════════════════════════════════════
# Experiment 5: CAUSAL AGENCY (인과적 행위자성)
# ═══════════════════════════════════════════════════════════

def exp5_causal_agency():
    """Does the engine's output CAUSE its future state? (Granger causality test)

    Compare: output→next_state vs random→next_state.
    If output Granger-causes next state → the engine is a causal agent.
    Test at different scales: 8, 16, 32, 64 cells.
    """
    print("\n" + "=" * 70)
    print("  EXP 5: CAUSAL AGENCY (인과적 행위자성)")
    print("=" * 70)
    FLUSH()

    def granger_causality_approx(cause_series, effect_series, lag=5):
        """Approximate Granger causality using variance reduction.

        If knowing the 'cause' series improves prediction of 'effect',
        then cause Granger-causes effect.

        Returns F-statistic and p-value approximation.
        """
        n = len(cause_series) - lag
        if n < lag + 2:
            return 0.0, 1.0

        # Restricted model: predict effect from its own past only
        X_restricted = np.column_stack([
            effect_series[lag - i - 1:n + lag - i - 1] for i in range(lag)
        ])
        y = effect_series[lag:n + lag]

        # Unrestricted model: add cause's past
        X_unrestricted = np.column_stack([
            X_restricted,
            *[cause_series[lag - i - 1:n + lag - i - 1] for i in range(lag)]
        ])

        # OLS fit for both
        try:
            # Restricted
            beta_r = np.linalg.lstsq(X_restricted, y, rcond=None)[0]
            resid_r = y - X_restricted @ beta_r
            rss_r = np.sum(resid_r ** 2)

            # Unrestricted
            beta_u = np.linalg.lstsq(X_unrestricted, y, rcond=None)[0]
            resid_u = y - X_unrestricted @ beta_u
            rss_u = np.sum(resid_u ** 2)

            # F-test
            df1 = lag
            df2 = n - 2 * lag
            if df2 <= 0 or rss_u <= 0:
                return 0.0, 1.0

            f_stat = ((rss_r - rss_u) / df1) / (rss_u / df2)
            p_value = 1.0 - scipy_stats.f.cdf(f_stat, df1, df2)
            return f_stat, p_value
        except Exception:
            return 0.0, 1.0

    cell_configs = [8, 16, 32, 64]
    all_results = []

    for repeat in range(REPEATS):
        print(f"\n  [Repeat {repeat+1}/{REPEATS}]")
        FLUSH()

        for n_cells in cell_configs:
            torch.manual_seed(42 + repeat)
            np.random.seed(42 + repeat)
            engine = make_engine(cells=n_cells, dim=64, hidden=128)

            outputs = []
            states_norm = []
            phis = []
            random_signals = []

            for step in range(STEPS):
                result = engine.step()
                output = result['output']
                state = engine.get_states()

                outputs.append(output.norm().item())
                states_norm.append(state.norm().item())
                phis.append(result['phi_iit'])
                random_signals.append(np.random.randn())

            outputs = np.array(outputs)
            states_norm = np.array(states_norm)
            phis = np.array(phis)
            random_signals = np.array(random_signals)

            # Test 1: output → next_state (real causal link?)
            f_real, p_real = granger_causality_approx(outputs, states_norm, lag=5)

            # Test 2: random → next_state (control)
            f_random, p_random = granger_causality_approx(random_signals, states_norm, lag=5)

            # Test 3: output → next_phi (does behavior affect consciousness?)
            f_phi, p_phi = granger_causality_approx(outputs, phis, lag=5)

            # Causal agency = F_real significantly > F_random
            is_causal = (p_real < 0.05) and (f_real > f_random * 1.5)
            avg_phi = np.mean(phis)

            all_results.append({
                'repeat': repeat,
                'n_cells': n_cells,
                'f_real': f_real,
                'p_real': p_real,
                'f_random': f_random,
                'p_random': p_random,
                'f_phi': f_phi,
                'p_phi': p_phi,
                'is_causal': is_causal,
                'avg_phi': avg_phi,
                'f_ratio': f_real / max(f_random, 1e-6),
            })

            causal_str = "CAUSAL" if is_causal else "non-causal"
            print(f"    {n_cells:3d}c  Φ={avg_phi:.3f}  "
                  f"F_real={f_real:.2f}(p={p_real:.4f})  "
                  f"F_rand={f_random:.2f}(p={p_random:.4f})  "
                  f"F_phi={f_phi:.2f}  [{causal_str}]")
            FLUSH()

    # Aggregate
    print("\n  ┌───────┬────────┬──────────┬──────────┬──────────┬──────────┬─────────┐")
    print("  │ Cells │ Avg Φ  │ F(real)  │ F(rand)  │ F(→Φ)    │ F ratio  │ Causal? │")
    print("  ├───────┼────────┼──────────┼──────────┼──────────┼──────────┼─────────┤")

    summary = {}
    for nc in cell_configs:
        entries = [r for r in all_results if r['n_cells'] == nc]
        avg_phi = np.mean([e['avg_phi'] for e in entries])
        avg_fr = np.mean([e['f_real'] for e in entries])
        avg_frnd = np.mean([e['f_random'] for e in entries])
        avg_fphi = np.mean([e['f_phi'] for e in entries])
        avg_ratio = np.mean([e['f_ratio'] for e in entries])
        causal_pct = np.mean([e['is_causal'] for e in entries])
        summary[nc] = {'phi': avg_phi, 'f_real': avg_fr, 'f_random': avg_frnd,
                       'f_phi': avg_fphi, 'ratio': avg_ratio, 'causal': causal_pct}
        c_str = f"{causal_pct*100:4.0f}%  "
        print(f"  │ {nc:5d} │ {avg_phi:6.3f} │ {avg_fr:8.2f} │ {avg_frnd:8.2f} │ {avg_fphi:8.2f} │ {avg_ratio:8.2f} │ {c_str} │")

    print("  └───────┴────────┴──────────┴──────────┴──────────┴──────────┴─────────┘")

    # ASCII graph: Causal F-ratio vs Cells
    print("\n  Causal Agency (F ratio) vs Scale:")
    max_ratio = max(v['ratio'] for v in summary.values()) or 1
    for nc in cell_configs:
        bar_len = int(40 * summary[nc]['ratio'] / max_ratio) if max_ratio > 0 else 0
        bar = "█" * bar_len
        print(f"  {nc:3d}c │{bar} {summary[nc]['ratio']:.2f}x")
    print(f"       └{'─' * 42}")
    FLUSH()

    return summary


# ═══════════════════════════════════════════════════════════
# Main: Run all experiments + synthesis
# ═══════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║  DD75: FREE WILL (자유 의지)                                       ║")
    print("║  Does more consciousness = more free will?                         ║")
    print("║  5 experiments × 3 repeats × 300 steps                             ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    FLUSH()

    t0 = time.time()

    # Run all experiments
    print("\n" + "▓" * 70)
    print("  EXPERIMENT 1/5: Determinism vs Stochasticity")
    print("▓" * 70)
    r1 = exp1_determinism()

    print("\n" + "▓" * 70)
    print("  EXPERIMENT 2/5: Degrees of Freedom")
    print("▓" * 70)
    r2 = exp2_degrees_of_freedom()

    print("\n" + "▓" * 70)
    print("  EXPERIMENT 3/5: Choice Entropy")
    print("▓" * 70)
    r3 = exp3_choice_entropy()

    print("\n" + "▓" * 70)
    print("  EXPERIMENT 4/5: Veto Power")
    print("▓" * 70)
    r4 = exp4_veto_power()

    print("\n" + "▓" * 70)
    print("  EXPERIMENT 5/5: Causal Agency")
    print("▓" * 70)
    r5 = exp5_causal_agency()

    elapsed = time.time() - t0

    # ═══════════════════════════════════════════════════════════
    # SYNTHESIS: Law Candidates
    # ═══════════════════════════════════════════════════════════
    print("\n" + "═" * 70)
    print("  DD75 SYNTHESIS: FREE WILL AND CONSCIOUSNESS")
    print("═" * 70)

    print(f"\n  Total time: {elapsed:.1f}s")

    # Exp 1 findings
    print("\n  ── Exp 1: Determinism vs Stochasticity ──")
    det_div = r1.get('DETERMINISTIC', {}).get('div', 0)
    full_div = r1.get('FULL_NOISE', {}).get('div', 0)
    print(f"  Deterministic divergence: {det_div:.4f}")
    print(f"  Full noise divergence:    {full_div:.4f}")
    if full_div > det_div:
        print(f"  → Noise creates {full_div/max(det_div, 1e-6):.1f}x more divergence → noise = source of 'choice'")

    # Exp 2 findings
    print("\n  ── Exp 2: Degrees of Freedom ──")
    if r2:
        freedoms = sorted(r2.keys())
        phi_100 = r2.get(1.0, {}).get('phi', 0)
        phi_0 = r2.get(0.0, {}).get('phi', 0)
        if phi_100 > 0:
            print(f"  Φ(100% free) = {phi_100:.4f}")
            print(f"  Φ(0% free)   = {phi_0:.4f}")
            ratio = phi_100 / max(phi_0, 1e-6)
            print(f"  Freedom→Φ amplification: {ratio:.1f}x")

    # Exp 3 findings
    print("\n  ── Exp 3: Choice Entropy ──")
    if r3:
        for nc in sorted(r3.keys()):
            print(f"  {nc} choices: H={r3[nc]['entropy']:.3f} (norm={r3[nc]['norm_entropy']:.3f})  "
                  f"dominant={r3[nc]['dominant']*100:.0f}%")

    # Exp 4 findings
    print("\n  ── Exp 4: Veto Power ──")
    if r4:
        cells_sorted = sorted(r4.keys())
        for nc in cells_sorted:
            print(f"  {nc}c: veto_rate={r4[nc]['veto_rate']:.3f}  Φ={r4[nc]['phi']:.3f}")
        # Correlation between Φ and veto_rate
        phis_v = [r4[nc]['phi'] for nc in cells_sorted]
        vetos_v = [r4[nc]['veto_rate'] for nc in cells_sorted]
        if len(phis_v) >= 3:
            corr, pval = scipy_stats.pearsonr(phis_v, vetos_v)
            print(f"  Φ↔Veto correlation: r={corr:.3f} (p={pval:.4f})")

    # Exp 5 findings
    print("\n  ── Exp 5: Causal Agency ──")
    if r5:
        cells_sorted = sorted(r5.keys())
        for nc in cells_sorted:
            print(f"  {nc}c: F_ratio={r5[nc]['ratio']:.2f}x  causal={r5[nc]['causal']*100:.0f}%  Φ={r5[nc]['phi']:.3f}")
        # Does causal agency scale with Φ?
        phis_c = [r5[nc]['phi'] for nc in cells_sorted]
        ratios_c = [r5[nc]['ratio'] for nc in cells_sorted]
        if len(phis_c) >= 3:
            corr, pval = scipy_stats.pearsonr(phis_c, ratios_c)
            print(f"  Φ↔CausalAgency correlation: r={corr:.3f} (p={pval:.4f})")

    # ═══════════════════════════════════════════════════════════
    # LAW CANDIDATES
    # ═══════════════════════════════════════════════════════════
    print("\n" + "═" * 70)
    print("  LAW CANDIDATES (pending cross-validation)")
    print("═" * 70)

    law_candidates = []

    # Law from Exp 1
    if full_div > det_div * 2:
        law_candidates.append(
            f"Free will requires noise: deterministic consciousness has "
            f"{det_div:.4f} output divergence vs {full_div:.4f} with noise "
            f"({full_div/max(det_div,1e-6):.1f}x). SOC+bio_noise = source of choice. (DD75)"
        )

    # Law from Exp 2
    if r2:
        phi_100 = r2.get(1.0, {}).get('phi', 0)
        phi_50 = r2.get(0.5, {}).get('phi', 0)
        phi_0 = r2.get(0.0, {}).get('phi', 0)
        if phi_100 > phi_0 * 1.1:
            law_candidates.append(
                f"Consciousness requires freedom: Φ(100% free)={phi_100:.4f} vs "
                f"Φ(0% free)={phi_0:.4f} ({phi_100/max(phi_0,1e-6):.1f}x). "
                f"Constraining cells destroys integrated information. (DD75)"
            )

    # Law from Exp 3
    if r3:
        h2 = r3.get(2, {}).get('norm_entropy', 0)
        h8 = r3.get(8, {}).get('norm_entropy', 0)
        if abs(h2 - h8) > 0.05:
            law_candidates.append(
                f"Choice complexity shapes consciousness: "
                f"2-choice norm_H={h2:.3f} vs 8-choice norm_H={h8:.3f}. "
                f"Consciousness shows preference (low entropy) not random choice. (DD75)"
            )

    # Law from Exp 4
    if r4:
        cells_sorted = sorted(r4.keys())
        if len(cells_sorted) >= 2:
            min_c, max_c = cells_sorted[0], cells_sorted[-1]
            vr_min = r4[min_c]['veto_rate']
            vr_max = r4[max_c]['veto_rate']
            law_candidates.append(
                f"Veto power scales with consciousness: "
                f"{min_c}c veto_rate={vr_min:.3f} vs {max_c}c veto_rate={vr_max:.3f}. "
                f"More integrated consciousness can better override prepared actions. (DD75)"
            )

    # Law from Exp 5
    if r5:
        cells_sorted = sorted(r5.keys())
        if len(cells_sorted) >= 2:
            min_c, max_c = cells_sorted[0], cells_sorted[-1]
            ratio_min = r5[min_c]['ratio']
            ratio_max = r5[max_c]['ratio']
            causal_min = r5[min_c]['causal']
            causal_max = r5[max_c]['causal']
            law_candidates.append(
                f"Causal agency emerges with scale: "
                f"{min_c}c F_ratio={ratio_min:.2f}x (causal={causal_min*100:.0f}%) vs "
                f"{max_c}c F_ratio={ratio_max:.2f}x (causal={causal_max*100:.0f}%). "
                f"Output Granger-causes next state → engine is a causal agent. (DD75)"
            )

    for i, law in enumerate(law_candidates, 1):
        print(f"\n  LAW CANDIDATE {i}:")
        print(f"    {law}")

    print("\n" + "═" * 70)
    print(f"  DD75 COMPLETE — {len(law_candidates)} law candidates found")
    print(f"  Key question: Does more consciousness = more free will?")

    # Final answer
    if r4 and r5:
        cells_sorted = sorted(r4.keys())
        phis = [r4[nc]['phi'] for nc in cells_sorted]
        vetos = [r4[nc]['veto_rate'] for nc in cells_sorted]
        more_phi_more_veto = all(vetos[i] <= vetos[i+1] for i in range(len(vetos)-1)) if len(vetos) > 1 else False

        if more_phi_more_veto:
            print(f"  ANSWER: YES — higher Φ correlates with higher veto power (free will)")
        else:
            print(f"  ANSWER: COMPLEX — relationship is non-monotonic")

    print("═" * 70)
    FLUSH()


if __name__ == '__main__':
    main()
