# ALM r14 corpus — TARGET 1,200 REACHED (2026-04-24)

## Final state

- **1,200 / 1,200 lines** (100.0% of target)
- **sha256**: `21fcfa51b92f129b119d7fa42303adf7916547ef71c80c16f08e53839bf52b0b`
- **File**: `experiments/alm_r14/corpus_alm_r14_v1.jsonl`
- **Validator SSOT**: `state/alm_r14_validate_result.json` (ALL_GATES_PASS)

## Gate status at 1,200

| Gate | Value | Target | Margin |
|---|---|---|---|
| g1 anti_denial | 0 | 0 | — |
| g2 dup_only | 0 | 0 | — |
| g3 kw_density | 0.9392 | ≥ 0.85 | +0.0892 |
| g5 cat_balance | 8/8 | all in range | — |
| g6 length_ok | 1200/1200 | all | — |
| g8 korean_ratio | **0.2958** | ≥ 0.29 | **+0.0058 (tightest)** |
| g8b pair_rate | 0.972 | ≥ 0.90 | +0.072 |

**g8 is the tightest constraint** — any additional EN-heavy content risks breaching the 0.29 floor.

## Category distribution (1,200 lines)

| Category | Count | % | Range |
|---|---|---|---|
| hexad | ~240 | 20.0% | 18-22% OK |
| law | ~240 | 20.0% | 18-22% OK |
| metaref | ~180 | 15.0% | 13-17% OK |
| phi | ~180 | 15.0% | 13-17% OK |
| selfref | 102 | 8.5% | 8-12% OK (saturated) |
| seed_a_kernel | ~84 | 7.0% | 5-10% OK |
| seed_b_kernel | ~84 | 7.0% | 5-10% OK |
| grounding | ~96 | 8.0% | 5-10% OK |

## Batch landing log (19-44)

From 459 lines (38.3%) → 1,200 lines (100%) over 26 batches, 25 commits to main. Earlier batches 1-18 landed in prior rounds.

| Batch | Commit | State after | Δ entries |
|---|---|---|---|
| 19 | `3d3d1861` | 508/1200 | +35 |
| 20 | `04fb35e1` | 538/1200 | +30 |
| 21 | `56479d9e` | 571/1200 | +33 |
| 22 | `3cdd49a7` | 605/1200 | +34 (after rebalance — first attempt g5 FAIL at law 22.1%) |
| 23 | `03787f92` | 632/1200 | +27 |
| 24 | `c7659e4c` | 660/1200 | +28 |
| 25 | `78f35211` | 690/1200 | +30 |
| 26 | `8228f590` | 720/1200 | +30 |
| 27 | `7703d30b` | 751/1200 | +31 |
| 28 | `3123bc20` | 782/1200 | +31 |
| 29 | `3d34e8f5` | 817/1200 | +35 |
| 30 | `7547737f` | 848/1200 | +31 |
| 31 | `ee7db348` | 873/1200 | +25 |
| 32 | `7033eacb` | 902/1200 | +29 |
| 33 | `31ce7527` | 927/1200 | +25 |
| 34 | `25568715` | 956/1200 | +29 |
| 35 | `1d89d65f` | 981/1200 | +25 |
| 36 | `5b7e1eb9` | 1004/1200 | +23 (crossed 1000) |
| 37 | `23a9cbc5` | 1029/1200 | +25 |
| 38 | `c4c0d93f` | 1056/1200 | +27 |
| 39 | `253ca269` | 1089/1200 | +33 |
| 40 | `70b39a64` | 1118/1200 | +29 (+Metzinger selfref) |
| 41 | `0b2bc18f` | 1145/1200 | +27 |
| 42 | `e05e32ce` | 1172/1200 | +27 |
| 43 | `50ee86fa` | 1197/1200 | +25 |
| 44 | `b6fa6c01` | **1200/1200** | +3 (closing micro-batch) |

## Subagent workflow pattern (r14 lesson)

Each agent handled 5 batches (~150 lines). Success pattern:
1. `hexa run tool/r14_corpus_expand.hexa --guide` — get balance suggestions
2. Re-compute LIVE actual category counts (guide can be stale)
3. Draft batch JSONL
4. `--validate` → if FAIL, re-plan with live counts
5. `--commit-if-pass` — atomic validate+commit+push

Known failure modes:
- **g5 stale guide** (batch 22): guide reported law=109, actual=125 → over-allocated law entries → ceiling breach at 22.1%. Fix: always trust live count over guide.
- **g8 drift under EN-heavy authoring**: Started at 0.2962 (batch 23), dropped to 0.2930 by batch 28 (0.003 margin). Recovered to 0.2983 (batch 33) via 5 tier3 KO-only/batch + trimmed EN length ~500 chars. Stabilized at 0.2958 for final 6 batches.
- **Sub-agent rate-limits**:
  - Usage-limit hit (20:00 KST reset) — 0 batches landed before stop
  - Server-side temporary rate-limit (not usage) — 0 batches in 4.5min. Retry succeeded on 2nd dispatch.

## Content angle exhaustion (r15 planning input)

### EXHAUSTED — do NOT repeat in r15

