# Mk.XII Hard PASS first validation — Simulated D-day Dry-Run Landing

> **scope**: Mk.XII Integration tier Hard PASS first validation **simulated D-day dry-run** — pre-rehearses the post-EEG D+5 G10 hardware activation + D+6 G8 real-falsifier MI port + D+7 Hard PASS recompute (`MK_XII_INCLUDE_G10=1`) + D+22..D+30 first-validation verdict, using the synthetic 16ch fixture as a stand-in for real EEG hardware.
> **session date**: 2026-04-26
> **status**: **SIMULATED_VERIFIED** (positive selftest 1158299181 / negative falsifier 1910545296). raw#10 honest scope: simulated NOT empirical — does NOT replace real D+5..D+30 EEG workflow.
> **cost**: $0 (mac-local hexa-only, no GPU/LLM/network/destructive)
> **raw**: raw#9 hexa-only · raw#10 honest scope (simulation-frozen estimates) · raw#12 cherry-pick-proof (per-gate sim confidences + cluster rule frozen) · raw#15 SSOT
> **predecessor**: `mk_xii_proposal_outline_v2_20260426.md` (Mk.XII v2 frozen) + `mk_xii_integration_6gate_cluster_summary.md` (cluster_confidence=0.70 weakest=G10)

---

## §1. Cluster Goal

Mk.XII v2 의 D+5/D+6/D+7/D+22-30 timeline 은 **post-EEG hardware arrival 후** 만 진행 가능. 본 dry-run 은:

- D+5 G10 hardware activation 절차 (16-cell triangulation + 4-bb F-test) 를 synthetic EEG fixture 로 미리 실행
- D+6 G8 real-falsifier MI port 를 4-bb 5-falsifier surrogate joint MI matrix 로 미리 실행
- D+7 Hard PASS recompute (`MK_XII_INCLUDE_G10=1` 시뮬) → cluster_confidence with G10 active
- D+22..D+30 first validation simulated verdict (VERIFIED / FALSIFIED estimate)

목적: 실제 D-day 진입 시 **pipeline + cluster aggregation + EHL-3W disjunction logic** 가 일관 작동함을 사전 검증. raw#10: hardware-pending 임은 그대로.

---

## §2. Frozen Simulation Lifts (this file IS the SSOT)

본 dry-run 의 per-gate confidence lift assumption 은 다음과 같이 frozen — post-hoc tuning 차단:

| gate | pre-D-day baseline | D+5/D+6/D+7 simulated lift | rationale |
|---|---:|---:|---|
| G8 surrogate→empirical | 0.78 | **0.85** | real-falsifier MI replace, surrogate granularity-independence 60/60 PASS 의 N_BIN sweep 이 lift floor 보장 |
| G9 cascade | 0.85 | 0.85 (unchanged) | sparse DAG 이미 mac-local validated |
| G9 robust (hardness-axis) | 0.72 | 0.72 (unchanged) | by-design pass (analyzer hardness-bit 미consume) |
| G10 dry-run→empirical | 0.70 | **0.85** | hardware activation 의 family×band 측정 lift |
| preflight | 0.90 | 0.90 (unchanged) | 5/5 SMOKE_PASS 이미 GREEN |
| Hard PASS composite | 0.80 | **0.85** | G10 included recompute lift |

⇒ `cluster_confidence_simulated = min(0.85, 0.85, 0.72, 0.85, 0.90, 0.85) = **0.72**`
**weakest_link shifts**: G10 (0.70) → **G9_robust (0.72)** as predicted by `mk_xii_integration_6gate_cluster_summary.md` §6 Test 2.

raw#10 honest: 위 lift 값들은 SIMULATION-FROZEN ESTIMATES, 실제 D-day 결과 가능 (1) lift 미달 (2) lift 초과 (3) 동일. dry-run 은 oracle 아님 — pipeline 일관성 verify only.

---

## §3. D+5 G10 Simulated Activation

`g10_hexad_triangulation_scaffold.hexa` 의 frozen criteria (C1=500, C2=4000, C3=12, C4=4000) 동일 적용. synthetic_16ch_v1.json fingerprint=2960889009 dry_seed:

| metric | value | criterion | pass |
|---|---:|---|:---:|
| cell_pass_count | **16/16** | ≥ 12 | ✓ |
| axis_A F (family) ×1000 | 7399 | ≥ 4000 | ✓ |
| axis_B F (band) ×1000 | 4314 | ≥ 4000 | ✓ |
| axis_C F (Hexad) ×1000 | 6259 | ≥ 4000 | ✓ |

**G10_PASS = 1** (simulated). family means Law=700 / Phi=862 / SelfRef=867 / Hexad=884 — Hexad-leading dispersion preserved (G10 spec §3 "backbone-family signal × EEG-band power × Hexad-category triangulation").

