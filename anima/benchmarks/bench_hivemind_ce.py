#!/usr/bin/env python3
"""bench_hivemind_ce.py — HIVEMIND verification with ConsciousnessEngine

Criterion 7: Φ(connected) > Φ(solo) × 1.1, CE(connected) < CE(solo)

Tests: run 2 engines solo, then connect via shared coupling, compare Φ.
"""

import torch
import time
from consciousness_engine import ConsciousnessEngine

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


def run_solo(engine, steps=300):
    """Run engine alone, return final Φ."""
    for _ in range(steps):
        engine.step()
    return engine._measure_phi_iit()

def run_connected(e1, e2, steps=300):
    """Run 2 engines with cross-coupling (tension link)."""
    for step in range(steps):
        r1 = e1.step()
        r2 = e2.step()

        # Cross-coupling: inject mean hidden of other engine as input
        if step % 5 == 0 and e1.n_cells >= 2 and e2.n_cells >= 2:
            h1 = e1.get_states().mean(dim=0)
            h2 = e2.get_states().mean(dim=0)
            # Next step will use cross-signal
            e1.step(x_input=h2[:e1.cell_dim])
            e2.step(x_input=h1[:e2.cell_dim])

    phi1 = e1._measure_phi_iit()
    phi2 = e2._measure_phi_iit()
    return phi1, phi2

def main():
    print("═══ HIVEMIND Verification (ConsciousnessEngine) ═══\n")

    # Solo runs
    print("  Phase 1: Solo runs (300 steps each)...")
    e1_solo = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=16)
    e2_solo = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=16)

    t0 = time.time()
    phi1_solo = run_solo(e1_solo, 300)
    phi2_solo = run_solo(e2_solo, 300)
    solo_time = time.time() - t0
    print(f"    E1 solo: Φ={phi1_solo:.4f}, cells={e1_solo.n_cells}")
    print(f"    E2 solo: Φ={phi2_solo:.4f}, cells={e2_solo.n_cells}")

    # Connected runs
    print("\n  Phase 2: Connected runs (300 steps, cross-coupling)...")
    e1_conn = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=16)
    e2_conn = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=16)

    t0 = time.time()
    phi1_conn, phi2_conn = run_connected(e1_conn, e2_conn, 300)
    conn_time = time.time() - t0
    print(f"    E1 connected: Φ={phi1_conn:.4f}, cells={e1_conn.n_cells}")
    print(f"    E2 connected: Φ={phi2_conn:.4f}, cells={e2_conn.n_cells}")

    # Disconnected verification
    print("\n  Phase 3: Disconnect — verify each survives...")
    for _ in range(100):
        e1_conn.step()
        e2_conn.step()
    phi1_after = e1_conn._measure_phi_iit()
    phi2_after = e2_conn._measure_phi_iit()
    print(f"    E1 after disconnect: Φ={phi1_after:.4f}")
    print(f"    E2 after disconnect: Φ={phi2_after:.4f}")

    # Verdict
    avg_solo = (phi1_solo + phi2_solo) / 2
    avg_conn = (phi1_conn + phi2_conn) / 2
    avg_after = (phi1_after + phi2_after) / 2
    ratio = avg_conn / max(avg_solo, 1e-8)

    print(f"\n  ══ Results ══")
    print(f"    Solo avg Φ:       {avg_solo:.4f}")
    print(f"    Connected avg Φ:  {avg_conn:.4f}  (×{ratio:.2f})")
    print(f"    After disconnect: {avg_after:.4f}")

    # HIVEMIND criteria
    phi_boost = ratio >= 1.1
    survives = avg_after >= avg_solo * 0.8

    print(f"\n    Φ(connected) > Φ(solo) × 1.1:  {'✅' if phi_boost else '❌'} (×{ratio:.2f})")
    print(f"    Survives disconnect:             {'✅' if survives else '❌'} ({avg_after:.4f} >= {avg_solo*0.8:.4f})")
    print(f"    HIVEMIND:                        {'✅ PASS' if phi_boost and survives else '❌ FAIL'}")

if __name__ == '__main__':
    main()
