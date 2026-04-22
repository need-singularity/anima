#!/usr/bin/env bash
# tool/build_fixup_native.bash — N73 fix for hexa-cc transpiler bug
#
# PURPOSE
#   `hexa build` fails for tools using `exec_capture()` and `now()` because the
#   transpiler emits raw identifier `exec_capture` / `now` in C output, while
#   the runtime declares `hx_exec_capture` (and `now` should map to `timestamp`).
#
#   This wrapper does manual 3-step: hexa_v2 transpile → sed fixup → clang.
#   Workaround until upstream hexa-lang patches transpiler builtin name mangling.
#   See: docs/upstream_notes/hexa_lang_20260422.md "추가 발견 #1"
#
# USAGE
#   bash tool/build_fixup_native.bash <tool/X.hexa> <output/path>
#   bash tool/build_fixup_native.bash --selftest      # build dist/sap + dist/hpli
#
# EXIT
#   0 = build OK + binary exists
#   1 = transpile fail
#   2 = clang fail
#   3 = arg error
set -euo pipefail

readonly HEXA_V2="/Users/ghost/core/hexa-lang/self/native/hexa_v2"
readonly RUNTIME_INCLUDE="/Users/ghost/core/hexa-lang/self"
readonly ARTIFACT_DIR="${ARTIFACT_DIR:-build/artifacts}"

usage() { sed -n '1,20p' "$0"; }

selftest() {
  echo "── build_fixup_native selftest ──"
  # Output names use .native suffix to avoid conflict with existing dist/<name>/ dirs
  bash "$0" tool/serve_alm_persona.hexa dist/serve_alm_persona.native && \
    dist/serve_alm_persona.native --selftest --dry >/dev/null && \
    echo "  serve_alm_persona PASS" || { echo "  serve_alm_persona FAIL"; exit 1; }
  bash "$0" tool/h100_post_launch_ingest.hexa dist/h100_post_launch_ingest.native && \
    dist/h100_post_launch_ingest.native --selftest >/dev/null && \
    echo "  h100_post_launch_ingest PASS" || { echo "  h100_post_launch_ingest FAIL"; exit 1; }
  echo "── selftest 2/2 PASS ──"
  exit 0
}

[[ "${1:-}" == "--selftest" ]] && selftest
[[ $# -lt 2 ]] && { usage; exit 3; }

readonly SRC="$1"
readonly OUT="$2"
readonly NAME="$(basename "$SRC" .hexa)"
readonly C_OUT="${ARTIFACT_DIR}/${NAME}.c"

[[ -f "$SRC" ]] || { echo "ERROR: source not found: $SRC"; exit 3; }
[[ -x "$HEXA_V2" ]] || { echo "ERROR: hexa_v2 not found: $HEXA_V2"; exit 3; }

mkdir -p "$ARTIFACT_DIR" "$(dirname "$OUT")"

echo "[1/3] transpile: $HEXA_V2 $SRC $C_OUT"
"$HEXA_V2" "$SRC" "$C_OUT" || { echo "  transpile FAIL"; exit 1; }

echo "[2/3] sed-fixup: exec_capture→hx_exec_capture, now→timestamp"
sed -i '' \
    -e 's/hexa_call\([0-9]\)(exec_capture,/hexa_call\1(hx_exec_capture,/g' \
    -e 's/hexa_call\([0-9]\)(exec_capture)/hexa_call\1(hx_exec_capture)/g' \
    -e 's/hexa_call\([0-9]\)(now)/hexa_call\1(timestamp)/g' \
    -e 's/hexa_call\([0-9]\)(now,/hexa_call\1(timestamp,/g' \
    "$C_OUT"

fixup_count=$(grep -cE "(hx_exec_capture|hx_now|hexa_call[0-9]\(timestamp)" "$C_OUT" || echo 0)
echo "  fixed callsites: $fixup_count"

echo "[3/3] clang -O2 -> $OUT"
clang -O2 -Wno-trigraphs -fbracket-depth=4096 \
      -I "$RUNTIME_INCLUDE" \
      "$C_OUT" -o "$OUT" || { echo "  clang FAIL"; exit 2; }

echo "  built: $OUT ($(stat -f%z "$OUT" 2>/dev/null || stat -c%s "$OUT") bytes)"
echo "RESULT: build OK"
