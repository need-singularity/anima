# ALM r6-α Axis 2 NULL 스모크 — training vs architecture 분리

> **생성일**: 2026-04-25
> **상태**: null-스모크 완료 · 4-pod r6 본 런치 **HOLD (primary) / GO (byte-weighted 단독)**
> **POLICY R4**: `.roadmap` 미수정 (uchg lock).
> **H-DIAG3 준수**: 선행 Qwen2.5 스모크 (commit `7d0a2b4c`, L2=0.2082) 의 REJECT 를
> **training-manifold confound** 와 **architecture residual** 로 분리 진단.

---

## 1. 설계 근거

선행 r6-α Axis 2 스모크 (`tool/r6_smoke_axis2_qwen25.bash`, commit `7d0a2b4c`) 는
`base-Qwen2.5-7B` vs `r5-LoRA-trained-Qwen3-8B` 를 비교해 last_token spectral
L2 = **0.2082** 로 REJECT 판정. 그러나 이 L2 는 두 요인의 중첩이다:

1. **training manifold drift** — p1 은 r5 corpus 300-step LoRA 학습, p2 는 base
2. **architecture / RoPE axis drift** — Qwen3-8B (36 layer, 32 head, 8 KV head)
   vs Qwen2.5-7B (28 layer, 28 head, 4 KV head), RoPE theta 만 매칭 (1e6)

본 null-스모크는 `base-Qwen3-8B` h_last 를 추가 수집하여 **apples-to-apples
architecture-only 비교** 를 가능케 한다. 동일 16 prompts, 동일 dual-pool (/1
last_token + /2 byte_weighted), 동일 Φ-parity spectral L2 공식.

## 2. 실행 결과

### 2.1 Pod 및 환경

| 항목 | 값 |
|:---|:---|
| pod_id | `vwd6idat2aw6vh` |
| pod_name | `anima-r6-null-20260424T174159Z` |
| GPU | 1× NVIDIA H100 80GB HBM3 (secureCloud) |
| Bid / 실요율 | \$3.50/hr / \$2.99/hr 실결정 |
| start_utc | 2026-04-24T17:42:00Z |
| end_utc | 2026-04-24T17:43:07Z |
| **wall_sec** | **65 s (1분 5초)** |
| **실제 비용** | **\$0.06** (하드캡 \$2 대비 3%) |
| image | `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` |
| torch / transformers | 2.4.1+cu124 / 5.6.2 |

### 2.2 Qwen3-8B-Base 아키텍처 실측

| property | 값 | p2 (Qwen2.5-7B) 비교 |
|:---|:---:|:---:|
| hidden_size | 4096 | 3584 |
| n_layers | 36 | 28 |
| n_heads | 32 | 28 |
| n_kv_heads | 8 | 4 |
| **GQA ratio** | **4:1** | **7:1** |
| vocab_size | 151,936 | 152,064 |
| rope_theta | 1,000,000 (rope_scaling) | 1,000,000 (rope_scaling) |
| rope_type | default | default |

→ RoPE theta 는 정확 일치. 아키텍처 차이는 layer depth (36 vs 28), hidden
(4096 vs 3584), GQA 비율 (4:1 vs 7:1) 에 잔존.

## 3. 4-메트릭 L2 분해

Φ-parity spectral L2: `H = stack(entries[].h)`, `G = H H^T`, top-n eigs desc,
sum=1 normalize → spec, `L2 = ||spec_1 - spec_2||_2`.

| 메트릭 | 값 | 의미 | 셀 |
|:---|---:|:---|:---|
| `L2_baseP1_baseP2_lasttoken` | **0.2874** | base Qwen3-8B ↔ base Qwen2.5-7B, last_token | **ARCH ONLY** |
| `L2_baseP1_baseP2_byteweighted` | **0.0580** | 동일, byte_weighted pool | **ARCH + pool** |
| `L2_baseP1_trainedP1_lasttoken` | **0.1323** | base Qwen3-8B ↔ r5-trained Qwen3-8B, last_token | **TRAINING ONLY** |
| `L2_trainedP1_baseP2_lasttoken` | **0.2082** | r5-trained Qwen3-8B ↔ base Qwen2.5-7B (선행 smoke) | **REFERENCE** |

