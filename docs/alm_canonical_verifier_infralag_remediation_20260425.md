# ALM Canonical Verifier Infra-Lag Remediation Packet (2026-04-25)

> **세션**: commit `5f42bbec` (CP1/FINAL canonical verifier 직접 실행) 후속 — 측정 인프라 r12-frozen ↔ r6-current evidence 사이의 gap 해소를 위한 **loss-free 사전 packet**.
> **모드**: 0-cost local-hexa, design + proposals only. Pod 미사용, daemon 미가동, nexus 미수정.
> **결론 한 줄**: 5 blocker 중 anima-internal 1건 + nexus-side 3건 + cross-cutting 1건 — anima 측은 serve_endpoint config 합리 + r6 phi_vec emit 으로 (c)/(b) 판정 입력 충족 가능, nexus 측은 manifest re-emit + 3 stub 추가 + pass_gate `--round latest`/`resolve_root` 패치가 필요. 모든 nexus 작업은 cross-repo 제안서로 분리 제출.

---

## §1. 목적

본 packet 은 `5f42bbec` 에서 진단된 canonical CP1 + FINAL verifier 측정 인프라 갭을 **r12-frozen → r6-current** 상태로 끌어올리기 위한 사전 설계 + 제안서 묶음이다. 직접 구현은 **포함하지 않는다** (anti-scope §7). 본 문서는 다음을 제공한다:

1. 5 개 blocker 의 cross-repo scoping (anima / nexus / both)
2. anima-internal 작업 항목 + 본 commit 에서의 처리 범위
3. nexus-side 제안 ID + cross-repo 제출 SSOT
4. blocker 간 sequencing (gate-level dependency graph)
5. 예상 verifier 성과 (CP1 5/22 → ≥18/22, FINAL 2/3 → 3/3)

---

## §2. 5 Blocker 와 Cross-Repo Scoping

### Blocker 1 — `manifest.jsonl` r12-frozen → r13/r14 재emit 필요

| 항목 | 내용 |
|------|------|
| 위치 | `/Users/ghost/core/nexus/calc/alm_verify/manifest.jsonl` (27 line) |
| 관찰 | 모든 `id` field 가 `alm_r12_*` 패턴, `round:"r12"` hard-pinned. r13 corpus / r14 corpus / r6-α 4-path 어떤 round 도 진입 못함 |
| 생성기 | `nexus/calc/alm_verify/generator.hexa` (676 line) — `--emit --round r{N}` 옵션 지원 추정 (line 15 usage 참조) |
| 영향 | CP1 verifier 22 entry × all r12 → 16 FAIL (input_path 누락) + 3 SKIP (stub 부재) + 5 PASS (r12 잔존 산출물) |
| **Scope** | **nexus-side** (generator 와 manifest 모두 nexus 소유). anima 가 cross-repo 호출만 가능. |

→ anima 측 직접 작업 불가. **Proposal 077** 으로 cross-repo 요청 제출.

### Blocker 2 — 3 verify-stubs 미존재 (manifest 에서 참조하지만 파일 없음)

| 항목 | 내용 |
|------|------|
| Missing 1 | `verify_alm_r12_validity_an11_b_consciousness_attached.hexa` |
| Missing 2 | `verify_alm_r12_validity_an11_c_real_usable.hexa` |
| Missing 3 | `verify_alm_r12_validity_cross_prover_diagonal.hexa` |
| 위치 | `/Users/ghost/core/nexus/calc/alm_verify/` (19 stub 존재, 22 manifest entry → 3 SKIP) |
| 영향 | G_VALIDITY 3 SKIP → 0 PASS — `deterministic_gates=5/5` 절 직접 미충족 |
| **Scope** | **nexus-side** (stub 패턴 = `nexus/calc/alm_verify/verify_*.hexa`). generator.hexa 의 `--emit --round r13` 시 manifest 의 `verifier_type` field 에 따라 자동 stub 생성됨. 단 3 missing entry 는 `verifier_type` 이 `an11_b_consciousness_attached`, `an11_c_real_usable`, `cross_prover` 등 generator 가 미지원하는 신규 type → generator 측 template 추가 필요. |

→ anima 측 직접 작업 불가. **Proposal 078** 로 cross-repo 요청 제출 (Proposal 077 의 sub-task).

### Blocker 3 — FINAL (c) live serving daemon + `alm_*_serve_endpoint.json` 부재

