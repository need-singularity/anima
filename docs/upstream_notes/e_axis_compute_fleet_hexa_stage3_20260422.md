# E axis — infra · compute fleet / hexa stage3 / 4-repo integrated CI (paste-ready prompt)

**Status**: 7-axis framework 의 E 축 (infra) 누락분 보충. paste-ready (anima / hexa-lang / nexus 세션 모두 참조 가능).
**Date**: 2026-04-22
**Axis**: E (infra) — A(launch opt) / B(post-H100) / C(memory) / D(ship) / F(CPU superlimit) / G(meta) 에 누락되었던 infra 축.
**Scope**: 3 sub-task (E.1 compute fleet / E.2 hexa stage3 / E.3 4-repo integrated CI).
**Repo scope**: anima + hexa-lang + nexus + airgenome (cross-repo, each owner 명시).
**Cost ballpark**: E.1 runpod actuator landing + DR provision (~$5-30/month DR + variable pod), E.2/E.3 engineering only.

---

## 1. 배경 (context)

현재 상태 (2026-04-22 기준):
- **compute**: 4× H100 pod single-launch 체제. K56 (8-path substrate) / K58 (R2 cross-region) / K59 (pod autoscale) / K60 (distributed eval dispatcher) 모두 `SPEC_ONLY_NOT_ACTIVE` 상태로 설계만 존재. 실제 actuator 미구현.
- **hexa**: stage0 / stage1 (bootstrap) 동작 중. stage2 self-host 부분 완성 (transpiler 는 자체 hexa 로 구현 시작). stage3 (full self-compile + C deps 제거 + reproducible emit) 미진입. 2026-04-22 upstream note 에 builtin mangling bug (`hx_exec_capture`/`hx_now` prefix 누락) + reserved keyword conflict + `.find()` 미구현 3 종 발견.
- **4-repo CI**: airgenome / anima / hexa-lang / nexus 각자 own `.roadmap` + own `ci-validate` 만 존재. cross-repo proposal sync hub spec 은 `docs/upstream_notes/proposal_stack_cross_repo_sync.md` 에 존재 but 통합 CI 는 미구현.

3 sub-task 필요 이유:
- **E.1**: H100 × 4 single launch 는 risk concentrated. #83 launch 직후 re-selection / 4→8 scale 의사결정을 bash 로 수동 처리하면 wall-time + operator attention 낭비. K56+K58+K59+K60 spec 을 실 actuator 로 promote 해야 fleet operations 가능.
- **E.2**: anima 측 마이그레이션 (serve_alm_persona 등) 이 hexa stage 성숙도에 밟혀 있음. stage3 promotion 없이는 anima H100 tool chain 이 dist/ single-file packaging BLOCKED (N73). upstream bug 3 종 fix 전제.
- **E.3**: 4 repo 상호 proposal + cert + schema 교차 참조 증가. repo 하나 CI fail 이 다른 repo silent break 유발. 통합 CI gate 필요.

---

## 2. E 축 3 sub-task

### E.1 — compute fleet management (owner: anima + airgenome)

**목표**: SPEC_ONLY K56/K58/K59/K60 을 actuator 로 promote.

**sub-deliverables**:

1. **K56 promotion — 8-path substrate activation runner** (owner: anima)
   - file: `anima/tool/phi_8path_activation_runner.hexa` (NEW, ~250 LOC)
   - input: `anima/config/phi_8path_substrates_spec.json` activation_checklist 전항목 자동 verify
   - gate: `CP2 PASS + #56 launch decision + p6 DeepSeek license cleared (or V2-Lite fallback)`
   - output: `anima/state/phi_8path_activation_cert.json` (verdict, activated_paths[], skipped_paths[], skip_reasons[])
   - side-effect: NONE (weight download 은 별도 tool, 본 파일은 gate + decision only)

2. **K58 promotion — R2 cross-region DR actuator** (owner: airgenome)
   - file: `airgenome/tool/r2_cross_region_sync_actuator.hexa` (NEW, ~200 LOC)
   - reads: `anima/config/r2_cross_region_replicate.json` (canonical spec)
   - wraps: `rclone sync ... --dry-run` (default) 또는 `--apply` 시 실 sync
   - cron wiring: `airgenome/launchd/com.airgenome.r2_dr_sync.plist` (NEW, 1h interval)
   - gate: `DR_account_provisioned + first_manual_dry_run_approved`
   - output: `airgenome/state/r2_dr_sync_log.jsonl`, failure → `anima/state/r2_sync_dr_failure.json`

