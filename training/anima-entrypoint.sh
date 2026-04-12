#!/bin/bash
# anima-entrypoint.sh — RunPod H100 컨테이너 시작 시 실행
#
# 1. anima repo git clone/pull
# 2. hexa-lang repo git clone/pull
# 3. hexa-lang cargo build --release (증분)
# 4. GPU smoke test (CUDA 가용 시)
# 5. CMD (기본: sshd)로 인계
#
# Docker 이미지 재빌드 없이 코드 갱신 → 컨테이너 재시작만으로 최신 코드 반영.

set -e

ANIMA_REPO="${ANIMA_REPO:-https://github.com/need-singularity/anima.git}"
ANIMA_BRANCH="${ANIMA_BRANCH:-main}"
ANIMA_DIR="${ANIMA_DIR:-/workspace/anima}"

HEXA_REPO="${HEXA_REPO:-https://github.com/need-singularity/hexa-lang.git}"
HEXA_BRANCH="${HEXA_BRANCH:-main}"
HEXA_DIR="${HEXA_DIR:-/workspace/hexa-lang}"
HEXA_BIN="${HEXA_BIN:-$HEXA_DIR/target/release/hexa}"

# ── helper ──
sync_repo() {
    local label="$1" repo="$2" branch="$3" dir="$4"
    if [ ! -d "$dir/.git" ]; then
        echo "[entrypoint] cloning $label: $repo ($branch) → $dir"
        git clone --depth 1 --branch "$branch" "$repo" "$dir"
    else
        echo "[entrypoint] pulling $label: $branch in $dir"
        ( cd "$dir" && git fetch --depth 1 origin "$branch" && git reset --hard "origin/$branch" )
    fi
    echo "[entrypoint] $label HEAD: $(cd "$dir" && git rev-parse --short HEAD)"
}

# ── 1. anima ──
sync_repo "anima" "$ANIMA_REPO" "$ANIMA_BRANCH" "$ANIMA_DIR"

# ── 2. hexa-lang ──
sync_repo "hexa-lang" "$HEXA_REPO" "$HEXA_BRANCH" "$HEXA_DIR"

# ── 3. cargo build (증분; 변경 없으면 거의 즉시 종료) ──
echo "[entrypoint] cargo build --release (incremental)..."
build_start=$(date +%s)
( cd "$HEXA_DIR" && cargo build --release 2>&1 | tail -5 )
build_end=$(date +%s)
echo "[entrypoint] build elapsed: $((build_end - build_start))s"

if [ -x "$HEXA_BIN" ]; then
    echo "[entrypoint] hexa: $($HEXA_BIN --version 2>/dev/null || echo built)"
else
    echo "[entrypoint] WARNING: $HEXA_BIN not found after build"
fi

# ── 4. GPU smoke test (CUDA 있을 때만, 실패해도 진행) ──
if command -v nvidia-smi &>/dev/null; then
    echo "[entrypoint] GPU detected:"
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader | sed 's/^/    /'
    if [ -x "$HEXA_BIN" ] && [ -f "$HEXA_DIR/self/ml/gpu_smoke_test.hexa" ]; then
        echo "[entrypoint] running gpu_smoke_test.hexa..."
        ( cd "$HEXA_DIR" && "$HEXA_BIN" self/ml/gpu_smoke_test.hexa 2>&1 | tail -10 ) || \
            echo "[entrypoint] smoke test FAILED (non-fatal, continuing)"
    fi
else
    echo "[entrypoint] no GPU (CPU-only mode)"
fi

echo "[entrypoint] handing off to CMD: $*"
exec "$@"
