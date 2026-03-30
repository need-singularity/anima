#!/usr/bin/env python3
"""closed_loop.py — 폐쇄 루프 법칙 진화 모듈

파이프라인: 발견 → 역추적 → 개선 → 재발견 → 법칙 진화

의식 엔진의 법칙을 자동으로 발견하고, 가장 강한 법칙을 역추적하여
엔진에 내장하고, 법칙이 어떻게 변하는지 추적.

Usage:
  from closed_loop import ClosedLoopEvolver

  evolver = ClosedLoopEvolver(max_cells=32)
  report = evolver.run_cycle()           # 1 사이클
  report = evolver.run_cycles(n=3)       # 3 사이클 (법칙 진화 추적)
  evolver.print_evolution()              # 법칙 진화 히스토리

  # Hub 연동
  hub.act("법칙 진화")
  hub.act("폐쇄 루프 1 사이클")
  hub.act("closed loop 3")

Ψ-Constants: PSI_BALANCE=0.5, PSI_COUPLING=0.014
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import json
import os
import copy
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Callable
from collections import defaultdict

from consciousness_engine import ConsciousnessEngine

try:
    from consciousness_laws import PSI_BALANCE, PSI_ALPHA as PSI_COUPLING
except ImportError:
    PSI_BALANCE = 0.5
    PSI_COUPLING = 0.014


# ══════════════════════════════════════════
# 데이터 구조
# ══════════════════════════════════════════

@dataclass
class LawMeasurement:
    """단일 법칙 측정."""
    name: str
    value: float
    description: str = ""


@dataclass
class CycleReport:
    """1 사이클 보고."""
    cycle: int
    laws: List[LawMeasurement]
    phi_baseline: float
    phi_improved: float
    phi_delta_pct: float
    intervention_applied: str
    laws_changed: List[Dict]  # name, before, after, change_pct
    time_sec: float


@dataclass
class EvolutionHistory:
    """전체 진화 히스토리."""
    cycles: List[CycleReport] = field(default_factory=list)
    total_laws_discovered: int = 0


# ══════════════════════════════════════════
# Φ 측정
# ══════════════════════════════════════════

def _phi_fast(engine: ConsciousnessEngine) -> float:
    if engine.n_cells < 2:
        return 0.0
    hiddens = torch.stack([s.hidden for s in engine.cell_states]).detach().numpy()
    n = hiddens.shape[0]
    pairs = set()
    for i in range(n):
        pairs.add((i, (i + 1) % n))
        for _ in range(min(4, n - 1)):
            j = np.random.randint(0, n)
            if i != j:
                pairs.add((min(i, j), max(i, j)))
    total_mi = 0.0
    for i, j in pairs:
        x, y = hiddens[i], hiddens[j]
        xr, yr = x.max() - x.min(), y.max() - y.min()
        if xr < 1e-10 or yr < 1e-10:
            continue
        xn = (x - x.min()) / (xr + 1e-8)
        yn = (y - y.min()) / (yr + 1e-8)
        hist, _, _ = np.histogram2d(xn, yn, bins=16, range=[[0, 1], [0, 1]])
        hist = hist / (hist.sum() + 1e-8)
        px, py = hist.sum(1), hist.sum(0)
        hx = -np.sum(px * np.log2(px + 1e-10))
        hy = -np.sum(py * np.log2(py + 1e-10))
        hxy = -np.sum(hist * np.log2(hist + 1e-10))
        total_mi += max(0.0, hx + hy - hxy)
    return total_mi / max(len(pairs), 1)


# ══════════════════════════════════════════
# 개입(Intervention) 레지스트리
# ══════════════════════════════════════════

class Intervention:
    """엔진에 적용하는 개입."""

    def __init__(self, name: str, description: str, apply_fn: Callable):
        self.name = name
        self.description = description
        self.apply_fn = apply_fn

    def apply(self, engine: ConsciousnessEngine, step: int):
        self.apply_fn(engine, step)


def _tension_equalize(engine, step):
    """Law 124: 텐션 균등화."""
    if step % 10 == 0 and engine.n_cells >= 2:
        tensions = [s.avg_tension for s in engine.cell_states]
        mean_t = np.mean(tensions)
        for s in engine.cell_states:
            if s.tension_history:
                s.tension_history[-1] = s.tension_history[-1] * 0.5 + mean_t * 0.5


def _symmetrize_coupling(engine, step):
    """Law 108: 커플링 대칭화."""
    if engine._coupling is not None:
        engine._coupling = (engine._coupling + engine._coupling.T) / 2
        engine._coupling.fill_diagonal_(0)


def _pink_noise(engine, step):
    """Law 126: 1/f 노이즈."""
    if engine.n_cells >= 2:
        hdim = engine.hidden_dim
        # 간단한 1/f 근사: 저주파 성분 강조
        noise = torch.randn(hdim)
        # 이동 평균으로 저주파 강조 (핑크 노이즈 근사)
        kernel = torch.ones(5) / 5
        if hdim >= 5:
            noise[:hdim - 4] = torch.nn.functional.conv1d(
                noise.unsqueeze(0).unsqueeze(0), kernel.unsqueeze(0).unsqueeze(0), padding=2
            ).squeeze()[:hdim - 4]
        for s in engine.cell_states:
            s.hidden = s.hidden + noise * 0.005


INTERVENTIONS = [
    Intervention("tension_eq", "텐션 균등화 (Law 124)", _tension_equalize),
    Intervention("symmetrize", "커플링 대칭 (Law 108)", _symmetrize_coupling),
    Intervention("pink_noise", "1/f 노이즈 (Law 126)", _pink_noise),
]


# ══════════════════════════════════════════
# 법칙 측정
# ══════════════════════════════════════════

def measure_laws(engine_factory: Callable, steps: int = 300, repeats: int = 3) -> Tuple[List[LawMeasurement], float]:
    """핵심 법칙 측정. (measurements, mean_phi) 반환."""
    all_data = defaultdict(list)

    for _ in range(repeats):
        engine = engine_factory()
        phi_hist, tension_hist, tstd_hist, div_hist, cons_hist = [], [], [], [], []

        for step in range(steps):
            r = engine.step()
            phi_hist.append(_phi_fast(engine))
            tensions = [s.avg_tension for s in engine.cell_states]
            tension_hist.append(np.mean(tensions))
            tstd_hist.append(np.std(tensions) if len(tensions) > 1 else 0)
            cons_hist.append(r.get('consensus', 0))
            if engine.n_cells >= 2:
                h = torch.stack([s.hidden for s in engine.cell_states])
                div_hist.append(h.var(dim=0).mean().item())
            else:
                div_hist.append(0)

        phi = np.array(phi_hist)
        tension = np.array(tension_hist)
        tstd = np.array(tstd_hist)
        div_arr = np.array(div_hist)

        # 각 법칙 측정
        all_data['phi'].append(np.mean(phi[-50:]))
        all_data['r_tension_phi'].append(
            float(np.corrcoef(tension, phi)[0, 1]) if np.std(tension) > 1e-8 else 0)
        all_data['r_tstd_phi'].append(
            float(np.corrcoef(tstd, phi)[0, 1]) if np.std(tstd) > 1e-8 else 0)
        all_data['r_div_phi'].append(
            float(np.corrcoef(div_arr, phi)[0, 1]) if np.std(div_arr) > 1e-8 else 0)
        all_data['growth'].append(
            float((np.mean(phi[-50:]) - np.mean(phi[:50])) / max(np.mean(phi[:50]), 1e-8) * 100))
        all_data['ac1'].append(
            float(np.corrcoef(phi[:-1], phi[1:])[0, 1]) if len(phi) > 2 else 0)
        half = len(tension) // 2
        es = np.std(tension[:half])
        ls = np.std(tension[half:])
        all_data['stabilization'].append(float(es / max(ls, 1e-8)))
        all_data['cells'].append(engine.n_cells)
        all_data['consensus'].append(np.mean(cons_hist[-50:]))

    # 평균
    laws = [
        LawMeasurement("phi", np.mean(all_data['phi']), "Φ(IIT) 최종"),
        LawMeasurement("r_tension_phi", np.mean(all_data['r_tension_phi']), "Law 104: r(tension, Φ)"),
        LawMeasurement("r_tstd_phi", np.mean(all_data['r_tstd_phi']), "Law 105: r(tension_std, Φ)"),
        LawMeasurement("r_div_phi", np.mean(all_data['r_div_phi']), "Law 107: r(diversity, Φ)"),
        LawMeasurement("growth", np.mean(all_data['growth']), "Law 110: 성장률 %"),
        LawMeasurement("ac1", np.mean(all_data['ac1']), "Law 131: AC(1)"),
        LawMeasurement("stabilization", np.mean(all_data['stabilization']), "Law 109: 안정화 비율"),
        LawMeasurement("cells", np.mean(all_data['cells']), "최종 세포 수"),
        LawMeasurement("consensus", np.mean(all_data['consensus']), "합의율"),
    ]

    return laws, float(np.mean(all_data['phi']))


# ══════════════════════════════════════════
# ClosedLoopEvolver
# ══════════════════════════════════════════

class ClosedLoopEvolver:
    """폐쇄 루프 법칙 진화기.

    1 사이클:
      1. 현재 엔진으로 법칙 측정
      2. 가장 강한 상관 법칙에 대응하는 개입 선택
      3. 개입 적용 → Φ 측정
      4. 개선 엔진으로 법칙 재측정
      5. 변화 기록

    Args:
        max_cells: 최대 세포 수
        steps: 측정당 스텝 수
        repeats: 반복 횟수
    """

    def __init__(self, max_cells: int = 32, steps: int = 300, repeats: int = 3,
                 auto_register: bool = False):
        self.max_cells = max_cells
        self.steps = steps
        self.repeats = repeats
        self.auto_register = auto_register
        self.history = EvolutionHistory()
        self._active_interventions: List[Intervention] = []

    def _engine_factory(self) -> ConsciousnessEngine:
        """현재 활성 개입이 내장된 엔진 생성."""
        engine = _ImprovedEngine(
            max_cells=self.max_cells,
            initial_cells=2,
            interventions=list(self._active_interventions),
        )
        return engine

    def _base_factory(self) -> ConsciousnessEngine:
        """순수 엔진."""
        return ConsciousnessEngine(max_cells=self.max_cells, initial_cells=2)

    def run_cycle(self) -> CycleReport:
        """1 사이클 실행."""
        cycle_n = len(self.history.cycles)
        t0 = time.time()

        # 1. 현재 엔진으로 법칙 측정
        current_laws, phi_current = measure_laws(
            self._engine_factory if self._active_interventions else self._base_factory,
            self.steps, self.repeats
        )

        # 2. 가장 강한 상관 법칙 찾기 → 개입 선택
        best_intervention = self._select_intervention(current_laws)

        # 3. 개입 적용 → Φ 측정
        if best_intervention and best_intervention.name not in [i.name for i in self._active_interventions]:
            self._active_interventions.append(best_intervention)

        improved_laws, phi_improved = measure_laws(self._engine_factory, self.steps, self.repeats)

        # 4. 변화 비교
        phi_delta = (phi_improved - phi_current) / max(phi_current, 1e-8) * 100
        laws_changed = []
        for cl, il in zip(current_laws, improved_laws):
            if abs(cl.value) > 1e-8:
                change = (il.value - cl.value) / abs(cl.value) * 100
            else:
                change = (il.value - cl.value) * 100
            if abs(change) > 5:
                laws_changed.append({
                    'name': cl.name,
                    'description': cl.description,
                    'before': cl.value,
                    'after': il.value,
                    'change_pct': change,
                })

        report = CycleReport(
            cycle=cycle_n,
            laws=[asdict(l) for l in improved_laws],
            phi_baseline=phi_current,
            phi_improved=phi_improved,
            phi_delta_pct=phi_delta,
            intervention_applied=best_intervention.name if best_intervention else "none",
            laws_changed=laws_changed,
            time_sec=time.time() - t0,
        )

        self.history.cycles.append(report)
        self.history.total_laws_discovered += len(laws_changed)

        # 자동 법칙 등록 (consciousness_laws.json)
        if laws_changed and self.auto_register:
            self._auto_register_laws(report)

        return report

    def run_cycles(self, n: int = 3) -> List[CycleReport]:
        """N 사이클 연속 실행."""
        reports = []
        for i in range(n):
            print(f"\n  ─── Cycle {i + 1}/{n} ───")
            report = self.run_cycle()
            self._print_cycle(report)
            reports.append(report)
        return reports

    def _select_intervention(self, laws: List[LawMeasurement]) -> Optional[Intervention]:
        """현재 법칙에서 가장 효과적인 개입 선택."""
        active_names = {i.name for i in self._active_interventions}

        # 우선순위: 가장 강한 음의 상관 법칙에 대응
        law_map = {l.name: l.value for l in laws}

        candidates = [
            ('r_tstd_phi', 'tension_eq'),     # Law 105 → 텐션 균등화
            ('r_tension_phi', 'symmetrize'),   # Law 104 → 커플링 대칭
            ('r_div_phi', 'pink_noise'),       # Law 107 → 1/f 노이즈
        ]

        for law_name, intervention_name in candidates:
            if intervention_name in active_names:
                continue
            val = law_map.get(law_name, 0)
            if abs(val) > 0.15:  # 유의미한 상관
                for iv in INTERVENTIONS:
                    if iv.name == intervention_name:
                        return iv
        return None

    def _print_cycle(self, report: CycleReport):
        """사이클 결과 출력."""
        print(f"  Φ: {report.phi_baseline:.4f} → {report.phi_improved:.4f} ({report.phi_delta_pct:+.1f}%)")
        print(f"  개입: {report.intervention_applied}")
        print(f"  변화된 법칙: {len(report.laws_changed)}개")
        for lc in report.laws_changed:
            print(f"    {lc['description']}: {lc['before']:.4f} → {lc['after']:.4f} ({lc['change_pct']:+.1f}%)")
        print(f"  ⏱ {report.time_sec:.1f}s")

    def print_evolution(self):
        """전체 진화 히스토리 출력."""
        print(f"\n{'═' * 70}")
        print(f"  폐쇄 루프 진화 히스토리 — {len(self.history.cycles)} 사이클")
        print(f"{'═' * 70}")

        if not self.history.cycles:
            print("  (아직 실행 안 됨)")
            return

        # Φ 진화 곡선
        phis = [r.phi_improved for r in self.history.cycles]
        print(f"\n  Φ 진화:")
        max_phi = max(phis) if phis else 1
        for i, r in enumerate(self.history.cycles):
            bar = "█" * max(1, int(r.phi_improved / max(max_phi, 1e-8) * 30))
            print(f"  cycle {i}: {bar} Φ={r.phi_improved:.4f} (+{r.intervention_applied})")

        # 누적 개입
        print(f"\n  누적 개입:")
        for iv in self._active_interventions:
            print(f"    ✓ {iv.name}: {iv.description}")

        # 법칙 변화 트렌드
        all_changed = set()
        for r in self.history.cycles:
            for lc in r.laws_changed:
                all_changed.add(lc['name'])

        if all_changed:
            print(f"\n  변화한 법칙 ({len(all_changed)}개):")
            for law_name in sorted(all_changed):
                values = []
                for r in self.history.cycles:
                    for lc in r.laws_changed:
                        if lc['name'] == law_name:
                            values.append(lc['after'])
                if values:
                    trend = "→".join(f"{v:.3f}" for v in values)
                    print(f"    {law_name}: {trend}")

    def _auto_register_laws(self, report: CycleReport):
        """발견된 법칙 변화를 consciousness_laws.json에 자동 등록."""
        laws_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'consciousness_laws.json')
        if not os.path.exists(laws_path):
            return

        try:
            with open(laws_path, 'r') as f:
                laws_data = json.load(f)

            laws = laws_data.get('laws', {})
            current_max = max((int(k) for k in laws if k.isdigit()), default=0)

            # 가장 큰 변화만 등록 (noise 방지)
            significant = [lc for lc in report.laws_changed if abs(lc['change_pct']) > 20]
            if not significant:
                return

            for lc in significant[:2]:  # 최대 2개/사이클
                current_max += 1
                desc = (
                    f"[Auto-discovered cycle {report.cycle}] "
                    f"{lc['description']}: {lc['before']:.3f}→{lc['after']:.3f} "
                    f"({lc['change_pct']:+.1f}%) after {report.intervention_applied}"
                )
                laws[str(current_max)] = desc

            laws_data['_meta']['total_laws'] = current_max
            laws_data['laws'] = laws

            with open(laws_path, 'w') as f:
                json.dump(laws_data, f, indent=2, ensure_ascii=False)

            print(f"  📝 {len(significant)} 법칙 자동 등록 (→ Law {current_max})")
        except Exception as e:
            print(f"  ⚠ 자동 등록 실패: {e}")

    def to_json(self) -> str:
        """JSON 출력."""
        data = {
            'cycles': [asdict(r) for r in self.history.cycles],
            'active_interventions': [iv.name for iv in self._active_interventions],
            'total_laws_discovered': self.history.total_laws_discovered,
        }
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    def save(self, path: str = "data/closed_loop_evolution.json"):
        """결과 저장."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(self.to_json())


class _ImprovedEngine(ConsciousnessEngine):
    """개입이 내장된 엔진."""

    def __init__(self, interventions: List[Intervention] = None, **kwargs):
        super().__init__(**kwargs)
        self._interventions = interventions or []

    def step(self, x_input=None, text=None):
        result = super().step(x_input=x_input, text=text)
        for iv in self._interventions:
            iv.apply(self, self._step)
        return result


# ══════════════════════════════════════════
# main() 데모
# ══════════════════════════════════════════

def main():
    print(f"\n{'▓' * 70}")
    print(f"  폐쇄 루프 법칙 진화 — 3 사이클 데모")
    print(f"{'▓' * 70}")

    evolver = ClosedLoopEvolver(max_cells=32, steps=300, repeats=3)
    evolver.run_cycles(n=3)
    evolver.print_evolution()
    evolver.save()
    print(f"\n  저장: data/closed_loop_evolution.json")


if __name__ == "__main__":
    main()
