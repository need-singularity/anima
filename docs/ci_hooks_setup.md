# CI Hooks Setup — ROI items C15 / C18 / D22

Generated: 2026-04-22
Source spec: `docs/h100_roi_improvements_20260422.md` (items #15, #18, #22)

This document describes how to manually invoke and (optionally) install three
CPU-only CI gates introduced as part of the ROI improvement pass:

| ROI | Tool | Purpose | Exit-non-zero on |
|-----|------|---------|------------------|
| C15 | `tool/ci_serve_alm_persona_smoke.hexa` | persona serve regression gate | selftest FAIL |
| C18 | `tool/h100_post_launch_ingest.hexa` + `tool/roadmap_83_auto_mark.hexa` | post-launch verdict ingest + roadmap #83 done proposal | propose-only (never aborts) |
| D22 | `tool/dest_alm_beta_ssot_ci.hexa` | β SSOT drift gate (re-uses ext-8 audit) | `accidental_count > 0` OR `verdict != CLEAN` OR `main_track_value != beta` |

All three tools are pure hexa, idempotent, and emit a JSON verdict
sidecar in `state/`. None of them mutate `.roadmap`, the SSOT files,
or any other repo SSOT — `chflags uchg` semantics are preserved.

---

## C15 — serve_alm_persona CPU CI smoke

### Manual invocation

```
hexa run tool/ci_serve_alm_persona_smoke.hexa            # run gate (exit 0/1)
hexa run tool/ci_serve_alm_persona_smoke.hexa --print    # run + dump JSON
hexa run tool/ci_serve_alm_persona_smoke.hexa --self-test
```

The gate shells out to `bash tool/serve_alm_persona.bash --selftest --dry`
and validates 3 conditions:

1. exit code 0
2. `state/serve_alm_persona_selftest.json` `.verdict == "PASS"`
3. `state/serve_alm_persona_selftest_verdict.txt` content == `"PASS"`

Verdict sidecar: `state/ci_serve_alm_persona_smoke.json`.

### Optional git pre-push hook

Create `.git/hooks/pre-push` with the snippet below and make it
executable. The hook is NOT installed automatically — you control
`.git/hooks/`.

```
#!/usr/bin/env bash
set -e
cd "$(git rev-parse --show-toplevel)"
hexa run tool/ci_serve_alm_persona_smoke.hexa
```

Then:

```
chmod +x .git/hooks/pre-push
```

To bypass once (e.g. for a docs-only commit you trust): `git push --no-verify`.

---

## C18 — post-launch ingest auto-mark roadmap #83

### Pipeline

1. `tool/h100_post_launch_ingest.hexa` reads the 5 H100×4 launch
   artifacts, computes `overall`, and emits
   `state/h100_launch_completion_verdict.json`. When
   `overall == VERIFIED` the verdict carries
   `roadmap_83_action: AUTO_MARK_DONE`; otherwise `WAIT`.
2. `tool/roadmap_83_auto_mark.hexa` reads that verdict and emits
   `state/roadmap_83_auto_mark_proposal.json` with the precise
   line pattern + replacement + uchg dance. **It never mutates
   `.roadmap`** — the user runs the dance manually.

### Manual invocation

```
hexa run tool/h100_post_launch_ingest.hexa            # ingest + emit verdict
hexa run tool/roadmap_83_auto_mark.hexa               # propose mark
hexa run tool/roadmap_83_auto_mark.hexa --print       # propose + dump JSON
hexa run tool/roadmap_83_auto_mark.hexa --self-test   # 6-scenario test
```

### Approval dance (user-driven, after VERIFIED)

```
chflags nouchg /Users/ghost/core/anima/.roadmap
# edit line matching '^roadmap 83 planned' → 'roadmap 83 done'
# append done_at + done_evidence pointer
chflags uchg   /Users/ghost/core/anima/.roadmap
hexa run tool/roadmap_83_auto_mark.hexa --print  # confirm consistent
```

### Optional cron / launchd (post-launch monitor)

Re-running the ingest tool every 5–15 min after H100 kickoff is safe
and idempotent. Example crontab line:

```
*/10 * * * * cd /Users/ghost/core/anima && /Users/ghost/core/hexa-lang/hexa run tool/h100_post_launch_ingest.hexa >> /tmp/h100_ingest.log 2>&1
```

Auto-mark consumer can chain afterwards via `&&` if desired.

---

## D22 — dest_alm_beta SSOT auto-CI gate

### Manual invocation

```
hexa run tool/dest_alm_beta_ssot_ci.hexa             # gate (exit 0/1/2)
hexa run tool/dest_alm_beta_ssot_ci.hexa --print     # gate + dump JSON
hexa run tool/dest_alm_beta_ssot_ci.hexa --self-test # 5-scenario test
```

The gate reads `state/dest_alm_beta_ssot_audit.json` (produced by
the ext-8 audit pass) and validates:

1. audit JSON present + parseable
2. `accidental_count == 0`
3. `main_track_value == "beta"`
4. `verdict == "CLEAN"`

Verdict sidecar: `state/dest_alm_beta_ssot_ci_verdict.json`.

### Optional git pre-commit hook

```
#!/usr/bin/env bash
set -e
cd "$(git rev-parse --show-toplevel)"
hexa run tool/dest_alm_beta_ssot_ci.hexa
```

Save as `.git/hooks/pre-commit` and `chmod +x` it. Bypass once with
`git commit --no-verify`.

### Combined pre-push hook (C15 + D22)

If you want both gates on `git push`:

```
#!/usr/bin/env bash
set -e
cd "$(git rev-parse --show-toplevel)"
hexa run tool/ci_serve_alm_persona_smoke.hexa
hexa run tool/dest_alm_beta_ssot_ci.hexa
```

Both gates are idempotent and finish in well under a second on the
local workstation (no GPU, no network).

---

## Hard constraints (all 3 gates)

- hexa-only; no `.py` in repo.
- Propose-only for the C18 roadmap mark (uchg dance enforced).
- Idempotent — re-running overwrites the verdict sidecar with the
  current state.
- No remote API calls; no implicit GPU work; CPU + filesystem only.
- Git hooks are NOT installed automatically — instructions above are
  copy-paste ready, you control `.git/hooks/`.

## Audit artifact

After install or first run see `state/ci_hooks_install_audit.json`
for a per-hook verdict + last-run timestamp summary.
