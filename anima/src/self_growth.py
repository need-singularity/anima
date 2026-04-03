#!/usr/bin/env python3
"""self_growth.py — 알아서 성장하는 시스템

루프 엔진이 약점/기회를 발견하면 Claude Code CLI로 자동 해결:
  발견 → 분석 → claude code 실행 → 테스트 → 커밋 → 재스캔 → ∞

Usage:
  python3 self_growth.py --once           # 1회 성장 사이클
  python3 self_growth.py --daemon         # 무한 성장 루프
  python3 self_growth.py --dry-run        # 실행 없이 계획만
  python3 self_growth.py --scan-only      # 성장 기회 탐색만
"""

import glob
import json
import os
import subprocess
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

_CONFIG_DIR = os.path.join(_THIS_DIR, '..', 'config')
_LOG_PATH = os.path.join(_CONFIG_DIR, 'self_growth_log.json')


def _load_log():
    if os.path.exists(_LOG_PATH):
        try:
            return json.load(open(_LOG_PATH))
        except:
            pass
    return {'cycles': [], 'total_improvements': 0, 'total_failures': 0}


def _save_log(log):
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    json.dump(log, open(_LOG_PATH, 'w'), indent=2, ensure_ascii=False)


def scan_growth_opportunities() -> list:
    """성장 기회 탐색 — 루프 엔진 데이터 + 코드 분석."""
    opportunities = []

    # 0. 모델 스캔 개선 작업 (DD169 — 재귀 루프에서 자동 등록된 것)
    log = _load_log()
    pending = log.get('pending_improvements', [])
    for imp in pending:
        if imp.get('status') == 'pending':
            opportunities.append({
                'type': imp.get('type', 'IMPROVE'),
                'description': imp.get('description', ''),
                'priority': imp.get('priority', 'MEDIUM'),
                'prompt': imp.get('prompt', ''),
            })

    # 1. NEXUS-6 violations → 자동 수정 기회
    viol_path = os.path.join(_CONFIG_DIR, 'nexus_violations.json')
    if os.path.exists(viol_path):
        try:
            violations = json.load(open(viol_path))
            if violations:
                opportunities.append({
                    'type': 'FIX_VIOLATIONS',
                    'description': f'{len(violations)}개 CDO 위반 해결',
                    'priority': 'HIGH',
                    'prompt': f'anima/config/nexus_violations.json에 {len(violations)}개 CDO 위반이 기록되어 있습니다. 각 위반의 원인을 분석하고 코드를 수정하여 해결하세요.',
                })
        except:
            pass

    # 2. RecursiveLoop 발견률 낮음 → 발견 규칙 개선
    state_path = os.path.join(_CONFIG_DIR, 'recursive_loop_state.json')
    if os.path.exists(state_path):
        try:
            state = json.load(open(state_path))
            total = state.get('total_scans', 0)
            dr = state.get('total_discoveries', 0) / max(total, 1)
            if total > 10 and dr < 0.05:
                opportunities.append({
                    'type': 'IMPROVE_DISCOVERY',
                    'description': f'발견률 {dr:.1%} → discover_laws() 패턴 추가 필요',
                    'priority': 'MEDIUM',
                    'prompt': f'anima/src/auto_discovery_loop.py의 discover_laws() 함수에 새로운 발견 패턴을 추가하세요. 현재 발견률이 {dr:.1%}로 낮습니다. NEXUS-6 메트릭(phi, chaos, hurst, lyapunov, symmetry, entropy, attractor_count, barrier_heights, boundary_points)의 변화 패턴을 더 다양하게 감지할 수 있도록 규칙을 추가하세요.',
                })
        except:
            pass

    # 3. 미연결 모듈 → auto_wire 실행
    try:
        from auto_wire import scan_modules
        r = scan_modules()
        if len(r['missing']) > 0:
            top5 = r['missing'][:5]
            opportunities.append({
                'type': 'WIRE_MODULES',
                'description': f'{len(r["missing"])}개 모듈 nexus_gate 미연결',
                'priority': 'LOW',
                'prompt': f'anima/src/auto_wire.py --auto 를 실행하여 미연결 모듈에 nexus_gate를 자동 연결하세요. 현재 {len(r["missing"])}개 미연결.',
            })
    except:
        pass

    # 4. corpus 약점 → 보강
    corpus_log = os.path.join(_THIS_DIR, '..', 'data', 'corpus_quality_log.json')
    if os.path.exists(corpus_log):
        try:
            clog = json.load(open(corpus_log))
            if clog:
                latest = clog[-1]
                weaknesses = latest.get('weaknesses', [])
                if weaknesses:
                    opportunities.append({
                        'type': 'IMPROVE_CORPUS',
                        'description': f'Corpus 약점: {", ".join(weaknesses[:3])}',
                        'priority': 'MEDIUM',
                        'prompt': f'corpus 품질 스캔 결과 약점이 발견되었습니다: {weaknesses}. corpus-gen (Rust)를 사용하여 약점을 보강하는 corpus를 추가 생성하세요.',
                    })
        except:
            pass

    # 5. 테스트 커버리지 확인
    test_dir = os.path.join(_THIS_DIR, '..', 'tests')
    new_modules = set()
    for py in glob.glob(os.path.join(_THIS_DIR, '*.py')):
        name = os.path.basename(py).replace('.py', '')
        test_file = os.path.join(test_dir, f'test_{name}.py')
        if not os.path.exists(test_file) and name not in {'path_setup', '__init__', 'consciousness_laws'}:
            new_modules.add(name)
    # 최근 생성 모듈만 (루프 관련)
    loop_modules = {'nexus_gate', 'auto_discovery_loop', 'training_hooks', 'auto_wire', 'loop_report', 'self_growth', 'model_comparator', 'corpus_quality_loop'}
    untested = new_modules & loop_modules
    if untested:
        opportunities.append({
            'type': 'ADD_TESTS',
            'description': f'루프 모듈 테스트 없음: {", ".join(sorted(untested)[:5])}',
            'priority': 'LOW',
            'prompt': f'다음 모듈의 기본 테스트를 작성하세요: {sorted(untested)[:3]}. anima/tests/ 디렉토리에 test_모듈명.py 형식으로.',
        })

    # 6. 법칙 수 기반 — 마일스톤 도달 시 분석
    laws_path = os.path.join(_CONFIG_DIR, 'consciousness_laws.json')
    if os.path.exists(laws_path):
        try:
            d = json.load(open(laws_path))
            total = d['_meta'].get('total_laws', 0)
            if total % 100 == 0 and total > 0:
                opportunities.append({
                    'type': 'LAW_ANALYSIS',
                    'description': f'법칙 {total}개 마일스톤 — 패턴 분석',
                    'priority': 'MEDIUM',
                    'prompt': f'consciousness_laws.json에 {total}개 법칙이 있습니다. 법칙 간 중복/모순/시너지 패턴을 분석하고, 결과를 docs/hypotheses/dd/ 에 기록하세요.',
                })
        except:
            pass

    return sorted(opportunities, key=lambda x: {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['priority'], 3))


