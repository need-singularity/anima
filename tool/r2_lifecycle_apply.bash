#!/usr/bin/env bash
# tool/r2_lifecycle_apply.bash — ROI G37: apply R2 lifecycle policy
#
# DEFAULT: dry-run (prints rclone/aws-s3 commands; no PUT performed).
# --apply: actually PUT the lifecycle JSON to each bucket.
#
# Backends (preferred → fallback):
#   1. rclone backend "r2:" with `rclone backend lifecycle` (Cloudflare R2)
#   2. aws s3api put-bucket-lifecycle-configuration --endpoint-url <r2_endpoint>
#
# Required env (only when --apply):
#   R2_ENDPOINT_URL  — e.g. https://<accountid>.r2.cloudflarestorage.com
#   AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY — R2 token credentials
#
# Usage:
#   tool/r2_lifecycle_apply.bash                     # dry (default)
#   tool/r2_lifecycle_apply.bash --apply             # PUT to all buckets
#   tool/r2_lifecycle_apply.bash --apply --bucket X  # single-bucket override
#
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POLICY="${R2_POLICY:-$ROOT/config/r2_lifecycle_policy.json}"
LOG="$ROOT/state/r2_lifecycle_apply.log"
APPLY=0
ONLY_BUCKET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --bucket) ONLY_BUCKET="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "[r2_lifecycle_apply] unknown arg: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$ROOT/state"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

if [[ ! -f "$POLICY" ]]; then
  echo "[r2_lifecycle_apply] policy missing: $POLICY" >&2
  exit 2
fi

# Extract bucket list from JSON via python3 (always available on macOS).
BUCKETS=$(python3 -c "import json,sys;d=json.load(open('$POLICY'));print(' '.join(d.get('buckets',[])))" 2>/dev/null)
if [[ -z "$BUCKETS" ]]; then
  echo "[r2_lifecycle_apply] no buckets declared in policy" >&2
  exit 2
fi
if [[ -n "$ONLY_BUCKET" ]]; then BUCKETS="$ONLY_BUCKET"; fi

MODE="dry-run"
[[ "$APPLY" -eq 1 ]] && MODE="apply"
echo "[$(ts)] r2_lifecycle_apply mode=$MODE policy=$POLICY"
echo "[$(ts)] target buckets: $BUCKETS"

HAVE_RCLONE=0
HAVE_AWS=0
command -v rclone >/dev/null 2>&1 && HAVE_RCLONE=1
command -v aws    >/dev/null 2>&1 && HAVE_AWS=1
echo "[$(ts)] backend: rclone=$HAVE_RCLONE aws=$HAVE_AWS"

rc_total=0
for b in $BUCKETS; do
  echo ""
  echo "==== bucket: $b"
  if [[ "$APPLY" -eq 0 ]]; then
    echo "  [DRY] would PUT lifecycle to bucket '$b'"
    if [[ "$HAVE_RCLONE" -eq 1 ]]; then
      echo "  [DRY] cmd: rclone backend lifecycle r2:$b $POLICY"
    fi
    if [[ "$HAVE_AWS" -eq 1 ]]; then
      echo "  [DRY] cmd: aws s3api put-bucket-lifecycle-configuration \\"
      echo "          --bucket $b --lifecycle-configuration file://$POLICY \\"
      echo "          --endpoint-url \"\$R2_ENDPOINT_URL\""
    fi
    if [[ "$HAVE_RCLONE" -eq 0 && "$HAVE_AWS" -eq 0 ]]; then
      echo "  [DRY] WARN: neither rclone nor aws CLI present — install one before --apply"
    fi
    continue
  fi

  # APPLY path
  applied=0
  if [[ "$HAVE_RCLONE" -eq 1 ]]; then
    echo "  [APPLY] rclone backend lifecycle r2:$b ..."
    if rclone backend lifecycle "r2:$b" "$POLICY" 2>>"$LOG"; then
      echo "  [APPLY-OK] rclone bucket=$b"
      applied=1
    else
      echo "  [APPLY-WARN] rclone failed (rc=$?) — falling back"
    fi
  fi
  if [[ "$applied" -eq 0 && "$HAVE_AWS" -eq 1 ]]; then
    if [[ -z "${R2_ENDPOINT_URL:-}" ]]; then
      echo "  [APPLY-FAIL] R2_ENDPOINT_URL not set" >&2
      rc_total=$((rc_total+1))
      continue
    fi
    echo "  [APPLY] aws s3api put-bucket-lifecycle-configuration --bucket $b ..."
    if aws s3api put-bucket-lifecycle-configuration \
         --bucket "$b" \
         --lifecycle-configuration "file://$POLICY" \
         --endpoint-url "$R2_ENDPOINT_URL" 2>>"$LOG"; then
      echo "  [APPLY-OK] aws bucket=$b"
      applied=1
    else
      echo "  [APPLY-FAIL] aws rc=$?" >&2
      rc_total=$((rc_total+1))
    fi
  fi
  if [[ "$applied" -eq 0 ]]; then
    echo "  [APPLY-FAIL] no backend succeeded for bucket=$b" >&2
    rc_total=$((rc_total+1))
  fi
done

echo ""
EST_PCT=$(python3 -c "import json;print(json.load(open('$POLICY')).get('estimated_savings',{}).get('monthly_pct_reduction',0))" 2>/dev/null)
echo "[$(ts)] DONE mode=$MODE failures=$rc_total estimated_monthly_pct_reduction=${EST_PCT:-0}%"
exit 0
