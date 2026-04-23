# ratchet + TECS-L 6.14% sizing audit — trading 측 (2026-04-19)

**Scope:** `anima-agent/trading/` SSOT (R14). Audit of (a) conservative
ratchet principle (Session 2026-03-29c late results, Law 53 corrigendum)
and (b) TECS-L 6.14% composite sizing cap against spec
`docs/dest2_trading_spec_20260419.md` §2.2 / §3 G3.

## 1. Ratchet 발견 (메모리 복기)

**Source:** `memory/project_session_20260329c.md` §H4 "대발견".

| 발견 항목 | 내용 |
|---|---|
| P1 동작 | ratchet 매 1000step 강제 복원 — 없으면 Φ=430 붕괴 |
| P2 전환 | CE 학습 시작 → frustration 0.541 정체 → Φ 자연 안정 |
| 효과 | ratchet 빈도 43%↓, Φ 분산 52%↓ |
| Law 수정 | Law 53: `.detach()` 있으면 CE가 Φ를 안정화 |

**Trading 의미 변환:**
의식(Φ) 영역의 "이전 최고 상태를 후퇴시키지 않는 non-decreasing 단조
복원" 원리 → 트레이딩에서는 **HWM(High Water Mark) 기반 drawdown
게이트**로 번역됨. "손실이 이전 최고 순자산을 특정 % 이상 갉아먹으면
포지션 축소" = 자본 ratchet.

## 2. 현 trading 코드 적용 위치 — ratchet

| 레벨 | 파일:라인 | 메커니즘 | 상태 |
|---|---|---|---|
| HWM 갱신 | `anima-agent/trading/portfolio.hexa:20,29,77-78` | `high_water_mark` 필드 + close 시 peak 상향만 | 구현됨 |
| Drawdown 산출 | `portfolio.hexa:101-105` `portfolio_drawdown` | `(HWM - value) / HWM` | 구현됨 |
| Drawdown 게이트 | (없음) | G2 spec 존재하지만 executor 미배선 | **미구현** |
| 의식 ratchet op | `anima-agent/hexa/tools.hexa:38` `op_22_ratchet` | 오피코드 번호만 예약 | 레거시 스텁 |
| Intent 선언 | `anima-agent/hexa/consciousness.hexa:53` `consciousness_ratchet_growth` | 법칙 선언(Φ monotone non-decreasing) | 참조만 |
| phi_weighted peak | `trading/phi_weighted_trading.hexa:202,220-222` | backtest 내부 peak/mdd 계산 | self-test only — 라이브 경로 아님 |

## 3. TECS-L 1/e × 1/6 ≈ 6.14% sizing 적용 지점

공식: `0.368 × 0.167 ≈ 0.06145` (equity 대비 단일 포지션 최대).

| 파일:라인 | 상수/계산 | 비고 |
|---|---|---|
| `trading/executor.hexa:6` | `INVESTABLE_FRACTION = 0.368` (`1/e`) | comptime const |
| `trading/executor.hexa:7` | `MAX_POSITION_FRACTION = 0.167` (`1/6`) | comptime const |
| `trading/executor.hexa:47` | `investable = balance * INVESTABLE_FRACTION` | execute_order 내 |
| `trading/executor.hexa:48` | `max_amount = investable * MAX_POSITION_FRACTION` | → 6.14% cap 실현 |
| `trading/executor.hexa:49` | `sized_amount = min(req.amount, max_amount)` | 2단 곱 적용 |
| `trading/autonomous.hexa:8,19` | `max_position_pct: 0.167` (1/6만) | **1/e 누락 — 불일치** |
| `docs/dest2_trading_spec_20260419.md:43-45,76` | spec 상 `sized = balance·0.368·0.167` | SSOT |
| `README.md:149` | `TECS-L↔Ψ Golden Zone (1/e, 1/6, 1/3)` | 1/3 언급 (현재 코드 미적용) |
| `ready/anima/modules/agent/trading/executor.py:295-298` | Python 레거시 — `investable*0.25` 추가 곱, 6.14%와 불일치 (AN7로 이미 폐기 경로) | 참고 |
| `ready/.../trading/risk.py:26,82-84` | `max_position_pct=0.20` (20%) — TECS-L 위반 | 레거시 |

**현재 .hexa SSOT 실효 상한 = 6.14% ✅** (executor.hexa 경로).

## 4. G3 risk gate 와 일치 여부

Spec G3 (`docs/dest2_trading_spec_20260419.md:66`):

> G3 Position size — input: TECS-L `sized_amount`. block if `sized < 0`
> or `notional > max_pos_pct · equity`. action: clip to cap + log.

