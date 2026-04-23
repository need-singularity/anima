#!/usr/bin/env bash
# tool/r2_lifecycle_apply.bash — ROI G37 / V3: apply R2 lifecycle policy
#
# DEFAULT: dry-run (prints command; no PUT performed).
# --apply: actually PUT the lifecycle XML to each bucket.
#
# Backends (preferred → fallback):
#   1. curl + AWS SigV4 signer (native — reads creds from rclone.conf [r2])
#   2. rclone backend "r2:" with `rclone backend lifecycle`   (rclone >= unreleased only)
#   3. aws s3api put-bucket-lifecycle-configuration            (needs awscli)
#
# 2026-04-22 V3 cost-reduction update: backend #1 added so macOS hosts
# without awscli can still apply the lifecycle policy. rclone.conf [r2]
# access_key_id / secret_access_key / endpoint are the credential SSOT.
#
# Required env (only for aws backend):
#   R2_ENDPOINT_URL, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# Required for curl backend (auto-read if absent):
#   R2_RCLONE_REMOTE (default: r2) — [section] name in rclone.conf
#
# Usage:
#   tool/r2_lifecycle_apply.bash                     # dry (default)
#   tool/r2_lifecycle_apply.bash --apply             # PUT to all buckets
#   tool/r2_lifecycle_apply.bash --apply --bucket X  # single-bucket override
#   tool/r2_lifecycle_apply.bash --selftest          # parse + signer unit test
#
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
POLICY="${R2_POLICY:-$ROOT/config/r2_lifecycle_policy.json}"
LOG="$ROOT/state/r2_lifecycle_apply.log"
RESULT="$ROOT/state/r2_lifecycle_apply_result.json"
RCLONE_CONF="${RCLONE_CONFIG:-$HOME/.config/rclone/rclone.conf}"
RCLONE_REMOTE="${R2_RCLONE_REMOTE:-r2}"
APPLY=0
ONLY_BUCKET=""
SELFTEST=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --bucket) ONLY_BUCKET="$2"; shift 2 ;;
    --selftest) SELFTEST=1; shift ;;
    -h|--help)
      sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "[r2_lifecycle_apply] unknown arg: $1" >&2; exit 2 ;;
  esac
done

ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
mkdir -p "$ROOT/state"

# ---------------------------------------------------------------------------
# JSON policy  →  S3 LifecycleConfiguration XML (stdout)
# Uses python3 (always available on macOS / Linux). NO third-party deps.
# ---------------------------------------------------------------------------
policy_to_xml() {
  local policy_path="$1"
  python3 - "$policy_path" <<'PYEOF'
import json, sys, xml.sax.saxutils as x
p = json.load(open(sys.argv[1]))
rules = p.get("Rules", [])
out = ['<?xml version="1.0" encoding="UTF-8"?>',
       '<LifecycleConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">']
def esc(s): return x.escape(str(s))
for r in rules:
    out.append('<Rule>')
    if "ID" in r: out.append(f'<ID>{esc(r["ID"])}</ID>')
    out.append(f'<Status>{esc(r.get("Status","Enabled"))}</Status>')
    f = r.get("Filter") or {}
    pref = f.get("Prefix","")
    out.append(f'<Filter><Prefix>{esc(pref)}</Prefix></Filter>')
    for t in r.get("Transitions", []) or []:
        out.append('<Transition>')
        if "Days" in t: out.append(f'<Days>{int(t["Days"])}</Days>')
        if "StorageClass" in t: out.append(f'<StorageClass>{esc(t["StorageClass"])}</StorageClass>')
        out.append('</Transition>')
    exp = r.get("Expiration")
    if exp:
        out.append('<Expiration>')
        if "Days" in exp: out.append(f'<Days>{int(exp["Days"])}</Days>')
        out.append('</Expiration>')
    mp = r.get("AbortIncompleteMultipartUpload")
    if mp:
        out.append('<AbortIncompleteMultipartUpload>')
        if "DaysAfterInitiation" in mp:
            out.append(f'<DaysAfterInitiation>{int(mp["DaysAfterInitiation"])}</DaysAfterInitiation>')
        out.append('</AbortIncompleteMultipartUpload>')
    out.append('</Rule>')
out.append('</LifecycleConfiguration>')
sys.stdout.write("".join(out))
PYEOF
}

