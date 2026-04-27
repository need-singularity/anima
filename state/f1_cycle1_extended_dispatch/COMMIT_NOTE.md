# F1 cycle 1 EXTENDED dispatch — commit attribution note

**Date**: 2026-04-28T08:50Z
**Per**: Agent 1 finding from sub-agent kick 2026-04-28T07:45Z
**Prior**: commit 150667a1 (F1 cycle 1 N=3) — same hook-race pattern recurred

## Intended vs actual commit attribution

Intended single commit:
- title: `feat(F1-cycle1-extended): phi_engine N=10 determinism + XMETA3 N=3 (torch-cpu) — RunPod blocker dissolved further`
- author hash: `a9fba6a6`

Actual reality (hook race during same session window):
- F1 dispatch artifacts (state/f1_cycle1_phi_engine_n10/* + state/f1_cycle1_xmeta3_n3/* + state/audit/anima_own_strengthen_audit.jsonl audit row) were SWEPT into the unrelated commit `2bdc3a8a` (`ledger(hxc-phase10-p2): A18 saving ω-cycle`) which fired 14 seconds before my explicit `git commit` call.
- My explicit commit `a9fba6a6` retained the F1-extended message but ended up committing only 2 unrelated files (`docs/hxc_deploy_d1_p2_batch_proposal_20260428.md` + `state/format_witness/2026-04-28_d1p1_canary_raw156_158.jsonl`) that were also caught in the same staging window.

This COMMIT_NOTE preserves the intended F1-extended commit message + file list for ledger/auditability — same mitigation pattern as 150667a1's `state/f1_cycle1_cpu_dispatch/COMMIT_NOTE.md`.

## Verified F1 cycle 1 EXTENDED outputs (in tree, committed via 2bdc3a8a)

### TASK A — phi_engine_eval N=10 cross-seed determinism
- Path: `state/f1_cycle1_phi_engine_n10/`
- 10 stdout captures (run_1.txt..run_10.txt) — all md5sum identical: `63e78b46556fbdc46f8546b1466d59a2`
- SUMMARY.json: phi_sum=6.88636 invariant across all 10 runs, wallclock_total=21.23s, mean=2.123s/run
- T5 BIT_EXACT_PASS — STRUCTURAL determinism (no RNG path; 12-engine registry-based selftest)
- Substrate: hexa-lang `/Users/ghost/core/hexa-lang/hexa run training/phi_engine_eval.hexa`

### TASK B — XMETA3 N=3 stochastic seed CPU dispatch
- Path: `state/f1_cycle1_xmeta3_n3/`
- Wrapper: `run_xmeta3_n3.py` (gitignored under state/, retained in working tree)
- results.json + run.log committed
- Seeds [42, 1337, 2718] × XMETA3 (256-cell mitosis + L1→L2→L3 metacognition + Phi-aware self-correction)
- Wallclock per seed: [379.44, 306.60, 190.19]s (total 876.23s)
- phi_final: [106.5339, 111.0709, 106.5238] mean=108.0429 range=4.5%
- final_cells=256 all seeds (max_cells reached)
- integration MI mean ~27.5k
- torch device CONFIRMED CPU (cuda False)
- LEGACY bench: `ready/bench/bench_phi_hypotheses_LEGACY.py:run_XMETA3_omega4_plus_metacog`

## raw 86 cost row (in audit ledger)

```
ts: 2026-04-28T08:48:48Z
action: f1_cycle1_extended_cpu_dispatch
cost_actual_usd: 0.0
vendor: local-cpu
substrate: Mac-CPU
task_a.wallclock_total_s: 21.230
task_b.wallclock_total_s: 876.23
combined verdict: substrate fully CPU-runnable
```

## raw 91 C3 honest disclosure

1. phi_engine N=10 determinism is STRUCTURAL — no RNG path, no seed input. Verifies
   substrate purity (hexa interpreter is bit-exact reproducible), NOT stochastic
   generalization across random seeds. To test stochastic generalization, the hexa
   evaluator would need a seeded RNG state input (not currently exposed).

2. XMETA3 N=3 stochastic seed variance is the REAL falsification test for the
   Python/torch path. 4.5% phi range (106.52..111.07) across 3 distinct seeds
   confirms the bench produces seed-sensitive outputs (i.e. it's actually running,
   not echoing constants), and CPU executability is confirmed.

3. Combined: F1 cycle 1 substrate is FULLY CPU-runnable for both:
   - hexa Phi evaluator (training/phi_engine_eval.hexa, 0 GPU refs)
   - Python XMETA3 mitosis bench (ready/bench/bench_phi_hypotheses_LEGACY.py, 0 .cuda() hard calls)

   RunPod 4-strike sustained fault is FURTHER DISSOLVED for this falsifier class.
   Blocker remains active for axis-105 Pilot-T1 + gemma-27b (separate scope).

## Wrapper-script gotcha (Mac CPU torch import + 72k-LoC LEGACY)

First run of `run_xmeta3_n3.py` was killed at 12 minutes with no stdout — root
cause: python stdout was block-buffered to pipe (tee). Re-ran with `python3 -u`
unbuffered + explicit `flush=True` on print calls; output then flowed correctly.
Total: ~14.5 min (12-min lossage + ~14.5 min successful re-run).

The 72k-line LEGACY bench file imports in ~12s on Mac (acceptable). Per-seed
XMETA3 wallclock varies 190..380s due to mitosis growth-trigger schedule
(early aggressive doubling under stochastic input).
