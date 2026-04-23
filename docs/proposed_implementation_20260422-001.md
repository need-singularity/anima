# Proposed Implementation Spec — proposal #20260422-001

Generated: 2026-04-22T14:10:02Z
Source: state/proposals/approved/<id>.json
Status: PROPOSE-ONLY (raw#20 — do NOT auto-implement)

---

## Title
P1 — proposal_inventory_init bootstrap (schema seed)

## Kind
tool

## Proposed module path (does not yet exist)
`tool/proposal_20260422-001.hexa`

## Rationale
Bootstrap state/proposals/ stack so future ideas accumulate as schema-valid proposal cards instead of spawning modules ad hoc (spec §1, §2, §15).

## Effort estimate
1h

## Impact estimate
unblocks P2-P9 (every later tool reads state/proposals/ — no infra means no proposal stack).

## Risk level
low

---

## Sub-agent instructions
1. Read the approved proposal JSON at `state/proposals/approved/20260422-001.json` for full spec.
2. Build the module at `tool/proposal_20260422-001.hexa` per hexa conventions (raw#9/10/11/15).
3. Include a `--selftest` that exits 0 on success.
4. After the module is built and selftest passes, the USER (not auto) runs:
   `hexa tool/proposal_archive.hexa --id 20260422-001 --module-path tool/proposal_20260422-001.hexa`
5. archive verifies file existence + selftest exit 0, then moves approved → archived.

## Anti-patterns
- ❌ This file is NOT executable spec — do NOT build until user spawns sub-agent.
- ❌ Do NOT modify .roadmap (uchg).
- ❌ Do NOT write .py files (hexa-only, raw#9).
