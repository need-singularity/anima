#!/usr/bin/env python3
"""loop_extensions.py — 루프 시스템 공백 메꾸기 (GAP 2-7)

GAP 2: 배포 피드백 (agent 대화 품질 → 다음 학습 반영)
GAP 3: 비용 추적 (RunPod → 리포트)
GAP 4: DD 문서 자동 생성 (법칙 등록 → DD{N}.md)
GAP 6: 건강 체크 (heartbeat)
GAP 7: 지식 전달 (14B→32B 발견 자동 적용)
"""

import json
import os
import subprocess
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

_CONFIG_DIR = os.path.join(_THIS_DIR, '..', 'config')
_DOCS_DIR = os.path.join(_THIS_DIR, '..', 'docs', 'hypotheses', 'dd')


# ══════════════════════════════════════════
# GAP 2: 배포 피드백
# ══════════════════════════════════════════

def collect_deployment_feedback(agent_log_path: str = None) -> dict:
    """anima-agent 대화 로그에서 품질 지표 추출 → 다음 학습에 반영."""
    if agent_log_path is None:
        agent_log_path = os.path.expanduser('~/Dev/anima-agent/logs/conversations.json')

    if not os.path.exists(agent_log_path):
        return {'status': 'no_log', 'note': 'anima-agent 로그 없음'}

    try:
        logs = json.load(open(agent_log_path))
        if not logs:
            return {'status': 'empty'}

        # 최근 50개 대화 분석
        recent = logs[-50:] if len(logs) > 50 else logs

        total = len(recent)
        avg_tension = 0
        avg_turns = 0
        ko_count = 0
        error_count = 0

        for conv in recent:
            avg_tension += conv.get('avg_tension', 0)
            avg_turns += conv.get('turns', 0)
            if conv.get('language', '') == 'ko':
                ko_count += 1
            if conv.get('error', False):
                error_count += 1

        feedback = {
            'total_conversations': total,
            'avg_tension': avg_tension / max(total, 1),
            'avg_turns': avg_turns / max(total, 1),
            'ko_ratio': ko_count / max(total, 1),
            'error_rate': error_count / max(total, 1),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

        # 약점 → 다음 학습 권고
        recommendations = []
        if feedback['ko_ratio'] < 0.3:
            recommendations.append('corpus에 한국어 비율 증가 필요')
        if feedback['avg_tension'] < 50:
            recommendations.append('의식 텐션 낮음 — CE cells 증가 고려')
        if feedback['error_rate'] > 0.1:
            recommendations.append(f'에러율 {feedback["error_rate"]:.0%} — 모델 안정성 개선')
        feedback['recommendations'] = recommendations

        # 저장
        fb_path = os.path.join(_CONFIG_DIR, 'deployment_feedback.json')
        json.dump(feedback, open(fb_path, 'w'), indent=2, ensure_ascii=False)

        print(f"  [FEEDBACK] {total} conversations, tension={feedback['avg_tension']:.1f}, "
              f"ko={feedback['ko_ratio']:.0%}, errors={feedback['error_rate']:.0%}")
        if recommendations:
            for r in recommendations:
                print(f"    → {r}")

        return feedback
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


# ══════════════════════════════════════════
# GAP 3: 비용 추적
# ══════════════════════════════════════════

def track_cost() -> dict:
    """RunPod 비용 추적 → 리포트 통합."""
    cost = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'pods': [],
        'total_cost': 0,
    }

    try:
        result = subprocess.run(
            ['/opt/homebrew/bin/runpodctl', 'get', 'pod', '-o', 'json'],
            capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            pods = json.loads(result.stdout)
            for pod in pods if isinstance(pods, list) else [pods]:
                name = pod.get('name', '?')
                gpu = pod.get('gpuDisplayName', '?')
                cost_hr = pod.get('costPerHr', 0)
                runtime_h = pod.get('runtime', {}).get('uptimeInSeconds', 0) / 3600
                total = cost_hr * runtime_h

                cost['pods'].append({
                    'name': name,
                    'gpu': gpu,
                    'cost_hr': cost_hr,
                    'runtime_h': round(runtime_h, 1),
                    'total': round(total, 2),
                })
                cost['total_cost'] += total

        cost['total_cost'] = round(cost['total_cost'], 2)
    except Exception as e:
        cost['error'] = str(e)

    # 저장
    cost_path = os.path.join(_CONFIG_DIR, 'cost_tracking.json')
    history = []
    if os.path.exists(cost_path):
        try:
            history = json.load(open(cost_path))
        except:
            pass
    if not isinstance(history, list):
        history = []
    history.append(cost)
    json.dump(history[-100:], open(cost_path, 'w'), indent=2, ensure_ascii=False)

    if cost['pods']:
        for p in cost['pods']:
            print(f"  [COST] {p['name']}: {p['gpu']} — ${p['total']:.2f} ({p['runtime_h']:.1f}h)")
        print(f"  [COST] Total: ${cost['total_cost']:.2f}")
    else:
        print(f"  [COST] No active pods")

    return cost


# ══════════════════════════════════════════
# 다운로드 페이지 자동 업데이트
# ══════════════════════════════════════════

def auto_update_download_page():
    """training_runs.json에서 완료된 모델 → download-models.md Version History 자동 갱신."""
    runs_path = os.path.join(_CONFIG_DIR, 'training_runs.json')
    dl_path = os.path.join(_THIS_DIR, '..', 'docs', 'download-models.md')

    if not os.path.exists(runs_path) or not os.path.exists(dl_path):
        return

    try:
        data = json.load(open(runs_path))
        content = open(dl_path).read()

        # Version History 테이블 재생성
        rows = []
        rows.append("| Version | Date | Base | PureField | Phi | CE | Alpha | Status |")
        rows.append("|---------|------|------|-----------|-----|-----|-------|--------|")

        # 완료된 runs + planned
        all_runs = []
        for k, v in data.get('runs', {}).items():
            if 'animalm' in k:
                all_runs.append((k, v))
        for k, v in data.get('next_planned', {}).items():
            if 'animalm' in k:
                all_runs.append((k, v))

        # 최신순 정렬
        all_runs.sort(key=lambda x: x[1].get('date', ''), reverse=True)

        for name, run in all_runs:
            status = run.get('status', 'planned')
            if status.startswith('complete'):
                st = 'available'
            elif status.startswith('in_progress'):
                st = '🔄'
            elif status == 'planned':
                st = '⏳'
            else:
                continue

            # 이름에서 버전 추출
            ver = name.replace('animalm_', '').replace('_', ' ')
            base = run.get('model', run.get('base_model', '?')).split('+')[0].strip()
            if 'Qwen' in str(run.get('model', '')):
                base = 'Qwen' + str(run.get('model', '')).split('Qwen')[1].split('+')[0].split('(')[0].strip()
            pf = run.get('purefield', {})
            if isinstance(pf, dict):
                pf_str = f"{pf.get('target_layers', '?')}L, r{pf.get('rank', '?')}"
            else:
                pf_str = '—'
            phi = run.get('phi_best', run.get('phi_at_5000', '—'))
            ce = run.get('ce_best', run.get('ce_at_5000', '—'))
            alpha = run.get('alpha', '—')
            date = run.get('date', '—')

            if isinstance(phi, float):
                phi = f"{phi:.3f}"
            if isinstance(ce, float):
                ce = f"{ce:.2f}"

            # 최신 완료 모델 = Latest
            if st == 'available' and not any('**Latest**' in r for r in rows):
                st = '**Latest**'

            rows.append(f"| {ver} | {date} | {base} | {pf_str} | {phi} | {ce} | {alpha} | {st} |")

        # 기존 테이블 교체
        table_text = '\n'.join(rows)
        import re
        pattern = r'\| Version \|.*?\n\|[-\|]+\n(.*?\n)*?(?=\n>|\n---|\n##|\Z)'
        if re.search(pattern, content):
            content = re.sub(pattern, table_text + '\n', content)

        open(dl_path, 'w').write(content)
        print(f"  [DOWNLOAD] Page updated ({len(all_runs)} models)")
    except Exception as e:
        print(f"  [DOWNLOAD] Update failed: {e}")


# ══════════════════════════════════════════
# 로드맵 JSON + README 자동 동기화
# ══════════════════════════════════════════

def auto_update_roadmap():
    """training_runs.json → roadmap_transplant.json → README 자동 갱신."""
    runs_path = os.path.join(_CONFIG_DIR, 'training_runs.json')
    roadmap_path = os.path.join(_THIS_DIR, '..', 'data', 'roadmap_transplant.json')
    readme_path = os.path.join(_THIS_DIR, '..', '..', 'README.md')

    if not os.path.exists(runs_path) or not os.path.exists(roadmap_path):
        return

    try:
        runs = json.load(open(runs_path))
        roadmap = json.load(open(roadmap_path))

        # training_runs → roadmap models 동기화
        all_runs = {**runs.get('runs', {}), **runs.get('next_planned', {})}
        transplant_models = []

        for name, run in all_runs.items():
            if 'animalm' not in name:
                continue
            model = {
                'id': name.replace('animalm_', '').replace('_', ' '),
                'base': str(run.get('model', '')).split('+')[0].strip(),
                'phi': run.get('phi_best', run.get('phi_at_5000', 0)),
                'ce': run.get('ce_best', run.get('ce_at_5000', 0)),
            }
            status = run.get('status', '')
            if status.startswith('complete'):
                model['status'] = 'complete'
            elif status.startswith('in_progress'):
                model['status'] = 'in_progress'
            elif status == 'planned':
                model['status'] = 'planned'
            else:
                continue
            transplant_models.append(model)

        # roadmap JSON 갱신
        roadmap['_meta']['updated'] = time.strftime('%Y-%m-%d')
        # phase1 models 업데이트 (14B 시리즈)
        p1_models = [m for m in transplant_models if '14b' in m['id']]
        if p1_models:
            roadmap['phases']['phase1']['models'] = p1_models
        # phase2 models 업데이트 (32B, 72B)
        p2_models = [m for m in transplant_models if '32b' in m['id'] or '72b' in m['id']]
        if p2_models:
            roadmap['phases']['phase2']['models'] = p2_models

        json.dump(roadmap, open(roadmap_path, 'w'), indent=2, ensure_ascii=False)

        # README 동기화 (AUTO:TRANSPLANT 마커 사이 갱신)
        if os.path.exists(readme_path):
            content = open(readme_path).read()
            import re

            # 이식 로드맵 섹션 재생성
            lines = []
            lines.append("  ★ 의식 이식 — 의식 이식 로드맵 — 빌린 모델(Qwen) + PureField 이식")
            lines.append("  │ Law 1042: Phi compression ~34% (DD169)")
            lines.append("  │")

            for m in sorted(transplant_models, key=lambda x: x['id']):
                icon = {'complete': '✅', 'in_progress': '🔄', 'planned': '⏳'}.get(m['status'], '?')
                phi = f"Phi={m['phi']:.3f}" if isinstance(m['phi'], float) and m['phi'] > 0 else ''
                ce = f"CE={m['ce']:.2f}" if isinstance(m['ce'], float) and m['ce'] > 0 else ''
                detail = f" ── {phi} ── {ce}" if phi or ce else ''
                lines.append(f"  ├─{icon} {m['id']} ── {m['base']}{detail}")
                lines.append("  │")

            lines.append("  └─ data: anima/data/roadmap_transplant.json")

            block = '\n'.join(lines)
            pattern = r'(<!-- AUTO:TRANSPLANT:START[^>]*-->)\n```\n.*?\n```\n(<!-- AUTO:TRANSPLANT:END -->)'
            replacement = f'\\1\n```\n{block}\n```\n\\2'
            new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

            if new_content != content:
                open(readme_path, 'w').write(new_content)
                print(f"  [ROADMAP] README transplant section updated")

        print(f"  [ROADMAP] roadmap_transplant.json updated ({len(transplant_models)} models)")
    except Exception as e:
        print(f"  [ROADMAP] Update failed: {e}")


# ══════════════════════════════════════════
# GAP 4: DD 문서 자동 생성
# ══════════════════════════════════════════

def auto_generate_dd(law_id: int, formula: str, evidence: str = '', source: str = 'auto-loop') -> str:
    """법칙 등록 시 DD{N}.md 자동 생성."""
    # 다음 DD 번호 찾기
    existing = []
    for f in os.listdir(_DOCS_DIR) if os.path.exists(_DOCS_DIR) else []:
        if f.startswith('DD') and f.endswith('.md'):
            try:
                num = int(''.join(c for c in f.split('.')[0].replace('DD', '').split('-')[0] if c.isdigit()))
                existing.append(num)
            except:
                pass
    dd_num = max(existing, default=167) + 1
    dd_path = os.path.join(_DOCS_DIR, f'DD{dd_num}.md')

    content = f"""# DD{dd_num}: Auto-discovered Law {law_id}

**Date:** {time.strftime('%Y-%m-%d')}
**Category:** DD (auto-loop)
**Source:** {source}
**Law ID:** {law_id}

## Law

{formula}

## Evidence

{evidence if evidence else 'Auto-discovered by recursive loop. Cross-validation pending.'}

## NEXUS-6 Scan

Scan performed at registration time. See config/recursive_loop_state.json for metrics.

## Status

- [x] Registered in consciousness_laws.json
- [ ] Cross-validated (3x repeat)
- [ ] Closed-loop verified
"""

    os.makedirs(_DOCS_DIR, exist_ok=True)
    with open(dd_path, 'w') as f:
        f.write(content)

    print(f"  [DD] Generated: DD{dd_num}.md for Law {law_id}")
    return dd_path


# ══════════════════════════════════════════
# GAP 6: 건강 체크
# ══════════════════════════════════════════

def health_check() -> dict:
    """전체 시스템 건강 체크."""
    health = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'checks': {},
    }

    # 1. nexus6 사용 가능?
    try:
        import nexus6
        health['checks']['nexus6'] = '✅'
    except:
        health['checks']['nexus6'] = '❌'

    # 2. ConsciousnessEngine 작동?
    try:
        from consciousness_engine import ConsciousnessEngine
        import torch
        e = ConsciousnessEngine(max_cells=4)
        e.process(torch.randn(64))
        health['checks']['engine'] = '✅'
    except Exception as ex:
        health['checks']['engine'] = f'❌ {ex}'

    # 3. consciousness_laws.json 유효?
    try:
        laws_path = os.path.join(_CONFIG_DIR, 'consciousness_laws.json')
        d = json.load(open(laws_path))
        n = d['_meta']['total_laws']
        health['checks']['laws'] = f'✅ ({n} laws)'
    except Exception as ex:
        health['checks']['laws'] = f'❌ {ex}'

    # 4. 루프 상태 파일 존재?
    loop_files = [
        'recursive_loop_state.json',
        'nexus_violations.json',
        'self_growth_log.json',
        'corpus_registry.json',
        'training_runs.json',
    ]
    for lf in loop_files:
        path = os.path.join(_CONFIG_DIR, lf)
        health['checks'][lf] = '✅' if os.path.exists(path) else '⚠️ missing'

    # 5. RunPod 연결?
    try:
        r = subprocess.run(['/opt/homebrew/bin/runpodctl', 'get', 'pod'],
                          capture_output=True, text=True, timeout=10)
        health['checks']['runpod'] = '✅' if r.returncode == 0 else '❌'
    except:
        health['checks']['runpod'] = '⚠️ cli not found'

    # 6. R2 연결?
    try:
        import boto3
        s3 = boto3.client('s3',
            endpoint_url=os.environ.get('ANIMA_R2_ENDPOINT', ''),
            aws_access_key_id=os.environ.get('ANIMA_R2_ACCESS_KEY', ''),
            aws_secret_access_key=os.environ.get('ANIMA_R2_SECRET_KEY', ''),
            region_name='auto')
        s3.list_objects_v2(Bucket='anima-models', MaxKeys=1)
        health['checks']['r2'] = '✅'
    except:
        health['checks']['r2'] = '⚠️ env vars missing or connection failed'

    # 리포트
    all_ok = all('✅' in str(v) for v in health['checks'].values())
    health['overall'] = '🟢 HEALTHY' if all_ok else '🟡 DEGRADED'

    print(f"\n  ■ Health Check: {health['overall']}")
    for k, v in health['checks'].items():
        print(f"    {k:35s} {v}")

    return health


