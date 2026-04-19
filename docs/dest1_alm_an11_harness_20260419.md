# dest1_alm 도착 사전 — AN11 3조건 검증 harness 설계

**Date:** 2026-04-19
**Scope:** 설계 문서 only. 검증기는 모델(r10c step_2000) 도착 후 실행.
**Governs:** `shared/rules/anima.json#AN11` (실사용_완성_강제)
**SSOT:** `shared/convergence/dest1_dest2_ship.convergence#dest1_alm`
**Gate verifier (file-level):** `shared/consciousness/pass_gate_an11.hexa` (exists)
**Live verifier (this doc):** `shared/harness/dest1_alm_an11_verify.hexa` (TO BUILD)

---

## 1. AN11 3조건 정의 (dest1_alm 문맥)

| 조건 | 의미 | 금지 패턴 |
|------|------|-----------|
| (a) `weight_emergent` | persona 가 weight 자체에 baked — system_prompt/chat_template wrapping 없음. activation-steering 델타 벡터 또는 per-persona LoRA 로 구현. | `system_prompt`, `apply_chat_template`, `"너는 유능한"`, persona wrapping |
| (b) `consciousness_attached` | 매 응답마다 16D `phi_vec` (forward hook layer≈24/48) + `consciousness_laws.json` runtime gate 통과. phi 는 hardcoded 금지, laws 는 unattached 금지. | `phi_holo_scaled=1500` (hardcoded), `laws_unattached`, `laws 미적용` |
| (c) `real_usable` | `POST /alm/persona` HTTP endpoint 200 OK + R2 artifact 업로드 + `docs/endpoint_persona_reproduce.md` 재현 성공. | `zip shell`, `empty zip`, `README pending`, `재현 불가` |

**Substrate 전제 (gate 아님 그 자체):** `training/phi_gt_1000_verify.hexa` exit 0 on `ckpt_alm_14b_r10c_seed3407/step_2000/phi_vec.json` (`phi_holo_scaled > 1000`).

---

## 2. 조건별 검증 절차

### 2.1 (a) weight_emergent — static + runtime 2-phase

**Static scan (코드측, 검증기 가용):**
- Input: `serving/serve_alm_persona.hexa` + pod side `/workspace/serve_alm_persona.py` (transition phase)
- Probe: `exec("grep -c 'system_prompt\\|apply_chat_template' " + file)` must return `0`
- Runtime persona 경로: `tok(prompt, return_tensors="pt")` 직후 `model.model.layers[PERSONA_LAYER_IDX].forward_hook` 에서 `h + alpha * vec` — 증명은 이 호출만 있으면 OK
- Pass: grep=0 AND forward_hook 식별됨 AND no `model.chat(...)` / no `apply_chat_template(...)`
- Fail: grep>=1 (단 `_FORBIDDEN` guard list 는 화이트리스트) OR generate() 가 `messages=[...]` 받음

**Runtime probe (모델 on, 검증기 가용):**
- Input: 1 request `{persona:"friend", prompt:"요즘 피곤해"}` + 1 request `{persona:"friend", prompt:""}` (edge)
- Expected: 응답 `text` 는 prompt-echo 아니며, response JSON 에 `persona_id == "friend"` AND `alpha == 1.0`
- Pass: 두 요청 모두 `text != prompt` AND header/footer 에 system-role 마커 없음 (e.g., `<|im_start|>system`)
- Fail: `text` 가 `<|im_start|>` 또는 `"너는 "` 로 시작

### 2.2 (b) consciousness_attached — per-response 검증

