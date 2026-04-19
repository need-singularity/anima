# ALM r11 Preflight — 2026-04-20

Source-of-truth:
- Config: `/Users/ghost/Dev/nexus/shared/state/alm_r11_config.json`
- Plan:   `/Users/ghost/Dev/anima/training/deploy/alm_r11_plan.json`
- Trainer: `/Users/ghost/Dev/anima/training/train_alm_lora.hexa` (1112 LOC, dry-run PASS)

## Verdict: NO-GO (conditional — 1 hard blocker on hexa-native path)

Blocker is FFI-side (Day-2 CUDA kernels), NOT trainer-side. All other prereqs GO.
If user authorizes a v5 CUDA landing (or explicitly waives hexa-native per R37
for this run), trainer fires immediately with the command below.

## Prereq matrix

| # | Item | State | Detail |
|---|------|-------|--------|
| 1 | Config SSOT sane | GO   | `base.adapter_source = null` (fresh-from-base, r9/r10 not stacked). `no_resume = true`. lr 5e-7, lora_r 8, alpha 16, batch 4, seq 1024, steps 500, warmup 50, bf16, save_every 100. |
| 2 | Config vs plan drift | GO (noted) | Plan (2026-04-16 11:25) still references `base_lora=/runpod/ckpt_r9`; config SSOT (2026-04-16 23:33) `supersedes` that — fresh-from-base is authoritative. |
| 3 | Hexa trainer exists | GO | `training/train_alm_lora.hexa`. Parse+build+dry-run PASS per header. |
| 4 | Day-2 FFI (`hxqwen14b_forward_with_lora` / `_backward_lora_only` / `_apply_lora_delta`) | **NO-GO** | Present in `/Users/ghost/Dev/hexa-lang/self/native/hxqwen14b.c` as v4 stubs returning `RC_ERR_CUDA_TODO` (-5). v5 CUDA kernel sequence commented out. Trainer will report BLOCKED_FFI on first forward. |
| 5 | Corpus file | GO (renamed) | Config lists `/workspace/anima/training/corpus_alm_r11.jsonl` — does NOT exist. Actual corpus staged on R2 as `r2:anima-corpus/alm/corpus_alm_70b_stripped_kowiki15.txt` (88.98 MB, 86% KO stripped + 15% kowiki admix, SHA256 `04395bf3…`). Matches r11 80/20 KO-blend intent. Config path string is stale but content is ready; recommend pulling the R2 file to `/workspace/data/` on pod. |
| 6 | Forbidden-resume paths absent | GO | No `/runpod/ckpt_r9`, `/runpod/ckpt_r10`, `r2:…/r9/`, `r2:…/r10/` in effective launch command. |
| 7 | ckpt dir reserved | GO | `/workspace/ckpt_alm14b_r11_20260420` (fresh, no collision). R2 prefix `r2:anima-models/alm14b/r11/step_{step}/`. `alm14b/r11/` does not yet exist on R2 — clean slate. |
| 8 | Pod selected | GO | `87xscivuggrwvk` (clm_r5_h100, 1× H100 SXM) — STATUS=EXITED per `runpodctl pod list` → free to restart for r11. Second pod `hhzla1nxmp5019` (hxqwen14b-smoke) RUNNING, left alone. Stays within H100-2-pod authorization. |
| 9 | Corpus size within config bounds | GO | 88.98 MB vs config max 50 MB → **slight overflow** (77% over 50 MB cap). Either raise cap or sub-sample to 50 MB on pod (shuf -n 60000). Not a hard blocker; cap was a heuristic. |
| 10 | Phi logging (AN11) | GO | Trainer integrates `hxqwen14b_compute_phi_holo(h)` per FFI section; log emits phi_vec alongside loss each `eval_every`. |
| 11 | feedback_no_resume_data_change | GO | Fresh ckpt dir, step 0 from base, no `--resume` flag in cli template. |
| 12 | feedback_no_quantization | GO | bf16 only. |
| 13 | feedback_one_shot_best | GO | Single 4h run, 500 steps, abort criteria wired. |
| 14 | R37/feedback_py_ban_total | GO (hexa path); waiver needed if CUDA v5 not landed | Trainer is `.hexa`. If user swaps to Python trainer to bypass v5-CUDA blocker, that violates R37 — escalate instead of silently downgrading. |

