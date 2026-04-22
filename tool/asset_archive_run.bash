#!/usr/bin/env bash
set -u
cd /Users/ghost/core/anima
ROOT="$(pwd)"
INVENTORY="$ROOT/state/asset_inventory.json"
LOG="$ROOT/state/asset_archive_log.jsonl"
LOCK="/tmp/asset_archive_run.lock"
export INVENTORY

# single-instance lock (macOS-compatible): check existing pid, otherwise claim
if [[ -f "$LOCK" ]]; then
  existing=$(cat "$LOCK" 2>/dev/null)
  if [[ -n "$existing" ]] && kill -0 "$existing" 2>/dev/null; then
    echo "[LOCKED] another instance alive pid=$existing — exit"
    exit 0
  fi
fi
echo $$ > "$LOCK"
trap 'rm -f "$LOCK"' EXIT

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
log() {
  local path="$1" action="$2" status="$3" detail="${4:-}"
  printf '{"ts":"%s","path":"%s","action":"%s","status":"%s","detail":"%s"}\n' \
    "$(ts)" "$path" "$action" "$status" "${detail//\"/\\\"}" >> "$LOG"
}

python3 - <<'PY' > /tmp/asset_archive_jobs.tsv
import json, os
inv=json.load(open(os.environ["INVENTORY"]))
rows=[]
for g in inv["groups"]:
  for a in g["assets"]:
    if a.get("action")=="archive_then_delete" and a.get("status")!="deleted":
      rows.append((a.get("size_bytes",0), a["path"], a["r2_bucket"], a["r2_key"]))
rows.sort(key=lambda r:-r[0])
for sz,p,b,k in rows:
  print(f"{sz}\t{p}\t{b}\t{k}")
PY

total_jobs=$(wc -l < /tmp/asset_archive_jobs.tsv | tr -d ' ')
echo "[$(ts)] START: $total_jobs jobs (largest-first, copyto for files)"
idx=0
while IFS=$'\t' read -r sz path bucket key; do
  idx=$((idx+1))
  echo ""
  echo "==== [$idx/$total_jobs] size=${sz} path=${path}"
  echo "     → r2:${bucket}/${key}"
  if [[ "$path" = /* ]]; then local_path="$path"; else local_path="$ROOT/$path"; fi
  if [[ ! -e "$local_path" ]]; then
    echo "  [SKIP] local missing"
    log "$path" "archive_then_delete" "skipped_missing" ""
    continue
  fi

  echo "  [UPLOAD] $(ts)"
  log "$path" "archive_then_delete" "uploading" ""
  if [[ -d "$local_path" ]]; then
    # directory: rclone copy with trailing /
    dst="r2:${bucket}/${key}"
    [[ "$dst" != */ ]] && dst="${dst}/"
    rclone copy "$local_path/" "$dst" \
      --transfers 4 --checkers 8 \
      --s3-chunk-size 64M --s3-upload-concurrency 4 \
      --stats 60s --stats-one-line
    rc=$?
  else
    # single file: rclone copyto for exact key mapping
    dst="r2:${bucket}/${key}"
    rclone copyto "$local_path" "$dst" \
      --s3-chunk-size 64M --s3-upload-concurrency 4 \
      --stats 60s --stats-one-line
    rc=$?
  fi

  if [[ $rc -ne 0 ]]; then
    echo "  [UPLOAD-FAIL] rc=$rc"
    log "$path" "archive_then_delete" "upload_failed" "rc=$rc"
    continue
  fi
  echo "  [UPLOAD-OK] $(ts)"

  # verify size
  if [[ -d "$local_path" ]]; then
    rclone check "$local_path/" "$dst" --size-only 2>&1 | tail -3
    vrc=${PIPESTATUS[0]}
    [[ $vrc -eq 0 ]] && vok=1 || vok=0
  else
    LS=$(stat -f '%z' "$local_path" 2>/dev/null)
    RS=$(rclone lsjson "$dst" 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print(d[0].get('Size',-1) if d else -1)" 2>/dev/null || echo -1)
    echo "  local=$LS r2=$RS"
    [[ "$LS" = "$RS" ]] && vok=1 || vok=0
  fi

  if [[ "$vok" = "1" ]]; then
    echo "  [VERIFIED] deleting local"
    log "$path" "archive_then_delete" "verified" ""
    rm -rf "$local_path"
    echo "  [DELETED] $(ts)"
    log "$path" "archive_then_delete" "deleted" ""
    df -h /Users/ghost 2>/dev/null | tail -1 | awk '{print "  disk: "$3" used, "$4" free ("$5")"}'
  else
    echo "  [VERIFY-FAIL] keeping local"
    log "$path" "archive_then_delete" "verify_failed" ""
  fi
done < /tmp/asset_archive_jobs.tsv
echo ""
echo "[$(ts)] DONE"
log "__all__" "archive_then_delete" "done" "total_jobs=$total_jobs"
