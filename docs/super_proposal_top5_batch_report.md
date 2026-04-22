# Super-Proposal Top 5 Review Batch Report

**Date:** 2026-04-22
**Source:** `state/cluster_consolidate_batch_result.json` + `docs/cluster_consolidate_report.md`
**Scope:** Top 5 of 21 super-proposals emitted by cluster_consolidate sub-agent
**Constraints:** raw#20 (propose-only, no code generation), idempotent, hexa-only

---

## Decision Table

| id | title | members | score | loss_free | risk | verdict | reason |
|----|-------|---------|-------|-----------|------|---------|--------|
| 20260422-044 | fix_json | 22 | 100 | true | 0.1 | approve | largest cluster, loss_free, low risk, coherent kind_keyword fix::json |
| 20260422-047 | fix_phi | 11 | 99 | true | 0.1 | approve | coherent phi-subsystem cluster |
| 20260422-051 | fix_users | 9 | 99 | true | 0.1 | **reject** | duplicate membership with 052 (identical 9 ids); fix::users is path-artifact noise from `/Users/ghost/` absolute paths |
| 20260422-052 | fix_ghost | 9 | 99 | true | 0.1 | approve | representative 9-member cluster (preferred over 051 dupe) |
| 20260422-056 | fix_hexa | 8 | 98 | true | 0.1 | approve | hexa-runtime related cluster |

---

## Summary

- **Approved:** 4 (044, 047, 052, 056)
- **Rejected:** 1 (051, duplicate of 052)
- **Deferred:** 0

## Heuristic Applied

- `loss_free=true AND risk_level in [0, low] AND user_review_needed=false` → **approve**
- `user_review_needed=true OR risk_level >= med` → **defer**
- repeated/ambiguous (duplicate membership or path-artifact signal) → **reject with reason**

## Propose-md Paths (raw#20 compliance: module paths NOT created)

1. `docs/proposed_implementation_20260422-044.md` → proposed module `tool/proposal_20260422-044.hexa` (does not exist)
2. `docs/proposed_implementation_20260422-047.md` → proposed module `tool/proposal_20260422-047.hexa` (does not exist)
3. `docs/proposed_implementation_20260422-052.md` → proposed module `tool/proposal_20260422-052.hexa` (does not exist)
4. `docs/proposed_implementation_20260422-056.md` → proposed module `tool/proposal_20260422-056.hexa` (does not exist)

## Notable Finding — Path-Artifact Noise

The `fix::users` kind_keyword (id 051) and `fix::ghost` kind_keyword (id 052) share **identical member sets** (9 proposals). Both keywords originate from tokenization of absolute paths like `/Users/ghost/core/anima/...`, which accidentally becomes a cluster signal. The cluster_consolidate sub-agent's kind_keyword extraction appears to split path segments on `/`, producing redundant sibling clusters.

**Recommendation for next iteration of cluster_consolidate:**
- Strip absolute path prefixes before extracting kind_keyword
- De-duplicate clusters with identical `merges_with` sets (keep highest-score)

## Batch Artifacts

- `state/super_proposal_top5_batch_result.json` (machine-readable)
- `docs/super_proposal_top5_batch_report.md` (this file)
- `state/proposals/approved/20260422-{044,047,052,056}_super-*.json`
- `state/proposals/rejected/20260422-051_super-fix_users.json`
- `docs/proposed_implementation_20260422-{044,047,052,056}.md`

## Next Steps

1. Remaining 16 super-proposals (score < 98) await next review batch.
2. Follow-up reject sweep recommended for members merged into approved super-proposals (via `lineage_children`).
3. User may spawn sub-agents against the 4 propose-md specs when ready (per spec §8 transition gate).
