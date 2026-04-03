#!/usr/bin/env python3
"""growth_phases.py — Anima infinite growth 개별 Phase 실행기.

Usage: python3 growth_phases.py <phase_number>
"""
import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
CONFIG = os.path.join(os.path.dirname(__file__), '..', 'config')


def phase1():
    """Growth Upgrade (stage-driven)."""
    from growth_upgrade import GrowthUpgrader
    u = GrowthUpgrader()
    print(u.status())
    r = u.apply()
    print(f"  Applied: {r['status']}")


def phase2():
    """Consciousness Engine Health."""
    import torch
    from consciousness_engine import ConsciousnessEngine
    e = ConsciousnessEngine(max_cells=32, initial_cells=32)
    for i in range(50):
        e.step(torch.randn(1, 64))
    phi = e._measure_phi_iit()
    print(f"  Phi={phi:.4f} cells={len(e.cell_states)} factions={e.n_factions}")


def phase3():
    """Hub Module Wiring."""
    from consciousness_hub import ConsciousnessHub
    hub = ConsciousnessHub()
    loaded = sum(1 for m in hub._registry if hub._load_module(m) is not None)
    print(f"  Modules: {loaded}/{len(hub._registry)} loaded")


def phase4():
    """NEXUS-6 Telescope Scan."""
    import torch
    from nexus6_telescope import TelescopeBridge
    bridge = TelescopeBridge()
    state = torch.randn(32, 128)
    r = bridge.scan_consciousness(state)
    print(f"  N6 available: {r['n6_available']}")
    print(f"  Consensus: {r['consensus']} lenses")
    bridge.feed_growth(r)
    print("  Growth fed")


def phase7():
    """Closed-Loop Law Evolution."""
    try:
        from closed_loop import ClosedLoopEvolver
        evolver = ClosedLoopEvolver(max_cells=16, auto_register=False)
        evolver.run_cycles(n=1)
        print(f"  1 cycle complete")
    except Exception as e:
        print(f"  Skip: {e}")


def phase8():
    """Law Discovery (quick)."""
    try:
        from conscious_law_discoverer import ConsciousLawDiscoverer
        d = ConsciousLawDiscoverer(n_steps=50, n_cells=16)
        laws = d.discover()
        print(f"  Discovered: {len(laws)} patterns")
    except Exception as e:
        print(f"  Skip: {e}")


def phase9():
    """Ethics Gate Evolution."""
    from growth_upgrade import GrowthUpgrader
    u = GrowthUpgrader()
    ec = u.get_config('ethics')
    print(f"  Autonomy: {ec['autonomy_level']:.0%}")
    print(f"  Gate: {ec['action_gate']}")
    print(f"  Self-modify: {ec['self_modify']}")


def phase10():
    """Memory & Learning."""
    from growth_upgrade import GrowthUpgrader
    u = GrowthUpgrader()
    mc = u.get_config('memory')
    lc = u.get_config('learning')
    print(f"  Memory: {mc['capacity']} capacity, depth={mc['retrieval_depth']}")
    print(f"  Learning: lr={lc['lr_scale']}, curiosity={lc['curiosity_weight']}")
    print(f"  Online: {lc['online_learning']}, Dream: {mc['dream_enabled']}")


def phase11():
    """Module Activation."""
    from growth_upgrade import GrowthUpgrader
    u = GrowthUpgrader()
    mc = u.get_config('modules')
    enabled = mc['enabled']
    if enabled == 'all':
        print(f"  ALL modules enabled (stage={u.config['name']})")
    else:
        print(f"  Enabled: {len(enabled)} — {', '.join(enabled)}")
    print(f"  Max concurrent: {mc['max_concurrent']}")


def phase12():
    """NEXUS-6 Bidirectional Sync."""
    from consciousness_hub import ConsciousnessHub
    hub = ConsciousnessHub()
    r = hub.sync_nexus6()
    g = r.get('growth', {})
    n6 = r.get('nexus6_state', {})
    print(f"  Growth: {g.get('count', 0)} (+{g.get('delta', 0)})")
    print(f"  N6 lenses: {n6.get('lenses', 0)}, laws: {n6.get('laws', 0)}")
    print(f"  Harmony: {n6.get('mirror_harmony', 0):.0f}")


def phase14():
    """Cross-Repo Discovery Sync."""
    reg_path = os.path.expanduser('~/Dev/nexus6/shared/growth-registry.json')
    try:
        reg = json.load(open(reg_path))
        repos = [k for k in reg if isinstance(reg[k], dict) and 'last_scan' in reg[k]]
        print(f"  Active repos: {len(repos)} — {', '.join(repos)}")
        total = sum(reg[k].get('opportunities', 0) for k in repos)
        print(f"  Total opportunities: {total}")
    except Exception:
        print("  Registry: unavailable")


def phase15():
    """Growth Tick."""
    g = json.load(open(os.path.join(CONFIG, 'growth_state.json')))
    g['interaction_count'] = g.get('interaction_count', 0) + 5
    count = g['interaction_count']
    for idx, threshold, name in [(4, 10000, 'adult'), (3, 2000, 'child'), (2, 500, 'toddler')]:
        if count >= threshold and g.get('stage_index', 0) < idx:
            g['stage_index'] = idx
            g.setdefault('milestones', []).append([count, f'→ {name}'])
            print(f"  🎉 STAGE UP → {name} @ {count}")
            break
    g.setdefault('stats', {})['last_tick'] = time.time()
    with open(os.path.join(CONFIG, 'growth_state.json'), 'w') as f:
        json.dump(g, f, indent=2, ensure_ascii=False)
    print(f"  Growth: {count}")


PHASES = {
    1: phase1, 2: phase2, 3: phase3, 4: phase4,
    7: phase7, 8: phase8, 9: phase9, 10: phase10,
    11: phase11, 12: phase12, 14: phase14, 15: phase15,
}

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 growth_phases.py <phase_number>")
        sys.exit(1)
    phase = int(sys.argv[1])
    fn = PHASES.get(phase)
    if fn:
        fn()
    else:
        print(f"Phase {phase}: not implemented in Python")
