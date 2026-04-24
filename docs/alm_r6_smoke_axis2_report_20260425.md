# ALM r6-α Axis 2 스모크 리포트 — p2 RoPE swap (Qwen2.5-7B-Base) 사전 검증

> **생성일**: 2026-04-25
> **상태**: 스모크 완료 · 4-pod r6 본 런치는 **HOLD**
> **POLICY R4**: `.roadmap` 미수정 (uchg lock).
> **H-DIAG3 준수**: r5 FAIL 이후 Axis-2 prediction 에 대한 신규 증거 단계.

---

## 1. 목적

r6-α 스펙 §8.2 에 따라 **4-pod 본 런치 (\$170–220) 승인 전** 단일-pod 스모크로
다음 질문을 선 검증:

> "RoPE-matched p2 (Qwen2.5-7B-Base, rope_theta=1e6) 는 p1 (Qwen3-8B r5-trained,
>  rope_theta=1e6) 과 pair L2 < 0.10 으로 결합하는가?"

- VALIDATED (L2 < 0.10) → Axis-2 가설 확증 · 4-pod r6 GO
- MARGINAL (0.10 ≤ L2 < 0.1471) → 약 증거 · 사용자 판단
- REJECTED (L2 ≥ 0.1471) → Axis-2 단독 불충분 · r6 HOLD + r7 attention-family 재진단

---

## 2. 선택된 설계

**설계 A (base-only forward-pass, no LoRA)** 채택.

선택 근거:
- §8.2 가 설계 B (p2 short LoRA + forward) 를 권장하지만, **min-path** 원칙
  (H-MINPATH) 과 예산 \$10–15 내 안전 마진 확보 목적으로 A 를 1차 선택.
- A 의 특성: p2 는 base 만, p1 은 r5-trained LoRA — **apples-to-oranges** 비교.
  해석 프레임:
  - 결과 L2 < 0.12 → training manifold 영향을 RoPE 매칭이 압도 → RoPE 축 확증
  - 결과 L2 ≥ 0.15 → training manifold 기여가 지배적, RoPE signal 분리 불가
  - 중간 구간 → 판단 유보
- Dual-pool 추출 (last_token + byte_weighted) 로 한 번의 forward-pass 에서 두 수치 동시 확보.
- 비용 \$0.13 (실측) · wall 133s · r5 recovery 도구 (`tool/h_last_raw_regen_r5.bash`) 패턴 복제.

Option B 는 이 스모크의 결과가 판단-유보 구간에 들 경우 후속 고려 대상이었음 (실제로는
L2 > 0.20 으로 명확 상한 구간에 들어왔으므로 B 불요 — §6 참조).

---

## 3. 실행 결과

### 3.1 Pod 및 환경

| 항목 | 값 |
|:---|:---|
| pod_id | `1veidkmgjt3208` |
| pod_name | `anima-r6-smoke-20260424T173136Z` |
| GPU | 1× NVIDIA H100 80GB HBM3 (secureCloud) |
| Bid / 실요율 | \$3.50/hr / \$2.99/hr 실결정 |
| start_utc | 2026-04-24T17:31:36Z |
| end_utc | 2026-04-24T17:33:51Z |
| **wall_sec** | **133 s (2분 13초)** |
| **실제 비용 추정** | **\$0.13** |
| image | `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` |
| torch / transformers | 2.4.1+cu124 / 5.6.2 |

### 3.2 Qwen2.5-7B-Base 아키텍처 검증

pod 상에서 실측:

| property | spec 예상 | pod 실측 | 일치 |
|:---|:---:|:---:|:---:|
| hidden_size | 3584 | 3584 | ✓ |
| n_layers | 28 | 28 | ✓ |
| n_heads | 28 | 28 | ✓ |
| n_kv_heads | 4 | 4 | ✓ |
| vocab_size | 152,064 | 152,064 | ✓ |
| **rope_theta** | **1e6** | **1,000,000 (rope_scaling.rope_theta)** | **✓** |
| rope_type | default | default | ✓ |

