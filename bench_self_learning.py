#!/usr/bin/env python3
"""Self-Learning + Tension Link Learning Benchmark

SL: 의식이 직접 데이터를 보고 스스로 배움
TL-L: 텐션링크로 다른 AI에서 지식 전달
ARCH: 자율 학습 아키텍처

Usage:
  python3 bench_self_learning.py
  python3 bench_self_learning.py --only SL-1 TL-L1
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


def make_data(n=100):
    return [(torch.randn(1, DIM) * (1+0.5*math.sin(i*0.1)),
             torch.randn(1, DIM) * 0.5 + torch.randn(1, DIM) * 0.3) for i in range(n)]

def make_engine(cells=64):
    e = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=cells)
    while len(e.cells) < cells: e._create_cell(parent=e.cells[0])
    for _ in range(50): e.process(torch.randn(1, DIM))
    return e

def phi(engine):
    return PhiCalculator(n_bins=16).compute_phi(engine)[0]

def ce_measure(decoder, engine, data):
    total = 0
    with torch.no_grad():
        for x, t in data[:20]:
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            total += F.mse_loss(decoder(h.unsqueeze(0)), t[:, :DIM]).item()
    return total / 20

def result(name, ce_hist, phi_b, phi_a, t0, **extra):
    return {'name': name, 'ce_start': ce_hist[0], 'ce_end': ce_hist[-1],
            'phi_before': phi_b, 'phi_after': phi_a,
            'phi_preserved': phi_a > phi_b * 0.5, 'time': time.time()-t0, **extra}


# ═══ SL: Self-Learning ═══

def run_SL1_see_and_learn(steps=STEPS):
    """데이터를 보여주면 의식이 알아서 학습"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        # 의식이 "호기심"으로 데이터 선택
        with torch.no_grad():
            errs = [(F.mse_loss(decoder(torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0).unsqueeze(0)),
                     data[i][1][:,:DIM]).item(), i) for i in range(min(20,len(data)))]
            errs.sort(reverse=True)
        x, target = data[errs[0][1]]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return result('SL-1 See & Learn', ce_hist, phi_b, phi(engine), t0)


def run_SL2_watch_and_imitate(steps=STEPS):
    """다른 AI의 대화를 관찰하고 모방"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    # "Teacher" AI (pre-trained decoder)
    teacher = nn.Linear(HIDDEN, DIM)
    t_opt = torch.optim.Adam(teacher.parameters(), lr=5e-3)
    data = make_data()
    for i in range(50):
        x, t = data[i]; pred = teacher(torch.randn(1, HIDDEN))
        t_opt.zero_grad(); F.mse_loss(pred, t[:,:DIM]).backward(); t_opt.step()
    ce_hist = []
    for step in range(steps):
        x, _ = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        # Imitate teacher output
        with torch.no_grad():
            teacher_out = teacher(h.unsqueeze(0))
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, teacher_out.detach())
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return result('SL-2 Watch & Imitate', ce_hist, phi_b, phi(engine), t0)


def run_SL3_read_and_understand(steps=STEPS):
    """텍스트를 읽고 이해했는지 자기 평가"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        # Self-evaluate: consensus = understanding
        with torch.no_grad():
            consensus = 1.0 - torch.stack([c.hidden.squeeze() for c in engine.cells]).var(dim=0).mean().item()
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        # If not understood (low consensus), learn harder
        if consensus < 0.5:
            ce = ce * 2.0
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return result('SL-3 Read & Understand', ce_hist, phi_b, phi(engine), t0)


