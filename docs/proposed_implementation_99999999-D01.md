# Proposed Implementation Spec — proposal #99999999-D01

Generated: 2026-04-22T12:58:22Z
Source: state/proposals/approved/<id>.json
Status: PROPOSE-ONLY (raw#20 — do NOT auto-implement)

---

## Title
demo flow proposal D01 (approve+implement+archive)

## Kind
tool

## Proposed module path (does not yet exist)
`tool/proposal_99999999-D01.hexa`

## Rationale
demonstrate full P4 4-tool flow

## Effort estimate
1

## Impact estimate
demo only

## Risk level
low

---

## Sub-agent instructions
1. Read the approved proposal JSON at `state/proposals/approved/99999999-D01.json` for full spec.
2. Build the module at `tool/proposal_99999999-D01.hexa` per hexa conventions (raw#9/10/11/15).
3. Include a `--selftest` that exits 0 on success.
4. After the module is built and selftest passes, the USER (not auto) runs:
   `hexa tool/proposal_archive.hexa --id 99999999-D01 --module-path tool/proposal_99999999-D01.hexa`
5. archive verifies file existence + selftest exit 0, then moves approved → archived.

## Anti-patterns
- ❌ This file is NOT executable spec — do NOT build until user spawns sub-agent.
- ❌ Do NOT modify .roadmap (uchg).
- ❌ Do NOT write .py files (hexa-only, raw#9).