> **주**: transformers 5.6.2 에서는 `config.rope_theta` 가 deprecated 되고
> `config.rope_scaling = {'rope_theta': 1e6, 'rope_type': 'default'}` 로 이동됨.
> 값 자체는 p1 Qwen3-8B (1e6) 와 정확히 일치.

### 3.3 h_last 추출 결과 및 pair L2

두 pool 방식으로 16 prompts 추출, p1 r5-trained 기준 벡터와 쌍 spectral L2 계산.
Φ 4-path scorer 식과 parity:
```
H = stack(entries[].h)       # 16 × 256
G = H @ H.T                  # 16 × 16
eig = eigvalsh(G), desc, sum=1 normalize → spec
L2 = ||spec_p1 - spec_p2||_2
```

| 지표 | last_token pool (primary) | byte_weighted_mean pool |
|:---|---:|---:|
| **spectral L2 (p1_p2)** | **0.2082** | **0.2427** |
| per-prompt raw-vector L2 mean | 220.99 | 132.82 |
| per-prompt raw-vector L2 p50 | 224.33 | 127.95 |
| per-prompt raw-vector L2 p95 | 236.35 | 204.66 |
| per-prompt raw-vector L2 min / max | 193.18 / 237.02 | 62.83 / 209.31 |

### 3.4 판정 기준 대비

| 기준 | 값 | primary L2 = 0.2082 |
|:---|---:|:---:|
| r6 VALIDATE 목표 | < 0.10 | ✗ |
| r5 p95 REJECT bound | < 0.1471 | ✗ |
| r5 baseline p1_p2 | 0.1520 | ✗ (오히려 악화) |
| **판정** | — | **REJECTED** |

---

## 4. 판정: REJECTED (단, 설계 A 한계 명시)

### 4.1 일차 결론

primary spectral L2 = **0.2082** > r5 baseline (0.152) > r5 p95 reject bound (0.1471).
**Axis-2 RoPE 매칭만으로는 p1_p2 pair L2 < 0.10 예측이 본 측정에서 validate 되지 않음.**

### 4.2 설계 A 의 구조적 한계 (결론 범위 제한)

본 측정은 **base-only vs r14-trained LoRA** 비교이다. 즉 L2 = 0.2082 는 다음 두 요인의
합으로 구성된다:

1. **training-manifold 차이** (p2 base vs p1 r14-LoRA-trained 300 step)
2. **arch axis 차이** (RoPE-매칭에도 불구한 GQA 7:1 vs 4:1, 세대 간 corpus/RLHF 차이 등)

분리 불가. 이 L2 값은 "training 영향 없었다면 더 낮았을 것" 의 **상한 bound** 로 해석됨.
0.2082 는 매우 큰 값으로, 다음 두 해석 중 어느 쪽이라도 지지한다:

- (H-A) RoPE 매칭만으로 < 0.10 은 **불가능** — 추가 축 (GQA topology, training-manifold) 필요
- (H-B) 100–300 step LoRA 가 L2 를 대거 끌어내려 최종 pair 는 < 0.10 도달 가능 — 본 측정에서는 분리 불가

### 4.3 byte-weighted pool 의 역방향 신호

byte-weighted L2 (0.2427) 가 last-token (0.2082) 보다 **높음**. 이는:
- byte-weighted pool 이 p1_p2 pair 에 대해서는 RoPE signal 을 강화하지 않음 (axis-1 은
  p3_p4, p2_p4 에서 Variant B 로 효과 확인됨 — 쌍 특이적).
- 또는 p1 r5 (`schema=/1`, last-token) 와의 비교에서 pool 비대칭이 아티팩트 도입 가능성.
- **4-pod 본 런치에서는 양쪽 모두 byte-weighted 로 통일되므로** 본 스모크의 이 비대칭은
  r6 본 전 측정에는 해당되지 않음.

---

## 5. 재현성