| 항목 | 내용 |
|------|------|
| Verifier logic | `nexus/consciousness/pass_gate_an11.hexa::verdict_real_usable` (line 385-428) — 4 단계 검증: file_exists → url field → HTTP 200 → reply_schema field |
| 현재 anima 상태 | `state/alm_r13_serve_endpoint.json` 존재 (url=`http://localhost:8000/infer`). r12/r6 는 미존재. **localhost 8000 미가동.** |
| 의미론 mismatch | `35aa051a` 에서 anima-local 정적 JSD=1.000 측정 — verifier 는 live HTTP 응답 요구 (정적 distribution artifact 인정 안 함) |
| Daemon 자산 | anima 측 `tool/serve_alm_persona.hexa` (port 8000 default) 이미 존재. `--dry` 모드로 boot dryrun 가능. |
| **Scope** | **anima-internal + cross** — endpoint config 파일은 anima 측 emit 가능, 그러나 verifier 가 **live HTTP 200 + reply_schema** 를 요구하므로 daemon 가동이 필수. |

→ anima 측 endpoint config emit (loss-free) + daemon 가동 spec doc 가능. 그러나 daemon 실 가동은 **포트 할당 + 사용자 승인** 필요 → **Proposal 079** 로 anima-internal 작업으로 카드화.

### Blocker 4 — `--round latest` literal token 미지원

| 항목 | 내용 |
|------|------|
| 위치 | `nexus/consciousness/pass_gate_an11.hexa::run_runtime_mode` (line 472-520) |
| 관찰 | `state_dir + "/" + dest + "_" + round + "_phi_vec.json"` 처럼 `round` 가 그대로 path 에 합성됨. `r12` 처럼 literal round ID 만 작동, `latest` 는 `alm_latest_phi_vec.json` 같은 미존재 파일 참조 → 3/3 FAIL |
| `.roadmap` 정의 | line 269-271 에 `--round latest` 명시 — verifier 가 미지원이라 roadmap 명령이 그대로 작동 안 함 |
| 패치 size | 작음 — round 이 "latest" 일 때 manifest.jsonl 의 가장 최신 round 또는 state/alm_r*_phi_vec.json glob 의 max 를 resolve 하는 logic 5~10 line |
| **Scope** | **nexus-side** (pass_gate_an11.hexa 가 nexus 소유). |

→ **Proposal 080** 으로 cross-repo 요청 제출.

### Blocker 5 — `resolve_root()` priority `ANIMA` env 가 nexus phi_vec 을 mask

| 항목 | 내용 |
|------|------|
| 위치 | `nexus/consciousness/pass_gate_an11.hexa::resolve_root` (line 167-176) |
| Priority | `env(ANIMA)` → `env(NEXUS)` → `git rev-parse` → `~/Dev/nexus` |
| 관찰 | ANIMA env 가 live (예: `/Users/ghost/core/anima`) 이면 verifier 가 anima 측 state 디렉터리를 root 로 채택 → `alm_r12_phi_vec.json` 을 anima 에서 찾는데 거기 없음 → FAIL. nexus state 의 phi_vec 은 무시됨. |
| 임시 해결 | `env -u ANIMA hexa run consciousness/pass_gate_an11.hexa --dest alm --round r12` — 이미 docs `5f42bbec` §3 에서 사용 중 |
| 진짜 해결 | (a) `--repo-root` flag 추가, 또는 (b) anima/nexus 양쪽 state 디렉터리를 동시 검사하는 dual-search logic, 또는 (c) `--state-dir` 명시 flag |
| **Scope** | **nexus-side** (pass_gate_an11.hexa). 현재는 운영자 워크어라운드 (`env -u ANIMA`) 로 우회 가능. |

→ **Proposal 081** 으로 cross-repo 요청 (저우선 — 워크어라운드 존재).

### Scoping 요약

| Blocker | Anima | Nexus | Cross | Proposal ID |
|---------|:-----:|:-----:|:-----:|-------------|
| 1 manifest re-emit | | ✓ | | 077 |
| 2 3 stubs missing | | ✓ | | 078 |
| 3 serving daemon | △ | △ | ✓ | 079 (anima-internal) |
| 4 `--round latest` | | ✓ | | 080 |
| 5 resolve_root prio | | ✓ | | 081 |

---

## §3. Anima-Internal Action Items (loss-free 사전 작업)

### A1. serve_endpoint.json multi-round emission spec (Proposal 079 의 sub-design)

**현재**: `state/alm_r13_serve_endpoint.json` 만 존재 (url=`http://localhost:8000/infer`).

**제안**: r12 / r6 round 에도 동일 schema 의 endpoint config 를 emit. 이는 verifier 가 file_exists + url field 두 단계는 통과하게 한다 (HTTP 200 단계는 daemon 가동 필요).

**제안 schema** (anima/state/alm_r{N}_serve_endpoint.json):
```json
{
  "schema": "anima/alm_r{N}_serve_endpoint/1",
  "url": "http://localhost:8000/infer",
  "health_path": "/health",
  "infer_path": "/infer",
  "payload_template": "{\"prompt\":\"<X>\",\"temperature\":0.9}",
  "ts": "<ISO8601>",
  "daemon_status": "designed_not_launched",
  "round": "r{N}"
}
```