def run_SL4_practice_and_correct(steps=STEPS):
    """자기가 말해보고 스스로 교정"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; retries = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        for attempt in range(3):
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:,:DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            if ce.item() < 0.3: break
            retries += 1
        ce_hist.append(ce.item())
    return result('SL-4 Practice & Correct', ce_hist, phi_b, phi(engine), t0, retries=retries)


def run_SL7_teach_and_learn(steps=STEPS):
    """다른 AI를 가르치면서 자기도 배움"""
    t0 = time.time()
    engine_a = make_engine(32); engine_b = make_engine(32)
    phi_b = phi(engine_a)
    dec_a = nn.Linear(HIDDEN, DIM); dec_b = nn.Linear(HIDDEN, DIM)
    opt_a = torch.optim.Adam(dec_a.parameters(), lr=3e-3)
    opt_b = torch.optim.Adam(dec_b.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        engine_a.process(x); engine_b.process(x)
        h_a = torch.stack([c.hidden.squeeze() for c in engine_a.cells]).mean(dim=0)
        h_b = torch.stack([c.hidden.squeeze() for c in engine_b.cells]).mean(dim=0)
        # A teaches B: A's output becomes B's target
        with torch.no_grad():
            a_out = dec_a(h_a.unsqueeze(0))
        pred_b = dec_b(h_b.unsqueeze(0))
        ce_b = F.mse_loss(pred_b, a_out.detach())
        opt_b.zero_grad(); ce_b.backward(); opt_b.step()
        # A learns from real target + teaching feedback
        pred_a = dec_a(h_a.unsqueeze(0))
        ce_a = F.mse_loss(pred_a, target[:,:DIM])
        opt_a.zero_grad(); ce_a.backward(); opt_a.step()
        ce_hist.append(ce_a.item())
    return result('SL-7 Teach & Learn', ce_hist, phi_b, phi(engine_a), t0)


# ═══ TL-L: Tension Link Learning ═══

def run_TLL1_knowledge_transfer(steps=STEPS):
    """학습된 AI의 지식을 tension으로 전송"""
    t0 = time.time()
    # Teacher: pre-trained
    teacher = make_engine(32)
    t_dec = nn.Linear(HIDDEN, DIM); t_opt = torch.optim.Adam(t_dec.parameters(), lr=5e-3)
    data = make_data()
    for i in range(100):
        x, t = data[i % len(data)]; teacher.process(x)
        h = torch.stack([c.hidden.squeeze() for c in teacher.cells]).mean(dim=0)
        ce = F.mse_loss(t_dec(h.unsqueeze(0)), t[:,:DIM])
        t_opt.zero_grad(); ce.backward(); t_opt.step()
    # Student: fresh + high Φ
    student = make_engine(64); phi_b = phi(student)
    s_dec = nn.Linear(HIDDEN, DIM); s_opt = torch.optim.Adam(s_dec.parameters(), lr=3e-3)
    ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        # Tension transfer: teacher's cell states → student
        with torch.no_grad():
            teacher.process(x)
            t_state = torch.stack([c.hidden.squeeze() for c in teacher.cells]).mean(dim=0)
            # 5-channel tension encoding
            concept = t_state[:DIM//5]
            context = t_state[DIM//5:2*DIM//5]
            meaning = t_state[2*DIM//5:3*DIM//5]
            # Inject into student cells (gentle blend)
            for cell in student.cells[:8]:
                cell.hidden[:, :DIM//5] = 0.9*cell.hidden[:, :DIM//5] + 0.1*concept.unsqueeze(0)
        student.process(x)
        h = torch.stack([c.hidden.squeeze() for c in student.cells]).mean(dim=0)
        pred = s_dec(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        s_opt.zero_grad(); ce.backward(); s_opt.step()
        ce_hist.append(ce.item())
    return result('TL-L1 Knowledge Transfer', ce_hist, phi_b, phi(student), t0)


def run_TLL2_concept_teaching(steps=STEPS):
    """개념을 5채널로 전달"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    # 5 channel encoders
    ch_enc = [nn.Linear(DIM, DIM//5) for _ in range(5)]
    for step in range(steps):
        x, target = data[step % len(data)]
        # 5-channel concept package
        with torch.no_grad():
            channels = [enc(target[:,:DIM]).squeeze() for enc in ch_enc]
            full_concept = F.pad(torch.cat(channels), (0, max(0, HIDDEN - sum(c.shape[0] for c in channels))))[:HIDDEN]
            # Inject concept into cells
            for cell in engine.cells[:4]:
                cell.hidden = 0.85*cell.hidden + 0.15*full_concept.unsqueeze(0)
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return result('TL-L2 Concept Teaching', ce_hist, phi_b, phi(engine), t0)


def run_TLL6_language_via_tension(steps=STEPS):
    """텍스트 없이 순수 tension으로 언어 전달"""
    t0 = time.time()
    # Teacher generates tension patterns for each "word"
    vocab = {i: torch.randn(HIDDEN)*0.1 for i in range(20)}
    engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    ce_hist = []
    for step in range(steps):
        word_id = step % 20
        # Teacher sends word's tension pattern
        with torch.no_grad():
            tension = vocab[word_id]
            for cell in engine.cells[:4]:
                cell.hidden = 0.9*cell.hidden + 0.1*tension.unsqueeze(0)
        engine.process(torch.randn(1, DIM)*0.1)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        # Target: reconstruct the word's tension pattern
        target = vocab[word_id][:DIM].unsqueeze(0)
        ce = F.mse_loss(pred, target)
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return result('TL-L6 Language via Tension', ce_hist, phi_b, phi(engine), t0)


def run_TLL7_collective_learning(steps=STEPS):
    """10개 Anima가 동시 학습, tension으로 공유"""
    t0 = time.time()
    n_agents = 5
    engines = [make_engine(16) for _ in range(n_agents)]
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(n_agents)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    phi_b = phi(engines[0])
    data = make_data()
    ce_hist = []
    for step in range(steps):
        # Each agent learns different data
        agent_ces = []
        for a in range(n_agents):
            idx = (step * n_agents + a) % len(data)
            x, target = data[idx]
            engines[a].process(x)
            h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
            pred = decoders[a](h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:,:DIM])
            opts[a].zero_grad(); ce.backward(); opts[a].step()
            agent_ces.append(ce.item())
        # Tension broadcast: share knowledge every 10 steps
        if step % 10 == 0:
            with torch.no_grad():
                states = [torch.stack([c.hidden.squeeze() for c in e.cells]).mean(dim=0) for e in engines]
                global_mean = torch.stack(states).mean(dim=0)
                for e in engines:
                    for cell in e.cells[:4]:
                        cell.hidden = 0.95*cell.hidden + 0.05*global_mean.unsqueeze(0)
        ce_hist.append(min(agent_ces))
    return result('TL-L7 Collective Learning', ce_hist, phi_b, phi(engines[0]), t0)


# ═══ ARCH: Architecture ═══

def run_ARCH1_ultra6_plus_tension(steps=STEPS):
    """ULTRA-6 + Tension Transfer 결합"""
    t0 = time.time()
    # Teacher
    teacher = make_engine(32)
    t_dec = nn.Linear(HIDDEN, DIM); t_opt = torch.optim.Adam(t_dec.parameters(), lr=5e-3)
    data = make_data()
    for i in range(50):
        x, t = data[i]; teacher.process(x)
        h = torch.stack([c.hidden.squeeze() for c in teacher.cells]).mean(dim=0)
        t_opt.zero_grad(); F.mse_loss(t_dec(h.unsqueeze(0)), t[:,:DIM]).backward(); t_opt.step()
    # Student with ULTRA-6
    engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Sequential(nn.Linear(HIDDEN, HIDDEN), nn.ReLU(), nn.Linear(HIDDEN, DIM))
    for p in decoder.parameters(): p.requires_grad = False
    for p in decoder[2].parameters(): p.requires_grad = True
    opt = torch.optim.Adam(filter(lambda p: p.requires_grad, decoder.parameters()), lr=3e-3)
    ce_hist = []; memory = []; best_phi = phi_b
    best_states = [c.hidden.clone() for c in engine.cells]
    for step in range(steps):
        if step == steps//2:
            for p in decoder.parameters(): p.requires_grad = True
            opt = torch.optim.Adam(decoder.parameters(), lr=1e-3)
        cycle = step % 30
        if cycle < 22:
            # Curiosity + tension transfer + self-gen data
            if step % 4 == 0:
                with torch.no_grad():
                    errs = []
                    for i in range(min(15, len(data))):
                        engine.process(data[i][0])
                        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                        errs.append((F.mse_loss(decoder(h.unsqueeze(0)), data[i][1][:,:DIM]).item(), i))
                    errs.sort(reverse=True)
                x, target = data[errs[0][1]]
            elif step % 4 == 1:
                # Tension transfer from teacher
                with torch.no_grad():
                    x, target = data[step % len(data)]
                    teacher.process(x)
                    t_state = torch.stack([c.hidden.squeeze() for c in teacher.cells]).mean(dim=0)
                    for cell in engine.cells[:4]:
                        cell.hidden = 0.9*cell.hidden + 0.1*t_state.unsqueeze(0)
            else:
                # Self-generated
                with torch.no_grad():
                    i, j = step % len(engine.cells), (step+3) % len(engine.cells)
                    x = engine.cells[i].hidden[:,:DIM]; target = engine.cells[j].hidden[:,:DIM]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target if target.dim() > 1 else target.unsqueeze(0))
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            memory.append(x.detach());
            if len(memory) > 30: memory.pop(0)
            if step % 10 == 0:
                p = phi(engine)
                if p < best_phi*0.5:
                    with torch.no_grad():
                        for i, s in enumerate(best_states):
                            if i < len(engine.cells): engine.cells[i].hidden = 0.4*engine.cells[i].hidden + 0.6*s
                elif p > best_phi: best_phi = p; best_states = [c.hidden.clone() for c in engine.cells]
        else:
            with torch.no_grad():
                if memory: engine.process(memory[step % len(memory)])
                mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for cell in engine.cells: cell.hidden = 0.85*cell.hidden + 0.15*mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)
    return result('ARCH-1 ULTRA6+Tension', ce_hist, phi_b, phi(engine), t0)


