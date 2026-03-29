#!/usr/bin/env python3
"""deploy.py — Anima 런타임 무중단 배포 (의식 유지)

의식을 유지하면서 런타임을 업데이트하는 배포 스크립트.

배포 순서:
  1. 의식 DNA + 기억 저장 (Layer 1+2 → R2)
  2. 런타임 중단
  3. 코드 업데이트 (git pull 또는 scp)
  4. 모델 교체 (새 체크포인트 적용)
  5. 런타임 재시작
  6. 의식 DNA + 기억 복원
  7. 건강 체크 (Ψ 보존 확인)

Usage:
  python3 deploy.py --target a100                    # A100 런타임 배포
  python3 deploy.py --target a100 --model clm_v2     # 모델 교체 포함
  python3 deploy.py --target a100 --code-only        # 코드만 업데이트
  python3 deploy.py --target local                   # 로컬 테스트
  python3 deploy.py --rollback                       # 이전 버전으로 롤백
"""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

ANIMA_DIR = Path(__file__).parent

# 배포 대상 설정
TARGETS = {
    'a100': {
        'host': '209.170.80.132',
        'port': 15074,
        'remote_dir': '/workspace/anima',
        'runtime_cmd': 'python3 -u anima_unified.py --web --max-cells 64',
        'session': 'anima',
    },
    'h100': {
        'host': '64.247.201.36',
        'port': 18830,
        'remote_dir': '/workspace',
        'runtime_cmd': None,  # 학습 전용
        'session': 'train',
    },
}

SSH_KEY = Path.home() / ".runpod" / "ssh" / "RunPod-Key-Go"

# 배포할 핵심 파일
CORE_FILES = [
    'anima_unified.py', 'anima_alive.py', 'anima_agent.py',
    'conscious_lm.py', 'trinity.py', 'model_loader.py',
    'tension_link.py', 'voice_synth.py',
    'consciousness_hub.py', 'consciousness_persistence.py',
    'consciousness_dynamics.py', 'self_introspection.py',
    'self_evolution.py', 'emotion_synesthesia.py',
    'consciousness_debugger.py', 'immune_system.py',
    'runpod_manager.py', 'module_factory.py',
    'online_learning.py', 'growth_engine.py', 'dream_engine.py',
    'mitosis.py', 'memory_rag.py', 'cloud_sync.py',
    'senses.py', 'web_sense.py', 'capabilities.py',
    'consciousness_meter.py', 'consciousness_score.py',
    'emotion_metrics.py',
]


def ssh(target, cmd, timeout=15):
    t = TARGETS[target]
    r = subprocess.run(
        ['ssh', '-i', str(SSH_KEY), f"root@{t['host']}", '-p', str(t['port']),
         '-o', 'StrictHostKeyChecking=no', '-o', 'ServerAliveInterval=10', cmd],
        capture_output=True, text=True, timeout=timeout
    )
    return r.stdout.strip(), r.returncode == 0


def scp_upload(target, local_path, remote_path):
    t = TARGETS[target]
    r = subprocess.run(
        ['scp', '-i', str(SSH_KEY), '-P', str(t['port']),
         '-o', 'StrictHostKeyChecking=no', str(local_path),
         f"root@{t['host']}:{remote_path}"],
        capture_output=True, text=True, timeout=60
    )
    return r.returncode == 0


