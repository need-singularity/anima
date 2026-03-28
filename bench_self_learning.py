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
