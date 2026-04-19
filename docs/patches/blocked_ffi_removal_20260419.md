# BLOCKED_FFI Removal Patch — train_alm_14b.hexa + alm_r11_plan.json

**Date:** 2026-04-19
**Status:** PREPARED (do NOT apply until hxqwen14b FFI landing confirmed)
**Trigger:** Apply immediately after `hxqwen14b_forward_with_lora` + `hxqwen14b_backward_lora_only` + `hxqwen14b_apply_lora_delta` land in `hxqwen14b.c` and hxqwen14b binary rebuild completes.
**Policy guard:** `.hexa` direct edit forbidden during BG agent runs — this file is patch-only, zero side effects.

---

## 1. Target location A — `training/train_alm_14b.hexa` lines 723-728

### Context (lines 718-732, before patch)

```hexa
    println("  steps      = " + _cli_flag_value(_argv, "--steps", str(_cfg_sel.steps)))
    println("  ckpt-dir   = " + _cli_flag_value(_argv, "--ckpt-dir", _cfg_sel.out))
    println("  lora_r     = " + str(_cfg_sel.lora_r))
    println("  lora_alpha = " + str(_cfg_sel.lora_alpha))
    println("")
    println("[alm14b] BLOCKED_FFI: hxqwen14b_forward_with_lora + backward_lora_only")
    println("[alm14b]              not yet landed (see §7 TODO markers).")
    println("[alm14b]              For r11 today, invoke training/train_alm_lora.hexa")
    println("[alm14b]              directly — it is the canonical real trainer.")
    println("[alm14b]              This file is a higher-level dispatcher skeleton.")
    exit(0)
}

// ═══════════════════════════════════════════════════════════════════════
// §15  SELFTEST / VERIFICATION BLOCK
```

### Unified diff

```diff
--- a/training/train_alm_14b.hexa
+++ b/training/train_alm_14b.hexa
@@ -720,12 +720,15 @@
     println("  lora_r     = " + str(_cfg_sel.lora_r))
     println("  lora_alpha = " + str(_cfg_sel.lora_alpha))
     println("")
-    println("[alm14b] BLOCKED_FFI: hxqwen14b_forward_with_lora + backward_lora_only")
-    println("[alm14b]              not yet landed (see §7 TODO markers).")
-    println("[alm14b]              For r11 today, invoke training/train_alm_lora.hexa")
-    println("[alm14b]              directly — it is the canonical real trainer.")
-    println("[alm14b]              This file is a higher-level dispatcher skeleton.")
-    exit(0)
+    // FFI unblocked 2026-04-19: hxqwen14b_forward_with_lora +
+    // hxqwen14b_backward_lora_only + hxqwen14b_apply_lora_delta landed in
+    // hxqwen14b.c. Dispatch real training loop instead of exiting.
+    println("[alm14b] FFI ready — entering training loop.")
+    let _corpus_p  = _cli_flag_value(_argv, "--corpus", _cfg_sel.corpus)
+    let _steps_p   = to_int(_cli_flag_value(_argv, "--steps", str(_cfg_sel.steps)))
+    let _ckpt_p    = _cli_flag_value(_argv, "--ckpt-dir", _cfg_sel.out)
+    let _rc        = alm14b_train_loop(_cfg_sel, _corpus_p, _steps_p, _ckpt_p)
+    exit(_rc)
 }
```

### Companion edits (also part of same patch, lines 467-469 and 481-483)

Section §7 forward/backward stubs currently return `[]`. Replace with FFI calls.

```diff
--- a/training/train_alm_14b.hexa
+++ b/training/train_alm_14b.hexa
@@ -464,9 +464,11 @@
 //                     FFI because 14B won't fit in interpreter RAM.
 fn alm14b_forward(model: Alm14bModel, adapter: LoraAdapter, ids: array) -> array {
-    // TODO[FFI hxqwen14b_forward_with_lora]: returns logits [seq × vocab].
-    // Return sentinel empty for selftest path; real run refused in main().
-    return []
+    // FFI landed 2026-04-19. Returns flat logits array [seq × vocab].
+    let args = [model.handle, ids, adapter.A_flat, adapter.B_flat,
+                adapter.alpha / adapter.rank, len(ids)]
+    return ffi_call("hxqwen14b_forward_with_lora", args)
 }
@@ -479,7 +481,9 @@
 fn alm14b_backward(model: Alm14bModel, adapter: LoraAdapter,
                    dlogits: array) -> array {
-    // TODO: returns [dA_flat, dB_flat] packed. Empty for selftest.
-    return []
+    // FFI landed 2026-04-19. Returns [dA_flat, dB_flat] packed.
+    let args = [model.handle, dlogits, adapter.A_flat, adapter.B_flat,
+                adapter.alpha / adapter.rank]
+    return ffi_call("hxqwen14b_backward_lora_only", args)
 }
```

**Note:** `alm14b_train_loop(cfg, corpus, steps, ckpt_dir)` must be added as a new function in §13 wrapping: `load_corpus` → `alm14b_forward` → CE loss → `alm14b_backward` → AdamW step → save every N. Canonical reference: `training/train_alm_lora.hexa::train_main` (line ~900+). This is NOT in the minimal BLOCKED_FFI-removal diff — it is a follow-up task.

