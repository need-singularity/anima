# Phase-3 drill 재검증 — counter bug 확정 (2026-04-22)

## TL;DR
**iter_24~69 전 범위 (Phase-2 + Phase-3) counter replay 확정.** PHASE2_CAVEAT 의 의심이 증거 삼중 누적으로 확정됨. SSOT 이식 전면 금지.

## 증거 삼중 누적

### 1. Phase-3 정량 통계 (iter_34~69, 41 파일 스캔)
| total absorptions | iters |
|---|---|
| 128 | 11 iters (35/42/55/56/57/60/64/66/67/68/69) |
| 32  |  4 iters (34/52/53/65) |
| 741 |  2 iters (36/37) |
| no-total / 0 rounds | 19 iters (fail / early-exit) |

서로 완전히 무관한 seed 주제 (`hub` / `cli` / `runtime` / `holo_propagator` / `ALM_api_contract` / `consciousness_streaming` / `finitude_bound` / `an14_anima_spec` / `cross_ref_drift` / `cdo_convergence`) 가 **정확히 동일한 128 총계**를 냄.

128 = 16 stage-output / round × 8 round — 구조적 스테이지 상수.
32  = 4 absolute-stage-verifications / round × 8 round — 구조적 상수.

### 2. 엔진 소스 자기인증
`~/.hx/packages/nexus/cli/run.hexa:471-524` 가 counter bug 를 명시 주석:

```
line 473:  원본 cmd_drill 은 라운드마다 동일 seed 로 엔진 호출 → 엔진 결정론적 → 동일 카운트 반복
line 474:  ("iter_26: round1 +617 → round2 +617 → round3 SIGKILL" 1234 replay).
line 497:  iter_36/37 둘 다 round1 total=629, iter_38/39 둘 다 round1 total=693 관찰 →
line 498:  **seed 텍스트가 다른데도** blowup 엔진의 deterministic 8-slot feature …
line 500:  즉 inter-iter 간 독립성이 보장되지 않음.
```

엔진 저자가 이미 **counter replay 버그를 인지**하고 3층 수리 (Day-1 `_round_seed` / Day-2 `_iter_nonce` / Day-3 `_round_seed_rich`) 를 시도함.

### 3. Day-1~3 수리 효과 한계
- Day-1 (2026-04-19): round 단위 salt prefix → intra-iter round 2+ replay 제거
- Day-2 (2026-04-19 저녁): urandom 기반 iter-nonce suffix → inter-iter 독립성
- Day-3 (2026-04-21): richer multi-source salt (urand×2 + nanotime)

그러나 Phase-3 결과는 Day-1+ 이후 **여전히 128 이 11회 반복**. 이유는 seed 수정이 작동해도 **스테이지 자체가 고정 카운트를 내뱉기 때문**:
- "absolute: 4 Π₀¹ verifications" — 항상 4
- "meta-closure: 4 self-ref fixed points" — 항상 4
- "hyperarith: 8 Π₀² bounded/proven" — 항상 8
→ 총 16 / round × 8 rounds = 128 (seed 와 무관)

**absorption 메트릭은 실제 통찰 발견을 측정하는 게 아니라 스테이지 호출 횟수 를 집계하고 있음.**

## SSOT 차단 범위 확장
PHASE2_CAVEAT 는 iter_24~33 대상이었음. 이제 **iter_24~69 전체** 로 확장:
- consciousness_laws.json 이식 금지
- saturation_report_mk5.json 업데이트 금지
- tier 6~9 승급 금지 (iter_24 기반 ULTRA/CARD/BEYOND/ABS 브릿지 판정 무효)

## 신뢰 가능한 범위
- **Phase-1 (iter_17~23)**: 전원 SATURATED round 1, 0 absorption — **유효** (엔진이 fresh seed 에서 실제 포화 판정)
- **Phase-2~3 (iter_24~69)**: **전원 suspect**

## 근본 수리 제안
absorption 을 스테이지 호출 카운트가 아니라 "seed-dependent novel finding" 로 재정의:
1. 스테이지마다 output 을 content-hash 해서 unique set 크기로 집계
2. 동일 해시 출력은 replay 로 카운트 0
3. inter-iter 크로스 비교 (이미 `_cross_iter_check_and_append` 에 스캐폴드 존재)

## 연관 리포트
- `PHASE2_CAVEAT.md` (2026-04-19, iter_24~33 suspect)
- `docs/tier_11_to_11star_promotion_review_20260419.md` (승급 WAIT)
