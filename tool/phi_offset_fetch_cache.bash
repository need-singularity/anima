#!/usr/bin/env bash
# tool/phi_offset_fetch_cache.bash — sister helper for phi_offset_auto_detect.hexa
#
# PURPOSE (ROI item C17, runtime companion)
#   The active hexa stage0 runtime blocks `exec`/`exec_with_status` and exposes
#   only a minimal string method surface, so the hexa side cannot run curl
#   directly. This helper does the actual HF config.json fetch and writes the
#   per-tag cache files that the hexa tool reads.
#
# WHAT IT DOES
#   For each of the 4 anima substrates (qwen3_8b / llama_3_1_8b /
#   ministral_3_14b / gemma_4_31b):
#     1. GET https://huggingface.co/<model_id>/raw/main/config.json
#        - sends Authorization: Bearer $HF_TOKEN if set
#        - --max-time 10
#     2. parses out hidden_size (top-level OR text_config.hidden_size for
#        multimodal wrappers Gemma-4 / Ministral-3) using jq if available
#        else python3 json fallback
#     3. writes:
#          state/cache/phi_offset_hf_config/<tag>.hidden_size  (single int)
#          state/cache/phi_offset_hf_config/<tag>.http_code    (e.g. "200")
#     4. touches sentinels:
#          state/cache/phi_offset_hf_config/.populated
#          state/cache/phi_offset_hf_config/.hf_token_present  (only if set)
#
# GRACEFUL DEGRADATION
#   - HF_TOKEN missing       → unauthenticated GET. Public repos succeed,
#                              gated repos return 401/403 (recorded; tool
#                              continues to next path).
#   - curl missing           → script exits 0 with warning (cache stays empty).
#   - DNS / network unreach  → http_code="000", hidden_size empty.
#   - jq + python3 missing   → records http_code only, no hidden_size.
#   Always exits 0 — degradation is reported via cache contents.
#
# WHAT IT DOES NOT DO
#   - NEVER downloads model weights (only the small config.json file).
#   - NEVER triggers training, H100 launch, or roadmap mutation.
#
# USAGE
#   bash tool/phi_offset_fetch_cache.bash
#   HF_TOKEN=hf_xxx bash tool/phi_offset_fetch_cache.bash    # for gated repos

set -u

CACHE_DIR="state/cache/phi_offset_hf_config"
TIMEOUT=10

mkdir -p "$CACHE_DIR"

# 4-path table (mirrors config/phi_4path_substrates.json)
TAGS=(
  "qwen3_8b"
  "llama_3_1_8b"
  "ministral_3_14b"
  "gemma_4_31b"
)
MODELS=(
  "Qwen/Qwen3-8B"
  "meta-llama/Llama-3.1-8B"
  "mistralai/Ministral-3-14B-Base-2512"
  "google/gemma-4-31B"
)

if ! command -v curl >/dev/null 2>&1; then
  echo "[phi_offset_fetch_cache] WARN: curl not found — cache will not be populated"
  exit 0
fi

HAS_JQ=0
HAS_PY=0
command -v jq      >/dev/null 2>&1 && HAS_JQ=1
command -v python3 >/dev/null 2>&1 && HAS_PY=1

if [ "$HAS_JQ" -eq 0 ] && [ "$HAS_PY" -eq 0 ]; then
  echo "[phi_offset_fetch_cache] WARN: neither jq nor python3 found — http_code will be recorded but hidden_size cannot be parsed"
fi

if [ -n "${HF_TOKEN:-}" ]; then
  : > "$CACHE_DIR/.hf_token_present"
  AUTH_HDR=(-H "Authorization: Bearer ${HF_TOKEN}")
  echo "[phi_offset_fetch_cache] HF_TOKEN present (Bearer auth enabled)"
else
  rm -f "$CACHE_DIR/.hf_token_present"
  AUTH_HDR=()
  echo "[phi_offset_fetch_cache] NOTE: HF_TOKEN unset — gated repos will return 401/403"
fi

extract_hidden_size() {
  local body_path="$1"
  if [ "$HAS_JQ" -eq 1 ]; then
    # try top-level hidden_size, then text_config.hidden_size
    local h
    h=$(jq -r '.hidden_size // .text_config.hidden_size // empty' < "$body_path" 2>/dev/null)
    if [ -n "$h" ] && [ "$h" != "null" ]; then
      echo "$h"
      return 0
    fi
  fi
  if [ "$HAS_PY" -eq 1 ]; then
    python3 - "$body_path" <<'PYEOF' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    h = d.get("hidden_size")
    if h is None:
        h = d.get("text_config", {}).get("hidden_size")
    if h is not None:
        print(int(h))
except Exception:
    pass
PYEOF
    return 0
  fi
  echo ""
}

n=${#TAGS[@]}
for ((i=0; i<n; i++)); do
  tag="${TAGS[$i]}"
  model="${MODELS[$i]}"
  url="https://huggingface.co/${model}/raw/main/config.json"
  body_path="$CACHE_DIR/${tag}.config.json"
  hidden_path="$CACHE_DIR/${tag}.hidden_size"
  code_path="$CACHE_DIR/${tag}.http_code"

  echo "[phi_offset_fetch_cache] fetch #$((i+1)): $tag ($model)"
  rm -f "$body_path" "$hidden_path" "$code_path"

  if [ ${#AUTH_HDR[@]} -gt 0 ]; then
    code=$(curl -s "${AUTH_HDR[@]}" -o "$body_path" -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || true)
  else
    code=$(curl -s -o "$body_path" -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || true)
  fi

  if [ -z "$code" ]; then code="000"; fi
  printf "%s" "$code" > "$code_path"

  if [ "$code" = "200" ]; then
    h=$(extract_hidden_size "$body_path")
    if [ -n "$h" ]; then
      printf "%s\n" "$h" > "$hidden_path"
      echo "    http=$code hidden_size=$h"
    else
      echo "    http=$code hidden_size=PARSE_FAIL (jq/python3 missing or schema unexpected)"
    fi
  else
    echo "    http=$code (no body parse)"
  fi
done

date -u +%FT%TZ > "$CACHE_DIR/.populated"
echo "[phi_offset_fetch_cache] done — cache at $CACHE_DIR"
echo "[phi_offset_fetch_cache] next: hexa tool/phi_offset_auto_detect.hexa"
exit 0