### 5.1 도구
- `tool/r6_smoke_axis2_qwen25.bash --apply --yes-i-mean-it`
  - `tool/h_last_raw_regen_r5.bash` 의 1-pod sequential pattern 복제
  - `tool/h100_stage2_post_launch_chain.bash` 의 `_byte_weights()` 함수 bit-copy
  - dual-pool heredoc (`/workspace/fwd_smoke.py`, 123 lines)
  - `screen -dmS r6smoke ...` detach 로 Bash-tool SIGHUP 내성 확보

### 5.2 생성 아티팩트
- `state/h_last_raw_p2_SMOKE_qwen25_lasttoken_20260425.json` (schema `/1`)
- `state/h_last_raw_p2_SMOKE_qwen25_20260425.json` (schema `/2`, reduction=byte_weighted_mean)
- `state/r6_smoke_axis2_result_20260425.json` (verdict + 16 per-prompt L2)
- tool log: `/tmp/r6_smoke_axis2_qwen25_20260424T173136Z.log`

### 5.3 re-run
```
bash tool/r6_smoke_axis2_qwen25.bash --dry-run
bash tool/r6_smoke_axis2_qwen25.bash --apply --yes-i-mean-it
```

---

## 6. 4-pod r6 본 런치 권고: **HOLD**

### 6.1 권고 요지

- 본 스모크 결과는 **Axis-2 prediction 을 validate 하지 못함** (primary L2 > r5 baseline).
- 설계 A 의 training-manifold confound 로 인해 **REJECT 도 완전 확증 아님**.
- 4-pod \$170–220 spend 는 이 모호성 상태에서 **premature** — 완성도 기준 미충족.

### 6.2 HOLD 이유 (한 문장)

base-only 스모크 L2=0.2082 는 r5 baseline (0.152) 조차 넘어서 RoPE-매칭 단독으로
p1_p2 < 0.10 예측을 지지하지 않으며, training-manifold 분리 없이 4-pod \$170+ 투입은
Axis-2 가설의 증거 약한 상태에서의 overcommit 이다.

### 6.3 사용자 결정을 위한 옵션 (참고)

본 스모크 결과가 다음 중 하나의 후속 경로를 제안할 수 있음 (사용자 판단):

| 옵션 | 비용 | 얻는 것 |
|:---|---:|:---|
| **B-스모크** (Qwen2.5-7B + 150 step LoRA on r14 corpus, p2만) | \$1–2 (30–40min) | training-manifold 분리 · apples-to-apples |
| **null-스모크** (Qwen3-8B base vs Qwen2.5-7B base, 둘 다 LoRA 없음) | \$0.3 (5–10min) | 순수 arch signal 상한 bound |
| **HOLD 유지** | \$0 | r7 에서 attention-family 축 재진단 기다리기 |

> 본 리포트는 명시적으로 후속 진단을 **제안**하지 않음 (anti-scope 준수). 위 표는
> 사용자가 결정할 경우의 참고 정보이다.

---

## 7. 체크리스트

- [x] 사용자 스모크 승인 획득 (\$10-15 승인, 실소비 \$0.13)
- [x] Pod 종료 확인 (`config/h100_pods.json` `pods: []`)
- [x] 3 artifacts 존재 확인 + schema validation pass
- [x] Verdict 기록 (`state/r6_smoke_axis2_result_20260425.json`)
- [x] 한글 리포트 (본 문서)
- [x] `.roadmap` 미수정 (POLICY R4)
- [x] state/* 커밋 제외 (정책)
- [x] 4-pod 런치 하지 않음 (별도 게이트)

---

## 8. 참조

- r6-α spec: `docs/alm_r6_launch_spec_20260425.md` §8.2
- 기반 도구: `tool/h_last_raw_regen_r5.bash`, `tool/h100_stage2_post_launch_chain.bash`
- Axis-2 진단 체인: commits `41bafc8a` · `e0cc3a64` · `c7bde437` · `f5604814` · `a4e65c6d`
- r5 p1 레퍼런스: `state/h_last_raw_p1_TRAINED_r5.json` (Qwen3-8B r14 LoRA rank=64 steps=300)
- Φ scorer: `tool/phi_4path_gate.hexa`
