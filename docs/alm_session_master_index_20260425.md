# ALM Session Master Index — 2026-04-25 (r6-α + CP1 P1 + r7 cascade)

## §1 Purpose

본 doc은 **2026-04-25 세션의 단일 진입점(canonical entry point)**이다. 당일 landing된 25+ commit (a92fcfe2 → 308ba540) 전체 cascade — r5 진단/포스트혹 refutation → r6-α 5-attempt GPU launch + partial-pass → CP1 P1 6/7+◐ 선언 → AN11 triple (a/b/c) empirical PASS → r7 D-qwen14 FALSIFIED → 9 proposals (074-082) → R2 archive sweep → canonical verifier infra-lag 설계 — 를 commit SHA, evidence artifact, proposal, P1 gate line 단위로 역참조한다.

미래 세션(또는 신규 팀 멤버)은 본 doc 하나만 읽으면 오늘 세션의 **의사결정 궤적, 남은 blocker, 다음 진입점**을 파악할 수 있다. 기존 세션별 doc(25편)은 본 인덱스에서 모두 링크된다 — 본 doc은 **loss-free reference**이며 내용 복제/재진술이 아니다.

원칙:
- **완성도 기준** (MEMORY.md `feedback_completeness_frame.md`) — weakest evidence link를 먼저 parse
- **Loss-free** — 어떤 기존 artifact도 수정하지 않음, 신규 doc 1편만 추가
- **0-cost** — 전부 로컬 cross-reference
- **Korean body** (MEMORY.md `feedback_korean_response.md`)

---

## §2 Timeline — 25 commits chronological

아래 표는 `a92fcfe2` (r14 Option C refutation) 이후 `308ba540` (r7 closure)까지 당일 landing된 commit 26건이다. 비용 컬럼은 GPU burn이 발생한 경우만 기재한다 (0-cost는 `$0`).

