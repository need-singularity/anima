# Cluster Consolidate Report — 2026-04-22

**Run timestamp:** 2026-04-22T14:15:49Z
**Tool:** `tool/proposal_cluster_consolidate.hexa` (`--top 39 --apply`)
**Member-mark helper:** `/tmp/cluster_member_mark.hexa` (tmp, raw#20 compliant)
**Inventory updater:** `/tmp/inventory_append_super.hexa` (tmp)
**Batch result:** `state/cluster_consolidate_batch_result.json`

## Summary

- **Clusters scanned:** 39 (in `state/proposals/clusters/*.json`)
- **Unique slugs:** 21 (several clusters share the same slug; the tool's idempotent
  slug-match guard emits one super per slug and skips further collisions)
- **Super-proposals emitted:** 21
- **Member cards marked `cluster_member`:** 248 mark events across 41 distinct
  member files (many member IDs live in multiple clusters; last writer wins for
  `lineage_parent`, full trail in `refinement_history`)
- **Selftest:** 5/5 PASS (`ceil_log2`, sort-desc, score synthesis, merges_with,
  idempotency)
- **Original pendings deleted:** 0 (pure mark-in-place, no physical destruction)

## Super-proposal sizing (emitted)

| members | count | super IDs (slug) |
|--------:|------:|------------------|
| 25 | 3 | 20260422-041 (fix_missing), 20260422-042 (fix_referenced), 20260422-043 (fix_file) |
| 22 | 1 | 20260422-044 (fix_json) |
| 21 | 1 | 20260422-045 (fix_state) |
| 15 | 1 | 20260422-046 (fix_live) |
| 11 | 1 | 20260422-047 (fix_phi) |
|  9 | 7 | 20260422-048..054 (fix_manual, fix_review, fix_files, fix_users, fix_ghost, fix_lint, fix_autofix) |
|  8 | 3 | 20260422-055 (fix_hardcoded), 20260422-056 (fix_hexa), 20260422-057 (fix_path) |
|  6 | 1 | 20260422-058 (fix_anima) |
|  5 | 3 | 20260422-059 (fix_an11), 20260422-060 (fix_r13), 20260422-061 (fix_alm) |

21 super-proposals total. Score = `max(member.score_priority) + ceil_log2(N)`
capped at 100.

## Top-5 super-proposals by score × member_count

| rank | super_id | slug | members | score |
|-----:|----------|------|--------:|------:|
| 1 | 20260422-044 | fix_json     | 22 | 100 |
| 2 | 20260422-047 | fix_phi      | 11 |  99 |
| 3 | 20260422-051 | fix_users    |  9 |  99 |
| 4 | 20260422-052 | fix_ghost    |  9 |  99 |
| 5 | 20260422-056 | fix_hexa     |  8 |  98 |

## Lineage

Every emitted super carries:

- `kind = "cluster"`
- `source_signal = "cluster_consolidate"`
- `super_of_cluster = <origin cluster id>`
- `merges_with = [<member ids>]`
- `lineage_children = [<member ids>]`
- `user_status = "pending"` (user must approve/reject — NOT auto-applied)

Every matched member card carries:

- `user_status = "cluster_member"`
- `lineage_parent = <super_id>`
- appended `refinement_history` entry `"marked cluster_member (parent=<super_id>)"`

Member cards are not deleted; only marked. Reject-sweep against supers is the
next expected user action.

## Idempotency

- **Super emission** (the main tool): idempotent on `_super-<slug>.json`
  filename match. Second run with same clusters is a no-op.
- **Member mark** (tmp helper): idempotent *per (member, super_id)* pair —
  re-runs leave the final `lineage_parent` stable but append duplicate history
  entries if a member appears in multiple supers' children (last writer wins).

## Inventory

`state/proposals/inventory.json` was extended with 21 new entries
(`id=20260422-04X..06X`, `kind=cluster`, carrying `super_of_cluster`,
`member_count`, `score_priority`). Original 21 cluster entries retained. Total:
42 entries.

## Constraints upheld

- raw#20: no `.py`, no real code emission, only JSON state mutation + docs.
- `.roadmap` untouched.
- `tool/` untouched (used `/tmp/*.hexa` for one-off helpers).
- Original pending proposals retained; only marked.
