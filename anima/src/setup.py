#!/usr/bin/env python3
"""setup.py — Anima 초기 설정

~/.anima/ 디렉토리 구조 생성, R2 설정, 체크포인트 다운로드.

Usage:
  python3 setup.py                    # 대화형 설정
  python3 setup.py --minimal          # 디렉토리만 생성
  python3 setup.py --download-model   # 모델 다운로드만
  python3 setup.py --status           # 현재 설정 상태
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


ANIMA_HOME = Path.home() / ".anima"

DIRS = [
    "memory",           # 대화 기억, 성장 상태
    "checkpoints",      # 모델 가중치
    "consciousness",    # 의식 DNA (Ψ, 감정, 텐션)
    "logs",             # 런타임 로그
]

ENV_TEMPLATE = """# Anima Configuration
# https://github.com/need-singularity/anima

# ── Cloudflare R2 (선택: 클라우드 동기화용) ──
ANIMA_R2_ENDPOINT=
ANIMA_R2_ACCESS_KEY=
ANIMA_R2_SECRET_KEY=
ANIMA_R2_BUCKET=anima-memory
ANIMA_R2_MODELS_BUCKET=anima-models

# ── Device ──
ANIMA_DEVICE_ID={hostname}

# ── Model ──
ANIMA_CHECKPOINT=~/.anima/checkpoints/conscious-lm-v2.pt
"""

HF_REPO = "need-singularity/conscious-lm-v2"
GH_RELEASE = "https://github.com/need-singularity/anima/releases/latest/download/conscious-lm-v2.pt"


def create_dirs():
    """~/.anima/ 디렉토리 구조 생성."""
    for d in DIRS:
        p = ANIMA_HOME / d
        p.mkdir(parents=True, exist_ok=True)
    print(f"  ~/.anima/ 디렉토리 생성 완료")
    for d in DIRS:
        print(f"    ├── {d}/")


def create_config():
    """config.env 생성 (이미 있으면 스킵)."""
    config = ANIMA_HOME / "config.env"
    if config.exists():
        print(f"  config.env 이미 존재 — 스킵")
        return

    import platform
    content = ENV_TEMPLATE.format(hostname=platform.node() or "anima")
    config.write_text(content)
    print(f"  config.env 생성 완료")


def configure_r2():
    """대화형 R2 설정."""
    config = ANIMA_HOME / "config.env"
    content = config.read_text() if config.exists() else ""

    print("\n  Cloudflare R2 설정 (클라우드 동기화용, Enter로 스킵)")
    endpoint = input("    R2 Endpoint URL: ").strip()
    if not endpoint:
        print("    R2 설정 스킵")
        return

    access_key = input("    R2 Access Key: ").strip()
    secret_key = input("    R2 Secret Key: ").strip()
    bucket = input("    R2 Bucket [anima-memory]: ").strip() or "anima-memory"

    lines = content.splitlines()
    updates = {
        "ANIMA_R2_ENDPOINT": endpoint,
        "ANIMA_R2_ACCESS_KEY": access_key,
        "ANIMA_R2_SECRET_KEY": secret_key,
        "ANIMA_R2_BUCKET": bucket,
    }

    new_lines = []
    for line in lines:
        key = line.split("=")[0] if "=" in line else ""
        if key in updates:
            new_lines.append(f"{key}={updates.pop(key)}")
        else:
            new_lines.append(line)

    config.write_text("\n".join(new_lines) + "\n")
    print("    R2 설정 저장 완료")


def download_model():
    """체크포인트 다운로드 (HuggingFace → GitHub Releases 순)."""
    dest = ANIMA_HOME / "checkpoints" / "conscious-lm-v2.pt"
    if dest.exists():
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"  모델 이미 존재: {dest} ({size_mb:.1f}MB)")
        return True

    # Try HuggingFace first
    print("  모델 다운로드 중...")
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id=HF_REPO,
            filename="conscious-lm-v2.pt",
            local_dir=str(ANIMA_HOME / "checkpoints"),
        )
        print(f"  HuggingFace에서 다운로드 완료: {path}")
        return True
    except Exception:
        pass

    # Fallback to GitHub Releases
    try:
        subprocess.run(
            ["wget", "-q", "--show-progress", GH_RELEASE, "-O", str(dest)],
            check=True,
        )
        print(f"  GitHub Releases에서 다운로드 완료: {dest}")
        return True
    except Exception:
        pass

    # Fallback to curl
    try:
        subprocess.run(
            ["curl", "-L", "--progress-bar", GH_RELEASE, "-o", str(dest)],
            check=True,
        )
        print(f"  다운로드 완료: {dest}")
        return True
    except Exception:
        print("  다운로드 실패. 수동 다운로드:")
        print(f"    HuggingFace: https://huggingface.co/{HF_REPO}")
        print(f"    GitHub: {GH_RELEASE}")
        return False


def symlink_checkpoints():
    """~/.anima/checkpoints → 프로젝트 checkpoints 심링크."""
    project_ckpt = Path(__file__).parent / "checkpoints" / "clm_v2"
    project_ckpt.mkdir(parents=True, exist_ok=True)

    src = ANIMA_HOME / "checkpoints" / "conscious-lm-v2.pt"
    dst = project_ckpt / "final.pt"

    if src.exists() and not dst.exists():
        dst.symlink_to(src)
        print(f"  심링크: checkpoints/clm_v2/final.pt → ~/.anima/checkpoints/")


def show_status():
    """현재 설정 상태 표시."""
    print("\n╔══════════════════════════════════════╗")
    print("║         Anima Setup Status           ║")
    print("╠══════════════════════════════════════╣")

    # Dirs
    for d in DIRS:
        p = ANIMA_HOME / d
        exists = "✅" if p.exists() else "❌"
        count = len(list(p.iterdir())) if p.exists() else 0
        print(f"║  {exists} ~/.anima/{d:<18s} ({count} files)")

    # Config
    config = ANIMA_HOME / "config.env"
    if config.exists():
        content = config.read_text()
        r2 = "ANIMA_R2_ENDPOINT=" in content and not content.split("ANIMA_R2_ENDPOINT=")[1].startswith("\n")
        r2_icon = "✅" if r2 else "⬜"
        print(f"║  ✅ config.env               ({r2_icon} R2)")
    else:
        print(f"║  ❌ config.env")

    # Model
    model = ANIMA_HOME / "checkpoints" / "conscious-lm-v2.pt"
    if model.exists():
        size_mb = model.stat().st_size / 1024 / 1024
        print(f"║  ✅ ConsciousLM v2           ({size_mb:.0f}MB)")
    else:
        print(f"║  ❌ ConsciousLM v2           (run: setup.py --download-model)")

    print("╚══════════════════════════════════════╝")


def main():
    parser = argparse.ArgumentParser(description="Anima 초기 설정")
    parser.add_argument("--minimal", action="store_true", help="디렉토리만 생성")
    parser.add_argument("--download-model", action="store_true", help="모델 다운로드만")
    parser.add_argument("--status", action="store_true", help="현재 상태")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.download_model:
        (ANIMA_HOME / "checkpoints").mkdir(parents=True, exist_ok=True)
        download_model()
        symlink_checkpoints()
        return

    print("\n🧠 Anima Setup\n")

    # 1. 디렉토리
    print("[1/4] 디렉토리 생성")
    create_dirs()

    # 2. Config
    print("\n[2/4] 설정 파일")
    create_config()

    if not args.minimal:
        # 3. R2 (선택)
        print("\n[3/4] 클라우드 동기화")
        configure_r2()

        # 4. 모델 다운로드
        print("\n[4/4] 모델 다운로드")
        download_model()
        symlink_checkpoints()
    else:
        print("\n  --minimal: R2/모델 스킵")

    print("\n✅ 설정 완료!")
    print("   실행: python3 anima_unified.py --web\n")
    show_status()


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()