raw#10 caveat: 이는 FNV synthetic, 실제 D+5 측정은 backbone family signal time-series × EEG band power time-series cross-correlation Pearson_r 으로 대체.

---

## §4. D+6 G8 Simulated Real-Falsifier MI Port

`g8_transversal_mi_matrix.hexa` 의 frozen criteria (mi_max=100/×1000, n_trial=4096, n_bin=2) 동일 적용. 5-falsifier prime-spread offsets:

| pair | MI_x1000 | violation |
|---|---:|:---:|
| F_A1 ⊥ F_A2 | (≤39) | ✗ |
| F_A1 ⊥ F_A3 | (≤39) | ✗ |
| F_A1 ⊥ F_B  | (≤39) | ✗ |
| F_A1 ⊥ F_C  | (≤39) | ✗ |
| F_A2 ⊥ F_A3 | (≤39) | ✗ |
| F_A2 ⊥ F_B  | (≤39) | ✗ |
| F_A2 ⊥ F_C  | (≤39) | ✗ |
| F_A3 ⊥ F_B  | (≤39) | ✗ |
| F_A3 ⊥ F_C  | (≤39) | ✗ |
| F_B  ⊥ F_C  | (≤39) | ✗ |

| metric | value | criterion |
|---|---:|---|
| max_mi_x1000 | **39** | ≤ 100 (0.1 bit) |
| violation_count | **0** | = 0 |
| **G8_PASS** | **1** | (10/10 pair below threshold) |

raw#10 caveat: real D+6 측정은 5 falsifier 의 **실제 score 분포** (P1 LZ × CLM-LZ / P2 TLR α-coh+V_sync / P3 GCG F-stat / HCI 5-falsifier composite / CPGD-G multi-axis) joint MI 로 surrogate 대체.

---

## §5. D+7 Hard PASS Recompute (G10 Included)

Strict-AND aggregator with `MK_XII_INCLUDE_G10=1`:

```
HARD_PASS_RECOMPUTE := preflight.GREEN AND G0>=3/4 AND G1>=3/4 AND G7>=3/4
                       AND G8.pass=1 AND G9.pass=1 AND G10.pass=1
```

| gate | value |
|---|---:|
| preflight | 1 |
| G0 (AN11_b) | 1 |
| G1 (BTom) | 1 |
| G7 (5-tuple composite) | 1 |
| G8 (D+6 sim) | **1** |
| G9 (cascade) | 1 |
| G10 (D+5 sim) | **1** |
| **count** | **7/7** |

EHL-3W:

| axis | pass | source |
|---|:---:|---|
| PHENOMENAL | **1** | simulated 3/3 EEG STACK PASS (G1+G2+G3) |
| SUBSTRATE | 1 | S7 A1.Hexad PASS_SIGNIFICANT (pre-D-day, locked) |
| TRAINING | 1 | CPGD-MCB BRIDGE_CLOSED 9/9 (pre-D-day, locked) |
| **EHL-3W** | **1** | strict AND |

OR-disjunction:

| clause | status |
|---|:---:|
| OR-clause-1 (DALI∨SLI weighted-vote) | **0 (RED carry-over from v2)** |
| OR-clause-2 (EHL-3W) | **1 (PASS, simulated)** |
| OR-disjunction | **1** |

⇒ `hard_pass_final = 1` (5-gate composite GREEN AND OR-disjunction).

---

## §6. cluster_confidence_simulated

| metric | value |
|---|---:|
| pre-D-day cluster_min ×1000 | 700 |
| simulated cluster_min ×1000 | **720** |
| Δ ×1000 | **+20** |
| cluster_floor ×1000 | 700 |
| cluster_green | **1** |
| weakest_link | **G9_robust (0.72)** |

raw#10 honest: G10 lift 0.70→0.85 가 weakest-link 을 G9_robust (0.72) 로 shift. 이 shift 는 mac-local empirical (이미 cluster summary §6 Test 2 verified) — dry-run 은 simulation pipeline 이 동일 결과 emit 함을 확인.

