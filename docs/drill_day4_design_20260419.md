# Drill Engine Day-4 Fix — Design Draft (조건부 실행, 2026-04-19)

> **상태**: DESIGN-ONLY. P3 drill (hetzner drill_v3 PID 4140597) 결과 수신 전에는 구현 금지.
> **베이스**: Day-3 `nexus/05efd2f4` — iter-nonce per-slot direct mix into `seed_to_features` (φ-residue).

---

## 1. 트리거 조건 (둘 중 하나 충족 시 Day-4 착수)

| 조건 | 관측 지점 | 임계값 | 의미 |
|---|---|---|---|
| T-A | P3 log `cross-iter replay-warn` 발화 | 1회 이상 | Day-3 mix 로도 iter-간 fuzzy-hash 재흡수 |
| T-B | P3 `seed_n6_ratio` 분포 | std < 0.05 **or** 동일-값 clustering ≥ 40% | 8D basis 의 non-orthogonality 로 mix 가 dot product 에서 상쇄 |

둘 다 음성이면 Day-3 로 동결 (Day-4 미실시, 자원 회수).

---

## 2. 핵심 진단 — 왜 Day-3 만으로 부족할 수 있는가

`seed_n6_ratio(s)` 는 8-slot feature 와 basis 의 **내적** (blowup.hexa L492-L509).

```
ratio = Σ feat[i] · basis[i]
basis = [1.0, 1.414, 0.577, 2.449, 0.25, 0.5, 0.167, 0.25]
```

- Day-3 가 8개 슬롯에 독립 residue `r_i = _slot_nonce_mix(nonce, i) ∈ [0,1)` 를 주입했지만,
- `_frac01` 이 `feat[i] + r_i ∈ [0,2)` 를 **[0,1) 로 collapse** → slot 간 확산이 단일 축 값으로 뭉개짐.
- basis weight 합 = 6.107 (비-정규, √6 dominant) → **slot 3 (√6=2.449)** 이 dot product 의 40% 차지.
  nonce mix 가 slot 3 에서 fmod-wrap 하면, 해당 iter 의 ratio shift 가 ±0.2 이내로 축소 가능.
- 결과: `seed_n6_ratio` 가 iter 간 여전히 유사 → h3_core6_cross_seed.hexa:202 parser 는 단일
  scalar 만 읽으므로 Day-3 의 8D 확산이 **관측 가능한 diversity 로 전달되지 않음**.

---

## 3. Day-4 설계 — 6→8 축 독립 stretch

### 3.1 목표

8개 slot 의 residue 가 **상쇄되지 않고** ratio 에 전파되도록, basis 를 **직교 사상**으로 재설계.

### 3.2 설계안 A (추천) — per-slot independent rank rotation

```
// Day-4: basis orthogonalization + nonce-dependent phase rotation
fn seed_n6_ratio_v4(s: string) -> f64 {
    let feat  = seed_to_features(s)          // Day-3 mix 유지
    let nonce = _extract_iter_nonce(s)
    // 6→8 축 확장: n=6, τ=4, σ=12, φ=4 canonical 유지 (σ·φ=n·τ=24 불변)
    // basis orthogonal: 각 축이 φ-residue 로 회전된 독립 directional vector
    let basis = [
        1.0,                          // constant (n=6 anchor)
        _phase_unit(nonce, 0),        // cos(2π · nonce_hash(0) / N)
        _phase_unit(nonce, 1),        // cos(2π · nonce_hash(1) / N)
        _phase_unit(nonce, 2),
        0.25, 0.5, 0.1667, 0.25       // σ/φ/τ ratio 블록 (불변 baseline)
    ]
    // 중요: feat[i] 는 _frac01 collapse 이전의 raw (feat_raw[i] ∈ [0,2)) 를 직접 사용
    let feat_raw = seed_to_features_raw(s)   // 신규 — _frac01 미적용
    let mut dot = 0.0
    let mut i: i64 = 0
    while i < 8 {
        dot = dot + to_float(feat_raw[i]) * to_float(basis[i])
        i = i + 1
    }
    return dot
}
```