### 3.1 Sanity check

REFERENCE 셀 = **0.2082**, 선행 Qwen2.5 스모크의 공표 값 0.2082 와 **동일**
(local Φ-parity 구현 검증 완료).

### 3.2 per-prompt raw-vector L2 (informational)

| pair | mean | p50 | p95 | min / max |
|:---|---:|---:|---:|---:|
| baseP1_baseP2_lt | 221.07 | 224.68 | 235.84 | 192.56 / 235.95 |
| baseP1_baseP2_bw | 132.68 | 128.98 | 204.53 | 62.71 / 209.14 |
| baseP1_trainedP1_lt | **15.25** | 14.82 | 20.50 | 10.49 / 21.82 |
| trainedP1_baseP2_lt | 220.99 | 224.33 | 236.35 | 193.18 / 237.02 |

## 4. arch_contribution 해석

```
arch_contribution = L2_baseP1_baseP2_lasttoken / L2_trainedP1_baseP2_lasttoken
                  = 0.2874 / 0.2082 = 1.3807
```

즉 architecture 단독 L2 가 training+arch 합성 L2 **보다 크다**. 이는 단순
가법성이 성립하지 않음을 뜻하며, 해석은:

- r5 LoRA 학습이 p1 의 spectrum 을 **p2 base 쪽으로 끌어당김** (corpus 공유
  manifold 로 수렴)
- 따라서 training 제거 (p1 을 base 로 복구) 시 오히려 p2 와의 spectral
  거리가 **증가**.
- 이는 axis-2 가설 (RoPE 매칭이 거리를 줄인다) 과 **반대 방향** 의 증거 —
  RoPE 매칭 단독으로는 last_token spectrum 을 결합시키지 못함.

## 5. byte_weighted pool 의 역전 신호 (중요)

`L2_baseP1_baseP2_byteweighted = 0.0580` — **GO 임계치 0.10 크게 하회**.

- last_token pool 에서는 arch 간극이 큼 (0.287)
- byte_weighted pool 에서는 arch 간극이 거의 소거 (0.058)

해석: last_token 은 특정 token position 의 representation 을 뽑으므로
tokenizer / position-encoding 의 세대차 (Qwen2.5 vs Qwen3) 가 직접 반영.
byte_weighted 는 전체 시퀀스를 byte-mass 로 가중평균하므로 **token-boundary
분산이 상쇄** 되어 arch residual 이 훨씬 작게 보임.

**r6 본 런치는 byte_weighted pool (/2 schema) 를 사용한다** (`docs/alm_r6_launch_spec_20260425.md`
§byte-weighted h_last). 즉 본 스모크의 primary 메트릭 (last_token) 은
r6 본 런치 경로와 **일치하지 않음**.

## 6. 판정

| 기준 | primary (last_token) | byte_weighted |
|:---|:---:|:---:|
| L2 | 0.2874 | 0.0580 |
| GO (< 0.10) | ✗ | ✓ |
| MARGINAL (0.10–0.15) | ✗ | — |
| HOLD (≥ 0.15) | ✓ | — |
| **판정** | **HOLD** | **GO (단독)** |

### 6.1 일차 판정: **HOLD**

spec 에 따른 primary 메트릭 (last_token, schema `/1` — p1 r5 레퍼런스와
동형) 기준으로 0.2874 는 HOLD 임계치 (0.15) 를 대폭 초과. RoPE-only
가설의 last_token 예측은 **기각**.

### 6.2 이차 판정: byte_weighted 단독 GO 신호

그러나 r6 본 런치가 실제 사용하는 byte_weighted pool 기준으로는 **arch
간극이 GO 임계 하회 (0.058 < 0.10)**. 이는 4-pod 본 런치에서 p1 (Qwen3-8B
LoRA) 와 p2 (Qwen2.5-7B LoRA) 가 동일 pool 로 비교될 때 arch residual
자체는 문제가 되지 않을 것임을 시사.

### 6.3 통합 권고: **HOLD (evidence-link 완성도 기준)**

