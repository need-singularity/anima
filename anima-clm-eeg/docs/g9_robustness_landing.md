# G9 Robustness Sweep — Landing

> **gate**: G9 robustness (sister of `g9_dag_cascade_analyzer`)
> **scope**: soft↔hard 재분류 perturbation 16 시나리오 (2^4) verdict invariance
> **session date**: 2026-04-26
> **proposal source**: `anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` §3 + g9 baseline sister
> **status**: **G9_ROBUST** (positive 100% invariance), **G9_FRAGILE** under collapse falsifier — both byte-identical

---

## §1. Frozen criteria

| criterion | budget | rationale |
|---|---|---|
| invariance_pct | ≥ **80 %** (12/16) | 4-edge canonical DAG 의 hardness axis 에 대한 verdict invariance. 80 % 미만 → FRAGILE. |
| inherits A,B | edge_max=7, cascade_max=2 | sister analyzer 와 동일, hexa-encoded 상수 |

threshold 와 16-scenario set 모두 implementation 시점에 frozen (raw#12 cherry-pick-proof).

---

## §2. Perturbation space

4 canonical edges (모두 row 4 = PARADIGM_V11 incoming):

| k | edge | baseline hardness |
|---|---|---|
| 0 | 4 ← 0 (PV11 ← HCI) | soft (0) |
| 1 | 4 ← 1 (PV11 ← CPGD) | soft (0) |
| 2 | 4 ← 2 (PV11 ← EEG_STACK) | hard (1) |
| 3 | 4 ← 3 (PV11 ← TRIBE_v2) | hard (1) |

Scenario index `s ∈ [0..15]` 의 비트 `b_k = (s >> k) & 1` 가 edge `k` 의 hardness 를
지정. canonical baseline = `s = 0 + 0 + 4·1 + 8·1 = 12`.

adjacency 는 **불변** (모든 시나리오에서 4 edge sparse encoding 유지).

---

## §3. 16-scenario verdict matrix

| s | hardness (edge0,1,2,3) | hard_count | cascade_max | g9_pass |
|---|---|---|---|---|
| 0  | 0,0,0,0 | 0 | 1 | ✓ |
| 1  | 1,0,0,0 | 1 | 1 | ✓ |
| 2  | 0,1,0,0 | 1 | 1 | ✓ |
| 3  | 1,1,0,0 | 2 | 1 | ✓ |
| 4  | 0,0,1,0 | 1 | 1 | ✓ |
| 5  | 1,0,1,0 | 2 | 1 | ✓ |
| 6  | 0,1,1,0 | 2 | 1 | ✓ |
| 7  | 1,1,1,0 | 3 | 1 | ✓ |
| 8  | 0,0,0,1 | 1 | 1 | ✓ |
| 9  | 1,0,0,1 | 2 | 1 | ✓ |
| 10 | 0,1,0,1 | 2 | 1 | ✓ |
| 11 | 1,1,0,1 | 3 | 1 | ✓ |
| 12 | 0,0,1,1 | 2 | 1 | ✓ ← canonical baseline |
| 13 | 1,0,1,1 | 3 | 1 | ✓ |
| 14 | 0,1,1,1 | 3 | 1 | ✓ |
| 15 | 1,1,1,1 | 4 | 1 | ✓ |

`hard_count` 는 binomial: 1×{0}, 4×{1}, 6×{2}, 4×{3}, 1×{4}.
`cascade_max = 1` 모든 시나리오에서 invariant — adjacency 불변 + cascade 는 column-sum 만 의존.

---

## §4. Verdict

| dimension | value | budget | pass |
|---|---|---|---|
| pass_count | 16 / 16 | — | — |
| matching_baseline | 16 / 16 | — | — |
| invariance_pct | **100 %** | ≥ 80 % | ✓ |
| **G9 robustness** | — | — | **G9_ROBUST** |

**해석**: G9 verdict 는 hardness 축에 대해 **strictly invariant**. 이는
analyzer 의 criteria (edge_count, cascade_max) 가 hardness bit 를 pass logic
에 사용하지 않기 때문에 expected result. 본 sweep 은 그 invariance 를
**empirical 하게 16-cell exhaustive** 측정으로 fix.

---

## §5. Falsifier (negative, mode `G9_FALSIFY=1`)

falsifier 는 hardness 가 아닌 **adjacency** 에 perturbation 을 가해 verdict
가 변동함을 증명:

- 4 edge 를 모두 column j=0 으로 collapse (rows 1,2,3,4 → col 0)
- `cascade_impact_of(0) = 4 > CASCADE_BUDGET=2`
- 결과: 16/16 FAIL, matching_baseline = 0/16, invariance = 0 %, verdict = **G9_FRAGILE**

→ falsifier 작동 확인. hardness sweep 만으로는 verdict 변동 detect 불가능
(by design); collapse 는 즉시 detect.

---

## §6. ω-cycle 6-step ledger

| step | activity | result |
|---|---|---|
| 1 design | 16-scenario set frozen, invariance ≥ 80 % | this doc §1+§2 |
| 2 implement | `tool/g9_robustness_sweep.hexa` raw#9 strict | adjacency reuse + hardness sweep + FNV fingerprint |
| 3 positive selftest | canonical sparse DAG, 16 hardness perturbations | 16/16 PASS, invariance 100 % → **G9_ROBUST** |
| 4 negative falsify | `G9_FALSIFY=1` collapse all edges to col 0 | 0/16 PASS, invariance 0 % → **G9_FRAGILE** |
| 5 byte-identical | 2× back-to-back runs (positive) | sha256 `3b6035d7…2b8` × 2 (identical) |
| 6 iterate | hardness invariance proven; next sweep candidate: `adjacency-1bit` | logged in memory + .roadmap |

---

## §7. Artefacts

| path | sha256 | size |
|---|---|---|
| `anima-clm-eeg/tool/g9_robustness_sweep.hexa` | `bd3beb6e33b949d0a7f1d1f1b75b5f4626c4a23aabe4cc97f64d53fadc6a53cc` | 250 LoC |
| `state/g9_robustness_sweep.json` (positive) | `3b6035d75c80f4dabb1605903643e8bd9420197cf68caa9d9274289c165a92b8` | 43 lines |
| `state/g9_robustness_sweep_falsify.json` (negative) | `b93792968f2bbafcc644adc301f18b9ded821c73e9700de0fdf2c66a84ba6f46` | 43 lines |
| `anima-clm-eeg/docs/g9_robustness_landing.md` | (this doc) | — |

`fingerprint` 필드 (positive cert): **3415978968** (FNV-32 chained over budgets+per-scenario+aggregates).

---

## §8. Reproduction

```bash
# Positive sweep (G9_ROBUST)
HEXA_RESOLVER_NO_REROUTE=1 hexa run \
  anima-clm-eeg/tool/g9_robustness_sweep.hexa
# → exit 0, verdict G9_ROBUST, invariance 100 %

# Falsifier (G9_FRAGILE)
G9_FALSIFY=1 G9_SWEEP_OUT=state/g9_robustness_sweep_falsify.json \
  HEXA_RESOLVER_NO_REROUTE=1 hexa run \
  anima-clm-eeg/tool/g9_robustness_sweep.hexa
# → exit 1, verdict G9_FRAGILE, invariance 0 %
```

---

## §9. Cross-references

- `anima-clm-eeg/tool/g9_dag_cascade_analyzer.hexa` — baseline (read-only sister)
- `anima-clm-eeg/docs/g9_dag_cascade_landing.md` — baseline landing
- `anima-clm-eeg/docs/mk_xii_proposal_outline_20260426.md` §3 — DAG canonical source
- raw#9 — hexa-only deterministic execution
- raw#10 — honest scope (hardness-only sweep; adjacency perturbation reserved for future cycle)
- raw#12 — cherry-pick-proof (16-scenario set + 80 % threshold frozen pre-execution)

omega-saturation:fixpoint-g9-robustness-hardness-axis
