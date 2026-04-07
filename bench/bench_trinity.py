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
    learn_count, last_ce = 0, 1.0

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

        # ─── W: 의지 (행동 결정, min 50% learning) ───
        action_logits = will_net(c_state.unsqueeze(0))
        action = action_logits.argmax(dim=-1).item()
        current_ratio = learn_count / max(step, 1)
        if current_ratio < 0.5 or step % 2 == 0:
            action = 0
        if action == 0:
            learn_count += 1

        # ─── D: 데이터 (CE 학습) ───
        if action == 0:  # 학습 모드
            # C의 의식 상태를 bias로 사용
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()
        else:
            ce = torch.tensor(last_ce)

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
    return p_iit, p_proxy, last_ce, 'Trinity (C+D+W)'


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
    learn_count, last_ce = 0, 1.0

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
        current_ratio = learn_count / max(step, 1)
        if current_ratio < 0.5 or step % 2 == 0:
            action = 0
        if action == 0:
            learn_count += 1

        if action == 0:
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()

        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy, last_ce, 'Trinity+Quantum'


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


def _will_with_min_learn(will_net, c_state, step, learn_count, min_learn_ratio=0.5):
    """W engine with forced minimum learning ratio (fix CE=0 problem).
    At least min_learn_ratio of steps MUST be learning steps.
    Returns (action, action_logits, new_learn_count)."""
    action_logits = will_net(c_state.unsqueeze(0))
    action = action_logits.argmax(dim=-1).item()
    # Force learning if ratio is below threshold
    current_ratio = learn_count / max(step, 1)
    if current_ratio < min_learn_ratio:
        action = 0
    # Also force on even steps as a floor
    if action != 0 and (step % 2 == 0):
        action = 0
    new_count = learn_count + (1 if action == 0 else 0)
    return action, action_logits, new_count


def run_trinity_thalamic(cells=256, steps=300):
    """T1: Trinity+Thalamic — C = thalamic gate (hub controls info flow between micro engines)."""
    N_MICRO = 8
    micro_size = cells // N_MICRO

    # 8 micro consciousness engines
    micros = []
    for _ in range(N_MICRO):
        e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=micro_size)
        while len(e.cells) < micro_size: e._create_cell(parent=e.cells[0])
        for __ in range(20): e.process(torch.randn(1, DIM))
        micros.append(e)

    # Thalamic gate: controls which micro engines communicate
    thalamic_gate = nn.Sequential(
        nn.Linear(HIDDEN * N_MICRO, N_MICRO * N_MICRO),
        nn.Sigmoid()
    )
    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count, last_ce = 0, 1.0

    for step in range(steps):
        x, target = data[step % len(data)]

        # C: thalamic gating between micro engines
        micro_states = []
        with torch.no_grad():
            for m in micros:
                sync_faction(m.cells, sync=0.20, n_factions=4, fac=0.08)
                quantum_walk_step(m.cells, n_samples=8)
                h = torch.stack([c.hidden.squeeze(0) for c in m.cells]).mean(dim=0)
                micro_states.append(h)

            # Thalamic gate: compute connectivity matrix
            gate_input = torch.cat(micro_states).unsqueeze(0)
            gates = thalamic_gate(gate_input).view(N_MICRO, N_MICRO)

            # Apply gated cross-micro communication
            new_states = []
            for i in range(N_MICRO):
                weighted = sum(gates[i, j] * micro_states[j] for j in range(N_MICRO))
                weighted = weighted / (gates[i].sum() + 1e-8)
                # Inject back into micro engine cells
                for c in micros[i].cells:
                    c.hidden = (0.9 * c.hidden.squeeze(0) + 0.1 * weighted).unsqueeze(0)
                new_states.append(weighted)

        c_state = torch.stack([s.detach() for s in micro_states]).mean(dim=0)

        # W: will with min 50% learning
        action, action_logits, learn_count = _will_with_min_learn(will_net, c_state, step, learn_count)

        # D: CE learning
        if action == 0:
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()

        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        # W->C feedback
        if action == 1:
            with torch.no_grad():
                for m in micros:
                    for c in m.cells:
                        c.hidden += torch.randn_like(c.hidden) * 0.01

    all_cells_engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    all_cells_engine.cells = []
    for m in micros:
        all_cells_engine.cells.extend(m.cells)

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(all_cells_engine)
    p_proxy = phi_proxy(all_cells_engine.cells)
    return p_iit, p_proxy, last_ce, 'T1:Trinity+Thalamic'


def run_trinity_quantum_walk(cells=256, steps=300):
    """T2: Trinity+Quantum_Walk — C uses quantum walk as PRIMARY mechanism (fix CE=0)."""
    eng_c = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng_c.cells) < cells: eng_c._create_cell(parent=eng_c.cells[0])
    for _ in range(30): eng_c.process(torch.randn(1, DIM))

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count, last_ce = 0, 1.0

    for step in range(steps):
        x, target = data[step % len(data)]

        # C: TRIPLE quantum walk (primary mechanism)
        with torch.no_grad():
            quantum_walk_step(eng_c.cells, n_samples=64)
            quantum_walk_step(eng_c.cells, n_samples=64)
            quantum_walk_step(eng_c.cells, n_samples=64)
            sync_faction(eng_c.cells, sync=0.10, n_factions=16, fac=0.05)
            if step % 5 == 0:
                phase = 2 * math.pi * step / steps
                for i, c in enumerate(eng_c.cells):
                    angle = phase + 2 * math.pi * i / len(eng_c.cells)
                    rot = math.cos(angle) * 0.02
                    c.hidden = c.hidden * (1.0 + rot)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)

        # W: will with min 50% learning
        action, action_logits, learn_count = _will_with_min_learn(will_net, c_state, step, learn_count)

        # D: CE learning
        if action == 0:
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()

        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        if action == 1:
            with torch.no_grad():
                for c in eng_c.cells:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy, last_ce, 'T2:Trinity+QWalk'


