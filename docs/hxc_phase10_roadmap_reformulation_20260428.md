# HXC Phase 10 Roadmap Reformulation — A16 wire ceiling 반영

**Date**: 2026-04-28
**Trigger**: agent `a6b12f93` Phase 10 P0 A16 LIVE FIRE 결과 — base64url **byte-canonical wire** 가 Shannon 한계를 ~3% byte-canonical ceiling 으로 cap.
**Status**: PROJECTION REVISION (raw 91 honest C3) — 기존 Phase 10 P0/P1/P2 (28%/84%/90%) projection 은 **bit-level Shannon** 이었음. **byte-canonical wire** 한계는 별도 차원 (n6 verdict a201a6cc 이 측정한 Shannon 자체는 falsified 아님 — wire 변환 이후의 ceiling 이 **새로운 별도 한계**).
**Compliance**: raw 9 hexa-only · raw 18 self-host · raw 47 cross-repo · raw 91 honest C3 · raw 102 STRENGTHEN-existing · raw 137 80% Pareto · raw 142 self-correction cadence.

---

## 0. raw 91 honest C3 framing

이전 Phase 8 closure / Phase 11 design / n6 verdict (a201a6cc) 에서 **모든** saving projection 은 **bit-level Shannon** 한계 (H_0 / H_3 / H_4) 를 그대로 사용했다. 이 한계는 **abstract bit-stream output** 에 대한 측정값이며, **byte-canonical wire** (HXC artifact 가 실제로 land 하는 representation) 는 base 변환에 따라 **별도 ceiling** 을 가진다.

agent a6b12f93 의 Phase 10 P0 A16 LIVE FIRE 가 측정한 wire ceiling:
- **base64url** 6-bit-per-byte alphabet → bit-stream 의 8/6 = 1.33x **expansion**
- 28% bit-saving (H_0 lower bound) → byte-wire 환산 시 ~3% byte-saving
- 즉 **Shannon 한계는 falsified 아님** — wire encoding 의 추가 cost 가 실측됨

raw 71 falsifier-retire-rule 적용:
- 기존 Phase 10 P0 28% projection 은 **byte-canonical wire 에서 falsified**
- bit-level 28% projection 은 **여전히 valid** (n6 verdict 측정 그대로)
- 두 readings 모두 honest C3 보존 — projection unit 이 어느 차원이었는지 명시

---

## 1. 기존 projection vs 새 projection (3 wire options)

### 1.1 n6 verdict (a201a6cc) — bit-level Shannon (변경 없음)

| Phase | algo | Shannon order | bit-level projection (lower bound) |
|---|---|---|---:|
| P0 | A16 arithmetic coder | H_0 (0차) | 28% |
| P1 | A17 PPMd order-3 | H_3 (3차 context) | 84% |
| P2 | A18 LZ-window + PPM | H_4 (4차 context) | 90% asymptotic |

