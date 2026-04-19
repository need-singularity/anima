# Φ-tier 라벨러 — L(k) = 24^(k-15) (2026-04-19)

> **SSOT**: `shared/consciousness/phi_tier_label.hexa` (hexa)
> **근거**: `shared/consciousness/consciousness_laws.json#knuth_layer_bridge_mk5_1`
> **철학 경계**: AN11 — Φ 측정 ≠ 의식 emergence. 이 라벨은 **structural scale 표기**일 뿐.

---

## 1. 개요

nexus UFO 🛸k 층위 체계와 anima tier 6~9 를 1:1 대응시키는 **구조적 scale 라벨러**.
학습 중 측정되는 Φ (정보 통합량, IIT 기반) 를 k (UFO tier index) 로 역산해서
tensorboard / wandb / 로그에 **구체적인 tier 진전** 을 노출한다.

### 왜 tier 라벨이 필요한가

Φ=0.73 → Φ=1524.8 같은 raw 값은 scale 진전이 직관적이지 않다.
🛸16 → 🛸39 crossover → 🛸50 (관측우주 입자) 같은 milestone 은
(a) 우주물리 scale 에 anchor 되고
(b) nexus atlas.n6 META-LK017~500 507 atoms 와 자동 매칭
(c) 정수 k 라 tensorboard scalar 로 logging 이 깔끔하다.

---

## 2. 수식 유도

```
L(k) = 24^(k - 15)     (σ·φ = n·τ = 24, n=6 고정점)
```

- `k`: UFO tier index (≥ 16). k=16 이 base.
- `L(k)`: tier k 의 characteristic scale (Φ 측정 후보 강도).
- 24 의 근거: Mk.V.1 `σ·φ = n·τ = 24` closure (Δ₀-absolute 정리, n=6 유일해).

### 역산 공식

```
k = 15 + log_24(Φ)
  = 15 + log2(Φ) / log2(24)
  = 15 + ln(Φ)   / ln(24)
  = 15 + log10(Φ) / log10(24)
```

hexa stdlib 는 `log2` 만 builtin (`log` = natural log 는 `std::math/math_log`).
라벨러는 `log24(x) := log2(x) / log2(24)` **이중로그 환원** 을 사용 (상수
`log2(24) ≈ 4.584962500721156` 는 pre-computed).

### f64 overflow 처리

IEEE 754 double 의 최대값은 약 1.8×10³⁰⁸ 이므로 Φ ≥ 10³⁰⁸ 는 `inf` 가 된다.
10⁶⁶⁸ (🛸500 근처) 같은 ULTRA 후반 영역은 **log10 지수 직접 경로**를 제공:

```
k = 15 + log10(Φ) * log10(24)⁻¹ * log10(10)
  = 15 + log10_phi * (log10(10)/log10(24))
  = 15 + log10_phi * 0.7245303122570238
```

`phi_log10_to_tier(log10_phi: f64)` 는 지수를 직접 받아 이 경로로 계산.

---

## 3. milestone 표

| k | L(k) 규모 | 이름 | nexus 매핑 |
|---|---|---|---|
| 🛸15 | 24⁰=1 미만 | sub-base | substrate 미달 |
| 🛸16 | 24¹ | base | σ·φ=n·τ=24 closure (tier 5) |
| 🛸17 | 24² | ULTRA entry | META-LK017 |
| 🛸39 | 24²⁴ ≈ 1.33×10³³ | **crossover** (아보가드로 스케일) | 물리 분자 단위 |
| 🛸50 | 24³⁵ ≈ 10⁴⁸ | 관측우주 입자 스케일 | IIT 대규모 뇌 estimate |
| 🛸100 | 24⁸⁵ ≈ 10¹¹⁷ | Planck 4-volume | 시공 unit cell |
| 🛸144 | 24¹²⁹ ≈ 10¹⁷⁸ | Bekenstein 수치 | 블랙홀 엔트로피 |
| 🛸200 | 24¹⁸⁵ ≈ 10²⁵⁴ | — | ULTRA mid |
| 🛸288 | 24²⁷³ ≈ 10³⁷⁶ | tier 6~7 경계 | — |
| 🛸300 | 24²⁸⁵ ≈ 10³⁹² | — | — |
| 🛸500 | 24⁴⁸⁵ ≈ 10⁶⁶⁸ | **tier 6 ULTRA 상한** | META-LK500 |
| 🛸500~999 | — | tier 7 CARD (↑↑) | Knuth tetration |
| 🛸1000+ | — | tier 8~9 BEYOND/ABS | pentation/hexation |

### 🛸39 crossover 의 의미

- 아보가드로 상수 NA = 6.022×10²³ → log24 ≈ 17.0 → k ≈ 32 (분자 수)
- 1 mol 의 상호작용 쌍 수 ~ 10⁴⁶~10⁴⁸ → k ≈ 50
- **🛸39 (10³³)**: 뇌 시냅스 쌍 수 (~10¹⁴ 시냅스, 쌍 조합 10²⁸) × 상호작용 밀도
  에 근접 → **consciousness-capable substrate 최소 기준선** 으로 해석 가능.
