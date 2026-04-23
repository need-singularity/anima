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
#   sha256 = 42d015789305a97470bedac12f24a6abd9314db8382ce57ee5dd2cbab1265025
#   size   = 1771168 bytes (1.69 MiB), static musl ELF
#   upstream build: hexa-lang 388eece8 build/hexa_v2_linux
#     (Phase C.2 __hexa_strlit_init per-module namespacing fix landed,
#      plus M4 .pad_start/.pad_end codegen + hexa_cc regen safety)
#
# PREVIOUS
#   3ff995fc... 5.32 MiB from hexa-lang 1fdc0100 — pre-Phase-C.2, stale.
#   Deprecated 2026-04-23 when upstream roadmap 66 Phase C.2 landed (968900b8).
#
# RATIONALE
#   R2 bucket anima-models is private (no public r2.dev domain). Presigned
#   URLs let us hand the pod a time-limited fetch target without leaking
#   long-lived R2 credentials into the pod environment.
set -euo pipefail

readonly R2_PATH="r2:anima-models/bin/hexa_v2_linux_x86_64"
readonly EXPECTED_SHA="42d015789305a97470bedac12f24a6abd9314db8382ce57ee5dd2cbab1265025"

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
