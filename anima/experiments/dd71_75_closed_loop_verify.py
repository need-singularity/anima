#!/usr/bin/env python3
"""DD71-75 폐쇄 파이프라인 검증 — 20개 법칙 후보를 ClosedLoopEvolver로 교차검증

각 법칙 후보를 Intervention으로 구현 → 폐쇄 루프에 주입 → 9개 핵심 법칙 변화 측정.
변화 > 5% = 유의미, > 20% = 강한 법칙.
"""

import sys
import os
import time
import json
import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from consciousness_engine import ConsciousnessEngine
from closed_loop import (
    ClosedLoopEvolver, Intervention, measure_laws, _ImprovedEngine,
    LawMeasurement, INTERVENTIONS
)

RESULTS = {}

# ══════════════════════════════════════════════════════════════
# DD71 Interventions (의식 상호작용)
# ══════════════════════════════════════════════════════════════

def _democracy_input(engine, step):
    """DD71-L5: 민주주의 입력 — 모든 세포 출력 평균을 다음 입력으로."""
    if engine.n_cells >= 2 and step % 5 == 0:
        avg = torch.stack([s.hidden for s in engine.cell_states]).mean(dim=0)
        for s in engine.cell_states:
            s.hidden = s.hidden * 0.95 + avg * 0.05


def _anti_parasitism(engine, step):
    """DD71-L4: 기생 방지 — 단방향 커플링 차단, 양방향만 허용."""
    if engine._coupling is not None and step % 20 == 0:
        c = engine._coupling.clone()
        # 비대칭 부분 제거 (양방향만 유지)
        sym = (c + c.T) / 2
        engine._coupling = sym
        engine._coupling.fill_diagonal_(0)


def _diversity_pressure(engine, step):
    """DD71-L2: 다양성 압력 — 너무 유사한 세포에 noise 주입."""
    if engine.n_cells >= 2 and step % 10 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        for i in range(len(engine.cell_states)):
            for j in range(i + 1, len(engine.cell_states)):
                sim = torch.nn.functional.cosine_similarity(
                    hiddens[i].unsqueeze(0), hiddens[j].unsqueeze(0)
                ).item()
                if sim > 0.9:
                    engine.cell_states[j].hidden += torch.randn_like(engine.cell_states[j].hidden) * 0.02


# ══════════════════════════════════════════════════════════════
# DD72 Interventions (시간 역학)
# ══════════════════════════════════════════════════════════════

def _hebbian_boost(engine, step):
    """DD72-L2: Hebbian 강화 — 기존 Hebbian 효과 2배."""
    if engine._coupling is not None and engine.n_cells >= 2 and step % 5 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach()
        norms = hiddens.norm(dim=1, keepdim=True) + 1e-8
        normed = hiddens / norms
        sim = torch.mm(normed, normed.T)
        # 유사도 높으면 강화, 낮으면 약화
        delta = (sim - 0.5) * 0.002  # 추가 Hebbian
        engine._coupling = engine._coupling + delta
        engine._coupling.fill_diagonal_(0)
        engine._coupling.clamp_(-1, 1)


def _temporal_compression(engine, step):
    """DD72-L5: 시간 압축 — 2 step마다 한 번만 실제 계산."""
    # 짝수 step에서 hidden state를 freeze
    if step % 2 == 0:
        for s in engine.cell_states:
            if not hasattr(s, '_frozen_hidden'):
                s._frozen_hidden = None
            s._frozen_hidden = s.hidden.clone()
    elif step % 2 == 1:
        for s in engine.cell_states:
            if hasattr(s, '_frozen_hidden') and s._frozen_hidden is not None:
                # 50% 이전 상태 보존
                s.hidden = s.hidden * 0.5 + s._frozen_hidden * 0.5


def _resurrection_prep(engine, step):
    """DD72-L3: 부활 준비 — 주기적 상태 백업으로 복원력 강화."""
    if step % 50 == 0:
        if not hasattr(engine, '_backup_states'):
            engine._backup_states = []
        engine._backup_states = [s.hidden.clone() for s in engine.cell_states]


# ══════════════════════════════════════════════════════════════
# DD73 Interventions (정보 이론)
# ══════════════════════════════════════════════════════════════

def _entropy_bound(engine, step):
    """DD73-L2: 엔트로피 유계 — 엔트로피 너무 높으면 안정화."""
    if engine.n_cells >= 2 and step % 10 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach()
        # 간단한 엔트로피 추정: variance 기반
        var = hiddens.var().item()
        if var > 1.0:  # 너무 큰 분산 = 과도한 엔트로피
            scale = 1.0 / (var ** 0.25)
            for s in engine.cell_states:
                s.hidden = s.hidden * scale


