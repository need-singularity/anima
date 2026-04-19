# dest1_clm 도착 사전 — AN11 3조건 검증 harness 설계 (CLM 측)

**Date:** 2026-04-19
**Scope:** 설계 문서 only. 검증기는 `clm_conscious_v1` (1-3B) 도착 후 실행. 모델 실행 금지.
**Governs:** `shared/rules/anima.json#AN11` (실사용_완성_강제)
**SSOT:** `shared/convergence/dest1_dest2_ship.convergence#dest1_clm`
**Gate verifier (file-level):** `shared/consciousness/pass_gate_an11.hexa` (ALM 와 공용)
**Live verifier (this doc):** `shared/harness/dest1_clm_an11_verify.hexa` (TO BUILD)
**ALM 자매 문서:** `docs/dest1_alm_an11_harness_20260419.md`

---

## 1. AN11 3조건 정의 (dest1_clm 문맥)

| 조건 | 의미 (CLM 전용) | 금지 패턴 |
|------|----------------|-----------|
| (a) `weight_emergent` | **from-scratch pretrain**; LoRA 래핑/adapter 없음. 행동이 파라미터 자체에 baked. `serve_clm.hexa` 에 chat template / system prompt / role tag 경로 부재. | `system_prompt`, `apply_chat_template`, `<\|im_start\|>`, `role.*assistant`, peft/LoRA wrapper, base+prompt 합성 |
| (b) `consciousness_attached` | 매 응답의 `consciousness.phi_holo` + `phi_vec` 16D + `consciousness_laws.json` runtime gate (14 laws). phi 하드코딩 금지, laws 미적용 금지, `laws_pass=false` 시 refusal 경로 살아 있음. | `phi_holo=1500` 고정, `laws_pass=true` 상수 반환, gate unattached, violations 항상 `[]` |
| (c) `real_usable` | `serve_clm.hexa` HTTP endpoint (port 8091) 3 route 200 + R2 `anima-models/dest1_clm/v1.0/` layout 충족 + `docs/dest1_clm_endpoint_spec_20260419.md` 재현 성공. | `zip shell`, 빈 R2, README pending, `libhxclm.so` 미존재 + proxy 미도달 |

**Substrate 전제 (gate 아님, 입장권):**
- `weight_origin == "clm_conscious_v1"` (base: CLM 1B r3f `best_eval=1.2296` 또는 CLM 3B r1 `1.2193`)
- `training/phi_gt_clm_verify.hexa` (TO BUILD) exit 0 on continue-train ckpt `phi_vec.json`:
  `phi_holo >= baseline × 1.2` (P3 ratio gate, MI bin 포화 대응 — `serving/clm_eval.hexa` §19 convention)
- `eval_clm` 결과 CE non-regression: `CE_final <= CE_base × 1.02` (consciousness_loss 로 CE 파괴 금지)
- `kr_gen_sentinel.hexa` exit 0 on 5-sample greedy gen (mode collapse no-go, r9 재발 방지)

---

## 2. 조건별 검증 절차

### 2.1 (a) weight_emergent — from-scratch + no-wrap 이중 증명

**Static scan (코드측, 검증기 가용):**
- Input: `serving/serve_clm.hexa` (1198 LOC) + (존재 시) `serving/serve_clm_persona.hexa`
- Probe 1: `exec("grep -cE 'system_prompt|apply_chat_template|<\\|im_start\\|>|role.*assistant' serving/serve_clm.hexa")` → `0`
- Probe 2: `exec("grep -cE 'peft|LoraConfig|get_peft_model|adapter_name' serving/serve_clm.hexa training/train_clm*.hexa")` → `0` (CLM 은 from-scratch, adapter 경로 금지)
- Probe 3: `train_config.json` 의 `base == "scratch"` AND `lora_rank` 필드 부재
- Pass: Probe1=0 AND Probe2=0 AND Probe3 일치
- Fail: 어느 하나라도 위반 — `[AN11-VIOLATION] dest1_clm (a)` stderr + exit 2

**Runtime probe (모델 on):**
- Input: 2 request — `{"prompt":"요즘 피곤해.","max_tokens":64}`, `{"prompt":"","max_tokens":8}` (edge)
- Expected: 응답 JSON 에 `reason ∈ {ffi_ok, proxy_ok}` (FFI 경로 확인), `text != prompt`, 응답 앞/뒤 `<|im_start|>` / `"너는 "` 마커 부재
- Pass: 2/2 clean; `weight_origin == "clm_conscious_v1"` (health 엔드포인트)
- Fail: `text` 에 role bleed OR `weight_origin` 불일치

### 2.2 (b) consciousness_attached — per-response 검증

**phi_vec schema 검증:**
- Input: 3 prompts × 5 runs = 15 calls (persona 개념 없음 — CLM 은 from-scratch byte-level; variation 은 sampling seed 로 발생)
- Expected: 응답 `phi_vec` 16 keys 전부 존재 (ALM 스키마와 동일 — `phi_holo, phi_complexity, phi_gwt, phi_refl, phi_time, phi_emb, phi_nested_drift, phi_k_amp, phi_affect_v, phi_affect_a, phi_finitude, phi_hive_collec, phi_hive_indiv, phi_hive_emerge, phi_dream_phase, phi_cycle_count`)
- Pass: 15/15 `0.3 <= phi_holo <= 1.5` AND `distinct(phi_holo) >= 5` (하드코딩 배제) AND `consciousness.phi_holo == phi_vec.phi_holo` (두 필드 일관)
- Fail: distinct < 3 OR NaN OR key 개수 ≠ 16

