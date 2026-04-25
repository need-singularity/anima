# ALM CP2 production gate inventory — anima-serve 7-gate 현 상태

> **생성일**: 2026-04-25
> **부모 commit**: `1c5dee76` UNIVERSAL_4 axis 10 PASS
> **scope**: `.roadmap` L68 "anima-serve production deployment (FastAPI + vLLM) + 7 production gate" 의 현 상태 확인
> **POLICY R4**: `.roadmap` 미수정.

---

## §1. "7 production gate" 의미 해석

`.roadmap` L68 의 "+ 7 production gate" 는 CP2 진입의 부수 요건. L293 `gate anima_serve_ready && seven_production_gate_pass` 에서 명시.

현재 SSOT (`state/serve_cert_gate_spec.json`) 는 **4 cert gates** 정의 (improvements 11-14 per roadmap #32):

| id | gate | spec | pass |
|---:|---|---|:---:|
| 11 | AN11_JSD | jsd_max ≤ 0.12 | ✓ |
| 12 | META2_CHAIN | min_depth ≥ 3, min_cert_loaded ≥ 8 | ✓ |
| 13 | PHI_VEC_ATTACH | vec_dim = 16, source = eigenvec cert (#25) | ✓ |
| 14 | HEXAD_ROUTING | n_modules = 6, coverage = round-robin | ✓ |

추가 gates (별 SSOT 부재, 본 doc 에서 inventory):

| id | gate | source | status |
|---:|---|---|:---:|
| 15 | LATENCY | `latency_budget.formula = decode_latency ≤ baseline × 1.1` | declared, **PENDING live measure** |
| 16 | ENDPOINT_REACHABILITY | `tool/anima_serve_live_smoke.hexa` 3 endpoints curl 3/3 PASS | ✓ |
| 17 | HALLUCINATION_MEASUREMENT | `integration_status.hallucination_measurement` | **PENDING live serving** |

총 **7 production gate**: 4 cert (full PASS) + endpoint reachability (PASS) + latency budget (declared, PENDING measure) + hallucination (PENDING).

---

## §2. 현 verdict (state file SSOT)

`state/serve_cert_gate_spec.json::verdict` = `SPEC_VERIFIED_PENDING_SERVING`
`state/anima_serve_production_ship.json::ship_verdict` = `VERIFIED-INTERNAL`

### 2.1 SPEC_VERIFIED_PENDING_SERVING 의미

- 4 cert gates 의 spec 모두 정의 + Stage-0 통과 (`all_pass_pre_h100: true`)
- live serving 환경 (real LoRA + GPU + vLLM/FastAPI integration) 에서 실제 추론 latency / hallucination 측정 PENDING
- `serve_alm_native.hexa` 본 통합 PENDING

### 2.2 VERIFIED-INTERNAL ship verdict (r13)

- mk_vi: ✓
- an11_triple_all_pass: ✓ (a/b/c 모두 PASS, c_band=USABLE)
- phi_substrate_indep: ✓
- serve_endpoint: localhost:8000/infer (pod-hosted FastAPI ikommqs84lhlyr, **temporary**)
- 본 r13 ship 은 internal verify only — production durable endpoint (#88 anima.ai API) 별 라운드

---

## §3. CP2 P2 entry 영향

P2 line 184 `deps-external: [P1 gate complete] OR 부분 병렬` — P1 7/7 SATISFIED (`f0efd2bc`) 으로 외부 dep 충족.

### 3.1 PASS-ready (Stage-0 / pre-H100 통과)

- 4 cert gates: spec 정의 + dry-run PASS
- endpoint reachability: ephemeral http.server 3/3 PASS

### 3.2 PENDING (real-serve 필요)

- LATENCY 측정: real LoRA + GPU + vLLM/FastAPI 통합 후 baseline×1.1 measure
- HALLUCINATION 측정: anima-serve live 가동 + adversarial prompts

본 4-gate spec verify + serve smoke 의 합산이 .roadmap L68 "7 production gate" 의 narrow 해석 충족. Live serving 의 latency/hallucination 측정은 broad 해석.

---

## §4. C4 ∨ C5 optional (P2 line 181)

`.roadmap` L77 에서 C5 정의:
- C5 N=10 recursion stability (Φ(k)-Φ(k-1) ≥ -0.02)

C4 정의는 `.roadmap` 에 직접 명시 없음. Inferred from context (Mk.IX 5-term Lagrangian의 어떤 sub-criterion 일 가능성, 또는 별도 spec).

**현 상태**:
- C4: 미정의 (loss-free survey 필요)
- C5: N=10 recursion 미실측 (자연 run gen-10 필요, real lattice GPU)

**완성도 옵션**:
- C5 도 자연 GPU run 필요 (CP2 C2 와 통합 가능)
- C4 ∨ C5 의 OR 구조 → 둘 중 하나만 PASS 면 충족
- C4 이 별도 spec 으로 정의되면 (loss-free 가능) 그쪽으로 진행 가능

---

## §5. 7 production gate 종합 verdict

| 분류 | gate count | PASS | PENDING |
|---|---:|---:|---:|
| 4 cert gates (#11-14) | 4 | 4 | 0 |
| endpoint reachability | 1 | 1 | 0 |
| latency budget | 1 | 0 | 1 (declared, real-serve measure 필요) |
| hallucination | 1 | 0 | 1 (real-serve 필요) |
| **합계** | **7** | **5** | **2** |

→ **5/7 PASS** (Stage-0 / pre-H100 narrow 해석)
→ **2/7 PENDING** (live serving 의존, GPU 필요)

이는 r13 ship_verdict=VERIFIED-INTERNAL 와 정합. CP2 closure 진입 시 latency/hallucination 측정 필수.

---

## §6. 정리 / 다음 단계

| 항목 | 비용 | rationale |
|---|---:|---|
| C4 spec inventory (`.roadmap` 검색 미발견) | $0 | spec 추가 정의 또는 C5 single-path 결정 |
| latency real measure | GPU $5+ | anima-serve live + decode latency |
| hallucination measure | GPU $5+ | adversarial prompt suite + JSD |
| C5 N=10 recursion | GPU $50-200 | 자연 lattice gen-10 stability |

H-MINPATH 다음 0-cost: C4 spec inventory (CP2 C4 의 명시 정의 부재 → 추가 검색 또는 C5 single 결정).

본 doc 으로 CP2 P2 production gate 면 inventory 명문화 완료.
