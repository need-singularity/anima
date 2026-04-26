# AWS Braket 가입 가이드 — anima-physics 5-substrate cover

이 문서는 anima-physics 의 cloud-substrate 확장을 위한 AWS Braket 계정 신규 가입과 비용 안전망 설정 가이드다. Braket 1 account 로 5 substrate (Rigetti·IQM superconducting / IonQ·AQT trapped-ion / QuEra Aquila analog Rydberg) 동시 cover.

> **raw#10 honest**: AWS Braket 은 free tier 가 거의 없는 사용량 과금 cloud 다 (시뮬레이터 분당 $0.075, 실제 hardware 는 task당 + shot당 변동 과금). 본 cycle 의 hexa facade 는 default `ANIMA_BRAKET_DRY_RUN=1` 로 cost-safe. 실제 호출 시 사용자 비용 발생.

---

## Section 1. AWS Account 가입

1. https://signin.aws.amazon.com/signup 에서 `Create AWS Account` 클릭.
2. 이메일 / 패스워드 / account name 입력.
3. **결제 카드 등록 필수** (free tier 라도 카드 등록 강제).
4. 전화 번호 인증 (SMS 또는 음성).
5. Support plan = **Basic (free)** 선택.
6. 가입 완료 후 root account 로 로그인.

---

## Section 2. Braket Service 활성화 + Region 선택

1. AWS Console → 검색창에 `Braket` → `Amazon Braket` 클릭.
2. `Get started with Amazon Braket` → **service terms 동의** (3rd-party device 제공자 데이터 처리 동의).
3. **Region 선택** (devices 별 region 다름):
   - **Rigetti Ankaa-3** → `us-west-1` (N. California)
   - **IonQ Aria/Forte** → `us-east-1` (N. Virginia)
   - **IQM Garnet** → `eu-north-1` (Stockholm)
   - **QuEra Aquila** → `us-east-1` (N. Virginia)
   - **권장**: 4 device 가용성 위해 `us-east-1` 기본 + Rigetti 호출 시 `us-west-1` 명시.
4. Braket Console 접근 가능 확인.

---

## Section 3. IAM User 생성 + Braket Policy + Access Key

> **root account 로 직접 access key 만들지 말 것** — 보안 모범 사례 위반.

1. AWS Console → `IAM` → `Users` → `Create user`.
2. User name = `anima-physics-braket` (예).
3. `Attach policies directly` 선택 → `AmazonBraketFullAccess` 검색 + 추가.
4. (선택) `IAMReadOnlyAccess` 도 추가하면 콘솔 자가-진단 편함.
5. User 생성 완료 후 `Security credentials` tab → `Create access key`.
6. Use case = `Command Line Interface (CLI)` 선택.
7. **Access key ID** + **Secret access key** 즉시 다운로드 (.csv) — secret 은 다시 볼 수 없음.

---

## Section 4. 환경 변수 설정

`~/.zshrc` 또는 `~/.bash_profile` 에 추가:

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="us-east-1"
# anima-physics cost-safe default (반드시 1 유지, 실호출 시 0)
export ANIMA_BRAKET_DRY_RUN=1
```

또는 `~/.aws/credentials` (보안 더 권장):

```
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
region = us-east-1
```

검증:

```bash
anima-physics/.venv/bin/python3 -c "import boto3; print(boto3.client('braket').list_devices(maxResults=3))" | head -5
```

---

## Section 5. 비용 Cap — Budgets + Alarm + Spending Limit

> **본 cycle 의 핵심 안전장치**. 가입 직후 반드시 설정.

### 5.1 Monthly Budget ($5 권장)

1. AWS Console → `Billing and Cost Management` → `Budgets` → `Create budget`.
2. Budget type = `Cost budget - Recommended`.
3. Period = `Monthly`, amount = **$5.00** (anima-physics dev/test 권장 한도).
4. Threshold:
   - **Actual** at 50% ($2.50) → email alarm
   - **Actual** at 80% ($4.00) → email alarm
   - **Forecasted** at 100% ($5.00) → email alarm
5. Email = 본인 주소 (예: `nerve011235@gmail.com`).

### 5.2 (Optional) AWS Service Quota — Braket Quantum Tasks

1. `Service Quotas` → `Amazon Braket` → 요청별 quota 확인.
2. Default 는 충분히 낮음; 별도 제한 안 해도 됨.

### 5.3 IAM Policy 로 Hard Stop (advanced)

`AmazonBraketFullAccess` 외에 deny policy 추가:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Deny",
      "Action": "braket:CreateQuantumTask",
      "Resource": "*",
      "Condition": {"StringNotEquals": {"aws:RequestTag/anima-cycle": "approved"}}
    }
  ]
}
```

→ 사용자가 명시적으로 tag 지정한 task 만 실행되게 강제 (선택).

---

## Section 6. Device ARN 별 호출 명령

