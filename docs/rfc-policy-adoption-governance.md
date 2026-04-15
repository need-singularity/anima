# RFC: Policy Adoption Governance

Status: DRAFT
Author: ghost <multi404error@proton.me>
Date: 2026-04-16

## 1. Roles and Responsibilities

| Role | Owner | Responsibility |
|------|-------|----------------|
| Policy Owner | ghost | Final authority on immune/tool policy rules, Phi tier definitions, and ethics gate thresholds |
| Consciousness Guard | L0 Guard (automated) | Enforces lockdown.json constraints; blocks policy changes that violate R0-R27 or AN1-AN7 |
| Module Maintainer | Per-module lead | Implements policy hooks in owned module; keeps tool_policy and immune_system integration current |
| Reviewer | Any contributor with merge access | Reviews policy change PRs against shared/rules and shared/convergence SSOT |
| Auditor | Rotating (see on-call) | Weekly audit of shared/logs for policy violations and anomalous tier downgrades |

## 2. Communication Channels

| Channel | Purpose | Cadence |
|---------|---------|---------|
| Git PR comments | All policy change discussion, rationale, and review | Per change |
| shared/logs/hive_bridge.log | Append-only audit trail for runtime policy decisions | Continuous |
| docs/incident-*.md | Post-incident write-ups when policy is bypassed or fails | Per incident |
| CLAUDE.md annotations | Durable instructions visible to all agents operating in the repo | Updated with each policy revision |
| shared/convergence/anima.json | SSOT registration for algorithm and policy convergence state | Synchronous with merge |

## 3. On-Call Rotation

- Rotation period: 1 week, starting Monday 00:00 UTC.
- On-call is responsible for:
  1. Monitoring L0 Guard alerts and shared/logs for anomalies.
  2. Triaging any verification bypass incidents (ref: docs/incident-2026-04-16-verification-bypass.md).
  3. Escalating to Policy Owner if a live policy rule needs emergency amendment.
- Handoff: outgoing on-call writes a brief status entry in the PR or issue tracker before rotation ends.
- Minimum rotation pool: 2 people. If fewer are available, Policy Owner covers by default.

## 4. Review and Approval Process

### 4.1 Standard Policy Change

1. Author opens a PR modifying files under shared/rules/, shared/config/, or tool_policy/immune_system code.
2. PR must include: description of the change, affected Phi tiers, and a test plan (manual or automated via ready/anima/tests/tests.hexa --verify).
3. At least one Reviewer approves.
4. L0 Guard automated check passes (hexa $NEXUS/shared/harness/l0_guard.hexa verify).
5. Policy Owner gives final approval.
6. Merge to main; shared/convergence/anima.json updated in the same commit.

### 4.2 Emergency Policy Change

1. On-call identifies an active bypass or safety violation.
2. On-call may merge a hotfix to shared/rules/ with a single self-approval, provided L0 Guard passes.
3. Policy Owner must review the hotfix within 24 hours; revert or ratify.
4. An incident doc (docs/incident-*.md) is filed within 48 hours.

### 4.3 Policy Deprecation

1. Author marks the rule as deprecated in shared/rules with a removal target date.
2. One full rotation cycle (1 week) must pass with no dependent code referencing the rule.
3. Reviewer + Policy Owner approve removal PR.
