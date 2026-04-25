#!/usr/bin/env bash
# tool/cp1_serve_launch_mac.bash — CP1 dest1 persona LOCAL on Mac mini M4 16GB
#
# PURPOSE
#   Serve the trained p1 LoRA adapter persistently on Mac mini M4 16GB using
#   llama.cpp (GGUF + Metal). This supersedes cp1_serve_launch.bash (which
#   targets RunPod secureCloud H100) for CP1 production serving after the
#   user's 2026-04-24 decision to run CP1 locally.
#
#   The cloud script is NOT removed — it remains the reference for H100 deploy.
#   This file is the Mac-local path.
#
# PIPELINE
#   1. Merge LoRA into base model   (peft.merge_and_unload → state/cp1_merged_model/)
#   2. Convert HF → GGUF            (llama.cpp/convert_hf_to_gguf.py)
#   3. Quantize GGUF                (llama-quantize, default Q5_K_M)
#   4. Install launchd plist        (~/Library/LaunchAgents/com.anima.cp1-serve.plist)
#   5. Start llama-server           (launchctl load + kickstart)
#   6. Health check                 (curl http://localhost:<port>/health)
#
# USAGE
#   bash tool/cp1_serve_launch_mac.bash --dry-run                          # default
#   bash tool/cp1_serve_launch_mac.bash --apply --yes-i-mean-it            # real
#   bash tool/cp1_serve_launch_mac.bash --help
#
# FLAGS
#   --base-model <id>   HF base model id       (default Qwen/Qwen3-8B)
#   --quant <level>     Q4_K_M | Q5_K_M | Q8_0 (default Q5_K_M)
#   --port <n>          llama-server port      (default 8000)
#
# ENV OVERRIDES
#   CP1_ADAPTER_PATH    adapter dir (default state/trained_adapters/p1/final)
#   CP1_LLAMA_CPP_DIR   llama.cpp checkout     (default /opt/homebrew/share/llama.cpp or ~/llama.cpp)
#
# EXIT
#   0 = dry-run pass OR apply success
#   1 = prereq fail (macOS/brew/llama.cpp/python deps/adapter missing)
#   2 = --apply without --yes-i-mean-it
#   3 = merge/convert/quantize/launchd failure
set -euo pipefail

readonly ANIMA_ROOT="/Users/ghost/core/anima"
readonly ADAPTER_PATH="${CP1_ADAPTER_PATH:-${ANIMA_ROOT}/state/trained_adapters/p1/final}"
readonly MERGED_DIR="${ANIMA_ROOT}/state/cp1_merged_model"
readonly GGUF_FP16="${ANIMA_ROOT}/state/cp1_merged.gguf"
readonly STATE_OUT="${ANIMA_ROOT}/state/cp1_serve_launch_state.json"
readonly PLIST_PATH="${HOME}/Library/LaunchAgents/com.anima.cp1-serve.plist"
readonly TS="$(date -u +%Y%m%dT%H%M%SZ)"
readonly LOG="/tmp/cp1_serve_launch_mac_${TS}.log"

# defaults (overridable via flags)
BASE_MODEL="Qwen/Qwen3-8B"
QUANT="Q5_K_M"
PORT="8000"
MODE="dry-run"
CONFIRM=""

print_help() { sed -n '1,35p' "$0"; }

# --- arg parse ---------------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)       MODE="dry-run"; shift ;;
    --apply)         MODE="apply"; shift ;;
    --yes-i-mean-it) CONFIRM="yes"; shift ;;
    --base-model)    BASE_MODEL="$2"; shift 2 ;;
    --quant)         QUANT="$2"; shift 2 ;;
    --port)          PORT="$2"; shift 2 ;;
    --help|-h)       print_help; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

case "${QUANT}" in
  Q4_K_M|Q5_K_M|Q8_0) : ;;
  *) echo "ERROR: --quant must be Q4_K_M | Q5_K_M | Q8_0 (got: ${QUANT})" >&2; exit 1 ;;
esac

readonly GGUF_QUANT="${ANIMA_ROOT}/state/cp1_merged-${QUANT}.gguf"

exec > >(tee -a "${LOG}") 2>&1
log() { printf '[%s] %s\n' "$(date -u +%H:%M:%SZ)" "$*"; }

log "mode=${MODE} log=${LOG}"
log "base_model=${BASE_MODEL}  adapter=${ADAPTER_PATH}  quant=${QUANT}  port=${PORT}"

# --- prereq check -------------------------------------------------------------
PREREQ_FAIL=0

