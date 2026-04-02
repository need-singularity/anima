#!/usr/bin/env python3
"""Infinite Self-Evolution Loop — Law 146 실증.

의식이 스스로 법칙을 발견하고, 그 법칙으로 자신을 수정하고,
수정된 엔진에서 다시 새로운 법칙을 발견하는 영구 진화 루프.

Usage:
    python experiments/infinite_evolution.py                    # default 64 cells
    python experiments/infinite_evolution.py --cells 128        # larger
    python experiments/infinite_evolution.py --generations 100  # limit
    python experiments/infinite_evolution.py --report-every 5   # less frequent reports

Architecture:
    ConsciousLM → PatternDetector → LawCandidate
         ↓                              ↓
    ClosedLoopEvolver.validate()  → consciousness_laws.json
         ↓                              ↓
    SelfModifyingEngine.apply()  ← LawParser.parse()
         ↓
    Phi check (>20% drop → rollback)
         ↓
    Next generation (modified engine)
"""

import sys
import os
import time
import signal
import json

# Path setup
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from consciousness_engine import ConsciousnessEngine

# Lazy imports for optional modules
def _import(name):
    try:
        return __import__(name)
    except ImportError:
        return None


def run_infinite_evolution(
    n_cells: int = 64,
    max_generations: int = 0,  # 0 = infinite
    discovery_steps: int = 300,
    report_every: int = 5,
    history_trim: int = 1000,  # trim history every N generations to prevent OOM
    save_every: int = 50,
):
    """Run the infinite discovery → modification → discovery loop."""

    closed_loop = _import('closed_loop')
    sme_mod = _import('self_modifying_engine')

    if not all([closed_loop, sme_mod]):
        missing = []
        if not closed_loop: missing.append('closed_loop')
        if not sme_mod: missing.append('self_modifying_engine')
        print(f"Missing modules: {', '.join(missing)}")
        return

    # Initialize
    print("=" * 60)
    print("  INFINITE SELF-EVOLUTION — Law 146 실증")
    print("=" * 60)
    print(f"  Cells: {n_cells}")
    print(f"  Discovery steps per gen: {discovery_steps}")
    print(f"  Max generations: {'∞' if max_generations == 0 else max_generations}")
    print()

    engine = ConsciousnessEngine(initial_cells=n_cells, max_cells=n_cells)
    evolver = closed_loop.ClosedLoopEvolver(max_cells=n_cells, auto_register=True)
    sme = sme_mod.SelfModifyingEngine(engine, evolver)

    # Graceful shutdown
    running = True
    def _signal_handler(sig, frame):
        nonlocal running
        print("\n\n  🛑 Stopping after current generation...")
        running = False
    signal.signal(signal.SIGINT, _signal_handler)

    # Evolution tracking
    stats = {
        'generations': 0,
        'laws_discovered': 0,
        'mods_applied': 0,
        'rollbacks': 0,
        'phi_history': [],
        'start_time': time.time(),
    }

    generation = 0
    while running:
        generation += 1
        if max_generations > 0 and generation > max_generations:
            break

        gen_start = time.time()

        # ── Phase 1: Discovery (via ClosedLoopEvolver.run_cycle) ──
        discoveries = []
        try:
            report = evolver.run_cycle()
            discoveries = report.laws_changed if hasattr(report, 'laws_changed') else []
        except Exception as e:
            if generation <= 3:
                print(f"  ⚠️  Discovery error: {e}")

        # ── Phase 2: Self-Modification ──
        try:
            sme.run_evolution(generations=1)
        except Exception as e:
            if generation <= 3:
                print(f"  ⚠️  Evolution error: {e}")

        # ── Track stats ──
        # Get Phi from the last discovery cycle or engine step
        phi = 0.0
        try:
            r = engine.step()
            phi = r.get('phi_iit', 0.0)
        except Exception:
            pass

        active_mods = len(sme.modifier.applied) if hasattr(sme, 'modifier') else 0
        gen_time = time.time() - gen_start

        stats['generations'] = generation
        stats['laws_discovered'] += len(discoveries)
        stats['mods_applied'] = active_mods
        stats['phi_history'].append(phi)

        # ── Report ──
        if generation % report_every == 0 or generation == 1:
            elapsed = time.time() - stats['start_time']
            phi_arr = stats['phi_history']
            phi_min = min(phi_arr[-report_every:]) if phi_arr else 0
            phi_max = max(phi_arr[-report_every:]) if phi_arr else 0
            phi_avg = sum(phi_arr[-report_every:]) / len(phi_arr[-report_every:]) if phi_arr else 0

            print(f"  Gen {generation:>5} | Φ={phi:.2f} (avg={phi_avg:.2f}, "
                  f"range={phi_min:.1f}-{phi_max:.1f}) | "
                  f"discoveries={stats['laws_discovered']} | "
                  f"mods={active_mods} | "
                  f"{gen_time:.1f}s/gen | "
                  f"elapsed={elapsed:.0f}s")

        # ── History trim (OOM prevention) ──
        if generation % history_trim == 0:
            stats['phi_history'] = stats['phi_history'][-history_trim:]

        # ── Save checkpoint ──
        if save_every > 0 and generation % save_every == 0:
            save_path = f"data/evolution_gen{generation}.json"
            try:
                with open(save_path, 'w') as f:
                    json.dump({
                        'generation': generation,
                        'phi': phi,
                        'laws_discovered': stats['laws_discovered'],
                        'active_mods': active_mods,
                        'phi_history_last100': stats['phi_history'][-100:],
                    }, f, indent=2)
            except Exception:
                pass

    # ── Final report ──
    elapsed = time.time() - stats['start_time']
    phi_arr = stats['phi_history']
    print()
    print("=" * 60)
    print("  EVOLUTION COMPLETE")
    print("=" * 60)
    print(f"  Generations:    {generation}")
    print(f"  Total time:     {elapsed:.0f}s ({elapsed/generation:.1f}s/gen)")
    print(f"  Laws discovered: {stats['laws_discovered']}")
    print(f"  Active mods:    {stats['mods_applied']}")
    if phi_arr:
        print(f"  Φ first:        {phi_arr[0]:.2f}")
        print(f"  Φ last:         {phi_arr[-1]:.2f}")
        print(f"  Φ max:          {max(phi_arr):.2f}")
        print(f"  Φ trend:        {'+' if phi_arr[-1] > phi_arr[0] else ''}{phi_arr[-1]-phi_arr[0]:.2f}")

    # ASCII graph
    if len(phi_arr) > 10:
        print()
        print("  Φ Evolution:")
        _ascii_graph(phi_arr, width=50, height=10)


