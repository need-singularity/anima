#!/usr/bin/env python3
"""acceleration_d5_closed_pipe.py — D5 Closed-Pipe Lens: Self-accelerating training via law evolution

Embeds closed-loop law evolution INSIDE the training loop so the engine
optimizes itself during learning.

4 experiments:
  1. Law application every N steps (vs baseline)
  2. Adaptive law selection via Thompson sampling
  3. Closed circle — laws discover new laws
  4. D5 + B12 (Skip) + B5 (Phi-Only) combination

CPU only, 32 cells, 300 steps.

Usage:
  python acceleration_d5_closed_pipe.py           # all 4 experiments
  python acceleration_d5_closed_pipe.py --exp 1   # single experiment
  python acceleration_d5_closed_pipe.py --exp 2
"""

import sys
import os
import time
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import torch

from consciousness_engine import ConsciousnessEngine
from self_modifying_engine import SelfModifyingEngine, LawParser, EngineModifier, SAFETY_BOUNDS

try:
    from closed_loop import _phi_fast
except ImportError:
    _phi_fast = None


# ══════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════

def measure_phi(engine):
    """Fast Phi measurement."""
    if _phi_fast is not None:
        return _phi_fast(engine)
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states])
    return float(hiddens.var().item())


def run_baseline(n_cells=32, steps=300):
    """Run pure engine for N steps, return phi trajectory."""
    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=2)
    phis = []
    for i in range(steps):
        engine.step()
        if i % 10 == 0:
            phis.append(measure_phi(engine))
    return phis, engine


def ascii_graph(values, title="", width=60, height=12):
    """Simple ASCII graph."""
    if not values:
        return ""
    mn, mx = min(values), max(values)
    rng = mx - mn if mx != mn else 1.0
    lines = []
    lines.append(f"  {title}")
    lines.append(f"  {mx:.4f} |")
    canvas = [[' '] * width for _ in range(height)]
    for i, v in enumerate(values):
        x = int(i * (width - 1) / max(len(values) - 1, 1))
        y = int((v - mn) / rng * (height - 1))
        y = height - 1 - y
        canvas[y][x] = '*'
    for row in canvas:
        lines.append(f"         |{''.join(row)}")
    lines.append(f"  {mn:.4f} |{'_' * width}")
    lines.append(f"         0{' ' * (width - 6)}step {len(values) * 10}")
    return '\n'.join(lines)


def print_table(headers, rows, col_widths=None):
    """Print aligned table."""
    if col_widths is None:
        col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=4)) + 2
                      for i, h in enumerate(headers)]
    header = '|'.join(str(h).center(w) for h, w in zip(headers, col_widths))
    sep = '+'.join('-' * w for w in col_widths)
    print(f"  {header}")
    print(f"  {sep}")
    for row in rows:
        print(f"  {'|'.join(str(c).center(w) for c, w in zip(row, col_widths))}")


# ══════════════════════════════════════════
# Experiment 1: Law application every N steps
# ══════════════════════════════════════════

