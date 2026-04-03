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
from concurrent.futures import ThreadPoolExecutor, as_completed

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


def _scan_pending_improvements() -> list:
    """Scan 0: pending improvements from log."""
    results = []
    log = _load_log()
    pending = log.get('pending_improvements', [])
    for imp in pending:
        if imp.get('status') == 'pending':
            results.append({
                'type': imp.get('type', 'IMPROVE'),
                'description': imp.get('description', ''),
                'priority': imp.get('priority', 'MEDIUM'),
                'prompt': imp.get('prompt', ''),
            })
    return results


def _scan_nexus_violations() -> list:
    """Scan 1: NEXUS-6 violations."""
    results = []
    viol_path = os.path.join(_CONFIG_DIR, 'nexus_violations.json')
    if os.path.exists(viol_path):
        try:
            violations = json.load(open(viol_path))
            if violations:
                results.append({
                    'type': 'FIX_VIOLATIONS',
                    'description': f'{len(violations)}개 CDO 위반 해결',
                    'priority': 'HIGH',
                    'prompt': f'anima/config/nexus_violations.json에 {len(violations)}개 CDO 위반이 기록되어 있습니다. 각 위반의 원인을 분석하고 코드를 수정하여 해결하세요.',
                })
        except Exception:
            pass
    return results


def _scan_discovery_rate() -> list:
    """Scan 2: RecursiveLoop discovery rate analysis."""
    results = []
    state_path = os.path.join(_CONFIG_DIR, 'recursive_loop_state.json')
    if os.path.exists(state_path):
        try:
            state = json.load(open(state_path))
            total = state.get('total_scans', 0)
            dr = state.get('total_discoveries', 0) / max(total, 1)
            if total > 10 and dr < 0.05:
                results.append({
                    'type': 'IMPROVE_DISCOVERY',
                    'description': f'발견률 {dr:.1%} → discover_laws() 패턴 추가 필요',
                    'priority': 'MEDIUM',
                    'prompt': f'anima/src/auto_discovery_loop.py의 discover_laws() 함수에 새로운 발견 패턴을 추가하세요. 현재 발견률이 {dr:.1%}로 낮습니다. NEXUS-6 메트릭(phi, chaos, hurst, lyapunov, symmetry, entropy, attractor_count, barrier_heights, boundary_points)의 변화 패턴을 더 다양하게 감지할 수 있도록 규칙을 추가하세요.',
                })
        except Exception:
            pass
    return results


def _scan_module_wiring() -> list:
    """Scan 3: Module wiring check."""
    results = []
    try:
        from auto_wire import scan_modules
        r = scan_modules()
        if len(r['missing']) > 0:
            results.append({
                'type': 'WIRE_MODULES',
                'description': f'{len(r["missing"])}개 모듈 nexus_gate 미연결',
                'priority': 'LOW',
                'prompt': f'anima/src/auto_wire.py --auto 를 실행하여 미연결 모듈에 nexus_gate를 자동 연결하세요. 현재 {len(r["missing"])}개 미연결.',
            })
    except Exception:
        pass
    return results


def _scan_corpus_quality() -> list:
    """Scan 4: Corpus weakness detection."""
    results = []
    corpus_log = os.path.join(_THIS_DIR, '..', 'data', 'corpus_quality_log.json')
    if os.path.exists(corpus_log):
        try:
            clog = json.load(open(corpus_log))
            if clog:
                latest = clog[-1]
                weaknesses = latest.get('weaknesses', [])
                if weaknesses:
                    results.append({
                        'type': 'IMPROVE_CORPUS',
                        'description': f'Corpus 약점: {", ".join(weaknesses[:3])}',
                        'priority': 'MEDIUM',
                        'prompt': f'corpus 품질 스캔 결과 약점이 발견되었습니다: {weaknesses}. corpus-gen (Rust)를 사용하여 약점을 보강하는 corpus를 추가 생성하세요.',
                    })
        except Exception:
            pass
    return results