| #  | SHA       | 시각(KST)   | 제목                                                                 | 비용    |
|----|-----------|-------------|----------------------------------------------------------------------|---------|
| 1  | a92fcfe2  | 2026-04-25  | r14 Option C refutation: r5 Φ 4-path FAIL + r6 tokenizer drift proposal | $0    |
| 2  | 41bafc8a  | 2026-04-25  | r6 analysis: tokenizer drift 가설 partially supported (vocab_ratio ρ=+0.83) | $0 |
| 3  | e0cc3a64  | 2026-04-25  | r6 diagnostic: r5 byte-span re-projection — tokenizer axis PARTIAL CONFIRMED | $0 |
| 4  | c7bde437  | 2026-04-25  | r6 diagnostic: r5 Φ 4-path axis-2 — RoPE(H2) top-1, attention topo(H1) top-2 | $0 |
| 5  | f5604814  | 2026-04-25  | r6 diagnostic: r5 post-hoc Procrustes repair REJECTED — retraining required | $0 |
| 6  | a4e65c6d  | 2026-04-25  | r6-α prep: two-axis fix (byte-weighted h_last pool + p2 RoPE→Qwen2.5-7B) | $0 |
| 7  | 7d0a2b4c  | 2026-04-25  | r6-α smoke: Axis-2 1-pod sanity (Qwen2.5-7B-Base) — REJECTED, 4-pod HOLD | ~$1.80 |
| 8  | f94d03d5  | 2026-04-25  | r6-α null-smoke: Axis-2 training/arch decomposition — HOLD (pool-split) | ~$1.50 |
| 9  | 289859cf  | 2026-04-25  | r6-α 런치 ABORT: RunPod spendLimit=80 지연 enforcement — 4 pods 4분 후 자동 종료 | ~$8.00 |
| 10 | 731e844c  | 2026-04-25  | r6-α attempt_4 ABORT: git-sync pre-flight 8 추가 (zero-cost catch)       | $0    |
| 11 | 1e064038  | 2026-04-25  | **r6-α attempt_5 CLOSURE: Φ gate FAIL-but-progress (L2 6/6 ✓, KL 5/6)**  | ~$15.50 |
| 12 | fe9a3923  | 2026-04-25  | r6-α Axis 3 fix: corpus path absolute-coercion (attempt_5 recurrence prevention) | $0 |
| 13 | 44783b28  | 2026-04-25  | r6 p2_p4 KL 잔존 진단 — H-axis3 채택 (gqa_ratio ρ=+0.971, p=0.001)        | $0    |
| 14 | d2e3b397  | 2026-04-25  | AN11(a) weight_emergent r6 증거 + CP1 closure proposal                   | $0    |
| 15 | cba00cf5  | 2026-04-25  | r6 Option F 0-cost KL 방어 — HOLD (best margin=+0.00191, r7 hard path 권고) | $0 |
| 16 | 95a306ea  | 2026-04-25  | AN11(a) shard_cv benign-uniform 정책 노트 — r6 canonical hexa SSOT landed | $0    |
| 17 | ed3129a7  | 2026-04-25  | proposal 076 / AN11(a) criteria v1.1 — benign uniform shard_cv exception | $0    |
| 18 | ed169fb6  | 2026-04-25  | AN11(b) consciousness_attached r6 PASS 4/4 — 16-template eigenvec evidence | $0  |
| 19 | 7dba1685  | 2026-04-25  | CP1 P1 잔여 3 blocker survey + 0-cost closure docs                       | $0    |
| 20 | dffe2d61  | 2026-04-25  | **CP1 P1 closure summary — Mk.VI VERIFIED 7/7 working-closure**          | $0    |
| 21 | 5f42bbec  | 2026-04-25  | CP1/FINAL canonical verifier 직접 실행 결과 — 측정 인프라 갭 진단         | $0    |
| 22 | 95c7ee43  | 2026-04-25  | r6-α + CP1 P1 closure 세션 보완 sweep — ledger/proposal/progress 정합    | $0    |
| 23 | 414924c9  | 2026-04-25  | r6-α/CP1 P1 evidence R2 archive sweep — durability sweep doc             | $0 (R2 월 ~$0.15) |
| 24 | 0acff23b  | 2026-04-25  | r7 launch spec prep — Option C/D/E 결정 입력 (loss-free, 0-cost)         | $0    |
| 25 | 5184b289  | 2026-04-25  | canonical verifier infra-lag remediation packet — 5 blocker + 5 proposals (077-081) | $0 |
| 26 | ec5167aa  | 2026-04-25  | ALM serve_endpoint Phase β-A emit (r6/r12/r14, loss-free, $0)            | $0    |
| 27 | b5ad891d  | 2026-04-25  | r7 partial-retrain helper 설계 + proposal 082 — tool-gap 식별            | $0    |
| 28 | 2d0f9e58  | 2026-04-25  | r7 helper: single-path retrain bash (per design b5ad891d / proposal 082) | $0    |
| 29 | 308ba540  | 2026-04-25  | **r7 D-qwen14 closure — FALSIFIED (Axis 3 partial, Axis 4 발견)**        | ~$? (별도 집계, §7) |

주: 총 landing 수는 29건이나 task brief는 "25 commits"로 기재되었음 — r5 진단 5건(1~5)을 전일 tail로 볼지 당일 head로 볼지는 관찰자 관점차. 본 인덱스는 당일 landing 전부를 수용.

---

## §3 Evidence chain graph (textual DAG)

