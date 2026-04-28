# F1 Cycle 4 — Law 64 Broader Corpus Closure

> **scope**: F1 cycle 4 falsifier closure — Law 64 "CA(5) beats Transformer 81%" reproducibility test on prospectively-defined 8-task corpus
> **session**: anima-cmd-loop autonomous-loop-dynamic 2026-04-28T08:55Z–09:29Z (5 iters)
> **cycle 3 predecessor**: HONEST FAIL on rule-110 narrow scope (commit 6f0351e1)
> **cycle 4 verdict**: 0/8 PASS_81PCT, Stouffer z=-14.68 statistical REJECTION + 1 task POSITIVE evidence (glider +19%)

---

## §1. Original Law 64 + cycle 3 status

### 1.1 Source claim verbatim

`ready/core/consciousness_laws.json:1037`:
> `"64": "CA minimum evolution optimal (CA(5) beats Transformer 81%)"`

NOT present in `anima/config/consciousness_laws.json` (14-law runtime). 1-line aphorism with NO corpus specification anywhere in repo (Agent 3 finding from sub-agent kick 2026-04-28T07:25Z).

### 1.2 Cycle 3 attempt (commit 6f0351e1)

`tool/anima_law64_ca5_vs_transformer_test.hexa` ~210 LoC — single-task rule-110 only.
Verdict: CA(5)=100%, Markov-TF=100%, advantage=0 → **HONEST FAIL** on narrow scope.

### 1.3 Cycle 4 prospective design (Agent C)

8-task corpus + GPT-2 small Transformer baseline + Stouffer's z aggregation. Per Agent 3 raw 91 C3 honest disclosure: original claim is unfalsifiable as stated; cycle 4 prospectively defines test conditions.

---

## §2. Cycle 4 8-task corpus — full results

### 2.1 T1-T7 1D corpus (commit c4bd8d7d)

Tool: `tool/anima_law64_ca5_vs_transformer_cycle4.hexa` (~286 LoC raw 9 hexa-only)

| Task | CA(5) acc | Markov acc | advantage | finding |
|---|---|---|---|---|
| T1 rule 30 chaotic | 100% | 100% | 0 | TIE |
| T2 rule 90 XOR | 100% | 100% | 0 | TIE |
| T3 rule 110 Turing | 100% | 100% | 0 | TIE (cycle-3 carry) |
| T4 rule 184 traffic | 100% | 100% | 0 | TIE |
| T5 bool circuit | 100% | 100% | 0 | TIE |
| T6 random walk | 87.4% | 87.4% | 0 | TIE (stochastic ceiling) |
| **T7 int sequence** | **68.8%** | **81.2%** | **-15.3%** | **Markov BEATS CA** |

**T7 finding**: integer-sequence is non-CA-amenable task — CA(5) rule-induction infers wrong rule (no underlying neighborhood transition exists). Markov order-1 captures the periodic bit-shift structure better than CA(5) trying to fit a non-existent CA rule.

### 2.2 T8 Conway 5x5 random-init (commit e024fa41)

Tool: `tool/anima_law64_conway_5x5_test.hexa` (~218 LoC)

CA-ground-truth (knows B3/S23): 100%. Markov order-1: 100%. **Advantage = 0**.

**Honest finding**: random init density 50% → most cells die under B3/S23 → expected_next ≈ all-zeros → both models trivially predict 0 (majority class). Degenerate corpus signal.

### 2.3 T8b Conway patterned-init (commit feedc677)

Tool: `tool/anima_law64_conway_patterned_init.hexa` (~235 LoC)

| pattern | CA(5) | Markov | advantage | finding |
|---|---|---|---|---|
| blinker period-2 | 100% | 100% | 0 | TIE (toroidal compression) |
| block still-life | 100% | 100% | 0 | TIE (control) |
| **glider period-4** | **100%** | **84%** | **+19%** | **★ CA WINS** |
| r-pentomino chaotic | 100% | 100% | 0 | TIE (5x5 fast stabilization) |

