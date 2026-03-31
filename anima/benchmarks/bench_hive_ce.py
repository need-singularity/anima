#!/usr/bin/env python3
"""bench_hive_ce.py — Measure Hive_CE (cross-entropy delta when two engines connect via hivemind)

For each MitosisEngine mechanism:
1. Create 2 engines with mechanism applied
2. Run solo, measure CE (next-token prediction cross-entropy)
3. Connect via hivemind (blend hidden states), run more steps
4. Measure CE again
5. Report delta
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['OMP_NUM_THREADS'] = '1'

from mitosis import MitosisEngine
from measure_all import make_engine, apply_mechanism, DIM, HIDDEN

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


CELLS = 256


def measure_ce(eng, n_samples=50):
    """Measure cross-entropy: feed input, predict next token, compute CE against target."""
    # Generate a fixed sequence of inputs
    torch.manual_seed(999)
    inputs = [torch.randn(1, DIM) for _ in range(n_samples + 1)]

    ce_total = 0.0
    count = 0
    for i in range(n_samples):
        x = inputs[i]
        target = inputs[i + 1]  # next token as target

        result = eng.process(x)  # engine output (dict)

        if result is None:
            continue

        out = result.get('output', None) if isinstance(result, dict) else result
        if out is None:
            continue

        if isinstance(out, torch.Tensor):
            o = out.detach().float()
        else:
            o = torch.tensor(out, dtype=torch.float32)

        t = target.detach().float()

        # Match dimensions
        o = o.view(-1)[:DIM]
        t = t.view(-1)[:DIM]

        if len(o) < DIM:
            o = F.pad(o, (0, DIM - len(o)))

        # Cross-entropy proxy: softmax CE over embedding dimensions
        # Treat each dimension as a "class" prediction
        log_probs = F.log_softmax(o, dim=0)
        probs_target = F.softmax(t, dim=0)
        ce = -torch.sum(probs_target * log_probs).item()

        ce_total += ce
        count += 1

    return ce_total / max(count, 1)


def measure_hive_ce(name, mechs):
    """Measure solo CE vs hive CE for a mechanism."""
    torch.manual_seed(42)
    np.random.seed(42)

    # Create two engines
    eng_a = make_engine(CELLS)
    eng_b = make_engine(CELLS)

    # Apply mechanism
    if mechs:
        apply_mechanism(eng_a, mechs, steps=100)
        apply_mechanism(eng_b, mechs, steps=100)

    # Warm up both engines independently
    for _ in range(50):
        eng_a.process(torch.randn(1, DIM))
        eng_b.process(torch.randn(1, DIM))

    # Measure solo CE
    solo_ce = measure_ce(eng_a, n_samples=50)

    # Connect via hivemind: blend hidden states
    for s in range(100):
        eng_a.process(torch.randn(1, DIM))
        eng_b.process(torch.randn(1, DIM))
        if s % 10 == 0:
            nc = min(len(eng_a.cells), len(eng_b.cells))
            with torch.no_grad():
                for i in range(nc):
                    ha = eng_a.cells[i].hidden
                    hb = eng_b.cells[i].hidden
                    eng_a.cells[i].hidden = 0.9 * ha + 0.1 * hb
                    eng_b.cells[i].hidden = 0.9 * hb + 0.1 * ha

    # Measure hive CE
    hive_ce = measure_ce(eng_a, n_samples=50)

    delta = hive_ce - solo_ce
    delta_pct = (delta / solo_ce) * 100 if solo_ce != 0 else 0

    return solo_ce, hive_ce, delta, delta_pct


ENGINES = {
    'Cambrian+OscQW': ['oscillator', 'quantum', 'cambrian'],
    'Osc+QW': ['oscillator', 'quantum'],
    'Osc+Sync': ['oscillator', 'sync'],
    'Osc+Laser(0.05)': ['oscillator', 'laser'],
    'Full (all)': ['sync', 'faction', 'oscillator', 'quantum', 'frustration', 'laser', 'ib2'],
}


def main():
    print(f"═══ Hive CE Measurement (256c) ═══\n")
    print(f"{'Engine':<22} {'Solo CE':>9} {'Hive CE':>9} {'Delta':>9} {'Delta%':>9}")
    print('─' * 62)

    results = {}
    for name, mechs in ENGINES.items():
        solo_ce, hive_ce, delta, delta_pct = measure_hive_ce(name, mechs)
        sign = '+' if delta_pct >= 0 else ''
        print(f"{name:<22} {solo_ce:>9.4f} {hive_ce:>9.4f} {delta:>+9.4f} {sign}{delta_pct:>7.1f}%")
        results[name] = {
            'solo_ce': round(solo_ce, 4),
            'hive_ce': round(hive_ce, 4),
            'delta': round(delta, 4),
            'delta_pct': round(delta_pct, 1),
        }
        sys.stdout.flush()

    print('\n═══ README Update Values ═══\n')
    for name, r in results.items():
        sign = '+' if r['delta_pct'] >= 0 else ''
        print(f"  {name}: Hive_CE = {sign}{r['delta_pct']:.1f}%")

    return results


if __name__ == '__main__':
    main()