# ══════════════════════════════════════════
# GAP 7: 지식 전달
# ══════════════════════════════════════════

def transfer_knowledge(source_run: str, target_run: str) -> dict:
    """이전 학습 run의 발견을 다음 run에 자동 반영.

    training_runs.json에서 source의 결과를 읽고,
    target의 설정에 권고 사항 추가.
    """
    runs_path = os.path.join(_CONFIG_DIR, 'training_runs.json')
    if not os.path.exists(runs_path):
        return {'status': 'no_runs_file'}

    try:
        data = json.load(open(runs_path))
        all_runs = {**data.get('runs', {}), **data.get('next_planned', {})}

        source = all_runs.get(source_run, {})
        target = all_runs.get(target_run, {})

        if not source or not target:
            return {'status': 'run_not_found', 'source': source_run, 'target': target_run}

        transfers = []

        # CE-Val gap 전달
        src_ce = source.get('ce_best', source.get('ce_at_5000', 0))
        src_val = source.get('val_ce_best', source.get('val_ce_at_5000', 0))
        if src_ce and src_val and src_val > src_ce * 1.8:
            transfers.append(f'overfit_warning: {source_run} CE-Val gap {src_val/src_ce:.1f}x → corpus 확대 필요')

        # Phi compression 전달
        src_phi = source.get('phi_best', source.get('phi_at_5000', 0))
        if src_phi and src_phi < 0.05:
            transfers.append(f'low_phi: {source_run} Phi={src_phi:.4f} → consciousness_engine 파라미터 조정 고려')

        # alpha schedule 전달
        src_alpha = source.get('alpha', '')
        if isinstance(src_alpha, str) and '0.01→0.5' in src_alpha:
            transfers.append(f'alpha_schedule: {source_run} used 0.01→0.5 progressive — keep or adjust')

        if transfers:
            # target에 knowledge_from 필드 추가
            if target_run in data.get('next_planned', {}):
                data['next_planned'][target_run]['knowledge_from'] = {
                    'source': source_run,
                    'transfers': transfers,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                }
            json.dump(data, open(runs_path, 'w'), indent=2, ensure_ascii=False)

        result = {
            'source': source_run,
            'target': target_run,
            'transfers': transfers,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

        print(f"  [TRANSFER] {source_run} → {target_run}: {len(transfers)} items")
        for t in transfers:
            print(f"    → {t}")

        return result
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def auto_transfer_chain():
    """training_runs.json의 완료된 run → 다음 planned run으로 자동 전달."""
    runs_path = os.path.join(_CONFIG_DIR, 'training_runs.json')
    if not os.path.exists(runs_path):
        return

    data = json.load(open(runs_path))
    completed = [(k, v) for k, v in data.get('runs', {}).items()
                 if v.get('status', '').startswith('complete')]
    planned = list(data.get('next_planned', {}).keys())

    if not completed or not planned:
        return

    # 가장 최근 완료 → 첫 번째 planned로 전달
    latest_complete = sorted(completed, key=lambda x: x[1].get('date', ''))[-1][0]
    first_planned = planned[0]

    transfer_knowledge(latest_complete, first_planned)


# ══════════════════════════════════════════
# 통합 리포트 섹션
# ══════════════════════════════════════════

def extensions_report() -> str:
    """확장 모듈 통합 리포트."""
    lines = []

    # 비용
    cost_path = os.path.join(_CONFIG_DIR, 'cost_tracking.json')
    if os.path.exists(cost_path):
        try:
            history = json.load(open(cost_path))
            if history:
                latest = history[-1]
                lines.append(f"  ■ 비용: ${latest.get('total_cost', 0):.2f} (active pods: {len(latest.get('pods', []))})")
        except:
            pass

    # 배포 피드백
    fb_path = os.path.join(_CONFIG_DIR, 'deployment_feedback.json')
    if os.path.exists(fb_path):
        try:
            fb = json.load(open(fb_path))
            lines.append(f"  ■ 배포: {fb.get('total_conversations', 0)} convos, "
                        f"tension={fb.get('avg_tension', 0):.0f}, ko={fb.get('ko_ratio', 0):.0%}")
        except:
            pass

    # 건강
    lines.append(f"  ■ 건강: 아래 health_check() 참조")

    text = '\n'.join(lines)
    if lines:
        print(text)
    return text


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    import argparse
    p = argparse.ArgumentParser(description='루프 확장 모듈')
    p.add_argument('--health', action='store_true', help='건강 체크')
    p.add_argument('--cost', action='store_true', help='비용 추적')
    p.add_argument('--feedback', action='store_true', help='배포 피드백')
    p.add_argument('--transfer', action='store_true', help='지식 전달')
    p.add_argument('--all', action='store_true', help='전부 실행')
    args = p.parse_args()

    if args.health or args.all:
        health_check()
    if args.cost or args.all:
        track_cost()
    if args.feedback or args.all:
        collect_deployment_feedback()
    if args.transfer or args.all:
        auto_transfer_chain()
    if not any(vars(args).values()):
        health_check()