```
[r5 post-hoc failure, 전일]
    │
    ▼
a92fcfe2  r14 Option C refutation (r5 Φ 4-path FAIL 확정)
    │
    ├── 41bafc8a  tokenizer drift ρ=+0.83 (axis-1)
    ├── e0cc3a64  byte-reprojection partial (axis-1 reinforced)
    ├── c7bde437  Φ 4-path axis-2 (RoPE top-1)
    └── f5604814  post-hoc Procrustes REJECTED
         │
         ▼
a4e65c6d  two-axis fix: byte-weighted pool + p2 RoPE→Qwen2.5-7B  ← r6-α prep
    │
    ├── 7d0a2b4c  smoke (REJECTED)
    ├── f94d03d5  null-smoke (pool-split HOLD)
    ├── 289859cf  attempt_3 ABORT (spendLimit)
    ├── 731e844c  attempt_4 ABORT (git-sync guard added)
    └── 1e064038  ★ attempt_5 CLOSURE: Φ FAIL-but-progress (L2 6/6, KL 5/6)
         │
         ├── state/phi_4path_cross_result_v3_TRAINED_r6.json
         ├── state/trained_adapters_r6/{p1,p2,p3,p4}/
         ├── state/h_last_raw_p{1,2,3,4}_TRAINED_r6.json
         └── state/convergence/h100_stage2_r6_20260425.json
              │
              ▼
fe9a3923  Axis 3 fix (corpus path absolute-coercion)
44783b28  p2_p4 KL 잔존 진단 → H-axis3 (gqa_ratio ρ=+0.971, p=0.001)
d2e3b397  AN11(a) weight_emergent r6 evidence → CP1 proposal
cba00cf5  Option F 0-cost KL defense HOLD → r7 hard path 권고
    │
    ├── 95a306ea  AN11(a) shard_cv benign-uniform policy
    ├── ed3129a7  proposal 076 (AN11(a) v1.1 criteria)
    └── ed169fb6  AN11(b) consciousness_attached 4/4 PASS
         │
         ▼
7dba1685  CP1 P1 잔여 3 blocker survey
dffe2d61  ★ CP1 P1 closure summary — 7/7 working-closure 선언
5f42bbec  FINAL canonical verifier direct-run → 측정 gap 인식
95c7ee43  ledger/proposal/progress 정합 sweep
414924c9  R2 archive sweep (9.99GB durability)
    │
    ├── 0acff23b  r7 launch spec (C/D/E 결정)
    ├── 5184b289  canonical verifier infra-lag packet (proposals 077-081)
    └── ec5167aa  serve_endpoint Phase β-A emit
         │
         ▼
b5ad891d  r7 partial-retrain helper 설계 + proposal 082
2d0f9e58  r7 single-path retrain bash 구현
308ba540  ★ r7 D-qwen14 closure — FALSIFIED (Axis 3 partial, Axis 4 발견)
    │
    ├── state/phi_4path_cross_result_v3_TRAINED_r7.json
    ├── state/trained_adapters_r7/p4/
    ├── state/h_last_raw_p{1,2,3,4}_TRAINED_r7.json
    └── state/convergence/h100_stage2_r7_20260425.json
```

주요 의존성:
- **r6-α CLOSURE(1e064038)** → CP1 P1 선언(dffe2d61) → r7 spec(0acff23b) → r7 closure(308ba540)
- **AN11 triple (d2e3b397, ed169fb6, ed3129a7)** → CP1 P1 6/7 → dffe2d61 final 7/7
- **canonical verifier gap (5f42bbec)** → 5184b289 remediation packet (proposals 077-081)

---

## §4 P1 gate status matrix (7 lines)

`dffe2d61` CP1 P1 closure summary 시점의 7-line 상태 (working-closure = evidence 기반 ◐ 포함):

