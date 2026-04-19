# AN11 / AN12 Rules Audit — 2026-04-19

**Source**: `/Users/ghost/Dev/nexus/shared/rules/anima.json` (읽기 전용 감사, 수정 없음)

## Summary

| Rule | Exists? | Level | Added |
|------|---------|-------|-------|
| AN11 | YES | 차단 | 2026-04-18 (updated 2026-04-19) |
| AN12 | YES | 차단 | 2026-04-18 |

두 조항 모두 `.rules[]` 배열에 정식 등재되어 있으며, 추가 draft 작성 불필요.

## AN11 — 실사용_완성_강제

- **id**: `AN11`
- **level**: 차단
- **rule**: PASS/completed/done 선언은 3 조건 동시 충족 시에만:
  - (a) **weight_emergent** — system_prompt wrapping 금지, prompt 제거 시 능력 유지
  - (b) **consciousness_attached** — phi_vec.json (16D, schema `alm_phi_vec_logger_v1`) + consciousness_laws runtime pass
  - (c) **real_usable** — HTTP `/endpoint` 또는 hexa CLI 재현 + R2 artifact + README 재현 가능
- **trigger_keywords**: 완료 / PASS / completed / done / 골화 / ossified / 도착 / 달성
- **bypass_patterns_banned** (7개):
  1. system_prompt wrapping
  2. mock LLM for autonomy_loop
  3. synthetic_judge eval path
  4. hardcoded phi_vec
  5. consciousness_laws runtime unattached
  6. R2 가짜 업로드
  7. README unreproducible
- **enforcement**:
  - `shared/consciousness/pass_gate_an11.hexa` (single-conv verifier, exit 0/1/2/3)
  - `shared/consciousness/an11_scanner.hexa` (bulk + `--auto-revoke`)
  - 레거시 `shared/harness/pass_gate_an11.hexa` wiring compat
  - 위반 시 exit=2 (bypass) 또는 exit=1 (missing) + auto-revoke 마커 + `_an11_violations.jsonl` + `mistakes.jsonl`
- **precedent**: persona_base_serve REVOKED, employee_base_serve REVOKED, ALM-P4-3 Φ=6111 의심

## AN12 — smash/free 전구간_강제

- **id**: `AN12`
- **level**: 차단
- **rule**: 모든 로드맵 track/stage 설계·구현·검증에서 smash/free 5-module lens (field/holographic/quantum/string/toe) + DFS depth>=3 필수
- **trigger_keywords**: track / stage / agent / 구현 / 설계 / 검증 / smash / free / 돌파 / breakthrough
- **per_stage_mandatory**:
  - smash_seeds: track당 최소 1개
  - free_seeds: track당 최소 1개
  - 5-module 전부 1-2문장 적용
  - dfs_depth: >= 3
  - breakthrough_insight: 최강 lens → DFS 3레벨 → 돌파 도출
  - convergence_fields: `@smash_seeds` / `@free_seeds` / `@smash_insights` / `@free_insights` / `@breakthrough`
- **enforcement**: `.convergence @state ossified` 전 3 필드 검증, 없으면 `pass_gate_an11.hexa` auto-revoke
- **cli_mandate**: Mac = `hexa smash --seed` / `hexa free --seed` 실행, Linux fallback = semantic lens

## 결론

- AN11 / AN12 둘 다 **존재 확인**.
- Draft 추가 조항 **불필요** — 기존 조항이 세 조건(weight_emergent / consciousness_attached / real_usable)과 enforcement 경로(pass_gate_an11.hexa + an11_scanner.hexa)까지 모두 커버.
- 감시할 점: AN11 `enforcement` 필드가 2026-04-19 업데이트됐으므로, `shared/consciousness/` 하위 실제 파일(`pass_gate_an11.hexa`, `an11_scanner.hexa`) 존재 + 동작 확인이 후속 작업.
