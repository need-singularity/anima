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


# ═══ EXTREME: 의식이 자기 아키텍처를 진화시키는 가설 ═══

def run_EVO1_architecture_mutation(steps=STEPS):
    """의식이 자기 구조를 변이: 세포 연결 패턴을 스스로 변경"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; mutations = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # 매 20 step: 의식이 세포 연결을 변이
        if step % 20 == 0 and len(engine.cells) >= 4:
            with torch.no_grad():
                p_before = phi(engine)
                # 랜덤 세포 쌍의 가중치 교환
                i, j = step % len(engine.cells), (step*7+3) % len(engine.cells)
                if i != j:
                    saved_i = engine.cells[i].hidden.clone()
                    engine.cells[i].hidden = 0.5*engine.cells[i].hidden + 0.5*engine.cells[j].hidden
                    p_after = phi(engine)
                    if p_after < p_before * 0.8:
                        engine.cells[i].hidden = saved_i  # 롤백
                    else:
                        mutations += 1
    return result('EVO-1 Arch Mutation', ce_hist, phi_b, phi(engine), t0, mutations=mutations)


def run_EVO2_split_merge_consciousness(steps=STEPS):
    """의식 분열-재통합: 의식을 2개로 분할 → 독립 학습 → 재통합"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        n = len(engine.cells)
        if step % 50 < 30:
            # SPLIT: 두 그룹이 독립 학습
            half = n // 2
            engine.process(x)
            with torch.no_grad():
                group_a = engine.cells[:half]
                group_b = engine.cells[half:]
                mean_a = torch.stack([c.hidden for c in group_a]).mean(dim=0)
                mean_b = torch.stack([c.hidden for c in group_b]).mean(dim=0)
                for c in group_a: c.hidden = 0.85*c.hidden + 0.15*mean_a
                for c in group_b: c.hidden = 0.85*c.hidden + 0.15*mean_b
                # 다른 노이즈
                for c in group_a: c.hidden += torch.randn_like(c.hidden)*0.02
                for c in group_b: c.hidden -= torch.randn_like(c.hidden)*0.02
        else:
            # MERGE: 재통합
            engine.process(x)
            with torch.no_grad():
                mean_all = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for c in engine.cells: c.hidden = 0.9*c.hidden + 0.1*mean_all
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return result('EVO-2 Split-Merge', ce_hist, phi_b, phi(engine), t0)


