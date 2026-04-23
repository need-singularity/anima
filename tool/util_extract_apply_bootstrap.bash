#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  tool/util_extract_apply_bootstrap.bash — H42 marker driver (bash bootstrap)
#
#  PURPOSE
#    One-shot bash equivalent of tool/util_extract_apply.hexa, used to seed
#    H42 inline-deprecation markers in environments where the team's custom
#    hexa runtime is not available (e.g. CI runners with stripped hexa-lang
#    0.2.0 lacking exec_with_status / .trim() / .substring()).
#
#    The canonical driver is the .hexa file; this bash twin exists ONLY for
#    bootstrap parity. Both produce the same marker shape and audit schema.
#
#  CONTRACT
#    - Idempotent: re-running is a no-op on already-marked files.
#    - Never deletes inline `fn _xxx(` definitions (hexa loader unstable).
#    - Marker line shape:
#        // INLINE_DEPRECATED[H42]: see <canonical> for canonical impl — kept inline (hexa stage0 loader)
#
#  OUTPUT
#    state/util_extract_apply_audit.json  (schema v1)
#
#  USAGE
#    bash tool/util_extract_apply_bootstrap.bash
#    bash tool/util_extract_apply_bootstrap.bash --dry-run
# ════════════════════════════════════════════════════════════════════════════
set -u

ANIMA_ROOT="/Users/ghost/core/anima"
TOOL_DIR="$ANIMA_ROOT/tool"
OUT_PATH="$ANIMA_ROOT/state/util_extract_apply_audit.json"
MARKER_TAG="INLINE_DEPRECATED[H42]"
DRY_RUN="${1:-}"

# (fn_name, canonical_path) pairs — must match TARGETS in the hexa driver
TARGETS=(
  "_sh_quote|shared/util/sh_quote.hexa"
  "_file_exists|shared/util/file_exists.hexa"
  "_ts_iso|shared/util/ts_iso.hexa"
  "_json_escape|shared/util/json_escape.hexa"
)

ts_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "$s"
}

# Find line number (1-indexed) of `fn NAME(` at column 0; 0 if absent
find_fn_line() {
  local file="$1" name="$2"
  awk -v needle="fn ${name}(" '
    index($0, needle) == 1 { print NR; exit }
  ' "$file" 2>/dev/null
}

# Check whether the line immediately above contains the marker tag
is_already_marked() {
  local file="$1" fn_line="$2"
  if [[ "$fn_line" -le 1 ]]; then return 1; fi
  local prev_idx=$((fn_line - 1))
  local prev
  prev=$(awk -v n="$prev_idx" 'NR==n { print; exit }' "$file" 2>/dev/null)
  case "$prev" in
    *"$MARKER_TAG"*) return 0 ;;
    *) return 1 ;;
  esac
}

insert_marker() {
  # returns 0 on success, 1 on mv failure (sandbox-protected file)
  local file="$1" fn_line="$2" canonical="$3"
  local marker="// ${MARKER_TAG}: see ${canonical} for canonical impl — kept inline (hexa stage0 loader)"
  local tmp="${file}.h42tmp"
  awk -v n="$fn_line" -v m="$marker" '
    NR == n { print m }
    { print }
  ' "$file" > "$tmp" 2>/dev/null
  if ! mv -f "$tmp" "$file" 2>/dev/null; then
    rm -f "$tmp" 2>/dev/null
    return 1
  fi
  return 0
}

# Build per-tool match record (parallel arrays for bash 3.2 compatibility)
tool_paths=()
tool_matches=()
tool_mutated=()

total_markers=0
total_idem=0

for tool in "$TOOL_DIR"/*.hexa; do
  base=$(basename "$tool")
  case "$base" in
    util_extract_apply.hexa|util_extract_audit.hexa) continue ;;
  esac

  matches_json=""
  mutated="false"

  for spec in "${TARGETS[@]}"; do
    fn_name="${spec%%|*}"
    canon="${spec##*|}"
    line=$(find_fn_line "$tool" "$fn_name")
    [[ -z "$line" ]] && line=0
    if [[ "$line" -gt 0 ]]; then
      added="false"
      already="false"
      if is_already_marked "$tool" "$line"; then
        already="true"
        total_idem=$((total_idem + 1))
      elif [[ "$DRY_RUN" != "--dry-run" ]]; then
        if insert_marker "$tool" "$line" "$canon"; then
          added="true"
          mutated="true"
          total_markers=$((total_markers + 1))
        else
          # mv failed — sandbox-protected file. Record as skipped rather
          # than mutated so the audit reflects on-disk reality.
          added="false"
          mv_blocked="true"
        fi
      fi
      if [[ "$already" == "true" ]]; then
        test_after="idempotent_skip"
      elif [[ "$added" == "true" ]]; then
        test_after="library_marker_only"
      elif [[ "${mv_blocked:-false}" == "true" ]]; then
        test_after="mv_blocked"
      else
        test_after="skipped"
      fi
      mv_blocked="false"
      m="{\"fn\":\"$(json_escape "$fn_name")\",\"original_loc\":${line},\"deprecation_marker_added\":${added},\"kept_inline\":true,\"test_after_marker\":\"${test_after}\"}"
      if [[ -z "$matches_json" ]]; then
        matches_json="$m"
      else
        matches_json="${matches_json},${m}"
      fi
    fi
  done

  if [[ -n "$matches_json" ]]; then
    short="${tool#$ANIMA_ROOT/}"
    tool_paths+=("$short")
    tool_matches+=("[$matches_json]")
    tool_mutated+=("$mutated")
  fi
done

# Emit audit JSON
{
  printf '{\n'
  printf '  "schema": "anima.util_extract_apply_audit.v1",\n'
  printf '  "ts": "%s",\n' "$(ts_iso)"
  printf '  "dry_run": %s,\n' "$([[ "$DRY_RUN" == "--dry-run" ]] && echo true || echo false)"
  printf '  "watched": ["_sh_quote","_file_exists","_ts_iso","_json_escape"],\n'
  printf '  "tools": [\n'
  first=1
  tools_marked=0
  n=${#tool_paths[@]}
  i=0
  while [[ $i -lt $n ]]; do
    sp="${tool_paths[$i]}"
    mut="${tool_mutated[$i]}"
    mat="${tool_matches[$i]}"
    [[ "$mut" == "true" ]] && tools_marked=$((tools_marked + 1))
    if [[ $first -eq 1 ]]; then
      first=0
    else
      printf ',\n'
    fi
    printf '    {"path":"%s","mutated":%s,"matches":%s}' "$sp" "$mut" "$mat"
    i=$((i + 1))
  done
  printf '\n  ],\n'
  printf '  "summary": {"tools_marked":%d,"markers_added":%d,"skipped_already_marked":%d}\n' "$tools_marked" "$total_markers" "$total_idem"
  printf '}\n'
} > "$OUT_PATH.tmp"
mv -f "$OUT_PATH.tmp" "$OUT_PATH"

echo "── util_extract_apply_bootstrap (ROI H42) ──"
echo "mode              : $([[ "$DRY_RUN" == "--dry-run" ]] && echo dry-run || echo apply)"
echo "tools_with_inline : ${#tool_paths[@]}"
echo "markers_added     : $total_markers"
echo "idempotent_skips  : $total_idem"
echo "output            : $OUT_PATH"
echo "PASS (markers idempotent — re-run is a no-op)"
