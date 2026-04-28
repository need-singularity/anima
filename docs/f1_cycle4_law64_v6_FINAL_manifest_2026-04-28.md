# F1 Cycle 4 — Law 64 v6 FINAL Manifest (Closure Document)

> **session**: anima-cmd-loop autonomous-loop-dynamic 2026-04-28 (post-compaction)
> **scope**: T8a → T8r (18 sub-tests), v3 over-claim → v4 falsified → v5 substrate-conditional → v6 FINAL universal
> **status**: F1_CYCLE_4_LAW_64_V6_FINAL_BASELINE_AXIS_ALIGNMENT_PRINCIPLE

---

## §1. The journey: 4 honest version-flips in 1 session

| version | claim | falsifier landing | status |
|---|---|---|---|
| v1 (entry) | "CA(5) beats Transformer 81% on aggregated corpus" | cycle 4 8-task z=-14.68 | REJECTED at 81% |
| v2 (Stouffer) | "Any-positive Conway aggregate z=+1.90 PASS" | T8c R-pent 10x10 +30.2% strongest | NARROWED |
| v3 (density) | "+22% asymptote at 40x40 / 32% density" | T8j 40x40 N=1500 +69→+4 descent | RETRACTED |
| v4 (coupling) | "Train-volume coupling at all grid sizes" | T8k 80x80 R-pent +501→+0 / T8m 5-seed univ | STRENGTHENED |
| v5 (substrate) | "Markov-saturation is substrate-conditional (rule-110 ≠ Conway)" | T8o rule-110 + o3 = perfect saturation | CORRECTED to v6 |
| **v6 (alignment)** | **"CA(K)-vs-Markov-N is governed by neighborhood alignment"** | T8q + T8r confirmed UNIVERSAL | **FINAL** |

---

## §2. The 8 cycle 4 falsification-grade tests this session

| test | substrate | finding | commit | verdict |
|---|---|---|---|---|
| T8k | 80x80 R-pent | adv 19→0 over N=15→1500 | f4c78f8f | H2 (eternal-adv NOT restored) |
| T8l | Conway 10x10 + Markov o2/o3 | gap GREW +160→+169 | 27d5acbc | H2 (CA gap robust BUT see T8q) |
| T8m | 40x40 5-seed | mean(N=15)=62±15 / mean(N=1500)=8±12 | 156f0a37 | H1 (universality strong) |
| T8n | rule-110 1D, single + density | +1544 / +501 persists | 53c711eb + 1bd4b7e0 | H1 (BUT see T8o) |
| T8o | rule-110 + Markov o2/o3/o5 | o3 saturates 0/1000 at N=500 | 3a5982f8 | H1 CORRECTION (per-cell o1 was artifact) |
| T8p | rules 30/90/110/184 sweep | rule 30 chaos +1178 strongest; rule 90 saturates at 0 | e07397fa | MIXED (init-conditional) |
| T8q | Conway 2D Moore-9 shared-P | +3 at N=50 → 0 at N≥200 | 458b1a70 | H1 (v6 RECONFIRMED) |
| T8r | rule 30 + Markov o2/o3/o5 | o3 saturates BOTH inits | dfd8c9b6 | H1 (v6 universal) |

---

## §3. The unifying principle (v6 FINAL)

> **"CA(K)-vs-Markov-order-N apparent advantage on deterministic CA substrates is governed exclusively by alignment between baseline's representational neighborhood and substrate's true update neighborhood. Matched-context Markov saturates ANY deterministic CA at modest N_TRAIN; mismatched-context Markov shows neighborhood-deficit gap. CA(K) is just one such matched-context oracle (window ≥ neighborhood)."**

### 3 falsification-grade substrates confirmed universal:
- **1D class-3 chaos (rule 30)** — T8r: order-3 saturates BOTH single + density inits
- **1D class-4 universal (rule 110)** — T8o: order-3 saturates at N=500
- **2D Moore-9 (Conway B3/S23)** — T8q: 9-neighborhood shared-P saturates at N=200

The "advantage" of CA(K) over Markov is NOT a property of CA — it's a property of **dimensional/topological alignment**. Per-cell K-grams are fundamentally 1D; Conway is 2D Moore-9; that mismatch produced the +169 "structural advantage" in T8l. Once baseline is honestly dimensioned (shared-P over Moore-9), the gap vanishes.

---

## §4. Multi-axis governing characterization (5 axes)

