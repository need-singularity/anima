# File Completion Ledger Summary

- generated: `2026-04-22T09:44:31Z`
- sources: `.roadmap` + `state/roadmap_progress.json` + `state/h100_launch_manifest.json`
- ledger SSOT: `state/file_completion_ledger.json`

## Totals

- total files referenced: **155**
- present: **134** (86.5%)
- missing: **21**

## By kind

| kind | count | present | missing |
|------|-------|---------|---------|
| tool | 54 | 52 | 2 |
| state | 73 | 59 | 14 |
| config | 7 | 4 | 3 |
| doc | 12 | 12 | 0 |
| cert | 5 | 3 | 2 |
| plist | 4 | 4 | 0 |

## Top 10 most-referenced

| path | refs | status |
|------|------|--------|
| `tool/cert_gate.hexa` | 6 | present |
| `state/cert_gate_result.json` | 5 | present |
| `.meta2-cert/cell-eigenvec-16.json` | 4 | present |
| `config/alm_r13_v2_config.json` | 4 | present |
| `docs/l3_collective_emergence_spec.md` | 3 | present |
| `edu/lora/cpgd_wrapper.hexa` | 3 | present |
| `state/alm_r13_an11_a_live.json` | 3 | missing |
| `state/alm_r13_drill_breakthrough.json` | 3 | present |
| `state/corpus_tier_manifest.json` | 3 | present |
| `state/mk_vi_definition.json` | 3 | present |

## Missing files (gap callouts grouped by kind)

### cert (2)

- `.meta2-cert/cell-mk8-stationary` — referenced by entries [22] [missing]
- `.meta2-cert/mk8-7axis-skeleton` — referenced by entries [22] [missing]

### config (3)

- `config/launchd/com.anima.{h100_auto_kill` — referenced by entries [34] [pattern_or_missing]
- `shared/bench/drill_breakthrough_criteria.json` — referenced by entries [4] [missing]
- `shared/roadmaps/anima.json` — referenced by entries [1,2] [missing]

### state (14)

- `state/agi_cp1_reached.json` — referenced by entries [11] [missing]
- `state/alm_r13_an11_a_live.json` — referenced by entries [9,10,11] [missing]
- `state/alm_r13_an11_b_live.json` — referenced by entries [9,11] [missing]
- `state/alm_r13_an11_c_live.json` — referenced by entries [9,11] [missing]
- `state/anima_serve_live_smoke_result.json` — referenced by entries [32] [missing]
- `state/anima_serve_production_ship.json` — referenced by entries [11] [missing]
- `state/h100_auto_kill_last_run.json` — referenced by entries [9] [missing]
- `state/phi_4path_cross_result.json` — referenced by entries [10,11,83] [missing]
- `state/phi_p1_qwen3_8b_live.json` — referenced by entries [10] [missing]
- `state/phi_p1-4_*_live.json` — referenced by entries [83] [pattern_or_missing]
- `state/phi_p2_llama_3_1_8b_live.json` — referenced by entries [10] [missing]
- `state/phi_p3_ministral_3_14b_live.json` — referenced by entries [10] [missing]
- `state/phi_p4_gemma_4_31b_live.json` — referenced by entries [10] [missing]
- `state/techniques_225_import_{b` — referenced by entries [69] [pattern_or_missing]

### tool (2)

- `tool/phi_extractor/` — referenced by entries [7] [pattern_or_missing]
- `tool/techniques_225_import_{b` — referenced by entries [69] [pattern_or_missing]

## Notes

- `pattern_or_missing` status = brace/wildcard/dir token captured from .roadmap text (e.g. `tool/phi_extractor/` directory ref, `state/phi_p{1-4}_*_live.json` glob).
- H100 stage live artifacts (`state/alm_r13_an11_*_live.json`, `state/phi_p[1-4]_*_live.json`) are expected post-H100-kickoff; their absence is by design pre-launch.
- `shared/roadmaps/anima.json` and `shared/bench/drill_breakthrough_criteria.json` reflect post-shared-decommission migration; canonical SSOTs live elsewhere (mirror notes in entries #1 #4).
- `.meta2-cert/cell-mk8-stationary` and `.meta2-cert/mk8-7axis-skeleton` cert tokens are referenced without `.json` suffix in #22 evidence; corresponding `.json` files DO exist (separate ledger row).
