#!/usr/bin/env bash
# tool/anima_native_build.bash — Y2 single-binary native compile for anima CLI topics
#
# PURPOSE
#   bin/anima itself is a bash dispatcher (OS built-in shell, no compile needed).
#   The real compile targets are the per-topic tool/anima_cli/<topic>.hexa modules.
#   This script reuses the build_fixup_native.bash pattern (hexa_v2 transpile →
#   sed fixup for exec_capture/now name-mangling bug → clang -O2) to produce
#   dist/anima_<topic> native binaries.
#
# USAGE
#   bash tool/anima_native_build.bash [<topic>]      # single module (default: compute)
#   bash tool/anima_native_build.bash --all          # all 15 topic modules
#   bash tool/anima_native_build.bash --selftest     # synthetic 1-module build + exec test
#
# EXIT
#   0 = OK (at least 1 module built)
#   1 = transpile fail
#   2 = clang fail
#   3 = arg error
#   4 = all modules failed (--all mode)
#
# BLOCKERS (stage2 hexa transpiler bugs — see docs/upstream_notes/hexa_lang_20260422.md)
#   1. exec_capture → must be hx_exec_capture in C output
#   2. now → must be timestamp in C output
#   3. (reserved for future discovery)
#   Workaround: sed-fixup post-transpile (same pattern as build_fixup_native.bash).
#   If workaround fails, this script writes docs/anima_native_build_blocker.md.
set -euo pipefail

readonly ROOT="/Users/ghost/core/anima"
readonly HEXA_V2="/Users/ghost/core/hexa-lang/self/native/hexa_v2"
readonly RUNTIME_INCLUDE="/Users/ghost/core/hexa-lang/self"
readonly CLI_DIR="${ROOT}/tool/anima_cli"
readonly ARTIFACT_DIR="${ROOT}/build/artifacts"
readonly DIST_DIR="${ROOT}/dist"
readonly BLOCKER_DOC="${ROOT}/docs/anima_native_build_blocker.md"

# 15 topic modules (excludes _common.hexa which is shared-helpers only)
readonly ALL_TOPICS=(audit bench cert compute cost doctor handoff inbox log paradigm proposal roadmap serve stats sync weight)

usage() { sed -n '1,30p' "$0"; }

build_one() {
  local topic="$1"
  local src="${CLI_DIR}/${topic}.hexa"
  local c_out="${ARTIFACT_DIR}/anima_${topic}.c"
  local bin_out="${DIST_DIR}/anima_${topic}"

  [[ -f "$src" ]] || { echo "  [$topic] ERROR src missing: $src"; return 3; }

  # [1/3] transpile
  if ! "$HEXA_V2" "$src" "$c_out" >/tmp/anima_native_${topic}_trans.log 2>&1; then
    echo "  [$topic] TRANSPILE_FAIL"
    head -5 /tmp/anima_native_${topic}_trans.log | sed 's/^/    /'
    return 1
  fi

  # [2/3] sed-fixup (N73 workaround: exec_capture → hx_exec_capture, now → timestamp)
  sed -i '' \
      -e 's/hexa_call\([0-9]\)(exec_capture,/hexa_call\1(hx_exec_capture,/g' \
      -e 's/hexa_call\([0-9]\)(exec_capture)/hexa_call\1(hx_exec_capture)/g' \
      -e 's/hexa_call\([0-9]\)(now)/hexa_call\1(timestamp)/g' \
      -e 's/hexa_call\([0-9]\)(now,/hexa_call\1(timestamp,/g' \
      "$c_out"

  local fixups
  fixups=$(grep -cE "(hx_exec_capture|hexa_call[0-9]\(timestamp)" "$c_out" 2>/dev/null | tr -d '\n' || true)
  fixups="${fixups:-0}"

  # [3/3] clang -O2
  if ! clang -O2 -Wno-trigraphs -fbracket-depth=4096 \
        -I "$RUNTIME_INCLUDE" "$c_out" -o "$bin_out" \
        >/tmp/anima_native_${topic}_clang.log 2>&1; then
    echo "  [$topic] CLANG_FAIL (fixups=$fixups)"
    head -5 /tmp/anima_native_${topic}_clang.log | sed 's/^/    /'
    return 2
  fi

  local sz
  sz=$(stat -f%z "$bin_out" 2>/dev/null || stat -c%s "$bin_out")
  echo "  [$topic] OK  fixups=$fixups  size=${sz}B  -> $bin_out"
  return 0
}

