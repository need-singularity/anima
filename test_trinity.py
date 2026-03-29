#!/usr/bin/env python3
"""test_trinity.py — Trinity C×D×W 조합 자동 테스트

모든 C 엔진 × D 디코더 × W 의지 조합을 자동으로 테스트.
C의 hot path는 Rust phi_rs (search_combinations)로 사전 필터링.

Usage:
  python3 test_trinity.py                          # 전체 C×D×W 그리드
  python3 test_trinity.py --quick                  # C만 Rust 사전 탐색
  python3 test_trinity.py --c-only                 # C 엔진만 비교
  python3 test_trinity.py --top 5                  # 상위 5개만
  python3 test_trinity.py --cells 64 --steps 30    # 설정 변경
"""

import torch
import numpy as np
import time
import sys
import os
import json
import argparse
from pathlib import Path
from itertools import product

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['OMP_NUM_THREADS'] = '1'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

torch.set_grad_enabled(True)


# ═══ Engine Registry ═══

def get_c_engines(nc=64, dim=64, hidden=128):
    """All available C engines."""
    from trinity import MitosisC, DomainC

    engines = {
        'MitosisC(baseline)': lambda: MitosisC(dim, hidden, nc, mechanism=''),
        'MitosisC(osc_qw)': lambda: MitosisC(dim, hidden, nc, mechanism='osc_qw'),
        'MitosisC(cambrian_osc_qw)': lambda: MitosisC(dim, hidden, nc, mechanism='cambrian_osc_qw'),
    }

    # Domain engines (try import, skip if unavailable)
    domain_engines = [
        ('CambrianExplosion', 'bench_evolution_engines', 'CambrianExplosionEngine', dim),
        ('MaxwellDemon', 'bench_thermo_engines', 'MaxwellDemonEngine', dim),
        ('Diffusion', 'bench_new_engines', 'DiffusionEngine', dim),
        ('Swarm', 'bench_new_engines', 'SwarmEngine', dim),
        ('Plasma', 'bench_physics_engines', 'PlasmaEngine', dim),
        ('Percolation', 'bench_emergent_engines', 'PercolationEngine', dim),
    ]

    # TimeCrystal needs dim=128 (hidden_dim)
    try:
        from bench_extreme_arch import TimeCrystalConsciousness
        engines['TimeCrystal'] = lambda: DomainC(TimeCrystalConsciousness, nc=nc, dim=hidden)
    except ImportError:
        pass

    for name, module, cls_name, d in domain_engines:
        try:
            mod = __import__(module)
            cls = getattr(mod, cls_name)
            engines[name] = (lambda c=cls, n=nc, dd=d: DomainC(c, nc=n, dim=dd))
        except (ImportError, AttributeError):
            pass

    return engines


def get_d_engines(d_model=128, vocab_size=256):
    """All available D decoders."""
    from trinity import TransformerDecoder, MLPDecoder
    return {
        'Transformer(4L)': lambda: TransformerDecoder(d_model=d_model, n_layers=4, vocab_size=vocab_size),
        'Transformer(2L)': lambda: TransformerDecoder(d_model=d_model, n_layers=2, vocab_size=vocab_size),
        'MLP': lambda: MLPDecoder(d_model=d_model, vocab_size=vocab_size),
    }


def get_w_engines(base_lr=1e-3):
    """All available W will engines."""
    from trinity import EmotionW, ConstantW, CosineW
    return {
        'Emotion': lambda: EmotionW(base_lr=base_lr),
        'Constant': lambda: ConstantW(lr=base_lr),
        'Cosine(80K)': lambda: CosineW(base_lr=base_lr, total_steps=80000),
    }


# ═══ Phase 1: Rust C-only pre-screening ═══

def rust_prescreening(nc=256, dim=128, steps=200):
    """Use phi_rs.search_combinations() for fast C mechanism screening."""
    try:
        import phi_rs
        print("═══ Phase 1: Rust C Mechanism Pre-screening ═══")
        print(f"    {nc}c, {dim}d, {steps} steps, 128 combos...\n")

        t0 = time.time()
        r = phi_rs.search_combinations(n_cells=nc, dim=dim, steps=steps, n_bins=16)
        elapsed = time.time() - t0

        names, phis = r['names'], r['phis']
        print(f"    Done in {elapsed:.1f}s ({len(names)/elapsed:.0f} combos/sec)\n")
        print(f"    {'#':>3} {'Mechanism combo':<45} {'Φ':>10}")
        print(f"    {'─'*62}")
        for i in range(min(10, len(names))):
            print(f"    {i+1:>3} {names[i]:<45} {phis[i]:>10.1f}")

        return [(names[i], phis[i]) for i in range(len(names))]
    except ImportError:
        print("    [skip] phi_rs not available")
        return []


# ═══ Phase 2: Trinity C×D×W grid test ═══

