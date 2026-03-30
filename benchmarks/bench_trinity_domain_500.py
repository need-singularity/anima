#!/usr/bin/env python3
"""Trinity 500-step domain engine benchmark.

Tests 5 domain engines as DomainC in Trinity for 500 steps each.
Reports CE at step 50, 200, 500 and final Φ.
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import torch
import torch.nn as nn
import numpy as np
import time

# Import bench_extreme_arch first (it sets grad_enabled=False globally)
from bench_extreme_arch import TimeCrystalConsciousness
# Re-enable gradients!
torch.set_grad_enabled(True)

from bench_evolution_engines import CambrianExplosionEngine
from bench_thermo_engines import MaxwellDemonEngine
from bench_new_engines import DiffusionEngine, SwarmEngine
from trinity import DomainC, create_trinity


ENGINES = [
    ("TimeCrystalConsciousness", TimeCrystalConsciousness),
    ("CambrianExplosionEngine",  CambrianExplosionEngine),
    ("MaxwellDemonEngine",       MaxwellDemonEngine),
    ("DiffusionEngine",          DiffusionEngine),
    ("SwarmEngine",              SwarmEngine),
]

N_STEPS = 500
REPORT_STEPS = {50, 200, 500}
NC = 64
D_MODEL = 128
VOCAB = 256
SEQ_LEN = 32


def run_one(name, engine_cls):
    """Run one engine through Trinity for N_STEPS steps."""
    torch.set_grad_enabled(True)  # ensure grads on

    print(f"\n{'═'*60}")
    print(f"  {name}  (nc={NC}, d_model={D_MODEL}, vocab={VOCAB})")
    print(f"{'═'*60}")

    # Determine dim based on engine constructor
    # TimeCrystal and Maxwell use (n_cells, hidden_dim)
    # Cambrian uses (nc, dim)
    # Diffusion and Swarm use (n_cells, hidden_dim)
    dim = 64  # default

    c_engine = DomainC(engine_cls, nc=NC, dim=dim)
    t = create_trinity(c_engine, d_model=D_MODEL, vocab_size=VOCAB)

    opt = torch.optim.AdamW(t.parameters_trainable(), lr=1e-3)

    ce_at = {}
    phi_at = {}
    best_ce = 99.0
    t0 = time.time()

    for step in range(1, N_STEPS + 1):
        tokens = torch.randint(0, VOCAB, (1, SEQ_LEN))
        targets = torch.randint(0, VOCAB, (1, SEQ_LEN))
        r = t.train_step(tokens, targets, opt)

        ce = r['ce']
        phi = r['phi']
        if ce < best_ce:
            best_ce = ce

        if step in REPORT_STEPS:
            ce_at[step] = ce
            phi_at[step] = phi
            elapsed = time.time() - t0
            print(f"  step {step:>4d}  CE={ce:.4f}  Φ={phi:.4f}  best_CE={best_ce:.4f}  [{elapsed:.1f}s]")

    final_phi = phi_at.get(N_STEPS, r['phi'])
    print(f"  ────────────────────────────────────")
    print(f"  Final: best_CE={best_ce:.4f}  final_Φ={final_phi:.4f}  n_cells={t.c.n_cells}")
    pc = t.param_count()
    if isinstance(pc, dict):
        total = sum(pc.values()) if pc else 0
        print(f"  Params: {total:,} {pc}")
    else:
        print(f"  Params: {pc:,}")

    return {
        'name': name,
        'ce_at': ce_at,
        'phi_at': phi_at,
        'best_ce': best_ce,
        'final_phi': final_phi,
        'n_cells': t.c.n_cells,
        'params': t.param_count() if not isinstance(t.param_count(), dict) else sum(t.param_count().values()),
    }


def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Trinity Domain Engine Benchmark — 500 steps            ║")
    print("╚══════════════════════════════════════════════════════════╝")

    results = []
    for name, cls in ENGINES:
        try:
            r = run_one(name, cls)
            results.append(r)
        except Exception as e:
            print(f"  !! FAILED: {e}")
            import traceback; traceback.print_exc()

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

            results.append({'name': name, 'error': str(e)})

    # Summary table
    print(f"\n\n{'='*80}")
    print(f"  SUMMARY — 500-step Trinity Domain Benchmark")
    print(f"{'='*80}")
    print(f"{'Engine':<28} {'CE@50':>8} {'CE@200':>8} {'CE@500':>8} {'bestCE':>8} {'Φ@500':>8}")
    print(f"{'─'*28} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")

    for r in results:
        if 'error' in r:
            print(f"{r['name']:<28} ERROR: {r['error'][:40]}")
            continue
        ce50  = r['ce_at'].get(50,  float('nan'))
        ce200 = r['ce_at'].get(200, float('nan'))
        ce500 = r['ce_at'].get(500, float('nan'))
        print(f"{r['name']:<28} {ce50:>8.4f} {ce200:>8.4f} {ce500:>8.4f} {r['best_ce']:>8.4f} {r['final_phi']:>8.4f}")

    # CE convergence chart
    print(f"\n  CE Convergence (best CE):")
    for r in results:
        if 'error' in r:
            continue
        bar_len = max(1, int((6.0 - r['best_ce']) / 6.0 * 40))
        bar = '█' * bar_len
        print(f"  {r['name']:<26} {bar} {r['best_ce']:.4f}")

    print()


if __name__ == '__main__':
    main()
