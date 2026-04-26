#!/usr/bin/env bash
set -uo pipefail
cd "/Users/ghost/core/anima"
MEASURE_CMD="$(cat '/Users/ghost/core/anima/state/v10_mk_xii_qwen_family_internal/qwen25_7b/measure_cmd.sh')"
hexa run tool/anima_runpod_orchestrator.hexa run \
  --pod-name "anima-mkxiiqwen-qwen25_7b" \
  --gpu-id "NVIDIA H100 80GB HBM3" \
  --image "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04" \
  --upload "/tmp/anima_phi_v3_canonical_helper.hexa_tmp:/workspace/anima_phi_v3_canonical_helper.py" \
  --command "${MEASURE_CMD}" \
  --download "/workspace/out:/Users/ghost/core/anima/state/v10_mk_xii_qwen_family_internal/qwen25_7b" \
  --max-cost 0.30 --max-runtime-min 15 --auto-terminate \
  --output "/Users/ghost/core/anima/state/v10_mk_xii_qwen_family_internal/qwen25_7b/runpod_run.json" --run-id "mkxii-qwen-qwen25_7b"
