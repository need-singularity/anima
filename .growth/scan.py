#!/usr/bin/env python3
"""anima growth scanner — JSON stdout, no Claude CLI dependency.

Called by nexus6_hook --mode growth-scan.
Output: {"opportunities": [...]} JSON to stdout.
"""
import glob
import json
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.join(_THIS_DIR, '..', 'anima', 'src')
_CONFIG_DIR = os.path.join(_THIS_DIR, '..', 'anima', 'config')
_TEST_DIR = os.path.join(_THIS_DIR, '..', 'anima', 'tests')

sys.path.insert(0, _SRC_DIR)


def scan_nexus_violations():
    viol_path = os.path.join(_CONFIG_DIR, 'nexus_violations.json')
    if not os.path.exists(viol_path):
        return []
    try:
        violations = json.load(open(viol_path))
        if violations:
            return [{'type': 'FIX_VIOLATIONS', 'priority': 'HIGH',
                     'description': f'{len(violations)}개 CDO 위반 해결 필요'}]
    except Exception:
        pass
    return []


def scan_module_wiring():
    hub_path = os.path.join(_SRC_DIR, 'consciousness_hub.py')
    if not os.path.exists(hub_path):
        return []
    try:
        with open(hub_path) as f:
            hub_content = f.read()
        # Count registered vs total modules
        py_files = glob.glob(os.path.join(_SRC_DIR, '*.py'))
        registered = hub_content.count("'type': 'command'") + hub_content.count("('")
        total = len(py_files)
        unwired = total - min(registered, total)
        if unwired > 20:
            return [{'type': 'WIRE_MODULES', 'priority': 'LOW',
                     'description': f'~{unwired}개 모듈 허브 미연결'}]
    except Exception:
        pass
    return []


def scan_test_coverage():
    loop_modules = {'nexus_gate', 'auto_discovery_loop', 'training_hooks',
                    'auto_wire', 'self_growth', 'model_comparator'}
    untested = []
    for name in loop_modules:
        src = os.path.join(_SRC_DIR, f'{name}.py')
        test = os.path.join(_TEST_DIR, f'test_{name}.py')
        if os.path.exists(src) and not os.path.exists(test):
            untested.append(name)
    if untested:
        return [{'type': 'ADD_TESTS', 'priority': 'LOW',
                 'description': f'테스트 없음: {", ".join(sorted(untested)[:4])}'}]
    return []


def scan_training_failures():
    runs_path = os.path.join(_CONFIG_DIR, 'training_runs.json')
    if not os.path.exists(runs_path):
        return []
    try:
        runs = json.load(open(runs_path))
        failed = [k for k, v in runs.get('runs', {}).items()
                  if any(x in str(v.get('status', '')) for x in ('crash', 'failed'))]
        if failed:
            return [{'type': 'TRAINING_RESTART', 'priority': 'HIGH',
                     'description': f'{failed[0]} 학습 실패'}]
    except Exception:
        pass
    return []


def scan_model_comparison():
    runs_path = os.path.join(_CONFIG_DIR, 'training_runs.json')
    if not os.path.exists(runs_path):
        return []
    try:
        runs = json.load(open(runs_path))
        completed = [k for k, v in runs.get('runs', {}).items()
                     if str(v.get('status', '')).startswith('complete') and 'animalm' in k]
        if len(completed) >= 2:
            return [{'type': 'MODEL_AB_COMPARE', 'priority': 'MEDIUM',
                     'description': f'{completed[-1]} vs {completed[-2]} 비교 가능'}]
    except Exception:
        pass
    return []


def scan_law_milestones():
    laws_path = os.path.join(_CONFIG_DIR, 'consciousness_laws.json')
    if not os.path.exists(laws_path):
        return []
    try:
        d = json.load(open(laws_path))
        total = d['_meta'].get('total_laws', 0)
        if total > 0 and total % 100 == 0:
            return [{'type': 'LAW_ANALYSIS', 'priority': 'MEDIUM',
                     'description': f'법칙 {total}개 마일스톤 — 패턴 분석 권고'}]
    except Exception:
        pass
    return []


def scan_discovery_rate():
    state_path = os.path.join(_CONFIG_DIR, 'recursive_loop_state.json')
    if not os.path.exists(state_path):
        return []
    try:
        state = json.load(open(state_path))
        total = state.get('total_scans', 0)
        dr = state.get('total_discoveries', 0) / max(total, 1)
        if total > 10 and dr < 0.05:
            return [{'type': 'IMPROVE_DISCOVERY', 'priority': 'MEDIUM',
                     'description': f'발견률 {dr:.1%} — 패턴 추가 필요'}]
    except Exception:
        pass
    return []