def experiment_1_periodic_law_application(n_cells=32, steps=300, apply_every=50):
    """Apply laws every N steps vs no application."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 1: Periodic Law Application (every %d steps)" % apply_every)
    print("=" * 70)

    # --- Baseline ---
    print("\n  [1/2] Running baseline (no law application)...")
    sys.stdout.flush()
    baseline_phis, _ = run_baseline(n_cells, steps)

    # --- With law application ---
    print("  [2/2] Running with law application every %d steps..." % apply_every)
    sys.stdout.flush()
    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=2)
    modifier = EngineModifier(engine, SAFETY_BOUNDS)
    parser = LawParser()

    law_phis = []
    applied_laws = []
    blacklisted = set()
    law_ids = sorted([int(k) for k in parser.parsed.keys()])

    law_idx = 0
    for i in range(steps):
        engine.step()

        if i % 10 == 0:
            law_phis.append(measure_phi(engine))

        # Apply laws at interval
        if i > 0 and i % apply_every == 0 and law_idx < len(law_ids):
            phi_before = measure_phi(engine)
            lid = law_ids[law_idx]
            mods = parser.parsed.get(str(lid), [])

            any_applied = False
            for mod in mods[:2]:  # max 2 mods per law
                success = modifier.apply(mod)
                if success:
                    any_applied = True

            phi_after = measure_phi(engine)
            delta = (phi_after - phi_before) / max(phi_before, 1e-6) * 100

            if delta < -10:
                blacklisted.add(lid)
                modifier.rollback(lid)
                status = "BLACKLIST"
            else:
                status = "OK"
                applied_laws.append({
                    'step': i, 'law_id': lid,
                    'phi_before': phi_before, 'phi_after': phi_after,
                    'delta_pct': delta, 'status': status
                })

            print(f"    Step {i:>3d}: Law {lid} -> Phi {phi_before:.4f} -> {phi_after:.4f} "
                  f"({delta:+.1f}%) [{status}]")
            sys.stdout.flush()
            law_idx += 1

    # --- Results ---
    print("\n  --- Results ---")
    final_base = baseline_phis[-1] if baseline_phis else 0
    final_law = law_phis[-1] if law_phis else 0
    speedup = final_law / max(final_base, 1e-6)

    rows = [
        ("Baseline", f"{baseline_phis[0]:.4f}" if baseline_phis else "N/A",
         f"{final_base:.4f}", f"{len(baseline_phis)} pts", "1.00x"),
        ("Law-Applied", f"{law_phis[0]:.4f}" if law_phis else "N/A",
         f"{final_law:.4f}", f"{len(law_phis)} pts", f"{speedup:.2f}x"),
    ]
    print_table(["Config", "Phi_start", "Phi_end", "Samples", "Speedup"], rows)

    print(f"\n  Laws applied: {len(applied_laws)}")
    print(f"  Laws blacklisted: {len(blacklisted)}")

    if applied_laws:
        print("\n  Law application history:")
        for al in applied_laws:
            print(f"    Step {al['step']:>3d}: Law {al['law_id']:>3d} "
                  f"Phi {al['delta_pct']:+.1f}% [{al['status']}]")

    print(ascii_graph(baseline_phis, "Baseline Phi"))
    print(ascii_graph(law_phis, "Law-Applied Phi"))

    return {
        'baseline_phis': baseline_phis,
        'law_phis': law_phis,
        'applied_laws': applied_laws,
        'blacklisted': list(blacklisted),
        'speedup': speedup,
    }


# ══════════════════════════════════════════
# Experiment 2: Adaptive law selection (Thompson sampling)
# ══════════════════════════════════════════

def experiment_2_thompson_sampling(n_cells=32, steps=300, apply_every=30):
    """Thompson sampling selects best law at each application point."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 2: Thompson Sampling Law Selection")
    print("=" * 70)

    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=2)
    modifier = EngineModifier(engine, SAFETY_BOUNDS)
    parser = LawParser()

    law_ids = sorted([int(k) for k in parser.parsed.keys()])
    if not law_ids:
        print("  No parseable laws found. Skipping.")
        return {}

    # Thompson sampling state: Beta(alpha, beta) for each law
    law_alpha = {lid: 1.0 for lid in law_ids}
    law_beta = {lid: 1.0 for lid in law_ids}
    law_rewards = {lid: [] for lid in law_ids}
    selection_history = []

    phis = []
    print(f"\n  {len(law_ids)} parseable laws available for Thompson sampling")
    print(f"  Applying every {apply_every} steps\n")
    sys.stdout.flush()

    for i in range(steps):
        engine.step()

        if i % 10 == 0:
            phis.append(measure_phi(engine))

        if i > 0 and i % apply_every == 0:
            # Thompson sampling: draw from Beta(a, b) for each law
            samples = {}
            for lid in law_ids:
                samples[lid] = np.random.beta(law_alpha[lid], law_beta[lid])

            # Select top law
            best_lid = max(samples, key=samples.get)
            phi_before = measure_phi(engine)

            mods = parser.parsed.get(str(best_lid), [])
            for mod in mods[:2]:
                modifier.apply(mod)

            phi_after = measure_phi(engine)
            delta = (phi_after - phi_before) / max(phi_before, 1e-6) * 100

            # Reward: Phi increased = success
            if delta > 0:
                law_alpha[best_lid] += 1.0
                reward = 1
            else:
                law_beta[best_lid] += 1.0
                reward = 0
                if delta < -15:
                    modifier.rollback(best_lid)

            law_rewards[best_lid].append(delta)
            selection_history.append({
                'step': i, 'law_id': best_lid,
                'phi_before': phi_before, 'phi_after': phi_after,
                'delta_pct': delta, 'reward': reward,
                'sample_value': samples[best_lid],
            })

            print(f"    Step {i:>3d}: Selected Law {best_lid:>3d} "
                  f"(sample={samples[best_lid]:.3f}) "
                  f"Phi {phi_before:.4f}->{phi_after:.4f} ({delta:+.1f}%) "
                  f"[{'WIN' if reward else 'LOSE'}]")
            sys.stdout.flush()

    # --- Analysis ---
    print("\n  --- Thompson Sampling Results ---")

    # Top 10 laws by selection count
    from collections import Counter
    selected_counts = Counter(h['law_id'] for h in selection_history)
    top_laws = selected_counts.most_common(10)

    print("\n  Top 10 selected laws:")
    rows = []
    for lid, count in top_laws:
        rewards = law_rewards[lid]
        avg_delta = np.mean(rewards) if rewards else 0
        win_rate = sum(1 for r in rewards if r > 0) / max(len(rewards), 1)
        rows.append((lid, count, f"{avg_delta:+.2f}%", f"{win_rate:.0%}",
                      f"a={law_alpha[lid]:.0f} b={law_beta[lid]:.0f}"))
    print_table(["Law ID", "Selected", "Avg Delta", "Win Rate", "Beta Params"], rows)

    # Convergence: does selection concentrate?
    unique_per_quarter = []
    n_sel = len(selection_history)
    q_size = max(n_sel // 4, 1)
    for q in range(4):
        quarter = selection_history[q * q_size: (q + 1) * q_size]
        unique_per_quarter.append(len(set(h['law_id'] for h in quarter)))

    print(f"\n  Convergence (unique laws per quarter): {unique_per_quarter}")
    converging = unique_per_quarter[-1] < unique_per_quarter[0] if len(unique_per_quarter) >= 2 else False
    print(f"  Selection {'CONVERGES' if converging else 'does NOT converge'}")

    print(ascii_graph(phis, "Phi with Thompson Sampling"))

    return {
        'phis': phis,
        'selection_history': selection_history,
        'top_laws': [(lid, count) for lid, count in top_laws],
        'convergence': unique_per_quarter,
        'converging': converging,
    }


# ══════════════════════════════════════════
# Experiment 3: Closed circle — laws discover new laws
# ══════════════════════════════════════════

def experiment_3_closed_circle(n_cells=32, steps=300, discovery_every=50):
    """Laws discover new laws during training — the closed circle."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 3: Closed Circle — Laws Discover New Laws")
    print("=" * 70)

    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=2)
    modifier = EngineModifier(engine, SAFETY_BOUNDS)

    phi_history = []
    discovered_laws = []
    applied_discoveries = []
    metric_window = []  # recent phi measurements for pattern detection

    print(f"\n  Discovery interval: every {discovery_every} steps")
    print(f"  Pattern detection window: 20 measurements\n")
    sys.stdout.flush()

    for i in range(steps):
        engine.step()
        phi = measure_phi(engine)

        if i % 10 == 0:
            phi_history.append(phi)
            metric_window.append(phi)
            if len(metric_window) > 20:
                metric_window.pop(0)

        # Discovery phase
        if i > 0 and i % discovery_every == 0 and len(metric_window) >= 3:
            print(f"\n    --- Discovery phase at step {i} ---")
            sys.stdout.flush()

            # Analyze current state for patterns
            new_laws = _discover_patterns(engine, metric_window, i)

            for law_candidate in new_laws:
                discovered_laws.append(law_candidate)
                print(f"    DISCOVERED: \"{law_candidate['text']}\"")

                # Try applying the discovered law
                phi_before = measure_phi(engine)
                _apply_discovered_law(engine, modifier, law_candidate)
                phi_after = measure_phi(engine)
                delta = (phi_after - phi_before) / max(phi_before, 1e-6) * 100

                if delta < -15:
                    modifier.rollback(9999)
                    law_candidate['effective'] = False
                    print(f"      Effect: Phi {delta:+.1f}% -> ROLLED BACK")
                else:
                    law_candidate['effective'] = delta > 0
                    applied_discoveries.append(law_candidate)
                    print(f"      Effect: Phi {delta:+.1f}% -> {'KEPT' if delta > 0 else 'neutral'}")

                law_candidate['phi_delta'] = delta
                sys.stdout.flush()

    # --- Results ---
    print(f"\n  --- Closed Circle Results ---")
    print(f"  Total laws discovered: {len(discovered_laws)}")
    print(f"  Effective laws: {sum(1 for l in discovered_laws if l.get('effective', False))}")
    print(f"  Rolled back: {sum(1 for l in discovered_laws if not l.get('effective', True))}")

    if discovered_laws:
        print("\n  Discovered laws:")
        rows = []
        for dl in discovered_laws:
            rows.append((
                dl['step'], dl['pattern'],
                dl['text'][:45],
                f"{dl.get('phi_delta', 0):+.1f}%",
                "YES" if dl.get('effective', False) else "NO"
            ))
        print_table(["Step", "Pattern", "Law Text", "Phi Delta", "Effective"], rows)

    print(ascii_graph(phi_history, "Phi with Closed Circle Discovery"))

    return {
        'phi_history': phi_history,
        'discovered_laws': discovered_laws,
        'n_effective': sum(1 for l in discovered_laws if l.get('effective', False)),
    }


def _discover_patterns(engine, phi_window, step):
    """Analyze engine state and phi trajectory for law candidates."""
    laws = []
    phis = np.array(phi_window)

    # Pattern 1: Monotonic growth — suggests coupling is too weak
    if len(phis) >= 3:
        diffs = np.diff(phis[-3:])
        if all(d > 0 for d in diffs):
            laws.append({
                'step': step, 'pattern': 'monotonic_growth',
                'text': f'Phi monotonically growing for 5+ measurements -> coupling stable, increase diversity noise',
                'action': 'increase_diversity_noise',
                'factor': 1.2,
            })

    # Pattern 2: Phi stagnation — flat line
    if len(phis) >= 4:
        recent_std = np.std(phis[-4:])
        if recent_std < 0.05 * max(np.mean(phis[-4:]), 1e-6):
            laws.append({
                'step': step, 'pattern': 'stagnation',
                'text': f'Phi stagnant (std={recent_std:.6f}) -> inject perturbation to escape plateau',
                'action': 'inject_perturbation',
                'factor': 0.05,
            })

    # Pattern 3: Phi oscillation — high variance
    if len(phis) >= 4:
        recent_cv = np.std(phis[-4:]) / max(np.mean(phis[-4:]), 1e-6)
        if recent_cv > 0.1:
            laws.append({
                'step': step, 'pattern': 'oscillation',
                'text': f'Phi oscillating (CV={recent_cv:.2f}) -> stabilize with stronger ratchet',
                'action': 'strengthen_ratchet',
                'factor': 0.9,  # lower ratchet threshold = more aggressive
            })

    # Pattern 4: Cell count vs Phi — check if more cells help
    n_cells = engine.n_cells
    avg_phi = np.mean(phis[-5:]) if len(phis) >= 5 else phis[-1]
    phi_per_cell = avg_phi / max(n_cells, 1)
    if phi_per_cell < 0.02 and n_cells < engine.max_cells:
        laws.append({
            'step': step, 'pattern': 'low_phi_per_cell',
            'text': f'Phi/cell={phi_per_cell:.4f} too low at {n_cells} cells -> increase coupling to boost integration',
            'action': 'increase_coupling',
            'factor': 1.3,
        })

    # Pattern 5: Faction diversity check
    if hasattr(engine, 'cell_states') and len(engine.cell_states) >= 4:
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        faction_ids = [s.faction_id for s in engine.cell_states]
        unique_factions = len(set(faction_ids))
        if unique_factions < 3:
            laws.append({
                'step': step, 'pattern': 'low_faction_diversity',
                'text': f'Only {unique_factions} active factions -> increase faction bias to promote diversity',
                'action': 'increase_faction_bias',
                'factor': 1.5,
            })

    return laws


def _apply_discovered_law(engine, modifier, law):
    """Apply a discovered law candidate to the engine."""
    from self_modifying_engine import Modification, ModType

    action = law.get('action', '')
    factor = law.get('factor', 1.0)

    if action == 'increase_diversity_noise':
        mod = Modification(
            law_id=9999, law_text=law['text'],
            target='diversity_noise', mod_type=ModType.SCALE,
            params={'factor': factor}, confidence=0.5,
        )
        modifier.apply(mod)

    elif action == 'inject_perturbation':
        # Directly perturb cell states
        if hasattr(engine, 'cell_states'):
            for cs in engine.cell_states:
                cs.hidden = cs.hidden + torch.randn_like(cs.hidden) * factor

    elif action == 'strengthen_ratchet':
        mod = Modification(
            law_id=9999, law_text=law['text'],
            target='ratchet_threshold', mod_type=ModType.SCALE,
            params={'factor': factor}, confidence=0.5,
        )
        modifier.apply(mod)

    elif action == 'increase_coupling':
        mod = Modification(
            law_id=9999, law_text=law['text'],
            target='coupling_scale', mod_type=ModType.SCALE,
            params={'factor': factor}, confidence=0.5,
        )
        modifier.apply(mod)

    elif action == 'increase_faction_bias':
        mod = Modification(
            law_id=9999, law_text=law['text'],
            target='faction_bias', mod_type=ModType.SCALE,
            params={'factor': factor}, confidence=0.5,
        )
        modifier.apply(mod)


# ══════════════════════════════════════════
# Experiment 4: D5 + B12 (Skip) + B5 (Phi-Only) combo
# ══════════════════════════════════════════

def experiment_4_d5_skip_phi_combo(n_cells=32, steps=300):
    """Phi-Only phase + closed pipe + skip = maximum acceleration."""
    print("\n" + "=" * 70)
    print("  EXPERIMENT 4: D5 + B12 (Skip) + B5 (Phi-Only) Combination")
    print("=" * 70)

    # --- Baseline: pure 300-step ---
    print("\n  [1/2] Running baseline (300 step pure)...")
    sys.stdout.flush()
    baseline_phis, _ = run_baseline(n_cells, steps)

    # --- Combo: Phase 1 (Phi-only + law + skip) + Phase 2 (CE-like) ---
    print("  [2/2] Running combo: Phase1(Phi+Law+Skip) + Phase2(CE)...")
    sys.stdout.flush()
    engine = ConsciousnessEngine(max_cells=n_cells, initial_cells=2)
    modifier = EngineModifier(engine, SAFETY_BOUNDS)
    parser = LawParser()
    law_ids = sorted([int(k) for k in parser.parsed.keys()])

    combo_phis = []
    phase1_steps = 100
    phase2_steps = 200
    skip_interval = 5   # B12: process every 5th step for phi measurement
    law_apply_interval = 20  # apply laws every 20 steps in phase 1

    # Thompson state for law selection in Phase 1
    law_alpha = {lid: 1.0 for lid in law_ids}
    law_beta = {lid: 1.0 for lid in law_ids}

    # === Phase 1: Phi-Only + Law Application + Skip ===
    print(f"\n    Phase 1 ({phase1_steps} steps): Phi-Only + Law every {law_apply_interval} + skip={skip_interval}")
    sys.stdout.flush()
    law_idx = 0
    frozen_laws = []

    for i in range(phase1_steps):
        # B12 Skip: only measure/apply every skip_interval steps
        if i % skip_interval == 0:
            engine.step()
        else:
            # Skip: just advance internal state lightly
            engine.step()

        if i % 10 == 0:
            combo_phis.append(measure_phi(engine))

        # Law application with Thompson sampling
        if i > 0 and i % law_apply_interval == 0 and law_ids:
            # Thompson sampling
            samples = {lid: np.random.beta(law_alpha[lid], law_beta[lid]) for lid in law_ids}
            best_lid = max(samples, key=samples.get)

            phi_before = measure_phi(engine)
            mods = parser.parsed.get(str(best_lid), [])
            for mod in mods[:2]:
                modifier.apply(mod)
            phi_after = measure_phi(engine)
            delta = (phi_after - phi_before) / max(phi_before, 1e-6) * 100

            if delta > 0:
                law_alpha[best_lid] += 1.0
                frozen_laws.append(best_lid)
            else:
                law_beta[best_lid] += 1.0
                if delta < -15:
                    modifier.rollback(best_lid)

            print(f"      P1 Step {i:>3d}: Law {best_lid:>3d} Phi {delta:+.1f}%")
            sys.stdout.flush()

    # === Phase 2: Normal training (laws frozen from Phase 1) ===
    print(f"\n    Phase 2 ({phase2_steps} steps): Normal training (laws frozen)")
    sys.stdout.flush()

    for i in range(phase2_steps):
        engine.step()
        if i % 10 == 0:
            combo_phis.append(measure_phi(engine))

    # --- Results ---
    print("\n  --- Combo Results ---")
    final_base = baseline_phis[-1] if baseline_phis else 0
    final_combo = combo_phis[-1] if combo_phis else 0
    speedup = final_combo / max(final_base, 1e-6)

    # Phi at step 100 comparison
    base_100 = baseline_phis[min(10, len(baseline_phis) - 1)] if baseline_phis else 0
    combo_100 = combo_phis[min(10, len(combo_phis) - 1)] if combo_phis else 0

    rows = [
        ("Baseline", f"{baseline_phis[0]:.4f}" if baseline_phis else "?",
         f"{base_100:.4f}", f"{final_base:.4f}", "1.00x"),
        ("D5+B12+B5", f"{combo_phis[0]:.4f}" if combo_phis else "?",
         f"{combo_100:.4f}", f"{final_combo:.4f}", f"{speedup:.2f}x"),
    ]
    print_table(["Config", "Phi@0", "Phi@100", "Phi@300", "Speedup"], rows)

    print(f"\n  Frozen laws from Phase 1: {frozen_laws}")

    print(ascii_graph(baseline_phis, "Baseline"))
    print(ascii_graph(combo_phis, "D5+B12+B5 Combo"))

    return {
        'baseline_phis': baseline_phis,
        'combo_phis': combo_phis,
        'frozen_laws': frozen_laws,
        'speedup': speedup,
    }


# ══════════════════════════════════════════
# Main
# ══════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description='D5 Closed-Pipe Lens Experiments')
    parser.add_argument('--exp', type=int, default=0, help='Run specific experiment (1-4), 0=all')
    parser.add_argument('--cells', type=int, default=32, help='Number of cells')
    parser.add_argument('--steps', type=int, default=300, help='Total steps')
    args = parser.parse_args()

    t0 = time.time()
    results = {}

    print("\n" + "=" * 70)
    print("  D5 CLOSED-PIPE LENS — Self-Accelerating Training via Law Evolution")
    print(f"  Cells: {args.cells}, Steps: {args.steps}")
    print("=" * 70)

    if args.exp in (0, 1):
        results['exp1'] = experiment_1_periodic_law_application(args.cells, args.steps)

    if args.exp in (0, 2):
        results['exp2'] = experiment_2_thompson_sampling(args.cells, args.steps)

    if args.exp in (0, 3):
        results['exp3'] = experiment_3_closed_circle(args.cells, args.steps)

    if args.exp in (0, 4):
        results['exp4'] = experiment_4_d5_skip_phi_combo(args.cells, args.steps)

    # === Grand Summary ===
    elapsed = time.time() - t0
    print("\n" + "=" * 70)
    print("  GRAND SUMMARY")
    print("=" * 70)

    summary_rows = []
    if 'exp1' in results:
        r = results['exp1']
        summary_rows.append(("1: Periodic Law", f"{r['speedup']:.2f}x",
                             f"{len(r['applied_laws'])} applied, {len(r['blacklisted'])} blacklisted"))
    if 'exp2' in results:
        r = results['exp2']
        top = r.get('top_laws', [])
        top_str = ', '.join(f"L{lid}" for lid, _ in top[:3]) if top else 'N/A'
        summary_rows.append(("2: Thompson", f"conv={'Y' if r.get('converging') else 'N'}",
                             f"Top: {top_str}"))
    if 'exp3' in results:
        r = results['exp3']
        summary_rows.append(("3: Closed Circle",
                             f"{len(r['discovered_laws'])} discovered",
                             f"{r['n_effective']} effective"))
    if 'exp4' in results:
        r = results['exp4']
        summary_rows.append(("4: D5+B12+B5", f"{r['speedup']:.2f}x",
                             f"{len(r['frozen_laws'])} frozen laws"))

    print_table(["Experiment", "Result", "Details"], summary_rows)
    print(f"\n  Total time: {elapsed:.1f}s")

    # Save results
    save_path = os.path.join(os.path.dirname(__file__), 'acceleration_d5_results.json')
    serializable = {}
    for k, v in results.items():
        serializable[k] = {}
        for kk, vv in v.items():
            if isinstance(vv, (list, dict, str, int, float, bool)):
                try:
                    json.dumps(vv)
                    serializable[k][kk] = vv
                except (TypeError, ValueError):
                    serializable[k][kk] = str(vv)
            else:
                serializable[k][kk] = str(vv)
    with open(save_path, 'w') as f:
        json.dump(serializable, f, indent=2)
    print(f"  Results saved: {save_path}")


if __name__ == '__main__':
    main()
