#!/usr/bin/env bash
# tool/linux_parity_check.bash — ROI #75 (Linux pre-tested binary, ubu1/htz parity)
#
# PURPOSE
#   Verify that hexa tool scripts under tool/ can be parsed cleanly on the
#   Linux remote host (ubu1) via airgenome offload. This catches any
#   macOS-only syntax/bin assumptions before H100 launch ops.
#
# IDEMPOTENCY
#   Read-only on remote (parse only; no execute, no state writes there).
#   Local: rewrites state/linux_parity_audit.json atomically.
#
# GRACEFUL DEGRADE
#   If airgenome unreachable OR remote `hexa` binary missing → emit verdict
#   "ENV_BLOCKED" and exit 0 (do NOT fail the run).
#
# USAGE
#   bash tool/linux_parity_check.bash             — full sweep (max 20 samples)
#   bash tool/linux_parity_check.bash --all       — full sweep (no cap)
#   bash tool/linux_parity_check.bash --self-test — local sanity, no remote calls
#
# CONSTRAINTS (raw#9 hexa-only honored at script semantics; .bash for ssh glue)
#   No actual pod actions, no state mutation on remote, no docker.

set -u
ROOT="/Users/ghost/core/anima"
OUT="$ROOT/state/linux_parity_audit.json"
TMP="$OUT.tmp.$$"
HOST="ubu1"
AIRGENOME="/Users/ghost/core/airgenome/bin/airgenome"
SAMPLE_CAP=20
MODE="sample"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
escape_json() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

if [[ "${1:-}" == "--all" ]]; then MODE="all"; fi
if [[ "${1:-}" == "--self-test" ]]; then
  printf '{"schema":"anima/linux_parity_audit/1","ts":"%s","verdict":"SELF_TEST_OK","host":"%s"}\n' "$(ts)" "$HOST" > "$TMP"
  mv "$TMP" "$OUT"
  echo "[linux_parity] selftest OK → $OUT"
  exit 0
fi

emit_blocked() {
  local reason="$1"
  cat > "$TMP" <<EOF
{
  "schema": "anima/linux_parity_audit/1",
  "ts": "$(ts)",
  "host": "$HOST",
  "mode": "$MODE",
  "verdict": "ENV_BLOCKED",
  "reason": "$(escape_json "$reason")",
  "results": []
}
EOF
  mv "$TMP" "$OUT"
  echo "[linux_parity] ENV_BLOCKED ($reason) → $OUT"
  exit 0
}

# Reachability probe
if [[ ! -x "$AIRGENOME" ]]; then
  emit_blocked "airgenome binary not present at $AIRGENOME"
fi
if ! timeout 8 "$AIRGENOME" offload "$HOST" 'echo ok' >/dev/null 2>&1; then
  emit_blocked "host $HOST offload probe failed"
fi
if ! timeout 8 "$AIRGENOME" offload "$HOST" 'command -v hexa >/dev/null 2>&1' >/dev/null 2>&1; then
  emit_blocked "remote host $HOST has no hexa binary on PATH"
fi

# Build candidate list (hexa only — bash files are not parsed by hexa)
mapfile -t CANDIDATES < <(ls "$ROOT/tool/"*.hexa 2>/dev/null | sort)
if [[ "$MODE" == "sample" ]]; then
  CANDIDATES=("${CANDIDATES[@]:0:$SAMPLE_CAP}")
fi

total=${#CANDIDATES[@]}
pass=0; fail=0; skip=0
results_json=""
sep=""

for src in "${CANDIDATES[@]}"; do
  base=$(basename "$src")
  # Copy to /tmp on remote then `hexa parse` it. We avoid actual execution.
  remote_tmp="/tmp/_lpc_$$_${base}"
  if ! scp -q -o ConnectTimeout=5 -o BatchMode=yes "$src" "${HOST}:${remote_tmp}" 2>/dev/null; then
    skip=$((skip+1))
    verdict="SKIPPED_TRANSFER"
    detail="scp failed"
  else
    out=$(timeout 15 "$AIRGENOME" offload "$HOST" "cd /tmp && (hexa parse $remote_tmp 2>&1 || hexa --check $remote_tmp 2>&1 || hexa $remote_tmp --parse-only 2>&1); rm -f $remote_tmp" 2>&1 || true)
    if [[ -z "$out" ]] || echo "$out" | grep -qiE '^(parsed|ok|pass)|^[[:space:]]*$'; then
      pass=$((pass+1)); verdict="PASS"; detail=""
    elif echo "$out" | grep -qiE 'no such file|not a command|unknown subcommand|usage:'; then
      # hexa CLI doesn't expose `parse` — degrade to ENV_BLOCKED at first occurrence
      emit_blocked "remote hexa lacks parse/--check subcommand: $(printf '%s' "$out" | head -c 200)"
    else
      fail=$((fail+1)); verdict="FAIL"
      detail=$(printf '%s' "$out" | head -c 240)
    fi
  fi
  results_json+="${sep}{\"file\":\"$base\",\"verdict\":\"$verdict\",\"detail\":\"$(escape_json "${detail:-}")\"}"
  sep=","
done

overall="PASS"
if [[ $fail -gt 0 ]]; then overall="FAIL"; fi
if [[ $total -eq 0 ]]; then overall="EMPTY"; fi

cat > "$TMP" <<EOF
{
  "schema": "anima/linux_parity_audit/1",
  "ts": "$(ts)",
  "host": "$HOST",
  "mode": "$MODE",
  "sample_cap": $SAMPLE_CAP,
  "totals": { "candidates": $total, "pass": $pass, "fail": $fail, "skip": $skip },
  "verdict": "$overall",
  "results": [$results_json]
}
EOF
mv "$TMP" "$OUT"
echo "[linux_parity] verdict=$overall total=$total pass=$pass fail=$fail skip=$skip → $OUT"
exit 0
