#!/usr/bin/env bash
# /Users/ghost/core/anima/state/v10_mk_xii_qwen_family_internal/launch_qwen_internal.bash
# Mk.XII Phase 3a-followup (axis 109): family-internal Qwen scale test.
# Disentangle aa9a4de3 HMK-B sign FLIP CONFOUNDED (Qwen3-8B → Qwen2.5-14B family change).
#
# Measure: Qwen2.5-7B + Qwen3-14B-Base BASE phi_v3_canonical (parallel pods).
# Reuse on disk:
#   - Qwen2.5-14B  : state/v10_mk_xii_phase3a/qwen3_14b/out/phi_v3.json
#   - Qwen3-8B     : state/v10_phi_v3_canonical/qwen3/out/phi_v3_canonical.json
#                    (or v10_phi_v3_corpus_axis_universal/qwen3_base/out/...)
#
# raw#9 strict: 기존 anima_phi_v3_canonical helper 재사용. NEW helper 없음.
# raw#10 honest: 본 cycle은 phi_v3_canonical ONLY (4-axis 아님). 다른 axes 는 disk reuse 불가.
# COST CAP $0.50 (2 H100 pods × ~3min × $2.99/hr ≈ $0.30).

set -uo pipefail

ANIMA="/Users/ghost/core/anima"
OUT_BASE="${ANIMA}/state/v10_mk_xii_qwen_family_internal"
HF_TOKEN_FILE="${ANIMA}/.secrets/hf_token"

cd "${ANIMA}"

# --- Step 0: emit helper (raw#37 transient) ---
echo "[qwen_internal] === STEP 0: emit phi_v3_canonical helper ==="
hexa run tool/anima_phi_v3_canonical.hexa --selftest 2>&1 | tail -3

if [ ! -f /tmp/anima_phi_v3_canonical_helper.hexa_tmp ]; then
  echo "ERR: missing helper /tmp/anima_phi_v3_canonical_helper.hexa_tmp"
  exit 2
fi
echo "[qwen_internal] helper present"

# --- Backbones ---
declare -a BACKBONES=(
  "qwen25_7b:Qwen/Qwen2.5-7B"
  "qwen3_14b:Qwen/Qwen3-14B-Base"
)

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
echo '=== AXIS: Phi v3 canonical (BASE only) ==='
ANIMA_OUTPUT=/workspace/out/phi_v3_canonical.json python3 /workspace/anima_phi_v3_canonical_helper.py 2>&1 | tail -8
ls -la /workspace/out/
EOCMD
}

# --- Step 1: launch 2 pods in parallel (background) ---
echo "[qwen_internal] === STEP 1: parallel pod launches ==="
PIDS=()
for entry in "${BACKBONES[@]}"; do
  short="${entry%%:*}"
  hf_id="${entry##*:}"
  pod_name="anima-mkxiiqwen-${short}"
  out_dir="${OUT_BASE}/${short}"
  mkdir -p "${out_dir}/out"

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
  --command "\${MEASURE_CMD}" \\
  --download "/workspace/out:${out_dir}" \\
  --max-cost 0.30 --max-runtime-min 15 --auto-terminate \\
  --output "${out_dir}/runpod_run.json" --run-id "mkxii-qwen-${short}"
EORUN
  chmod +x "${runner}"

  echo "[qwen_internal] launching ${pod_name} (${hf_id}) bg..."
  nohup bash "${runner}" > "${out_dir}/nohup.log" 2>&1 &
  PIDS+=($!)
  sleep 5
done

echo "[qwen_internal] ${#PIDS[@]} pods launched, PIDs: ${PIDS[*]}"
echo "[qwen_internal] === STEP 2: waiting for completion ==="

EXIT_STATUSES=()
for pid in "${PIDS[@]}"; do
  if wait "$pid"; then
    EXIT_STATUSES+=(0)
  else
    EXIT_STATUSES+=($?)
  fi
done

echo "[qwen_internal] exit statuses: ${EXIT_STATUSES[*]}"
echo "[qwen_internal] === outputs ==="
for entry in "${BACKBONES[@]}"; do
  short="${entry%%:*}"
  echo "--- ${short} ---"
  ls -la "${OUT_BASE}/${short}/out/" 2>&1 || echo "  (no out dir)"
done
echo "[qwen_internal] launch driver DONE"