- `seed_to_features_raw` 신설: Day-3 의 `_frac01` 을 **건너뛴** 원본 sum 반환 (신규 fn, 기존 `seed_to_features` 무변경).
- `_phase_unit(nonce, k)` = `cos(2π · _slot_nonce_mix(nonce, k+4))` — slot 4–7 의 φ-residue 를 phase 로 재활용.
- basis[0,4–7] 은 Day-3 이전 baseline 그대로 → n=6, σ·φ=n·τ=24 canonical 보존.

### 3.3 설계안 B (백업) — fmod-wrap 제거 + basis L1 normalize

- `_frac01` 대신 `_soft_clip(x) = tanh(x - 0.5) · 0.5 + 0.5` 로 wrap-collapse 회피.
- basis 를 L1=1 로 정규화 (`[0.164, 0.232, 0.095, 0.401, 0.041, 0.082, 0.027, 0.041]` → `/ 1.083`).
- 장점: 기존 parser (h3_core6:202) 가 읽는 `seed_n6_ratio` 스케일 [0,1] 로 축소 → log diff 민감도 상승.
- 단점: 과거 iter 1–33 과 scalar 호환성 깨짐 (역사 데이터 재해석 필요).

**권장**: A 우선, B 는 A smoke fail 시 fallback.

---

## 4. fmod-into-[0,1] collapse 회피 3-layer 가드

1. **raw 계층 유지**: `seed_to_features_raw` 는 `_frac01` 미적용 → 풀스케일 `[0, 2.0)` 보존.
2. **basis re-weight**: Day-4 basis 에서 √6 (2.449) 같은 dominant term 완화 → slot 간 weight 균등.
3. **phase-rotation**: nonce-dependent `cos(·)` 로 dot product 에 **부호 진동** 주입 → 동일 raw 입력이라도 iter 별 ratio 분기.

---

## 5. h3_core6_cross_seed.hexa:202 stdout parser 영향

L202 의 파서는 단순 `line.contains("seed_n6_ratio=")` 후 첫 토큰 `to_float` — **포맷 불변**.
- Day-4 는 `seed_n6_ratio()` 반환 스칼라만 변경 → parser 수정 0.
- 단, 설계안 B 채택 시 스케일이 [1.0, 2.0] → [0.0, 1.0] 으로 축소 → S9 gate G3 (Spearman |ρ|>0.5)
  의 순위 구조는 유지되지만, 절대 분포 관찰하는 downstream 로그에 **단위 변환 주석** 필요.
- mock_blowup (L256–L258) 의 `ratio = 1.0 + (sh%10000)/10000` 도 [1.0,2.0] 가정 → Day-4 A 는 영향 無,
  B 채택 시 mock 도 동반 수정.

---

## 6. 불변식 체크리스트

- [ ] n=6, σ=12, φ=4, τ=4 (σ·φ=n·τ=24) canonical 식별 번호 보존 — basis slot 4–7 불변.
- [ ] Day-1 round-salt PREFIX, Day-2 `#iter-nonce=<N>` SUFFIX 호환 — suffix 제거 시 nonce=0 → basis 정적 → Day-3 이하 동일.
- [ ] `blowup.hexa` 외 수정 無 — L0 골화 파일 불변 (seed_engine.hexa, run.hexa, h3_core6 건드리지 않음).
- [ ] Smoke: iter 34–40 simulate, 동일 base seed + 7 nonces → `seed_n6_ratio` std ≥ 0.15 (Day-3 관측치 × 3).

---

## 7. 실행 체크포인트 (P3 결과 수신 후)

1. P3 로그에서 replay-warn grep → T-A 판정.
2. `seed_n6_ratio` 분포 히스토그램 → T-B 판정.
3. 트리거 양성 시: 설계안 A 로 `blowup.hexa` 패치 (≤80 LOC diff), nexus 브랜치 `drill-day4` 에 격리.
4. Mac smoke (`/tmp/day4_test.hexa`) 통과 후 hetzner 재배포, drill_v4 PID 기록.
5. 실패 시 설계안 B 로 fallback, 여전히 실패 시 drill 엔진 축 개수 자체를 8→12 확장하는 Day-5 설계 진입.

---

**END** — 실구현은 P3 결과 확인 후 유저 승인 받아 착수.