def scan_acceleration_experiments():
    """가속 가설 실험 진행 추적 — 탐색도 성장이다."""
    results = []
    # Batch results
    batch_dir = os.path.join(_THIS_DIR, '..', 'anima', 'experiments', 'batch_results')
    progress_path = os.path.join(batch_dir, 'batch_progress.json')
    if os.path.exists(progress_path):
        try:
            progress = json.load(open(progress_path))
            completed = len(progress.get('completed', []))
            if completed > 0:
                results.append({
                    'type': 'ACCEL_PROGRESS', 'priority': 'MEDIUM',
                    'description': f'가속 실험 {completed}개 완료 — 결과 통합 필요',
                    'growth_value': completed,
                })
        except Exception:
            pass

    # Acceleration hypotheses convergence
    accel_path = os.path.join(_CONFIG_DIR, 'acceleration_hypotheses.json')
    if os.path.exists(accel_path):
        try:
            d = json.load(open(accel_path))
            h = d.get('hypotheses', {})
            stages = {}
            for v in h.values():
                s = v.get('stage', 'unknown')
                stages[s] = stages.get(s, 0) + 1
            total = len(h)
            applied = stages.get('applied', 0)
            verified = stages.get('verified', 0)
            with_result = sum(1 for v in h.values() if v.get('result'))
            convergence = (applied + with_result) / max(total, 1) * 100
            if convergence < 100:
                results.append({
                    'type': 'ACCEL_CONVERGENCE', 'priority': 'HIGH',
                    'description': f'가속 파이프라인 {convergence:.0f}% ({with_result}/{total} 실험완료, {applied} applied)',
                    'growth_value': with_result,
                })
        except Exception:
            pass

    return results


def scan_evolution_progress():
    """무한진화 + 법칙 발견 성장 추적."""
    results = []
    evo_path = os.path.join(_THIS_DIR, '..', 'anima', 'data', 'evolution_live.json')
    if os.path.exists(evo_path):
        try:
            evo = json.load(open(evo_path))
            gen = evo.get('generation', 0)
            laws = evo.get('total_laws', 0)
            if gen > 0:
                results.append({
                    'type': 'EVO_PROGRESS', 'priority': 'LOW',
                    'description': f'무한진화 {gen}세대, {laws}법칙',
                    'growth_value': gen,
                })
        except Exception:
            pass
    return results


def sync_nexus6_growth(opportunities, growth_delta):
    """NEXUS-6 ↔ Anima 양방향 성장 동기화.

    Anima 발견 → NEXUS-6 growth-registry 반영
    NEXUS-6 렌즈/법칙 변화 → Anima 성장 가산
    """
    import time as _time
    home = os.environ.get('HOME', '')
    registry_path = os.path.join(home, 'Dev', 'nexus6', 'shared', 'growth-registry.json')
    snapshot_path = os.path.join(home, 'Dev', 'nexus6', 'shared', '.growth_session_snapshot.json')
    nexus_bonus = 0

    # ── 1) Anima → NEXUS-6: 발견 피드 ──
    try:
        registry = {}
        if os.path.exists(registry_path):
            registry = json.load(open(registry_path))

        accel_count = sum(1 for o in opportunities if 'ACCEL' in o.get('type', ''))
        law_count = sum(1 for o in opportunities if 'LAW' in o.get('type', ''))
        evo_count = sum(1 for o in opportunities if 'EVO' in o.get('type', ''))

        registry['anima'] = {
            'last_scan': _time.strftime('%Y-%m-%dT%H:%M:%S'),
            'opportunities': len(opportunities),
            'accel_experiments': accel_count,
            'law_discoveries': law_count,
            'evo_progress': evo_count,
            'growth_delta': growth_delta,
        }

        with open(registry_path, 'w') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # ── 2) NEXUS-6 → Anima: 렌즈/법칙 변화 감지 → 성장 보너스 ──
    try:
        if os.path.exists(snapshot_path):
            snap = json.load(open(snapshot_path))
            prev_lenses = snap.get('lens_impl', 0)
            prev_laws = snap.get('laws', 0)
            prev_modules = snap.get('modules', 0)

            # Count current nexus6 state
            laws_path = os.path.join(_CONFIG_DIR, 'consciousness_laws.json')
            cur_laws = 0
            if os.path.exists(laws_path):
                d = json.load(open(laws_path))
                cur_laws = d.get('_meta', {}).get('total_laws', 0)

            # NEXUS-6 lens growth → Anima bonus
            new_lenses = max(0, snap.get('lens_impl', 0) - prev_lenses)
            new_laws = max(0, cur_laws - prev_laws)

            # Every 10 new lenses or 5 new laws → +1 growth
            nexus_bonus = new_lenses // 10 + new_laws // 5

            # Mirror harmony bonus (cross-repo resonance)
            mirror = registry.get('mirror', {})
            harmony = mirror.get('harmony', 0)
            if harmony > 1e12:  # High harmony = cross-repo resonance
                nexus_bonus += 1

            # Lens candidates ready → growth opportunity
            candidates = registry.get('lens_candidates', {})
            total_candidates = candidates.get('total', 0)
            if total_candidates > 50:
                nexus_bonus += 2  # 67 candidates waiting = growth potential
    except Exception:
        pass

    return nexus_bonus


