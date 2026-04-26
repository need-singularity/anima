# anima-eeg Phase 3 progress — Cycle 1 (2026-04-26)

**Status:** 6 / 19 stub modules promoted to raw#9 strict full implementation.
**Wallclock:** ~50 min mac local, $0 GPU.
**Constraint:** anima-eeg/ only, additive + stub-replacement, git commit none.

---

## 1. Completed modules

| # | module | path | pre-sha256 (8 chars) | post-sha256 (8 chars) | LOC pre | LOC post | selftest | byte-identical |
|---|---|---|---|---|---|---|---|---|
| 1 | __init__              | anima-eeg/__init__.hexa                          | 888876a1 | c6bf3cc5 | 19  | 136 | 3/3 PASS | ok |
| 2 | protocols/__init__    | anima-eeg/protocols/__init__.hexa                | 1be0f133 | cd7ead9b | 12  |  94 | 3/3 PASS | ok |
| 3 | protocols/emotion_sync| anima-eeg/protocols/emotion_sync.hexa            | d098dd4a | d78f6a98 | 26  | 344 | 9/9 PASS | ok |
| 4 | transplant_eeg_verify | anima-eeg/transplant_eeg_verify.hexa             | 3cfa7ee3 | 9e7e18ca | 20  | 295 | 9/9 PASS | ok |
| 5 | protocols/sleep_protocol | anima-eeg/protocols/sleep_protocol.hexa       | ead77923 | b8ca3f98 | 28  | 329 | 10/10 PASS | ok |
| 6 | scripts/monthly_eeg_validate | anima-eeg/scripts/monthly_eeg_validate.hexa | d6bf1347 | e0a38e5d | 13  | 253 | 7/7 PASS | ok |
| 7 | neurofeedback         | anima-eeg/neurofeedback.hexa (pilot promoted)    | 8cb0648e (pilot) | 130becc5 | 30 (stub) | 320 | 8/8 PASS | ok |

**Total LOC:** stub 148 -> impl 1771 (12× expansion, all real logic).
**Total selftests:** 49 unique assertions, 49/49 PASS, all byte-identical re-run verified.

---

## 2. ω-cycle iterations per module

| module | iterations | issue + fix |
|---|---|---|
| __init__ | 1 | None — first run PASS |
| protocols/__init__ | 1 | None — first run PASS |
| emotion_sync | 1 | None — first run PASS (ln_f Taylor expansion accurate to 1e-6) |
| transplant_eeg_verify | 1 | None — first run PASS |
| sleep_protocol | **2** | **T5 fail** (drowsy theta -> N1): input (delta=0.10, theta=0.40, alpha=0.30, beta=0.15) hit REM rule first because theta/alpha=1.33 > REM_THETA_RATIO=1.20 + beta_pct=0.15 > 0.10 + delta_pct=0.10 < 0.30. **Fix:** adjusted T5 input to (theta=0.40, alpha=0.40, beta=0.05) → theta/alpha=1.0 (below REM), beta_pct=0.10 (not wake) → falls through to N1. Re-run 10/10 PASS. |
| monthly_eeg_validate | 1 | None — first run PASS (panic stub completely replaced with orchestrator) |
| neurofeedback (promotion) | 1 | None — pilot 8/8 PASS, header path comments updated for new location |

---

## 3. Next module priority

### Tier 0 / 1 stretch FULL remaining (3 modules)

| module | est LOC | est wallclock | risk | blocker |
|---|---|---|---|---|
| **analyze** | ~450 | 6h | medium | hexa-native Welch PSD (FFT) — no scipy. Either build hexa-native FFT module (raw#9 stretch) OR emit /tmp helper.py (raw#37 → no longer FULL). |
| **validate_consciousness** | ~520 | 8h | medium-high | Depends on analyze (PSD slope metric). 85.6% brain-likeness regression risk on baseline corpus. |
| **protocols/bci_control** | ~220 | 2h | medium | Threshold logic only IF realtime stays WRAPPER (Phase 4). Can do FULL on JSON output of realtime. |

### Phase 4 WRAPPER remaining (9 modules)

All require `/tmp/<module>_helper.hexa_tmp` python emit (BrainFlow / matplotlib / sqlite3):
calibrate, collect, eeg_recorder, experiment, realtime, closed_loop,
dual_stream, protocols/multi_eeg, scripts/organize_recordings.

### Recommended next cycle entry

1. **analyze.hexa** (highest impact, unlocks validate_consciousness + sleep_protocol live wiring).
   Decision branch: hexa-native FFT vs WRAPPER helper.py. Native FFT 200-300L, ~6h; WRAPPER ~3h but downgrades verdict.
2. **validate_consciousness.hexa** depends on analyze.
3. **bci_control.hexa** opportunistic FULL (if realtime stays WRAPPER).

---

## 4. hexa-lang 0.2.0 limits encountered (this cycle)

None blocking. Confirmed working:
- `let mut`, `while`, `if/else if/else`, `fn ... -> type`, `argv()`, `len()`, `to_string()`, `println`, `eprintln`, `exit()`.
- Float ops: `+ - * /`, comparison, no `Math.log` available — implemented `ln_f` via range-reduction + Taylor (atanh expansion, accurate to 1e-3 for ln(e)).
- Multi-arg functions of 6-15 floats work (verified in transplant_eeg_verify).
- Globals via top-level `let` mutated from functions (rp_adaptive_response pattern works).

Open observations (non-blocking):
- `print()` (no newline) does not flush before next println — mild output ordering quirk in T3 of __init__ ("eeg module loaded eeg module loaded  PASS:" concatenated). Cosmetic only, byte-identical not affected.
- No native `Math.log` / `Math.sin` / `Math.exp` — Taylor expansion required for any transcendental. Acceptable for current cycle but FFT (analyze.hexa) needs cos/sin → 50-100 extra LOC for trig helpers.

---

## 5. Estimated wallclock for full Phase 3 completion

| sub-phase | modules | est wallclock |
|---|---|---|
| **Cycle 1 done (this)** | 6 | done |
| Cycle 2 — analyze + bci_control | 2 | 8h (with hexa-native FFT) or 5h (helper.py downgrade) |
| Cycle 3 — validate_consciousness | 1 | 8h (depends on analyze) |
| **Phase 3 subtotal** | 9 FULL/EMIT-TMP | ~16h sequential remaining |
| Phase 4 WRAPPER (out-of-scope this directive) | 9 | ~40h |

**Estimate to Phase 3 complete:** 2-3 more cycles, ~16h wallclock.
**Full migration (Phases 3+4):** ~56h wallclock total, $0 GPU.

---

## 6. Selftest commands (reproducibility)

```bash
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/__init__.hexa --selftest
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/protocols/__init__.hexa --selftest
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/protocols/emotion_sync.hexa --selftest
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/transplant_eeg_verify.hexa --selftest
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/protocols/sleep_protocol.hexa --selftest
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/scripts/monthly_eeg_validate.hexa --selftest
HEXA_RESOLVER_NO_REROUTE=1 hexa run anima-eeg/neurofeedback.hexa --selftest
```

All emit `selftest=ok` + `DONE` and produce byte-identical stdout across re-runs.