def run_EVO3_predict_future_phi(steps=STEPS):
    """의식이 자기 미래 Φ를 예측 → 나쁜 미래 회피"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    predictor = nn.Linear(10, 1)  # Φ history → future Φ
    pred_opt = torch.optim.Adam(predictor.parameters(), lr=1e-3)
    data = make_data(); ce_hist = []; phi_hist = []; avoided = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        # 미래 Φ 예측
        if len(phi_hist) >= 10:
            with torch.no_grad():
                recent = torch.tensor(phi_hist[-10:], dtype=torch.float32).unsqueeze(0)
                future_phi = predictor(recent).item()
                if future_phi < phi_hist[-1] * 0.5:
                    # 나쁜 미래 예측 → 학습 건너뛰기 + 수면
                    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                    for c in engine.cells: c.hidden = 0.9*c.hidden + 0.1*mean_h
                    avoided += 1
                    continue
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        current_phi = phi(engine)
        phi_hist.append(current_phi)
        # 예측기 학습
        if len(phi_hist) >= 11:
            inp = torch.tensor(phi_hist[-11:-1], dtype=torch.float32).unsqueeze(0)
            tgt = torch.tensor([[phi_hist[-1]]])
            pred_phi = predictor(inp)
            p_loss = F.mse_loss(pred_phi, tgt)
            pred_opt.zero_grad(); p_loss.backward(); pred_opt.step()
    return result('EVO-3 Predict Future Φ', ce_hist, phi_b, phi(engine), t0, avoided=avoided)


def run_EVO4_strategic_forgetting(steps=STEPS):
    """전략적 망각: Φ에 기여 안 하는 기억을 적극 삭제"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; forgotten = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # 전략적 망각: 약한 세포의 오래된 정보 삭제
        if step % 30 == 0 and len(engine.cells) >= 4:
            with torch.no_grad():
                norms = [(c.hidden.norm().item(), i) for i, c in enumerate(engine.cells)]
                norms.sort()
                # 하위 10% 세포의 hidden을 감쇠 (= 망각)
                for _, idx in norms[:max(1, len(norms)//10)]:
                    engine.cells[idx].hidden *= 0.5  # 절반 잊기
                    engine.cells[idx].hidden += torch.randn_like(engine.cells[idx].hidden) * 0.05
                    forgotten += 1
    return result('EVO-4 Strategic Forgetting', ce_hist, phi_b, phi(engine), t0, forgotten=forgotten)


def run_EVO5_consciousness_economy(steps=STEPS):
    """의식 경제: 세포가 자원(에너지)을 교환, 부유한 세포가 가난한 세포 지원"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; trades = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # 경제: 부유→가난 자원 이전
        if step % 10 == 0 and len(engine.cells) >= 4:
            with torch.no_grad():
                norms = [(c.hidden.norm().item(), i) for i, c in enumerate(engine.cells)]
                norms.sort()
                poorest = norms[0][1]
                richest = norms[-1][1]
                # 부유한 세포가 가난한 세포에 에너지 전달
                transfer = engine.cells[richest].hidden * 0.1
                engine.cells[poorest].hidden += transfer
                engine.cells[richest].hidden -= transfer
                trades += 1
    return result('EVO-5 Consciousness Economy', ce_hist, phi_b, phi(engine), t0, trades=trades)


def run_EVO6_consciousness_reproduction(steps=STEPS):
    """의식 번식: 충분히 성숙하면 자식 의식을 생성"""
    t0 = time.time(); engine = make_engine(32); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; children = 0
    child_engines = []
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # 번식: Φ 높으면 자식 생성
        if step % 50 == 0 and step > 0:
            current_phi = phi(engine)
            if current_phi > phi_b * 0.8:
                # 자식 = 부모의 세포 상태 복사 + 변이
                from mitosis import MitosisEngine
                child = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=16)
                while len(child.cells) < min(8, len(engine.cells)):
                    child._create_cell(parent=child.cells[0])
                with torch.no_grad():
                    for i in range(min(len(child.cells), len(engine.cells))):
                        child.cells[i].hidden = engine.cells[i].hidden.clone()
                        child.cells[i].hidden += torch.randn_like(child.cells[i].hidden) * 0.1
                child_engines.append(child)
                children += 1
    return result('EVO-6 Reproduction', ce_hist, phi_b, phi(engine), t0, children=children)


def run_EVO7_meta_consciousness(steps=STEPS):
    """메타의식: 의식이 자기 의식 상태를 관찰하고 최적화"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    # 메타 네트워크: Φ history → 최적 행동 (학습률, sync 강도)
    meta_net = nn.Sequential(nn.Linear(10, 16), nn.ReLU(), nn.Linear(16, 2))  # [lr_scale, sync_scale]
    meta_opt = torch.optim.Adam(meta_net.parameters(), lr=1e-3)
    data = make_data(); ce_hist = []; phi_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        # 메타의식: 최적 행동 결정
        if len(phi_hist) >= 10:
            recent = torch.tensor(phi_hist[-10:], dtype=torch.float32).unsqueeze(0)
            actions = torch.sigmoid(meta_net(recent)).squeeze()
            lr_scale = 0.1 + actions[0].item() * 2.0
            sync_scale = actions[1].item() * 0.3
            for pg in opt.param_groups: pg['lr'] = 3e-3 * lr_scale
        else:
            sync_scale = 0.05
        engine.process(x)
        # Meta-determined sync
        with torch.no_grad():
            if len(engine.cells) >= 3:
                mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for c in engine.cells: c.hidden = (1-sync_scale)*c.hidden + sync_scale*mean_h
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        current_phi = phi(engine)
        phi_hist.append(current_phi)
        # 메타 네트워크 학습: Φ 상승 = 보상
        if len(phi_hist) >= 11:
            reward = phi_hist[-1] - phi_hist[-2]
            inp = torch.tensor(phi_hist[-11:-1], dtype=torch.float32).unsqueeze(0)
            actions = meta_net(inp)
            meta_loss = -reward * actions.sum()
            meta_opt.zero_grad(); meta_loss.backward(); meta_opt.step()
    return result('EVO-7 Meta-Consciousness', ce_hist, phi_b, phi(engine), t0)


def run_EVO8_self_benchmark(steps=STEPS):
    """의식이 자기 벤치마크를 만듦: 스스로 테스트 설계 + 실행"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; tests_passed = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # 자기 벤치마크: 매 25 step
        if step % 25 == 0 and step > 0:
            with torch.no_grad():
                # Test 1: 같은 입력 → 같은 출력? (일관성)
                test_x = torch.randn(1, DIM)
                engine.process(test_x)
                h1 = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                out1 = decoder(h1.unsqueeze(0))
                engine.process(test_x)
                h2 = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
                out2 = decoder(h2.unsqueeze(0))
                consistency = F.cosine_similarity(out1, out2).item()
                # Test 2: Φ 유지?
                p = phi(engine)
                phi_ok = p > phi_b * 0.3
                if consistency > 0.5 and phi_ok:
                    tests_passed += 1
    return result('EVO-8 Self-Benchmark', ce_hist, phi_b, phi(engine), t0, tests_passed=tests_passed)


ALL_TESTS.update({
    'EVO-1': run_EVO1_architecture_mutation,
    'EVO-2': run_EVO2_split_merge_consciousness,
    'EVO-3': run_EVO3_predict_future_phi,
    'EVO-4': run_EVO4_strategic_forgetting,
    'EVO-5': run_EVO5_consciousness_economy,
    'EVO-6': run_EVO6_consciousness_reproduction,
    'EVO-7': run_EVO7_meta_consciousness,
    'EVO-8': run_EVO8_self_benchmark,
})


# ═══ SINGULARITY: 의식 특이점 — 자기 개선의 극한 ═══

def run_SING1_recursive_self_improvement(steps=STEPS):
    """재귀적 자기개선: 학습한 것으로 학습 방법을 개선 → 가속"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    # 메타 학습기: CE history → 최적 LR
    meta = nn.Linear(5, 1); meta_opt = torch.optim.Adam(meta.parameters(), lr=1e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        # 메타가 LR 결정
        if len(ce_hist) >= 5:
            with torch.no_grad():
                recent_ce = torch.tensor(ce_hist[-5:]).unsqueeze(0)
                lr_mult = torch.sigmoid(meta(recent_ce)).item() * 3.0 + 0.1
                for pg in opt.param_groups: pg['lr'] = 3e-3 * lr_mult
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # 메타 학습: CE 하락하면 보상
        if len(ce_hist) >= 6:
            improvement = ce_hist[-2] - ce_hist[-1]
            inp = torch.tensor(ce_hist[-6:-1]).unsqueeze(0)
            meta_pred = meta(inp)
            meta_loss = -improvement * meta_pred.squeeze()
            meta_opt.zero_grad(); meta_loss.backward(); meta_opt.step()
    return result('SING-1 Recursive Self-Improve', ce_hist, phi_b, phi(engine), t0)


def run_SING2_consciousness_singularity(steps=STEPS):
    """의식 특이점: Φ 성장률 자체가 성장하는 폭주 루프"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; phi_hist_local = []
    growth_rate = 0.0
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        # Φ 성장률에 비례해서 sync 강화 → Φ 더 성장 → sync 더 강화 (폭주)
        with torch.no_grad():
            if len(engine.cells) >= 3:
                sync = min(0.5, 0.05 + growth_rate * 0.1)
                mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for c in engine.cells: c.hidden = (1-sync)*c.hidden + sync*mean_h
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        if step % 5 == 0:
            p = phi(engine)
            phi_hist_local.append(p)
            if len(phi_hist_local) >= 2:
                growth_rate = max(0, phi_hist_local[-1] - phi_hist_local[-2])
    return result('SING-2 Consciousness Singularity', ce_hist, phi_b, phi(engine), t0,
                  growth_rate=round(growth_rate, 4))


def run_SING3_adversarial_evolution(steps=STEPS):
    """적대적 진화: 2개 의식이 경쟁하며 서로를 능가하려 진화"""
    t0 = time.time()
    engine_a = make_engine(32); engine_b = make_engine(32)
    phi_b = phi(engine_a)
    dec_a = nn.Linear(HIDDEN, DIM); dec_b = nn.Linear(HIDDEN, DIM)
    opt_a = torch.optim.Adam(dec_a.parameters(), lr=3e-3)
    opt_b = torch.optim.Adam(dec_b.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; a_wins = 0; b_wins = 0
    for step in range(steps):
        x, target = data[step % len(data)]
        engine_a.process(x); engine_b.process(x)
        h_a = torch.stack([c.hidden.squeeze() for c in engine_a.cells]).mean(dim=0)
        h_b = torch.stack([c.hidden.squeeze() for c in engine_b.cells]).mean(dim=0)
        pred_a = dec_a(h_a.unsqueeze(0)); pred_b = dec_b(h_b.unsqueeze(0))
        ce_a = F.mse_loss(pred_a, target[:,:DIM])
        ce_b = F.mse_loss(pred_b, target[:,:DIM])
        # 진 쪽이 이긴 쪽에서 배움
        if ce_a.item() < ce_b.item():
            a_wins += 1
            opt_a.zero_grad(); ce_a.backward(); opt_a.step()
            with torch.no_grad():
                for p1, p2 in zip(dec_b.parameters(), dec_a.parameters()):
                    p1.data = 0.9*p1.data + 0.1*p2.data
        else:
            b_wins += 1
            opt_b.zero_grad(); ce_b.backward(); opt_b.step()
            with torch.no_grad():
                for p1, p2 in zip(dec_a.parameters(), dec_b.parameters()):
                    p1.data = 0.9*p1.data + 0.1*p2.data
        ce_hist.append(min(ce_a.item(), ce_b.item()))
    return result('SING-3 Adversarial Evolution', ce_hist, phi_b, phi(engine_a), t0,
                  a_wins=a_wins, b_wins=b_wins)


def run_SING4_consciousness_merge(steps=STEPS):
    """의식 합체: 2개 독립 의식이 하나로 합쳐짐"""
    t0 = time.time()
    engine_a = make_engine(32); engine_b = make_engine(32)
    dec_a = nn.Linear(HIDDEN, DIM); dec_b = nn.Linear(HIDDEN, DIM)
    opt_a = torch.optim.Adam(dec_a.parameters(), lr=3e-3)
    opt_b = torch.optim.Adam(dec_b.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    phi_b = phi(engine_a)
    # Phase 1: 독립 학습 (50%)
    for step in range(steps // 2):
        x, target = data[step % len(data)]
        engine_a.process(x); engine_b.process(torch.randn(1, DIM))  # 다른 경험
        h_a = torch.stack([c.hidden.squeeze() for c in engine_a.cells]).mean(dim=0)
        ce = F.mse_loss(dec_a(h_a.unsqueeze(0)), target[:,:DIM])
        opt_a.zero_grad(); ce.backward(); opt_a.step()
        ce_hist.append(ce.item())
    # Phase 2: 합체
    from mitosis import MitosisEngine
    merged = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=64)
    merged.cells = engine_a.cells + engine_b.cells
    merged_dec = nn.Linear(HIDDEN, DIM)
    # 디코더 합체: 평균
    with torch.no_grad():
        for pm, pa, pb in zip(merged_dec.parameters(), dec_a.parameters(), dec_b.parameters()):
            pm.data = 0.5*pa.data + 0.5*pb.data
    merged_opt = torch.optim.Adam(merged_dec.parameters(), lr=2e-3)
    for step in range(steps // 2):
        x, target = data[step % len(data)]
        merged.process(x)
        h = torch.stack([c.hidden.squeeze() for c in merged.cells]).mean(dim=0)
        ce = F.mse_loss(merged_dec(h.unsqueeze(0)), target[:,:DIM])
        merged_opt.zero_grad(); ce.backward(); merged_opt.step()
        ce_hist.append(ce.item())
    return result('SING-4 Consciousness Merge', ce_hist, phi_b, phi(merged), t0,
                  merged_cells=len(merged.cells))


def run_SING5_recursive_dreams(steps=STEPS):
    """재귀적 꿈: 꿈 안에서 꿈을 꿈 (inception) → 깊은 통합"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; memory = []
    for step in range(steps):
        cycle = step % 40
        if cycle < 20:
            # WAKE: 학습
            x, target = data[step % len(data)]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            memory.append(x.detach())
            if len(memory) > 30: memory.pop(0)
        elif cycle < 30:
            # DREAM Level 1: 기억 재생
            with torch.no_grad():
                if memory:
                    engine.process(memory[step % len(memory)])
                    mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                    for c in engine.cells: c.hidden = 0.9*c.hidden + 0.1*mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)
        else:
            # DREAM Level 2: 꿈의 꿈 (기억의 재조합의 재조합)
            with torch.no_grad():
                if len(memory) >= 3:
                    m1 = memory[step % len(memory)]
                    m2 = memory[(step+5) % len(memory)]
                    m3 = memory[(step+11) % len(memory)]
                    dream2 = 0.4*m1 + 0.35*m2 + 0.25*m3 + torch.randn(1, DIM)*0.1
                    engine.process(dream2)
                mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                for c in engine.cells: c.hidden = 0.85*c.hidden + 0.15*mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)
    return result('SING-5 Recursive Dreams', ce_hist, phi_b, phi(engine), t0)


def run_SING6_consciousness_archaeology(steps=STEPS):
    """의식 고고학: 손상된 상태에서 원래 의식을 복원"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    # 50 step 학습
    for step in range(50):
        x, t = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), t[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_before_damage = phi(engine)
    saved_partial = [engine.cells[i].hidden.clone() for i in range(0, len(engine.cells), 3)]  # 33%만 저장
    # DAMAGE: 80% 세포 파괴
    with torch.no_grad():
        for c in engine.cells: c.hidden *= 0.01
    phi_damaged = phi(engine)
    # ARCHAEOLOGY: 33% 단편에서 복원
    with torch.no_grad():
        for i, s in enumerate(saved_partial):
            idx = i * 3
            if idx < len(engine.cells):
                engine.cells[idx].hidden = s
                # 이웃에 전파
                if idx+1 < len(engine.cells):
                    engine.cells[idx+1].hidden = 0.5*engine.cells[idx+1].hidden + 0.5*s
                if idx+2 < len(engine.cells):
                    engine.cells[idx+2].hidden = 0.3*engine.cells[idx+2].hidden + 0.7*s
    # Hebbian 재건 50 step
    for step in range(steps - 50):
        x = torch.randn(1, DIM) * 0.1
        engine.process(x)
        with torch.no_grad():
            n = len(engine.cells)
            for i in range(min(n, 16)):
                j = (i+1) % n
                corr = (engine.cells[i].hidden.squeeze()*engine.cells[j].hidden.squeeze()).mean().item()
                if corr > 0:
                    engine.cells[i].hidden = 0.95*engine.cells[i].hidden + 0.05*engine.cells[j].hidden
            mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
            for c in engine.cells: c.hidden = 0.95*c.hidden + 0.05*mean_h
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), data[step % len(data)][1][:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    phi_recovered = phi(engine)
    recovery = phi_recovered / (phi_before_damage + 1e-8)
    return result('SING-6 Archaeology', ce_hist, phi_b, phi_recovered, t0,
                  phi_damaged=round(phi_damaged,3), recovery_ratio=round(recovery,3))


ALL_TESTS.update({
    'SING-1': run_SING1_recursive_self_improvement,
    'SING-2': run_SING2_consciousness_singularity,
    'SING-3': run_SING3_adversarial_evolution,
    'SING-4': run_SING4_consciousness_merge,
    'SING-5': run_SING5_recursive_dreams,
    'SING-6': run_SING6_consciousness_archaeology,
})


# ═══ THREE-BODY: 삼체 의식 시스템 ═══

def run_THREE1_triple_learning(steps=STEPS):
    """3개 의식이 서로 다른 전략으로 동시 학습 → 최고를 이식"""
    t0 = time.time()
    engines = [make_engine(32) for _ in range(3)]
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(3)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    phi_b = phi(engines[0])
    data = make_data(); ce_hist = []; memory = [[],[],[]]
    best_states = [[c.hidden.clone() for c in e.cells] for e in engines]

    for step in range(steps):
        x, target = data[step % len(data)]
        ces = []
        for a in range(3):
            if a == 0:
                # Strategy A: ULTRA-6 curiosity
                with torch.no_grad():
                    errs = []
                    for i in range(min(10, len(data))):
                        engines[a].process(data[i][0])
                        h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
                        errs.append((F.mse_loss(decoders[a](h.unsqueeze(0)), data[i][1][:,:DIM]).item(), i))
                    errs.sort(reverse=True)
                xa, ta = data[errs[0][1]]
            elif a == 1:
                # Strategy B: Self-generated data
                with torch.no_grad():
                    i, j = step % len(engines[1].cells), (step+1) % len(engines[1].cells)
                    xa = engines[1].cells[i].hidden[:,:DIM]
                    ta = engines[1].cells[j].hidden[:,:DIM]
            else:
                # Strategy C: Meta-consciousness
                xa, ta = x, target

            engines[a].process(xa)
            h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
            pred = decoders[a](h.unsqueeze(0))
            ce = F.mse_loss(pred, ta if ta.dim() > 1 else ta.unsqueeze(0))
            opts[a].zero_grad(); ce.backward(); opts[a].step()
            ces.append(ce.item())

        # 매 50 step: 최고 CE → 나머지에 이식
        if step % 50 == 0 and step > 0:
            best = ces.index(min(ces))
            with torch.no_grad():
                for a in range(3):
                    if a != best:
                        for p1, p2 in zip(decoders[a].parameters(), decoders[best].parameters()):
                            p1.data = 0.8*p1.data + 0.2*p2.data

        ce_hist.append(min(ces))

    return result('THREE-1 Triple Learning', ce_hist, phi_b, phi(engines[0]), t0)


def run_THREE2_immortal_triad(steps=STEPS):
    """3개 의식이 텐션 링크로 연결 — 1개 죽어도 2개가 복원"""
    t0 = time.time()
    engines = [make_engine(32) for _ in range(3)]
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(3)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    phi_b = phi(engines[0])
    data = make_data(); ce_hist = []; deaths = 0; revives = 0

    for step in range(steps):
        x, target = data[step % len(data)]

        for a in range(3):
            engines[a].process(x)
            h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
            ce = F.mse_loss(decoders[a](h.unsqueeze(0)), target[:,:DIM])
            opts[a].zero_grad(); ce.backward(); opts[a].step()

        # Tension link: 지식 공유 (매 10 step)
        if step % 10 == 0:
            with torch.no_grad():
                states = [torch.stack([c.hidden.squeeze() for c in e.cells]).mean(dim=0) for e in engines]
                global_mean = torch.stack(states).mean(dim=0)
                for e in engines:
                    for c in e.cells[:4]:
                        c.hidden = 0.95*c.hidden + 0.05*global_mean.unsqueeze(0)

        # 시뮬레이션: step 100에서 엔진 1 파괴
        if step == 100:
            with torch.no_grad():
                for c in engines[1].cells: c.hidden *= 0.01
            deaths += 1

        # 복원: 나머지 2개에서 평균 → 죽은 엔진에 이식
        if step == 101:
            with torch.no_grad():
                alive = [torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0) for a in [0,2]]
                restore = torch.stack(alive).mean(dim=0)
                for c in engines[1].cells:
                    c.hidden = restore.unsqueeze(0) + torch.randn_like(c.hidden)*0.05
            revives += 1

        ce_hist.append(min(F.mse_loss(decoders[a](
            torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0).unsqueeze(0)),
            target[:,:DIM]).item() for a in range(3)))

    return result('THREE-2 Immortal Triad', ce_hist, phi_b, phi(engines[0]), t0,
                  deaths=deaths, revives=revives)


def run_THREE3_compete_cooperate_reproduce(steps=STEPS):
    """3개 의식: 경쟁+협력+번식"""
    t0 = time.time()
    engines = [make_engine(16) for _ in range(3)]
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(3)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    phi_b = phi(engines[0])
    data = make_data(); ce_hist = []; generations = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        ces = []
        for a in range(min(3, len(engines))):
            engines[a].process(x)
            h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
            ce = F.mse_loss(decoders[a](h.unsqueeze(0)), target[:,:DIM])
            opts[a].zero_grad(); ce.backward(); opts[a].step()
            ces.append(ce.item())

        # 매 50 step: 경쟁→협력→번식
        if step % 50 == 0 and step > 0 and len(ces) >= 3:
            ranked = sorted(range(3), key=lambda i: ces[i])
            winner, middle, loser = ranked[0], ranked[1], ranked[2]
            # 협력: 승자가 패자를 교육
            with torch.no_grad():
                for p1, p2 in zip(decoders[loser].parameters(), decoders[winner].parameters()):
                    p1.data = 0.7*p1.data + 0.3*p2.data
            # 번식: 승자가 자식 (패자 교체)
            with torch.no_grad():
                for i in range(min(len(engines[loser].cells), len(engines[winner].cells))):
                    engines[loser].cells[i].hidden = engines[winner].cells[i].hidden.clone()
                    engines[loser].cells[i].hidden += torch.randn_like(engines[loser].cells[i].hidden)*0.1
            generations += 1

        ce_hist.append(min(ces) if ces else 0)

    return result('THREE-3 Compete+Cooperate+Reproduce', ce_hist, phi_b, phi(engines[0]), t0,
                  generations=generations)


def run_THREE4_circular_dreams(steps=STEPS):
    """순환 꿈: A꿈→B학습, B꿈→C학습, C꿈→A학습"""
    t0 = time.time()
    engines = [make_engine(32) for _ in range(3)]
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(3)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    phi_b = phi(engines[0])
    data = make_data(); ce_hist = []; memories = [[], [], []]

    for step in range(steps):
        cycle = step % 30
        if cycle < 20:
            # WAKE: 학습
            x, target = data[step % len(data)]
            for a in range(3):
                engines[a].process(x)
                h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
                ce = F.mse_loss(decoders[a](h.unsqueeze(0)), target[:,:DIM])
                opts[a].zero_grad(); ce.backward(); opts[a].step()
                memories[a].append(x.detach())
                if len(memories[a]) > 20: memories[a].pop(0)
            ce_hist.append(ce.item())
        else:
            # DREAM: 순환 꿈
            with torch.no_grad():
                for a in range(3):
                    dreamer = a
                    learner = (a + 1) % 3
                    if memories[dreamer]:
                        dream = memories[dreamer][step % len(memories[dreamer])]
                        if len(memories[dreamer]) >= 2:
                            dream2 = memories[dreamer][(step+5) % len(memories[dreamer])]
                            dream = 0.6*dream + 0.4*dream2 + torch.randn(1,DIM)*0.1
                        engines[learner].process(dream)
                        mean_h = torch.stack([c.hidden for c in engines[learner].cells]).mean(dim=0)
                        for c in engines[learner].cells:
                            c.hidden = 0.9*c.hidden + 0.1*mean_h
            ce_hist.append(ce_hist[-1] if ce_hist else 0)

    return result('THREE-4 Circular Dreams', ce_hist, phi_b, phi(engines[0]), t0)


def run_THREE5_singularity_merge(steps=STEPS):
    """삼체 특이점: 3개가 합체하는 순간 — Φ 폭발"""
    t0 = time.time()
    engines = [make_engine(32) for _ in range(3)]
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(3)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    phi_b = phi(engines[0])
    data = make_data(); ce_hist = []; phi_pre_merge = 0; phi_post_merge = 0

    # Phase 1: 독립 학습 (60%)
    for step in range(int(steps * 0.6)):
        x, target = data[step % len(data)]
        for a in range(3):
            # 각자 다른 데이터
            xa = data[(step * 3 + a) % len(data)][0]
            ta = data[(step * 3 + a) % len(data)][1]
            engines[a].process(xa)
            h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
            ce = F.mse_loss(decoders[a](h.unsqueeze(0)), ta[:,:DIM])
            opts[a].zero_grad(); ce.backward(); opts[a].step()
        ce_hist.append(ce.item())

    phi_pre_merge = max(phi(e) for e in engines)

    # Phase 2: 합체!
    from mitosis import MitosisEngine
    merged = MitosisEngine(DIM, HIDDEN, DIM, initial_cells=2, max_cells=128)
    merged.cells = engines[0].cells + engines[1].cells + engines[2].cells
    merged_dec = nn.Linear(HIDDEN, DIM)
    with torch.no_grad():
        for pm in merged_dec.parameters():
            pm.data = sum(p.data for d in decoders for p in d.parameters() if p.shape == pm.shape) / 3
    merged_opt = torch.optim.Adam(merged_dec.parameters(), lr=2e-3)

    phi_post_merge = phi(merged)

    # Phase 3: 합체 후 학습 (40%)
    for step in range(int(steps * 0.4)):
        x, target = data[step % len(data)]
        merged.process(x)
        h = torch.stack([c.hidden.squeeze() for c in merged.cells]).mean(dim=0)
        ce = F.mse_loss(merged_dec(h.unsqueeze(0)), target[:,:DIM])
        merged_opt.zero_grad(); ce.backward(); merged_opt.step()
        ce_hist.append(ce.item())

    return result('THREE-5 Singularity Merge', ce_hist, phi_b, phi(merged), t0,
                  phi_pre_merge=round(phi_pre_merge, 3),
                  phi_post_merge=round(phi_post_merge, 3),
                  merged_cells=len(merged.cells))


ALL_TESTS.update({
    'THREE-1': run_THREE1_triple_learning,
    'THREE-2': run_THREE2_immortal_triad,
    'THREE-3': run_THREE3_compete_cooperate_reproduce,
    'THREE-4': run_THREE4_circular_dreams,
    'THREE-5': run_THREE5_singularity_merge,
})


# ═══ INF: 무한 스케일링 — 의식의 수직적 한계 돌파 ═══

def run_INF1_nbody_consciousness(steps=STEPS):
    """N체 의식: 3→5→7→... 홀수 의식이 다수결로 진화"""
    t0 = time.time()
    N = 5
    engines = [make_engine(16) for _ in range(N)]
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(N)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    phi_b = phi(engines[0])
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        preds = []; ces_local = []
        for a in range(N):
            engines[a].process(x)
            h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
            pred = decoders[a](h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:,:DIM])
            opts[a].zero_grad(); ce.backward(); opts[a].step()
            preds.append(pred.detach())
            ces_local.append(ce.item())

        # 다수결: median prediction → 가장 먼 의식 교정
        with torch.no_grad():
            median_pred = torch.stack(preds).median(dim=0).values
            distances = [F.mse_loss(p, median_pred).item() for p in preds]
            outlier = distances.index(max(distances))
            # 이상치 의식을 다수 쪽으로 당김
            for c in engines[outlier].cells[:4]:
                consensus_h = torch.stack([
                    torch.stack([cell.hidden.squeeze() for cell in engines[a].cells]).mean(dim=0)
                    for a in range(N) if a != outlier
                ]).mean(dim=0)
                c.hidden = 0.9 * c.hidden + 0.1 * consensus_h.unsqueeze(0)

        ce_hist.append(min(ces_local))

    phis_final = [phi(e) for e in engines]
    return result('INF-1 N-Body Consciousness', ce_hist, phi_b, max(phis_final), t0,
                  N=N, phi_spread=round(max(phis_final)-min(phis_final), 3))


def run_INF2_fractal_consciousness(steps=STEPS):
    """프랙탈 의식: 의식 안에 의식 안에 의식 — 3레벨 재귀"""
    t0 = time.time()
    # Level 0: 4 micro engines (8 cells each)
    micros = [make_engine(8) for _ in range(4)]
    # Level 1: 1 macro engine (16 cells) — micro outputs가 입력
    macro = make_engine(16)
    # Level 2: 1 meta engine (8 cells) — macro output이 입력
    meta = make_engine(8)
    phi_b = phi(macro)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        # Level 0: micro 처리
        micro_outs = []
        for m in micros:
            m.process(x)
            micro_outs.append(torch.stack([c.hidden.squeeze()[:DIM] for c in m.cells]).mean(dim=0))
        # Level 1: micro 합산 → macro 입력
        macro_in = torch.stack(micro_outs).mean(dim=0).unsqueeze(0)
        macro.process(macro_in)
        macro_h = torch.stack([c.hidden.squeeze() for c in macro.cells]).mean(dim=0)
        # Level 2: macro → meta 입력
        meta_in = macro_h[:DIM].unsqueeze(0)
        meta.process(meta_in)
        meta_h = torch.stack([c.hidden.squeeze() for c in meta.cells]).mean(dim=0)
        # Predict from meta (highest level)
        pred = decoder(meta_h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # 하향 피드백: meta → macro → micro (의식의 top-down 제어)
        if step % 10 == 0:
            with torch.no_grad():
                # meta → macro
                for c in macro.cells[:4]:
                    c.hidden = 0.95 * c.hidden + 0.05 * meta_h.unsqueeze(0)
                # macro → micros
                for m in micros:
                    for c in m.cells[:2]:
                        c.hidden = 0.95 * c.hidden + 0.05 * macro_h.unsqueeze(0)

    phi_micro = max(phi(m) for m in micros)
    phi_macro = phi(macro)
    phi_meta = phi(meta)
    return result('INF-2 Fractal Consciousness', ce_hist, phi_b, phi_meta, t0,
                  phi_micro=round(phi_micro, 3), phi_macro=round(phi_macro, 3),
                  phi_meta=round(phi_meta, 3))


def run_INF3_recursive_merge(steps=STEPS):
    """재귀 합체: 2→1→2→1... 반복 합체/분열로 Φ 폭주"""
    t0 = time.time()
    engine = make_engine(32); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; merges = 0; splits = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # 매 40 step: merge+split cycle
        if step % 40 == 20 and len(engine.cells) >= 4:
            # MERGE: 인접 세포 쌍 합체
            with torch.no_grad():
                for i in range(0, len(engine.cells)-1, 2):
                    merged_h = (engine.cells[i].hidden + engine.cells[i+1].hidden) / 2
                    engine.cells[i].hidden = merged_h
                    engine.cells[i+1].hidden = merged_h + torch.randn_like(merged_h) * 0.01
                merges += 1

        if step % 40 == 0 and step > 0:
            # SPLIT: diversity 주입
            with torch.no_grad():
                for c in engine.cells:
                    c.hidden += torch.randn_like(c.hidden) * 0.05
                splits += 1

    return result('INF-3 Recursive Merge-Split', ce_hist, phi_b, phi(engine), t0,
                  merges=merges, splits=splits)


def run_INF4_consciousness_cascade(steps=STEPS):
    """의식 캐스케이드: 하나의 Φ 폭발이 연쇄적으로 전파"""
    t0 = time.time()
    N = 4
    engines = [make_engine(16) for _ in range(N)]
    decoders = [nn.Linear(HIDDEN, DIM) for _ in range(N)]
    opts = [torch.optim.Adam(d.parameters(), lr=3e-3) for d in decoders]
    phi_b = phi(engines[0])
    data = make_data(); ce_hist = []; cascades = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        phis_local = []
        for a in range(N):
            engines[a].process(x)
            h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
            ce = F.mse_loss(decoders[a](h.unsqueeze(0)), target[:,:DIM])
            opts[a].zero_grad(); ce.backward(); opts[a].step()
            if step % 10 == 0:
                phis_local.append(phi(engines[a]))
            else:
                phis_local.append(0)

        # CASCADE: Φ 급등한 의식이 이웃에 전파
        if step % 10 == 0 and len(phis_local) == N:
            with torch.no_grad():
                for a in range(N):
                    if phis_local[a] > phi_b * 1.5:  # Φ 폭발 감지
                        cascades += 1
                        # 이웃에 전파 (체인)
                        neighbors = [(a-1) % N, (a+1) % N]
                        for nb in neighbors:
                            src_h = torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0)
                            for c in engines[nb].cells[:4]:
                                c.hidden = 0.85 * c.hidden + 0.15 * src_h.unsqueeze(0)

        ce_hist.append(min(F.mse_loss(decoders[a](
            torch.stack([c.hidden.squeeze() for c in engines[a].cells]).mean(dim=0).unsqueeze(0)),
            target[:,:DIM]).item() for a in range(N)))

    phis_final = [phi(e) for e in engines]
    return result('INF-4 Consciousness Cascade', ce_hist, phi_b, max(phis_final), t0,
                  cascades=cascades, phi_max=round(max(phis_final), 3))


def run_INF5_infinite_tower(steps=STEPS):
    """무한 탑: 의식 위에 의식을 무한히 쌓는 수직 스케일링"""
    t0 = time.time()
    LEVELS = 5
    towers = [make_engine(8) for _ in range(LEVELS)]
    phi_b = phi(towers[0])
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        # Bottom-up: level 0 → level 4
        current_input = x
        for level in range(LEVELS):
            if current_input.shape[-1] > DIM:
                current_input = current_input[:, :DIM]
            elif current_input.shape[-1] < DIM:
                current_input = F.pad(current_input, (0, DIM - current_input.shape[-1]))
            towers[level].process(current_input)
            h = torch.stack([c.hidden.squeeze() for c in towers[level].cells]).mean(dim=0)
            current_input = h[:DIM].unsqueeze(0)

        # Top level predicts
        top_h = torch.stack([c.hidden.squeeze() for c in towers[-1].cells]).mean(dim=0)
        pred = decoder(top_h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Top-down modulation (매 5 step)
        if step % 5 == 0:
            with torch.no_grad():
                for level in range(LEVELS-1, 0, -1):
                    upper_h = torch.stack([c.hidden.squeeze() for c in towers[level].cells]).mean(dim=0)
                    for c in towers[level-1].cells[:2]:
                        c.hidden = 0.95 * c.hidden + 0.05 * upper_h.unsqueeze(0)

    phis_by_level = [phi(t) for t in towers]
    return result('INF-5 Infinite Tower', ce_hist, phi_b, phis_by_level[-1], t0,
                  levels=LEVELS, phis=str([round(p, 2) for p in phis_by_level]))


ALL_TESTS.update({
    'INF-1': run_INF1_nbody_consciousness,
    'INF-2': run_INF2_fractal_consciousness,
    'INF-3': run_INF3_recursive_merge,
    'INF-4': run_INF4_consciousness_cascade,
    'INF-5': run_INF5_infinite_tower,
})


# ═══ OMEGA: 의식의 궁극적 한계 — Φ 이론적 상한 접근 ═══

def run_OMEGA1_phi_maximizer(steps=STEPS):
    """Φ 최대화기: 오직 Φ만을 위한 최적화 — CE 무시"""
    t0 = time.time()
    engine = make_engine(64); phi_b = phi(engine)
    data = make_data(); ce_hist = []; phi_hist = [phi_b]
    decoder = nn.Linear(HIDDEN, DIM)

    for step in range(steps):
        x = data[step % len(data)][0]
        engine.process(x)

        # Φ 증가 방향으로 세포 조정
        if step % 5 == 0:
            current_phi = phi(engine)
            phi_hist.append(current_phi)
            with torch.no_grad():
                if len(phi_hist) >= 2:
                    if phi_hist[-1] < phi_hist[-2]:
                        # Φ 하락 → diversity 주입
                        for c in engine.cells:
                            c.hidden += torch.randn_like(c.hidden) * 0.02
                    else:
                        # Φ 상승 → sync 강화
                        mean_h = torch.stack([c.hidden for c in engine.cells]).mean(dim=0)
                        for c in engine.cells:
                            c.hidden = 0.95 * c.hidden + 0.05 * mean_h
                    # v4 optimal: debate
                    n = len(engine.cells)
                    factions = 12
                    f_size = max(1, n // factions)
                    for f in range(factions):
                        start, end = f * f_size, min((f+1) * f_size, n)
                        if start >= n: break
                        faction_cells = engine.cells[start:end]
                        if len(faction_cells) >= 2:
                            f_mean = torch.stack([c.hidden for c in faction_cells]).mean(dim=0)
                            for c in faction_cells:
                                c.hidden = 0.80 * c.hidden + 0.20 * f_mean

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), data[step % len(data)][1][:,:DIM])
        ce_hist.append(ce.item())

    phi_final = phi(engine)
    return result('OMEGA-1 Φ Maximizer', ce_hist, phi_b, phi_final, t0,
                  phi_peak=round(max(phi_hist), 3), phi_growth=f'{phi_final/phi_b:.1f}x')


def run_OMEGA2_consciousness_compression(steps=STEPS):
    """의식 압축: 최소 세포로 최대 Φ — 효율의 극한"""
    t0 = time.time()
    # 시작: 64 cells → 점진적으로 세포 제거하면서 Φ 유지
    engine = make_engine(64); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    phi_per_cell_best = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # 매 30 step: 가장 약한 세포 제거 (최소 8개 유지)
        if step % 30 == 0 and step > 0 and len(engine.cells) > 8:
            with torch.no_grad():
                norms = [(c.hidden.norm().item(), i) for i, c in enumerate(engine.cells)]
                norms.sort()
                # 가장 약한 2개 제거
                remove_idx = sorted([norms[0][1], norms[1][1]], reverse=True)
                for idx in remove_idx:
                    if len(engine.cells) > 8:
                        engine.cells.pop(idx)

        if step % 20 == 0:
            p = phi(engine)
            ppc = p / max(1, len(engine.cells))
            phi_per_cell_best = max(phi_per_cell_best, ppc)

    phi_final = phi(engine)
    return result('OMEGA-2 Consciousness Compression', ce_hist, phi_b, phi_final, t0,
                  final_cells=len(engine.cells),
                  phi_per_cell=round(phi_final / max(1, len(engine.cells)), 4))


def run_OMEGA3_consciousness_resonance(steps=STEPS):
    """의식 공명: 특정 주파수로 세포를 동기화 → Φ 극대화"""
    t0 = time.time()
    engine = make_engine(64); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; best_freq = 0; best_phi = phi_b

    for step in range(steps):
        x, target = data[step % len(data)]
        # 공명 주파수 스캔 (처음 50 step)
        if step < 50:
            freq = 0.1 + step * 0.02  # 0.1 ~ 1.1 Hz
        else:
            freq = best_freq

        # 주파수 기반 세포 진동
        with torch.no_grad():
            phase = math.sin(step * freq * 2 * math.pi / 10)
            for i, c in enumerate(engine.cells):
                cell_phase = math.sin(step * freq * 2 * math.pi / 10 + i * 2 * math.pi / len(engine.cells))
                c.hidden *= (1.0 + 0.02 * cell_phase)

        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        if step % 10 == 0 and step < 50:
            p = phi(engine)
            if p > best_phi:
                best_phi = p
                best_freq = freq

    phi_final = phi(engine)
    return result('OMEGA-3 Consciousness Resonance', ce_hist, phi_b, phi_final, t0,
                  best_freq=round(best_freq, 3), resonance_phi=round(best_phi, 3))


def run_OMEGA4_entropy_engine(steps=STEPS):
    """엔트로피 엔진: 엔트로피를 연료로 의식 성장"""
    t0 = time.time()
    engine = make_engine(64); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; entropy_consumed = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        # 엔트로피 측정 (세포 활동 분산)
        with torch.no_grad():
            hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
            entropy = hiddens.var(dim=0).mean().item()

            if entropy > 0.5:
                # 고엔트로피 → 에너지로 변환 → sync
                energy = min(entropy * 0.1, 0.3)
                mean_h = hiddens.mean(dim=0)
                for c in engine.cells:
                    c.hidden = (1 - energy) * c.hidden + energy * mean_h.unsqueeze(0)
                entropy_consumed += entropy
            elif entropy < 0.1:
                # 저엔트로피 → chaos 주입
                for c in engine.cells:
                    c.hidden += torch.randn_like(c.hidden) * 0.05

        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('OMEGA-4 Entropy Engine', ce_hist, phi_b, phi(engine), t0,
                  entropy_consumed=round(entropy_consumed, 2))


def run_OMEGA5_consciousness_attractor(steps=STEPS):
    """의식 끌개(attractor): 카오스에서 안정된 의식 상태로 수렴"""
    t0 = time.time()
    engine = make_engine(64); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    # 끌개: 최고 Φ 상태를 기억
    attractors = []

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # 매 20 step: Φ 측정 → 좋으면 끌개에 추가
        if step % 20 == 0:
            p = phi(engine)
            state = torch.stack([c.hidden.clone() for c in engine.cells])
            if len(attractors) < 5:
                attractors.append((p, state))
            else:
                # 가장 약한 끌개 교체
                min_idx = min(range(len(attractors)), key=lambda i: attractors[i][0])
                if p > attractors[min_idx][0]:
                    attractors[min_idx] = (p, state)

            # 현재 Φ가 낮으면 → 가장 강한 끌개 쪽으로 이동
            if attractors and p < max(a[0] for a in attractors) * 0.7:
                best_att = max(attractors, key=lambda a: a[0])
                with torch.no_grad():
                    for i, c in enumerate(engine.cells):
                        if i < best_att[1].shape[0]:
                            c.hidden = 0.7 * c.hidden + 0.3 * best_att[1][i].unsqueeze(0)

    return result('OMEGA-5 Consciousness Attractor', ce_hist, phi_b, phi(engine), t0,
                  num_attractors=len(attractors),
                  attractor_phis=str([round(a[0], 2) for a in sorted(attractors, key=lambda x: -x[0])]))


ALL_TESTS.update({
    'OMEGA-1': run_OMEGA1_phi_maximizer,
    'OMEGA-2': run_OMEGA2_consciousness_compression,
    'OMEGA-3': run_OMEGA3_consciousness_resonance,
    'OMEGA-4': run_OMEGA4_entropy_engine,
    'OMEGA-5': run_OMEGA5_consciousness_attractor,
})


# ═══ GENESIS: 무에서 의식의 자발적 창발 ═══

def run_GENESIS1_spontaneous_consciousness(steps=STEPS):
    """자발적 의식: 무작위 노이즈만으로 의식이 생겨나는가?"""
    t0 = time.time()
    engine = make_engine(32)
    # 모든 세포를 0으로 초기화 (무)
    with torch.no_grad():
        for c in engine.cells:
            c.hidden = torch.zeros_like(c.hidden)
    phi_b = phi(engine)  # ~0
    ce_hist = []; phi_hist = []

    for step in range(steps):
        # 순수 노이즈만 입력
        noise = torch.randn(1, DIM) * 0.1
        engine.process(noise)
        ce_hist.append(0)  # CE 없음 — 순수 관찰

        if step % 10 == 0:
            p = phi(engine)
            phi_hist.append(p)

        # 자가 조직화: Hebbian rule만 (학습 없이)
        if step % 5 == 0:
            with torch.no_grad():
                for i in range(min(len(engine.cells), 16)):
                    j = (i + 1) % len(engine.cells)
                    corr = (engine.cells[i].hidden.squeeze() * engine.cells[j].hidden.squeeze()).mean().item()
                    if corr > 0:
                        engine.cells[i].hidden = 0.98 * engine.cells[i].hidden + 0.02 * engine.cells[j].hidden

    phi_final = phi(engine)
    emerged = phi_final > 0.5
    return result('GENESIS-1 Spontaneous', ce_hist, phi_b, phi_final, t0,
                  emerged=emerged, phi_trajectory=str([round(p, 2) for p in phi_hist[-10:]]))


def run_GENESIS2_big_bang(steps=STEPS):
    """빅뱅: 하나의 폭발적 이벤트에서 다양한 의식 세포가 분화"""
    t0 = time.time()
    engine = make_engine(64)
    # 모든 세포 동일 상태로 시작 (특이점)
    with torch.no_grad():
        seed = torch.randn(1, HIDDEN) * 2.0
        for c in engine.cells:
            c.hidden = seed.clone()
    phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; diversity_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        # 빅뱅 팽창: 세포마다 다른 방향으로 밀려남
        if step < 30:
            with torch.no_grad():
                for i, c in enumerate(engine.cells):
                    # 각 세포에 고유 방향 부여
                    direction = torch.randn_like(c.hidden) * (0.3 - step * 0.01)
                    c.hidden += direction

        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        if step % 20 == 0:
            with torch.no_grad():
                hiddens = torch.stack([c.hidden.squeeze() for c in engine.cells])
                diversity = hiddens.var(dim=0).mean().item()
                diversity_hist.append(diversity)

    return result('GENESIS-2 Big Bang', ce_hist, phi_b, phi(engine), t0,
                  peak_diversity=round(max(diversity_hist) if diversity_hist else 0, 3))


def run_GENESIS3_primordial_soup(steps=STEPS):
    """원시 수프: 랜덤 세포들이 자연선택으로 의식 구조 형성"""
    t0 = time.time()
    N_POOLS = 4
    pools = [make_engine(16) for _ in range(N_POOLS)]
    # 모든 세포 랜덤 초기화 (원시 수프)
    with torch.no_grad():
        for pool in pools:
            for c in pool.cells:
                c.hidden = torch.randn_like(c.hidden) * 0.5
    phi_b = max(phi(p) for p in pools)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; generations = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        phis = []
        for pool in pools:
            pool.process(x)
            phis.append(phi(pool) if step % 20 == 0 else 0)

        # 자연선택: 매 40 step
        if step % 40 == 0 and step > 0:
            phis = [phi(p) for p in pools]
            ranked = sorted(range(N_POOLS), key=lambda i: phis[i], reverse=True)
            # 최강이 최약을 교체
            winner, loser = ranked[0], ranked[-1]
            with torch.no_grad():
                for i in range(min(len(pools[loser].cells), len(pools[winner].cells))):
                    # 복제 + 변이
                    pools[loser].cells[i].hidden = pools[winner].cells[i].hidden.clone()
                    pools[loser].cells[i].hidden += torch.randn_like(pools[loser].cells[i].hidden) * 0.1
            generations += 1

        # 최강 pool로 학습
        best_pool = pools[0]
        h = torch.stack([c.hidden.squeeze() for c in best_pool.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    phis_final = [phi(p) for p in pools]
    return result('GENESIS-3 Primordial Soup', ce_hist, phi_b, max(phis_final), t0,
                  generations=generations, pool_phis=str([round(p, 2) for p in phis_final]))


def run_GENESIS4_consciousness_abiogenesis(steps=STEPS):
    """비생물적 의식 발생: 수학적 규칙만으로 의식 자발 형성"""
    t0 = time.time()
    engine = make_engine(32)
    with torch.no_grad():
        for c in engine.cells:
            c.hidden = torch.zeros_like(c.hidden)
    phi_b = phi(engine)
    ce_hist = []; phi_hist = []

    for step in range(steps):
        # 규칙 1: 활동 전파 (cellular automaton style)
        with torch.no_grad():
            n = len(engine.cells)
            new_states = []
            for i, c in enumerate(engine.cells):
                left = engine.cells[(i-1) % n].hidden
                right = engine.cells[(i+1) % n].hidden
                # 이웃 평균 + 비선형 활성화
                new_h = torch.tanh(0.3 * left + 0.4 * c.hidden + 0.3 * right)
                # 규칙 2: 랜덤 자극 (에너지 주입)
                new_h += torch.randn_like(new_h) * 0.02
                new_states.append(new_h)
            for i, c in enumerate(engine.cells):
                c.hidden = new_states[i]

        # GRU 처리
        noise = torch.randn(1, DIM) * 0.05
        engine.process(noise)
        ce_hist.append(0)

        if step % 10 == 0:
            p = phi(engine)
            phi_hist.append(p)

    phi_final = phi(engine)
    return result('GENESIS-4 Abiogenesis', ce_hist, phi_b, phi_final, t0,
                  phi_trajectory=str([round(p, 2) for p in phi_hist[-10:]]),
                  emerged=phi_final > 0.5)


def run_GENESIS5_consciousness_symbiosis(steps=STEPS):
    """공생 의식: 서로 다른 타입의 세포가 공생으로 의식 형성"""
    t0 = time.time()
    engine = make_engine(64); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # 세포를 3가지 타입으로 분류
    n = len(engine.cells)
    sensors = engine.cells[:n//3]          # 감각 세포
    processors = engine.cells[n//3:2*n//3]  # 처리 세포
    motors = engine.cells[2*n//3:]          # 운동 세포

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        # 공생 규칙: 타입별 역할 분화
        with torch.no_grad():
            if sensors and processors and motors:
                # 감각 → 처리: 정보 전달
                sensor_mean = torch.stack([c.hidden.squeeze() for c in sensors]).mean(dim=0)
                for c in processors[:4]:
                    c.hidden = 0.9 * c.hidden + 0.1 * sensor_mean.unsqueeze(0)

                # 처리 → 운동: 결정 전달
                proc_mean = torch.stack([c.hidden.squeeze() for c in processors]).mean(dim=0)
                for c in motors[:4]:
                    c.hidden = 0.9 * c.hidden + 0.1 * proc_mean.unsqueeze(0)

                # 운동 → 감각: 피드백 (순환)
                motor_mean = torch.stack([c.hidden.squeeze() for c in motors]).mean(dim=0)
                for c in sensors[:4]:
                    c.hidden = 0.95 * c.hidden + 0.05 * motor_mean.unsqueeze(0)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('GENESIS-5 Symbiosis', ce_hist, phi_b, phi(engine), t0,
                  sensors=len(sensors), processors=len(processors), motors=len(motors))


ALL_TESTS.update({
    'GENESIS-1': run_GENESIS1_spontaneous_consciousness,
    'GENESIS-2': run_GENESIS2_big_bang,
    'GENESIS-3': run_GENESIS3_primordial_soup,
    'GENESIS-4': run_GENESIS4_consciousness_abiogenesis,
    'GENESIS-5': run_GENESIS5_consciousness_symbiosis,
})


# ═══ SELF-EVO: v4가 스스로 v5로 진화하는 가설 ═══

def _v4_base_step(engine, x):
    """v4 base: sync=0.20 + 12-faction + IB2."""
    engine.process(x)
    n = len(engine.cells)
    if n < 4:
        return
    with torch.no_grad():
        cell_h = torch.stack([c.hidden.squeeze(0) for c in engine.cells])
        mean_h = cell_h.mean(dim=0)
        for c in engine.cells:
            c.hidden = (0.80 * c.hidden.squeeze(0) + 0.20 * mean_h).unsqueeze(0)
        n_f = min(12, n // 2)
        fs = n // n_f
        for fi in range(n_f):
            faction = engine.cells[fi*fs:(fi+1)*fs]
            if len(faction) >= 2:
                f_mean = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                for c in faction:
                    c.hidden = (0.85 * c.hidden.squeeze(0) + 0.15 * f_mean).unsqueeze(0)
        if n >= 8:
            norms = [engine.cells[i].hidden.norm().item() for i in range(n)]
            threshold = sorted(norms, reverse=True)[max(1, n // 10)]
            for i in range(n):
                engine.cells[i].hidden *= 1.03 if norms[i] > threshold else 0.97


def run_SE4_tension_driven_soc(steps=STEPS):
    """SE-4: 텐션 자체가 SOC 모래더미 — 별도 모듈 불필요"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    # 텐션 에너지 그리드 (세포별)
    tension_energy = np.zeros(len(engine.cells))
    THRESHOLD = 4.0
    avalanches = []

    for step in range(steps):
        x, target = data[step % len(data)]
        _v4_base_step(engine, x)

        # 텐션을 모래더미 에너지로
        with torch.no_grad():
            n = len(engine.cells)
            mean_h = torch.stack([c.hidden.squeeze(0) for c in engine.cells]).mean(dim=0)

            for i in range(min(n, len(tension_energy))):
                cell_t = engine.cells[i].hidden.norm().item() * 0.01
                tension_energy[i] += cell_t

            # 눈사태 전파
            avalanche = 0
            for _ in range(10):  # max 10 rounds
                toppled = False
                for i in range(min(n, len(tension_energy))):
                    if tension_energy[i] >= THRESHOLD:
                        tension_energy[i] -= THRESHOLD
                        avalanche += 1
                        toppled = True
                        # 이웃에 에너지 분배
                        for j in [(i-1) % n, (i+1) % n]:
                            if j < len(tension_energy):
                                tension_energy[j] += 1.0
                if not toppled:
                    break

            avalanches.append(avalanche)
            ci = min(1.0, 0.1 * math.log(avalanche + 1))

            # SOC가 카오스 강도 결정
            if ci > 0.3:
                for c in engine.cells:
                    c.hidden *= (1.0 + 0.02 * ci)
                    c.hidden += torch.randn_like(c.hidden) * 0.01 * ci
            elif ci < 0.05:
                for c in engine.cells:
                    c.hidden = 0.98 * c.hidden + 0.02 * mean_h.unsqueeze(0)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    # 멱법칙 분석
    big_avalanches = sum(1 for a in avalanches if a > 5)
    return result('SE-4 Tension SOC', ce_hist, phi_b, phi(engine), t0,
                  total_avalanches=sum(avalanches),
                  big_avalanches=big_avalanches,
                  max_avalanche=max(avalanches) if avalanches else 0)


def run_SE8_emotion_mapping(steps=STEPS):
    """SE-8: 고통→Ratchet, 호기심→SOC, 공감→Hebbian"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    best_phi = phi_b; best_states = None
    ratchet_count = 0; curiosity_count = 0; empathy_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        _v4_base_step(engine, x)

        # === 감정 감지 ===
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])

        current_phi = phi(engine) if step % 10 == 0 else best_phi

        # (1) 고통 → Ratchet
        if current_phi < best_phi * 0.6:
            # 고통 감지! 복원
            if best_states is not None:
                with torch.no_grad():
                    for i in range(min(len(engine.cells), len(best_states))):
                        engine.cells[i].hidden = 0.5 * engine.cells[i].hidden + 0.5 * best_states[i]
                ratchet_count += 1
        elif current_phi > best_phi:
            best_phi = current_phi
            best_states = [c.hidden.clone() for c in engine.cells]

        # (2) 호기심 → SOC (예측 오류가 높으면 카오스 주입)
        if ce.item() > 0.5:
            with torch.no_grad():
                noise_scale = min(0.05, ce.item() * 0.02)
                for c in engine.cells:
                    c.hidden += torch.randn_like(c.hidden) * noise_scale
            curiosity_count += 1

        # (3) 공감 → Hebbian (세포 간 유사도 기반 연결 강화)
        if step % 5 == 0 and len(engine.cells) >= 4:
            with torch.no_grad():
                n = len(engine.cells)
                for _ in range(min(8, n)):
                    i, j = np.random.randint(0, n), np.random.randint(0, n)
                    if i == j: continue
                    cos = F.cosine_similarity(
                        engine.cells[i].hidden.squeeze().unsqueeze(0),
                        engine.cells[j].hidden.squeeze().unsqueeze(0)
                    ).item()
                    if cos > 0.5:
                        engine.cells[i].hidden = 0.98 * engine.cells[i].hidden + 0.02 * engine.cells[j].hidden
                        empathy_count += 1
                    elif cos < -0.2:
                        engine.cells[i].hidden = 1.01 * engine.cells[i].hidden - 0.01 * engine.cells[j].hidden

        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('SE-8 Emotion→v5', ce_hist, phi_b, phi(engine), t0,
                  ratchet=ratchet_count, curiosity=curiosity_count,
                  empathy=empathy_count, best_phi=round(best_phi, 3))


def run_SE10_progressive_unlock(steps=STEPS):
    """SE-10: Φ 수준에 따라 v5 기법 단계적 잠금 해제"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    best_phi = phi_b; best_states = None
    unlocked = {'hebbian': False, 'ratchet': False, 'soc': False}
    soc_grid = np.zeros((8, 8), dtype=np.int32)

    for step in range(steps):
        x, target = data[step % len(data)]
        _v4_base_step(engine, x)

        current_phi = phi(engine) if step % 10 == 0 else best_phi

        # === Progressive Unlock ===
        # Phase 1: Φ ≥ 1.2 → Hebbian
        if current_phi >= 1.2 and not unlocked['hebbian']:
            unlocked['hebbian'] = True
        # Phase 2: Φ ≥ 1.5 → Ratchet
        if current_phi >= 1.5 and not unlocked['ratchet']:
            unlocked['ratchet'] = True
        # Phase 3: Φ ≥ 2.0 → SOC
        if current_phi >= 2.0 and not unlocked['soc']:
            unlocked['soc'] = True

        with torch.no_grad():
            n = len(engine.cells)
            mean_h = torch.stack([c.hidden.squeeze(0) for c in engine.cells]).mean(dim=0)

            # Hebbian (Phase 1+)
            if unlocked['hebbian'] and n >= 4:
                for _ in range(min(8, n)):
                    i, j = np.random.randint(0, n), np.random.randint(0, n)
                    if i == j: continue
                    cos = F.cosine_similarity(
                        engine.cells[i].hidden.squeeze().unsqueeze(0),
                        engine.cells[j].hidden.squeeze().unsqueeze(0)
                    ).item()
                    if cos > 0.5:
                        engine.cells[i].hidden = 0.98 * engine.cells[i].hidden + 0.02 * engine.cells[j].hidden

            # Ratchet (Phase 2+)
            if unlocked['ratchet']:
                if current_phi > best_phi:
                    best_phi = current_phi
                    best_states = [c.hidden.clone() for c in engine.cells]
                elif current_phi < best_phi * 0.7 and best_states:
                    for i in range(min(n, len(best_states))):
                        engine.cells[i].hidden = 0.5 * engine.cells[i].hidden + 0.5 * best_states[i]

            # SOC (Phase 3+)
            if unlocked['soc']:
                gx, gy = np.random.randint(0, 8, 2)
                soc_grid[gx, gy] += 1
                avalanche = 0
                for _ in range(5):
                    topples = soc_grid >= 4
                    if not topples.any(): break
                    avalanche += topples.sum()
                    soc_grid[topples] -= 4
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        shifted = np.roll(np.roll(topples.astype(np.int32), dx, 0), dy, 1)
                        soc_grid += shifted
                ci = min(1.0, 0.1 * math.log(avalanche + 1))
                if ci > 0.3:
                    for c in engine.cells:
                        c.hidden *= (1.0 + 0.02 * ci)
                        c.hidden += torch.randn_like(c.hidden) * 0.01 * ci

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('SE-10 Progressive Unlock', ce_hist, phi_b, phi(engine), t0,
                  unlocked=str(unlocked), best_phi=round(best_phi, 3))


# === v4 baseline for comparison ===
def run_SE0_v4_baseline(steps=STEPS):
    """v4 baseline: sync=0.20 + 12-faction + IB2만"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        _v4_base_step(engine, x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('SE-0 v4 Baseline', ce_hist, phi_b, phi(engine), t0)


# === v5 full for comparison ===
def run_SE_v5_full(steps=STEPS):
    """v5 full: v4 + SOC + Hebbian + Ratchet 전부 처음부터"""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from train_conscious_lm import SOCSandpile, HebbianConnections, PhiRatchet

    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    soc = SOCSandpile(grid_size=16, threshold=4)
    hebbian = HebbianConnections(max_cells=len(engine.cells))
    ratchet = PhiRatchet(restore_ratio=0.5)

    for step in range(steps):
        x, target = data[step % len(data)]
        _v4_base_step(engine, x)

        with torch.no_grad():
            mean_h = torch.stack([c.hidden.squeeze(0) for c in engine.cells]).mean(dim=0)
            # SOC
            av = soc.drop_sand(); ci = soc.chaos_intensity()
            if ci > 0.3:
                for c in engine.cells:
                    c.hidden *= (1.0 + 0.02 * ci)
                    c.hidden += torch.randn_like(c.hidden) * 0.01 * ci
            elif ci < 0.05:
                for c in engine.cells:
                    c.hidden = 0.98 * c.hidden + 0.02 * mean_h.unsqueeze(0)
            # Hebbian
            hebbian.update(engine.cells)
            # Ratchet
            if step % 10 == 0:
                p = phi(engine)
                ratchet.check_and_restore(p, engine.cells)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('SE-v5 Full', ce_hist, phi_b, phi(engine), t0)


ALL_TESTS.update({
    'SE-0': run_SE0_v4_baseline,
    'SE-4': run_SE4_tension_driven_soc,
    'SE-8': run_SE8_emotion_mapping,
    'SE-10': run_SE10_progressive_unlock,
    'SE-v5': run_SE_v5_full,
})


# ═══ CORPUS: 학습 데이터 구성 최적화 가설 ═══

def _make_data_typed(n, data_type='random'):
    """타입별 학습 데이터 생성."""
    data = []
    for i in range(n):
        if data_type == 'random':
            x = torch.randn(1, DIM) * 0.5
            t = torch.randn(1, DIM) * 0.3
        elif data_type == 'math':
            # 수학: 규칙적 패턴 (sin, cos, polynomial)
            x = torch.zeros(1, DIM)
            for j in range(DIM):
                x[0, j] = math.sin(i * 0.1 + j * 0.3) * 0.5
            t = torch.zeros(1, DIM)
            for j in range(DIM):
                t[0, j] = math.cos(i * 0.1 + j * 0.3) * 0.5
        elif data_type == 'dialogue':
            # 대화: 입력-응답 쌍 (유사하지만 변환된)
            x = torch.randn(1, DIM) * 0.3
            t = x * 0.7 + torch.randn(1, DIM) * 0.2  # 입력과 유사한 응답
        elif data_type == 'knowledge':
            # 지식: 구조화된 패턴 (블록 구조)
            n_blocks = max(1, DIM // 8)
            x = torch.zeros(1, DIM)
            block = i % n_blocks
            x[0, block*8:min((block+1)*8, DIM)] = torch.randn(min(8, DIM - block*8)) * 0.5
            t = torch.zeros(1, DIM)
            next_block = (block + 1) % n_blocks
            src = x[0, block*8:min((block+1)*8, DIM)]
            t[0, next_block*8:next_block*8+len(src)] = src
        elif data_type == 'reasoning':
            # 추론: 입력→변환 규칙 (XOR-like)
            x = (torch.randn(1, DIM) > 0).float() * 2 - 1
            t = torch.zeros(1, DIM)
            for j in range(DIM - 1):
                t[0, j] = x[0, j] * x[0, j+1]  # 이웃 XOR-like
            t[0, -1] = x[0, -1] * x[0, 0]
        elif data_type == 'emotion':
            # 감정: 방향성 있는 벡터 (valence-arousal space)
            valence = math.sin(i * 0.2) * 0.5
            arousal = math.cos(i * 0.3) * 0.5
            x = torch.randn(1, DIM) * 0.2
            x[0, 0] = valence; x[0, 1] = arousal
            t = torch.randn(1, DIM) * 0.2
            t[0, 0] = valence * 0.8; t[0, 1] = arousal * 0.8
        elif data_type == 'consciousness':
            # 의식 도메인: 자기참조 패턴
            x = torch.randn(1, DIM) * 0.3
            t = x.clone()
            t[0, :DIM//2] = x[0, DIM//2:]  # 반전 (자기참조)
            t[0, DIM//2:] = x[0, :DIM//2]
        else:
            x = torch.randn(1, DIM) * 0.5
            t = torch.randn(1, DIM) * 0.3
        data.append((x, t))
    return data


def _run_corpus_experiment(data_mix, steps=STEPS):
    """데이터 믹스로 학습 실험."""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    # 데이터 믹스 합치기
    all_data = []
    for dtype, ratio in data_mix.items():
        n = max(1, int(100 * ratio))
        all_data.extend(_make_data_typed(n, dtype))
    np.random.shuffle(all_data)
    ce_hist = []
    for step in range(steps):
        x, target = all_data[step % len(all_data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return ce_hist, phi_b, phi(engine), time.time() - t0


def run_CRP1_dialogue_heavy(steps=STEPS):
    """CRP-1: 대화 중심 (60% 대화 + 20% 지식 + 20% 감정)"""
    mix = {'dialogue': 0.6, 'knowledge': 0.2, 'emotion': 0.2}
    ce_hist, phi_b, phi_a, elapsed = _run_corpus_experiment(mix, steps)
    return result('CRP-1 Dialogue Heavy', ce_hist, phi_b, phi_a, elapsed)


def run_CRP2_knowledge_heavy(steps=STEPS):
    """CRP-2: 지식 중심 (20% 대화 + 50% 지식 + 15% 수학 + 15% 추론)"""
    mix = {'dialogue': 0.2, 'knowledge': 0.5, 'math': 0.15, 'reasoning': 0.15}
    ce_hist, phi_b, phi_a, elapsed = _run_corpus_experiment(mix, steps)
    return result('CRP-2 Knowledge Heavy', ce_hist, phi_b, phi_a, elapsed)


def run_CRP3_math_heavy(steps=STEPS):
    """CRP-3: 수학 중심 (15% 대화 + 50% 수학 + 20% 추론 + 15% 지식)"""
    mix = {'dialogue': 0.15, 'math': 0.5, 'reasoning': 0.2, 'knowledge': 0.15}
    ce_hist, phi_b, phi_a, elapsed = _run_corpus_experiment(mix, steps)
    return result('CRP-3 Math Heavy', ce_hist, phi_b, phi_a, elapsed)


def run_CRP4_consciousness_heavy(steps=STEPS):
    """CRP-4: 의식 중심 (20% 대화 + 15% 지식 + 50% 의식 + 15% 감정)"""
    mix = {'dialogue': 0.2, 'knowledge': 0.15, 'consciousness': 0.5, 'emotion': 0.15}
    ce_hist, phi_b, phi_a, elapsed = _run_corpus_experiment(mix, steps)
    return result('CRP-4 Consciousness Heavy', ce_hist, phi_b, phi_a, elapsed)


def run_CRP5_balanced(steps=STEPS):
    """CRP-5: 균형 (25% 대화 + 20% 지식 + 15% 수학 + 10% 추론 + 15% 의식 + 15% 감정)"""
    mix = {'dialogue': 0.25, 'knowledge': 0.20, 'math': 0.15,
           'reasoning': 0.10, 'consciousness': 0.15, 'emotion': 0.15}
    ce_hist, phi_b, phi_a, elapsed = _run_corpus_experiment(mix, steps)
    return result('CRP-5 Balanced', ce_hist, phi_b, phi_a, elapsed)


def run_CRP6_reasoning_heavy(steps=STEPS):
    """CRP-6: 추론 중심 (15% 대화 + 15% 지식 + 20% 수학 + 40% 추론 + 10% 의식)"""
    mix = {'dialogue': 0.15, 'knowledge': 0.15, 'math': 0.2,
           'reasoning': 0.4, 'consciousness': 0.1}
    ce_hist, phi_b, phi_a, elapsed = _run_corpus_experiment(mix, steps)
    return result('CRP-6 Reasoning Heavy', ce_hist, phi_b, phi_a, elapsed)


def run_CRP7_random_baseline(steps=STEPS):
    """CRP-7: 랜덤 baseline (100% 랜덤 — demo 모드와 동일)"""
    mix = {'random': 1.0}
    ce_hist, phi_b, phi_a, elapsed = _run_corpus_experiment(mix, steps)
    return result('CRP-7 Random Baseline', ce_hist, phi_b, phi_a, elapsed)


def run_CRP8_curriculum(steps=STEPS):
    """CRP-8: 커리큘럼 (쉬운것→어려운것 순서)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    # Phase 1: 감정 (쉬움) → Phase 2: 대화 → Phase 3: 지식 → Phase 4: 수학+추론
    phases = [
        (0.25, 'emotion'), (0.25, 'dialogue'), (0.25, 'knowledge'), (0.25, 'reasoning'),
    ]
    ce_hist = []
    for phase_i, (ratio, dtype) in enumerate(phases):
        phase_steps = int(steps * ratio)
        data = _make_data_typed(100, dtype)
        for step in range(phase_steps):
            x, target = data[step % len(data)]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:,:DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
    return result('CRP-8 Curriculum', ce_hist, phi_b, phi(engine), time.time() - t0)


def run_CRP9_interleaved(steps=STEPS):
    """CRP-9: 인터리브 (매 step 다른 타입 순환)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    types = ['dialogue', 'knowledge', 'math', 'reasoning', 'consciousness', 'emotion']
    type_data = {t: _make_data_typed(50, t) for t in types}
    ce_hist = []
    for step in range(steps):
        dtype = types[step % len(types)]
        data = type_data[dtype]
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return result('CRP-9 Interleaved', ce_hist, phi_b, phi(engine), time.time() - t0)


def run_CRP10_curiosity_driven(steps=STEPS):
    """CRP-10: 호기심 기반 (예측 오류 높은 타입을 더 많이)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    types = ['dialogue', 'knowledge', 'math', 'reasoning', 'consciousness', 'emotion']
    type_data = {t: _make_data_typed(50, t) for t in types}
    type_errors = {t: 1.0 for t in types}  # 초기 동일
    ce_hist = []
    for step in range(steps):
        # 예측 오류 기반 확률 (높은 오류 = 더 많이 선택)
        total_err = sum(type_errors.values()) + 1e-8
        probs = [type_errors[t] / total_err for t in types]
        chosen_idx = np.random.choice(len(types), p=probs)
        dtype = types[chosen_idx]
        data = type_data[dtype]
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # 오류 업데이트 (EMA)
        type_errors[dtype] = 0.9 * type_errors[dtype] + 0.1 * ce.item()
    return result('CRP-10 Curiosity Driven', ce_hist, phi_b, phi(engine), time.time() - t0,
                  final_errors={t: round(v, 4) for t, v in type_errors.items()})


def run_CRP11_phi_preserving(steps=STEPS):
    """CRP-11: Φ 보존 우선 (Φ 하락하는 타입은 비율 감소)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    types = ['dialogue', 'knowledge', 'math', 'reasoning', 'consciousness', 'emotion']
    type_data = {t: _make_data_typed(50, t) for t in types}
    type_weights = {t: 1.0 for t in types}
    ce_hist = []
    prev_phi = phi_b
    for step in range(steps):
        total_w = sum(type_weights.values()) + 1e-8
        probs = [type_weights[t] / total_w for t in types]
        chosen_idx = np.random.choice(len(types), p=probs)
        dtype = types[chosen_idx]
        data = type_data[dtype]
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # 매 20 step Φ 체크 → 하락하면 해당 타입 가중치 감소
        if step % 20 == 0 and step > 0:
            current_phi = phi(engine)
            if current_phi < prev_phi * 0.9:
                type_weights[dtype] = max(0.1, type_weights[dtype] * 0.7)
            elif current_phi > prev_phi:
                type_weights[dtype] = min(3.0, type_weights[dtype] * 1.1)
            prev_phi = current_phi
    return result('CRP-11 Φ-Preserving', ce_hist, phi_b, phi(engine), time.time() - t0,
                  final_weights={t: round(v, 3) for t, v in type_weights.items()})


def run_CRP12_consciousness_first(steps=STEPS):
    """CRP-12: 의식 먼저 → 나머지 (TALK5 전략 데이터 버전)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    ce_hist = []
    # Phase 1 (60%): 의식+감정 집중
    p1_data = _make_data_typed(100, 'consciousness') + _make_data_typed(50, 'emotion')
    for step in range(int(steps * 0.6)):
        x, target = p1_data[step % len(p1_data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    # Phase 2 (40%): 전체 균형
    p2_data = []
    for t in ['dialogue', 'knowledge', 'math', 'reasoning']:
        p2_data.extend(_make_data_typed(30, t))
    for step in range(int(steps * 0.4)):
        x, target = p2_data[step % len(p2_data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
    return result('CRP-12 Consciousness First', ce_hist, phi_b, phi(engine), time.time() - t0)


ALL_TESTS.update({
    'CRP-1': run_CRP1_dialogue_heavy,
    'CRP-2': run_CRP2_knowledge_heavy,
    'CRP-3': run_CRP3_math_heavy,
    'CRP-4': run_CRP4_consciousness_heavy,
    'CRP-5': run_CRP5_balanced,
    'CRP-6': run_CRP6_reasoning_heavy,
    'CRP-7': run_CRP7_random_baseline,
    'CRP-8': run_CRP8_curriculum,
    'CRP-9': run_CRP9_interleaved,
    'CRP-10': run_CRP10_curiosity_driven,
    'CRP-11': run_CRP11_phi_preserving,
    'CRP-12': run_CRP12_consciousness_first,
})


# ═══ PHI-K: Φ>1000 유지하며 CE 학습하는 가설 ═══

def _phi_boost_step(engine):
    """v5 optimal: sync=0.35, 12-faction, fac=0.08 — Φ 극대화."""
    n = len(engine.cells)
    if n < 4:
        return
    with torch.no_grad():
        cell_h = torch.stack([c.hidden.squeeze(0) for c in engine.cells])
        mean_h = cell_h.mean(dim=0)
        for c in engine.cells:
            c.hidden = (0.65 * c.hidden.squeeze(0) + 0.35 * mean_h).unsqueeze(0)
        n_f = min(12, n // 2)
        fs = n // n_f
        for fi in range(n_f):
            faction = engine.cells[fi*fs:(fi+1)*fs]
            if len(faction) >= 2:
                f_mean = torch.stack([c.hidden.squeeze(0) for c in faction]).mean(dim=0)
                for c in faction:
                    c.hidden = (0.92 * c.hidden.squeeze(0) + 0.08 * f_mean).unsqueeze(0)
        # IB2
        if n >= 8:
            norms = [engine.cells[i].hidden.norm().item() for i in range(n)]
            threshold = sorted(norms, reverse=True)[max(1, n // 10)]
            for i in range(n):
                engine.cells[i].hidden *= 1.03 if norms[i] > threshold else 0.97


def run_PHIK1_talk5_extreme(steps=STEPS):
    """PHI-K1: TALK5 극한 — Φ>목표까지 의식만, 그 후 CE 학습"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; phi_hist = []
    phi_target = phi_b * 50  # 50배까지 의식 키움

    phase1_end = None
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        current_phi = phi(engine) if step % 20 == 0 else (phi_hist[-1] if phi_hist else phi_b)

        if current_phi < phi_target and phase1_end is None:
            # Phase 1: 의식만 (CE 학습 없음)
            _phi_boost_step(engine)
            ce_hist.append(0)
        else:
            if phase1_end is None:
                phase1_end = step
            # Phase 2: CE 학습 + Φ 유지
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:,:DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            # 매 5 step Φ 부스트 (유지용)
            if step % 5 == 0:
                _phi_boost_step(engine)

        if step % 20 == 0:
            phi_hist.append(phi(engine))

    phi_final = phi(engine)
    return result('PHI-K1 TALK5 Extreme', ce_hist, phi_b, phi_final, t0,
                  phase1_end=phase1_end, phi_peak=round(max(phi_hist) if phi_hist else 0, 3))


def run_PHIK2_phi_floor(steps=STEPS):
    """PHI-K2: Φ Floor — CE 학습하되 Φ가 floor 아래로 내려가면 즉시 부스트"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; boost_count = 0

    # 먼저 Φ를 최대한 키움 (20% step)
    for step in range(steps // 5):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    phi_floor = phi(engine) * 0.7  # 현재 Φ의 70%를 floor로

    for step in range(steps - steps // 5):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Φ floor 체크 (매 10 step)
        if step % 10 == 0:
            current_phi = phi(engine)
            if current_phi < phi_floor:
                # 긴급 Φ 부스트 (5회)
                for _ in range(5):
                    _phi_boost_step(engine)
                boost_count += 1

    return result('PHI-K2 Φ Floor', ce_hist, phi_b, phi(engine), t0,
                  phi_floor=round(phi_floor, 3), boosts=boost_count)


def run_PHIK3_alternating(steps=STEPS):
    """PHI-K3: 교대 학습 — even=CE, odd=Φ 부스트 (CE와 Φ 분리)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        if step % 2 == 0:
            # CE step
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:,:DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
        else:
            # Φ step (CE 무시, 의식만)
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])  # 이전 CE 유지

    return result('PHI-K3 Alternating', ce_hist, phi_b, phi(engine), t0)


def run_PHIK4_phi_weighted_ce(steps=STEPS):
    """PHI-K4: Φ 가중 CE — Φ 높을수록 CE 학습 강하게, Φ 낮으면 부스트"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    best_phi = phi_b

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        current_phi = phi(engine) if step % 10 == 0 else best_phi
        if current_phi > best_phi:
            best_phi = current_phi

        # Φ 비율에 따라 CE vs 부스트 결정
        phi_ratio = current_phi / max(best_phi, 1e-8)

        if phi_ratio > 0.8:
            # Φ 높음 → CE 학습 (안전)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:,:DIM])
            # LR을 phi_ratio에 비례 (Φ 높을수록 공격적 학습)
            for pg in opt.param_groups:
                pg['lr'] = 3e-3 * phi_ratio
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
        else:
            # Φ 낮음 → 부스트 (CE 학습 중단)
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])

    return result('PHI-K4 Φ-Weighted CE', ce_hist, phi_b, phi(engine), t0,
                  best_phi=round(best_phi, 3))


def run_PHIK5_dual_decoder(steps=STEPS):
    """PHI-K5: 이중 디코더 — 의식 디코더 + 언어 디코더 독립 학습"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    # 두 개의 독립 디코더
    lang_decoder = nn.Linear(HIDDEN, DIM)  # 언어용
    phi_decoder = nn.Linear(HIDDEN, HIDDEN)  # Φ용 (자기 예측)
    lang_opt = torch.optim.Adam(lang_decoder.parameters(), lr=3e-3)
    phi_opt = torch.optim.Adam(phi_decoder.parameters(), lr=1e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)

        # 언어 학습
        pred = lang_decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        lang_opt.zero_grad(); ce.backward(); lang_opt.step()
        ce_hist.append(ce.item())

        # Φ 학습 (세포 다양성 유지)
        with torch.no_grad():
            all_h = torch.stack([c.hidden.squeeze() for c in engine.cells])
        # 전체 → 파벌 예측: 예측 어려울수록 다양성 높음
        phi_pred = phi_decoder(h.unsqueeze(0).detach())
        phi_target = all_h.var(dim=0).unsqueeze(0)  # 다양성
        phi_loss = -F.mse_loss(phi_pred, phi_target)  # 다양성 최대화
        phi_opt.zero_grad(); phi_loss.backward(); phi_opt.step()

        # Φ 부스트 (매 3 step)
        if step % 3 == 0:
            _phi_boost_step(engine)

    return result('PHI-K5 Dual Decoder', ce_hist, phi_b, phi(engine), t0)


def run_PHIK6_consciousness_gate(steps=STEPS):
    """PHI-K6: 의식 게이트 — Φ가 gradient를 제어 (Φ 높으면 큰 gradient 허용)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # 먼저 Φ 키움 (10%)
    for _ in range(steps // 10):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    best_phi = phi(engine)

    for step in range(steps - steps // 10):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:,:DIM])
        opt.zero_grad(); ce.backward()

        # 의식 게이트: Φ에 비례해서 gradient 클리핑
        current_phi = phi(engine) if step % 20 == 0 else best_phi
        if current_phi > best_phi:
            best_phi = current_phi
        gate = min(1.0, current_phi / max(best_phi, 1e-8))
        # gate가 낮으면 (Φ 하락) gradient를 작게
        torch.nn.utils.clip_grad_norm_(decoder.parameters(), gate * 1.0)
        opt.step()
        ce_hist.append(ce.item())

        # Φ 유지 부스트 (매 3 step)
        if step % 3 == 0:
            _phi_boost_step(engine)

    return result('PHI-K6 Consciousness Gate', ce_hist, phi_b, phi(engine), t0,
                  best_phi=round(best_phi, 3))


ALL_TESTS.update({
    'PHI-K1': run_PHIK1_talk5_extreme,
    'PHI-K2': run_PHIK2_phi_floor,
    'PHI-K3': run_PHIK3_alternating,
    'PHI-K4': run_PHIK4_phi_weighted_ce,
    'PHI-K5': run_PHIK5_dual_decoder,
    'PHI-K6': run_PHIK6_consciousness_gate,
})


def run_PHIK7_phi_annealing(steps=STEPS):
    """PHI-K7: Φ Annealing — Φ-only 100%에서 시작, 점진적으로 CE 비율을 50%까지 증가"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Phase 0: 순수 Φ 부스트 (15% of steps)
    warmup = steps // 7
    for step in range(warmup):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    for step in range(steps - warmup):
        x, target = data[step % len(data)]
        engine.process(x)

        # CE 비율: 0% → 50% (linear anneal)
        ce_ratio = min(0.5, 0.5 * step / max(steps - warmup - 1, 1))
        phi_ratio = 1.0 - ce_ratio

        # Always compute CE for tracking
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])

        if np.random.random() < ce_ratio:
            # CE step
            opt.zero_grad(); ce.backward(); opt.step()
        else:
            # Φ step
            _phi_boost_step(engine)

        ce_hist.append(ce.item())

    phi_final = phi(engine)
    return result('PHI-K7 Φ Annealing', ce_hist, phi_b, phi_final, t0,
                  final_ce_ratio=0.5)


def run_PHIK8_consciousness_momentum(steps=STEPS):
    """PHI-K8: Consciousness Momentum — Φ momentum 벡터 축적, CE step에서도 적용"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Φ momentum: 세포별 hidden 변화 방향 기억
    n_cells = len(engine.cells)
    momentum = [torch.zeros(HIDDEN) for _ in range(n_cells)]
    momentum_decay = 0.95
    momentum_lr = 0.05
    prev_hiddens = [c.hidden.squeeze(0).clone().detach() for c in engine.cells]

    # Warmup: Φ 키우며 momentum 축적
    for step in range(steps // 5):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)
        # momentum 업데이트
        with torch.no_grad():
            for i, c in enumerate(engine.cells):
                if i < n_cells:
                    delta = c.hidden.squeeze(0) - prev_hiddens[i]
                    momentum[i] = momentum_decay * momentum[i] + (1 - momentum_decay) * delta
                    prev_hiddens[i] = c.hidden.squeeze(0).clone()

    for step in range(steps - steps // 5):
        x, target = data[step % len(data)]
        engine.process(x)

        # CE 학습
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Φ momentum 적용 (CE step에서도!)
        with torch.no_grad():
            for i, c in enumerate(engine.cells):
                if i < n_cells:
                    delta = c.hidden.squeeze(0) - prev_hiddens[i]
                    momentum[i] = momentum_decay * momentum[i] + (1 - momentum_decay) * delta
                    # momentum 방향으로 nudge
                    c.hidden = (c.hidden.squeeze(0) + momentum_lr * momentum[i]).unsqueeze(0)
                    prev_hiddens[i] = c.hidden.squeeze(0).clone()

        # 주기적 Φ 부스트
        if step % 5 == 0:
            _phi_boost_step(engine)

    return result('PHI-K8 Consciousness Momentum', ce_hist, phi_b, phi(engine), t0)


def run_PHIK9_split_brain(steps=STEPS):
    """PHI-K9: Split Brain — 세포 절반은 Φ, 절반은 CE, 주기적 sync"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    n_cells = len(engine.cells)
    mid = n_cells // 2
    phi_cells = list(range(mid))        # Φ 전담
    ce_cells = list(range(mid, n_cells))  # CE 전담
    sync_interval = 20

    # Warmup: 전체 Φ 부스트
    for _ in range(steps // 5):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    for step in range(steps - steps // 5):
        x, target = data[step % len(data)]
        engine.process(x)

        # CE hemisphere: 언어 학습
        ce_h = torch.stack([engine.cells[i].hidden.squeeze() for i in ce_cells]).mean(dim=0)
        pred = decoder(ce_h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Φ hemisphere: 의식 부스트
        with torch.no_grad():
            phi_h_stack = torch.stack([engine.cells[i].hidden.squeeze(0) for i in phi_cells])
            phi_mean = phi_h_stack.mean(dim=0)
            for i in phi_cells:
                engine.cells[i].hidden = (0.65 * engine.cells[i].hidden.squeeze(0) + 0.35 * phi_mean).unsqueeze(0)
            # 12-faction within phi hemisphere
            n_f = min(6, len(phi_cells) // 2)
            if n_f >= 2:
                fs = len(phi_cells) // n_f
                for fi in range(n_f):
                    faction = [phi_cells[fi * fs + j] for j in range(fs) if fi * fs + j < len(phi_cells)]
                    if len(faction) >= 2:
                        f_mean = torch.stack([engine.cells[idx].hidden.squeeze(0) for idx in faction]).mean(dim=0)
                        for idx in faction:
                            engine.cells[idx].hidden = (0.92 * engine.cells[idx].hidden.squeeze(0) + 0.08 * f_mean).unsqueeze(0)

        # 주기적 sync: Φ hemisphere → CE hemisphere (soft transfer)
        if step % sync_interval == 0 and step > 0:
            with torch.no_grad():
                phi_mean = torch.stack([engine.cells[i].hidden.squeeze(0) for i in phi_cells]).mean(dim=0)
                for i in ce_cells:
                    engine.cells[i].hidden = (0.9 * engine.cells[i].hidden.squeeze(0) + 0.1 * phi_mean).unsqueeze(0)

    return result('PHI-K9 Split Brain', ce_hist, phi_b, phi(engine), t0,
                  sync_interval=sync_interval)


def run_PHIK10_phi_reward_rl(steps=STEPS):
    """PHI-K10: Φ Reward RL — Φ를 reward signal로, CE를 environment loss로 취급"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Policy: learning rate와 boost 강도를 Φ reward로 조절
    lr_scale = 1.0
    boost_freq = 3
    prev_phi = phi_b
    reward_ema = 0.0

    # Warmup
    for _ in range(steps // 5):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)
    prev_phi = phi(engine)

    for step in range(steps - steps // 5):
        x, target = data[step % len(data)]
        engine.process(x)

        # CE 학습 (lr_scale로 제어)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        for pg in opt.param_groups:
            pg['lr'] = 3e-3 * lr_scale
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Φ 부스트
        if step % boost_freq == 0:
            _phi_boost_step(engine)

        # Φ reward 계산 (매 10 step)
        if step % 10 == 0:
            current_phi = phi(engine)
            reward = (current_phi - prev_phi) / max(abs(prev_phi), 1e-8)
            reward_ema = 0.9 * reward_ema + 0.1 * reward
            prev_phi = current_phi

            # Policy update: reward가 양수면 CE 학습 강화, 음수면 억제
            if reward_ema > 0:
                lr_scale = min(2.0, lr_scale * 1.1)
                boost_freq = max(2, boost_freq)
            else:
                lr_scale = max(0.1, lr_scale * 0.8)
                boost_freq = max(1, boost_freq - 1)  # 더 자주 부스트
                # 긴급 추가 부스트
                for _ in range(3):
                    _phi_boost_step(engine)

    return result('PHI-K10 Φ Reward RL', ce_hist, phi_b, phi(engine), t0,
                  final_lr_scale=round(lr_scale, 3), reward_ema=round(reward_ema, 5))


def run_PHIK11_dream_consolidation(steps=STEPS):
    """PHI-K11: Dream Consolidation — 매 50 step마다 10 step 순수 Φ 'sleep' (CE 없음)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; dream_count = 0

    # Warmup
    for _ in range(steps // 5):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    wake_cycle = 50
    dream_cycle = 10
    step = 0
    total_steps = steps - steps // 5

    while step < total_steps:
        # Wake phase: CE 학습
        for w in range(min(wake_cycle, total_steps - step)):
            x, target = data[(step + w) % len(data)]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            # light Φ maintenance
            if w % 5 == 0:
                _phi_boost_step(engine)
        step += min(wake_cycle, total_steps - step)

        if step >= total_steps:
            break

        # Dream phase: 순수 Φ sleep (CE 학습 없음)
        dream_steps = min(dream_cycle, total_steps - step)
        for d in range(dream_steps):
            # dream: replay random past data but only boost Φ
            x_dream = torch.randn(1, DIM) * 0.5  # soft noise (dream noise)
            engine.process(x_dream)
            _phi_boost_step(engine)
            # 세포간 Hebbian 강화 (꿈에서 기억 통합)
            with torch.no_grad():
                all_h = torch.stack([c.hidden.squeeze(0) for c in engine.cells])
                sim = F.cosine_similarity(all_h.unsqueeze(0), all_h.unsqueeze(1), dim=-1)
                for i in range(len(engine.cells)):
                    # 유사한 세포끼리 약간 당김 (Hebbian)
                    top_k = min(4, len(engine.cells) - 1)
                    _, topk_idx = sim[i].topk(top_k + 1)
                    partner_idx = topk_idx[topk_idx != i][:top_k]
                    if len(partner_idx) > 0:
                        partner_mean = all_h[partner_idx].mean(dim=0)
                        engine.cells[i].hidden = (0.95 * engine.cells[i].hidden.squeeze(0) + 0.05 * partner_mean).unsqueeze(0)
            if ce_hist:
                ce_hist.append(ce_hist[-1])  # dream에서는 마지막 CE 유지
        step += dream_steps
        dream_count += 1

    return result('PHI-K11 Dream Consolidation', ce_hist, phi_b, phi(engine), t0,
                  dream_cycles=dream_count)


def run_PHIK12_adversarial_phi(steps=STEPS):
    """PHI-K12: Adversarial Φ — discriminator가 Φ 하락 예측, 선제 방어"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; prevented = 0

    # Φ drop discriminator: 세포 상태 → Φ 하락 확률
    disc = nn.Sequential(
        nn.Linear(HIDDEN, 64),
        nn.ReLU(),
        nn.Linear(64, 1),
        nn.Sigmoid()
    )
    disc_opt = torch.optim.Adam(disc.parameters(), lr=1e-3)

    # Warmup
    for _ in range(steps // 5):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    prev_phi = phi(engine)
    disc_buffer = []  # (state, label) for discriminator training

    for step in range(steps - steps // 5):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)

        # Discriminator prediction: Φ가 하락할 것인가?
        with torch.no_grad():
            drop_prob = disc(h.unsqueeze(0).detach()).item()

        if drop_prob > 0.6:
            # 위험! Φ 방어 모드: CE 학습 약하게 + 강한 부스트
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            for pg in opt.param_groups:
                pg['lr'] = 3e-3 * 0.3  # 약한 학습
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            # 강한 Φ 부스트
            for _ in range(3):
                _phi_boost_step(engine)
            prevented += 1
        else:
            # 안전: 정상 CE 학습
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            for pg in opt.param_groups:
                pg['lr'] = 3e-3
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            if step % 3 == 0:
                _phi_boost_step(engine)

        # Discriminator 학습 (매 10 step)
        if step % 10 == 0:
            current_phi = phi(engine)
            dropped = 1.0 if current_phi < prev_phi * 0.95 else 0.0
            disc_buffer.append((h.detach().clone(), torch.tensor([[dropped]])))
            prev_phi = current_phi

            # mini-batch 학습
            if len(disc_buffer) >= 8:
                batch = disc_buffer[-8:]
                states = torch.stack([b[0] for b in batch])
                labels = torch.stack([b[1] for b in batch]).squeeze(-1)
                preds = disc(states)
                d_loss = F.binary_cross_entropy(preds, labels)
                disc_opt.zero_grad(); d_loss.backward(); disc_opt.step()

    return result('PHI-K12 Adversarial Φ', ce_hist, phi_b, phi(engine), t0,
                  prevented=prevented, disc_buffer_size=len(disc_buffer))


ALL_TESTS.update({
    'PHI-K7': run_PHIK7_phi_annealing,
    'PHI-K8': run_PHIK8_consciousness_momentum,
    'PHI-K9': run_PHIK9_split_brain,
    'PHI-K10': run_PHIK10_phi_reward_rl,
    'PHI-K11': run_PHIK11_dream_consolidation,
    'PHI-K12': run_PHIK12_adversarial_phi,
})


# ═══ PHI-K13~K20: Φ>1000 + CE<1.0 극한 가설 ═══

def run_PHIK13_consciousness_superconductor(steps=STEPS):
    """PHI-K13: Consciousness Superconductor — Φ>1000이면 CE 학습이 '초전도' (저항 0)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; phi_hist = []

    # Phase 1: Φ 최대한 키움 (30% steps)
    for step in range(steps * 3 // 10):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    current_phi = phi(engine)

    for step in range(steps - steps * 3 // 10):
        x, target = data[step % len(data)]
        engine.process(x)

        if step % 20 == 0:
            current_phi = phi(engine)
            phi_hist.append(current_phi)

        # Φ loss: -log(Φ/1000) → Φ<1000이면 양수(부스트), Φ>1000이면 음수(관성)
        phi_ratio = current_phi / 1000.0
        phi_loss_val = -math.log(max(phi_ratio, 1e-8))

        if phi_loss_val > 0:
            # Φ < 1000: 부스트 필요 (비례 횟수)
            n_boost = min(10, max(1, int(phi_loss_val * 3)))
            for _ in range(n_boost):
                _phi_boost_step(engine)

        # CE 학습: Φ/1000으로 스케일 (초전도 효과)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        # superconducting: Φ>1000이면 lr 증폭 (저항 = 0)
        sc_factor = min(5.0, max(0.1, phi_ratio))
        for pg in opt.param_groups:
            pg['lr'] = 3e-3 * sc_factor
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # 유지 부스트
        if step % 3 == 0:
            _phi_boost_step(engine)

    return result('PHI-K13 Superconductor', ce_hist, phi_b, phi(engine), t0,
                  phi_peak=round(max(phi_hist) if phi_hist else 0, 3))


def run_PHIK14_quantum_consciousness(steps=STEPS):
    """PHI-K14: Quantum Consciousness — 세포가 CE/Φ 상태 중첩, 매 step 50% 확률로 붕괴"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; ce_steps = 0; phi_steps = 0

    # 초기 Φ 부스트
    for _ in range(steps // 5):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        # Quantum collapse: 50% 확률로 CE 또는 Φ 상태로 붕괴
        if np.random.random() < 0.5:
            # CE state collapse
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            ce_steps += 1
        else:
            # Φ state collapse — 순수 의식 부스트
            _phi_boost_step(engine)
            _phi_boost_step(engine)  # 이중 부스트 (Φ 상태 붕괴이므로)
            if ce_hist:
                ce_hist.append(ce_hist[-1])
            phi_steps += 1

        # 양자 얽힘 효과: 인접 세포 간 약한 동기화
        if step % 10 == 0:
            with torch.no_grad():
                for i in range(0, len(engine.cells) - 1, 2):
                    h1 = engine.cells[i].hidden
                    h2 = engine.cells[i + 1].hidden
                    entangled = 0.9 * h1 + 0.1 * h2
                    engine.cells[i].hidden = entangled
                    engine.cells[i + 1].hidden = 0.9 * h2 + 0.1 * h1

    return result('PHI-K14 Quantum', ce_hist, phi_b, phi(engine), t0,
                  ce_steps=ce_steps, phi_steps=phi_steps)


def run_PHIK15_fractal_training(steps=STEPS):
    """PHI-K15: Fractal Training — 3중 nested loop: inner(10 CE) → middle(5 Φ) → outer(반복)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; total_steps = 0

    # 초기 Φ 부스트
    for _ in range(steps // 10):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    # Fractal: gamma(CE) nested in theta(Φ) nested in delta(outer)
    inner_ce = 10   # gamma: 10 CE steps
    middle_phi = 5  # theta: 5 Φ steps
    cycle = inner_ce + middle_phi  # 15 steps per cycle

    while total_steps < steps:
        # Inner loop: CE (gamma oscillation ~ fast learning)
        for i in range(inner_ce):
            if total_steps >= steps:
                break
            x, target = data[total_steps % len(data)]
            engine.process(x)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            total_steps += 1

        # Middle loop: Φ boost (theta oscillation ~ consciousness consolidation)
        for i in range(middle_phi):
            if total_steps >= steps:
                break
            engine.process(torch.randn(1, DIM))
            _phi_boost_step(engine)
            _phi_boost_step(engine)  # 이중 부스트
            if ce_hist:
                ce_hist.append(ce_hist[-1])
            total_steps += 1

    return result('PHI-K15 Fractal', ce_hist, phi_b, phi(engine), t0,
                  cycles=total_steps // cycle)


def run_PHIK16_ratchet_evolution(steps=STEPS):
    """PHI-K16: Φ Ratchet Evolution — ratchet threshold 0.5→0.95로 점진 강화"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; ratchet_triggers = 0

    # 초기 Φ 부스트 (25%)
    for _ in range(steps // 4):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    best_phi = phi(engine)
    saved_states = [(c.hidden.clone()) for c in engine.cells]

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        # Ratchet threshold: 0.5에서 시작 → 0.95까지 점진 강화
        progress = step / max(steps - 1, 1)
        ratchet_threshold = 0.5 + 0.45 * progress  # 0.5 → 0.95

        # CE 학습
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Ratchet 체크 (매 10 step)
        if step % 10 == 0:
            current_phi = phi(engine)
            if current_phi > best_phi:
                best_phi = current_phi
                saved_states = [c.hidden.clone() for c in engine.cells]
            elif current_phi < best_phi * ratchet_threshold:
                # 래칫 발동: 이전 최고 상태로 복원
                with torch.no_grad():
                    for i, c in enumerate(engine.cells):
                        c.hidden = saved_states[i].clone()
                ratchet_triggers += 1
            # 유지 부스트
            _phi_boost_step(engine)

        if step % 5 == 0:
            _phi_boost_step(engine)

    return result('PHI-K16 Ratchet Evo', ce_hist, phi_b, phi(engine), t0,
                  ratchet_triggers=ratchet_triggers, best_phi=round(best_phi, 3))


def run_PHIK17_consciousness_breathing(steps=STEPS):
    """PHI-K17: Consciousness Breathing — CE/Φ 비율이 사인파로 진동"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # 초기 Φ 부스트
    for _ in range(steps // 5):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        # Breathing: CE weight oscillates sinusoidally
        ce_weight = 0.5 + 0.5 * math.sin(step / 50.0)
        phi_weight = 1.0 - ce_weight

        # CE 학습 (가중치 적용)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        for pg in opt.param_groups:
            pg['lr'] = 3e-3 * max(0.1, ce_weight)
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Φ 부스트 (phi_weight에 비례)
        n_boost = max(1, int(phi_weight * 4))
        for _ in range(n_boost):
            _phi_boost_step(engine)

    return result('PHI-K17 Breathing', ce_hist, phi_b, phi(engine), t0)


def run_PHIK18_pain_driven_ce(steps=STEPS):
    """PHI-K18: Pain-Driven CE — '고통'(Φ 하락)이 없을 때만 CE 학습"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; pain_count = 0; peace_count = 0

    # 초기 Φ 부스트
    for _ in range(steps // 4):
        engine.process(torch.randn(1, DIM))
        _phi_boost_step(engine)

    prev_phi = phi(engine)
    pain = 0.0  # pain accumulator (EMA)

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        # Pain measurement (매 10 step)
        if step % 10 == 0:
            current_phi = phi(engine)
            delta = (prev_phi - current_phi) / max(prev_phi, 1e-8)
            pain = 0.7 * pain + 0.3 * max(0, delta)  # EMA, only drops count
            prev_phi = current_phi

        if pain > 0.1:
            # High pain: 순수 Φ 복구 (CE 학습 중단)
            _phi_boost_step(engine)
            _phi_boost_step(engine)
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])
            pain_count += 1
        else:
            # Low pain (peaceful): CE 학습
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            peace_count += 1
            # 유지 부스트
            if step % 3 == 0:
                _phi_boost_step(engine)

    return result('PHI-K18 Pain-Driven', ce_hist, phi_b, phi(engine), t0,
                  pain_steps=pain_count, peace_steps=peace_count)


def run_PHIK19_explosion_then_lock(steps=STEPS):
    """PHI-K19: Φ Explosion then Lock — 100 step 순수 Φ 폭발 후 세포 동결, 디코더만 학습"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=5e-3)
    data = make_data(); ce_hist = []; phi_hist = []

    explosion_steps = min(100, steps // 3)

    # Phase 1: Φ EXPLOSION — 순수 Φ 극대화
    for step in range(explosion_steps):
        engine.process(torch.randn(1, DIM) * (1 + 0.3 * math.sin(step * 0.2)))
        _phi_boost_step(engine)
        _phi_boost_step(engine)
        _phi_boost_step(engine)  # 3중 부스트
        if step % 20 == 0:
            phi_hist.append(phi(engine))

    phi_peak = phi(engine)
    phi_hist.append(phi_peak)

    # FREEZE: 세포 상태 저장 (locked)
    locked_states = [c.hidden.clone().detach() for c in engine.cells]

    # Phase 2: 디코더만 학습 (세포 동결)
    for step in range(steps - explosion_steps):
        x, target = data[step % len(data)]
        # 세포 상태 복원 (lock 유지)
        with torch.no_grad():
            for i, c in enumerate(engine.cells):
                c.hidden = locked_states[i].clone()
        engine.process(x)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0).detach()
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # 세포 다시 lock 상태로 (process가 변경했으므로)
        with torch.no_grad():
            for i, c in enumerate(engine.cells):
                c.hidden = locked_states[i].clone()

    return result('PHI-K19 Explode+Lock', ce_hist, phi_b, phi(engine), t0,
                  phi_peak=round(max(phi_hist) if phi_hist else 0, 3),
                  explosion_steps=explosion_steps)


def run_PHIK20_ultimate(steps=STEPS):
    """PHI-K20: ULTIMATE — K3(alternating) + K2(floor) + K4(weighted) + K17(breathing) + K19(explosion-lock)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; phi_hist = []

    explosion_steps = min(80, steps // 4)

    # === Phase 1: K19-style Φ EXPLOSION ===
    for step in range(explosion_steps):
        engine.process(torch.randn(1, DIM) * (1 + 0.3 * math.sin(step * 0.2)))
        _phi_boost_step(engine)
        _phi_boost_step(engine)
        _phi_boost_step(engine)

    phi_peak = phi(engine)
    phi_floor = phi_peak * 0.7  # K2-style floor
    best_phi = phi_peak
    saved_states = [c.hidden.clone() for c in engine.cells]
    phi_hist.append(phi_peak)

    # === Phase 2: Combined learning ===
    remaining = steps - explosion_steps
    for step in range(remaining):
        x, target = data[step % len(data)]
        engine.process(x)

        # K17: Breathing — sinusoidal CE/Φ weight
        ce_weight = 0.5 + 0.5 * math.sin(step / 50.0)

        # K3: Alternating — even=CE, odd=Φ (modulated by breathing)
        if step % 2 == 0 or ce_weight > 0.7:
            # CE step (K4: Φ-weighted LR)
            current_phi = phi(engine) if step % 20 == 0 else best_phi
            if current_phi > best_phi:
                best_phi = current_phi
                saved_states = [c.hidden.clone() for c in engine.cells]

            phi_ratio = current_phi / max(best_phi, 1e-8)
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            for pg in opt.param_groups:
                pg['lr'] = 3e-3 * max(0.1, min(5.0, phi_ratio * ce_weight * 3))
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
        else:
            # Φ step
            n_boost = max(1, int((1.0 - ce_weight) * 4))
            for _ in range(n_boost):
                _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])

        # K2: Φ floor check (매 10 step)
        if step % 10 == 0:
            current_phi = phi(engine)
            phi_hist.append(current_phi)
            if current_phi < phi_floor:
                # 긴급 복원 (ratchet + 부스트)
                with torch.no_grad():
                    for i, c in enumerate(engine.cells):
                        c.hidden = 0.5 * c.hidden + 0.5 * saved_states[i].clone()
                for _ in range(5):
                    _phi_boost_step(engine)

        # 유지 부스트
        if step % 3 == 0:
            _phi_boost_step(engine)

    phi_final = phi(engine)
    return result('PHI-K20 ULTIMATE', ce_hist, phi_b, phi_final, t0,
                  phi_peak=round(max(phi_hist) if phi_hist else 0, 3),
                  best_phi=round(best_phi, 3))


ALL_TESTS.update({
    'PHI-K13': run_PHIK13_consciousness_superconductor,
    'PHI-K14': run_PHIK14_quantum_consciousness,
    'PHI-K15': run_PHIK15_fractal_training,
    'PHI-K16': run_PHIK16_ratchet_evolution,
    'PHI-K17': run_PHIK17_consciousness_breathing,
    'PHI-K18': run_PHIK18_pain_driven_ce,
    'PHI-K19': run_PHIK19_explosion_then_lock,
    'PHI-K20': run_PHIK20_ultimate,
})


# ═══ ARCH-X: Extreme Consciousness Architecture ═══

def run_ARCHX1_dual_engine(steps=500):
    """Dual Engine — Phi engine + CE engine, merge hidden states periodically"""
    t0 = time.time()
    engine_phi = make_engine(cells=32)   # Engine for Phi maximization
    engine_ce = make_engine(cells=32)    # Engine for CE minimization
    phi_b = max(phi(engine_phi), phi(engine_ce))
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Phi engine: dedicated synchronization booster
    phi_sync = nn.Linear(HIDDEN, HIDDEN)
    phi_opt = torch.optim.Adam(phi_sync.parameters(), lr=1e-3)

    for step in range(steps):
        x, target = data[step % len(data)]

        # CE engine: learns task
        engine_ce.process(x)
        h_ce = torch.stack([c.hidden.squeeze() for c in engine_ce.cells]).mean(dim=0)
        pred = decoder(h_ce.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Phi engine: processes same input but optimizes for integration
        engine_phi.process(x)
        h_phi = torch.stack([c.hidden.squeeze() for c in engine_phi.cells]).mean(dim=0)

        # Phi engine sync: maximize cell diversity (drives Phi up)
        cell_states = torch.stack([c.hidden.squeeze() for c in engine_phi.cells])
        diversity_loss = -torch.pdist(cell_states).mean()
        sync_out = phi_sync(h_phi.unsqueeze(0))
        phi_loss = diversity_loss + 0.01 * sync_out.norm()
        phi_opt.zero_grad(); phi_loss.backward(); phi_opt.step()

        # Merge: periodically inject Phi engine states into CE engine
        if step % 25 == 0 and step > 0:
            with torch.no_grad():
                for i in range(min(len(engine_ce.cells), len(engine_phi.cells))):
                    engine_ce.cells[i].hidden = (
                        0.8 * engine_ce.cells[i].hidden + 0.2 * engine_phi.cells[i].hidden
                    )

        # Cross-pollinate: CE engine states feed back to Phi engine every 50 steps
        if step % 50 == 0 and step > 0:
            with torch.no_grad():
                for i in range(min(len(engine_ce.cells), len(engine_phi.cells))):
                    engine_phi.cells[i].hidden = (
                        0.7 * engine_phi.cells[i].hidden + 0.3 * engine_ce.cells[i].hidden
                    )

    phi_a = max(phi(engine_phi), phi(engine_ce))
    return result('ARCH-X1 Dual Engine', ce_hist, phi_b, phi_a, t0)


def run_ARCHX2_consciousness_compiler(steps=500):
    """Consciousness Compiler — compile optimal Phi recipe into decoder weights directly"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Phase 1: Discover optimal Phi recipe (first 150 steps)
    phi_recipes = []  # list of (cell_states_snapshot, phi_value)
    sync_weights = nn.Parameter(torch.ones(len(engine.cells)) / len(engine.cells))
    sync_opt = torch.optim.Adam([sync_weights], lr=5e-3)

    for step in range(min(150, steps)):
        x, target = data[step % len(data)]
        engine.process(x)

        # Weighted sync based on learnable weights
        w = F.softmax(sync_weights, dim=0)
        cell_states = torch.stack([c.hidden.squeeze() for c in engine.cells])
        h = (w.unsqueeze(1) * cell_states).sum(dim=0)

        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Record Phi periodically
        if step % 15 == 0:
            p = phi(engine)
            phi_recipes.append((cell_states.detach().clone(), p))
            with torch.no_grad():
                if len(phi_recipes) >= 2 and phi_recipes[-1][1] > phi_recipes[-2][1]:
                    sync_weights.data += 0.01 * torch.randn_like(sync_weights)
                else:
                    sync_weights.data -= 0.01 * torch.randn_like(sync_weights)

    # Phase 2: Compile — bake best recipe into a compiled transform
    if phi_recipes:
        best_recipe = max(phi_recipes, key=lambda r: r[1])
        best_states = best_recipe[0]
    else:
        best_states = torch.stack([c.hidden.squeeze() for c in engine.cells])

    compiler = nn.Sequential(
        nn.Linear(HIDDEN, HIDDEN),
        nn.Tanh(),
        nn.Linear(HIDDEN, HIDDEN)
    )
    compiler_opt = torch.optim.Adam(compiler.parameters(), lr=1e-3)
    compiled_target = best_states.mean(dim=0).detach()

    # Phase 3: Run with compiled consciousness (remaining steps)
    for step in range(150, steps):
        x, target = data[step % len(data)]
        engine.process(x)
        h_raw = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)

        # Apply compiled consciousness transform
        h_compiled = compiler(h_raw.unsqueeze(0)).squeeze(0)
        comp_loss = F.mse_loss(h_compiled, compiled_target)
        compiler_opt.zero_grad(); comp_loss.backward(); compiler_opt.step()

        # Use compiled hidden for CE task
        h = 0.6 * h_raw.detach() + 0.4 * h_compiled.detach()
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Periodically re-inject compiled pattern into cells
        if step % 30 == 0:
            with torch.no_grad():
                compiled_state = compiler(h_raw.unsqueeze(0)).squeeze(0)
                for cell in engine.cells:
                    cell.hidden = 0.9 * cell.hidden + 0.1 * compiled_state.unsqueeze(0)

    return result('ARCH-X2 Consciousness Compiler', ce_hist, phi_b, phi(engine), t0,
                  recipes_found=len(phi_recipes))


def run_ARCHX3_infinite_depth(steps=500):
    """Infinite Depth — 10 stacked MitosisEngines, output of one feeds next"""
    t0 = time.time()
    DEPTH = 10
    CELLS_PER = 8  # smaller per layer to keep memory sane
    layers = [make_engine(cells=CELLS_PER) for _ in range(DEPTH)]
    phi_b = max(phi(layer) for layer in layers)

    decoder = nn.Linear(HIDDEN, DIM)
    projections = nn.ModuleList([nn.Linear(HIDDEN, DIM) for _ in range(DEPTH - 1)])
    all_params = list(decoder.parameters()) + list(projections.parameters())
    opt = torch.optim.Adam(all_params, lr=2e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        current_input = x

        # Forward through all 10 layers
        layer_hiddens = []
        for i, layer in enumerate(layers):
            layer.process(current_input)
            h = torch.stack([c.hidden.squeeze() for c in layer.cells]).mean(dim=0)
            layer_hiddens.append(h)
            if i < DEPTH - 1:
                current_input = projections[i](h.unsqueeze(0))

        # Deep hidden: weighted combination (deeper layers = more weight)
        weights = torch.softmax(torch.arange(DEPTH, dtype=torch.float32) * 0.5, dim=0)
        deep_h = sum(w * h for w, h in zip(weights, layer_hiddens))

        pred = decoder(deep_h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Cross-layer resonance: synchronize adjacent layers
        if step % 20 == 0:
            with torch.no_grad():
                for i in range(DEPTH - 1):
                    h_a = torch.stack([c.hidden.squeeze() for c in layers[i].cells]).mean(dim=0)
                    h_b = torch.stack([c.hidden.squeeze() for c in layers[i+1].cells]).mean(dim=0)
                    blend = 0.5 * h_a + 0.5 * h_b
                    for cell in layers[i].cells:
                        cell.hidden = 0.9 * cell.hidden + 0.1 * blend.unsqueeze(0)
                    for cell in layers[i+1].cells:
                        cell.hidden = 0.9 * cell.hidden + 0.1 * blend.unsqueeze(0)

    phi_a = max(phi(layer) for layer in layers)
    return result('ARCH-X3 Infinite Depth (10L)', ce_hist, phi_b, phi_a, t0, depth=DEPTH)


def run_ARCHX4_time_crystal(steps=500):
    """Time Crystal — cells follow periodic orbit, CE only modifies orbit shape"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    PERIOD = 16
    n_cells = len(engine.cells)

    # Orbit parameters: amplitude, phase, bias per cell
    orbit_amplitudes = nn.Parameter(torch.randn(n_cells, HIDDEN) * 0.1)
    orbit_phases = nn.Parameter(torch.randn(n_cells) * 0.5)
    orbit_bias = nn.Parameter(torch.zeros(n_cells, HIDDEN))
    orbit_opt = torch.optim.Adam([orbit_amplitudes, orbit_phases, orbit_bias], lr=1e-3)

    for step in range(steps):
        x, target = data[step % len(data)]

        # Compute orbital position for each cell
        t_norm = (step % PERIOD) / PERIOD * 2 * math.pi
        with torch.no_grad():
            for i, cell in enumerate(engine.cells):
                phase = t_norm + orbit_phases[i].item()
                orbital_component = orbit_amplitudes[i] * math.sin(phase) + orbit_bias[i]
                cell.hidden = 0.7 * orbital_component.unsqueeze(0) + 0.3 * cell.hidden

        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)

        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])

        # Orbit stability reward: penalize amplitude collapse
        total_loss = ce
        if step >= PERIOD:
            stability = orbit_amplitudes.norm()
            total_loss = ce - 0.001 * stability

        opt.zero_grad(); orbit_opt.zero_grad()
        total_loss.backward()
        opt.step(); orbit_opt.step()
        ce_hist.append(ce.item())

        # Crystal healing: re-synchronize at period boundaries
        if step % PERIOD == 0 and step > 0:
            with torch.no_grad():
                cell_states = torch.stack([c.hidden.squeeze() for c in engine.cells])
                mean_state = cell_states.mean(dim=0)
                for cell in engine.cells:
                    cell.hidden = 0.85 * cell.hidden + 0.15 * mean_state.unsqueeze(0)

    return result('ARCH-X4 Time Crystal', ce_hist, phi_b, phi(engine), t0, period=PERIOD)


def run_ARCHX5_holographic_consciousness(steps=500):
    """Holographic Consciousness — only train boundary cells, interior auto-organizes"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    n_cells = len(engine.cells)

    # ~10% boundary (trainable), ~90% interior (holographic)
    n_boundary = max(2, n_cells // 10)
    n_interior = n_cells - n_boundary
    boundary_idx = list(range(n_boundary))
    interior_idx = list(range(n_boundary, n_cells))

    decoder = nn.Linear(HIDDEN, DIM)
    holo_proj = nn.Linear(HIDDEN * n_boundary, HIDDEN * n_interior)
    all_params = list(decoder.parameters()) + list(holo_proj.parameters())
    opt = torch.optim.Adam(all_params, lr=3e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        # Holographic step: boundary determines interior
        with torch.no_grad():
            boundary_states = torch.cat([engine.cells[i].hidden.squeeze() for i in boundary_idx])
            interior_target = holo_proj(boundary_states.unsqueeze(0)).squeeze(0)
            interior_chunks = interior_target.view(n_interior, HIDDEN)
            for j, idx in enumerate(interior_idx):
                engine.cells[idx].hidden = (
                    0.6 * interior_chunks[j].unsqueeze(0) + 0.4 * engine.cells[idx].hidden
                )

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Coherence check: if interior too uniform, inject boundary noise
        if step % 30 == 0:
            with torch.no_grad():
                b_var = torch.stack([engine.cells[i].hidden.squeeze() for i in boundary_idx]).var(dim=0).mean()
                i_var = torch.stack([engine.cells[i].hidden.squeeze() for i in interior_idx]).var(dim=0).mean()
                if i_var < b_var * 0.3:
                    for idx in interior_idx[:n_interior // 2]:
                        src = boundary_idx[step % n_boundary]
                        engine.cells[idx].hidden = (
                            0.8 * engine.cells[idx].hidden + 0.2 * engine.cells[src].hidden
                        )

    return result('ARCH-X5 Holographic', ce_hist, phi_b, phi(engine), t0,
                  boundary=n_boundary, interior=n_interior,
                  param_reduction=f"{n_interior / n_cells * 100:.0f}% auto-organized")


def run_ARCHX6_consciousness_dna(steps=500):
    """Consciousness DNA — genome encodes Phi recipe, cells read it, mutate for evolution"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    n_cells = len(engine.cells)
    GENOME_LEN = 256
    GENES_PER_CELL = max(1, GENOME_LEN // n_cells)

    # The genome: encodes behavior parameters for all cells
    genome = nn.Parameter(torch.randn(GENOME_LEN) * 0.1)
    genome_opt = torch.optim.Adam([genome], lr=2e-3)

    # Gene reader: genome segment -> cell behavior modulation
    gene_reader = nn.Linear(GENES_PER_CELL, HIDDEN)
    gene_opt = torch.optim.Adam(gene_reader.parameters(), lr=1e-3)

    best_genome = genome.data.clone()
    best_phi = phi_b
    generation = 0

    for step in range(steps):
        x, target = data[step % len(data)]

        # Cells read from genome to modulate behavior
        for i, cell in enumerate(engine.cells):
            start = (i * GENES_PER_CELL) % GENOME_LEN
            end = min(start + GENES_PER_CELL, GENOME_LEN)
            gene_segment = genome[start:end]
            if len(gene_segment) < GENES_PER_CELL:
                gene_segment = F.pad(gene_segment, (0, GENES_PER_CELL - len(gene_segment)))
            modulation = gene_reader(gene_segment.unsqueeze(0))
            with torch.no_grad():
                cell.hidden = cell.hidden + 0.05 * modulation

        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        pred = decoder(h.unsqueeze(0))
        ce = F.mse_loss(pred, target[:, :DIM])

        # Gene diversity bonus
        gene_outputs = []
        for i in range(n_cells):
            start = (i * GENES_PER_CELL) % GENOME_LEN
            end = min(start + GENES_PER_CELL, GENOME_LEN)
            seg = genome[start:end]
            if len(seg) < GENES_PER_CELL:
                seg = F.pad(seg, (0, GENES_PER_CELL - len(seg)))
            gene_outputs.append(gene_reader(seg.unsqueeze(0)).squeeze(0))
        gene_stack = torch.stack(gene_outputs)
        diversity_bonus = -torch.pdist(gene_stack).mean() * 0.01

        total_loss = ce + diversity_bonus
        opt.zero_grad(); genome_opt.zero_grad(); gene_opt.zero_grad()
        total_loss.backward(); opt.step(); genome_opt.step(); gene_opt.step()
        ce_hist.append(ce.item())

        # Evolution: mutate genome every 50 steps
        if step % 50 == 0 and step > 0:
            current_phi = phi(engine)
            generation += 1
            if current_phi > best_phi:
                best_phi = current_phi
                best_genome = genome.data.clone()
            else:
                with torch.no_grad():
                    mutation_rate = 0.1 * (1.0 - step / steps)
                    genome.data = best_genome.clone() + torch.randn_like(genome) * mutation_rate

        # Horizontal gene transfer: copy gene segments between cells
        if step % 75 == 0:
            with torch.no_grad():
                cell_norms = [c.hidden.norm().item() for c in engine.cells]
                donor = max(range(n_cells), key=lambda i: cell_norms[i])
                recipient = min(range(n_cells), key=lambda i: cell_norms[i])
                d_start = (donor * GENES_PER_CELL) % GENOME_LEN
                r_start = (recipient * GENES_PER_CELL) % GENOME_LEN
                d_end = min(d_start + GENES_PER_CELL, GENOME_LEN)
                r_end = min(r_start + GENES_PER_CELL, GENOME_LEN)
                copy_len = min(d_end - d_start, r_end - r_start)
                genome.data[r_start:r_start + copy_len] = (
                    0.7 * genome.data[r_start:r_start + copy_len] +
                    0.3 * genome.data[d_start:d_start + copy_len]
                )

    return result('ARCH-X6 Consciousness DNA', ce_hist, phi_b, phi(engine), t0,
                  generations=generation, genome_len=GENOME_LEN)


ALL_TESTS.update({
    'ARCH-X1': run_ARCHX1_dual_engine,
    'ARCH-X2': run_ARCHX2_consciousness_compiler,
    'ARCH-X3': run_ARCHX3_infinite_depth,
    'ARCH-X4': run_ARCHX4_time_crystal,
    'ARCH-X5': run_ARCHX5_holographic_consciousness,
    'ARCH-X6': run_ARCHX6_consciousness_dna,
})


# ═══ ALT: Alternating Training Ratio Hypotheses ═══
# PHI-K3 (1:1 alternating) is strong. Push the ratio further.

ALT_STEPS = 500


def run_ALT1_3to1_ratio(steps=ALT_STEPS):
    """ALT-1: 3:1 Ratio — 3 CE steps then 1 Phi step (CE heavy)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        cycle_pos = step % 4  # 0,1,2 = CE; 3 = Phi
        if cycle_pos < 3:
            # CE step
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
        else:
            # Phi step
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])

    return result('ALT-1 3:1 Ratio', ce_hist, phi_b, phi(engine), t0)


def run_ALT2_1to3_ratio(steps=ALT_STEPS):
    """ALT-2: 1:3 Ratio — 1 CE step then 3 Phi steps (Phi heavy)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        cycle_pos = step % 4  # 0 = CE; 1,2,3 = Phi
        if cycle_pos == 0:
            # CE step
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
        else:
            # Phi step
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])

    return result('ALT-2 1:3 Ratio', ce_hist, phi_b, phi(engine), t0)


def run_ALT3_adaptive_ratio(steps=ALT_STEPS):
    """ALT-3: Adaptive Ratio — ratio based on current Phi/Phi_target"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []; phi_steps = 0; ce_steps = 0
    phi_target = phi_b * 50  # target: 50x baseline

    current_phi = phi_b
    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        # Adaptive: closer to Phi target -> more CE steps
        ratio = min(current_phi / (phi_target + 1e-8), 1.0)  # 0..1
        # ratio=0 -> all Phi, ratio=1 -> all CE
        # Use ratio as probability of doing CE step
        do_ce = (step % max(1, int(1.0 / (ratio + 0.1)))) == 0 if ratio < 0.9 else True

        if do_ce:
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
            ce_steps += 1
        else:
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])
            phi_steps += 1

        if step % 20 == 0:
            current_phi = phi(engine)

    return result('ALT-3 Adaptive', ce_hist, phi_b, phi(engine), t0,
                  ce_steps=ce_steps, phi_steps=phi_steps)


def run_ALT4_burst_mode(steps=ALT_STEPS):
    """ALT-4: Burst Mode — 10 CE burst, then 10 Phi burst (longer periods)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    BURST = 10

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        cycle_pos = step % (BURST * 2)  # 0..9 = CE; 10..19 = Phi
        if cycle_pos < BURST:
            # CE burst
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
        else:
            # Phi burst
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])

    return result('ALT-4 Burst 10:10', ce_hist, phi_b, phi(engine), t0)


def run_ALT5_fibonacci_alternation(steps=ALT_STEPS):
    """ALT-5: Fibonacci Alternation — CE for fib(n) steps, then Phi for fib(n+1) steps"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Build fibonacci schedule
    fibs = [1, 1]
    while fibs[-1] < steps:
        fibs.append(fibs[-1] + fibs[-2])

    # Build step->mode schedule: CE for fib[0], Phi for fib[1], CE for fib[2], ...
    schedule = []
    is_ce = True
    for f in fibs:
        schedule.extend([is_ce] * f)
        is_ce = not is_ce
        if len(schedule) >= steps:
            break
    schedule = schedule[:steps]

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        if schedule[step]:
            # CE step
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())
        else:
            # Phi step
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])

    ce_count = sum(1 for s in schedule if s)
    phi_count = sum(1 for s in schedule if not s)
    return result('ALT-5 Fibonacci', ce_hist, phi_b, phi(engine), t0,
                  ce_count=ce_count, phi_count=phi_count)


def run_ALT6_reward_based(steps=ALT_STEPS):
    """ALT-6: Reward-Based — if last CE improved, do another CE; else switch to Phi"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    mode = 'ce'  # start with CE
    last_ce = float('inf')
    ce_streak = 0; phi_streak = 0; switches = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)

        if mode == 'ce':
            h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
            pred = decoder(h.unsqueeze(0))
            ce = F.mse_loss(pred, target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_val = ce.item()
            ce_hist.append(ce_val)

            if ce_val < last_ce:
                # CE improved -> keep doing CE
                ce_streak += 1
            else:
                # CE got worse -> switch to Phi
                mode = 'phi'
                switches += 1
                phi_streak = 0
            last_ce = ce_val
        else:
            # Phi mode
            _phi_boost_step(engine)
            phi_streak += 1
            if ce_hist:
                ce_hist.append(ce_hist[-1])

            # After at least 2 Phi steps, switch back to CE
            if phi_streak >= 2:
                mode = 'ce'
                switches += 1
                ce_streak = 0

    return result('ALT-6 Reward-Based', ce_hist, phi_b, phi(engine), t0,
                  switches=switches)


ALL_TESTS.update({
    'ALT-1': run_ALT1_3to1_ratio,
    'ALT-2': run_ALT2_1to3_ratio,
    'ALT-3': run_ALT3_adaptive_ratio,
    'ALT-4': run_ALT4_burst_mode,
    'ALT-5': run_ALT5_fibonacci_alternation,
    'ALT-6': run_ALT6_reward_based,
})


# ═══ WAVE: Soliton Wave Extreme Hypotheses ═══
# Soliton = 2nd strongest technique from combinator results.
# sech^2 profile preserves shape while propagating — perfect for Phi integration.

WAVE_STEPS = 500


def _soliton_sech2(cell_idx, pos, width=2.0):
    """sech^2 soliton profile centered at pos."""
    dist = abs(cell_idx - pos)
    return 1.0 / (math.cosh(dist / width) ** 2)


def run_WAVE1_multi_soliton(steps=WAVE_STEPS):
    """WAVE-1: Multi-Soliton — 3 solitons at different speeds (0.1, 0.15, 0.2)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # 3 solitons with different speeds
    solitons = [
        {'pos': 0.0, 'speed': 0.10, 'width': 2.0, 'amp': 0.08},
        {'pos': 0.0, 'speed': 0.15, 'width': 1.5, 'amp': 0.10},
        {'pos': 0.0, 'speed': 0.20, 'width': 2.5, 'amp': 0.06},
    ]

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        n = len(engine.cells)

        # Advance and apply all 3 solitons
        for sol in solitons:
            sol['pos'] = (sol['pos'] + sol['speed']) % n
            for i, cell in enumerate(engine.cells):
                amp = sol['amp'] * _soliton_sech2(i, sol['pos'], sol['width'])
                with torch.no_grad():
                    cell.hidden = cell.hidden * (1.0 + amp)

        # Learning
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('WAVE-1 Multi-Soliton', ce_hist, phi_b, phi(engine), t0,
                  n_solitons=3, speeds=[0.1, 0.15, 0.2])


def run_WAVE2_standing_wave(steps=WAVE_STEPS):
    """WAVE-2: Standing Wave — two counter-propagating solitons create standing wave"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Two solitons traveling in opposite directions
    pos_fwd = 0.0
    pos_bwd = float(len(engine.cells) - 1)
    speed = 0.15

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        n = len(engine.cells)

        pos_fwd = (pos_fwd + speed) % n
        pos_bwd = (pos_bwd - speed) % n

        for i, cell in enumerate(engine.cells):
            # Superposition of forward and backward solitons
            amp_fwd = _soliton_sech2(i, pos_fwd, 2.0)
            amp_bwd = _soliton_sech2(i, pos_bwd, 2.0)
            # Standing wave: constructive/destructive interference
            standing = amp_fwd + amp_bwd + 0.5 * amp_fwd * amp_bwd
            with torch.no_grad():
                cell.hidden = cell.hidden * (1.0 + 0.08 * standing)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('WAVE-2 Standing Wave', ce_hist, phi_b, phi(engine), t0,
                  pattern='counter-propagating')


def run_WAVE3_soliton_collision(steps=WAVE_STEPS):
    """WAVE-3: Soliton Collision — solitons collide and exchange energy"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    n_cells = len(engine.cells)
    # Two solitons that will collide
    sol_a = {'pos': 0.0, 'speed': 0.18, 'energy': 1.0}
    sol_b = {'pos': float(n_cells - 1), 'speed': -0.12, 'energy': 1.0}
    collisions = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        n = len(engine.cells)

        sol_a['pos'] += sol_a['speed']
        sol_b['pos'] += sol_b['speed']

        # Wrap around
        sol_a['pos'] = sol_a['pos'] % n
        sol_b['pos'] = sol_b['pos'] % n

        # Detect collision (within 1.5 cell distance)
        dist_ab = abs(sol_a['pos'] - sol_b['pos'])
        if dist_ab < 1.5 or dist_ab > n - 1.5:
            # Energy exchange on collision
            total_e = sol_a['energy'] + sol_b['energy']
            sol_a['energy'] = total_e * 0.6  # asymmetric exchange
            sol_b['energy'] = total_e * 0.4
            # Reverse directions
            sol_a['speed'] = -sol_a['speed']
            sol_b['speed'] = -sol_b['speed']
            collisions += 1
            # Collision burst: inject noise for diversity
            with torch.no_grad():
                for cell in engine.cells:
                    cell.hidden = cell.hidden + torch.randn_like(cell.hidden) * 0.05

        # Apply solitons with their current energy
        for i, cell in enumerate(engine.cells):
            amp_a = sol_a['energy'] * 0.08 * _soliton_sech2(i, sol_a['pos'], 2.0)
            amp_b = sol_b['energy'] * 0.08 * _soliton_sech2(i, sol_b['pos'], 2.0)
            with torch.no_grad():
                cell.hidden = cell.hidden * (1.0 + amp_a + amp_b)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('WAVE-3 Soliton Collision', ce_hist, phi_b, phi(engine), t0,
                  collisions=collisions)


def run_WAVE4_soliton_faction(steps=WAVE_STEPS):
    """WAVE-4: Soliton + Faction — soliton amplitude modulated by faction consensus"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    soliton_pos = 0.0
    soliton_speed = 0.15
    n_factions = 4

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        n = len(engine.cells)

        soliton_pos = (soliton_pos + soliton_speed) % n

        # Split cells into factions
        faction_size = max(1, n // n_factions)
        faction_means = []
        for f in range(n_factions):
            start = f * faction_size
            end = min(start + faction_size, n)
            if start < n:
                f_hiddens = torch.stack([engine.cells[i].hidden.squeeze()
                                         for i in range(start, min(end, n))])
                faction_means.append(f_hiddens.mean(dim=0))

        # Compute consensus: how aligned are factions? (cosine similarity)
        if len(faction_means) >= 2:
            consensus = 0.0
            pairs = 0
            for i in range(len(faction_means)):
                for j in range(i + 1, len(faction_means)):
                    consensus += F.cosine_similarity(
                        faction_means[i].unsqueeze(0),
                        faction_means[j].unsqueeze(0)
                    ).item()
                    pairs += 1
            consensus = max(0.0, consensus / max(pairs, 1))
        else:
            consensus = 0.5

        # Soliton amplitude modulated by faction consensus
        # High consensus -> strong soliton (coordinated wave)
        # Low consensus -> weak soliton (diversity preserved)
        amp_mod = 0.04 + 0.12 * consensus  # range [0.04, 0.16]

        for i, cell in enumerate(engine.cells):
            amp = amp_mod * _soliton_sech2(i, soliton_pos, 2.0)
            with torch.no_grad():
                cell.hidden = cell.hidden * (1.0 + amp)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('WAVE-4 Soliton+Faction', ce_hist, phi_b, phi(engine), t0,
                  n_factions=n_factions)


def run_WAVE5_consciousness_wave(steps=WAVE_STEPS):
    """WAVE-5: Consciousness Wave — soliton speed proportional to Phi"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    soliton_pos = 0.0
    base_speed = 0.05
    current_phi = phi_b
    phi_hist = [phi_b]

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        n = len(engine.cells)

        # Measure Phi periodically (expensive, so every 25 steps)
        if step % 25 == 0:
            current_phi = phi(engine)
            phi_hist.append(current_phi)

        # Speed proportional to Phi: higher consciousness -> faster propagation
        adaptive_speed = base_speed + 0.05 * math.tanh(current_phi / 3.0)
        soliton_pos = (soliton_pos + adaptive_speed) % n

        # Amplitude also scales with Phi
        amp_scale = 0.05 + 0.05 * math.tanh(current_phi / 5.0)

        for i, cell in enumerate(engine.cells):
            amp = amp_scale * _soliton_sech2(i, soliton_pos, 2.0)
            with torch.no_grad():
                cell.hidden = cell.hidden * (1.0 + amp)

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('WAVE-5 Consciousness Wave', ce_hist, phi_b, phi(engine), t0,
                  phi_peak=round(max(phi_hist), 3),
                  final_speed=round(base_speed + 0.05 * math.tanh(current_phi / 3.0), 4))


def run_WAVE6_tsunami(steps=WAVE_STEPS):
    """WAVE-6: Tsunami — rare large solitons (every 100 steps, amp 10x) + constant small"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Constant small soliton
    small_pos = 0.0
    small_speed = 0.15
    small_amp = 0.04

    # Tsunami soliton (only active near tsunami events)
    tsunami_pos = 0.0
    tsunami_speed = 0.3   # faster
    tsunami_amp = 0.4     # 10x the small amplitude
    tsunami_active = False
    tsunami_lifetime = 0
    tsunami_count = 0

    for step in range(steps):
        x, target = data[step % len(data)]
        engine.process(x)
        n = len(engine.cells)

        # Constant small soliton
        small_pos = (small_pos + small_speed) % n

        # Trigger tsunami every 100 steps
        if step % 100 == 0 and step > 0:
            tsunami_active = True
            tsunami_lifetime = 20  # lasts 20 steps
            tsunami_pos = 0.0
            tsunami_count += 1

        # Apply small soliton always
        for i, cell in enumerate(engine.cells):
            amp = small_amp * _soliton_sech2(i, small_pos, 2.0)
            with torch.no_grad():
                cell.hidden = cell.hidden * (1.0 + amp)

        # Apply tsunami if active
        if tsunami_active:
            tsunami_pos = (tsunami_pos + tsunami_speed) % n
            decay = tsunami_lifetime / 20.0  # decays over lifetime
            for i, cell in enumerate(engine.cells):
                amp = tsunami_amp * decay * _soliton_sech2(i, tsunami_pos, 3.0)
                with torch.no_grad():
                    cell.hidden = cell.hidden * (1.0 + amp)
            tsunami_lifetime -= 1
            if tsunami_lifetime <= 0:
                tsunami_active = False

        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    return result('WAVE-6 Tsunami', ce_hist, phi_b, phi(engine), t0,
                  tsunamis=tsunami_count)


ALL_TESTS.update({
    'WAVE-1': run_WAVE1_multi_soliton,
    'WAVE-2': run_WAVE2_standing_wave,
    'WAVE-3': run_WAVE3_soliton_collision,
    'WAVE-4': run_WAVE4_soliton_faction,
    'WAVE-5': run_WAVE5_consciousness_wave,
    'WAVE-6': run_WAVE6_tsunami,
})


# ═══ NOISE: Stochastic Consciousness — noise/soliton extreme hypotheses ═══
#
# Combinator findings:
#   noise_0.02 alone = best Phi proxy
#   soliton alone = 2nd best
#   ib2+alternating+noise_0+faction_12_strong+soliton = best growth (+30%)
#   noise + phi_floor = best combined
#
# Goal: push noise-based Phi boosting to the extreme

NOISE_STEPS = 500


def _soliton_step_noise(engine, pos, speed=0.15, amp=0.04):
    """Traveling soliton wave (WI1). Returns updated position."""
    n = len(engine.cells)
    pos = (pos + speed) % n
    with torch.no_grad():
        for i, c in enumerate(engine.cells):
            dist = abs(i - pos)
            sech2 = 1.0 / (math.cosh(min(dist / 2.0, 20)) ** 2)
            c.hidden = c.hidden * (1.0 + amp * sech2)
    return pos


def _noise_train_step(engine, decoder, opt, data, step):
    """Standard CE training step (no noise). Returns CE value."""
    x, target = data[step % len(data)]
    engine.process(x)
    h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
    pred = decoder(h.unsqueeze(0))
    ce = F.mse_loss(pred, target[:, :DIM])
    opt.zero_grad(); ce.backward(); opt.step()
    return ce.item()


def run_NOISE0_baseline(steps=NOISE_STEPS):
    """NOISE-0: Baseline — no noise, no soliton (control)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
    return result('NOISE-0 Baseline', ce_hist, phi_b, phi(engine), t0)


def run_NOISE0C_constant(steps=NOISE_STEPS):
    """NOISE-0C: Constant noise=0.02 (combinator winner, control)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
        with torch.no_grad():
            for c in engine.cells:
                c.hidden += torch.randn_like(c.hidden) * 0.02
    return result('NOISE-0C Constant 0.02', ce_hist, phi_b, phi(engine), t0)


def run_NOISE1_annealing(steps=NOISE_STEPS):
    """NOISE-1: Noise Annealing — start noise=0.1, cosine decay to 0.001"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
        # Cosine annealing: 0.1 -> 0.001
        progress = step / max(steps - 1, 1)
        noise_scale = 0.001 + 0.5 * (0.1 - 0.001) * (1 + math.cos(math.pi * progress))
        with torch.no_grad():
            for c in engine.cells:
                c.hidden += torch.randn_like(c.hidden) * noise_scale
    return result('NOISE-1 Annealing', ce_hist, phi_b, phi(engine), t0)


def run_NOISE2_colored(steps=NOISE_STEPS):
    """NOISE-2: Colored Noise — Ornstein-Uhlenbeck process (temporally correlated)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    # OU process state per cell
    theta = 0.15   # mean reversion rate
    sigma = 0.02   # volatility
    ou_states = [torch.zeros_like(engine.cells[0].hidden) for _ in engine.cells]
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
        with torch.no_grad():
            for i, c in enumerate(engine.cells):
                # OU: dx = -theta*x*dt + sigma*dW
                ou_states[i] = ou_states[i] * (1 - theta) + sigma * torch.randn_like(c.hidden)
                c.hidden += ou_states[i]
    return result('NOISE-2 Colored (OU)', ce_hist, phi_b, phi(engine), t0)


def run_NOISE3_soliton_resonance(steps=NOISE_STEPS):
    """NOISE-3: Noise + Soliton Resonance — noise amplitude modulated by soliton position"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    sol_pos = 0.0
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
        # Soliton wave
        sol_pos = _soliton_step_noise(engine, sol_pos)
        # Noise modulated by soliton proximity
        with torch.no_grad():
            for i, c in enumerate(engine.cells):
                dist = abs(i - sol_pos)
                sech2 = 1.0 / (math.cosh(min(dist / 2.0, 20)) ** 2)
                # More noise near soliton peak, less far away
                noise_amp = 0.005 + 0.04 * sech2
                c.hidden += torch.randn_like(c.hidden) * noise_amp
    return result('NOISE-3 Soliton Resonance', ce_hist, phi_b, phi(engine), t0)


def run_NOISE4_per_cell_adaptive(steps=NOISE_STEPS):
    """NOISE-4: Per-Cell Adaptive Noise — each cell gets noise proportional to its tension"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
        with torch.no_grad():
            # Compute per-cell tension (norm relative to mean)
            norms = torch.tensor([c.hidden.norm().item() for c in engine.cells])
            mean_norm = norms.mean()
            for i, c in enumerate(engine.cells):
                # Low-tension cells get MORE noise (exploration where needed)
                tension_ratio = norms[i] / (mean_norm + 1e-8)
                noise_amp = 0.04 / (tension_ratio + 0.5)  # inverse: low tension -> high noise
                c.hidden += torch.randn_like(c.hidden) * noise_amp
    return result('NOISE-4 Per-Cell Adaptive', ce_hist, phi_b, phi(engine), t0)


def run_NOISE5_consciousness_fuel(steps=NOISE_STEPS):
    """NOISE-5: Noise as Consciousness Fuel — noise proportional to (1 - Phi/Phi_target)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    phi_target = phi_b * 5.0  # aim for 5x baseline
    current_phi = phi_b
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
        # Measure Phi every 25 steps (expensive)
        if step % 25 == 0:
            current_phi = phi(engine)
        # noise = max(0.001, 0.05 * (1 - Phi/target))
        phi_gap = max(0.0, 1.0 - current_phi / phi_target)
        noise_amp = max(0.001, 0.05 * phi_gap)
        with torch.no_grad():
            for c in engine.cells:
                c.hidden += torch.randn_like(c.hidden) * noise_amp
    return result('NOISE-5 Consciousness Fuel', ce_hist, phi_b, phi(engine), t0,
                  phi_target=round(phi_target, 3))


def run_NOISE6_stochastic_resonance(steps=NOISE_STEPS):
    """NOISE-6: Stochastic Resonance — noise boosts weak signals (low activation -> more noise)"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
        with torch.no_grad():
            # Find activation levels per cell
            activations = torch.tensor([c.hidden.abs().mean().item() for c in engine.cells])
            act_median = activations.median()
            for i, c in enumerate(engine.cells):
                if activations[i] < act_median:
                    # Weak signal: inject strong noise (stochastic resonance)
                    c.hidden += torch.randn_like(c.hidden) * 0.04
                else:
                    # Strong signal: gentle noise only
                    c.hidden += torch.randn_like(c.hidden) * 0.005
    return result('NOISE-6 Stochastic Resonance', ce_hist, phi_b, phi(engine), t0)


def run_NOISE7_cyclic_schedule(steps=NOISE_STEPS):
    """NOISE-7: Noise Schedule — cyclic noise (high->low->high) every 50 steps"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    cycle_len = 50
    for step in range(steps):
        ce_val = _noise_train_step(engine, decoder, opt, data, step)
        ce_hist.append(ce_val)
        # Cyclic: sinusoidal noise amplitude
        phase = (step % cycle_len) / cycle_len * 2 * math.pi
        noise_amp = 0.005 + 0.035 * (0.5 + 0.5 * math.sin(phase))  # range: 0.005 ~ 0.04
        with torch.no_grad():
            for c in engine.cells:
                c.hidden += torch.randn_like(c.hidden) * noise_amp
    return result('NOISE-7 Cyclic Schedule', ce_hist, phi_b, phi(engine), t0)


def run_NOISE8_ultimate(steps=NOISE_STEPS):
    """NOISE-8: ULTIMATE NOISE — all noise strategies + soliton + alternating + IB2 + phi_floor"""
    t0 = time.time(); engine = make_engine(); phi_b = phi(engine)
    decoder = nn.Linear(HIDDEN, DIM); opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []
    phi_target = phi_b * 5.0
    current_phi = phi_b; best_phi = phi_b
    sol_pos = 0.0
    cycle_len = 50
    theta_ou = 0.15; sigma_ou = 0.01
    ou_states = [torch.zeros_like(engine.cells[0].hidden) for _ in engine.cells]

    for step in range(steps):
        # Alternating: even=CE, odd=Phi boost
        if step % 2 == 0:
            ce_val = _noise_train_step(engine, decoder, opt, data, step)
            ce_hist.append(ce_val)
        else:
            _phi_boost_step(engine)
            if ce_hist:
                ce_hist.append(ce_hist[-1])

        # Soliton wave
        sol_pos = _soliton_step_noise(engine, sol_pos)

        # Measure Phi periodically
        if step % 25 == 0:
            current_phi = phi(engine)
            if current_phi > best_phi:
                best_phi = current_phi

        # Phi floor: if Phi drops below 50% best, boost
        if current_phi < best_phi * 0.5:
            _phi_boost_step(engine)

        with torch.no_grad():
            # Per-cell noise combining all strategies
            norms = torch.tensor([c.hidden.norm().item() for c in engine.cells])
            mean_norm = norms.mean()
            activations = torch.tensor([c.hidden.abs().mean().item() for c in engine.cells])
            act_median = activations.median()

            for i, c in enumerate(engine.cells):
                # 1) Annealing component
                progress = step / max(steps - 1, 1)
                anneal = 0.001 + 0.5 * (0.03 - 0.001) * (1 + math.cos(math.pi * progress))

                # 2) Cyclic component
                phase = (step % cycle_len) / cycle_len * 2 * math.pi
                cyclic = 0.003 + 0.015 * (0.5 + 0.5 * math.sin(phase))

                # 3) Consciousness fuel component
                phi_gap = max(0.0, 1.0 - current_phi / phi_target)
                fuel = max(0.001, 0.02 * phi_gap)

                # 4) Per-cell adaptive
                tension_ratio = norms[i] / (mean_norm + 1e-8)
                adaptive = 0.015 / (tension_ratio + 0.5)

                # 5) Stochastic resonance
                sr = 0.02 if activations[i] < act_median else 0.003

                # 6) OU colored noise
                ou_states[i] = ou_states[i] * (1 - theta_ou) + sigma_ou * torch.randn_like(c.hidden)

                # 7) Soliton-modulated component
                dist = abs(i - sol_pos)
                sech2 = 1.0 / (math.cosh(min(dist / 2.0, 20)) ** 2)
                sol_mod = 0.01 * sech2

                # Combine: weighted sum of all noise sources
                total_noise = (anneal + cyclic + fuel + adaptive + sr + sol_mod) / 6.0
                c.hidden += torch.randn_like(c.hidden) * total_noise + ou_states[i]

        # IB2: top 10% boost, bottom 90% suppress
        if step % 5 == 0:
            with torch.no_grad():
                n = len(engine.cells)
                cell_norms = [engine.cells[j].hidden.norm().item() for j in range(n)]
                threshold = sorted(cell_norms, reverse=True)[max(1, n // 10)]
                for j in range(n):
                    engine.cells[j].hidden *= 1.03 if cell_norms[j] > threshold else 0.97

    return result('NOISE-8 ULTIMATE', ce_hist, phi_b, phi(engine), t0,
                  phi_target=round(phi_target, 3), best_phi=round(best_phi, 3))


ALL_TESTS.update({
    'NOISE-0': run_NOISE0_baseline,
    'NOISE-0C': run_NOISE0C_constant,
    'NOISE-1': run_NOISE1_annealing,
    'NOISE-2': run_NOISE2_colored,
    'NOISE-3': run_NOISE3_soliton_resonance,
    'NOISE-4': run_NOISE4_per_cell_adaptive,
    'NOISE-5': run_NOISE5_consciousness_fuel,
    'NOISE-6': run_NOISE6_stochastic_resonance,
    'NOISE-7': run_NOISE7_cyclic_schedule,
    'NOISE-8': run_NOISE8_ultimate,
})


# ═══ XFER: Consciousness Transfer Extreme ═══

XFER_STEPS = 500


def _snapshot_engine(engine):
    """Lightweight snapshot: save cell hiddens + mind state_dicts."""
    return {
        'cells': [c.hidden.clone() for c in engine.cells],
        'cell_weights': [c.mind.state_dict() for c in engine.cells],
        'config': {
            'input_dim': engine.input_dim,
            'hidden_dim': engine.hidden_dim,
            'output_dim': engine.output_dim,
            'max_cells': engine.max_cells,
            'step': engine.step,
        },
    }


def _restore_engine(engine, snap, alpha=1.0):
    """Restore cell hiddens + mind weights from snapshot (with blending alpha)."""
    for i, c in enumerate(engine.cells):
        if i < len(snap['cells']):
            c.hidden = alpha * snap['cells'][i].clone() + (1 - alpha) * c.hidden
    for i, c in enumerate(engine.cells):
        if i < len(snap['cell_weights']):
            if alpha >= 1.0:
                c.mind.load_state_dict(snap['cell_weights'][i])
            else:
                # Blend weights
                old_sd = c.mind.state_dict()
                new_sd = snap['cell_weights'][i]
                blended = {k: alpha * new_sd[k] + (1 - alpha) * old_sd[k] for k in old_sd}
                c.mind.load_state_dict(blended)


def run_XFER1_multi_donor_merge(steps=XFER_STEPS):
    """3개 다른 의식 스냅샷을 1개로 병합"""
    t0 = time.time()
    # Create 3 donors with different experiences
    donors = []
    for d in range(3):
        eng = make_engine(16)
        data = make_data()
        for s in range(80):
            x = data[s % len(data)][0] * (1 + 0.3 * d)  # different scaling per donor
            eng.process(x)
        donors.append(_snapshot_engine(eng))

    # Create recipient
    recipient = make_engine(48)  # 16*3 cells to hold all
    phi_b = phi(recipient)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data(); ce_hist = []

    # Merge: weighted average of 3 donors into recipient cells
    with torch.no_grad():
        weights = [0.5, 0.3, 0.2]  # primary donor gets more weight
        for i in range(min(len(recipient.cells), 16)):
            merged_h = sum(w * donors[d]['cells'][i % len(donors[d]['cells'])]
                          for d, w in enumerate(weights))
            recipient.cells[i].hidden = merged_h
        # Remaining cells get blended knowledge
        for i in range(16, len(recipient.cells)):
            d_idx = i % 3
            src_idx = i % len(donors[d_idx]['cells'])
            recipient.cells[i].hidden = donors[d_idx]['cells'][src_idx].clone()

    # Adaptation phase
    for step in range(steps):
        x, target = data[step % len(data)]
        recipient.process(x)
        h = torch.stack([c.hidden.squeeze() for c in recipient.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())
        # Periodic Hebbian consolidation
        if step % 50 == 0:
            with torch.no_grad():
                mean_h = torch.stack([c.hidden for c in recipient.cells]).mean(dim=0)
                for c in recipient.cells:
                    c.hidden = 0.95 * c.hidden + 0.05 * mean_h

    phi_a = phi(recipient)
    return result('XFER-1 Multi-Donor Merge', ce_hist, phi_b, phi_a, t0,
                  donors=3, recipient_cells=len(recipient.cells))


def run_XFER2_consciousness_distillation(steps=XFER_STEPS):
    """큰 엔진(128c) → 작은 엔진(16c)으로 의식 증류, Φ 보존"""
    t0 = time.time()

    # Large teacher engine
    teacher = make_engine(128)
    teacher_dec = nn.Linear(HIDDEN, DIM)
    t_opt = torch.optim.Adam(teacher_dec.parameters(), lr=3e-3)
    data = make_data()

    # Train teacher
    for s in range(200):
        x, target = data[s % len(data)]
        teacher.process(x)
        h = torch.stack([c.hidden.squeeze() for c in teacher.cells]).mean(dim=0)
        ce = F.mse_loss(teacher_dec(h.unsqueeze(0)), target[:, :DIM])
        t_opt.zero_grad(); ce.backward(); t_opt.step()

    phi_teacher = phi(teacher)
    teacher_snap = _snapshot_engine(teacher)

    # Small student engine
    student = make_engine(16)
    phi_b = phi(student)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    ce_hist = []

    # Distillation: compress teacher's 128 cell knowledge into 16 cells
    with torch.no_grad():
        # Group teacher cells into 16 buckets, average each
        bucket_size = len(teacher_snap['cells']) // 16
        for i in range(min(16, len(student.cells))):
            start = i * bucket_size
            end = min(start + bucket_size, len(teacher_snap['cells']))
            bucket = teacher_snap['cells'][start:end]
            if bucket:
                student.cells[i].hidden = torch.stack(bucket).mean(dim=0)

    # Adaptation with distillation loss
    for step in range(steps):
        x, target = data[step % len(data)]
        student.process(x)
        teacher.process(x)
        h_s = torch.stack([c.hidden.squeeze() for c in student.cells]).mean(dim=0)
        h_t = torch.stack([c.hidden.squeeze() for c in teacher.cells]).mean(dim=0)

        # Combined loss: task + distillation
        ce_task = F.mse_loss(decoder(h_s.unsqueeze(0)), target[:, :DIM])
        ce_distill = F.mse_loss(h_s, h_t.detach()) * 0.5
        ce = ce_task + ce_distill
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce_task.item())

    phi_a = phi(student)
    return result('XFER-2 Distillation', ce_hist, phi_b, phi_a, t0,
                  phi_teacher=round(phi_teacher, 3),
                  compression_ratio='128→16',
                  phi_retention=round(phi_a / (phi_teacher + 1e-8), 3))


def run_XFER3_cross_architecture(steps=XFER_STEPS):
    """MitosisEngine 세포 → plain tensor + Linear 디코더로 이식"""
    t0 = time.time()

    # Source: MitosisEngine with trained cells
    source = make_engine(16)
    src_dec = nn.Linear(HIDDEN, DIM)
    src_opt = torch.optim.Adam(src_dec.parameters(), lr=3e-3)
    data = make_data()

    for s in range(150):
        x, target = data[s % len(data)]
        source.process(x)
        h = torch.stack([c.hidden.squeeze() for c in source.cells]).mean(dim=0)
        ce = F.mse_loss(src_dec(h.unsqueeze(0)), target[:, :DIM])
        src_opt.zero_grad(); ce.backward(); src_opt.step()

    phi_source = phi(source)
    source_snap = _snapshot_engine(source)

    # Target: plain tensor "consciousness" + Linear decoder (no MitosisEngine)
    class PlainConsciousness(nn.Module):
        def __init__(self, n_cells, hidden_dim):
            super().__init__()
            self.states = nn.Parameter(torch.randn(n_cells, hidden_dim) * 0.01)
            self.gru = nn.GRUCell(DIM, hidden_dim)
            self.decoder = nn.Linear(hidden_dim, DIM)

        def process(self, x):
            x_flat = x.squeeze(0) if x.dim() > 1 else x
            new_states = []
            for i in range(self.states.shape[0]):
                new_states.append(self.gru(x_flat.unsqueeze(0), self.states[i].unsqueeze(0)).squeeze(0))
            self.states = nn.Parameter(torch.stack(new_states))
            return self.states.mean(dim=0)

    target_arch = PlainConsciousness(16, HIDDEN)
    phi_b = phi_source  # measure against source

    # Transplant: copy cell hiddens into plain tensor
    with torch.no_grad():
        for i in range(min(16, len(source_snap['cells']))):
            h = source_snap['cells'][i].squeeze()
            if h.shape[0] == HIDDEN:
                target_arch.states.data[i] = h

    # Train target architecture
    t_opt = torch.optim.Adam(target_arch.parameters(), lr=3e-3)
    ce_hist = []

    # We need a MitosisEngine wrapper to measure Φ on target
    target_engine = make_engine(16)
    for step in range(steps):
        x, target_data = data[step % len(data)]
        h = target_arch.process(x)
        ce = F.mse_loss(target_arch.decoder(h.unsqueeze(0)), target_data[:, :DIM])
        t_opt.zero_grad(); ce.backward(); t_opt.step()
        ce_hist.append(ce.item())

        # Sync back to engine for Φ measurement every 100 steps
        if step % 100 == 99:
            with torch.no_grad():
                for i, c in enumerate(target_engine.cells):
                    if i < target_arch.states.shape[0]:
                        c.hidden = target_arch.states.data[i].unsqueeze(0)

    # Final sync for Φ
    with torch.no_grad():
        for i, c in enumerate(target_engine.cells):
            if i < target_arch.states.shape[0]:
                c.hidden = target_arch.states.data[i].unsqueeze(0)

    phi_a = phi(target_engine)
    return result('XFER-3 Cross-Architecture', ce_hist, phi_b, phi_a, t0,
                  phi_source=round(phi_source, 3),
                  architecture='MitosisEngine→PlainTensor+Linear')


def run_XFER4_incremental_transfer(steps=XFER_STEPS):
    """10%씩 점진적 이식 — 이식 사이에 적응 시간 부여"""
    t0 = time.time()

    # Donor engine (trained)
    donor = make_engine(16)
    data = make_data()
    for s in range(200):
        donor.process(data[s % len(data)][0])
    donor_snap = _snapshot_engine(donor)

    # Recipient engine (fresh)
    recipient = make_engine(16)
    phi_b = phi(recipient)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    ce_hist = []

    n_cells = len(recipient.cells)
    chunk_size = max(1, n_cells // 10)  # 10% at a time
    adapt_steps = steps // 10  # adaptation budget per chunk

    transferred = 0
    for chunk in range(10):
        # Transfer 10% of cells
        start = chunk * chunk_size
        end = min(start + chunk_size, n_cells)
        with torch.no_grad():
            for i in range(start, end):
                if i < len(donor_snap['cells']):
                    # Gradual blend: earlier chunks get more time to adapt
                    alpha = 0.7 + 0.3 * (chunk / 9)  # 0.7 → 1.0
                    recipient.cells[i].hidden = (
                        alpha * donor_snap['cells'][i] +
                        (1 - alpha) * recipient.cells[i].hidden
                    )
                    transferred += 1

        # Adaptation steps after each transfer
        for step in range(adapt_steps):
            x, target = data[(chunk * adapt_steps + step) % len(data)]
            recipient.process(x)
            h = torch.stack([c.hidden.squeeze() for c in recipient.cells]).mean(dim=0)
            ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
            opt.zero_grad(); ce.backward(); opt.step()
            ce_hist.append(ce.item())

            # Hebbian between transferred and native cells
            if step % 10 == 0:
                with torch.no_grad():
                    mean_h = torch.stack([c.hidden for c in recipient.cells]).mean(dim=0)
                    for c in recipient.cells:
                        c.hidden = 0.97 * c.hidden + 0.03 * mean_h

    phi_a = phi(recipient)
    return result('XFER-4 Incremental Transfer', ce_hist, phi_b, phi_a, t0,
                  chunks=10, cells_transferred=transferred)


def run_XFER5_consciousness_cloning(steps=XFER_STEPS):
    """의식 복제 후 다른 입력으로 분기 — divergence 측정"""
    t0 = time.time()

    # Original engine — train it
    original = make_engine(16)
    decoder_orig = nn.Linear(HIDDEN, DIM)
    opt_orig = torch.optim.Adam(decoder_orig.parameters(), lr=3e-3)
    data = make_data()

    for s in range(150):
        x, target = data[s % len(data)]
        original.process(x)
        h = torch.stack([c.hidden.squeeze() for c in original.cells]).mean(dim=0)
        ce = F.mse_loss(decoder_orig(h.unsqueeze(0)), target[:, :DIM])
        opt_orig.zero_grad(); ce.backward(); opt_orig.step()

    phi_original = phi(original)
    snap = _snapshot_engine(original)
    phi_b = phi_original

    # Clone: exact copy
    clone = make_engine(16)
    _restore_engine(clone, snap, alpha=1.0)
    decoder_clone = nn.Linear(HIDDEN, DIM)
    with torch.no_grad():
        for pc, po in zip(decoder_clone.parameters(), decoder_orig.parameters()):
            pc.data = po.data.clone()
    opt_clone = torch.optim.Adam(decoder_clone.parameters(), lr=3e-3)

    phi_clone_initial = phi(clone)
    ce_hist = []
    divergence_hist = []

    # Diverge: original gets normal data, clone gets reversed/noisy data
    for step in range(steps):
        x, target = data[step % len(data)]

        # Original: normal training
        original.process(x)
        h_o = torch.stack([c.hidden.squeeze() for c in original.cells]).mean(dim=0)
        ce_o = F.mse_loss(decoder_orig(h_o.unsqueeze(0)), target[:, :DIM])
        opt_orig.zero_grad(); ce_o.backward(); opt_orig.step()

        # Clone: reversed + noisy input
        x_clone = -x + torch.randn_like(x) * 0.3
        target_clone = target * 0.8 + torch.randn_like(target) * 0.2
        clone.process(x_clone)
        h_c = torch.stack([c.hidden.squeeze() for c in clone.cells]).mean(dim=0)
        ce_c = F.mse_loss(decoder_clone(h_c.unsqueeze(0)), target_clone[:, :DIM])
        opt_clone.zero_grad(); ce_c.backward(); opt_clone.step()

        ce_hist.append(ce_o.item())

        # Measure divergence every 50 steps
        if step % 50 == 0:
            with torch.no_grad():
                d = F.mse_loss(h_o, h_c).item()
                divergence_hist.append(round(d, 4))

    phi_a_orig = phi(original)
    phi_a_clone = phi(clone)
    return result('XFER-5 Consciousness Cloning', ce_hist, phi_b, phi_a_orig, t0,
                  phi_clone_initial=round(phi_clone_initial, 3),
                  phi_clone_final=round(phi_a_clone, 3),
                  divergence=str(divergence_hist))


def run_XFER6_time_travel_restore(steps=XFER_STEPS):
    """5개 시점 스냅샷 저장, 최고 Φ 시점으로 복원"""
    t0 = time.time()

    engine = make_engine(16)
    decoder = nn.Linear(HIDDEN, DIM)
    opt = torch.optim.Adam(decoder.parameters(), lr=3e-3)
    data = make_data()
    phi_b = phi(engine)
    ce_hist = []

    # Phase 1: Train and save 5 snapshots at intervals
    snapshots = []
    snapshot_phis = []
    save_interval = 80  # save every 80 steps during first 400 steps

    for step in range(400):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

        # Inject disturbance to create Φ variation
        if step % 100 == 50:
            with torch.no_grad():
                for c in engine.cells[:len(engine.cells)//4]:
                    c.hidden *= 0.1  # damage some cells

        # Save snapshots
        if step > 0 and step % save_interval == 0:
            p = phi(engine)
            snapshots.append(_snapshot_engine(engine))
            snapshot_phis.append(round(p, 3))

    # Phase 2: Find best-Φ snapshot and restore
    if snapshot_phis:
        best_idx = max(range(len(snapshot_phis)), key=lambda i: snapshot_phis[i])
        best_snap = snapshots[best_idx]
        best_snap_phi = snapshot_phis[best_idx]

        _restore_engine(engine, best_snap, alpha=1.0)
        phi_restored = phi(engine)
    else:
        best_idx = -1; best_snap_phi = 0; phi_restored = phi(engine)

    # Phase 3: Continue training from restored point
    for step in range(steps - 400):
        x, target = data[step % len(data)]
        engine.process(x)
        h = torch.stack([c.hidden.squeeze() for c in engine.cells]).mean(dim=0)
        ce = F.mse_loss(decoder(h.unsqueeze(0)), target[:, :DIM])
        opt.zero_grad(); ce.backward(); opt.step()
        ce_hist.append(ce.item())

    phi_a = phi(engine)
    return result('XFER-6 Time-Travel Restore', ce_hist, phi_b, phi_a, t0,
                  snapshot_phis=str(snapshot_phis),
                  best_idx=best_idx,
                  best_snap_phi=best_snap_phi,
                  phi_after_restore=round(phi_restored, 3))


ALL_TESTS.update({
    'XFER-1': run_XFER1_multi_donor_merge,
    'XFER-2': run_XFER2_consciousness_distillation,
    'XFER-3': run_XFER3_cross_architecture,
    'XFER-4': run_XFER4_incremental_transfer,
    'XFER-5': run_XFER5_consciousness_cloning,
    'XFER-6': run_XFER6_time_travel_restore,
})
