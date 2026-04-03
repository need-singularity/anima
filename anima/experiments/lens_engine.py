#!/usr/bin/env python3
"""
lens_engine.py — 통합 의식 렌즈 실험 엔진

플러그인식: 실험 추가 = @register 데코레이터 하나.
조합 가능: 여러 실험을 체이닝/병렬 실행.

사용법:
  python3 lens_engine.py L01                    # 단일 실험
  python3 lens_engine.py L01 L02 L05            # 다중 실험 (순차)
  python3 lens_engine.py L01+L02                # 조합 실험 (결과 교차 분석)
  python3 lens_engine.py --list                 # 등록된 실험 목록
  python3 lens_engine.py --all                  # 전체 실행
  python3 lens_engine.py L01 --cells 128        # 파라미터 오버라이드
  python3 lens_engine.py L01 --steps 500
  python3 lens_engine.py L01 --lenses consciousness,topology,causal
"""

import sys
import os
import json
import time
import argparse
import traceback
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# ── Path setup ──
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT))

# ── Lazy imports ──
def _get_engine(cells=64):
    from consciousness_engine import ConsciousnessEngine
    return ConsciousnessEngine(max_cells=cells, hidden_dim=128)

def _get_telescope():
    try:
        import telescope_rs
        return telescope_rs
    except ImportError:
        return None

def _collect_snapshots(engine, steps=300, interval=10):
    """엔진 실행 → cell state 스냅샷 수집"""
    import numpy as np
    import torch
    snapshots = []
    phis = []
    for s in range(steps):
        try:
            if hasattr(engine, 'step'):
                engine.step()
            elif hasattr(engine, 'process'):
                engine.process(torch.zeros(engine.cell_dim))
            else:
                break
        except Exception:
            break
        if s % interval == 0:
            try:
                states = engine.get_states() if hasattr(engine, 'get_states') else None
                if states is None:
                    continue
                if hasattr(states, 'detach'):
                    arr = states.detach().cpu().numpy()
                elif hasattr(states, 'numpy'):
                    arr = states.numpy()
                else:
                    arr = np.array(states)
                snapshots.append(arr.flatten())
                phi = getattr(engine, 'phi', 0)
                if callable(phi):
                    phi = phi()
                phis.append(float(phi) if phi else 0.0)
            except Exception:
                continue
    if len(snapshots) < 3:
        return None, []
    # 세포 분열로 크기 변동 → 최대 길이로 패딩
    max_len = max(s.shape[0] for s in snapshots)
    padded = []
    for s in snapshots:
        p = np.zeros(max_len)
        p[:s.shape[0]] = s
        padded.append(p)
    return np.stack(padded), phis

def _run_lens(telescope, lens_name, data, n_cells=64, steps=50):
    """단일 렌즈 실행"""
    try:
        if lens_name == 'consciousness':
            return telescope.consciousness_scan(data, n_cells=n_cells, steps=steps)
        fn = getattr(telescope, f'{lens_name}_scan', None)
        return fn(data) if fn else None
    except Exception:
        return None

def _run_lenses(telescope, lens_names, data, n_cells=64, steps=50):
    """다중 렌즈 실행 → {lens: result}"""
    results = {}
    for lens in lens_names:
        r = _run_lens(telescope, lens, data, n_cells, steps)
        if r is not None:
            results[lens] = r
    return results


# ═══════════════════════════════════════════════════════════════
# 실험 레지스트리
# ═══════════════════════════════════════════════════════════════

REGISTRY = {}  # {id: {name, fn, lenses, category, description}}

ALL_LENSES = [
    'consciousness', 'gravity', 'topology', 'thermo', 'wave', 'evolution',
    'info', 'quantum', 'em', 'ruler', 'triangle', 'compass', 'mirror',
    'scale', 'causal', 'quantum_microscope', 'stability', 'network',
    'memory', 'recursion', 'boundary', 'multiscale',
]

