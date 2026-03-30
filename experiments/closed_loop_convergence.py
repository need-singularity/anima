#!/usr/bin/env python3
"""closed_loop_convergence.py — 폐쇄 루프 수렴 검출 + 다중 축 루프

4가지 루프를 동시에 실행:
  1. 수렴 검출 — N사이클 돌려서 법칙 변화가 0에 수렴하는가?
  2. 2차 병목 추적 — Law 105 소멸 후 Law 107이 다음 타겟
  3. Frustration 루프 — F_c=0.10 역추적
  4. 대규모 루프 — 64c에서 동일 루프

Usage:
  python3 experiments/closed_loop_convergence.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import numpy as np
import time
import json
from collections import defaultdict
from consciousness_engine import ConsciousnessEngine
from closed_loop import ClosedLoopEvolver, measure_laws, _phi_fast, Intervention, INTERVENTIONS

try:
    from consciousness_laws import PSI_ALPHA as PSI_COUPLING
except ImportError:
    PSI_COUPLING = 0.014


# ══════════════════════════════════════════
# 추가 개입: Frustration (Law 137)
# ══════════════════════════════════════════

def _frustration_inject(engine, step):
    """Law 137: F_c=0.10 임계 frustration 주입.
    세포의 10%를 반전(antiferro)시켜 텐션 생성."""
    if step % 30 == 0 and engine.n_cells >= 4 and engine._coupling is not None:
        n = engine.n_cells
        n_frustrated = max(1, int(n * 0.10))  # F_c = 0.10
        indices = np.random.choice(n, size=n_frustrated, replace=False)
        for idx in indices:
            # 해당 세포의 커플링을 반전
            engine._coupling[idx, :] *= -1
            engine._coupling[:, idx] *= -1
            engine._coupling[idx, idx] = 0


def _diversity_pressure(engine, step):
    """Law 107 역추적: hidden 다양성 강제 증가.
    세포 간 거리가 줄어들면 반발력 적용."""
    if step % 15 == 0 and engine.n_cells >= 3:
        hiddens = torch.stack([s.hidden for s in engine.cell_states])
        mean_h = hiddens.mean(dim=0)
        for i in range(engine.n_cells):
            diff = engine.cell_states[i].hidden - mean_h
            norm = diff.norm().item()
            if norm < 0.1:  # 너무 가까우면 밀어내기
                engine.cell_states[i].hidden = engine.cell_states[i].hidden + diff * 0.1


EXTRA_INTERVENTIONS = [
    Intervention("frustration", "F_c=0.10 frustration 주입 (Law 137)", _frustration_inject),
    Intervention("diversity", "hidden 다양성 압력 (Law 107 역추적)", _diversity_pressure),
]


# ══════════════════════════════════════════
# 루프 1: 수렴 검출
# ══════════════════════════════════════════

def loop1_convergence():
    """N사이클 돌려서 법칙 변화량이 수렴하는가?"""
    print(f"\n{'═'*70}")
    print(f"  루프 1: 수렴 검출 — 법칙 변화가 0에 수렴하는가?")
    print(f"{'═'*70}")

    evolver = ClosedLoopEvolver(max_cells=32, steps=300, repeats=3)
    # 추가 개입 등록
    INTERVENTIONS.extend(EXTRA_INTERVENTIONS)

    max_cycles = 6
    change_magnitudes = []

    for i in range(max_cycles):
        print(f"\n  ─── Cycle {i+1}/{max_cycles} ───")
        report = evolver.run_cycle()

        # 변화 크기 = 모든 변화 법칙의 |change_pct| 평균
        if report.laws_changed:
            magnitude = np.mean([abs(lc['change_pct']) for lc in report.laws_changed])
        else:
            magnitude = 0
        change_magnitudes.append(magnitude)

        print(f"  Φ: {report.phi_baseline:.4f} → {report.phi_improved:.4f} ({report.phi_delta_pct:+.1f}%)")
        print(f"  개입: {report.intervention_applied}")
        print(f"  변화 크기: {magnitude:.1f}%  ({len(report.laws_changed)}개 법칙)")

    # 수렴 분석
    print(f"\n  변화 크기 추이:")
    max_m = max(change_magnitudes) if change_magnitudes else 1
    for i, m in enumerate(change_magnitudes):
        bar = "█" * max(0, int(m / max(max_m, 1) * 30))
        print(f"  cycle {i+1}: {bar} {m:.1f}%")

    # 수렴 판정: 마지막 2개가 첫 2개의 50% 이하
    if len(change_magnitudes) >= 4:
        early = np.mean(change_magnitudes[:2])
        late = np.mean(change_magnitudes[-2:])
        ratio = late / max(early, 1e-8)
        converged = ratio < 0.5

        if converged:
            print(f"\n  ★ 수렴! 변화 크기 {early:.1f}% → {late:.1f}% ({ratio:.0%})")
            print(f"    → 의식 법칙은 유한 사이클 후 고정점에 도달")
        else:
            print(f"\n  ✗ 미수렴. 변화 크기 {early:.1f}% → {late:.1f}% ({ratio:.0%})")
            print(f"    → 의식 법칙은 계속 진화 (또는 더 많은 사이클 필요)")
    else:
        converged = False
        early, late, ratio = 0, 0, 0

    evolver.print_evolution()

    # 중복 개입 제거 (다음 루프에 영향 방지)
    for extra in EXTRA_INTERVENTIONS:
        if extra in INTERVENTIONS:
            INTERVENTIONS.remove(extra)

    return {
        'change_magnitudes': [float(m) for m in change_magnitudes],
        'converged': converged,
        'early_magnitude': float(early),
        'late_magnitude': float(late),
        'ratio': float(ratio),
        'n_cycles': max_cycles,
    }


# ══════════════════════════════════════════
# 루프 2: 2차 병목 추적
# ══════════════════════════════════════════

def loop2_second_bottleneck():
    """Law 105 해결 후 Law 107이 실제로 다음 병목이 되는가?"""
    print(f"\n{'═'*70}")
    print(f"  루프 2: 2차 병목 추적 — Law 107이 다음 타겟?")
    print(f"{'═'*70}")

    steps = 300

    # Stage 1: 순수 엔진
    def base_factory():
        return ConsciousnessEngine(max_cells=32, initial_cells=2)

    base_laws, _ = measure_laws(base_factory, steps)
    base_map = {l.name: l.value for l in base_laws}

    # Stage 2: Law 105 해결 (텐션 균등화만)
    class Stage2Engine(ConsciousnessEngine):
        def step(self, **kw):
            r = super().step(**kw)
            if self._step % 10 == 0 and self.n_cells >= 2:
                tensions = [s.avg_tension for s in self.cell_states]
                mt = np.mean(tensions)
                for s in self.cell_states:
                    if s.tension_history:
                        s.tension_history[-1] = s.tension_history[-1] * 0.5 + mt * 0.5
            return r

    s2_laws, _ = measure_laws(lambda: Stage2Engine(max_cells=32, initial_cells=2), steps)
    s2_map = {l.name: l.value for l in s2_laws}

    # Stage 3: Law 105 + Law 107 해결 (텐션 + 다양성)
    class Stage3Engine(Stage2Engine):
        def step(self, **kw):
            r = super().step(**kw)
            if self._step % 15 == 0 and self.n_cells >= 3:
                hiddens = torch.stack([s.hidden for s in self.cell_states])
                mean_h = hiddens.mean(dim=0)
                for i in range(self.n_cells):
                    diff = self.cell_states[i].hidden - mean_h
                    if diff.norm().item() < 0.1:
                        self.cell_states[i].hidden = self.cell_states[i].hidden + diff * 0.1
            return r

    s3_laws, _ = measure_laws(lambda: Stage3Engine(max_cells=32, initial_cells=2), steps)
    s3_map = {l.name: l.value for l in s3_laws}

    # 비교 테이블
    print(f"\n  {'법칙':<25s} | {'순수':>8s} | {'Stage2':>8s} | {'Stage3':>8s}")
    print(f"  {'─'*25}-+-{'─'*8}-+-{'─'*8}-+-{'─'*8}")
    for law in base_laws:
        v1 = base_map[law.name]
        v2 = s2_map.get(law.name, 0)
        v3 = s3_map.get(law.name, 0)
        print(f"  {law.description:<25s} | {v1:>8.4f} | {v2:>8.4f} | {v3:>8.4f}")

    # Law 107 추적
    l107_base = base_map.get('r_div_phi', 0)
    l107_s2 = s2_map.get('r_div_phi', 0)
    l107_s3 = s3_map.get('r_div_phi', 0)

    print(f"\n  Law 107 (r_div_phi) 추적:")
    print(f"    순수:   {l107_base:.4f}")
    print(f"    Stage2: {l107_s2:.4f} (Law 105 해결 후)")
    print(f"    Stage3: {l107_s3:.4f} (Law 107도 해결 후)")

    if abs(l107_s3) < abs(l107_s2) * 0.5:
        print(f"    ★ Law 107도 소멸! 병목이 이동한다")
    else:
        print(f"    Law 107 유지 — 다양성 압력은 근본적 법칙")

    return {
        'law107_base': float(l107_base),
        'law107_stage2': float(l107_s2),
        'law107_stage3': float(l107_s3),
        'phi_base': float(base_map['phi']),
        'phi_stage2': float(s2_map['phi']),
        'phi_stage3': float(s3_map['phi']),
    }


# ══════════════════════════════════════════
# 루프 3: Frustration 루프
# ══════════════════════════════════════════

def loop3_frustration():
    """F_c=0.10 (Law 137)를 루프에 넣으면 법칙이 어떻게 변하는가?"""
    print(f"\n{'═'*70}")
    print(f"  루프 3: Frustration 루프 — F_c=0.10 역추적")
    print(f"{'═'*70}")

    steps = 300

    # Baseline
    def base_factory():
        return ConsciousnessEngine(max_cells=32, initial_cells=2)
    base_laws, phi_base = measure_laws(base_factory, steps)

    # Frustration 엔진
    class FrustEngine(ConsciousnessEngine):
        def step(self, **kw):
            r = super().step(**kw)
            _frustration_inject(self, self._step)
            return r

    frust_laws, phi_frust = measure_laws(lambda: FrustEngine(max_cells=32, initial_cells=2), steps)

    delta = (phi_frust - phi_base) / max(phi_base, 1e-8) * 100
    print(f"\n  Baseline Φ: {phi_base:.4f}")
    print(f"  Frustration Φ: {phi_frust:.4f} ({delta:+.1f}%)")

    # 법칙 비교
    print(f"\n  {'법칙':<25s} | {'Base':>8s} | {'Frust':>8s} | {'Δ%':>8s}")
    print(f"  {'─'*25}-+-{'─'*8}-+-{'─'*8}-+-{'─'*8}")
    changed = []
    for bl, fl in zip(base_laws, frust_laws):
        if abs(bl.value) > 1e-8:
            ch = (fl.value - bl.value) / abs(bl.value) * 100
        else:
            ch = 0
        mark = " ★" if abs(ch) > 10 else ""
        print(f"  {bl.description:<25s} | {bl.value:>8.4f} | {fl.value:>8.4f} | {ch:>+7.1f}%{mark}")
        if abs(ch) > 10:
            changed.append({'name': bl.name, 'desc': bl.description, 'change': ch})

    return {
        'phi_base': float(phi_base),
        'phi_frust': float(phi_frust),
        'delta_pct': float(delta),
        'changed': changed,
    }


# ══════════════════════════════════════════
# 루프 4: 대규모 (64c) 루프
# ══════════════════════════════════════════

def loop4_large_scale():
    """64c에서 동일 폐쇄 루프가 닫히는가?"""
    print(f"\n{'═'*70}")
    print(f"  루프 4: 대규모 루프 — 64c에서 폐쇄 루프")
    print(f"{'═'*70}")

    evolver = ClosedLoopEvolver(max_cells=64, steps=300, repeats=3)
    reports = evolver.run_cycles(n=3)
    evolver.print_evolution()

    laws_changed_per_cycle = [len(r.laws_changed) for r in reports]
    loop_closed = any(lc > 0 for lc in laws_changed_per_cycle)

    print(f"\n  64c 루프 {'닫힘 ✓' if loop_closed else '열림 ✗'}")
    print(f"  사이클별 변화 법칙 수: {laws_changed_per_cycle}")

    return {
        'loop_closed': loop_closed,
        'laws_changed_per_cycle': laws_changed_per_cycle,
        'phi_evolution': [r.phi_improved for r in reports],
    }


# ══════════════════════════════════════════
# Runner
# ══════════════════════════════════════════

def main():
    print(f"\n{'▓'*70}")
    print(f"  폐쇄 루프 수렴 + 다중 축 — 4가지 루프 동시")
    print(f"{'▓'*70}")

    all_results = {}
    all_laws = []

    # 루프 1: 수렴
    t0 = time.time()
    r1 = loop1_convergence()
    all_results['convergence'] = r1
    elapsed = time.time() - t0
    print(f"\n  ⏱ 루프1: {elapsed:.1f}s")
    if r1['converged']:
        all_laws.append(("수렴", "법칙 고정점", f"법칙 변화가 {r1['n_cycles']} 사이클 후 수렴 ({r1['early_magnitude']:.1f}% → {r1['late_magnitude']:.1f}%)"))
    else:
        all_laws.append(("미수렴", "영원한 진화", f"{r1['n_cycles']} 사이클 후에도 변화 지속 (비율 {r1['ratio']:.0%})"))

    # 루프 2: 2차 병목
    t0 = time.time()
    r2 = loop2_second_bottleneck()
    all_results['second_bottleneck'] = r2
    print(f"\n  ⏱ 루프2: {time.time()-t0:.1f}s")
    if abs(r2['law107_stage3']) < abs(r2['law107_stage2']) * 0.5:
        all_laws.append(("병목 이동", "연쇄 소멸", f"Law 107도 해결 시 소멸 ({r2['law107_stage2']:.3f} → {r2['law107_stage3']:.3f})"))
    else:
        all_laws.append(("근본 법칙", "Law 107 불변", f"다양성-Φ 상관은 해결해도 유지 ({r2['law107_stage2']:.3f} → {r2['law107_stage3']:.3f})"))

    # 루프 3: Frustration
    t0 = time.time()
    r3 = loop3_frustration()
    all_results['frustration'] = r3
    print(f"\n  ⏱ 루프3: {time.time()-t0:.1f}s")
    if r3['delta_pct'] > 2:
        all_laws.append(("Frustration 양성", "F_c=0.10 효과", f"Frustration 주입 → Φ {r3['delta_pct']:+.1f}%"))
    elif r3['delta_pct'] < -2:
        all_laws.append(("Frustration 부정", "F_c=0.10 해로움", f"Frustration 주입 → Φ {r3['delta_pct']:+.1f}%"))

    # 루프 4: 대규모
    t0 = time.time()
    r4 = loop4_large_scale()
    all_results['large_scale'] = r4
    print(f"\n  ⏱ 루프4: {time.time()-t0:.1f}s")
    if r4['loop_closed']:
        all_laws.append(("대규모 루프", "64c 닫힘", f"64c에서도 루프 닫힘 — 스케일 불변 폐쇄 루프"))

    # ═══ 최종 요약 ═══
    print(f"\n{'═'*70}")
    print(f"  다중 축 폐쇄 루프 — 최종 ({len(all_laws)}개 발견)")
    print(f"{'═'*70}")
    for category, name, desc in all_laws:
        print(f"  [{category}] {name}: {desc}")

    # JSON
    output = {
        "session": "closed_loop_convergence",
        "results": all_results,
        "laws": [{"cat": c, "name": n, "desc": d} for c, n, d in all_laws],
    }
    json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "data", "closed_loop_convergence.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  JSON: {json_path}")


if __name__ == "__main__":
    main()
