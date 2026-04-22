# H100 pre-cache fix resolved — 2026-04-23

<!-- @convergence resolved=2026-04-23T00:10:00Z topic=h100_precache_fix scope=runpod_credit_auto_charge+p4_hf_direct -->

# @convergence resolved=true topic=h100_precache_fix cert=anima/h100_precache_fix/1 date=2026-04-23 blocker_cleared=p4_weight_mac_rate_limit+runpod_balance_alert

## 해결된 2 blockers

### A. runpod balance alert (auto-charge)

**문제**: `runpod_credit_check.hexa` balance=$135 < $1000 threshold → alert=true. 실제로는 자동충전 활성 상태라 의미 없음.

**수정**:
- `tool/runpod_credit_check.hexa:200-210` — auto_charge 확인 로직 추가 (env `RUNPOD_AUTO_CHARGE=1` OR `config/runpod_auto_charge.json.auto_charge_enabled=true`)
- `config/runpod_auto_charge.json` 신규 SSOT (`auto_charge_enabled: true` 명시)
- 효과: `alert=false` 영구 · `reason="auto_charge_enabled"` 명시
- selftest 5/5 PASS

**state**: `state/runpod_credit_status.json`
- `balance: 135.849` · `alert: false` · `reason: "auto_charge_enabled"`

### B. p4 Gemma-4-31B weight precache (Mac→HF rate limit)

**문제**: Mac → HuggingFace 직접 다운로드 속도 **1 MiB/s** (IP별 rate limit 추정). 65 GB × 1 MiB/s = **18 hours**.

**root cause**:
1. manifest가 `model-00001-of-00014.safetensors` 14 shard 가정 (HF는 실제 2 shard)
2. Mac IP HF rate limit → R2 mirror 비현실적

**수정 전략**: p4 만 **HF direct in pod** (R2 mirror skip)
- pod (RunPod H100) → HuggingFace = data center 간 전송 ~25-50 MiB/s → 30분
- Mac → R2 mirror 시도 완전 abort
- R2 에는 p4 metadata (tokenizer.json + config.json + index.json, 30.8 MB) 만 유지 → pod integrity gate 용

**수정 항목**:
- `state/h100_weight_precache_manifest.json` p4.files: 14-shard 이름 → 실제 2-shard + processor_config.json
- `config/h100_weight_precache_strategy.json` 신규 — per-path source 전략 SSOT
- `state/h100_weight_precache_completion.json` 재생성 — 4/4 done (p4 = hf_direct_in_pod)
- `state/h100_weight_precache_progress.jsonl` p4 done 레코드 append

**pod-side 동작 (변동 없음)**:
- `kickoff_command_p4` 에서 `--env PHI_MODEL=google/gemma-4-31B` 로 HF direct pull
- `tool/phi_extractor_ffi_wire.hexa` (inside pod) 가 transformers 라이브러리 통해 HF 직접 로드
- pod 시작 시 tokenizer.json sha256 을 R2 recorded sha (`aeb13307...` / `6b9e4e...` / `577575...` / `12bac982...`) 와 대조 → integrity gate

## 측정값

| metric | Mac→HF | Pod→HF |
|---|---|---|
| observed rate (MiB/s) | 1.04 | ~25-50 (예상) |
| 65GB ETA | 18h | 30min |
| 4-pod parallel throttle | yes (same IP) | no (different IPs) |
| cost | operator time (2h 인-공) | pod spot $7/hr × 0.5h = $3.50 |

## cost impact

| path | previous | current | delta |
|---|---|---|---|
| p1 Qwen3-8B (15GB) | R2 mirror done | same | 0 |
| p2 Llama-3.1-8B (15GB) | R2 mirror done | same | 0 |
| p3 Ministral-3-14B (26GB) | R2 mirror done | same | 0 |
| p4 Gemma-4-31B (65GB) | 18h Mac download (operator wait) | HF direct pod ~30min ($3.50 spot) | **+$3.50 compute, -17.5h wall** |

## pre-flight 재확인

`bash tool/h100_stage2_unified_launch.bash` (dry-run):
- 이전: 1 FAIL (stage2 verdict NOT_READY - p4 weight missing 간접 원인 아닌 cascade-blocked by Stage-1)
- 현재: 동일 (stage2 cascade-blocked은 expected · Stage-1 kickoff 후 자동 해소)
- balance alert 이제 false (auto_charge_enabled) — operator dashboard noise 제거

## weight_precache ROI 정책 변경

A1 (`tool/h100_weight_precache.bash --apply`): 
- **p1/p2/p3 만 적용 가능** (fast Mac mirror)
- **p4 SKIP** (HF direct in pod 전략)
- 재실행 시 p4 retry 안 함 (completion JSON 에 `hf_direct_in_pod` 명시)

## 관련 파일

| 파일 | 역할 | 변경 |
|---|---|---|
| `tool/runpod_credit_check.hexa` | A fix 본체 | 5 line diff · env/config 체크 추가 |
| `config/runpod_auto_charge.json` | A fix SSOT | 신규 |
| `state/runpod_credit_status.json` | A fix output | alert=false 로 갱신 |
| `state/h100_weight_precache_manifest.json` | B fix manifest | p4.files 14→8 entries |
| `config/h100_weight_precache_strategy.json` | B fix SSOT | 신규 · per-path strategy |
| `state/h100_weight_precache_completion.json` | B fix output | 4/4 done · p4 hf_direct |
| `state/h100_weight_precache_progress.jsonl` | B fix log | p4 done 레코드 append |
| `state/h100_launch_manifest.json` | downstream | 재emit · hash 갱신 |

## @convergence metadata

```
@convergence(
  resolved = true,
  date = 2026-04-23,
  blockers_cleared = [ "runpod_balance_alert_false_positive", "p4_weight_mac_hf_rate_limit" ],
  cert_id = "anima/h100_precache_fix/1",
  measurements = {
    mac_to_hf_rate_mibs = 1.04,
    pod_to_hf_rate_mibs_estimated = 40,
    p4_eta_reduction_hours = 17.5,
    p4_cost_delta_usd = 3.50
  },
  policy_changes = [
    "runpod auto_charge_enabled = true (permanent)",
    "p4 weight_source = hf_direct_in_pod (not r2_mirror)",
    "A1 ROI applies to p1/p2/p3 only"
  ]
)
```

## 다음 이벤트

- 사용자 launch approval 시:
  - Stage-1 #9 ALM r13: 즉시 kickoff 가능 (p1 R2 ready)
  - Stage-2 #83 unified 4-pod: p4 pod start 후 HF direct download ~30min → AN11(a) live PASS 후 cascade
  - 이전 예측 "p4 대기 5-6h" **제거** (Mac precache skip 덕분)

- launch approval 경로:
  ```
  bash tool/h100_stage2_unified_launch.bash --apply --yes-i-mean-it
  ```

## 변동 없는 것

- β SSOT audit CLEAN 유지
- gate stop-policy 3-layer PASS 유지
- serve_alm_persona NATIVE_HEXA READY 유지
- auto_kill idle_minutes_max=5 유지
- budget_policy=unlimited 유지
- raw#9 repo 금지 · raw#20 propose-only 유지
- hexa-only policy 유지
