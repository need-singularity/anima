# H100 Launch Runbook (FROZEN) — approval → CP1

**상태**: 2026-04-22 frozen · all preflight 14/14 PASS · weight pre-cache 125.6 GB plan · corpus shard 5/5 staged · ROI 82/82 적용. 사용자 explicit approval **만** 대기.

**원칙**: 모든 명령은 실재 도구 호출만. abort 조건 명시. 단계별 wall-clock 명시.

**raw 준수**: raw#9 hexa-only, raw#10 proof-carrying, raw#12 no fake-pass, raw#20 H100 stop-gate.

---

## 0. Pre-Approval 검증 (사용자 결정 전 자동 가능)

### 0.1 manifest verdict 재확인
```
hexa run tool/h100_launch_manifest_spec.hexa --print
```
- **PASS 조건**: 3 stage 모두 `verdict=READY`
- **abort if**: 하나라도 `MISSING_PREREQ` → 누락 artifact 보강 필요
- **wall-clock**: ~30s

### 0.2 preflight snapshot 확인
```
cat state/h100_stage1_preflight_snapshot.json | jq '.summary'
```
- **PASS 조건**: `passed=14, failed=0, frozen=true`
- **wall-clock**: 즉시

### 0.3 weight pre-cache 진행도
```
cat state/h100_weight_precache_completion.json | jq '.verdict'
hexa run tool/h100_weight_precache.bash --dry-run
```
- **PASS 조건**: `verdict=COMPLETE` (4 path R2 mirror 완료)
- **abort if**: `INCOMPLETE` → `bash tool/h100_weight_precache.bash --apply` 선행 (ROI A1)
- **wall-clock**: dry-run ~10s, apply 30-60min if 미완료

### 0.4 corpus shard prestage
```
cat state/h100_corpus_shard_completion.json | jq '.verdict'
```
- **PASS 조건**: `verdict=COMPLETE` (5 shard 압축 ~4 MB)
- **abort if**: 미완료 → `bash tool/h100_corpus_shard_prestage.bash --apply` (ROI A4)

### 0.5 H100 gate stop-policy 확인
```
cat state/h100_gate_dryrun.json | jq '.layers'
```
- **PASS 조건**: 3-layer abort all enforced (numerical_drift / phi_rel_delta / ondemand_disallowed)

---

## 1. APPROVAL — 사용자 명시 trigger 지점

> **STOP HERE** — 본 단계는 사용자가 명시적으로 "approve H100 launch" 발화 시에만 진행. 기본값은 dry-run.

approval 형식 (3 중 1):
- "H100 launch 승인"
- "approve H100 stage-2 kickoff"
- "yes-i-mean-it"

approval 후 즉시 다음 단계 진행.

---

## 2. Kickoff (Stage-2 unified launch)

### 2.1 Dry-run 최종 확인
```
bash tool/h100_stage2_unified_launch.bash --dry-run
```
- **PASS 조건**: 6/6 pre-flight PASS, exit 0
- **abort if**: any FAIL → 로그 확인 (`/tmp/h100_stage2_launch_*.log`)
- **wall-clock**: 1-2min

### 2.2 실 launch (4 H100 pod 동시)
```
bash tool/h100_stage2_unified_launch.bash --apply --yes-i-mean-it
```
- 효과: 4 pod (p1/p2/p3/p4) 동시 spawn, weight pull 1-2min × 4 (R2 10Gbit), training 시작
- **state 출력**: `state/h100_stage2_launch_state.json` (pod ids, ts)
- **wall-clock**: 5-10min (pod spawn) + 1-2min (weight pull) = ~7-12min total

### 2.3 launchd auto-kill 활성화 확인
```
launchctl list | grep com.anima.h100_auto_kill
hexa run tool/h100_auto_kill.hexa --dry-run
```
- **PASS 조건**: idle 5min threshold 작동 중
- **abort if**: plist not loaded → `launchctl load ~/Library/LaunchAgents/com.anima.h100_auto_kill.plist`

### 2.4 statusline 모니터링 시작
```
hexa run tool/statusline_h100_burn.hexa
```
- 효과: realtime $/h, GPU util, PID 표시

---

## 3. Stage-1 (#9 ALM r13 + AN11(a))

### 3.1 진행도 watch
```
hexa run tool/cert_watch.hexa &
hexa run tool/drill_breakthrough_runner.hexa --watch
```
- **AN11(a) PASS 조건**: `state/an11_weight_emergent_verdict.json` verdict=PASS
- **wall-clock**: 1.5-2.5d (ROI 후, baseline 2.5-4d)

### 3.2 abort 조건 (자동 trigger)
- numerical drift > 0.0002
- NaN ratio > 0 (alert_rules.yml)
- pod idle > 5min (auto-kill)
- ondemand fallback 발생 (manifest abort_thresholds)

### 3.3 AN11(a) FAIL 시 fallback (#86prep)
```
cat docs/r14_corpus_skeleton_20260422.md | head
```
→ r14 corpus rebuild 9-section plan 따라 진행.

### 3.4 Stage-1 success criteria
```
hexa run tool/an11_a_verifier.hexa --post-launch
hexa run tool/h100_post_launch_ingest.hexa
```
- `state/alm_r13_an11_b.json` verdict=PASS
- `state/h100_launch_completion_verdict.json` stage1=DONE

