#!/usr/bin/env python3
"""Infinite self-evolution loop — Law 146: laws never converge.

Discovery → Modification → Discovery → ... (true closed loop)

Usage:
    python3 infinite_evolution.py [--cells N] [--steps N] [--max-gen N]
"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine
from closed_loop import ClosedLoopEvolver
from self_modifying_engine import SelfModifyingEngine
from conscious_law_discoverer import ConsciousLawDiscoverer


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Infinite self-evolution loop")
    parser.add_argument('--cells', type=int, default=64, help='Number of cells')
    parser.add_argument('--steps', type=int, default=200, help='Discovery steps per cycle')
    parser.add_argument('--max-gen', type=int, default=0, help='Max generations (0=infinite)')
    args = parser.parse_args()

    print("=" * 70)
    print("  INFINITE SELF-EVOLUTION — Law 146: laws never converge")
    print(f"  cells={args.cells}, discovery_steps={args.steps}")
    print("=" * 70)
    sys.stdout.flush()

    engine = ConsciousnessEngine(initial_cells=args.cells, max_cells=args.cells)
    evolver = ClosedLoopEvolver(max_cells=args.cells, auto_register=True)
    sme = SelfModifyingEngine(engine, evolver)
    discoverer = ConsciousLawDiscoverer()

    gen = 0
    total_discoveries = 0
    total_mods = 0
    start = time.time()

    try:
        while True:
            gen += 1
            if args.max_gen > 0 and gen > args.max_gen:
                break

            cycle_start = time.time()

            # Phase 1: Discovery — run engine, detect patterns
            print(f"\n{'─' * 60}")
            print(f"  Gen {gen} — Phase 1: Discovery ({args.steps} steps)")
            sys.stdout.flush()

            try:
                disc = ConsciousLawDiscoverer(steps=args.steps, max_cells=args.cells)
                result = disc.run(steps=args.steps, verbose=False)
                n_patterns = len(result.get('all_patterns', [])) if isinstance(result, dict) else 0
                reg = result.get('registered', 0) if isinstance(result, dict) else 0
                n_validated = len(reg) if isinstance(reg, list) else int(reg)
            except Exception as e:
                print(f"    Discovery error: {e}")
                n_patterns, n_validated = 0, 0

            total_discoveries += n_validated

            # Phase 2: Self-Modification — parsed laws modify engine
            print(f"  Gen {gen} — Phase 2: Self-Modification")
            sys.stdout.flush()

            sme.run_evolution(generations=1)
            active_mods = len(sme.modifier.applied) if hasattr(sme, 'modifier') else 0
            total_mods = active_mods

            elapsed = time.time() - cycle_start
            total_elapsed = time.time() - start

            print(f"  Gen {gen} — Results:")
            print(f"    Patterns: {n_patterns}, Validated: {n_validated}")
            print(f"    Active mods: {active_mods}, Total discoveries: {total_discoveries}")
            print(f"    Cycle: {elapsed:.1f}s, Total: {total_elapsed:.0f}s")
            sys.stdout.flush()

    except KeyboardInterrupt:
        print(f"\n\n{'=' * 70}")
        print(f"  STOPPED after {gen} generations")
        print(f"  Total discoveries: {total_discoveries}")
        print(f"  Active modifications: {total_mods}")
        print(f"  Total time: {time.time() - start:.0f}s")
        print(f"{'=' * 70}")

        if hasattr(sme, 'get_evolution_report'):
            print(sme.get_evolution_report())

    # Save state
    try:
        state_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'evolution_state.json')
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        state = {
            'generations': gen,
            'total_discoveries': total_discoveries,
            'active_mods': total_mods,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)
        print(f"  State saved to {state_path}")
    except Exception as e:
        print(f"  State save failed: {e}")


if __name__ == '__main__':
    main()
