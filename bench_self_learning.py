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
