#!/usr/bin/env bash
# tool/serve_alm_persona.bash — DEPRECATION SHIM (was 333L runtime bridge)
# Native runtime is tool/serve_alm_persona.hexa (stage0 exec_capture/setenv/env,
# hexa-lang upstream 2026-04-22). This shim forwards args 1:1 to keep legacy
# `bash tool/serve_alm_persona.bash ...` invocations green. Remove once all
# callers cut over. See state/serve_alm_persona_dryrun.json (schema v3) +
# docs/upstream_notes/hexa_lang_20260422.md.
set -u
HEXA_BIN="${HEXA_BIN:-}"
if [ -z "$HEXA_BIN" ]; then
  if [ -x "$HOME/core/hexa-lang/hexa" ]; then HEXA_BIN="$HOME/core/hexa-lang/hexa"
  else HEXA_BIN="hexa"; fi
fi
HEXA_FILE="$(cd "$(dirname "$0")/.." && pwd)/tool/serve_alm_persona.hexa"
echo "[serve_alm_persona] DEPRECATED bash bridge — forwarding to native hexa ($HEXA_FILE)" >&2
exec "$HEXA_BIN" "$HEXA_FILE" "$@"