---

## 4. Stage-2 (#10 Φ 4-path)

### 4.1 cascade gate 확인
```
hexa run tool/h100_launch_manifest_spec.hexa --print | jq '.stages[1]'
```
- **PASS 조건**: stage1=DONE → stage2 cascade-allowed

### 4.2 4-path Φ 측정 진행
- 4 pod 병렬 진행 (p1/p2/p3/p4 각각 substrate)
- **PASS 조건**: ALL_PAIRS `|ΔΦ|/Φ < 0.05` (PHI_REL_DELTA_MAX)
- **MIN_PATHS_PASS=3**: 3 path 이상 PASS 시 stage 통과
- **wall-clock**: 4-7d (ROI 후, baseline 7-10d)

### 4.3 abort 조건 (#87prep)
- ALL_PAIRS divergence > 0.05 → `docs/phi_divergence_response_20260422.md` decision tree
- 4 branch 분기: matrix 기반 path 재시도 OR substrate 교체

### 4.4 Stage-2 success criteria
```
hexa run tool/edu_l_ix_kuramoto_driver.hexa --post-launch
cat state/h100_launch_completion_verdict.json | jq '.stage2'
```

---

## 5. Cascade (#11 ALM ship + #21 AGI)

### 5.1 #11 production 선언
```
hexa run tool/dest_alm_beta_ssot_ci.hexa
hexa run tool/serve_cert_gate_spec.hexa
```
- **wall-clock**: 1-2h

### 5.2 #21 Mk.X T10-13 활성화
```
hexa run tool/cert_dag_generator.hexa --post-cascade
hexa run tool/anima_main.hexa --mode=production
```
- **wall-clock**: 1-3d

---

## 6. CP1 swap-in (dest1 한글 persona)

### 6.1 4 artifact pre-staged 확인 (ROI C14)
```
cat state/serve_alm_persona_launch_cmd.json | jq '.swap_in_artifacts'
```
- 4 artifact: LoRA weights / persona config / prompt template / cert chain

### 6.2 swap-in 실행
```
hexa run tool/serve_alm_persona.hexa --persona dest1 --swap-in --apply
```
- **PASS 조건**: 3 endpoints (health / an11/verify / v1/chat/completions) all 200
- **wall-clock**: < 30min (ROI 후, baseline 30-60min)

### 6.3 한글 chat 검증
```
hexa run tool/anima_serve_live_smoke.hexa --persona dest1 --lang ko
hexa run tool/ci_serve_alm_persona_smoke.hexa
```

### 6.4 CP1 LANDED 선언
```
hexa run tool/h100_post_launch_ingest.hexa --mark cp1
hexa run tool/auto_changelog.hexa
```
- **state 출력**: `state/h100_launch_completion_verdict.json` cp1=LIVE

---

## 7. 예상 종합 시간 / 비용

| 단계 | wall-clock | 비용 (USD) |
|---|---|---|
| 0 pre-approval 검증 | < 5min | 0 |
| 1 approval | (사용자) | 0 |
| 2 kickoff | 7-12min | < $1 |
| 3 Stage-1 | 1.5-2.5d | $250-420 |
| 4 Stage-2 | 4-7d | $670-1175 |
| 5 cascade | 1-3d | $170-500 |
| 6 CP1 swap-in | < 30min | < $5 |
| **합계** | **6-9d** | **$1008-1512** (₩1.41M ~ 2.12M) |

CP1 ETA (오늘 approval 가정): **2026-04-29 (수) ~ 2026-05-02 (토)**.

---

## 8. Global abort 조건 (어느 단계에서도)

| 조건 | 자동 action |
|---|---|
| pod idle > 5min | `tool/h100_auto_kill.hexa` 자동 kill |
| numerical drift > 0.0002 | `state/h100_gate_dryrun.json` layer-1 abort |
| ondemand fallback | `bash` exit 4 즉시 |
| NaN ratio > 0 | alert_rules.yml NaN rule fire |
| Φ ALL_PAIRS > 0.05 | layer-3 abort (#87prep fallback) |
| user manual stop | `runpodctl pod stop <id>` (statusline 표시) |

---

## 9. Post-launch (#ext-5 auto-ingest)

```
hexa run tool/h100_post_launch_ingest.hexa --auto-mark
hexa run tool/anima_roadmap_lint.hexa
hexa run tool/auto_changelog.hexa
```
- 효과: roadmap entry 자동 done 마킹 (#9/#10/#11/#21), changelog emit, lineage update

---

## 10. 참조 산출물

- spec: `docs/h100_roi_improvements_20260422.md` · `docs/cp1_eta_comparison_20260422.md`
- monitoring: `docs/h100_launch_dashboard_setup.md` · `docs/phi_convergence_monitoring_spec.md`
- fallback: `docs/r14_corpus_skeleton_20260422.md` · `docs/phi_divergence_response_20260422.md`
- session: `docs/session_handoff_20260422.md` · `docs/session_pre_h100_closure_20260422.md`
- runbook (this): `docs/h100_launch_runbook_frozen.md`