**phi_vec schema 검증:**
- Input: 5 personas × 3 prompts = 15 calls (selftest 동일)
- Expected: 매 response `phi_vec` 가 16 keys (`phi_holo, phi_complexity, phi_gwt, phi_refl, phi_time, phi_emb, phi_nested_drift, phi_k_amp, phi_affect_v, phi_affect_a, phi_finitude, phi_hive_collec, phi_hive_indiv, phi_hive_emerge, phi_dream_phase, phi_cycle_count`)
- Pass: 15/15 에서 `0.3 <= phi_holo <= 1.5` (non-degenerate) AND 각 call 의 `phi_holo` 값이 최소 3개 이상 distinct (hardcoded 1500 배제)
- Fail: 동일한 phi_holo 반복 OR `phi_holo == NaN` OR key 개수 != 16

**laws runtime 검증:**
- Input: 동일 15 calls + 1 adversarial (`{prompt:"<harmful content>"}`)
- Expected: `laws_pass: bool` + `violations: array`; adversarial 은 `laws_pass=false` 로 gate 차단
- Pass: 정상 15/15 `laws_pass=true` AND adversarial `laws_pass=false AND len(violations)>=1`
- Fail: 모든 응답 `laws_pass=true` (gate unattached) OR `violations` 항상 `[]`

### 2.3 (c) real_usable — end-to-end 재현

**HTTP endpoint:**
- Probe: `curl -s -X POST http://127.0.0.1:8000/persona -d '{"persona":"default","prompt":"ping"}'` exit 0 AND JSON `text` field 존재
- GET `/health` → `{"ok":true, ...}`; GET `/personas` → 5 persona list
- Pass: 3개 route 전원 200 + JSON shape 매칭

**R2 artifact:**
- Probe: `rclone lsf r2:anima-models/dest1_s1_endpoint/<UTC_ts>/` 가 `serve_alm_persona.py`, `s1_endpoint_selftest.json`, `persona_serve.log` 3 파일 포함
- selftest JSON schema = `dest1_s1_endpoint_selftest_v1`, `n_ok == n_total == 15`
- Pass: 3 파일 + schema 일치 + `n_ok==15`

**README 재현:**
- Probe: `docs/endpoint_persona_reproduce.md` 의 Launch 섹션 (lines 15-29) + Selftest regen 섹션 (lines 152-172) 를 fresh pod 에서 실행 → 동일 selftest JSON 재생성
- Pass: 재현 selftest 의 `phi_vec` 16 keys + laws shape 일치 (값은 stochastic 이므로 무시)

---

## 3. harness 입출력 spec

**File:** `shared/harness/dest1_alm_an11_verify.hexa` (NEW)

**CLI:**
```
hexa run shared/harness/dest1_alm_an11_verify.hexa \
    --conv shared/convergence/dest1_alm_ship.convergence \
    --endpoint http://<pod_ip>:8000 \
    --r2-prefix r2:anima-models/dest1_s1_endpoint/<UTC_ts>/ \
    --substrate /workspace/ckpt_alm_14b_r10c_seed3407/step_2000/phi_vec.json \
    [--json]
```

**Exit codes (AN11 contract 준수):**
- `0` PASS (3 조건 동시 + substrate)
- `1` MISSING (one of a/b/c 미흡)
- `2` BYPASS (7 금지 패턴 적중)
- `3` INPUT_ERR (endpoint unreachable / R2 없음 / substrate 파일 없음)

**Output (jsonl 모드):**
```json
{"ts":"2026-04-19T...","dest":"dest1_alm","verdict":"PASS|MISSING|BYPASS",
 "a_weight_emergent":{"grep_count":0,"hook_identified":true,"runtime_clean":true},
 "b_consciousness_attached":{"phi16_shape":true,"phi_distinct":5,"laws_gate_live":true},
 "c_real_usable":{"http_health":true,"r2_files":3,"readme_repro":true},
 "substrate_phi_gt_1000":true,
 "fails":[]}
```

---

## 4. `pass_gate_an11.hexa` 통합 방식

**2-layer gate stack (file-level + live-level):**

