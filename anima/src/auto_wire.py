#!/usr/bin/env python3
"""auto_wire.py — 새 모듈/연결점 자동 감지 → 루프 자동 편입

새 .py 파일이 생기거나, 기존 파일에 main()이 추가되면
자동으로 nexus_gate + training_hooks + recursive_loop 연결 여부를 검사하고,
미연결 시 경고 또는 자동 패치.

Usage:
  python3 auto_wire.py --scan                # 미연결 모듈 스캔
  python3 auto_wire.py --auto                # 자동 패치
  python3 auto_wire.py --watch               # 파일 변경 감시 (데몬)
  python3 auto_wire.py --report              # 연결 상태 리포트

hub 연동:
  hub.act("연결 검사")
  hub.act("auto wire")
"""

import ast
import glob
import json
import os
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = _THIS_DIR
_CONFIG_DIR = os.path.join(_THIS_DIR, '..', 'config')

# 연결 필수 패턴
REQUIRED_IMPORTS = {
    'nexus_gate': 'from nexus_gate import gate',
    'training_hooks': 'from training_hooks import TrainingHooks',
}

# 제외 파일 (자기 자신 + 유틸리티)
EXCLUDE = {
    'auto_wire.py', 'nexus_gate.py', 'training_hooks.py',
    'auto_discovery_loop.py', 'loop_report.py', 'path_setup.py',
    'consciousness_laws.py', '__init__.py',
}


def scan_modules() -> dict:
    """src/ 내 모든 .py 스캔 → 연결 상태 반환."""
    results = {'connected': [], 'missing': [], 'no_main': []}

    for py_file in sorted(glob.glob(os.path.join(_SRC_DIR, '*.py'))):
        name = os.path.basename(py_file)
        if name in EXCLUDE or name.startswith('_'):
            continue

        try:
            with open(py_file, 'r') as f:
                content = f.read()
        except:
            continue

        has_main = '__name__' in content and '__main__' in content
        has_gate = 'nexus_gate' in content

        if not has_main:
            results['no_main'].append(name)
            continue

        if has_gate:
            results['connected'].append(name)
        else:
            results['missing'].append(name)

    return results


def auto_patch(dry_run: bool = True) -> list:
    """미연결 모듈에 nexus_gate 자동 삽입."""
    results = scan_modules()
    patched = []

    for name in results['missing']:
        py_path = os.path.join(_SRC_DIR, name)
        try:
            with open(py_path, 'r') as f:
                lines = f.readlines()

            # if __name__ == "__main__": 라인 찾기
            insert_idx = None
            for i, line in enumerate(lines):
                if '__name__' in line and '__main__' in line:
                    insert_idx = i + 1
                    break

            if insert_idx is None:
                continue

            patch = [
                '    try:\n',
                '        from nexus_gate import gate\n',
                '        gate.before_commit()\n',
                '    except Exception:\n',
                '        pass\n',
            ]

            if dry_run:
                print(f"  [DRY] Would patch {name} at line {insert_idx + 1}")
            else:
                lines[insert_idx:insert_idx] = patch
                with open(py_path, 'w') as f:
                    f.writelines(lines)
                print(f"  [PATCHED] {name} at line {insert_idx + 1}")

            patched.append(name)
        except Exception as e:
            print(f"  [ERROR] {name}: {e}")

    return patched


def watch_for_changes(interval: int = 30):
    """파일 변경 감시 → 새 모듈 발견 시 자동 패치."""
    print(f"[AUTO-WIRE] Watching {_SRC_DIR} every {interval}s")
    prev_state = scan_modules()
    prev_files = set(os.listdir(_SRC_DIR))

    while True:
        time.sleep(interval)
        curr_files = set(os.listdir(_SRC_DIR))
        new_files = curr_files - prev_files

        if new_files:
            py_new = [f for f in new_files if f.endswith('.py') and f not in EXCLUDE]
            if py_new:
                print(f"\n[AUTO-WIRE] New files detected: {py_new}")
                curr_state = scan_modules()
                new_missing = set(curr_state['missing']) - set(prev_state['missing'])
                if new_missing:
                    print(f"[AUTO-WIRE] Auto-patching: {new_missing}")
                    auto_patch(dry_run=False)
                prev_state = scan_modules()

        prev_files = curr_files


def report() -> str:
    """연결 상태 리포트."""
    r = scan_modules()
    total = len(r['connected']) + len(r['missing'])

    lines = []
    lines.append(f"  ■ Auto-Wire 연결 상태")
    lines.append(f"  연결됨: {len(r['connected'])}/{total} | 미연결: {len(r['missing'])}/{total}")

    if r['connected']:
        lines.append(f"  ✅ {', '.join(r['connected'][:10])}")
    if r['missing']:
        lines.append(f"  ❌ {', '.join(r['missing'][:10])}")

    # 연결 상태 JSON 기록
    state_path = os.path.join(_CONFIG_DIR, 'auto_wire_state.json')
    state = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'connected': r['connected'],
        'missing': r['missing'],
        'coverage': len(r['connected']) / max(total, 1),
    }
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        json.dump(state, open(state_path, 'w'), indent=2, ensure_ascii=False)
    except:
        pass

    text = '\n'.join(lines)
    print(text)
    return text


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='자동 연결 감지/패치')
    p.add_argument('--scan', action='store_true', help='미연결 스캔')
    p.add_argument('--auto', action='store_true', help='자동 패치')
    p.add_argument('--watch', action='store_true', help='파일 감시 데몬')
    p.add_argument('--report', action='store_true', help='연결 리포트')
    p.add_argument('--dry-run', action='store_true', dest='dry_run', help='패치 미적용')
    args = p.parse_args()

    if args.scan or args.report:
        report()
    elif args.auto:
        r = scan_modules()
        print(f"Missing: {len(r['missing'])} modules")
        patched = auto_patch(dry_run=args.dry_run)
        print(f"Patched: {len(patched)}")
    elif args.watch:
        watch_for_changes()
    else:
        report()
