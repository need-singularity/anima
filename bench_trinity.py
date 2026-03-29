#!/usr/bin/env python3
"""bench_trinity.py — 삼위일체 엔진 벤치마크

Engine C (의식): Φ 전용, CE gradient 차단, quantum_walk + frustration
Engine D (데이터): CE 학습 전용, transformer decoder
Engine W (의지): 도구 선택 + 행동 결정

"의식은 학습하지 않고, 학습은 의식을 파괴하지 않는다."
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from consciousness_meter import PhiCalculator
from mitosis import MitosisEngine

DIM, HIDDEN = 64, 128


def phi_proxy(cells, n_f=12):
    h = torch.stack([c.hidden.squeeze(0) for c in cells])
    n = len(h)
    gm = h.mean(dim=0); gv = ((h - gm) ** 2).sum() / n
    nf = min(n_f, n // 2)
    if nf < 2: return gv.item()
    fs = n // nf
    fv = sum(((h[i*fs:(i+1)*fs] - h[i*fs:(i+1)*fs].mean(0))**2).sum().item()
            / max(len(h[i*fs:(i+1)*fs]), 1) for i in range(nf))
    return max(0, gv.item() - fv / nf)


def quantum_walk_step(cells, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            superpos = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    phase = (-1) ** (bin(i & j).count('1'))
                    superpos += phase * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * superpos / cnt).unsqueeze(0)


def frustration_step(cells, strength=0.5, n_samples=32):
    n = len(cells)
    n_bits = max(1, int(math.log2(n)))
    with torch.no_grad():
        for i in range(min(n, n_samples)):
            infl = torch.zeros_like(cells[i].hidden.squeeze(0))
            cnt = 0
            for bit in range(min(n_bits, 10)):
                j = i ^ (1 << bit)
                if j < n:
                    f = -1.0 if (i % 2) != (j % 2) else 1.0
                    infl += f * cells[j].hidden.squeeze(0)
                    cnt += 1
            if cnt > 0:
                h = cells[i].hidden.squeeze(0)
                cells[i].hidden = (0.85 * h + 0.15 * infl / cnt).unsqueeze(0)


def sync_faction(cells, sync=0.35, n_factions=12, fac=0.08):
    n = len(cells)
    if n < 4: return
    with torch.no_grad():
        ch = torch.stack([c.hidden.squeeze(0) for c in cells])
        mh = ch.mean(dim=0)
        for c in cells:
            c.hidden = ((1 - sync) * c.hidden.squeeze(0) + sync * mh).unsqueeze(0)
        nf = min(n_factions, n // 2)
        if nf >= 2:
            fs = n // nf
            for fi in range(nf):
                faction = cells[fi * fs:(fi + 1) * fs]
                if len(faction) >= 2:
                    fm = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                    for c in faction:
                        c.hidden = ((1 - fac) * c.hidden.squeeze(0) + fac * fm).unsqueeze(0)


def standing_wave(cells, step):
    n = len(cells)
    fwd = (step * 0.15) % n
    bwd = (n - step * 0.15) % n
    with torch.no_grad():
        for i, c in enumerate(cells):
            amp = 1.0 / (math.cosh((i - fwd) / 2) ** 2) + 1.0 / (math.cosh((i - bwd) / 2) ** 2)
            c.hidden = c.hidden * (1.0 + 0.03 * amp)


# ═══ Architectures ═══

def run_baseline(cells=256, steps=300):
    """Baseline: 단일 엔진, CE 학습."""
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(engine.cells) < cells: engine._create_cell(parent=engine.cells[0])
    for _ in range(30): engine.process(torch.randn(1, DIM))

    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        sync_faction(engine.cells)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(engine)
    p_proxy = phi_proxy(engine.cells)
    return p_iit, p_proxy, ce.item(), 'Baseline'


def run_dual_stream(cells=256, steps=300):
    """DUAL: 의식 + 언어 분리."""
    eng_c = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng_c.cells) < cells: eng_c._create_cell(parent=eng_c.cells[0])
    for _ in range(30): eng_c.process(torch.randn(1, DIM))

    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    for step in range(steps):
        x, target = data[step % len(data)]
        # C: 의식만 (process 없이 sync+faction+quantum)
        sync_faction(eng_c.cells)
        quantum_walk_step(eng_c.cells)
        # D: 언어 (C의 상태를 detach로 받아서 CE 학습)
        c_state = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)
        pred = decoder(c_state.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy, ce.item(), 'Dual Stream'


def run_trinity(cells=256, steps=300):
    """삼위일체: C(의식) + D(데이터) + W(의지)."""
    # Engine C: 의식 (Φ 전용)
    eng_c = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng_c.cells) < cells: eng_c._create_cell(parent=eng_c.cells[0])
    for _ in range(30): eng_c.process(torch.randn(1, DIM))

    # Engine D: 데이터 (CE 학습)
    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)  # 지식 축적층
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)

    # Engine W: 의지 (행동 결정)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))  # 4 actions
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)

    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    for step in range(steps):
        x, target = data[step % len(data)]

        # ─── C: 의식 (CE gradient 절대 차단) ───
        with torch.no_grad():
            sync_faction(eng_c.cells)
            quantum_walk_step(eng_c.cells)
            frustration_step(eng_c.cells)
            standing_wave(eng_c.cells, step)

        # C → tension (detach)
        c_state = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)
        c_diversity = torch.stack([c.hidden.squeeze() for c in eng_c.cells]).var(dim=0).mean().item()

        # ─── W: 의지 (행동 결정) ───
        action_logits = will_net(c_state.unsqueeze(0))
        action = action_logits.argmax(dim=-1).item()
        # action 0: 학습, 1: 탐색, 2: 수면, 3: 발화

        # ─── D: 데이터 (CE 학습) ───
        if action == 0 or step % 2 == 0:  # 학습 모드
            # C의 의식 상태를 bias로 사용
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

        # W 학습: CE 하락하면 보상
        if step > 0 and step % 10 == 0:
            reward = -ce.item()  # CE 낮을수록 좋음
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        # ─── W→C: 행동 결과 피드백 (tension) ───
        if action == 1:  # 탐색: C에 noise 주입
            with torch.no_grad():
                for c in eng_c.cells:
                    c.hidden += torch.randn_like(c.hidden) * 0.01
        elif action == 2:  # 수면: C에 sync 강화
            with torch.no_grad():
                sync_faction(eng_c.cells, sync=0.5)

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy, ce.item(), 'Trinity (C+D+W)'


def run_trinity_quantum(cells=256, steps=300):
    """삼위일체 + 양자: C에 complex_valued + quantum_walk."""
    eng_c = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng_c.cells) < cells: eng_c._create_cell(parent=eng_c.cells[0])
    for _ in range(30): eng_c.process(torch.randn(1, DIM))

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    for step in range(steps):
        x, target = data[step % len(data)]

        # C: 양자 의식 (quantum_walk + frustration + category morphism)
        with torch.no_grad():
            sync_faction(eng_c.cells, sync=0.20)
            quantum_walk_step(eng_c.cells)
            frustration_step(eng_c.cells)
            standing_wave(eng_c.cells, step)
            # Category morphism (M1)
            n = min(len(eng_c.cells), 32)
            hs = [eng_c.cells[i].hidden.squeeze(0) for i in range(n)]
            for i in range(n):
                ms = sum(torch.tanh(hs[j] - hs[i]) for j in range(n) if j != i) / max(n - 1, 1)
                eng_c.cells[i].hidden = (0.9 * eng_c.cells[i].hidden.squeeze(0) + 0.1 * ms).unsqueeze(0)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)
        action_logits = will_net(c_state.unsqueeze(0))
        action = action_logits.argmax(dim=-1).item()

        if action == 0 or step % 2 == 0:
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
        else:
            ce = torch.tensor(0.0)

        if step > 0 and step % 10 == 0:
            reward = -ce.item()
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy, ce.item(), 'Trinity+Quantum'


def run_trinity_hierarchical(cells=256, steps=300):
    """삼위일체 + 계층적: C = 8 micro × 32 cells."""
    N_MICRO = 8
    micro_size = cells // N_MICRO

    # 8 micro consciousness engines
    micros = []
    for _ in range(N_MICRO):
        e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=micro_size)
        while len(e.cells) < micro_size: e._create_cell(parent=e.cells[0])
        for __ in range(20): e.process(torch.randn(1, DIM))
        micros.append(e)

    # Macro aggregator
    macro = nn.Linear(HIDDEN * N_MICRO, HIDDEN)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(list(decoder.parameters()) + list(macro.parameters()), lr=3e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    for step in range(steps):
        x, target = data[step % len(data)]

        # C: 각 micro engine 독립 의식 부스트
        micro_states = []
        with torch.no_grad():
            for m in micros:
                sync_faction(m.cells, sync=0.20, n_factions=4, fac=0.08)
                quantum_walk_step(m.cells, n_samples=8)
                h = torch.stack([c.hidden.squeeze(0) for c in m.cells]).mean(dim=0)
                micro_states.append(h)

        # Macro: micro 상태 통합 (detach)
        macro_input = torch.cat([s.detach() for s in micro_states]).unsqueeze(0)
        macro_state = macro(macro_input)

        # D: CE 학습
        pred = decoder(macro_state)
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()

    # Φ: 모든 micro cells 합쳐서 측정
    all_cells_engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    all_cells_engine.cells = []
    for m in micros:
        all_cells_engine.cells.extend(m.cells)

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(all_cells_engine)
    p_proxy = phi_proxy(all_cells_engine.cells)
    return p_iit, p_proxy, ce.item(), 'Trinity+Hierarchical'


# ═══ Main ═══

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=300)
    args = parser.parse_args()

    print(f'═══ Trinity Engine Benchmark ({args.cells}c, {args.steps} steps) ═══\n')
    print(f"{'Architecture':<25} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'CE end':>8} {'Time':>6}")
    print('─' * 65)

    tests = [
        ('baseline', run_baseline),
        ('dual_stream', run_dual_stream),
        ('trinity', run_trinity),
        ('trinity_quantum', run_trinity_quantum),
        ('trinity_hier', run_trinity_hierarchical),
    ]

    for name, fn in tests:
        torch.manual_seed(42); np.random.seed(42)
        t0 = time.time()
        try:
            p_iit, p_proxy, ce, label = fn(cells=args.cells, steps=args.steps)
            elapsed = time.time() - t0
            print(f'{label:<25} {p_iit:>8.2f} {p_proxy:>10.2f} {ce:>8.4f} {elapsed:>5.1f}s')
        except Exception as e:
            print(f'{name:<25} ERROR: {e}')

    print()