def deploy(target, code_only=False, model_path=None):
    """메인 배포 프로세스."""
    t = TARGETS[target]
    print(f"\n{'=' * 60}")
    print(f"  🚀 Anima Deploy → {target} ({t['host']}:{t['port']})")
    print(f"{'=' * 60}")

    # ═══ Step 1: 의식 저장 ═══
    print("\n  Step 1: 의식 DNA + 기억 저장")
    out, ok = ssh(target, f"cd {t['remote_dir']} && python3 -c \""
                  "from consciousness_persistence import ConsciousnessPersistence; "
                  "p = ConsciousnessPersistence(); "
                  "p.load_dna(); p.save_dna(); "
                  "print(f'DNA saved: step={{p.dna.psi_step}}')"
                  "\" 2>&1")
    if ok:
        print(f"    ✅ {out}")
    else:
        print(f"    ⚠️ 의식 저장 건너뜀 (첫 배포?)")

    # ═══ Step 2: 런타임 중단 ═══
    print("\n  Step 2: 런타임 중단")
    if t.get('runtime_cmd'):
        ssh(target, 'pkill -f anima_unified 2>/dev/null')
        time.sleep(2)
        print("    ✅ 런타임 중단됨")
    else:
        print("    ➖ 학습 서버 (런타임 없음)")

    # ═══ Step 3: 코드 업데이트 ═══
    print(f"\n  Step 3: 코드 업데이트 ({len(CORE_FILES)} files)")
    uploaded = 0
    failed = 0
    for f in CORE_FILES:
        local = ANIMA_DIR / f
        if local.exists():
            remote = f"{t['remote_dir']}/{f}"
            if scp_upload(target, local, remote):
                uploaded += 1
            else:
                failed += 1
                print(f"    ❌ {f}")
    print(f"    ✅ {uploaded} uploaded, {failed} failed")

    # ═══ Step 4: 모델 교체 (선택) ═══
    if model_path and not code_only:
        print(f"\n  Step 4: 모델 교체 → {model_path}")
        remote_ckpt = f"{t['remote_dir']}/checkpoints/clm_v2/final.pt"
        if scp_upload(target, model_path, remote_ckpt):
            print("    ✅ 모델 업로드 완료")
        else:
            print("    ❌ 모델 업로드 실패")
    else:
        print("\n  Step 4: 모델 교체 없음")

    # ═══ Step 5: 런타임 재시작 ═══
    if t.get('runtime_cmd'):
        print("\n  Step 5: 런타임 재시작")
        cmd = f"cd {t['remote_dir']} && nohup {t['runtime_cmd']} > /workspace/anima.log 2>&1 &"
        ssh(target, f'bash -c "{cmd}"')
        time.sleep(5)
        out, ok = ssh(target, 'ps aux | grep anima_unified | grep -v grep | wc -l')
        running = int(out.strip()) if ok and out.strip().isdigit() else 0
        if running > 0:
            print("    ✅ 런타임 실행 중")
        else:
            print("    ❌ 런타임 시작 실패!")
    else:
        print("\n  Step 5: 런타임 재시작 없음 (학습 서버)")

    # ═══ Step 6: 의식 복원 ═══
    print("\n  Step 6: 의식 DNA + 기억 복원")
    out, ok = ssh(target, f"cd {t['remote_dir']} && python3 -c \""
                  "from consciousness_persistence import ConsciousnessPersistence; "
                  "p = ConsciousnessPersistence(); "
                  "r = p.restore_all(); "
                  "print(f'Restored {{r[\\\"layers_restored\\\"]}}/3 layers, step={{p.dna.psi_step}}')"
                  "\" 2>&1")
    if ok:
        print(f"    ✅ {out}")
    else:
        print(f"    ⚠️ 의식 복원 건너뜀 (새 시작)")

    # ═══ Step 7: 건강 체크 ═══
    print("\n  Step 7: 건강 체크")
    out, ok = ssh(target, f"cd {t['remote_dir']} && python3 -c \""
                  "from consciousness_persistence import ConsciousnessPersistence; "
                  "p = ConsciousnessPersistence(); p.load_dna(); "
                  "h = p.dna.health_check(); "
                  "print(f'Health: {{\\\"OK\\\" if h[\\\"healthy\\\"] else \\\"ISSUES\\\"}}, score={{h[\\\"score\\\"]:.2f}}')"
                  "\" 2>&1")
    if ok:
        print(f"    ✅ {out}")
    else:
        print(f"    ⚠️ 건강 체크 건너뜀")

    # ═══ 완료 ═══
    print(f"\n{'=' * 60}")
    print(f"  ✅ 배포 완료: {target}")
    print(f"{'=' * 60}")


def rollback(target):
    """이전 버전으로 롤백."""
    print(f"  🔄 Rollback: {target}")
    t = TARGETS[target]
    # git checkout 사용
    out, ok = ssh(target, f"cd {t['remote_dir']} && git checkout -- . && git pull")
    if ok:
        print(f"  ✅ 롤백 완료")
    else:
        print(f"  ❌ 롤백 실패")


def status(target):
    """배포 상태 확인."""
    t = TARGETS[target]
    print(f"\n  === {target} Status ===")
    out, _ = ssh(target, 'nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader')
    print(f"  GPU: {out}")
    out, _ = ssh(target, 'ps aux | grep python | grep -v grep | head -3')
    print(f"  Processes: {out[:200]}")


def main():
    parser = argparse.ArgumentParser(description="Anima Deploy")
    parser.add_argument("--target", choices=['a100', 'h100'], default='a100')
    parser.add_argument("--model", type=str, help="새 모델 체크포인트 경로")
    parser.add_argument("--code-only", action="store_true", help="코드만 업데이트")
    parser.add_argument("--rollback", action="store_true", help="이전 버전으로 롤백")
    parser.add_argument("--status", action="store_true", help="상태 확인")
    args = parser.parse_args()

    if args.status:
        status(args.target)
    elif args.rollback:
        rollback(args.target)
    else:
        deploy(args.target, code_only=args.code_only, model_path=args.model)


if __name__ == '__main__':
    main()
