#!/usr/bin/env bash
# tool/proposal_conflict_selftest.bash — runtime selftest harness for
#   tool/proposal_conflict_detect.hexa  +  tool/proposal_conflict_resolve.hexa
#
# Hexa stage0 interpreter on this host is REPL-only, so the .hexa selftests
# cannot be exercised in-place. This bash harness re-implements the SAME
# detect/resolve algorithms via jq + filesystem ops to give a concrete pass/fail
# verdict on the design.
#
# Spec source: docs/anima_proposal_stack_paradigm_20260422.md §3 step 6 + §6.
#
# USAGE: bash tool/proposal_conflict_selftest.bash
# EXIT : 0 = ALL PASS · 1 = any FAIL

set -euo pipefail

SANDBOX="${TMPDIR:-/tmp}/anima_proposal_conflict_selftest_$$"
trap 'rm -rf "$SANDBOX"' EXIT

PEND="$SANDBOX/pending"
REJ="$SANDBOX/rejected"
DEB="$SANDBOX/debate"
mkdir -p "$PEND" "$REJ" "$DEB"

now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }

atomic_write() {
  local path="$1" body="$2"
  mkdir -p "$(dirname "$path")"
  local tmp="$path.tmp"
  printf '%s' "$body" > "$tmp"
  mv -f "$tmp" "$path"
}

pair_slug() {
  local a="$1" b="$2"
  if [[ "$a" < "$b" || "$a" == "$b" ]]; then echo "${a}__vs__${b}"; else echo "${b}__vs__${a}"; fi
}

# ─── DETECT (mirrors proposal_conflict_detect.hexa) ────────────────

# Returns 0/1 = explicit conflict
detect_explicit() {
  local fa="$1" fb="$2"
  local id_a id_b cw_a cw_b
  id_a=$(jq -r '.id' "$fa"); id_b=$(jq -r '.id' "$fb")
  cw_a=$(jq -r '(.conflicts_with // []) | .[]' "$fa" 2>/dev/null || true)
  cw_b=$(jq -r '(.conflicts_with // []) | .[]' "$fb" 2>/dev/null || true)
  grep -qx "$id_b" <<<"$cw_a" && return 0
  grep -qx "$id_a" <<<"$cw_b" && return 0
  return 1
}

