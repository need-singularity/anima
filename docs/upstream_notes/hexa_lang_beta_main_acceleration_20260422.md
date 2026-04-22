# hexa-lang β main 가속 — upstream 설계 스냅샷 (2026-04-22)

**Upstream 원본**: `$HEXA_LANG/docs/hexa_beta_main_top10_design_20260422.md`
**Upstream 브레인스토밍**: `$HEXA_LANG/docs/loss_free_roi_brainstorm_20260422.md`
**Upstream roadmap**: `.roadmap` 엔트리 54–63 (HXA-#01 ~ #10)

본 문서는 hexa-lang 측에서 β main (CP1 → CP2 → AGI v0.1) 가속을 위해 확정한 TOP 10 설계 스냅샷의 **anima 소비자 관점 미러**. anima 측에서 해야 할 사전 준비 + 마이그레이션 포인트를 정리.

---

## 1. anima 소비자 관점 요약 (hexa-lang NN → anima 영향)

| hexa-lang | anima 소비 경로 | 영향 |
|---|---|---|
| 54 cert_gate stdlib | `tool/cert_gate.hexa` refactor | −500 LOC 제거 (mechanism stdlib 이동), +200 LOC 유지 (policy). byte-identical selftest 재검증. |
| 55 deterministic FP | 모든 FP 연산 | `HEXA_STRICT_FP=1` 켜지면 FMA 비활성 → **training convergence 약간 드리프트**. 4-path Φ cross-substrate byte-identical 획득. |
| 56 http server | `tool/serve_alm_persona.hexa` | bash `nc` loop 제거, native hexa http server 직접 binding. `build_serve_loop_script` 삭제. |
| 57 BLAS-lite | `tool/phi_extractor_cpu.hexa` + `phi_extractor_ffi_wire.hexa` | 3 call-site (dot/nrm2/axpy) stdlib import 교체. 1×→8× 벡터 가속. |
| 58 eigen decomp | `tool/phi_extractor_*.hexa` | **현재 LCG synthetic fixture** → 실제 symmetric eigendecomp 도입. AN11(b) 16-template eigenvec cos>0.5 실증. |
| 59 .meta2-cert schema | `.meta2-cert/` 재조직 | schema v2 bump + `archive/` 하위로 timestamped mirror 이동 + `index.json` triggers 플래튼. 100-cert round-trip PASS 확보. |
| 60 CPGD | `edu/lora/cpgd_wrapper.hexa` + `cpgd_minimal_proof.hexa` + `lora_cpgd_init.hexa` + `tool/cpgd_minimal_proof.hexa` | 인라인 수학 ~700 LOC 제거 → stdlib import. selftest SHA 유지. |
| 61 proof-carrying ckpt | `ready/anima/checkpoints/**` | `.pt`/`.hexaw` → `.pcc` 마이그레이션 (genesis-retroactive cert 부여). G36 xxhash dedup 18 GiB 절감. |
| 62 signal + flock | `tool/serve_alm_persona.hexa` | bash `trap` 제거 + native SIGTERM handler. `state/serve_alm_persona_log.jsonl` append에 `with_lock_exclusive` 적용. |
| 63 concurrent serve | `serving/concurrent_serve_3in1.hexa` (신규) | CP2 dest2 employee/trading/zeta 3-endpoint 동시 서빙. SharedModelHandle read-only. |

---

## 2. anima 측 선행 준비 (hexa-lang 랜딩 대기 중 가능한 작업)

### 2.1 `.meta2-cert/` 마이그레이션 준비 (upstream 59 대응)
- `.meta2-cert/` 내 10 파일 전수 조사, entry cert에 `"schema_version":"2"` 추가 후보 확인.
- `evidence[].type` → `kind` 일괄 재작성 드라이런 스크립트 (stdlib validator landing 후 실행).
- timestamped mirror (`20260420T210243Z_*.json`) → `.meta2-cert/archive/` 이동 계획.
- **주의**: `index.json:entries[]` append-only 유지, `prev_index_sha` 체인 보전.

### 2.2 ckpt 목록화 (upstream 61 대응)
- `ready/anima/checkpoints/**` 하위 `.pt` + `.hexaw` 전수 목록 + 각 ckpt의 출처 (어느 training run, 어느 seed, 어느 cert-chain tip) 정리.
- `genesis-retroactive` 부여 시 reference할 cert chain 안전하게 anchor (raw#10 proof-carrying).

### 2.3 CP2 3-endpoint bench scaffold (upstream 63 대응)
- `bench/cp2_3in1_sequential.hexa` — 단일 스레드 300-request harness (upstream dispatch 전 baseline 확보 가능).
- `bench/cp2_3in1_concurrent.hexa` — upstream `concurrent_serve` landing 후에만 실행.

### 2.4 `tool/cert_gate.hexa` mechanism/policy 경계 식별 (upstream 54 대응)
- 현재 980 LOC 중 stdlib 이동 대상 (`verdict_base_score`, `json_str_field`, `compute_reward`, `sha256_file`, `load_cert`, `load_state`, `clamp`, `detail_json`, `write_result`) ≈ 500 LOC.
- anima 전용 유지 (`CORE_CERTS`, `MK8_TRIPLET`, `AN11_STATE_FILES`, `HEXAD_STATE_FILES`, `AUX_STATE_FILES`, `alignment_bias_factor`, `compute_an11/hexad/mk8/aux`, CLI `--target alm_r12`) ≈ 200 LOC.
- pre-migration `state/cert_gate_result.json` golden 캡처 → upstream 랜딩 후 byte-identical 회귀 게이트.

### 2.5 phi_extractor 콜사이트 정리 (upstream 57 + 58 대응)
- `tool/phi_extractor_cpu.hexa` 라인 250, 264, 347의 3 hot-loop 위치 문서화.
- `tool/phi_extractor_ffi_wire.hexa` 라인 199-220, 504-508 AN11(b) 경로 문서화.
- upstream `stdlib/linalg` + `stdlib/math/eigen` landing 후 import 교체만 남도록 준비.

### 2.6 serve_alm_persona 환경 정리 (upstream 56 + 62 대응)
- 현재 bash `nc` loop + `trap` + sentinel 파일 메커니즘 문서화.
- upstream 신규 native path 도입 후 제거 대상 라인 식별 (313-345 serve loop, 526-542 nohup 호출, trap 라인).
- E2E 테스트 fixture (fork + SIGTERM + shutdown.json verdict 검증) 사전 설계.

---

## 3. anima roadmap 내 업스트림 의존 선언 (권장)

hexa-lang 54–63이 anima 소비 의존을 만족시켜야 하는 β main 마일스톤. anima roadmap에 cross-repo dep 명시를 권장:

```
# anima/.roadmap — upstream 의존 선언 예시
anima@xxx  depends-on  hexa-lang@54  # cert_gate stdlib (B1)
anima@xxx  depends-on  hexa-lang@55  # deterministic FP (B20) — 4-path Φ critical
anima@xxx  depends-on  hexa-lang@56  # http server (B7) — CP1 serve prod-ready
anima@xxx  depends-on  hexa-lang@57  # BLAS-lite (B16) — phi_extractor 가속
anima@xxx  depends-on  hexa-lang@58  # eigen (B3) — AN11(b) 실측
anima@xxx  depends-on  hexa-lang@59  # .meta2-cert schema (B25) — 외부 채택
anima@xxx  depends-on  hexa-lang@60  # CPGD (B15) — AGI v0.1 70B retrain
anima@xxx  depends-on  hexa-lang@61  # proof-carrying ckpt (B5) — 위변조 차단
anima@xxx  depends-on  hexa-lang@62  # signal+flock (B8+B10) — CP1 graceful
anima@xxx  depends-on  hexa-lang@63  # concurrent serve (B12) — CP2 3-in-1
```

---

## 4. 시간 예상 / 병렬 실행

Upstream critical path (병렬 landing):
- **B20 (3.6주) → B16 (4주) → B3 + B15 (2주 + 2일) ≈ 9주**
- anima 마이그레이션은 각 upstream 랜딩마다 0.5–1주 추가.
- 전체 β main 가속 완료 예상: **~11–13주** (병렬), ~25주 (단일 직렬, 1인).

CP1 (serve_alm_persona LIVE) 가속 체감은 **B7 + B8+B10** 완료만으로도 상당 — 2–3주 내 가능.
CP2 (multi-endpoint) 가속 체감은 **B12 완료** 시점 — B7+B62 완료 후 2일 추가.
AGI v0.1 70B retrain 가속은 **B16 + B15 + B20** 모두 필요 — critical path full 소비.

---

## 5. 상태 추적

본 문서는 2026-04-22 스냅샷. 실제 진행은 hexa-lang 측 .roadmap 54–63 상태 필드 (`planned` → `active` → `done`) + anima 소비자 마이그레이션 PR로 추적.

업데이트 시점:
- hexa-lang roadmap 상태 전환 시
- 설계 변경 시 (upstream 원본 문서와 동기화)
- anima 측 마이그레이션 landing 시

Upstream 원본이 SSOT. 본 미러는 anima 기획 맥락용. 양자 불일치 시 upstream 우선.
