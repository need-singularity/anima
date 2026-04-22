# Proposed Implementation Spec — proposal #20260422-056

Generated: 2026-04-22T14:37:08Z
Source: state/proposals/approved/<id>.json
Status: PROPOSE-ONLY (raw#20 — do NOT auto-implement)

---

## Title
super-proposal: fix_hexa  (8 members)

## Kind
cluster

## Proposed module path (does not yet exist)
`tool/proposal_20260422-056.hexa`

## Rationale
Consolidates 8 pending proposals (20260422-001, 20260422-003, 20260422-004, 20260422-009, 20260422-037, 20260422-038, 20260422-039, 20260422-040) sharing cluster signal 'cluster: kind_keyword = fix::hexa'. Single super-proposal lets reviewer approve/reject the entire batch in one action; original members can then be marked merged → super on follow-up reject sweep. Spec: docs/anima_proposal_stack_paradigm_20260422.md §3 step 5.

## Effort estimate


## Impact estimate
95

## Risk level
0.1

---

## Sub-agent instructions
1. Read the approved proposal JSON at `state/proposals/approved/20260422-056.json` for full spec.
2. Build the module at `tool/proposal_20260422-056.hexa` per hexa conventions (raw#9/10/11/15).
3. Include a `--selftest` that exits 0 on success.
4. After the module is built and selftest passes, the USER (not auto) runs:
   `hexa tool/proposal_archive.hexa --id 20260422-056 --module-path tool/proposal_20260422-056.hexa`
5. archive verifies file existence + selftest exit 0, then moves approved → archived.

## Anti-patterns
- ❌ This file is NOT executable spec — do NOT build until user spawns sub-agent.
- ❌ Do NOT modify .roadmap (uchg).
- ❌ Do NOT write .py files (hexa-only, raw#9).