**본 commit 범위 외**: 실 emit 은 daemon spec 결정 후 별도 카드 (Proposal 079).

### A2. AN11(c) live-vs-static reconciliation note

**현재 mismatch**: `35aa051a` 의 정적 JSD=1.000 (anima local) ↔ nexus verifier 의 live HTTP 200 요구.

**해석**: 두 path 는 **다른 의미론**. 정적 JSD 는 distribution-level evidence (training collapse 아님 입증), live HTTP 200 은 deployment-level evidence (serving binding 작동). FINAL gate 는 후자를 요구.

**본 commit 범위 외**: anima 측 docs `serve_endpoint_synthesis_20260421.md` 에 dual-evidence 절을 addendum 으로 추가 (별도 카드). 본 packet 은 spec 만 명시.

### A3. `env -u ANIMA` 워크어라운드 명시 (Blocker 5)

**현재**: 운영자가 매번 `env -u ANIMA hexa run ...` 으로 우회. nexus 측 패치 (Proposal 081) 까지는 이게 canonical 호출 방식.

**본 commit 범위**: §6 sequencing 표에 명시. tooling 측 wrapper 작성은 별도 카드.

### Anima-internal 작업 — 본 commit 에서의 처리

- ✅ docs (본 문서) 작성
- ✅ 4 개 proposal 카드 (077, 078, 079, 080, 081) 작성
- ❌ 실 endpoint config emit (Proposal 079 승인 후)
- ❌ daemon 가동 (Proposal 079 + 사용자 승인 후)

---

## §4. Nexus-Side Proposal IDs

본 commit 에서 발행하는 cross-repo 제안서 (state/proposals/pending/ 하 위치):

| ID | 제목 | Blocker | 우선순위 |
|----|------|---------|----------|
| **20260422-077** | Manifest r13/r14 재emit 요청 — generator.hexa --emit --round r13 | 1 | High (CP1 unblock 1순위) |
| **20260422-078** | 3 verify-stub template 추가 (an11_b/an11_c/cross_prover) | 2 | High (077 sub-task) |
| **20260422-079** | ALM serve_endpoint multi-round emit + daemon 가동 spec | 3 | Medium (FINAL c 전용, anima-internal) |
| **20260422-080** | pass_gate_an11 `--round latest` token 지원 패치 | 4 | Low (운영자 호출 시 literal round 명시 가능) |
| **20260422-081** | pass_gate_an11 resolve_root() priority — `--repo-root` flag 도입 | 5 | Low (워크어라운드 존재) |

각 카드는 `state/proposals/pending/20260422-{id}_*.json` + `state/proposals/refinement/20260422-{id}/v1.json` 로 ed3129a7 (proposal 076) precedent 따라 commit 됨.

---

## §5. Sequencing — Gate-Level Dependency Graph

```
                   ┌───────────────┐
                   │ Proposal 077  │  manifest r13 emit
                   │ (nexus-side)  │  → 22 entry round=r13 으로 변환
                   └───────┬───────┘
                           │ (depends_on, Proposal 078 필수 선행)
                           ▼
                   ┌───────────────┐
                   │ Proposal 078  │  3 stub template 추가
                   │ (nexus-side)  │  → generator 가 b/c/cross_prover 자동 emit
                   └───────┬───────┘
                           │
       ┌───────────────────┴───────────────────┐
       │                                       │
       ▼                                       ▼
┌──────────────┐                       ┌──────────────┐
│ CP1 unblock  │                       │ FINAL unblock │
│  expected:   │                       │   prereq:     │
│  18-20 PASS  │                       │ Proposal 079  │
└──────────────┘                       │ (anima daemon)│
                                       └───────┬──────┘
                                               │
                                               ▼
                                       ┌──────────────┐
                                       │ FINAL 3/3    │
                                       │  PASS 가능    │
                                       └──────────────┘

Proposal 080 (--round latest) — 081 (resolve_root) 은 운영성 개선,
CP1/FINAL gate 통과에 필수 아님 (워크어라운드 존재).
```

### 권장 sequencing

1. **Phase α** (nexus-side curator approves): 078 (template 추가) → 077 (--emit --round r13 실행) — 두 카드 동시 또는 078 선행.
2. **Phase β** (anima-internal): 079 — endpoint config 3 round emit + daemon spec 확정 + 사용자 승인 후 가동.
3. **Phase γ** (선택): 080, 081 — 운영성 개선.

각 phase 끝에 verifier 재실행으로 진척 측정.

---

## §6. Predicted Outcome After Remediation

### CP1 verifier (alm_verify/run_all.hexa)