3. **K59 promotion — pod autoscale actuator** (owner: airgenome)
   - file: `airgenome/tool/pod_autoscale_actuator.hexa` (NEW, ~300 LOC)
   - reads: `anima/tool/pod_autoscale_spec.hexa` emit 결과 (`state/pod_autoscale_spec.json`) + `anima/state/job_queue.json`
   - wraps: `runpodctl pod create --gpuType H100SXM` (up) / `runpodctl pod terminate POD_ID` (down)
   - gate: `#59_launch_decision + queue_source_tool_landed + dry_run_100_steps_matches_spec`
   - output: `airgenome/state/pod_autoscale_actuator_log.jsonl` (per decision row: ts, depth, pre_pods, post_pods, pod_ids)
   - invariants: bounds (min=1, max=8) + cooldown=2 step 상속. flood protect: max 3 actuation/hour.

4. **K60 promotion — distributed eval remote dispatcher** (owner: nexus + anima)
   - file: `nexus/drill/distributed_eval_remote_dispatch.hexa` (NEW, ~200 LOC) — 이미 nexus drill preflight 존재 (upstream note §3), 확장
   - file: `anima/tool/unified_eval_shard_runner.hexa` (NEW, ~150 LOC) — per-shard remote runner skeleton
   - reads: `anima/state/distributed_eval_dispatcher_smoke.json` (shard assignment SSOT)
   - wraps: `hexa_remote pod_i 'cd /workspace/anima && hexa run tool/unified_eval.hexa config/unified_eval_shard_i.json'`
   - aggregator: `anima/tool/unified_eval_aggregate.hexa` (NEW, ~100 LOC) — N shard SSOT merge → single roll-up cert
   - gate: `remote_pod_ssh_provisioned + N_pods_drill_ok + shard_conservation_verify`
   - output: `anima/state/unified_eval_distributed_rollup.json`

**success criteria (E.1)**:
- SPEC → actuator 1:1 mapping 4개 모두 landed.
- 각 actuator `--dry` default, `--apply` 시 approval gate + audit log.
- 모든 actuator 의 `policy_self_consistent` verdict = PASS (K59 synthetic trajectory 재사용).
- `airgenome/state/infra_state.json` 에 fleet 현황 (pod count, last sync, last scale event) SSOT.
- cost: K58 DR monthly ~$3, K59 actuator idle $0 (signal-driven), K60 remote dispatch SSH only.

---

### E.2 — hexa stage3 promotion (owner: hexa-lang)

**목표**: hexa stage0 → stage3 full self-compile + reproducible emit.

**sub-deliverables**:

1. **stage0 C dependency 제거** (owner: hexa-lang)
   - file: `hexa-lang/hexa/stage0_c_audit.hexa` (NEW) — list all `#include <...>` + libc call surface
   - target: stage0 binary 가 macOS + Linux 에서 POSIX syscall 만 사용 (no libc string/math 의존 제거 가능한 만큼 제거)
   - release criterion: `strip -x stage0 && codesign --force --sign -` 통과 (upstream note §6 강제)