log "prereq: macOS"
if [[ "$(uname)" != "Darwin" ]]; then
  log "  [FAIL] not macOS (uname=$(uname)). This script is Mac-only."
  log "         For H100 serving use tool/cp1_serve_launch.bash instead."
  PREREQ_FAIL=1
else
  log "  [PASS] Darwin $(uname -r)  arch=$(uname -m)"
fi

log "prereq: brew"
if ! command -v brew >/dev/null 2>&1; then
  log "  [FAIL] brew not installed. Install: https://brew.sh"
  PREREQ_FAIL=1
else
  log "  [PASS] $(brew --version | head -1)"
fi

log "prereq: llama.cpp (convert_hf_to_gguf.py + llama-quantize + llama-server)"
LLAMA_CPP_DIR="${CP1_LLAMA_CPP_DIR:-}"
LLAMA_QUANT_BIN=""
LLAMA_SERVER_BIN=""
LLAMA_CONVERT_PY=""

# search common locations
for candidate in \
    "${LLAMA_CPP_DIR}" \
    "/opt/homebrew/share/llama.cpp" \
    "/opt/homebrew/opt/llama.cpp/share/llama.cpp" \
    "${HOME}/llama.cpp" \
    "${ANIMA_ROOT}/vendor/llama.cpp"; do
  [[ -z "${candidate}" ]] && continue
  if [[ -f "${candidate}/convert_hf_to_gguf.py" ]]; then
    LLAMA_CONVERT_PY="${candidate}/convert_hf_to_gguf.py"
    LLAMA_CPP_DIR="${candidate}"
    break
  fi
done

if command -v llama-quantize >/dev/null 2>&1; then
  LLAMA_QUANT_BIN="$(command -v llama-quantize)"
elif [[ -x "${LLAMA_CPP_DIR}/build/bin/llama-quantize" ]]; then
  LLAMA_QUANT_BIN="${LLAMA_CPP_DIR}/build/bin/llama-quantize"
elif [[ -x "${LLAMA_CPP_DIR}/llama-quantize" ]]; then
  LLAMA_QUANT_BIN="${LLAMA_CPP_DIR}/llama-quantize"
fi

if command -v llama-server >/dev/null 2>&1; then
  LLAMA_SERVER_BIN="$(command -v llama-server)"
elif [[ -x "${LLAMA_CPP_DIR}/build/bin/llama-server" ]]; then
  LLAMA_SERVER_BIN="${LLAMA_CPP_DIR}/build/bin/llama-server"
elif [[ -x "${LLAMA_CPP_DIR}/llama-server" ]]; then
  LLAMA_SERVER_BIN="${LLAMA_CPP_DIR}/llama-server"
fi

if [[ -z "${LLAMA_CONVERT_PY}" || -z "${LLAMA_QUANT_BIN}" || -z "${LLAMA_SERVER_BIN}" ]]; then
  log "  [FAIL] llama.cpp components missing:"
  log "         convert_hf_to_gguf.py = ${LLAMA_CONVERT_PY:-NOT FOUND}"
  log "         llama-quantize        = ${LLAMA_QUANT_BIN:-NOT FOUND}"
  log "         llama-server          = ${LLAMA_SERVER_BIN:-NOT FOUND}"
  log "         Install options:"
  log "           1) brew install llama.cpp"
  log "           2) git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp && \\"
  log "                cd ~/llama.cpp && cmake -B build -DGGML_METAL=ON && cmake --build build -j"
  log "         Then set CP1_LLAMA_CPP_DIR=~/llama.cpp (or wherever) if not brewed."
  PREREQ_FAIL=1
else
  log "  [PASS] convert_hf_to_gguf.py = ${LLAMA_CONVERT_PY}"
  log "  [PASS] llama-quantize        = ${LLAMA_QUANT_BIN}"
  log "  [PASS] llama-server          = ${LLAMA_SERVER_BIN}"
fi

log "prereq: Python 3.10+ with peft / transformers / huggingface_hub"
PY_BIN="$(command -v python3 || true)"
if [[ -z "${PY_BIN}" ]]; then
  log "  [FAIL] python3 not found. brew install python@3.11"
  PREREQ_FAIL=1
