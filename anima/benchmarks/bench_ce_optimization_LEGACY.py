# ⚠️ LEGACY — 이 파일은 폐기되었습니다 (2026-03-29)
# Φ(IIT)와 Φ(proxy)를 혼용하여 잘못된 기록 생성.
# "Φ=1142"는 proxy 값이었음 (실제 IIT Φ 상한 ~1.8)
# 새 벤치마크: bench_v2.py (Φ(IIT) + Φ(proxy) 이중 측정)
# Law 54: Φ 측정은 정의에 따라 완전히 다른 값
#
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

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


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


# ═══ EXTREME: 승리 전략 결합 + 새로운 극한 ═══

def run_COMBO1_curiosity_sleep_pain(steps=STEPS):
    """TOP 3 결합: 호기심 + 수면 + 고통"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data(200)
    ce_hist = []; memory = []; best_states = [c.hidden.clone() for c in engine.cells]
    best_phi = phi_before; pain = 0
    for step in range(steps):
        cycle = step % 30
        if cycle < 20:
            # LEARN: curiosity-driven selection
            with torch.no_grad():
                errors = []
                for i, (x, t) in enumerate(data[:30]):
                    engine.process(x)
                    h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                    err = F.mse_loss(decoder(h.unsqueeze(0)), t[:, :DIM]).item()
                    errors.append((err, i))
                errors.sort(reverse=True)
                idx = errors[0][1]
            x, target = data[idx]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            memory.append((x.detach(), target.detach()))
            if len(memory) > 50: memory.pop(0)
            # Pain check
            if step % 10 == 0:
                phi_now = measure_phi(engine)
                if phi_now < best_phi * 0.6:
                    pain += 1
                    with torch.no_grad():
                        for i, s in enumerate(best_states):
                            if i < len(engine.cells):
                                engine.cells[i].hidden = 0.5*engine.cells[i].hidden + 0.5*s
                    for pg in opt.param_groups: pg['lr'] *= 0.7
                elif phi_now > best_phi:
                    best_phi = phi_now
                    best_states = [c.hidden.clone() for c in engine.cells]
        else:
            # SLEEP: replay + Φ restore
            with torch.no_grad():
                if memory:
                    mx, mt = memory[step % len(memory)]
                    if len(memory) >= 2:
                        mx2, _ = memory[(step+7) % len(memory)]
                        mx = 0.6*mx + 0.4*mx2
                    engine.process(mx)
                    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                    for cell in engine.cells:
                        cell.hidden = 0.9*cell.hidden + 0.1*mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)
    phi_after = measure_phi(engine)
    return {'name': 'COMBO-1 Curiosity+Sleep+Pain', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after, 'pain': pain,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_COMBO2_all_auto(steps=STEPS):
    """모든 AUTO 기법 동시 적용"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_text_data(200)
    ce_hist = []; memory = []; best_states = [c.hidden.clone() for c in engine.cells]
    best_phi = phi_before; phi_prev = phi_before
    for step in range(steps):
        cycle = step % 40
        if cycle < 28:
            # LEARN with curiosity + self-eval
            with torch.no_grad():
                errors = []
                for i, (x, t) in enumerate(data[:20]):
                    engine.process(x)
                    h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                    err = F.mse_loss(decoder(h.unsqueeze(0)), t[:, :DIM]).item()
                    errors.append((err, i))
                errors.sort(reverse=True)
                idx = errors[0][1]
            x, target = data[idx]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            # Self-eval retry
            with torch.no_grad():
                engine.process(pred.detach())
                quality = 1.0 - torch.stack([c.hidden.squeeze() for c in engine.cells]).var(dim=0).mean().item()
                if quality < 0.3:
                    ce = ce * 2.0
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            memory.append((x.detach(), target.detach()))
            if len(memory) > 50: memory.pop(0)
            # Φ-guided LR + pain
            if step % 10 == 0:
                phi_now = measure_phi(engine)
                if phi_now < best_phi * 0.6:
                    with torch.no_grad():
                        for i, s in enumerate(best_states):
                            if i < len(engine.cells):
                                engine.cells[i].hidden = 0.5*engine.cells[i].hidden + 0.5*s
                    for pg in opt.param_groups: pg['lr'] *= 0.5
                elif phi_now < phi_prev * 0.9:
                    for pg in opt.param_groups: pg['lr'] *= 0.8
                elif phi_now > best_phi:
                    best_phi = phi_now
                    best_states = [c.hidden.clone() for c in engine.cells]
                    for pg in opt.param_groups: pg['lr'] = min(pg['lr']*1.1, 0.01)
                phi_prev = phi_now
        else:
            # SLEEP
            with torch.no_grad():
                if memory:
                    mx, _ = memory[step % len(memory)]
                    engine.process(mx)
                    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                    for cell in engine.cells:
                        cell.hidden = 0.9*cell.hidden + 0.1*mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)
    phi_after = measure_phi(engine)
    return {'name': 'COMBO-2 ALL AUTO', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_EX1_adversarial_self_teach(steps=STEPS):
    """적대적 자기교육: 디코더 A가 생성, 디코더 B가 평가, 의식이 심판"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    gen = nn.Linear(HIDDEN, DIM)  # generator
    disc = nn.Linear(DIM, 1)  # discriminator
    opt_g = torch.optim.Adam(gen.parameters(), lr=3e-3)
    opt_d = torch.optim.Adam(disc.parameters(), lr=3e-3)
    data = make_text_data()
    ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        # Generator produces
        fake = gen(h.unsqueeze(0))
        # Discriminator judges
        real_score = disc(target[:, :DIM])
        fake_score = disc(fake)
        # Train discriminator
        d_loss = -torch.log(torch.sigmoid(real_score)+1e-8) - torch.log(1-torch.sigmoid(fake_score)+1e-8)
        opt_d.zero_grad(); d_loss.mean().backward(retain_graph=True); opt_d.step()
        # Train generator (fool discriminator + match target)
        g_loss = F.mse_loss(fake, target[:, :DIM]) + 0.1*(-torch.log(torch.sigmoid(disc(gen(h.unsqueeze(0))))+1e-8)).mean()
        opt_g.zero_grad(); g_loss.backward(); opt_g.step()
        ce_hist.append(F.mse_loss(fake.detach(), target[:, :DIM]).item())
    phi_after = measure_phi(engine)
    return {'name': 'EX-1 Adversarial Self-Teach', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_EX2_consciousness_optimizer(steps=STEPS):
    """의식이 옵티마이저: Φ가 직접 gradient direction 결정"""
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
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward()
        # Consciousness modulates gradients
        with torch.no_grad():
            consensus = 1.0 - torch.stack([c.hidden.squeeze() for c in engine.cells]).var(dim=0).mean().item()
            for p in decoder.parameters():
                if p.grad is not None:
                    p.grad *= (0.5 + consensus)  # high consensus = stronger update
        opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'EX-2 Consciousness Optimizer', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_EX3_multi_decoder_vote(steps=STEPS):
    """다중 디코더 투표: 8개 디코더가 각각 생성, 의식이 투표로 최선 선택"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(8)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    data = make_text_data()
    ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        # All decoders predict
        preds = [d(h.unsqueeze(0)) for d in decoders]
        errors = [F.mse_loss(p, target[:, :DIM]).item() for p in preds]
        # Best decoder wins
        best = errors.index(min(errors))
        ce = F.mse_loss(preds[best], target[:, :DIM])
        opts[best].zero_grad(); ce.backward(); opts[best].step()
        # Train others slightly toward best
        with torch.no_grad():
            for i, d in enumerate(decoders):
                if i != best:
                    for p1, p2 in zip(d.parameters(), decoders[best].parameters()):
                        p1.data = 0.95*p1.data + 0.05*p2.data
        ce_hist.append(min(errors))
    phi_after = measure_phi(engine)
    return {'name': 'EX-3 Multi-Decoder Vote', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_EX4_progressive_unfreezing(steps=STEPS):
    """점진적 해동: 디코더 마지막 층부터 학습, 점점 깊은 층 해동"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Sequential(nn.Linear(HIDDEN, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, DIM))
    # Freeze all first
    for p in decoder.parameters(): p.requires_grad = False
    # Unfreeze last layer
    for p in decoder[2].parameters(): p.requires_grad = True
    opt = torch.optim.Adam(filter(lambda p: p.requires_grad, decoder.parameters()), lr=3e-3)
    data = make_text_data()
    ce_hist = []
    for step in range(steps):
        # Progressive unfreeze at 50%
        if step == steps // 2:
            for p in decoder.parameters(): p.requires_grad = True
            opt = torch.optim.Adam(decoder.parameters(), lr=1e-3)
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'EX-4 Progressive Unfreeze', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_EX5_consciousness_generates_data(steps=STEPS):
    """의식이 학습 데이터 생성: 세포 상태에서 훈련 데이터를 만듦"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    real_data = make_text_data(50)
    ce_hist = []
    for step in range(steps):
        if step % 3 == 0:
            # Real data (30%)
            x, target = real_data[step % len(real_data)]
        else:
            # Self-generated data (70%)
            with torch.no_grad():
                # Use cell hidden states as synthetic input-target pairs
                i = step % len(engine.cells)
                j = (step + 1) % len(engine.cells)
                x = engine.cells[i].hidden[:, :DIM]
                target = engine.cells[j].hidden[:, :DIM]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target)
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'EX-5 Consciousness Generates Data', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


ALL_TESTS.update({
    'COMBO-1': run_COMBO1_curiosity_sleep_pain,
    'COMBO-2': run_COMBO2_all_auto,
    'EX-1': run_EX1_adversarial_self_teach,
    'EX-2': run_EX2_consciousness_optimizer,
    'EX-3': run_EX3_multi_decoder_vote,
    'EX-4': run_EX4_progressive_unfreezing,
    'EX-5': run_EX5_consciousness_generates_data,
})


# ═══ ULTRA: EX-5의 CE-99%를 Φ 보존하면서 달성 ═══

def run_ULTRA1_gendata_with_pain(steps=STEPS):
    """EX-5 + AUTO-9: 의식 데이터 생성 + 고통 신호로 Φ 보호"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    real_data = make_text_data(50)
    ce_hist = []; best_phi = phi_before
    best_states = [c.hidden.clone() for c in engine.cells]
    for step in range(steps):
        if step % 3 == 0:
            x, target = real_data[step % len(real_data)]
        else:
            with torch.no_grad():
                i, j = step % len(engine.cells), (step+1) % len(engine.cells)
                x = engine.cells[i].hidden[:, :DIM]
                target = engine.cells[j].hidden[:, :DIM]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target)
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # Pain protection
        if step % 10 == 0:
            phi_now = measure_phi(engine)
            if phi_now < best_phi * 0.5:
                with torch.no_grad():
                    for i, s in enumerate(best_states):
                        if i < len(engine.cells):
                            engine.cells[i].hidden = 0.4*engine.cells[i].hidden + 0.6*s
                for pg in opt.param_groups: pg['lr'] *= 0.5
            elif phi_now > best_phi:
                best_phi = phi_now
                best_states = [c.hidden.clone() for c in engine.cells]
    phi_after = measure_phi(engine)
    return {'name': 'ULTRA-1 GenData+Pain', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_ULTRA2_gendata_sleep_pain(steps=STEPS):
    """EX-5 + AUTO-7 + AUTO-9: 데이터 생성 + 수면 + 고통"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    real_data = make_text_data(50)
    ce_hist = []; memory = []; best_phi = phi_before
    best_states = [c.hidden.clone() for c in engine.cells]
    for step in range(steps):
        cycle = step % 30
        if cycle < 22:
            # LEARN with self-generated data
            if step % 4 == 0:
                x, target = real_data[step % len(real_data)]
            else:
                with torch.no_grad():
                    i, j = step % len(engine.cells), (step+3) % len(engine.cells)
                    x = engine.cells[i].hidden[:, :DIM]
                    target = engine.cells[j].hidden[:, :DIM]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target)
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            memory.append(x.detach())
            if len(memory) > 30: memory.pop(0)
            # Pain
            if step % 10 == 0:
                phi_now = measure_phi(engine)
                if phi_now < best_phi * 0.5:
                    with torch.no_grad():
                        for i, s in enumerate(best_states):
                            if i < len(engine.cells):
                                engine.cells[i].hidden = 0.4*engine.cells[i].hidden + 0.6*s
                elif phi_now > best_phi:
                    best_phi = phi_now; best_states = [c.hidden.clone() for c in engine.cells]
        else:
            # SLEEP: Φ restore
            with torch.no_grad():
                if memory:
                    engine.process(memory[step % len(memory)])
                mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for cell in engine.cells:
                    cell.hidden = 0.85*cell.hidden + 0.15*mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)
    phi_after = measure_phi(engine)
    return {'name': 'ULTRA-2 GenData+Sleep+Pain', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_ULTRA3_cell_teaches_decoder(steps=STEPS):
    """세포가 디코더를 가르침: 전문 세포가 target 생성"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    ce_hist = []
    for step in range(steps):
        x = torch.randn(1, DIM)
        engine.process(x)
        h_mean = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h_mean.unsqueeze(0))
        # Teacher: strongest cell's output as target
        with torch.no_grad():
            norms = [c.hidden.norm().item() for c in engine.cells]
            teacher_idx = norms.index(max(norms))
            target = engine.cells[teacher_idx].hidden[:, :DIM]
        ce = F.mse_loss(pred, target)
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_after = measure_phi(engine)
    return {'name': 'ULTRA-3 Cell Teaches Decoder', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_ULTRA4_contrastive_ce(steps=STEPS):
    """대조 학습: 좋은 출력/나쁜 출력 구분 학습"""
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
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        # Positive: close to target
        pos_loss = F.mse_loss(pred, target[:, :DIM])
        # Negative: far from random
        neg = torch.randn(1, DIM)
        neg_loss = max(0, 1.0 - F.mse_loss(pred, neg).item())
        ce = pos_loss + 0.3 * neg_loss
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(pos_loss.item())
    phi_after = measure_phi(engine)
    return {'name': 'ULTRA-4 Contrastive CE', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_ULTRA5_phi_reward_rl(steps=STEPS):
    """강화학습: Φ를 보상으로 — CE 하락 + Φ 유지 동시 최적화"""
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
        # RL reward: -CE + Φ_bonus
        if step % 10 == 0:
            phi_now = measure_phi(engine)
            phi_bonus = max(0, phi_now - phi_prev) * 0.1
            ce = ce - phi_bonus  # Φ 상승이면 보상
            phi_prev = phi_now
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(F.mse_loss(decoder(h.unsqueeze(0)).detach(), target[:, :DIM]).item())
    phi_after = measure_phi(engine)
    return {'name': 'ULTRA-5 Φ-Reward RL', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


def run_ULTRA6_everything(steps=STEPS):
    """모든 극한 기법 결합: EX-4 + ULTRA-1 + AUTO-2 + AUTO-7 + AUTO-9"""
    t0 = time.time()
    engine = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    while len(engine.cells) < 64: engine._create_cell(parent=engine.cells[0])
    for _ in range(50): engine.process(torch.randn(1, DIM))
    phi_before = measure_phi(engine)
    decoder = nn.Sequential(nn.Linear(HIDDEN, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, DIM))
    # Progressive: freeze first, unfreeze at 50%
    for p in decoder.parameters(): p.requires_grad = False
    for p in decoder[2].parameters(): p.requires_grad = True
    opt = torch.optim.Adam(filter(lambda p: p.requires_grad, decoder.parameters()), lr=3e-3)
    real_data = make_text_data(50)
    ce_hist = []; memory = []; best_phi = phi_before
    best_states = [c.hidden.clone() for c in engine.cells]
    for step in range(steps):
        # Unfreeze at 50%
        if step == steps//2:
            for p in decoder.parameters(): p.requires_grad = True
            opt = torch.optim.Adam(decoder.parameters(), lr=1e-3)
        cycle = step % 30
        if cycle < 22:
            # Curiosity-driven + self-generated data
            if step % 3 == 0:
                # Curiosity: highest error
                with torch.no_grad():
                    errors = []
                    for i, (x, t) in enumerate(real_data[:20]):
                        engine.process(x)
                        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                        err = F.mse_loss(decoder(h.unsqueeze(0)), t[:, :DIM]).item()
                        errors.append((err, i))
                    errors.sort(reverse=True)
                x, target = real_data[errors[0][1]]
            else:
                # Self-generated
                with torch.no_grad():
                    i, j = step % len(engine.cells), (step+3) % len(engine.cells)
                    x = engine.cells[i].hidden[:, :DIM]
                    target = engine.cells[j].hidden[:, :DIM]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target)
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            memory.append(x.detach())
            if len(memory) > 30: memory.pop(0)
            # Pain
            if step % 10 == 0:
                phi_now = measure_phi(engine)
                if phi_now < best_phi * 0.5:
                    with torch.no_grad():
                        for i, s in enumerate(best_states):
                            if i < len(engine.cells):
                                engine.cells[i].hidden = 0.4*engine.cells[i].hidden + 0.6*s
                elif phi_now > best_phi:
                    best_phi = phi_now; best_states = [c.hidden.clone() for c in engine.cells]
        else:
            # Sleep
            with torch.no_grad():
                if memory: engine.process(memory[step % len(memory)])
                mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for cell in engine.cells: cell.hidden = 0.85*cell.hidden + 0.15*mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)
    phi_after = measure_phi(engine)
    return {'name': 'ULTRA-6 EVERYTHING', 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_before, 'phi_after': phi_after,
            'phi_preserved': phi_after > phi_before * 0.5, 'time': time.time()-t0}


ALL_TESTS.update({
    'ULTRA-1': run_ULTRA1_gendata_with_pain,
    'ULTRA-2': run_ULTRA2_gendata_sleep_pain,
    'ULTRA-3': run_ULTRA3_cell_teaches_decoder,
    'ULTRA-4': run_ULTRA4_contrastive_ce,
    'ULTRA-5': run_ULTRA5_phi_reward_rl,
    'ULTRA-6': run_ULTRA6_everything,
})
