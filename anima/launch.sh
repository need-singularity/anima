#!/bin/bash
# Anima Launch — 전부 한 방에
set -e

ANIMA_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ANIMA_DIR"

export KMP_DUPLICATE_LIB_OK=TRUE

# Load environment variables
[ -f "$ANIMA_DIR/.local/.env" ] && set -a && source "$ANIMA_DIR/.local/.env" && set +a
[ -f "$ANIMA_DIR/.env" ] && set -a && source "$ANIMA_DIR/.env" && set +a

echo "=================================================="
echo "  Anima — Full Launch"
echo "=================================================="

# ─── Dependency Check ───
echo ""
echo "  Checking dependencies..."
FAIL=0

check() {
    if python3 -c "$2" 2>/dev/null; then
        echo "  [OK] $1"
    else
        echo "  [!!] $1 — $3"
        FAIL=1
    fi
}

check "torch"      "import torch"           "pip3 install --break-system-packages torch"
check "websockets" "import websockets"       "pip3 install --break-system-packages websockets"
check "numpy"      "import numpy"            "brew install numpy && brew link --overwrite numpy"
check "cv2"        "import cv2"              "brew reinstall opencv"

# CLI tools
for cmd in claude whisper-cli; do
    if command -v $cmd &>/dev/null; then
        echo "  [OK] $cmd"
    else
        echo "  [!!] $cmd — not found"
        FAIL=1
    fi
done

# Camera test
CAM=$(python3 -c "
import cv2
cap = cv2.VideoCapture(0)
print('ok' if cap.isOpened() else 'denied')
cap.release()
" 2>/dev/null || echo "fail")

# R2 Cloud
if [ -n "$ANIMA_R2_ENDPOINT" ]; then
    echo "  [OK] R2 cloud ($ANIMA_R2_BUCKET)"
else
    echo "  [--] R2 cloud (ANIMA_R2_* 환경변수 없음)"
fi

if [ "$CAM" = "ok" ]; then
    echo "  [OK] camera"
else
    echo "  [!!] camera — 시스템 설정 → 개인정보 → 카메라 → Terminal 허용"
fi

# Whisper model
MODEL="/tmp/ggml-base.bin"
if [ -f "$MODEL" ]; then
    echo "  [OK] whisper model"
else
    echo "  [DL] whisper model downloading..."
    curl -sL "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin" -o "$MODEL"
    echo "  [OK] whisper model"
fi

if [ "$FAIL" -eq 1 ]; then
    echo ""
    echo "  Fix the issues above, then re-run."
    exit 1
fi

# ─── Rust VAD build (if not built) ───
if [ -d "$ANIMA_DIR/vad-rs" ]; then
    if [ ! -f "$ANIMA_DIR/vad-rs/target/release/anima-vad" ]; then
        echo ""
        echo "  Building Rust VAD..."
        (cd "$ANIMA_DIR/vad-rs" && cargo build --release 2>/dev/null) &
        VAD_PID=$!
    fi
fi

# ─── Launch ───
echo ""
echo "  Launching Anima (all modules)..."
echo "  Web:  http://localhost:8765"
echo "  Voice: always listening"
echo "  Camera: active"
echo "  Press Ctrl+C to stop"
echo "=================================================="
echo ""

exec python3 "$ANIMA_DIR/anima_unified.py" --all "$@"
