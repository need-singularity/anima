#!/usr/bin/env bash
# tool/h100_pods_sync.bash — refresh config/h100_pods.json from live runpodctl.
#
# PURPOSE
#   h100_auto_kill.hexa reads config/h100_pods.json as its pod registry. The
#   committed stub entry (pod_id=stub-pod-001) was never updated after real
#   pod launches, so the auto-kill guard silently watched a non-existent pod
#   while real pods burned unmonitored (captured in I_post_session_caveat).
#
#   This script queries runpodctl + the RunPod GraphQL API to rebuild the
#   registry with currently-running pods and their actual SSH coordinates.
#
# USAGE
#   bash tool/h100_pods_sync.bash [--out <path>] [--dry]
#     --out <path>  write target (default: config/h100_pods.json)
#     --dry         print JSON to stdout, do not write
#
# OUTPUT SHAPE (matches config/h100_pods.json schema consumed by h100_auto_kill)
#   {
#     "_comment": "...",
#     "pods": [
#       { "pod_id": "…", "provider": "runpod", "ssh_host": "…",
#         "ssh_port": <public tcp port>, "ssh_user": "root",
#         "last_activity_source": "nvidia_smi",
#         "notes": "auto-synced from runpodctl @ <iso>" }
#     ],
#     "updated_at": "<iso>",
#     "source": "tool/h100_pods_sync.bash"
#   }
#
# SAFETY
#   - Read-only on RunPod side (pod list + per-pod runtime query).
#   - Overwrites config/h100_pods.json atomically via temp file + mv.
#   - Emits empty pods[] if no pods are running (correctly deauthorises stale
#     entries rather than leaving stubs).
set -euo pipefail

OUT=/Users/ghost/core/anima/config/h100_pods.json
DRY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --dry) DRY=1; shift ;;
    --help|-h) sed -n '1,30p' "$0"; exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

command -v runpodctl >/dev/null || { echo "ERROR: runpodctl not installed" >&2; exit 3; }
command -v jq        >/dev/null || { echo "ERROR: jq not installed"        >&2; exit 3; }

readonly API_KEY=$(grep "^apikey" /Users/ghost/.runpod/config.toml | sed "s/apikey = '//;s/'//")
[[ -n "$API_KEY" ]] || { echo "ERROR: runpod apikey missing from ~/.runpod/config.toml" >&2; exit 4; }

readonly TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Collect live pod ids. runpodctl 1.x emits JSON array on stdout (even when empty).
ids=$(runpodctl pod list 2>/dev/null | jq -r '.[].id // empty')

pods_json='[]'
if [[ -n "$ids" ]]; then
  rows=()
  while IFS= read -r pid; do
    [[ -z "$pid" ]] && continue
    # Query runtime for public TCP port + ip
    payload=$(curl -s -X POST "https://api.runpod.io/graphql" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $API_KEY" \
      -d "{\"query\":\"query { pod(input:{podId:\\\"$pid\\\"}){ id name runtime { ports { ip isIpPublic privatePort publicPort type } } } }\"}")
    # Pick first public tcp port mapped to private 22
    host=$(echo "$payload" | jq -r '.data.pod.runtime.ports[]? | select(.type=="tcp" and .isIpPublic==true and .privatePort==22) | .ip' | head -1)
    port=$(echo "$payload" | jq -r '.data.pod.runtime.ports[]? | select(.type=="tcp" and .isIpPublic==true and .privatePort==22) | .publicPort' | head -1)
    [[ -z "$host" ]] && host=""
    [[ -z "$port" ]] && port=22
    rows+=("$(jq -n --arg id "$pid" --arg host "$host" --argjson port "$port" --arg ts "$TS" '{
      pod_id: $id, provider: "runpod", ssh_host: $host, ssh_port: $port,
      ssh_user: "root", last_activity_source: "nvidia_smi",
      notes: "auto-synced from runpodctl @ \($ts)"
    }')")
  done <<< "$ids"
  if (( ${#rows[@]} > 0 )); then
    pods_json=$(printf '%s\n' "${rows[@]}" | jq -s '.')
  fi
fi

out_json=$(jq -n --argjson pods "$pods_json" --arg ts "$TS" '{
  "_comment": "H100 pod registry — auto-synced from runpodctl + RunPod GraphQL. Run bash tool/h100_pods_sync.bash to refresh. Empty pods[] means no live pods; h100_auto_kill will emit zero-pod verdict accordingly.",
  pods: $pods, updated_at: $ts, source: "tool/h100_pods_sync.bash"
}')

if (( DRY )); then
  echo "$out_json"
else
  tmp=$(mktemp)
  printf '%s\n' "$out_json" > "$tmp"
  mv "$tmp" "$OUT"
  count=$(echo "$out_json" | jq '.pods | length')
  echo "synced $count pod(s) → $OUT ($TS)"
fi
