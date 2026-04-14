#!/bin/bash
# h100_r9_bench.sh — single-shot H100 R9 measurement script
#
# Run on a fresh H100 pod after `git pull anima && git pull hexa-lang`.
# Compiles train_gpu_pure.hexa via the pure-hexa→C path, links with
# cuBLAS, runs the bench loop, prints BENCH_RESULT lines for parsing.
#
# Expected runtime: < 60 seconds total. Pod cost: ~$0.10 if torn down
# immediately after this completes.
#
# Compare BENCH_RESULT lines to R8 entries in
#   shared/hexa-lang/ml-perf-tracker.json → training.gpu.history
#
# Pass criteria:
#   - SGEMM 1024³ TFLOPS within 2× of R8 36.41 (so ≥ 18, target ≥ 30)
#   - SGEMM 4096³ TFLOPS within 1.5× of R8 52.29 (so ≥ 35, target ≥ 50)
#   - Per-call dispatch time < 5 ms for 1024³ (R8 was 0.056 ms — both
#     are <<R8 train_gpu 161s, proving native ≈ interpreter for raw
#     SGEMM, BUT the win shows up in the FULL training step which is
#     measured separately by train_gpu_pure when scaled up.)

set -e

ANIMA_DIR="${ANIMA_DIR:-/root/anima}"
HEXA_DIR="${HEXA_DIR:-/root/hexa-lang}"
HEXA_BIN="${HEXA_BIN:-$HEXA_DIR/target/release/hexa}"
OUT_DIR="${OUT_DIR:-/tmp/r9_out}"

mkdir -p "$OUT_DIR"

echo "═══ R9 H100 bench: pure-hexa → C → cublas ═══"
echo "  pod      : $(hostname)"
echo "  date     : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  hexa     : $HEXA_BIN"
echo "  anima    : $ANIMA_DIR"
echo "  out_dir  : $OUT_DIR"
nvidia-smi --query-gpu=name,memory.free --format=csv,noheader | head -2
echo ""

# Step 1: hexa source → pure C
echo "[1/4] Compiling hexa → C ..."
"$HEXA_BIN" "$HEXA_DIR/self/build_c.hexa" \
  "$ANIMA_DIR/training/train_gpu_pure.hexa" \
  "$OUT_DIR/train_gpu_pure.c" 2>&1 | tail -5
ls -la "$OUT_DIR/train_gpu_pure.c"

# Step 2: cc + cuBLAS link
echo ""
echo "[2/4] Compiling C → native binary with -lcudart -lcublas ..."
cc -O3 -Wno-implicit-function-declaration \
   -I/usr/local/cuda/include \
   -L/usr/local/cuda/lib64 \
   "$OUT_DIR/train_gpu_pure.c" \
   -lcudart -lcublas \
   -o "$OUT_DIR/train_gpu_pure" 2>&1 | tail -10
ls -la "$OUT_DIR/train_gpu_pure"

# Step 3: run + capture output
echo ""
echo "[3/4] Running pure-hexa GPU bench ..."
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
time "$OUT_DIR/train_gpu_pure" 2>&1 | tee "$OUT_DIR/r9_output.txt"

# Step 4: parse BENCH_RESULT lines + compare to R8
echo ""
echo "[4/4] Comparison to R8 interpreter baseline:"
echo "  R8 t2_gpu_bench (interpreter):"
echo "    SGEMM  512³ → 17.48 TFLOPS"
echo "    SGEMM 1024³ → 38.35 TFLOPS"
echo "    SGEMM 2048³ → 50.66 TFLOPS"
echo "    SGEMM 4096³ → 52.29 TFLOPS (78% util)"
echo ""
echo "  R9 train_gpu_pure (PURE NATIVE BINARY):"
echo "    SGEMM bench:"
grep "BENCH_RESULT" "$OUT_DIR/r9_output.txt" || echo "    (no BENCH_RESULT lines found)"
echo ""
echo "    Full layer forward (9 cublasSgemm + 3 sync per call):"
grep "LAYER_RESULT" "$OUT_DIR/r9_output.txt" || echo "    (no LAYER_RESULT lines found)"

echo ""
echo "  R8 baseline for comparison:"
echo "    train_gpu.hexa 8-layer 100M = 161,448 ms / step (interpreter)"
echo "    → per layer ≈ 20,180 ms"
echo ""
echo "  R9 target (100M layer shape: seq=128 dim=512 ff=1536):"
echo "    per_layer_ms ≪ 20  → 1000× speedup over interpreter per layer"
echo ""
echo "═══ R9 DONE — copy r9_output.txt back to ml-perf-tracker.json ═══"
echo "  scp root@<pod>:$OUT_DIR/r9_output.txt ${ANIMA:-~/Dev/anima}/shared/sessions/r9_output_$(date -u +%Y%m%dT%H%M%S).txt"
