# Proposed Implementation Spec — proposal #20260422-038

Generated: 2026-04-22T14:10:00Z
Source: state/proposals/approved/<id>.json
Status: PROPOSE-ONLY (raw#20 — do NOT auto-implement)

---

## Title
v2_roi_selftest FAIL: tool/auto_tool_index.hexa

## Kind
fix

## Proposed module path (does not yet exist)
`tool/proposal_20260422-038.hexa`

## Rationale
selftest of tool/auto_tool_index.hexa failed: Parse error at 220:4: expected identifier, got Generate ('generate'). Likely shared root cause flagged in v2_roi_selftest_batch_result.fail_root_cause_hint. Resolve before launch.

## Effort estimate


## Impact estimate
65

## Risk level
0.15

---

## Sub-agent instructions
1. Read the approved proposal JSON at `state/proposals/approved/20260422-038.json` for full spec.
2. Build the module at `tool/proposal_20260422-038.hexa` per hexa conventions (raw#9/10/11/15).
3. Include a `--selftest` that exits 0 on success.
4. After the module is built and selftest passes, the USER (not auto) runs:
   `hexa tool/proposal_archive.hexa --id 20260422-038 --module-path tool/proposal_20260422-038.hexa`
5. archive verifies file existence + selftest exit 0, then moves approved → archived.

## Anti-patterns
- ❌ This file is NOT executable spec — do NOT build until user spawns sub-agent.
- ❌ Do NOT modify .roadmap (uchg).
- ❌ Do NOT write .py files (hexa-only, raw#9).