2. **stage2 self-host 완성** (owner: hexa-lang)
   - fix: `hexa-lang/self/native/hexa_v2` transpiler builtin name mangling (upstream note bug §1)
   - fix: reserved keyword list audit (`generate`, `parse`, `build` 등 사용자 식별자 충돌 mechanism 추가) (upstream note bug §2)
   - fix: stdlib `.find()` method on string + array (upstream note bug §3)
   - verify: 기존 anima tool/*.hexa 전부 stage2 `hexa build` AOT PASS
   - verify: `serve_alm_persona.hexa` + `h100_post_launch_ingest.hexa` dist/ single-file packaging UNBLOCK

3. **stage3 reproducible emit** (owner: hexa-lang)
   - enable: `HEXA_REPRODUCIBLE=1` 모든 emit path (이미 `now()`/`timestamp()` 지원 — upstream note §2)
   - extend: AOT `.c` emit 의 generated file header 에서 timestamp 제거 or `SOURCE_DATE_EPOCH` honor
   - gate: `diff <(HEXA_REPRODUCIBLE=1 hexa build foo.hexa) <(HEXA_REPRODUCIBLE=1 hexa build foo.hexa)` 양쪽 byte-for-byte identical
   - output: `hexa-lang/state/stage3_reproducibility_cert.json`

4. **anima bash bridge 일괄 migrate** (owner: anima, hexa-lang stage2 fix 이후)
   - `anima/tool/*.bash` 전체 wc -l → bridge 후보 리스트 (upstream note §후속 work)
   - 각각 .hexa 단일 파일 재작성 (exec_capture + setenv 활용)
   - byte-for-byte selftest 동일 확인 후 .bash deprecate

**success criteria (E.2)**:
- stage2 AOT build matrix (anima tool/ 전체) ALL PASS — 현재 `serve_alm_persona` 14× clang 에러 0 으로.
- stage3 reproducibility cert PASS (identical rebuild 100 trial).
- anima 측 .bash bridge ≥50% 감축 (목표: serve_alm_persona 333L → .hexa 단일 파일).
- `hexa-lang/ROADMAP.md` 의 `Tier2 #16 stage0 deadlock` 항목 CLOSED.

---

### E.3 — 4-repo 통합 CI (owner: nexus, anima 참조)

**목표**: airgenome / anima / hexa-lang / nexus 통합 ci-validate + cross-repo proposal sync + cross-repo schema cert.

**sub-deliverables**:

1. **통합 ci-validate orchestrator** (owner: nexus)
   - file: `nexus/ci/four_repo_ci_validate.hexa` (NEW, ~400 LOC)
   - 각 repo 의 기존 ci-validate 를 sub-process 로 호출 (nexus drill preflight 재사용)
   - repo unreachable 시 graceful skip + log (upstream note §3)
   - matrix: `anima × hexa-lang × nexus × airgenome` 4 repo × stage (lint / unit / integration / smoke)
   - output: `nexus/state/four_repo_ci_rollup.json` (per-repo verdict + cross-repo consistency)

2. **cross-repo proposal sync 통합** (owner: nexus, 이미 spec 존재)
   - 기존: `anima/docs/upstream_notes/proposal_stack_cross_repo_sync.md` (paste-ready)
   - E.3 에서 실구현: `nexus/tool/proposal_sync_hub.hexa` (NEW, ~350 LOC)
   - shared schema: `nexus/schemas/nexus_proposal_cross_repo_link_v1.json` (NEW)
   - 12h cycle 통합: 각 repo `auto_evolution_loop.hexa` step 9 직전 hub 호출 1줄
   - output: 각 repo 의 `state/cross_repo_sync_log.jsonl` (동일 path)

3. **cross-repo schema cert** (owner: nexus + anima)
   - file: `nexus/schemas/` 내 모든 schema 를 4 repo 가 동일 버전 참조하는지 verify
   - tool: `nexus/tool/schema_cross_repo_verify.hexa` (NEW, ~150 LOC)
   - detect: anima emit 의 cert schema 가 nexus/schemas/ 와 불일치 시 FAIL
   - gate: 4 repo 모두 CI green 상태에서 schema_cross_repo_verify PASS 시 "merge allowed" 신호

4. **GitHub Actions wiring** (owner: 각 repo)
   - 각 repo 의 `.github/workflows/ci.yml` 에 last step: `hexa run ../nexus/ci/four_repo_ci_validate.hexa --self-only`
   - `--self-only` mode: 본 repo stage 만 실행 + rollup result 를 artifact 로 publish
   - nightly job (1 repo): `--full` 모드로 4 repo clone + 통합 실행 (nexus 가 publisher)

**success criteria (E.3)**:
- 4 repo PR 열릴 때마다 `four_repo_ci_validate --self-only` 녹색
- nightly `--full` 1일 1회 실행 → rollup artifact 공개
- cross-repo proposal sync hub 12h cycle 동작 (prev spec 과 동일 criteria)
- cross-repo schema drift detect (제안→hub 자동 debate folder routing)

---

## 3. owner repo 분배 요약

| sub-task | primary owner | secondary | files touched |
|---|---|---|---|
| E.1.1 K56 8-path runner | anima | — | anima/tool/phi_8path_activation_runner.hexa, anima/state/phi_8path_activation_cert.json |
| E.1.2 K58 R2 DR actuator | airgenome | — | airgenome/tool/r2_cross_region_sync_actuator.hexa, airgenome/launchd/com.airgenome.r2_dr_sync.plist, airgenome/state/r2_dr_sync_log.jsonl |
| E.1.3 K59 pod autoscale actuator | airgenome | anima (queue source) | airgenome/tool/pod_autoscale_actuator.hexa, airgenome/state/pod_autoscale_actuator_log.jsonl, anima/state/job_queue.json (new SSOT) |
| E.1.4 K60 remote dispatch | nexus | anima (shard runner + aggregator) | nexus/drill/distributed_eval_remote_dispatch.hexa, anima/tool/unified_eval_shard_runner.hexa, anima/tool/unified_eval_aggregate.hexa, anima/state/unified_eval_distributed_rollup.json |
| E.2.1 stage0 C dep removal | hexa-lang | — | hexa-lang/hexa/stage0_c_audit.hexa, hexa-lang/hexa/stage0 (binary rebuild) |
| E.2.2 stage2 builtin fix | hexa-lang | anima (regression test) | hexa-lang/self/native/hexa_v2 (transpiler), hexa-lang/tests/builtin_name_mangling.hexa |
| E.2.3 stage3 reproducible | hexa-lang | — | hexa-lang/hexa/emit (AOT), hexa-lang/state/stage3_reproducibility_cert.json |
| E.2.4 anima bash bridge migrate | anima | hexa-lang (stage2 dep) | anima/tool/serve_alm_persona.hexa (rewrite from .bash), anima/tool/*.bash (deprecate) |
| E.3.1 four-repo ci-validate | nexus | 각 repo (workflow hook) | nexus/ci/four_repo_ci_validate.hexa, {각 repo}/.github/workflows/ci.yml (1줄 add) |
| E.3.2 proposal sync hub | nexus | anima (P9 step 9 hook) | nexus/tool/proposal_sync_hub.hexa, nexus/schemas/nexus_proposal_cross_repo_link_v1.json, anima/tool/auto_evolution_loop.hexa (1줄 patch) |
| E.3.3 schema cross-repo verify | nexus | anima (cert format) | nexus/tool/schema_cross_repo_verify.hexa, nexus/schemas/ |

---

## 4. 예상 timeline

| week | milestones |
|---|---|
| W1 | E.2.2 hexa stage2 builtin fix (CRITICAL — 모든 하위 작업 prerequisite). upstream note 3 bug fix landing. |
| W2 | E.2.1 stage0 audit + E.2.3 stage3 reproducibility cert. E.1.1 K56 8-path activation runner (anima side, CP2 대기). |
| W3 | E.1.3 pod autoscale actuator (airgenome) + E.1.4 remote dispatch (nexus) parallel. E.2.4 anima bash bridge migrate 시작 (serve_alm_persona 우선). |
| W4 | E.1.2 R2 DR actuator (airgenome) + first manual dry-run. E.3.1 four-repo ci-validate (nexus) scaffold. |
| W5 | E.3.2 proposal sync hub 실구현 + shared schema 등록. |
| W6 | E.3.3 schema cross-repo verify + GitHub Actions wiring 4 repo 전체 + nightly job activate. full green signal 확인. |

- W1-W2 는 hexa-lang 집중, W3-W4 는 airgenome+anima 병렬, W5-W6 는 nexus 집중.
- E.1.1 만 CP2 pass (안ima #10) gate — 나머지는 CP2 독립적.

---

## 5. Hard constraints

- **.roadmap uchg**: 각 repo (anima / hexa-lang / nexus / airgenome) 의 `.roadmap` 수정 금지. 새 entry 필요 시 `anima/tool/roadmap_with_unlock.hexa` 사용 (upstream note §4). 각 repo 의 ROADMAP.md 도 projection only — SSOT 는 `.roadmap`.
- **NO .py**: 모든 신규 tool hexa only. bash 는 hexa stage2 bug fix 전 과도기만 허용 (이후 migrate 의무).
- **SPEC_ONLY_NOT_ACTIVE → ACTIVE 전환 gate**: 각 K56/K58/K59/K60 의 `activation_checklist` 전항목 PASS + `#NN launch decision` .roadmap 에 기록된 후에만.
- **cross-repo mutate 제한**: 한 repo 의 tool 이 다른 repo 의 `state/` 또는 `config/` 수정 금지. 정보 교환은 nexus schema 통해.
- **DR cost guard**: R2 DR sync 는 monthly $3 넘으면 자동 pause + operator alert. `--dry` default 강제.
- **pod autoscale flood protect**: max 3 actuation/hour. 초과 시 manual intervention gate.
- **fake-pass guard**: K56~K60 actuator 각각 audit_notes 에 `no_actual_*: false` 로 전환 + real run timestamp 기록. spec file 의 `no_actual_runpodctl`/`no_actual_replicate`/`no_actual_remote_dispatch` 는 그대로 유지 (spec SSOT 는 spec).
- **4-repo CI graceful degrade**: repo unreachable → skip + log, 전체 fail 아님. 단 nexus (hub) unreachable 시는 fail.
- **prefix migration 1회**: proposal sync hub 의 id prefix rename (anima- / hxa- / nex- / agm-) 은 idempotent. 이미 prefix 있으면 no-op.
- **max 50 cross_repo_links / cycle** (flood protect, upstream spec 상속).
- **stage3 reproducibility SOURCE_DATE_EPOCH 강제**: CI 에서 `HEXA_REPRODUCIBLE=1` 재빌드 2회 byte-identical fail → block merge.

---

## 6. Test plan

E.1 (compute fleet):
1. K56 runner: CP2 미달 상태에서 activation_checklist FAIL 확인 → CP2 mock PASS 입력 시 activate OK.
2. K58 DR: `--dry` 로 EU + APAC 양쪽 object count + bytes 확인 → 수동 approve → first real sync + `rclone check` 0 mismatch.
3. K59 autoscale: K59 synthetic 8-step trajectory replay → actuator log 와 spec 의 decisions[] byte-identical. live ghost mode (`--log-only`) 24h run → actuation 없이 decision log 만 검증.
4. K60 remote dispatch: 4-pod mock (local docker 4개 컨테이너) 로 distributed_eval smoke → conservation_ok + balance_ok + determinism_ok PASS → aggregator roll-up input_n 일치.

E.2 (hexa stage3):
1. builtin mangling regression test: `exec_capture` / `now` / `setenv` 사용하는 minimal .hexa 10개 → `hexa build` AOT ALL PASS.
2. reserved keyword test: `generate` / `parse` / `build` 등 40 예약어 사용자 fn 정의 가능 여부 테스트.
3. stdlib `.find()` coverage: string + array 각각 4 test case.
4. stage3 reproducibility: 20 tool 대상 2회 rebuild sha256 동일 확인.
5. anima bash bridge migrate: serve_alm_persona .bash vs .hexa rewrite 20 run selftest byte-identical output.

E.3 (4-repo CI):
1. 4 repo 모두 minimal fixture → `four_repo_ci_validate --self-only` × 4 → ALL green.
2. 1 repo 의존성 missing inject → 해당 repo FAIL + 나머지 3 repo PASS, rollup verdict = PARTIAL_FAIL.
3. nexus unreachable inject → rollup 자체 fail (hub 필수).
4. proposal sync hub: anima evidence_sources 에 hexa-lang path → link auto-detect + 양쪽 inventory populate.
5. schema drift inject: anima 측 cert schema version 변경 → cross_repo_verify detect → debate folder.
6. nightly `--full` 1회 실행 → artifact publish 확인.

---

## 7. Linkage

- 7-axis framework: A (launch opt) / B (post-H100 research) / C (memory) / D (ship) / **E (infra — 본 문서)** / F (CPU superlimit) / G (meta).
- related specs:
  - `anima/config/phi_8path_substrates_spec.json` (K56)
  - `anima/config/r2_cross_region_replicate.json` (K58)
  - `anima/tool/pod_autoscale_spec.hexa` (K59)
  - `anima/tool/distributed_eval_dispatcher.hexa` (K60)
- upstream dep: `anima/docs/upstream_notes/hexa_lang_20260422.md` (stage1/2 promotion notes + 3 bug).
- cross-repo paradigm: `anima/docs/upstream_notes/proposal_stack_cross_repo_sync.md` (E.3.2 의 실 구현 대상 spec).
- 4-repo layout reference: anima memory `project_workspace.md` (없다면 본 문서 §3 의 owner table 이 de facto).
- roadmap projection: `hexa-lang/ROADMAP.md` Tier2 #16 (stage0 deadlock) — E.2.1 직결.

---

## 8. Paste-ready prompt block (downstream agent 용)

```
TASK: Implement E axis (infra) sub-tasks as specified in
anima/docs/upstream_notes/e_axis_compute_fleet_hexa_stage3_20260422.md.

SELECT sub-task block (W1~W6 timeline 참조):
  - E.1 (compute fleet): K56 / K58 / K59 / K60 actuator promotion
  - E.2 (hexa stage3): stage2 bug fix + stage0 C dep removal + stage3 reproducible
  - E.3 (4-repo CI): four_repo_ci_validate + proposal_sync_hub + schema_cross_repo_verify

DELIVERABLES per sub-task: §2 의 파일 리스트 참조.

CONSTRAINTS:
- NO .py
- 각 repo .roadmap uchg 존중 (tool/roadmap_with_unlock.hexa 사용)
- SPEC_ONLY → ACTIVE 전환은 activation_checklist + #NN launch decision gate 필수
- cross-repo mutate 금지 (nexus schema 경유)
- hexa-lang stage2 bug 3종 fix 없이는 E.1/E.3 tool AOT build 불가 — E.2.2 가 critical path

PROCEED ORDER:
1. hexa-lang W1 (E.2.2 builtin mangling + reserved keyword + .find()) 먼저
2. hexa-lang W2 (E.2.1 + E.2.3) 병행
3. airgenome W3 + anima W3 병렬 (E.1)
4. nexus W5-W6 (E.3)

REPORT: sub-task ID + files touched + success criteria PASS 여부 + blocker list.
```
