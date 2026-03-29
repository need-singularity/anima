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
    from trinity import EmotionW, ConstantW, CosineW, NarrativeW, DaseinW, CompositeW
    return {
        'Emotion': lambda: EmotionW(base_lr=base_lr),
        'Constant': lambda: ConstantW(lr=base_lr),
        'Narrative': lambda: NarrativeW(base_lr=base_lr),
        'Dasein': lambda: DaseinW(base_lr=base_lr),
        'Perfect6': lambda: CompositeW([DaseinW(base_lr=base_lr), NarrativeW(base_lr=base_lr), EmotionW(base_lr=base_lr)], [1/2, 1/3, 1/6]),
    }


def get_m_engines():
    """All M (memory) engines."""
    from trinity import VectorMemory, NoMemory
    return {'None': lambda: None, 'Vector': lambda: VectorMemory(), 'NoMem': lambda: NoMemory()}


def get_s_engines():
    """All S (sense) engines."""
    from trinity import TensionSense, PassthroughSense
    return {'None': lambda: None, 'Tension': lambda: TensionSense(), 'Passthru': lambda: PassthroughSense()}


def get_e_engines():
    """All E (ethics) engines."""
    from trinity import EmpathyEthics, NoEthics
    return {'None': lambda: None, 'Empathy': lambda: EmpathyEthics(), 'NoEthics': lambda: NoEthics()}


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
             c_only=False, hexad=False, base_lr=1e-3):
    """Run C×D×W (×M×S×E) grid search.

    c_only: fix D,W (test C engines only)
    hexad: include M,S,E in grid (6-module combos)
    """
    c_engines = get_c_engines(nc=nc, dim=64, hidden=128)
    d_engines = get_d_engines(d_model=d_model, vocab_size=vocab_size)
    w_engines = get_w_engines(base_lr=base_lr)

    if c_only:
        d_engines = {'Xfmr4L': list(d_engines.values())[0]}
        w_engines = {'Emotion': list(w_engines.values())[0]}

    if hexad:
        m_engines = get_m_engines()
        s_engines = get_s_engines()
        e_engines = get_e_engines()
        combos = list(product(
            c_engines.items(), d_engines.items(), w_engines.items(),
            m_engines.items(), s_engines.items(), e_engines.items()
        ))
    else:
        combos = list(product(c_engines.items(), d_engines.items(), w_engines.items()))

    total = len(combos)
    if top_n and top_n < total:
        combos = combos[:top_n]
        total = len(combos)

    n_m = len(get_m_engines()) if hexad else 1
    n_s = len(get_s_engines()) if hexad else 1
    n_e = len(get_e_engines()) if hexad else 1
    mode = "Hexad C×D×W×M×S×E" if hexad else "Trinity C×D×W"

    print(f"\n═══ Phase 2: {mode} Grid ({total} combos, {n_steps} steps) ═══\n")
    print(f"  C:{len(c_engines)} D:{len(d_engines)} W:{len(w_engines)} M:{n_m} S:{n_s} E:{n_e}")
    print(f"  cells={nc}, d_model={d_model}, vocab={vocab_size}\n")

    header = f"{'C':<20} {'D':<12} {'W':<10} "
    if hexad:
        header += f"{'M':<8} {'S':<8} {'E':<8} "
    header += f"{'CE':>8} {'Φ':>10} {'Pain':>6} {'Time':>6}"
    print(header)
    print('─' * len(header))

    results = []
    for combo in combos:
        if hexad:
            (c_name, c_fn), (d_name, d_fn), (w_name, w_fn), \
            (m_name, m_fn), (s_name, s_fn), (e_name, e_fn) = combo
        else:
            (c_name, c_fn), (d_name, d_fn), (w_name, w_fn) = combo
            m_name, m_fn = 'None', lambda: None
            s_name, s_fn = 'None', lambda: None
            e_name, e_fn = 'None', lambda: None

        try:
            r = test_combo(c_fn, d_fn, w_fn, n_steps=n_steps,
                           seq_len=32, vocab_size=vocab_size)
            line = f"{c_name:<20} {d_name:<12} {w_name:<10} "
            if hexad:
                line += f"{m_name:<8} {s_name:<8} {e_name:<8} "
            line += f"{r['ce']:>8.4f} {r['phi']:>10.3f} {r['pain']:>6.3f} {r['time']:>5.1f}s"
            print(line)
            results.append({
                'c': c_name, 'd': d_name, 'w': w_name,
                'm': m_name, 's': s_name, 'e': e_name, **r
            })
        except Exception as e:
            err_line = f"{c_name:<20} {d_name:<12} {w_name:<10} "
            print(f"{err_line} ERROR: {str(e)[:30]}")

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
    parser.add_argument('--hexad', action='store_true', help='Full 6-module grid (C×D×W×M×S×E)')
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

    # Phase 2: Full grid
    run_grid(nc=args.cells, n_steps=args.steps, d_model=args.d_model,
             vocab_size=args.vocab, top_n=args.top, c_only=args.c_only,
             hexad=args.hexad)


if __name__ == '__main__':
    main()