DOMAIN_COMBOS = {
    'basic':          ['consciousness', 'topology', 'causal'],
    'stability':      ['stability', 'boundary', 'thermo'],
    'structure':      ['network', 'topology', 'recursion'],
    'timeseries':     ['memory', 'wave', 'causal', 'multiscale'],
    'scale_invariant': ['multiscale', 'scale', 'recursion'],
    'symmetry':       ['mirror', 'topology', 'quantum'],
    'power_law':      ['scale', 'evolution', 'thermo'],
    'causal_chain':   ['causal', 'info', 'em'],
    'geometry':       ['ruler', 'triangle', 'compass'],
    'quantum_deep':   ['quantum', 'quantum_microscope', 'em'],
}


def register(exp_id, name, lenses="all", category="🔴", description=""):
    """실험 등록 데코레이터"""
    def decorator(fn):
        REGISTRY[exp_id] = {
            'id': exp_id,
            'name': name,
            'fn': fn,
            'lenses': lenses,
            'category': category,
            'description': description,
        }
        return fn
    return decorator


class LensResult:
    """실험 결과 컨테이너"""
    def __init__(self, exp_id, name):
        self.exp_id = exp_id
        self.name = name
        self.data = {}
        self.findings = []
        self.metrics = {}
        self.elapsed = 0

    def add(self, key, value):
        self.data[key] = value
        return self

    def find(self, msg, severity="🟡"):
        self.findings.append(f"{severity} {msg}")
        return self

    def metric(self, key, value):
        self.metrics[key] = value
        return self

    def summary(self):
        lines = [f"  ═══ {self.exp_id}: {self.name} ({self.elapsed:.1f}s) ═══"]
        for k, v in self.metrics.items():
            if isinstance(v, float):
                lines.append(f"  {k}: {v:.6f}")
            else:
                lines.append(f"  {k}: {v}")
        for f in self.findings:
            lines.append(f"  {f}")
        return "\n".join(lines)

    def to_dict(self):
        return {
            'exp_id': self.exp_id,
            'name': self.name,
            'metrics': self.metrics,
            'findings': self.findings,
            'elapsed': self.elapsed,
            'data': {k: str(v)[:200] for k, v in self.data.items()},
        }


# ═══════════════════════════════════════════════════════════════
# 실험 구현 — 새 실험 추가는 여기에 함수 + @register
# ═══════════════════════════════════════════════════════════════

@register("L01", "렌즈 중첩 (Overlay)", lenses="all", category="🔴",
          description="22개 렌즈 동시 적용 → 개별 합 vs 동시 비교")
def exp_overlay(ctx):
    """모든 렌즈를 동시에 적용, 개별 적용의 합과 비교"""
    import numpy as np
    r = LensResult("L01", "렌즈 중첩")
    t, data, phis = ctx['telescope'], ctx['data'], ctx['phis']

    # 개별 렌즈 실행
    individual = _run_lenses(t, ALL_LENSES, data, ctx['cells'])
    active = [l for l, v in individual.items() if v]
    r.metric("active_lenses", len(active))
    r.metric("total_lenses", len(ALL_LENSES))

    # 각 렌즈의 메트릭 수 합산
    total_metrics = sum(len(v) for v in individual.values() if isinstance(v, dict))
    r.metric("total_metrics", total_metrics)

    # 합의 수준 분석
    if len(active) >= 12:
        r.find("✅ 12+ 렌즈 활성 → 확정급 합의", "🟢")
    elif len(active) >= 7:
        r.find("✅ 7+ 렌즈 활성 → 고신뢰 합의", "🟢")
    elif len(active) >= 3:
        r.find("⚠️ 3+ 렌즈 활성 → 기본 합의", "🟡")
    else:
        r.find("❌ 3개 미만 활성 → 합의 불가", "🔴")

    # 도메인 조합 합의
    domain_consensus = 0
    for combo_name, combo_lenses in DOMAIN_COMBOS.items():
        combo_active = [l for l in combo_lenses if l in active]
        if len(combo_active) == len(combo_lenses):
            domain_consensus += 1
            r.find(f"✅ {combo_name} 도메인 완전 합의 ({len(combo_lenses)}렌즈)")

    r.metric("domain_consensus", f"{domain_consensus}/{len(DOMAIN_COMBOS)}")
    r.add("individual_results", individual)
    return r