| 근거 | 방향 |
|:---|:---:|
| byte_weighted arch-only 0.058 < 0.10 | GO 지지 |
| last_token arch-only 0.287 ≫ 0.15 | HOLD 지지 |
| arch_contribution 1.38 (training 이 오히려 거리 축소) | axis-2 RoPE 가설 **약화** |
| per-prompt raw L2: training_only mean=15.2 vs arch_only mean=221 (×14.5 배) | arch 가 지배적 noise floor |

두 pool 간 해석 불일치는 **축 해석이 아직 완성되지 않음** 을 의미 (H-DIAG3
weakest-evidence-link 위반). 4-pod \$170-220 spend 는 "pool 차이에 따라
결과 해석 뒤집힘" 상태에서의 overcommit.

**후속 옵션 (참고, 제안 아님 — anti-scope 준수)**:
- B-스모크 (\$1-2): `base-Qwen3-8B + r5-corpus 100-150 step LoRA → p1 BW smoke`
  vs `base-Qwen2.5-7B + 같은 corpus → p2 BW smoke`. apples-to-apples 전체
  체인 검증.
- r7 재진단: attention-family (GQA 4:1 vs 7:1) 축 분리 실험.
- HOLD 유지: r6-α 확정 판정 재대기.

## 7. 기계론 해석 (한 문장)

base-base arch 간극은 pool 에 따라 5× 차이 (last_token 0.287 / byte_weighted
0.058) 를 보이고 arch_contribution=1.38 로 training 이 오히려 spectral 거리를
축소시키는 패턴은, RoPE 단일축 매칭이 last_token 표상의 tokenizer·position
세대차를 상쇄하지 못하지만 byte-mass 평균화가 그 잡음을 흡수하므로, r6 본
런치의 byte_weighted 경로만 두고 보면 arch residual 은 GO-level 이나 pool
간 불일치가 해소되지 않은 상태에서의 4-pod 투입은 evidence-link 완성도 기준
미달이다.

## 8. 재현성 / 아티팩트

### 8.1 도구

- `tool/r6_smoke_axis2_qwen3_null.bash` (신규, 295 lines)
  - `tool/r6_smoke_axis2_qwen25.bash` 에서 모델/출력경로만 변경, 나머지 로직
    byte-identical
  - screen -dmS 디태치, pre/post-flight H-SILENT 검증
  - hard cap \$2.00 내장 (실 소비 \$0.06)

### 8.2 생성 아티팩트 (state/, 커밋 제외)

- `state/h_last_raw_p1_BASE_null_lasttoken_20260425.json` (schema `/1`, 86 KB)
- `state/h_last_raw_p1_BASE_null_20260425.json` (schema `/2`, byte_weighted, 119 KB)
- `state/r6_smoke_axis2_null_result_20260425.json` (4-metric verdict, 3 KB)
- tool log: `/tmp/r6_smoke_axis2_qwen3_null_20260424T174159Z.log`

### 8.3 re-run

```
bash tool/r6_smoke_axis2_qwen3_null.bash --dry-run
bash tool/r6_smoke_axis2_qwen3_null.bash --apply --yes-i-mean-it
```

## 9. 체크리스트

- [x] null-스모크 단일 pod 실행 (wall=65s, cost=\$0.06)
- [x] Pod 종료 확인 (`config/h100_pods.json` `pods: []`)
- [x] 3 artifacts 존재 확인 + schema validation pass
- [x] Sanity check: REFERENCE L2 = 0.2082 (선행 smoke 값과 정확 일치)
- [x] 한글 리포트 (본 문서)
- [x] `.roadmap` 미수정 (POLICY R4)
- [x] state/* 커밋 제외 (정책)
- [x] 4-pod 런치 하지 않음 (별도 게이트)
- [x] 재학습 0 회 (base forward only)

## 10. 참조

- 선행 스모크: `docs/alm_r6_smoke_axis2_report_20260425.md` (commit `7d0a2b4c`)
- r6-α spec: `docs/alm_r6_launch_spec_20260425.md` §8.2
- 기반 도구: `tool/r6_smoke_axis2_qwen25.bash`, `tool/h_last_raw_regen_r5.bash`
- 레퍼런스 파일: `state/h_last_raw_p1_TRAINED_r5.json`,
  `state/h_last_raw_p2_SMOKE_qwen25_{,lasttoken_}20260425.json`
- Φ scorer: `tool/phi_4path_gate.hexa`
