# Proposal Stack — Top 10 Pending Review (2026-04-22)

Status: **propose-only review document** (raw#20)
Scope: pre-H100 ROI N2 — score-sorted top 10 of ~41 unique pending proposals.
Source: `state/proposals/pending/*.json` (40 unique IDs + 1 sample seed = 41).
Sort key: `score_priority` desc, `risk_level` asc, `first_seen_ts` asc.

This document is a **decision aid**. No proposal is auto-approved. The user
runs `hexa run tool/proposal_approve.hexa --id <N>` per item below.

---

## Summary table

| rank | id | score | risk | loss_free | kind | source_signal | verdict |
|---:|---|---:|---:|:-:|---|---|---|
| 1 | 20260422-001 (sample) | 95 | n/a | true | tool | seed | **archive** (already implemented as P1 bootstrap) |
| 2 | 20260422-017 | 42 | 0.10 | true | fix | file_completion | **approve** |
| 3 | 20260422-016 | 42 | 0.10 | true | fix | file_completion | **approve** |
| 4 | 20260422-013 | 42 | 0.10 | true | fix | file_completion | **dedup → 017** |
| 5 | 20260422-012 | 42 | 0.10 | true | fix | file_completion | **dedup → 016** |
| 6 | 20260422-002 | 41 | 0.05 | true | fix | secret_scan | **approve (urgent)** |
| 7 | 20260422-001 (secret) | 41 | 0.05 | true | fix | secret_scan | **dedup → 002** |
| 8 | 20260422-040 | 39 | 0.15 | true | fix | v2_roi_selftest | **approve (cluster as super)** |
| 9 | 20260422-039 | 39 | 0.15 | true | fix | v2_roi_selftest | **approve (cluster as super)** |
| 10 | 20260422-038 | 39 | 0.15 | true | fix | v2_roi_selftest | **approve (cluster as super)** |

Auto-implement gate (N1: score≥80 + risk=0 + loss_free=true): only the
sample/bootstrap entry would pass score≥80, but no pending entry has
`risk_level == 0` strictly. **Verdict: 0 auto-implementable today** — every
top-10 item still needs a human approve step.

---

## 1.  20260422-001 — proposal_inventory_init bootstrap  (score 95)

* **Title**: P1 — proposal_inventory_init bootstrap (schema seed)
* **Kind / source**: tool / seed (sample.json)
* **Evidence**: `docs/anima_proposal_stack_paradigm_20260422.md` §1 / §2 / §13 / §15
* **Effort / impact**: 1h / unblocks P2-P9
* **Decision**: **archive** — `tool/proposal_inventory_init.hexa` already
  exists and `state/proposals/inventory.json` is populated. Run
  `proposal_archive.hexa --id 20260422-001 --module-path tool/proposal_inventory_init.hexa`.
* **Why not auto**: it's a sample seed with no concrete `risk_level`.

## 2.  20260422-017 — missing .meta2-cert/mk8-7axis-skeleton  (score 42)

* **Kind / source**: fix / file_completion_ledger
* **Evidence**: `state/file_completion_ledger.json` → `missing_files[].path = .meta2-cert/mk8-7axis-skeleton`
* **Effort / impact**: 2h / cert reference unblock (impact 65 — kind=cert)
* **Decision**: **approve** — cert ledgers are referenced but absent. Either
  (a) generate the cert skeleton (loss-free, mechanical) or (b) remove the
  reference with explicit owner sign-off. Recommend (a) given mk8 7-axis is
  active spec line.

## 3.  20260422-016 — missing .meta2-cert/cell-mk8-stationary  (score 42)

* **Kind / source**: fix / file_completion_ledger
* **Evidence**: `state/file_completion_ledger.json` → `missing_files[].path = .meta2-cert/cell-mk8-stationary`
* **Effort / impact**: 2h / cert reference unblock
* **Decision**: **approve** — same reasoning as #2 (cert artifact missing).
  Bundle approval with #2 in a single super-proposal (see N3 cluster super
  candidate `meta2-cert-rehydration`).

## 4.  20260422-013 — missing .meta2-cert/mk8-7axis-skeleton (dup)  (score 42)

* **Decision**: **dedup** — identical title + path as #2 (id 017).
  Re-emit cycle produced two cards. Run
  `proposal_reject.hexa --id 20260422-013 --reason "dedup → 20260422-017"`.

## 5.  20260422-012 — missing .meta2-cert/cell-mk8-stationary (dup)  (score 42)

