# Proposal Stack — TOP 10 Review Batch Report (2026-04-22)

**Run ts**: 2026-04-22T14:10:07Z
**Source**: `docs/proposal_top10_review_20260422.md`
**Batch result JSON**: `state/proposal_top10_batch_result.json`
**Constraints**: raw#20 (propose-md only, NO code gen) · idempotent · hexa-only

---

## Heuristic applied

| rule | condition | action |
|---|---|---|
| approve | `loss_free==true AND risk_level<=low AND score_priority>=40` | pending → approved + emit propose-md |
| reject (med+) | `risk_level>=med` | pending → rejected (none matched in top-10) |
| reject (low score) | `score_priority<20` | pending → rejected (none matched in top-10) |
| defer | title contains `TODO`/`explore` | keep in pending (none matched) |
| **dedup override** | doc-specified `dedup → <id>` | reject with dedup reason (overrides heuristic approve) |

Note: v2_roi_selftest trio (038-040) scored 39 (<40 threshold) but carried
doc-verdict "approve as cluster super" (pre-H100 selftest fail triage is
critical). Doc-verdict override applied → approved.

## Decision table

| rank | id | file_slug | kind | score | risk | verdict | action |
|---:|---|---|---|---:|---:|---|---|
| 1 | 20260422-001 | sample | tool | 95 | low | **approve** | pending → approved (+ propose-md) |
| 2 | 20260422-017 | cert-mk8-7axis-skeleton | fix | 42 | 0.10 | **approve** | pending → approved (+ propose-md) |
| 3 | 20260422-016 | cert-cell-mk8-stationary | fix | 42 | 0.10 | **approve** | pending → approved (+ propose-md) |
| 4 | 20260422-013 | cert-mk8-7axis-skeleton (dup) | fix | 42 | 0.10 | **reject (dedup)** | pending → rejected (veto=1) → 017 |
| 5 | 20260422-012 | cert-cell-mk8-stationary (dup) | fix | 42 | 0.10 | **reject (dedup)** | pending → rejected (veto=1) → 016 |
| 6 | 20260422-002 | secret-scan pr_preview_env_spec.json | fix | 41 | 0.05 | **approve (urgent)** | pending → approved (+ propose-md) |
| 7 | 20260422-001 | secret-scan phi_offset_auto_detect.hexa (dup) | fix | 41 | 0.05 | **reject (dedup)** | pending → rejected (veto=1) → 002 |
| 8 | 20260422-040 | v2roi-fail roadmap_diff_viz | fix | 39 | 0.15 | **approve (cluster)** | pending → approved (+ propose-md) |
| 9 | 20260422-039 | v2roi-fail cert_graph_gen | fix | 39 | 0.15 | **approve (cluster)** | pending → approved (+ propose-md) |
| 10 | 20260422-038 | v2roi-fail auto_tool_index | fix | 39 | 0.15 | **approve (cluster)** | pending → approved (+ propose-md) |

## Aggregate counts

| bucket | count | ids |
|---|---:|---|
| approved | **7** | 001 (sample), 017, 016, 002 (secret), 040, 039, 038 |
| rejected | **3** | 013 (dedup→017), 012 (dedup→016), 001 (secret-dup→002) |
| deferred | 0 | — |
| skipped (already processed) | 0 | — |
| propose-md emitted | **7** | one per approved id |

## Artifacts emitted (raw#20: spec only, no code)

- `docs/proposed_implementation_20260422-001.md` (sample/seed spec)
- `docs/proposed_implementation_20260422-017.md` (cert skeleton)
- `docs/proposed_implementation_20260422-016.md` (cert cell)
- `docs/proposed_implementation_20260422-002.md` (secret scan triage)
- `docs/proposed_implementation_20260422-040.md` (v2roi fix)
- `docs/proposed_implementation_20260422-039.md` (v2roi fix)
- `docs/proposed_implementation_20260422-038.md` (v2roi fix)

## Follow-ups (user-initiated)

1. **Archive sample-001 seed**: `hexa tool/proposal_archive.hexa --id 20260422-001 --module-path tool/proposal_inventory_init.hexa`
   — blocked by current `proposal_inventory_init --selftest` FAIL (unknown inventory schema `anima.proposal_inventory.v1`); fix selftest first.
2. **Consolidate v2roi trio**: `hexa tool/proposal_cluster_consolidate.hexa --apply` → super-v2roi-selftest-fix.
3. **Spawn sub-agents** per propose-md specs (017, 016, 002, 038, 039, 040) — user explicit, one at a time.

## Post-batch state

| dir | count |
|---|---:|
| pending/ | 66 |
| approved/ | 7 |
| rejected/ | 3 |
| archived/ | 0 |

## Id-collision handling notes

Several top-10 proposals shared numeric id prefixes with other (non-top-10)
pending entries (e.g., `20260422-002_lint-autofix*` collides with
`20260422-002_secret-scan*`). To target the correct file, `--id` was passed
as the **full basename-without-extension** (e.g.,
`20260422-002_secret-scan-medium-entropy-hit-in-users-ghost-co`). This hits
`_resolve_proposal_file`'s exact-path branch first, bypassing the
alphabetical-first fallback that would have mis-targeted the lint entry.

No auto-implement. No code generation. raw#20 respected.