| Substrate | Provider | Device | ARN | Region |
|-----------|----------|--------|-----|--------|
| Superconducting | Rigetti | Ankaa-3 | `arn:aws:braket:us-west-1::device/qpu/rigetti/Ankaa-3` | us-west-1 |
| Superconducting | IQM | Garnet | `arn:aws:braket:eu-north-1::device/qpu/iqm/Garnet` | eu-north-1 |
| Trapped-ion | IonQ | Aria-1 | `arn:aws:braket:us-east-1::device/qpu/ionq/Aria-1` | us-east-1 |
| Trapped-ion | IonQ | Forte-1 | `arn:aws:braket:us-east-1::device/qpu/ionq/Forte-1` | us-east-1 |
| Analog Rydberg | QuEra | Aquila | `arn:aws:braket:us-east-1::device/qpu/quera/Aquila` | us-east-1 |

> 본 cycle 은 Rigetti Ankaa-3 + QuEra Aquila 만 cover. 나머지 sibling cycle.

### 6.1 DRY_RUN 모드 (default — cost $0)

```bash
# Rigetti
hexa run anima-physics/superconducting/cloud_facade_poc.hexa
# QuEra Aquila
hexa run anima-physics/analog/cloud_facade_poc.hexa
```

→ verdict 기대값 (creds 없을 때): `PREP_NO_CREDS_DEGRADED`
→ verdict 기대값 (creds 있을 때): `PREP_DRY_RUN_PASS` (api_call_count=0 검증)

### 6.2 LIVE 모드 (실제 hardware 호출 — 비용 발생!)

```bash
# 비용 cap 설정 확인 후
export ANIMA_BRAKET_DRY_RUN=0

# Rigetti 4-qubit GHZ (예상 비용 $0.30 – $1.00)
hexa run anima-physics/superconducting/cloud_facade_poc.hexa

# QuEra Aquila 4-atom MIS (예상 비용 $0.30 – $1.00)
hexa run anima-physics/analog/cloud_facade_poc.hexa
```

→ verdict 기대값: `LIVE_PASS` 또는 `LIVE_FAIL_<reason>`

### 6.3 Self-test (cloud 호출 없음)

```bash
hexa run anima-physics/superconducting/cloud_facade_poc.hexa --selftest
hexa run anima-physics/analog/cloud_facade_poc.hexa --selftest
```

→ venv / SDK / credential 검출만 점검. cost = $0.

---

## Section 7. 실제 비용 vs Free Tier (raw#10 honest)

| Item | Cost | Notes |
|------|------|-------|
| Account 가입 | $0 | Free |
| Braket service activation | $0 | Free |
| Local SV1/DM1 simulator | $0.075/min | usage-based |
| QPU Rigetti Ankaa-3 | $0.30/task + $0.00035/shot | task당 minimum |
| QuEra Aquila | $0.30/task + $0.01/shot | analog AHS |
| IonQ Aria | $0.30/task + $0.03/shot | premium |
| Free Tier monthly credit | $0 | **Braket has NO standalone free tier as of 2026-04** |

> 본 cycle 4-qubit/4-atom probe (100 shots 2회) 예상 비용:
> - Rigetti: ~$0.67 (2 task × $0.30 + 200 shot × $0.00035)
> - QuEra: ~$2.60 (2 task × $0.30 + 200 shot × $0.01)
> 합 ~$3.27 (1 cycle full LIVE).

---

## Section 8. 후속 단계 (sibling cycle)

본 cycle 종료 후, **사용자 명시 명령 시** 다음 단계 진행:

1. AWS account 가입 + IAM key 발급
2. budget cap $5 설정 + 메일 alarm 활성
3. `~/.aws/credentials` 또는 env 설정 + DRY_RUN selftest 재실행 (PREP_DRY_RUN_PASS 확인)
4. `ANIMA_BRAKET_DRY_RUN=0` + LIVE 호출 (1 device 씩 단계 진행 권장)
5. Marker (`state/v10_anima_physics_cloud_facade/poc_*/marker.json`) verdict = `LIVE_PASS` 확인

---

## Section 9. 산출물 매핑

| File | Role |
|------|------|
| `anima-physics/superconducting/cloud_facade_poc.hexa` | raw#9 Rigetti facade |
| `anima-physics/analog/cloud_facade_poc.hexa` | raw#9 QuEra facade |
| `scripts/anima_physics_braket_rigetti_probe.py` | raw#37 Rigetti probe |
| `scripts/anima_physics_braket_quera_probe.py` | raw#37 Aquila probe |
| `state/v10_anima_physics_cloud_facade/poc_superconducting_braket_rigetti/marker.json` | Rigetti silent-land marker |
| `state/v10_anima_physics_cloud_facade/poc_analog_braket_quera/marker.json` | QuEra silent-land marker |
| `anima-physics/docs/aws_braket_signup_guide.md` | 본 가이드 |
