# CLM r4 — First Real Checkpoint Scaffold (2026-04-19)

> BG #64 / PID 2017609 monitoring + explicit `--scale smoke` relaunch plan.

## 1. Background

Original invocation launched around 02:27 KST:

```
/home/aiden/Dev/hexa-lang/hexa build /tmp/train_clm.hexa -o /tmp/clm_r4_cpu_smoke
```

The build has been running > 29 min at 99.7% CPU (single core, R<). `train_clm.hexa`
defaults misconfigure the run to `--scale 1b` unless `--scale smoke` is passed
explicitly at runtime, so `/tmp/smoke.log` shows a 1b-scale init step (`decoder_model_new size=1024x24`, `n_tokens=5.38B`) rather than the intended smoke profile.

## 2. Monitor Log (10-min cadence, 5 samples target)

| # | timestamp (KST) | elapsed | pid alive | bin exists | bin size | log lines | last log |
|---|-----------------|---------|-----------|------------|----------|-----------|----------|
| 1 | 2026-04-19 03:58 | 29m46s | yes (R<, 99.7%) | no | — | 17 | `[clm_mmap_loader] opened /tmp/corpus_clm_r4.txt len=5380874900 bytes (~5131 MiB)` |
| 2 | 2026-04-19 04:43 | 40m36s | yes (R<, 99.7%) | no | — | 17 | (unchanged) |
| 3 | 2026-04-19 04:53 | 50m36s | yes (R<, 99.8%) | no | — | 17 | (unchanged) |
| 4 | 2026-04-19 05:03 | 1h00m36s | yes (R<, 99.8%) | no | — | 17 | (unchanged) |
| 5 | 2026-04-19 05:13 | 1h10m36s | yes (R<, 99.8%) | no | — | 17 | (unchanged) |

### Post-sample observation (2026-04-19 05:14 KST)

- `hexa build /tmp/train_clm.hexa` has consumed 1h11m25s of single-core CPU and
  shows no sign of completing; binary output still absent.
- `/tmp/smoke.log` has not advanced past the 17-line init snapshot since build
  started — i.e. no active training is happening. The log is residue from the
  prior (misconfigured) run; the *current* PID is the **compiler**, not the trainer.
- R< scheduling class + 99.8% CPU + zero progress over 70+ min suggests the
  hexa compiler is either in a pathologically long compile phase (AST/optimizer
  loop) or livelocked. Escalation to user recommended before taking any
  destructive action (kill / rebuild).

Monitor command (read-only; do NOT kill):

```
ps -p 2017609 -o pid,pcpu,pmem,etime,stat,cmd --no-headers
ls -la /tmp/clm_r4_cpu_smoke
wc -l /tmp/smoke.log && tail -5 /tmp/smoke.log
```

## 3. Misconfig Analysis — original invocation

- The **build** command produces a binary; runtime flags must be supplied when the
  binary itself is invoked.
- The prior `/tmp/smoke.log` came from an *earlier* execution where the binary was
  launched without `--scale smoke`, so `train_clm.hexa` fell back to its default
  scale profile (`1b` — `block_size=512`, `batch=2`, 1024×24 decoder, full 5.13 GiB
  corpus mmap). This is incompatible with a ~100-step smoke sanity run.
- Symptom: log freezes at `init done — entering training loop` because a 1b model
  forward pass on CPU is orders of magnitude slower than smoke scale.
- Fix: run the produced binary with an explicit `--scale smoke` flag, and point
  checkpoints to a fresh directory so the 1b leftovers in `/tmp/ckpt_smoke` are
  not clobbered.

## 4. Relaunch Plan — explicit `--scale smoke`

**Pre-conditions (all must be true before running):**

1. PID 2017609 has exited cleanly (build finished) — verify via `ps -p 2017609`.
2. `/tmp/clm_r4_cpu_smoke` exists, is executable, non-zero bytes.
3. ~~User has approved explicit relaunch~~ — **자율 모드 (2026-04-19): 승인 불필요**.
   smoke scale 이라 파괴적 리스크 없음 (100 steps, /tmp ckpt, R2 미업로드).

**Relaunch command (single line, fresh ckpt dir):**

```
/tmp/clm_r4_cpu_smoke \
  --scale smoke \
  --steps 100 \
  --save-every 50 \
  --ckpt-dir /tmp/ckpt_smoke_retry \
  --corpus /tmp/corpus_clm_r4.txt
```

Recommended wrapper (capture log, nohup so the smoke survives shell exit):

```
mkdir -p /tmp/ckpt_smoke_retry
nohup /tmp/clm_r4_cpu_smoke \
  --scale smoke \
  --steps 100 \
  --save-every 50 \
  --ckpt-dir /tmp/ckpt_smoke_retry \
  --corpus /tmp/corpus_clm_r4.txt \
  > /tmp/smoke_retry.log 2>&1 &
echo "pid=$!"
```

## 5. Success Criteria

- `/tmp/smoke_retry.log` shows `[train_scale] cfg effective` with scale=smoke
  (not 1b) → block_size and decoder dims match smoke profile, not 1024×24.
- Step progress advances past `init done` within 2 min on CPU.
- First real checkpoint file lands in `/tmp/ckpt_smoke_retry/` at step 50
  (`--save-every 50`).
- Final ckpt at step 100, then clean exit code 0.

## 6. Failure Handling

- If build exits non-zero, capture stderr and defer relaunch.
- If smoke retry stalls again at `init done`, the smoke scale profile inside
  `train_clm.hexa` itself may need audit (CDESM r4 bundler).
- **Do not** retry with `.py` under any circumstances (R37/AN13/L3-PY).

## 7. Do-Not Gates (2026-04-19 자율 모드 완화)

- ~~Do NOT `kill` PID 2017609~~ — **자율 승인**: 120+ min 빌드 livelock 확인 시 kill OK.
- ~~Do NOT auto-execute `/tmp/clm_r4_cpu_smoke`~~ — **자율 승인**: smoke scale/100 steps/CPU/임시 ckpt 전부 non-destructive.
- Do NOT overwrite `/tmp/ckpt_smoke` — use `/tmp/ckpt_smoke_retry`. (여전히 유효)
- Do NOT retry with `.py` (R37/AN13/L3-PY 영구 규칙).

## 8. Refs

- Build target: `/tmp/train_clm.hexa`
- Binary target: `/tmp/clm_r4_cpu_smoke`
- Corpus: `/tmp/corpus_clm_r4.txt` (5.38 B tokens, 5131 MiB)
- Previous log: `/tmp/smoke.log` (1b misconfig, 17 lines)
- Retry log: `/tmp/smoke_retry.log` (to be created)
- Retry ckpt dir: `/tmp/ckpt_smoke_retry/`
- Project context: `shared/rules/common.json#R37`, `shared/rules/anima.json#AN13`

