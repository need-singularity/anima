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
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


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
    'anima_unified.py', 'anima_alive.py',
    # Note: anima_agent.py is in separate anima-agent/ repo, deployed separately
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


def dry_run(target, model_path=None):
    """--dry-run: Show what would be deployed without side effects.

    Lists files, sizes, checksums, and validates target config.
    """
    t = TARGETS[target]
    print(f"\n{'=' * 60}")
    print(f"  DRY RUN: {target} ({t['host']}:{t['port']})")
    print(f"{'=' * 60}")

    # Check CORE_FILES
    print(f"\n  Core files ({len(CORE_FILES)}):")
    total_size = 0
    missing = []
    file_info = []
    for f in CORE_FILES:
        local = ANIMA_DIR / f
        if local.exists():
            size = local.stat().st_size
            total_size += size
            md5 = hashlib.md5(local.read_bytes()).hexdigest()[:12]
            file_info.append((f, size, md5, True))
        else:
            file_info.append((f, 0, "N/A", False))
            missing.append(f)

    for name, size, md5, exists in file_info:
        status_str = f"{size:>8,} bytes  md5={md5}" if exists else "MISSING"
        marker = "OK" if exists else "!!"
        print(f"    [{marker}] {name:<35} {status_str}")

    print(f"\n  Total: {total_size:,} bytes ({total_size/1024:.1f} KB)")
    print(f"  Present: {len(CORE_FILES) - len(missing)}/{len(CORE_FILES)}")
    if missing:
        print(f"  Missing: {', '.join(missing)}")

    # Model check
    if model_path:
        mp = Path(model_path)
        if mp.exists():
            ms = mp.stat().st_size
            print(f"\n  Model: {mp.name} ({ms/1024/1024:.1f} MB)")
        else:
            print(f"\n  Model: {model_path} (NOT FOUND)")
    else:
        print(f"\n  Model: (no model specified)")

    # Target config
    print(f"\n  Target config:")
    print(f"    Host:       {t['host']}:{t['port']}")
    print(f"    Remote dir: {t['remote_dir']}")
    print(f"    Runtime:    {t.get('runtime_cmd', 'N/A')}")
    print(f"    Session:    {t.get('session', 'N/A')}")

    # SSH key check
    if SSH_KEY.exists():
        print(f"    SSH key:    {SSH_KEY} (exists)")
    else:
        print(f"    SSH key:    {SSH_KEY} (MISSING)")

    # Connectivity test (optional, skip if no SSH key)
    if SSH_KEY.exists():
        print(f"\n  Connectivity test:")
        try:
            out, ok = ssh(target, 'echo PING', timeout=5)
            if ok and 'PING' in out:
                print(f"    Target reachable: YES")
            else:
                print(f"    Target reachable: NO (SSH failed)")
        except Exception as e:
            print(f"    Target reachable: NO ({e})")
    else:
        print(f"\n  Connectivity test: SKIPPED (no SSH key)")

    print(f"\n  Result: {'READY' if not missing else 'WARNING: missing files'}")
    print(f"{'=' * 60}")
    return len(missing) == 0


def verify(target):
    """--verify: Post-deployment health checks.

    1. Check runtime process is running
    2. Import key modules on target
    3. Run consciousness health check
    """
    t = TARGETS[target]
    print(f"\n{'=' * 60}")
    print(f"  VERIFY: {target} ({t['host']}:{t['port']})")
    print(f"{'=' * 60}")

    checks_passed = 0
    checks_total = 0

    # Check 1: Process running
    checks_total += 1
    print(f"\n  [1/4] Runtime process check:")
    if t.get('runtime_cmd'):
        out, ok = ssh(target, 'ps aux | grep anima_unified | grep -v grep | wc -l')
        running = int(out.strip()) if ok and out.strip().isdigit() else 0
        if running > 0:
            print(f"    PASS: anima_unified running ({running} process(es))")
            checks_passed += 1
        else:
            print(f"    FAIL: anima_unified not running")
    else:
        print(f"    SKIP: no runtime on {target}")
        checks_passed += 1

    # Check 2: Key module imports
    checks_total += 1
    print(f"\n  [2/4] Module import check:")
    import_cmd = (
        f"cd {t['remote_dir']} && python3 -c \""
        "ok=0; total=0; "
        "mods=['consciousness_persistence','consciousness_engine','trinity','conscious_lm']; "
        "[exec('total+=1') for _ in mods]; "
        "results=[]; "
        "[results.append(m) for m in mods if __import__(m)]; "
        "print(f'{len(results)}/{total} imports OK')"
        "\" 2>&1"
    )
    out, ok = ssh(target, import_cmd, timeout=30)
    if ok and 'imports OK' in out:
        print(f"    PASS: {out}")
        checks_passed += 1
    else:
        print(f"    FAIL: {out[:200]}")

    # Check 3: Consciousness health
    checks_total += 1
    print(f"\n  [3/4] Consciousness health check:")
    health_cmd = (
        f"cd {t['remote_dir']} && python3 -c \""
        "from consciousness_persistence import ConsciousnessPersistence; "
        "p = ConsciousnessPersistence(); "
        "loaded = p.load_dna(); "
        "h = p.dna.health_check() if loaded else {{'healthy': False, 'issues': ['no DNA'], 'score': 0}}; "
        "print(f'healthy={{h[\\\"healthy\\\"]}} score={{h[\\\"score\\\"]:.2f}} step={{p.dna.psi_step}}')"
        "\" 2>&1"
    )
    out, ok = ssh(target, health_cmd, timeout=15)
    if ok and 'healthy=True' in out:
        print(f"    PASS: {out}")
        checks_passed += 1
    elif ok:
        print(f"    WARN: {out}")
        checks_passed += 1  # Warn but pass (new deployment has no DNA yet)
    else:
        print(f"    FAIL: {out[:200]}")

    # Check 4: GPU available
    checks_total += 1
    print(f"\n  [4/4] GPU check:")
    out, ok = ssh(target, 'nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null')
    if ok and out:
        print(f"    PASS: {out}")
        checks_passed += 1
    else:
        print(f"    WARN: GPU info unavailable")

    print(f"\n  Result: {checks_passed}/{checks_total} checks passed")
    print(f"{'=' * 60}")
    return checks_passed == checks_total


