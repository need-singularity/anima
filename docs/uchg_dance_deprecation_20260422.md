# Manual chflags uchg dance — deprecated 2026-04-22

Status: DEPRECATED. Migrate to `hexa tool/roadmap_with_unlock.hexa` (PR #25).

## Why

The legacy 3-step sequence

```
chflags nouchg <path>
<edit ...>
chflags uchg   <path>
```

leaks the file as **unlocked** if the edit step crashes, the host catches a
signal (SIGINT/SIGTERM from `kill`, IDE shutdown, agent context-switch),
or the process is killed mid-write. The relock step never runs.

PR #25 of `hexa-lang` ships `tool/roadmap_with_unlock.hexa`, which wraps
the dance under a bash `trap '<relock>' EXIT INT TERM`. Relock fires on
**every** exit path except SIGKILL (which nothing survives). On macOS the
helper uses `chflags`; on Linux it falls back to `chattr +i/-i` (with
`sudo -n` retry).

## Migration recipe

Replace:

```hexa
let was_locked = is_uchg(path)
if was_locked { exec("chflags nouchg " + path) }
write_file(path, new_body)
if was_locked { exec("chflags uchg " + path) }
```

With:

```hexa
// 1. stage the new content into a tempfile
let tmp = path + ".tmp.with_unlock." + ts
write_file(tmp, new_body)
// 2. atomic mv via the helper (relock on EXIT/INT/TERM via bash trap)
let cmd = "hexa /Users/ghost/core/hexa-lang/tool/roadmap_with_unlock.hexa" +
          " --file " + path + " -- mv " + tmp + " " + path
let r = exec_with_status(cmd)
```

For an in-place append (e.g. `printf %s\\n line >> path`):

```hexa
let inner = "printf %s\\\\n " + sh_quote(line) + " >> " + sh_quote(path)
let cmd = "hexa /Users/ghost/core/hexa-lang/tool/roadmap_with_unlock.hexa" +
          " --file " + sh_quote(path) +
          " -- bash -c " + sh_quote(inner)
exec_with_status(cmd)
```

Helper exit code mirrors the wrapped command, so existing exit-code
semantics in caller tools are preserved 1:1. The helper auto-detects
whether the file was actually locked beforehand and skips both unlock and
relock if not — making it idempotent for both scenarios.

## Manual fallback (helper absent)

If `tool/roadmap_with_unlock.hexa` is missing from the system (fresh
checkout, hexa-lang not installed, etc.), keep the legacy dance behind an
`exists()` guard, e.g.:

```hexa
if !exists(WITH_UNLOCK_TOOL) {
    if was_locked { chflags_set(path, "nouchg") }
    write_file(path, body)
    if was_locked { chflags_set(path, "uchg") }
} else {
    // helper path
}
```

All migrated anima tools embed this fallback so they remain functional
without the helper. The audit at `state/uchg_dance_migration_audit.json`
records per-tool migration state.

## Lint guard

`tool/uchg_safe_edit.hexa` rejects (exit 3) any file containing the
manual dance. Wire it into pre-commit / CI to prevent regression:

```
hexa tool/uchg_safe_edit.hexa --file tool/<your_tool>.hexa --allow-comments
```

## Files migrated 2026-04-22

Executable dance migrations:

- `tool/roadmap_auto_reflect.hexa` — `--apply` path → `with_unlock_apply()`
- `tool/phase_progression_controller.hexa` — `_raw_audit_append` wrap
- `tool/ps_9_l0_lock.hexa` — `l0_lock` → `_stage_via_helper`
- `tool/phase_flow_planner.hexa` — `_append_entries` (initial grep
  missed this; dance was hidden behind `_chflags()` indirection)

Proposal text rewritten:

- `tool/roadmap_83_auto_mark.hexa` — `dance` array → `recipe` that
  invokes `roadmap_with_unlock.hexa`

Files inspected and confirmed NOT to contain a dance (lock-only or
comment-only references retained):

- `tool/roadmap_mistake_auto_fix.hexa` — single `chflags uchg` re-apply
  (recovery-only; no preceding unlock)
- `tool/roadmap_live_daemon.hexa` — enforce-only
- `tool/roadmap_integrity_guard.hexa` — check-only
- `tool/closure_debt_scanner.hexa`, `tool/problem_solving_protocol.hexa`,
  `tool/ps_10_milestone.hexa`, `tool/ssot_cross_check.hexa` —
  comment / docstring references only
