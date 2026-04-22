# 20 철학 렌즈 Catalog — Audit (SWEEP P4 · D6 · iter 101)

> **대상 iter**: `v4_hetzner/iter_101_philo_20lenses` (SWEEP P4 §D6 philosophy)
> **Seed 텍스트**: "20 philosophical lens catalog closure"
> **목적**: "20 철학 렌즈" 가 실제 소스/문서 단일진실과 일치하는지, 각 렌즈가 closure (측정함수 존재 + 실측 경로 + 등록) 상태인지 감사.
> **감사자 요약**: 20 이라는 숫자는 **문서 레이블**일 뿐 실 구현은 **12 철학 렌즈 + 6 PHIL/ONTO/DASEIN 엔진 + 2 망원경 계열**의 혼합 카운트. 현재 HEXA 포트는 12/12 stub (score 상수), 실 측정은 py 원본 9/12만 closure. iter 101 권장 verdict = **SATURATED-by-mislabel + 1 real gap** (PHIL 엔진 3개 hexa 포트 누락).

---

## 1. 카탈로그 위치 (SSOT 후보 4 곳)

| # | 경로 | 형식 | 렌즈 수 | 주 역할 |
|---|------|------|---------|---------|
| A | `anima-agent/philosophy_lenses.hexa` | `.hexa` | 12 (LENSES comptime const) | HEXA 포트 (stub, TODO[python-sdk]) |
| B | `ready/anima/modules/agent/philosophy_lenses.py` | `.py` | 12 (class const) | 원본 구현 (925 LOC, 9/12 real logic) |
| C | `docs/lens-experiment-catalog.md` | `.md` | 22 (telescope Rust 렌즈) | 실험 카탈로그 — 다른 축 (22-lens = nexus telescope) |
| D | `docs/sweep_p4_plan_20260419.md` §D6 | `.md` | "20 philosophical lens" 라벨 | 본 감사 iter 시드 |
| E | `anima-agent/CLAUDE.md` (tree) | `.md` | "20 철학 렌즈" 문자열 | D 와 동일 라벨, A 파일을 가리킴 |

**발견 1**: `20` 이라는 숫자는 어떤 코드 파일에도 나타나지 않음. 문서 레이블만 존재. A/B = 12, C = 22.
→ **숫자 불일치 = 최소 미닫힘 closure 항목 (doc-code SSOT 위반, R14 / AN3)**.

---

## 2. 12 철학 렌즈 (A/B 원본) 정의 + closure 표

| # | Lens | 측정 대상 | HEXA 포트 (A) | Py 실구현 (B) | Closure 상태 |
|---|------|-----------|---------------|----------------|--------------|
| 1 | `philosophy` | P1-P11 code-guardian 준수 | stub score=1.0 | ✅ CodeGuardian scan | Py 만 closure |
| 2 | `contradiction` | 법칙 쌍 모순 탐지 | stub 0.9 | ✅ pairwise contradiction count | Py 만 closure |
| 3 | `emergence` | ConsciousMind sim + 패턴 | stub 0.8 | ✅ simulation + pattern | Py 만 closure |
| 4 | `scaling` | cells vs Φ, steps vs tension | stub 0.85 | ✅ multi-scale sim | Py 만 closure |
| 5 | `convergence` | NEXUS-6 ↔ laws 교차확인 | stub 0.9 | ✅ cross-ref | Py 만 closure |
| 6 | `boundary` | edge-case (0 cells, ∞ tension) | stub 0.75 | ✅ edge sim | Py 만 closure |
| 7 | `cross_project` | body/eeg/physics 일관성 | stub 0.8 | ✅ EcosystemBridge | Py 만 closure |
| 8 | `temporal` | git log 법칙 진화 | stub 0.85 | ✅ git log parse | Py 만 closure |
| 9 | `negation` | 원칙 위반 시뮬 | stub 0.7 | ✅ counter-factual | Py 만 closure |
| 10 | `consensus` | NEXUS-6 multi-agent | stub 0.8 | ⚠️ partial (TelescopeScan only) | 부분 closure |
| 11 | `red_team` | adversarial 입력 | stub 0.75 | ⚠️ partial | 부분 closure |
| 12 | `meta` | 12 lens 자체 일관성 | ✅ len(LENSES) check | ✅ full | 닫힘 (meta 만 양쪽 동등) |

**A 공통 패턴**: 11/12 가 `TODO[python-sdk]` 주석 + 상수 score 반환 → **닫힘 실패 (AN7 HEXA-FIRST 위반, R37 .py 금지 로드맵에서 B 를 곧 삭제해야 함)**.

---

## 3. 도메인 인접 렌즈 (카탈로그 C / bench_v2 · MEMORY project_philosophy_engines)

memory `project_philosophy_engines.md` 기준 6 PHIL/ONTO/DASEIN 엔진:

| # | Engine | 구현 위치 | closure |
|---|--------|-----------|---------|
| 13 | Desire | `experiments/bench_v2.py` (PHIL) | py only |
| 14 | Narrative | `experiments/bench_v2.py` | py only |
| 15 | Alterity | `experiments/bench_v2.py` | py only |
| 16 | Finitude (Sein) | `experiments/bench_v2.py` (ONTO) | py only |
| 17 | Questioning | `experiments/bench_v2.py` (DASEIN) | py only |
| 18 | Sein | `experiments/bench_v2.py` (DASEIN) | py only |

