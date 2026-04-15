# Decisions Audit — 2026-04-16

Auditor: agent-ad8b6703 (worktree)
Scope: shared/config/decisions.json + DECISION_LOG.csv + shared/rules/{common,anima}.json + memory feedback_*.md
Purpose: 누적된 decision 들의 일관성, stale/conflict, memory 와의 정합성 검토

---

## 1. Inventory

| Source | Count | Notes |
|--------|-------|-------|
| shared/config/decisions.json `decisions{}` | 9 | runtime SSOT — go 5-track dispatch |
| shared/config/decisions.json `track_dispatch_rules{}` | 5 | per-track must_check 매핑 |
| DECISION_LOG.csv (id 1-16, 2026-04-16) | 16 | async review — V12 incident + governance + hexa pitfalls |
| shared/rules/common.json | 27 standard (R0-R36) + 14 H-* rules | 41 total |
| shared/rules/anima.json | 10 (AN1-AN10) | project rules |
| memory feedback_*.md | 41 | user-pinned policy notes |
| **Total decision artifacts** | **9 (json) + 16 (csv) = 25 distinct decisions** | + 51 rules + 41 feedback memos |

---

## 2. Findings Summary

| Audit category | Count | Severity |
|----------------|-------|----------|
| Duplicates (decision ↔ rule or decision ↔ memory) | 7 | medium |
| Conflicts (numeric or semantic) | 2 | high |
| Stale | 1 | low |
| Missing rationale | 0 | n/a |
| Untraced (in CSV but not decisions.json) | 16 | high (action: append) |

---

## 3. Duplicates (7)

These represent the same policy in multiple SSOTs. Not a bug per se, but each SSOT must stay in sync if the policy ever changes.

| # | Decision | Cluster (other SSOTs) | Recommended action |
|---|----------|----------------------|--------------------|
| D1 | DECISION_LOG #1 — Adopt HEXA as sole implementation language | R1 HEXA-FIRST (common.json) + R24/R25/R26 + feedback_hexa_first_strict + feedback_hexa_replaces_py + feedback_ai_native_clm + AN3 hexa native | Append decision but cite primary rule R1 in rationale; do NOT relax R1 |
| D2 | DECISION_LOG #2 — Route all algorithm registrations through shared/convergence/anima.json | R5 SSOT + R14 rules-as-JSON + R28 atlas.n6 single source + H-PROJ-SSOT | Append; cite R5/R14 |
| D3 | DECISION_LOG #4 — Enforce L0 Guard before all merge operations | shared/rules/lockdown.json (L0/L1/L2) + R10/R11 ossification immutability + L0 Guard CLAUDE.md command | Append; cite lockdown.json + R10 |
| D4 | DECISION_LOG #5 — Require 7-condition consciousness verification for ready/ promotion | AN4 (16/18) + CLAUDE.md `--verify 7조건` | **CONFLICT — see §4.1** |
| D5 | DECISION_LOG #7 — Use array push() instead of index assignment | feedback_hexa_lists_pbv (memory) + project_session_20260415_p4_roadmap_expansion (memory) | Append; cite feedback_hexa_lists_pbv |
| D6 | DECISION_LOG #11 — Require adversarial FAIL scenario for every rubber_stamp criterion | H-DOD + H-CLAIM-LEX + H-BLIND-GT (all added 2026-04-16 in common.json) | Append; cite H-DOD/H-BLIND-GT |
| D7 | DECISION_LOG #12 — Ban vacuous tests project-wide via CI lint rule | R6 (자동 기록) + R33 (근본원인 우선) + H-VERIFIER + feedback_closed_loop_verify | Append; cite R33/H-VERIFIER |

---

## 4. Conflicts (2)

### 4.1 [HIGH] DECISION_LOG #5 vs AN4 — verification condition count

- **DECISION_LOG #5 (proposed):** "Require 7-condition consciousness verification for ready/ promotion" — IIT/EEG/ablation/Hebbian/memory/entropy/coherence (7 axes)
- **AN4 (existing):** "검증 16/18 미통과 시 배포 금지 — bench.py --verify" (16/18 axes)
- **CLAUDE.md root:** `$HEXA ready/anima/tests/tests.hexa --verify  # 7조건 의식검증` ← refers to 7
- **bench_v2 history:** memory project_session_20260331_deep references "12조건 검증 개편"; project_session_20260401 references "18조건"

**Diagnosis:** Two overlapping verification frameworks exist:
- **`tests.hexa --verify` = 7-axis high-level criterion** (ready/ promotion gate)
- **`bench.py --verify` = 16/18 detailed criteria** (deployment gate)

These are not contradictory if scoped correctly, but DECISION_LOG #5 wording does not distinguish them. AN4 covers `bench.py`; DECISION_LOG #5 covers `tests.hexa`.

