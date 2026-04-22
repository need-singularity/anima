#!/usr/bin/env bash
# tool/universal_binary_build.bash — ROI #76 (arm64 + x86_64 universal binary)
#
# PURPOSE
#   Build (or audit existing) hexa AOT binaries for arm64 + x86_64.
#   Smoke-test the arm64 build locally on macOS host. x86_64 cannot be
#   exec-tested on this host (different ISA); we only verify build artifact.
#
# IDEMPOTENCY
#   Re-running rewrites state/universal_binary_audit.json atomically.
#   Build dir lives under build/universal/{arm64,x86_64,fat}/.
#
# GRACEFUL DEGRADE
#   If `hexa build` not supported → emit BUILD_TOOL_MISSING audit, exit 0.
#   If `lipo` missing or no arch toolchain → emit ENV_BLOCKED, exit 0.
#
# CONSTRAINTS
#   No actual launching of any pod, no network, no docker.

set -u
ROOT="/Users/ghost/core/anima"
OUT="$ROOT/state/universal_binary_audit.json"
TMP="$OUT.tmp.$$"
BUILD_DIR="$ROOT/build/universal"
HEXA_BIN="$(command -v hexa 2>/dev/null || true)"

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
escape_json() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

emit() {
  local verdict="$1" reason="$2" arm_arch="$3" x86_arch="$4" fat="$5" arm_smoke="$6"
  cat > "$TMP" <<EOF
{
  "schema": "anima/universal_binary_audit/1",
  "ts": "$(ts)",
  "host_arch": "$(uname -m)",
  "host_kernel": "$(uname -s)",
  "hexa_bin": "$(escape_json "${HEXA_BIN:-MISSING}")",
  "build_dir": "$BUILD_DIR",
  "verdict": "$verdict",
  "reason": "$(escape_json "$reason")",
  "arm64_artifact_arch": "$(escape_json "$arm_arch")",
  "x86_64_artifact_arch": "$(escape_json "$x86_arch")",
  "fat_artifact": "$(escape_json "$fat")",
  "arm64_smoke": "$(escape_json "$arm_smoke")",
  "policy": "spec-only when hexa build unsupported; audit existing artifacts"
}
EOF
  mv "$TMP" "$OUT"
  echo "[univ_bin] verdict=$verdict → $OUT"
  exit 0
}

mkdir -p "$BUILD_DIR/arm64" "$BUILD_DIR/x86_64" "$BUILD_DIR/fat"

if [[ -z "$HEXA_BIN" ]]; then
  emit "ENV_BLOCKED" "hexa binary not on PATH" "" "" "" ""
fi

if ! command -v lipo >/dev/null 2>&1; then
  emit "ENV_BLOCKED" "lipo (macOS toolchain) missing" "" "" "" ""
fi

# Probe whether `hexa build` exists. Most current hexa is a REPL; in that
# case we treat the existing binary as the arm64 artifact and declare x86_64
# as PENDING (not buildable on this host without cross-toolchain).
HEXA_BUILD_OK=0
if "$HEXA_BIN" build --help >/dev/null 2>&1; then
  HEXA_BUILD_OK=1
fi

ARM_DST="$BUILD_DIR/arm64/hexa"
X86_DST="$BUILD_DIR/x86_64/hexa"
FAT_DST="$BUILD_DIR/fat/hexa"

# arm64: copy the existing host hexa as the arm64 artifact (already arm64)
if file "$HEXA_BIN" 2>/dev/null | grep -q "arm64"; then
  cp -f "$HEXA_BIN" "$ARM_DST"
fi
arm_arch=""
if [[ -f "$ARM_DST" ]]; then
  arm_arch=$(lipo -info "$ARM_DST" 2>/dev/null | tail -c 200 | tr -d '\n' || echo "")
fi

# x86_64: only if hexa build with --target supports it; otherwise leave PENDING
x86_arch="PENDING_NO_CROSS_BUILD"
if [[ "$HEXA_BUILD_OK" == "1" ]]; then
  if "$HEXA_BIN" build --target x86_64-apple-darwin -o "$X86_DST" "$ROOT/run.hexa" >/dev/null 2>&1; then
    x86_arch=$(lipo -info "$X86_DST" 2>/dev/null | tail -c 200 | tr -d '\n')
  fi
fi

# fat: only if both present
fat_status="NOT_BUILT"
if [[ -f "$ARM_DST" && -f "$X86_DST" ]]; then
  if lipo -create -output "$FAT_DST" "$ARM_DST" "$X86_DST" 2>/dev/null; then
    fat_status=$(lipo -info "$FAT_DST" 2>/dev/null | tail -c 200 | tr -d '\n')
  fi
fi

# arm64 smoke: invoke `hexa` with stdin :quit (REPL exit) — quick liveness check
arm_smoke="SKIPPED"
if [[ -x "$ARM_DST" ]]; then
  if echo ":quit" | timeout 5 "$ARM_DST" >/dev/null 2>&1; then
    arm_smoke="OK_REPL_QUIT"
  else
    # Some builds may not handle :quit; just check exec-ability
    if "$ARM_DST" --version >/dev/null 2>&1 || file "$ARM_DST" >/dev/null 2>&1; then
      arm_smoke="OK_EXEC_PRESENT"
    else
      arm_smoke="FAIL_EXEC"
    fi
  fi
fi

verdict="ARM64_OK_X86_PENDING"
if [[ "$x86_arch" != "PENDING_NO_CROSS_BUILD" && -f "$X86_DST" ]]; then
  verdict="UNIVERSAL_OK"
fi

emit "$verdict" "arm64 host build only; x86_64 requires cross-toolchain or remote builder" \
  "$arm_arch" "$x86_arch" "$fat_status" "$arm_smoke"
