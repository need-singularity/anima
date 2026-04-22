#!/usr/bin/env bash
# archive_v2_sync_inventory.bash — reconcile asset_inventory.json against archive log
#
# The driver logs progress to state/asset_archive_log.jsonl but does NOT mutate
# state/asset_inventory.json (log is SSOT, inventory is planning input). This
# script updates inventory.status to "archived" for any asset whose path has
# a terminal event (status=deleted or status=archived_no_delete) in the log.
#
# Usage:
#   bash tool/archive_v2_sync_inventory.bash            # write-apply
#   bash tool/archive_v2_sync_inventory.bash --dry      # show what would change

set -euo pipefail
cd "$(dirname "$0")/.."

DRY=0
for a in "$@"; do [[ "$a" == "--dry" ]] && DRY=1; done

INVENTORY="state/asset_inventory.json"
LOG="state/asset_archive_log.jsonl"

terminal_paths=$(jq -sr 'map(select(.status=="deleted" or .status=="archived_no_delete") | .path) | unique | .[]' "$LOG")

if [[ -z "$terminal_paths" ]]; then
    echo "[sync] no terminal events in log"
    exit 0
fi

echo "[sync] $(echo "$terminal_paths" | wc -l | tr -d ' ') paths with terminal events"

tmp=$(mktemp -t archive_v2_inv.XXXX)
trap 'rm -f "$tmp"' EXIT

# Pass terminal paths as a JSON array to jq
jq \
    --argjson targets "$(echo "$terminal_paths" | jq -Rcs 'split("\n") | map(select(length>0))')" \
    '
    . as $inv
    | .groups |= map(
        .assets |= map(
            if (.path as $p | $targets | index($p)) then
                . + {status: "archived", archived_at: (now | strftime("%Y-%m-%dT%H:%M:%SZ"))}
            else
                .
            end
        )
    )
    | .last_synced_at = (now | strftime("%Y-%m-%dT%H:%M:%SZ"))
    ' "$INVENTORY" > "$tmp"

# Count changes
before=$(jq '[.groups[].assets[] | select(.status=="pending")] | length' "$INVENTORY")
after=$(jq '[.groups[].assets[] | select(.status=="pending")] | length' "$tmp")
delta=$((before - after))

echo "[sync] pending: $before -> $after (delta=-$delta archived)"

if [[ $DRY -eq 1 ]]; then
    echo "[dry] inventory not written"
    echo "---diff sample (first 20 changed)---"
    diff <(jq '.groups[].assets[] | select(.status=="archived") | .path' "$tmp" | head -20) <(echo "(old)") 2>/dev/null | head -25 || true
    exit 0
fi

cp "$tmp" "$INVENTORY"
echo "[sync] wrote $INVENTORY"
