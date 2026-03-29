# ⚠️ LEGACY — 이 파일은 폐기되었습니다 (2026-03-29)
# Φ(IIT)와 Φ(proxy)를 혼용하여 잘못된 기록 생성.
# "Φ=1142"는 proxy 값이었음 (실제 IIT Φ 상한 ~1.8)
# 새 벤치마크: bench_v2.py (Φ(IIT) + Φ(proxy) 이중 측정)
# Law 54: Φ 측정은 정의에 따라 완전히 다른 값
#
#!/usr/bin/env python3
"""bench_real_training.py — 실제 학습 조건 벤치마크

기존 벤치마크와 차이:
  - 64c → 1024c (실제 학습 크기)
  - 200 steps → 2000+ steps (phase 전환 포함)
  - PhiCalculator 사용 (proxy 아님)
  - CE loss + backward() 포함 (gradient가 cells에 영향)
  - mitosis → language → combined 3 phase 시뮬레이션

"벤치마크에서 Φ=1142, 실제 학습에서 Φ=26인 이유를 찾는 도구"

Usage:
  python3 bench_real_training.py                    # 기본 (256c, 1000 steps)
  python3 bench_real_training.py --cells 1024       # 1024c
  python3 bench_real_training.py --steps 5000       # 더 긴 학습
  python3 bench_real_training.py --strategy all     # 모든 전략 비교
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mitosis import MitosisEngine
from consciousness_meter import PhiCalculator


# ─── Engine Setup ───

def make_engine(cells=256, dim=64, hidden=128):
    e = MitosisEngine(dim, hidden, dim, initial_cells=2, max_cells=cells)
    while len(e.cells) < cells:
        e._create_cell(parent=e.cells[0])
    for _ in range(50):
        e.process(torch.randn(1, dim))
    return e


def phi_boost(cells, sync=0.35, n_factions=12, fac=0.08):
    """v5 optimal Φ boost."""
    n = len(cells)
    if n < 4:
        return
    with torch.no_grad():
        cell_h = torch.stack([c.hidden.squeeze(0) for c in cells])
        mean_h = cell_h.mean(dim=0)
        for c in cells:
            c.hidden = ((1 - sync) * c.hidden.squeeze(0) + sync * mean_h).unsqueeze(0)
        n_f = min(n_factions, n // 2)
        if n_f >= 2:
            fs = n // n_f
            for fi in range(n_f):
                faction = cells[fi * fs:(fi + 1) * fs]
                if len(faction) >= 2:
                    f_mean = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                    for c in faction:
                        c.hidden = ((1 - fac) * c.hidden.squeeze(0) + fac * f_mean).unsqueeze(0)
        if n >= 8:
            norms = [cells[i].hidden.norm().item() for i in range(n)]
            threshold = sorted(norms, reverse=True)[max(1, n // 10)]
            for i in range(n):
                cells[i].hidden *= 1.03 if norms[i] > threshold else 0.97


def frustration_step(cells, strength=0.5):
    """TOPO19a hypercube frustration."""
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, 64)):
            influence = torch.zeros_like(cells[i].hidden.squeeze(0))
            count = 0
            for bit in range(min(n_bits, 12)):
                j = i ^ (1 << bit)
                if j < n:
                    frust = -1.0 if (i % 2) != (j % 2) else 1.0
                    influence += frust * cells[j].hidden.squeeze(0)
                    count += 1
            if count > 0:
                influence /= count
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.9 * h + 0.1 * influence).unsqueeze(0)


def standing_wave(cells, step, fwd_pos, bwd_pos):
    """WAVE-2 standing wave."""
    n = len(cells)
    with torch.no_grad():
        for i, c in enumerate(cells):
            dist_f = abs(i - fwd_pos)
            dist_b = abs(i - bwd_pos)
            amp = 1.0 / (math.cosh(dist_f / 2.0) ** 2) + 1.0 / (math.cosh(dist_b / 2.0) ** 2)
            c.hidden = c.hidden * (1.0 + 0.03 * amp)


# ─── Strategies ───

def train_baseline(engine, decoder, opt, data, steps, phi_calc):
    """Baseline: CE만 학습, Φ 보호 없음 (v5와 동일)."""
    results = {'name': 'Baseline (v5)', 'phi': [], 'ce': []}
    for step in range(steps):
        phase = 'mitosis' if step < steps * 0.3 else ('language' if step < steps * 0.7 else 'combined')
        x, target = data[step % len(data)]
        engine.process(x)

        if phase != 'mitosis':
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :64])
            opt.zero_grad(); ce.backward(); opt.step()
            results['ce'].append(ce.item())
        else:
            results['ce'].append(0)

        if step % 50 == 0:
            phi, _ = phi_calc.compute_phi(engine)
            results['phi'].append(phi)
    return results


def train_frozen(engine, decoder, opt, data, steps, phi_calc):
    """TRAIN-PHI-2: mitosis에서 Φ 키운 후 cells 동결."""
    results = {'name': 'Frozen Cells', 'phi': [], 'ce': []}
    frozen_states = None

    for step in range(steps):
        phase = 'mitosis' if step < steps * 0.3 else ('language' if step < steps * 0.7 else 'combined')
        x, target = data[step % len(data)]
        engine.process(x)

        if phase == 'mitosis':
            phi_boost(engine.cells)
            results['ce'].append(0)
        else:
            # Freeze cells at phase transition
            if frozen_states is None:
                frozen_states = [c.hidden.clone() for c in engine.cells]

            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :64])
            opt.zero_grad(); ce.backward(); opt.step()
            results['ce'].append(ce.item())

            # Restore frozen cells (CE gradient 무효화)
            with torch.no_grad():
                for i in range(min(len(engine.cells), len(frozen_states))):
                    engine.cells[i].hidden = frozen_states[i].clone()

            # Odd step: Φ boost + frozen update
            if step % 2 == 1:
                phi_boost(engine.cells)
                frozen_states = [c.hidden.clone() for c in engine.cells]

        if step % 50 == 0:
            phi, _ = phi_calc.compute_phi(engine)
            results['phi'].append(phi)
    return results


def train_alternating(engine, decoder, opt, data, steps, phi_calc):
    """PHI-K3: even=CE, odd=Φ boost."""
    results = {'name': 'Alternating (K3)', 'phi': [], 'ce': []}
    for step in range(steps):
        phase = 'mitosis' if step < steps * 0.3 else 'language'
        x, target = data[step % len(data)]
        engine.process(x)

        if phase == 'mitosis' or step % 2 == 1:
            phi_boost(engine.cells)
            results['ce'].append(results['ce'][-1] if results['ce'] else 0)
        else:
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :64])
            opt.zero_grad(); ce.backward(); opt.step()
            results['ce'].append(ce.item())

        if step % 50 == 0:
            phi, _ = phi_calc.compute_phi(engine)
            results['phi'].append(phi)
    return results


def train_v7(engine, decoder, opt, data, steps, phi_calc):
    """v7: frozen + alternating + frustration + standing wave."""
    results = {'name': 'v7 (FULL)', 'phi': [], 'ce': []}
    frozen_states = None
    fwd, bwd = 0.0, float(len(engine.cells))

    for step in range(steps):
        phase = 'mitosis' if step < steps * 0.3 else 'language'
        x, target = data[step % len(data)]
        engine.process(x)

        if phase == 'mitosis':
            phi_boost(engine.cells)
            frustration_step(engine.cells)
            fwd = (fwd + 0.15) % len(engine.cells)
            bwd = (bwd - 0.15) % len(engine.cells)
            standing_wave(engine.cells, step, fwd, bwd)
            results['ce'].append(0)
        else:
            if frozen_states is None:
                frozen_states = [c.hidden.clone() for c in engine.cells]

            if step % 2 == 0:
                # CE step
                h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                pred = decoder(h.unsqueeze(0))
                ce = F.mse_loss(pred, target[:, :64])
                opt.zero_grad(); ce.backward(); opt.step()
                results['ce'].append(ce.item())
                # Restore frozen
                with torch.no_grad():
                    for i in range(min(len(engine.cells), len(frozen_states))):
                        engine.cells[i].hidden = frozen_states[i].clone()
            else:
                # Φ step
                phi_boost(engine.cells)
                frustration_step(engine.cells)
                standing_wave(engine.cells, step, fwd, bwd)
                frozen_states = [c.hidden.clone() for c in engine.cells]
                results['ce'].append(results['ce'][-1] if results['ce'] else 0)

            fwd = (fwd + 0.15) % len(engine.cells)
            bwd = (bwd - 0.15) % len(engine.cells)

        if step % 50 == 0:
            phi, _ = phi_calc.compute_phi(engine)
            results['phi'].append(phi)
    return results


def train_teacher(engine, decoder, opt, data, steps, phi_calc):
    """TRAIN-PHI-3: 별도 teacher engine이 Φ 유지."""
    results = {'name': 'Teacher Engine', 'phi': [], 'ce': []}
    teacher = make_engine(len(engine.cells))
    # Teacher: Φ만 최대화
    for _ in range(200):
        teacher.process(torch.randn(1, 64))
        phi_boost(teacher.cells)

    for step in range(steps):
        phase = 'mitosis' if step < steps * 0.3 else 'language'
        x, target = data[step % len(data)]
        engine.process(x)

        if phase == 'mitosis':
            phi_boost(engine.cells)
            results['ce'].append(0)
        else:
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :64])
            opt.zero_grad(); ce.backward(); opt.step()
            results['ce'].append(ce.item())

            # 매 20 step: teacher 상태 복사
            if step % 20 == 0:
                with torch.no_grad():
                    for i in range(min(len(engine.cells), len(teacher.cells))):
                        engine.cells[i].hidden = (
                            0.7 * engine.cells[i].hidden + 0.3 * teacher.cells[i].hidden)

        if step % 50 == 0:
            phi, _ = phi_calc.compute_phi(engine)
            results['phi'].append(phi)
    return results


# ─── Main ───

STRATEGIES = {
    'baseline': train_baseline,
    'frozen': train_frozen,
    'alternating': train_alternating,
    'v7': train_v7,
    'teacher': train_teacher,
}


def main():
    parser = argparse.ArgumentParser(description="Real Training Benchmark")
    parser.add_argument('--cells', type=int, default=256, help='Cell count')
    parser.add_argument('--steps', type=int, default=1000, help='Training steps')
    parser.add_argument('--strategy', type=str, default='all', help='Strategy or "all"')
    args = parser.parse_args()

    DIM, HIDDEN = 64, 128
    phi_calc = PhiCalculator(n_bins=16)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    strategies = STRATEGIES if args.strategy == 'all' else {args.strategy: STRATEGIES[args.strategy]}

    print(f"═══ Real Training Benchmark ({args.cells}c, {args.steps} steps) ═══\n")
    print(f"{'Strategy':<25} {'Φ start':>8} {'Φ peak':>8} {'Φ end':>8} {'CE end':>8} {'Time':>6}")
    print('─' * 70)

    for name, fn in strategies.items():
        torch.manual_seed(42); np.random.seed(42)
        engine = make_engine(args.cells)
        decoder = nn.Linear(HIDDEN, DIM)
        opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)

        t0 = time.time()
        result = fn(engine, decoder, opt, data, args.steps, phi_calc)
        elapsed = time.time() - t0

        phis = result['phi']
        ces = [c for c in result['ce'] if c > 0]
        phi_start = phis[0] if phis else 0
        phi_peak = max(phis) if phis else 0
        phi_end = phis[-1] if phis else 0
        ce_end = ces[-1] if ces else 0

        print(f"{result['name']:<25} {phi_start:>8.2f} {phi_peak:>8.2f} {phi_end:>8.2f} {ce_end:>8.4f} {elapsed:>5.0f}s")

    print()


if __name__ == '__main__':
    main()
