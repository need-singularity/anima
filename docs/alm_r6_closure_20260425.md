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