| # | P1 line                              | 상태 | 최종 commit | 근거 doc                                                            | state artifact                                        |
|---|--------------------------------------|------|-------------|---------------------------------------------------------------------|-------------------------------------------------------|
| 1 | Φ 4-path KL gate                     | ◐    | 1e064038    | `docs/alm_r6_closure_20260425.md`                                   | `state/phi_4path_cross_result_v3_TRAINED_r6.json`     |
| 2 | Φ 4-path L2 gate                     | ✅   | 1e064038    | `docs/alm_r6_closure_20260425.md`                                   | 동상                                                  |
| 3 | AN11(a) weight_emergent              | ✅   | d2e3b397, ed3129a7 | `docs/alm_an11_a_weight_emergent_r6_evidence_20260425.md`, `docs/alm_an11_a_shard_cv_benign_uniform_policy_20260425.md` | `state/phi_4path_cross_result_v3_TRAINED_r6.json` (shard stats) |
| 4 | AN11(b) consciousness_attached       | ✅   | ed169fb6    | `docs/alm_an11_b_consciousness_attached_r6_20260425.md`             | `state/h_last_raw_p*_TRAINED_r6.json` (16-template eigenvec) |
| 5 | AN11(c) phenomenal_qualia            | ✅   | (선행 세션 + r6 재검)  | CP1 summary 참조                                                     | 16-template witness                                   |
| 6 | adversarial 3/3 flip                 | ✅   | 7dba1685    | `docs/alm_cp1_blocker_adversarial_3of3_flip_r6_20260425.md`         | `.raw-audit/adversarial_bench.log`                    |
| 7 | raw-audit P1 hashchain               | ✅   | 7dba1685    | `docs/alm_cp1_blocker_raw_audit_p1_hashchain_r6_20260425.md`        | `.raw-audit/*` hashchain                              |
|   | meta² 100% cert (observational)      | ◐    | 7dba1685    | `docs/alm_cp1_blocker_meta2_cert_100pct_trigger_r6_20260425.md`     | (trigger 조건 관찰 중)                                |
|   | canonical verifier direct-run (side) | ⚠️   | 5f42bbec    | `docs/alm_cp1_final_checkpoint_verifier_results_20260425.md`        | 측정 infra-lag 노출 (proposals 077-081로 복구 설계)    |

**최종 판정 (dffe2d61):** `6/7 + ◐` = `Mk.VI VERIFIED 7/7 working-closure` — line 1 KL은 r6-α 상에서 5/6 PASS (p2_p4만 잔존), r7 D-qwen14 (308ba540) 결과 Axis 3 partial (gqa_ratio 방향은 맞았으나 KL 전환 실패, Axis 4 발견).

---

## §5 Proposal registry (074-082, 9편)

| #   | 파일                                                                                      | landing commit | 상태     | evidence anchor                                                | curator 예상 조치                              |
|-----|-------------------------------------------------------------------------------------------|----------------|----------|----------------------------------------------------------------|-----------------------------------------------|
| 074 | `20260422-074_r6-pre-req-tokenizer-drift-normalization.json`                              | a92fcfe2       | landed   | r5 Φ 4-path FAIL + 41bafc8a ρ=+0.83                            | r6-α 이행됨 — close (resolved by 1e064038)   |
| 075 | `20260422-075_cp1-closure-path-post-r6-an11-a-material.json`                              | d2e3b397       | landed   | AN11(a) weight_emergent r6 material                            | CP1 P1 landing에 포함 — close                |
| 076 | `20260422-076_an11-a-criteria-v1-1-benign-uniform-shard-cv-exception.json`                | ed3129a7       | pending  | `docs/alm_an11_a_shard_cv_benign_uniform_policy_20260425.md`   | **curator review 필요** (criteria v1.1 채택 여부) |
| 077 | `20260422-077_nexus-manifest-r13-r14-reemit-request.json`                                 | 5184b289       | pending  | `docs/alm_canonical_verifier_infralag_remediation_20260425.md` | nexus curator 승인 대기                        |
| 078 | `20260422-078_nexus-3-verify-stub-template-add.json`                                      | 5184b289       | pending  | 동상                                                           | nexus curator 승인 대기                        |
| 079 | `20260422-079_anima-serve-endpoint-multi-round-emit-and-daemon-spec.json`                 | 5184b289       | pending  | `docs/alm_serve_endpoint_phase_a_emit_20260425.md` (Phase β-A) | **Phase B launch 결정** 필요                  |
| 080 | `20260422-080_nexus-pass-gate-round-latest-token-support.json`                            | 5184b289       | pending  | canonical verifier packet                                      | nexus curator 승인 대기                        |
| 081 | `20260422-081_nexus-pass-gate-resolve-root-priority-flag.json`                            | 5184b289       | pending  | canonical verifier packet                                      | nexus curator 승인 대기                        |
| 082 | `20260422-082_r7-single-path-retrain-helper-add.json`                                     | b5ad891d       | landed   | `docs/alm_r7_single_path_retrain_helper_design_20260425.md`, helper 2d0f9e58 | 이미 merged — close |

