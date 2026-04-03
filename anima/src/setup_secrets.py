#!/usr/bin/env python3
"""setup_secrets.py — API 키/시크릿을 vault에 저장

.env 파일이나 직접 입력으로 시크릿을 SecretVault(keychain)에 저장.

Usage:
  python3 setup_secrets.py                          # .env에서 자동 로드
  python3 setup_secrets.py --from-env ~/Dev/TECS-L/.env  # 특정 .env
  python3 setup_secrets.py --set KEY=VALUE          # 직접 설정
  python3 setup_secrets.py --list                   # 저장된 키 목록
  python3 setup_secrets.py --export                 # 환경변수로 내보내기
"""

import argparse
import os
from pathlib import Path
from secret_vault import SecretVault

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


KNOWN_KEYS = [
    'ANIMA_R2_ENDPOINT',
    'ANIMA_R2_ACCESS_KEY',
    'ANIMA_R2_SECRET_KEY',
    'ANIMA_R2_BUCKET',
    'CLOUDFLARE_API_TOKEN',
    'YOUTUBE_API_KEY',
    'YOUTUBE_OAUTH_TOKEN',
    'RUNPOD_API_KEY',
    'GITHUB_TOKEN',
    'OPENAI_API_KEY',
    'ANTHROPIC_API_KEY',
    'HF_TOKEN',
]

ENV_SEARCH_PATHS = [
    Path.home() / "Dev" / "TECS-L" / ".env",
    Path.home() / "Dev" / "anima" / ".env",
    Path.home() / ".env",
]


def load_env_file(path: str) -> dict:
    """Parse .env file."""
    result = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                result[key.strip()] = value.strip()
    return result


def main():
    parser = argparse.ArgumentParser(description="Setup Secrets")
    parser.add_argument("--from-env", type=str, help=".env 파일 경로")
    parser.add_argument("--set", type=str, action="append", help="KEY=VALUE 직접 설정")
    parser.add_argument("--list", action="store_true", help="저장된 키 목록")
    parser.add_argument("--export", action="store_true", help="환경변수로 내보내기 명령 출력")
    parser.add_argument("--auto", action="store_true", help="자동: .env 찾아서 저장")
    args = parser.parse_args()

    vault = SecretVault()

    if args.list:
        print("=== Vault 저장 키 ===\n")
        for k in KNOWN_KEYS:
            v = vault.get(k)
            if v:
                print(f"  ✅ {k}: {v[:12]}...")
            else:
                print(f"  ❌ {k}")
        return

    if args.export:
        print("# 환경변수 내보내기 (셸에 복붙):")
        for k in KNOWN_KEYS:
            v = vault.get(k)
            if v:
                print(f"export {k}={v}")
        return

    if args.set:
        for item in args.set:
            if '=' in item:
                k, v = item.split('=', 1)
                vault.set(k.strip(), v.strip())
                print(f"  ✅ {k.strip()}: 저장됨")
        return

    # .env 파일에서 로드
    env_path = args.from_env
    if not env_path:
        # 자동 검색
        for p in ENV_SEARCH_PATHS:
            if p.exists():
                env_path = str(p)
                break

    if not env_path or not os.path.exists(env_path):
        print("  .env 파일을 찾을 수 없습니다.")
        print(f"  검색 경로: {[str(p) for p in ENV_SEARCH_PATHS]}")
        print(f"  직접 지정: python3 setup_secrets.py --from-env /path/.env")
        return

    print(f"=== {env_path} → Vault 저장 ===\n")
    env_data = load_env_file(env_path)

    saved = 0
    for key in KNOWN_KEYS:
        if key in env_data:
            vault.set(key, env_data[key])
            print(f"  ✅ {key}: {env_data[key][:12]}...")
            saved += 1

    # .env에 있지만 KNOWN_KEYS에 없는 것도 저장
    for key, value in env_data.items():
        if key not in KNOWN_KEYS and not key.startswith('#'):
            vault.set(key, value)
            print(f"  ✅ {key}: {value[:12]}... (추가)")
            saved += 1

    print(f"\n  {saved}개 저장 완료!")
    print(f"  {vault.status()}")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