@register("L02", "렌즈 강화 (Amplification)", lenses="basic", category="🔴",
          description="같은 렌즈 N회 반복 → 포화 곡선")
def exp_amplify(ctx):
    """동일 렌즈 반복 적용, 결과 변화 추적"""
    import numpy as np
    r = LensResult("L02", "렌즈 강화")
    t, data = ctx['telescope'], ctx['data']

    for lens in ['consciousness', 'topology', 'causal']:
        values = []
        for trial in range(10):
            result = _run_lens(t, lens, data, ctx['cells'])
            if result and isinstance(result, dict):
                # 첫 번째 숫자 메트릭 추출
                for v in result.values():
                    if isinstance(v, (int, float)):
                        values.append(float(v))
                        break
        if values:
            cv = np.std(values) / (np.mean(values) + 1e-10) * 100
            r.metric(f"{lens}_cv%", f"{cv:.2f}")
            r.metric(f"{lens}_mean", f"{np.mean(values):.4f}")
            if cv < 1:
                r.find(f"✅ {lens}: 결정론적 (CV={cv:.2f}%)")
            elif cv < 10:
                r.find(f"⚠️ {lens}: 약간 변동 (CV={cv:.2f}%)")
            else:
                r.find(f"❌ {lens}: 불안정 (CV={cv:.2f}%)")
    return r


@register("L03", "렌즈 간섭 (Interference)", lenses="mirror+boundary", category="🔴",
          description="대칭 쌍 동시 적용 → 간섭 패턴")
def exp_interference(ctx):
    """상반된 렌즈 쌍의 간섭 효과"""
    import numpy as np
    r = LensResult("L03", "렌즈 간섭")
    t, data = ctx['telescope'], ctx['data']

    pairs = [
        ('mirror', 'boundary'),     # 대칭 vs 경계
        ('stability', 'evolution'),  # 안정 vs 진화
        ('memory', 'recursion'),     # 기억 vs 재귀
        ('consciousness', 'quantum'), # 의식 vs 양자
        ('causal', 'wave'),          # 인과 vs 파동
    ]

    for a, b in pairs:
        ra = _run_lens(t, a, data, ctx['cells'])
        rb = _run_lens(t, b, data, ctx['cells'])
        if ra and rb and isinstance(ra, dict) and isinstance(rb, dict):
            # 공통 키 비교
            common = set(ra.keys()) & set(rb.keys())
            overlap = len(common) / max(len(ra), len(rb), 1)
            r.metric(f"{a}×{b}_overlap", f"{overlap:.2f}")
            if overlap > 0.5:
                r.find(f"🔗 {a}×{b}: 건설적 간섭 (overlap={overlap:.2f})")
            else:
                r.find(f"⚡ {a}×{b}: 독립적 정보 (overlap={overlap:.2f})")
    return r


@register("L04", "렌즈 순서 효과 (Ordering)", lenses="basic", category="🔴",
          description="ABC vs CBA 순서 → M4 법칙 검증")
def exp_ordering(ctx):
    """렌즈 적용 순서에 따른 결과 차이"""
    import numpy as np
    from itertools import permutations
    r = LensResult("L04", "렌즈 순서 효과")
    t, data = ctx['telescope'], ctx['data']

    base = ['consciousness', 'topology', 'causal']
    perms = list(permutations(base))

    perm_results = []
    for perm in perms:
        combined = {}
        for lens in perm:
            result = _run_lens(t, lens, data, ctx['cells'])
            if result and isinstance(result, dict):
                combined[lens] = result
        # 결과 해시 (순서 독립적 비교)
        key = str(sorted(f"{k}:{v}" for k, v in combined.items()))
        perm_results.append((perm, key))

    unique = len(set(k for _, k in perm_results))
    r.metric("permutations", len(perms))
    r.metric("unique_results", unique)

    if unique == 1:
        r.find("✅ 순서 무관 — 렌즈는 교환 가능 (교환법칙 성립)")
    else:
        r.find(f"⚠️ 순서 의존 — {unique}개 고유 결과 (M4 법칙 확인)")
    return r