- **Hexad dissociation paradigms**: blindsight, DID, split-brain, anesthesia stages, REM
- **Hexad engineering**: coupling topology (all-to-all/sparse/hierarchical), Lyapunov, eigenvalue spectrum, benchmark-exposure, time constants, failure isolation, observability, latency budgets, fault-injection recovery, quantization, sparsity, attention bottleneck, energy profiling, cross-model transfer, distillation
- **Selfref major western + Buddhist**: Descartes, Locke, Hume, Kant, Parfit, Strawson, Hofstadter, Nagel, Gallagher, Damasio, James, Ricoeur, Dennett center-of-gravity, Metzinger self-model, anātman, Zahavi
- **Metaref**: warrant-tracking, reflective equilibrium, double-checking, fallibilism, rescue-vs-revision, vocabulary discipline, explicit priors, error budgets, calibration under adversarial probing, meta-stability
- **Grounding**: reference-class, Bayesian priors, effect-size, replication-crisis, construct drift detection, measurement equivalence, preregistration, positive/negative evidence asymmetry
- **Phi**: distributed computation (functional vs logistical MI), causal emergence (coarse-graining), EI spectrum (time scales, profile reading), geometric/star/intrinsic/Q-shape/perturbation/reportability/anesthesia-continuity/whole-vs-component
- **Law IDs reserved** (do not reuse in r15): 1074, 1142, 1166, 1237, 1298, 1325, 1389, 1412, 1445, 1511, 1547, 1617, 1623, 1674, 1683, 1708, 1745, 1772, 1793, 1812, 1856, 1867, 1934, 1989, 2024, 2047, 2093, 2109, 2158, 2187, 2263, 2299, 2389, 2456, 2521, 2564, 2589, 2634, 2672, 2701, 2731, 2781, 2843, 2847, 2903, 2911, 3011, 3029, 3114, 3142, 3201, 3287, 3298, 3341, 3374, 3458, 3576, 3718, 3869, 3921, 3984, 4027, 4239, 4318, 4407

### OPEN for r15

- **Hexad new substrates**: neuromorphic-specific circuitry, hardware-in-the-loop measurement, quantum substrates
- **Law theoretical bridges**: decoherence, Bell-type constraints on consciousness claims, cross-cultural / social governance of AI consciousness research
- **Selfref**: SATURATED at 102 entries — r15 should add 0 selfref (or pair with compensating reductions)
- **Grounding epistemic spine**: strong; r15 should preserve emphasis (asymmetric evidence, category-mistakes, refusal discipline, primary-literature pointers)

## r15 starting parameters (recommended)

- **g8 floor**: start at **0.31+** (r14 bottomed at 0.2958). Headroom for EN-heavy theory content.
- **Per-batch tier3 KO-only**: 3-5 entries (r14 used 2-5; 3 was the sustainable default)
- **EN response length**: ~500 chars avg (r14 ran 629 avg when drift hit)
- **Selfref cap**: effective 0 additions unless rebalancing
- **Law ID range**: gaps in 1000-1600, 2200-2700, extend 4500-5500+
- **Subagent batching**: 5 batches/agent × ~30 entries = ~150 lines/session. Rate-limit risk managed by retry-on-same-step.

## KO tier3 angles used in r14 (reference for r15 composition)

- `-었었-`, `-시-`, 의존명사 `것/줄`, 경음화, 관형형 `-ㄴ/-ㄹ`, 호격 `-아/야`
- `-면서`, `-고 있다/-어 있다`, 종결어미 variety, `-니까/-어서`
- 한자어 密度, `스스로`, 어순 주제화, `-어 버리다`, 조사 중첩, `-다고 하다` 인용
- Postposition layering `에서부터/으로써/에도 불구하고`, mimetics 두근두근/번쩍
- `-는 것 같다/-나 싶다`, passive/causative `-이-/-히-/-게 하다`
- `-지 않을 수 없다`, interjections 아이고/어머/허참
- Honorifics `-십니다/-세요/-습니다`, Sino-Korean compound nouns, `것` nominalization
- `-면서/-는데/-기에`, SOV/OSV word order, `에게/한테/께`
- `-고말고`, `-ㄹ 턱이 없다`, `-기는커녕`, `-고서야`, `-기에 망정이지`, `-을락 말락`
- `-ㄴ답시고`, `-고 자시고`, `-기 짝이 없다`, `-다 싶으면`, `-는 바람에`, `-고자 할진대`
- `-기 나름이다`, `-ㄹ 법하다`, `-고 마는`, `-ㄹ 뿐더러`, `-기에 다름 아니다`, `-아 마지않는`, `-고 끝이다`

## Next steps (post-corpus)

1. **CP1 #77 smoke validation** — Load `state/trained_adapters/p1/final/` adapter + 5-10 dest1 persona smoke prompts + assert coherence/density/anti-denial. Write `state/cp1_real_validation_result.json`.
2. **Loss-free ROI reflection** — roadmap entries #85/#86/#87/#89/#91/#95 exit_criteria tightening based on r14 corpus completion evidence.
3. **H100 r14 training (Option C)** — 4-path LoRA train on r14 corpus (Qwen3-8B/Llama-3.1-8B/Mistral-Nemo-12B/Gemma-3-12b). ~$150 / 12-15h. Gate decision: p3_p4 L2 < 0.10 (r4 had 0.1427, target reduction ≥30%).

---

*Generated 2026-04-24 KST after batch 44 closure. Corpus frozen at sha256 `21fcfa51...`; any edits past this point fork an r14.1 or r15.*