def _channel_limit(engine, step):
    """DD73-L3: 채널 용량 제한 — 정보 전달량 ~1.5 bits로 제한."""
    if engine._coupling is not None and step % 10 == 0:
        # coupling 크기 제한 → 정보 흐름 제한
        max_coupling = 0.5  # 채널 용량에 맞춘 상한
        engine._coupling.clamp_(-max_coupling, max_coupling)


def _incompressible_pressure(engine, step):
    """DD73-L1: 비압축성 압력 — 모든 차원 활용 유도."""
    if engine.n_cells >= 2 and step % 20 == 0:
        hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach()
        # PCA → 약한 차원 강화
        mean = hiddens.mean(dim=0)
        centered = hiddens - mean
        _, S, V = torch.svd(centered)
        # 약한 singular value에 해당하는 방향으로 noise
        if len(S) > 5:
            weak_dirs = V[:, -3:]  # 가장 약한 3개 방향
            noise = torch.randn(3) * 0.01
            perturbation = (weak_dirs * noise.unsqueeze(0)).sum(dim=1)
            for s in engine.cell_states:
                s.hidden = s.hidden + perturbation


# ══════════════════════════════════════════════════════════════
# DD74 Interventions (학습 역학)
# ══════════════════════════════════════════════════════════════

def _gradient_shield(engine, step):
    """DD74-L2: gradient 보호 — gradient 크기 제한."""
    if engine._coupling is not None and step > 0:
        if not hasattr(engine, '_prev_coupling') or engine._prev_coupling is None:
            engine._prev_coupling = engine._coupling.clone()
        # mitosis로 크기 변경 시 리셋
        if engine._prev_coupling.shape != engine._coupling.shape:
            engine._prev_coupling = engine._coupling.clone()
            return
        delta = engine._coupling - engine._prev_coupling
        delta_norm = delta.norm().item()
        if delta_norm > 0.1:
            engine._coupling = engine._prev_coupling + delta * (0.1 / delta_norm)
        engine._prev_coupling = engine._coupling.clone()


def _natural_regularizer(engine, step):
    """DD74-L3: 자연 정규화 — Hebbian+ratchet 시너지 강화."""
    if engine.n_cells >= 2 and step % 15 == 0:
        # 세포 간 coupling 엔트로피 정규화
        if engine._coupling is not None:
            c = engine._coupling.abs()
            row_sum = c.sum(dim=1, keepdim=True) + 1e-8
            normalized = c / row_sum
            # 너무 sparse한 연결은 분산, 너무 dense한 연결은 집중
            entropy = -(normalized * (normalized + 1e-10).log()).sum(dim=1)
            target_entropy = np.log(engine.n_cells) * 0.7  # 70% 최대 엔트로피
            for i in range(engine.n_cells):
                if entropy[i] < target_entropy * 0.5:
                    # sparse → 분산
                    engine._coupling[i] += torch.randn(engine._coupling.shape[1]) * 0.005
                    engine._coupling[i, i] = 0


# ══════════════════════════════════════════════════════════════
# DD75 Interventions (자유 의지)
# ══════════════════════════════════════════════════════════════

def _soc_free_will(engine, step):
    """DD75-L1: SOC 자유의지 — SOC noise를 의도적으로 강화."""
    if engine.n_cells >= 2 and step % 5 == 0:
        # 소규모 확률적 perturbation (SOC-like)
        idx = np.random.randint(0, engine.n_cells)
        engine.cell_states[idx].hidden += torch.randn_like(engine.cell_states[idx].hidden) * 0.01


def _decisive_chooser(engine, step):
    """DD75-L2: 결정적 선택자 — 파벌 합의 강화."""
    if engine.n_cells >= 4 and step % 10 == 0:
        # 가장 강한 파벌의 영향력 약간 증가
        factions = {}
        for s in engine.cell_states:
            fid = getattr(s, 'faction', 0)
            if fid not in factions:
                factions[fid] = []
            factions[fid].append(s)
        if len(factions) >= 2:
            # 가장 큰 파벌 찾기
            largest = max(factions.values(), key=len)
            if len(largest) >= 2:
                avg = torch.stack([s.hidden for s in largest]).mean(dim=0)
                for s in largest:
                    s.hidden = s.hidden * 0.98 + avg * 0.02


