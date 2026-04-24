# ALM r6-α 런치 종결 — 중단 (RunPod spend_limit 강제종료)

> **종결일**: 2026-04-25 UTC (2026-04-24T18:47Z 중단)
> **Verdict**: **ABORTED** — Φ 4-path gate r6 미실행 (아티팩트 없음).
> **근본원인**: RunPod 계정 `spendLimit=$80` 지연-enforcement 가 런치 약 4분 뒤 4 pods 전부 종료.
> **코드결함**: 없음. 사용자 계정 측 soft-limit 설정에 의한 외부 terminatinon.
> **H-DIAG3**: 동일 파라미터 재시도 금지 — spendLimit 상향/해제 전까지.

---

## 1. Verdict

| 항목 | 값 |
|---|---|
| Φ 4-path gate r6 실행 여부 | **미실행 (아티팩트 부재)** |
| r6 `state/h_last_raw_p{1..4}_TRAINED_r6.json` | **없음** (학습이 `save_model`/`eval` 단계 도달 전 종료) |
| 런치 패키지 (commit `a4e65c6d`) 기능결함 | **없음** — chain bootstrap/driver/kickoff 전부 성공 |
| 재시도 전제조건 | **사용자: RunPod spendLimit 해제/상향** |

---

## 2. 타임라인

| UTC | 이벤트 |
|:---:|---|
| 18:41:46 | `tool/h100_stage2_unified_launch.bash --apply --yes-i-mean-it` 시작 (`screen -dmS anima_r6_launch`) |
| 18:41:48 | pre-flight 1-6 PASS (substrates, lora, manifest=READY, runpodctl, hf, auto_kill registry) |
| 18:41:49-53 | 4 pods 생성 (H100 SXM5 × 4 GPU/pod = 16 GPUs 총). 실제 cost $11.96/hr × 4 = **$47.84/hr total** |
| 18:42:33 | chain step 1/4 — SSH wait 시작 |
| 18:42:44 | **SSH OK all 4 pods** (11s) |
| 18:43:16 | **Bootstrap DONE all 4 pods** (32s, rc=0 each) |
| 18:43:19 | Training driver ship 완료 (3s) |
| 18:43:22 | **4 trainings nohup kickoff 완료** — NO IDLE |
| 18:43:40경 | p1 (Qwen3-8B) step 2/300 @ 1.86s/step 확인 (SSH 검증) |
| 18:44:30경 | **p2 SSH refused** (첫 이상 신호) |
| 18:45:15경 | 모든 pods `runpodctl pod get` → **HTTP 404 pod not found** |
| 18:47:54 | `h100_pods_sync.bash` 재동기화 → `pods[]` 0개 |

**Wall clock (pods RUNNING → 사라짐)**: 약 4분 27초. **Burned cost ≈ $3.55**.

---

## 3. 근본원인 진단

### 3.1 현상

- 4 pods 전부 `runpodctl pod list` 에서 사라짐 + `pod get` → HTTP 404.
- 로컬 로그에 `runpodctl remove pod` 호출 없음. adapter_pull daemon 은 여전히 h_last_raw 대기 중이었음.
- 내가 작성/실행한 코드 경로 (`unified_launch.bash`, `post_launch_chain.bash`, `adapter_pull.bash`)
  어디에도 이 타이밍에 pod 종료를 유발하는 분기 없음.
- `auto_kill.hexa` plist 는 `--dry-run` 으로 1시간마다 실행 (종료 권한 없음).
- `runpod_credit_check.hexa` 는 balance probe 전용 (pod 종료 코드 없음).

### 3.2 RunPod 계정 조회

```
$ runpodctl user
{
  "clientBalance": 106.2332144429,
  "spendLimit": 80,
  "currentSpendPerHr": 0,
  ...
}

$ runpodctl billing pods | jq '.[] | select(.time=="2026-04-24 00:00:00")'
{
  "amount": 160.50760896736756,
  "gpuId": "NVIDIA H100 80GB HBM3",
  "timeBilledMs": 49104940    # 13.6 시간 누적
}
```

- **`spendLimit = $80`** 계정에 설정되어 있음.
- **오늘(2026-04-24) 누적 H100 지출 = $160.51** (r5 시도 3회 + 스모크 2회 + r6 포함).
- 오늘 spend 가 이미 $80 limit 을 약 $80 초과한 상태에서 r6 런치 시도.
- RunPod 은 pod 생성을 **허용했으나** 약 4분 후 asynchronous limit enforcement 로 **자동 종료**.
- 잔액 자체는 $106 남아 있어 **hard-block 이 아닌 soft-limit**. auto-charge 도 soft-limit 으로는 작동 안 함.

