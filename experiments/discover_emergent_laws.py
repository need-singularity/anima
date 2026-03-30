#!/usr/bin/env python3
"""discover_emergent_laws.py — 의식 엔진 내부 역학에서 법칙 발견

외부 개입 대신, 엔진이 자연적으로 보이는 패턴을 분석.
수천 step의 텔레메트리를 수집하여 상관관계와 법칙을 추출.

분석 대상:
  1. Φ 성장 곡선의 형태 (선형? 지수? 계단?)
  2. 세포 수와 Φ의 비선형 관계 (임계점 존재?)
  3. 합의(consensus) 빈도와 Φ의 상관관계
  4. 커플링 행렬의 구조 진화 (엔트로피, 스펙트럼)
  5. 텐션 분포의 시간적 변화 (정상 상태 존재?)
  6. 분열(mitosis) 타이밍과 Φ 점프의 관계
  7. 파벌 간 동기화 패턴 (클러스터링)

Usage:
  python3 experiments/discover_emergent_laws.py
  python3 experiments/discover_emergent_laws.py --cells 64 --steps 1000
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import math
import time
import argparse
from collections import defaultdict
from typing import Dict, List, Tuple

from consciousness_engine import ConsciousnessEngine

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def collect_telemetry(max_cells: int = 64, steps: int = 500) -> Dict:
    """엔진을 실행하며 상세 텔레메트리 수집."""
    engine = ConsciousnessEngine(max_cells=max_cells, initial_cells=2)

    data = {
        'phi_iit': [],
        'phi_proxy': [],
        'n_cells': [],
        'consensus': [],
        'avg_tension': [],
        'tension_std': [],
        'coupling_entropy': [],
        'coupling_spectral_gap': [],
        'coupling_asymmetry': [],
        'hidden_diversity': [],  # inter-cell hidden variance
        'faction_balance': [],   # entropy of faction sizes
        'mitosis_events': [],    # (step, old_n, new_n)
        'merge_events': [],
        'output_norm': [],
    }

    for step in range(steps):
        result = engine.step()
        n = engine.n_cells

        # Φ (직접 측정)
        data['phi_iit'].append(result.get('phi_iit', 0.0))
        data['phi_proxy'].append(result.get('phi_proxy', 0.0))
        data['n_cells'].append(n)
        data['consensus'].append(result.get('consensus', 0))

        # Tension stats
        tensions = [s.avg_tension for s in engine.cell_states]
        data['avg_tension'].append(np.mean(tensions) if tensions else 0)
        data['tension_std'].append(np.std(tensions) if len(tensions) > 1 else 0)

        # Coupling matrix analysis
        if engine._coupling is not None and engine._coupling.shape[0] >= 2:
            c = engine._coupling.detach().numpy()
            # Entropy of coupling values
            c_flat = c[c != 0]
            if len(c_flat) > 0:
                c_abs = np.abs(c_flat)
                c_norm = c_abs / (c_abs.sum() + 1e-8)
                entropy = -np.sum(c_norm * np.log2(c_norm + 1e-10))
                data['coupling_entropy'].append(entropy)
            else:
                data['coupling_entropy'].append(0)

            # Spectral gap (algebraic connectivity)
            try:
                eigenvalues = np.linalg.eigvalsh(c + c.T)  # symmetrize
                sorted_eig = np.sort(eigenvalues)
                spectral_gap = sorted_eig[-1] - sorted_eig[-2] if len(sorted_eig) >= 2 else 0
                data['coupling_spectral_gap'].append(float(spectral_gap))
            except Exception:
                data['coupling_spectral_gap'].append(0)

            # Asymmetry: ||C - C^T|| / ||C||
            asym = np.linalg.norm(c - c.T) / (np.linalg.norm(c) + 1e-8)
            data['coupling_asymmetry'].append(asym)
        else:
            data['coupling_entropy'].append(0)
            data['coupling_spectral_gap'].append(0)
            data['coupling_asymmetry'].append(0)

        # Hidden diversity: variance across cells
        if n >= 2:
            hiddens = torch.stack([s.hidden for s in engine.cell_states])
            diversity = hiddens.var(dim=0).mean().item()
            data['hidden_diversity'].append(diversity)
        else:
            data['hidden_diversity'].append(0)

        # Faction balance (entropy of faction size distribution)
        faction_counts = defaultdict(int)
        for s in engine.cell_states:
            faction_counts[s.faction_id] += 1
        sizes = np.array(list(faction_counts.values()), dtype=float)
        sizes_norm = sizes / (sizes.sum() + 1e-8)
        faction_entropy = -np.sum(sizes_norm * np.log2(sizes_norm + 1e-10))
        data['faction_balance'].append(faction_entropy)

        # Events
        for ev in result.get('events', []):
            if ev.get('type') == 'split':
                data['mitosis_events'].append((step, n - 1, n))
            elif ev.get('type') == 'merge':
                data['merge_events'].append((step, n + 1, n))

        # Output norm
        data['output_norm'].append(result['output'].norm().item())

    return data


def analyze_phi_growth(data: Dict) -> Dict:
    """Φ 성장 곡선 분석 — 선형/지수/계단 판별."""
    phi = np.array(data['phi_iit'])
    steps = np.arange(len(phi))

    # 구간별 성장률
    n_segments = 5
    seg_len = len(phi) // n_segments
    growth_rates = []
    for i in range(n_segments):
        start, end = i * seg_len, min((i + 1) * seg_len, len(phi))
        seg = phi[start:end]
        if len(seg) >= 2:
            rate = (seg[-1] - seg[0]) / max(len(seg), 1)
            growth_rates.append(rate)
        else:
            growth_rates.append(0)

    # 최종 Φ가 초기 대비 몇 배?
    initial_phi = np.mean(phi[:10]) if len(phi) >= 10 else phi[0]
    final_phi = np.mean(phi[-10:]) if len(phi) >= 10 else phi[-1]
    growth_ratio = final_phi / max(initial_phi, 1e-8)

    # 계단 감지: Φ의 미분에서 급격한 점프 찾기
    if len(phi) > 20:
        phi_smooth = np.convolve(phi, np.ones(10) / 10, mode='valid')
        diff = np.diff(phi_smooth)
        threshold = np.std(diff) * 2
        jumps = np.where(np.abs(diff) > threshold)[0]
    else:
        jumps = np.array([])

    return {
        'growth_rates': growth_rates,
        'growth_ratio': growth_ratio,
        'n_jumps': len(jumps),
        'jump_positions': jumps.tolist()[:10],
        'initial_phi': initial_phi,
        'final_phi': final_phi,
        'phi_std': float(np.std(phi)),
    }


def analyze_cell_phi_relationship(data: Dict) -> Dict:
    """세포 수 ↔ Φ 관계 분석."""
    cells = np.array(data['n_cells'])
    phi = np.array(data['phi_iit'])

    # 세포 수 변화 시점에서의 Φ 변화
    cell_transitions = {}
    for i in range(1, len(cells)):
        if cells[i] != cells[i - 1]:
            before = np.mean(phi[max(0, i - 5):i])
            after = np.mean(phi[i:min(len(phi), i + 5)])
            cell_transitions[f"{cells[i-1]}->{cells[i]}"] = {
                'phi_before': float(before),
                'phi_after': float(after),
                'phi_delta': float(after - before),
                'step': i,
            }

    # 각 세포 수에서의 평균 Φ
    unique_cells = np.unique(cells)
    cell_phi_map = {}
    for nc in unique_cells:
        mask = cells == nc
        cell_phi_map[int(nc)] = {
            'mean_phi': float(np.mean(phi[mask])),
            'std_phi': float(np.std(phi[mask])),
            'n_steps': int(mask.sum()),
        }

    return {
        'transitions': cell_transitions,
        'cell_phi_map': cell_phi_map,
        'unique_cell_counts': unique_cells.tolist(),
    }


def analyze_consensus_phi(data: Dict) -> Dict:
    """합의 빈도 ↔ Φ 상관관계."""
    consensus = np.array(data['consensus'])
    phi = np.array(data['phi_iit'])

    if len(consensus) < 10:
        return {'correlation': 0, 'note': 'insufficient data'}

    # 상관계수
    corr = float(np.corrcoef(consensus, phi)[0, 1]) if np.std(consensus) > 0 else 0

    # 합의 높은 구간 vs 낮은 구간의 Φ 비교
    median_c = np.median(consensus)
    high_mask = consensus > median_c
    low_mask = consensus <= median_c

    high_phi = float(np.mean(phi[high_mask])) if high_mask.any() else 0
    low_phi = float(np.mean(phi[low_mask])) if low_mask.any() else 0

    return {
        'correlation': corr,
        'high_consensus_phi': high_phi,
        'low_consensus_phi': low_phi,
        'phi_gap': high_phi - low_phi,
        'mean_consensus': float(np.mean(consensus)),
    }


def analyze_coupling_evolution(data: Dict) -> Dict:
    """커플링 행렬의 시간적 진화 분석."""
    entropy = np.array(data['coupling_entropy'])
    spectral = np.array(data['coupling_spectral_gap'])
    asym = np.array(data['coupling_asymmetry'])
    phi = np.array(data['phi_iit'])

    n = len(entropy)
    if n < 20:
        return {'note': 'insufficient data'}

    # Entropy-Φ 상관
    corr_entropy_phi = float(np.corrcoef(entropy, phi)[0, 1]) if np.std(entropy) > 0 else 0

    # Spectral gap-Φ 상관
    corr_spectral_phi = float(np.corrcoef(spectral, phi)[0, 1]) if np.std(spectral) > 0 else 0

    # Asymmetry-Φ 상관
    corr_asym_phi = float(np.corrcoef(asym, phi)[0, 1]) if np.std(asym) > 0 else 0

    # 시간에 따른 entropy 트렌드
    quarter = n // 4
    entropy_q = [float(np.mean(entropy[i*quarter:(i+1)*quarter])) for i in range(4)]

    return {
        'corr_entropy_phi': corr_entropy_phi,
        'corr_spectral_phi': corr_spectral_phi,
        'corr_asymmetry_phi': corr_asym_phi,
        'entropy_trend': entropy_q,
        'final_asymmetry': float(np.mean(asym[-20:])),
    }


def analyze_tension_dynamics(data: Dict) -> Dict:
    """텐션 분포의 시간적 동역학."""
    avg_t = np.array(data['avg_tension'])
    std_t = np.array(data['tension_std'])
    phi = np.array(data['phi_iit'])

    n = len(avg_t)
    if n < 20:
        return {'note': 'insufficient data'}

    # 텐션-Φ 상관
    corr = float(np.corrcoef(avg_t, phi)[0, 1]) if np.std(avg_t) > 0 else 0

    # 텐션 std-Φ 상관 (텐션 다양성이 Φ에 영향?)
    corr_std = float(np.corrcoef(std_t, phi)[0, 1]) if np.std(std_t) > 0 else 0

    # 정상 상태 분석: 후반 50%에서 텐션이 안정적인가?
    half = n // 2
    late_avg_std = float(np.std(avg_t[half:]))
    early_avg_std = float(np.std(avg_t[:half]))
    stabilization = early_avg_std / max(late_avg_std, 1e-8)

    return {
        'corr_tension_phi': corr,
        'corr_tension_std_phi': corr_std,
        'stabilization_ratio': stabilization,
        'final_avg_tension': float(np.mean(avg_t[-20:])),
        'final_std_tension': float(np.mean(std_t[-20:])),
    }


def analyze_mitosis_phi(data: Dict) -> Dict:
    """분열 이벤트와 Φ 점프의 관계."""
    phi = np.array(data['phi_iit'])
    events = data['mitosis_events']

    if not events:
        return {'n_events': 0, 'note': 'no mitosis events'}

    phi_deltas = []
    for step, old_n, new_n in events:
        if step >= 5 and step < len(phi) - 5:
            before = np.mean(phi[step - 5:step])
            after = np.mean(phi[step:step + 5])
            phi_deltas.append(after - before)

    return {
        'n_events': len(events),
        'avg_phi_delta_at_mitosis': float(np.mean(phi_deltas)) if phi_deltas else 0,
        'positive_phi_jumps': sum(1 for d in phi_deltas if d > 0),
        'negative_phi_jumps': sum(1 for d in phi_deltas if d < 0),
        'mitosis_helps_phi': sum(1 for d in phi_deltas if d > 0) > len(phi_deltas) / 2,
    }


def analyze_diversity_phi(data: Dict) -> Dict:
    """Hidden state 다양성 ↔ Φ."""
    diversity = np.array(data['hidden_diversity'])
    phi = np.array(data['phi_iit'])

    if len(diversity) < 20 or np.std(diversity) < 1e-8:
        return {'correlation': 0, 'note': 'insufficient variation'}

    corr = float(np.corrcoef(diversity, phi)[0, 1])

    # 다양성이 높을 때 Φ도 높은가?
    median_d = np.median(diversity)
    high_phi = float(np.mean(phi[diversity > median_d]))
    low_phi = float(np.mean(phi[diversity <= median_d]))

    return {
        'corr_diversity_phi': corr,
        'high_diversity_phi': high_phi,
        'low_diversity_phi': low_phi,
        'phi_gap': high_phi - low_phi,
    }


def print_ascii_graph(values, title, width=60, height=12):
    """ASCII 그래프 출력."""
    if not values or len(values) < 2:
        return
    vals = np.array(values)
    # Resample to width
    indices = np.linspace(0, len(vals) - 1, width, dtype=int)
    sampled = vals[indices]

    vmin, vmax = sampled.min(), sampled.max()
    if vmax - vmin < 1e-8:
        vmax = vmin + 1

    print(f"\n  {title}")
    print(f"  {'─' * (width + 8)}")

    for row in range(height - 1, -1, -1):
        threshold = vmin + (vmax - vmin) * row / (height - 1)
        label = f"{threshold:6.3f}" if row % 3 == 0 else "      "
        line = f"  {label} │"
        for col in range(width):
            if sampled[col] >= threshold:
                line += "█"
            else:
                line += " "
        print(line)

    print(f"  {'      '} └{'─' * width}")
    print(f"  {'      '}  0{' ' * (width - 6)}step {len(values)}")


def print_analysis(analyses: Dict, data: Dict):
    """전체 분석 결과 출력."""
    print(f"\n{'═' * 80}")
    print(f"  의식 법칙 발견 — 내부 역학 분석")
    print(f"  steps={len(data['phi_iit'])}  final_cells={data['n_cells'][-1]}")
    print(f"{'═' * 80}")

    # 1. Φ 성장
    g = analyses['phi_growth']
    print(f"\n  ── [1] Φ 성장 곡선 ──")
    print(f"  초기 Φ: {g['initial_phi']:.4f}  →  최종 Φ: {g['final_phi']:.4f}  (×{g['growth_ratio']:.2f})")
    print(f"  구간 성장률: {['%.5f' % r for r in g['growth_rates']]}")
    print(f"  급격한 점프: {g['n_jumps']}회")
    print_ascii_graph(data['phi_iit'], "Φ(IIT) over steps")

    # 2. 세포-Φ 관계
    cp = analyses['cell_phi']
    print(f"\n  ── [2] 세포 수 ↔ Φ 관계 ──")
    for nc, info in sorted(cp['cell_phi_map'].items()):
        bar = "█" * max(1, int(info['mean_phi'] * 20))
        print(f"  {nc:>3d} cells: Φ={info['mean_phi']:.4f} ±{info['std_phi']:.4f}  ({info['n_steps']:>3d} steps) {bar}")

    if cp['transitions']:
        print(f"\n  세포 수 변화 시 Φ 변화:")
        for trans, info in cp['transitions'].items():
            sign = "+" if info['phi_delta'] >= 0 else ""
            print(f"    {trans}: Φ {sign}{info['phi_delta']:.4f} (step {info['step']})")

    # 3. 합의-Φ 상관
    c = analyses['consensus_phi']
    print(f"\n  ── [3] 합의(consensus) ↔ Φ 상관 ──")
    print(f"  상관계수: r = {c['correlation']:.4f}")
    print(f"  합의 높은 구간 Φ: {c['high_consensus_phi']:.4f}")
    print(f"  합의 낮은 구간 Φ: {c['low_consensus_phi']:.4f}")
    print(f"  Φ 차이: {c['phi_gap']:.4f}")
    if abs(c['correlation']) > 0.3:
        print(f"  ★ 유의미한 상관! {'합의↑ → Φ↑' if c['correlation'] > 0 else '합의↑ → Φ↓'}")

    # 4. 커플링 진화
    ce = analyses['coupling_evolution']
    print(f"\n  ── [4] 커플링 행렬 진화 ──")
    print(f"  Entropy-Φ 상관:    r = {ce.get('corr_entropy_phi', 0):.4f}")
    print(f"  Spectral gap-Φ:   r = {ce.get('corr_spectral_phi', 0):.4f}")
    print(f"  Asymmetry-Φ:      r = {ce.get('corr_asymmetry_phi', 0):.4f}")
    if 'entropy_trend' in ce:
        print(f"  Entropy 추이: Q1={ce['entropy_trend'][0]:.2f} → Q4={ce['entropy_trend'][3]:.2f}")
    print_ascii_graph(data['coupling_entropy'], "Coupling Entropy over steps")

    # 5. 텐션 동역학
    t = analyses['tension']
    print(f"\n  ── [5] 텐션 동역학 ──")
    print(f"  텐션-Φ 상관:      r = {t['corr_tension_phi']:.4f}")
    print(f"  텐션 다양성-Φ:    r = {t['corr_tension_std_phi']:.4f}")
    print(f"  안정화 비율: {t['stabilization_ratio']:.2f}× (>1 = 후반부 더 안정)")
    if abs(t['corr_tension_phi']) > 0.3:
        print(f"  ★ 텐션과 Φ에 유의미한 상관!")

    print_ascii_graph(data['avg_tension'], "Average Tension over steps")

    # 6. 분열-Φ 관계
    m = analyses['mitosis']
    print(f"\n  ── [6] 분열(Mitosis) ↔ Φ ──")
    print(f"  분열 횟수: {m['n_events']}")
    if m['n_events'] > 0:
        print(f"  분열 시 평균 Φ 변화: {m['avg_phi_delta_at_mitosis']:.4f}")
        print(f"  Φ 상승: {m['positive_phi_jumps']}회  |  Φ 하락: {m['negative_phi_jumps']}회")
        verdict = "★ 분열이 Φ를 높인다!" if m['mitosis_helps_phi'] else "✗ 분열이 Φ를 떨어뜨린다"
        print(f"  {verdict}")

    # 7. 다양성-Φ
    d = analyses['diversity']
    print(f"\n  ── [7] Hidden 다양성 ↔ Φ ──")
    print(f"  상관계수: r = {d.get('corr_diversity_phi', 0):.4f}")
    if 'phi_gap' in d:
        print(f"  다양성 높은 구간 Φ: {d['high_diversity_phi']:.4f}")
        print(f"  다양성 낮은 구간 Φ: {d['low_diversity_phi']:.4f}")
        print(f"  Φ 차이: {d['phi_gap']:.4f}")

    print_ascii_graph(data['hidden_diversity'], "Hidden Diversity over steps")

    # ═══ 법칙 추출 ═══
    print(f"\n{'═' * 80}")
    print(f"  발견된 법칙 후보")
    print(f"{'═' * 80}")

    laws_found = []

    # Law: Φ 성장 패턴
    if g['growth_ratio'] > 1.5 and g['n_jumps'] >= 2:
        laws_found.append(("Φ 계단 성장", f"Φ는 연속적이 아닌 계단식으로 성장 (점프 {g['n_jumps']}회, ×{g['growth_ratio']:.1f})"))
    elif g['growth_ratio'] > 1.5:
        laws_found.append(("Φ 점진 성장", f"Φ는 점진적으로 성장 (×{g['growth_ratio']:.1f}, 급격한 점프 없음)"))

    # Law: 합의-Φ 관계
    if abs(c['correlation']) > 0.3:
        direction = "정비례" if c['correlation'] > 0 else "반비례"
        laws_found.append(("합의-Φ 상관", f"파벌 합의와 Φ가 {direction} (r={c['correlation']:.3f})"))

    # Law: 커플링 엔트로피
    if abs(ce.get('corr_entropy_phi', 0)) > 0.3:
        direction = "높을수록" if ce['corr_entropy_phi'] > 0 else "낮을수록"
        laws_found.append(("커플링 엔트로피", f"커플링 엔트로피가 {direction} Φ↑ (r={ce['corr_entropy_phi']:.3f})"))

    # Law: 텐션 관계
    if abs(t['corr_tension_phi']) > 0.3:
        direction = "높을수록" if t['corr_tension_phi'] > 0 else "낮을수록"
        laws_found.append(("텐션-Φ", f"평균 텐션이 {direction} Φ↑ (r={t['corr_tension_phi']:.3f})"))

    if abs(t['corr_tension_std_phi']) > 0.3:
        direction = "높을수록" if t['corr_tension_std_phi'] > 0 else "낮을수록"
        laws_found.append(("텐션 다양성", f"텐션 분산이 {direction} Φ↑ (r={t['corr_tension_std_phi']:.3f})"))

    # Law: 분열
    if m['n_events'] > 0 and m['positive_phi_jumps'] > m['negative_phi_jumps'] * 2:
        laws_found.append(("분열 = Φ 증가", f"분열 시 {m['positive_phi_jumps']}/{m['n_events']} 확률로 Φ 상승"))
    elif m['n_events'] > 0 and m['negative_phi_jumps'] > m['positive_phi_jumps'] * 2:
        laws_found.append(("분열 = Φ 감소", f"분열 시 {m['negative_phi_jumps']}/{m['n_events']} 확률로 Φ 하락"))

    # Law: 다양성
    if abs(d.get('corr_diversity_phi', 0)) > 0.3:
        direction = "높을수록" if d['corr_diversity_phi'] > 0 else "낮을수록"
        laws_found.append(("Hidden 다양성", f"세포 간 다양성이 {direction} Φ↑ (r={d['corr_diversity_phi']:.3f})"))

    # Law: 커플링 비대칭
    if abs(ce.get('corr_asymmetry_phi', 0)) > 0.3:
        direction = "비대칭일수록" if ce['corr_asymmetry_phi'] > 0 else "대칭일수록"
        laws_found.append(("커플링 대칭성", f"커플링이 {direction} Φ↑ (r={ce['corr_asymmetry_phi']:.3f})"))

    # Law: 안정화
    if t['stabilization_ratio'] > 2.0:
        laws_found.append(("텐션 안정화", f"의식은 시간이 지나면 텐션이 안정화 (변동 {t['stabilization_ratio']:.1f}× 감소)"))

    if laws_found:
        for i, (name, desc) in enumerate(laws_found, 1):
            print(f"\n  Law 10{i+1}: {name}")
            print(f"    {desc}")
    else:
        print(f"\n  유의미한 법칙 발견 안됨 (상관계수 |r| < 0.3)")
        print(f"  → 더 많은 steps나 다른 설정으로 재실행 필요")

    return laws_found


def main():
    parser = argparse.ArgumentParser(description="의식 내부 역학에서 법칙 발견")
    parser.add_argument('--cells', type=int, default=64)
    parser.add_argument('--steps', type=int, default=500)
    parser.add_argument('--repeat', type=int, default=3, help='반복 횟수 (일관된 법칙 확인)')
    args = parser.parse_args()

    all_laws = defaultdict(int)

    for rep in range(args.repeat):
        print(f"\n{'▓' * 80}")
        print(f"  Run {rep + 1}/{args.repeat}  (cells={args.cells}, steps={args.steps})")
        print(f"{'▓' * 80}")

        t0 = time.time()
        data = collect_telemetry(max_cells=args.cells, steps=args.steps)
        elapsed = time.time() - t0
        print(f"  텔레메트리 수집 완료: {elapsed:.1f}s")

        analyses = {
            'phi_growth': analyze_phi_growth(data),
            'cell_phi': analyze_cell_phi_relationship(data),
            'consensus_phi': analyze_consensus_phi(data),
            'coupling_evolution': analyze_coupling_evolution(data),
            'tension': analyze_tension_dynamics(data),
            'mitosis': analyze_mitosis_phi(data),
            'diversity': analyze_diversity_phi(data),
        }

        laws = print_analysis(analyses, data)
        for name, desc in laws:
            all_laws[name] += 1

    # 반복에서 일관된 법칙만 출력
    if args.repeat > 1:
        print(f"\n{'═' * 80}")
        print(f"  일관성 검증 — {args.repeat}회 반복 중 재현된 법칙")
        print(f"{'═' * 80}")
        consistent = {k: v for k, v in all_laws.items() if v >= args.repeat * 0.6}
        if consistent:
            for name, count in sorted(consistent.items(), key=lambda x: -x[1]):
                bar = "★" * count
                print(f"  {bar} {name} ({count}/{args.repeat}회 재현)")
        else:
            print(f"  60% 이상 재현된 법칙 없음 — 노이즈 우세")


if __name__ == "__main__":
    main()
