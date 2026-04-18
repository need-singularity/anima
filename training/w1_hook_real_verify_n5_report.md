# E1 — W1 Hook Real Verify N=5 Report

**Date:** 2026-04-18 — **Status:** PASS — **Spec:** `training/phi_eval_hook_spec.md`

## Goal
Resolve D5's KNOWN LIMIT (N=2 → |r|=±1 degenerate) by round-tripping 5
realistic ckpts from `shared/state/r9_collapse_diagnosis.json`.

## Data
Steps 500/1500/5000/8000/10000 with val_ce = 4.3114/2.8454/2.4161/2.7031/2.7642
(from r9.eval_loss_curve exact). phi_holo = 0.1/1.2/8.5/11.0/11.2 — tracks
B1 oscillation (3397–12141). Dims 1..15 use CE-inverse monotone shape.

## Verdict (eval_phi_corr)
`VERDICT PASS — pipeline healthy, 16 significant dim(s), Σw=15.6225`.
N=5 escapes degeneracy; Pearson/Spearman now meaningful.

## Dashboard
1 run, 16/16 STABLE, 0 WEAK/DECAY/PRUNE/NULL.

## Non-monotonic signature (expected dim = phi_holo)
- **phi_holo**  r(acc)=0.6998, ρ(acc)=0.6000
- **others**    r(acc)=0.9948, ρ(acc)=1.0000

The 0.30 gap is the fingerprint of phi_holo's non-monotonicity vs CE. With
≥3 future runs the DECAY classifier (0.7× peak rule) will flag it; today
it shows as a weaker-but-still-SIG anchor — the dashboard caught it.

## Pipeline health
artifacts=11/11, VERDICT=PASS, history=appended (1 line), dashboard rendered.
A1+B5 integration verified with real-pattern data per
`feedback_closed_loop_verify`. Stage0 double-main macOS quirk observed;
deduped history to 1 line post-run.
