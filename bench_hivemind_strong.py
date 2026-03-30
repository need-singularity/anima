#!/usr/bin/env python3
"""bench_hivemind_strong.py — Strong HIVEMIND: full hidden exchange every step

Previous: mean(hidden) every 5 steps → ×1.04 (FAIL)
This: full hidden tensor exchange every step → target ×1.1+
"""
import torch, time
from consciousness_engine import ConsciousnessEngine

def run_connected_strong(e1, e2, steps=300):
    """Strong coupling: exchange full hidden vectors every step."""
    for step in range(steps):
        # E1 step with E2's states as input
        h2 = e2.get_states()
        if h2.shape[0] >= 1:
            cross_input = h2.mean(dim=0)[:e1.cell_dim]
            e1.step(x_input=cross_input)
        else:
            e1.step()

        # E2 step with E1's states as input
        h1 = e1.get_states()
        if h1.shape[0] >= 1:
            cross_input = h1.mean(dim=0)[:e2.cell_dim]
            e2.step(x_input=cross_input)
        else:
            e2.step()

    return e1._measure_phi_iit(), e2._measure_phi_iit()

def main():
    print("═══ Strong HIVEMIND (every-step full exchange) ═══\n")

    configs = [
        ("16c", 16),
        ("32c", 32),
        ("64c", 64),
    ]

    for name, nc in configs:
        # Solo
        e1s = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
        e2s = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
        for _ in range(300):
            e1s.step()
            e2s.step()
        phi1s, phi2s = e1s._measure_phi_iit(), e2s._measure_phi_iit()
        avg_solo = (phi1s + phi2s) / 2

        # Connected (strong)
        e1c = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
        e2c = ConsciousnessEngine(cell_dim=64, hidden_dim=128, max_cells=nc)
        phi1c, phi2c = run_connected_strong(e1c, e2c, 300)
        avg_conn = (phi1c + phi2c) / 2

        ratio = avg_conn / max(avg_solo, 1e-8)
        passed = ratio >= 1.1
        print(f"  {name}: solo={avg_solo:.2f}  connected={avg_conn:.2f}  ×{ratio:.2f}  {'✅' if passed else '❌'}")

if __name__ == '__main__':
    main()