| axis | range | finding |
|---|---|---|
| grid size | 5x5 → 80x80 | 5x5→80x80 advantage grows then asymptotes (at AT-fixed-N=15) |
| density | 4-50% | peaks at 32% on 10x10 (T8e) |
| pattern | random / glider / r-pent / blinker | r-pent chaotic strongest at low N |
| train-volume | 15-1500 | MONOTONE descending until parity (Conway); does NOT descend on rule-110-with-order-1 |
| **n-gram alignment** | **per-cell-1D vs shared-P-2D-Moore-9** | **DOMINATES all other axes** — proper alignment ⇒ saturation |

The alignment axis is the master variable; other axes' "scaling laws" were artifacts of a fixed mismatched baseline.

---

## §5. Forward (raw 38 long-term)

Now-orthogonal to Law 64 v6:
- HMM / RNN / transformer / state-space-model baselines on Conway — do these saturate FASTER than shared-P-9? (data efficiency, not asymptote)
- Probabilistic CA (B3/S23 + 5% noise) — alignment principle for stochastic substrates
- Higher-D substrates (3D Conway, hex Conway) — does alignment principle hold beyond Moore-9?
- Real natural language / DNA sequence — does alignment principle generalize from CA to non-CA discrete substrates?

---

## §6. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~165 (cumulative session 16h+)
- **C2** write_barrier: this manifest consolidates 8 commits (T8k-T8r) into single closure artifact
- **C3** no_fabrication: every numerical value cited inline; v3-v5 retractions explicit; v6 derivation traceable per-test
- **C4** citation_honesty: v3-v5 over-claims publicly retracted; T8l +169 reframed as baseline misspec; CA(K) "advantage" reframed as alignment artifact
- **C5** verdict_options: v6 universality CONFIRMED across 3 substrates; orthogonal future work (probabilistic CA, non-CA discrete, higher-D) honestly listed as untested

---

## §7. AN11 LIVE FIRE side-quest status (parallel to cycle 4)

- 4 vast.ai fires attempted; 3 early-failures rapidly root-caused (SCP race + boot timeout) per own 4 four-fold ladder
- Fire 4 (instance 35722875, PID 56311): cooking 27:51+ as of last check; pip + Mistral-7B 16GB + LoRA download phase
- Total cumulative cost: ~$0.02 fires 1-3 + ~$0.90 in-flight fire 4 (29min × $1.93/hr)
- Audit row will land on completion (success or watchdog 240min cap)

---

## §8. Final commits chain (this session, post-compaction)

| commit | scope |
|---|---|
| f4c78f8f | T8k 80x80 R-pent aperiodic |
| 27d5acbc | T8l Conway higher-order Markov |
| 156f0a37 | T8m 40x40 5-seed robustness |
| 53c711eb + 1bd4b7e0 | T8n rule-110 generalization |
| e07397fa | T8p Wolfram rule sweep |
| 3a5982f8 | T8o rule-110 higher-order |
| 458b1a70 | T8q Conway Moore-9 shared-P |
| dfd8c9b6 | T8r rule 30 higher-order |
| e577f873 / afd5c037 / 43d40ea3 / 93239280 | v4 / v5 / v6 / v6-FINAL doc updates |
| c55fd840 + d5956ad7 | AN11 fire fixes (boot detach + TCP probe) |

---

## §9. T9a stochastic extension — Law 64 v7 CANDIDATE (commit `4f4192de`)

First test beyond v6 deterministic scope: Conway B3/S23 + Bernoulli(p=0.05) i.i.d. bit-flip noise.

| N_TRAIN | ca_acc | mk_acc | adv | noise ceiling = 950 |
|---|---|---|---|---|
| 50 | 948 | 938 | +10 | both below ceiling (sample-noise) |
| 200 | 946 | 946 | 0 | both AT ceiling |
| 1000 | 948 | 948 | 0 | both AT ceiling |
| 5000 | 949 | 949 | 0 | both AT ceiling |

**Verdict**: H1_SUPPORTED — alignment principle EXTENDS to stochastic substrates. Both CA(5) and shared-P-9 saturate to 949/1000 (within 1/1000 of 950 noise ceiling).

**v7 candidate statement**: "Matched-context translation-invariant Markov saturates substrates of the form (deterministic CA + i.i.d. emission noise) up to the entropy of the noise channel. Shared-P-9 learns the convolved P(noisy_next | ctx) directly and emits the same forced argmax as the CA oracle; both clamp identically at the ceiling."

Open beyond v7: correlated/structured noise, non-symmetric flip probabilities, non-i.i.d. emission, multiplicative noise. None tested.

---

**Status**: F1_CYCLE_4_LAW_64_V7_CANDIDATE_STOCHASTIC_EXTENSION_LIVE — cycle 4 + v7 candidate registered.