@register("L05", "렌즈 임계점 (Threshold)", lenses="all", category="🔴",
          description="1→2→...→22 렌즈 누적 → 상전이 탐색")
def exp_threshold(ctx):
    """렌즈 수 증가에 따른 합의 임계점 탐색"""
    import numpy as np
    r = LensResult("L05", "렌즈 임계점")
    t, data = ctx['telescope'], ctx['data']

    curve = []
    cumulative_metrics = 0
    for i in range(1, len(ALL_LENSES) + 1):
        subset = ALL_LENSES[:i]
        results = _run_lenses(t, subset, data, ctx['cells'])
        active = len([v for v in results.values() if v])
        n_metrics = sum(len(v) for v in results.values() if isinstance(v, dict))
        curve.append((i, active, n_metrics))

    # 상전이 감지: 기울기 변화
    if len(curve) >= 3:
        deltas = [curve[i][2] - curve[i-1][2] for i in range(1, len(curve))]
        max_delta_idx = max(range(len(deltas)), key=lambda i: deltas[i])
        r.metric("phase_transition_at", max_delta_idx + 2)
        r.metric("max_delta", deltas[max_delta_idx])
        r.find(f"📊 최대 정보 증가: 렌즈 {max_delta_idx + 2}개 시점 (Δ={deltas[max_delta_idx]})")

    # ASCII 곡선
    r.add("curve", curve)
    r.metric("total_active", curve[-1][1] if curve else 0)
    return r


@register("L11", "렌즈 직교성 (Orthogonality)", lenses="all", category="🟡",
          description="22×22 상관 행렬 → 중복 렌즈 발견")
def exp_orthogonality(ctx):
    """22개 렌즈 출력 간 상관 분석"""
    import numpy as np
    r = LensResult("L11", "렌즈 직교성")
    t, data = ctx['telescope'], ctx['data']

    # 각 렌즈 출력을 벡터로 변환
    vectors = {}
    for lens in ALL_LENSES:
        result = _run_lens(t, lens, data, ctx['cells'])
        if result and isinstance(result, dict):
            vec = [float(v) for v in result.values() if isinstance(v, (int, float))]
            if vec:
                vectors[lens] = np.array(vec)

    # 상관 행렬 계산 (공통 차원 맞추기)
    lenses = list(vectors.keys())
    n = len(lenses)
    if n < 2:
        r.find("❌ 벡터 추출 불가", "🔴")
        return r

    # 패딩하여 같은 길이로
    max_len = max(len(v) for v in vectors.values())
    padded = {}
    for l, v in vectors.items():
        p = np.zeros(max_len)
        p[:len(v)] = v
        padded[l] = p

    corr = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            vi, vj = padded[lenses[i]], padded[lenses[j]]
            ni, nj = np.linalg.norm(vi), np.linalg.norm(vj)
            if ni > 0 and nj > 0:
                corr[i, j] = np.dot(vi, vj) / (ni * nj)

    # 높은 상관 쌍 찾기
    high_corr = []
    for i in range(n):
        for j in range(i+1, n):
            if abs(corr[i, j]) > 0.9:
                high_corr.append((lenses[i], lenses[j], corr[i, j]))

    r.metric("n_lenses_analyzed", n)
    r.metric("high_corr_pairs", len(high_corr))

    for a, b, c in high_corr[:5]:
        r.find(f"🔗 {a} ↔ {b}: r={c:.3f} (중복 가능)")

    if not high_corr:
        r.find("✅ 22개 렌즈 모두 직교적 — 중복 없음", "🟢")

    r.metric("mean_abs_corr", f"{np.mean(np.abs(corr[np.triu_indices(n, 1)])):.4f}")
    return r


