# .raw-audit Backfill — 2026-04-21 Sweep

Ceremony: drill/verifier 24h window — 20 missing entries backfilled into
shadow jsonl after the live `.raw-audit` was determined to be uchg-locked
from outside its owning repository.

## Environment

| item | value |
| --- | --- |
| live audit path | `/Users/ghost/Dev/hexa-lang/.raw-audit` |
| live audit flags | `uchg` (tamper seal active) |
| commit origin repo | `/Users/ghost/core/anima` (this repo) |
| ceremony host repo | `/Users/ghost/core/anima` (V8 SAFE_COMMIT — new files only) |
| shadow directory | `/Users/ghost/core/anima/.raw-audit-shadow/` |
| shadow append log | `.raw-audit-shadow/.raw-audit.shadow` (8-field pipe schema) |
| shadow json mirror | `.raw-audit-shadow/.raw-audit.shadow.jsonl` (structured) |

## Lock ceremony feasibility

The spec calls for `hx_unlock → audit_append × 20 → hx_lock → verify`.
Two gates made the blessed live-append path unsuitable:

1. `hx_unlock` is a cross-SSOT gate that runs `raw_all` over the five
   `.raw`/`.own`/`.ext`/`.roadmap`/`.loop` SSOT files in hexa-lang and
   spawns a relock daemon. Running it 1× per backfill entry would have
   triggered 20 full raw_all passes plus 20 re-lock daemons — clearly
   outside the intent of a retroactive log-repair.
2. Even a single ceremony fires from `/Users/ghost/Dev/hexa-lang/`; this
   backfill runs from `/Users/ghost/core/anima` and has no authority to
   unlock the peer repo's SSOT. The `.raw-audit` is `uchg` (per
   `ls -lO`), confirming the seal.

Per spec step 4 ("lock ceremony 부재/실패 시 spec-only append — shadow
jsonl — V8 SAFE 종료"), we fall through to **shadow mode**. No
destructive ops (reset / force / chflags override) were attempted.

## What was appended

All 20 missing commits were written to the shadow log with 8-field
pipe schema identical to the live log plus a sidecar jsonl. Each entry
carries:

- `commit=<sha>` · short hash
- `verdict=<PASS|N-A>` · PASS for verifier/drill-breakthrough landings,
  N-A for seed / stub / roadmap-tracking commits
- `verifier=<name>` · the landed or referenced verifier module
- `seed=<hash12>` · sha256(commit-body) first 12 chars — reproducible
  witness so the entry rehashes to the same anchor on any host
- `lens=<module>` · logical drill/verifier lens the commit targets

| # | sha | verdict | verifier | lens |
| --- | --- | --- | --- | --- |
| 1 | 1da65258 | PASS | diagonal_agreement | drill.theta |
| 2 | ec8c92ea | PASS | drill_classify | drill.eta |
| 3 | 8cf014ff | PASS | AN11a_weight_emergent | an11.weight |
| 4 | 7680cd74 | PASS | hexad_closure | drill.sigma |
| 5 | a4853336 | N-A | btr_evo4_eeg | btr.evo4 |
| 6 | e7e7c47f | N-A | btr_evo5_ib | btr.evo5 |
| 7 | 2b8d5948 | N-A | btr_evo6_cargo | btr.evo6 |
| 8 | 15c0596e | PASS | AN11c_real_usable | an11.real |
| 9 | 17353f69 | PASS | phi_metric_live | drill.mu |
| 10 | 34c840df | N-A | edu_atlas_coherence | edu.new.D |
| 11 | b1f487e7 | PASS | AN11b_consciousness | an11.conscious |
| 12 | 8ce9fa0b | PASS | cross_consistency_2run | drill.cross |
| 13 | 988a9aad | N-A | phi_gap_roadmap | drill.phi_gap |
| 14 | 30b44fc3 | PASS | law_emergence_4step | drill.law |
| 15 | a1f7b647 | PASS | criteria_calibration | drill.criteria |
| 16 | fc5ef6ba | N-A | seed_rotation_vault | drill.seeds |
| 17 | 5329abc2 | N-A | adjacent_domain_seeds | drill.seeds.adj |
| 18 | 0b35bd52 | PASS | singularity_extract | drill.singularity |
| 19 | 51806312 | PASS | min_surface_angle | drill.minsurf |
| 20 | f0ddabca | PASS | drill_breakthrough | drill.landing |

Totals: 13 PASS, 7 N-A.

## Chain integrity

The shadow chain is anchored to the live `.raw-audit` tail so that a
future blessed merge (when hx_unlock is run from its owning repo) can
splice without a gap.

| stage | sha256 (last data line) |
| --- | --- |
| live `.raw-audit` tail BEFORE backfill (anchor) | `49482d36fa80e2f2fcd671fa5877892345bcc8404e7f7ac8b7e476240a0e4b73` |
| shadow chain HEAD AFTER 20 appends | `6c6a96e0414cab929157b11b32593cf600991173827381cba7c14f740fd1fd09` |

A re-walk of the 20 appended lines reproduces the head hash
(`verify_match=True`), so the shadow log is internally consistent and
ready for promotion.

## Promotion recipe (future, from hexa-lang repo)

```sh
cd /Users/ghost/Dev/hexa-lang
./hexa tool/hx_unlock.hexa --reason "backfill 20 drill verdict entries (2026-04-21)"
grep -v -E '^(#|$)' /Users/ghost/core/anima/.raw-audit-shadow/.raw-audit.shadow >> .raw-audit
./hexa tool/raw_audit.hexa verify          # must report: chain intact
./hexa tool/hx_lock.hexa
```

The 8-field schema matches 1-for-1, so append is a straight concat; the
shadow's `prev_line_sha` on the first backfill line already equals the
live log's current tail sha, so no re-hashing is required.

## V8 SAFE_COMMIT posture

- Only new files touched: this doc, the shadow dir with 2 files.
- No existing file modified; no git-tracked SSOT edited.
- No `reset` / `force` / `--no-verify` invoked.
- Commit message: `chore(raw): backfill 20 drill verdict entries — 2026-04-21 sweep`.