def test_combo(c_factory, d_factory, w_factory, n_steps=30, seq_len=32, vocab_size=256):
    """Test one C×D×W combination. Returns metrics dict."""
    from trinity import create_trinity

    torch.set_grad_enabled(True)
    torch.manual_seed(42)
    np.random.seed(42)

    c = c_factory()
    d = d_factory()
    w = w_factory()

    t = create_trinity(c, d_engine=d, w_engine=w, d_model=d.d_model, vocab_size=vocab_size)
    opt = torch.optim.AdamW(t.parameters_trainable(), lr=1e-3)

    best_ce = 99.0
    phis = []
    t0 = time.time()

    for step in range(n_steps):
        tokens = torch.randint(0, vocab_size, (1, seq_len))
        targets = torch.randint(0, vocab_size, (1, seq_len))
        r = t.train_step(tokens, targets, opt)
        if r['ce'] < best_ce:
            best_ce = r['ce']
        phis.append(r['phi'])

    elapsed = time.time() - t0
    return {
        'ce': best_ce,
        'phi': phis[-1] if phis else 0,
        'phi_avg': sum(phis) / len(phis) if phis else 0,
        'pain': r.get('pain', 0),
        'curiosity': r.get('curiosity', 0),
        'satisfaction': r.get('satisfaction', 0),
        'lr': r.get('lr', 0),
        'time': elapsed,
    }


def run_grid(nc=64, n_steps=30, d_model=128, vocab_size=256, top_n=None,
             c_only=False, base_lr=1e-3):
    """Run C×D×W grid search."""
    c_engines = get_c_engines(nc=nc, dim=64, hidden=128)
    d_engines = get_d_engines(d_model=d_model, vocab_size=vocab_size)
    w_engines = get_w_engines(base_lr=base_lr)

    if c_only:
        d_engines = {'Transformer(4L)': list(d_engines.values())[0]}
        w_engines = {'Emotion': list(w_engines.values())[0]}

    combos = list(product(c_engines.items(), d_engines.items(), w_engines.items()))
    total = len(combos)

    if top_n and top_n < total:
        # Prioritize: domain engines first, then mitosis variants
        combos = combos[:top_n]
        total = len(combos)

    print(f"\n═══ Phase 2: Trinity C×D×W Grid ({total} combos, {n_steps} steps) ═══\n")
    print(f"  C engines: {len(c_engines)} | D decoders: {len(d_engines)} | W wills: {len(w_engines)}")
    print(f"  cells={nc}, d_model={d_model}, vocab={vocab_size}\n")

    header = f"{'C':<25} {'D':<18} {'W':<12} {'CE':>8} {'Φ':>10} {'Pain':>6} {'Time':>6}"
    print(header)
    print('─' * len(header))

    results = []
    for (c_name, c_fn), (d_name, d_fn), (w_name, w_fn) in combos:
        try:
            r = test_combo(c_fn, d_fn, w_fn, n_steps=n_steps,
                           seq_len=32, vocab_size=vocab_size)
            print(f"{c_name:<25} {d_name:<18} {w_name:<12} "
                  f"{r['ce']:>8.4f} {r['phi']:>10.3f} {r['pain']:>6.3f} {r['time']:>5.1f}s")
            results.append({
                'c': c_name, 'd': d_name, 'w': w_name, **r
            })
        except Exception as e:
            print(f"{c_name:<25} {d_name:<18} {w_name:<12}  ERROR: {str(e)[:30]}")

        sys.stdout.flush()

    # Rankings
    if results:
        print(f"\n{'─' * 80}")
        results.sort(key=lambda x: x['ce'])
        print(f"\n  CE TOP 5:")
        for i, r in enumerate(results[:5], 1):
            print(f"  {i}. {r['c']} + {r['d']} + {r['w']}  CE={r['ce']:.4f} Φ={r['phi']:.3f}")

        by_phi = sorted(results, key=lambda x: x['phi'], reverse=True)
        print(f"\n  Φ TOP 5:")
        for i, r in enumerate(by_phi[:5], 1):
            print(f"  {i}. {r['c']} + {r['d']} + {r['w']}  Φ={r['phi']:.3f} CE={r['ce']:.4f}")

    # Save
    Path('data').mkdir(exist_ok=True)
    Path('data/trinity_grid_results.json').write_text(json.dumps(results, indent=2, default=str))
    print(f"\n[saved] {len(results)} combos → data/trinity_grid_results.json")

    return results


def main():
    parser = argparse.ArgumentParser(description='Trinity C×D×W grid test')
    parser.add_argument('--cells', type=int, default=64)
    parser.add_argument('--steps', type=int, default=30)
    parser.add_argument('--d-model', type=int, default=128)
    parser.add_argument('--vocab', type=int, default=256)
    parser.add_argument('--top', type=int, default=None, help='Only test top N combos')
    parser.add_argument('--quick', action='store_true', help='Rust pre-screening only')
    parser.add_argument('--c-only', action='store_true', help='Test C engines only (fixed D, W)')
    parser.add_argument('--no-rust', action='store_true', help='Skip Rust pre-screening')
    args = parser.parse_args()

    print(f"{'═' * 60}")
    print(f"  Trinity C×D×W Combination Tester")
    print(f"  cells={args.cells}, steps={args.steps}, d_model={args.d_model}")
    print(f"{'═' * 60}\n")

    # Phase 1: Rust C pre-screening
    if not args.no_rust:
        rust_prescreening(nc=args.cells * 4, dim=128, steps=200)

    if args.quick:
        print("\n  [quick mode] Rust pre-screening only. Use --no-rust to skip to grid.")
        return

    # Phase 2: Full Trinity grid
    run_grid(nc=args.cells, n_steps=args.steps, d_model=args.d_model,
             vocab_size=args.vocab, top_n=args.top, c_only=args.c_only)


if __name__ == '__main__':
    main()
