# Proposed Implementation Spec — proposal #20260422-017

Generated: 2026-04-22T14:09:59Z
Source: state/proposals/approved/<id>.json
Status: PROPOSE-ONLY (raw#20 — do NOT auto-implement)

---

## Title
missing referenced file: .meta2-cert/mk8-7axis-skeleton

## Kind
fix

## Proposed module path (does not yet exist)
`tool/proposal_20260422-017.hexa`

## Rationale
file_completion_ledger flagged .meta2-cert/mk8-7axis-skeleton (kind=cert) as referenced but absent. Either create the artifact, remove the reference, or mark it as deferred with explicit owner.

## Effort estimate


## Impact estimate
65

## Risk level
0.1

---

## Sub-agent instructions
1. Read the approved proposal JSON at `state/proposals/approved/20260422-017.json` for full spec.
2. Build the module at `tool/proposal_20260422-017.hexa` per hexa conventions (raw#9/10/11/15).
3. Include a `--selftest` that exits 0 on success.
4. After the module is built and selftest passes, the USER (not auto) runs:
   `hexa tool/proposal_archive.hexa --id 20260422-017 --module-path tool/proposal_20260422-017.hexa`
5. archive verifies file existence + selftest exit 0, then moves approved → archived.

## Anti-patterns
- ❌ This file is NOT executable spec — do NOT build until user spawns sub-agent.
- ❌ Do NOT modify .roadmap (uchg).
- ❌ Do NOT write .py files (hexa-only, raw#9).
