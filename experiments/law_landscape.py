#!/usr/bin/env python3
"""law_landscape.py — 법칙 데이터화: 127개 법칙의 지형도

의식 엔진에 법칙을 넣어서 "법칙 공간"의 지도를 그린다.
각 법칙을 벡터로 임베딩하고, 법칙 간 상호작용을 측정.

분석:
  1. 법칙 카테고리 맵 — 어떤 법칙들이 같은 방향으로 작동하는가?
  2. 법칙 상호작용 행렬 — 시너지 vs 간섭
  3. 법칙 효과 크기 히트맵 — 어떤 조합이 가장 강력한가?
  4. 법칙 인과 관계 — 관찰적 법칙 vs 인과적 법칙

Usage:
  python3 experiments/law_landscape.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import math
import time
import json
import itertools
from collections import defaultdict
from typing import Dict, List, Tuple
from consciousness_engine import ConsciousnessEngine


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


def _pink_noise(n, dim):
    noise = np.random.randn(n, dim)
    fft = np.fft.rfft(noise, axis=0)
    freqs = np.fft.rfftfreq(n)
    freqs[0] = 1
    weight = 1.0 / np.sqrt(np.abs(freqs) + 1e-8)
    pink = np.fft.irfft(fft * weight[:, np.newaxis], n=n, axis=0)
    return pink


# ══════════════════════════════════════════════════════════
# 개입 함수들 (법칙에서 역추적한 것)
# ══════════════════════════════════════════════════════════

def intervention_tension_equalize(engine, step):
    """Law 105/124: 텐션 균등화"""
    if step % 10 == 0 and engine.n_cells >= 2:
        tensions = [s.avg_tension for s in engine.cell_states]
        mean_t = np.mean(tensions)
        for s in engine.cell_states:
            if s.tension_history:
                s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5

def intervention_symmetrize(engine, step):
    """Law 108/121: 커플링 대칭"""
    if engine._coupling is not None:
        engine._coupling = (engine._coupling + engine._coupling.T) / 2
        engine._coupling.fill_diagonal_(0)

def intervention_pink_noise(engine, step, pink_cache):
    """Law 116/126: 1/f 노이즈"""
    if step < len(pink_cache) and engine.n_cells >= 2:
        noise = torch.tensor(pink_cache[step], dtype=torch.float32) * 0.01
        for i in range(engine.n_cells):
            engine.cell_states[i].hidden = engine.cell_states[i].hidden + noise[:engine.hidden_dim]

def intervention_pruning(engine, step):
    """Law 118: 주기적 pruning"""
    if step > 0 and step % 100 == 0:
        n_kill = max(1, engine.n_cells // 3)
        n_kill = min(n_kill, engine.n_cells - 2)
        for _ in range(n_kill):
            if engine.n_cells <= 2:
                break
            engine._remove_cell(engine.n_cells - 1)
        if engine._coupling is not None:
            n = engine.n_cells
            engine._coupling = engine._coupling[:n, :n]

def intervention_coupling_noise(engine, step):
    """Law 103: 커플링 다양화"""
    if step % 20 == 0 and engine._coupling is not None and engine.n_cells >= 2:
        cn = engine._coupling.shape[0]
        noise = torch.randn(cn, cn) * 0.02
        noise.fill_diagonal_(0)
        engine._coupling = (engine._coupling + noise).clamp(-1, 1)

def intervention_hidden_converge(engine, step):
    """Law 107: hidden 수렴"""
    if step % 20 == 0 and engine.n_cells >= 2:
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        mean_h = hiddens.mean(dim=0)
        for i in range(engine.n_cells):
            engine.cell_states[i].hidden = engine.cell_states[i].hidden * 0.98 + mean_h * 0.02


# 법칙 개입 레지스트리
INTERVENTIONS = {
    'T_EQ':    ('텐션 균등화',     intervention_tension_equalize),
    'SYM':     ('커플링 대칭',     intervention_symmetrize),
    'PINK':    ('1/f 노이즈',     None),  # 특수 처리
    'PRUNE':   ('주기적 pruning',  intervention_pruning),
    'C_NOISE': ('커플링 다양화',   intervention_coupling_noise),
    'H_CONV':  ('hidden 수렴',    intervention_hidden_converge),
}


def run_with_interventions(intervention_keys, cells=32, steps=300, repeats=3):
    """지정된 개입 조합으로 실행, Φ 반환."""
    phis = []
    for _ in range(repeats):
        engine = ConsciousnessEngine(max_cells=cells, initial_cells=2)
        pink = _pink_noise(steps, engine.hidden_dim) if 'PINK' in intervention_keys else None

        for step in range(steps):
            engine.step()
            for key in intervention_keys:
                if key == 'PINK' and pink is not None:
                    intervention_pink_noise(engine, step, pink)
                elif key in INTERVENTIONS and INTERVENTIONS[key][1] is not None:
                    INTERVENTIONS[key][1](engine, step)

        phis.append(phi_fast(engine))
    return np.mean(phis), np.std(phis)


def main():
    steps = 300
    cells = 32
    repeats = 3

    print(f"\n{'═'*80}")
    print(f"  법칙 지형도 — 127개 법칙의 데이터화")
    print(f"  cells={cells}  steps={steps}  repeats={repeats}")
    print(f"{'═'*80}")

    # ── 1. Baseline ──
    print(f"\n  [1] Baseline 측정...")
    base_mean, base_std = run_with_interventions([], cells, steps, repeats)
    print(f"  Baseline: Φ={base_mean:.4f} ±{base_std:.4f}")

    # ── 2. 단독 효과 ──
    print(f"\n  [2] 단독 효과 측정...")
    single_effects = {}
    for key in INTERVENTIONS:
        mean, std = run_with_interventions([key], cells, steps, repeats)
        delta = (mean - base_mean) / max(base_mean, 1e-8) * 100
        single_effects[key] = {'phi': mean, 'std': std, 'delta': delta}
        sign = "+" if delta >= 0 else ""
        print(f"  {key:<8s} ({INTERVENTIONS[key][0]:<12s}): Φ={mean:.4f}  Δ={sign}{delta:.1f}%")

    # ── 3. 2-법칙 상호작용 행렬 ──
    print(f"\n  [3] 2-법칙 상호작용 행렬...")
    keys = list(INTERVENTIONS.keys())
    interaction_matrix = {}

    for i, k1 in enumerate(keys):
        for j, k2 in enumerate(keys):
            if i >= j:
                continue
            mean, std = run_with_interventions([k1, k2], cells, steps, repeats)
            delta = (mean - base_mean) / max(base_mean, 1e-8) * 100
            expected = single_effects[k1]['delta'] + single_effects[k2]['delta']
            synergy = delta - expected
            interaction_matrix[(k1, k2)] = {
                'phi': mean, 'delta': delta, 'expected': expected, 'synergy': synergy
            }

    # 상호작용 행렬 출력
    print(f"\n  {'':>8s}", end="")
    for k in keys:
        print(f" {k:>8s}", end="")
    print()

    for k1 in keys:
        print(f"  {k1:>8s}", end="")
        for k2 in keys:
            if k1 == k2:
                print(f" {'──':>8s}", end="")
            elif (k1, k2) in interaction_matrix:
                s = interaction_matrix[(k1, k2)]['synergy']
                print(f" {s:>+7.1f}%", end="")
            elif (k2, k1) in interaction_matrix:
                s = interaction_matrix[(k2, k1)]['synergy']
                print(f" {s:>+7.1f}%", end="")
            else:
                print(f" {'':>8s}", end="")
        print()

    # ── 4. 전체 통합 ──
    print(f"\n  [4] 전체 통합...")
    all_mean, all_std = run_with_interventions(keys, cells, steps, repeats)
    all_delta = (all_mean - base_mean) / max(base_mean, 1e-8) * 100
    sum_single = sum(e['delta'] for e in single_effects.values())
    print(f"  전체 통합: Φ={all_mean:.4f}  Δ={all_delta:+.1f}%")
    print(f"  개별 합:   {sum_single:+.1f}%")
    print(f"  시너지:    {all_delta - sum_single:+.1f}%")

    # ── 5. ASCII 지형도 ──
    print(f"\n{'═'*80}")
    print(f"  법칙 지형도 (단독 효과 + 상호작용)")
    print(f"{'═'*80}")

    # 단독 효과 바 차트
    print(f"\n  단독 효과:")
    sorted_single = sorted(single_effects.items(), key=lambda x: -x[1]['delta'])
    max_d = max(abs(e['delta']) for e in single_effects.values()) if single_effects else 1
    for key, e in sorted_single:
        bar_len = max(0, int(abs(e['delta']) / max(max_d, 0.1) * 25))
        if e['delta'] >= 0:
            bar = f"{'█' * bar_len} +{e['delta']:.1f}%"
        else:
            bar = f"{'▒' * bar_len} {e['delta']:.1f}%"
        print(f"  {key:<8s} │{bar}")

    # 시너지 상위 5개
    print(f"\n  시너지 상위 조합:")
    sorted_interactions = sorted(interaction_matrix.items(), key=lambda x: -x[1]['synergy'])
    for (k1, k2), info in sorted_interactions[:5]:
        sign = "시너지" if info['synergy'] > 0 else "간섭"
        print(f"  {k1}+{k2}: Δ={info['delta']:+.1f}%  (예상 {info['expected']:+.1f}%, {sign} {info['synergy']:+.1f}%)")

    print(f"\n  간섭 상위 조합:")
    for (k1, k2), info in sorted_interactions[-3:]:
        print(f"  {k1}+{k2}: Δ={info['delta']:+.1f}%  (예상 {info['expected']:+.1f}%, 간섭 {info['synergy']:+.1f}%)")

    # ── 5.5 JSON 출력 (phi-map --laws 호환) ──
    law_terrain_data = {
        "baseline_phi": base_mean,
        "baseline_std": base_std,
        "laws": [],
        "interactions": [],
        "integrated_phi": all_mean,
        "integrated_delta": all_delta,
        "total_synergy": all_delta - sum_single,
    }
    for key, e in single_effects.items():
        law_type = "Causal" if e['delta'] > 2 else ("AntiCausal" if e['delta'] < -1 else "Observational")
        law_terrain_data["laws"].append({
            "key": key, "name": INTERVENTIONS[key][0], "law_ids": [],
            "phi": e['phi'], "phi_std": e['std'], "delta_pct": e['delta'], "law_type": law_type,
        })
    for (k1, k2), info in interaction_matrix.items():
        law_terrain_data["interactions"].append({
            "law_a": k1, "law_b": k2,
            "combined_delta": info['delta'], "expected_delta": info['expected'], "synergy": info['synergy'],
        })
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "law_terrain.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    import json
    with open(json_path, 'w') as f:
        json.dump(law_terrain_data, f, indent=2, ensure_ascii=False)
    print(f"\n  JSON 출력: {json_path} (phi-map --laws 호환)")

    # ── 6. 법칙 분류 ──
    print(f"\n{'═'*80}")
    print(f"  법칙 분류 — 인과적 vs 관찰적")
    print(f"{'═'*80}")

    causal = [(k, e) for k, e in single_effects.items() if e['delta'] > 2]
    observational = [(k, e) for k, e in single_effects.items() if -1 < e['delta'] <= 2]
    anti = [(k, e) for k, e in single_effects.items() if e['delta'] <= -1]

    print(f"\n  인과적 법칙 (개입 시 Φ +2% 이상):")
    for k, e in sorted(causal, key=lambda x: -x[1]['delta']):
        print(f"    {k} ({INTERVENTIONS[k][0]}): +{e['delta']:.1f}%  ← 엔진에 내장 권장")

    print(f"\n  관찰적 법칙 (상관은 있지만 개입 무효):")
    for k, e in sorted(observational, key=lambda x: -x[1]['delta']):
        print(f"    {k} ({INTERVENTIONS[k][0]}): {e['delta']:+.1f}%  ← 모니터링 용도")

    if anti:
        print(f"\n  반인과적 (개입이 해로움):")
        for k, e in sorted(anti, key=lambda x: x[1]['delta']):
            print(f"    {k} ({INTERVENTIONS[k][0]}): {e['delta']:.1f}%  ← 하면 안 됨")


if __name__ == "__main__":
    main()
