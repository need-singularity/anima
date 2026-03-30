#!/bin/bash
# Anima 환경 설정 스크립트
# Usage: bash setup.sh          # 전체 설치
#        bash setup.sh --minimal # 최소 설치

set -e

echo "═══ Anima Setup ═══"

# Python 확인
python3 --version || { echo "❌ Python3 필요"; exit 1; }

# 최소 설치
pip3 install torch numpy websockets boto3

if [ "$1" != "--minimal" ]; then
    # 전체 설치
    pip3 install -r requirements.txt

    # macOS 전용
    if [ "$(uname)" = "Darwin" ]; then
        brew install portaudio opencv 2>/dev/null || true
        brew install whisper-cli 2>/dev/null || true
    fi

    # Rust (anima-rs, phi-rs)
    if command -v cargo &>/dev/null; then
        echo "Rust OK"
        cd anima-rs && maturin build --release 2>/dev/null && cd ..
    fi
fi

# 시크릿 설정
python3 setup_secrets.py 2>/dev/null || true

# 체크포인트 다운로드
mkdir -p checkpoints/clm_v2
if [ ! -f checkpoints/clm_v2/final.pt ]; then
    echo "체크포인트 다운로드..."
    wget -q https://pub-ce65aaa63c864b889ad793d3d26aa3aa.r2.dev/clm-v2/latest.pt \
        -O checkpoints/clm_v2/final.pt 2>/dev/null || echo "⚠️ 체크포인트 다운로드 실패"
fi

echo "✅ 설치 완료!"
echo "실행: python3 anima_unified.py --web"