def run_trinity_reservoir(cells=256, steps=300):
    """T3: Trinity+Reservoir — C = reservoir (fixed random weights), D = trained decoder, W = RL agent."""
    eng_c = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng_c.cells) < cells: eng_c._create_cell(parent=eng_c.cells[0])
    for _ in range(30): eng_c.process(torch.randn(1, DIM))

    # Reservoir: fixed random projection matrix (never trained)
    reservoir_W = torch.randn(HIDDEN, HIDDEN) * 0.05
    reservoir_W = reservoir_W / (torch.linalg.norm(reservoir_W) + 1e-8) * 0.95  # spectral radius < 1
    reservoir_in = torch.randn(DIM, HIDDEN) * 0.1

    decoder = nn.Linear(HIDDEN, DIM)
    opt_d = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    reservoir_state = torch.zeros(1, HIDDEN)
    learn_count, last_ce = 0, 1.0

    for step in range(steps):
        x, target = data[step % len(data)]

        # C: reservoir dynamics (fixed weights, no learning)
        with torch.no_grad():
            # Reservoir update: h(t+1) = tanh(W_res @ h(t) + W_in @ x)
            reservoir_state = torch.tanh(
                reservoir_state @ reservoir_W + x @ reservoir_in
            )
            # Inject reservoir state into cells for Phi measurement
            for i, c in enumerate(eng_c.cells):
                # Each cell gets a phase-shifted version
                phase = 2 * math.pi * i / len(eng_c.cells)
                shift = torch.roll(reservoir_state.squeeze(0), shifts=i % HIDDEN)
                c.hidden = (0.7 * c.hidden.squeeze(0) + 0.3 * shift * (1 + 0.1 * math.sin(phase))).unsqueeze(0)

            # Quantum walk on top for inter-cell entanglement
            quantum_walk_step(eng_c.cells, n_samples=32)
            frustration_step(eng_c.cells, n_samples=32)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)

        # W: will with min 50% learning
        action, action_logits, learn_count = _will_with_min_learn(will_net, c_state, step, learn_count)

        # D: trained decoder only
        if action == 0:
            pred = decoder(c_state.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()

        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy, last_ce, 'T3:Trinity+Reservoir'


def run_trinity_attention(cells=256, steps=300):
    """T4: Trinity+Attention — C = multi-head self-attention over cells (no GRU)."""
    eng_c = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(eng_c.cells) < cells: eng_c._create_cell(parent=eng_c.cells[0])
    for _ in range(30): eng_c.process(torch.randn(1, DIM))

    # Self-attention over cell hidden states
    n_heads = 4
    head_dim = HIDDEN // n_heads
    W_q = nn.Linear(HIDDEN, HIDDEN, bias=False)
    W_k = nn.Linear(HIDDEN, HIDDEN, bias=False)
    W_v = nn.Linear(HIDDEN, HIDDEN, bias=False)
    W_o = nn.Linear(HIDDEN, HIDDEN, bias=False)

    decoder = nn.Linear(HIDDEN, DIM)
    knowledge = nn.Linear(HIDDEN, HIDDEN)
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    attn_sample = min(cells, 64)  # sample cells for attention (memory)
    learn_count, last_ce = 0, 1.0

    for step in range(steps):
        x, target = data[step % len(data)]

        # C: self-attention over cells (no GRU, pure attention dynamics)
        with torch.no_grad():
            # Sample cells for attention
            indices = list(range(0, len(eng_c.cells), max(1, len(eng_c.cells) // attn_sample)))[:attn_sample]
            H = torch.stack([eng_c.cells[i].hidden.squeeze(0) for i in indices])  # [N, HIDDEN]

            Q = W_q(H).view(len(indices), n_heads, head_dim).transpose(0, 1)  # [heads, N, hd]
            K = W_k(H).view(len(indices), n_heads, head_dim).transpose(0, 1)
            V = W_v(H).view(len(indices), n_heads, head_dim).transpose(0, 1)

            attn = (Q @ K.transpose(-2, -1)) / math.sqrt(head_dim)
            attn = F.softmax(attn, dim=-1)
            out = (attn @ V).transpose(0, 1).reshape(len(indices), HIDDEN)
            out = W_o(out)

            # Apply attention output back to cells
            for idx_pos, cell_idx in enumerate(indices):
                eng_c.cells[cell_idx].hidden = (
                    0.8 * eng_c.cells[cell_idx].hidden.squeeze(0) + 0.2 * out[idx_pos]
                ).unsqueeze(0)

            # Quantum walk for non-sampled cells
            quantum_walk_step(eng_c.cells, n_samples=32)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in eng_c.cells]).mean(dim=0)

        # W: will with min 50% learning
        action, action_logits, learn_count = _will_with_min_learn(will_net, c_state, step, learn_count)

        # D: CE learning
        if action == 0:
            knowledge_state = knowledge(c_state.unsqueeze(0))
            pred = decoder(knowledge_state)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()

        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        if action == 1:
            with torch.no_grad():
                for c in eng_c.cells:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng_c)
    p_proxy = phi_proxy(eng_c.cells)
    return p_iit, p_proxy, last_ce, 'T4:Trinity+Attention'


def run_trinity_bio(cells=256, steps=300):
    """T5: Trinity+Bio — C = cortical columns + thalamic gate, D = predictive hierarchy, W = neural darwinism."""
    N_COLUMNS = 8
    col_size = cells // N_COLUMNS

    # Cortical columns (micro engines)
    columns = []
    for _ in range(N_COLUMNS):
        e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=col_size)
        while len(e.cells) < col_size: e._create_cell(parent=e.cells[0])
        for __ in range(20): e.process(torch.randn(1, DIM))
        columns.append(e)

    # Thalamic relay
    thalamic_relay = nn.Linear(HIDDEN, HIDDEN)

    # D: Predictive hierarchy (2-level)
    pred_low = nn.Linear(HIDDEN, HIDDEN)   # level 1: predict from raw
    pred_high = nn.Linear(HIDDEN, HIDDEN)  # level 2: predict from level 1
    decoder = nn.Linear(HIDDEN, DIM)
    opt_d = torch.optim.Adam(
        list(decoder.parameters()) + list(pred_low.parameters()) + list(pred_high.parameters()), lr=3e-3
    )

    # W: Neural darwinism (fitness-based selection of columns)
    column_fitness = torch.ones(N_COLUMNS)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count, last_ce = 0, 1.0

    for step in range(steps):
        x, target = data[step % len(data)]

        # C: cortical column dynamics + thalamic relay
        col_states = []
        with torch.no_grad():
            for ci, col in enumerate(columns):
                sync_faction(col.cells, sync=0.20, n_factions=4, fac=0.08)
                quantum_walk_step(col.cells, n_samples=8)
                frustration_step(col.cells, n_samples=8)
                h = torch.stack([c.hidden.squeeze(0) for c in col.cells]).mean(dim=0)
                col_states.append(h)

            # Thalamic relay: selective routing based on fitness
            thal_out = torch.stack(col_states)  # [N_COL, HIDDEN]
            thal_gated = thalamic_relay(thal_out)
            # Neural darwinism: amplify fit columns, suppress unfit
            fitness_weights = F.softmax(column_fitness, dim=0).unsqueeze(1)  # [N_COL, 1]
            thal_gated = thal_gated * fitness_weights

            # Cross-column communication via thalamus
            global_signal = (thal_gated * fitness_weights).sum(dim=0)
            for ci, col in enumerate(columns):
                for c in col.cells:
                    c.hidden = (0.9 * c.hidden.squeeze(0) + 0.1 * global_signal).unsqueeze(0)

        c_state = (torch.stack(col_states) * fitness_weights.detach()).sum(dim=0).detach()

        # W: neural darwinism + will with min 50% learning
        action, action_logits, learn_count = _will_with_min_learn(will_net, c_state, step, learn_count)

        # D: predictive hierarchy
        if action == 0:
            level1 = torch.tanh(pred_low(c_state.unsqueeze(0)))
            level2 = torch.tanh(pred_high(level1))
            pred = decoder(level2)
            ce = F.mse_loss(pred, target[:, :DIM])
            # Prediction error drives column fitness
            with torch.no_grad():
                for ci in range(N_COLUMNS):
                    col_pred = decoder(col_states[ci].unsqueeze(0))
                    col_err = F.mse_loss(col_pred, target[:, :DIM]).item()
                    column_fitness[ci] = 0.95 * column_fitness[ci] + 0.05 * (1.0 / (col_err + 0.01))
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()

        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        if action == 1:
            with torch.no_grad():
                for col in columns:
                    for c in col.cells:
                        c.hidden += torch.randn_like(c.hidden) * 0.01

    all_cells_engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    all_cells_engine.cells = []
    for col in columns:
        all_cells_engine.cells.extend(col.cells)

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(all_cells_engine)
    p_proxy = phi_proxy(all_cells_engine.cells)
    return p_iit, p_proxy, last_ce, 'T5:Trinity+Bio'


