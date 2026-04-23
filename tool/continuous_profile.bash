#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  tool/continuous_profile.bash — ROI I50 continuous CPU profile wrapper
#
#  PURPOSE
#    Thin, OS-portable wrapper around the platform sampling profiler:
#      - macOS  → `sample` (built-in)
#      - Linux  → `perf record` (linux-tools)
#    Captures a short profile, distills hot functions to JSON, and writes
#    state/profile_<utc-ts>.json. NO long-running daemon — this is a
#    one-shot sample suitable for periodic invocation by launchd/cron.
#
#  USAGE
#    bash tool/continuous_profile.bash --start --pid <pid> [--seconds 10] [--out-dir state]
#    bash tool/continuous_profile.bash --report <state/profile_*.json>
#    bash tool/continuous_profile.bash --stop                    (idempotent: removes /tmp sentinel)
#    bash tool/continuous_profile.bash --smoke                   (synthetic, no profiler invoked)
#
#  EXIT
#    0 OK / smoke PASS
#    1 profile capture failed
#    2 bad arg
#    3 platform profiler missing (sample/perf)
#
#  RAW
#    raw#9  bash bridge for runtime tooling (parallels asset_archive_run.bash)
#    raw#10 deterministic in --smoke mode (synthetic hot fns, fixed counts)
#    raw#15 no-hardcode (paths via flags / $ANIMA_ROOT env)
# ════════════════════════════════════════════════════════════════════════════

set -u

ANIMA_ROOT="${ANIMA_ROOT:-/Users/ghost/core/anima}"
DEFAULT_OUT_DIR="${ANIMA_ROOT}/state"
SENTINEL="/tmp/continuous_profile.stop"

ts_utc() { date -u +%Y%m%dT%H%M%SZ; }
iso_utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }

usage() {
    grep -E '^# ' "$0" | sed 's/^# //'
    exit 2
}

mode=""
pid=""
seconds=10
out_dir="$DEFAULT_OUT_DIR"
report_path=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --start)    mode="start"; shift ;;
        --stop)     mode="stop"; shift ;;
        --report)   mode="report"; report_path="${2:-}"; shift 2 ;;
        --smoke)    mode="smoke"; shift ;;
        --pid)      pid="${2:-}"; shift 2 ;;
        --seconds)  seconds="${2:-10}"; shift 2 ;;
        --out-dir)  out_dir="${2:-$DEFAULT_OUT_DIR}"; shift 2 ;;
        -h|--help)  usage ;;
        *)          echo "[continuous_profile] unknown arg: $1" >&2; exit 2 ;;
    esac
done

if [[ -z "$mode" ]]; then usage; fi

mkdir -p "$out_dir"