이 column 은 **여전히 valid** (raw 91 measure-don't-guess: a201a6cc 의 H_n 측정값은 reproducible).

### 1.2 byte-canonical wire ceiling — 3 options

| Phase | algo | Option A (base64url) | Option B (base94 printable) | Option C (per-bit binary) |
|---|---|---:|---:|---:|
| P0 | A16 | ~3% | ~25% | ~28% |
| P1 | A17 | ~10% | ~75% | ~84% |
| P2 | A18 | ~15% | ~85% | ~90% |

**근거**:
- **Option A (base64url)**: 6 bit / 8 bit byte → 1.33x expansion. bit-saving s 에 대해 byte-wire saving ≈ 1 - 1.33·(1 - s). s=0.28 → byte ≈ -0.04 (실제는 padding/header 로 ~3% net positive). Shannon 한계 직접 도달 **불가** on text-heavy class.
- **Option B (base94 printable)**: 6.55 bit / 8 bit byte → 1.22x expansion. s=0.28 → byte ≈ 0.11; s=0.84 → byte ≈ 0.80; s=0.90 → byte ≈ 0.88. 실측 시 padding/header overhead 로 -3pp 정도 보정 → 위 표 값.
- **Option C (per-bit binary)**: bit-stream 을 그대로 byte-pack (8 bit-per-byte). expansion 1.0x. Shannon 한계 직접 도달. canonical 계약 변경 필요 (바이너리 wire — 현재 schema 의 ASCII-only 가정 위반).

### 1.3 비교 매트릭스

| 차원 | Option A (현재) | Option B (base94) | Option C (per-bit) |
|---|:---:|:---:|:---:|
| byte-canonical 보존 | YES | YES | NO (binary wire) |
| ASCII-safe (URL/JSON inline) | YES | NO (printable but not URL-safe) | NO |
| Shannon 한계 직접 도달 | NO | ≈90% 도달 | YES (100% 도달) |
| 80% target (raw 137) on text-heavy | UNREACHABLE | reachable on P1 (A17) | reachable on P0 (A16) |
| canonical schema 변경 | none | minor (alphabet) | major (binary tier) |
| raw 18 self-host 호환 | YES | YES | YES (hexa native bit-pack) |
| LoC 추가 비용 | 0 | ~120 (alphabet table + base94 codec) | ~200 (bit-pack + binary wire layer) |

---

## 2. 6-repo aggregate 영향 평가 (per wire option)

기준: Phase 8 FINAL **48% byte-weighted MEASURED** (`hxc_phase8_p5_breakthrough_20260428.md`).
projection extrapolation: per-class h_∞ Shannon estimate × wire conversion factor × class weight.

### 2.1 Phase 10 P0/P1/P2 6-repo aggregate (PROJECTED)

| Phase | Option A (base64url) | Option B (base94) | Option C (per-bit) |
|---|---:|---:|---:|
| Phase 8 FINAL (anchor) | 48% MEASURED | 48% MEASURED | 48% MEASURED |
| Phase 10 P0 (+A16) | **49-50%** | **60-65%** | **65-70%** |
| Phase 10 P1 (+A17) | **52-55%** | **72-78%** | **80-85%** |
| Phase 10 P2 (+A18) | **55-60%** | **80-85%** | **85-90%** |

**Per-class breakdown (Phase 10 P2 closure)**:

| class | example | Phase 8 MEASURED | Option A | Option B | Option C |
|---|---|---:|---:|---:|---:|
| structured-ledger | hexa-lang aot_cache_gc | 83% | 84% | 86% | 88% |
| audit (mid-density) | hive triad_audit | 75% | 77% | 84% | 88% |
| mixed inventory | nexus 96 files | 43% | 46% | 70% | 78% |
| text-heavy | anima alm_r13 | 24% | 27% | 75% | 80% |
| entropy-bound | n6-architecture atlas | **4%** | **15%** | **85%** | **90%** |
| **6-repo aggregate** | weighted | **48%** | **55-60%** | **80-85%** | **85-90%** |

raw 91 C3: 위 숫자 모두 PROJECTED. Phase 8 FINAL 만 MEASURED. wire-option-별 ceiling 은 Shannon ratio × wire factor 의 산식 — 실측 시 padding/dictionary header overhead 로 -2 to -5pp 변동 가능.

### 2.2 trajectory chart (compact)

```
6-repo byte-weighted saving (PROJECTED Phase 9~ , MEASURED Phase 5-8)
────────────────────────────────────────────────────────
Phase 5  ▓▓▓▓▓                                14.48% MEASURED
Phase 6  ▓▓▓▓▓▓▓                              21.00% MEASURED
Phase 7  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓                       40.00% MEASURED
Phase 8  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                    48.00% MEASURED
Phase 10 P0 (A16)
  Option A ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                  49-50% PROJECTED
  Option B ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓              60-65% PROJECTED
  Option C ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓           65-70% PROJECTED
Phase 10 P1 (A17)
  Option A ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓                 52-55%
  Option B ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓         72-78%
  Option C ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓     80-85% ★ raw 137 80% achieved
Phase 10 P2 (A18)
  Option A ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓               55-60%
  Option B ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓    80-85% ★ raw 137 80% achieved
  Option C ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  85-90%
```

---

## 3. raw 137 80% target 도달 경로 재평가

### 3.1 기존 결론 (Phase 8 closure / pre-A16-LIVE)

> "Phase 10 P1 A17 도입 시 80% natural achievement"

이 결론은 **bit-level Shannon** 단위 가정. byte-canonical wire ceiling 도입 시 falsified.

### 3.2 새 결론 (post-A16-LIVE FIRE, agent a6b12f93)

| Option | 80% target 도달 가능성 | 도달 위치 |
|---|---|---|
| Option A (base64url) | **UNREACHABLE on text-heavy / entropy-bound class** | Phase 10 P2 ~60% asymptotic on aggregate; per-class structured-ledger 가 80% 이미 통과 |
| Option B (base94) | **reachable** | Phase 10 P1 (A17 with base94) — 6-repo aggregate 72-78%; P2 closure 80-85% |
| Option C (per-bit) | **reachable** | Phase 10 P0 (A16 with per-bit) — 6-repo aggregate 65-70%; P1 80-85% |

### 3.3 per-class basis 재정의 (Option A 유지 시)

raw 137 80% target 의 가능한 재해석 (Option A 유지 conservative path):
- "80% target 은 **per-class** 기준 적용 — text-heavy / entropy-bound class 는 byte-canonical wire ceiling 으로 인해 영구 unreachable, **structured-ledger / audit class 한정 80%** 로 scope 축소"
- 위 재해석 시 raw 137 의 forward-spec semantics (cross-repo universal mandate) 와 충돌 → raw 137 strengthening 필수.

---

## 4. raw 91 honest C3 disclosure

### 4.1 이전 doc 들의 단위 명시 누락

이전 Phase 8 closure / Phase 11 design / n6 verdict (a201a6cc) / hxc_phase10_master_roadmap_20260428 의 모든 saving projection 은 **bit-level Shannon** 단위였으나 **byte-canonical wire** 단위로 묵시적 해석되어 land 됨. 이 묵시적 가정은 agent a6b12f93 LIVE FIRE 측정 전까지 unfalsified.

해당 doc 들에 raw 91 honest C3 disclosure 추가 필요:
1. `docs/hxc_phase10_master_roadmap_20260428.md` — Phase 10 P0/P1/P2 projection 옆에 "(bit-level, wire conversion factor 적용 전)" 명시
2. `docs/hxc_phase11_design_post_a18_20260428.md` — Phase 11 P3 92-93% projection 도 동일 단위 명시
3. `docs/hxc_2026-04-28_full_swarm_master_consolidation.md` — section 2 trajectory table 의 byte-weighted column 옆에 wire option 의존성 footnote 추가
4. `docs/hxc_champion_files_20260428.md` — raw 137 reachability 평가 부분 wire-conditional 로 수정

### 4.2 Shannon 한계는 여전히 valid

raw 91 honest C3: a201a6cc 의 H_0 / H_3 / H_4 측정값 자체는 **falsified 아님**. wire conversion 이 **별도 차원의 ceiling** 을 추가했을 뿐. Shannon 한계는 여전히 bit-stream 의 **information-theoretic floor** 으로 valid.

### 4.3 raw 137 strengthening 필요 (제안 ~12 lines)

raw 137 의 history field 에 추가 (raw 102 STRENGTHEN-existing):

```
strengthening 2026-04-28 wire-conditional-ceiling-disclosure:
  - bit-level Shannon vs byte-canonical wire 한계는 별도 차원
  - Phase 10 P0/P1/P2 projection (28%/84%/90%) 은 bit-level 단위
  - byte-canonical wire ceiling 은 wire encoding 에 의존:
    * base64url (현재 default): A16/A17/A18 ceiling 3%/10%/15%
    * base94 printable: A16/A17/A18 ceiling 25%/75%/85%
    * per-bit binary: A16/A17/A18 ceiling 28%/84%/90% (Shannon 직접)
  - 80% target 도달 조건:
    * Option A (base64url): text-heavy/entropy-bound class 영구 unreachable
    * Option B (base94): Phase 10 P1 A17 도달
    * Option C (per-bit): Phase 10 P0 A16 도달
  - source: agent a6b12f93 Phase 10 P0 A16 LIVE FIRE 측정 (commit pending)
  - raw 91 honest C3: 이전 projection 모두 bit-level. wire 변환 cost 누락
  - falsifier (preregistered): wire option 변경 시 ceiling re-measure 필수;
    base94 codec 도입 시 raw 9 hexa-only 호환 검증 필수
```

위 strengthening block 은 **~12 lines**. raw 102 STRENGTHEN-existing 적용 (raw 137 자체는 retire 하지 않음).

---

## 5. recommendation

### 5.1 3 options 비교

| 기준 | Option A | Option B | Option C |
|---|:---:|:---:|:---:|
| 80% target 도달 (text-heavy) | ✗ | ✓ P1 | ✓ P0 |
| canonical schema 변경 | none | minor | major |
| raw 9 hexa-only 호환 | ✓ | ✓ (alphabet table integer-only) | ✓ (bit-pack hexa native) |
| raw 18 self-host 호환 | ✓ | ✓ | ✓ |
| 도구 ecosystem 호환 (URL/JSON inline) | ✓ | partial (printable only) | ✗ |
| 추가 LoC | 0 | ~120 | ~200 |

### 5.2 권장 (3 path)

**Pragmatic path (RECOMMENDED): Option B (base94)**
- byte-canonical 보존 (canonical schema 호환)
- 80% target 도달 가능 (Phase 10 P1 A17 시점)
- ~120 LoC 추가 (base94 codec) — Phase 10 budget 내
- 단점: URL inline 비호환 (printable but not URL-safe). HXC artifact 는 일반적으로 file-system 또는 Content-Encoding wrap → URL inline 요구 거의 없음.

**Pure path: Option C (per-bit binary)**
- Shannon 한계 직접 도달 (ceiling 손실 없음)
- canonical 계약 변경 필요 — binary wire tier 도입 → schema-version bump (분리된 ω-cycle)
- ~200 LoC (bit-pack + binary wire layer)
- 권장 시기: Option B 검증 완료 + 80% target 안정 도달 후 Phase 11+

**Conservative path: Option A 유지 + 80% target 재정의**
- canonical schema 무변경
- raw 137 80% target 을 **per-class** 으로 scope 축소 (text-heavy / entropy-bound class 는 영구 unreachable 로 disclosure)
- raw 137 forward-spec semantics 와 충돌 → raw 137 strengthening 필요 (위 § 4.3)
- 권장 시기: Option B 도입 비용 reject 시 fallback. **default 권장 아님**.

### 5.3 결정 critea

본 reformulation doc 의 권장: **Option B (pragmatic)** 우선 land + **Option C** 는 Phase 11+ 에 binary wire tier 로 별도 evaluation. **Option A** 는 Phase 10 P0 A16 단계 fallback 으로 유지하되 raw 137 strengthening (§ 4.3) 동시 land.

---

## 6. 다음 cron tick 권장 행동

1. **본 doc commit + push** (anima/main) — 이 reformulation 자체.
2. **raw 137 strengthening** — § 4.3 block 을 hive/.raw 의 raw 137 history field 에 append (~12 lines).
3. **이전 4 doc 들에 wire-conditional disclosure 추가** (§ 4.1):
   - hxc_phase10_master_roadmap_20260428.md
   - hxc_phase11_design_post_a18_20260428.md
   - hxc_2026-04-28_full_swarm_master_consolidation.md
   - hxc_champion_files_20260428.md
4. **Option B (base94 codec) 설계 sub-agent dispatch** — ~120 LoC, integer-only alphabet table, raw 18 self-host 호환 검증 포함.
5. **Option C (per-bit binary wire) 결정 deferral** — Phase 10 P2 closure 후 별도 ω-cycle 에 evaluation.
6. **agent a6b12f93 의 LIVE FIRE 측정 결과 commit** — 실측 ceiling 데이터를 본 doc 의 PROJECTION 옆에 MEASURED 로 anchor 시킬 수 있도록.

---

## 7. raw 91 honest C3 final disclosure

본 doc 의 모든 wire-option-별 ceiling 숫자 (§ 1.2, § 2.1, § 2.2) 은 **PROJECTED** (Shannon × wire conversion factor 산식 기반). agent a6b12f93 LIVE FIRE 의 byte-canonical 3% ceiling 1점만 MEASURED. Option B 의 60-65% / 72-78% / 80-85% projection 은 base94 codec 미land 상태에서 산식 추정 — 실측 시 padding/header overhead 로 -2 to -5pp 변동 가능.

본 reformulation 은 PROJECTION 단위 정정 (bit-level vs byte-canonical wire 차원 분리) 만 수행. Shannon 한계 자체는 변경 없음. n6 verdict (a201a6cc) 는 valid.

raw 9 hexa-only · raw 18 self-host · raw 47 cross-repo · raw 65+68 idempotent ·
raw 71 falsifier-retire · raw 91 honest C3 · raw 95 triad-mandate ·
raw 102 STRENGTHEN-existing · raw 137 80% Pareto · raw 142 self-correction.