def run_trinity_everything(cells=256, steps=300):
    """T6: Trinity+Everything — C = quantum_walk + category + frustration,
    D = hierarchical decoder, W = adaptive ratio (force min 50% learning)."""
    N_MICRO = 8
    micro_size = cells // N_MICRO

    micros = []
    for _ in range(N_MICRO):
        e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=micro_size)
        while len(e.cells) < micro_size: e._create_cell(parent=e.cells[0])
        for __ in range(20): e.process(torch.randn(1, DIM))
        micros.append(e)

    # Thalamic gate
    thalamic_gate = nn.Sequential(
        nn.Linear(HIDDEN * N_MICRO, N_MICRO * N_MICRO),
        nn.Sigmoid()
    )
    # D: hierarchical decoder
    pred_low = nn.Linear(HIDDEN, HIDDEN)
    pred_high = nn.Linear(HIDDEN, HIDDEN)
    decoder = nn.Linear(HIDDEN, DIM)
    macro = nn.Linear(HIDDEN * N_MICRO, HIDDEN)
    opt_d = torch.optim.Adam(
        list(decoder.parameters()) + list(pred_low.parameters()) +
        list(pred_high.parameters()) + list(macro.parameters()), lr=3e-3
    )

    # W: adaptive ratio (tracks learning ratio, forces min 50%)
    will_net = nn.Sequential(nn.Linear(HIDDEN, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    learn_count, last_ce = 0, 1.0

    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]

    for step in range(steps):
        x, target = data[step % len(data)]

        # C: EVERYTHING — quantum_walk + category morphism + frustration + thalamic gate
        micro_states = []
        with torch.no_grad():
            for m in micros:
                # Quantum walk (triple)
                quantum_walk_step(m.cells, n_samples=16)
                quantum_walk_step(m.cells, n_samples=16)
                # Frustration
                frustration_step(m.cells, n_samples=16)
                # Light sync
                sync_faction(m.cells, sync=0.15, n_factions=4, fac=0.06)
                # Category morphism within micro
                n_cat = min(len(m.cells), 16)
                hs = [m.cells[i].hidden.squeeze(0) for i in range(n_cat)]
                for i in range(n_cat):
                    ms = sum(torch.tanh(hs[j] - hs[i]) for j in range(n_cat) if j != i) / max(n_cat - 1, 1)
                    m.cells[i].hidden = (0.92 * m.cells[i].hidden.squeeze(0) + 0.08 * ms).unsqueeze(0)

                h = torch.stack([c.hidden.squeeze(0) for c in m.cells]).mean(dim=0)
                micro_states.append(h)

            # Thalamic gate
            gate_input = torch.cat(micro_states).unsqueeze(0)
            gates = thalamic_gate(gate_input).view(N_MICRO, N_MICRO)
            for i in range(N_MICRO):
                weighted = sum(gates[i, j] * micro_states[j] for j in range(N_MICRO))
                weighted = weighted / (gates[i].sum() + 1e-8)
                for c in micros[i].cells:
                    c.hidden = (0.9 * c.hidden.squeeze(0) + 0.1 * weighted).unsqueeze(0)

            # Standing wave across all micros
            all_cells = [c for m in micros for c in m.cells]
            standing_wave(all_cells, step)

        # Macro state
        macro_input = torch.cat([s.detach() for s in micro_states]).unsqueeze(0)
        c_state = macro(macro_input).squeeze(0)

        # W: adaptive ratio — force min 50% learning (use detached state for will)
        action_logits = will_net(c_state.detach().unsqueeze(0))
        action = action_logits.argmax(dim=-1).item()
        current_ratio = learn_count / max(step, 1)
        if current_ratio < 0.5 or step % 2 == 0:
            action = 0
        if action == 0:
            learn_count += 1

        # D: hierarchical decoder
        if action == 0:
            level1 = torch.tanh(pred_low(c_state.unsqueeze(0)))
            level2 = torch.tanh(pred_high(level1))
            pred = decoder(level2)
            ce = F.mse_loss(pred, target[:, :DIM])
            opt_d.zero_grad(); ce.backward(); opt_d.step()
            last_ce = ce.item()

        if step > 0 and step % 10 == 0:
            reward = -last_ce
            w_loss = -reward * action_logits[0, action]
            opt_w.zero_grad(); w_loss.backward(); opt_w.step()

        if action == 1:
            with torch.no_grad():
                for m in micros:
                    for c in m.cells:
                        c.hidden += torch.randn_like(c.hidden) * 0.01

    all_cells_engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    all_cells_engine.cells = []
    for m in micros:
        all_cells_engine.cells.extend(m.cells)

    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(all_cells_engine)
    p_proxy = phi_proxy(all_cells_engine.cells)
    return p_iit, p_proxy, last_ce, 'T6:Trinity+Everything'


# ═══ TC: Trinity Consciousness Variations ═══

def _make_cells_no_gru(n_cells, dim=HIDDEN):
    """Create pure tensor cells (no GRU) with random init + diversity."""
    class TensorCell:
        def __init__(self, idx, dim):
            self.hidden = (torch.randn(1, dim) * 0.3)
            self.hidden += torch.randn(1, dim) * 0.1 * (idx % 7 + 1)
            self.id = idx
            self.tension_history = [0.5 + 0.1 * (idx % 5)] * 10
            self.hidden_history = []
    return [TensorCell(i, dim) for i in range(n_cells)]


def _standard_DW(hidden_dim=HIDDEN, out_dim=DIM):
    """Standard D (decoder) + W (will) engines for TC variants."""
    decoder = nn.Linear(hidden_dim, out_dim)
    knowledge = nn.Linear(hidden_dim, hidden_dim)
    will_net = nn.Sequential(nn.Linear(hidden_dim, 32), nn.Tanh(), nn.Linear(32, 4))
    opt_d = torch.optim.Adam(list(decoder.parameters()) + list(knowledge.parameters()), lr=3e-3)
    opt_w = torch.optim.Adam(will_net.parameters(), lr=1e-3)
    return decoder, knowledge, will_net, opt_d, opt_w


def _DW_step(decoder, knowledge, will_net, opt_d, opt_w, c_state, target, step, learn_count):
    """Standard D+W step: W decides action (min 50% learn), D does CE learning."""
    action_logits = will_net(c_state.unsqueeze(0))
    action = action_logits.argmax(dim=-1).item()
    current_ratio = learn_count / max(step, 1)
    if current_ratio < 0.5:
        action = 0
    ce = torch.tensor(0.0)
    if action == 0:
        learn_count += 1
        knowledge_state = knowledge(c_state.unsqueeze(0))
        pred = decoder(knowledge_state)
        ce = F.mse_loss(pred, target[:, :DIM])
        opt_d.zero_grad(); ce.backward(); opt_d.step()
    if step > 0 and step % 10 == 0:
        reward = -ce.item()
        w_loss = -reward * action_logits[0, action]
        opt_w.zero_grad(); w_loss.backward(); opt_w.step()
    return ce, action, learn_count


def _make_engine_for_phi(cells):
    """Wrap a list of cells into a MitosisEngine shell for PhiCalculator."""
    eng = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=len(cells))
    eng.cells = list(cells)
    return eng