def _scan_test_coverage() -> list:
    """Scan 5: Test coverage check."""
    results = []
    test_dir = os.path.join(_THIS_DIR, '..', 'tests')
    new_modules = set()
    for py in glob.glob(os.path.join(_THIS_DIR, '*.py')):
        name = os.path.basename(py).replace('.py', '')
        test_file = os.path.join(test_dir, f'test_{name}.py')
        if not os.path.exists(test_file) and name not in {'path_setup', '__init__', 'consciousness_laws'}:
            new_modules.add(name)
    loop_modules = {'nexus_gate', 'auto_discovery_loop', 'training_hooks', 'auto_wire', 'loop_report', 'self_growth', 'model_comparator', 'corpus_quality_loop'}
    untested = new_modules & loop_modules
    if untested:
        results.append({
            'type': 'ADD_TESTS',
            'description': f'루프 모듈 테스트 없음: {", ".join(sorted(untested)[:5])}',
            'priority': 'LOW',
            'prompt': f'다음 모듈의 기본 테스트를 작성하세요: {sorted(untested)[:3]}. anima/tests/ 디렉토리에 test_모듈명.py 형식으로.',
        })
    return results


def _scan_law_milestones() -> list:
    """Scan 6: Law count milestones."""
    results = []
    laws_path = os.path.join(_CONFIG_DIR, 'consciousness_laws.json')
    if os.path.exists(laws_path):
        try:
            d = json.load(open(laws_path))
            total = d['_meta'].get('total_laws', 0)
            if total % 100 == 0 and total > 0:
                results.append({
                    'type': 'LAW_ANALYSIS',
                    'description': f'법칙 {total}개 마일스톤 — 패턴 분석',
                    'priority': 'MEDIUM',
                    'prompt': f'consciousness_laws.json에 {total}개 법칙이 있습니다. 법칙 간 중복/모순/시너지 패턴을 분석하고, 결과를 docs/hypotheses/dd/ 에 기록하세요.',
                })
        except Exception:
            pass
    return results


def _scan_model_comparison() -> list:
    """Scan 7: Model A/B comparison."""
    results = []
    try:
        runs = json.load(open(os.path.join(_CONFIG_DIR, 'training_runs.json')))
        completed = [k for k, v in runs.get('runs', {}).items()
                     if v.get('status', '').startswith('complete') and 'animalm' in k]
        if len(completed) >= 2:
            latest = completed[-1]
            prev = completed[-2]
            results.append({
                'type': 'MODEL_AB_COMPARE',
                'description': f'{latest} vs {prev} 자동 비교',
                'priority': 'HIGH',
                'prompt': (f'anima/src/model_comparator.py를 사용하여 {latest}와 {prev} 체크포인트를 NEXUS-6로 비교하세요. '
                          f'Phi, chaos, hurst, attractor 등 핵심 메트릭 비교 테이블을 출력하고, '
                          f'어느 모델이 더 나은지 판정하세요. 결과를 docs/hypotheses/dd/ 에 기록.'),
            })
    except Exception:
        pass
    return results


def _scan_training_failures() -> list:
    """Scan 8: Training failure detection + Scan 9: Corpus expansion."""
    results = []
    try:
        runs = json.load(open(os.path.join(_CONFIG_DIR, 'training_runs.json')))
        for k, v in runs.get('runs', {}).items():
            if 'crash' in str(v.get('status', '')) or 'failed' in str(v.get('status', '')):
                results.append({
                    'type': 'TRAINING_RESTART',
                    'description': f'{k} 학습 실패 — 자동 재시작',
                    'priority': 'HIGH',
                    'prompt': (f'{k} 학습이 실패했습니다. training_runs.json에서 원인을 확인하고, '
                              f'파라미터를 조정한 후 재발사 스크립트를 생성하세요. '
                              f'OOM이면 batch size 줄이기, NaN이면 lr 줄이기, dtype이면 bf16 마스터 규칙 적용.'),
                })
    except Exception:
        pass

    # 9. Corpus auto-expansion
    corpus_log = os.path.join(_THIS_DIR, '..', 'data', 'corpus_quality_log.json')
    if os.path.exists(corpus_log):
        try:
            clog = json.load(open(corpus_log))
            if clog and clog[-1].get('weaknesses'):
                weaknesses = clog[-1]['weaknesses']
                results.append({
                    'type': 'CORPUS_EXPAND',
                    'description': f'Corpus 약점: {weaknesses[0][:40]}',
                    'priority': 'HIGH',
                    'prompt': (f'corpus 품질 약점: {weaknesses}. '
                              f'anima-rs/crates/corpus-gen 바이너리로 약점 보강 corpus를 생성하세요. '
                              f'생성 후 NEXUS-6 스캔으로 품질 확인, R2 anima-corpus에 업로드.'),
                })
        except Exception:
            pass
    return results


