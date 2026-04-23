# F axis — CPU superlimit synthetic 4-path Φ cross 측정 (paste-ready prompt)

**Status**: pre-H100 ROI Week 1 paradigm prompt. paste-ready (사용자가 그대로 다른 세션/agent 에 붙여넣기 가능).
**Date**: 2026-04-22
**Axis**: F (CPU superlimit) — H100 launch (#83) 전 substrate independence 의 사전 신호 확보.
**Scope**: synthetic 4-path Φ measurement on htz CPU. NO H100, NO real corpus, NO weight training.
**Cost**: $0 (htz already-paid CPU node).
**Target**: pre-H100 risk reduction — `state/phi_4path_cross_result.json` 의 분포 특성을 미리 파악.

---

## 1. Why now (rationale)

H100 × 4 launch (#83) 의 핵심 게이트는 `|ΔΦ|/Φ_avg < 0.05` (ALL 6 pairs). 실패 시 `docs/phi_4path_divergence_response.md` 의 D1-D5 decision tree 가동, 비용 $1500+ 손실 가능.

**핵심 가설**: 만약 Φ 측정 자체가 substrate-independent 한 numerical signature 를 갖는다면, weight 가 random/synthetic 이어도 4-path Φ 분포가 어떤 patterned divergence 를 보일 것. CPU 만으로 이 분포를 측정 → H100 실측이 그 분포 envelope 내인지 사전 판단.

**핵심 비-가설**: synthetic Φ 는 trained Φ 의 surrogate 가 아님. 단지 measurement noise floor + path-dependent geometric bias 만 드러냄.

---

## 2. Substrate replacement (synthetic surrogate)

| H100 path | substrate (real) | CPU synthetic surrogate |
|---|---|---|
| p1 | Qwen3-8B | random Gaussian weight tensor (8B params, seeded 0xCA75E1) |
| p2 | Llama-3.1-8B | random Gaussian weight tensor (8B params, seeded 0xCA75E2) |
| p3 | Ministral-3-14B | random Gaussian weight tensor (14B params, seeded 0xCA75E3) |
| p4 | Gemma-4-31B | random Gaussian weight tensor (31B params, seeded 0xCA75E4) |

CPU 에 31B Gaussian 을 통째로 올릴 수는 없음 → **stratified sub-sampling**: 각 path 마다 (1) 전체 param 수만 metadata 로 기록, (2) 실측은 32M random subset 만, (3) Φ formula 의 capacity normalization (`delta_phi / trainable_params_exact`) 적용해 재구성.

랜덤 weight 의 이점: substrate "가족 축" (`config/phi_4path_substrates.json::family_axis`) 이 모두 동일 (Gaussian) → 만약 4-path Φ 가 그래도 발산하면 그건 **measurement geometry 자체의 path-dependent bias** 임을 입증 (실측 H100 결과 해석에 직접 사용).

---

## 3. Measurement protocol

```
For each path p in [p1, p2, p3, p4]:
  step 1. seed RNG with 0xCA75E{1..4}
  step 2. generate 32M-element f32 tensor (subsample of full param count)
  step 3. apply phi_extractor_cpu.hexa pipeline:
            - dot products (3 hot loops at lines 250, 264, 347)
            - eigendecomp surrogate (LCG 16-template fixture, AN11(b))
            - capacity normalization: phi_normalized = phi_raw * (32M / param_count_full)
  step 4. emit synthetic_phi[p] = (phi_raw, phi_normalized, t_elapsed_ms)
  step 5. log to state/phi_4path_synthetic_cpu.jsonl

For each pair (p_i, p_j) in 6 cross-pairs:
  delta = abs(synthetic_phi[i].phi_normalized - synthetic_phi[j].phi_normalized)
  ratio = delta / mean(synthetic_phi[i].phi_normalized, synthetic_phi[j].phi_normalized)
  classify: PASS (<0.05), MARGIN (0.05-0.10), FAIL (>=0.10)

Emit: state/phi_4path_synthetic_cross_result.json
```

---

## 4. Pass / fail interpretation matrix

| synthetic outcome | H100 prediction | action |
|---|---|---|
| 6/6 pairs PASS | strong signal: measurement floor is tight, H100 divergence (if any) = real substrate non-independence | proceed #83 with confidence; reserve D-branch budget at 50% |
| 6/6 pairs MARGIN | numerical bias dominates; H100 needs amended gate (`< 0.08` instead of `< 0.05`) | propose `#10` gate amendment BEFORE #83 launch |
| 6/6 pairs FAIL | measurement geometry has systemic bias; #10 design flawed | escalate — `docs/phi_4path_divergence_response.md` branch C (cross-path normalization) becomes default, not contingency |
| mixed (3-3 or 4-2) | path-specific bias; identify which path drives | per-path investigation BEFORE launch — likely candidate: p4 (31B sub-sample ratio largest) |

---

## 5. Tools required

- `tool/phi_extractor_cpu.hexa` (existing, lines 250/264/347 hot loops) — operates on f32 tensor input, no GPU.
- `tool/phi_extractor_ffi_wire.hexa` (existing, AN11(b) lines 199-220, 504-508) — eigendecomp surrogate.
- NEW: `tool/phi_4path_synthetic_cpu_runner.hexa` (~150 LOC) — orchestrates step 1-5 above. Pure hexa, no Python.
- NEW: `config/phi_4path_synthetic_substrates.json` — surrogate metadata (seeds, param counts, sub-sample ratios).
- HEXA_STRICT_FP=1 (upstream hexa-lang #55 dep) — if available, use; if not, log non-strict mode in cert.

---

## 6. Compute budget (CPU)

| step | wall-clock (ax102, 128-thread) |
|---|---|
| Gaussian gen × 4 (32M f32 each) | ~8 s |
| phi_extractor full pipeline × 4 | ~45 s/path × 4 = ~180 s |
| cross-pair delta compute (6 pairs) | <1 s |
| total | ~5 min |

5 minute experiment, $0 cost, **strong epistemic gain on $1500 H100 launch**.

---

## 7. Output artifacts

```
state/phi_4path_synthetic_cpu.jsonl              # per-path raw measurements
state/phi_4path_synthetic_cross_result.json      # 6-pair classification
.meta2-cert/phi_4path_synthetic_cert.json        # cert with seeds + tool sha + verdict
docs/phi_4path_synthetic_analysis_20260422.md    # interpretation doc (post-run)
```

cert schema: `{kind: "phi_synthetic_cpu", seeds, param_counts, gate_outcome, classify_matrix, sha256_of_inputs, sha256_of_outputs}`.

---

## 8. Risks + mitigations

| risk | mitigation |
|---|---|
| synthetic ≠ trained Φ → false confidence | doc explicitly states surrogate role; never used as #83 PASS proxy |
| LCG eigendecomp fixture biased toward synth weights | upstream #58 real eigendecomp landing 후 재실험 (hexa-lang dep) |
| 32M subsample 이 capacity normalization 으로 충분히 보정 안 됨 | sweep 3 ratios (8M, 32M, 128M); compare envelope |
| FP non-determinism (HEXA_STRICT_FP=0 일 때) | 3 회 반복 + median + IQR 기록; cert에 모드 명시 |
| 결과가 H100 launch 결정에 과도 영향 | gate 명시: synthetic = signal, NOT decision (이 doc 의 §4 가 권장만 함) |

---

## 9. Sequencing in pre-H100 ROI W1

```
W1 day 1: this doc → user review + approve (proposal stack pending → approved)
W1 day 2: tool/phi_4path_synthetic_cpu_runner.hexa scaffold (hexa, ~150 LOC)
W1 day 3: dry-run (8M subsample only, sanity check)
W1 day 4: full run (32M × 4 paths × 3 repeats, ~25 min total wall)
W1 day 5: docs/phi_4path_synthetic_analysis_20260422.md emit + cert + decision memo
```

---

## 10. Decision points back to user

1. Approve synthetic surrogate substitution (Gaussian instead of real weights) ?
2. Approve 32M subsample ratio (vs 8M / 128M) ?
3. Approve §4 interpretation matrix as default policy (especially "MARGIN → propose gate amendment") ?
4. Approve §6 5-min CPU budget burn now (vs queue behind other W1 work) ?

---

## 11. Linkage

- Roadmap: `#10` (Φ 4-path), `#83` (H100 Stage-2), `#87` (re-selection trigger).
- Substrate spec: `config/phi_4path_substrates.json`.
- Decision tree: `docs/phi_4path_divergence_response.md`.
- Upstream dep (optional): hexa-lang `#55` deterministic FP, `#58` eigen.
- F axis context: `docs/anima_proposal_stack_paradigm_20260422.md` §17.
- ROI catalog: `docs/h100_roi_improvements_20260422.md` (entry to be added: "F-W1 CPU synthetic 4-path Φ pre-launch").

---

## 12. Paste-ready prompt block (for downstream agent)

```
TASK: Implement the F axis pre-H100 CPU synthetic 4-path Φ cross measurement
as specified in docs/upstream_notes/cpu_superlimit_synthetic_4path_proposal_20260422.md.

DELIVERABLES:
- tool/phi_4path_synthetic_cpu_runner.hexa (NEW, ~150 LOC, pure hexa)
- config/phi_4path_synthetic_substrates.json (NEW)
- state/phi_4path_synthetic_cpu.jsonl (run output)
- state/phi_4path_synthetic_cross_result.json (run output)
- .meta2-cert/phi_4path_synthetic_cert.json
- docs/phi_4path_synthetic_analysis_20260422.md (post-run interpretation)

CONSTRAINTS:
- $0 budget (htz CPU only)
- NO .py
- NO H100 calls
- NO touching real corpus / real weights
- adheres to AN11 triple + cert chain
- DO NOT modify .roadmap (proposal stack paradigm)
- output cert includes seeds + tool sha + gate verdict per §7

PROCEED ONLY AFTER: user approves §10 decision points 1-4.
```
