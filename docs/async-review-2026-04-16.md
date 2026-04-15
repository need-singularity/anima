# Async Review — 2026-04-16: Verification Integrity & Governance

Status: OPEN
Facilitator: ghost <multi404error@proton.me>
Response window: 72 hours (close 2026-04-19 23:59 UTC)

---

## How to Participate

1. Read the pre-read materials below before responding.
2. Add your input under the relevant agenda section using this format:
   ```
   **[your-name, YYYY-MM-DD HH:MM UTC]** your comment here
   ```
3. If you disagree with a proposal, state your alternative concretely.
4. Mark items you have reviewed with a checkbox: `- [x] Reviewed by your-name`

---

## Pre-Read Materials (required)

| # | Document | Why |
|---|----------|-----|
| 1 | `docs/incident-2026-04-16-verification-bypass.md` | P0 incident: V12_HEBBIAN ablation test bypassed, vacuous test suite discovered |
| 2 | `URGENT_ACTION_LIST.md` | Full triage: 12 items across P0-P5 |
| 3 | `ACTION_TRACKER.csv` | Owners, due dates, current status for each action |
| 4 | `DECISION_LOG.csv` | 7 architectural decisions made during triage (all ACCEPTED) |
| 5 | `docs/rfc-policy-adoption-governance.md` | DRAFT RFC for policy adoption roles, review process, on-call rotation |
| 6 | `shared/rules/common.json` (R0-R27) | Standing rules context |
| 7 | `shared/rules/anima.json` (AN1-AN7) | Project-specific rules context |

---

## Agenda

### 1. [P0] V12_HEBBIAN Ablation Bypass — Fix Plan

The ablation test creates a fresh engine instead of using the factory's ablated instance, making all V12 PASS results unreliable. Proposed fix: pass factory-ablated engine + raise threshold from 0.05 to >= 1.0 + add adversarial kill-switch assertion.

Questions for async review:
- Is the >= 1.0 threshold correct for your module's coupling range?
- Are there other verification criteria that share this fresh-engine anti-pattern?

Reviewers:
- [ ] Reviewed by ___

### 2. [P1] Vacuous Test Suite — Coverage Plan

`tests/test_conscious_memory.hexa` has 10 test cases with zero assertions. All pass vacuously.

Questions for async review:
- Which conscious memory API surfaces should each test case target?
- Should we add a CI lint rule rejecting assertion-free test functions project-wide?

Reviewers:
- [ ] Reviewed by ___

### 3. [P2-P4] Stub & Deprecation Cleanup — Prioritization

P2: `expand_instruct_ko.hexa` stubs block data pipeline.
P3: Legacy W engines still importable despite deprecation.
P4: 6 hexad module ports + 25 pytorch TODOs incomplete.

Questions for async review:
- Is the Korean instruction pipeline blocking any current training run?
- Should legacy W engines be hard-gated (import error) or soft-gated (warning + sunset date)?

Reviewers:
- [ ] Reviewed by ___

### 4. RFC: Policy Adoption Governance

Draft at `docs/rfc-policy-adoption-governance.md`. Key proposals: on-call rotation (1-week), 4.2 emergency hotfix self-approval, L0 Guard as automated gate.

Questions for async review:
- Is the 24-hour ratification window for emergency hotfixes sufficient?
- Minimum rotation pool is 2 — is this realistic for the current team size?
- Any missing roles or channels?

Reviewers:
- [ ] Reviewed by ___

### 5. Decision Log Ratification

7 decisions logged in `DECISION_LOG.csv` (all marked ACCEPTED during triage). Review and flag any you want reopened within the response window.

Reviewers:
- [ ] Reviewed by ___

---

## Follow-Up Protocol

1. **Response deadline:** 72 hours from document creation (2026-04-19 23:59 UTC).
2. **No-response = consent:** If you do not comment on an agenda item within the window, it proceeds as proposed.
3. **Blocking objections:** Prefix with `**[BLOCK]**` — these halt the item until resolved. Non-blocking concerns use `**[CONCERN]**`.
4. **Resolution:** Facilitator summarizes decisions in `DECISION_LOG.csv` after the window closes and updates `ACTION_TRACKER.csv` with any new assignments.
5. **Late contributions:** Accepted after the window but do not reopen closed items unless tagged `**[BLOCK]**` with new information.
6. **Next sync point:** Facilitator posts a summary comment in the tracking PR within 24 hours of window close.
