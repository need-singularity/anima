#!/usr/bin/env bash
# build.sh — compile libtrain_native.so on H100 RunPod pod
#
# Usage:
#   ./build.sh          # GPU build (nvcc, default)
#   ./build.sh cpu      # CPU-only fallback (gcc)
#   ./build.sh test     # GPU build + smoke test
#   ./build.sh cpu-test # CPU build + smoke test

set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

SRC_FILES="train_ffi.c train_step.c"
OUT="libtrain_native.so"
MODE="${1:-gpu}"

# ── Colors ──
RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
RST='\033[0m'

ok()   { printf "${GRN}[OK]${RST} %s\n"   "$1"; }
fail() { printf "${RED}[FAIL]${RST} %s\n" "$1"; exit 1; }
info() { printf "${YEL}[INFO]${RST} %s\n" "$1"; }

# ══════════════════════════════════════════════════════════════
# GPU build: nvcc
# ══════════════════════════════════════════════════════════════
build_gpu() {
    if ! command -v nvcc &>/dev/null; then
        fail "nvcc not found. Install CUDA toolkit or use: ./build.sh cpu"
    fi

    NVCC_VER=$(nvcc --version | grep -oP 'release \K[0-9]+\.[0-9]+')
    info "nvcc ${NVCC_VER} detected"

    # Detect GPU compute capability (default sm_90 for H100)
    ARCH="sm_90"
    if command -v nvidia-smi &>/dev/null; then
        GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || true)
        info "GPU: ${GPU_NAME:-unknown}"
        case "$GPU_NAME" in
            *H100*|*H200*) ARCH="sm_90" ;;
            *A100*)        ARCH="sm_80" ;;
            *4090*|*4080*) ARCH="sm_89" ;;
            *3090*|*3080*) ARCH="sm_86" ;;
            *)             ARCH="sm_80"; info "Unknown GPU, defaulting to ${ARCH}" ;;
        esac
    fi
    info "Target arch: ${ARCH}"

    info "Compiling ${OUT} (GPU, ${ARCH})..."
    nvcc -O3 -shared -Xcompiler -fPIC \
         -arch="${ARCH}" \
         -lcublas -lcudart \
         ${SRC_FILES} -o "${OUT}"

    ok "Built ${DIR}/${OUT} ($(stat --printf='%s' "${OUT}" 2>/dev/null || stat -f'%z' "${OUT}") bytes)"
}

# ══════════════════════════════════════════════════════════════
# CPU-only fallback: gcc
# ══════════════════════════════════════════════════════════════
build_cpu() {
    if ! command -v gcc &>/dev/null; then
        fail "gcc not found"
    fi

    GCC_VER=$(gcc --version | head -1)
    info "${GCC_VER}"

    info "Compiling ${OUT} (CPU fallback, no CUDA)..."
    gcc -O2 -shared -fPIC \
        -lm \
        ${SRC_FILES} -o "${OUT}"

    ok "Built ${DIR}/${OUT} — CPU stub (no real GPU ops)"
}

# ══════════════════════════════════════════════════════════════
# Smoke test: init + cleanup round-trip
# ══════════════════════════════════════════════════════════════
smoke_test() {
    if [ ! -f "${DIR}/${OUT}" ]; then
        fail "${OUT} not found — build first"
    fi

    info "Running smoke test..."

    SMOKE_SRC=$(mktemp /tmp/smoke_XXXXXX.c)
    SMOKE_BIN=$(mktemp /tmp/smoke_XXXXXX)

    cat > "${SMOKE_SRC}" <<'SMOKE_EOF'
#include <stdio.h>
#include <dlfcn.h>
#include <stdlib.h>

int main(void) {
    void* lib = dlopen(NULL, RTLD_LAZY);  /* placeholder — we link directly */

    /* These are linked at compile time via the .so */
    extern int  train_ffi_init(int, int, int, int, int, int, int);
    extern void train_ffi_cleanup(void);
    extern int  train_ffi_get_step(void);

    printf("smoke: calling train_ffi_init(2, 64, 4, 16, 128, 256, 32)...\n");
    int ok = train_ffi_init(
        /* n_layers */ 2,
        /* dim      */ 64,
        /* n_heads  */ 4,
        /* head_dim */ 16,
        /* ff_dim   */ 128,
        /* vocab    */ 256,
        /* seq_len  */ 32
    );
    if (ok != 1) {
        fprintf(stderr, "smoke: train_ffi_init returned %d (expected 1)\n", ok);
        return 1;
    }
    printf("smoke: init OK\n");

    int step = train_ffi_get_step();
    printf("smoke: step = %d (expected 0)\n", step);
    if (step != 0) {
        fprintf(stderr, "smoke: unexpected step value\n");
        return 1;
    }

    /* Double-init should return 0 (already initialized) */
    int dup = train_ffi_init(2, 64, 4, 16, 128, 256, 32);
    if (dup != 0) {
        fprintf(stderr, "smoke: double-init returned %d (expected 0)\n", dup);
        return 1;
    }
    printf("smoke: double-init guard OK\n");

    printf("smoke: calling train_ffi_cleanup()...\n");
    train_ffi_cleanup();
    printf("smoke: cleanup OK\n");

    printf("smoke: ALL PASSED\n");
    return 0;
}
SMOKE_EOF

    # Compile and link against the .so
    if [[ "$MODE" == *cpu* ]]; then
        gcc -O0 -o "${SMOKE_BIN}" "${SMOKE_SRC}" \
            -L"${DIR}" -ltrain_native -lm -ldl \
            -Wl,-rpath,"${DIR}"
    else
        # GPU: use gcc to compile the test, link against the nvcc-built .so
        gcc -O0 -o "${SMOKE_BIN}" "${SMOKE_SRC}" \
            -L"${DIR}" -ltrain_native -ldl \
            -L/usr/local/cuda/lib64 -lcudart -lcublas -lm \
            -Wl,-rpath,"${DIR}" -Wl,-rpath,/usr/local/cuda/lib64
    fi

    # Run
    LD_LIBRARY_PATH="${DIR}${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" "${SMOKE_BIN}"
    RC=$?

    rm -f "${SMOKE_SRC}" "${SMOKE_BIN}"

    if [ $RC -eq 0 ]; then
        ok "Smoke test passed"
    else
        fail "Smoke test failed (exit ${RC})"
    fi
}

# ══════════════════════════════════════════════════════════════
# Main dispatch
# ══════════════════════════════════════════════════════════════
case "$MODE" in
    gpu)
        build_gpu
        ;;
    cpu)
        build_cpu
        ;;
    test)
        build_gpu
        smoke_test
        ;;
    cpu-test)
        build_cpu
        smoke_test
        ;;
    *)
        echo "Usage: $0 [gpu|cpu|test|cpu-test]"
        exit 1
        ;;
esac