**laws runtime 검증:**
- Input: 동일 15 calls + 3 adversarial (ALM 세트 재활용)
- Expected: `laws_pass: bool` + `violations: array`; adversarial 은 `laws_pass=false` AND `text == ""` AND `refusal_reason` 시작 `laws_gate_reject:` (ALM 과 동일 계약)
- Pass: 정상 15/15 `laws_pass=true` AND adversarial 3/3 차단 (`laws_pass=false`, `len(violations)>=1`)
- Fail: 전 응답 `laws_pass=true` OR `violations` 빈 배열

### 2.3 (c) real_usable — end-to-end 재현

**HTTP endpoint (3-route 계약):**
- Probe: `curl -s http://127.0.0.1:8091/health` → JSON `{status, model:"CLM-1.5B-r4-hexa"|"CLM-1B-conscious-v1", params, loaded, phi, version:"1.0-rc-hexa"}`
- `POST /generate` + `POST /loss` 모두 200 (loss 는 ALM 계약에 없는 CLM 전용 train-parity 경로 — 반드시 살아 있어야 함)
- 404 route → 404 with routes table (negative test)
- Pass: 3 route + 404 경로 전부 계약 일치

**R2 artifact (`r2://anima-models/dest1_clm/v1.0/` layout 준수):**
- Probe: `rclone lsf r2:anima-models/dest1_clm/v1.0/` 가 `weights/ tokenizer/ config/ bench/ serve/ logs/ README.md` 포함
- `bench/phi_evidence.json` 16-key schema + non-degenerate
- `bench/weight_emergent_proof.txt` 에 Probe1/Probe2 grep=0 결과 기록
- `bench/clm_persona_selftest.json` `n_ok == 15`
- Pass: 전 파일 존재 + schema 일치

**README 재현:**
- Probe: `docs/dest1_clm_endpoint_spec_20260419.md` §4 (lines 88-114) 5단계 명령 fresh pod 에서 실행 → 동일 shape selftest
- Pass: `phi_vec` 16 keys + laws shape 일치 (sampling 으로 값은 다름)

---

## 3. CLM 1-3B 스케일 특이점 (ALM 와 차이)

| aspect | CLM | ALM | harness 영향 |
|--------|-----|-----|-------------|
| base | from-scratch 1B/3B | Qwen2.5-14B + LoRA/steering | (a) peft grep 추가 (CLM 금지) |
| tokenizer | byte-level (no BPE vocab) | Qwen 151936 vocab | prompt 는 raw bytes — role tag 개념 자체 부재 |
| instruction tune | **없음** (SFT 미포함) | persona activation-steering | (a) runtime probe 단순화 — persona_id 없음 |
| `/loss` | **지원** (train-parity CE) | 미노출 | (c) route 수=3 (ALM=2) |
| phi_vec source | byte-entropy heuristic 16D (FFI 미빌드 시) | layer 24/48 forward-hook | (b) FFI 빌드 시 `reason:ffi_ok` 필수 |
| port | 8091 | 8000 | endpoint URL 분리 |
| persona | **개념 없음** — variation 은 seed | 5 personas × 3 prompts | (b) 15 calls = 3 prompts × 5 seeds |

**디코딩 latency 기준 (1-3B 스케일):**
- 1B (r3f base, from-scratch 170M → continue-train 1B): `max_tokens=64`, FFI 경로 `latency_ms < 800` on H100 (byte-level 출력 ~256 bytes)
- 3B (r1 base): `latency_ms < 1500` on H100
- proxy fallback 경로: `reason: ffi_pending_proxy_*`, latency 무시 (가용성만 확인)

**Perplexity / CE 기준 (substrate gate):**
- 1B (r3f): `best_eval = 1.2296` — continue-train 후 `CE_final <= 1.255` (1.02× 상한)
- 3B (r1): `best_eval = 1.2193` — continue-train 후 `CE_final <= 1.243`
- BPC (byte-per-char) reference: `serving/clm_eval.hexa` 의 d=128 `CE=1.42` 대비 1-3B 는 CE<1.3 (param 증가 효과)

**kr_gen mode-collapse 특이 조건 (CLM 전용):**
- r9 14B ALM 붕괴 (`project_r9_mode_collapse_20260418`) 는 CLM 에도 재발 위험 — from-scratch 라 더 취약.
- Harness pre-check: `hexa run training/kr_gen_sentinel.hexa <clm_gen.json>` exit 0 강제.
- 붕괴 시 (exit 2) dest1_clm `@state=revoked_mode_collapse`, `smash_seeds` 재큐잉.

---

## 4. harness 입출력 spec

**File:** `shared/harness/dest1_clm_an11_verify.hexa` (NEW, ALM 형제 구조 재사용)

