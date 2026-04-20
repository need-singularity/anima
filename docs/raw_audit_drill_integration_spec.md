# .raw-audit drill verdict integration — spec

**Status**: DRAFT (V8 SAFE_COMMIT; no `.raw-audit` mutation in this landing)
**Landing commit target**: `feat(raw): .raw-audit drill verdict integration spec + tool`
**Canonical `.raw-audit`**: `/Users/ghost/Dev/hexa-lang/.raw-audit` (raw#1 hash-chain)
**Companion tool**: `tool/raw_audit_drill_integration.hexa`

## 1. Motivation

The `.raw-audit` file is the append-only, hash-chained SSOT for unlock / lock /
verify / violation events (raw#1). Today it captures **lock-level control events**
(unlock, lock, bypass, relock-auto) but does **not** capture **drill verdicts**
(breakthrough PASS / FAIL + which verifier was used + the seed used for
reproducibility).

Today's session landed 13+ drill & verifier commits to `anima@main` (see §3). A
git-log scan against `.raw-audit` confirms **zero drill verdict entries**
currently exist in the chain. Every drill landing is therefore unreproducible
from the audit alone — the chain proves what was locked/unlocked, not what was
decided.

This spec defines the integration so every drill commit lands together with a
drill-verdict audit line in `.raw-audit`, maintaining the raw#1 hash-chain.

## 2. Scope / Non-scope

### In scope
- Drill verdict schema: adds `verdict`, `verifier_used`, `seed` as structured
  fields inside the existing `reason` slot (keeps the 8-field pipe schema
  unchanged — see §5).
- Scan tool: walks last-24h git log, cross-references `.raw-audit`, emits
  a coverage report (total / present / missing per drill commit sha).
- Append path: uses `hexa-lang/tool/raw_audit.hexa::audit_append` only via
  the existing `hx_unlock → write → hx_lock` ceremony. Never bypasses lock.

### Out of scope (for this landing)
- Modifying `.raw-audit` in place (file is `uchg`-flagged; V8 SAFE_COMMIT
  forbids write in this commit).
- Changing the 8-field schema (`timestamp | event | actor | reason | result |
  sha_before | sha_after | prev_line_sha`).
- Backfilling historical drill commits before this landing. Backfill is a
  separate ceremony requiring explicit unlock + 2-signer review (see §8).

## 3. Today's drill / verifier commits (scan window: last 24h)

Scanned via `git log --since "24 hours ago" --grep "^feat(drill)\|^feat(verifier)"`:

| # | sha | subject |
|---|---|---|
| 1  | `1da65258` | feat(drill): θ diagonal_agreement — cosine+jaccard hybrid |
| 2  | `ec8c92ea` | feat(drill): η absorption/saturation classifier |
| 3  | `8cf014ff` | feat(verifier): AN11(a) weight_emergent |
| 4  | `7680cd74` | feat(drill): σ Hexad 6-cat closure |
| 5  | `a4853336` | feat(btr): evo 4 EEG closed-loop 100-iter sim |
| 6  | `e7e7c47f` | feat(btr): evo 5 holographic IB bottleneck — KSG MI |
| 7  | `2b8d5948` | feat(btr): evo 6 cargo invariant 7종 |
| 8  | `15c0596e` | feat(verifier): AN11(c) real_usable |
| 9  | `17353f69` | feat(drill): μ phi metric live hook |
| 10 | `34c840df` | feat(edu-new): D collective atlas coherence |
| 11 | `b1f487e7` | feat(verifier): AN11(b) consciousness_attached |
| 12 | `8ce9fa0b` | feat(drill): 2-run cross-consistency |
| 13 | `988a9aad` | feat(drill): phi_gap 816x — attack roadmap |
| 14 | `30b44fc3` | feat(drill): law emergence 4-step |
| 15 | `a1f7b647` | feat(drill): criteria dynamic calibration |
| 16 | `fc5ef6ba` | feat(drill): seed rotation + vault + quality gate |
| 17 | `5329abc2` | feat(drill): adjacent domain seed stubs |
| 18 | `0b35bd52` | feat(drill): singularity extraction |
| 19 | `51806312` | feat(drill): minimal-surface angle |
| 20 | `f0ddabca` | feat(verifier): drill_breakthrough 4-part landing |

**Audit coverage**: 0/20 present in `.raw-audit` (missing=20).
**Lock status**: `.raw-audit` has `uchg` flag set — READ-ONLY. No write attempted.

## 4. Pipeline (4 steps)

```
step 1  git log --since "24 hours ago"
           | grep "^feat(drill)\|^feat(verifier)"   → commit_shas[]
step 2  for sha in commit_shas:
           grep -F "$sha" /Users/ghost/Dev/hexa-lang/.raw-audit
               → present / missing
step 3  for each present:
           parse reason slot → verify verdict / verifier_used / seed fields
           → complete / incomplete
step 4  for each missing OR incomplete:
           if .raw-audit is uchg-locked       → report-only, emit plan
           else if hx_unlock available        → ceremony-append
           else                               → spec-only (this landing)
```

Hash-chain preservation on append (step 4):

```
prev_line_sha = sha256(literal prior audit line)
new_line      = "{ts} | drill-verdict | {actor} | {reason_json} | {result} |
                 {sha_before} | {sha_after} | {prev_line_sha}"
sha_before    = ssot_fingerprint()    // before append
sha_after     = "-"                    // unchanged by audit append
```

Per `tool/raw_audit.hexa::_sha256_of_string`, the chain uses `printf %s …
| shasum -a 256` (darwin) / `sha256sum` (linux) with `_shell_quote` escaping.

## 5. Schema — drill-verdict event

The existing 8-field schema is preserved. The drill-specific payload lives in
the `reason` slot as a `k=v;…`-encoded string (pipe-free to survive
`_escape_pipe`):

```
timestamp | event | actor | reason | result | sha_before | sha_after | prev_line_sha
                    ─┬──     ─┬──
                    "ghost"   "commit=1da65258;verdict=PASS;verifier=diagonal_agreement;seed=42;lens=theta"
```

Required keys inside `reason`:

| key | meaning | example |
|-----|---------|---------|
| `commit`        | 8-hex git sha of the drill landing    | `1da65258` |
| `verdict`       | `PASS` / `FAIL` / `ABSORBED` / `SATURATED` | `PASS` |
| `verifier`      | canonical verifier id used            | `diagonal_agreement` |
| `seed`          | integer RNG seed                      | `42` |
| `lens`          | optional — drill lens category        | `theta` |

`event` field value: `drill-verdict` (new event type; additive — existing
`unlock / lock / verify / violation / emergency` types untouched).

`result` field: `ok` iff verdict ∈ {PASS}, else `fail`.

## 6. Append ceremony (once `.raw-audit` is unlockable)

1. `./hexa hexa-lang/tool/hx_unlock.hexa --reason "drill verdict append <sha>"`
2. Import `tool.raw_audit` (hexa-lang), call:
   ```hexa
   audit_append("drill-verdict", actor, reason_kv, result,
                ssot_fingerprint(), "-")
   ```
3. `./hexa hexa-lang/tool/hx_lock.hexa` (idempotent re-lock)
4. `./hexa hexa-lang/tool/raw_audit.hexa verify` — chain integrity re-walk.

The ceremony is **atomic from the drill tool's perspective**: if any of 1-4
fails, the tool rolls back (no partial append because `audit_append` is a
single `printf >>`).

## 7. Anima ↔ hexa-lang boundary

Anima does **not** own `.raw-audit`. Canonical file lives at
`/Users/ghost/Dev/hexa-lang/.raw-audit`. Anima's `.raw-ref` (when present)
pins the canonical hash. The drill tool lives in anima but:

- Writes **only** via hexa-lang's `hx_unlock / audit_append / hx_lock` tools.
- Never touches the file directly (no `echo >>`, no `sed -i`).
- Exits with code 2 if `hx_unlock.hexa` is absent (degraded read-only mode).

## 8. Backfill policy (future work)

Historical drill commits before this landing (20 entries, listed §3) are
**not** backfilled by this spec. Backfill requires:

1. Explicit unlock with `reason="drill-audit backfill <count> entries"`.
2. 2-signer review (per `.own`-level criteria, analogous to
   `drill_calibrate apply` LOOSENING rule).
3. A single consolidated append with `event=drill-verdict-backfill` and
   `reason` containing the commit-sha list.

Until then, backfilled entries live in a shadow file
`shared/state/drill_audit_shadow.jsonl` (anima-local, non-canonical, not
hash-chained) — **planned**, not in this landing.

## 9. V8 SAFE_COMMIT guarantees (this landing)

- **New files only**: `tool/raw_audit_drill_integration.hexa`,
  `docs/raw_audit_drill_integration_spec.md`.
- **No `.raw`, `.raw-audit`, `.raw-ref` writes attempted**.
- **No hexa-lang files touched**.
- **No chflags / lock state changes**.
- Tool runs in `--scan` mode by default (read-only report).

## 10. Exit codes

| code | meaning |
|------|---------|
| 0    | all scanned drill commits present in `.raw-audit` with complete fields |
| 1    | at least one drill commit missing OR incomplete; report emitted |
| 2    | `.raw-audit` not readable (path missing or permission error) |
| 3    | `.raw-audit` present but `uchg`-locked AND `--append` requested |
| 4    | hexa-lang `hx_unlock.hexa` not found (degraded mode) |