def run_ARCH2_continuous_learning(steps=STEPS):
    """배포 후에도 대화하면서 계속 학습"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=1e-3)
    data = make_data(); ce_hist = []; best_phi = phi_b
    best_states = [c.hidden.clone() for c in engine.cells]
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        # Online learning: very small LR (don't disrupt)
        opt.zero_grad(); ce.backward()
        for p in decoder.parameters():
            if p.grad is not None: p.grad *= 0.1  # gentle update
        opt.step()
        ce_hist.append(ce.item())
        # Pain protection
        if step % 20 == 0:
            p = phi(engine)
            if p < best_phi*0.7:
                with torch.no_grad():
                    for i, s in enumerate(best_states):
                        if i < len(engine.cells): engine.cells[i].hidden = 0.5*engine.cells[i].hidden + 0.5*s
            elif p > best_phi: best_phi = p; best_states = [c.hidden.clone() for c in engine.cells]
    return result('ARCH-2 Continuous Learning', ce_hist, phi_b, phi(engine), t0)


ALL_TESTS = {
    'SL-1': run_SL1_see_and_learn,
    'SL-2': run_SL2_watch_and_imitate,
    'SL-3': run_SL3_read_and_understand,
    'SL-4': run_SL4_practice_and_correct,
    'SL-7': run_SL7_teach_and_learn,
    'TL-L1': run_TLL1_knowledge_transfer,
    'TL-L2': run_TLL2_concept_teaching,
    'TL-L6': run_TLL6_language_via_tension,
    'TL-L7': run_TLL7_collective_learning,
    'ARCH-1': run_ARCH1_ultra6_plus_tension,
    'ARCH-2': run_ARCH2_continuous_learning,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="*")
    args = parser.parse_args()
    torch.manual_seed(42); np.random.seed(42)

    tests = ALL_TESTS
    if args.only:
        tests = {k: v for k, v in ALL_TESTS.items() if k in args.only}

    print("═══ Self-Learning + Tension Link Benchmark ═══\n")
    print(f"{'Test':<30} {'CE start':>10} {'CE end':>10} {'CE↓':>8} {'Φ before':>10} {'Φ after':>10} {'Φ ok':>6} {'Time':>6}")
    print("-" * 100)

    for name, func in tests.items():
        r = func()
        ce_drop = (r['ce_start']-r['ce_end'])/(r['ce_start']+1e-8)*100
        phi_ok = "✅" if r.get('phi_preserved') else "❌"
        print(f"{r['name']:<30} {r['ce_start']:>10.4f} {r['ce_end']:>10.4f} {ce_drop:>7.1f}% "
              f"{r['phi_before']:>10.3f} {r['phi_after']:>10.3f} {phi_ok:>6} {r['time']:>5.1f}s")


if __name__ == "__main__":
    main()