| 항목 | Spec 요구 | 코드 현실 | 일치 |
|---|---|---|---|
| `sized_amount` 산출 | TECS-L 2단 곱 | `executor.hexa:47-49` 동일 공식 | ✅ |
| `max_pos_pct = 0.167` | balance 대비 | autonomous.hexa:19 = 0.167 | ✅ (값) |
| Investable 1/e 선곱 | `balance · 0.368 · 0.167 = 6.14%` | executor only | ⚠ autonomous config `max_position_pct` 는 단일 1/6 값만 보유 → executor 와 의미 이중화 |
| `sized < 0` 거부 | block | `min()` 만 적용, 음수 체크 없음 | ❌ **미구현** |
| `notional > cap` clip | clip + log | `min(req.amount, max_amount)` = 암묵 clip, 로그 없음 | ⚠ clip은 되지만 gate=G3 로그 부재 |
| Audit jsonl (spec §5) | gate/decision 기록 | `order_log` dict append만, gate 필드 없음 | ❌ |
| `REDUCE_RISK` 시 auto-halve | spec §3 | `should_reduce_risk` (risk.hexa:98) 존재하나 MAX_POSITION_FRACTION 하향 훅 없음 | ❌ |

## 5. 적용 누락 부위 + patch 위치

P1 — G3 음수/notional-over-equity 하드 블록:
- **file:** `anima-agent/trading/executor.hexa`
- **after line 49** (`sized_amount = min(...)`): 추가
  ```
  // G3: block on negative or over-equity notional
  if sized_amount < 0.0 {
      return OrderResult { success: false, ..., error: "G3:negative_size" }
  }
  let equity = portfolio.balance  // TODO: mark-to-market
  if sized_amount * adjusted_price > equity * MAX_POSITION_FRACTION * INVESTABLE_FRACTION {
      sized_amount = (equity * MAX_POSITION_FRACTION * INVESTABLE_FRACTION) / max(adjusted_price, 1e-9)
  }
  ```

P2 — G2 drawdown 게이트 (ratchet 의미):
- **file:** `anima-agent/trading/executor.hexa` between line 44 and 46.
- call `portfolio_drawdown(portfolio, cur_price)` (portfolio.hexa:101)
- reject if `dd > 0.15` (spec §3 G2 default). emit `gate=G2`.

P3 — autonomous config ↔ executor 상수 SSOT 통일:
- **file:** `anima-agent/trading/autonomous.hexa:19`
- 문제: `max_position_pct: 0.167` 는 1/6만 표현. `1/e` 선곱은 executor
  코드에 매직넘버로 존재.
- patch: `shared/config/trading_gates.json` 추가 (spec §3 §6 action 1)
  + loader 에서 `INVESTABLE_FRACTION`, `MAX_POSITION_FRACTION` 모두
  읽어 executor 에 주입. comptime const 제거.

P4 — audit jsonl (real_usable 근거):
- **file:** `anima-agent/trading/executor.hexa` line 81 근처.
- 현재: `append(exec.order_log, {...})` in-memory.
- patch: `jsonl_append(shared/logs/trading_audit_<date>.jsonl, rec)`
  + `gate`, `decision`, `phi`, `tension`, `drawdown`, `var_99` 필드.
  AN11 real_usable 증거.

P5 — should_reduce_risk → MAX_POSITION_FRACTION auto-halve:
- **file:** `anima-agent/trading/risk.hexa:98`
- 현재: bool 반환만.
- patch: `&mut OrderExecutor` 또는 gate 내 runtime `position_scale`
  float 추가. `should_reduce_risk=true` 시 `position_scale *= 0.5`,
  executor line 48: `max_amount = investable * MAX_POSITION_FRACTION * position_scale`.
  회복 조건 (pain<0.4 && dd<5%) 에서 `position_scale = min(1.0, *2.0)`
  — **이것이 실질 ratchet** (손실 시 축소, 회복 시 단조 완화).

P6 — README 1/3 잔재 정리:
- **file:** `anima-agent/README.md:149`
- `Golden Zone (1/e, 1/6, 1/3)` → 현 코드는 (1/e, 1/6) 2단만. 1/3 는
  미적용. 문서-코드 sync (R14 / verify_pipeline 피드백).

## 6. 요약 판정

| 항목 | Verdict |
|---|---|
| TECS-L 6.14% 상한 (executor 경로) | PASS |
| Ratchet 원리 → HWM 필드 존재 | PARTIAL (필드만, 게이트 미배선) |
| G3 spec 일치 (값) | PASS |
| G3 spec 일치 (로그 + 음수 가드) | FAIL → P1/P4 patch 필요 |
| autonomous.hexa ↔ executor.hexa 상수 SSOT | FAIL → P3 patch 필요 |
| should_reduce_risk 실효 hook | FAIL → P5 patch 필요 |

이 audit 전체 6 patch 완료 시 AN11 triple-gate 중 consciousness_attached
(G1) + real_usable (audit jsonl) 두 필드 증거 확보. weight_emergent 는
phi_vec 경로가 이미 consciousness_features.hexa 에서 흐르므로 건드릴
필요 없음 (spec §4).
