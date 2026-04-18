# CLM r4 Pod2 Python→Hexa-Native Migration Plan

**Status:** PLAN ONLY (not executed). User must approve before relaunch.
**Authored:** 2026-04-18
**Pod:** `16oxzm6py5xdss` (anima-clm1b-r4-pod2, H100 80GB)
**Violation:** `feedback_py_ban_total` + `feedback_ai_native_clm` + `feedback_hexa_first_strict`

## 1. Violation summary

The currently running training on pod2 executes `train_clm_1b.py` (PID 1395,
torch.compile SM90 warming, RSS 147 GB) launched by the bash runner emitted
from `training/deploy/clm_r4_launch.hexa` (lines 185-198). The launcher's own
header at L26-33 flags the design exception ("SM90 cuLaunchKernelEx issue")
but the user's strict policy (memory: `feedback_py_ban_total`, dated
2026-04-16) explicitly forbids ALL Python — no create/edit/run — including
pod execution.

**Rule resolution (policy vs. resumption):** because the Python process has
already consumed ~1h of a $129.5 / 43h run, the user-facing decision is
"kill+relaunch-hexa" vs. "let the py finish then switch r5 to hexa". This
document presents the migration path; kill is NOT executed by this BG agent.

## 2. Hexa-native readiness

As of commit `0513127b` (2026-04-18), the hexa-native CLM GPU trainer is
production-candidate:

| Component | Path | Status |
|-----------|------|--------|
| Trainer | `training/train_clm_gpu.hexa` | USE_FUSED=1 patched, 4.27% MFU (1.54× vs. 2.78%) |
| Scale config | `training/train_clm.hexa::scale_1_5b` | d=2048 L=24 H=16 d_ff=8192 bf16 — matches `clm_1b_config.json` |
| Corpus loader | `training/clm_mmap_loader.hexa` | mmap byte-window (5.38 GB-safe, avoids 172 GiB RAM blowup) |
| Launch wrapper | `training/deploy/clm_r4_launch.hexa` | Currently dispatches .py. Needs fork to hexa-native variant. |
| Binary install | `/usr/local/bin/clm_r4_launch` on pod2 | Installed but currently wraps the .py call |

## 3. Relaunch script (SCAFFOLD CREATED 2026-04-18)

- [x] Scaffold created: `training/deploy/clm_r4_pod2_relaunch_hexa_native.hexa`
  (supports `--selftest` and `--dry-run` only; live fire gated on
  `LIVE_FIRE_OK=1` env + explicit user confirmation).

Responsibilities:

1. SSH to pod2 and `tmux kill-session -t clm-r4`
2. `pkill -f train_clm_1b.py` (idempotent)
3. scp `train_clm.hexa` + `train_clm_gpu.hexa` + `clm_mmap_loader.hexa` +
   `clm_1b_config.json` to `/workspace/anima/training/`
4. Cross-compile hexa sources to linux x86_64 ELF on macOS
   (`scripts/cross_compile_linux.hexa`, proven path per `0513127b`), scp the
   .c + runtime.c, remote `gcc` link (avoids GLIBC_2.38 vs 2.35 mismatch)
5. `tmux new -d -s clm-r4-hexa 'clm_r4_hexa_native --corpus /workspace/corpus_clm_r4.txt --steps 750000 --batch 8 --seq 512 --lr 3e-4 --warmup 5000 --save-every 5000 --ckpt-dir /workspace/ckpt_clm1b_r4 2>&1 | tee /workspace/clm_r4_hexa.log'`
6. Verify within 60 s: `nvidia-smi` util > 5 %, loss line present
   (else kill per `RUNPOD_SILENT_CPU_FALLBACK` ossified rule)

## 4. Cost diff

| Scenario | Wall (h) | Cost | Loss | Recovery |
|----------|----------|------|------|----------|
| Let Python finish | 43.3 | $129.5 | eval≤1.0 expected | no rework |
| Kill now, hexa relaunch | 43.3 + unknown SM90 cuLaunchKernelEx | $129.5+ | TBD — hexa-native CLM GPU path has unresolved SM90 failures (per `deploy/h100_clm_native_run.log` 2026-04-16) | **HIGH RISK** — may fail to train at all |
| Let finish, r5 hexa-only | 43.3 | $129.5 (r4) + r5 | r4 delivered | **RECOMMENDED** |

## 5. Rollback

If hexa-native kicks and SM90 cuLaunchKernelEx recurs within first 100 steps:

1. `tmux kill-session -t clm-r4-hexa`
2. `pkill -f clm_r4_hexa_native`
3. Revert to Python trainer TEMPORARILY: restart `clm_r4_launch.hexa` (the
   existing bash wrapper works)
4. Open blocker issue against `training/train_clm_gpu.hexa` SM90 path
5. Do NOT mark as permanent — the user rule is absolute; hexa path must land.

## 6. Recommendation

**Hold on kill.** Let the current Python r4 finish (43h remaining, ~$130
sunk cost protected). Concurrently:

- Fix `train_clm_gpu.hexa` SM90 cuLaunchKernelEx in background
- When it passes a 100-step smoke on an idle H100 (new pod or post-r4 pod2),
  qualify it for r5
- r5 onward uses hexa-native ONLY; Python trainer deleted from repo
- Update `clm_r4_launch.hexa` L26-33 to remove the "py carve-out"
  justification — remove the Python code path entirely

## 7. Immediate cleanup (this session)

- [x] Delete `anima-agent/results/_persona_demo.py` (untracked, hexa equiv
      exists: `serving/persona_apply.hexa` + `serving/serve_14b_ubuntu.hexa`)
- [x] Verify `PreToolUse:Write` hook blocks .py/.rs/.sh/.c file creation
      (tested 2026-04-18, block message delivered)
- [x] `.gitignore` already ignores `*.py` implicitly via `/data/` and
      `anima-agent/results/*.py`; no repo-level `*.py` ignore rule exists,
      so untracked .py files remain visible in `git status` (intentional —
      keeps the user aware of any stray Python)
- [ ] User decision: continue pod2 Python r4 to completion vs. kill + hexa relaunch
- [ ] Update `feedback_py_ban_total.md` memory: clarify "pod execution is
      also Python — include remote pods in the ban" (see section 8)

## 8. Suggested memory update

`~/.claude-claude4/projects/-Users-ghost-Dev-anima/memory/feedback_py_ban_total.md`
should add a bullet:

> BG agents dispatching Python on remote GPU pods (RunPod, Vast, Hetzner) are
> also in violation. The ban covers execution venue, not just local repo
> files. `train_clm_1b.py` on pod2 discovered 2026-04-18 — migration plan
> `training/deploy/clm_r4_pod2_py_to_hexa_migration.md`.

## 9. Files referenced

- `training/deploy/clm_r4_launch.hexa` (the offending launcher)
- `training/deploy/clm_r4_pod2_fire_log_20260418_214746.md`
- `training/deploy/clm_r4_pod2_relaunch_hexa_native.hexa` (scaffold, 2026-04-18)
- `training/train_clm.hexa` (scale_1_5b)
- `training/train_clm_gpu.hexa` (USE_FUSED=1 patch)
- `training/clm_mmap_loader.hexa` (byte mmap)
- `training/clm_gpu_mfu_unblock_report_20260418.md`
- commit `0513127b` (MFU breakthrough + pod2 hexa binary install)
- commits `f64f6af3` + `a4e9e58e` (sister Linux x86_64 hexa_v2 crossbuild)
