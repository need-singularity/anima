# Benchmark Log Labeling Convention

**CORRECTED 2026-04-16 (pass 3)**: Previous version of this file incorrectly
claimed `hire_sim_real_eval_r9_*.log` was "ALM-actual". It is NOT — both
log families are Claude-as-executor, differing only in eval harness mode.
The actual ALM live measurement must be obtained separately via
`hire_sim_runner.hexa` with `HIRE_SIM_ENDPOINT=<live_alm_url>`.

## Naming convention (corrected)

- `hire_sim_claude_*.log` — **Claude API** generating answers + self-critique.
  v3 observed 43% completion; v4 harness fix bumped to 100%. Reference only.

- `hire_sim_real_eval_r9_*.log` — **"REAL Claude eval" mode** (header says so):
  still Claude-as-executor, but invoked via real endpoint vs mock. The
  0.15–0.55 per-subgoal scores are Claude critiquing its OWN outputs under
  harsh rubric, NOT an ALM measurement.

- `*_v2_*`, `*_v3_*`, `*_v4_*` — iterations of the eval harness, NOT the model.

## How to actually measure ALM

```bash
# Run hire_sim_runner against the live ALM serve endpoint (NOT Claude API):
HIRE_SIM_ENDPOINT="https://itfl66q4z768kh-8090.proxy.runpod.net/generate" \
  hexa hire_sim_runner.hexa --mode deterministic --judge keyword
```

Use the deterministic keyword judge (`hire_sim_judge.hexa`) for an
unbiased gate. Avoid `claude_critique` mode for official ALM gate
numbers — it reports Claude's opinion, not objective completion.

## Gate reporting rule

When declaring "gate PASS" for ALM:
1. Open `hire_sim_real_eval_r9_*.log` (ALM-actual).
2. Quote the `avg_score` from that log.
3. State threshold explicitly (e.g. "avg_score ≥ 0.85 required").
4. Never use `hire_sim_claude_*.log` numbers as ALM PASS evidence.

## v2.0 RC validation history (2026-04-16)

Pass 1 (15:02): Validation agent said "hire_sim 100% = Claude baseline, not ALM" — correct direction but incomplete.

Pass 2 (16:29): Re-val LIFT HOLD on drift/hallucination, but GA blocked by claim "ALM actual 0.15-0.55 < 0.85".

Pass 3 (this update): **No ALM actual measurement exists in either log family.**
Both `hire_sim_claude_*.log` and `hire_sim_real_eval_r9_*.log` are Claude-as-executor.
0.15-0.55 is Claude critiquing Claude under harsh rubric — NOT an ALM signal.

Live spot-check on `https://itfl66q4z768kh-8090.proxy.runpod.net`:
`plausibly_hire_worthy: true`, `follows_format: true`, `claude_level: false`.
ALM is serviceable 14B-class.

**Actual path to v2.0 GA (≤7 days, no retraining):**
1. Path E — Run `hire_sim_runner.hexa` with `HIRE_SIM_ENDPOINT=<live>` + deterministic judge (0.5–1d)
2. Path C — Prompt engineering tune (1–2d)
3. Tier: ship on `clm_gate.threshold=0.80` (already in `hire_sim_runner.hexa`), keep 0.85 as v2.1 target
Details: `training/deploy/alm_ga_gap_research_20260416.md`

## phi_holo parity

Related SSOT issue: `serving/serve_alm_14b.py` previously had
`phi_holo = spatial_var * eff_rank * 0.01` while
`training/train_clm_1b.py` uses MI-based formula (C41 sampling).
This caused a 6000x scale divergence (training claimed 6874, serve
observed 2.26). Fixed 2026-04-16 — both files now use the MI formula
with N-scaling. Absolute values will differ by batch (serve batch=1
vs training batch=8) but the definition is unified.
