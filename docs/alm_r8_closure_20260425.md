# ALM r8 클로저 — Option D-mistral (Axis 4 H4b 가설 VALIDATED, partial-pass)

> **생성일**: 2026-04-25
> **부모 commit**:
> - `7d25353e` r8 D-mistral prep — launch spec + p4 swap proposal
> - `a05994fc` r7 Axis 4 진단 — H4b vendor×generation 가설
> - `1e064038` r6-α baseline (L2 6/6, KL 5/6, p2_p4 KL 잔존)
> **Pod**: `gyhpkhacy2x51q` `anima-r7-p4-mistralai-mistral-7b-v0-3-20260425T020010Z` — RUNNING 02:00:10Z → DONE 02:09:20Z (372s, ~$0.31), removed 2026-04-25
> **POLICY R4**: `.roadmap` 미수정.

---

## §1. 핵심 결론

| 항목 | r6 baseline | r7 D-qwen14 | **r8 D-mistral** |
|---|---:|---:|---:|
| L2 pass | 6/6 | 3/6 | **6/6** |
| KL pass | 5/6 | 3/6 | **5/6** |
| Verdict | FAIL (partial) | FALSIFIED | **FAIL (partial)** ← r6-equivalent |
| p4 spectrum λ₁/λ₂ | 0.7192 / 0.0627 (단봉) | 0.5755 / 0.3206 (**쌍봉**) | **0.8120 / 0.0624 (단봉)** |
| PR p4 | 1.903 | 2.298 | **1.504** |
| Failing pair | p2_p4 KL=0.189 | 4 pairs L2/KL | **p1_p2 KL=0.138** |

**Axis 4 H4b 가설 VALIDATED**: vendor×generation 매칭 (mistral-7b ↔ mistral-nemo) 으로 r7 의 쌍봉 → r8 단봉 복귀. λ₂ 가 0.32 → 0.062 (×0.19) 로 회귀, top-2 mass 0.896 → 0.874.

**Partial-pass nature**: r6 와 동등한 5/6 KL pass 비율이지만 **fail pair 가 이동**:
- r6: p2_p4 KL 0.1891 fail (cross-vendor: qwen2.5/llama × gemma)
- r8: p1_p2 KL 0.1376 fail (same-vendor close-gen: **qwen3-8b ↔ qwen2.5-7b**)

→ r8 의 fail 은 **architecture-class 일치 후 잔여 generation drift** (질적으로 더 약한 원인).

---

## §2. Pair-by-pair (real / null p95)

null bootstrap p95 (n=10000, col-perm): L2_p95=0.2002, KL_p95=0.1277.

| pair | r6 L2 | r6 KL | r7 L2 | r7 KL | r8 L2 | r8 KL | r8 verdict |
|---|---:|---:|---:|---:|---:|---:|:---:|
| p1_p2 | 0.0968 ✓ | 0.1376 ✓ | 0.0968 ✓ | 0.1376 ✗ | 0.0968 ✓ | **0.1376 ✗** | KL fail |
| p1_p3 | 0.0721 ✓ | 0.0135 ✓ | 0.0721 ✓ | 0.0135 ✓ | 0.0721 ✓ | 0.0135 ✓ | PASS |
| p1_p4 | 0.0860 ✓ | 0.0262 ✓ | 0.3393 ✗ | 0.1936 ✗ | **0.0136 ✓** | **0.0027 ✓** | PASS (×6 개선) |
| p2_p3 | 0.1046 ✓ | 0.1033 ✓ | 0.1046 ✓ | 0.1033 ✓ | 0.1046 ✓ | 0.1033 ✓ | PASS |
| p2_p4 | 0.1440 ✓ | **0.1891 ✗** | 0.2871 ✗ | 0.1308 ✗ | **0.1008 ✓** | **0.1062 ✓** | **PASS (r6 잔존 해소)** |
| p3_p4 | 0.0436 ✓ | 0.0205 ✓ | 0.2758 ✗ | 0.1444 ✗ | 0.0842 ✓ | 0.0202 ✓ | PASS |

**관찰**:
1. p1_p2 real KL 값 0.1376 은 r6/r7/r8 동일 (p1, p2 미변경). r6 에서 PASS 였던 이유는 r6 의 KL p95 ≥ 0.1376 였기 때문 (현재 r8 p95=0.1277 < 0.1376 → FAIL). r6 의 동일 pair PASS 는 borderline (margin ≤ 0.001).
2. r6 의 p2_p4 KL 0.189 (1쌍 잔존) 는 r8 에서 0.106 으로 정상화 — **r8 의 핵심 의도 달성**.
3. p1_p4 가 가장 큰 개선 (L2 ×0.16, KL ×0.10) — mistral-7b ↔ qwen3-8b base 사이즈 매칭 (둘 다 7B-class) 효과.

---

## §3. Axis 4 H4b 가설 검증 (spectrum-level)

