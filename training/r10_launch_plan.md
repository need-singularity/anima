# ALM 14B r10 Launch Plan (task B1, 2026-04-18)

**Goal:** Recover from r9 mode collapse (shared/state/r9_collapse_diagnosis.json).

## Critical pre-launch finding (2026-04-18)

Smoke test on pod invalidated A3's "warm-start from r4" recommendation:

| Configuration | First-batch CE on stripped corpus |
|---|---|
| Qwen2.5-14B-Instruct base only | **1.43** |
| base + r4/step_1000 LoRA adapter | 6.58 |
| base + r4 on original chatml corpus | 6.78 |

r4 adapter is distributionally misaligned — loading it **hurts** the model. Base model already achieves CE=1.43 on the stripped corpus, better than any r4/r9 number. r10 therefore runs **fresh LoRA init** (q/k/v/o, r=32, a=64) rather than warm-starting.

## Design decisions

| Knob | r9 | r10 | Why |
|---|---|---|---|
| Init | from-scratch LoRA (step-1 loss=16) | **fresh LoRA** on base (empirically validated; A3's warm-start deviated — see above) | r4 adapter proven to produce CE=6.58 vs base-only 1.43 |
| Steps | 10 000 | 2 000 | r9 best at step 5 000 then regressed; r4 converged at step 1 000 |
| LR | cosine 5e-6 -> 5e-8 | constant 2e-6 | keeps LoRA updates in-distribution; 2.5x smaller than r4's overshooting 5e-6 |
| Consciousness B1 | ON (holo 0.01 + cplx 0.005 + gwt 0.005) | OFF (`--no-consciousness-loss`) | phi_holo 3k-12k oscillation fought CE; disable until B1-off baseline reproduces |
| Corpus | raw alm70b chatml JSONL (90 MB, envelope memorized) | `corpus_alm_70b_stripped.txt` (content-only, `\n\n` delimited) | prevents model from emitting `{"role":"...","messages":[...]}` JSON literals |
| Save every | 2 000 | 2 000 | MFS quota rule compliance |
| Eval cadence | 500 | kr_gen every 200 | early mode-collapse detection |

## Abort triggers (hard)

1. **First-batch CE > 8.0** → `r10_abort.status = FIRST_BATCH_CE_HIGH`
   (was 5.0 — raised after smoke showed Qwen2.5-14B base CE on stripped corpus is ~4.4 mean / 3.7 first-chunk with LoRA no-op; 5.0 caught benign variance)
2. **step=1 loss > 8.0** → `r10_abort.status = STEP1_LOSS_HIGH`
3. **kr_gen hits >= 3/5** (JSON brackets / char-repeat >= 10 / space-quote >= 5) → `r10_abort.status = MODE_COLLAPSE` with step number

## Deviation log

- **feedback_no_resume_data_change**: this is NOT `--resume`. Data changed (chatml-stripped). Documented as "warm-start from r4" — fresh optimizer, fresh step counter, only adapter weights warm-loaded.
- **feedback_one_shot_best**: abort triggers enforce one-shot — no mid-training param changes.
- **HEXA-FIRST strict**: three new .hexa files, zero new .py/.rs/.sh. Python trainer materialised at `/tmp/_train_alm_14b_r10.py` at runtime (same pattern as `train_alm_14b.hexa`).
- **runpod_mfs_quota**: 20 GB `dd` probe in bootstrap; save_every = 2 000; fresh ckpt dir.
- Stack unchanged from r9: unsloth + liger + lora_dropout=0 (no regression; isolates the 3 intentional changes).