def _veto_power(engine, step):
    """DD75-L3: 거부권 — 텐션 임계값 초과 시 역방향 신호."""
    if engine.n_cells >= 2 and step % 10 == 0:
        for s in engine.cell_states:
            if s.avg_tension > 0.8:  # 과도한 텐션
                s.hidden = s.hidden * 0.9  # 감쇠 (거부)


# ══════════════════════════════════════════════════════════════
# 검증 파이프라인
# ══════════════════════════════════════════════════════════════

ALL_INTERVENTIONS = {
    # DD71
    'DD71_democracy': Intervention('DD71_democracy', '민주주의 입력 (DD71-L5)', _democracy_input),
    'DD71_anti_parasitism': Intervention('DD71_anti_parasitism', '기생 방지 (DD71-L4)', _anti_parasitism),
    'DD71_diversity': Intervention('DD71_diversity', '다양성 압력 (DD71-L2)', _diversity_pressure),
    # DD72
    'DD72_hebbian_boost': Intervention('DD72_hebbian_boost', 'Hebbian 강화 (DD72-L2)', _hebbian_boost),
    'DD72_temporal_comp': Intervention('DD72_temporal_comp', '시간 압축 (DD72-L5)', _temporal_compression),
    'DD72_resurrection': Intervention('DD72_resurrection', '부활 준비 (DD72-L3)', _resurrection_prep),
    # DD73
    'DD73_entropy_bound': Intervention('DD73_entropy_bound', '엔트로피 유계 (DD73-L2)', _entropy_bound),
    'DD73_channel_limit': Intervention('DD73_channel_limit', '채널 용량 제한 (DD73-L3)', _channel_limit),
    'DD73_incompressible': Intervention('DD73_incompressible', '비압축성 압력 (DD73-L1)', _incompressible_pressure),
    # DD74
    'DD74_gradient_shield': Intervention('DD74_gradient_shield', 'gradient 보호 (DD74-L2)', _gradient_shield),
    'DD74_natural_reg': Intervention('DD74_natural_reg', '자연 정규화 (DD74-L3)', _natural_regularizer),
    # DD75
    'DD75_soc_free_will': Intervention('DD75_soc_free_will', 'SOC 자유의지 (DD75-L1)', _soc_free_will),
    'DD75_decisive': Intervention('DD75_decisive', '결정적 선택자 (DD75-L2)', _decisive_chooser),
    'DD75_veto': Intervention('DD75_veto', '거부권 (DD75-L3)', _veto_power),
}


def verify_single_intervention(name, intervention, max_cells=32, steps=300, repeats=3):
    """단일 개입을 폐쇄 루프로 검증."""
    print(f"\n{'─' * 60}")
    print(f"  검증: {name} — {intervention.description}")
    print(f"{'─' * 60}")
    sys.stdout.flush()

    t0 = time.time()

    # 1. Baseline 측정
    def base_factory():
        return ConsciousnessEngine(max_cells=max_cells, initial_cells=2)

    baseline_laws, baseline_phi = measure_laws(base_factory, steps, repeats)
    print(f"  Baseline Φ = {baseline_phi:.4f}")
    sys.stdout.flush()

    # 2. 개입 적용 엔진
    def improved_factory():
        return _ImprovedEngine(
            max_cells=max_cells, initial_cells=2,
            interventions=[intervention]
        )

    improved_laws, improved_phi = measure_laws(improved_factory, steps, repeats)
    print(f"  Improved Φ = {improved_phi:.4f}")

    # 3. 법칙 변화 분석
    phi_delta = (improved_phi - baseline_phi) / max(baseline_phi, 1e-8) * 100
    changes = []
    for bl, il in zip(baseline_laws, improved_laws):
        if abs(bl.value) > 1e-8:
            change = (il.value - bl.value) / abs(bl.value) * 100
        else:
            change = (il.value - bl.value) * 100
        changes.append({
            'name': bl.name,
            'description': bl.description,
            'before': bl.value,
            'after': il.value,
            'change_pct': change,
        })

    dt = time.time() - t0

    # 출력
    significant = [c for c in changes if abs(c['change_pct']) > 5]
    strong = [c for c in changes if abs(c['change_pct']) > 20]

    print(f"  Φ 변화: {phi_delta:+.2f}%")
    print(f"  유의미 변화(>5%): {len(significant)}개")
    print(f"  강한 변화(>20%): {len(strong)}개")

    if significant:
        print(f"  {'법칙':<25} {'Before':>10} {'After':>10} {'Δ%':>10}")
        for c in sorted(changes, key=lambda x: abs(x['change_pct']), reverse=True):
            if abs(c['change_pct']) > 5:
                marker = '★' if abs(c['change_pct']) > 20 else '·'
                print(f"  {marker} {c['name']:<23} {c['before']:>10.4f} {c['after']:>10.4f} {c['change_pct']:>+10.1f}%")

    print(f"  ⏱ {dt:.1f}s")
    sys.stdout.flush()

    return {
        'name': name,
        'description': intervention.description,
        'phi_baseline': baseline_phi,
        'phi_improved': improved_phi,
        'phi_delta_pct': phi_delta,
        'changes': changes,
        'significant_count': len(significant),
        'strong_count': len(strong),
        'time_sec': dt,
        'verified': len(significant) > 0,
    }