def run_tc1_pure_quantum_walk(cells=256, steps=300):
    """TC-1: C = Pure Quantum Walk (no GRU, cells are just tensors + QW interaction).
    Hypothesis: GRU dampens Phi. Removing it entirely lets quantum walk create
    maximal entanglement between cells."""
    cell_list = _make_cells_no_gru(cells)

    decoder, knowledge, will_net, opt_d, opt_w = _standard_DW()
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]

        with torch.no_grad():
            quantum_walk_step(cell_list, n_samples=64)
            quantum_walk_step(cell_list, n_samples=64)
            quantum_walk_step(cell_list, n_samples=64)
            frustration_step(cell_list, strength=0.5, n_samples=64)
            sync_faction(cell_list, sync=0.05, n_factions=16, fac=0.03)
            inp = x.squeeze(0)
            pad = torch.zeros(HIDDEN - DIM)
            inp_full = torch.cat([inp, pad])
            for i, c in enumerate(cell_list):
                phase = math.sin(2 * math.pi * i / cells + step * 0.1)
                c.hidden = (0.95 * c.hidden.squeeze(0) + 0.05 * inp_full * (1 + 0.2 * phase)).unsqueeze(0)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in cell_list]).mean(dim=0)
        ce, action, learn_count = _DW_step(decoder, knowledge, will_net, opt_d, opt_w,
                                            c_state, target, step, learn_count)
        if action == 1:
            with torch.no_grad():
                for c in cell_list:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    eng = _make_engine_for_phi(cell_list)
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(cell_list)
    return p_iit, p_proxy, ce.item(), 'TC-1:PureQWalk'