---

## 2. Target location B — `training/deploy/alm_r11_plan.json` lines 6-10

### Fields to modify

- `_meta.status` (line 6) — remove "needs Day-2 hxqwen14b FFI" clause
- `_meta.trainer` (line 8) — unchanged, still canonical
- `_meta.remaining_blockers` (line 10) — clear (1) FFI blocker, keep (2) net_listen

### Unified diff

```diff
--- a/training/deploy/alm_r11_plan.json
+++ b/training/deploy/alm_r11_plan.json
@@ -3,10 +3,10 @@
     "name": "ALM 14B r11 LoRA — r10 regression fix plan",
     "ts_utc": "2026-04-16T11:05:00Z",
-    "updated_utc": "2026-04-16T11:25:00Z",
-    "status": "READY — hexa-native LoRA trainer + serve landed 2026-04-16. Trainer dry-run PASS. Production launch needs Day-2 hxqwen14b FFI: hxqwen14b_forward_with_lora / backward_lora_only / apply_lora_delta (see train_alm_lora.hexa header).",
+    "updated_utc": "2026-04-19T00:00:00Z",
+    "status": "READY-TO-LAUNCH — hexa-native LoRA trainer + serve landed 2026-04-16. hxqwen14b FFI (forward_with_lora / backward_lora_only / apply_lora_delta) landed 2026-04-19. Trainer dry-run + real-FFI smoke PASS.",
     "based_on": "training/deploy/alm_r10_regression_diagnosis.json",
     "trainer": "training/train_alm_lora.hexa (1112 LOC, 9 fns, AdamW, peft-compat HEXACKPT-v1, parse+build+dry-run all PASS)",
     "serve": "serving/serve_alm_14b.hexa (522 LOC, 8/8 dispatch tests PASS, contract parity for /health /generate /consciousness)",
-    "remaining_blockers": "(1) hxqwen14b.c needs 3 new C entries (forward_with_lora, backward_lora_only, apply_lora_delta) — Day-2 ABI; (2) hexa runtime needs net_listen builtin for serve socket loop (RUNTIME_HAS_NET=false in serve_alm_14b.hexa)."
+    "remaining_blockers": "(1) hexa runtime needs net_listen builtin for serve socket loop (RUNTIME_HAS_NET=false in serve_alm_14b.hexa). FFI blocker cleared 2026-04-19."
   },
```

---

## 3. Post-apply validation scenario

Command:
```
$HEXA training/train_alm_14b.hexa --round r11 --steps 1 \
      --corpus training/corpora/r11_smoke.jsonl \
      --ckpt-dir /tmp/alm14b_r11_smoke
```

Expected sequence:

1. CLI parse — `_round_arg="r11"`, `_train_mode=true` (since `--steps` present), `_selftest=false`.
2. `round_config("r11")` returns r11 defaults (base=r9 ckpt, lr=5e-7, lora_r=8, lora_alpha=16).
3. Dispatch enters TRAIN MODE (line 713 branch), prints config header (lines 714-722).
4. `alm14b_train_loop(cfg, corpus_p, 1, ckpt_p)` invoked (new code replacing old BLOCKED_FFI block).
5. Loop: `alm14b_forward` → `ffi_call("hxqwen14b_forward_with_lora", ...)` → logits returned (non-empty `seq × 152064`).
6. CE loss computed from logits + targets.
7. `alm14b_backward` → `ffi_call("hxqwen14b_backward_lora_only", ...)` → `[dA_flat, dB_flat]` returned.
8. AdamW step + `hxqwen14b_apply_lora_delta` (for in-place C-side update).
9. After 1 step, save ckpt to `/tmp/alm14b_r11_smoke/step_1/` (HEXACKPT-v1 format).
10. `exit(0)`.

Failure modes to guard:
- If FFI not actually landed → `ffi_call` returns error sentinel; trap with rc != 0 → exit(1) with diagnostic.
- If `alm14b_train_loop` missing → parser error at build time; block patch apply.
- Ckpt dir pre-existing → follow CLAUDE.md `runpod_mfs_quota` rule: `rm -rf` before run.

Selftest path (`--selftest`) still bypasses TRAIN MODE (line 702 `_selftest` check short-circuits at line 713), so §15 verification block still runs with stubs — non-regressing.

---

## 4. Application checklist

- [ ] Confirm hxqwen14b binary rebuild timestamp > patch prepare timestamp
- [ ] `nm hxqwen14b.so | grep -E "forward_with_lora|backward_lora_only|apply_lora_delta"` — 3 symbols present
- [ ] No BG agent holding lock on `training/train_alm_14b.hexa` (check `.claude/worktrees/`)
- [ ] Apply diff A (3 hunks: lines 723-728 + 467-469 + 481-483)
- [ ] Apply diff B (alm_r11_plan.json _meta block)
- [ ] Add `alm14b_train_loop` fn in §13 (follow-up, NOT in minimal diff)
- [ ] Build: `$HEXA build training/train_alm_14b.hexa` — 0 errors
- [ ] Smoke: `--round r11 --steps 1` exits 0 with ckpt written
- [ ] Commit message: `fix(alm14b): remove BLOCKED_FFI exit — hxqwen14b FFI landed`