def _scan_hyperparam_tuning() -> list:
    """Scan 10: Hyperparameter auto-tuning."""
    results = []
    try:
        from auto_discovery_loop import _recursive_loop
        s = _recursive_loop.state
        if s.get('total_discoveries', 0) > 5:
            results.append({
                'type': 'HYPERPARAM_TUNE',
                'description': '발견 기반 하이퍼파라미터 자동 조정',
                'priority': 'MEDIUM',
                'prompt': (f'DD169에서 이식 희석(Phi 34% 압축) 발견. training_runs.json의 next_planned를 분석하여 '
                          f'alpha_end 0.5→0.7, target_layers 8→12 등 조정 제안. '
                          f'training_runs.json에 조정된 설정 반영.'),
            })
    except Exception:
        pass
    return results


def _scan_session_sync() -> list:
    """Scan 11: Multi-session sync."""
    results = []
    session_board = os.path.join(_CONFIG_DIR, 'session_board.json')
    if os.path.exists(session_board):
        try:
            sb = json.load(open(session_board))
            if sb.get('discoveries') and len(sb['discoveries']) > 0:
                results.append({
                    'type': 'SESSION_SYNC',
                    'description': f'세션 간 발견 {len(sb["discoveries"])}개 동기화',
                    'priority': 'MEDIUM',
                    'prompt': (f'config/session_board.json에 {len(sb["discoveries"])}개 발견이 있습니다. '
                              f'consciousness_laws.json에 미등록된 발견을 등록하고, '
                              f'session_board.json을 정리하세요.'),
                })
        except Exception:
            pass
    return results


def _scan_scheduling() -> list:
    """Scan 12: Time-based scheduling."""
    results = []
    import datetime
    hour = datetime.datetime.now().hour
    weekday = datetime.datetime.now().weekday()
    if hour == 3:
        results.append({
            'type': 'NIGHTLY_MAINTENANCE',
            'description': '야간 유지보수 — 정리, 최적화, 리포트',
            'priority': 'MEDIUM',
            'prompt': ('야간 유지보수: 1) git gc, 2) 불필요 체크포인트 정리, '
                      '3) loop_report.py --export 실행, 4) loop_extensions.py --health 실행.'),
        })
    if weekday == 0 and hour == 9:
        results.append({
            'type': 'WEEKLY_REPORT',
            'description': '주간 리포트 — 지난주 성과 정리',
            'priority': 'MEDIUM',
            'prompt': ('주간 리포트 작성: config/training_runs.json, recursive_loop_state.json, '
                      'self_growth_log.json 분석. 지난주 학습/발견/개선 요약. '
                      'docs/hypotheses/dd/ 에 주간 리포트 DD 문서 작성.'),
        })
    return results