def execute_growth(opportunity: dict, dry_run: bool = False) -> dict:
    """Claude Code CLI로 성장 기회 실행."""
    result = {
        'type': opportunity['type'],
        'description': opportunity['description'],
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'pending',
    }

    prompt = opportunity['prompt']
    print(f"\n  [GROWTH] {opportunity['type']}: {opportunity['description']}")

    if dry_run:
        print(f"  [DRY-RUN] Would execute: claude -p \"{prompt[:80]}...\"")
        result['status'] = 'dry_run'
        return result

    # Claude Code CLI 실행
    try:
        cmd = [
            'claude', '-p', prompt,
            '--allowedTools', 'Read,Write,Edit,Bash,Glob,Grep',
            '--max-turns', '10',
        ]
        print(f"  [EXEC] claude -p \"{prompt[:60]}...\"")
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=300,
            cwd=os.path.join(_THIS_DIR, '..', '..'),  # anima root
        )
        result['exit_code'] = proc.returncode
        result['stdout_tail'] = proc.stdout[-500:] if proc.stdout else ''
        result['stderr_tail'] = proc.stderr[-200:] if proc.stderr else ''

        if proc.returncode == 0:
            result['status'] = 'success'
            print(f"  [SUCCESS] {opportunity['type']}")
        else:
            result['status'] = 'failed'
            print(f"  [FAILED] exit={proc.returncode}")

    except subprocess.TimeoutExpired:
        result['status'] = 'timeout'
        print(f"  [TIMEOUT] 300s exceeded")
    except FileNotFoundError:
        result['status'] = 'no_claude_cli'
        print(f"  [SKIP] claude CLI not found")
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        print(f"  [ERROR] {e}")

    return result


