# F1 Cycle 4 Closure — Law 64 v4 multi-dimensional coupling

> **predecessor**: `docs/f1_cycle4_law64_closure_v3_density_2026-04-28.md` (commit `27e38a7a`, v3 density-controlled)
> **this doc**: T8i (10x10 train-volume) + T8j (40x40 train-volume coupling) + Law 64 v4 statement
> **session**: autonomous-loop iter 21+ post-compaction
> **status**: eternal-advantage hypothesis FALSIFIED at tested scales — multi-dim coupling established

---

## §1. T8i — 10x10 train-volume sweep (commit `2e7c226f`)

| N_TRAIN | ca_acc | tf_acc | advantage_per_thousand | Δ |
|---|---|---|---|---|
| 15 | 1000 | 940 | +63 | — |
| 50 | 1000 | 990 | +10 | -53 |
| 150 | 1000 | 1000 | 0 | -10 |
| 500 | 1000 | 1000 | 0 | 0 ★ CONVERGED |
| 1500 | 1000 | 1000 | 0 | 0 |

**Verdict**: CONVERGED_TO_PARITY at N=500. Markov order-1 fully memorizes the small periodic orbit on 10x10/32%.

---

## §2. T8j — 40x40 train-volume coupling test (commit `8871288a`)

Pre-registered hypotheses (raw 12 frozen):
- **H1 (coupling structural)**: advantage > +50/1000 at ALL ticks → state space exceeds bigram capacity
- **H2 (uncoupled universal)**: advantage converges to 0 by N=1500 → Markov universal at any scale

| N_TRAIN | advantage_per_thousand | Δ |
|---|---|---|
| 15 | +69 | — |
| 50 | +29 | -40 |
| 150 | +23 | -6 |
| 500 | +21 | -2 |
| 1500 | +4 | -17 ★ broke convergence streak |

**Verdict**: AMBIGUOUS — neither H1 nor H2 cleanly satisfied.
- H1: 1/5 ticks > +50 (only N=15) — FAILED
- H2: final=4 ≠ 0; criterion never met — FAILED

**Pattern**: 40x40 advantage descends ~10x slower than 10x10 (10x10 hit parity at N=150; 40x40 still descending at N=1500), but DOES descend.

---

## §3. Law 64 v4 statement (FALSIFICATION-grade refinement)

### v3 (now retracted as over-claim)
> "CA(5) outperforms order-1 Markov on Conway substrate; +22% asymptote at 40x40 / 32% density"

### v4 (defensible after T8j)
> "CA(5)-vs-Markov-order-1 advantage on Conway is **INTRINSICALLY TRAIN-VOLUME-DEPENDENT** at every grid size tested. The advantage axis cannot be cleanly separated from the train-volume axis; H1 (structural eternal advantage) is **FALSIFIED** for 40x40/32%/seed=20260428. The v3 framing 'advantage CONVERGES at +22% on 40x40' must be qualified as 'ASYMPTOTE WITHIN A TRAIN-VOLUME WINDOW' — at fixed N_TRAIN=15."

### Open
- 80x80 / N_TRAIN=1500 / aperiodic init (R-pentomino chaotic) regimes — does eternal advantage restore?
- Markov order-2 / order-3 — does the gap survive higher-order n-gram baselines?

---

## §4. Multi-dimensional governing summary

Law 64 has now been measured along 4 axes:

| axis | tested range | finding |
|---|---|---|
| grid size | 5x5 → 80x80 | 5x5 → 80x80 advantage grows then asymptotes (+22% at 40x40+) AT N=15 |
| density | 4-50% | peaks at 32% density on 10x10 (T8e earlier) |
| pattern | random / glider / r-pent / blinker | r-pentomino chaotic strongest (+30.2% on 10x10 N=15) |
| **train-volume** | **15-1500** | **MONOTONE DESCENDING** (collapse @10x10 / slow descent @40x40) |

Train-volume axis is the FALSIFIER — only the first 3 axes were "scaling laws"; train-volume is the dual axis where Markov saturates. The 4 axes are COUPLED, not independent. Law 64 is no longer a monotone scaling law in any single dimension.

---

## §5. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~135 (cumulative session 16h+)
- **C2** write_barrier: this doc consolidates 2 commits (T8i 2e7c226f + T8j 8871288a) into Law 64 v4
- **C3** no_fabrication: every numerical value cited inline; no extrapolation beyond tested grid range
- **C4** citation_honesty: H1 falsification + v3-to-v4 retraction explicit; train-volume coupling caveat preserved
- **C5** verdict_options: dual-perspective (10x10 collapse-fast / 40x40 collapse-slow / 80x80 unknown) honestly enumerated

---

## §6. AN11 LIVE FIRE side-quest status

3 vast.ai fires attempted, all FAILED with progressive root-causing:

| fire | failure mode | fix landed |
|---|---|---|
| 02:35Z (35721749) | SCP race — sshd not listening | TCP probe NEEDED |
| 02:36Z (35721780) | SSH boot pip install timeout 120s | nohup bash -c detach (c55fd840) |
| 02:58Z (35722589) | SCP race AGAIN — boot fix correct but unreached | TCP probe added (d5956ad7) |

Total cost ~$0.02 across 3 instances (each <60s pod runtime). Per own 4 step (a)+(b)+(c)+(d), each iter produced a canonical helper code fix; no silent retries.

---

**Status**: F1_CYCLE_4_LAW_64_V4_MULTI_DIMENSIONAL_COUPLING_LIVE