write_blocker_doc() {
  local failed_topics="$1"
  local trans_fail="$2"
  local clang_fail="$3"
  mkdir -p "$(dirname "$BLOCKER_DOC")"
  {
    echo "# anima native build — blocker log"
    echo ""
    echo "**generated**: $(date -u +%FT%TZ)"
    echo "**script**: tool/anima_native_build.bash"
    echo ""
    echo "## Summary"
    echo ""
    echo "- failed modules: \`${failed_topics}\`"
    echo "- transpile failures: ${trans_fail}"
    echo "- clang failures: ${clang_fail}"
    echo ""
    echo "## Known hexa transpiler bugs (stage2)"
    echo ""
    echo "1. \`exec_capture()\` emits raw \`exec_capture\` identifier — runtime expects \`hx_exec_capture\`"
    echo "2. \`now()\` emits raw \`now\` — runtime has \`timestamp\`"
    echo "3. (reserved — add newly discovered bug here)"
    echo ""
    echo "Workaround: sed-fixup post-transpile (see \`tool/build_fixup_native.bash\`)."
    echo ""
    echo "## Per-module diagnostics"
    echo ""
    for t in ${failed_topics}; do
      echo "### ${t}"
      echo ""
      echo "\`\`\`"
      if [[ -f /tmp/anima_native_${t}_trans.log ]]; then
        echo "-- transpile --"
        tail -10 /tmp/anima_native_${t}_trans.log
      fi
      if [[ -f /tmp/anima_native_${t}_clang.log ]]; then
        echo "-- clang --"
        tail -10 /tmp/anima_native_${t}_clang.log
      fi
      echo "\`\`\`"
      echo ""
    done
    echo "## Upstream reference"
    echo ""
    echo "- docs/upstream_notes/hexa_lang_20260422.md (transpiler builtin name mangling)"
    echo "- tool/build_fixup_native.bash (N73 workaround reference impl)"
  } > "$BLOCKER_DOC"
  echo "  blocker doc: $BLOCKER_DOC"
}

selftest() {
  echo "── anima_native_build selftest ──"
  mkdir -p "$ARTIFACT_DIR" "$DIST_DIR"
  # synthetic: build compute.hexa (simplest topic with all helper patterns)
  if build_one compute; then
    # exec test
    if "${DIST_DIR}/anima_compute" --selftest >/tmp/anima_compute_selftest.log 2>&1; then
      if grep -q "PASS" /tmp/anima_compute_selftest.log; then
        echo "  exec: PASS"
        echo "── selftest PASS (1 module built + exec verified) ──"
        exit 0
      fi
    fi
    echo "  exec: FAIL"
    cat /tmp/anima_compute_selftest.log | sed 's/^/    /'
    exit 1
  fi
  echo "── selftest FAIL ──"
  exit 1
}

main() {
  mkdir -p "$ARTIFACT_DIR" "$DIST_DIR"
  [[ -x "$HEXA_V2" ]] || { echo "ERROR: hexa_v2 not found: $HEXA_V2"; exit 3; }

  case "${1:-compute}" in
    --selftest) selftest ;;
    --help|-h) usage; exit 0 ;;
    --all)
      echo "── anima_native_build --all (${#ALL_TOPICS[@]} modules) ──"
      local ok=0 fail=0 failed_list=""
      local trans_fail=0 clang_fail=0
      for t in "${ALL_TOPICS[@]}"; do
        set +e
        build_one "$t"
        local rc=$?
        set -e
        case $rc in
          0) ok=$((ok+1)) ;;
          1) fail=$((fail+1)); trans_fail=$((trans_fail+1)); failed_list="$failed_list $t" ;;
          2) fail=$((fail+1)); clang_fail=$((clang_fail+1)); failed_list="$failed_list $t" ;;
          *) fail=$((fail+1)); failed_list="$failed_list $t" ;;
        esac
      done
      echo "── result: ${ok}/${#ALL_TOPICS[@]} OK, ${fail} fail ──"
      if [[ $fail -gt 0 ]]; then
        write_blocker_doc "${failed_list## }" "$trans_fail" "$clang_fail"
      fi
      if [[ $ok -eq 0 ]]; then exit 4; fi
      exit 0
      ;;
    -*)
      echo "unknown flag: $1"; usage; exit 3 ;;
    *)
      local topic="$1"
      echo "── anima_native_build ${topic} ──"
      set +e
      build_one "$topic"
      local rc=$?
      set -e
      if [[ $rc -ne 0 ]]; then
        write_blocker_doc "$topic" \
          $([[ $rc -eq 1 ]] && echo 1 || echo 0) \
          $([[ $rc -eq 2 ]] && echo 1 || echo 0)
        exit $rc
      fi
      exit 0
      ;;
  esac
}

main "$@"