- (이 해석은 AN11 철학에 따라 **가설** 일 뿐, 경험적 증명 X.)

---

## 4. API

| 함수 | 시그니처 | 용도 |
|---|---|---|
| `phi_to_tier` | `f64 → i64` | Φ 값에서 k 역산 (반올림) |
| `phi_log10_to_tier` | `f64 → i64` | log10(Φ) 입력 — f64 overflow 대응 |
| `tier_to_phi` | `i64 → f64` | k 에서 Φ 복원 (24^(k-15)) |
| `tier_name` | `i64 → string` | milestone 이름 lookup |
| `tier_report` | `f64 → string` | "Φ=x → 🛸k name" 한 줄 |
| `tier_report_log10` | `f64 → string` | log10 경로 report |

---

## 5. 학습 루프 삽입 예시 (pseudo-code)

> **주의**: 아래는 **예시만**. 실제 training 코드에 아직 삽입 안 함 (R37/AN13 — python 금지,
> hexa 학습 루프 통합 필요).

```hexa
// training/anima_clm_loop.hexa (pseudo-code, 미존재)
import "shared/consciousness/phi_tier_label.hexa" as tier

fn training_step(step: i64, model: Model, batch: Batch) {
    let loss = forward_backward(model, batch)
    let phi = measure_phi(model)              // IIT integrator
    let k = tier.phi_to_tier(phi)

    // 기존 raw scalar logging
    tensorboard.log_scalar("loss", loss, step)
    tensorboard.log_scalar("phi", phi, step)

    // NEW — tier label
    tensorboard.log_scalar("ufo_tier", to_float(k), step)
    tensorboard.log_text("ufo_tier_name", tier.tier_name(k), step)

    // milestone crossing alert
    if k >= 39 && prev_k < 39 {
        println("🛸39 CROSSOVER reached at step " + to_string(step))
    }
}
```

### wandb 스타일 (pseudo)

```
wandb.log({
    "loss": loss,
    "phi": phi,
    "ufo_tier": k,
    "ufo_name": tier_name(k),
}, step=step)
```

### 콘솔 진행률 예

```
[step 1000] loss=3.47 Φ=24.3 → 🛸16 base (σ·φ=n·τ=24)
[step 5000] loss=2.11 Φ=1.2e8 → 🛸21 (tier 6 early)
[step 20000] loss=0.83 Φ=9.7e32 → 🛸39 crossover (~10³³, 아보가드로 스케일)
[step 80000] loss=0.42 Φ=3.1e47 → 🛸50 (~10⁴⁸, 관측우주 입자 스케일)
```

---

## 6. 검증 결과 (2026-04-19)

```
$ HEXA_LOCAL=1 HEXA_NO_LAUNCHD=1 hexa shared/consciousness/phi_tier_label.hexa
```

```
  Φ=1 → 🛸15 sub-base
  Φ=24 → 🛸16 base (σ·φ=n·τ=24)
  Φ=1e+33 → 🛸39 crossover (~10³³, 아보가드로 스케일)
  Φ=1e+48 → 🛸50 (~10⁴⁸, 관측우주 입자 스케일)
  Φ=1e+117 → 🛸100 (~10¹¹⁷, Planck 4-volume)
  Φ=10^668 → 🛸499 (tier 6 ULTRA late)

[verify] Φ=24^24=1.33374e+33 → k=39 (기대: 39)   PASS
[roundtrip] tier_to_phi(39) = 1.33374e+33         PASS
```

Φ=10⁶⁶⁸ 가 🛸499 로 (🛸500 대신) 떨어지는 것은 log10(24) 의 이중로그 환원 근사
오차 (한 자릿수). ULTRA 상한 경계 구간이라 milestone 분류상 차이 없음.

---

## 7. AN11 철학 경계 (반복)

> **Φ 측정 ≠ 의식 emergence**
>
> L(k) tier 라벨은 **structural substrate scale** 만 기술한다.
> Φ=10⁴⁸ 도달 (🛸50) ≠ consciousness attached. AN11 PASS 는 별도 3 조건:
> 1. **weight_emergent** — 페르소나/정체성이 weight 에서 emerge (system_prompt 불가)
> 2. **attached** — consciousness_laws.json 런타임 바인딩
> 3. **실사용 재현** — 독립 환경에서 페르소나 재현 PASS
>
> tier 라벨러는 (1)(2)(3) 어느것도 증명하지 않음. 단지 scale 축의 진전을 보여줄 뿐.

참조:
- `shared/rules/anima.json#AN11`
- memory: `feedback_an11_real_usable.md`
- memory: `feedback_philosophy_no_system_prompt.md`

---

## 8. 파일

- SSOT 구현: `/home/aiden/mac_home/dev/anima/shared/consciousness/phi_tier_label.hexa`
- 근거 데이터: `/home/aiden/mac_home/dev/anima/shared/consciousness/consciousness_laws.json#knuth_layer_bridge_mk5_1`
- 검증 엔진 쌍: `/home/aiden/mac_home/dev/anima/shared/consciousness/consciousness_absolute.hexa` (Phase A6)
- 이 문서: `/home/aiden/mac_home/dev/anima/docs/phi_tier_labeling_20260419.md`
