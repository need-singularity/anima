#!/usr/bin/env bash
# /Users/ghost/core/anima/state/v10_mk_xii_phase3a/launch_phase3a.bash
# Mk.XII v2 Phase 3a 13B pilot fan-out (axis 99).
# 3-bb (Llama-13B gated → deferred) × 4-axis parallel pods.
# raw#9 strict: 기존 4 helpers 재사용 (anima_an11b_eigen / anima_phi_v3_canonical /
#                anima_b_tom / anima_cmt). 신규 helper 없음.
# raw#37 transient: helpers emit /tmp via hexa --selftest.
# raw#10 honest substitution:
#   - Llama-3B gated for `dancinlife` (axis 86 unblocked NOT) → deferred
#   - gemma-2-27b 너무 비싸 → gemma-2-9b 대체 (12B-class equivalent)
#   - Mistral-Small-24B → Mistral-Nemo-12B (cost cap)
#
# COST CAP $2.00 hard. 3 pods × ~12-15min × $2.99/hr ≈ $0.55-0.75/pod = $1.65-2.25.
# auto_terminate=true, max-cost 0.70/pod, max-runtime 22min.

set -uo pipefail

ANIMA="/Users/ghost/core/anima"
OUT_BASE="${ANIMA}/state/v10_mk_xii_phase3a"
HF_TOKEN_FILE="${ANIMA}/.secrets/hf_token"

cd "${ANIMA}"

# --- Step 0: emit helpers via selftest (raw#37) ---
echo "[phase3a] === STEP 0: emit 4 axis helpers ==="
hexa run tool/anima_phi_v3_canonical.hexa --selftest 2>&1 | tail -3
hexa run tool/anima_an11b_eigen.hexa --selftest 2>&1 | tail -3
hexa run tool/anima_b_tom.hexa --selftest 2>&1 | tail -3
hexa run tool/anima_cmt.hexa --selftest 2>&1 | tail -3

for h in /tmp/anima_phi_v3_canonical_helper.hexa_tmp \
         /tmp/anima_an11b_eigen_helper.hexa_tmp \
         /tmp/anima_b_tom_helper.hexa_tmp \
         /tmp/anima_cmt_helper.hexa_tmp; do
  if [ ! -f "$h" ]; then
    echo "ERR: missing helper $h"; exit 2
  fi
done
echo "[phase3a] all 4 helpers present"

# --- Backbones (raw#10 honest substitution) ---
declare -a BACKBONES=(
  "mistral_nemo_12b:mistralai/Mistral-Nemo-Base-2407"
  "qwen3_14b:Qwen/Qwen2.5-14B"
  "gemma_9b:google/gemma-2-9b"
)

# --- Per-pod 4-axis sequential SSH command builder ---
build_measure_cmd() {
  local hf_id="$1"
  cat <<EOCMD
set -e
mkdir -p /workspace/out
cat > /workspace/.hf_token <<HFEOT
$(cat ${HF_TOKEN_FILE})
HFEOT
pip install -q transformers accelerate sentencepiece 2>&1 | tail -3
export ANIMA_BASE='${hf_id}'
echo '=== AXIS 1: Phi v3 (load=1, all axes share weights via re-load) ==='
ANIMA_OUTPUT=/workspace/out/phi_v3.json python3 /workspace/anima_phi_v3_canonical_helper.py 2>&1 | tail -8
echo '=== AXIS 2: AN11(b) ==='
ANIMA_OUT_HLAST=/workspace/out/an11b_h_last.json ANIMA_OUT_EIGEN=/workspace/out/an11b.json python3 /workspace/anima_an11b_eigen_helper.py 2>&1 | tail -8
echo '=== AXIS 3: B-ToM ==='
ANIMA_OUTPUT=/workspace/out/btom.json python3 /workspace/anima_b_tom_helper.py 2>&1 | tail -8
echo '=== AXIS 4: CMT ==='
ANIMA_OUTPUT=/workspace/out/cmt.json python3 /workspace/anima_cmt_helper.py 2>&1 | tail -8
ls -la /workspace/out/
EOCMD
}

# --- Step 1: launch 3 pods in parallel (background) ---
echo "[phase3a] === STEP 1: parallel pod launches ==="
PIDS=()
for entry in "${BACKBONES[@]}"; do
  short="${entry%%:*}"
  hf_id="${entry##*:}"
  pod_name="anima-mkxii3a-${short}"
  out_dir="${OUT_BASE}/${short}"
  mkdir -p "${out_dir}/out"

  # Build per-backbone runner script (raw#37 transient, .bash kept for traceability)
  runner="${out_dir}/run.bash"
  measure_cmd_file="${out_dir}/measure_cmd.sh"
  build_measure_cmd "${hf_id}" > "${measure_cmd_file}"

  cat > "${runner}" <<EORUN
#!/usr/bin/env bash
set -uo pipefail
cd "${ANIMA}"
MEASURE_CMD="\$(cat '${measure_cmd_file}')"
hexa run tool/anima_runpod_orchestrator.hexa run \\
  --pod-name "${pod_name}" \\
  --gpu-id "NVIDIA H100 80GB HBM3" \\
  --image "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04" \\
  --upload "/tmp/anima_phi_v3_canonical_helper.hexa_tmp:/workspace/anima_phi_v3_canonical_helper.py" \\
  --upload "/tmp/anima_an11b_eigen_helper.hexa_tmp:/workspace/anima_an11b_eigen_helper.py" \\
  --upload "/tmp/anima_b_tom_helper.hexa_tmp:/workspace/anima_b_tom_helper.py" \\
  --upload "/tmp/anima_cmt_helper.hexa_tmp:/workspace/anima_cmt_helper.py" \\
  --command "\${MEASURE_CMD}" \\
  --download "/workspace/out:${out_dir}" \\
  --max-cost 0.70 --max-runtime-min 22 --auto-terminate \\
  --output "${out_dir}/runpod_run.json" --run-id "mkxii-3a-${short}"
EORUN
  chmod +x "${runner}"

  echo "[phase3a] launching ${pod_name} (${hf_id}) bg..."
  nohup bash "${runner}" > "${out_dir}/nohup.log" 2>&1 &
  PIDS+=($!)
  sleep 5  # stagger pod create
done

echo "[phase3a] ${#PIDS[@]} pods launched, PIDs: ${PIDS[*]}"
echo "[phase3a] === STEP 2: waiting for completion ==="

EXIT_STATUSES=()
for pid in "${PIDS[@]}"; do
  if wait "$pid"; then
    EXIT_STATUSES+=(0)
  else
    EXIT_STATUSES+=($?)
  fi
done

echo "[phase3a] exit statuses: ${EXIT_STATUSES[*]}"
echo "[phase3a] === outputs ==="
for entry in "${BACKBONES[@]}"; do
  short="${entry%%:*}"
  echo "--- ${short} ---"
  ls -la "${OUT_BASE}/${short}/out/" 2>&1 || echo "  (no out dir)"
done
echo "[phase3a] launch driver DONE"