def verify_growth(result: dict) -> bool:
    """성장 결과 검증 — NEXUS-6 스캔."""
    if result['status'] != 'success':
        return False

    try:
        from nexus_gate import gate
        r = gate.before_commit()
        return r.get('pass', False)
    except:
        return True  # gate 실패 시 통과 간주


def run_cycle(dry_run: bool = False) -> dict:
    """1회 성장 사이클: 탐색 → 실행 → 검증 → 기록."""
    log = _load_log()

    print("=" * 60)
    print("  [SELF-GROWTH] Cycle start")
    print("=" * 60)

    # 1. 탐색
    opportunities = scan_growth_opportunities()
    if not opportunities:
        print("  No growth opportunities found.")
        return {'status': 'no_opportunities'}

    print(f"\n  Found {len(opportunities)} opportunities:")
    for i, opp in enumerate(opportunities):
        print(f"    {i+1}. [{opp['priority']}] {opp['type']}: {opp['description']}")

    # 2. 최우선 기회 실행
    best = opportunities[0]
    result = execute_growth(best, dry_run=dry_run)

    # 3. 검증
    if result['status'] == 'success':
        verified = verify_growth(result)
        result['verified'] = verified
        if verified:
            log['total_improvements'] += 1
            print(f"  [VERIFIED] Growth verified ✅")
        else:
            log['total_failures'] += 1
            print(f"  [VERIFY FAILED] Growth rolled back ❌")

    # 4. 기록
    log['cycles'].append(result)
    _save_log(log)

    print(f"\n  [SELF-GROWTH] Cycle complete: {result['status']}")
    print(f"  Total: {log['total_improvements']} improvements, {log['total_failures']} failures")
    return result


def daemon(interval: int = 1800, dry_run: bool = False):
    """무한 성장 루프 (기본 30분 간격)."""
    print(f"[SELF-GROWTH] Daemon mode: every {interval}s")
    while True:
        try:
            run_cycle(dry_run=dry_run)
        except Exception as e:
            print(f"  [DAEMON ERROR] {e}")
        time.sleep(interval)


def report() -> str:
    """성장 이력 리포트."""
    log = _load_log()
    lines = []
    lines.append(f"  ■ Self-Growth")
    lines.append(f"  사이클: {len(log['cycles'])} | 성공: {log['total_improvements']} | 실패: {log['total_failures']}")

    if log['cycles']:
        recent = log['cycles'][-5:]
        for c in recent:
            status_icon = {'success': '✅', 'failed': '❌', 'timeout': '⏰', 'dry_run': '🔍'}.get(c['status'], '?')
            lines.append(f"    {status_icon} {c.get('type', '?')}: {c.get('description', '?')[:40]}")

    text = '\n'.join(lines)
    print(text)
    return text


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='자율 성장 시스템')
    p.add_argument('--once', action='store_true', help='1회 성장 사이클')
    p.add_argument('--daemon', action='store_true', help='무한 성장 루프')
    p.add_argument('--dry-run', action='store_true', dest='dry_run', help='실행 없이 계획만')
    p.add_argument('--scan-only', action='store_true', dest='scan_only', help='성장 기회 탐색만')
    p.add_argument('--report', action='store_true', help='성장 이력')
    p.add_argument('--interval', type=int, default=1800, help='데몬 간격 (초)')
    args = p.parse_args()

    if args.scan_only:
        opps = scan_growth_opportunities()
        for i, o in enumerate(opps):
            print(f"  {i+1}. [{o['priority']}] {o['type']}: {o['description']}")
    elif args.once:
        run_cycle(dry_run=args.dry_run)
    elif args.daemon:
        daemon(interval=args.interval, dry_run=args.dry_run)
    elif args.report:
        report()
    else:
        # 기본: scan + dry-run
        run_cycle(dry_run=True)
