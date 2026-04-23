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

# MINIMAL SELFTEST (T1-T4 ROI): parse-clean + 1 invariant. Does NOT exec hexa.
if [[ "${1:-}" == "--selftest" ]]; then
  echo "── serve_alm_persona.bash (shim) selftest ──"
  bash -n "$0" || { echo "  parse FAIL"; exit 1; }
  if [[ ! -f "$HEXA_FILE" ]]; then echo "  invariant FAIL: target hexa missing ($HEXA_FILE)"; exit 1; fi
  echo "  parse: PASS"
  echo "  invariant: shim target $HEXA_FILE present"
  echo "  SELFTEST PASS"
  exit 0
fi

echo "[serve_alm_persona] DEPRECATED bash bridge — forwarding to native hexa ($HEXA_FILE)" >&2
exec "$HEXA_BIN" "$HEXA_FILE" "$@"
