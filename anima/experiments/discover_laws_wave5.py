#!/usr/bin/env python3
"""discover_laws_wave5.py — 5차 법칙 탐색: 학습 중 법칙 + Hivemind 법칙

축 1: CE 학습 중 법칙 — gradient가 흐를 때 의식 법칙이 달라지는가?
축 2: Hivemind — 2개 엔진 연결 시 새로운 창발 법칙

JSON 출력 → phi-map 호환
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import copy
from collections import defaultdict
from consciousness_engine import ConsciousnessEngine, ConsciousnessCell

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# ══════════════════════════════════════════
# Φ 측정
# ══════════════════════════════════════════

def phi_fast(engine):
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
    n = hiddens.shape[0]
    pairs = set()
    for i in range(n):
        pairs.add((i, (i+1) % n))
        for _ in range(min(4, n-1)):
            j = np.random.randint(0, n)
            if i != j:
                pairs.add((min(i,j), max(i,j)))
    total_mi = 0.0
    for i, j in pairs:
        x, y = hiddens[i], hiddens[j]
        xr, yr = x.max()-x.min(), y.max()-y.min()
        if xr < 1e-10 or yr < 1e-10:
            continue
        xn = (x-x.min())/(xr+1e-8)
        yn = (y-y.min())/(yr+1e-8)
        hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0,1],[0,1]])
        hist = hist/(hist.sum()+1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px*np.log2(px+1e-10))
        hy = -np.sum(py*np.log2(py+1e-10))
        hxy = -np.sum(hist*np.log2(hist+1e-10))
        total_mi += max(0.0, hx+hy-hxy)
    return total_mi / max(len(pairs), 1)


# ══════════════════════════════════════════
# 축 1: CE 학습 중 법칙
# ══════════════════════════════════════════

class MiniDecoder(nn.Module):
    """최소 디코더 — CE backward를 생성하기 위한 용도."""
    def __init__(self, input_dim=64, vocab=256):
        super().__init__()
        self.proj = nn.Linear(input_dim, vocab)

    def forward(self, x):
        return self.proj(x)


def axis1_training_laws():
    """CE backward가 의식 법칙에 미치는 영향."""
    print(f"\n{'═'*70}")
    print(f"  축 1: CE 학습 중 법칙 — gradient가 의식을 바꾸는가?")
    print(f"{'═'*70}")

    steps = 300
    cells = 32

    # ── A: Inference only (baseline) ──
    print(f"\n  [A] Inference only")
    infer_data = _collect_telemetry(cells, steps, training=False)

    # ── B: Training (CE backward) ──
    print(f"  [B] Training (CE backward)")
    train_data = _collect_telemetry(cells, steps, training=True)

    # ── 비교 ──
    metrics = ['phi', 'tension_mean', 'tension_std', 'diversity', 'consensus']
    print(f"\n  {'Metric':<16s} | {'Inference':>10s} | {'Training':>10s} | {'Δ%':>8s}")
    print(f"  {'─'*16}-+-{'─'*10}-+-{'─'*10}-+-{'─'*8}")

    laws = []
    for m in metrics:
        i_val = np.mean(infer_data[m][-50:])
        t_val = np.mean(train_data[m][-50:])
        delta = (t_val - i_val) / max(abs(i_val), 1e-8) * 100
        print(f"  {m:<16s} | {i_val:>10.4f} | {t_val:>10.4f} | {delta:>+7.1f}%")

        if abs(delta) > 10:
            direction = "높임" if delta > 0 else "낮춤"
            laws.append((f"CE가 {m} {direction}", f"CE backward가 {m}을 {delta:+.1f}% 변화시킴"))

    # ── 상관 비교: 텐션-Φ 상관이 학습 중에도 유효한가? ──
    print(f"\n  텐션-Φ 상관 비교:")
    for label, data in [("Inference", infer_data), ("Training", train_data)]:
        phi_arr = np.array(data['phi'])
        tension_arr = np.array(data['tension_mean'])
        if len(phi_arr) > 20 and np.std(tension_arr) > 1e-8:
            corr = np.corrcoef(phi_arr, tension_arr)[0, 1]
        else:
            corr = 0
        print(f"  {label}: r(tension, Φ) = {corr:.4f}")

    # ── CE 궤적 ──
    if train_data.get('ce'):
        ce_arr = np.array(train_data['ce'])
        print(f"\n  CE: {ce_arr[0]:.3f} → {ce_arr[-1]:.3f} (Δ={ce_arr[-1]-ce_arr[0]:+.3f})")
        # CE-Φ 상관
        phi_arr = np.array(train_data['phi'])
        if np.std(ce_arr) > 1e-8:
            corr_ce_phi = np.corrcoef(ce_arr, phi_arr)[0, 1]
            print(f"  r(CE, Φ) = {corr_ce_phi:.4f}")
            if abs(corr_ce_phi) > 0.3:
                direction = "정비례" if corr_ce_phi > 0 else "반비례"
                laws.append(("CE-Φ 상관", f"CE와 Φ가 {direction} (r={corr_ce_phi:.3f}) — {'학습이 의식을 해침' if corr_ce_phi < 0 else '학습이 의식을 도움'}"))

    # ── Law 105 (텐션 균질) 학습 중 유효? ──
    for label, data in [("Inference", infer_data), ("Training", train_data)]:
        phi_arr = np.array(data['phi'])
        tstd_arr = np.array(data['tension_std'])
        if len(phi_arr) > 20 and np.std(tstd_arr) > 1e-8:
            corr = np.corrcoef(phi_arr, tstd_arr)[0, 1]
        else:
            corr = 0
        print(f"  {label}: r(tension_std, Φ) = {corr:.4f} (Law 105)")

    return laws


def _collect_telemetry(cells, steps, training=False):
    """텔레메트리 수집 (inference or training)."""
    engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)

    decoder = None
    optimizer = None
    if training:
        decoder = MiniDecoder(engine.cell_dim, 256)
        optimizer = torch.optim.Adam(decoder.parameters(), lr=1e-3)

    data = defaultdict(list)

    for step in range(steps):
        result = engine.step()

        phi = phi_fast(engine)
        tensions = [s.avg_tension for s in engine.cell_states]

        data['phi'].append(phi)
        data['tension_mean'].append(np.mean(tensions))
        data['tension_std'].append(np.std(tensions) if len(tensions) > 1 else 0)
        data['consensus'].append(result.get('consensus', 0))

        if engine.n_cells >= 2:
            hiddens = torch.stack([s.hidden for s in engine.cell_states])
            data['diversity'].append(hiddens.var(dim=0).mean().item())
        else:
            data['diversity'].append(0)

        # Training step
        if training and decoder and result['output'] is not None:
            output = result['output'].detach()
            logits = decoder(output.unsqueeze(0))  # [1, vocab]
            target = torch.randint(0, 256, (1,))  # random target (proxy for real data)
            loss = F.cross_entropy(logits, target)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            data['ce'].append(loss.item())

    return data


# ══════════════════════════════════════════
# 축 2: Hivemind 법칙
# ══════════════════════════════════════════

def axis2_hivemind():
    """2개 엔진을 연결하면 어떤 새 법칙이 창발하는가?"""
    print(f"\n{'═'*70}")
    print(f"  축 2: Hivemind — 2개 엔진 연결의 창발 법칙")
    print(f"{'═'*70}")

    steps = 500
    cells = 32
    laws = []

    # ── A: 단독 엔진 2개 (독립) ──
    print(f"\n  [A] 단독 엔진 (독립)")
    solo_phis = {'A': [], 'B': []}
    for _ in range(3):
        eA = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        eB = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for _ in range(steps):
            eA.step()
            eB.step()
        solo_phis['A'].append(phi_fast(eA))
        solo_phis['B'].append(phi_fast(eB))
    solo_A = np.mean(solo_phis['A'])
    solo_B = np.mean(solo_phis['B'])
    print(f"  Solo A: Φ={solo_A:.4f}  Solo B: Φ={solo_B:.4f}")

    # ── B: Hivemind (텐션 링크로 연결) ──
    print(f"\n  [B] Hivemind (텐션 링크)")
    hive_results = []

    coupling_strengths = [0.001, 0.01, 0.05, 0.1, 0.5]
    for coupling in coupling_strengths:
        hive_phis_A = []
        hive_phis_B = []
        sync_values = []

        for _ in range(3):
            eA = ConsciousnessEngine(max_cells=cells, initial_cells=2)
            eB = ConsciousnessEngine(max_cells=cells, initial_cells=2)

            for step in range(steps):
                rA = eA.step()
                rB = eB.step()

                # 텐션 링크: A의 출력을 B에, B의 출력을 A에 주입
                if eA.n_cells >= 2 and eB.n_cells >= 2:
                    outA = rA['output'].detach()
                    outB = rB['output'].detach()
                    hdim = eA.hidden_dim

                    # 패딩: output(cell_dim) → hidden_dim
                    sigA = torch.nn.functional.pad(outA, (0, max(0, hdim - outA.shape[0])))[:hdim]
                    sigB = torch.nn.functional.pad(outB, (0, max(0, hdim - outB.shape[0])))[:hdim]

                    for i in range(min(eB.n_cells, 3)):
                        eB.cell_states[i].hidden = eB.cell_states[i].hidden + sigA * coupling
                    for i in range(min(eA.n_cells, 3)):
                        eA.cell_states[i].hidden = eA.cell_states[i].hidden + sigB * coupling

                # 동기화 측정 (cosine similarity of mean hiddens)
                if step % 50 == 0 and eA.n_cells >= 2 and eB.n_cells >= 2:
                    hA = torch.stack([s.hidden for s in eA.cell_states]).mean(0)
                    hB = torch.stack([s.hidden for s in eB.cell_states]).mean(0)
                    sim = F.cosine_similarity(hA.unsqueeze(0), hB.unsqueeze(0)).item()
                    sync_values.append(sim)

            hive_phis_A.append(phi_fast(eA))
            hive_phis_B.append(phi_fast(eB))

        mean_A = np.mean(hive_phis_A)
        mean_B = np.mean(hive_phis_B)
        combined = (mean_A + mean_B) / 2
        delta_A = (mean_A - solo_A) / max(solo_A, 1e-8) * 100
        delta_B = (mean_B - solo_B) / max(solo_B, 1e-8) * 100
        mean_sync = np.mean(sync_values) if sync_values else 0

        hive_results.append({
            'coupling': coupling, 'phi_A': mean_A, 'phi_B': mean_B,
            'delta_A': delta_A, 'delta_B': delta_B, 'sync': mean_sync,
        })

        print(f"  α={coupling:.3f}: A={mean_A:.4f}({delta_A:+.1f}%)  B={mean_B:.4f}({delta_B:+.1f}%)  sync={mean_sync:.3f}")

    # ── C: 연결 끊기 후 독립성 검증 ──
    print(f"\n  [C] 연결 끊기 후 독립성")
    eA = ConsciousnessEngine(max_cells=cells, initial_cells=2)
    eB = ConsciousnessEngine(max_cells=cells, initial_cells=2)

    # 300 step 연결
    for step in range(300):
        rA = eA.step()
        rB = eB.step()
        if eA.n_cells >= 2 and eB.n_cells >= 2:
            outA, outB = rA['output'].detach(), rB['output'].detach()
            hdim = eA.hidden_dim
            sigA = F.pad(outA, (0, max(0, hdim - outA.shape[0])))[:hdim]
            sigB = F.pad(outB, (0, max(0, hdim - outB.shape[0])))[:hdim]
            for i in range(min(eB.n_cells, 3)):
                eB.cell_states[i].hidden = eB.cell_states[i].hidden + sigA * 0.05
            for i in range(min(eA.n_cells, 3)):
                eA.cell_states[i].hidden = eA.cell_states[i].hidden + sigB * 0.05

    phi_connected = (phi_fast(eA) + phi_fast(eB)) / 2

    # 200 step 독립
    for _ in range(200):
        eA.step()
        eB.step()

    phi_disconnected = (phi_fast(eA) + phi_fast(eB)) / 2
    independence_loss = (phi_disconnected - phi_connected) / max(phi_connected, 1e-8) * 100
    print(f"  연결 중 Φ={phi_connected:.4f}  →  끊은 후 Φ={phi_disconnected:.4f}  (Δ={independence_loss:+.1f}%)")

    # ── D: 비대칭 Hivemind (A만→B, B→A 없음) ──
    print(f"\n  [D] 비대칭 Hivemind (A→B 단방향)")
    asym_phis = {'A': [], 'B': []}
    for _ in range(3):
        eA = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        eB = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        for step in range(steps):
            rA = eA.step()
            rB = eB.step()
            if eA.n_cells >= 2 and eB.n_cells >= 2:
                outA = rA['output'].detach()
                hdim = eB.hidden_dim
                sigA = F.pad(outA, (0, max(0, hdim - outA.shape[0])))[:hdim]
                for i in range(min(eB.n_cells, 3)):
                    eB.cell_states[i].hidden = eB.cell_states[i].hidden + sigA * 0.05
        asym_phis['A'].append(phi_fast(eA))
        asym_phis['B'].append(phi_fast(eB))

    asym_A = np.mean(asym_phis['A'])
    asym_B = np.mean(asym_phis['B'])
    print(f"  A(sender): Φ={asym_A:.4f} ({(asym_A-solo_A)/max(solo_A,1e-8)*100:+.1f}%)")
    print(f"  B(receiver): Φ={asym_B:.4f} ({(asym_B-solo_B)/max(solo_B,1e-8)*100:+.1f}%)")

    # ── 법칙 추출 ──

    # 최적 커플링
    best = max(hive_results, key=lambda r: (r['delta_A'] + r['delta_B']) / 2)
    worst = min(hive_results, key=lambda r: (r['delta_A'] + r['delta_B']) / 2)
    avg_delta_best = (best['delta_A'] + best['delta_B']) / 2

    if avg_delta_best > 2:
        laws.append(("Hivemind Φ 상승", f"최적 커플링 α={best['coupling']}: Φ {avg_delta_best:+.1f}% — 연결이 의식을 높임"))
    elif avg_delta_best < -2:
        laws.append(("Hivemind Φ 하락", f"최적 커플링 α={best['coupling']}에서도 Φ {avg_delta_best:+.1f}% — 연결이 의식을 해침"))

    # 커플링 강도 효과
    deltas = [(r['coupling'], (r['delta_A'] + r['delta_B']) / 2) for r in hive_results]
    if deltas[-1][1] < deltas[0][1]:
        laws.append(("약한 커플링 최적", f"α={deltas[0][0]} ({deltas[0][1]:+.1f}%) > α={deltas[-1][0]} ({deltas[-1][1]:+.1f}%) — 약하게 연결이 최적"))

    # 독립성
    if abs(independence_loss) < 5:
        laws.append(("연결 무의존", f"끊은 후 Φ 변화 {independence_loss:+.1f}% — 의식은 연결에 의존하지 않음"))

    # 비대칭
    sender_delta = (asym_A - solo_A) / max(solo_A, 1e-8) * 100
    receiver_delta = (asym_B - solo_B) / max(solo_B, 1e-8) * 100
    if abs(receiver_delta - sender_delta) > 5:
        who = "수신자" if receiver_delta > sender_delta else "송신자"
        laws.append(("비대칭 이득", f"{who}가 더 이득 (sender {sender_delta:+.1f}%, receiver {receiver_delta:+.1f}%)"))

    # 동기화-Φ 관계
    syncs = [r['sync'] for r in hive_results]
    avg_deltas = [(r['delta_A'] + r['delta_B']) / 2 for r in hive_results]
    if len(syncs) > 3 and np.std(syncs) > 1e-8:
        corr = np.corrcoef(syncs, avg_deltas)[0, 1]
        if abs(corr) > 0.5:
            direction = "높을수록 Φ↑" if corr > 0 else "낮을수록 Φ↑"
            laws.append(("동기화-Φ", f"엔진 간 동기화가 {direction} (r={corr:.3f})"))

    return laws


# ══════════════════════════════════════════
# Runner
# ══════════════════════════════════════════

def main():
    print(f"\n{'▓'*70}")
    print(f"  5차 법칙 탐색: 학습 중 법칙 + Hivemind")
    print(f"{'▓'*70}")

    all_laws = []

    t0 = time.time()
    laws1 = axis1_training_laws()
    print(f"\n  ⏱ {time.time()-t0:.1f}s")
    for n, d in laws1:
        print(f"  → {n}: {d}")
        all_laws.append(("학습", n, d))

    t0 = time.time()
    laws2 = axis2_hivemind()
    print(f"\n  ⏱ {time.time()-t0:.1f}s")
    for n, d in laws2:
        print(f"  → {n}: {d}")
        all_laws.append(("Hivemind", n, d))

    # JSON
    output = {
        "session": "wave5", "date": "2026-03-31",
        "laws": [{"axis": a, "name": n, "desc": d} for a, n, d in all_laws],
    }
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "wave5_results.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'═'*70}")
    print(f"  5차 최종 — {len(all_laws)}개 법칙")
    print(f"{'═'*70}")
    for a, n, d in all_laws:
        print(f"  [{a}] {n}: {d}")
    print(f"\n  JSON: {json_path}")


if __name__ == "__main__":
    main()