* **Decision**: **dedup** — identical to #3 (id 016). Reject with reason
  `dedup → 20260422-016`.

## 6.  20260422-002 — secret_scan MEDIUM entropy in pr_preview_env_spec.json  (score 41)

* **Kind / source**: fix / secret_scan
* **Evidence**: `state/secret_scan_violations.json` →
  `/Users/ghost/core/anima/config/pr_preview_env_spec.json` (MEDIUM entropy,
  near-keyword classification).
* **Effort / impact**: 1h / 60
* **Decision**: **approve (urgent)** — secret scanner flagged a MEDIUM hit
  in a config file. Required action: classify (a) redact, (b) allowlist with
  justification, or (c) rotate. Pre-H100 launch this MUST be triaged
  (credentials in PR-preview spec are the highest blast radius).

## 7.  20260422-001 — secret_scan MEDIUM entropy in pr_preview_env_spec.json (dup)  (score 41)

* **Decision**: **dedup** — collision with #6 (id 002). The secret scanner
  re-emitted under a fresh seq because the inventory schema reset between
  cycles. Reject with `dedup → 20260422-002 (secret)`.

## 8.  20260422-040 — v2_roi_selftest FAIL: tool/roadmap_diff_viz.hexa  (score 39)

* **Kind / source**: fix / v2_roi_selftest
* **Evidence**: `state/v2_roi_selftest_batch_result.json` →
  `tools[].verdict=FAIL` for `tool/roadmap_diff_viz.hexa` (parse error
  at 309:4: expected identifier, got `Generate ('generate')`).
* **Effort / impact**: 1.5h / 65
* **Decision**: **approve as super-proposal member** — bundle 037-040
  into `super-v2roi-selftest-fix` (N3 cluster). All four share root cause
  per `fail_root_cause_hint`. Single fix (likely identifier mangling) likely
  resolves all four.

## 9.  20260422-039 — v2_roi_selftest FAIL: tool/cert_graph_gen.hexa  (score 39)

* **Decision**: **approve as super-proposal member** — see #8. Same root
  cause hint, same fix surface.

## 10. 20260422-038 — v2_roi_selftest FAIL: tool/auto_tool_index.hexa  (score 39)

* **Decision**: **approve as super-proposal member** — see #8. Same root
  cause hint, same fix surface.

---

## Aggregate verdict

| action | count | ids |
|---|---:|---|
| **archive** | 1 | 001 (sample/seed) |
| **approve standalone** | 2 | 017, 016 |
| **approve urgent** | 1 | 002 (secret_scan) |
| **approve as cluster super** | 3 | 037-040 (v2roi selftest fail batch — see N3) |
| **dedup-reject** | 3 | 013→017, 012→016, 001(secret)→002 |

Net to user-approve queue: **6 distinct items** out of top 10. Three are
duplicates that should be rejected with `dedup` reason; one is already
implemented (sample seed → archive); the v2roi-fail trio merges into one
super-proposal (see `tool/proposal_cluster_consolidate.hexa`).

## Next-step CLI (user runs sequentially)

```sh
# 1. archive the seed
hexa run tool/proposal_archive.hexa --id 20260422-001 \
        --module-path tool/proposal_inventory_init.hexa

# 2. approve cert / secret items
hexa run tool/proposal_approve.hexa --id 20260422-017
hexa run tool/proposal_approve.hexa --id 20260422-016
hexa run tool/proposal_approve.hexa --id 20260422-002

# 3. dedup-reject duplicates
hexa run tool/proposal_reject.hexa --id 20260422-013 --reason "dedup → 017"
hexa run tool/proposal_reject.hexa --id 20260422-012 --reason "dedup → 016"
hexa run tool/proposal_reject.hexa --id 20260422-001 --reason "dedup → 002 (secret)"

# 4. consolidate the v2roi-fail trio into a super-proposal
hexa run tool/proposal_cluster_consolidate.hexa --apply

# 5. emit propose-md spec for each newly-approved id (raw#20: only md)
hexa run tool/proposal_implement.hexa --id 20260422-017
hexa run tool/proposal_implement.hexa --id 20260422-016
hexa run tool/proposal_implement.hexa --id 20260422-002
```

Hard constraints reaffirmed:

- DO NOT modify `.roadmap` (uchg).
- DO NOT auto-implement (raw#20).
- Auto-threshold scan (`tool/proposal_auto_threshold.hexa`): 0 auto-emits
  today (no pending item satisfies risk == 0 strictly).