else
  py_ver="$("${PY_BIN}" -c 'import sys; print("%d.%d"%sys.version_info[:2])' 2>/dev/null || echo "?")"
  py_major="$(echo "${py_ver}" | cut -d. -f1)"
  py_minor="$(echo "${py_ver}" | cut -d. -f2)"
  if [[ "${py_major}" != "3" || "${py_minor}" -lt 10 ]]; then
    log "  [FAIL] python3 = ${py_ver} (need ≥3.10)"
    PREREQ_FAIL=1
  else
    log "  [PASS] python3 = ${py_ver} (${PY_BIN})"
  fi
  missing_pkgs=""
  for pkg in peft transformers huggingface_hub; do
    if ! "${PY_BIN}" -c "import ${pkg}" >/dev/null 2>&1; then
      missing_pkgs="${missing_pkgs} ${pkg}"
    fi
  done
  if [[ -n "${missing_pkgs}" ]]; then
    log "  [FAIL] missing python pkgs:${missing_pkgs}"
    log "         Install: ${PY_BIN} -m pip install peft 'transformers>=4.44' huggingface_hub safetensors torch"
    PREREQ_FAIL=1
  else
    log "  [PASS] peft / transformers / huggingface_hub importable"
  fi
fi

log "prereq: trained adapter dir"
if [[ ! -d "${ADAPTER_PATH}" ]]; then
  log "  [FAIL] ${ADAPTER_PATH} missing"
  PREREQ_FAIL=1
else
  for required in adapter_config.json adapter_model.safetensors; do
    if [[ ! -f "${ADAPTER_PATH}/${required}" ]]; then
      log "  [FAIL] ${ADAPTER_PATH}/${required} missing"
      PREREQ_FAIL=1
    fi
  done
  [[ "${PREREQ_FAIL}" -eq 0 ]] && log "  [PASS] adapter_config.json + adapter_model.safetensors present"
fi

if [[ "${PREREQ_FAIL}" -ne 0 ]]; then
  log ""
  log "PREREQ FAIL — resolve the [FAIL] lines above, then re-run."
  exit 1
fi

# --- dry-run output -----------------------------------------------------------
if [[ "${MODE}" == "dry-run" ]]; then
  log ""
  log "DRY-RUN: 6-step Mac-local CP1 serve plan"
  log ""
  log "  [1/6] Merge LoRA adapter into base model"
  log "        python3 -c 'peft.PeftModel.from_pretrained(base=${BASE_MODEL}, adapter=${ADAPTER_PATH}).merge_and_unload()'"
  log "        → ${MERGED_DIR}/"
  log "        (skipped if ${MERGED_DIR}/config.json already present)"
  log ""
  log "  [2/6] Convert HF → GGUF (fp16)"
  log "        ${PY_BIN} ${LLAMA_CONVERT_PY} ${MERGED_DIR} --outfile ${GGUF_FP16}"
  log "        (skipped if ${GGUF_FP16} already present)"
  log ""
  log "  [3/6] Quantize GGUF → ${QUANT}"
  log "        ${LLAMA_QUANT_BIN} ${GGUF_FP16} ${GGUF_QUANT} ${QUANT}"
  log "        (skipped if ${GGUF_QUANT} already present)"
  log ""
  log "  [4/6] Install launchd plist (persistent, boot-on-login)"
  log "        path: ${PLIST_PATH}"
  log "        label: com.anima.cp1-serve"
  log "        exec:  ${LLAMA_SERVER_BIN} -m ${GGUF_QUANT} --host 127.0.0.1 --port ${PORT} \\"
  log "                                   -c 4096 -ngl 99 --metal --jinja"
  log ""
  log "  [5/6] Start llama-server"
  log "        launchctl unload ${PLIST_PATH} 2>/dev/null || true"
  log "        launchctl load ${PLIST_PATH}"
  log "        launchctl kickstart -k gui/\$(id -u)/com.anima.cp1-serve"
  log ""
  log "  [6/6] Health check"
  log "        curl -fsS http://127.0.0.1:${PORT}/health  # expect 200 + adapter info"
  log ""
  log "DRY-RUN: state JSON target = ${STATE_OUT}"
  log "DRY-RUN: expected perf on M4 16GB @ ${QUANT}: p99 ≈300ms, ~35 tok/s"
  log ""
  log "DRY-RUN: to actually launch run: $0 --apply --yes-i-mean-it"
  exit 0
fi

# --- apply mode ---------------------------------------------------------------
if [[ "${CONFIRM}" != "yes" ]]; then
  log "ERROR: --apply requires --yes-i-mean-it"
  exit 2
fi

# [1/6] Merge LoRA
log "APPLY [1/6]: merge LoRA adapter → ${MERGED_DIR}"
if [[ -f "${MERGED_DIR}/config.json" ]]; then
  log "  SKIP: ${MERGED_DIR} already has config.json"