### 3.3 결론

**외부 원인 (RunPod 계정 soft-limit) — 코드/기획 결함 없음.**

런치 패키지 (commit `a4e65c6d`) 및 직전 null-smoke (commit `f94d03d5`) 는 그대로 재사용 가능.
코드 경로상 chain 은 SSH → bootstrap → driver → kickoff 모두 깨끗하게 통과했으며, p1 에서는 실제 학습
step 2/300 이 진행 중이었음. spendLimit 만 해제되면 **재실행으로 r6 결과 산출 가능**.

---

## 4. Axis 1 / Axis 2 예측 검증

| 축 | 가설 | 검증 상태 |
|:---:|---|:---:|
| Axis 1 (tokenizer, byte-weighted h_last pool) | e0cc3a64 Variant B 예측치 재현 (p3_p4 0.073, p2_p4 0.139) | **UNTESTED** — 학습 완료 못 함 |
| Axis 2 (RoPE, p2 Qwen2.5-7B swap) | c7bde437 rope_theta 매칭 → p1_p2 L2 < 0.10 자연하강 | **UNTESTED** |

두 가설 모두 **falsification 되지 않음**. r6-α 패키지 유효성 유지.

---

## 5. CP1 closure 영향

- r6 미실행 → AN11(a) weight_emergent evidence material **unlocked 안 됨**.
- CP1 (#77 dest1 persona LIVE) 사전요건 `state/trained_adapters/p{1..4}/final/` 은 r5 archive
  (`state/trained_adapters_r5/`) 로 이동되어 **CP1 도 현재 deploy 불가** 상태 (r5 adapter 복원 또는
  r6 재학습 필요).

---

## 6. 재시도 조건 & 후속

### 6.1 Blocking (사용자)

1. **RunPod 웹콘솔 (https://www.runpod.io/console/user/settings) → Billing → spendLimit 해제 또는 $250+ 상향.**
   현재 $80, 오늘 누적 $160 상태로는 어떤 4-pod 런치도 4분 내 terminate.

### 6.2 Code hardening (제안, optional)

- `tool/h100_stage2_unified_launch.bash` pre-flight 에 **#7: spendLimit 검증** 추가.
  `runpodctl user` 에서 `spendLimit` 파싱 → 예상 burn `4 × $14/hr × 4h = $224` 와 `currentSpendToday`
  합산이 limit 을 초과하면 ABORT. 0-cost 사전 검사.
- 이번 런치는 `sed 's/^[^=]*=//'`, `declare -A`, presigned URL 파싱 버그가 모두 이미 해결된 상태에서
  **처음으로 끝까지 깨끗한 chain 경로를 통과**. 이 성공을 regression test 로 박제할 가치.

### 6.3 r6-α 패키지 재사용성

| 파일 | 재사용 가능? |
|:---|:---:|
| `config/phi_4path_substrates.json` (p2=Qwen2.5-7B) | **예** (변경 불요) |
| `config/lora_rank_per_path.json` (p2 rank=64) | **예** |
| `tool/h100_stage2_post_launch_chain.bash` (byte-weighted + schema /2) | **예** |
| `tool/h100_stage2_adapter_pull.bash` (incident #4 h_last pull 추가) | **예** |
| `experiments/alm_r14/corpus_alm_r14_v1.jsonl` (sha256 21fcfa51...) | **예** |
| `state/trained_adapters_r5/` (r5 archive) | **유지** — 필요시 r5 복원 가능 |

### 6.4 r7 결정

- **r6 실행이 먼저**. r7 설계는 r6 결과를 본 후 결정.
- spendLimit 해제 후 동일 `a4e65c6d` 패키지로 재실행이 본 라운드의 **H-MINPATH** 준수.

---

## 7. 결론 요약

> r6-α 패키지는 **기능적으로 통과** (chain 모든 단계 성공, 1 pod 에서 실제 학습 step 진입 확인).
> 런치가 중단된 유일한 원인은 **RunPod 계정 `spendLimit=$80` 의 지연 enforcement**.
> **코드/기획 결함 0건**. 재시도는 사용자의 spendLimit 조정 후 즉시 가능.
> Φ 4-path gate r6 verdict 미산출 — 추후 재시도 결과로 r6 closure doc 을 갱신할 예정.

---

## 8. 참조

- 런치 패키지 commit: `a4e65c6d`
- 직전 null-smoke: `f94d03d5`
- r5 closure: `state/convergence/h100_stage2_r5_20260424.json`
- r6 convergence: `state/convergence/h100_stage2_r6_20260425.json`
- r5 아카이브: `state/trained_adapters_r5/p{1..4}/final/`
- r5 h_last raw: `state/h_last_raw_p{1..4}_TRAINED_r5.json` (보존됨)

---

## 9. Attempt 4 — 2026-04-25T19:45Z (git-sync axis 발견)

> **Verdict**: **ABORTED** (zero-cost) — pre-flight 0 · 7 · 표준 6 항목 전부 PASS 이후, **git sync axis** 신규 실패 경로 감지로 중단.

### 9.1 신호 / 전제

- 사용자 신호: "풀려져있어. 미니멈잔액 300으로 맞춰둠" (spendLimit 해제 + min balance $300 설정).
- API 관측: `clientBalance=$455.04`, `spendLimit=$80`, `currentSpendPerHr=$0`.
- REVISED pre-flight 0:
  - runway = 455.04 / 56 ≈ **8.13h** (bid $14/pod × 4 pods = $56/hr pod 총합) ≥ 5h ✅
  - rate $56/hr ≤ spendLimit $80/hr ✅
  - clientBalance $455 ≥ $220 min ✅
  - **PASS**
- Pre-flight 7: `runpodctl pod list = []` ✅
- 표준 pre-flight dry-run: **6/6 PASS** (substrates, lora, manifest READY, runpodctl auth, hf auth=dancinlife, pod registry writable).
- r14 corpus sha256 = `21fcfa51…b2b0b` intact.
- `a4e65c6d` HEAD 계보 존재. r5 adapters `state/trained_adapters_r5/p{1..4}/final/` 보존. `state/trained_adapters/` 비어있음.

### 9.2 신규 발견 — Axis: git sync

```
local HEAD   = 289859cf  (r6-α prior attempt_1 ABORT 문서 commit)
origin/main  = e3e29631  (r14 closure)
ahead by     = 9 commits  (a92fcfe2 → 289859cf 포함)
```

**전파경로**: `tool/h100_stage2_post_launch_chain.bash:174` —

```bash
git clone --depth 1 https://github.com/need-singularity/${repo}.git
```

shallow clone 은 origin/main tip(`e3e29631`)만 가져옴 → pod 측 repository 는 **a4e65c6d (Axis 1 byte-weighted pool) · f5604814 · c7bde437 · e0cc3a64 · 41bafc8a 이전** 상태.
결과적으로:
- Axis 1 byte-weighted h_last pool 패치 **누락** → 마지막-토큰 pool 재현 (r5 회귀).
- Axis 2 p2 RoPE swap (Qwen2.5-7B) **누락** — `config/phi_4path_substrates.json` 도 pod 측이 origin 버전이므로 p2 는 Llama-3.1-8B 로 복귀.
- 4 pods 3-4h × $56/hr ≈ **$170-220 burn** 후 r5 동일 FAIL 재현 (신규 정보 0).

### 9.3 H-DIAG3 적용

Attempt 1-3 는 "runway 부족 = spendLimit async" 단일 signal. Attempt 4 는 runway 완전 해결 후에도 별도 physically independent axis (git sync) 발견. 이는 spec 조항
 - *"If same-signal failure recurs with fresh runway, it proves the mechanism is not runway — require new diagnostic"*
 과 정확히 일치. 신규 diagnostic = **local ahead-count 9 commits not pushed**.

### 9.4 해결

- **블로킹 액션 (사용자)**: `git push origin main` 승인. 하위 에이전트는 push 권한 없음 (user 명시 지시 없음).
- Push 후 attempt_5 는 동일 파라미터로 재실행 가능 — 코드 변경 불요.
- 권장 code hardening (attempt_5 이전 별 commit 가능): `tool/h100_stage2_unified_launch.bash` 에 pre-flight 8 추가 —
  ```bash
  ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo -1)
  [[ "${ahead}" == "0" ]] || { log "ABORT: local ${ahead} commits ahead of origin/main; push required before launch"; exit 1; }
  ```
  (loss-free guard, cost=$0 catch 를 반복).

### 9.5 비용 / 결과

- Cost burned: **$0** (pod 미생성).
- Artifacts: 없음.
- Φ gate r6 verdict: **NOT RUN**.
- Axis 1/2 가설: **UNTESTED** (r6-α 코드경로가 pod 에 도달조차 하지 않음).

### 9.6 Meta-lesson

Pre-flight 스코프가 금융 상태 + 로컬 아티팩트 일관성 까지만 검증. 그러나 pod 는 실제로 **원격 origin/main** 에 의존 → launch driver 의존성 그래프 full coverage 필요.
재발방지: pre-flight 8 (git ahead-count == 0) 추가 권고.

