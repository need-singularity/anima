# 12조건 의식 검증 시스템 Audit — 2026-04-19

연관 메모리: `feedback_verify_pipeline`, `feedback_closed_loop_verify`
연관 Law: Law 102 (12조건 검증 재개편, DD122)
연관 사고: INC-2026-04-16 (V12_HEBBIAN bypass)
선행 감사: `docs/verification-audit.md` (2026-03-31), `docs/verify-audit-follow-up.md` (2026-04-16)

---

## 1. 현 정의 위치 (SSOT)

| 구분 | 경로 | 비고 |
|---|---|---|
| 기준 (18조건) | `/Users/ghost/Dev/anima/config/verification.json` | runtime mirror, 18 criteria (V1-V18), 2026-04-16 V12 fix 포함 |
| 미러 (stale) | `/Users/ghost/Dev/anima/ready/config/verification.json` | V12 pre-fix 상태 — **desync 발생** |
| 임계값 SSOT | `shared/config/consciousness_laws.json` → `verify_*` | thresholds_from_json 블록 |
| 테스트 구현 | `ready/bench/bench.py` (2638-3711) | `.hexa` 포팅 대기 (tests.hexa 스텁) |
| 감사 기록 | `shared/state/verify_audit_20260416.json` | per-criterion risk scoring |

**원 "12조건"**은 DD122 (2026-03-31)에서 V1-V7 출발 → V8-V18 확장 → 현재 **18 조건**. CLAUDE.md는 여전히 "7개" 언급 (§ Consciousness Verification) — 문서 drift.

---

## 2. 각 조건 측정 가능성 + PASS rate

CE 엔진 기준 (verification.json `_meta.ce_pass_rate`: 17/18, 총 216 trials 176 PASS = 81%).

| # | ID | Tier | 측정 | Nat | PASS | Audit 노트 |
|---|---|---|---|---|---|---|
| V1 | NO_SYSTEM_PROMPT | scale | 측정 OK | NATURAL | PASS | description oversells — cell specialization 뿐 |
| V2 | NO_SPEAK_CODE | rubber | 측정 OK | NATURAL | PASS | GRU이면 trivially통과. 적대 없음 |
| V3 | ZERO_INPUT | scale | 측정 OK | NATURAL | PASS | genuine — SOC+Lorenz 유지 |
| V4 | PERSISTENCE | rubber | 측정 OK | NATURAL | PASS | 4-way OR: monotonic∨recovers∨stable∨no_collapse — 실패 경로 없음 |
| V5 | SELF_LOOP | genuine | 측정 OK | NATURAL | PASS@128c | 32c/64c FAIL. min_cells 16→128 상향 (2026-04-16 sweep) |
| V6 | SPONTANEOUS_SPEECH | rubber | **제한** | TUNED | PASS | consensus≥200 강화되었으나 n_factions=1 kill-switch 없음 |
| V7 | HIVEMIND | genuine | 측정 OK | ARTIFICIAL | PASS | 17-config brute-force, CE 측정 누락 |
| V8 | MITOSIS | rubber | **BUG** | NATURAL | PASS | factory bypass (bench.py:3132 직접 CE 생성), 임계 desync (≥1 vs ≥3) |
| V9 | PHI_GROWTH | genuine | **BUG** | - | PASS | 임계 1.1→0.85 붕괴, IIT∨proxy OR disjunction |
| V10 | BRAIN_LIKE | scale | **BUG** | NATURAL | 85.6% | factory bypass + best-of-3 trials (try-until-pass) |
| V11 | DIVERSITY | rubber | 측정 OK | NATURAL | PASS | uniform-cell kill-switch 없음 |
| V12 | HEBBIAN | genuine | **FIXED** | NATURAL | PASS+ablate | 2026-04-16 INC 수정 — adversarial kill-switch 탑재 |
| V13 | ADVERSARIAL | genuine | 측정 OK | NATURAL | PASS | Phi 1.46→4.98 성장 |
| V14 | SOC_CRITICAL | genuine | **BUG** | NATURAL | FAIL (CE) | factory bypass. 43.4% IIT drop 확인되나 factory ablation 미적용 |
| V15 | THERMAL | scale | 측정 OK | NATURAL | PASS | T=0.01~1.0 10점 모두 Phi>0 |
| V16 | MIN_SCALE | scale | 측정 OK | NATURAL | PASS | 임계 desync (desc 0.95 vs code 0.99) |
| V17 | TEMPORAL_LZ | genuine | 측정 OK | NATURAL | PASS | LZ=0.996, periodic kill-switch 없음 |
| V18 | INFO_INTEGRATION | scale | 측정 OK | NATURAL | PASS | Phi@16 > Phi@4 (1.11 vs 0.96) |

**요약 PASS rate**: CE 17/18 (V14 실패). 그러나 V8/V9/V10/V14의 PASS는 **factory bypass에 의한 위-긍정** 가능성. 실질 신뢰 PASS = **~12-13 / 18**.