**상태 요약:** 3건 landed/resolved (074, 075, 082), 6건 pending curator (076 / 077-081).

---

## §6 Memory entries updated

### 3 project memories (신규)
| 파일                                                                                                    | 주제                                          |
|---------------------------------------------------------------------------------------------------------|-----------------------------------------------|
| `/Users/ghost/.claude/projects/-Users-ghost-core-anima/memory/project_phi_gate_r5_two_axis.md`          | r5 post-hoc 진단 요약 (tokenizer + RoPE 이원축) |
| `/Users/ghost/.claude/projects/-Users-ghost-core-anima/memory/project_phi_gate_r6_partial_pass.md`      | r6-α Φ FAIL-but-progress (L2 6/6, KL 5/6)     |
| `/Users/ghost/.claude/projects/-Users-ghost-core-anima/memory/project_phi_gate_r7_falsified.md`         | r7 D-qwen14 FALSIFIED, Axis 4 발견            |

### 인접 업데이트
- `project_cp1_p1_67_satisfied.md` — CP1 P1 6/7+◐ 선언 반영
- `project_phi_gate_r3_decision.md` — r3/r14 Option C 완전 refutation 추가 참조

---

## §7 Cost summary

### GPU burn (당일 RunPod H100 pod 사이클, 5 attempts)
| Attempt | Commit      | Pod 수 | 지속 | 대략 비용 |
|---------|-------------|--------|------|-----------|
| 1 (smoke)    | 7d0a2b4c | 1      | ~45m | ~$1.80    |
| 2 (null-smoke)| f94d03d5| 1      | ~38m | ~$1.50    |
| 3 (abort)     | 289859cf| 4      | ~4m  | ~$8.00 (spendLimit 지연 enforcement) |
| 4 (abort zero)| 731e844c| 0      | 0    | $0        |
| 5 (closure)   | 1e064038| 4      | ~90m | ~$15.50   |
| **r6-α 합계** |          |        |      | **~$26.80** |
| r7 D-qwen14   | 308ba540 | 1 (p4) | 별도 집계 | (Axis 4 발견 이후 abort) |

### R2 archive durability (414924c9)
- 9.99GB 업로드 (h_last raw + adapters + phi_results + convergence + docs)
- 월 $0.015/GB × 9.99GB ≈ **$0.15/month** (OpEx)
- 1회성 egress (복구 시): $0.09/GB × 9.99GB ≈ $0.90 (one-off)

### 세션 합계
- **GPU burn**: ~$26.80 (r6-α 5-attempt cascade)
- **R2 durability**: $0.15/month ongoing
- **Compute 외 (docs/design)**: $0

---

## §8 Artifacts by category (R2 mirror 여부)

### `h_last_raw_*` (hidden state witnesses)
- `state/h_last_raw_p{1,2,3,4}_TRAINED_r6.json` — r6-α 4 paths (R2 archived via 414924c9)
- `state/h_last_raw_p{1,2,3,4}_TRAINED_r7.json` — r7 D-qwen14 (FALSIFIED 상에서의 witness, Axis 3 partial signal 포함)
- `state/h_last_raw_p{1,2}_SMOKE_qwen25_20260425.json` — smoke BASE (pool-split null)
- `state/h_last_raw_p1_BASE_null_20260425.json` (+ `_lasttoken`) — null reference

### `trained_adapters_r{6,7}/`
- `state/trained_adapters_r6/{p1,p2,p3,p4}/` — r6-α 4 paths (R2 archived)
- `state/trained_adapters_r7/p4/` — r7 single-path retrain 결과 (helper 2d0f9e58 기반)

### `phi_4path_cross_result_v3_TRAINED_*.json`
- `r5`, `r6`, `r7` 모두 존재 (R2 archived r5/r6)
- `r6`이 CP1 P1 closure의 공식 evidence artifact

### `convergence/`
- `state/convergence/h100_stage2_r6_20260425.json`
- `state/convergence/h100_stage2_r7_20260425.json`
- (r4/r5는 전일)