else
  mkdir -p "${MERGED_DIR}"
  "${PY_BIN}" - <<PYEOF || { log "MERGE FAIL"; exit 3; }
import os, sys
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import torch

base_id  = "${BASE_MODEL}"
adapter  = "${ADAPTER_PATH}"
out_dir  = "${MERGED_DIR}"

print(f"[merge] loading base {base_id} ...")
tok = AutoTokenizer.from_pretrained(base_id)
mdl = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.float16, low_cpu_mem_usage=True)
print(f"[merge] loading adapter {adapter} ...")
mdl = PeftModel.from_pretrained(mdl, adapter)
print(f"[merge] merging + unloading ...")
mdl = mdl.merge_and_unload()
print(f"[merge] saving to {out_dir} ...")
mdl.save_pretrained(out_dir, safe_serialization=True)
tok.save_pretrained(out_dir)
print("[merge] done")
PYEOF
fi

# [2/6] Convert HF → GGUF
log "APPLY [2/6]: convert HF → GGUF fp16 → ${GGUF_FP16}"
if [[ -f "${GGUF_FP16}" ]]; then
  log "  SKIP: ${GGUF_FP16} already present"
else
  "${PY_BIN}" "${LLAMA_CONVERT_PY}" "${MERGED_DIR}" --outfile "${GGUF_FP16}" || { log "CONVERT FAIL"; exit 3; }
fi

# [3/6] Quantize
log "APPLY [3/6]: quantize → ${GGUF_QUANT}"
if [[ -f "${GGUF_QUANT}" ]]; then
  log "  SKIP: ${GGUF_QUANT} already present"
else
  "${LLAMA_QUANT_BIN}" "${GGUF_FP16}" "${GGUF_QUANT}" "${QUANT}" || { log "QUANTIZE FAIL"; exit 3; }
fi

# [4/6] Install launchd plist
log "APPLY [4/6]: install launchd plist → ${PLIST_PATH}"
mkdir -p "$(dirname "${PLIST_PATH}")"
cat > "${PLIST_PATH}" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>               <string>com.anima.cp1-serve</string>
  <key>ProgramArguments</key>
  <array>
    <string>${LLAMA_SERVER_BIN}</string>
    <string>-m</string><string>${GGUF_QUANT}</string>
    <string>--host</string><string>127.0.0.1</string>
    <string>--port</string><string>${PORT}</string>
    <string>-c</string><string>4096</string>
    <string>-ngl</string><string>99</string>
    <string>--metal</string>
    <string>--jinja</string>
  </array>
  <key>RunAtLoad</key>           <true/>
  <key>KeepAlive</key>           <true/>
  <key>StandardOutPath</key>     <string>/tmp/anima_cp1_serve.out.log</string>
  <key>StandardErrorPath</key>   <string>/tmp/anima_cp1_serve.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
PLIST_EOF

# [5/6] Start llama-server
log "APPLY [5/6]: start llama-server via launchctl"
launchctl unload "${PLIST_PATH}" 2>/dev/null || true
launchctl load "${PLIST_PATH}" || { log "LAUNCHCTL LOAD FAIL"; exit 3; }
launchctl kickstart -k "gui/$(id -u)/com.anima.cp1-serve" || true

# [6/6] Health check (poll briefly; llama-server needs ~3-8s to load the model)
log "APPLY [6/6]: health check http://127.0.0.1:${PORT}/health"
health_ok=0
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/tmp/anima_cp1_health.json 2>/dev/null; then
    health_ok=1
    log "  [PASS] /health responded (attempt ${i}):"
    log "         $(head -c 200 /tmp/anima_cp1_health.json)"
    break
  fi
  sleep 2
done
if [[ "${health_ok}" -ne 1 ]]; then
  log "  [FAIL] /health did not respond within 30s. Tail /tmp/anima_cp1_serve.err.log for cause."
  exit 3
fi

# write state
cat > "${STATE_OUT}" <<EOF
{
  "schema": "anima/cp1_serve_launch/1",
  "mode": "mac-local",
  "base_model": "${BASE_MODEL}",
  "quant": "${QUANT}",
  "gguf_path": "${GGUF_QUANT}",
  "port": ${PORT},
  "plist": "${PLIST_PATH}",
  "launched_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "expected_p99_ms": 300,
  "expected_tok_per_s": 35
}
EOF
log "launch state written: ${STATE_OUT}"
log "APPLY: complete. CP1 live on Mac at http://127.0.0.1:${PORT} (launchd = persistent, boot-on-login)."
exit 0