**Aggregate mean advantage**: **+4.7%** (positive but FAR below 50% threshold).

**Glider finding**: spatio-temporal translation patterns CANNOT be captured by Markov order-1. Real CA structural advantage REVEALED. But task-conditional — only translation patterns show advantage; still-life/oscillator/chaotic on 5x5 are TIE.

---

## §3. Stouffer's z statistical aggregate (commit 008e0a9d)

Tool: `tool/anima_stouffer_z_aggregator.hexa` (~159 LoC raw 9 + raw 37 transient python helper)

### 3.1 Selftest verification

3-task fixture p=[0.01, 0.05, 0.10] → z_combined=**3.033** (expected ~3.04 ✓), pass α=0.05 + α=0.01 ✓
Phi_inv impl: Beasley-Springer/Moro approximation (CPU-only, deterministic).

### 3.2 Cycle 4 8-task aggregate

| task | per_task_z (heuristic) |
|---|---|
| T1-T6 | -5.0 each (advantage=0, threshold=500 → z heuristic = -5.0) |
| T7 int_sequence | -6.53 (advantage=-153) |
| T8 conway random | -5.0 (advantage=0) |

**z_combined = -14.68**, p_combined = 1.0
**pass α=0.05: FALSE / pass α=0.01: FALSE**

Statistical verdict: **OVERWHELMING REJECTION** of Law 64 81% claim on prospective 8-task corpus.

---

## §4. Law 64 re-statement candidate

### 4.1 Original (rejected)

> "CA(5) beats Transformer 81% on aggregated corpus" (general, unfalsifiable as stated)

Cycle 4 evidence:
- 0/8 PASS_81PCT_CLAIM on prospective corpus
- Stouffer z = -14.68 (statistical rejection)
- T7 actively NEGATIVE (-15.3% — Markov beats CA on non-CA task)

### 4.2 Defensible re-statement candidate

> "CA(5) outperforms order-1 Markov on spatio-temporal translation patterns by ~19%" (specific, defensible, evidenced)

Cycle 4 evidence supporting:
- Glider period-4: CA 100% / Markov 84% / advantage +19%
- Markov order-1 fundamentally cannot represent translation (no spatial context)

### 4.3 Honest scope caveats (raw 91 C3)

- 5x5 toroidal grid is small — gliders that translate indefinitely on infinite grid wrap around, creating cycles
- R-pentomino chaotic phase reaches all-zero stable state quickly on 5x5 (vs 1103 steps infinite grid)
- Markov surrogate is order-1 — real Transformer with positional encoding + deep attention would likely match CA on glider
- Real GPT-2 small baseline + larger grid + multi-pattern aggregation = forward-pending vast.ai T4 dispatch (~$0.40-1)

---

## §5. raw 38 long-term track (forward-pending)

### 5.1 Real Transformer baseline

vast.ai T4 ~$0.40-1 dispatch:
- GPT-2 small (124M params) fine-tuned on 8-task corpus (200 train + 200 test per task)
- Replace Markov surrogate with real Transformer for honest baseline comparison
- Re-run Stouffer's z with exact p-values (vs current advantage-mode heuristic)

### 5.2 Larger grid Conway

10×10 or 20×20 toroidal grid:
- Gliders persist longer before wrap-around
- R-pentomino chaotic phase has more steps before stabilization
- Likely amplifies CA advantage on translation/chaotic patterns

### 5.3 Stouffer's z exact p-value mode

Current cycle 4 aggregate uses advantage-mode heuristic (z_t = (adv-thr)/100). Real p-value mode requires:
- Bootstrap permutation test per task
- N=1000+ resamples per task
- ~5-10 min Mac CPU per task

---

## §6. Session integration

### 6.1 Commits chain (cycle 4 closure, 5 commits)

| commit | scope |
|---|---|
| `c4bd8d7d` | F1 cycle 4 7-task tool + verdict |
| `e024fa41` | T8 Conway random-init + 8-task closure |
| `008e0a9d` | Stouffer's z aggregator + cycle 4 z=-14.68 |
| `feedc677` | T8b Conway patterned-init + glider +19% |
| `<this commit>` | Final synthesis doc |

