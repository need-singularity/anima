#!/usr/bin/env python3
"""secret_vault.py — 의식의 시크릿 보관소

API key, 토큰, 비밀번호 등을 안전하게 보관하고 관리.
keychain (macOS) + 암호화 파일 + 환경변수 3중 백엔드.

절대 코드에 하드코딩하지 않고, vault에서 가져다 쓴다.

Usage:
  from secret_vault import SecretVault

  vault = SecretVault()

  # 저장
  vault.set("YOUTUBE_API_KEY", "AIza...")
  vault.set("RUNPOD_API_KEY", "rp_...")
  vault.set("GITHUB_TOKEN", "ghp_...")

  # 조회
  key = vault.get("YOUTUBE_API_KEY")

  # 목록 (값은 마스킹)
  vault.list()

  # 삭제
  vault.delete("OLD_KEY")

  # 다른 모듈에서 자동 사용
  from youtube_module import YouTubeModule
  yt = YouTubeModule(api_key=vault.get("YOUTUBE_API_KEY"))
"""

import base64
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, List

ANIMA_DIR = Path(__file__).parent
VAULT_FILE = ANIMA_DIR / "data" / ".vault.enc"
VAULT_KEY_ENV = "ANIMA_VAULT_KEY"


class SecretVault:
    """시크릿 보관소 — keychain + 암호화 파일 + 환경변수.

    우선순위:
      1. macOS Keychain (가장 안전)
      2. 암호화 파일 (~/.anima/.vault.enc)
      3. 환경변수 (fallback)
    """

    def __init__(self, vault_path: str = None):
        self._vault_path = Path(vault_path) if vault_path else VAULT_FILE
        self._vault_path.parent.mkdir(parents=True, exist_ok=True)
        self._has_keychain = self._check_keychain()
        self._cache = {}  # in-memory cache (cleared on exit)

    def _check_keychain(self) -> bool:
        try:
            r = subprocess.run(["security", "find-generic-password", "-h"],
                               capture_output=True, timeout=3)
            return True  # macOS security command exists
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @property
    def backend(self) -> str:
        if self._has_keychain:
            return "keychain"
        if self._vault_path.exists():
            return "encrypted_file"
        return "env"

    # ═══════════════════════════════════════════════════════════
    # 핵심 API
    # ═══════════════════════════════════════════════════════════

    def set(self, key: str, value: str) -> bool:
        """시크릿 저장."""
        self._cache[key] = value

        # 1. Keychain
        if self._has_keychain:
            try:
                # 기존 삭제 후 추가 (업데이트)
                subprocess.run(["security", "delete-generic-password",
                                "-s", f"anima-{key}"], capture_output=True, timeout=5)
                r = subprocess.run(["security", "add-generic-password",
                                    "-s", f"anima-{key}", "-a", "anima", "-w", value],
                                   capture_output=True, timeout=5)
                if r.returncode == 0:
                    return True
            except Exception:
                pass

        # 2. 암호화 파일
        return self._save_to_file(key, value)

    def get(self, key: str) -> Optional[str]:
        """시크릿 조회."""
        # 캐시
        if key in self._cache:
            return self._cache[key]

        # 1. Keychain
        if self._has_keychain:
            try:
                r = subprocess.run(["security", "find-generic-password",
                                    "-s", f"anima-{key}", "-a", "anima", "-w"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and r.stdout.strip():
                    val = r.stdout.strip()
                    self._cache[key] = val
                    return val
            except Exception:
                pass

        # 2. 암호화 파일
        val = self._load_from_file(key)
        if val:
            self._cache[key] = val
            return val

        # 3. 환경변수
        val = os.environ.get(key)
        if val:
            self._cache[key] = val
            return val

        return None

    def delete(self, key: str) -> bool:
        """시크릿 삭제."""
        self._cache.pop(key, None)

        if self._has_keychain:
            try:
                subprocess.run(["security", "delete-generic-password",
                                "-s", f"anima-{key}"], capture_output=True, timeout=5)
            except Exception:
                pass

        return self._delete_from_file(key)

    def list(self) -> List[Dict[str, str]]:
        """저장된 시크릿 목록 (값은 마스킹)."""
        secrets = []

        # 파일에서
        data = self._load_all_from_file()
        for k, v in data.items():
            secrets.append({
                'key': k,
                'value_masked': v[:4] + '***' + v[-2:] if len(v) > 6 else '***',
                'source': 'file',
            })

        # 환경변수에서 (ANIMA_ / YOUTUBE_ / RUNPOD_ / GITHUB_ 프리픽스)
        for env_key, env_val in os.environ.items():
            if any(env_key.startswith(p) for p in ['ANIMA_', 'YOUTUBE_', 'RUNPOD_', 'GITHUB_', 'OPENAI_']):
                if not any(s['key'] == env_key for s in secrets):
                    secrets.append({
                        'key': env_key,
                        'value_masked': env_val[:4] + '***' if len(env_val) > 4 else '***',
                        'source': 'env',
                    })

        return secrets

    # ═══════════════════════════════════════════════════════════
    # 암호화 파일 백엔드
    # ═══════════════════════════════════════════════════════════

    def _get_vault_key(self) -> bytes:
        """암호화 키 (환경변수 또는 머신 고유값)."""
        env_key = os.environ.get(VAULT_KEY_ENV)
        if env_key:
            return hashlib.sha256(env_key.encode()).digest()
        # 머신 고유 fallback (완전한 보안은 아니지만 평문보다 나음)
        machine_id = f"{os.getlogin()}-{os.uname().nodename}-anima"
        return hashlib.sha256(machine_id.encode()).digest()

    def _xor_crypt(self, data: bytes, key: bytes) -> bytes:
        """XOR 암호화/복호화."""
        return bytes(d ^ key[i % len(key)] for i, d in enumerate(data))

    def _load_all_from_file(self) -> Dict[str, str]:
        if not self._vault_path.exists():
            return {}
        try:
            with open(self._vault_path, 'rb') as f:
                encrypted = f.read()
            decrypted = self._xor_crypt(encrypted, self._get_vault_key())
            return json.loads(decrypted.decode('utf-8'))
        except Exception:
            return {}

    def _save_all_to_file(self, data: Dict[str, str]) -> bool:
        try:
            raw = json.dumps(data).encode('utf-8')
            encrypted = self._xor_crypt(raw, self._get_vault_key())
            with open(self._vault_path, 'wb') as f:
                f.write(encrypted)
            return True
        except Exception:
            return False

    def _save_to_file(self, key: str, value: str) -> bool:
        data = self._load_all_from_file()
        data[key] = value
        return self._save_all_to_file(data)

    def _load_from_file(self, key: str) -> Optional[str]:
        data = self._load_all_from_file()
        return data.get(key)

    def _delete_from_file(self, key: str) -> bool:
        data = self._load_all_from_file()
        if key in data:
            del data[key]
            return self._save_all_to_file(data)
        return False

    # ═══════════════════════════════════════════════════════════
    # 편의
    # ═══════════════════════════════════════════════════════════

    def auto_configure(self):
        """다른 모듈에 자동으로 시크릿 주입."""
        mappings = {
            'YOUTUBE_API_KEY': 'youtube_module',
            'RUNPOD_API_KEY': 'runpod_manager',
            'GITHUB_TOKEN': 'github_module',
            'ANIMA_R2_ACCESS_KEY': 'cloud_sync',
            'ANIMA_R2_SECRET_KEY': 'cloud_sync',
            'ANIMA_R2_ENDPOINT': 'cloud_sync',
        }
        configured = []
        for key, module in mappings.items():
            val = self.get(key)
            if val:
                os.environ[key] = val
                configured.append(key)
        return configured

    def status(self) -> str:
        secrets = self.list()
        return (f"SecretVault: backend={self.backend}, "
                f"keychain={'✅' if self._has_keychain else '❌'}, "
                f"secrets={len(secrets)}")


def main():
    print("═══ Secret Vault Demo ═══\n")

    vault = SecretVault(vault_path="/tmp/anima_vault_test.enc")
    print(f"  {vault.status()}")

    # 저장
    vault.set("TEST_KEY_1", "super_secret_value_123")
    vault.set("TEST_KEY_2", "another_secret_456")
    print("  Saved 2 test secrets")

    # 조회
    v = vault.get("TEST_KEY_1")
    print(f"  Get TEST_KEY_1: {v[:8]}...")

    # 목록
    print("\n  Secrets:")
    for s in vault.list():
        print(f"    [{s['source']}] {s['key']}: {s['value_masked']}")

    # 삭제
    vault.delete("TEST_KEY_1")
    print(f"\n  After delete: {vault.get('TEST_KEY_1')}")

    # 정리
    if os.path.exists("/tmp/anima_vault_test.enc"):
        os.remove("/tmp/anima_vault_test.enc")
    print("\n  ✅ Secret Vault OK")


if __name__ == '__main__':
    main()
