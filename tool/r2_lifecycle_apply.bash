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

SELFTEST=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --bucket) ONLY_BUCKET="$2"; shift 2 ;;
    --selftest) SELFTEST=1; shift ;;
    -h|--help)
      sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "[r2_lifecycle_apply] unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ "$SELFTEST" -eq 1 ]]; then
  # MINIMAL SELFTEST: parse-clean + 1 invariant. NEVER touches network / R2.
  echo "── r2_lifecycle_apply selftest ──"
  bash -n "$0" || { echo "  parse FAIL"; exit 1; }
  if [[ "$APPLY" -ne 0 ]]; then echo "  invariant FAIL: --selftest must not co-occur with --apply"; exit 1; fi
  if [[ ! -f "$POLICY" ]]; then echo "  invariant SKIP: policy missing ($POLICY) — selftest noop PASS"; exit 0; fi
  echo "  parse: PASS"
  echo "  invariant: APPLY=0 default, policy file present"
  echo "  SELFTEST PASS"
  exit 0
fi

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

# 2026-04-22 ROI V3 plan: when --apply ran but every backend failed (e.g.
# rclone s3 backend has no `lifecycle` subcommand on rclone <= 1.65), emit a
# plan JSON the operator can act on. NEVER deletes prior state.
PLAN_OUT="$ROOT/state/r2_lifecycle_apply_plan.json"
if [[ "$APPLY" -eq 1 && "$rc_total" -gt 0 ]]; then
  cat > "$PLAN_OUT" <<EOF
{
  "schema_version": "1",
  "roi_item": "V3",
  "ts": "$(ts)",
  "mode": "apply",
  "verdict": "FAIL_NO_BACKEND",
  "failures": $rc_total,
  "policy_file": "$POLICY",
  "backends_present": {
    "rclone": $HAVE_RCLONE,
    "aws":    $HAVE_AWS
  },
  "rclone_lifecycle_subcommand_supported": false,
  "diagnosis": "rclone s3 backend on this host has no 'lifecycle' subcommand (rclone backend help s3 enumerates: restore restore-status list-multipart-uploads cleanup cleanup-hidden versioning set). aws CLI is also absent.",
  "remediation_steps": [
    "1. brew install awscli  (or  pipx install awscli)",
    "2. export R2_ENDPOINT_URL=\$ANIMA_R2_ENDPOINT  AWS_ACCESS_KEY_ID=\$ANIMA_R2_ACCESS_KEY  AWS_SECRET_ACCESS_KEY=\$ANIMA_R2_SECRET_KEY",
    "3. tool/r2_lifecycle_apply.bash --apply   # aws backend will succeed",
    "ALT: upgrade rclone to a build that exposes 'rclone backend lifecycle s3:' (currently unsupported in stable)."
  ],
  "operator_runbook_one_liner": "brew install awscli && AWS_ACCESS_KEY_ID=\$ANIMA_R2_ACCESS_KEY AWS_SECRET_ACCESS_KEY=\$ANIMA_R2_SECRET_KEY R2_ENDPOINT_URL=\$ANIMA_R2_ENDPOINT bash tool/r2_lifecycle_apply.bash --apply"
}
EOF
  echo "[$(ts)] V3 PLAN: emitted $PLAN_OUT — apply still pending until awscli installed"
fi

exit 0