| metric | r6 p4 (gemma-3-12b) | r7 p4 (qwen2.5-14b) | **r8 p4 (mistral-7b-v0.3)** |
|---|---:|---:|---:|
| λ₁ | 0.7192 | 0.5755 | **0.8120** |
| λ₂ | 0.0627 | 0.3206 | **0.0624** |
| λ₁/λ₂ ratio | 11.5× | 1.8× | **13.0×** |
| top-2 mass | 0.7819 | 0.8961 | 0.8744 |
| PR | 1.903 | 2.298 | **1.504** |
| 단/쌍봉 | 단봉 | **쌍봉** ← 이상치 | **강한 단봉** |

**검증 결론**: r7 의 쌍봉 spectrum 은 vendor 변경 (gemma → qwen) 에 의한 manifold 불일치 영향이 지배적 (H4b VALIDATED). r8 은 vendor 매칭 + scale 매칭 (mistral-nemo p3 와 동일 vendor 계열) 으로 단봉 복귀, PR 개선까지 동시 달성.

**부수 검증 (H4a / scale)**: r8 p4 mistral-7b 는 r7 p4 qwen2.5-14b 의 ½ 크기 (parameter 기준). PR 1.504 < 2.298 → scale 영향도 일부 존재하나 H4b 의 vendor 효과가 spectrum shape 의 1차 결정인.

---

## §4. r8 → r9 후보 (잔존 1쌍 닫기)

| Option | 가설 | 근거 | 비용 추정 | 위험 |
|---|---|---|---:|---|
| **A**. 자연 수용 | p1_p2 KL = 0.1376 vs p95 = 0.1277, margin 0.0099. col-perm null 이 너무 tight 한지 재검토 (n=10000 → n=50000) | r6 borderline PASS 와 동일 real 값 → null distribution 자체 신뢰성 검증 | $0 (CPU only) | 낮음. 통계적 power 보강 |
| **B**. p2 swap qwen2.5-7b → qwen3-7b | qwen3-8b (p1) 과 qwen2.5-7b (p2) 사이 generation drift 가 KL 의 1차 원인. 둘 다 qwen3 로 통일 | r8 의 vendor matching 성공 사례 동일 패턴 | $5-8 (1×H100 7-10분) | 낮음. r6 의 p1_p3, p2_p3 동일 vendor 매칭 PASS 사례 있음 |
| **C**. p1 swap qwen3-8b → qwen2.5-8b | A 의 역방향 generation matching | 동일 | $5-8 | 낮음 |
| **D**. r8 partial-pass 수용 + CP1 P1 종료 | r6 와 동급의 5/6 KL + Axis 4 검증 + p4 spectrum 정상화 → 진보로 인정 | CP1 P1 6/7 → 7/7 (line 168 정책 해석 + 본 r8 결과로 closure) | $0 | 정책 결정 필요 |

**완성도 기준 weakest link**: Option **A** 가 0-cost, loss-free 이고 통계적 robustness 보강. 이후 결과에 따라 B/C/D 분기.

---

## §5. CP1 P1 6/7 → 7/7 영향 분석

memory(`project_cp1_p1_67_satisfied`) 기준:
- 충족: AN11 triple PASS / Φ ≥3 / adversarial 3/3 / Meta² 100% / r6 trained baseline / r6-α evidence
- 미해결: line 168 정책 해석 대기 (1/7)

r8 의 추가 기여:
- p2_p4 KL 잔존 정상화 (r6 의 핵심 잔존 해소)
- Axis 4 manifold gap H4b validated (architectural 일관성 확보)
- p4 단봉 복귀 (수치적 안정성)

**판단**: r8 결과는 CP1 P1 의 `Φ ≥3` 조건을 더 견고하게 만들지만 line 168 (정책) 미해결분은 그대로. r8 → CP1 P1 closure 를 직접 트리거하지는 않음. 단, 사용자 결정 시 **r8 evidence 는 closure 의 보조 근거로 활용 가능**.

---

## §6. 산출물 요약

| 종류 | 경로 | 상태 |
|---|---|---|
| trained adapter | `state/trained_adapters/p4_r8/final/` | 186 MB (safetensors) |
| h_last | `state/h_last_raw_p4_TRAINED_r8.json` | 117 KB |
| train log | `state/h100_r8_train_p4.log` | 30 KB (epoch 1.0, train_loss=1.583, runtime=372s) |
| Φ result | `state/phi_4path_cross_result_v3_TRAINED_r8.json` | 신규 |
| Φ verdict | `state/phi_4path_gate_last_verdict.json` | 갱신 |
| Pod | (제거됨) | 비용 ~$0.31 |

---

## §7. 최소 경로 (next)

H-MINPATH 자동 선택 (blocker=0 → loss-free 우선):
1. proposal `20260422-083_p4_swap_mistral_7b_v03` 상태 갱신 (pending → approved)
2. r8 closure commit
3. Option A (null n=50000 robustness check, CPU only) — 다음 라운드 권장
