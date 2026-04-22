# Reproducible emit workflow (anima × hexa-lang PR #23)

Per `docs/upstream_notes/hexa_lang_20260422.md`, the hexa primitives
`now()`, `timestamp()`, `time_ms()`, `utc_iso_now()`, `utc_compact_now()`
honor two environment variables:

- `SOURCE_DATE_EPOCH=<unix_seconds>` — pin all timestamp primitives to that
  exact instant. Used for byte-reproducible re-emit (CI verify, manifest
  refresh without dirty git status).
- `HEXA_REPRODUCIBLE=1` — pin to epoch 0 (`1970-01-01T00:00:00Z`). Used
  when the actual timestamp value is irrelevant — only "is the file
  byte-stable on re-emit?" matters.

## Anima emitters wired to native primitives

Refactored from manual `exec("date -u …")` to `utc_iso_now()` / `now()`:

- `tool/h100_launch_manifest_spec.hexa`
- `tool/h100_post_launch_ingest.hexa`
- `tool/h100_auto_kill.hexa`
- `tool/l3_pre_launch_validate.hexa`

See `state/reproducible_emit_audit.json` for the full inventory.

## When to use which

| Scenario | Env var |
|---|---|
| CI: "did this manifest re-emit produce only timestamp diffs?" | `SOURCE_DATE_EPOCH=$(git log -1 --format=%ct -- <emit_path>)` |
| Local: "I just want a clean re-emit, don't care about timestamp" | `HEXA_REPRODUCIBLE=1` |
| Production emit (real wall clock) | _no env var_ |

## Per-file git mtime helper

```bash
sde() { git log -1 --format=%ct -- "$1"; }
SOURCE_DATE_EPOCH=$(sde state/h100_launch_manifest.json) \
  hexa tool/h100_launch_manifest_spec.hexa
```

## CI gate

`tool/reproducible_emit_check.hexa` runs the target tool twice with the
same `SOURCE_DATE_EPOCH` (auto-derived via `git log -1 --format=%ct`),
restores the prev-hash baseline between runs, then asserts byte
equality. Any drift exits 1 with a unified diff.

```bash
hexa tool/reproducible_emit_check.hexa \
  --tool tool/h100_launch_manifest_spec.hexa \
  --emit state/h100_launch_manifest.json
```

Defaults to the H100 launch manifest if no flags supplied.

## What this eliminates

Before: every `hexa run tool/h100_launch_manifest_spec.hexa` produced a
timestamp-only diff in `state/h100_launch_manifest.json`, requiring
`git checkout state/h100_launch_manifest.json` after each verify pass.

After: `SOURCE_DATE_EPOCH=$(git log -1 --format=%ct -- state/h100_launch_manifest.json) hexa run …`
returns the file to its on-disk hash if no semantic content changed.
No checkout dance. CI can detect actual semantic drift.

## Hard guarantee

When neither env var is set, behavior is unchanged — `utc_iso_now()`
returns wall-clock UTC exactly as before. Existing emitter outputs are
not affected by this refactor.