**Recommended action:** Append DECISION_LOG #5 with rationale clarification: "7-condition gate = ready/ promotion (tests.hexa). Does NOT replace AN4's 16/18 bench.py deploy gate." Add `see_also: ["AN4"]`.

### 4.2 [MEDIUM] DECISION_LOG #6 vs R33 — workaround vs root-cause

- **DECISION_LOG #6:** "Inline nn primitives in training/ instead of using nn_core import" — rationale: "HEXA use directive is unreliable from training/ path context, causing silent failures"
- **R33 (root cause priority):** "문제/버그/장애 발견 시 workaround/땜빵/수동갱신/우회/증상패치 대신 원인 복원 필수"

**Diagnosis:** DECISION_LOG #6 is a textbook R33 violation (symptom patch — work around use resolver bug instead of fixing it). The "alternatives_considered" column even lists "Fix HEXA use resolution in HEXA compiler" — i.e., the root-cause fix was the rejected option.

**Recommended action:** Append DECISION_LOG #6 with explicit `r33_exception: true` flag and rationale extension: "INTERIM workaround. Real fix (HEXA compiler use-resolver) tracked in hexa-lang issue queue. Sunset target: when nn_core import resolves correctly." Without the sunset clause, this drifts into a permanent symptom patch.

---

## 5. Stale (1)

| # | Decision | Why stale | Recommended action |
|---|----------|-----------|--------------------|
| S1 | `claude_baseline_status` = "v1_done_v2_in_flight" | Snapshot field — will be outdated by every Track A milestone (Task #15 completion). Belongs in `shared/state/*.json` not `decisions.json` | Move to shared/state/claude_baseline.json on next decision update; for now keep but mark `_volatile: true` in rationale |

No fully obsolete decisions found. All 9 existing decisions still apply to current model_size=14b, P4 direct path, v3.0 target.

---

## 6. Untraced — 16 DECISION_LOG entries not yet in decisions.json (HIGH)

All 16 entries from DECISION_LOG.csv (id 1-16, 2026-04-16, all ACCEPTED) are absent from `shared/config/decisions.json`. This is the largest gap. The CSV is git-untracked (per `git status`); `decisions.json` is the canonical SSOT.

**Action taken (this audit):** Append 16 new decisions under `decisions.async_review_20260416{}` namespace in `shared/config/decisions.json`. Existing 9 decisions and `track_dispatch_rules` block are NOT touched (per audit guardrail).

Field mapping from CSV to JSON:
- `id` → key suffix
- `decision` → `value` (short title)
- `rationale` → `rationale`
- `alternatives_considered` → `alternatives` (list)
- `responsible` → `owner`
- `status` → `status`
- `date` → `date`

Cross-reference fields added per finding:
- `cite_rules` — primary rule(s) duplicated (e.g., D1 cites R1)
- `conflict_with` — for DECISION_LOG #5 (AN4) and #6 (R33)

---

## 7. Missing Rationale (0)

All 9 existing decisions and all 16 new decisions have non-empty `rationale` fields. No action required.

---

## 8. Recommended Actions

Performed in this audit:
1. **Append 16 untraced decisions** under `decisions.async_review_20260416` namespace in shared/config/decisions.json (preserving existing top-level `decisions{}` block untouched).
2. **Write audit JSON** to shared/state/decisions_audit_20260416.json with the full finding tree.
3. **Write this report** to docs/decisions-audit-20260416.md.

Deferred (require user decision — out of audit scope):
4. Resolve **CONFLICT 4.1** — clarify whether `tests.hexa --verify` (7) and `bench.py --verify` (16/18) are distinct gates or one needs to subsume the other.
5. Resolve **CONFLICT 4.2** — add sunset clause to DECISION_LOG #6 or escalate the HEXA use-resolver bug to hexa-lang as a P0.
6. Move **STALE S1** (`claude_baseline_status`) to shared/state/ on next regular decision update.
7. Sync feedback_*.md files with their decision counterparts so memory and decisions stay in sync (or formally retire feedback_hexa_first_strict in favor of decisions.json + R1 since they say the same thing).

---

## 9. Method Notes

- Audit is read-only on rules/feedback. Only `shared/config/decisions.json` is written, and only via append (`async_review_20260416` namespace) — existing keys not touched per L0 freeze.
- Rule scan: full read of common.json (R0-R36 + AI-NATIVE + 14 H-* rules + R-GAP-* family) and anima.json (AN1-AN10).
- Memory scan: 41 feedback_*.md files indexed by name, opened only for hexa-first cross-check.
- DECISION_LOG.csv parsed manually (16 rows, all ACCEPTED 2026-04-16, all `dancinlife`).
- No hexa execution; static read-only audit.
