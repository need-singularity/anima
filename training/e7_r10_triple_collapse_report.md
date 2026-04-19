# E7 — r10 Triple Collapse Root Cause + r10c Redesign

**Session:** 2026-04-18 E7 (local-scope deliverables)
**Scope:** diagnose why r10 failed 3× and did not abort on collapse; specify r10c.
**Companion artifacts:**
- `shared/convergence/alm_14b_r10.convergence` (OSSIFIED tracking record)
- `shared/convergence/runpod_autopilot.convergence` (F1 F1-OSS-01/02/03 + E7 gap)
- `shared/harness/convergence_update.hexa` (I1 gap scanner)

---

## 1. Event chain

| Attempt | Fix driver | First-batch CE | Crash site | Root cause |
|---------|------------|----------------|------------|------------|
| 1 (E5) | clean start | n/a | kwarg `num_logits_to_keep` | unsloth API rename → `logits_to_keep` |
| 2 (E5 relaunch) | keep rename | 5.2372 (good) | step 200 `kr_gen` | CUDA OOM 80MiB need / 12.12MiB free; train activations not freed before `fast_generate` |
| 3 (E6 OOM fix) | `gc.collect + empty_cache + no_grad + max_new_tokens=32 + PYTORCH_ALLOC_CONF=expandable_segments:True` | 5.2372 (match) | step 200 post-kr_gen forward resume | fragmentation OOM + **inline collapse_score FALSE CLEAN** on mode-collapsed samples |

---

## 2. The three bugs behind the 3rd failure

### Bug 1 — inline `collapse_score` is ASCII-only

`training/launch_alm_14b_r10.hexa:183-190` embeds a Python `collapse_score(s)` that checks:

```python
if s.count('{"') >= 3: return True
if s.count('":"') >= 3: return True
for ch in ['n', ' ', '?', "'"]:
    if ch*10 in s: return True
if " '" * 5 in s: return True
```

The step-200 kr_gen samples actually written to `kr_gen_step_200.json` were:
- `녕녕녕녕녕녕녕녕녕녕...` (10+ Korean byte repeat of 녕)
- `낙 낙 낙 낙 낙 ...` (Korean char + space repeat)
- `IRRIRRIRRIRR...` (ASCII 3-char cycle, no single-char ≥10)

None trip the four ASCII single-char runs; none trip `{"` or `":"`. Result: `hits=0`, training continues, step 200 is accepted as "clean" and OOM masks the real collapse.

**`training/kr_gen_sentinel.hexa` already implements the correct semantics** (`max_byte_run` — any byte repeating ≥10 consecutively, byte-level safe for multi-byte hangul). It exists in-tree but is **not invoked** from r10. r10b (via H2) correctly wires it as a subprocess (`launch_alm_14b_r10b.hexa:354-368`) — r10 must too.

### Bug 2 — F1 watchdog reports `TRAINING` on dead PID

Reproduced twice in this session (attempt 2 and attempt 3): the F1 watchdog heartbeat file kept stating `TRAINING` after the python trainer had died. Current `runpod_watchdog.hexa` writes status based on file-modtime rather than PID liveness. Must gate `TRAINING` emission with `kill -0 $PID`:

```hexa
fn is_pid_alive(pid: string) -> bool {
    let rc = exec("kill -0 " + pid + " 2>/dev/null; echo $?").trim()
    return rc == "0"
}
```

All `TRAINING` writes become conditional on this; otherwise emit `DEAD_PID`.

### Bug 3 — loss below 1.0 at step 200 on 14B fresh LoRA is collapse, not convergence

The "step 200 loss=0.4152 극적 돌파" celebration was premature — same signature as r9 undetected 5000-step collapse. OSSIFIED: **sub-1.0 loss at step < 500 on fresh-init 14B LoRA requires kr_gen_sentinel PASS before acceptance.** Encoded as `E7-OSS-03` in `alm_14b_r10.convergence`.

---

## 3. r10c redesign (minimum viable fix)

Keep all E5/E6 fixes. Add:

1. **Sentinel integration (Bug 1 fix):** replace r10's inline `run_kr_gen` collapse_score with a subprocess call to `kr_gen_sentinel.hexa`, using its exit code (2 = COLLAPSED) as authoritative. Keep inline as fallback only when hexa binary unavailable.
2. **Watchdog PID liveness (Bug 2 fix):** patch `runpod_watchdog.hexa` + `runpod_autopilot.hexa` watcher to gate `TRAINING` behind `kill -0 $PID`.
3. **Early-step collapse gate (Bug 3 fix):** add `if step <= 500 and loss < 1.0: force_run_kr_gen(step); abort if COLLAPSED` — sub-threshold loss triggers immediate sentinel regardless of `eval_every` cadence.
4. **Corpus diversity:** mix ≥15% kowiki into stripped_70b. Pure stripped is too narrow distributionally — encourages repeat-token local minima that appear as collapse.
5. **Seed sweep smoke:** before full 2000-step launch, run 200-step smokes at seeds `3407 / 42 / 1337` and accept only if all three PASS the sentinel; one collapsing → surface as data issue, not seed-specific luck.

Launch cost delta: +3 smokes × ~5 min = +15 min pre-launch. Savings: 3rd full-run OOM/collapse = ~13 min wasted + pod time; breakeven after first saved crash.

---

## 4. What the local session did NOT ship (scope / access limits)

- Pod-side patch application to `/tmp/_r10_train.py` — no SSH from local CLI session.
- `runpod_watchdog.hexa` kill-0 fix — stubbed here, implementation pending local write (file exists at `training/runpod_watchdog.hexa`, 7813 bytes).
- Full r10c launcher — sibling of `launch_alm_14b_r10.hexa`. Added as item `r10c_pending` in next-levers; awaiting user go.

---

## 5. Convergence auto-flow (I1) — what this session ossified

- New: `shared/convergence/alm_14b_r10.convergence` (E7-OSS-01/02/03)
- New: `shared/convergence/runpod_autopilot.convergence` (F1-OSS-01/02/03 + E7 gap)
- Updated: `shared/convergence/anima.json` items `r10_fresh_stripped`, `runpod_autopilot_f1`, `r10b_warm_start_spec`; `updated` bumped to 2026-04-18.
- New: `shared/harness/convergence_update.hexa` — read-only gap scanner (training/serving `*_report.md` vs `.convergence` coverage). Exit 2 on gaps.

Policy: `.convergence` files are never auto-written by the scanner (hallucinated-track risk). Human/Claude reviews scanner output, then writes the file by hand. This keeps SSOT integrity while automating gap *detection*.