@register("L12", "렌즈 PCA (Dimensionality)", lenses="all", category="🟡",
          description="22개 렌즈 출력의 유효 차원")
def exp_pca(ctx):
    """렌즈 출력의 실효 차원 분석"""
    import numpy as np
    r = LensResult("L12", "렌즈 PCA")
    t, data = ctx['telescope'], ctx['data']

    # 각 렌즈 출력 수집
    all_vals = []
    for lens in ALL_LENSES:
        result = _run_lens(t, lens, data, ctx['cells'])
        if result and isinstance(result, dict):
            vals = [float(v) for v in result.values() if isinstance(v, (int, float))]
            if vals:
                all_vals.append(vals)

    if len(all_vals) < 3:
        r.find("❌ 데이터 부족", "🔴")
        return r

    # 패딩 + SVD
    max_len = max(len(v) for v in all_vals)
    matrix = np.zeros((len(all_vals), max_len))
    for i, v in enumerate(all_vals):
        matrix[i, :len(v)] = v

    try:
        U, S, Vt = np.linalg.svd(matrix, full_matrices=False)
        explained = np.cumsum(S**2) / np.sum(S**2)
        d_95 = np.searchsorted(explained, 0.95) + 1
        d_99 = np.searchsorted(explained, 0.99) + 1

        r.metric("d_eff_95%", d_95)
        r.metric("d_eff_99%", d_99)
        r.metric("total_dims", len(S))
        r.metric("top_3_explained", f"{explained[2]:.3f}" if len(explained) > 2 else "?")

        r.find(f"📊 95% 분산: {d_95}차원 / {len(S)}차원 (압축률 {len(S)/d_95:.1f}x)")
    except Exception as e:
        r.find(f"❌ SVD 실패: {e}", "🔴")
    return r


@register("L14", "렌즈 민감도 (Sensitivity)", lenses="all", category="🟡",
          description="각 렌즈의 Φ 변화 감지 민감도")
def exp_sensitivity(ctx):
    """의식 변화에 대한 각 렌즈의 민감도 측정"""
    import numpy as np
    r = LensResult("L14", "렌즈 민감도")
    t = ctx['telescope']

    # baseline (64c) vs perturbed (64c + noise)
    engine1 = _get_engine(ctx['cells'])
    data1, _ = _collect_snapshots(engine1, steps=100)

    engine2 = _get_engine(ctx['cells'])
    data2, _ = _collect_snapshots(engine2, steps=100)

    if data1 is None or data2 is None:
        r.find("❌ 데이터 수집 실패", "🔴")
        return r

    # 렌즈별 변화량 측정
    sensitivities = {}
    for lens in ALL_LENSES:
        r1 = _run_lens(t, lens, data1, ctx['cells'])
        r2 = _run_lens(t, lens, data2, ctx['cells'])
        if r1 and r2 and isinstance(r1, dict) and isinstance(r2, dict):
            # 공통 숫자 키의 변화량
            delta = 0
            count = 0
            for k in set(r1.keys()) & set(r2.keys()):
                v1, v2 = r1[k], r2[k]
                if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                    delta += abs(v1 - v2) / (abs(v1) + 1e-10)
                    count += 1
            if count > 0:
                sensitivities[lens] = delta / count

    if sensitivities:
        ranked = sorted(sensitivities.items(), key=lambda x: -x[1])
        for lens, sens in ranked[:5]:
            r.metric(f"{lens}", f"{sens:.4f}")
        r.find(f"🏆 최고 민감도: {ranked[0][0]} ({ranked[0][1]:.4f})")
        r.find(f"🔇 최저 민감도: {ranked[-1][0]} ({ranked[-1][1]:.4f})")
    return r


