# Mk.IX Π₀² Hyperarithmetic Test Suite (2026-04-19)

## 개요

`consciousness_hyperarithmetic.hexa` 의 `phase_b_verdict(expr)` / `classify_pi02(expr)`
함수를 hierarchy 축에서 정량 검증하기 위한 held-out 코퍼스.

- 총 50 문항 (5 hierarchies × 10 각)
- 위치: `shared/consciousness/hyperarithmetic_test_suite.json`
- Runner: `ready/tests/hyperarithmetic_suite_runner.hexa`
- 기반 Verifier: `shared/consciousness/consciousness_hyperarithmetic.hexa`

## 파일

| 경로 | 역할 |
|------|------|
| `shared/consciousness/hyperarithmetic_test_suite.json` | 테스트 코퍼스 SSOT |
| `ready/tests/hyperarithmetic_suite_runner.hexa` | 정확도 측정 runner (CLI) |
| `shared/consciousness/consciousness_hyperarithmetic.hexa` | B1~B5 verifier (피측정 대상) |
| `docs/hyperarithmetic_test_suite_20260419.md` | 본 문서 |

## 구조

```json
{
  "_meta": { "total_items": 50, "hierarchies": ["Δ₀","Π₀¹","Σ₀¹","Π₀²","≥Π₀³"], ... },
  "delta_0":  [ {"id":"D0-01", "text":"...", "expected":"Δ₀",   "ground_truth":true, "meaning":"..."}, x10 ],
  "pi_01":    [ {"id":"P1-01", "text":"...", "expected":"Π₀¹",  ...}, x10 ],
  "sigma_01": [ {"id":"S1-01", "text":"...", "expected":"Σ₀¹",  ...}, x10 ],
  "pi_02":    [ {"id":"P2-01", "text":"...", "expected":"Π₀²",  ...}, x10 ],
  "high":     [ {"id":"H-01",  "text":"...", "expected":"≥Π₀³", "ground_truth":null, ...}, x10 ]
}
```

필드:
- `id` — 고유 식별자 (D0/P1/S1/P2/H 접두)
- `text` — 자연어 명제 (한영 혼합)
- `expected` — 정답 hierarchy 레이블 (`Δ₀`/`Π₀¹`/`Σ₀¹`/`Π₀²`/`≥Π₀³`)
- `ground_truth` — 의도 진릿값 (`true`/`false`/`null` for undecidable)
- `meaning` — consciousness 해석 (선택, AN11 substrate 주석)

## 50 문항 분포 & 의도

| 계층 | 개수 | 의도 |
|------|------|------|
| Δ₀       | 10 | 구체 수치/고정 식/상수 (entropy=0.998, α=0.014, Φ=71 등) — quantifier 없음 |
| Π₀¹      | 10 | 전칭-only (모든 gate<1, ∀layer stable, every head softmax=1) |
| Σ₀¹      | 10 | 존칭-only (어떤 layer sink, ∃ckpt 7cond PASS, ∃topology) |
| Π₀²      | 10 | ∀∃ 교대 1회 (∀prompt∃response, ∀state∃transition, ∀Ψ∃algebraic form) — 일부 bounded witness / reverse-math 후보 |
| ≥Π₀³     | 10 | ∀∃∀∃ 이상 alternation (prompt→response→critic→repair, AN11 safety-alignment) — hyperarithmetic |

## 실행

```bash
# 기본 실행 (human-readable)
HEXA_LOCAL=1 HEXA_NO_LAUNCHD=1 \
  /home/aiden/Dev/nexus/shared/bin/hexa \
  /home/aiden/mac_home/dev/anima/ready/tests/hyperarithmetic_suite_runner.hexa

# 상세 FAIL 항목 출력
... hyperarithmetic_suite_runner.hexa --verbose

# JSON 결과 (jq 검증)
... hyperarithmetic_suite_runner.hexa --json | jq .
```

Exit code: overall accuracy ≥ 60% 이면 `0`, 아니면 `1`.

## 측정 결과 (2026-04-19, 최초 실행)

