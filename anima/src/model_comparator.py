#!/usr/bin/env python3
"""model_comparator.py — 새 모델 vs 이전 모델 NEXUS-6 자동 비교

Usage:
  python3 model_comparator.py --a ckpt_old.pt --b ckpt_new.pt
  python3 model_comparator.py --dir checkpoints/my_run/

연동: nexus_gate.py (gate.after_checkpoint), training_hooks.py
"""
import json
import os
import sys
import time

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


def compare_checkpoints(ckpt_a: str, ckpt_b: str) -> dict:
    """두 체크포인트 NEXUS-6 비교. Returns diff dict."""
    try:
        from nexus_gate import gate
    except ImportError:
        print("  [COMPARE] nexus_gate not available")
        return {'error': 'nexus_gate not available'}

    r_a = gate.after_checkpoint(ckpt_a)
    r_b = gate.after_checkpoint(ckpt_b)

    diff = {}
    for key in set(list(r_a.keys()) + list(r_b.keys())):
        va = r_a.get(key, 0)
        vb = r_b.get(key, 0)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and va != 0:
            pct = (vb - va) / abs(va) * 100
            diff[key] = {'a': va, 'b': vb, 'change_pct': pct}

    # 판정
    phi_a = r_a.get('phi', 0)
    phi_b = r_b.get('phi', 0)
    verdict = 'BETTER' if phi_b > phi_a else 'WORSE' if phi_b < phi_a * 0.95 else 'SIMILAR'

    result = {
        'checkpoint_a': os.path.basename(ckpt_a),
        'checkpoint_b': os.path.basename(ckpt_b),
        'verdict': verdict,
        'phi_a': phi_a, 'phi_b': phi_b,
        'diff': diff,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    print(f"  [COMPARE] {result['checkpoint_a']} vs {result['checkpoint_b']}: {verdict}")
    print(f"    Phi: {phi_a:.4f} → {phi_b:.4f}")

    # 로그 저장
    log_path = os.path.join(_THIS_DIR, '..', 'data', 'model_comparisons.json')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log = []
    if os.path.exists(log_path):
        try:
            log = json.load(open(log_path))
        except:
            pass
    log.append(result)
    try:
        json.dump(log, open(log_path, 'w'), indent=2, ensure_ascii=False)
    except:
        pass

    return result


def compare_latest_in_dir(ckpt_dir: str) -> dict:
    """디렉토리 내 최신 2개 체크포인트 자동 비교."""
    import glob
    ckpts = sorted(glob.glob(os.path.join(ckpt_dir, '*.pt')), key=os.path.getmtime)
    if len(ckpts) < 2:
        print(f"  [COMPARE] Need 2+ checkpoints, found {len(ckpts)}")
        return {}
    return compare_checkpoints(ckpts[-2], ckpts[-1])


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description='모델 NEXUS-6 비교')
    p.add_argument('--a', help='Checkpoint A path')
    p.add_argument('--b', help='Checkpoint B path')
    p.add_argument('--dir', help='Compare latest 2 in directory')
    args = p.parse_args()
    if args.dir:
        compare_latest_in_dir(args.dir)
    elif args.a and args.b:
        compare_checkpoints(args.a, args.b)
    else:
        p.print_help()