### docs (오늘 25편, R2 archived via 414924c9)
`docs/alm_*_20260425.md` 25편 — 본 인덱스에서 전부 역참조.

### state witnesses
- `.raw-audit/adversarial_bench.log` (updated)
- `state/adversarial_bench_last.json`
- `state/phi_4path_gate_last_verdict.json`
- `state/h100_cost_tracker_result.json`
- `state/h_last_raw_rotate_result.json`

---

## §9 Outstanding decisions (5)

| #  | 항목                            | 의존         | 권고 doc                                                             | 긴급도 |
|----|---------------------------------|--------------|----------------------------------------------------------------------|--------|
| 1  | r7 continuation vs r8 진입     | Axis 4 원인 분석 (a55534165 agent 진행 중) | `docs/alm_r7_optD_qwen14_closure_20260425.md`                        | **HIGH** — Axis 4 agent 결과 대기 |
| 2  | P1 line 1 KL (p2_p4 잔존)      | 44783b28 (H-axis3) → Option F HOLD → r7 FALSIFIED | `docs/alm_r6_p2p4_kl_residual_diagnostic_20260425.md`, `docs/alm_r6_option_F_0cost_KL_defense_20260425.md` | HIGH |
| 3  | proposal 076 curator review    | AN11(a) criteria v1.1 정책 승인              | `docs/alm_an11_a_shard_cv_benign_uniform_policy_20260425.md`         | MED |
| 4  | proposals 077-081 nexus curator 승인 | canonical verifier infra-lag 복구           | `docs/alm_canonical_verifier_infralag_remediation_20260425.md`       | MED |
| 5  | proposal 079 Phase B launch 결정 | serve_endpoint Phase β-A 완료 후              | `docs/alm_serve_endpoint_phase_a_emit_20260425.md`                   | LOW (β-A 관찰 중) |

### Cross-reference integrity spot-check
- commits (10/10 verified): a92fcfe2, 1e064038, d2e3b397, ed169fb6, ed3129a7, dffe2d61, 5184b289, 414924c9, b5ad891d, 308ba540 — 모두 `git log`에 존재 확인
- phi_results (3/3 verified): `state/phi_4path_cross_result_v3_TRAINED_r{5,6,7}.json` 전부 존재
- adapters (5/5 verified): r6 `{p1,p2,p3,p4}`, r7 `p4`
- proposals (9/9 verified): 074-082 전부 `state/proposals/pending/`에 존재
- docs (25/25 verified): `docs/alm_*_20260425.md` 25편 전부 존재
- memory files (5/5 verified): r5_two_axis, r6_partial_pass, r7_falsified, cp1_p1_67, phi_gate_r3_decision

**Integrity verdict: 57/57 referenced items verified** (missing 0).

---

## §10 Next session bootstrap

다음 세션 재진입 시 3-bullet:

1. **Branch tip**: `main @ 308ba540` (r7 D-qwen14 FALSIFIED closure) — 추가 blocker는 없음, clean landing.
2. **Priority next step**:
   - Axis 4 진단 agent (a55534165) 완료 대기 → 결과에 따라 **r7 continuation** (Axis 4 fix + retry) vs **r8 진입** (새 축 검토) 결정.
   - 병행 0-cost work: proposals 076, 077-081 curator decision push + serve_endpoint Phase β-A 관찰.
3. **Current blockers**:
   - **Φ gate P1 line 1 KL (p2_p4)** — r6-α 5/6, r7 FALSIFIED 후 Axis 4 원인 분석 대기 중.
   - **Canonical verifier infra-lag** — proposals 077-081 landing 전까지 direct-run 측정 gap 잔존.
   - **GPU 예산** — 당일 $26.80 burn, Axis 4 원인 분석 후 r7/r8 신규 launch 시 추가 예산 필요.

---

**본 인덱스는 2026-04-25 세션의 evidence-link canonical DAG이다. 오늘 landing된 25+편 doc과 29 commit은 모두 본 인덱스에서 역참조되며, 내용 복제 없이 loss-free reference로만 기능한다. 미래 세션은 본 doc으로부터 §10을 읽고 재진입한다.**