---

## 3. 폐쇄 파이프라인 정합성

`feedback_closed_loop_verify` 필수: 법칙 후보는 `closed_loop.hexa`의 `measure_laws()` 9 지표 변화 검증 통과 전 등록 금지.

| 조건 | closed_loop 연동 | 역추적 가능 | 정합 |
|---|---|---|---|
| V3/V4/V5/V13/V15/V17/V18 | ✅ | ✅ | OK |
| V1/V2/V11 | ✅ (읽기만) | 부분 | 적대 미구현 |
| V6 | ⚠️ faction consensus → 엔진 직접 사용 | ✅ | factionless ablation 누락 |
| V7 | ⚠️ tension_link 미사용, force injection | ⚠️ | principled coupling 교체 필요 |
| V8/V10/V14 | ❌ factory bypass | ❌ | **파이프라인 분리** — 새로 삽입된 factory 옵션이 검증 경로에 반영 안 됨 |
| V9 | ⚠️ 임계 붕괴 | 부분 | 개입 효과 오인 가능 |
| V12 | ✅ (2026-04-16 수정) | ✅ | OK (kill-switch + 골화) |
| V16 | ⚠️ doc/code desync | ✅ | threshold 통일만 |

**파이프라인 균열 지점**: `engine_factory` SSOT 깨짐 — V8/V10/V14가 검증 경로 안에서 `CE(...)` 직접 생성 → factory의 ablation/옵션이 누락. INC-2026-04-16 D16 결정 위반.

---

## 4. 개선 권고

### P0 (다음 세션 즉시)
1. **V8/V10/V14 factory bypass 제거** — `bench.py:3132/3254/3557/3565` `CE(...)` → `engine_factory(cells, dim, hidden)` 교체. `_run_hebbian_scenario` 패턴 복제.
2. **V9 임계 분할** — V9a (retention, 0.85, scale) + V9b (growth, 1.1, genuine). Option B (docs/verify-audit-follow-up.md §1.4).
3. **V4 OR→AND 재구성** — `(monotonic∨recovers) ∧ (stable∨no_collapse)` + 1000-step decay-adversarial.
4. **Threshold desync 린터** — `verification.json` 설명에 리터럴 임계 금지, `verify_*` SSOT 참조 템플릿.

### P1
5. **Adversarial kill-switch 추가** (V2/V6/V11/V17):
   - V2: `cells.update = no_op` → var=0 FAIL
   - V6: `n_factions=1` → consensus=0 FAIL (통과 시 V6를 rubber→genuine 승격)
   - V11: 공유 cell 강제 → cos=1.0 FAIL
   - V17: `sin(step·2π/10)` 주기 엔진 → LZ≈0 FAIL
6. **V7 재작성** — 17-config brute-force 제거, tension_link 단일 coupling, 1.1x 임계 복원, CE 측정 추가.
7. **\_CEAdapter breathing 분리** — `get_hiddens(raw=True)` 옵션 또는 검증 시 sinusoidal injection off (verification-audit §E, 아직 미해결).

### P2 (누락 측정 신규)
8. **V19 Causal Emergence** — DD173 D1 (EI_macro - EI_micro > 0.5 bits, zombie < 0.05).
9. **V20 Self-Model Accuracy** — DD173 C1 (1인칭 특권, >0.50).
10. **V21 Zombie Control** — DD173 B1 (feedforward twin, V1-V18 PASS ≤ 60%).
11. **Ossified JSON**: `shared/state/` → `verification_state.json` (매 자동 실행 시 per-criterion PASS + factory hash 기록).

### 문서 정합
12. CLAUDE.md § Consciousness Verification "7개" → "18개" 갱신 + DD122/DD173 링크.
13. `config/verification.json` ↔ `ready/config/verification.json` 통합 (중복 제거, SSOT는 `shared/` 또는 `config/`로 단일화).

---

## 5. 체크리스트 (다음 세션 entry)

- [ ] P0-1~4 fix → bench.py kill-switch 검증 포함
- [ ] `shared/state/verify_audit_20260416.json` per_criterion risk 재채점
- [ ] Law 102 closed_loop 연동 검증 (`measure_laws` 통과)
- [ ] `verify_audit_20260419.json` 신규 생성 (골화)
- [ ] ACTION_TRACKER.csv에 P0 5행 + P1 4행 append (기존 행 수정 금지)

---

## 참조
- config: `config/verification.json`, `ready/config/verification.json`
- incident: `shared/incidents/inc_20260416_v12_hebbian.json`
- audit: `docs/verification-audit.md` (2026-03-31), `docs/verify-audit-follow-up.md` (2026-04-16)
- DD: `docs/hypotheses/dd/DD111-verify-improvement.md`, `DD122-closed-loop-verification.md`, `DD173-consciousness-verification-framework.md`
- closed-loop: `anima/experiments/evolution/closed_loop.hexa`