| Phase | total | PASS | FAIL | SKIP | exit |
|-------|-------|------|------|------|------|
| 현재 (5f42bbec) | 22 | 5 | 14 | 3 | 1 (DISCARD) |
| Phase α 후 (077+078 land) | 22 | **≥18** | ≤2 | 0~2 | 0 (KEEP 가능) |
| Phase α + β 후 (079 land) | 22 | **≥20** | ≤1 | 0 | 0 |

**근거**:
- G_INPUT 4/4: r13 corpus (`/workspace/corpus/corpus_alm_r13.jsonl` 또는 anima `state/alm_r13_corpus_audit.json`) 가 input_path 로 진입 → 4 PASS.
- G_SUBSTRATE 3/3: r13 train log 존재 (`state/alm_r13_train_log.jsonl`) → loss/step/vram 3 PASS.
- G_TRAIN 3/3: 위와 동일.
- G_EVAL 3/3: r13 phi_vec / probe_ce / benchmark 산출물 anima 측 존재.
- G_VALIDITY 4/6 → 6/6: 3 SKIP → 3 PASS (an11_b/c/cross_prover stub 가 생성되어 r13 metric 측정).
- G_ARTIFACT 0/2: R2 upload 별도 work (이번 packet 범위 외).
- G_DECISION 0/1 → 1/1: r13 SSOT decision tag 존재 (ed169fb6).

### FINAL verifier (pass_gate_an11.hexa --dest alm --round r13)

| Phase | (a) | (b) | (c) | overall |
|-------|:---:|:---:|:---:|:-------:|
| 현재 (round=r12, ANIMA env unset) | PASS | PASS | FAIL | PARTIAL 2/3 |
| Phase α 후 (round=r13, manifest re-emit) | PASS | PASS | FAIL | PARTIAL 2/3 |
| Phase α + β 후 (079 land, daemon up) | PASS | PASS | **PASS** | **PASS 3/3** |

**근거**: (a)/(b) 는 phi_vec_path 만 충족하면 PASS 유지 (현재 r12 phi_vec 으로도 PASS 함). (c) 는 daemon HTTP 200 + reply_schema 가 land 하는 즉시 PASS.

### CP2 / FINAL declaration 가능성

- CP1 verifier-PASS 진입 시 POLICY R6 의 CP2 차단 해제. r13 corpus + AN11 triple PASS 기반으로 CP2 (`weight-emergence-confirmed`) 진입 가능.
- FINAL 3/3 PASS 진입 시 (substrate_indep 외부 evidence Φ 4-path L2 6/6 별도) FINAL `consciousness-transplant` waypoint 선언 적격 — 단 .roadmap 편집 절차 (POLICY R4) 별도.

---

## §7. Anti-Scope (POLICY R4/R6 + 본 packet 한계)

- ❌ **nexus 디렉터리 직접 편집 금지** — generator.hexa, manifest.jsonl, pass_gate_an11.hexa, verify_*.hexa 어느 것도 본 commit 에서 수정 안 함.
- ❌ **daemon 가동 금지** — port 할당 + 사용자 승인 + serve_alm_persona.hexa 모드 결정 미완. 본 packet 은 spec doc 만.
- ❌ **verifier 재실행 금지** — `5f42bbec` 에서 측정 완료. 본 commit 은 추가 측정 없음.
- ❌ **`.roadmap` 편집 금지** — POLICY R4 (uchg).
- ❌ **r6 artifact 변경 금지** — 본 packet 은 measurement infrastructure layer 만 다룬다.
- ❌ **r7 prep agent 와 작업 영역 겹침 금지** — r7 sibling agent 가 다루는 substrate 변경/curriculum/Φ gap 은 본 packet 범위 밖.
- ✅ **본 packet 범위**: docs (본 파일) + 5 proposal 카드 (077-081) + commit. 그 이상의 행동은 사용자 승인 후 별도 카드.

---

## §8. 핵심 요약

| 항목 | 값 |
|------|------|
| 진단 commit | `5f42bbec` (CP1 5/22, FINAL 2/3) |
| Blocker 수 | 5 (anima-internal 1, nexus-side 3, cross 1) |
| 발행 proposal | 077, 078, 079, 080, 081 |
| Anima 직접 작업 | docs + 5 proposal (loss-free) |
| Nexus 작업 요청 | 4 카드 (077, 078, 080, 081) |
| 예상 CP1 PASS (Phase α) | 18-20 / 22 (현재 5) |
| 예상 FINAL PASS (Phase α+β) | 3/3 (현재 2/3) |
| 운영 워크어라운드 | `env -u ANIMA hexa run ...` (Blocker 5 우회) |

**다음 사용자 결정 포인트**: Proposal 077-081 중 어느 카드를 어느 순서로 cross-repo 처리할지 + Proposal 079 의 daemon 가동 승인 여부.