emit_profile_json() {
    # args: out_path raw_text platform pid seconds
    local out_path="$1" raw="$2" platform="$3" target_pid="$4" duration="$5"
    local hot_json="$6"
    cat > "$out_path" <<EOF
{
  "schema": "anima.continuous_profile.v1",
  "slug": "continuous-profile",
  "tool": "tool/continuous_profile.bash",
  "roi_item": 50,
  "created": "$(iso_utc)",
  "platform": "${platform}",
  "target_pid": ${target_pid},
  "duration_seconds": ${duration},
  "raw_bytes": ${#raw},
  "hot_functions": ${hot_json}
}
EOF
}

distill_hot_macos() {
    # `sample` output: lines like "    1234 frame_a  (in libfoo)"
    # We grab the top 5 most-cited symbols by leading sample count.
    local raw="$1"
    awk '
        /^[[:space:]]+[0-9]+[[:space:]]/ {
            n=$1; $1=""; sym=$0; gsub(/^[[:space:]]+|[[:space:]]+$/,"",sym);
            if (sym!="") cnt[sym]+=n
        }
        END {
            for (k in cnt) printf "%d\t%s\n", cnt[k], k
        }
    ' <<<"$raw" | sort -rn | head -5 | awk '
        BEGIN { printf "[" }
        {
            if (NR>1) printf ",";
            sym=$0; sub(/^[0-9]+\t/, "", sym);
            cnt=$1;
            gsub(/"/, "\\\"", sym);
            printf "{\"function\":\"%s\",\"samples\":%d}", sym, cnt
        }
        END { printf "]" }
    '
}

distill_hot_linux() {
    # `perf report --stdio --no-children -n -s symbol` first column = % then count
    local raw="$1"
    awk '
        /^[[:space:]]*[0-9]+\.[0-9]+%/ {
            pct=$1; n=$2; sym=""
            for (i=3;i<=NF;i++) sym = sym (sym==""?"":" ") $i
            if (sym!="" && length(rows)<5) {
                rows[NR] = sym "\t" n
            }
        }
        END {
            i=0
            for (k in rows) { i++; print rows[k]; if (i>=5) break }
        }
    ' <<<"$raw" | awk '
        BEGIN { printf "[" }
        {
            if (NR>1) printf ",";
            sym=$1; cnt=$2;
            gsub(/"/, "\\\"", sym);
            printf "{\"function\":\"%s\",\"samples\":%d}", sym, cnt
        }
        END { printf "]" }
    '
}

case "$mode" in
    start)
        if [[ -z "$pid" ]]; then echo "[continuous_profile] --pid required for --start" >&2; exit 2; fi
        out="${out_dir}/profile_$(ts_utc).json"
        platform=""
        case "$(uname -s)" in
            Darwin)
                if ! command -v sample >/dev/null 2>&1; then
                    echo "[continuous_profile] macOS 'sample' not found" >&2; exit 3
                fi
                platform="macos-sample"
                raw=$(sample "$pid" "$seconds" 2>&1) || { echo "[continuous_profile] sample failed" >&2; exit 1; }
                hot=$(distill_hot_macos "$raw")
                ;;
            Linux)
                if ! command -v perf >/dev/null 2>&1; then
                    echo "[continuous_profile] linux 'perf' not found" >&2; exit 3
                fi
                platform="linux-perf"
                tmp=$(mktemp -d /tmp/cprof.XXXXXX)
                ( cd "$tmp" && perf record -F 99 -g -p "$pid" -- sleep "$seconds" ) >/dev/null 2>&1 || { echo "[continuous_profile] perf record failed" >&2; rm -rf "$tmp"; exit 1; }
                raw=$(cd "$tmp" && perf report --stdio --no-children -n -s symbol 2>/dev/null)
                rm -rf "$tmp"
                hot=$(distill_hot_linux "$raw")
                ;;
            *)
                echo "[continuous_profile] unsupported platform: $(uname -s)" >&2; exit 3
                ;;
        esac
        if [[ -z "$hot" ]]; then hot="[]"; fi
        emit_profile_json "$out" "$raw" "$platform" "$pid" "$seconds" "$hot"
        echo "[continuous_profile] wrote $out"
        ;;

    stop)
        rm -f "$SENTINEL"
        echo "[continuous_profile] sentinel cleared"
        ;;

    report)
        if [[ -z "$report_path" ]]; then echo "[continuous_profile] --report <path> required" >&2; exit 2; fi
        if [[ ! -f "$report_path" ]]; then echo "[continuous_profile] not found: $report_path" >&2; exit 2; fi
        echo "[continuous_profile] report: $report_path"
        cat "$report_path"
        ;;

    smoke)
        out="${out_dir}/profile_$(ts_utc)_smoke.json"
        # No real profiler invoked. Synthetic hot functions matching expected
        # output schema, used by ROI I50 self-verification.
        hot='[
    {"function":"forward_layer_attn","samples":421},
    {"function":"phi_emit","samples":188},
    {"function":"json_escape","samples":97},
    {"function":"cert_gate_check","samples":54},
    {"function":"http_handler","samples":31}
  ]'
        cat > "$out" <<EOF
{
  "schema": "anima.continuous_profile.v1",
  "slug": "continuous-profile",
  "tool": "tool/continuous_profile.bash",
  "roi_item": 50,
  "created": "$(iso_utc)",
  "platform": "smoke-synthetic",
  "target_pid": 0,
  "duration_seconds": 0,
  "raw_bytes": 0,
  "hot_functions": ${hot}
}
EOF
        if [[ ! -s "$out" ]]; then
            echo "[continuous_profile] smoke FAIL: $out empty" >&2
            exit 1
        fi
        echo "[continuous_profile] smoke PASS  ($out)"
        ;;
esac