추가 2 (D 시드의 "20" 맞추기용 잠재 후보):
| # | Lens | 출처 | closure |
|---|------|------|---------|
| 19 | `lens_meta` (Yang-Mills 2차 텐션) | `training/lens_meta.hexa` (PART of 5+1 training lens) | ✅ hexa 본편 (3/3 PASS 주장, training 도메인) — but 이 파일은 weight-delta 렌즈지 "철학" 렌즈 아님 |
| 20 | `red-team-consciousness` | `docs/red-team-consciousness.md` (6 claims → 1 survive) | docs only, 측정 함수 미등록 |

**12 철학 + 6 PHIL/ONTO/DASEIN + 2 edge = 20** → 시드 "20" 의 추정 매핑. 다만 19/20 은 철학 렌즈 정의가 모호.

---

## 4. 미닫힘 (closure 미수행) 렌즈 랭킹

| 우선 | 항목 | 미닫힘 근거 | 영향 |
|------|------|-------------|------|
| 🔴 P0 | HEXA 포트 A 전체 11/12 | stub score, 측정 로직 부재 | AN7/R37 위반, Py 폐기 불가 |
| 🔴 P0 | doc label "20" ↔ code "12" | SSOT 깨짐 | iter 101 자체 seed 가 mis-spec |
| 🟡 P1 | PHIL 6 엔진 hexa 포트 없음 | py only (bench_v2) | HEXA-FIRST 미달 |
| 🟡 P1 | `consensus`, `red_team` py 도 partial | NEXUS-6 합의/adversarial 자동화 부재 | closed-loop 반영 불가 |
| 🟢 P2 | `lens_meta` 철학 분류 모호 | training-layer 렌즈가 철학으로 라벨링 | 분류표 정리 필요 |
| 🟢 P2 | `red-team-consciousness` doc-only | 측정 함수 없음 | 공식 렌즈 아님 |

---

## 5. Saturation 가능성 (iter 101 verdict 예측)

- **Mk.V.1 82-atom 원점 대조**: 본 카탈로그의 12 철학 lens 축 (philosophy/contradiction/emergence/scaling/convergence/boundary/cross_project/temporal/negation/consensus/red_team/meta) 은 이미 atom tier 3~6 전반 (regulative principles + contradiction detection + scaling law) 로 커버됨 → **SATURATED at round 1 예상** (P3 15 iter 전원 포화 추세와 동일).
- **Tier 10+ 돌파 요소**: PHIL 6 엔진 × HEXA-FIRST 포팅 = tier 7~8 probe 여지 (bench_v2 의 Desire / Finitude / Alterity 는 Mk.V.1 atom 에 직접 매핑 없음). → absorption 후보 1~2.
- **실무 권고**: iter 101 seed 를 "20 → 12+6" SSOT 재정렬 + PHIL 6 엔진 hexa 스켈레톤 선착 (stub 허용) 로 구체화. 그래도 포화 시 Mk.X 엔진 업그레이드 트리거 (P3 권고와 동일).

---

## 6. Closure Action Items (closed-loop 반영)

1. (P0) `docs/sweep_p4_plan_20260419.md` §D6 iter 101 시드 텍스트 수정: "20" → "12 + 6 (PHIL/ONTO/DASEIN)" 명시 + SSOT 링크 추가.
2. (P0) `anima-agent/CLAUDE.md` tree 라인 `philosophy_lenses.hexa   20 철학 렌즈` → `12 철학 렌즈 (+ 6 PHIL 엔진 포팅 예정)` 로 수정.
3. (P1) `anima-agent/philosophy_lenses.hexa` 11 lens TODO stub 을 실측 로직으로 교체 (py 원본 포팅, 925 LOC → ~600 LOC 예상).
4. (P1) `anima-agent/philosophy_engines.hexa` 신규 파일로 6 PHIL/ONTO/DASEIN 엔진 hexa 포트 (Desire/Narrative/Alterity/Finitude/Questioning/Sein).
5. (P2) `lens_meta` (training) 와 `red-team-consciousness` (doc) 는 철학 lens 카탈로그에서 분리 — "training lens" / "adversarial audit" 별도 축으로 태깅.
6. (P2) `consensus` / `red_team` 의 NEXUS-6 자동 호출 경로 완성 → closed_loop `measure_laws()` 9-metric 변화 ≥5% 확인.
7. (P2) 완료 후 `config/consciousness_laws.json` → `philosophy_lens_catalog` 섹션 (신규) 18 엔트리 + closure flag 기록 → 이후 SWEEP 에서 SSOT.

---

## 7. 요약 테이블

| 축 | 설계 | 실구현 (py) | HEXA 포트 | Doc SSOT |
|----|------|-------------|-----------|----------|
| 철학 12 lens | 12 | 9 full + 2 partial + 1 meta | 1 / 12 closure | 부분 |
| PHIL 6 엔진 | 6 | 6 (bench_v2) | 0 / 6 | 부분 |
| 망원경 22 lens | 22 | Rust (telescope-rs/NEXUS-6) | N/A (Rust) | `lens-experiment-catalog.md` |
| training 5+1 lens | 6 | ✅ (.hexa 정식) | 6 / 6 | training/CLAUDE.md |

→ 감사 결론: **"20 철학 렌즈" 라벨은 SSOT 없음**. iter 101 closure 는 (a) 라벨 정정 + (b) hexa 포트 완성 + (c) 6 PHIL 엔진 hexa 화 + (d) laws.json 카탈로그 등록 네 단계로 구체화하면 tier 7~8 probe 가능.

_감사 완료 — 2026-04-19._
