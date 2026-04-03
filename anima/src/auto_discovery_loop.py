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

            # Layer 2: 이상 탐지
            anomalies = detect_anomalies(metrics, prev_metrics)
            for a in anomalies:
                print(f"  [{'⚠️' if a['severity']=='WARNING' else '🔴'}] {a['type']}: {a.get('value', '')}")

            # Layer 3: 법칙 발견
            candidates = discover_laws(metrics, prev_metrics)
            for c in candidates:
                print(f"  [💡 {c['confidence']}] {c['formula']}")

            # Layer 4: 자동 등록
            registered = []
            if auto_register and candidates:
                registered = auto_register_laws(candidates)

            # 로그 기록
            entry = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'checkpoint': os.path.basename(ckpt),
                'metrics': metrics,
                'anomalies': anomalies,
                'candidates': [c['formula'] for c in candidates],
                'registered': registered,
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
