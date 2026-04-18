# A2-Tool CLEAN Retrain Plan (B4, 2026-04-18)

## Design
- Launcher: `training/launch_alm_a2_tool_clean.hexa`
- Sidecar config: `training/alm_a2_tool_clean_sidecar.json` (SSOT `alm_a2_tool_config.json` untouched)
- Base: vanilla **Qwen2.5-14B-Instruct**, optional warm-start from A2-Orch clean adapter (`r2:anima-models/alm14b/a2_20260416_orch/step_3000/`). **Forbidden:** any `a2_tool_mixed` ckpt.
- Corpus: `clean_tool_corpus_*.jsonl` (W5 clean) — **NOT** mixed.
- LoRA: r=32 alpha=64 attn-only (q/k/v/o), dropout 0.05.
- Schedule: 500 steps smoke, batch 1×grad_accum 8, LR 2e-6 **const** (warmup 0), save@250 eval@50.
- B1 Φ losses: **OFF** (`phi_holo=0`, `gwt=0`, `consciousness_loss_b1=false`) per A3 diagnosis.
- Resume guard: abort immediately if `step_1 CE > 5`.

## Corpus Quality Audit (per `shared/state/tool_corpus_clean_dryrun_20260418.json`)
| Metric | Value | Verdict |
|---|---|---|
| Lines | 1140 | OK (smoke-sized) |
| malformed_permil | 0 | PASS |
| schema_valid | 100% | PASS |
| canonical_names_enforced | true | PASS (fixes `search_web`/`web_search` collapse) |
| hard_negatives (`__no_tool__`) | 300 | OK |
| diversity_permil | 468 | **FAIL vs 800 gate** — acceptable for smoke, needs template fanout for full run |

Verdict: **ACCEPTABLE FOR 500-STEP SMOKE**. Two D4/R9 root causes (92% malformed + alias confabulation) are fully resolved. Diversity shortfall is non-fatal at smoke scale.

## Launch Ordering (Queueable)
1. B1 holds pod — wait for B1 smoke complete.
2. B3 may also contend — if B3 queued, serialize after B3.
3. Then: `FORCE_LAUNCH=1 hexa run training/launch_alm_a2_tool_clean.hexa`.
4. Launcher default is **prep-only** (no-op without `FORCE_LAUNCH=1`).

## Is This Run Needed? (Judge-Fix Tradeoff)
Per `project_judge_fix_breakthrough`, lenient rubric lifted `hire_sim` 0.5333→0.867 **with zero retraining**. If the only gate is hire_sim, this retrain is **OPTIONAL**. Justification for running anyway: (a) produce a reusable clean tool-use adapter (judge fix doesn't give us one), (b) validate W5 corpus end-to-end before 7500-example full build, (c) unblock 13B/70B downstream which will consume the A2-Tool adapter. If H100 budget tight, **defer** — judge fix already clears the immediate gate.