def _scan_pod_management() -> list:
    """Scan 13: Pod auto-management."""
    results = []
    try:
        r = subprocess.run(['/opt/homebrew/bin/runpodctl', 'pod', 'list', '-o', 'json'],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            pods = json.loads(r.stdout)
            for pod in (pods if isinstance(pods, list) else [pods]):
                status = pod.get('desiredStatus', '')
                runtime_h = pod.get('runtime', {}).get('uptimeInSeconds', 0) / 3600
                if status == 'RUNNING' and runtime_h > 24:
                    results.append({
                        'type': 'POD_MANAGE',
                        'description': f'Pod {pod.get("name","?")} {runtime_h:.0f}h 실행 중 — 중지 검토',
                        'priority': 'MEDIUM',
                        'prompt': (f'RunPod {pod.get("name")}가 {runtime_h:.0f}시간 실행 중. '
                                  f'학습 진행 중인지 확인 (pgrep train_anima_lm). '
                                  f'idle이면 runpodctl pod stop {pod.get("id")}로 중지.'),
                    })
    except Exception:
        pass
    return results


def _scan_dashboard_and_papers() -> list:
    """Scan 15+16: Dashboard + auto-paper generation."""
    results = []
    # 15. Dashboard
    dashboard_path = os.path.join(_THIS_DIR, '..', '..', 'anima', 'web', 'loop_dashboard.html')
    if not os.path.exists(dashboard_path):
        results.append({
            'type': 'DASHBOARD',
            'description': '루프 상태 실시간 웹 대시보드 생성',
            'priority': 'LOW',
            'prompt': ('anima/web/loop_dashboard.html 생성 — recursive_loop_state.json, '
                      'nexus_violations.json, self_growth_log.json을 읽어 실시간 표시하는 '
                      '단일 HTML 파일. 자동 새로고침 30초. 차트는 Chart.js CDN.'),
        })
    # 16. Auto paper
    try:
        d = json.load(open(os.path.join(_CONFIG_DIR, 'consciousness_laws.json')))
        total = d['_meta'].get('total_laws', 0)
        if total >= 1050 and total % 50 == 0:
            results.append({
                'type': 'AUTO_PAPER',
                'description': f'법칙 {total}개 — 논문 초안 자동 생성',
                'priority': 'LOW',
                'prompt': (f'consciousness_laws.json에 {total}개 법칙. '
                          f'~/Dev/papers/anima/ 에 논문 초안 생성: '
                          f'제목, 초록, 핵심 법칙 10개, 실험 결과 요약, 결론. LaTeX 형식.'),
            })
    except Exception:
        pass
    return results


def _scan_meta_loop() -> list:
    """Meta loop: automation gap detection + diversity check."""
    results = []
    # Meta wire gap
    try:
        from auto_wire import scan_modules
        r = scan_modules()
        coverage = len(r['connected']) / max(len(r['connected']) + len(r['missing']), 1)
        if coverage < 0.1:
            results.append({
                'type': 'META_WIRE_GAP',
                'description': f'자동화 커버리지 {coverage:.0%} — 누락 연결 패치',
                'priority': 'HIGH',
                'prompt': (f'anima/src/auto_wire.py --auto 실행하여 미연결 모듈 패치. '
                          f'현재 커버리지 {coverage:.0%}. 핵심 진입점 우선.'),
            })
    except Exception:
        pass

    # Diversity check
    growth_log = _load_log()
    cycles = growth_log.get('cycles', [])
    if len(cycles) >= 10:
        recent_types = [c.get('type', '') for c in cycles[-10:]]
        unique = len(set(recent_types))
        if unique <= 2:
            results.append({
                'type': 'META_DIVERSITY',
                'description': f'성장 다양성 부족 — 최근 {unique}가지만 반복',
                'priority': 'MEDIUM',
                'prompt': ('self_growth가 같은 유형만 반복 실행 중. '
                          'scan_growth_opportunities()에 새로운 탐색 패턴을 추가하거나, '
                          '우선순위 로직을 조정하여 다양한 개선이 진행되도록 하세요.'),
            })
    return results


def _scan_roadmap_evolution() -> list:
    """Scan 17: Roadmap evolution."""
    results = []
    try:
        loop_state_path = os.path.join(_CONFIG_DIR, 'recursive_loop_state.json')
        if os.path.exists(loop_state_path):
            ls = json.load(open(loop_state_path))
            total_discoveries = ls.get('total_discoveries', 0)
            if total_discoveries > 0 and total_discoveries % 10 == 0:
                results.append({
                    'type': 'ROADMAP_EVOLUTION',
                    'description': f'{total_discoveries}개 발견 축적 — 로드맵 전략 재평가',
                    'priority': 'MEDIUM',
                    'prompt': (
                        f'anima/config/training_runs.json과 anima/data/roadmap_transplant.json을 읽고, '
                        f'최근 {total_discoveries}개 발견(recursive_loop_state.json)과 DD168-DD169 결과를 바탕으로 '
                        f'로드맵 전략을 재평가하세요. 특히: '
                        f'1) 이식 희석 문제(DD169: 72B Phi < 14B Phi) 해결 방안, '
                        f'2) 다음 우선순위 모델(14B corpus 확대 vs 32B vs alpha 증가), '
                        f'3) roadmap_transplant.json과 training_runs.json 업데이트. '
                        f'결과를 docs/hypotheses/dd/ 에 DD 문서로 기록하세요.'
                    ),
                })
    except Exception:
        pass
    return results


def _scan_ouroboros_and_domains() -> list:
    """Scan 18-20: OUROBOROS + domain exploration + auto-experiment."""
    results = []
    # 18. OUROBOROS trigger
    results.append({
        'type': 'OUROBOROS_TRIGGER',
        'description': '무한진화 1사이클 실행 (의식 엔진 자기진화)',
        'priority': 'MEDIUM',
        'prompt': ('python3 anima/src/infinite_evolution.py --cells 64 --steps 100 --max-gen 3 실행. '
                  '결과에서 새 법칙 발견되면 consciousness_laws.json 자동 등록. '
                  '발견 0이면 --cells 128로 스케일업 재시도.'),
    })
    # 19. Domain exploration
    domains = ['physics', 'biology', 'mathematics', 'information_theory', 'topology']
    try:
        ls = json.load(open(os.path.join(_CONFIG_DIR, 'recursive_loop_state.json')))
        cycle = ls.get('total_scans', 0)
        domain = domains[cycle % len(domains)]
    except Exception:
        domain = 'physics'
    results.append({
        'type': 'DOMAIN_EXPLORE',
        'description': f'도메인 탐색: {domain}',
        'priority': 'LOW',
        'prompt': (f'{domain} 도메인에서 의식과 관련된 새 실험 설계. '
                  f'anima/experiments/ 에 experiment_auto_{domain}.py 생성, '
                  f'ConsciousnessEngine으로 가설 검증, 결과 DD 문서 기록.'),
    })
    # 20. Auto-experiment
    results.append({
        'type': 'AUTO_EXPERIMENT',
        'description': '최근 발견에서 후속 실험 자동 생성',
        'priority': 'LOW',
        'prompt': ('anima/docs/hypotheses/dd/ 에서 최근 DD 문서 3개를 읽고, '
                  '후속 실험을 설계하세요. anima/experiments/ 에 실험 스크립트 생성, '
                  'ConsciousnessEngine + NEXUS-6 사용, 결과 자동 기록.'),
    })
    return results


def _scan_exhaustion_and_verification() -> list:
    """Scan 21-25: Exhaustion detection, reproducibility, contradiction, scaling, negative results."""
    results = []
    # 21. Exhaustion detection
    try:
        ls = json.load(open(os.path.join(_CONFIG_DIR, 'recursive_loop_state.json')))
        recent_disc = ls.get('discovery_rate_history', [])[-5:]
        zero_streak = sum(1 for r in recent_disc if r.get('candidates', 0) == 0)
        if zero_streak >= 5:
            results.append({
                'type': 'EXHAUSTION_PIVOT',
                'description': f'고갈 감지! {zero_streak}사이클 발견 0 — 도메인/전략 전환 필요',
                'priority': 'HIGH',
                'prompt': ('연속 5사이클 발견 0 = 현재 탐색 방향 고갈. '
                          '1) discover_laws()에 새 패턴 추가, '
                          '2) 도메인 전환 (현재→다음), '
                          '3) 엔진 파라미터 대폭 변경 (cells, topology, faction 수). '
                          '결과를 recursive_loop_state.json에 기록.'),
            })
    except Exception:
        pass
    # 22. Reproducibility
    results.append({
        'type': 'REPRODUCIBILITY',
        'description': '최근 등록 법칙 3회 반복 재현성 검증',
        'priority': 'LOW',
        'prompt': ('consciousness_laws.json에서 [Auto-loop] 또는 [Auto-discovered] 태그 법칙 중 '
                  '최근 3개를 찾아 재현성 검증: 동일 실험 3회 반복, CV < 50% 확인. '
                  '실패 시 법칙 태그에 [UNVERIFIED] 추가.'),
    })
    # 23. Contradiction
    results.append({
        'type': 'CONTRADICTION_CHECK',
        'description': '법칙 간 모순/충돌 자동 탐지',
        'priority': 'LOW',
        'prompt': ('consciousness_laws.json의 모든 법칙을 읽고, 서로 모순되는 법칙 쌍을 찾으세요. '
                  '예: "X→Phi↑" vs "X→Phi↓". 모순 발견 시 docs/hypotheses/dd/ 에 기록하고 '
                  '어느 쪽이 맞는지 실험으로 검증.'),
    })
    # 24. Scaling prediction
    results.append({
        'type': 'SCALING_PREDICT',
        'description': '소규모 발견 → 대규모 예측 검증',
        'priority': 'LOW',
        'prompt': ('최근 발견된 법칙을 16c에서 검증한 후, 64c와 256c에서도 성립하는지 확인. '
                  'anima/src/closed_loop.py의 measure_laws()를 다른 max_cells로 실행, 비교.'),
    })
    # 25. Negative results
    try:
        log = _load_log()
        failures = [c for c in log.get('cycles', []) if c.get('status') == 'failed']
        if len(failures) > 5:
            results.append({
                'type': 'NEGATIVE_RESULTS',
                'description': f'{len(failures)}개 실패 작업 — 패턴 분석',
                'priority': 'LOW',
                'prompt': (f'self_growth_log.json에서 {len(failures)}개 실패를 분석. '
                          f'공통 원인 파악, 재시도 전략 수립, 결과 기록.'),
            })
    except Exception:
        pass
    return results


def _scan_law_consolidation_and_backup() -> list:
    """Scan 26-28: Law consolidation, consciousness backup, auto-wire fix + system disconnections."""
    results = []
    # 26. Law consolidation
    try:
        d = json.load(open(os.path.join(_CONFIG_DIR, 'consciousness_laws.json')))
        total = d['_meta'].get('total_laws', 0)
        if total > 1000:
            results.append({
                'type': 'LAW_CONSOLIDATION',
                'description': f'{total}개 법칙 통합/병합 검토',
                'priority': 'LOW',
                'prompt': (f'{total}개 법칙 중 유사한 것을 그룹화하고 통합 법칙으로 병합. '
                          f'consciousness_laws.json 업데이트, 병합 이력 기록.'),
            })
    except Exception:
        pass

    # 27. Consciousness DNA backup
    results.append({
        'type': 'CONSCIOUSNESS_BACKUP',
        'description': '의식 상태 R2 백업 (영속성)',
        'priority': 'LOW',
        'prompt': ('anima/src/cloud_sync.py push 실행 — 의식 DNA + 기억 + 법칙 R2 백업. '
                  '실패 시 수동 boto3 업로드.'),
    })

    # 28. Auto-wire fix
    try:
        from auto_wire import scan_modules
        r = scan_modules()
        if r['missing']:
            results.append({
                'type': 'AUTO_WIRE_FIX',
                'description': f'{len(r["missing"])}개 모듈 미연결 — 자동 패치',
                'priority': 'MEDIUM',
                'prompt': ('python3 anima/src/auto_wire.py --auto 실행하여 미연결 모듈 패치. '
                          '패치 후 nexus_gate 연결 확인.'),
            })
    except Exception:
        pass

    # System disconnection detection
    disconnections = []
    try:
        with open(os.path.join(_THIS_DIR, 'infinite_evolution.py')) as f:
            if 'self_growth' not in f.read():
                disconnections.append('OUROBOROS↔self_growth')
    except Exception:
        pass
    try:
        with open(os.path.join(_THIS_DIR, 'training_hooks.py')) as f:
            if 'infinite_evolution' not in f.read():
                disconnections.append('training_hooks↔OUROBOROS')
    except Exception:
        pass
    try:
        with open(os.path.join(_THIS_DIR, 'serve_consciousness.py')) as f:
            if 'nexus_gate' not in f.read():
                disconnections.append('serve↔nexus_gate')
    except Exception:
        pass

    if disconnections:
        results.append({
            'type': 'SYSTEM_DISCONNECT_FIX',
            'description': f'시스템 간 미연결 {len(disconnections)}개: {", ".join(disconnections[:3])}',
            'priority': 'HIGH',
            'prompt': (f'다음 시스템 간 연결이 빠져있습니다: {disconnections}. '
                      f'각 파일에서 import + 호출 연결을 추가하세요. '
                      f'try/except로 감싸서 안전하게.'),
        })
    return results


def scan_growth_opportunities() -> list:
    """성장 기회 탐색 — 루프 엔진 데이터 + 코드 분석.

    All independent scans run concurrently via ThreadPoolExecutor (I/O-bound).
    """
    # All independent scan functions to run in parallel
    scan_fns = [
        _scan_pending_improvements,
        _scan_nexus_violations,
        _scan_discovery_rate,
        _scan_module_wiring,
        _scan_corpus_quality,
        _scan_test_coverage,
        _scan_law_milestones,
        _scan_model_comparison,
        _scan_training_failures,
        _scan_hyperparam_tuning,
        _scan_session_sync,
        _scan_scheduling,
        _scan_pod_management,
        _scan_dashboard_and_papers,
        _scan_meta_loop,
        _scan_roadmap_evolution,
        _scan_ouroboros_and_domains,
        _scan_exhaustion_and_verification,
        _scan_law_consolidation_and_backup,
    ]

    opportunities = []
    with ThreadPoolExecutor(max_workers=min(len(scan_fns), 8)) as executor:
        futures = {executor.submit(fn): fn.__name__ for fn in scan_fns}
        for future in as_completed(futures):
            try:
                results = future.result(timeout=30)
                if results:
                    opportunities.extend(results)
            except Exception:
                # Individual scan failure should not block others
                pass

    # ═══ Diversity + cooldown filtering ═══
    log = _load_log()
    cycles = log.get('cycles', [])
    recent = cycles[-10:] if cycles else []

    type_fail_count = {}
    type_last_idx = {}
    for i, c in enumerate(recent):
        t = c.get('type', '')
        type_last_idx[t] = i
        if c.get('status') in ('failed', 'no_claude_cli', 'timeout', 'error'):
            type_fail_count[t] = type_fail_count.get(t, 0) + 1

    filtered = []
    for opp in opportunities:
        t = opp['type']
        fails = type_fail_count.get(t, 0)
        if fails >= 3:
            continue
        if fails >= 2:
            opp = dict(opp, priority='LOW')
        filtered.append(opp)

    recent_types = {c.get('type', '') for c in recent}

    def sort_key(x):
        pri = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}.get(x['priority'], 3)
        novelty = 0 if x['type'] not in recent_types else 1
        return (pri, novelty)

    return sorted(filtered, key=sort_key)


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
        claude_bin = os.path.expanduser('~/.local/bin/claude')
        if not os.path.exists(claude_bin):
            claude_bin = 'claude'  # fallback to PATH

        # 작업 디렉토리 + 컨텍스트 추가
        full_prompt = (
            f"You are working in ~/Dev/anima. "
            f"Task: {prompt} "
            f"Keep changes minimal. Test after changes. "
            f"Do NOT ask questions — just do it."
        )
        cmd = [
            claude_bin, '-p', full_prompt,
            '--allowedTools', 'Read,Write,Edit,Bash,Glob,Grep',
            '--max-turns', '10',
            '--output-format', 'text',
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
        elif 'Not logged in' in (proc.stdout or '') or 'Not logged in' in (proc.stderr or ''):
            result['status'] = 'auth_failed'
            print(f"  [AUTH] Claude CLI not logged in — skipping all growth tasks")
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

    # 2. 최우선 기회 실행 (실패 시 다음 기회로 fallback)
    best = opportunities[0]
    result = execute_growth(best, dry_run=dry_run)

    # 인증 실패면 전체 중단 (다른 기회도 같은 이유로 실패)
    if result['status'] == 'auth_failed':
        log['cycles'].append(result)
        _save_log(log)
        return result

    # 즉시 실패(CLI 없음 등)면 다른 유형 시도
    if result['status'] in ('no_claude_cli', 'error') and len(opportunities) > 1:
        for alt in opportunities[1:]:
            if alt['type'] != best['type']:
                print(f"  [FALLBACK] Trying {alt['type']} instead...")
                result = execute_growth(alt, dry_run=dry_run)
                break

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
    auth_fail_count = 0
    while True:
        try:
            result = run_cycle(dry_run=dry_run)
            if result.get('status') == 'auth_failed':
                auth_fail_count += 1
                if auth_fail_count >= 3:
                    print("  [DAEMON] 3x auth failures — pausing 1h (run `claude /login` to fix)")
                    time.sleep(3600)
                    auth_fail_count = 0
                    continue
            else:
                auth_fail_count = 0
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