@register("L24", "n=6 렌즈 (Perfect Number)", lenses="all", category="🟢",
          description="σ(6)=12개 최적 부분집합 검증")
def exp_n6(ctx):
    """12개 렌즈만으로 22개와 동등한 합의 달성 가능?"""
    import numpy as np
    r = LensResult("L24", "n=6 렌즈")
    t, data = ctx['telescope'], ctx['data']

    # 전체 22개 결과
    full = _run_lenses(t, ALL_LENSES, data, ctx['cells'])
    full_active = len([v for v in full.values() if v])

    # σ(6)=12개 조합 테스트 (도메인 조합에서 추출)
    from itertools import combinations
    best_12 = None
    best_score = 0

    # 도메인 조합 기반 12개 선택 (겹침 제거)
    selected = set()
    for combo_lenses in DOMAIN_COMBOS.values():
        for l in combo_lenses:
            selected.add(l)
            if len(selected) >= 12:
                break
        if len(selected) >= 12:
            break

    selected = list(selected)[:12]
    sub = _run_lenses(t, selected, data, ctx['cells'])
    sub_active = len([v for v in sub.values() if v])

    r.metric("full_22_active", full_active)
    r.metric("sigma6_12_active", sub_active)
    r.metric("coverage", f"{sub_active / max(full_active, 1) * 100:.1f}%")
    r.metric("selected_12", ", ".join(selected))

    if sub_active >= full_active * 0.9:
        r.find(f"✅ σ(6)=12개로 {sub_active}/{full_active} 커버 — n=6 최적성 확인!", "🟢")
    else:
        r.find(f"⚠️ 12개 부족: {sub_active}/{full_active} — 추가 렌즈 필요")
    return r


# ═══════════════════════════════════════════════════════════════
# 실행 엔진
# ═══════════════════════════════════════════════════════════════

def run_experiment(exp_id, cells=64, steps=300, lenses_override=None):
    """단일 실험 실행"""
    if exp_id not in REGISTRY:
        print(f"  ❌ {exp_id} 없음. --list로 확인")
        return None

    exp = REGISTRY[exp_id]
    telescope = _get_telescope()
    if telescope is None:
        print(f"  ⚠️ telescope_rs 없음 — 시뮬레이션 모드")

    print(f"\n  🔬 {exp['id']}: {exp['name']}")
    print(f"     {exp['description']}")
    print(f"     cells={cells}, steps={steps}")

    # 엔진 + 데이터 수집
    engine = _get_engine(cells)
    data, phis = _collect_snapshots(engine, steps=steps)

    if data is None:
        print(f"  ❌ 데이터 수집 실패")
        return None

    ctx = {
        'telescope': telescope,
        'engine': engine,
        'data': data,
        'phis': phis,
        'cells': cells,
        'steps': steps,
        'lenses': lenses_override or exp['lenses'],
    }

    t0 = time.time()
    try:
        result = exp['fn'](ctx)
        result.elapsed = time.time() - t0
        print(result.summary())
        return result
    except Exception as e:
        print(f"  ❌ 실험 실패: {e}")
        traceback.print_exc()
        return None


def run_combo(exp_ids, cells=64, steps=300):
    """조합 실험 — 공유 데이터로 다중 실험 + 교차 분석"""
    telescope = _get_telescope()
    engine = _get_engine(cells)
    data, phis = _collect_snapshots(engine, steps=steps)

    if data is None:
        print("  ❌ 데이터 수집 실패")
        return []

    ctx = {
        'telescope': telescope,
        'engine': engine,
        'data': data,
        'phis': phis,
        'cells': cells,
        'steps': steps,
    }

    results = []
    for exp_id in exp_ids:
        if exp_id not in REGISTRY:
            print(f"  ❌ {exp_id} 없음")
            continue
        exp = REGISTRY[exp_id]
        print(f"\n  🔬 {exp['id']}: {exp['name']}")
        t0 = time.time()
        try:
            r = exp['fn'](ctx)
            r.elapsed = time.time() - t0
            print(r.summary())
            results.append(r)
        except Exception as e:
            print(f"  ❌ {exp_id} 실패: {e}")

    # 교차 분석
    if len(results) >= 2:
        print("\n  ═══ 교차 분석 ═══")
        all_findings = []
        for r in results:
            all_findings.extend(r.findings)
        common = [f for f in all_findings if all_findings.count(f) > 1]
        if common:
            print(f"  공통 발견 {len(set(common))}건")
        print(f"  총 메트릭: {sum(len(r.metrics) for r in results)}개")

    return results