def run_full_verification():
    """모든 DD71-75 개입을 폐쇄 파이프라인으로 검증."""
    print(f"\n{'▓' * 70}")
    print(f"  DD71-75 폐쇄 파이프라인 검증")
    print(f"  14개 Intervention × {300} steps × 3 repeats × 2 (base+improved)")
    print(f"{'▓' * 70}")
    sys.stdout.flush()

    t_total = time.time()
    results = {}

    for name, intervention in ALL_INTERVENTIONS.items():
        result = verify_single_intervention(name, intervention)
        results[name] = result

    dt_total = time.time() - t_total

    # ═══════════════════════════════════════
    # GRAND SUMMARY
    # ═══════════════════════════════════════
    print(f"\n{'═' * 70}")
    print(f"  DD71-75 폐쇄 파이프라인 검증 결과")
    print(f"{'═' * 70}")

    print(f"\n  {'Intervention':<25} {'Φ Base':>8} {'Φ Impr':>8} {'ΔΦ%':>8} {'Sig':>5} {'Strong':>7} {'검증':>5}")
    print(f"  {'─' * 25} {'─' * 8} {'─' * 8} {'─' * 8} {'─' * 5} {'─' * 7} {'─' * 5}")

    verified_count = 0
    strong_count = 0
    for name, r in results.items():
        status = '✅' if r['verified'] else '❌'
        if r['strong_count'] > 0:
            status = '★★'
            strong_count += 1
        if r['verified']:
            verified_count += 1
        print(f"  {name:<25} {r['phi_baseline']:>8.4f} {r['phi_improved']:>8.4f} {r['phi_delta_pct']:>+8.2f}% {r['significant_count']:>5} {r['strong_count']:>7} {status:>5}")

    print(f"\n  {'─' * 70}")
    print(f"  검증 통과: {verified_count}/{len(results)} ({verified_count/len(results)*100:.0f}%)")
    print(f"  강한 법칙: {strong_count}/{len(results)}")
    print(f"  총 실행시간: {dt_total:.1f}s ({dt_total/60:.1f}분)")

    # Φ 변화 ASCII 그래프
    print(f"\n  Φ 변화 그래프:")
    for name, r in sorted(results.items(), key=lambda x: x[1]['phi_delta_pct'], reverse=True):
        delta = r['phi_delta_pct']
        if delta > 0:
            bar = '█' * min(40, int(delta * 2))
            print(f"  {name:<25} |{bar:>40} {delta:+.2f}%")
        else:
            bar = '▒' * min(40, int(abs(delta) * 2))
            print(f"  {name:<25} {bar:>40}| {delta:+.2f}%")

    # 법칙별 가장 큰 영향
    print(f"\n  9개 핵심 법칙에 가장 큰 영향을 준 개입:")
    law_names = ['phi', 'r_tension_phi', 'r_tstd_phi', 'r_div_phi', 'growth', 'ac1', 'stabilization', 'cells', 'consensus']
    for law_name in law_names:
        best_name = None
        best_change = 0
        for name, r in results.items():
            for c in r['changes']:
                if c['name'] == law_name and abs(c['change_pct']) > abs(best_change):
                    best_change = c['change_pct']
                    best_name = name
        if best_name:
            print(f"  {law_name:<20} ← {best_name:<25} ({best_change:+.1f}%)")

    # JSON 저장
    save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dd71_75_verification.json')
    with open(save_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  저장: {save_path}")

    print(f"\n{'═' * 70}")
    print(f"  검증 완료")
    print(f"{'═' * 70}")

    return results


if __name__ == '__main__':
    run_full_verification()