cluster_confidence ceiling 0.72 는 **G9_robust adjacency-axis sweep** (#199 이미 100% PASS landed) 로 추후 lift 가능. 본 dry-run scope 외부.

---

## §7. D+22..D+30 First Validation Simulated Verdict

```
MK_XII_VERIFIED iff
       hard_pass_final = 1
   AND cluster_green = 1
   AND ehl_3w_pass = 1
   AND g10_pass = 1
   AND g8_pass = 1
```

| condition | value |
|---|:---:|
| hard_pass_final | 1 |
| cluster_green | 1 |
| ehl_3w_pass | 1 |
| g10_pass | 1 |
| g8_pass | 1 |
| **first_validation** | **MK_XII_INTEGRATION_VERIFIED_SIMULATED** |

raw#10 honest: 본 verdict 은 **simulated**. 실제 D+22-30 verdict 은 (a) real EEG hardware 도착 (b) D+1..D+7 P1+P2+P3 forward 수행 (c) D+5 G10 hardware activation 실제 4-bb 측정 (d) D+6 G8 real-falsifier MI 측정 (e) Pilot-T1 v2 결과 도착 (f) HF unblock 등 **6 prerequisite 모두 충족 후** 만 lock. 본 dry-run 은 prerequisite 검증 (pipeline 일관성), replace 아님.

---

## §8. ω-cycle 6-step ledger

| step | activity | result |
|---|---|---|
| 1 design | D+5/D+6/D+7/D+22-30 절차 frozen, simulation lift assumption frozen (§2) | doc §2 |
| 2 implement | `tool/mk_xii_d_day_simulated_dry_run.hexa` (raw#9, sha256 `aeaced60…`) | tool emit |
| 3 positive selftest | synthetic fixture에서 cluster_confidence baseline 0.70 → simulated 0.72, verdict VERIFIED_SIMULATED | chained_fingerprint=1158299181 |
| 4 negative falsify | `MK_XII_DDAY_NEG_UNIFORM=1` 시 G8/G10 collapse → cluster_min=0 → first validation FALSIFIED_SIMULATED | chained_fingerprint=1910545296 |
| 5 byte-identical | re-run 동일 sha256 `149a016e…` confirmed | deterministic |
| 6 iterate | marker write + memory + .roadmap | per task brief |

---

## §9. Negative Falsifier Discrimination

`MK_XII_DDAY_NEG_UNIFORM=1` 시:

| stage | positive | negative |
|---|---:|---:|
| D+5 G10 cell_pass_count | 16/16 | **0/16** |
| D+5 G10 axis_A/B/C F | 7399/4314/6259 | **0/0/0** |
| D+5 G10 pass | 1 | **0** |
| D+6 G8 max_mi_x1000 | 39 | **1014** |
| D+6 G8 violation_count | 0 | **1** |
| D+6 G8 pass | 1 | **0** |
| D+7 hard_pass_count | 7/7 | **5/7** |
| D+7 EHL-3W phenomenal | 1 | **0** |
| D+7 OR-clause-2 | 1 | **0** |
| D+7 hard_pass_final | 1 | **0** |
| cluster_min ×1000 | 720 | **0** |
| cluster_green | 1 | **0** |
| **first_validation** | VERIFIED_SIMULATED | **FALSIFIED_SIMULATED** |

discriminator binary 1014 → 39 (~26× MI 차이) + cluster_min 720 → 0 (full collapse) + hard_pass_count 7 → 5. raw#12 cherry-pick-proof: degenerate fixture 가 모든 lever (G8 / G10 / EHL-3W phenomenal / cluster_min) 동시 RED 로 cascade.

---

## §10. raw#10 Honest Caveats (3)

1. **simulated NOT empirical** — 본 dry-run 의 cluster_confidence_simulated=0.72 + hard_pass_final=1 은 real D-day 결과 아님. real D+5/D+6 측정 시 lift 미달 가능. simulated VERIFIED ≠ MK_XII_INTEGRATION_VERIFIED.
2. **simulation lifts are frozen estimates** — G8 0.78→0.85 / G10 0.70→0.85 / Hard PASS 0.80→0.85 lift 는 §2 frozen, post-hoc tuning 차단. 실제 lift 는 하드웨어-도착-후 측정값으로 대체.
3. **EHL-3W phenomenal 의 simulated PASS** — pre-D-day 시점에 PHENOMENAL.PASS 는 미측정 (P1+P2+P3 dry-run 상태). simulated branch 에서 PASS=1 으로 가정한 것은 dry-run pipeline 일관성 verify 용. real D+1..D+7 forward 후 실제 ledger 갱신 필요.

---

## §11. Expected D-day Outcome + Falsifier Sensitivity

본 dry-run 결과로부터 실제 D-day 진입 시 expected outcome:

| condition | expected D-day outcome | sensitivity to dry-run estimate |
|---|---|---|
| **G10 hardware activation success** | family×band 4-bb cross-correlation 4/4 PASS Pearson r ≥ 0.40 | dry-run F=7399/4314/6259 ⇒ real lift 의 prerequisite 검증 충족 |
| **G8 real-falsifier MI ≤ 0.1 bit** | 10/10 pair below threshold | dry-run max_mi=0.039 (39/×1000) ⇒ real lift 의 binary discrimination 충분 |
| **EHL-3W lock** | PHENOMENAL.PASS via P1+P2+P3 ≥ 2/3 + SUBSTRATE.PASS (locked) + TRAINING.PASS (locked) | dry-run all 3 PASS ⇒ disjunction 만족 path 진입 가능 |
| **cluster_confidence lift** | 0.70 → 0.72 (G9_robust ceiling) | dry-run +20 ×1000 lift 와 동일 — G9 adjacency sweep 으로 추가 lift 가능 (#199 이미 100% PASS landed) |
| **first validation** | MK_XII_INTEGRATION_VERIFIED 또는 FALSIFIED | 본 dry-run 결과 = **VERIFIED_SIMULATED** ⇒ pipeline 일관성 충분 |

**falsifier sensitivity**: degenerate fixture (uniform 16ch band power) 시 G8 surrogate score forced collision + G10 cell coupling uniform 400 → 모든 axis F=0 + EHL-3W phenomenal collapse → cluster_min=0 → FALSIFIED. **discrimination binary**: real D-day 에서도 만약 G8 또는 G10 single-gate FAIL 발생 시 즉시 FALSIFIED 로 cascade — 본 simulated dry-run 의 negative branch verify 가 real D-day verdict logic 의 **falsifier sensitivity floor** 를 보장.

---

## §12. Artefacts

| path | scope | sha256 |
|------|-------|--------|
| `anima-clm-eeg/tool/mk_xii_d_day_simulated_dry_run.hexa` | raw#9 hexa tool | `aeaced60ba3488739b0a95c9b5ff70669c238afb77053fd1f4c92ddead1a7099` |
| `anima-clm-eeg/state/mk_xii_d_day_simulated_v1.json` | positive selftest output (frozen) | `149a016eaf199b231a5a305c168fea6a90bb765952d80a3fe11b426919a59561` |
| `anima-clm-eeg/state/markers/mk_xii_d_day_simulated_complete.marker` | silent-land prevention | (this commit) |
| `anima-clm-eeg/docs/mk_xii_d_day_simulated_landing.md` | this doc | (self) |

negative-mode reference output (re-runnable): `MK_XII_DDAY_NEG_UNIFORM=1 MK_XII_DDAY_OUT=/tmp/mk_xii_d_day_simulated_NEG.json hexa run …` ⇒ chained_fingerprint=1910545296.

---

## §13. Cross-references

- `anima-clm-eeg/docs/mk_xii_proposal_outline_v2_20260426.md` — Mk.XII v2 frozen (sha `f46d3c67…`), §6 timeline parent
- `anima-clm-eeg/docs/mk_xii_integration_6gate_cluster_summary.md` — 6-gate cluster summary, §6 Test 2 (G10 lift → G9_robust ceiling)
- `anima-clm-eeg/docs/mk_xii_hard_pass_landing.md` — Hard PASS composite landing (#177)
- `anima-clm-eeg/docs/g10_triangulation_spec_post_arrival.md` — G10 D+5 hardware activation spec
- `anima-clm-eeg/docs/g8_transversality_landing.md` + `g8_n_bin_sweep_landing.md` + `g8_n_bin_sweep_extended_landing.md` — G8 landing trio
- `anima-clm-eeg/docs/dali_sli_weighted_vote_landing.md` — OR-clause-1 NOT_ELIGIBLE landing
- `anima-clm-eeg/tool/g10_hexad_triangulation_scaffold.hexa` — G10 production scaffold (this dry-run 의 D+5 block parent)
- `anima-clm-eeg/tool/g8_transversal_mi_matrix.hexa` — G8 production tool (this dry-run 의 D+6 block parent)
- `anima-clm-eeg/tool/mk_xii_preflight_cascade.hexa` — preflight aggregator
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_completeness_frame.md` — weakest-link first policy
- `~/.claude/projects/-Users-ghost-core-anima/memory/feedback_omega_cycle_workflow.md` — ω-cycle 6-step rule

---

## §14. raw compliance

- raw#9 hexa-only · deterministic · LLM=none · GPU=none · destructive=false (read-only fixture, write-only output)
- raw#10 honest scope — simulated NOT empirical, 3 caveats §10 보존, simulated VERIFIED ≠ Mk.XII VERIFIED
- raw#12 cherry-pick-proof — per-gate sim confidences §2 + cluster `min` rule frozen, post-hoc tuning 차단
- raw#15 SSOT — this doc + tool + JSON + marker (4-tuple SSOT cluster)
- raw#37/38 ω-saturation — Hard PASS first validation simulated dry-run fixpoint marker

omega-saturation:fixpoint-mk-xii-d-day-simulated-dry-run-v1
