#!/usr/bin/env python3
"""Hypothesis Generator — 자동 가설 생성 + 벤치마크 + 등록

invest의 generate_and_verify_hypotheses.py 패턴 적용:
1. 기존 가설의 패턴 분석 → 새 가설 자동 생성
2. 벤치마크 실행 → CONFIRMED만 등록
3. 조합 탐색 (top-N 결합)

Usage:
  python hypothesis_generator.py --generate 10    # 10개 자동 생성
  python hypothesis_generator.py --combine-top 5  # top-5 조합
  python hypothesis_generator.py --mutate A1      # A1 변형 생성
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
import itertools
from dataclasses import dataclass
from typing import List, Dict, Callable

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator
from bench_phi_hypotheses import BenchResult, make_diverse_inputs, run_baseline


# ═══════════════════════════════════════════════════════════
# Technique Library — 기본 기법 블록
# ═══════════════════════════════════════════════════════════

def tech_ib2_selective(engine, x, dim):
    """IB2: 선택적 주의 (top-25%)."""
    with torch.no_grad():
        k = max(1, dim // 4)
        _, idx = x.squeeze().abs().topk(k)
        att = torch.zeros_like(x)
        att.squeeze()[idx] = x.squeeze()[idx] * 2.0
    return att


def tech_growth(engine, frac, max_cells, step_i):
    """TS4-style exponential growth."""
    for pct in [0.10, 0.25, 0.40, 0.55, 0.70]:
        if frac >= pct and len(engine.cells) < min(int(2**((pct+0.1)*8)), max_cells):
            target = min(len(engine.cells)*2, max_cells)
            while len(engine.cells) < target:
                engine._create_cell(parent=engine.cells[step_i % len(engine.cells)])


def tech_metacog(engine, phi, phi_ema, l2, l3, hidden):
    """XMETA3: 3-level metacognition."""
    with torch.no_grad():
        l1 = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        l2_new = 0.9 * l2 + 0.1 * l1
        l3_new = 0.95 * l3 + 0.05 * l2_new
        if phi < phi_ema * 0.7:
            for cell in engine.cells:
                cell.hidden += torch.randn_like(cell.hidden) * 0.04
        for cell in engine.cells:
            cell.hidden = 0.99 * cell.hidden + 0.01 * l3_new.unsqueeze(0)
    return l2_new, l3_new


def tech_entropy_norm(engine):
    """INFO1: 최대 엔트로피 정규화."""
    with torch.no_grad():
        for cell in engine.cells:
            h = cell.hidden.squeeze()
            h_c = h - h.mean()
            cell.hidden = 0.95 * cell.hidden + 0.05 * (h_c / (h_c.std() + 1e-8)).unsqueeze(0)


def tech_empathy(engine):
    """XETH2: 공감 윤리."""
    with torch.no_grad():
        if len(engine.cells) >= 3:
            norms = [c.hidden.norm().item() for c in engine.cells]
            mn = sum(norms) / len(norms)
            for i, cell in enumerate(engine.cells):
                if norms[i] < mn * 0.4:
                    others = torch.stack([c.hidden for j, c in enumerate(engine.cells) if j != i][:6]).mean(dim=0)
                    cell.hidden = 0.7 * cell.hidden + 0.3 * others


def tech_thermo(engine):
    """THERMO1: 산일 구조 (엔트로피 조절)."""
    with torch.no_grad():
        hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
        entropy = hiddens.var(dim=0).mean().item()
        if entropy > 2.0:
            for cell in engine.cells:
                cell.hidden *= 0.98
        elif entropy < 0.1:
            for cell in engine.cells:
                cell.hidden += torch.randn_like(cell.hidden) * 0.03


def tech_mutation(engine, step_i):
    """MUT2: 유익 돌연변이."""
    with torch.no_grad():
        n = len(engine.cells)
        if n >= 2 and step_i % 3 == 0:
            idx = step_i % n
            engine.cells[idx].hidden += torch.randn_like(engine.cells[idx].hidden) * 0.1


# ═══════════════════════════════════════════════════════════
# Auto-Generate: 기법 조합으로 새 가설 자동 생성
# ═══════════════════════════════════════════════════════════

TECHNIQUES = {
    'ib2': tech_ib2_selective,
    'growth': tech_growth,
    'metacog': tech_metacog,
    'entropy': tech_entropy_norm,
    'empathy': tech_empathy,
    'thermo': tech_thermo,
    'mutation': tech_mutation,
}


def generate_hypothesis(tech_names: List[str], max_cells: int = 64,
                       steps: int = 100, dim: int = 64, hidden: int = 128) -> BenchResult:
    """기법 조합으로 자동 가설 실행."""
    t0 = time.time()
    engine = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=max_cells)
    phi_calc = PhiCalculator(n_bins=16)
    phi_hist = []
    phi_ema = 1.0
    l2 = torch.zeros(hidden)
    l3 = torch.zeros(hidden)

    inputs = make_diverse_inputs(steps, dim)

    for step_i, x in enumerate(inputs):
        frac = step_i / steps

        # Apply selected techniques
        if 'ib2' in tech_names:
            x = tech_ib2_selective(engine, x, dim)

        if 'growth' in tech_names:
            tech_growth(engine, frac, max_cells, step_i)

        engine.process(x)
        phi, _ = phi_calc.compute_phi(engine)
        phi_hist.append(phi)
        phi_ema = 0.9 * phi_ema + 0.1 * phi

        if 'metacog' in tech_names:
            l2, l3 = tech_metacog(engine, phi, phi_ema, l2, l3, hidden)

        if 'entropy' in tech_names:
            tech_entropy_norm(engine)

        if 'empathy' in tech_names:
            tech_empathy(engine)

        if 'thermo' in tech_names:
            tech_thermo(engine)

        if 'mutation' in tech_names:
            tech_mutation(engine, step_i)

    phi_final, comp = phi_calc.compute_phi(engine)
    name = "+".join(tech_names)
    return BenchResult(
        f"AUTO_{name}", f"Auto-generated: {name}",
        phi_final, phi_hist, comp['total_mi'],
        comp['min_partition_mi'], comp['integration'],
        comp['complexity'], time.time() - t0,
        extra={'techs': tech_names, 'final_cells': len(engine.cells)},
    )


def auto_generate_and_test(n_combos: int = 20, max_combo_size: int = 4,
                           steps: int = 100) -> List[BenchResult]:
    """자동으로 기법 조합을 생성하고 벤치마크."""
    tech_keys = list(TECHNIQUES.keys())
    results = []

    # Baseline
    torch.manual_seed(42); np.random.seed(42)
    baseline = run_baseline(steps=steps)
    print(f"Baseline Φ = {baseline.phi:.4f}\n")

    # Generate all combos of size 2-4
    all_combos = []
    for size in range(2, max_combo_size + 1):
        for combo in itertools.combinations(tech_keys, size):
            all_combos.append(list(combo))

    # Shuffle and take top-N
    import random
    random.seed(42)
    random.shuffle(all_combos)
    selected = all_combos[:n_combos]

    for i, techs in enumerate(selected):
        torch.manual_seed(42); np.random.seed(42)
        try:
            r = generate_hypothesis(techs, max_cells=64, steps=steps)
            ratio = r.phi / max(baseline.phi, 1e-8)
            verdict = "✅" if ratio >= 2.0 else "🟧" if ratio >= 1.2 else "⚪"
            print(f"  {verdict} {'+'.join(techs):30s} Φ={r.phi:>8.2f} ×{ratio:>6.1f}")
            results.append(r)
        except Exception as e:
            print(f"  ❌ {'+'.join(techs):30s} FAILED: {e}")

    results.sort(key=lambda x: -x.phi)
    print(f"\n{'='*60}")
    print(f"Top 5 auto-generated hypotheses:")
    for r in results[:5]:
        ratio = r.phi / max(baseline.phi, 1e-8)
        print(f"  {r.hypothesis:35s} Φ={r.phi:>8.2f} ×{ratio:>6.1f}")

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", type=int, default=20, help="Number of combos to test")
    parser.add_argument("--max-size", type=int, default=4, help="Max techniques per combo")
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--max-cells", type=int, default=64, help="Max cells for auto-generated")
    args = parser.parse_args()

    print("╔══════════════════════════════════════════════════╗")
    print("║  Hypothesis Generator (invest-inspired)          ║")
    print(f"║  Combos: {args.generate}, Max size: {args.max_size}                    ║")
    print("╚══════════════════════════════════════════════════╝\n")

    results = auto_generate_and_test(
        n_combos=args.generate,
        max_combo_size=args.max_size,
        steps=args.steps,
    )
