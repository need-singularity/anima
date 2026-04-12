#!/bin/bash
# ═══════════════════════════════════════════════════════════════
#  serving/ckpt_save_hook.sh — ALM 14B r4 save-triggered KR sampler
#
#  Polls /workspace/train_r4.log for new "[save] /workspace/ckpt_alm_14b_r4/step_NNNN"
#  lines. On each new save, writes the ckpt path to /tmp/kr_ckpt_path.txt and
#  invokes kr_sample_at_ckpt.hexa. All invocations logged to /workspace/ckpt_hook.log.
#
#  Parallel to r2_sidecar / r2_sidecar_r3 / r2_sidecar_zstd; does NOT modify the
#  running training process or any existing sidecar.
#
#  Run (manual):
#    bash /workspace/anima/serving/ckpt_save_hook.sh
#
#  Daemon mode (NOT launched by deploy):
#    nohup bash /workspace/anima/serving/ckpt_save_hook.sh \
#      > /workspace/ckpt_hook.out 2>&1 &
# ═══════════════════════════════════════════════════════════════

set -u

TRAIN_LOG="${TRAIN_LOG:-/workspace/train_r4.log}"
HOOK_LOG="${HOOK_LOG:-/workspace/ckpt_hook.log}"
SEEN_FILE="${SEEN_FILE:-/workspace/.ckpt_hook_seen}"
KR_SAMPLE_HEXA="${KR_SAMPLE_HEXA:-/workspace/anima/serving/kr_sample_at_ckpt.hexa}"
KR_QUALITY_GATE_HEXA="${KR_QUALITY_GATE_HEXA:-/workspace/anima/serving/kr_quality_gate.hexa}"
ARG_FILE="${ARG_FILE:-/tmp/kr_ckpt_path.txt}"
POLL_SEC="${POLL_SEC:-30}"

touch "$SEEN_FILE" "$HOOK_LOG"

log() {
    local msg="$1"
    local stamp
    stamp=$(date +%Y-%m-%dT%H:%M:%S)
    printf '[%s] %s\n' "$stamp" "$msg" | tee -a "$HOOK_LOG"
}

run_once() {
    # Scan TRAIN_LOG for [save] lines we haven't seen.
    # Line format: [save] /workspace/ckpt_alm_14b_r4/step_NNNN
    if [ ! -f "$TRAIN_LOG" ]; then
        log "WARN train_log_missing=$TRAIN_LOG"
        return
    fi
    while IFS= read -r line; do
        # Extract path after "[save] "
        local ckpt_path="${line#\[save\] }"
        # Basic sanity: must start with /workspace/ckpt_
        case "$ckpt_path" in
            /workspace/ckpt_*) ;;
            *) continue ;;
        esac
        # Skip if already seen
        if grep -qF "$ckpt_path" "$SEEN_FILE"; then
            continue
        fi
        # Wait for the ckpt dir to actually exist (trainer prints before save completes in some paths)
        if [ ! -d "$ckpt_path" ]; then
            log "defer ckpt_not_ready=$ckpt_path"
            continue
        fi
        if [ ! -f "$ckpt_path/adapter_config.json" ]; then
            log "defer adapter_config_missing=$ckpt_path"
            continue
        fi

        log "trigger ckpt=$ckpt_path"
        printf '%s\n' "$ckpt_path" > "$ARG_FILE"
        # Invoke kr_sample_at_ckpt.hexa. Output to hook log.
        if hexa "$KR_SAMPLE_HEXA" >> "$HOOK_LOG" 2>&1; then
            log "sample_ok ckpt=$ckpt_path"
            # Chain into kr_quality_gate.hexa: parses /workspace/kr_samples.log,
            # writes /workspace/kr_quality.log, which monitor_alm_r4 polls.
            if [ -f "$KR_QUALITY_GATE_HEXA" ]; then
                if hexa "$KR_QUALITY_GATE_HEXA" >> "$HOOK_LOG" 2>&1; then
                    log "quality_gate_ok ckpt=$ckpt_path"
                else
                    log "quality_gate_fail ckpt=$ckpt_path rc=$?"
                    # still mark seen — gate retry can happen on next ckpt
                fi
            else
                log "quality_gate_skip missing=$KR_QUALITY_GATE_HEXA"
            fi
            printf '%s\n' "$ckpt_path" >> "$SEEN_FILE"
        else
            log "sample_fail ckpt=$ckpt_path rc=$?"
            # don't mark seen — retry next sweep
        fi
        rm -f "$ARG_FILE"
    done < <(grep -E '^\[save\] /workspace/ckpt_' "$TRAIN_LOG")
}

log "hook START train_log=$TRAIN_LOG hexa=$KR_SAMPLE_HEXA"

# If invoked with ONCE=1, run once and exit (for testing).
if [ "${ONCE:-0}" = "1" ]; then
    run_once
    log "hook ONCE DONE"
    exit 0
fi

while true; do
    run_once
    sleep "$POLL_SEC"
done