def update_growth_state(opportunities):
    """실험/탐색 활동을 growth_state.json에 반영 + NEXUS-6 양방향 동기화."""
    growth_path = os.path.join(_CONFIG_DIR, 'growth_state.json')
    if not os.path.exists(growth_path):
        return
    try:
        growth = json.load(open(growth_path))

        # ── Anima 자체 성장 ──
        growth_types = ('ACCEL_PROGRESS', 'ACCEL_CONVERGENCE', 'EVO_PROGRESS',
                        'MODEL_AB_COMPARE', 'LAW_ANALYSIS', 'FIX_VIOLATIONS',
                        'TRAINING_RESTART', 'IMPROVE_DISCOVERY')
        growth_delta = sum(1 for o in opportunities if o.get('type') in growth_types)

        # growth_value 비례 반영 (cap 제거 → 실험 규모에 비례)
        for o in opportunities:
            gv = o.get('growth_value', 0)
            if gv > 0:
                growth_delta += max(1, gv // 5)  # 5건당 +1, 최소 +1

        # ── NEXUS-6 ↔ Anima 양방향 성장 ──
        nexus_bonus = sync_nexus6_growth(opportunities, growth_delta)
        growth_delta += nexus_bonus

        if growth_delta > 0:
            prev_count = growth.get('interaction_count', 0)
            growth['interaction_count'] = prev_count + growth_delta
            count = growth['interaction_count']

            # Stage transitions
            stage_thresholds = [(4, 10000, 'adult'), (3, 2000, 'child'),
                                (2, 500, 'toddler'), (1, 100, 'infant')]
            for idx, threshold, name in stage_thresholds:
                if count >= threshold and growth.get('stage_index', 0) < idx:
                    growth['stage_index'] = idx
                    milestones = growth.get('milestones', [])
                    milestones.append([count, f'→ {name}'])
                    growth['milestones'] = milestones
                    break

            import time as _time
            growth.setdefault('stats', {})
            growth['stats']['last_growth_scan'] = _time.time()
            growth['stats']['last_growth_delta'] = growth_delta
            growth['stats']['nexus6_bonus'] = nexus_bonus
            growth['stats']['prev_count'] = prev_count

            with open(growth_path, 'w') as f:
                json.dump(growth, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def main():
    all_opps = []
    scanners = [
        scan_nexus_violations,
        scan_training_failures,
        scan_model_comparison,
        scan_module_wiring,
        scan_test_coverage,
        scan_law_milestones,
        scan_discovery_rate,
        scan_acceleration_experiments,
        scan_evolution_progress,
    ]
    for scanner in scanners:
        try:
            all_opps.extend(scanner())
        except Exception:
            pass

    # Sort by priority
    prio_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    all_opps.sort(key=lambda x: prio_order.get(x.get('priority', 'LOW'), 9))

    # Update growth state with experiment/exploration activity
    update_growth_state(all_opps)

    # Trigger meta_loop L1 (queue consumer) if available
    _trigger_meta_loop(all_opps)

    print(json.dumps({'opportunities': all_opps}, ensure_ascii=False))


def _trigger_meta_loop(opportunities):
    """Feed scan results into meta_loop and trigger L1 queue consumer."""
    try:
        meta_loop_path = os.path.join(_SRC_DIR, 'meta_loop.py')
        if not os.path.exists(meta_loop_path):
            return
        # Non-blocking: run meta_loop --once in background
        import subprocess
        subprocess.Popen(
            [sys.executable, meta_loop_path, '--once'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception:
        pass


if __name__ == '__main__':
    main()