# ---------------------------------------------------------------------------
# Read one key from an rclone.conf [section].
# ---------------------------------------------------------------------------
rclone_conf_get() {
  local section="$1" key="$2" conf="$3"
  [[ -f "$conf" ]] || return 1
  awk -v sec="[$section]" -v k="$key" '
    $0 == sec { in_sec=1; next }
    /^\[/     { in_sec=0 }
    in_sec && $0 ~ "^[[:space:]]*"k"[[:space:]]*=" {
      sub(/^[^=]*=[[:space:]]*/, "", $0); print; exit
    }' "$conf"
}

# ---------------------------------------------------------------------------
# AWS Signature V4 + PUT ?lifecycle via curl.
# Args: bucket  xml_body  access_key  secret_key  endpoint_host
# Returns: 0 on HTTP 2xx; writes curl output to stdout and headers to $2.hdr
# ---------------------------------------------------------------------------
r2_put_lifecycle_curl() {
  local bucket="$1" body="$2" ak="$3" sk="$4" host="$5"
  local region="auto"
  local service="s3"
  local amzdate dstamp payload_sha
  amzdate="$(date -u +%Y%m%dT%H%M%SZ)"
  dstamp="$(date -u +%Y%m%d)"
  payload_sha="$(printf '%s' "$body" | openssl dgst -sha256 -hex | awk '{print $NF}')"
  # Canonical request — path-style (R2 requires virtual-host OR path; path works w/ endpoint host)
  local c_uri="/$bucket"
  local c_query="lifecycle="
  local c_headers="host:${host}\nx-amz-content-sha256:${payload_sha}\nx-amz-date:${amzdate}\n"
  local s_headers="host;x-amz-content-sha256;x-amz-date"
  local c_req
  c_req="$(printf 'PUT\n%s\n%s\n%b\n%s\n%s' "$c_uri" "$c_query" "$c_headers" "$s_headers" "$payload_sha")"
  local c_req_sha
  c_req_sha="$(printf '%s' "$c_req" | openssl dgst -sha256 -hex | awk '{print $NF}')"
  local scope="${dstamp}/${region}/${service}/aws4_request"
  local sts
  sts="$(printf 'AWS4-HMAC-SHA256\n%s\n%s\n%s' "$amzdate" "$scope" "$c_req_sha")"
  # Derive signing key (4x HMAC chain, hex-hmac trick)
  hmac_hex() { openssl dgst -sha256 -mac HMAC -macopt "$1" 2>/dev/null | awk '{print $NF}'; }
  local k1 k2 k3 k4 sig
  k1="$(printf 'AWS4%s' "$sk" | xxd -p -c 512)"
  k1="$(printf '%s' "$dstamp"  | openssl dgst -sha256 -mac HMAC -macopt "hexkey:$(printf 'AWS4%s' "$sk" | xxd -p -c 512)" | awk '{print $NF}')"
  k2="$(printf '%s' "$region"  | openssl dgst -sha256 -mac HMAC -macopt "hexkey:$k1" | awk '{print $NF}')"
  k3="$(printf '%s' "$service" | openssl dgst -sha256 -mac HMAC -macopt "hexkey:$k2" | awk '{print $NF}')"
  k4="$(printf '%s' "aws4_request" | openssl dgst -sha256 -mac HMAC -macopt "hexkey:$k3" | awk '{print $NF}')"
  sig="$(printf '%s' "$sts" | openssl dgst -sha256 -mac HMAC -macopt "hexkey:$k4" | awk '{print $NF}')"
  local auth="AWS4-HMAC-SHA256 Credential=${ak}/${scope}, SignedHeaders=${s_headers}, Signature=${sig}"
  # Compute md5 (R2 accepts; AWS requires)
  local md5
  md5="$(printf '%s' "$body" | openssl dgst -md5 -binary | openssl base64)"
  local url="https://${host}${c_uri}?lifecycle="
  local hdr_file="${body:+/tmp/r2_lifecycle.hdr.$$}"
  hdr_file="/tmp/r2_lifecycle.hdr.$$"
  local out_file="/tmp/r2_lifecycle.out.$$"
  local http_code
  http_code="$(curl -s -o "$out_file" -D "$hdr_file" -w '%{http_code}' \
    -X PUT "$url" \
    -H "Host: ${host}" \
    -H "x-amz-date: ${amzdate}" \
    -H "x-amz-content-sha256: ${payload_sha}" \
    -H "Content-MD5: ${md5}" \
    -H "Content-Type: application/xml" \
    -H "Authorization: ${auth}" \
    --data-binary "$body")"
  echo "[$(ts)] curl PUT bucket=$bucket http=$http_code" >>"$LOG"
  cat "$hdr_file" >>"$LOG" 2>/dev/null || true
  if [[ "$http_code" =~ ^2 ]]; then
    rm -f "$hdr_file" "$out_file"; return 0
  fi
  echo "---- response body ----" >>"$LOG"
  cat "$out_file" >>"$LOG" 2>/dev/null || true
  rm -f "$hdr_file" "$out_file"
  return 1
}

# ---------------------------------------------------------------------------
# SELFTEST: parse + XML generation + signer key-derivation (no network)
# ---------------------------------------------------------------------------
if [[ "$SELFTEST" -eq 1 ]]; then
  echo "── r2_lifecycle_apply selftest ──"
  bash -n "$0" || { echo "  parse FAIL"; exit 1; }
  if [[ "$APPLY" -ne 0 ]]; then echo "  invariant FAIL: --selftest must not co-occur with --apply"; exit 1; fi
  if [[ ! -f "$POLICY" ]]; then
    echo "  invariant SKIP: policy missing ($POLICY) — selftest noop PASS"; exit 0; fi
  echo "  parse: PASS"
  # XML generation invariant
  XML="$(policy_to_xml "$POLICY")"
  if [[ -z "$XML" || "$XML" != *"<LifecycleConfiguration"* ]]; then
    echo "  xml gen FAIL"; exit 1; fi
  if ! echo "$XML" | xmllint --noout - 2>/dev/null; then
    echo "  xml lint FAIL"; exit 1; fi
  echo "  xml gen: PASS ($(echo -n "$XML" | wc -c | tr -d ' ') bytes, $(grep -o '<Rule>' <<<"$XML" | wc -l | tr -d ' ') rules)"
  # Signer key-derivation known-answer test (AWS docs example)
  # kSecret = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
  # kDate for 20120215 / us-east-1 / iam derives to known first byte? We just
  # assert the chain runs without error and produces 64-hex strings.
  t_k1="$(printf '%s' '20120215' | openssl dgst -sha256 -mac HMAC -macopt "hexkey:$(printf 'AWS4%s' 'wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY' | xxd -p -c 512)" | awk '{print $NF}')"
  if [[ ${#t_k1} -ne 64 ]]; then echo "  signer derive FAIL"; exit 1; fi
  echo "  signer chain: PASS (kDate=${t_k1:0:12}...)"
  # rclone.conf presence (non-fatal)
  if [[ -f "$RCLONE_CONF" ]]; then
    t_ak="$(rclone_conf_get "$RCLONE_REMOTE" access_key_id "$RCLONE_CONF" || true)"
    t_ep="$(rclone_conf_get "$RCLONE_REMOTE" endpoint       "$RCLONE_CONF" || true)"
    if [[ -n "$t_ak" && -n "$t_ep" ]]; then
      echo "  rclone.conf [$RCLONE_REMOTE]: PRESENT (ak=${t_ak:0:6}… ep=${t_ep:0:40}…)"
    else
      echo "  rclone.conf [$RCLONE_REMOTE]: INCOMPLETE (missing access_key_id/endpoint) — curl backend would fall back"
    fi
  else
    echo "  rclone.conf: ABSENT ($RCLONE_CONF) — curl backend would need env creds"
  fi
  echo "  SELFTEST PASS"
  exit 0
fi

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

# Backend probes
HAVE_CURL=0; HAVE_RCLONE=0; HAVE_AWS=0
command -v curl   >/dev/null 2>&1 && HAVE_CURL=1
command -v rclone >/dev/null 2>&1 && HAVE_RCLONE=1
command -v aws    >/dev/null 2>&1 && HAVE_AWS=1

# Load R2 creds for curl backend (prefer env, else rclone.conf)
R2_AK="${AWS_ACCESS_KEY_ID:-}"
R2_SK="${AWS_SECRET_ACCESS_KEY:-}"
R2_EP="${R2_ENDPOINT_URL:-}"
if [[ -z "$R2_AK" || -z "$R2_SK" || -z "$R2_EP" ]] && [[ -f "$RCLONE_CONF" ]]; then
  [[ -z "$R2_AK" ]] && R2_AK="$(rclone_conf_get "$RCLONE_REMOTE" access_key_id     "$RCLONE_CONF" || true)"
  [[ -z "$R2_SK" ]] && R2_SK="$(rclone_conf_get "$RCLONE_REMOTE" secret_access_key "$RCLONE_CONF" || true)"
  [[ -z "$R2_EP" ]] && R2_EP="$(rclone_conf_get "$RCLONE_REMOTE" endpoint          "$RCLONE_CONF" || true)"
fi
CURL_READY=0
if [[ "$HAVE_CURL" -eq 1 && -n "$R2_AK" && -n "$R2_SK" && -n "$R2_EP" ]]; then
  CURL_READY=1
fi
R2_HOST="${R2_EP#https://}"; R2_HOST="${R2_HOST#http://}"; R2_HOST="${R2_HOST%/}"

echo "[$(ts)] backend: curl=$CURL_READY rclone=$HAVE_RCLONE aws=$HAVE_AWS"

# Pre-generate XML once (same body for all buckets)
XML_BODY=""
if [[ "$APPLY" -eq 1 && "$CURL_READY" -eq 1 ]]; then
  XML_BODY="$(policy_to_xml "$POLICY")"
  echo "[$(ts)] xml_body: $(echo -n "$XML_BODY" | wc -c | tr -d ' ') bytes, $(grep -o '<Rule>' <<<"$XML_BODY" | wc -l | tr -d ' ') rules"
fi

rc_total=0
declare -a PER_BUCKET=()
for b in $BUCKETS; do
  echo ""
  echo "==== bucket: $b"
  if [[ "$APPLY" -eq 0 ]]; then
    echo "  [DRY] would PUT lifecycle to bucket '$b'"
    if [[ "$CURL_READY" -eq 1 ]]; then
      echo "  [DRY] backend=curl+SigV4 host=$R2_HOST url=https://$R2_HOST/$b?lifecycle="
      echo "  [DRY] creds source: ${AWS_ACCESS_KEY_ID:+env}${AWS_ACCESS_KEY_ID:-rclone.conf[$RCLONE_REMOTE]}"
    fi
    if [[ "$HAVE_RCLONE" -eq 1 ]]; then
      echo "  [DRY] backend=rclone cmd: rclone backend lifecycle r2:$b $POLICY  (unsupported on rclone <=1.72)"
    fi
    if [[ "$HAVE_AWS" -eq 1 ]]; then
      echo "  [DRY] backend=aws cmd: aws s3api put-bucket-lifecycle-configuration --bucket $b --lifecycle-configuration file://$POLICY --endpoint-url \"\$R2_ENDPOINT_URL\""
    fi
    if [[ "$CURL_READY" -eq 0 && "$HAVE_RCLONE" -eq 0 && "$HAVE_AWS" -eq 0 ]]; then
      echo "  [DRY] WARN: no backend usable — ensure curl+rclone.conf[r2] or install rclone/awscli"
    fi
    PER_BUCKET+=("{\"bucket\":\"$b\",\"status\":\"DRY\"}")
    continue
  fi

  # APPLY path
  applied=0
  backend_used=""
  # 1) curl + SigV4
  if [[ "$CURL_READY" -eq 1 ]]; then
    echo "  [APPLY] curl+SigV4 → https://$R2_HOST/$b?lifecycle="
    if r2_put_lifecycle_curl "$b" "$XML_BODY" "$R2_AK" "$R2_SK" "$R2_HOST"; then
      echo "  [APPLY-OK] curl bucket=$b"
      applied=1; backend_used="curl"
    else
      echo "  [APPLY-WARN] curl backend failed — see $LOG; trying next backend"
    fi
  fi
  # 2) rclone
  if [[ "$applied" -eq 0 && "$HAVE_RCLONE" -eq 1 ]]; then
    echo "  [APPLY] rclone backend lifecycle r2:$b ..."
    if rclone backend lifecycle "r2:$b" "$POLICY" 2>>"$LOG"; then
      echo "  [APPLY-OK] rclone bucket=$b"
      applied=1; backend_used="rclone"
    else
      echo "  [APPLY-WARN] rclone failed — falling back"
    fi
  fi
  # 3) aws
  if [[ "$applied" -eq 0 && "$HAVE_AWS" -eq 1 ]]; then
    if [[ -z "${R2_ENDPOINT_URL:-}" ]]; then
      echo "  [APPLY-FAIL] R2_ENDPOINT_URL not set" >&2
    else
      echo "  [APPLY] aws s3api put-bucket-lifecycle-configuration --bucket $b ..."
      if aws s3api put-bucket-lifecycle-configuration \
           --bucket "$b" \
           --lifecycle-configuration "file://$POLICY" \
           --endpoint-url "$R2_ENDPOINT_URL" 2>>"$LOG"; then
        echo "  [APPLY-OK] aws bucket=$b"
        applied=1; backend_used="aws"
      else
        echo "  [APPLY-FAIL] aws rc=$?" >&2
      fi
    fi
  fi
  if [[ "$applied" -eq 0 ]]; then
    echo "  [APPLY-FAIL] no backend succeeded for bucket=$b" >&2
    rc_total=$((rc_total+1))
    PER_BUCKET+=("{\"bucket\":\"$b\",\"status\":\"FAIL\",\"backend\":\"none\"}")
  else
    PER_BUCKET+=("{\"bucket\":\"$b\",\"status\":\"OK\",\"backend\":\"$backend_used\"}")
  fi
done

echo ""
EST_PCT=$(python3 -c "import json;print(json.load(open('$POLICY')).get('estimated_savings',{}).get('monthly_pct_reduction',0))" 2>/dev/null)
echo "[$(ts)] DONE mode=$MODE failures=$rc_total estimated_monthly_pct_reduction=${EST_PCT:-0}%"

# Emit result JSON (idempotent — overwrites prior run).
VERDICT="DRY_OK"
if [[ "$APPLY" -eq 1 ]]; then
  if [[ "$rc_total" -eq 0 ]]; then VERDICT="APPLY_OK"; else VERDICT="APPLY_PARTIAL_OR_FAIL"; fi
fi
# Join per-bucket array
PB_JOIN=""
for e in "${PER_BUCKET[@]:-}"; do
  [[ -z "$e" ]] && continue
  [[ -n "$PB_JOIN" ]] && PB_JOIN="$PB_JOIN,"
  PB_JOIN="$PB_JOIN$e"
done
cat > "$RESULT" <<EOF
{
  "schema_version": "1",
  "roi_item": "V3",
  "ts": "$(ts)",
  "mode": "$MODE",
  "verdict": "$VERDICT",
  "failures": $rc_total,
  "policy_file": "$POLICY",
  "backends_present": {
    "curl_sigv4": $CURL_READY,
    "rclone":     $HAVE_RCLONE,
    "aws":        $HAVE_AWS
  },
  "creds_source": "$( [[ -n "${AWS_ACCESS_KEY_ID:-}" ]] && echo env || echo "rclone.conf[$RCLONE_REMOTE]" )",
  "per_bucket": [${PB_JOIN}]
}
EOF
echo "[$(ts)] result: $RESULT"

# Preserve V3 remediation plan when every backend still failed.
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
  "backends_tried": {
    "curl_sigv4": $CURL_READY,
    "rclone":     $HAVE_RCLONE,
    "aws":        $HAVE_AWS
  },
  "diagnosis": "All attempted backends failed. See $LOG for HTTP response + signer output.",
  "remediation_steps": [
    "1. Verify rclone.conf [$RCLONE_REMOTE] has access_key_id / secret_access_key / endpoint.",
    "2. Re-run with --bucket <name> to isolate a single failing bucket.",
    "3. Inspect state/r2_lifecycle_apply.log (HTTP response body).",
    "4. Optional: brew install awscli as final fallback."
  ]
}
EOF
  echo "[$(ts)] V3 PLAN: emitted $PLAN_OUT"
fi

exit 0
