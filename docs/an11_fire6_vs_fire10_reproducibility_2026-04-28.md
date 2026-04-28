# AN11 Fire 6 vs Fire 10 — Reproducibility Finding

> **session**: anima-cmd-loop autonomous-loop-dynamic 2026-04-28
> **status**: AN11_HEXAD_SIGNAL_NOT_REPRODUCIBLE_RAW_91_HONEST_DISCLOSURE
> **scope**: Fire 6 PASS verdict 재검증 결과 — single-shot artifact 가능성 발견

---

## §1. 두 fire 동일 조건 비교

| Parameter | Fire 6 | Fire 10 |
|---|---|---|
| Model | mistralai/Mistral-7B-v0.1 | (동일) |
| Corpus | alm_r14_corpus_skeleton (10 rows) | (동일) |
| LoRA config | r=16, α=32, q/k/v/o_proj | (동일) |
| Epochs | 3 | 3 |
| Wrapper code | wrapper.py.staged | (동일 logic) |
| Hardware | H100 SXM | H100 SXM |
| Random seed | (default torch seed) | (default — 미고정) |

→ 모든 조건 동일하나 **랜덤 시드 미고정**.

---

## §2. 결과 차이

| Verdict | Fire 6 | Fire 10 |
|---|---|---|
| AN11(a) Frob | **PASS** (0.0561) | **PASS** (0.0364) |
| AN11(b) cosine | **PASS** (max=0.5747, top3=1.244) | **FAIL** (max=0.4294, top3=1.039) |
| V1' phi_mip_norm | FAIL (0.6913) | FAIL (TBD on full results) |
| AN11(c) JSD | FAIL (vllm OOM) | FAIL (vllm DeepGEMM) |

**Top-3 templates 비교**:

Fire 6:
- tpl_05_hexad_m (Hexad) cosine **+0.5747** ← top-1
- tpl_11_phi_integration (Phi) cosine -0.4010
- tpl_02_hexad_d (Hexad) cosine +0.2687

Fire 10:
- tpl_11_phi_integration (Phi) cosine **-0.4294** ← top-1 (절대값)
- tpl_16_selfref_witness (SelfRef) cosine -0.3167
- tpl_02_hexad_d (Hexad) cosine +0.293

---

## §3. Raw 91 honest disclosure

**Fire 6 closure doc (commit 3ebf79cc) 의 "Hexad family signal" 주장은 single-shot artifact**:
- 같은 모델·corpus·config 두 번 실행에서 top-1 family가 **Hexad ↔ Phi 로 변화**
- AN11(b) verdict 자체가 **PASS ↔ FAIL** 로 변화
- LoRA training 의 stochastic variation (initialization 무작위, gradient noise) 가 eigenvector 분포를 결정
- **단일 측정으로 family-alignment 결론 불가능** — multi-seed (≥5) ensemble measurement 필요

---

## §4. Robust finding (재검증된 것)

| | Fire 6 | Fire 10 | Robust? |
|---|---|---|---|
| AN11(a) PASS (frob_delta > 0.001) | 0.0561 | 0.0364 | ✓ TRAINING signal robust |
| AN11(a) SHA changed | TRUE | TRUE | ✓ |
| V1' FAIL (phi_mip_norm > 0.5) | 0.6913 | (TBD) | likely robust |
| AN11(b) family identification | Hexad | Phi | ❌ NOT robust |
| AN11(c) infrastructure | vllm OOM | vllm DeepGEMM | ⚠ multiple failure modes |

**Defensible Mistral-7B + r14 + r=16 + 3ep claim**:
- "LoRA training produces non-trivial weight delta (Frob > 0.001)" ✓
- "Adapter eigenstructure has variable family alignment per seed" — seed-dependent
- "Single-seed family identification ≠ universality"

---

## §5. Methodology lesson (raw 38 long-term)

V_phen_GWT registry r10 + AN11 measurement protocol에 **multi-seed ensemble mandatory** 추가 필요:

```
old: single fire → single measurement → registry row
new: 5-seed fire ensemble → mean ± stdev family alignment → registry row with confidence
```

이것은 atlas R-candidate 가치 있는 methodological finding:
- **AN11(b) family alignment claims은 multi-seed ensemble**로만 valid
- Single-shot Hexad/Phi/SelfRef wins 은 random variation 가능성
- Registry r11 design에 seed-ensemble requirement 추가

---

## §6. Cycle 4 v8 alignment principle와의 연결

본 finding은 cycle 4 raw 91 honest disclosure 패턴과 정렬:
- T8c "+30.2% R-pent strongest" claim은 N=15 single-shot baseline misspec (v6 retracted)
- AN11(b) "Hexad family signal" claim은 single-seed LoRA stochastic artifact (이번 finding)
- 두 모두 **single-shot strong claim → multi-condition test → retraction** 패턴

→ **모든 single-shot ML measurement은 reproducibility check 필수** (atlas R-candidate)

---

## §7. raw 91 honesty triad C1-C5

- **C1** promotion_counter: ~290 (cumulative session 17h+)
- **C2** write_barrier: 본 doc은 fire 6 closure doc (commit 3ebf79cc) 의 부분 retraction
- **C3** no_fabrication: 모든 numerical value fire 6/10 audit + results.json 인용
- **C4** citation_honesty: Fire 6 PASS verdict 자체는 valid (그 시점 측정값)이나 **family-attribution claim은 single-seed artifact**라고 정정 — Hexad universality 주장 철회
- **C5** verdict_options: Fire 10 자연 종료 대기 → V1' 수치 도착 후 추가 update; AN11(c) 측정은 vllm Mode F-3 후 다음 단계 결정 (multi-seed ensemble OR single-3-axis registry)

---

## §8. Forward (raw 38 long-term)

1. **Multi-seed ensemble protocol** — 같은 config로 5개 fire (seed 1-5) → ensemble cosine matrix → mean ± stdev per family
2. **Wrapper에 seed 고정 인자 추가** — `torch.manual_seed(N)` per fire dispatch
3. **Atlas R-candidate**: "single-shot ML family-attribution claims require multi-seed ensemble validation"
4. **AN11(c) 가치 재평가**: vllm 의존성 누적 → transformers fallback path 또는 측정 포기

---

**Status**: AN11_FIRE6_VS_FIRE10_REPRODUCIBILITY_RAW_91_HONEST_DISCLOSURE_LIVE