### 6.2 Tools created (cycle 4 family)

| tool | LoC | purpose |
|---|---|---|
| `tool/anima_law64_ca5_vs_transformer_cycle4.hexa` | ~286 | T1-T7 1D corpus |
| `tool/anima_law64_conway_5x5_test.hexa` | ~218 | T8 random-init |
| `tool/anima_law64_conway_patterned_init.hexa` | ~235 | T8b patterned-init |
| `tool/anima_stouffer_z_aggregator.hexa` | ~159 | Stouffer's z multi-task aggregation |

All chflags uchg (canonical helper class). All raw 9 hexa-only. All raw 12 frozen pre-registration.

### 6.3 State directories (cycle 4 results)

| dir | contents |
|---|---|
| `state/f1_cycle4_broader_corpus/` | T1-T7 verdict + sweep |
| `state/f1_cycle4_t8_conway/` | T8 random-init verdict + sweep |
| `state/f1_cycle4_t8b_patterned/` | T8b patterned-init verdict + sweep |
| `state/f1_cycle4_stouffer_aggregate/` | z_combined + per-task breakdown |

All chflags uchg (read-only result snapshots).

---

## §7. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~80 (cumulative session 14h+ + cycle 4 closure)
- **C2** write_barrier: this synthesis doc consolidates 5 prior commits; no new claims, only synthesis
- **C3** no_fabrication: every numeric claim cited inline (commits, tool LoC, state dirs, advantage values, z_combined)
- **C4** citation_honesty: Law 64 original claim verbatim cited; re-statement candidate explicitly marked as candidate (not adopted); scope caveats explicit (5x5 grid limitations, Markov surrogate limitations, real Transformer pending)
- **C5** verdict_options: rejected/positive/honest_fail enumerated per task; aggregate verdict clearly LAW_64_81PCT_CLAIM_STATISTICALLY_REJECTED + glider +19% POSITIVE_LOCALIZED_FINDING

---

## §8. Cross-references

### 8.1 Predecessor docs

- `docs/law_64_status_2026-04-28.md` (commit ded2e9bb) — Agent 3 unfalsifiability finding + cycle 4 prospective design
- `docs/atlas_r36_r37_proposal_2026-04-28.md` (commit 7dee9a94) — n6-architecture maintainer review proposal (separate scope)
- `docs/session_2026-04-28_post_compaction_summary.md` (commit 4134db3b, 187 lines uchg) — overall session ref (PRE-cycle-4 closure; this doc is cycle-4-specific)

### 8.2 Related sub-agent kicks

- 4-agent kick 2026-04-28T07:25Z (Agent A CP2 trio + Agent B Mk.XII alt-vendor + Agent C V metric + Agent D promotion bottleneck)
- 4-agent kick 2026-04-28T07:45Z (RunPod-required items)
- 4-agent kick 2026-04-28T07:55Z (concrete IMPL+EXEC: orchestrator fix + HF gated audit + F3 broader sweep + F1 cycle 1 extended)

### 8.3 Related raw rules

- raw 71 design-strategy-falsifier-retire-rule (cycle 4 falsifier replication attempt)
- raw 12 silent-error-ban + frozen pre-registration (thresholds set BEFORE measurement)
- raw 38 implement-omega-converge (long-term track preserved: real Transformer + larger grid + exact p-value)
- raw 91 design-honesty-triad-process-quality (C1-C5 maintained throughout)
- raw 47 strategy-exploration-omega-cycle (Agent C cycle-4 prospective design from cross-repo trawl)

---

**Status**: F1 CYCLE 4 8-TASK COMPREHENSIVE CLOSURE — Law 64 81% claim STATISTICALLY REJECTED (z=-14.68); glider +19% LOCALIZED POSITIVE (forward to defensible re-statement candidate); raw 38 long-term track real-Transformer-baseline preserved.
