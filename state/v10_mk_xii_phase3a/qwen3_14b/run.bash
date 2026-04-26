#!/usr/bin/env bash
set -uo pipefail
cd "/Users/ghost/core/anima"
MEASURE_CMD="$(cat '/Users/ghost/core/anima/state/v10_mk_xii_phase3a/qwen3_14b/measure_cmd.sh')"
hexa run tool/anima_runpod_orchestrator.hexa run \
  --pod-name "anima-mkxii3a-qwen3_14b" \
  --gpu-id "NVIDIA H100 80GB HBM3" \
  --image "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04" \
  --upload "/tmp/anima_phi_v3_canonical_helper.hexa_tmp:/workspace/anima_phi_v3_canonical_helper.py" \
  --upload "/tmp/anima_an11b_eigen_helper.hexa_tmp:/workspace/anima_an11b_eigen_helper.py" \
  --upload "/tmp/anima_b_tom_helper.hexa_tmp:/workspace/anima_b_tom_helper.py" \
  --upload "/tmp/anima_cmt_helper.hexa_tmp:/workspace/anima_cmt_helper.py" \
  --command "${MEASURE_CMD}" \
  --download "/workspace/out:/Users/ghost/core/anima/state/v10_mk_xii_phase3a/qwen3_14b" \
  --max-cost 0.70 --max-runtime-min 22 --auto-terminate \
  --output "/Users/ghost/core/anima/state/v10_mk_xii_phase3a/qwen3_14b/runpod_run.json" --run-id "mkxii-3a-qwen3_14b"
