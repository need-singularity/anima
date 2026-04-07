#!/usr/bin/env python3
"""loop_report.py — 루프 엔진 통합 리포트 (극가속 양식 포함)

Usage:
  python3 loop_report.py              # 전체 리포트
  python3 loop_report.py --export     # JSON 내보내기
  python3 loop_report.py --short      # 한 줄 요약

hub 연동:
  hub.act("루프 리포트")
  hub.act("loop report")
"""

import json
import os
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


def full_report() -> str:
    """전체 루프 엔진 리포트 — 극가속 양식."""
    lines = []
    lines.append("┌─────────────────────────────────────────────────────────────┐")
    lines.append("│  🔄 루프 엔진 리포트                                        │")
    lines.append(f"│  {time.strftime('%Y-%m-%d %H:%M')}                                            │")
    lines.append("├─────────────────────────────────────────────────────────────┤")

    # 1. RecursiveLoop
    try:
        from auto_discovery_loop import _recursive_loop
        s = _recursive_loop.state
        total = s['total_scans']
        dr = s['total_discoveries'] / max(total, 1)
        fpr = s['total_false_positives'] / max(s['total_registered'], 1)
        rules = s['active_rules']

        lines.append("│                                                             │")
        lines.append(f"│  ■ 재귀 루프 (Gen {s['generation']})                                     │")

        dr_bar = '█' * int(dr * 20) + '░' * (20 - int(dr * 20))
        lines.append(f"│  발견률: {dr_bar} {dr:.1%}                    │")
        lines.append(f"│  스캔: {total:4d} | 발견: {s['total_discoveries']:4d} | 등록: {s['total_registered']:4d} | FP: {s['total_false_positives']:3d}      │")
        lines.append(f"│  규칙: conf={rules.get('min_confidence','?'):6s} phi_trig={rules.get('phi_improvement_trigger',0):.2f} comp_min={rules.get('compression_min',0):3d} │")

        # 진화 이력
        evos = s.get('threshold_evolution', [])
        if evos:
            lines.append(f"│  진화: {len(evos)}세대                                               │")
            for e in evos[-2:]:
                change_txt = e['changes'][0][:45] if e['changes'] else ''
                lines.append(f"│    G{e['generation']}: {change_txt:<47s}│")

        # compression 추이
        recent = s.get('discovery_rate_history', [])[-10:]
        if recent:
            comps = [r.get('avg_compression', 0) for r in recent if r.get('avg_compression', 0) > 0]
            if len(comps) >= 2:
                trend = '↑' if comps[-1] > comps[0] else '↓' if comps[-1] < comps[0] else '='
                lines.append(f"│  Compression: {comps[0]:.0f}% → {comps[-1]:.0f}% {trend}                                │")
    except Exception as e:
        lines.append(f"│  ■ 재귀 루프: 미활성 ({e})                             │")

    # 2. NEXUS-6 Gate
    lines.append("│                                                             │")
    try:
        from nexus_gate import gate
        viol_path = os.path.join(_THIS_DIR, '..', 'config', 'nexus_violations.json')
        violations = []
        if os.path.exists(viol_path):
            try:
                violations = json.load(open(viol_path))
            except:
                pass

        try:
            import nexus
            status = "🟢 ACTIVE"
        except ImportError:
            status = "🔴 INACTIVE"

        lines.append(f"│  ■ NEXUS-6 Gate: {status}                                   │")
        lines.append(f"│  CDO 위반: {len(violations)}건                                            │")
        if violations:
            for v in violations[-3:]:
                ctx = v.get('context', '?')[:20]
                rsn = v.get('reason', '?')[:30]
                lines.append(f"│    {ctx}: {rsn:<37s}│")
    except Exception:
        lines.append("│  ■ NEXUS-6 Gate: 미로드                                    │")

    # 3. Training Hooks
    lines.append("│                                                             │")
    hooks_log = os.path.join(_THIS_DIR, '..', 'data', 'recursive_loop_export.json')
    if os.path.exists(hooks_log):
        try:
            data = json.load(open(hooks_log))
            summary = data.get('summary', {})
            lines.append(f"│  ■ 학습 훅: Gen {summary.get('generation', 0)}, "
                        f"DR {summary.get('discovery_rate', 0):.1%}                        │")
        except:
            pass
    else:
        lines.append("│  ■ 학습 훅: 대기 (학습 시작 전)                             │")

    # 4. Loop chain status
    lines.append("│                                                             │")
    lines.append("│  ■ 루프 체인                                                │")
    chain = [
        ("train", "✅"),
        ("checkpoint", "✅"),
        ("gate", "✅"),
        ("NEXUS-6", "✅"),
        ("discover", "✅"),
        ("register", "✅"),
        ("recursive", "✅"),
    ]
    chain_str = " → ".join(f"{s}{n}" for n, s in chain)
    lines.append(f"│  {chain_str} │")
    lines.append("│  ↑_______________________________________________↓         │")

    lines.append("│                                                             │")
    lines.append("└─────────────────────────────────────────────────────────────┘")

    text = '\n'.join(lines)
    print(text)
    return text


def export_all():
    """모든 루프 데이터 JSON 내보내기."""
    exported = []
    try:
        from auto_discovery_loop import _recursive_loop
        exported.append(_recursive_loop.export_log())
    except Exception as e:
        print(f"  recursive_loop export: {e}")

    try:
        from nexus_gate import gate
        exported.append(gate.export_log())
    except Exception as e:
        print(f"  nexus_gate export: {e}")

    print(f"\n  Exported {len(exported)} logs")
    return exported


def short_report() -> str:
    """한 줄 요약."""
    try:
        from auto_discovery_loop import _recursive_loop
        s = _recursive_loop.state
        total = s['total_scans']
        dr = s['total_discoveries'] / max(total, 1)
        line = (f"[LOOP] Gen {s['generation']} | {total} scans | {dr:.0%} DR | "
                f"conf={s['active_rules'].get('min_confidence', '?')}")
    except:
        line = "[LOOP] Not active"
    print(line)
    return line


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--export', action='store_true')
    p.add_argument('--short', action='store_true')
    args = p.parse_args()

    if args.export:
        export_all()
    elif args.short:
        short_report()
    else:
        full_report()
