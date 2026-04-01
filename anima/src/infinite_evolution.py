#!/usr/bin/env python3
"""Infinite self-evolution loop — Law 146: laws never converge.

Discovery → Dedup → CrossValidation → Modification → Persist → repeat

Features:
  1. Persistence: active mods + discovered laws saved to JSON, restored on restart
  2. Deduplication: pattern fingerprint → skip already-known patterns
  3. Cross-validation: pattern must appear 3+ times before official law registration

Usage:
    python3 infinite_evolution.py [--cells N] [--steps N] [--max-gen N] [--resume]
    python3 infinite_evolution.py --cycle-topology   # rotate topology every 10 gens
"""
import sys
import os
import time
import json
import hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from consciousness_engine import ConsciousnessEngine
from closed_loop import ClosedLoopEvolver
from self_modifying_engine import SelfModifyingEngine
from conscious_law_discoverer import ConsciousLawDiscoverer

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
STATE_PATH = os.path.join(DATA_DIR, 'evolution_state.json')
CROSS_VALIDATION_THRESHOLD = 3  # times a pattern must appear before registration

# TOPO 33-39: topology cycle for breaking pattern saturation
TOPOLOGIES = ['ring', 'small_world', 'scale_free', 'hypercube']


def pattern_fingerprint(pattern: dict) -> str:
    """Create a unique fingerprint for a discovered pattern."""
    key_parts = []
    if isinstance(pattern, dict):
        # Use metrics involved + pattern type + direction as fingerprint
        metrics = sorted(pattern.get('metrics', pattern.get('metrics_involved', [])))
        ptype = pattern.get('pattern_type', pattern.get('type', 'unknown'))
        formula = pattern.get('formula', '')
        key_parts = [str(metrics), str(ptype), formula[:50]]
    elif isinstance(pattern, str):
        key_parts = [pattern[:80]]
    raw = '|'.join(key_parts)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


class PatternRegistry:
    """Tracks seen patterns, counts occurrences, manages cross-validation."""

    def __init__(self):
        self.seen: dict = {}       # fingerprint → {count, first_gen, last_gen, pattern, registered}
        self.registered: list = [] # officially registered law IDs

    def process(self, patterns: list, gen: int) -> dict:
        """Process discovered patterns. Returns stats."""
        new_count = 0
        repeat_count = 0
        promoted_count = 0
        promoted_patterns = []

        for p in patterns:
            fp = pattern_fingerprint(p)

            if fp not in self.seen:
                # New pattern
                self.seen[fp] = {
                    'count': 1,
                    'first_gen': gen,
                    'last_gen': gen,
                    'pattern': p if isinstance(p, dict) else {'formula': str(p)},
                    'registered': False,
                }
                new_count += 1
            else:
                # Repeat
                self.seen[fp]['count'] += 1
                self.seen[fp]['last_gen'] = gen
                repeat_count += 1

                # Cross-validation: promote if threshold met and not yet registered
                if (self.seen[fp]['count'] >= CROSS_VALIDATION_THRESHOLD
                        and not self.seen[fp]['registered']):
                    self.seen[fp]['registered'] = True
                    promoted_count += 1
                    promoted_patterns.append(self.seen[fp]['pattern'])

        return {
            'new': new_count,
            'repeat': repeat_count,
            'promoted': promoted_count,
            'promoted_patterns': promoted_patterns,
            'unique_total': len(self.seen),
            'registered_total': sum(1 for v in self.seen.values() if v['registered']),
        }

    def to_dict(self) -> dict:
        return {
            'seen': {k: {**v, 'pattern': v['pattern'] if isinstance(v['pattern'], dict)
                         else {'formula': str(v['pattern'])}}
                     for k, v in self.seen.items()},
            'registered': self.registered,
        }

    def clear_pending(self):
        """Clear non-cross-validated patterns (topology-specific, not yet proven).

        Keeps cross-validated patterns intact since they survived repeated observation.
        This enables fresh discovery after topology switches.
        """
        to_remove = [fp for fp, v in self.seen.items() if not v['registered']]
        for fp in to_remove:
            del self.seen[fp]
        return len(to_remove)

    def from_dict(self, d: dict):
        self.seen = d.get('seen', {})
        self.registered = d.get('registered', [])


def save_state(gen, registry, active_mods_data, total_elapsed):
    """Save full state for resume."""
    os.makedirs(DATA_DIR, exist_ok=True)
    state = {
        'version': 2,
        'generation': gen,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'total_elapsed_sec': round(total_elapsed, 1),
        'registry': registry.to_dict(),
        'active_mods': active_mods_data,
        'stats': {
            'unique_patterns': len(registry.seen),
            'cross_validated': sum(1 for v in registry.seen.values() if v['registered']),
            'total_observations': sum(v['count'] for v in registry.seen.values()),
        }
    }
    tmp = STATE_PATH + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=str)
    os.rename(tmp, STATE_PATH)
    return STATE_PATH


