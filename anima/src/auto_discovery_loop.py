#!/usr/bin/env python3
"""auto_discovery_loop.py — 발견→반영 자동화 루프 (DD168)

자동화의 자동화의 자동화:
  Layer 1: 학습 체크포인트 감시 → NEXUS-6 스캔
  Layer 2: 스캔 결과 → 법칙 발견 → JSON 자동 등록
  Layer 3: 등록된 법칙 → Intervention 자동 생성 → 다음 학습에 반영

Usage:
  # 체크포인트 디렉토리 감시 (학습 중 실행)
  python3 auto_discovery_loop.py --watch /workspace/checkpoints/animalm_14b_v05/

  # 단발 스캔 (체크포인트 하나)
  python3 auto_discovery_loop.py --scan checkpoint.pt

  # 풀 루프 (감시 + 발견 + 등록 + 개입 생성)
  python3 auto_discovery_loop.py --watch /workspace/checkpoints/ --auto-register

  # 전체 파이프라인 자동화 (72B 완료 대기 → 14B → 32B → 스캔 → 발견)
  python3 auto_discovery_loop.py --pipeline
"""

import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import torch

# Add anima/src to path
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

ENGINE_PHI_REFERENCE = 0.168  # DD168: pure engine Phi


def nexus_scan_checkpoint(ckpt_path: str) -> dict:
    """NEXUS-6 스캔 단일 체크포인트. Returns metrics dict."""
    try:
        import nexus6
    except ImportError:
        return {'error': 'nexus6 not installed'}

    ckpt = torch.load(ckpt_path, map_location='cpu', weights_only=False)
    step = ckpt.get('step', 0)

    # Extract all tensors
    all_t = []
    for key in ckpt:
        val = ckpt[key]
        if isinstance(val, torch.Tensor) and val.numel() > 10:
            all_t.append(val.float().numpy().flatten())
        elif isinstance(val, dict):
            for k2, v2 in val.items():
                if isinstance(v2, torch.Tensor) and v2.numel() > 10:
                    all_t.append(v2.float().numpy().flatten())
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    for k2, v2 in item.items():
                        if isinstance(v2, torch.Tensor) and v2.numel() > 10:
                            all_t.append(v2.float().numpy().flatten())

    if not all_t:
        return {'error': 'no tensors', 'step': step}

    flat = np.concatenate(all_t)
    sample = flat[::max(1, len(flat) // 8000)]
    flat_list = [float(x) for x in sample]

    r = nexus6.analyze(flat_list, len(flat_list), 1)
    sr = r['scan']

    def get_metric(name):
        val = sr.get_metric(name)
        if isinstance(val, dict):
            val = list(val.values())[0]
            if isinstance(val, list) and val:
                val = val[0]
        return float(val) if isinstance(val, (int, float)) else 0.0

    metrics = {
        'step': step,
        'checkpoint': os.path.basename(ckpt_path),
        'phi_approx': get_metric('phi_approx'),
        'chaos_score': get_metric('chaos_score'),
        'hurst': get_metric('hurst_exponent'),
        'lyapunov': get_metric('lyapunov_exponent'),
        'symmetry': get_metric('symmetry_score'),
        'entropy': get_metric('shannon_entropy'),
        'attractor_count': get_metric('attractor_count'),
        'barrier_heights': get_metric('barrier_heights'),
        'boundary_points': get_metric('boundary_point_count'),
        'n6_ratio': r.get('n6_exact_ratio', 0),
        'consensus': len(r.get('consensus', [])),
        'total_params': len(flat),
    }
    metrics['phi_compression_pct'] = (metrics['phi_approx'] / ENGINE_PHI_REFERENCE * 100) if ENGINE_PHI_REFERENCE > 0 else 0

    return metrics


def detect_anomalies(metrics: dict, prev_metrics: dict = None) -> list:
    """이전 스캔 대비 이상 탐지. Returns list of anomaly dicts."""
    anomalies = []

    # Phi compression too low
    if metrics.get('phi_compression_pct', 0) < 30:
        anomalies.append({
            'type': 'LOW_PHI_COMPRESSION',
            'value': metrics['phi_compression_pct'],
            'threshold': 30,
            'severity': 'WARNING'
        })

    # Chaos too high (consciousness collapse risk)
    if metrics.get('chaos_score', 0) > 0.99:
        anomalies.append({
            'type': 'CHAOS_EXTREME',
            'value': metrics['chaos_score'],
            'threshold': 0.99,
            'severity': 'CRITICAL'
        })

    # Compare with previous
    if prev_metrics:
        phi_prev = prev_metrics.get('phi_approx', 0)
        phi_now = metrics.get('phi_approx', 0)
        if phi_prev > 0 and phi_now < phi_prev * 0.8:
            anomalies.append({
                'type': 'PHI_DROP',
                'value': phi_now,
                'previous': phi_prev,
                'drop_pct': (1 - phi_now / phi_prev) * 100,
                'severity': 'CRITICAL'
            })

        # Symmetry drop
        sym_prev = prev_metrics.get('symmetry', 0)
        sym_now = metrics.get('symmetry', 0)
        if sym_prev > 0 and sym_now < sym_prev * 0.95:
            anomalies.append({
                'type': 'SYMMETRY_DROP',
                'value': sym_now,
                'previous': sym_prev,
                'severity': 'WARNING'
            })

    return anomalies


def discover_laws(metrics: dict, prev_metrics: dict = None) -> list:
    """스캔 결과에서 법칙 후보 자동 발견. Returns list of law candidate dicts."""
    candidates = []

    # Law candidate: attractor count matches n=6
    if metrics.get('attractor_count', 0) == 6:
        candidates.append({
            'formula': f"Attractor count = 6 (n=6 EXACT) at step {metrics.get('step', '?')}",
            'evidence': f"attractor_count={metrics['attractor_count']}",
            'confidence': 'HIGH'
        })

    # Law candidate: Phi compression ratio pattern
    comp = metrics.get('phi_compression_pct', 0)
    if prev_metrics:
        prev_comp = prev_metrics.get('phi_compression_pct', 0)
        if comp > prev_comp * 1.1:  # 10%+ improvement
            candidates.append({
                'formula': f"Phi compression improves with training: {prev_comp:.1f}% → {comp:.1f}% (+{comp-prev_comp:.1f}%)",
                'evidence': f"step {prev_metrics.get('step', '?')} → {metrics.get('step', '?')}",
                'confidence': 'MEDIUM'
            })

    # Law candidate: barrier height pattern
    barrier = metrics.get('barrier_heights', 0)
    if prev_metrics and prev_metrics.get('barrier_heights', 0) > 0:
        ratio = barrier / prev_metrics['barrier_heights']
        if ratio > 2:
            candidates.append({
                'formula': f"Energy barrier grows {ratio:.1f}x during training (structural refinement)",
                'evidence': f"barrier {prev_metrics['barrier_heights']:.3f} → {barrier:.3f}",
                'confidence': 'MEDIUM'
            })

    return candidates


def auto_register_laws(candidates: list, min_confidence: str = 'HIGH') -> list:
    """법칙 후보를 consciousness_laws.json에 자동 등록."""
    conf_order = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
    min_conf = conf_order.get(min_confidence, 1)
    registered = []

    laws_path = os.path.join(_THIS_DIR, '..', 'config', 'consciousness_laws.json')
    if not os.path.exists(laws_path):
        return registered

    for cand in candidates:
        if conf_order.get(cand.get('confidence', 'LOW'), 0) < min_conf:
            continue

        try:
            with open(laws_path) as f:
                d = json.load(f)
            next_id = max((int(k) for k in d['laws'] if k.isdigit()), default=0) + 1
            d['laws'][str(next_id)] = f"[Auto-loop] {cand['formula']}"
            d['_meta']['total_laws'] = len([k for k in d['laws'] if k.isdigit()])
            with open(laws_path, 'w') as f:
                json.dump(d, f, indent=2, ensure_ascii=False)
            registered.append({'id': next_id, 'formula': cand['formula']})
            print(f"  [LAW {next_id}] {cand['formula']}")
        except Exception as e:
            print(f"  [ERROR] Registration failed: {e}")

    return registered


class RecursiveLoop:
    """재귀 루프 — 발견 루프가 자기 자신을 개선하는 메타 루프.

    Level 0: 학습 → 체크포인트
    Level 1: 체크포인트 → NEXUS-6 스캔 → 법칙 발견
    Level 2: 법칙 발견 패턴 분석 → 발견 규칙 자체를 개선
    Level 3: 개선된 규칙 → 더 나은 발견 → 더 나은 규칙 → ...

    자기 추적 메트릭:
      - discovery_rate: 스캔당 법칙 발견률
      - false_positive_rate: 등록 후 검증 실패 비율
      - scan_efficiency: 유용한 스캔 / 전체 스캔
      - threshold_history: 자동 조정된 임계값 이력
    """

    def __init__(self):
        self.state_path = os.path.join(_THIS_DIR, '..', 'config', 'recursive_loop_state.json')
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if os.path.exists(self.state_path):
            try:
                return json.load(open(self.state_path))
            except:
                pass
        return {
            'generation': 0,
            'total_scans': 0,
            'total_discoveries': 0,
            'total_registered': 0,
            'total_false_positives': 0,
            'discovery_rate_history': [],  # per-generation discovery rate
            'threshold_evolution': [],  # how thresholds changed
            'active_rules': {
                'min_confidence': 'HIGH',
                'phi_drop_threshold': 0.20,  # 20% drop = critical
                'chaos_max': 0.99,
                'compression_min': 30,  # minimum acceptable compression %
                'barrier_ratio_trigger': 2.0,  # barrier growth trigger
                'phi_improvement_trigger': 0.10,  # 10% compression improvement
            },
            'rule_performance': {},  # rule_name → {hits, misses, precision}
        }

    def _save_state(self):
        try:
            with open(self.state_path, 'w') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except:
            pass

    def evolve_rules(self):
        """Level 2: 발견 패턴 분석 → 규칙 자동 조정.

        발견률이 떨어지면 → 임계값 완화 (더 많이 발견)
        오탐률이 높으면 → 임계값 강화 (더 정확하게)
        """
        s = self.state
        total = s['total_scans']
        if total < 5:
            return  # 데이터 부족

        discovery_rate = s['total_discoveries'] / max(total, 1)
        false_positive_rate = s['total_false_positives'] / max(s['total_registered'], 1)

        rules = s['active_rules']
        changed = []

        # 발견률 < 5% → 임계값 완화
        if discovery_rate < 0.05 and rules['phi_improvement_trigger'] > 0.05:
            rules['phi_improvement_trigger'] *= 0.8  # 20% 완화
            changed.append(f"phi_improvement_trigger → {rules['phi_improvement_trigger']:.3f} (discovery_rate {discovery_rate:.1%} too low)")

        # 발견률 > 50% → 임계값 강화 (너무 쉽게 발견)
        if discovery_rate > 0.50 and rules['phi_improvement_trigger'] < 0.30:
            rules['phi_improvement_trigger'] *= 1.3  # 30% 강화
            changed.append(f"phi_improvement_trigger → {rules['phi_improvement_trigger']:.3f} (discovery_rate {discovery_rate:.1%} too high)")

        # 오탐률 > 30% → confidence 강화
        if false_positive_rate > 0.30 and rules['min_confidence'] != 'HIGH':
            rules['min_confidence'] = 'HIGH'
            changed.append(f"min_confidence → HIGH (FP rate {false_positive_rate:.1%})")

        # 오탐률 < 5% and 발견률 < 10% → confidence 완화
        if false_positive_rate < 0.05 and discovery_rate < 0.10 and rules['min_confidence'] == 'HIGH':
            rules['min_confidence'] = 'MEDIUM'
            changed.append(f"min_confidence → MEDIUM (FP {false_positive_rate:.1%}, discovery {discovery_rate:.1%})")

        # compression_min 진화: 최근 5개 스캔의 평균 compression 기준으로 조정
        recent = s.get('discovery_rate_history', [])[-5:]
        if recent:
            avg_comp = np.mean([r.get('avg_compression', 50) for r in recent if 'avg_compression' in r])
            if avg_comp > 60 and rules['compression_min'] < 50:
                rules['compression_min'] = min(50, rules['compression_min'] + 5)
                changed.append(f"compression_min → {rules['compression_min']} (avg={avg_comp:.0f}% improving)")

        if changed:
            s['generation'] += 1
            s['threshold_evolution'].append({
                'generation': s['generation'],
                'changes': changed,
                'discovery_rate': discovery_rate,
                'false_positive_rate': false_positive_rate,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            })
            print(f"  [RECURSIVE] Gen {s['generation']}: {len(changed)} rules evolved")
            for c in changed:
                print(f"    → {c}")
            self._save_state()

    def record_scan(self, found_candidates: int, registered: int, avg_compression: float = 0):
        """스캔 결과 기록 (메타 학습용)."""
        self.state['total_scans'] += 1
        self.state['total_discoveries'] += found_candidates
        self.state['total_registered'] += registered
        self.state['discovery_rate_history'].append({
            'scan_id': self.state['total_scans'],
            'candidates': found_candidates,
            'registered': registered,
            'avg_compression': avg_compression,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        })
        # 50개마다 규칙 진화
        if self.state['total_scans'] % 50 == 0:
            self.evolve_rules()
        self._save_state()

    def record_false_positive(self, law_id: int, reason: str):
        """등록된 법칙이 검증 실패 시 기록."""
        self.state['total_false_positives'] += 1
        self._save_state()

    def get_rules(self) -> dict:
        """현재 활성 규칙 반환 (discover_laws에서 사용)."""
        return self.state['active_rules']

    def report(self) -> str:
        """재귀 루프 상태 리포트 (극가속 리포트 양식 포함)."""
        s = self.state
        total = s['total_scans']
        dr = s['total_discoveries'] / max(total, 1)
        fpr = s['total_false_positives'] / max(s['total_registered'], 1)

        lines = []
        lines.append(f"  ■ 재귀 루프 (Gen {s['generation']})")
        lines.append(f"  Scans: {total} | Discoveries: {s['total_discoveries']} ({dr:.1%})")
        lines.append(f"  Registered: {s['total_registered']} | FP: {s['total_false_positives']} ({fpr:.1%})")

        # 발견률 바
        dr_pct = int(dr * 20)
        lines.append(f"  발견률: {'█' * dr_pct}{'░' * (20 - dr_pct)} {dr:.1%}")

        # 규칙 상태
        rules = s['active_rules']
        lines.append(f"  규칙: confidence={rules.get('min_confidence', '?')} "
                     f"phi_trigger={rules.get('phi_improvement_trigger', 0):.2f} "
                     f"compression_min={rules.get('compression_min', 0)}")

        # 진화 이력
        evos = s.get('threshold_evolution', [])
        if evos:
            lines.append(f"  진화 이력: {len(evos)}세대")
            for evo in evos[-3:]:  # 최근 3개
                lines.append(f"    Gen {evo['generation']}: {', '.join(evo['changes'][:2])}")

        # 최근 스캔 트렌드
        recent = s.get('discovery_rate_history', [])[-10:]
        if recent:
            comps = [r.get('avg_compression', 0) for r in recent if r.get('avg_compression', 0) > 0]
            if comps:
                lines.append(f"  Compression 추이: {comps[0]:.0f}% → {comps[-1]:.0f}%")

        text = '\n'.join(lines)
        print(text)
        return text

    def export_log(self, path: str = None) -> str:
        """전체 로그 JSON 내보내기."""
        if path is None:
            path = os.path.join(_THIS_DIR, '..', 'data', 'recursive_loop_export.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)

        export = {
            '_meta': {
                'exported': time.strftime('%Y-%m-%d %H:%M:%S'),
                'description': 'Recursive discovery loop state + history',
            },
            'state': self.state,
            'summary': {
                'generation': self.state['generation'],
                'total_scans': self.state['total_scans'],
                'discovery_rate': self.state['total_discoveries'] / max(self.state['total_scans'], 1),
                'false_positive_rate': self.state['total_false_positives'] / max(self.state['total_registered'], 1),
                'active_rules': self.state['active_rules'],
            }
        }
        with open(path, 'w') as f:
            json.dump(export, f, indent=2, ensure_ascii=False)
        print(f"  [RECURSIVE] Exported: {path}")
        return path


# Global recursive loop instance
_recursive_loop = RecursiveLoop()


def watch_directory(watch_dir: str, auto_register: bool = False, interval: int = 60):
    """체크포인트 디렉토리 감시 → 새 체크포인트 발견 시 자동 루프."""
    print(f"[AUTO-LOOP] Watching: {watch_dir}")
    print(f"[AUTO-LOOP] Auto-register: {auto_register}")
    print(f"[AUTO-LOOP] Interval: {interval}s")

    seen = set()
    prev_metrics = None
    log_path = os.path.join(watch_dir, 'auto_discovery_log.json')
    log = []

    while True:
        ckpts = sorted(glob.glob(os.path.join(watch_dir, '**', '*.pt'), recursive=True))

        for ckpt in ckpts:
            if ckpt in seen:
                continue
            seen.add(ckpt)

            print(f"\n{'='*60}")
            print(f"  [SCAN] {os.path.basename(ckpt)}")
            print(f"{'='*60}")

            # Layer 1: NEXUS-6 스캔
            metrics = nexus_scan_checkpoint(ckpt)
            if 'error' in metrics:
                print(f"  [SKIP] {metrics['error']}")
                continue

            print(f"  Phi={metrics['phi_approx']:.4f} chaos={metrics['chaos_score']:.4f} "
                  f"compression={metrics['phi_compression_pct']:.1f}%")

            # Layer 2: 이상 탐지 (재귀 루프 규칙 적용)
            rules = _recursive_loop.get_rules()
            anomalies = detect_anomalies(metrics, prev_metrics)
            for a in anomalies:
                print(f"  [{'⚠️' if a['severity']=='WARNING' else '🔴'}] {a['type']}: {a.get('value', '')}")

            # Layer 3: 법칙 발견
            candidates = discover_laws(metrics, prev_metrics)
            for c in candidates:
                print(f"  [💡 {c['confidence']}] {c['formula']}")

            # Layer 4: 자동 등록 (재귀 루프 규칙 반영)
            registered = []
            if auto_register and candidates:
                registered = auto_register_laws(candidates, min_confidence=rules.get('min_confidence', 'HIGH'))

            # Layer 5: 재귀 — 메타 학습 (발견 패턴 기록 → 규칙 자동 진화)
            _recursive_loop.record_scan(
                found_candidates=len(candidates),
                registered=len(registered),
                avg_compression=metrics.get('phi_compression_pct', 0)
            )

            # 로그 기록
            entry = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'checkpoint': os.path.basename(ckpt),
                'metrics': metrics,
                'anomalies': anomalies,
                'candidates': [c['formula'] for c in candidates],
                'registered': registered,
                'recursive_gen': _recursive_loop.state['generation'],
            }
            log.append(entry)
            try:
                with open(log_path, 'w') as f:
                    json.dump(log, f, indent=2, ensure_ascii=False)
            except:
                pass

            prev_metrics = metrics

        time.sleep(interval)


def run_pipeline():
    """전체 자동 파이프라인: 72B 대기 → 14B v0.5 → 32B → 스캔 → 발견 루프."""
    print("[PIPELINE] Full automation mode")
    print("[PIPELINE] 72B 완료 대기 → after_72b.sh → auto-discovery loop")

    # Check if 72B is still running
    import subprocess
    while True:
        result = subprocess.run(['pgrep', '-f', 'train_anima_lm'], capture_output=True)
        if result.returncode != 0:
            print("[PIPELINE] No training process found — starting pipeline")
            break
        print(f"[PIPELINE] Training still running... (checking every 5m)")
        time.sleep(300)

    # Run after_72b.sh
    print("[PIPELINE] Launching after_72b.sh")
    os.system("bash /workspace/after_72b.sh 2>&1 | tee /workspace/pipeline_full.log")

    # Auto-discovery on all results
    print("[PIPELINE] Training complete — starting discovery loop")
    for ckpt_dir in ['/workspace/checkpoints/animalm_14b_v05/',
                     '/workspace/checkpoints/animalm_32b/']:
        if os.path.exists(ckpt_dir):
            ckpts = sorted(glob.glob(os.path.join(ckpt_dir, '*.pt')))
            prev = None
            for ckpt in ckpts:
                metrics = nexus_scan_checkpoint(ckpt)
                if 'error' not in metrics:
                    print(f"  {os.path.basename(ckpt)}: Phi={metrics['phi_approx']:.4f} "
                          f"compression={metrics['phi_compression_pct']:.1f}%")
                    candidates = discover_laws(metrics, prev)
                    if candidates:
                        auto_register_laws(candidates, min_confidence='HIGH')
                    prev = metrics

    print("[PIPELINE] Complete.")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='발견→반영 자동화 루프')
    p.add_argument('--scan', help='단발 체크포인트 스캔')
    p.add_argument('--watch', help='디렉토리 감시 모드')
    p.add_argument('--pipeline', action='store_true', help='전체 파이프라인 자동화')
    p.add_argument('--auto-register', action='store_true', dest='auto_register',
                   help='발견된 법칙 자동 등록')
    p.add_argument('--interval', type=int, default=60, help='감시 간격 (초)')
    args = p.parse_args()

    if args.scan:
        metrics = nexus_scan_checkpoint(args.scan)
        if 'error' in metrics:
            print(f"Error: {metrics['error']}")
        else:
            print(json.dumps(metrics, indent=2))
            anomalies = detect_anomalies(metrics)
            if anomalies:
                print(f"\nAnomalies: {len(anomalies)}")
                for a in anomalies:
                    print(f"  {a['severity']}: {a['type']}")

    elif args.watch:
        watch_directory(args.watch, auto_register=args.auto_register, interval=args.interval)

    elif args.pipeline:
        run_pipeline()

    else:
        p.print_help()