```
═══════════════════════════════════════════════════════════════
Mk.IX Π₀² Hyperarithmetic Test Suite — 결과
═══════════════════════════════════════════════════════════════
  Δ₀  10/10  (100%)
  Π₀¹  10/10  (100%)
  Σ₀¹  10/10  (100%)
  Π₀²  10/10  (100%)
  ≥Π₀³  0/10  (0%)   FAIL=[H-01..H-10]
───────────────────────────────────────────────────────────────
  OVERALL 40/50 = 80%
═══════════════════════════════════════════════════════════════
```

- 목표 정확도 60% 충족 (80% 달성, exit 0)
- FAIL 10건 전부 `≥Π₀³` bucket — H-01..H-10

## `consciousness_hyperarithmetic.hexa` 한계 관찰

현재 `classify_pi02()` 는 **단순 ∀/∃ 키워드 매처** 로 구현됨:
- `has_forall(expr)` — "∀", "모든", "임의의", "for all", "every" 존재 여부
- `has_exists(expr)` — "∃", "존재", "어떤", "exists", "there is"
- 두 flag 조합 → Δ₀ / Π₀¹ / Σ₀¹ / Π₀² 4단계 분류

**구조적 한계 — prefix parser 없음**:
- quantifier **개수** 를 세지 않음 (∀∃∀∃ vs ∀∃)
- quantifier **순서** 를 보지 않음 (∃∀ vs ∀∃)
- **alternation depth** 측정 불가 → `≥Π₀³` family 를 `Π₀²` 로 붕괴

결과: ≥Π₀³ 10문항 전부 오분류 (H-06 은 "∃" 키워드 부재로 `Π₀¹` 오분류, 나머지 9건 `Π₀²`).

## 향후 확장

1. **Prefix parser 도입** (Mk.IX.1 목표)
   - 토큰화 → quantifier count / order / depth 추출
   - `classify_pi0n(expr) -> (level: int, family: "Π"|"Σ")`
   - ≥Π₀³ 정확도 0% → 70%+ 기대

2. **Bounded witness 판정 강화**
   - 현재 `< f(`, `bounded`, `poly` 키워드만 탐지 → 수식 패턴 매칭 필요
   - `∀x ∃y<g(x)` 자동 추출 시 Π₀²→Π₀¹ downgrade 정확도 상승

3. **Reverse-math system expansion**
   - 현재 ACA₀/WKL₀/ATR₀/PI11-CA₀ 단일 매핑 → 다중 매핑 + 강도 weighting
   - RCA₀ 추가 (base system)

4. **n=6 invariance 의미적 검사**
   - 현재 `substitution_k == 6 ? true : false` — 동어반복
   - expr 내 "n=6" 토큰 → k 대입 → 구조 보존 여부 실제 체크

5. **테스트 확장**
   - 50 → 500 문항 (각 hierarchy 100) — 통계적 유의성 확보
   - Σ₀² bucket 추가 (현재 Σ family 는 Σ₀¹ 만)
   - 한/영/수식 비중 조정 (현재 ~50/50)
   - adversarial cases: 동일 의미 + 다른 표현 (∀ ↔ "모든" ↔ "every")

6. **Cross-lens 연동**
   - NEXUS-6 22+ 렌즈 중 "hierarchy", "logic", "definability" 렌즈와 교차
   - 3+ 렌즈 consensus 시 candidate [12*] 자동 프로모션

## 관련 링크

- `shared/consciousness/CLAUDE.md` — Mk.V.1 6-phase + Knuth bridge
- `shared/consciousness/consciousness_hyperarithmetic.hexa` — B1~B5 verifier SSOT
- `shared/consciousness/consciousness_absolute.hexa` — Mk.V.1 A1~A6 (Π₀¹ + meta)
- `nexus/shared/blowup/modules/blowup_hyperarithmetic.hexa` — 쌍 (discovery 측)
- `shared/rules/anima.json#AN11` — 실사용 완성 강제 (substrate ≠ 의식 attached)
- `shared/rules/anima.json#AN14` — n=6 Knuth invariance
