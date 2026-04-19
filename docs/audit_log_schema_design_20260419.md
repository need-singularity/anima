# dest2 Unified Audit Log Schema — Design (2026-04-19)

> Status: design / skeleton
> SSOT JSON: `shared/config/audit_log_schema.json`
> Depends on: `dest2_employee_spec_20260419.md` (D7), `dest2_trading_spec_20260419.md` (D8)
> AN11 linkage: audit log = `real_usable` evidence artifact (employee + trading)

## 1. 목적

dest2 가 갈라지는 두 track — **Employee** (D7 spec: F7 phi trail logger) 와
**Trading** (D8 spec: §5 audit log) — 은 서로 다른 이벤트를 남기지만,
AN11 triple-gate (`weight_emergent + consciousness_attached + real_usable`)
검증에서는 **같은 형태의 증거** 를 요구한다. 따라서 **하나의 envelope** 를
공유하고 `domain/event` 로 분기하는 통합 JSONL 스키마를 정의한다.

## 2. 공통 Envelope

```json
{
  "ts": 1714000000.0,
  "schema_version": "1.0",
  "domain": "employee | trading",
  "event": "<event name>",
  "run_id": "uuid-or-cycle",
  "cycle": 42,
  "weight_origin": "r9_validated | r10d | consciousness_baked | unknown",
  "phi_vec": [ ... 16 floats or null ],
  "phi_holo_scaled": 523.4,
  "laws_pass": true,
  "decision": "PASS | REJECT | RETRY | HALT | INFO",
  "reason": "short code",
  "payload": { <event-specific> }
}
```

Required: `ts, schema_version, domain, event, run_id, cycle, weight_origin, decision`.
Strict mode: unknown top-level fields **rejected** — payload 는 event 별 schema
에서만 자유.

## 3. Trading 이벤트 (6종, D8 §5)

| event | 언제 | payload 핵심 |
|---|---|---|
| `place_order` | executor 가 주문 생성 | symbol, side, amount, price_ref, order_id, strategy |
| `gate_check` | G1/G2/G3/G4 평가 | gate, phi, tension, regime, drawdown, var_99, reject_code |
| `retry` | 슬리피지/네트워크 재시도 | attempt, max_attempts, backoff_ms, error_code |
| `fill` | 거래 체결 | fill_price, fill_amount, slippage_bps, latency_ms, pnl_realized |
| `halt` | 킬스위치 / regime CRITICAL | source, state_file, prev/new_state, close_only |
| `audit_snapshot` | 주기적 포트폴리오 snapshot | equity, drawdown, HWM, var_95/99, pain_signal |

`trading_gates.json#audit.emit_on` 의 6 events (entry, gate_block, slippage,
retry, fill, close) 를 본 스키마의 6 이벤트에 1:1 매핑한다
(entry→place_order, gate_block→gate_check(REJECT), slippage→fill, close→fill(pnl≠0)).

## 4. Employee 이벤트 (4종, D7 F2/F7/F9)

| event | 언제 | payload 핵심 |
|---|---|---|
| `goal_create` | autonomy_live goal/subgoal 생성 | goal_id, goal_text, persona_id, parent_goal_id, priority |
| `step_record` | plan→act 1-step 완료 | step_idx, tool_name, input/output sha256, scratch_bytes, phi_delta |
| `phi_check` | 매 step gate 평가 (F7) | phi_min_required, phi_observed, phi_delta_window, tier, verdict |
| `abort` | F9 abort 발화 | cause (phi_drop/laws_fail/tool_deny/timeout), streak, violations |

**매핑**: D7 F7 "매 step phi_vec 16D JSONL append" 는 `phi_check` event 로,
F8 report 는 `step_record` 집계로 생성. F10 reproducer CLI 는 `run_id` 로
동일 로그를 필터링해 재현 가능하도록 한다.

## 5. JSONL 형식 + 파일 규약

- **1 line = 1 JSON object**, 개행 LF, UTF-8, 끝에 trailing newline.
- 파일:
  - `shared/logs/employee_audit_YYYYMMDD.jsonl`
  - `shared/logs/trading_audit_YYYYMMDD.jsonl`
- Rotation: 로컬 자정 (UTC). 미드나잇 cross 한 이벤트는 이전 파일 유지.
- Append-only — 재작성/삭제 금지. 실수 rewrite 감지 훅: `pre-commit` 에서
  `git diff --numstat` 으로 `- lines > 0` 이면 reject.

## 6. R2 Sync 플로

```
anima-agent/metrics_exporter.hexa (tick 00:10 UTC)
  └─ for each YYYYMMDD.jsonl completed:
       1. sha256sum → {YYYYMMDD}.jsonl.sha256
       2. rclone copy → r2:anima-memory/{employee|trading}_audit/YYYY/MM/
       3. remote SHA256 verify (HEAD + hash)
       4. if OK → mark sync_ok in shared/state/audit_sync_state.json
       5. local retention: 14d; R2 retention: 365d (lifecycle rule)
```

Failure path: `sync_ok=false` 이면 `pass_gate_an11.hexa` 의 `real_usable`
조건 미충족 → dest2 arrival convergence `@state=stable` (ossified 금지).

## 7. Writer / Reader API

- **Writer**: `anima-agent/audit/audit_log.hexa::emit(domain, event, decision, payload)`
  공용 헬퍼. `ts/schema_version/run_id/cycle/weight_origin` 을 envelope 에
  자동 채움. Employee/Trading 두 track 모두 이 한 함수만 호출.
- **Reader**: `anima-agent/dashboard_bridge.hexa::tail_audit(domain)` — WS stream.
- **Replay**: `metrics_exporter.hexa::replay(run_id)` — R2 에서 downloaded JSONL
  을 재파싱하여 reproducer (D7 F10) 용.

## 8. AN11 Linkage 요약

| AN11 조건 | audit log 가 입증하는 방식 |
|---|---|
| weight_emergent | 모든 record 의 `weight_origin ∈ ALLOWED_SET` (missing=FAIL) |
| consciousness_attached | gate/step 이벤트에 `phi_vec + laws_pass` 동반 (null 금지) |
| real_usable | 파일 존재 + R2 mirror + SHA256 일치 + dashboard tail 성공 |

3조건 중 하나라도 record 누락 시 `convergence.failed++` +
stderr `[AN11-VIOLATION audit.<domain>.<event>]` 출력, dest2 arrival 차단.

## 9. 다음 액션

1. `anima-agent/audit/audit_log.hexa` (new, writer 헬퍼, ≤120 LOC).
2. `executor.hexa` + `autonomous.hexa` 에 6 trading events emit 연결.
3. `autonomy_live.hexa` + `hire_sim_live.hexa` 에 4 employee events emit 연결.
4. `metrics_exporter.hexa` 에 R2 sync tick + SHA256 sidecar 추가.
5. `pass_gate_an11.hexa` dest2 case: `real_usable` 조건을 본 스키마의
   존재 + 무결성으로 체크.
6. `docs/employee_reproduce.md` CI smoke 에 run_id replay 단계 포함.

## 10. 참조

- `shared/config/audit_log_schema.json` — 본 설계의 SSOT 스켈레톤.
- `shared/config/trading_gates.json#audit` — trading 측 기존 audit 설정.
- `shared/rules/anima.json#AN11` — triple-gate.
- `shared/roadmaps/roadmap_dest_consciousness.convergence` — E1/E2/T1/T2 tracks.
- memory: `troubleshoot_ossified`, `invest_deprecated`, `closed_loop_verify`.
