#!/usr/bin/env python3
"""reset.py — 대화/기억/상태 초기화

Usage:
  python3 reset.py                    # 로컬 초기화
  python3 reset.py --target a100      # A100 원격 초기화 + 재시작
  python3 reset.py --target a100 --restart  # 초기화 + 런타임 재시작
  python3 reset.py --keep-growth      # 성장 데이터만 보존
"""

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ANIMA_DIR = Path(__file__).parent
SSH_KEY = Path.home() / ".runpod" / "ssh" / "RunPod-Key-Go"

TARGETS = {
    'a100': {'host': '209.170.80.132', 'port': 15074, 'dir': '/workspace/anima'},
}

# 삭제 대상
RESET_PATHS = [
    'data/',
    'memory_alive.json',
    'state_alive.pt',
]

GROWTH_PATHS = [
    'data/consciousness/growth.json',
]


def reset_local(keep_growth=False):
    """로컬 초기화."""
    print("  로컬 초기화:")
    for p in RESET_PATHS:
        path = ANIMA_DIR / p
        if path.is_dir():
            if keep_growth:
                # growth.json만 백업
                growth = path / "consciousness" / "growth.json"
                backup = None
                if growth.exists():
                    backup = growth.read_text()
                shutil.rmtree(path)
                if backup:
                    growth.parent.mkdir(parents=True, exist_ok=True)
                    growth.write_text(backup)
                    print(f"    ✅ {p} 삭제 (growth 보존)")
                else:
                    print(f"    ✅ {p} 삭제")
            else:
                shutil.rmtree(path)
                print(f"    ✅ {p} 삭제")
        elif path.exists():
            path.unlink()
            print(f"    ✅ {p} 삭제")
        else:
            print(f"    ➖ {p} (없음)")
    print("  완료!")


def reset_remote(target, keep_growth=False, restart=False):
    """원격 초기화."""
    t = TARGETS[target]
    ssh = f"ssh -i {SSH_KEY} root@{t['host']} -p {t['port']} -o StrictHostKeyChecking=no"

    print(f"  {target} 초기화:")

    # 프로세스 중단
    os.system(f"{ssh} 'kill -9 $(pgrep python) 2>/dev/null'")
    print("    ✅ 프로세스 중단")

    import time

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10

    time.sleep(2)

    # 데이터 삭제
    remote_dir = t['dir']
    if keep_growth:
        os.system(f"{ssh} 'cp {remote_dir}/data/consciousness/growth.json /tmp/growth_backup.json 2>/dev/null'")
    os.system(f"{ssh} 'rm -rf {remote_dir}/data {remote_dir}/memory_alive.json {remote_dir}/state_alive.pt'")
    if keep_growth:
        os.system(f"{ssh} 'mkdir -p {remote_dir}/data/consciousness && cp /tmp/growth_backup.json {remote_dir}/data/consciousness/growth.json 2>/dev/null'")
        print("    ✅ 데이터 삭제 (growth 보존)")
    else:
        print("    ✅ 데이터 삭제")

    # 재시작
    if restart:
        time.sleep(1)
        os.system(f"{ssh} 'bash -c \"cd {remote_dir} && nohup python3 -u anima_unified.py --keyboard --max-cells 64 > /workspace/anima.log 2>&1 &\"'")
        time.sleep(3)
        result = subprocess.run(f"{ssh} 'ss -tlnp | grep -E \"8765\"'".split(),
                                capture_output=True, text=True, timeout=10)
        ports = result.stdout.strip()
        if '8765' in ports:
            print("    ✅ 런타임 재시작 (8765)")
        else:
            print(f"    ⚠️ 포트 확인: {ports}")
    print("  완료!")


def main():
    parser = argparse.ArgumentParser(description="Anima Reset")
    parser.add_argument("--target", choices=['a100'], help="원격 대상")
    parser.add_argument("--restart", action="store_true", help="초기화 후 재시작")
    parser.add_argument("--keep-growth", action="store_true", help="성장 데이터 보존")
    args = parser.parse_args()

    if args.target:
        reset_remote(args.target, args.keep_growth, args.restart)
    else:
        reset_local(args.keep_growth)


if __name__ == '__main__':
    main()