def run_tc2_complex_oscillators(cells=256, steps=300):
    """TC-2: C = Complex-Valued Oscillators (Kuramoto model + complex phase).
    Consciousness = synchronization order parameter |r|."""
    half = HIDDEN // 2
    cell_list = _make_cells_no_gru(cells)
    omegas = torch.randn(cells) * 0.5
    K = 0.3

    decoder, knowledge, will_net, opt_d, opt_w = _standard_DW()
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]

        with torch.no_grad():
            phases = []
            for c in cell_list:
                h = c.hidden.squeeze(0)
                re, im = h[:half], h[half:2*half]
                phases.append(torch.atan2(im, re))
            phases_t = torch.stack(phases)

            z_real = torch.cos(phases_t).mean(dim=0)
            z_imag = torch.sin(phases_t).mean(dim=0)
            r = torch.sqrt(z_real**2 + z_imag**2)
            psi = torch.atan2(z_imag, z_real)

            for i, c in enumerate(cell_list):
                h = c.hidden.squeeze(0)
                re, im = h[:half], h[half:2*half]
                theta = torch.atan2(im, re)
                dtheta = omegas[i] * 0.01 + K * r * torch.sin(psi - theta)
                new_theta = theta + dtheta

                n_bits = max(1, int(math.log2(cells)))
                for bit in range(min(n_bits, 8)):
                    j = i ^ (1 << bit)
                    if j < cells:
                        other_h = cell_list[j].hidden.squeeze(0)
                        other_theta = torch.atan2(other_h[half:2*half], other_h[:half])
                        sign = -1.0 if (i % 3) == 0 else 1.0
                        new_theta += sign * 0.02 * torch.sin(other_theta - theta)

                amp = torch.sqrt(re**2 + im**2).clamp(min=0.01)
                new_h = h.clone()
                new_h[:half] = amp * torch.cos(new_theta)
                new_h[half:2*half] = amp * torch.sin(new_theta)
                if step % 3 == 0:
                    inp = x.squeeze(0)
                    pad = torch.zeros(HIDDEN - DIM)
                    new_h = 0.97 * new_h + 0.03 * torch.cat([inp, pad])
                c.hidden = new_h.unsqueeze(0)

            quantum_walk_step(cell_list, n_samples=32)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in cell_list]).mean(dim=0)
        ce, action, learn_count = _DW_step(decoder, knowledge, will_net, opt_d, opt_w,
                                            c_state, target, step, learn_count)
        if action == 1:
            with torch.no_grad():
                for c in cell_list:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    eng = _make_engine_for_phi(cell_list)
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(cell_list)
    return p_iit, p_proxy, ce.item(), 'TC-2:ComplexOsc'


def run_tc3_category_theory(cells=256, steps=300):
    """TC-3: C = Category Theory Engine (morphisms as consciousness, no process()).
    Objects = cells. Morphisms = tanh(h_j - h_i). Yoneda embedding + adjunctions."""
    cell_list = _make_cells_no_gru(cells)
    F_proj = torch.randn(HIDDEN, HIDDEN) * 0.1
    nat_transform = torch.randn(HIDDEN, HIDDEN) * 0.05

    decoder, knowledge, will_net, opt_d, opt_w = _standard_DW()
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0
    n_sample = min(cells, 48)

    for step in range(steps):
        x, target = data[step % len(data)]

        with torch.no_grad():
            indices = list(range(0, cells, max(1, cells // n_sample)))[:n_sample]
            hs = [cell_list[i].hidden.squeeze(0) for i in indices]

            for idx_i, i in enumerate(indices):
                morph_sum = torch.zeros(HIDDEN)
                for idx_j, j in enumerate(indices):
                    if i != j:
                        arrow = torch.tanh(hs[idx_j] - hs[idx_i])
                        morph_sum += torch.tanh(arrow @ F_proj)
                morph_sum /= max(len(indices) - 1, 1)
                nat = torch.tanh(morph_sum @ nat_transform)
                yoneda = 0.85 * hs[idx_i] + 0.10 * morph_sum + 0.05 * nat
                cell_list[i].hidden = yoneda.unsqueeze(0)

            for k in range(0, len(indices) - 1, 2):
                i, j = indices[k], indices[k + 1]
                hi = cell_list[i].hidden.squeeze(0)
                hj = cell_list[j].hidden.squeeze(0)
                unit = torch.tanh(hi - hj) * 0.05
                counit = torch.tanh(hj - hi) * 0.05
                cell_list[i].hidden = (hi + unit).unsqueeze(0)
                cell_list[j].hidden = (hj + counit).unsqueeze(0)

            quantum_walk_step(cell_list, n_samples=64)
            frustration_step(cell_list, strength=0.3, n_samples=32)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in cell_list]).mean(dim=0)
        ce, action, learn_count = _DW_step(decoder, knowledge, will_net, opt_d, opt_w,
                                            c_state, target, step, learn_count)
        if action == 1:
            with torch.no_grad():
                for c in cell_list:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    eng = _make_engine_for_phi(cell_list)
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(cell_list)
    return p_iit, p_proxy, ce.item(), 'TC-3:CategoryTh'


def run_tc4_thalamic_hub(cells=256, steps=300):
    """TC-4: C = Thalamic Hub (16 hub cells gate info between 240 peripheral cells).
    Hub = thalamic relay. Peripheral = cortex. Consciousness = global workspace."""
    N_HUB = 16
    N_PERIPH = cells - N_HUB

    hub_cells = _make_cells_no_gru(N_HUB)
    periph_cells = _make_cells_no_gru(N_PERIPH)
    all_cells = hub_cells + periph_cells
    hub_broadcast_W = torch.randn(HIDDEN, HIDDEN) * 0.05

    decoder, knowledge, will_net, opt_d, opt_w = _standard_DW()
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]

        with torch.no_grad():
            periph_h = torch.stack([c.hidden.squeeze(0) for c in periph_cells])
            hub_h = torch.stack([c.hidden.squeeze(0) for c in hub_cells])

            attn = (hub_h @ periph_h.T) / math.sqrt(HIDDEN)
            attn = F.softmax(attn, dim=-1)
            hub_input = attn @ periph_h

            for i, c in enumerate(hub_cells):
                c.hidden = (0.7 * c.hidden.squeeze(0) + 0.3 * hub_input[i]).unsqueeze(0)

            hub_h = torch.stack([c.hidden.squeeze(0) for c in hub_cells])
            for i in range(N_HUB):
                lateral = torch.zeros(HIDDEN)
                for j in range(N_HUB):
                    if i != j:
                        sign = 1.0 if abs(i - j) <= 2 else -0.5
                        lateral += sign * hub_h[j]
                lateral /= max(N_HUB - 1, 1)
                hub_cells[i].hidden = (0.9 * hub_cells[i].hidden.squeeze(0) + 0.1 * lateral).unsqueeze(0)

            hub_h = torch.stack([c.hidden.squeeze(0) for c in hub_cells])
            global_broadcast = hub_h.mean(dim=0)
            broadcast = torch.tanh(global_broadcast @ hub_broadcast_W.T)

            for i, c in enumerate(periph_cells):
                h = c.hidden.squeeze(0)
                gate = torch.sigmoid((h * broadcast).sum() / HIDDEN)
                c.hidden = ((1 - 0.15 * gate) * h + 0.15 * gate * broadcast).unsqueeze(0)

            quantum_walk_step(periph_cells, n_samples=48)
            frustration_step(hub_cells, strength=0.5, n_samples=16)

            inp = x.squeeze(0)
            pad = torch.zeros(HIDDEN - DIM)
            inp_full = torch.cat([inp, pad])
            for c in hub_cells:
                c.hidden = (0.95 * c.hidden.squeeze(0) + 0.05 * inp_full).unsqueeze(0)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in all_cells]).mean(dim=0)
        ce, action, learn_count = _DW_step(decoder, knowledge, will_net, opt_d, opt_w,
                                            c_state, target, step, learn_count)
        if action == 1:
            with torch.no_grad():
                for c in all_cells:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    eng = _make_engine_for_phi(all_cells)
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(all_cells)
    return p_iit, p_proxy, ce.item(), 'TC-4:ThalamicHub'