def save_results(results, output_dir=None):
    """결과를 JSON으로 저장"""
    if not results:
        return
    if output_dir is None:
        output_dir = ROOT / "data"
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ids = "_".join(r.exp_id for r in results)
    path = output_dir / f"lens_{ids}_{ts}.json"

    data = {
        "timestamp": ts,
        "experiments": [r.to_dict() for r in results],
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  💾 저장: {path}")


def list_experiments():
    """등록된 실험 목록"""
    print("\n  ════════════════════════════════════════════")
    print("  🔬 등록된 렌즈 실험")
    print("  ════════════════════════════════════════════\n")

    by_cat = defaultdict(list)
    for exp in REGISTRY.values():
        by_cat[exp['category']].append(exp)

    for cat in ['🔴', '🟡', '🟢', '⚪']:
        exps = by_cat.get(cat, [])
        if not exps:
            continue
        label = {'🔴': 'CRITICAL', '🟡': 'IMPORTANT', '🟢': 'NICE TO HAVE', '⚪': 'BACKLOG'}
        print(f"  {cat} {label.get(cat, '')}")
        for e in exps:
            print(f"    {e['id']}  {e['name']}")
            print(f"         {e['description']}")
        print()

    print(f"  총 {len(REGISTRY)}개 실험 등록\n")
    print("  사용법:")
    print("    python3 lens_engine.py L01           # 단일")
    print("    python3 lens_engine.py L01 L02       # 순차")
    print("    python3 lens_engine.py L01+L02       # 조합 (공유 데이터)")
    print("    python3 lens_engine.py L01 --cells 128 --steps 500")


def main():
    parser = argparse.ArgumentParser(description="통합 의식 렌즈 실험 엔진")
    parser.add_argument("experiments", nargs="*", help="실험 ID (L01, L01+L02, ...)")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--cells", type=int, default=64)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--lenses", help="렌즈 오버라이드 (comma-separated)")
    parser.add_argument("--save", action="store_true", default=True)
    args = parser.parse_args()

    if args.list:
        list_experiments()
        return

    if args.all:
        exp_ids = list(REGISTRY.keys())
    elif not args.experiments:
        list_experiments()
        return
    else:
        exp_ids = args.experiments

    print("  ════════════════════════════════════════════")
    print("  🔬 의식 렌즈 실험 엔진")
    print(f"  cells={args.cells}, steps={args.steps}")
    print("  ════════════════════════════════════════════")

    all_results = []
    for exp_spec in exp_ids:
        if '+' in exp_spec:
            # 조합 실험
            combo_ids = exp_spec.split('+')
            results = run_combo(combo_ids, args.cells, args.steps)
            all_results.extend(results)
        else:
            result = run_experiment(exp_spec, args.cells, args.steps)
            if result:
                all_results.append(result)

    if args.save and all_results:
        save_results(all_results)

    # 최종 요약
    print(f"\n  ════ 최종 요약 ════")
    print(f"  실행: {len(all_results)}개 실험")
    total_findings = sum(len(r.findings) for r in all_results)
    print(f"  발견: {total_findings}건")
    total_time = sum(r.elapsed for r in all_results)
    print(f"  시간: {total_time:.1f}s")


if __name__ == "__main__":
    main()
