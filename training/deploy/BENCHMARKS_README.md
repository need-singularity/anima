# Benchmark Log Labeling Convention

**CRITICAL**: Do not conflate Claude baseline results with ALM-actual results.
This was a blocking issue in ALM v2.0 RC validation (2026-04-16) — the
"hire_sim 100% PASS" claim turned out to be Claude baseline, not ALM.

## Naming convention

- `hire_sim_claude_*.log` — **Claude API** evaluating Claude's own answers.
  Reference ceiling, not a training signal. **Do not cite as ALM gate result.**

- `hire_sim_real_eval_r9_*.log` — **ALM 14B r9** answering, evaluated by
  a fixed rubric. avg_score field is the ALM-actual number. Typical
  r9 range observed: avg 0.15–0.55 per task.

- `*_v2_*`, `*_v3_*`, `*_v4_*` — iterations of the eval script, NOT
  iterations of the model.

## Gate reporting rule

When declaring "gate PASS" for ALM:
1. Open `hire_sim_real_eval_r9_*.log` (ALM-actual).
2. Quote the `avg_score` from that log.
3. State threshold explicitly (e.g. "avg_score ≥ 0.85 required").
4. Never use `hire_sim_claude_*.log` numbers as ALM PASS evidence.

## v2.0 RC validation (2026-04-16)

Claim: hire_sim 100% PASS
Source: `hire_sim_claude_*.log` (Claude evaluating Claude, unrelated to ALM)
Actual ALM score: avg 0.15–0.55 per `hire_sim_real_eval_r9_*.log`
Verdict: **mislabeled — does NOT satisfy 85% threshold**

Next eval must cite the ALM log file explicitly.

## phi_holo parity

Related SSOT issue: `serving/serve_alm_14b.py` previously had
`phi_holo = spatial_var * eff_rank * 0.01` while
`training/train_clm_1b.py` uses MI-based formula (C41 sampling).
This caused a 6000x scale divergence (training claimed 6874, serve
observed 2.26). Fixed 2026-04-16 — both files now use the MI formula
with N-scaling. Absolute values will differ by batch (serve batch=1
vs training batch=8) but the definition is unified.
