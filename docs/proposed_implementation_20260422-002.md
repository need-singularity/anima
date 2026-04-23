# Proposed Implementation Spec — proposal #20260422-002

Generated: 2026-04-22T14:10:02Z
Source: state/proposals/approved/<id>.json
Status: PROPOSE-ONLY (raw#20 — do NOT auto-implement)

---

## Title
secret_scan: MEDIUM entropy hit in /Users/ghost/core/anima/config/pr_preview_env_spec.json

## Kind
fix

## Proposed module path (does not yet exist)
`tool/proposal_20260422-002.hexa`

## Rationale
secret_scanner flagged MEDIUM entropy match (GENERIC_HIGH_ENTROPY, near keyword "secret"). Manual review required to either redact, mark allowlist, or rotate credential.

## Effort estimate


## Impact estimate
60

## Risk level
0.05

---

## Sub-agent instructions
1. Read the approved proposal JSON at `state/proposals/approved/20260422-002.json` for full spec.
2. Build the module at `tool/proposal_20260422-002.hexa` per hexa conventions (raw#9/10/11/15).
3. Include a `--selftest` that exits 0 on success.
4. After the module is built and selftest passes, the USER (not auto) runs:
   `hexa tool/proposal_archive.hexa --id 20260422-002 --module-path tool/proposal_20260422-002.hexa`
5. archive verifies file existence + selftest exit 0, then moves approved → archived.

## Anti-patterns
- ❌ This file is NOT executable spec — do NOT build until user spawns sub-agent.
- ❌ Do NOT modify .roadmap (uchg).
- ❌ Do NOT write .py files (hexa-only, raw#9).
