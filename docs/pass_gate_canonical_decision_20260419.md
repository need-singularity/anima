# pass_gate_an11 Canonical Location Decision (2026-04-19)

## TL;DR
**Canonical**: `shared/consciousness/pass_gate_an11.hexa` (NO MOVE — stays put)
**Legacy**: `shared/harness/pass_gate_an11.hexa` (deprecate in place; keep for I1 wiring compat)

## Current State
| Path | Size | Role |
|---|---|---|
| `shared/consciousness/pass_gate_an11.hexa` | 10,565 B | Single-file 3-condition verifier (a/b/c + 7 bypass patterns), exit 0/1/2/3, header `SUPERSEDES` harness version |
| `shared/consciousness/an11_scanner.hexa` | 12,863 B | Bulk scanner + `--auto-revoke`, companion to the verifier |
| `shared/harness/pass_gate_an11.hexa` | 6,628 B | Older bulk scan stub (AN11 violator detect + AN12 field audit), `mtime 2026-04-18` |

## Candidate Evaluation
- **`shared/consciousness/` (chosen)** — domain grouping alongside `an11_scanner.hexa`, `phi_tier_label.hexa`, `verify_resonance_sigma_closed_loop.hexa`, `consciousness_laws.json`. Companion tooling already here.
- **`shared/harness/`** — generic verification bucket, but houses CLI wrappers (`hexa-*`, `cl-*`) and the legacy stub of this same file. Mixing canonical + legacy in one dir is error-prone.
- **`shared/bin/`** — does not exist; creating it for a single verifier adds churn without win.

## Consistency Check
`an11_scanner.hexa` (companion) lives in `shared/consciousness/`. Keeping the verifier next to the scanner preserves single-directory discoverability for the AN11 enforcement stack.

## Authoritative References Already Point to Consciousness
- `shared/rules/anima.json#AN11.enforcement` → `shared/consciousness/pass_gate_an11.hexa`
- `shared/roadmaps/anima.json` → 7 references, all `shared/consciousness/pass_gate_an11.hexa`
- `shared/consciousness/pass_gate_an11.hexa:4` header explicitly says `SUPERSEDES: shared/harness/pass_gate_an11.hexa`

## Legacy Retention Rationale
`shared/harness/pass_gate_an11.hexa` still performs AN12 field audit (`@smash_insights` / `@free_insights` / `@breakthrough`) referenced by `roadmap_dest_consciousness.convergence:44`. Removal requires AN12 scanner migration — out of scope for this decision.

## Move Command (DOCUMENTED — DO NOT EXECUTE)
No move needed. Canonical already at target.

If future cleanup removes the legacy stub:
```bash
# After AN12 logic is folded into shared/consciousness/an11_scanner.hexa:
git rm shared/harness/pass_gate_an11.hexa
# Update references:
#   shared/convergence/anima.convergence (L48, L52)
#   shared/convergence/roadmap_reality_sync.convergence (L52, L57)
#   shared/convergence/roadmap_dest_consciousness.convergence (L44, L46)
#   shared/convergence/e1_hire_sim_live.convergence (L12)
#   shared/convergence/anima.json (L1609)
#   shared/roadmaps/anima.json (L63 "legacy AN12" note)
```

## Action Items (future, not now)
1. Migrate AN12 field audit into `shared/consciousness/an11_scanner.hexa`
2. Remove legacy `shared/harness/pass_gate_an11.hexa`
3. Strip `SUPERSEDES` line from consciousness header