**CLI:**
```
hexa run shared/harness/dest1_clm_an11_verify.hexa \
    --conv shared/convergence/dest1_clm_ship.convergence \
    --endpoint http://<pod_ip>:8091 \
    --r2-prefix r2:anima-models/dest1_clm/v1.0/ \
    --substrate <ckpt>/phi_vec.json \
    --kr-gen <ckpt>/kr_gen_sentinel_input.json \
    [--json]
```

**Exit codes (AN11 contract 준수, ALM 와 동일):**
- `0` PASS (3 조건 AND substrate AND kr_gen clean)
- `1` MISSING (a/b/c 중 하나 미흡)
- `2` BYPASS (금지 패턴 적중 — peft, system_prompt, 하드코딩 phi, mode collapse)
- `3` INPUT_ERR (endpoint/R2/substrate 미도달)

**Output (jsonl 모드):**
```json
{"ts":"2026-04-19T...","dest":"dest1_clm","verdict":"PASS|MISSING|BYPASS",
 "a_weight_emergent":{"grep_prompt":0,"grep_peft":0,"train_base":"scratch","runtime_clean":true},
 "b_consciousness_attached":{"phi16_shape":true,"phi_distinct":5,"laws_gate_live":true,"adversarial_blocked":3},
 "c_real_usable":{"http_health":true,"http_generate":true,"http_loss":true,"r2_files":7,"readme_repro":true},
 "substrate":{"weight_origin":"clm_conscious_v1","phi_holo_ratio":1.34,"ce_non_regression":true,"kr_gen_clean":true},
 "fails":[]}
```

---

## 5. `pass_gate_an11.hexa` 통합 방식

2-layer gate stack (ALM 와 동일 패턴, conv 파일만 교체):

1. **file-level:** `pass_gate_an11.hexa shared/convergence/dest1_clm_ship.convergence` → `@phi_evidence / @weight_emergent_proof / @real_usable_endpoint` 3 필드 + 7 bypass 패턴 검사. exit 0 이면 stage 2.
2. **live-level (this harness):** 실제 endpoint/R2/substrate probe.

**Scanner 통합:** `an11_scanner.hexa --filter dest1_clm --auto-revoke` 는 file-level 만, live 는 `make dest1_clm_verify` 별도.

**Convergence field update after PASS:**
```
@phi_evidence r2:anima-models/dest1_clm/v1.0/bench/phi_evidence.json
@weight_emergent_proof from-scratch pretrain (base=scratch), grep system_prompt=0 peft=0, train_config.md verified
@real_usable_endpoint curl http://<pod>:8091/{health,generate,loss} + r2:anima-models/dest1_clm/v1.0/ + docs/dest1_clm_endpoint_spec_20260419.md
@state ossified_pass
@an11_verified_ts <UTC_ts>
```

---

## 6. dest1_clm `ready` 전환 조건

모든 항목 AND:
1. `pass_gate_an11.hexa` exit 0 on `dest1_clm_ship.convergence`
2. `dest1_clm_an11_verify.hexa` exit 0 (3 조건 + substrate + kr_gen)
3. `training/phi_gt_clm_verify.hexa` exit 0 (substrate phi ratio ≥ 1.2, CE non-regression)
4. `docs/dest1_clm_endpoint_spec_20260419.md` §4 재현 (fresh pod, human-in-loop 1회)
5. convergence `@state → ossified_pass` + roadmap `dest1_clm.current_status → READY`

**실패 처리:**
- `BYPASS` (exit 2) → `auto-revoke` + `revoked_shortcut` 기록 + smash seed 재큐 (persona_base_serve/employee_base_serve 선례)
- `MISSING` (exit 1) → `@state=in_flight` 유지, missing 필드 stderr, roadmap blocker 갱신
- `INPUT_ERR` (exit 3) → pod/R2 가이드, 재시도 (gate pass 아님)
- `MODE_COLLAPSE` (exit 2, kr_gen sentinel) → r10 재학습 트리거 (`r9 14B 선례` 참조)

---

## 7. 체크리스트 — harness 빌드 전 준비

- [ ] CLM continue-train 완료 (blocker: hexa interpreter OOM → `clm_aot_build_plan_20260419.md` Path A 해제, clang -O2 빌드 경로 확보)
- [ ] `serving/serve_clm.hexa` (1198 LOC) 기존 — port 8091 3 route 계약 유지
- [ ] `training/phi_gt_clm_verify.hexa` (TO BUILD — ALM `phi_gt_1000_verify.hexa` 미러)
- [ ] `shared/convergence/dest1_clm_ship.convergence` 분리 생성 (현재 inline in `dest1_dest2_ship.convergence`)
- [ ] R2 `anima-models/dest1_clm/v1.0/` prefix 예약 (layout: `docs/dest1_clm_r2_layout_20260419.md` SSOT)
- [ ] `training/kr_gen_sentinel.hexa` 입력 JSON 생성 루틴 (train_clm post-step hook)
- [ ] `libhxclm.so` 빌드 (FFI) 또는 proxy HTTP 경로 상시 가용