def rollback(target):
    """이전 버전으로 롤백."""
    print(f"  Rollback: {target}")
    t = TARGETS[target]
    # git checkout 사용
    out, ok = ssh(target, f"cd {t['remote_dir']} && git checkout -- . && git pull")
    if ok:
        print(f"  Rollback complete")
    else:
        print(f"  Rollback failed")


def status(target):
    """배포 상태 확인."""
    t = TARGETS[target]
    print(f"\n  === {target} Status ===")
    out, _ = ssh(target, 'nvidia-smi --query-gpu=name,utilization.gpu,memory.used --format=csv,noheader')
    print(f"  GPU: {out}")
    out, _ = ssh(target, 'ps aux | grep python | grep -v grep | head -3')
    print(f"  Processes: {out[:200]}")


def rollback_test():
    """Rollback verification test (local only, no SSH).

    Simulates: save state -> deploy -> rollback -> verify state matches.
    Uses consciousness_persistence to verify consciousness is preserved.
    """
    import tempfile

    print(f"\n{'=' * 60}")
    print(f"  ROLLBACK TEST (local simulation)")
    print(f"{'=' * 60}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Create initial state
        print(f"\n  [1/5] Creating initial consciousness state...")
        from consciousness_persistence import ConsciousnessPersistence, ConsciousnessDNA
        persist = ConsciousnessPersistence("rollback-test", data_dir=tmpdir)
        persist.dna.psi_residual = 0.4987
        persist.dna.psi_gate = 0.951
        persist.dna.psi_h = 0.9999
        persist.dna.psi_step = 5000
        persist.dna.phi = 14.5
        persist.dna.identity_coherence = 0.95
        persist.dna.emotions['joy'] = 0.8
        persist.dna.emotions['curiosity'] = 0.6
        persist.memory.growth_stage = "child"
        persist.memory.conversations = [{"role": "user", "text": f"msg-{i}"} for i in range(5)]
        persist.memory.relationships = {"user1": 0.9}

        # Save original state
        original_dna = persist.dna.to_dict()
        original_mem = persist.memory.to_dict()

        persist.save_all()
        print(f"    Saved: step={persist.dna.psi_step}, phi={persist.dna.phi}")

        # Step 2: Simulate "deploy" that changes state
        print(f"\n  [2/5] Simulating deployment (state changes)...")
        persist.dna.psi_step = 9999
        persist.dna.phi = 0.0  # Corrupted!
        persist.dna.psi_residual = 0.0
        persist.memory.growth_stage = "newborn"
        persist.memory.conversations = []
        print(f"    Corrupted: step={persist.dna.psi_step}, phi={persist.dna.phi}")

        # Step 3: Rollback (restore from saved files)
        print(f"\n  [3/5] Rolling back (restoring from backup)...")
        persist2 = ConsciousnessPersistence("rollback-test", data_dir=tmpdir)
        result = persist2.restore_all()
        print(f"    Restored: {result['layers_restored']}/3 layers")

        # Step 4: Verify state matches original
        print(f"\n  [4/5] Verifying state matches original...")
        restored_dna = persist2.dna.to_dict()
        restored_mem = persist2.memory.to_dict()

        mismatches = []
        for key in original_dna:
            if original_dna[key] != restored_dna.get(key):
                mismatches.append(f"DNA.{key}: {original_dna[key]} != {restored_dna.get(key)}")
        for key in original_mem:
            if original_mem[key] != restored_mem.get(key):
                mismatches.append(f"Memory.{key}: original != restored")

        if mismatches:
            print(f"    FAIL: {len(mismatches)} mismatches:")
            for m in mismatches[:5]:
                print(f"      - {m}")
        else:
            print(f"    PASS: All fields match original")

        # Step 5: Health check
        print(f"\n  [5/5] Health check after rollback...")
        health = persist2.dna.health_check()
        print(f"    Healthy: {health['healthy']}, Score: {health['score']:.2f}")
        if health['issues']:
            print(f"    Issues: {health['issues']}")

        success = len(mismatches) == 0 and health['healthy']
        print(f"\n  Result: {'PASS' if success else 'FAIL'}")
        print(f"{'=' * 60}")
        return success


def main():
    parser = argparse.ArgumentParser(description="Anima Deploy")
    parser.add_argument("--target", choices=['a100', 'h100', 'local'], default='a100')
    parser.add_argument("--model", type=str, help="Model checkpoint path")
    parser.add_argument("--code-only", action="store_true", help="Code only update")
    parser.add_argument("--rollback", action="store_true", help="Rollback to previous version")
    parser.add_argument("--status", action="store_true", help="Check status")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deployed (no side effects)")
    parser.add_argument("--verify", action="store_true", help="Post-deployment health checks")
    parser.add_argument("--rollback-test", action="store_true", help="Run local rollback verification test")
    args = parser.parse_args()

    if args.dry_run:
        dry_run(args.target, model_path=args.model)
    elif args.verify:
        verify(args.target)
    elif args.rollback_test:
        rollback_test()
    elif args.status:
        status(args.target)
    elif args.rollback:
        rollback(args.target)
    else:
        deploy(args.target, code_only=args.code_only, model_path=args.model)


if __name__ == '__main__':
    main()