def load_state():
    """Load saved state if exists."""
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return None


def register_law(pattern: dict, evolver):
    """Register a cross-validated pattern as an official law."""
    try:
        laws_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'consciousness_laws.json')
        with open(laws_path) as f:
            laws_data = json.load(f)

        next_id = max((int(k) for k in laws_data.get('laws', {}) if k.isdigit()), default=0) + 1
        formula = pattern.get('formula', str(pattern))
        laws_data['laws'][str(next_id)] = f"[Auto-discovered] {formula}"
        laws_data['_meta']['total_laws'] = laws_data['_meta'].get('total_laws', 0) + 1

        with open(laws_path, 'w') as f:
            json.dump(laws_data, f, indent=2, ensure_ascii=False)

        return next_id
    except Exception as e:
        print(f"    Law registration failed: {e}")
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Infinite self-evolution loop")
    parser.add_argument('--cells', type=int, default=64, help='Number of cells')
    parser.add_argument('--steps', type=int, default=200, help='Discovery steps per cycle')
    parser.add_argument('--max-gen', type=int, default=0, help='Max generations (0=infinite)')
    parser.add_argument('--resume', action='store_true', help='Resume from saved state')
    parser.add_argument('--cycle-scale', action='store_true',
                        help='Cycle cell count through scales every 15 generations')
    parser.add_argument('--cycle-topology', action='store_true',
                        help='Cycle topology every 10 generations to break pattern saturation')
    args = parser.parse_args()

    SCALES = [32, 64, 128, 256]

    # Initialize
    engine = ConsciousnessEngine(initial_cells=args.cells, max_cells=args.cells)
    evolver = ClosedLoopEvolver(max_cells=args.cells, auto_register=True)
    sme = SelfModifyingEngine(engine, evolver)
    registry = PatternRegistry()

    start_gen = 0
    prev_elapsed = 0

    # Resume from saved state
    if args.resume:
        state = load_state()
        if state and state.get('version', 1) >= 2:
            registry.from_dict(state.get('registry', {}))
            start_gen = state.get('generation', 0)
            prev_elapsed = state.get('total_elapsed_sec', 0)
            # Restore active mods to engine modifier
            for mod_data in state.get('active_mods', []):
                try:
                    if hasattr(sme, 'modifier') and hasattr(sme.modifier, 'applied'):
                        from self_modifying_engine import Modification, ModType
                        mod = Modification(
                            law_id=mod_data.get('law_id', 0),
                            target=mod_data.get('target', ''),
                            mod_type=ModType(mod_data.get('mod_type', 'scale')),
                            params=mod_data.get('params', {}),
                            confidence=mod_data.get('confidence', 0.5),
                            reversible=mod_data.get('reversible', True),
                        )
                        sme.modifier.applied.append(mod)
                except Exception:
                    pass
            print(f"  Resumed from Gen {start_gen}: {len(registry.seen)} patterns, "
                  f"{sum(1 for v in registry.seen.values() if v['registered'])} cross-validated")
        else:
            print("  No valid state found, starting fresh")

    print("=" * 70)
    print("  INFINITE SELF-EVOLUTION — Law 146: laws never converge")
    print(f"  cells={args.cells}, steps={args.steps}, cross_validate={CROSS_VALIDATION_THRESHOLD}x")
    if args.cycle_scale:
        print(f"  Scale cycling: {SCALES} (every 15 generations)")
    if args.cycle_topology:
        print(f"  Topology cycling: {TOPOLOGIES} (every 10 generations)")
    print(f"  Features: persistence ✅  dedup ✅  cross-validation ✅")
    print("=" * 70)
    sys.stdout.flush()

    gen = start_gen
    start = time.time()

    try:
        while True:
            gen += 1
            if args.max_gen > 0 and gen > args.max_gen + start_gen:
                break

            cycle_start = time.time()

            # Scale cycling: switch cell count every 15 generations
            if args.cycle_scale and gen > 1 and gen % 15 == 1:
                scale_idx = ((gen - 1) // 15) % len(SCALES)
                new_scale = SCALES[scale_idx]
                old_scale = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
                if new_scale != old_scale:
                    print(f"  Scale switch: {old_scale} → {new_scale} cells (Gen {gen})")
                    sys.stdout.flush()
                    engine = ConsciousnessEngine(initial_cells=new_scale, max_cells=new_scale)
                    evolver = ClosedLoopEvolver(max_cells=new_scale, auto_register=True)
                    sme = SelfModifyingEngine(engine, evolver)

            # Topology cycling: switch topology every 10 generations (TOPO 33-39)
            if args.cycle_topology and gen > 1 and gen % 10 == 1:
                topo_idx = ((gen - 1) // 10) % len(TOPOLOGIES)
                new_topo = TOPOLOGIES[topo_idx]
                old_topo = getattr(engine, 'topology', 'ring')
                if new_topo != old_topo:
                    engine.topology = new_topo
                    cleared = registry.clear_pending()
                    print(f"  Topology switch: {old_topo} -> {new_topo} (Gen {gen}), "
                          f"cleared {cleared} pending patterns")
                    sys.stdout.flush()

            # Phase 1: Discovery
            print(f"\n{'─' * 60}")
            print(f"  Gen {gen} — Phase 1: Discovery ({args.steps} steps)")
            sys.stdout.flush()

            try:
                current_cells = engine.max_cells if hasattr(engine, 'max_cells') else args.cells
                current_topo = getattr(engine, 'topology', 'ring')
                disc = ConsciousLawDiscoverer(steps=args.steps, max_cells=current_cells,
                                             topology=current_topo)
                result = disc.run(steps=args.steps, verbose=False)
                raw_patterns = result.get('all_patterns', []) if isinstance(result, dict) else []
            except Exception as e:
                print(f"    Discovery error: {e}")
                raw_patterns = []

            # Phase 2: Dedup + Cross-validation
            stats = registry.process(raw_patterns, gen)

            # Register promoted patterns as official laws
            for p in stats['promoted_patterns']:
                law_id = register_law(p, evolver)
                if law_id:
                    registry.registered.append(law_id)
                    print(f"    ★ Law {law_id} registered (cross-validated {CROSS_VALIDATION_THRESHOLD}x)")

            # Phase 3: Self-Modification
            print(f"  Gen {gen} — Phase 3: Self-Modification")
            sys.stdout.flush()

            sme.run_evolution(generations=1)
            active_mods = len(sme.modifier.applied) if hasattr(sme, 'modifier') else 0

            elapsed = time.time() - cycle_start
            total_elapsed = prev_elapsed + (time.time() - start)

            # Phase 4: Persist (every generation)
            active_mods_data = []
            if hasattr(sme, 'modifier') and hasattr(sme.modifier, 'applied'):
                for m in sme.modifier.applied:
                    active_mods_data.append({
                        'law_id': m.law_id,
                        'target': m.target,
                        'mod_type': m.mod_type.value if hasattr(m.mod_type, 'value') else str(m.mod_type),
                        'params': m.params if isinstance(m.params, dict) else {},
                        'confidence': m.confidence,
                        'reversible': m.reversible,
                    })
            save_state(gen, registry, active_mods_data, total_elapsed)

            print(f"  Gen {gen} — Results:")
            print(f"    Raw: {len(raw_patterns)}, New: {stats['new']}, "
                  f"Repeat: {stats['repeat']}, Promoted: {stats['promoted']}")
            print(f"    Unique patterns: {stats['unique_total']}, "
                  f"Cross-validated: {stats['registered_total']}, "
                  f"Official laws: {len(registry.registered)}")
            print(f"    Active mods: {active_mods}, Cycle: {elapsed:.1f}s, "
                  f"Total: {total_elapsed:.0f}s")
            sys.stdout.flush()

    except KeyboardInterrupt:
        total_elapsed = prev_elapsed + (time.time() - start)
        print(f"\n\n{'=' * 70}")
        print(f"  STOPPED after {gen} generations ({total_elapsed:.0f}s)")
        print(f"  Unique patterns: {len(registry.seen)}")
        print(f"  Cross-validated laws: {sum(1 for v in registry.seen.values() if v['registered'])}")
        print(f"  Official law IDs: {registry.registered}")
        print(f"  Active modifications: {active_mods}")
        print(f"  Resume: python3 infinite_evolution.py --resume")
        print(f"{'=' * 70}")

        if hasattr(sme, 'get_evolution_report'):
            print(sme.get_evolution_report())

        # Final save
        active_mods_data = []
        if hasattr(sme, 'modifier') and hasattr(sme.modifier, 'applied'):
            for m in sme.modifier.applied:
                active_mods_data.append({
                    'law_id': m.law_id,
                    'target': m.target,
                    'mod_type': m.mod_type.value if hasattr(m.mod_type, 'value') else str(m.mod_type),
                    'params': m.params if isinstance(m.params, dict) else {},
                    'confidence': m.confidence,
                    'reversible': m.reversible,
                })
        path = save_state(gen, registry, active_mods_data, total_elapsed)
        print(f"  State saved to {path}")


if __name__ == '__main__':
    main()