# Echoes path of file_direction conflict, empty if none.
detect_file_direction() {
  local fa="$1" fb="$2"
  jq -nr --slurpfile a "$fa" --slurpfile b "$fb" '
    def tf(x):
      (x[0].touched_files // [])
      | map(if type == "string" then {path: ., direction: "modify"} else . end);
    [tf($a)[] as $ax | tf($b)[] as $bx
      | select($ax.path == $bx.path)
      | select( ($ax.direction == "add" and $bx.direction == "remove")
             or ($ax.direction == "remove" and $bx.direction == "add") )
      | $ax.path] | first // ""
  '
}

# Returns 0/1 = paradigm-axis conflict
detect_paradigm_axis() {
  local fa="$1" fb="$2"
  jq -e -nr --slurpfile a "$fa" --slurpfile b "$fb" '
    ($a[0] | .kind == "paradigm" and (.axis // "") != "") and
    ($b[0] | .kind == "paradigm" and (.axis // "") != "") and
    ($a[0].axis == $b[0].axis) and
    ($a[0].hypothesis // "") != ($b[0].hypothesis // "")
  ' >/dev/null 2>&1
}

# Emit debate file (idempotent)
emit_debate() {
  local id_a="$1" id_b="$2" kind="$3" reason="$4"
  local slug; slug=$(pair_slug "$id_a" "$id_b")
  local path="$DEB/$slug.json"
  if [[ -f "$path" ]]; then
    local st; st=$(jq -r '.status' "$path")
    if [[ "$st" == "open" || "$st" == "resolved" ]]; then echo "$path"; return; fi
  fi
  local lo hi
  if [[ "$id_a" < "$id_b" || "$id_a" == "$id_b" ]]; then lo="$id_a"; hi="$id_b"; else lo="$id_b"; hi="$id_a"; fi
  jq -n --arg slug "$slug" --arg lo "$lo" --arg hi "$hi" --arg k "$kind" \
        --arg r "$reason" --arg ts "$(now_iso)" '
    {schema:"anima.proposal.debate.v1", pair_slug:$slug, ids:[$lo,$hi],
     kind:$k, reason:$r, status:"open", created_at:$ts,
     awaiting:"user_resolution", resolved_at:null, winner:null,
     loser:null, resolution_reason:null}
  ' > "$path.tmp"
  mv -f "$path.tmp" "$path"
  echo "$path"
}

scan_all() {
  local files=()
  while IFS= read -r -d '' f; do files+=("$f"); done < <(find "$PEND" -name "*.json" -print0 | sort -z)
  local n=${#files[@]} i=0
  while [[ $i -lt $n ]]; do
    local j=$((i+1))
    while [[ $j -lt $n ]]; do
      local fa="${files[$i]}" fb="${files[$j]}"
      local ida idb; ida=$(jq -r '.id' "$fa"); idb=$(jq -r '.id' "$fb")
      local kind="" reason="" path=""
      if detect_explicit "$fa" "$fb"; then
        kind="explicit"; reason="conflicts_with field declares incompatibility"
      elif path=$(detect_file_direction "$fa" "$fb"); [[ -n "$path" ]]; then
        kind="file_direction"; reason="opposite add/remove on path: $path"
      elif detect_paradigm_axis "$fa" "$fb"; then
        local ax; ax=$(jq -r '.axis' "$fa")
        kind="paradigm_axis"; reason="kind=paradigm, axis=$ax, divergent hypothesis"
      fi
      if [[ -n "$kind" ]]; then echo "$ida|$idb|$kind|$reason"; fi
      j=$((j+1))
    done
    i=$((i+1))
  done
}

# ─── RESOLVE (mirrors proposal_conflict_resolve.hexa) ─────────────

resolve_pair() {
  local id1="$1" id2="$2" winner="$3" reason="$4"
  if [[ "$winner" != "$id1" && "$winner" != "$id2" ]]; then
    echo "ERR: winner $winner not in [$id1,$id2]" >&2; return 2
  fi
  local loser; if [[ "$winner" == "$id1" ]]; then loser="$id2"; else loser="$id1"; fi
  local slug; slug=$(pair_slug "$id1" "$id2")
  local dpath="$DEB/$slug.json"
  [[ -f "$dpath" ]] || { echo "ERR: debate $dpath missing" >&2; return 3; }
  local st; st=$(jq -r '.status' "$dpath")
  if [[ "$st" == "resolved" ]]; then
    local ew; ew=$(jq -r '.winner' "$dpath")
    if [[ "$ew" == "$winner" ]]; then return 0; fi
    echo "ERR: already resolved with winner=$ew, refusing $winner" >&2; return 4
  fi
  local lpath="$PEND/$loser.json" wpath="$PEND/$winner.json"
  [[ -f "$wpath" ]] || { echo "ERR: winner pending file missing" >&2; return 5; }
  [[ -f "$lpath" ]] || { echo "ERR: loser pending file missing"  >&2; return 5; }
  local now; now=$(now_iso)
  local conflict_reason="lost debate vs $winner — $reason"
  jq --arg now "$now" --arg r "$conflict_reason" \
     '. + {user_status:"rejected", user_decision_at:$now, user_decision_reason:$r}' \
     "$lpath" > "$REJ/$loser.json.tmp"
  mv -f "$REJ/$loser.json.tmp" "$REJ/$loser.json"
  rm -f "$lpath"
  jq --arg now "$now" --arg w "$winner" --arg l "$loser" --arg rr "$reason" \
     '. + {status:"resolved", awaiting:null, resolved_at:$now, winner:$w, loser:$l, resolution_reason:$rr}' \
     "$dpath" > "$dpath.tmp"
  mv -f "$dpath.tmp" "$dpath"
  return 0
}

revoke_pair() {
  local slug="$1"
  local dpath="$DEB/$slug.json"
  [[ -f "$dpath" ]] || { echo "ERR: debate missing" >&2; return 3; }
  local st; st=$(jq -r '.status' "$dpath")
  [[ "$st" == "resolved" ]] || { echo "ERR: not resolved (st=$st)" >&2; return 6; }
  local loser; loser=$(jq -r '.loser' "$dpath")
  [[ -n "$loser" && "$loser" != "null" ]] || { echo "ERR: no loser recorded" >&2; return 7; }
  local rpath="$REJ/$loser.json"
  [[ -f "$rpath" ]] || { echo "ERR: rejected file missing" >&2; return 8; }
  jq '. + {user_status:"pending", user_decision_at:null, user_decision_reason:null}' \
     "$rpath" > "$PEND/$loser.json.tmp"
  mv -f "$PEND/$loser.json.tmp" "$PEND/$loser.json"
  rm -f "$rpath"
  jq '. + {status:"open", awaiting:"user_resolution", resolved_at:null, winner:null, loser:null, resolution_reason:null}' \
     "$dpath" > "$dpath.tmp"
  mv -f "$dpath.tmp" "$dpath"
  return 0
}

# ─── DETECT SELFTEST ──────────────────────────────────────────────

PASS_D=0; FAIL_D=0
echo "── proposal_conflict_detect selftest ──"

# Seed 4 proposals → expect 2 conflict pairs:
#   (A1, A2) explicit
#   (A3, A4) file_direction (add vs remove on shared/foo.hexa)
cat >"$PEND/A1.json" <<'JSON'
{"id":"A1","kind":"tool","conflicts_with":["A2"],"touched_files":[]}
JSON
cat >"$PEND/A2.json" <<'JSON'
{"id":"A2","kind":"tool","conflicts_with":[],"touched_files":[]}
JSON
cat >"$PEND/A3.json" <<'JSON'
{"id":"A3","kind":"paradigm","axis":"eta","hypothesis":"X","touched_files":[{"path":"shared/foo.hexa","direction":"remove"}]}
JSON
cat >"$PEND/A4.json" <<'JSON'
{"id":"A4","kind":"paradigm","axis":"eta","hypothesis":"Y","touched_files":[{"path":"shared/foo.hexa","direction":"add"}]}
JSON

CONF=()
while IFS= read -r line; do CONF+=("$line"); done < <(scan_all)
echo "  detected pairs: ${#CONF[@]}"
for c in "${CONF[@]}"; do echo "    $c"; done

if [[ ${#CONF[@]} -eq 2 ]]; then
  echo "  S1 PASS: 2 conflict pairs"
  PASS_D=$((PASS_D+1))
else
  echo "  S1 FAIL: expected 2 pairs, got ${#CONF[@]}"
  FAIL_D=$((FAIL_D+1))
fi

# S2 — emit debate files
written=0
for c in "${CONF[@]}"; do
  IFS='|' read -r ida idb kind reason <<<"$c"
  emit_debate "$ida" "$idb" "$kind" "$reason" >/dev/null
  written=$((written+1))
done
emitted=$(find "$DEB" -name "*.json" | wc -l | tr -d ' ')
if [[ "$emitted" == "$written" && "$written" == "2" ]]; then
  echo "  S2 PASS: 2 debate files written"
  PASS_D=$((PASS_D+1))
else
  echo "  S2 FAIL: emitted=$emitted written=$written (want 2)"
  FAIL_D=$((FAIL_D+1))
fi

# S3 — idempotent re-emit
sample_path=$(find "$DEB" -name "*.json" | head -1)
mt_before=$(stat -f %m "$sample_path")
sleep 1
for c in "${CONF[@]}"; do
  IFS='|' read -r ida idb kind reason <<<"$c"
  emit_debate "$ida" "$idb" "$kind" "$reason" >/dev/null
done
mt_after=$(stat -f %m "$sample_path")
if [[ "$mt_before" == "$mt_after" ]]; then
  echo "  S3 PASS: idempotent re-emit (open debate preserved)"
  PASS_D=$((PASS_D+1))
else
  echo "  S3 FAIL: mtime changed (before=$mt_before after=$mt_after)"
  FAIL_D=$((FAIL_D+1))
fi

# S4 — schema completeness
sample=$(jq -r '[has("schema"),has("pair_slug"),has("ids"),has("kind"),has("reason"),has("status"),has("created_at"),has("winner")] | all' "$sample_path")
if [[ "$sample" == "true" ]]; then
  echo "  S4 PASS: debate schema complete"
  PASS_D=$((PASS_D+1))
else
  echo "  S4 FAIL: missing schema fields"
  FAIL_D=$((FAIL_D+1))
fi

echo "proposal_conflict_detect: ${PASS_D}/$((PASS_D+FAIL_D)) PASS"

# Save debate sample for report
DEB_SAMPLE="$sample_path"
DEB_SAMPLE_BODY=$(cat "$DEB_SAMPLE")

# ─── RESOLVE SELFTEST ─────────────────────────────────────────────

PASS_R=0; FAIL_R=0
echo
echo "── proposal_conflict_resolve selftest ──"

# Reset sandbox: 4 fresh pending + 2 fresh debates.
rm -rf "$PEND" "$REJ" "$DEB"
mkdir -p "$PEND" "$REJ" "$DEB"
for id in B1 B2 B3 B4; do
  cat >"$PEND/$id.json" <<JSON
{"id":"$id","version":1,"title":"synthetic $id","kind":"tool","user_status":"pending"}
JSON
done
emit_debate "B1" "B2" "explicit" "synthetic conflict 1" >/dev/null
emit_debate "B3" "B4" "file_direction" "synthetic conflict 2" >/dev/null

# S1 — resolve pair#1 (B1 wins)
if resolve_pair "B1" "B2" "B1" "B1 has stronger evidence" \
   && [[ -f "$REJ/B2.json" && ! -f "$PEND/B2.json" && -f "$PEND/B1.json" ]] \
   && [[ "$(jq -r .status "$DEB/B1__vs__B2.json")" == "resolved" ]] \
   && [[ "$(jq -r .winner "$DEB/B1__vs__B2.json")" == "B1" ]] \
   && jq -r .user_decision_reason "$REJ/B2.json" | grep -q "lost debate vs B1"; then
  echo "  S1 PASS: pair#1 resolved (B1 wins, B2 → rejected)"
  PASS_R=$((PASS_R+1))
else
  echo "  S1 FAIL"; FAIL_R=$((FAIL_R+1))
fi

# S2 — idempotent re-resolve (same winner)
if resolve_pair "B1" "B2" "B1" "B1 has stronger evidence"; then
  echo "  S2 PASS: idempotent re-resolve no-op"
  PASS_R=$((PASS_R+1))
else
  echo "  S2 FAIL: re-resolve unexpectedly errored"; FAIL_R=$((FAIL_R+1))
fi

# S3 — mismatched re-resolve must error (exit 4)
set +e
resolve_pair "B1" "B2" "B2" "trying to flip"; rc=$?
set -e
if [[ "$rc" == "4" ]]; then
  echo "  S3 PASS: mismatched re-resolve refused (exit 4)"
  PASS_R=$((PASS_R+1))
else
  echo "  S3 FAIL: expected exit 4, got $rc"; FAIL_R=$((FAIL_R+1))
fi

# S4 — revoke pair#1 → loser back to pending, debate=open
if revoke_pair "B1__vs__B2" \
   && [[ -f "$PEND/B2.json" && ! -f "$REJ/B2.json" ]] \
   && [[ "$(jq -r .status "$DEB/B1__vs__B2.json")" == "open" ]]; then
  echo "  S4 PASS: revoke restored loser to pending, debate=open"
  PASS_R=$((PASS_R+1))
else
  echo "  S4 FAIL"; FAIL_R=$((FAIL_R+1))
fi

# S5 — resolve pair#2 (B4 wins)
if resolve_pair "B3" "B4" "B4" "B4 covers both axes" \
   && [[ -f "$REJ/B3.json" && ! -f "$PEND/B3.json" ]]; then
  echo "  S5 PASS: pair#2 resolved (B4 wins, B3 → rejected)"
  PASS_R=$((PASS_R+1))
else
  echo "  S5 FAIL"; FAIL_R=$((FAIL_R+1))
fi

echo "proposal_conflict_resolve: ${PASS_R}/$((PASS_R+FAIL_R)) PASS"

# ─── FINAL VERDICT + ARTIFACTS ────────────────────────────────────

TOTAL=$((PASS_D+PASS_R))
FAILS=$((FAIL_D+FAIL_R))

echo
echo "── selftest verdicts ──"
echo "  detect : ${PASS_D}/$((PASS_D+FAIL_D)) PASS"
echo "  resolve: ${PASS_R}/$((PASS_R+FAIL_R)) PASS"
echo
echo "── debate folder sample (post-detect) ──"
echo "$DEB_SAMPLE_BODY"
echo
echo "── conflict detection sample (raw scan_all output) ──"
for c in "${CONF[@]}"; do echo "  $c"; done

if [[ "$FAILS" == "0" ]]; then
  echo
  echo "ALL PASS (${TOTAL}/${TOTAL})"
  exit 0
fi
echo
echo "FAIL (${TOTAL}/$((TOTAL+FAILS)) PASS, ${FAILS} fails)"
exit 1