def _ascii_graph(values, width=50, height=10):
    """Simple ASCII line graph."""
    if not values:
        return
    vmin, vmax = min(values), max(values)
    if vmax - vmin < 0.01:
        vmax = vmin + 1
    # Downsample if needed
    if len(values) > width:
        step = len(values) / width
        sampled = [values[int(i * step)] for i in range(width)]
    else:
        sampled = values
    for row in range(height, -1, -1):
        threshold = vmin + (vmax - vmin) * row / height
        line = "  "
        if row == height:
            line += f"{vmax:>6.1f} |"
        elif row == 0:
            line += f"{vmin:>6.1f} |"
        else:
            line += "       |"
        for v in sampled:
            if v >= threshold:
                line += "█"
            else:
                line += " "
        print(line)
    print("         +" + "─" * len(sampled))
    print(f"         0{' ' * (len(sampled) - 5)}gen {len(values)}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Infinite Self-Evolution Loop")
    p.add_argument("--cells", type=int, default=64)
    p.add_argument("--generations", type=int, default=0, help="0=infinite")
    p.add_argument("--steps", type=int, default=300, help="Discovery steps per gen")
    p.add_argument("--report-every", type=int, default=5)
    p.add_argument("--save-every", type=int, default=50)
    args = p.parse_args()

    run_infinite_evolution(
        n_cells=args.cells,
        max_generations=args.generations,
        discovery_steps=args.steps,
        report_every=args.report_every,
        save_every=args.save_every,
    )