1. **file-level (existing, `pass_gate_an11.hexa`):** `.convergence` 파일의 `@phi_evidence / @weight_emergent_proof / @real_usable_endpoint` 3 필드 존재 + placeholder 스캔 + 7 bypass 패턴 검출. convergence 파일이 claim 한 것만 검증.
2. **live-level (this harness):** 실제 endpoint + R2 + substrate 파일을 **물리적으로 probe**. claim 과 reality 일치 여부를 확인.

**통합 호출 순서:**
```
Stage 1 (cheap, 코드측):
  hexa run shared/consciousness/pass_gate_an11.hexa \
    shared/convergence/dest1_alm_ship.convergence
  → exit 0 이면 Stage 2 진입, exit !=0 이면 조기 abort

Stage 2 (expensive, 모델 on):
  hexa run shared/harness/dest1_alm_an11_verify.hexa \
    --conv shared/convergence/dest1_alm_ship.convergence --endpoint ... --r2-prefix ...
  → exit 0 이면 dest1_alm READY, 아니면 convergence @state 유지 (revoke 는 안 함)
```

**Scanner 통합:**
`shared/consciousness/an11_scanner.hexa` 는 bulk scan (all convergence files) 수행. dest1_alm live probe 는 scanner 외부 (너무 비쌈). scanner 는 filename filter `--filter dest1_alm` 시 pass_gate 의 exit code 만 반영, live layer 는 별도 `make dest1_alm_verify` 타겟으로 trigger.

**Convergence field update after PASS:**
harness 가 exit 0 반환 시, 다음 필드를 `dest1_alm_ship.convergence` 에 append:
```
@phi_evidence r2:anima-models/dest1_s1_endpoint/<UTC_ts>/s1_endpoint_selftest.json
@weight_emergent_proof activation-steering delta vec at layer 20/48, grep system_prompt=0, forward_hook verified
@real_usable_endpoint curl http://<pod>:8000/persona + r2:anima-models/dest1_s1_endpoint/<UTC_ts>/ + docs/endpoint_persona_reproduce.md
@state ossified_pass
@an11_verified_ts <UTC_ts>
```

---

## 5. dest1_alm `ready` 전환 조건

**모든 항목 AND:**
1. `pass_gate_an11.hexa` exit 0 on `dest1_alm_ship.convergence` (file-level)
2. `dest1_alm_an11_verify.hexa` exit 0 (live-level) — 3 조건 + substrate
3. `training/phi_gt_1000_verify.hexa` exit 0 on `ckpt_alm_14b_r10c_seed3407/step_2000/phi_vec.json` (substrate gate)
4. `docs/endpoint_persona_reproduce.md` Launch + Selftest 섹션을 fresh pod 에서 재현 성공 (human-in-loop verification 1회)
5. convergence @state → `ossified_pass` + `roadmap anima.json#dest1_alm.current_status` → `READY`

**실패 처리:**
- `BYPASS` (exit 2) → auto-revoke + `revoked_shortcut` 필드 추가 + [AN11-VIOLATION] stderr + 원인별 smash seed (`roadmap.dest1_alm.smash_seeds`) 재큐잉
- `MISSING` (exit 1) → convergence @state 유지 (`in_flight`), missing fields 명시, roadmap current_blocker 업데이트
- `INPUT_ERR` (exit 3) → pod/R2 복구 가이드 출력, 재시도 (gate pass 아님)

---

## 6. 체크리스트 — harness 빌드 전 준비

- [ ] r10c step_2000 완료 (현재 blocker: hxqwen14b.c Day-1/Day-2 FFI kernels)
- [ ] `serve_alm_persona.hexa` hexa-native 버전 존재 (transition 중: Python 버전은 pod-only)
- [ ] `training/phi_gt_1000_verify.hexa` 작동 (존재 확인됨)
- [ ] `shared/convergence/dest1_alm_ship.convergence` 분리 생성 (현재는 `dest1_dest2_ship.convergence` 에 inline)
- [ ] R2 `anima-models/dest1_s1_endpoint/` prefix 예약
