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
    ]
    for scanner in scanners:
        try:
            all_opps.extend(scanner())
        except Exception:
            pass

    # Sort by priority
    prio_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
    all_opps.sort(key=lambda x: prio_order.get(x.get('priority', 'LOW'), 9))

    print(json.dumps({'opportunities': all_opps}, ensure_ascii=False))


if __name__ == '__main__':
    main()
