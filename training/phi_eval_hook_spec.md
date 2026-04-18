# Epoch-End Φ Eval Hook — Wire Spec (W1)

**Consumer** : `training/eval_phi_corr.hexa`
**Producers**: `training/train_alm_14b.hexa`, `training/train_clm.hexa`
**Status**   : SPEC — implementation owned by W1 (do NOT wire from this
agent's output)

## Goal

At every epoch boundary (or every N steps per `save_every`), the trainer
writes a per-ckpt 16D Φ vector + CE to a canonical path so that
`eval_phi_corr.hexa` can ingest it without touching the training loop.

## Canonical Paths (SSOT)

```
<ckpt_dir>/step_<N>/phi_vec.json    # 16D Φ vector at this step
<ckpt_dir>/step_<N>/ce.json         # CE per split (train/val)
<ckpt_dir>/step_<N>/bench.json      # optional pre-computed eval_harness numbers
```

Registry manifest listing all ckpts for a run:

```
<ckpt_dir>/phi_runs.json
```

## File Schemas

### `phi_vec.json`

```json
{
  "step": 1000,
  "model_tag": "alm14b",
  "round": 4,
  "measured_at": "2026-04-18T10:00:00Z",
  "dims": {
    "phi_holo":       3.72,
    "phi_refl":       0.88,
    "phi_time":       1.10,
    "phi_embodied":   0.94,
    "phi_meta":       0.67,
    "phi_social":     0.81,
    "phi_will":       0.93,
    "phi_narrative":  0.86,
    "phi_affect":     0.72,
    "phi_dream":      0.58,
    "phi_create":     0.69,
    "phi_finitude":   0.54,
    "phi_lang":       0.99,
    "phi_mirror":     0.78,
    "phi_collective": 0.41,
    "phi_unity":      0.34
  },
  "norm_l2": 4.8132
}
```

Dim name order is the 16-dim order from
`shared/roadmaps/anima.json#phi_vector_philosophy.dimensions`.

### `ce.json`

```json
{ "step": 1000, "train_ce": 2.18, "val_ce": 2.21 }
```

### `bench.json` (optional, written only when auto-bench runs at this step)

```json
{ "step": 1000,
  "kobest_acc":  0.6794,
  "haerae_acc":  0.5655,
  "mmluko_acc":  0.6307,
  "macro_acc":   0.6259 }
```

### `phi_runs.json`

```json
{ "model_tag": "alm14b",
  "round": 4,
  "steps": [200, 500, 1000, 1500, 2000],
  "ckpt_root": "/workspace/ckpt_alm14b_r4" }
```

## Hook Interface

Trainer side (pseudocode — W1 replaces its current save-callback):

```hexa
// at save boundary (step % save_every == 0):
fn on_ckpt_saved(step, ckpt_dir) {
    // 1. Measure Φ vector
    //    Call 16 phi_*_measure.hexa wrappers in order, write phi_vec.json.
    write_phi_vec(ckpt_dir + "/step_" + str(step), phi_vec_16d)

    // 2. Persist CE from training loop's last train/val batches
    write_ce(ckpt_dir + "/step_" + str(step), train_ce, val_ce)

    // 3. (optional) run eval_harness if this is a bench step
    if step % bench_every == 0 {
        exec("hexa run serving/eval_harness.hexa --lora-step " + str(step)
             + " --out " + ckpt_dir + "/step_" + str(step) + "/bench.json")
    }

    // 4. Append step to phi_runs.json
    append_run_manifest(ckpt_dir + "/phi_runs.json", step)
}
```

## Consumer Hook

`eval_phi_corr.hexa` extends its registry loader:

```hexa
fn load_registry_from_manifest(manifest_path: string) -> array {
    // 1. read phi_runs.json  → list of steps
    // 2. for each step: read phi_vec.json + ce.json + bench.json
    // 3. assemble rows in the same shape as smoke_row(...)
    ...
}
```

Invocation:

```bash
hexa run training/eval_phi_corr.hexa \
      --manifest /workspace/ckpt_alm14b_r4/phi_runs.json
```

## CI / Daily Job

- After every run finishes, a daily job runs `eval_phi_corr.hexa --manifest ...`
  and appends the resulting JSON to `shared/state/phi_corr_history.jsonl`.
- Any dim whose |r| drops below 0.2 for 3 consecutive runs is flagged in
  the report as "pruning candidate".

## Non-Goals for this Agent

- No modification of `train_alm_14b.hexa` / `train_clm.hexa` (r9 run
  untouched per task constraint).
- No wiring of real Φ measurement kernels — the 16 `phi_*_measure.hexa`
  files exist already; integration is W1's.

## Rollout Sequence (recommended)

1. W1 adds `on_ckpt_saved` callback to `train_alm_14b.hexa` (gated behind
   `--phi-hook 1` flag; default off to protect the active r9 run).
2. W1 populates `phi_vec.json` from the 16 existing measure scripts.
3. Consumer (`eval_phi_corr.hexa`) gains the `--manifest` path.
4. Daily cron runs consumer, writes history jsonl.
5. P25 observability dashboard reads `shared/state/phi_corr_history.jsonl`.