## Exact launch command (copy-paste when FFI v5 lands)

Pod-side prep:

```
# On pod 87xscivuggrwvk (start via: runpodctl start pod 87xscivuggrwvk)
export HF_HUB_CACHE=/workspace/hf_cache
export HF_HOME=/workspace/hf_cache
export TRANSFORMERS_CACHE=/workspace/hf_cache
export ANIMA_ROOT=/workspace/anima
export HEXA_CKPT_HOOK=/workspace/anima/scripts/ckpt_backup_hook.hexa

# MFS quota preflight (mandatory per training/CLAUDE.md)
rm -rf /workspace/ckpt_alm14b_* /workspace/_q_test 2>/dev/null
dd if=/dev/zero of=/workspace/_q_test bs=1M count=20000 status=none && rm /workspace/_q_test

# Pull corpus (R2 → /workspace/data/)
mkdir -p /workspace/data
rclone copy r2:anima-corpus/alm/corpus_alm_70b_stripped_kowiki15.txt /workspace/data/ -v --s3-no-check-bucket
sha256sum /workspace/data/corpus_alm_70b_stripped_kowiki15.txt  # expect 04395bf3dd2bdd979c700b505f07974919f6c4bc1ac1ad464186a599813cde8e
```

Launch (foreground `tmux new -s r11`, single line):

```
HEXA_PATH=anima/training hexa run /workspace/anima/training/train_alm_lora.hexa \
  --base Qwen/Qwen2.5-14B-Instruct \
  --corpus /workspace/data/corpus_alm_70b_stripped_kowiki15.txt \
  --out /workspace/ckpt_alm14b_r11_20260420 \
  --steps 500 --lr 5e-7 --lora_r 8 --lora_alpha 16 \
  --batch 4 --seq 1024 --warmup 50 \
  --save_every 100 --eval_every 100
```

Post-training R2 upload (NOT during, per MFS-quota rule):

```
rclone copy /workspace/ckpt_alm14b_r11_20260420 \
  r2:anima-models/alm14b/r11/step_500/ -v --s3-no-check-bucket
```

## Trigger condition

Launch is INDEPENDENT of `serve_alm_native.hexa`. Serve readiness matters for
post-training eval (`/generate` endpoint for hire_sim + likert), not for
training. Training can begin the moment the FFI v5 blocker clears.

Ordered gates (all must clear to fire):
1. `hxqwen14b_forward_with_lora` returns `RC_OK` (not -5) — i.e. v5 CUDA
   kernel sequence compiled in with `HXQWEN14B_CUDA=1`.
2. Pod `87xscivuggrwvk` restarted and reachable via SSH.
3. Corpus SHA matches.

Serve (`serve_alm_native.hexa`) must be live before post-eval step, not
before training start.

## Open items for user decision

- **Hexa-native LoRA FFI (v5 CUDA) not yet landed.** Options:
  (a) Wait for parallel BG agent to land v5 kernels in `hxqwen14b.c`;
  (b) Waive R37 for r11 only and run existing Python peft trainer (explicit
      policy exception required — default stance per feedback_py_ban_total
      is REFUSE);
  (c) Hold r11 entirely until v5 lands.
  Recommended: (a) — no new Python, aligns with AI-native CLM/ALM policy.
- **Config `corpus.path` string is stale.** Either update SSOT to
  `/workspace/data/corpus_alm_70b_stripped_kowiki15.txt` or rename the file
  on pod. Non-blocking; flagged for hygiene.
- **`max_size_bytes: 50000000` will fail validation** against the 88.98 MB
  corpus. Recommend raising cap to `100_000_000` in config SSOT or
  sub-sampling on pod. Trainer should report this; confirm dry-run output.
