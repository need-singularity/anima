#!/usr/bin/env bash
# tool/fetch_hexa_binary_url.bash — emit 7-day presigned R2 URL for the
# Linux x86_64 hexa_v2 binary used during H100 pod bootstrap.
#
# USAGE
#   bash tool/fetch_hexa_binary_url.bash [--expire 168h] [--export]
#
# OUTPUT
#   Default: prints the URL to stdout.
#   --export: also prints a shell-ready `export HEXA_URL=...` line (for
#             piping into ssh/scp, or `eval "$(bash ...)"` locally).
#
# SOURCE
#   r2:anima-models/bin/hexa_v2_linux_x86_64
#   sha256 = 3ff995fc8b68e3a5b9e46a803a269e03204ff0b439a668a6dfadc58acc01d496
#   size   = 5580408 bytes (5.32 MiB), static musl ELF
#   upstream build: hexa-lang 1fdc0100 build/hexa_v2_linux_x86_64
#
# RATIONALE
#   R2 bucket anima-models is private (no public r2.dev domain). Presigned
#   URLs let us hand the pod a time-limited fetch target without leaking
#   long-lived R2 credentials into the pod environment.
set -euo pipefail

readonly R2_PATH="r2:anima-models/bin/hexa_v2_linux_x86_64"
readonly EXPECTED_SHA="3ff995fc8b68e3a5b9e46a803a269e03204ff0b439a668a6dfadc58acc01d496"

expire="168h"
want_export=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --expire) expire="$2"; shift 2 ;;
    --export) want_export=1; shift ;;
    --help|-h)
      sed -n '1,20p' "$0"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

command -v rclone >/dev/null || { echo "ERROR: rclone not installed" >&2; exit 3; }

url=$(rclone link "$R2_PATH" --expire "$expire" 2>/dev/null)
[[ -n "$url" ]] || { echo "ERROR: rclone link returned empty — check r2: remote + anima-models bucket access" >&2; exit 4; }

if (( want_export )); then
  printf 'export HEXA_URL=%q\n' "$url"
  printf 'export HEXA_SHA256=%s\n' "$EXPECTED_SHA"
else
  echo "$url"
fi