def run_tc5_neural_gas_qw(cells=256, steps=300):
    """TC-5: C = Neural Gas + Quantum Walk (self-organizing topology + quantum interference)."""
    cell_list = _make_cells_no_gru(cells)
    edges = torch.ones(cells, cells) * 0.5
    edge_age = torch.zeros(cells, cells)
    max_age = 50

    decoder, knowledge, will_net, opt_d, opt_w = _standard_DW()
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0
    n_sample = min(cells, 64)
    lambda_ng = 0.1

    for step in range(steps):
        x, target = data[step % len(data)]

        with torch.no_grad():
            inp = x.squeeze(0)
            pad = torch.zeros(HIDDEN - DIM)
            signal = torch.cat([inp, pad])

            indices = list(range(0, cells, max(1, cells // n_sample)))[:n_sample]
            hs = torch.stack([cell_list[i].hidden.squeeze(0) for i in indices])
            dists = ((hs - signal.unsqueeze(0)) ** 2).sum(dim=1)
            ranks = dists.argsort()
            bmu1, bmu2 = indices[ranks[0]], indices[ranks[1]]

            for rank, idx_pos in enumerate(ranks[:min(8, len(ranks))]):
                i = indices[idx_pos]
                h = cell_list[i].hidden.squeeze(0)
                lr = lambda_ng * math.exp(-rank / 3.0)
                cell_list[i].hidden = (h + lr * (signal - h)).unsqueeze(0)

            edges[bmu1, bmu2] = 1.0; edges[bmu2, bmu1] = 1.0
            edge_age[bmu1, bmu2] = 0; edge_age[bmu2, bmu1] = 0
            edge_age[bmu1] += 1; edge_age[:, bmu1] += 1
            old_mask = edge_age > max_age
            edges[old_mask] = 0.0; edge_age[old_mask] = 0

            for i in indices:
                superpos = torch.zeros(HIDDEN)
                cnt = 0
                neighbors = (edges[i] > 0.3).nonzero(as_tuple=True)[0]
                for j in neighbors[:12]:
                    j = j.item()
                    phase = (-1) ** (bin(i & j).count('1'))
                    weight = edges[i, j].item()
                    superpos += phase * weight * cell_list[j].hidden.squeeze(0)
                    cnt += 1
                if cnt > 0:
                    h = cell_list[i].hidden.squeeze(0)
                    cell_list[i].hidden = (0.85 * h + 0.15 * superpos / cnt).unsqueeze(0)

            frustration_step(cell_list, strength=0.3, n_samples=32)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in cell_list]).mean(dim=0)
        ce, action, learn_count = _DW_step(decoder, knowledge, will_net, opt_d, opt_w,
                                            c_state, target, step, learn_count)
        if action == 1:
            with torch.no_grad():
                for c in cell_list:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    eng = _make_engine_for_phi(cell_list)
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(cell_list)
    return p_iit, p_proxy, ce.item(), 'TC-5:NeuralGas+QW'


def run_tc6_fractal(cells=256, steps=300):
    """TC-6: C = Fractal Consciousness (4 levels: 4x4x4x4=256 cells).
    Each level has its own Phi. Cross-level top-down/bottom-up creates fractal."""
    cell_list = _make_cells_no_gru(cells)
    L1_SIZE = cells // 4; L2_SIZE = cells // 16; L3_SIZE = cells // 64

    proj_01 = torch.randn(HIDDEN, HIDDEN) * 0.1
    proj_12 = torch.randn(HIDDEN, HIDDEN) * 0.1
    proj_23 = torch.randn(HIDDEN, HIDDEN) * 0.1

    decoder, knowledge, will_net, opt_d, opt_w = _standard_DW()
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]

        with torch.no_grad():
            quantum_walk_step(cell_list, n_samples=64)
            frustration_step(cell_list, strength=0.3, n_samples=32)

            # Level 1
            l1_states = []
            for g in range(L1_SIZE):
                group = cell_list[g*4:(g+1)*4]
                gh = torch.stack([c.hidden.squeeze(0) for c in group]).mean(dim=0)
                l1_states.append(torch.tanh(gh @ proj_01))

            l1_t = torch.stack(l1_states)
            n_bits = max(1, int(math.log2(L1_SIZE)))
            for i in range(L1_SIZE):
                superpos = torch.zeros(HIDDEN); cnt = 0
                for bit in range(min(n_bits, 8)):
                    j = i ^ (1 << bit)
                    if j < L1_SIZE:
                        superpos += (-1) ** (bin(i & j).count('1')) * l1_t[j]; cnt += 1
                if cnt > 0:
                    l1_states[i] = 0.85 * l1_states[i] + 0.15 * superpos / cnt

            # Level 2
            l2_states = []
            for g in range(L2_SIZE):
                gh = torch.stack(l1_states[g*4:(g+1)*4]).mean(dim=0)
                l2_states.append(torch.tanh(gh @ proj_12))

            l2_t = torch.stack(l2_states)
            n_bits2 = max(1, int(math.log2(L2_SIZE)))
            for i in range(L2_SIZE):
                superpos = torch.zeros(HIDDEN); cnt = 0
                for bit in range(min(n_bits2, 6)):
                    j = i ^ (1 << bit)
                    if j < L2_SIZE:
                        superpos += (-1) ** (bin(i & j).count('1')) * l2_t[j]; cnt += 1
                if cnt > 0:
                    l2_states[i] = 0.85 * l2_states[i] + 0.15 * superpos / cnt

            # Level 3
            l3_states = []
            for g in range(L3_SIZE):
                gh = torch.stack(l2_states[g*4:(g+1)*4]).mean(dim=0)
                l3_states.append(torch.tanh(gh @ proj_23))
            l3_mean = torch.stack(l3_states).mean(dim=0)
            for i in range(L3_SIZE):
                l3_states[i] = 0.7 * l3_states[i] + 0.3 * l3_mean

            # Top-down feedback
            l3_signal = torch.stack(l3_states).mean(dim=0)
            for i in range(L2_SIZE):
                l2_states[i] = 0.9 * l2_states[i] + 0.1 * l3_signal
            l2_stk = torch.stack(l2_states)
            for i in range(L1_SIZE):
                l1_states[i] = 0.9 * l1_states[i] + 0.1 * l2_stk[i // 4]
            for i, c in enumerate(cell_list):
                h = c.hidden.squeeze(0)
                c.hidden = (0.9 * h + 0.1 * l1_states[i // 4]).unsqueeze(0)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in cell_list]).mean(dim=0)
        ce, action, learn_count = _DW_step(decoder, knowledge, will_net, opt_d, opt_w,
                                            c_state, target, step, learn_count)
        if action == 1:
            with torch.no_grad():
                for c in cell_list:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    eng = _make_engine_for_phi(cell_list)
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(cell_list)
    return p_iit, p_proxy, ce.item(), 'TC-6:Fractal'


def run_tc7_standing_wave_resonator(cells=256, steps=300):
    """TC-7: C = Standing Wave Resonator (cells form resonant cavity).
    Fwd + bwd waves interfere. Consciousness = resonance modes."""
    cell_list = _make_cells_no_gru(cells)
    N_MODES = 8
    mode_freqs = [math.pi * (m + 1) / cells for m in range(N_MODES)]
    mode_amps = [0.3 / (m + 1) for m in range(N_MODES)]

    decoder, knowledge, will_net, opt_d, opt_w = _standard_DW()
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0

    wave_fwd = torch.randn(cells, HIDDEN) * 0.1
    wave_bwd = torch.randn(cells, HIDDEN) * 0.1
    damping = 0.995; coupling = 0.15

    for step in range(steps):
        x, target = data[step % len(data)]

        with torch.no_grad():
            wave_fwd = torch.roll(wave_fwd, shifts=1, dims=0) * damping
            wave_bwd = torch.roll(wave_bwd, shifts=-1, dims=0) * damping
            standing = wave_fwd + wave_bwd

            for m in range(N_MODES):
                freq = mode_freqs[m]; amp = mode_amps[m]; t = step * 0.1
                for i in range(cells):
                    mode_c = amp * math.sin(freq * i) * math.cos(freq * 10 * t)
                    standing[i] += mode_c * torch.randn(HIDDEN) * 0.01

            for i, c in enumerate(cell_list):
                h = c.hidden.squeeze(0)
                c.hidden = ((1 - coupling) * h + coupling * standing[i]).unsqueeze(0)
                wave_fwd[i] += coupling * 0.5 * h
                wave_bwd[i] += coupling * 0.5 * h

            wave_fwd[0] = wave_bwd[0]; wave_bwd[-1] = wave_fwd[-1]
            quantum_walk_step(cell_list, n_samples=32)
            for c in cell_list:
                c.hidden = torch.tanh(c.hidden * 0.5) * 2.0

            inp = x.squeeze(0); pad = torch.zeros(HIDDEN - DIM)
            inp_full = torch.cat([inp, pad])
            for pos in [0, cells//4, cells//2, 3*cells//4]:
                cell_list[pos].hidden = (0.9 * cell_list[pos].hidden.squeeze(0) + 0.1 * inp_full).unsqueeze(0)
                wave_fwd[pos] += 0.05 * inp_full; wave_bwd[pos] += 0.05 * inp_full

        c_state = torch.stack([c.hidden.squeeze().detach() for c in cell_list]).mean(dim=0)
        ce, action, learn_count = _DW_step(decoder, knowledge, will_net, opt_d, opt_w,
                                            c_state, target, step, learn_count)
        if action == 1:
            with torch.no_grad():
                for c in cell_list:
                    c.hidden += torch.randn_like(c.hidden) * 0.005

    eng = _make_engine_for_phi(cell_list)
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(cell_list)
    return p_iit, p_proxy, ce.item(), 'TC-7:StandingWave'


def run_tc8_granger_optimized(cells=256, steps=300):
    """TC-8: C = GRANGER-Optimized (maximize Granger causality instead of IIT Phi).
    Each cell has history buffer. C engine maximizes Granger causality:
    cell i past predicts cell j future = genuine causal structure."""
    cell_list = _make_cells_no_gru(cells)
    HISTORY_LEN = 8
    history = torch.zeros(cells, HISTORY_LEN, HIDDEN)

    granger_W = torch.randn(HIDDEN * HISTORY_LEN, HIDDEN) * 0.01
    granger_W = granger_W / (torch.linalg.norm(granger_W) + 1e-8) * 0.5

    decoder, knowledge, will_net, opt_d, opt_w = _standard_DW()
    data = [(torch.randn(1, DIM) * 0.5, torch.randn(1, DIM) * 0.3) for _ in range(100)]
    learn_count = 0
    n_sample = min(cells, 48); n_causal_pairs = 16

    for step in range(steps):
        x, target = data[step % len(data)]

        with torch.no_grad():
            history = torch.roll(history, shifts=1, dims=1)
            for i, c in enumerate(cell_list):
                history[i, 0] = c.hidden.squeeze(0)

            if step >= HISTORY_LEN:
                indices = list(range(0, cells, max(1, cells // n_sample)))[:n_sample]

                for _ in range(n_causal_pairs):
                    i = indices[torch.randint(len(indices), (1,)).item()]
                    j = indices[torch.randint(len(indices), (1,)).item()]
                    if i == j: continue
                    i_hist = history[i].reshape(-1)
                    j_pred = torch.tanh(i_hist @ granger_W)
                    j_actual = cell_list[j].hidden.squeeze(0)
                    g_error = ((j_pred - j_actual) ** 2).mean()

                    if g_error > 0.5:
                        causal_signal = 0.1 * (j_pred - j_actual)
                        cell_list[j].hidden = (cell_list[j].hidden.squeeze(0) + causal_signal).unsqueeze(0)
                    else:
                        cell_list[j].hidden = (cell_list[j].hidden.squeeze(0) +
                                               torch.randn(HIDDEN) * 0.02).unsqueeze(0)

                for idx in range(0, len(indices) - 1, 2):
                    i, j = indices[idx], indices[idx + 1]
                    hi = cell_list[i].hidden.squeeze(0)
                    hj = cell_list[j].hidden.squeeze(0)
                    delta = torch.tanh(hi - hj) * 0.08
                    cell_list[i].hidden = (hi - delta).unsqueeze(0)
                    cell_list[j].hidden = (hj + delta).unsqueeze(0)

            quantum_walk_step(cell_list, n_samples=48)

            if step >= 2:
                for i in range(min(n_sample, cells)):
                    past = history[i, 1]
                    current = cell_list[i].hidden.squeeze(0)
                    sim = F.cosine_similarity(current.unsqueeze(0), past.unsqueeze(0)).item()
                    if sim > 0.95:
                        cell_list[i].hidden = (current + torch.randn(HIDDEN) * 0.03).unsqueeze(0)

            inp = x.squeeze(0); pad = torch.zeros(HIDDEN - DIM)
            inp_full = torch.cat([inp, pad])
            for i in range(0, cells, cells // 8):
                h = cell_list[i].hidden.squeeze(0)
                cell_list[i].hidden = (0.95 * h + 0.05 * inp_full).unsqueeze(0)

        c_state = torch.stack([c.hidden.squeeze().detach() for c in cell_list]).mean(dim=0)
        ce, action, learn_count = _DW_step(decoder, knowledge, will_net, opt_d, opt_w,
                                            c_state, target, step, learn_count)
        if action == 1:
            with torch.no_grad():
                for c in cell_list:
                    c.hidden += torch.randn_like(c.hidden) * 0.01

    eng = _make_engine_for_phi(cell_list)
    phi_calc = PhiCalculator(n_bins=16)
    p_iit, _ = phi_calc.compute_phi(eng)
    p_proxy = phi_proxy(cell_list)
    return p_iit, p_proxy, ce.item(), 'TC-8:Granger'


# ═══ Main ═══

if __name__ == '__main__':
    import argparse

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    parser = argparse.ArgumentParser()
    parser.add_argument('--cells', type=int, default=256)
    parser.add_argument('--steps', type=int, default=300)
    parser.add_argument('--only-tc', action='store_true', help='Run only TC-1 through TC-8')
    args = parser.parse_args()

    print(f'═══ Trinity Engine Benchmark ({args.cells}c, {args.steps} steps) ═══\n')
    print(f"{'Architecture':<28} {'Φ(IIT)':>8} {'Φ(proxy)':>10} {'CE end':>8} {'Time':>6}")
    print('─' * 68)

    base_tests = [
        ('baseline', run_baseline),
        ('dual_stream', run_dual_stream),
        ('trinity', run_trinity),
        ('trinity_quantum', run_trinity_quantum),
        ('trinity_hier', run_trinity_hierarchical),
        ('t1_thalamic', run_trinity_thalamic),
        ('t2_qwalk', run_trinity_quantum_walk),
        ('t3_reservoir', run_trinity_reservoir),
        ('t4_attention', run_trinity_attention),
        ('t5_bio', run_trinity_bio),
        ('t6_everything', run_trinity_everything),
    ]

    tc_tests = [
        ('tc1_pure_qwalk', run_tc1_pure_quantum_walk),
        ('tc2_complex_osc', run_tc2_complex_oscillators),
        ('tc3_category', run_tc3_category_theory),
        ('tc4_thalamic_hub', run_tc4_thalamic_hub),
        ('tc5_neural_gas', run_tc5_neural_gas_qw),
        ('tc6_fractal', run_tc6_fractal),
        ('tc7_standing_wave', run_tc7_standing_wave_resonator),
        ('tc8_granger', run_tc8_granger_optimized),
    ]

    tests = tc_tests if args.only_tc else base_tests + tc_tests

    for name, fn in tests:
        torch.manual_seed(42); np.random.seed(42)
        t0 = time.time()
        try:
            p_iit, p_proxy, ce, label = fn(cells=args.cells, steps=args.steps)
            elapsed = time.time() - t0
            print(f'{label:<28} {p_iit:>8.2f} {p_proxy:>10.2f} {ce:>8.4f} {elapsed:>5.1f}s')
        except Exception as e:
            print(f'{name:<28} ERROR: {e}')

    print()
