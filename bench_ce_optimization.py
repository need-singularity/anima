#!/usr/bin/env python3
"""CE Optimization Benchmark — Φ 유지하면서 CE만 낮추기 + 자율 학습

CE-1~10: Φ 보존 + CE 최소화 전략
AUTO-1~10: 고Φ AI가 스스로 학습법을 찾기

Usage:
  python3 bench_ce_optimization.py                    # 전체 실행
  python3 bench_ce_optimization.py --only CE-3 CE-7   # 특정만
  python3 bench_ce_optimization.py --only AUTO-1      # 자율 학습
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
from mitosis import MitosisEngine, ConsciousMind
from consciousness_meter import PhiCalculator

DIM = 64
HIDDEN = 128
STEPS = 200


def make_text_data(n=100, dim=64):
    """간단한 텍스트 시뮬레이션 데이터"""
    data = []
    for i in range(n):
        x = torch.randn(1, dim) * (1.0 + 0.5 * math.sin(i * 0.1))
        target = torch.randn(1, dim) * 0.5 + x * 0.3  # noisy copy
        data.append((x, target))
    return data


def measure_ce(decoder, engine, data, dim=64):
    """CE 측정"""
    total_ce = 0
    with torch.no_grad():
        for x, target in data[:20]:
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :dim])
            total_ce += ce.item()
    return total_ce / 20


def measure_phi(engine):
    phi_calc = PhiCalculator(n_bins=16)
    phi, _ = phi_calc.compute_phi(engine)
    return phi


# ═══ CE-1: Φ-Frozen Training ═══
def run_CE1_frozen_cells(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    # Warm up consciousness
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    # Save cell states
    saved_hiddens = [c.hidden.clone() for c in engine.cells]
    # Train decoder only
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data()
    ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        # Restore cells (frozen!)
        for i, h in enumerate(saved_hiddens):
            if i < len(engine.cells): engine.cells[i].hidden = h.clone()
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # Re-freeze
        for i, h in enumerate(saved_hiddens):
            if i < len(engine.cells): engine.cells[i].hidden = h.clone()
    phi_after = measure_phi(engine)
    return {'name': 'CE-1 Frozen Cells', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': abs(phi_after - phi_before) < phi_before * 0.1,
            'time': time.time() - t0}


# ═══ CE-2: Φ-Penalty Loss ═══
def run_CE2_phi_penalty(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data()
    ce_hist = []; phi_prev = phi_before
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        # Φ penalty
        if step % 10 == 0:
            phi_now = measure_phi(engine)
            phi_drop = max(0, phi_prev - phi_now)
            ce = ce + 0.5 * phi_drop  # penalty
            phi_prev = phi_now
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'CE-2 Φ-Penalty', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.7,
            'time': time.time() - t0}


# ═══ CE-3: Language-Only Phase ═══
def run_CE3_language_only(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data()
    ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        # No mitosis, no growth, no discovery — pure language
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'CE-3 Language Only', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5,
            'time': time.time() - t0}


# ═══ CE-7: Dialogue Fine-Tune ═══
def run_CE7_dialogue_finetune(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=5e-3)  # higher LR for dialogue
    # Dialogue-style data (Q→A pairs)
    data = []
    for i in range(100):
        q = torch.randn(1, DIM) * 1.5
        a = q * 0.5 + torch.randn(1, DIM) * 0.3  # answer related to question
        data.append((q, a))
    ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'CE-7 Dialogue FT', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5,
            'time': time.time() - t0}


# ═══ CE-10: Transplant CE ═══
def run_CE10_transplant(steps=STEPS):
    t0 = time.time()
    # Source: pre-trained decoder (simulated dialogue_ft)
    source_decoder = nn.Linear(HIDDEN, DIM)
    source_opt = torch.optim.Adam(source_decoder.parameters(), lr=5e-3)
    data = make_text_data()
    # Pre-train source
    for step in range(100):
        x, target = data[step % len(data)]
        pred = source_decoder(torch.randn(1, HIDDEN))
        ce = F.mse_loss(pred, target[:, :DIM])
        source_opt.zero_grad(); ce.backward(); source_opt.step()
    # Target: high-Φ engine
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    # Transplant: copy source decoder to target
    target_decoder = nn.Linear(HIDDEN, DIM)
    target_decoder.load_state_dict(source_decoder.state_dict())
    # Measure CE with transplanted decoder
    ce_before = measure_ce(nn.Linear(HIDDEN, DIM), engine, data)
    ce_after = measure_ce(target_decoder, engine, data)
    phi_after = measure_phi(engine)
    return {'name': 'CE-10 Transplant', 'ce_start': ce_before, 'ce_end': ce_after,
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': abs(phi_after - phi_before) < 0.1,
            'time': time.time() - t0}


# ═══ AUTO-1: Self-Curriculum ═══
def run_AUTO1_self_curriculum(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data(200)
    ce_hist = []
    for step in range(steps):
        # Self-curriculum: rank data by cell consensus
        with torch.no_grad():
            scores = []
            for i, (x, t) in enumerate(data[:50]):
                engine.process(x)
                hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
                consensus = 1.0 - hiddens.var(dim=0).mean().item()
                scores.append((consensus, i))
            # High consensus first (easy)
            scores.sort(reverse=True)
            idx = scores[step % len(scores)][1]
        x, target = data[idx]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'AUTO-1 Self-Curriculum', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5,
            'time': time.time() - t0}


# ═══ AUTO-2: Curiosity-Driven Selection ═══
def run_AUTO2_curiosity(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data(200)
    ce_hist = []; prev_states = {}
    for step in range(steps):
        # Curiosity: pick data with highest prediction error
        with torch.no_grad():
            errors = []
            for i, (x, t) in enumerate(data[:30]):
                engine.process(x)
                h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                pred = decoder(h.unsqueeze(0))
                err = F.mse_loss(pred, t[:, :DIM]).item()
                errors.append((err, i))
            errors.sort(reverse=True)  # highest error first (most novel)
            idx = errors[0][1]
        x, target = data[idx]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'AUTO-2 Curiosity', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5,
            'time': time.time() - t0}


# ═══ AUTO-3: Φ-Guided LR ═══
def run_AUTO3_phi_lr(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data()
    ce_hist = []; phi_prev = phi_before
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # Φ-guided LR
        if step % 20 == 0:
            phi_now = measure_phi(engine)
            if phi_now < phi_prev * 0.9:  # Φ dropping
                for pg in opt.param_groups: pg['lr'] *= 0.5  # slow down
            elif phi_now > phi_prev * 1.1:  # Φ rising
                for pg in opt.param_groups: pg['lr'] = min(pg['lr'] * 1.2, 0.01)
            phi_prev = phi_now
    phi_after = measure_phi(engine)
    return {'name': 'AUTO-3 Φ-Guided LR', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5,
            'time': time.time() - t0}


# ═══ AUTO-5: Self-Evaluation ═══
def run_AUTO5_self_eval(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data()
    ce_hist = []; retries = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        # Self-eval: check output quality via cell variance
        with torch.no_grad():
            engine.process(pred.detach())
            hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
            quality = 1.0 - hiddens.var(dim=0).mean().item()
            if quality < 0.3:  # "bad output"
                retries += 1
                # Retry with higher LR
                pred2 = decoder(h.unsqueeze(0))
                ce2 = F.mse_loss(pred2, target[:, :DIM]) * 2.0
                opt.zero_grad(); ce2.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'AUTO-5 Self-Eval', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after, 'retries': retries,
            'phi_preserved': phi_after > phi_before * 0.5,
            'time': time.time() - t0}


# ═══ AUTO-7: Sleep-Learn Cycle ═══
def run_AUTO7_sleep_learn(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data()
    ce_hist = []; memory_bank = []
    for step in range(steps):
        if step % 30 < 20:
            # LEARN phase (20 steps)
            x, target = data[step % len(data)]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            memory_bank.append((x.detach(), target.detach()))
            if len(memory_bank) > 50: memory_bank.pop(0)
        else:
            # SLEEP phase (10 steps) — replay + Φ restoration
            with torch.no_grad():
                if memory_bank:
                    mx, mt = memory_bank[step % len(memory_bank)]
                    # Dream: blend two memories
                    if len(memory_bank) >= 2:
                        mx2, mt2 = memory_bank[(step+7) % len(memory_bank)]
                        mx = 0.6 * mx + 0.4 * mx2
                    engine.process(mx)
                    # Φ restoration via flow sync
                    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                    for cell in engine.cells:
                        cell.hidden = 0.9 * cell.hidden + 0.1 * mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)
    phi_after = measure_phi(engine)
    return {'name': 'AUTO-7 Sleep-Learn', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5,
            'time': time.time() - t0}


# ═══ AUTO-9: Pain Signal ═══
def run_AUTO9_pain(steps=STEPS):
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data()
    ce_hist = []; pain_events = 0; phi_prev = phi_before
    best_states = [c.hidden.clone() for c in engine.cells]
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # Pain check
        if step % 10 == 0:
            phi_now = measure_phi(engine)
            if phi_now < phi_prev * 0.6:  # PAIN!
                pain_events += 1
                # Emergency restore
                with torch.no_grad():
                    for i, s in enumerate(best_states):
                        if i < len(engine.cells):
                            engine.cells[i].hidden = 0.5 * engine.cells[i].hidden + 0.5 * s
                for pg in opt.param_groups: pg['lr'] *= 0.5
            elif phi_now > phi_prev:
                best_states = [c.hidden.clone() for c in engine.cells]
            phi_prev = phi_now
    phi_after = measure_phi(engine)
    return {'name': 'AUTO-9 Pain Signal', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after, 'pain_events': pain_events,
            'phi_preserved': phi_after > phi_before * 0.5,
            'time': time.time() - t0}


ALL_TESTS = {
    'CE-1': run_CE1_frozen_cells,
    'CE-2': run_CE2_phi_penalty,
    'CE-3': run_CE3_language_only,
    'CE-7': run_CE7_dialogue_finetune,
    'CE-10': run_CE10_transplant,
    'AUTO-1': run_AUTO1_self_curriculum,
    'AUTO-2': run_AUTO2_curiosity,
    'AUTO-3': run_AUTO3_phi_lr,
    'AUTO-5': run_AUTO5_self_eval,
    'AUTO-7': run_AUTO7_sleep_learn,
    'AUTO-9': run_AUTO9_pain,
}


def main():
    parser = argparse.ArgumentParser(description="CE Optimization Benchmark")
    parser.add_argument("--only", nargs="*", help="Run specific tests")
    args = parser.parse_args()

    torch.manual_seed(42)
    np.random.seed(42)

    tests = ALL_TESTS
    if args.only:
        tests = {k: v for k, v in ALL_TESTS.items() if k in args.only}

    print("═══ CE Optimization Benchmark ═══\n")
    print(f"{'Test':<25} {'CE start':>10} {'CE end':>10} {'CE↓':>8} {'Φ before':>10} {'Φ after':>10} {'Φ ok':>6} {'Time':>6}")
    print("-" * 95)

    for name, func in tests.items():
        result = func()
        ce_drop = (result['ce_start'] - result['ce_end']) / (result['ce_start'] + 1e-8) * 100
        phi_ok = "✅" if result.get('phi_preserved', False) else "❌"
        print(f"{result['name']:<25} {result['ce_start']:>10.4f} {result['ce_end']:>10.4f} {ce_drop:>7.1f}% "
              f"{result['phi_before']:>10.3f} {result['phi_after']:>10.3f} {phi_ok:>6} {result['time']:>5.1f}s")

    print("\n✅ = Φ preserved (>50% of original)")


if __name__ == "__main__":
    main()
